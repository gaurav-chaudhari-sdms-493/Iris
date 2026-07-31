#!/bin/bash
# Project Iris - Full Stack Runner Script

echo "============================================================"
echo " Starting Project Iris (Python Backend + React Frontend)   "
echo "============================================================"

# Resolve project root from this script's own location so the repo can be moved.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NODE_BIN="/home/stark/.cache/JetBrains/PyCharm2026.2/acp-agents/.runtimes/node/24.13.0/bin"
[ -d "$NODE_BIN" ] && export PATH=$NODE_BIN:$PATH

# Start Backend Server on Port 8008
echo "[1/2] Launching Python FastAPI & WebSocket Engine on http://localhost:8008..."
cd "$PROJECT_ROOT/backend" || exit 1
./iris_env/bin/uvicorn server:app --host 0.0.0.0 --port 8008 &
BACKEND_PID=$!

sleep 4

# Start Frontend Vite Dev Server on Port 5173
echo "[2/2] Launching React Dashboard on http://localhost:5173..."
cd "$PROJECT_ROOT/frontend" || exit 1
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "============================================================"
echo " Project Iris is Live!"
echo " Backend API & Telemetry: http://localhost:8008"
echo " Interactive Dashboard:  http://localhost:5173"
echo " Press Ctrl+C or run './stop.sh' to stop all servers."
echo "============================================================"

# Occupant depth-gate health check.
#
# The gate that separates lounge occupants from the developer row behind them is
# a measured head size, and that measurement only holds while people sit roughly
# where they sat during calibration. This re-measures the live scene and reports
# drift.
#
# It REPORTS ONLY and never edits .env: the suggested threshold is meaningless
# unless both areas are occupied, so a value adopted automatically could gate out
# real people. When the scene cannot support a verdict it says so and changes
# nothing. Runs in the background so it never delays startup.
HOUR=$(date +%-H)
if [ "$HOUR" -ge 8 ] && [ "$HOUR" -lt 20 ]; then
    (
        cd "$PROJECT_ROOT/backend" || exit 0
        sleep 6   # let the backend finish claiming the camera and CPU
        ./iris_env/bin/python -m hardware.measure_heads --check 2>/dev/null \
            | grep -E "^\[gate check\]|^ +|^=" || true
    ) &
else
    echo " [gate check] Skipped outside office hours - the developer row is empty,"
    echo "              so there is nothing to calibrate against."
fi

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
