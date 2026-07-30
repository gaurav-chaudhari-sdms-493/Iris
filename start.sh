#!/bin/bash
# Project Iris - Full Stack Runner Script

echo "============================================================"
echo " Starting Project Iris (Python Backend + React Frontend)   "
echo "============================================================"

NODE_BIN="/home/stark/.cache/JetBrains/PyCharm2026.2/acp-agents/.runtimes/node/24.13.0/bin"
export PATH=$NODE_BIN:$PATH

# Start Backend Server on Port 8008
echo "[1/2] Launching Python FastAPI & WebSocket Engine on http://localhost:8008..."
cd /home/stark/JetBrainsProjects/Iris/backend
./iris_env/bin/uvicorn server:app --host 0.0.0.0 --port 8008 &
BACKEND_PID=$!

sleep 4

# Start Frontend Vite Dev Server on Port 5173
echo "[2/2] Launching React Dashboard on http://localhost:5173..."
cd /home/stark/JetBrainsProjects/Iris/frontend
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "============================================================"
echo " Project Iris is Live!"
echo " Backend API & Telemetry: http://localhost:8008"
echo " Interactive Dashboard:  http://localhost:5173"
echo " Press Ctrl+C or run './stop.sh' to stop all servers."
echo "============================================================"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
