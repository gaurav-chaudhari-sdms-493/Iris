# Project Iris 👁️⚡

> **Commercial Office Automation & AI Vision Telemetry Dashboard**  
> *Real-time occupancy tracking, 2D spatial floorplan mapping, physical 12-gang switchboard control, and smart HVAC energy optimization powered by YOLOv8, FastAPI, and React.*

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Operational / Production Ready`
- **Classification**: `STARK AI Internal & Proprietary`

---

## 🌟 Overview

**Project Iris** is an intelligent, high-efficiency commercial office automation system designed exclusively for STARK AI commercial office spaces. It combines real-time computer vision occupancy tracking with automated physical relay switching and IR climate control.

By replacing traditional static motion sensors with real-time **YOLOv8 person detection** and **OpenCV fast spatial motion analysis**, Project Iris achieves precision energy management:
- **Instant Re-Energize**: Automatically turns ON spatial lights and AC when occupants enter the office.
- **Fine-Grained Vacancy Timers**: Automatically powers down Light Bulbs (3s), LED Panels (5s), and AC/TV (10 mins) when zero occupants are detected.
- **Dynamic Climate Adaptation**: Adjusts AC target temperature to **22°C Cool High** during high occupancy ($\ge 4$ occupants) and maintains **24°C Cool Auto** during standard occupancy ($1\text{--}3$ occupants).
- **Anti-Flicker Hysteresis**: Holds auxiliary bulbs for 3 seconds during headcount transitions to prevent light flashing.

---

## 📚 Repository Documentation Index

| Document | Description |
| :--- | :--- |
| 📖 [Functional Spec Document](file:///home/stark/JetBrainsProjects/Iris/Docs/Project%20Iris.md) | Detailed FSD covering hardware architecture, vision engine, and orchestration rules |
| 🏗️ [System Architecture](file:///home/stark/JetBrainsProjects/Iris/ARCHITECTURE.md) | Component architecture, data flow diagrams, and state machine specifications |
| 🔌 [API & WebSockets Reference](file:///home/stark/JetBrainsProjects/Iris/Docs/API_REFERENCE.md) | Complete REST API endpoints and real-time WebSocket telemetry protocol |
| ⚡ [AZIOT Relay Commands](file:///home/stark/JetBrainsProjects/Iris/Docs/AZIOT_RELAY_COMMANDS.md) | Direct `curl` command reference for testing physical switch channels |
| 🚀 [Deployment & Ops Guide](file:///home/stark/JetBrainsProjects/Iris/DEPLOYMENT.md) | Hardware key extraction, Wi-Fi setup, environment configuration, systemd autostart |
| 🧪 [Testing & Verification Guide](file:///home/stark/JetBrainsProjects/Iris/TESTING.md) | Hardware mock testing, API test suites, and CPU allocation benchmarks |
| 🛡️ [Security Policy](file:///home/stark/JetBrainsProjects/Iris/SECURITY.md) | Internal vulnerability disclosure, IoT network isolation, secrets protection |
| 🤝 [Internal Developer Guide](file:///home/stark/JetBrainsProjects/Iris/CONTRIBUTING.md) | Internal engineering guidelines, code style (PEP 8, Prettier), branch workflow |
| 📜 [Changelog](file:///home/stark/JetBrainsProjects/Iris/CHANGELOG.md) | Full version release history and technical change tracking |

---

## 🚀 Key Features

- 🎯 **1-Second Real-Time YOLOv8 Detection**: High-speed occupant headcount tracking and spatial zone assignment using lightweight PyTorch YOLOv8 (`models/best.pt`).
- 🗺️ **Interactive 2D Spatial Floorplan**: Custom top-view room visualization rendering active ceiling panel lights (LP1–LP4), track spotlight rails (LB1–LB12), AC cassette unit, TV display, and 12-gang physical switchboard state.
- ⚡ **AZIOT 4 Node Smart Switch Integration**: Direct local TCP control of physical relay channels mapped to switchboard buttons (S7, S4, S2, S12).
- ❄️ **Smart HVAC & TV IR Automation**: Broadlink RM4 Mini IR blaster adjusting climate output according to real-time headcount.
- 📊 **Live Energy Metrics**: Real-time tracking of active load (kW), cumulative energy saved (kWh), and financial cost savings ($USD).
- 🎬 **Custom MP4 & Live RTSP Feed**: Continuous looping demo feed generator (`backend/video.mp4` or synthetic frames) and live RTSP camera connection.

---

## 🏗️ System Architecture

```
                       ┌────────────────────────────────┐
                       │  CCTV Camera Feed / video.mp4  │
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │  Fast Motion & YOLO Engine     │
                       │    (Headcount & Spatial BBoxes)│
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │  FastAPI Orchestration Engine  │
                       │    (5 FPS Telemetry Stream)    │
                       └───────┬────────────────────────┘
                               │                │
             WebSocket / MJPEG │                │ Local TCP / IR Commands
                               ▼                ▼
           ┌──────────────────────┐   ┌──────────────────────────┐
           │ React 18 + Tailwind  │   │  AZIOT 4 Node Switch     │
           │ Dashboard (Vite 5)   │   │  Broadlink IR (AC & TV)  │
           └──────────────────────┘   └──────────────────────────┘
```

---

## 🔌 Hardware & Switch Mapping

### Switchboard & AZIOT Channel Mapping

| Physical Switch | Load Description | Module & Channel | Hardware Type | Default Spatial Zone |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | Wall TV Display | Broadlink IR Blaster | IR Command | Zone 3 (TV & Lounge) |
| **S7** | TV Area Bulbs `LB1`–`LB3` | AZIOT Module A — Ch 1 | Physical Relay | Zone 3 (TV & Lounge) |
| **S4** | Upper Bulbs `LB4`–`LB6` | AZIOT Module A — Ch 2 | Physical Relay | Zone 1 (Upper Desks) |
| **S2** | Lower Bulbs `LB7`–`LB9` | AZIOT Module A — Ch 3 | Physical Relay | Zone 2 (Lower Desks) |
| **S12** | Far Bulbs `LB10`–`LB12` | AZIOT Module A — Ch 4 | Physical Relay | Zone 3 (Far Area) |
| **S3** | Upper LED Panels `LP1`–`LP2` | Virtual Software Switch | Software Mock | Zone 1 & Zone 2 |
| **S10** | Lower LED Panels `LP3`–`LP4` | Virtual Software Switch | Software Mock | Zone 2 & Zone 3 |
| **AC Unit** | Ceiling Cassette AC | Broadlink IR Blaster | IR Command | Central HVAC |

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python**: 3.10+
- **Node.js**: v18+ (with `npm`)
- **FFmpeg & OpenCV Dependencies**: Required for video decoding

### Quickstart

1. **Clone Internal Repository**:
   ```bash
   git clone git@github.com:stark-ai/Project-Iris.git
   cd Project-Iris
   ```

2. **Start All Services**:
   ```bash
   ./start.sh
   ```
   *This automatically sets up Python virtual environments, installs frontend node modules, builds frontend assets, and starts the FastAPI server on `http://localhost:8008` (and Vite frontend on `http://localhost:5173`).*

3. **Stop All Services**:
   ```bash
   ./stop.sh
   ```

---

## 💻 Tech Stack

- **Frontend**: React 18, Vite 5, Tailwind CSS v4, Lucide Icons, Recharts, WebSockets
- **Backend**: Python 3, FastAPI, Uvicorn, AsyncIO, PyTorch, OpenCV
- **AI & Vision**: YOLOv8 (`models/best.pt`), Custom OpenCV Motion Engine
- **Hardware Protocol**: `tinytuya` (Local TCP for AZIOT Switches), `broadlink` (IR Blaster)

---

## 📄 Licensing & Intellectual Property

**STARK AI Proprietary & Confidential**. All rights reserved. See `LICENSE` for formal notice.
