# Changelog - Project Iris 👁️⚡

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`
- **Classification**: `STARK AI Internal & Proprietary`

---

All notable changes to **Project Iris** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-31

### 🌟 Added
- **STARK AI Proprietary Enterprise Software Classification**: Formalized proprietary software license and internal security protocols.
- **1-Second Real-Time YOLOv8 Headcount Engine**: High-speed PyTorch occupant detection running at 1-second polling intervals (`models/best.pt`).
- **Fast Spatial Motion Engine**: OpenCV 5 FPS Gaussian pixel-difference engine detecting instant motion across designated spatial zone bounding boxes.
- **Fine-Grained Auto-Off Vacancy Timers**:
  - Light Bulbs (LB): **3 Seconds** vacancy shut-off.
  - LED Panels (LP): **5 Seconds** vacancy shut-off.
  - Air Conditioner (AC) & TV: **10 Minutes (600 Seconds)** vacancy shut-off.
- **Anti-Flicker Hysteresis Window**: 3-second delay hold on auxiliary bulbs (`S7` and `S2`) during headcount transitions ($>3$ to $1\text{--}3$) to eliminate light flashing.
- **AZIOT 4 Node Smart Switch Driver**: Direct local TCP socket integration (`tinytuya`) for physical switches `S7` (TV Bulbs), `S4` (Upper Bulbs), `S2` (Lower Bulbs), and `S12` (Far Bulbs).
- **Broadlink RM4 Mini IR Driver**: Infrared command broadcasting for Cassette AC temperature/fan adjustments and Wall TV power control.
- **Synthetic Stream & MP4 Player Control Engine**: Video feed generator with play, pause, seek, step, speed control, and live feed switching.
- **React 18 + Tailwind CSS 2D Spatial Dashboard**: Real-time top-view room layout rendering active light fixtures, headcount count, active power (kW), cumulative energy saved (kWh), and financial cost savings ($USD).
- **Software Engineering Industry Documentation Suite**:
  - 📖 [README.md](file:///home/stark/JetBrainsProjects/Iris/README.md): Project overview, switchboard table, quickstart guide.
  - 🏗️ [ARCHITECTURE.md](file:///home/stark/JetBrainsProjects/Iris/ARCHITECTURE.md): Component breakdown, FSM diagrams, telemetry data flow.
  - 🔌 [Docs/API_REFERENCE.md](file:///home/stark/JetBrainsProjects/Iris/Docs/API_REFERENCE.md): Full REST API endpoints & WebSockets protocol reference.
  - ⚡ [Docs/AZIOT_RELAY_COMMANDS.md](file:///home/stark/JetBrainsProjects/Iris/Docs/AZIOT_RELAY_COMMANDS.md): Direct `curl` testing reference.
  - 🚀 [DEPLOYMENT.md](file:///home/stark/JetBrainsProjects/Iris/DEPLOYMENT.md): Hardware setup, Tuya local keys extraction, systemd autostart guide.
  - 🧪 [TESTING.md](file:///home/stark/JetBrainsProjects/Iris/TESTING.md): Hardware mock mode testing, API test suite, CPU thread allocation check.
  - 🛡️ [SECURITY.md](file:///home/stark/JetBrainsProjects/Iris/SECURITY.md): Internal security vulnerability reporting policy & IoT network isolation guidelines.
  - 🤝 [CONTRIBUTING.md](file:///home/stark/JetBrainsProjects/Iris/CONTRIBUTING.md): Internal developer guide, code style (PEP 8, Prettier), branch workflow.
  - 📜 [CHANGELOG.md](file:///home/stark/JetBrainsProjects/Iris/CHANGELOG.md): Version history and release tracking.

### 🔧 Changed
- **CPU Allocation Management**: Thread allocation capped to 50% system CPU cores (`torch.set_num_threads`) for optimal multitasking.
- **Tuya Hardware Reconnection Logic**: Auto-reconnects socket on network failure and restarts vacancy timers upon reconnection to prevent blackouts.
