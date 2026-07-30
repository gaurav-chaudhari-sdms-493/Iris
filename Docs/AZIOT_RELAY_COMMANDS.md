# AZIOT 4 Node Smart Switch - API & Curl Reference

This guide provides `curl` commands for controlling the physical **AZIOT 4 Node Smart Switch** (Light Bulbs LB1–LB12 across 4 channels) via the Project Iris API.

---

## 📌 Base URL
- **Local Server**: `http://localhost:8008`
- **Network Interface**: `http://192.168.30.126:8008`

---

## 🛠️ Recommended Setup (Manual Mode)

To prevent the computer vision AI occupancy engine from auto-overriding your manual tests, set the system mode to **MANUAL** first:

```bash
curl -X POST http://localhost:8008/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "MANUAL"}'
```

---

## 💡 Individual Light Control Commands

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

- **Pulse Node 1 (TV Area Bulbs)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 1}'
  ```

- **Pulse Node 2 (Upper Bulbs)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 2}'
  ```

- **Pulse Node 3 (Lower Bulbs)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 3}'
  ```

- **Pulse Node 4 (Far Bulbs)**:
  ```bash
  curl -X POST http://localhost:8008/api/hardware/test \
    -H "Content-Type: application/json" \
    -d '{"channel": 4}'
  ```

---

## 📊 Hardware Status Check

Query live physical relay states, connection latency, and Wi-Fi mode:

```bash
curl -X GET http://localhost:8008/api/hardware/status
```
