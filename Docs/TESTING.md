# Project Iris - Testing & Verification Guide

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`

---

This guide outlines the testing strategy, mock hardware test procedures, API suite execution, and performance verification for **Project Iris**.

---

## 1. Testing Strategy Overview

Project Iris includes multiple layers of verification:

```
+-------------------------------------------------------------------------+
|                              TEST SUITES                                |
|  +--------------------------+  +-------------------------------------+  |
|  |   Hardware Mock Testing  |  |     FastAPI REST & WS API Testing   |  |
|  |  (Simulated Relays & IR) |  |   (Endpoints & WebSockets Telemetry)|  |
|  +--------------------------+  +-------------------------------------+  |
|  +--------------------------+  +-------------------------------------+  |
|  |  CV & YOLO Simulation    |  |     CPU & Thread Allocation Check   |  |
|  | (Synthetic Video Frames) |  |   (Max 50% CPU Budget Enforcement)  |  |
|  +--------------------------+  +-------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 2. Hardware Mock Mode Testing

When developing without physical AZIOT relays connected:

1. Enable Mock Mode in `backend/.env`:
   ```env
   IRIS_HARDWARE_MOCK=true
   ```

2. Or send POST request to FastAPI:
   ```bash
   curl -X POST http://localhost:8008/api/hardware/mode \
     -H "Content-Type: application/json" \
     -d '{"mock_mode": true}'
   ```

3. Verify status:
   ```bash
   curl -X GET http://localhost:8008/api/hardware/status
   ```
   *Expected Output*: `"mock_mode": true`, channel states toggle cleanly without network socket errors.

---

## 3. Automated API Endpoint Tests

### 3.1 REST API Endpoint Verification

You can execute Python syntax and module integrity checks:

```bash
cd backend
source iris_env/bin/activate
python3 -m py_compile server.py orchestrator.py config.py hardware/tuya_manager.py hardware/broadlink_manager.py
```

### 3.2 Automated Test Script (`pytest`)

To run automated integration tests:

```bash
cd backend
source iris_env/bin/activate
pytest tests/ -v
```

---

## 4. Manual Verification Workflows

### 4.1 System Mode Transition Testing

1. **Set to MANUAL Mode**:
   ```bash
   curl -X POST http://localhost:8008/api/mode -H "Content-Type: application/json" -d '{"mode": "MANUAL"}'
   ```
2. **Override Switch S7 (TV Area Bulbs)**:
   ```bash
   curl -X POST http://localhost:8008/api/override -H "Content-Type: application/json" -d '{"switch_id": "S7", "state": true}'
   ```
3. **Pulse Test Channel 1**:
   ```bash
   curl -X POST http://localhost:8008/api/hardware/test -H "Content-Type: application/json" -d '{"channel": 1}'
   ```
4. **Set to PRESENTATION Mode**:
   ```bash
   curl -X POST http://localhost:8008/api/mode -H "Content-Type: application/json" -d '{"mode": "PRESENTATION"}'
   ```
   *Verify telemetry returns TV power ON, AC set to 24°C LOW fan, and ambient panels OFF.*

---

## 5. Vision Engine & Headcount Simulation

To simulate headcount changes without a physical camera:

1. Use WebSocket client or curl to simulate headcount:
   ```bash
   # Connect to WebSocket ws://localhost:8008/ws/telemetry and send:
   {"action": "headcount_simulate", "count": 4}
   ```
2. Verify automated lighting response:
   - When headcount $>3$: All light bulbs (`S7`, `S4`, `S2`, `S12`) turn **ON**, AC sets to **22°C Cool High**.
   - When headcount drops to 0: Bulbs turn OFF after **3 seconds**, LED panels after **5 seconds**, AC after **10 minutes**.

---

## 6. CPU & Performance Benchmarking

### CPU Core Cap Verification
Project Iris automatically caps CPU thread consumption to 50% of available cores:

```bash
# Check server startup log output:
[CPU Power Management] Process allocated 4 threads out of 8 system cores (50% CPU limit).
```

### Video Stream Performance Benchmark
- Frame Rate Target: **5 FPS** (`200ms` cycle time)
- Telemetry Latency: **< 10ms**
- CPU Overhead: **< 15%** under standard PyTorch YOLOv8 execution.
