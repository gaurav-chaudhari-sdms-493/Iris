# **Project Iris - Detailed Technical Implementation Guide (FSD)**

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`

---

## **1. Executive Summary**

Traditional PIR motion sensors are inefficient for commercial office environments—they fail to detect stationary employees at desks, cause lights to shut off unexpectedly, and cannot dynamically scale Air Conditioning based on occupant load.

**Project Iris** is a hybrid IoT and Computer Vision automation engine designed for STARK AI commercial office spaces. It utilizes an overhead CCTV camera feed (or synthetic MP4 video input) combined with lightweight PyTorch YOLOv8 object detection and OpenCV fast spatial motion analysis:

> 1. **Instant Spatial Motion Lighting (<200 ms delay):** Triggered by fast pixel-difference contour detection across designated room bounding boxes.
> 2. **Real-Time 1-Second YOLO Occupancy Engine:** Evaluates headcount snapshot frames to dynamically control lighting levels and AC setpoints.
> 3. **Fine-Grained Auto-Off Timers:** Prevents wasted electricity by applying staggered vacancy shutoffs (Light Bulbs: 3s, LED Panels: 5s, AC/TV: 10 mins).
> 4. **Anti-Flicker Hysteresis:** Retains auxiliary lighting rows for 3 seconds during headcount drops to ensure smooth visual transitions.

---

## **2. Hardware Architecture & Bill of Materials (BOM)**

- **Vision Source:** Existing Ceiling Dome CCTV Camera (accessible via local IP/RTSP stream) or local file (`backend/video.mp4`).
- **Edge Compute:** Local Workstation (Intel i7 / multi-core CPU) allocated max 50% CPU thread utilization (`torch.set_num_threads`).
- **Lighting Control:** **AZIOT 4 Node Smart Switch** (Tuya-compatible 4-relay module).
  - *Mounting Strategy:* Installed inside standard junction box in the false ceiling to bypass space constraints behind the 12-gang wall switchboard.
- **AC & Media Control:** **Broadlink RM4 Mini** IR Blaster (placed on desk divider with clear line-of-sight to Cassette AC and Wall TV).

---

## **3. Physical Wiring & Circuit Mapping**

The system maps AI detection zones directly to the existing physical switchboard (`S1`–`S12`). The AZIOT relay channels are wired in parallel with manual wall switches so physical manual overrides remain fully operational.

### AZIOT 4 Node Smart Switch (Module A) Wiring Table

| Switch ID | Physical Target | Relay Channel | Control Protocol | Spatial Zone |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | Wall TV Display | IR Payload | Broadlink IR | Zone 3 (TV & Lounge) |
| **S7** | TV Area Bulbs `LB1`–`LB3` | Module A — Channel 1 | Local TCP (`tinytuya`) | Zone 3 (TV & Lounge) |
| **S4** | Upper Bulbs `LB4`–`LB6` | Module A — Channel 2 | Local TCP (`tinytuya`) | Zone 1 (Upper Desks) |
| **S2** | Lower Bulbs `LB7`–`LB9` | Module A — Channel 3 | Local TCP (`tinytuya`) | Zone 2 (Lower Desks) |
| **S12** | Far Bulbs `LB10`–`LB12` | Module A — Channel 4 | Local TCP (`tinytuya`) | Zone 3 (Far Area) |
| **S3** | Upper LED Panels `LP1`–`LP2` | Virtual Channel | Software Mock | Zone 1 & Zone 2 |
| **S10** | Lower LED Panels `LP3`–`LP4` | Virtual Channel | Software Mock | Zone 2 & Zone 3 |

---

## **4. Environment & Dependencies Setup**

Run all commands within an isolated Python virtual environment (Python 3.10+ required):

```bash
# Create and activate virtual environment
python3 -m venv iris_env
source iris_env/bin/activate

# Install required IoT, CV, FastAPI, and AI packages
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install tinytuya broadlink opencv-python ultralytics fastapi uvicorn pydantic
```

---

## **5. IoT Hardware Interfacing Layer**

### **5.1 Lighting Control (`tinytuya`)**

AZIOT devices run Tuya firmware. Direct local TCP connection (port 6668) bypasses Tuya cloud servers for sub-100ms latency:

```python
import tinytuya

# Connect locally to AZIOT 4 Node Smart Switch
relay_a = tinytuya.OutletDevice(
    dev_id='YOUR_DEVICE_ID',
    address='192.168.30.125', # Static IP on local network
    local_key='YOUR_LOCAL_KEY',
    version=3.3
)

# Control individual nodes (1-indexed)
relay_a.set_status(True, switch=1)   # Turn ON Switch S7 (TV Area Bulbs)
relay_a.set_status(False, switch=3)  # Turn OFF Switch S2 (Lower Bulbs)
```

### **5.2 AC & TV Control (`broadlink`)**

The RM4 Mini broadcasts Infrared (IR) pulses learned from physical remotes:

```python
import broadlink

devices = broadlink.discover(timeout=5)
rm4 = devices[0]
rm4.auth()

# Send command to AC
AC_COOL_24 = bytes.fromhex("2600500000012...")
rm4.send_data(AC_COOL_24)
```

---

## **6. Computer Vision Layer**

### **6.1 Fast Motion Engine (OpenCV at 5 FPS)**

Evaluates frame-by-frame pixel differences across spatial bounding boxes (`SPATIAL_ZONES`) for instant visual telemetry feedback:

```python
import cv2

diff = cv2.absdiff(frame1, frame2)
gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (5, 5), 0)
_, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
dilated = cv2.dilate(thresh, None, iterations=3)
contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
```

### **6.2 Real-Time Occupancy Engine (YOLOv8 at 1-Second Interval)**

Executes lightweight object detection (`models/best.pt` or `yolov8n.pt`) at 1-second intervals to calculate total headcount:

```python
from ultralytics import YOLO

model = YOLO('models/best.pt')

def get_occupancy_count(frame):
    results = model(frame, verbose=False)
    count = 0
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:  # Class ID 0 = 'person'
                count += 1
    return count
```

---

## **7. Non-Blocking Async Orchestration Engine**

The orchestrator executes a non-blocking step loop at 5 FPS (`200ms` cycle). CPU core allocation is capped at 50% system capacity to guarantee smooth multitasking.

### **7.1 Headcount Lighting & Climate Rules (AUTO Mode)**

- **Headcount > 3 (High Occupancy)**:
  - Turn **ON** ALL Light Bulbs (`S7`, `S4`, `S2`, `S12`).
  - Set AC to **22°C Cool High**.
- **Headcount 1–3 (Standard Occupancy)**:
  - Turn **ON** Upper & Far Bulbs (`S4`, `S12`).
  - Hold extra bulbs (`S7`, `S2`) for a **3-second anti-flicker delay** before turning OFF.
  - Set AC to **24°C Cool Auto**.
- **Headcount == 0 (Zero Occupancy / Vacancy)**:
  - **Light Bulbs (LB)**: Auto-OFF after **3 seconds**.
  - **LED Panels (LP)**: Auto-OFF after **5 seconds**.
  - **Air Conditioner (AC) & TV**: Auto-OFF after **10 minutes (600 seconds)**.

---

## **8. Frontend Dashboard Requirements**

The React 18 dashboard (`frontend/`) presents live telemetry over WebSockets (`/ws/telemetry`):

1. **2D Spatial Floorplan**: Interactive top-view visualization rendering active lights, active zones, and headcount.
2. **System Telemetry Panel**: Live Headcount, AC Setpoint/Fan Speed, Active Power (kW), Cumulative kWh Saved, and Financial Cost Saved ($USD).
3. **Switchboard Override Matrix**: Manual toggles for physical switches `S1`–`S12`.
4. **Preset Selector**:
   - **AUTO**: Full AI vision control.
   - **PRESENTATION**: Dims ambient lighting, turns ON TV, sets AC to quiet mode (24°C Low Fan).
   - **POWER_SAVING**: Forces all lights, AC, and TV OFF.
   - **MANUAL**: Bypasses AI vision overrides for direct testing.

---

## **9. Edge Case & Failure Handling**

- **Network Disconnection / Recovery**: Auto-reconnects to Tuya local sockets. Re-starting 3-strike vacancy timers upon hardware reconnection to prevent accidental blackout.
- **Hardware Mock Mode**: Automatically falls back to mock hardware driver when physical relays are disconnected or `HARDWARE_MOCK_MODE=true`.
- **RTSP Stream Pause / Resume**: Suspends background YOLO CPU calculations when streaming is paused, conserving server resources.