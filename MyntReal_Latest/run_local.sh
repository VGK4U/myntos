#!/bin/bash
# Local development startup script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Set fallback database to postgres if not set
if [ -z "$DATABASE_URL" ] && [ -z "$PROD_DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://127.0.0.1:5433/myntreal_dev"
    echo "Using local PostgreSQL database at: $DATABASE_URL"
fi

if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="dev-secret-key-123"
fi

export AI_AUDIO_DIR="$SCRIPT_DIR/tmp_ai_audio"

# Clean up existing processes on ports 8000 and 5000
echo "Cleaning up any existing processes on port 8000 and 5000..."
pkill -f "uvicorn.*8000" || true
pkill -f "node.*server.js" || true
sleep 1

# Start Backend using Virtual Environment Python
echo "Starting Backend (FastAPI) on port 8000..."
cd "$SCRIPT_DIR/backend"
"$SCRIPT_DIR/venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend using Node
echo "Starting Frontend (Node.js) on port 5001..."
cd "$SCRIPT_DIR/frontend"
export PORT=5001
node server.js &
FRONTEND_PID=$!

# Start WhatsApp Group Bot Gateway on port 5002
if [ -d "$SCRIPT_DIR/backend/whatsapp-group-bot" ]; then
    echo "Starting WhatsApp Web Group Bot Gateway on port 5002..."
    cd "$SCRIPT_DIR/backend/whatsapp-group-bot"
    export PORT=5002
    node server.js &
    GROUP_BOT_PID=$!
fi

echo "======================================"
echo "Servers are starting up!"
echo "Backend API: http://localhost:8000"
echo "Frontend App: http://localhost:5001"
echo "WhatsApp Group Bot: http://localhost:5002/qr"
echo "Press Ctrl+C to stop servers."
echo "======================================"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID $GROUP_BOT_PID
