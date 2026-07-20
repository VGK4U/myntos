#!/bin/bash
set -e

echo "============================================================"
echo "  DATABASE COPY: Development → Production (FIXED VERSION)"
echo "  ALL USERS | ALL DATA | EVERYTHING"
echo "============================================================"
echo ""

# Database URLs
DEV_URL="postgresql://neondb_owner:npg_LYfk0Nre2IKo@ep-bitter-heart-adi4zlxw.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
PROD_URL="postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

echo "⚠️  WARNING: This will REPLACE ALL production data"
echo ""
read -p "Type 'YES' to continue: " confirm

if [ "$confirm" != "YES" ]; then
    echo ""
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "🚀 Starting full database copy..."
echo ""

# Install PostgreSQL if needed
if ! command -v pg_dump &> /dev/null; then
    echo "📦 Installing PostgreSQL tools..."
    nix-env -iA nixpkgs.postgresql
    echo "✅ Installed"
    echo ""
fi

# Step 1: Export with proper flags
echo "📤 Exporting from Development..."
pg_dump "$DEV_URL" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > /tmp/full_database.sql

FILE_SIZE=$(stat -f%z /tmp/full_database.sql 2>/dev/null || stat -c%s /tmp/full_database.sql)
echo "✅ Exported: $(echo "scale=2; $FILE_SIZE/1024/1024" | bc) MB"
echo ""

# Step 2: Import to Production
echo "📥 Importing to Production..."
echo "   (Errors about roles/permissions are normal and safe to ignore)"
psql "$PROD_URL" < /tmp/full_database.sql > /tmp/import_log.txt 2>&1

# Check for real errors (not role/permission errors)
if grep -i "ERROR" /tmp/import_log.txt | grep -v "role" | grep -v "permission" | grep -v "does not exist" > /dev/null; then
    echo ""
    echo "❌ Import had errors:"
    grep -i "ERROR" /tmp/import_log.txt | grep -v "role" | grep -v "permission" | head -20
    echo ""
    echo "Full log saved to: /tmp/import_log.txt"
    exit 1
fi

echo "✅ Import complete"
echo ""

# Cleanup
rm -f /tmp/full_database.sql /tmp/import_log.txt

echo "============================================================"
echo "  ✅ DATABASE COPY COMPLETE!"
echo "============================================================"
echo ""
echo "📝 Next: Restart FastAPI Backend and test with any user"
echo ""
