# Project Iris - Operations & Deployment Guide

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`

---

This guide details the hardware deployment, network configuration, environment parameters, production installation, and Linux autostart service setup for **Project Iris**.

---

## 1. Network Topology & Hardware Requirements

### Network Architecture
To ensure low latency (<100ms) and reliable IoT control, all Project Iris components must reside on the same **2.4GHz Wi-Fi network subnet** (e.g., `192.168.30.0/24` or `192.168.1.0/24`).

```
                              +--------------------------+
                              |   Local Wi-Fi Router     |
                              |  (Subnet 192.168.30.x)   |
                              +------------+-------------+
                                           |
           +-------------------------------+-------------------------------+
           |                               |                               |
           v                               v                               v
+----------------------+        +----------------------+        +----------------------+
|  Edge Compute Server |        | AZIOT 4 Node Switch  |        | Broadlink RM4 Mini   |
| (192.168.30.126)     |        | (192.168.30.125)     |        | (192.168.30.60)      |
+----------------------+        +----------------------+        +----------------------+
```

### Static IP Reservation
Assign static IP leases on your Wi-Fi router for:
1. **Edge Compute Workstation**: Running Project Iris backend & frontend.
2. **AZIOT 4 Node Smart Switch**: Relay Module controlling switches `S7`, `S4`, `S2`, `S12`.
3. **Broadlink RM4 Mini**: IR Blaster controlling AC & TV.
4. **CCTV Camera**: RTSP camera stream endpoint.

---

## 2. Hardware Interfacing & Keys Extraction

### 2.1 Extracting Tuya Local Keys for AZIOT Switch
1. Register a free Tuya Developer account at [iot.tuya.com](https://iot.tuya.com).
2. Pair the AZIOT Smart Switch with the **Smart Life** mobile app.
3. Link your Smart Life account under Tuya Developer Portal $\rightarrow$ Cloud $\rightarrow$ Development $\rightarrow$ Link Tuya App Account.
4. Run the `tinytuya` setup wizard on your compute machine:
   ```bash
   python3 -m tinytuya wizard
   ```
5. Enter your Tuya API Key, Secret, and Region (`in` or `us`).
6. The wizard will scan local Wi-Fi and output `devices.json` containing the **Device ID**, **IP Address**, and **Local Key**.

### 2.2 Broadlink RM4 Mini Setup & Learning Mode
1. Connect Broadlink RM4 Mini using the Broadlink / IHC mobile app to connect to local 2.4GHz Wi-Fi.
2. **Crucial Step**: In the Broadlink app device settings, **disable "Lock Device"** so local network SDK pings are accepted.
3. To learn remote IR codes, execute the learning script or use Broadlink python library:
   ```python
   import broadlink
   device = broadlink.discover(timeout=5)[0]
   device.auth()
   device.enter_learning()
   # Press button on physical AC remote...
   ir_hex = device.check_data()
   print("Learned Hex:", ir_hex.hex())
   ```

---

## 3. Environment Variable Configuration (`.env`)

Create or edit `backend/.env`:

```env
# RTSP & Video Feed Configuration
IRIS_RTSP_URL=rtsp://admin:password@192.168.30.100:554/stream1
IRIS_VIDEO_PATH=data/office/VIDEO-2026-07-28-15-36-24.mp4
IRIS_SIMULATED=true
IRIS_YOLO_MODEL=models/best.pt

# Hardware Operation Mode
# Set to 'false' for live physical Wi-Fi hardware, 'true' for local testing
IRIS_HARDWARE_MOCK=false

# AZIOT 4 Node Smart Switch Credentials (Module A)
RELAY_A_ID=bf1b6580f4f9f4a567xxxx
RELAY_A_IP=192.168.30.125
RELAY_A_KEY=30467c6999xxxxxx
RELAY_A_VERSION=3.3

# Broadlink RM4 Mini Credentials
BROADLINK_IP=192.168.30.60
BROADLINK_MAC=A4:91:B1:00:00:00

# Tuya Developer Cloud Credentials
TUYA_API_KEY=your_tuya_api_key
TUYA_API_SECRET=your_tuya_api_secret
TUYA_PROJECT_CODE=your_project_code
TUYA_API_REGION=in
```

---

## 4. Production Deployment & Autostart Setup

### 4.1 Production Build
Build the optimized React single-page frontend static asset bundle:

```bash
cd frontend
npm run build
cd ..
```
*FastAPI automatically detects and serves static assets from `frontend/dist` on port `8008`.*

### 4.2 Systemd Linux Autostart Service Setup

To ensure Project Iris starts automatically on system boot, create a systemd service file:

1. Create `/etc/systemd/system/iris.service`:
   ```ini
   [Unit]
   Description=Project Iris Commercial Office Automation Engine
   After=network.target

   [Service]
   Type=simple
   User=stark
   WorkingDirectory=/home/stark/JetBrainsProjects/Iris
   ExecStart=/home/stark/JetBrainsProjects/Iris/start.sh
   ExecStop=/home/stark/JetBrainsProjects/Iris/stop.sh
   Restart=always
   RestartSec=5
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable iris.service
   sudo systemctl start iris.service
   ```

3. Verify service status:
   ```bash
   sudo systemctl status iris.service
   ```

---

## 5. Troubleshooting & Maintenance

### 5.1 Tuya Relay Connection Failure (`901` Connection Error)
- **Symptom**: `tinytuya` returns socket connection error.
- **Root Cause**: Tuya hardware allows only **1 active local TCP connection** at a time.
- **Resolution**: Close the Smart Life / Tuya Smart mobile app on all phones connected to the network.

### 5.2 Broadlink Discovery Timeout
- **Symptom**: `broadlink.discover()` fails to locate RM4 Mini.
- **Root Cause**: Device is locked or compute server is on a different VLAN/subnet.
- **Resolution**: Ensure compute machine and Broadlink RM4 Mini share the exact same IP subnet (`192.168.30.x`) and "Lock Device" is disabled in the app.

### 5.3 RTSP Stream Latency / Lag
- **Symptom**: Video preview lags behind real-time events.
- **Resolution**: OpenCV buffer size is forced to 1 frame in `orchestrator.py` (`cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)`). Ensure network bandwidth is sufficient for 1080p RTSP stream.
