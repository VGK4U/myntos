#!/bin/bash
# ==============================================================================
# Mynt OS Permanent Local Development Supervisor
# Single Source of Truth for Node Frontend (5001), FastAPI Backend (8000), and WhatsApp Bot (5002)
# Features: Child PID Tracking, Graceful Hot-Reload on Source Change, Readiness Verification
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/artifacts/daemon_logs"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

# 1. Start Local PostgreSQL on Port 5433 if configured locally
PG_CTL=$(which pg_ctl 2>/dev/null || echo "/opt/homebrew/opt/postgresql@16/bin/pg_ctl")
if [ -x "$PG_CTL" ]; then
    if [ -d "$PROJECT_DIR/postgres_data" ] && ! "$PG_CTL" -D "$PROJECT_DIR/postgres_data" status > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUPERVISOR] Starting local PostgreSQL on port 5433..." >> "$LOG_DIR/supervisor.log"
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

# DC Protocol (ARCHITECTURAL FIX - Sep 2026): Enforce local DB isolation for local supervisor
# NEVER connect to production RDS from local development daemon
export ENVIRONMENT="development"
export ALLOW_PROD_DB_ACCESS="0"
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5433/myntreal_dev"
export PROD_DATABASE_URL="$DATABASE_URL"
export RUN_STARTUP_MIGRATIONS="0"
export RUN_EXPLICIT_MIGRATIONS="0"
export SKIP_MODULE_MIGRATIONS="1"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-123}"
export AI_AUDIO_DIR="$PROJECT_DIR/tmp_ai_audio"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python3")
fi

NODE_BIN=$(which node 2>/dev/null || echo "/opt/homebrew/bin/node")

# Global Child PIDs
NODE_PID=""
BACKEND_PID=""
WA_PID=""
SHUTTING_DOWN=0

log_msg() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [SUPERVISOR] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_DIR/supervisor.log"
}

# ------------------------------------------------------------------------------
# Readiness Check Helpers
# ------------------------------------------------------------------------------
wait_for_port() {
    local port="$1"
    local timeout="$2"
    local name="$3"
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if nc -z 127.0.0.1 "$port" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
    done
    return 1
}

wait_for_http() {
    local url="$1"
    local timeout="$2"
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        local code=$(curl -s -o /dev/null -w "%{http_code}" -m 2 "$url" 2>/dev/null || echo "000")
        if [ "$code" -ge 200 ] && [ "$code" -lt 400 ]; then
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
    done
    return 1
}

# ------------------------------------------------------------------------------
# Start / Stop Handlers
# ------------------------------------------------------------------------------
start_backend() {
    log_msg "Starting FastAPI Backend on port 8000..."
    cd "$PROJECT_DIR/backend"
    "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
    log_msg "FastAPI Backend spawned with PID=$BACKEND_PID"
    
    if wait_for_port 8000 30 "Backend"; then
        log_msg "FastAPI Backend (PID=$BACKEND_PID) verified READY on port 8000."
    else
        log_msg "WARNING: FastAPI Backend (PID=$BACKEND_PID) port 8000 not responding within timeout."
    fi
}

start_frontend() {
    log_msg "Starting Node Frontend on port 5001..."
    cd "$PROJECT_DIR/frontend"
    export PORT=5001
    "$NODE_BIN" server.js >> "$LOG_DIR/frontend.log" 2>&1 &
    NODE_PID=$!
    echo "$NODE_PID" > "$LOG_DIR/frontend.pid"
    log_msg "Node Frontend spawned with PID=$NODE_PID"
    
    if wait_for_http "http://127.0.0.1:5001/" 15; then
        log_msg "Node Frontend (PID=$NODE_PID) verified READY on port 5001."
    else
        log_msg "WARNING: Node Frontend (PID=$NODE_PID) port 5001 not responding within timeout."
    fi
}

start_whatsapp() {
    if [ -d "$PROJECT_DIR/backend/whatsapp-group-bot" ]; then
        local existing_pid=$(lsof -nP -i :5002 -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
            WA_PID="$existing_pid"
            echo "$WA_PID" > "$LOG_DIR/whatsapp.pid"
            log_msg "WhatsApp Bot already listening on port 5002 (PID=$WA_PID). Adopted into supervisor."
            return 0
        fi

        log_msg "Starting WhatsApp Bot on port 5002..."
        cd "$PROJECT_DIR/backend/whatsapp-group-bot"
        export PORT=5002
        "$NODE_BIN" server.js >> "$LOG_DIR/whatsapp.log" 2>&1 &
        WA_PID=$!
        echo "$WA_PID" > "$LOG_DIR/whatsapp.pid"
        log_msg "WhatsApp Bot spawned with PID=$WA_PID"
        
        if wait_for_port 5002 10 "WhatsApp Bot"; then
            log_msg "WhatsApp Bot (PID=$WA_PID) verified READY on port 5002."
        fi
    fi
}

# ------------------------------------------------------------------------------
# Graceful Reload Handlers
# ------------------------------------------------------------------------------
reload_frontend() {
    local reason="$1"
    log_msg "Detected frontend change: $reason"
    log_msg "Requesting graceful reload of Node Frontend (PID=$NODE_PID)..."
    
    if [ -n "$NODE_PID" ] && kill -0 "$NODE_PID" 2>/dev/null; then
        kill -TERM "$NODE_PID" 2>/dev/null
        local count=0
        while kill -0 "$NODE_PID" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        log_msg "Previous Node Frontend process (PID=$NODE_PID) exited cleanly."
    fi
    
    start_frontend
}

reload_backend() {
    local reason="$1"
    log_msg "Detected backend change: $reason"
    log_msg "Requesting graceful reload of FastAPI Backend (PID=$BACKEND_PID)..."
    
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill -TERM "$BACKEND_PID" 2>/dev/null
        local count=0
        while kill -0 "$BACKEND_PID" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        log_msg "Previous FastAPI Backend process (PID=$BACKEND_PID) exited cleanly."
    fi
    
    start_backend
}

# ------------------------------------------------------------------------------
# Clean Supervisor Shutdown
# ------------------------------------------------------------------------------
graceful_shutdown() {
    if [ $SHUTTING_DOWN -eq 1 ]; then
        return
    fi
    SHUTTING_DOWN=1
    log_msg "Supervisor received shutdown signal. Stopping managed children gracefully..."
    
    if [ -n "$NODE_PID" ] && kill -0 "$NODE_PID" 2>/dev/null; then
        log_msg "Stopping Node Frontend (PID=$NODE_PID)..."
        kill -TERM "$NODE_PID" 2>/dev/null
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_msg "Stopping FastAPI Backend (PID=$BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "$WA_PID" ] && kill -0 "$WA_PID" 2>/dev/null; then
        log_msg "Stopping WhatsApp Bot (PID=$WA_PID)..."
        kill -TERM "$WA_PID" 2>/dev/null
    fi
    
    sleep 1.5
    rm -f "$LOG_DIR/frontend.pid" "$LOG_DIR/backend.pid" "$LOG_DIR/whatsapp.pid"
    log_msg "All managed services stopped. Supervisor exiting cleanly."
    exit 0
}

trap graceful_shutdown SIGINT SIGTERM SIGHUP EXIT

# ------------------------------------------------------------------------------
# Source File Signature Helpers (mtime tracking)
# ------------------------------------------------------------------------------
get_frontend_sig() {
    stat -f "%m" "$PROJECT_DIR/frontend/server.js" 2>/dev/null || echo "0"
}

get_backend_sig() {
    find "$PROJECT_DIR/backend/app" -name "*.py" -exec stat -f "%m" {} + 2>/dev/null | sort -n | tail -1 || echo "0"
}

# ------------------------------------------------------------------------------
# Boot Sequence
# ------------------------------------------------------------------------------
log_msg "================================================================="
log_msg "Starting MyntOS Local Development Supervisor"
log_msg "================================================================="

start_backend
start_frontend
start_whatsapp

LAST_FRONTEND_SIG=$(get_frontend_sig)
LAST_BACKEND_SIG=$(get_backend_sig)

log_msg "Supervisor running. Monitoring source changes and child health..."

# ------------------------------------------------------------------------------
# Main Supervisor Loop
# ------------------------------------------------------------------------------
while true; do
    sleep 2
    if [ $SHUTTING_DOWN -eq 1 ]; then
        break
    fi
    
    # 1. Child Health Monitoring & Auto-Restart if child exited unexpectedly
    if [ -n "$NODE_PID" ] && ! kill -0 "$NODE_PID" 2>/dev/null; then
        log_msg "Node Frontend (PID=$NODE_PID) exited unexpectedly. Auto-recovering..."
        start_frontend
    fi
    
    if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_msg "FastAPI Backend (PID=$BACKEND_PID) exited unexpectedly. Auto-recovering..."
        start_backend
    fi
    
    if [ -n "$WA_PID" ] && ! kill -0 "$WA_PID" 2>/dev/null; then
        if [ -d "$PROJECT_DIR/backend/whatsapp-group-bot" ]; then
            log_msg "WhatsApp Bot (PID=$WA_PID) exited unexpectedly. Auto-recovering..."
            start_whatsapp
        fi
    fi
    
    # 2. Source Change Detection (Hot-Reload)
    CURR_FRONTEND_SIG=$(get_frontend_sig)
    if [ "$CURR_FRONTEND_SIG" != "$LAST_FRONTEND_SIG" ] && [ -n "$CURR_FRONTEND_SIG" ]; then
        LAST_FRONTEND_SIG="$CURR_FRONTEND_SIG"
        reload_frontend "frontend/server.js modified"
    fi
    
    CURR_BACKEND_SIG=$(get_backend_sig)
    if [ "$CURR_BACKEND_SIG" != "$LAST_BACKEND_SIG" ] && [ -n "$CURR_BACKEND_SIG" ]; then
        LAST_BACKEND_SIG="$CURR_BACKEND_SIG"
        reload_backend "backend python source modified"
    fi
done
