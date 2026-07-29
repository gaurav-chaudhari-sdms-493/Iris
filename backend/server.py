"""
FastAPI Server & WebSocket Telemetry Provider
Exposes REST and WebSockets APIs for Project Iris Frontend Dashboard.
FSD Reference: Section 8
"""

import asyncio
import cv2
import json
import logging
from typing import Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from orchestrator import IrisOrchestrator
from config import SWITCH_MAPPINGS, SPATIAL_ZONES

import os
import torch
import cv2

# Cap processing power to half of system threads (50% CPU allocation)
total_cores = os.cpu_count() or 4
half_cores = max(1, total_cores // 2)
try:
    torch.set_num_threads(half_cores)
except Exception:
    pass
cv2.setNumThreads(half_cores)
os.environ["OMP_NUM_THREADS"] = str(half_cores)
os.environ["MKL_NUM_THREADS"] = str(half_cores)
os.environ["OPENBLAS_NUM_THREADS"] = str(half_cores)

logger = logging.getLogger("iris.server")
logging.basicConfig(level=logging.INFO)
logger.info(f"[CPU Power Management] Process allocated {half_cores} threads out of {total_cores} system cores (50% CPU limit).")

app = FastAPI(title="Project Iris Backend Engine", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = IrisOrchestrator()
connected_websockets = set()

# Models
class SwitchOverrideRequest(BaseModel):
    switch_id: str
    state: bool

class ModeRequest(BaseModel):
    mode: str

class ACRequest(BaseModel):
    temperature: Optional[int] = None
    power: Optional[str] = None
    mode: Optional[str] = None
    fan_speed: Optional[str] = None

class PlayerControlRequest(BaseModel):
    action: str
    value: Optional[Any] = None


@app.on_event("startup")
async def startup_event():
    logger.info("Project Iris Backend API starting up...")
    asyncio.create_task(background_telemetry_loop())

async def background_telemetry_loop():
    """Runs frame processing loop at 5 FPS and broadcasts telemetry via WebSocket."""
    while True:
        try:
            # Read frame in worker thread to avoid blocking main asyncio event loop
            frame = await asyncio.to_thread(
                orchestrator.stream_gen.read_frame,
                orchestrator.zone_states,
                orchestrator.headcount
            )

            # Process motion and occupancy step in worker thread
            telemetry = await asyncio.to_thread(
                orchestrator.process_telemetry_step,
                frame
            )

            # Broadcast to all connected React WebSocket clients
            if connected_websockets:
                payload = json.dumps(telemetry)
                disconnected = set()
                for ws in list(connected_websockets):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                connected_websockets.difference_update(disconnected)

        except Exception as e:
            logger.error(f"Error in background telemetry loop: {e}")

        await asyncio.sleep(0.2)  # 5 FPS (200ms)


@app.get("/api/telemetry")
async def get_telemetry():
    """Returns instant telemetry JSON snapshot."""
    return orchestrator.get_telemetry()

@app.get("/api/switches")
async def get_switches():
    """Returns physical switch mapping catalog."""
    return {"switches": SWITCH_MAPPINGS, "relays": orchestrator.tuya.get_state()}

@app.post("/api/override")
async def override_switch(req: SwitchOverrideRequest):
    """Executes manual switch override (S1-S12)."""
    success = orchestrator.trigger_manual_switch(req.switch_id, req.state)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to override switch {req.switch_id}")
    return {"status": "success", "switch": req.switch_id, "state": req.state}

@app.post("/api/mode")
async def set_system_mode(req: ModeRequest):
    """Sets system operating mode (AUTO, PRESENTATION, POWER_SAVING, MANUAL)."""
    mode = req.mode.upper()
    if mode == "PRESENTATION":
        res = orchestrator.activate_presentation_mode()
    elif mode in ["AUTO", "POWER_SAVING", "MANUAL"]:
        orchestrator.system_mode = mode
        if mode == "POWER_SAVING":
            for z_id in SPATIAL_ZONES:
                orchestrator._apply_zone_lighting(z_id, False)
            orchestrator.broadlink.send_ac_command(24, power="OFF")
            orchestrator.broadlink.toggle_tv_power("OFF")
        res = orchestrator.get_telemetry()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid mode {mode}")

    return {"status": "success", "mode": mode, "telemetry": res}

@app.post("/api/ac")
async def set_ac(req: ACRequest):
    """Manual AC control endpoint."""
    current_ac = orchestrator.broadlink.ac_state
    temp = req.temperature if req.temperature is not None else current_ac.get("temperature", 24)
    power = req.power if req.power is not None else current_ac.get("power", "ON")
    mode = req.mode if req.mode is not None else current_ac.get("mode", "COOL")
    fan = req.fan_speed if req.fan_speed is not None else current_ac.get("fan_speed", "AUTO")
    
    orchestrator.broadlink.send_ac_command(temp, power=power, mode=mode, fan=fan)
    res = orchestrator.broadlink.ac_state

    if connected_websockets:
        payload = json.dumps(orchestrator.get_telemetry())
        for ws in list(connected_websockets):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    return {"status": "success", "ac_state": res}

@app.post("/api/player/control")
async def control_player(req: PlayerControlRequest):
    """Player control endpoint (play, pause, toggle, seek, seek_relative, set_speed, set_source, step, live)."""
    res = orchestrator.control_player(req.action, req.value)
    if connected_websockets:
        payload = json.dumps(orchestrator.get_telemetry())
        for ws in list(connected_websockets):
            try:
                await ws.send_text(payload)
            except Exception:
                pass
    return {"status": "success", "player_state": res}

@app.get("/video_feed")
async def video_feed():
    """MJPEG stream endpoint for real-time video preview in React frontend."""
    async def generate():
        while True:
            frame = await asyncio.to_thread(
                orchestrator.stream_gen.read_frame,
                orchestrator.zone_states,
                orchestrator.headcount
            )
            # Draw motion bounding boxes on stream overlay
            for x, y, bw, bh in orchestrator.latest_motion_boxes:
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 255), 2)
                cv2.putText(frame, "MOTION", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            # Draw person boxes on stream overlay
            for p in orchestrator.latest_person_boxes:
                bx, by, bw, bh = p["bbox"]
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
                cv2.putText(frame, f"PERSON {p.get('confidence', '')}", (bx, by - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

            ret, jpeg = await asyncio.to_thread(cv2.imencode, '.jpg', frame)
            if not ret:
                await asyncio.sleep(0.05)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            await asyncio.sleep(0.05)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """WebSocket endpoint broadcasting live telemetry and receiving commands."""
    await websocket.accept()
    connected_websockets.add(websocket)
    logger.info(f"WebSocket client connected. Active clients: {len(connected_websockets)}")

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                action = msg.get("action")
                if action == "override":
                    orchestrator.trigger_manual_switch(msg.get("switch_id"), msg.get("state"))
                elif action == "preset":
                    if msg.get("preset") == "PRESENTATION":
                        orchestrator.activate_presentation_mode()
                    elif msg.get("preset") == "POWER_SAVING":
                        orchestrator.system_mode = "POWER_SAVING"
                        for z_id in SPATIAL_ZONES:
                            orchestrator._apply_zone_lighting(z_id, False)
                        orchestrator.broadlink.send_ac_command(24, power="OFF")
                    elif msg.get("preset") in ["AUTO", "MANUAL"]:
                        orchestrator.system_mode = msg.get("preset")
                elif action == "headcount_simulate":
                    # Debug slider simulation for headcount testing
                    orchestrator.headcount = int(msg.get("count", 2))
                elif action == "player_control":
                    orchestrator.control_player(msg.get("control_action"), msg.get("value"))
                    if connected_websockets:
                        payload = json.dumps(orchestrator.get_telemetry())
                        for ws in list(connected_websockets):
                            try:
                                await ws.send_text(payload)
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")

    except (WebSocketDisconnect, Exception) as e:
        connected_websockets.discard(websocket)
        logger.info(f"WebSocket client disconnected.")


# Serve Frontend Static Build on Backend Port 8008 for Convenience
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_frontend_root():
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"status": "Project Iris Backend API Live"}

