#!/bin/bash
# ==============================================================================
# Mynt OS Permanent Daemon Supervisor
# Automatically manages PostgreSQL, FastAPI Backend, Frontend, and WhatsApp Bot
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/artifacts/daemon_logs"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

# 1. Start Local PostgreSQL on Port 5433 if not already running
PG_CTL=$(which pg_ctl 2>/dev/null || echo "/opt/homebrew/opt/postgresql@16/bin/pg_ctl")
if [ -x "$PG_CTL" ]; then
    if ! "$PG_CTL" -D "$PROJECT_DIR/postgres_data" status > /dev/null 2>&1; then
        echo "[$(date)] Starting local PostgreSQL on port 5433..." >> "$LOG_DIR/supervisor.log"
        "$PG_CTL" -D "$PROJECT_DIR/postgres_data" -l "$PROJECT_DIR/postgres_data/server.log" -o "-p 5433 -h 127.0.0.1" start >> "$LOG_DIR/supervisor.log" 2>&1 || true
        sleep 2
    fi
fi

# Load environment variables
if [ -f "$PROJECT_DIR/backend/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/backend/.env" | xargs)
elif [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://127.0.0.1:5433/myntreal_dev}"
export PROD_DATABASE_URL="${PROD_DATABASE_URL:-$DATABASE_URL}"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-123}"
export AI_AUDIO_DIR="$PROJECT_DIR/tmp_ai_audio"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python3")
fi

NODE_BIN=$(which node 2>/dev/null || echo "/opt/homebrew/bin/node")

# Function to run Backend Supervisor
run_backend() {
    while true; do
        # Defensively release any stale process holding port 8000 before spawning
        OLD_PIDS=$(lsof -ti :8000 2>/dev/null || true)
        if [ -n "$OLD_PIDS" ]; then
            echo "[$(date)] Cleaning up stale process on port 8000 (PIDs: $OLD_PIDS)..." >> "$LOG_DIR/backend.log"
            kill -9 $OLD_PIDS 2>/dev/null || true
            sleep 1
        fi
        echo "[$(date)] Starting FastAPI Backend on port 8000..." >> "$LOG_DIR/backend.log"
        cd "$PROJECT_DIR/backend"
        "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> "$LOG_DIR/backend.log" 2>&1 || true
        echo "[$(date)] FastAPI Backend exited. Restarting in 2s..." >> "$LOG_DIR/backend.log"
        sleep 2
    done
}

# Function to run Frontend Supervisor
run_frontend() {
    while true; do
        echo "[$(date)] Starting Node Frontend on port 5001..." >> "$LOG_DIR/frontend.log"
        cd "$PROJECT_DIR/frontend"
        export PORT=5001
        "$NODE_BIN" server.js >> "$LOG_DIR/frontend.log" 2>&1 || true
        echo "[$(date)] Node Frontend exited. Restarting in 2s..." >> "$LOG_DIR/frontend.log"
        sleep 2
    done
}

# Function to run WhatsApp Group Bot Supervisor
run_whatsapp() {
    if [ -d "$PROJECT_DIR/backend/whatsapp-group-bot" ]; then
        while true; do
            # Defensively release any stale process holding port 5002 before spawning
            OLD_WA_PIDS=$(lsof -ti :5002 2>/dev/null || true)
            if [ -n "$OLD_WA_PIDS" ]; then
                echo "[$(date)] Cleaning up stale process on port 5002 (PIDs: $OLD_WA_PIDS)..." >> "$LOG_DIR/whatsapp.log"
                kill -9 $OLD_WA_PIDS 2>/dev/null || true
                sleep 1
            fi
            echo "[$(date)] Starting WhatsApp Bot on port 5002..." >> "$LOG_DIR/whatsapp.log"
            cd "$PROJECT_DIR/backend/whatsapp-group-bot"
            export PORT=5002
            "$NODE_BIN" server.js >> "$LOG_DIR/whatsapp.log" 2>&1 || true
            echo "[$(date)] WhatsApp Bot exited. Restarting in 3s..." >> "$LOG_DIR/whatsapp.log"
            sleep 3
        done
    fi
}

# Start all components concurrently
run_backend &
run_frontend &
run_whatsapp &

# Wait for all background jobs
wait
