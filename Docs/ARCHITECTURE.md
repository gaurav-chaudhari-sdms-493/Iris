# Project Iris - System Architecture & Technical Design Document

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`

---

## 1. Architectural Overview

**Project Iris** is structured as an event-driven, micro-orchestrated edge system. It bridges real-time computer vision analysis with local physical IoT hardware relays and interactive WebSockets telemetry dashboards.

```
+-----------------------------------------------------------------------------------+
|                                  VISION SOURCE                                    |
|             Ceiling CCTV RTSP Stream / Local MP4 Demo / Synthetic Feed            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              COMPUTER VISION LAYER                                |
|  +-------------------------------------+  +------------------------------------+  |
|  |     Fast Spatial Motion Engine      |  |     YOLOv8 Occupancy Engine       |  |
|  |  (OpenCV 5 FPS Pixel-Difference)    |  |   (PyTorch 1-Second Headcount)     |  |
|  +------------------+------------------+  +-----------------+------------------+  |
+---------------------|---------------------------------------|---------------------+
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           FASTAPI ASYNC ORCHESTRATOR                              |
|  - Non-Blocking 5 FPS Execution Step Loop (200ms)                                 |
|  - Headcount Rule Engine & Dynamic AC Setpoint Logic                              |
|  - Device-Specific Auto-Off Vacancy Timers (LB: 3s | LP: 5s | AC/TV: 600s)         |
|  - Anti-Flicker Hysteresis Manager (3-Second Hold Window)                         |
|  - Energy Savings & kWh Financial Calculator                                      |
+--------------------+------------------------------------+-------------------------+
                     |                                    |
                     v                                    v
+----------------------------------+    +-------------------------------------------+
|          HARDWARE LAYER          |    |              PRESENTATION LAYER           |
| - Tuya Local TCP (`tinytuya`)    |    | - React 18 / Vite 5 Dashboard             |
|   AZIOT 4 Node Smart Switch      |    | - Real-time WebSockets Telemetry Stream   |
| - Broadlink RM4 IR Blaster       |    | - MJPEG Stream Overlay Generator          |
|   Cassette AC & Wall TV Display  |    | - Interactive 2D Spatial Floorplan Map    |
+----------------------------------+    +-------------------------------------------+
```

---

## 2. Component Breakdown

### 2.1 Computer Vision Layer (`backend/vision/`)
- **`FastMotionEngine`** (`motion_engine.py`):
  Runs at 5 FPS to compute frame-by-frame absolute Gaussian differences (`cv2.absdiff`). Calculates spatial motion intensity percentage across defined bounding boxes (`SPATIAL_ZONES`).
- **`OccupancyEngine`** (`occupancy_engine.py`):
  Executes lightweight YOLOv8 neural network inference (`models/best.pt`) on 1-second intervals. Filters bounding boxes by Class ID 0 (`person`) to establish exact headcount.
- **`SyntheticStreamGenerator`** (`stream_gen.py`):
  Provides zero-dependency video streaming fallback, supporting MP4 video playback controls (play, pause, seek, step, speed) or dynamic synthetic frame generation when camera feeds are offline.

### 2.2 Async Orchestrator (`backend/orchestrator.py`)
Acts as the central system coordinator executing at 5 FPS:
- **CPU Allocation Manager**: Caps PyTorch and OpenCV CPU usage to max 50% system threads (`torch.set_num_threads`).
- **State Evaluator**: Computes active power consumption, kWh saved, cost saved ($USD), and spatial zone statuses.
- **Vacancy Controller**: Evaluates vacancy timers and manages automated device shut-offs.

### 2.3 Hardware Integration Layer (`backend/hardware/`)
- **`TuyaRelayManager`** (`tuya_manager.py`):
  Manages direct local TCP socket connections to the AZIOT 4 Node Smart Switch via `tinytuya`. Features automatic socket reconnect, retry logic, and seamless mock fallback (`HARDWARE_MOCK_MODE=true`).
- **`BroadlinkIRManager`** (`broadlink_manager.py`):
  Discovers and communicates with Broadlink RM4 Mini IR blasters. Broadcasts learned IR pulse hex arrays to toggle Wall TV power and set AC temperature/fan modes.

### 2.4 Presentation & API Layer (`backend/server.py` & `frontend/`)
- **FastAPI Engine**: Serves REST management routes (`/api/override`, `/api/mode`, `/api/ac`, `/api/hardware/*`) and live MJPEG video stream (`/video_feed`).
- **WebSocket Telemetry Broadcaster** (`/ws/telemetry`): Streams JSON state payloads to connected React frontend clients every 200ms.
- **React Dashboard**: Renders interactive 2D spatial floorplan, live metric charts, switchboard toggles, and video preview.

---

## 3. Finite State Machine (FSM) Specifications

### 3.1 System Operating Modes FSM

```
                +-------------------------------------------------------+
                |                                                       |
                v                                                       |
         +--------------+   Select Preset    +-------------------+      |
         |  AUTO MODE   | -----------------> | PRESENTATION MODE |      |
         | (AI Control) |                    | (TV ON, AC 24°C)  |      |
         +------+-------+                    +---------+---------+      |
                |                                      |                |
 Switch Override|                                      |                |
 or API Command |                                      |                |
                v                                      v                |
         +--------------+                    +-------------------+      | Reset Preset
         | MANUAL MODE  | <----------------- | POWER SAVING MODE | -----+
         | (AI Bypassed)|                    | (All Devices OFF) |
         +--------------+                    +-------------------+
```

### 3.2 Vacancy Auto-Off Countdown FSM (AUTO Mode)

```
        Headcount > 0
      +---------------+
      |               |
      v               |
+------------+   Headcount == 0   +------------------+
| OCCUPIED   | -----------------> | VACANCY DETECTED |
|  STATE     |                    +--------+---------+
+------------+                             |
                                           | t >= 3s
                                           v
                                  +------------------+
                                  | Light Bulbs OFF  |  (Nodes 1, 2, 3, 4)
                                  +--------+---------+
                                           |
                                           | t >= 5s
                                           v
                                  +------------------+
                                  | LED Panels OFF   |
                                  +--------+---------+
                                           |
                                           | t >= 600s (10 min)
                                           v
                                  +------------------+
                                  | AC & TV OFF      |
                                  +------------------+
```

---

## 4. Anti-Flicker Hysteresis Window

To eliminate rapid light cycling when occupants move briefly out of camera range or when headcount fluctuates between 4 and 3 people:
1. When headcount transitions from $>3$ to $1\text{--}3$, the system immediately lowers AC setpoint to 24°C Cool Auto.
2. Extra lighting rows (`S7` and `S2`) are held **ON** in memory for a **3.0-second anti-flicker delay window**.
3. If headcount remains $1\text{--}3$ for the full 3 seconds, `S7` and `S2` are turned OFF. If headcount rises back above 3 within 3 seconds, the timer resets without cycling relays.

---

## 5. Telemetry Data Flow Sequence

```
[ CCTV Stream ] ---> OpenCV Motion Engine (5 FPS) -------> [ Telemetry Step ]
[ Video Frame ] ---> YOLOv8 Headcount Engine (1 Sec) ----> [ Telemetry Step ]
                                                                   |
                                                                   v
                                                        FastAPI WebSocket Broadcast
                                                                   |
                                          +------------------------+------------------------+
                                          |                                                 |
                                          v                                                 v
                              React 2D Spatial Dashboard                       AZIOT Local TCP Relays
                              (Websockets Client 200ms)                        Broadlink IR Blaster
```
