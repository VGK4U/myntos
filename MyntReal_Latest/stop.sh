#!/bin/bash
# Stops all Mynt OS services
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Stopping Mynt OS services..."

if [ -f "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid" ]; then
    SUP_PID=$(cat "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid")
    kill -9 $SUP_PID 2>/dev/null || true
    rm -f "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid"
fi

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "node server.js" 2>/dev/null || true
pkill -f "daemon_supervisor.sh" 2>/dev/null || true

echo "Backend, Frontend, and WhatsApp Bot stopped."
