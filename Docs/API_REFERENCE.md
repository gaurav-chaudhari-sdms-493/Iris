# Project Iris - REST API & WebSocket Protocol Reference

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`

---

The Project Iris backend provides FastAPI REST endpoints and WebSockets streaming APIs for controlling hardware, monitoring AI telemetry, and driving the React 2D Spatial Dashboard.

---

## 📌 Base URL & Headers
- **Local Workstation**: `http://localhost:8008`
- **LAN Address**: `http://192.168.30.126:8008`
- **Content-Type**: `application/json`

---

## 1. REST API Endpoints

### 1.1 `GET /api/telemetry`
Returns the instant system state and AI telemetry snapshot.

- **Response `200 OK`**:
```json
{
  "timestamp": 1722421500.12,
  "system_mode": "AUTO",
  "headcount": 2,
  "zero_occupancy_strikes": 0,
  "zone_states": {
    "Zone_1_Upper": true,
    "Zone_2_Lower": false,
    "Zone_3_TV_Far": true
  },
  "zone_motion_levels": {
    "Zone_1_Upper": 12.4,
    "Zone_2_Lower": 0.0,
    "Zone_3_TV_Far": 4.1
  },
  "ac_state": {
    "temperature": 24,
    "power": "ON",
    "mode": "COOL",
    "fan_speed": "AUTO"
  },
  "tv_state": {
    "power": "ON"
  },
  "relays": {
    "Relay_A": { "1": false, "2": true, "3": false, "4": true },
    "Relay_B": { "1": false, "2": false, "3": false, "4": false }
  },
  "player_state": {
    "playing": true,
    "current_time": 14.2,
    "duration": 60.0,
    "speed": 1.0
  },
  "energy_metrics": {
    "active_kw": 1.8,
    "kwh_saved_today": 0.42,
    "cost_saved_usd": 0.06
  },
  "motion_boxes": [[120, 80, 45, 50]],
  "person_boxes": [
    { "bbox": [100, 70, 50, 110], "confidence": 0.92 }
  ]
}
```

---

### 1.2 `GET /api/switches`
Returns physical switch mapping catalog and relay status.

- **Response `200 OK`**:
```json
{
  "switches": {
    "S1": { "name": "TV Power Switch", "type": "IR", "device": "Broadlink", "target": "TV" },
    "S7": { "name": "TV Area Bulbs LB1-LB3", "type": "Relay", "module": "A", "channel": 1 },
    "S4": { "name": "Upper Bulbs LB4-LB6", "type": "Relay", "module": "A", "channel": 2 },
    "S2": { "name": "Lower Bulbs LB7-LB9", "type": "Relay", "module": "A", "channel": 3 },
    "S12": { "name": "Far Bulbs LB10-LB12", "type": "Relay", "module": "A", "channel": 4 }
  },
  "relays": {
    "Relay_A": { "1": false, "2": true, "3": false, "4": true }
  }
}
```

---

### 1.3 `POST /api/override`
Executes manual switch control. Automatically sets system mode to `MANUAL`.

- **Request Body**:
```json
{
  "switch_id": "S7",
  "state": true
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "switch": "S7",
  "state": true
}
```

---

### 1.4 `POST /api/mode`
Sets overall system mode (`AUTO`, `PRESENTATION`, `POWER_SAVING`, `MANUAL`).

- **Request Body**:
```json
{
  "mode": "PRESENTATION"
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "mode": "PRESENTATION",
  "telemetry": { ... }
}
```

---

### 1.5 `POST /api/ac`
Manual Broadlink IR Air Conditioner control.

- **Request Body**:
```json
{
  "temperature": 22,
  "power": "ON",
  "mode": "COOL",
  "fan_speed": "HIGH"
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "ac_state": {
    "temperature": 22,
    "power": "ON",
    "mode": "COOL",
    "fan_speed": "HIGH"
  }
}
```

---

### 1.6 `POST /api/player/control`
Controls synthetic / MP4 video stream playback.

- **Request Body**:
```json
{
  "action": "play|pause|toggle|seek|set_speed|live",
  "value": 15.0
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "player_state": {
    "playing": true,
    "current_time": 15.0
  }
}
```

---

### 1.7 `GET /api/hardware/status`
Returns connection status and latency details for physical AZIOT relay modules.

- **Response `200 OK`**:
```json
{
  "mock_mode": false,
  "relay_a": {
    "dev_id": "bf1b6580f4f9f4a567xxxx",
    "address": "192.168.30.125",
    "version": 3.3,
    "connected": true,
    "channels": { "1": false, "2": true, "3": false, "4": true }
  }
}
```

---

### 1.8 `POST /api/hardware/mode`
Toggles between Hardware Real Wi-Fi Control and Mock Mode.

- **Request Body**:
```json
{
  "mock_mode": true
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "hardware": { ... }
}
```

---

### 1.9 `POST /api/hardware/config`
Updates AZIOT relay local network connection credentials.

- **Request Body**:
```json
{
  "address": "192.168.30.125",
  "dev_id": "bf1b6580f4f9f4a567xxxx",
  "local_key": "30467c6999xxxxxx",
  "version": 3.3
}
```

---

### 1.10 `POST /api/hardware/test`
Pulse tests an individual node channel (1–4) on AZIOT switch (ON $\rightarrow$ 1s $\rightarrow$ OFF).

- **Request Body**:
```json
{
  "channel": 1
}
```
- **Response `200 OK`**:
```json
{
  "status": "success",
  "tested_channel": 1
}
```

---

### 1.11 `GET /video_feed`
MJPEG video stream endpoint with real-time motion & bounding box visual overlays.
- **Content-Type**: `multipart/x-mixed-replace; boundary=frame`

---

## 2. WebSocket Protocol (`/ws/telemetry`)

React frontend connects via WebSocket (`ws://localhost:8008/ws/telemetry`) for real-time bi-directional telemetry streaming.

### 2.1 Outbound Server Telemetry Stream (Broadcast every 200ms)
The server pushes JSON telemetry payloads continuously to all connected clients (see `GET /api/telemetry` schema).

### 2.2 Inbound Client Commands

Clients can send JSON commands over the WebSocket connection:

1. **Switch Override**:
   ```json
   { "action": "override", "switch_id": "S7", "state": true }
   ```
2. **Preset Change**:
   ```json
   { "action": "preset", "preset": "PRESENTATION" }
   ```
3. **Headcount Debug Simulation**:
   ```json
   { "action": "headcount_simulate", "count": 4 }
   ```
4. **Player Control**:
   ```json
   { "action": "player_control", "control_action": "pause" }
   ```
