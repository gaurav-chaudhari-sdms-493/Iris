# AZIOT 4 Node Smart Switch - API & Curl Reference

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Operational / Production Ready`

---

This guide provides direct `curl` shell commands for controlling the physical **AZIOT 4 Node Smart Switch** (Light Bulbs LB1–LB12 across 4 channels) and related IoT appliances via the Project Iris API.

---

## 📌 Base URL
- **Local Workstation**: `http://localhost:8008`
- **LAN Interface**: `http://192.168.30.126:8008`

---

## 🛠️ Recommended Setup (Manual Mode)

To prevent the computer vision AI occupancy engine from overriding your manual tests, set the system mode to **MANUAL** first:

```bash
curl -X POST http://localhost:8008/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "MANUAL"}'
```

---

## 💡 Individual Light Control Commands (Switch Overrides)

### 1. TV Area Bulbs (Node 1 / Switch `S7`)
- **Turn ON**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S7", "state": true}'
  ```
- **Turn OFF**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S7", "state": false}'
  ```

---

### 2. Upper Bulbs (Node 2 / Switch `S4`)
- **Turn ON**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S4", "state": true}'
  ```
- **Turn OFF**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S4", "state": false}'
  ```

---

### 3. Lower Bulbs (Node 3 / Switch `S2`)
- **Turn ON**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S2", "state": true}'
  ```
- **Turn OFF**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S2", "state": false}'
  ```

---

### 4. Far Bulbs (Node 4 / Switch `S12`)
- **Turn ON**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S12", "state": true}'
  ```
- **Turn OFF**:
  ```bash
  curl -X POST http://localhost:8008/api/override \
    -H "Content-Type: application/json" \
    -d '{"switch_id": "S12", "state": false}'
  ```

---

## ⚡ 1-Second Pulse Test Commands (ON -> 1s -> OFF)

Pulse test individual relay channels on the physical AZIOT switch:

- **Pulse Node 1 (TV Area Bulbs - S7)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 1}'
  ```

- **Pulse Node 2 (Upper Bulbs - S4)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 2}'
  ```

- **Pulse Node 3 (Lower Bulbs - S2)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 3}'
  ```

- **Pulse Node 4 (Far Bulbs - S12)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 4}'
  ```

---

## ❄️ Manual Air Conditioner (AC) Control

Adjust climate settings manually:

```bash
curl -X POST http://localhost:8008/api/ac \
  -H "Content-Type: application/json" \
  -d '{"temperature": 22, "power": "ON", "mode": "COOL", "fan_speed": "HIGH"}'
```

---

## ⚙️ Hardware Connection & Mock Mode Settings

### Toggle Hardware Mock Mode vs Real Wi-Fi Control
```bash
# Enable Mock Mode
curl -X POST http://localhost:8008/api/hardware/mode \
  -H "Content-Type: application/json" \
  -d '{"mock_mode": true}'

# Disable Mock Mode (Enable Real Physical Wi-Fi Relays)
curl -X POST http://localhost:8008/api/hardware/mode \
  -H "Content-Type: application/json" \
  -d '{"mock_mode": false}'
```

### Update AZIOT Relay Connection Credentials
```bash
curl -X POST http://localhost:8008/api/hardware/config \
  -H "Content-Type: application/json" \
  -d '{
    "address": "192.168.30.125",
    "dev_id": "bf1b6580f4f9f4a567xxxx",
    "local_key": "30467c6999xxxxxx",
    "version": 3.3
  }'
```

---

## 🎬 Video Stream Player Control Commands

Control playback state of the synthetic / MP4 feed:

- **Play**: `curl -X POST http://localhost:8008/api/player/control -H "Content-Type: application/json" -d '{"action": "play"}'`
- **Pause**: `curl -X POST http://localhost:8008/api/player/control -H "Content-Type: application/json" -d '{"action": "pause"}'`
- **Seek to timestamp**: `curl -X POST http://localhost:8008/api/player/control -H "Content-Type: application/json" -d '{"action": "seek", "value": 15.0}'`

---

## 📊 Hardware & Telemetry Status Checks

### Query Physical Relay Details
```bash
curl -X GET http://localhost:8008/api/hardware/status
```

### Query Instant Telemetry Snapshot
```bash
curl -X GET http://localhost:8008/api/telemetry
```
