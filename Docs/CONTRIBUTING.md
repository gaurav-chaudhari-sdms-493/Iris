# Internal Engineering & Contribution Guide - Project Iris 👁️⚡

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`
- **Classification**: `STARK AI Internal & Confidential`

---

Welcome to the internal engineering guide for **Project Iris**. This repository is a **STARK AI Proprietary Project** intended exclusively for authorized STARK AI engineers, IoT specialists, and system integrators.

This document outlines our internal code style, git workflows, testing standards, and pull request procedures.

---

## 🔒 Confidentiality & Non-Disclosure Notice

All code, AI model weights (`models/best.pt`), hardware credentials, and documentation within this repository are proprietary assets of STARK AI Inc.
- Do NOT push code or `.env` secrets to public GitHub repositories.
- Do NOT share hardware local keys (`RELAY_A_KEY`) or RTSP network credentials outside the STARK AI network.

---

## 💻 Local Developer Environment Setup

### 1. Internal Repository Access
```bash
git clone git@github.com:stark-ai/Project-Iris.git
cd Project-Iris
```

### 2. Set Up Python Virtual Environment
```bash
cd backend
python3 -m venv iris_env
source iris_env/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Set Up Node.js Frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Enable Hardware Mock Mode for Local Development
When developing without physical AZIOT relay modules or Broadlink IR hardware connected to your local network, enable **Mock Mode**:

Set in `backend/.env`:
```env
IRIS_HARDWARE_MOCK=true
IRIS_SIMULATED=true
```

Or invoke via local API:
```bash
curl -X POST http://localhost:8008/api/hardware/mode \
  -H "Content-Type: application/json" \
  -d '{"mock_mode": true}'
```

---

## 🌿 Internal Git Branching Strategy

We follow a structured internal branching model:
- `main`: Production-ready release branch deployed on office edge servers.
- `develop`: Integration branch for active engineering work.
- `feature/<ticket-id>-<short-description>`: Feature development branches.
- `hotfix/<ticket-id>-<short-description>`: Production emergency bugfix branches.

### Creating a Development Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/IRIS-102-anti-flicker-enhancement
```

---

## 🎨 Internal Code Standards

### Python (Backend)
- **Style Guide**: Strict adherence to [PEP 8](https://peps.python.org/pep-0008/).
- **Type Annotations**: Mandatory type hints (`str`, `int`, `dict`, `Optional[Any]`) for all backend methods.
- **Async Execution**: Non-blocking execution loops (`asyncio.to_thread` for PyTorch / OpenCV operations).
- **CPU Allocation Safety**: Enforce `torch.set_num_threads()` limits (max 50% CPU allocation).

### React & JavaScript (Frontend)
- **Style Guide**: Functional React 18 components with Hooks.
- **Styling**: Tailwind CSS utility classes and Vanilla CSS. Avoid inline style objects where possible.
- **Icons**: Standardize on `lucide-react`.
- **Production Build**: Verify `npm run build` succeeds without build warnings or missing assets.

---

## 🧪 Pre-Commit Verification Checklist

Before submitting an internal Pull Request:
1. **Python Syntax Check**:
   ```bash
   python3 -m py_compile backend/server.py backend/orchestrator.py
   ```
2. **Frontend Production Build**:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
3. **Smoke Test API Endpoints**:
   ```bash
   ./start.sh
   curl http://localhost:8008/api/telemetry
   ./stop.sh
   ```

---

## 📝 Internal Commit Message Standards

Use clear conventional commit prefix formatting:
- `feat(hardware): add auto-reconnect logic for Tuya local TCP socket`
- `fix(orchestrator): resolve headcount anti-flicker timer reset bug`
- `docs(api): update OpenAPI schemas for hardware control endpoints`
- `style(frontend): improve contrast ratio on spatial floorplan badges`

---

## 📬 Code Review & Merge Process

1. Push your branch to the internal STARK AI git server.
2. Open a Pull Request against `develop`.
3. Require at least **1 senior lead review approval** before merging into `develop`.
4. Merges to `main` require deployment testing on an authorized office test bench.
