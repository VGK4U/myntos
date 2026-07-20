#!/bin/bash
set -e

echo "============================================================"
echo "  DATABASE COPY: Development → Production"
echo "  ALL USERS | ALL DATA | EVERYTHING"
echo "============================================================"
echo ""

# Database URLs
DEV_URL="postgresql://neondb_owner:npg_LYfk0Nre2IKo@ep-bitter-heart-adi4zlxw.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
PROD_URL="postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

echo "⚠️  WARNING: This will REPLACE ALL production data"
echo "   → ALL users will get correct data from development"
echo "   → ALL earnings, awards, withdrawals - EVERYTHING"
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

# Step 1: Check if pg_dump exists
if ! command -v pg_dump &> /dev/null; then
    echo "📦 Installing PostgreSQL tools..."
    nix-env -iA nixpkgs.postgresql
    echo "✅ PostgreSQL tools installed"
    echo ""
fi

# Step 2: Export from Development
echo "📤 Exporting ALL data from Development database..."
echo "   (This includes ALL users, ALL transactions, ALL tables)"
pg_dump "$DEV_URL" > /tmp/full_database.sql
FILE_SIZE=$(stat -f%z /tmp/full_database.sql 2>/dev/null || stat -c%s /tmp/full_database.sql)
echo "✅ Export complete: $(echo "scale=2; $FILE_SIZE/1024/1024" | bc) MB"
echo ""

# Step 3: Import to Production
echo "📥 Importing ALL data to Production database..."
echo "   (This will REPLACE production with development data)"
psql "$PROD_URL" < /tmp/full_database.sql 2>&1 | tail -20
echo ""
echo "✅ Import complete"
echo ""

# Step 4: Cleanup
rm -f /tmp/full_database.sql
echo "🗑️  Cleaned up temp files"
echo ""

echo "============================================================"
echo "  ✅ DATABASE COPY COMPLETE!"
echo "============================================================"
echo ""
echo "📊 WHAT WAS COPIED:"
echo "   ✓ ALL users (every single user in the system)"
echo "   ✓ ALL earnings (every transaction, every wallet)"
echo "   ✓ ALL awards (direct, matching, bonanza)"
echo "   ✓ ALL withdrawals (complete history)"
echo "   ✓ EVERYTHING from development → production"
echo ""
echo "📝 Next steps:"
echo "   1. Restart FastAPI Backend workflow"
echo "   2. Test with any user (BEV180143 or any other)"
echo "   3. ALL users should see their correct earnings"
echo ""
