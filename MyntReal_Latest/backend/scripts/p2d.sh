#!/bin/bash
# p2d - Production to Development Database Copy
# Usage: bash p2d.sh
# 
# Required environment variables:
#   DEV_DATABASE_URL - Development database connection string
#   PROD_DATABASE_URL - Production database connection string

set -e

echo "============================================================"
echo "  DATABASE COPY: Development → Production"
echo "============================================================"
echo ""

# Check for required environment variables
if [ -z "$DEV_DATABASE_URL" ] || [ -z "$PROD_DATABASE_URL" ]; then
    echo "❌ ERROR: Required environment variables not set"
    echo ""
    echo "Please set:"
    echo "  export DEV_DATABASE_URL='postgresql://...'"
    echo "  export PROD_DATABASE_URL='postgresql://...'"
    echo ""
    exit 1
fi

DEV_URL="$DEV_DATABASE_URL"
PROD_URL="$PROD_DATABASE_URL"

echo "⚠️  WARNING: This will REPLACE ALL production data with development data"
echo ""
read -p "Type 'YES' to continue: " confirm

if [ "$confirm" != "YES" ]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "📤 Exporting from Development..."
pg_dump "$DEV_URL" --clean --if-exists --no-owner --no-privileges > /tmp/db_backup.sql

FILE_SIZE=$(du -h /tmp/db_backup.sql | cut -f1)
echo "✅ Exported: $FILE_SIZE"
echo ""

echo "📥 Importing to Production..."
psql "$PROD_URL" -f /tmp/db_backup.sql > /tmp/import.log 2>&1

echo "✅ Import complete"
echo ""

# Verify
PROD_USERS=$(psql "$PROD_URL" -t -c "SELECT COUNT(*) FROM \"user\";")
PROD_TRANS=$(psql "$PROD_URL" -t -c "SELECT COUNT(*) FROM \"transaction\";")

echo "📊 Production Database:"
echo "   Users: $PROD_USERS"
echo "   Transactions: $PROD_TRANS"
echo ""

# Cleanup
rm -f /tmp/db_backup.sql /tmp/import.log

echo "✅ COPY COMPLETE!"
echo ""
echo "📝 Next: Restart FastAPI Backend workflow"
echo ""
