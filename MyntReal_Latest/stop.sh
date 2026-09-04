#!/bin/bash
# Stops all Mynt OS services
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Stopping Mynt OS services..."

if [ -f "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid" ]; then
    SUP_PID=$(cat "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid")
    kill -9 $SUP_PID 2>/dev/null || true
    rm -f "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid"
fi

pkill -9 -f "daemon_supervisor.sh" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "server.js" 2>/dev/null || true

# Free ports directly if still bound
for port in 8000 5001 5002; do
    PIDS=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        kill -9 $PIDS 2>/dev/null || true
    fi
done

echo "Backend, Frontend, and WhatsApp Bot stopped."
