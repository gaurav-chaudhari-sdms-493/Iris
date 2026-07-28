#!/bin/bash
# Project Iris - Stop Script

echo "============================================================"
echo " Stopping Project Iris (Python Backend + React Frontend)    "
echo "============================================================"

# Stop Backend API on Port 8008
BACKEND_PIDS=$(lsof -t -i:8008 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
    echo "[1/2] Terminating FastAPI Backend on port 8008 (PIDs: $BACKEND_PIDS)..."
    kill -9 $BACKEND_PIDS 2>/dev/null
else
    echo "[1/2] FastAPI Backend is not running on port 8008."
fi

# Stop Frontend Vite Server on Port 5173
FRONTEND_PIDS=$(lsof -t -i:5173 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "[2/2] Terminating React Vite Dev Server on port 5173 (PIDs: $FRONTEND_PIDS)..."
    kill -9 $FRONTEND_PIDS 2>/dev/null
else
    echo "[2/2] React Frontend is not running on port 5173."
fi

# Kill any remaining uvicorn or vite processes started from Iris directory as fallback
pkill -f "uvicorn server:app --host 0.0.0.0 --port 8008" 2>/dev/null
pkill -f "vite --port 5173" 2>/dev/null

echo "============================================================"
echo " Project Iris Services Stopped Successfully!"
echo "============================================================"
