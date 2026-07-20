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

# Verify critical environment variables
echo ""
echo "Checking environment variables..."
if [ -z "$SECRET_KEY" ]; then
    echo "Warning: SECRET_KEY not set, using fallback"
    export SECRET_KEY="production-fallback-key-$(date +%s)"
fi

if [ -z "$DATABASE_URL" ] && [ -z "$PROD_DATABASE_URL" ]; then
    echo "Error: No DATABASE_URL or PROD_DATABASE_URL found"
    exit 1
else
    echo "Database URL configured"
fi

# Kill any existing processes on our ports
echo ""
echo "Cleaning up existing processes..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "gunicorn.*8000" 2>/dev/null || true
sleep 1

# Start backend with gunicorn + 2 UvicornWorkers in background
# DC_WS_CAPACITY_001: 2 workers prevents single-worker queue exhaustion under load.
# --preload ensures lifespan/startup (APScheduler, DB migrations) runs once in the
# master process before workers fork — prevents duplicate background jobs.
echo ""
echo "Starting FastAPI Backend with Gunicorn (2 UvicornWorkers, background)..."
cd "$SCRIPT_DIR/backend"

gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --preload &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# DC Protocol: Start frontend IMMEDIATELY (parallel startup)
# Frontend has graceful handling for backend unavailability
echo ""
echo "Starting Frontend Server on port ${PORT:-5000} (parallel)..."
cd "$SCRIPT_DIR/frontend"
echo "======================================"
echo "Startup complete - serving traffic"
echo "======================================"
exec node server.js
