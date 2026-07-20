#!/bin/bash

echo "🔄 Production Database Reset Script"
echo "===================================="
echo ""

# Check if production database URL is set
if [ -z "$PRODUCTION_DATABASE_URL" ]; then
    echo "⚠️  PRODUCTION_DATABASE_URL not found in environment variables"
    echo ""
    echo "Please set it first using:"
    echo "export PRODUCTION_DATABASE_URL='your-production-db-url'"
    echo ""
    echo "Or run this script with the URL:"
    echo "./reset_production.sh 'postgresql://user:pass@host:port/db'"
    exit 1
fi

# Use provided URL or environment variable
DB_URL="${1:-$PRODUCTION_DATABASE_URL}"

echo "📊 Connecting to production database..."
echo ""

# Run the reset script
psql "$DB_URL" -f backend/PRODUCTION_RESET_SCRIPT.sql

echo ""
echo "✅ Reset completed!"
echo ""
echo "Next steps:"
echo "1. Verify the results above show all 0s"
echo "2. If successful, changes are already committed"
echo "3. Check your app at https://app.bevseries.com"
