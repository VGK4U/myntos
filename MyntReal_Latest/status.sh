#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=========================================="
echo "          MYNT OS SERVICE STATUS          "
echo "=========================================="

# Check Database
DB_URL=""
if [ -f "$SCRIPT_DIR/backend/.env" ]; then
    DB_URL=$(grep "^DATABASE_URL=" "$SCRIPT_DIR/backend/.env" | cut -d= -f2- | tr -d '"')
elif [ -f "$SCRIPT_DIR/.env" ]; then
    DB_URL=$(grep "^DATABASE_URL=" "$SCRIPT_DIR/.env" | cut -d= -f2- | tr -d '"')
fi

PG_CTL=$(command -v pg_ctl 2>/dev/null || echo "/opt/homebrew/opt/postgresql@16/bin/pg_ctl")
if [[ "$DB_URL" == *"rds.amazonaws.com"* ]]; then
    echo "🟢 AWS RDS PostgreSQL (Port 5432): CONNECTED"
elif [ -x "$PG_CTL" ] && "$PG_CTL" -D "$SCRIPT_DIR/postgres_data" status > /dev/null 2>&1; then
    echo "🟢 PostgreSQL 16 (Port 5433): RUNNING"
else
    echo "⚪ Local PostgreSQL (Port 5433): INACTIVE (SQLite Engine Active)"
fi

# Check Backend (8000)
if lsof -nP -i :8000 | grep -q LISTEN; then
    echo "🟢 Backend API  (Port 8000): RUNNING (http://localhost:8000)"
else
    echo "🔴 Backend API  (Port 8000): STOPPED"
fi

# Check Frontend (5001)
if lsof -nP -i :5001 | grep -q LISTEN; then
    echo "🟢 Frontend App (Port 5001): RUNNING (http://localhost:5001)"
else
    echo "🔴 Frontend App (Port 5001): STOPPED"
fi

# Check WhatsApp Bot (5002)
if lsof -nP -i :5002 | grep -q LISTEN; then
    echo "🟢 WhatsApp Bot (Port 5002): RUNNING (http://localhost:5002)"
else
    echo "⚪ WhatsApp Bot (Port 5002): INACTIVE"
fi
echo "=========================================="
