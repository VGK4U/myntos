#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=========================================="
echo "          MYNT OS SERVICE STATUS          "
echo "=========================================="

# Check PostgreSQL (5433)
if /opt/homebrew/opt/postgresql@16/bin/pg_ctl -D "$SCRIPT_DIR/postgres_data" status > /dev/null 2>&1; then
    echo "🟢 PostgreSQL 16 (Port 5433): RUNNING"
else
    echo "🔴 PostgreSQL 16 (Port 5433): STOPPED"
fi

# Check Backend (8000)
if lsof -i :8000 | grep -q LISTEN; then
    echo "🟢 Backend API  (Port 8000): RUNNING (http://localhost:8000)"
else
    echo "🔴 Backend API  (Port 8000): STOPPED"
fi

# Check Frontend (5001)
if lsof -i :5001 | grep -q LISTEN; then
    echo "🟢 Frontend App (Port 5001): RUNNING (http://localhost:5001)"
else
    echo "🔴 Frontend App (Port 5001): STOPPED"
fi

# Check WhatsApp Bot (5002)
if lsof -i :5002 | grep -q LISTEN; then
    echo "🟢 WhatsApp Bot (Port 5002): RUNNING (http://localhost:5002)"
else
    echo "⚪ WhatsApp Bot (Port 5002): INACTIVE"
fi
echo "=========================================="
