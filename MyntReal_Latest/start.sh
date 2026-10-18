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
export ENVIRONMENT="${ENVIRONMENT:-production}"
export NODE_ENV="${NODE_ENV:-production}"
export ALLOW_PROD_DB_ACCESS="1"

# Load production credentials from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Loading production credentials from .env..."
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
elif [ -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "Loading production credentials from backend/.env..."
    export $(grep -v '^#' "$SCRIPT_DIR/backend/.env" | xargs)
fi

# Verify critical environment variables
echo ""
echo "Checking environment variables..."
if [ -z "$SECRET_KEY" ]; then
    echo "WARNING: SECRET_KEY is not set in AWS environment variables! Please configure SECRET_KEY in Elastic Beanstalk Console."
    export SECRET_KEY="${ENV_SECRET_KEY:-default-mnr-system-secret-key-change-in-eb}"
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
pkill -f "whatsapp-group-bot/server.js" 2>/dev/null || true
lsof -ti:5002 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend with auto-restart supervisor loop in background
# Ensures backend stays alive and automatically restarts if worker crashes
echo ""
echo "Starting FastAPI Backend with Uvicorn supervisor (background)..."
(
  PYTHON_EXE=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python3")
  echo "Running database schema synchronization..."
  $PYTHON_EXE "$SCRIPT_DIR/backend/scripts/run_schema_migrations.py" || true

  while true; do
    cd "$SCRIPT_DIR/backend"
    $PYTHON_EXE -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info || true
    echo "[SUPERVISOR] FastAPI Backend process exited. Restarting in 2 seconds..."
    sleep 2
  done
) &
BACKEND_PID=$!
echo "Backend Supervisor PID: $BACKEND_PID"

# Start WhatsApp Group Bot daemon (port 5002) in background ONLY if node_modules exists
if [ -f "$SCRIPT_DIR/backend/whatsapp-group-bot/server.js" ] && [ -d "$SCRIPT_DIR/backend/whatsapp-group-bot/node_modules" ]; then
    echo "Starting WhatsApp Group Bot daemon on port 5002 (background)..."
    (
        cd "$SCRIPT_DIR/backend/whatsapp-group-bot"
        export NODE_PATH="$SCRIPT_DIR/frontend/node_modules:$SCRIPT_DIR/backend/whatsapp-group-bot/node_modules:${NODE_PATH}"
        while true; do
            echo "[SUPERVISOR] Starting WhatsApp Bot daemon on port 5002..."
            node --max-old-space-size=256 server.js || true
            echo "[SUPERVISOR] WhatsApp Bot daemon exited. Restarting in 30 seconds..."
            sleep 30
        done
    ) &
    WA_PID=$!
    echo "WhatsApp Bot Supervisor PID: $WA_PID"
fi

# Start Frontend Server on port 5000 immediately to satisfy AWS ALB /health checks
echo ""
echo "Starting Frontend Server on port ${PORT:-5000} immediately for AWS health checks..."
cd "$SCRIPT_DIR/frontend"
echo "======================================"
echo "Startup complete - serving traffic"
echo "======================================"

while true; do
  echo "[SUPERVISOR] Starting Node.js Frontend on port ${PORT:-5000}..."
  if [ -f "server.js" ]; then
    node --max-old-space-size=512 server.js || true
  elif [ -f "static-server.js" ]; then
    node --max-old-space-size=512 static-server.js || true
  else
    echo "ERROR: Neither static-server.js nor server.js found in $(pwd)"
    sleep 5
  fi
  echo "[SUPERVISOR] Node.js Frontend exited with code $?. Restarting in 2 seconds..."
  sleep 2
done
