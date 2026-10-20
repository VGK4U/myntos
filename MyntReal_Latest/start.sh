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

# Kill any existing processes on our ports (use graceful SIGTERM for WhatsApp Bot so it flushes S3 session)
echo ""
echo "Cleaning up existing processes..."
pkill -TERM -f "whatsapp-group-bot/server.js" 2>/dev/null || true
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "gunicorn.*8000" 2>/dev/null || true
sleep 2

# Propagate container SIGTERM/SIGINT to WhatsApp Bot so it flushes S3 session and releases lease cleanly
cleanup_on_exit() {
    echo "[SHUTDOWN] Forwarding SIGTERM to WhatsApp Bot and Backend..."
    pkill -TERM -f "whatsapp-group-bot/server.js" 2>/dev/null || true
    sleep 3
    pkill -TERM -f "uvicorn.*8000" 2>/dev/null || true
    exit 0
}
trap cleanup_on_exit SIGTERM SIGINT

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
        # Wait up to 45s for FastAPI Backend (:8000) to be ready so S3 session restore succeeds on first boot
        for i in $(seq 1 45); do
            if curl -sSf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
                echo "[SUPERVISOR] FastAPI Backend (:8000) is healthy. Launching WhatsApp Bot daemon..."
                break
            fi
            sleep 1
        done
        while true; do
            echo "[SUPERVISOR] Starting WhatsApp Bot daemon on port 5002..."
            node --max-old-space-size=256 server.js || true
            echo "[SUPERVISOR] WhatsApp Bot daemon exited. Restarting in 10 seconds..."
            sleep 10
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
