#!/bin/bash
# Starts Mynt OS in background with detached supervisor
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/artifacts/daemon_logs"

echo "Starting Mynt OS background services..."
nohup bash "$SCRIPT_DIR/daemon_supervisor.sh" > "$SCRIPT_DIR/artifacts/daemon_logs/supervisor_nohup.log" 2>&1 &
BG_PID=$!
echo "$BG_PID" > "$SCRIPT_DIR/artifacts/daemon_logs/supervisor.pid"

sleep 3
bash "$SCRIPT_DIR/status.sh"
