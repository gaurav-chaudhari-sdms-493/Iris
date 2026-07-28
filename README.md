# Project Iris 👁️⚡
> **Commercial Office Automation & AI Vision Telemetry Dashboard**  
> *Real-time occupancy tracking, 2D spatial floorplan mapping, physical 12-gang switchboard control, and smart HVAC energy optimization powered by YOLOv8, FastAPI, and React.*

---

## 🌟 Overview

**Project Iris** is an intelligent, high-efficiency commercial office automation system designed for STARK AI office spaces. It combines computer vision occupancy tracking with automated physical relay switching and IR climate control.

By replacing traditional static motion sensors with real-time **YOLOv8 person detection**, Project Iris achieves precision energy management:
- **Instant Re-Energize**: Automatically turns ON spatial lights and AC when occupants enter the office.
- **Rapid Energy Shutoff**: Automatically powers down all non-essential lights, AC, and TV when zero occupants are detected for 3 consecutive seconds.
- **Dynamic Climate Adaptation**: Lowers AC target temperature to **22°C Cool High** during high occupancy ($\ge 4$ occupants) and maintains **24°C Cool Auto** during standard occupancy.

---

## 🚀 Key Features

- 🎯 **1-Second Real-Time YOLOv8 Detection**: High-speed occupant headcount tracking and spatial zone assignment using lightweight PyTorch YOLOv8.
- 🗺️ **Interactive 2D Spatial Floorplan**: Custom top-view room visualization rendering active ceiling panel lights (LP1–LP4), track spotlight rails (LB1–LB12), AC cassette unit, TV display, and 12-gang physical switchboard state.
- ⚡ **Physical 12-Gang Switchboard Integration**: Direct mapping between physical wall switches (S1–S12), Tuya Relay modules, and Broadlink IR commands.
- ❄️ **Smart HVAC & TV Automation**: Automated Broadlink IR control adjusting climate output according to real-time headcount.
- 📊 **Live Energy Metrics**: Real-time tracking of active load (kW), cumulative energy saved (kWh), and financial cost savings ($USD).
- 🎬 **Custom MP4 Video Feed & RTSP Support**: Auto-detects local MP4 demo videos (`backend/video.mp4`) with continuous seamless looping or connects directly to live RTSP CCTV camera streams.

---

## 🏗️ System Architecture

```
                       ┌────────────────────────────────┐
                       │  CCTV Camera Feed / video.mp4  │
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │  YOLOv8 Computer Vision Engine │
                       │    (Headcount & Spatial BBoxes)│
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │  FastAPI Orchestration Engine  │
                       │    (5 FPS Telemetry Stream)    │
                       └───────┬────────────────┬───────┘
                               │                │
             WebSocket / WS    │                │  Relay / IR Commands
                               ▼                ▼
           ┌──────────────────────┐   ┌──────────────────────────┐
           │ React 18 + Tailwind  │   │  Tuya Relays (Mod A & B) │
           │ Dashboard (Vite 5)   │   │  Broadlink IR (AC & TV)  │
           └──────────────────────┘   └──────────────────────────┘
```

---

## 🔌 Hardware & Wiring Specifications

### Physical 12-Gang Switchboard Schematic (`S1` – `S12`)

| Switch ID | Target Load / Appliance | Controlled By / Relay Channel | Spatial Zone |
| :--- | :--- | :--- | :--- |
| **S1** | Wall TV Display | Broadlink IR Blaster | Zone 3 (TV & Lounge) |
| **S2** | Track Spotlights `LB7`, `LB8`, `LB9` | Tuya Module B — Ch 1 | Zone 2 (Lower Desks) |
| **S3** | LED Panels `LP1`, `LP2` | Tuya Module A — Ch 1 | Zone 1 & Zone 2 |
| **S4** | Track Spotlights `LB4`, `LB5`, `LB6` | Tuya Module A — Ch 4 | Zone 1 (Upper Desks) |
| **S5 – S6** | Spare Auxiliary Lines | Unassigned | Auxiliary |
| **S7** | Track Spotlights `LB1`, `LB2`, `LB3` | Tuya Module A — Ch 3 | Zone 1 (Upper Desks) |
| **S8 – S9** | Spare Auxiliary Lines | Unassigned | Auxiliary |
| **S10** | LED Panels `LP3`, `LP4` | Tuya Module A — Ch 2 | Zone 3 & Zone 2 |
| **S11** | Auxiliary Pass-through | Unassigned | Auxiliary |
| **S12** | Track Spotlights `LB10`, `LB11`, `LB12` | Tuya Module B — Ch 2 | Zone 3 (TV & Lounge) |
| **AC Unit** | Ceiling Cassette AC | Broadlink IR Blaster | Central HVAC |

*Note: AC unit is continuously powered and controlled via IR commands.*

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python**: 3.10+ (with `venv` support)
- **Node.js**: v18+ (with `npm`)
- **FFmpeg**: Required for OpenCV video stream decoding

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Project-Iris.git
cd Project-Iris
```

### 2. Environment Setup

The backend virtual environment and frontend dependencies are managed automatically via the startup script. Alternatively, set up manually:

#### Backend Setup:
```bash
cd backend
python3 -m venv iris_env
source iris_env/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
./iris_env/bin/pip install -r requirements.txt
cd ..
```

#### Frontend Setup:
```bash
cd frontend
npm install
cd ..
```

---

## 🚦 Running Project Iris

### Start All Services

Use the automated start script to launch both the FastAPI backend (`http://localhost:8008`) and Vite React frontend (`http://localhost:5173`):

```bash
./start.sh
```

### Stop All Services

To cleanly terminate all running background processes:

```bash
./stop.sh
```

---

## 🐳 Docker Deployment

### Option A: Using Docker Compose (Recommended)

Build and start the container with a single command:

```bash
docker-compose up -d --build
```

Access the live dashboard at **`http://localhost:8008`**.

To stop the container:
```bash
docker-compose down
```

---

### Option B: Using Standalone Docker CLI

1. **Build Image**:
   ```bash
   docker build -t project-iris:latest .
   ```

2. **Run Container**:
   ```bash
   docker run -d \
     --name project-iris \
     -p 8008:8008 \
     -v $(pwd)/backend/video.mp4:/app/backend/video.mp4 \
     project-iris:latest
   ```

---

## 📹 Using Custom MP4 Video Input

To run Project Iris against your own office video feed:

1. Place your video file at:
   ```path
   backend/video.mp4
   ```
2. Start the system:
   ```bash
   ./start.sh
   ```
3. Open `http://localhost:5173` in your browser. The system will detect `video.mp4`, stream it continuously in a loop, and execute live YOLOv8 headcount tracking.

---

## 💻 Tech Stack

- **Frontend**: React 18, Vite 5, Tailwind CSS v4, Lucide Icons, WebSockets
- **Backend**: Python 3, FastAPI, Uvicorn, AsyncIO, PyTorch, OpenCV
- **AI & Computer Vision**: YOLOv8 (`yolov8n.pt`), Custom Contour Motion Engine
- **Hardware Integration**: Tuya Open API (Relay Modules), Broadlink IR SDK

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
