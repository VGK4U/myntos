#!/bin/bash
set -euo pipefail

# BeV 2.0 Production Startup Script with Enhanced Error Handling and Logging
echo "========================================="
echo "🚀 Starting BeV 2.0 Production Application"
echo "========================================="
echo "Timestamp: $(date)"
echo ""

# Get absolute root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT_DIR}/backend:${PYTHONPATH:-}"

# Function to log messages with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
error_exit() {
    log "❌ ERROR: $1"
    exit 1
}

# Cleanup function
cleanup() {
    log "🛑 Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Check environment
log "🔍 Checking environment..."
if [ -z "${DATABASE_URL:-}" ]; then
    log "⚠️  WARNING: DATABASE_URL not set (may use SQLite fallback)"
fi
log "✅ Environment check complete"

# Start Backend with Gunicorn
log "📦 Starting FastAPI backend with Gunicorn..."
cd "$ROOT_DIR/backend" || error_exit "Backend directory not found"

# Start gunicorn with production settings and error logging
gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload 2>&1 &

BACKEND_PID=$!
log "✅ Backend started with PID: $BACKEND_PID"

# Wait for backend to initialize (increased delay for reliability)
log "⏳ Waiting for backend to initialize..."
sleep 7

# Check if backend process is still running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    error_exit "Backend process failed to start or crashed immediately"
fi

# Test backend health with retries
log "🏥 Testing backend health..."
BACKEND_READY=false
for i in {1..15}; do
    if curl -f -s http://127.0.0.1:8000/docs >/dev/null 2>&1 || \
       curl -f -s http://127.0.0.1:8000/ >/dev/null 2>&1; then
        log "✅ Backend is healthy and responding on port 8000"
        BACKEND_READY=true
        break
    fi
    log "⏳ Waiting for backend... attempt $i/15"
    sleep 2
done

if [ "$BACKEND_READY" = false ]; then
    error_exit "Backend failed health check after 15 attempts (30 seconds)"
fi

# Start Frontend
log "🌐 Starting Frontend static server..."
cd "$ROOT_DIR/frontend" || error_exit "Frontend directory not found"

# Start frontend with error logging
node static-server.js 2>&1 &
FRONTEND_PID=$!
log "✅ Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to initialize
log "⏳ Waiting for frontend to initialize..."
sleep 3

# Check if frontend process is still running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    error_exit "Frontend process failed to start or crashed immediately"
fi

# Test frontend health with retries
log "🏥 Testing frontend health..."
FRONTEND_READY=false
for i in {1..10}; do
    if curl -f -s http://127.0.0.1:5000 >/dev/null 2>&1 || \
       curl -f -s http://127.0.0.1:5000/login >/dev/null 2>&1; then
        log "✅ Frontend is healthy and responding on port 5000"
        FRONTEND_READY=true
        break
    fi
    log "⏳ Waiting for frontend... attempt $i/10"
    sleep 2
done

if [ "$FRONTEND_READY" = false ]; then
    error_exit "Frontend failed health check after 10 attempts (20 seconds)"
fi

log ""
log "========================================="
log "✅ Application started successfully!"
log "   Backend PID: $BACKEND_PID (port 8000)"
log "   Frontend PID: $FRONTEND_PID (port 5000)"
log "========================================="
log "📊 Monitoring processes..."

# Monitor processes and keep script running
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        error_exit "Backend process died unexpectedly"
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        error_exit "Frontend process died unexpectedly"
    fi
    sleep 30
done
