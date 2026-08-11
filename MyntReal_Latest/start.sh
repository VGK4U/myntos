#!/bin/bash
# Production Startup Script - Parallel Launch for Autoscale
# DC Protocol Jan 2026: Frontend starts immediately to satisfy port 5000 requirement
# Backend starts in parallel - frontend handles temporary unavailability gracefully

set -e

echo "======================================"
echo "Starting MNR Reference Program"
echo "======================================"
echo "Startup time: $(date)"
echo "Environment: ${NODE_ENV:-production}"
echo "Frontend port: ${PORT:-5000}"
echo "Backend port: 8000 (internal)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/backend:$SCRIPT_DIR:${PYTHONPATH}"

# Verify critical environment variables
echo ""
echo "Checking environment variables..."
if [ -z "$SECRET_KEY" ]; then
    echo "Warning: SECRET_KEY not set, using fallback"
    export SECRET_KEY="production-fallback-key-$(date +%s)"
fi

if [ -z "$DATABASE_URL" ] && [ -z "$PROD_DATABASE_URL" ]; then
    echo "Warning: No DATABASE_URL or PROD_DATABASE_URL found in environment, falling back to application config"
else
    echo "Database URL configured"
fi

# Kill any existing processes on our ports
echo ""
echo "Cleaning up existing processes..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "gunicorn.*8000" 2>/dev/null || true
sleep 1

# Start backend with auto-restart supervisor loop in background
# Ensures backend stays alive and automatically restarts if worker crashes
echo ""
echo "Starting FastAPI Backend with Uvicorn supervisor (background)..."
(
  while true; do
    echo "[SUPERVISOR] Starting FastAPI Backend on port 8000..."
    cd "$SCRIPT_DIR/backend"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
    echo "[SUPERVISOR] FastAPI Backend process exited with code $?. Restarting in 2 seconds..."
    sleep 2
  done
) &
BACKEND_PID=$!
echo "Backend Supervisor PID: $BACKEND_PID"

# Let FastAPI Backend start in the background while we immediately start the frontend.
# This prevents 502/5xx errors during Elastic Beanstalk deployments by ensuring
# port 5000 is open and ready to answer ELB health checks instantly.
echo ""
echo "Backend is warming up in the background. Starting frontend server immediately..."

# Start Frontend Server on port 5000 with supervisor loop
echo ""
echo "Starting Frontend Server on port ${PORT:-5000}..."
cd "$SCRIPT_DIR/frontend"
echo "======================================"
echo "Startup complete - serving traffic"
echo "======================================"

while true; do
  echo "[SUPERVISOR] Starting Node.js Frontend on port ${PORT:-5000}..."
  node server.js || true
  echo "[SUPERVISOR] Node.js Frontend exited with code $?. Restarting in 2 seconds..."
  sleep 2
done
