#!/bin/bash
# ==============================================================================
# Mynt OS Permanent Daemon Supervisor
# Automatically manages PostgreSQL, FastAPI Backend, Frontend, and WhatsApp Bot
# ==============================================================================

PROJECT_DIR="/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest"
LOG_DIR="$PROJECT_DIR/artifacts/daemon_logs"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

# 1. Start Local PostgreSQL on Port 5433 if not already running
if ! /opt/homebrew/opt/postgresql@16/bin/pg_ctl -D "$PROJECT_DIR/postgres_data" status > /dev/null 2>&1; then
    echo "[$(date)] Starting local PostgreSQL on port 5433..." >> "$LOG_DIR/supervisor.log"
    /opt/homebrew/opt/postgresql@16/bin/pg_ctl -D "$PROJECT_DIR/postgres_data" -l "$PROJECT_DIR/postgres_data/server.log" -o "-p 5433 -h 127.0.0.1" start >> "$LOG_DIR/supervisor.log" 2>&1 || true
    sleep 2
fi

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Ensure local database is used for local resilience
export DATABASE_URL="postgresql://127.0.0.1:5433/myntreal_dev"
export PROD_DATABASE_URL="postgresql://127.0.0.1:5433/myntreal_dev"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-123}"
export AI_AUDIO_DIR="$PROJECT_DIR/tmp_ai_audio"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Function to run Backend Supervisor
run_backend() {
    while true; do
        echo "[$(date)] Starting FastAPI Backend on port 8000..." >> "$LOG_DIR/backend.log"
        cd "$PROJECT_DIR/backend"
        "$PROJECT_DIR/venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_DIR/backend.log" 2>&1 || true
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
        /opt/homebrew/bin/node server.js >> "$LOG_DIR/frontend.log" 2>&1 || true
        echo "[$(date)] Node Frontend exited. Restarting in 2s..." >> "$LOG_DIR/frontend.log"
        sleep 2
    done
}

# Function to run WhatsApp Group Bot Supervisor
run_whatsapp() {
    if [ -d "$PROJECT_DIR/backend/whatsapp-group-bot" ]; then
        while true; do
            echo "[$(date)] Starting WhatsApp Bot on port 5002..." >> "$LOG_DIR/whatsapp.log"
            cd "$PROJECT_DIR/backend/whatsapp-group-bot"
            export PORT=5002
            /opt/homebrew/bin/node server.js >> "$LOG_DIR/whatsapp.log" 2>&1 || true
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
