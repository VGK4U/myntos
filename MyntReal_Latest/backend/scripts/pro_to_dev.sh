#!/bin/bash
# Pro to Dev - Complete Production → Development Database Copy
# Usage: bash backend/scripts/pro_to_dev.sh
# Copies ALL production data to development (full end-to-end replacement)

set -e

PROD_URL=$(echo "$PROD_DATABASE_URL" | sed 's/require\./require/g')
DEV_URL="$DATABASE_URL"

if [ -z "$PROD_URL" ] || [ -z "$DEV_URL" ]; then
    echo "ERROR: PROD_DATABASE_URL or DATABASE_URL not set"
    exit 1
fi

echo ""
echo "========================================"
echo "  PRO TO DEV - Full Database Copy"
echo "========================================"
echo "  Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "[1/4] Dumping production database..."
pg_dump "$PROD_URL" \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    -F c \
    -f /tmp/prod_dump.backup 2>/dev/null

DUMP_SIZE=$(du -h /tmp/prod_dump.backup | cut -f1)
echo "       Done ($DUMP_SIZE)"

echo "[2/4] Dropping all dev tables..."
psql "$DEV_URL" -q -c "
DO \$\$
DECLARE r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS \"' || r.tablename || '\" CASCADE';
    END LOOP;
END \$\$;
" 2>/dev/null
echo "       Done"

echo "[3/4] Restoring production data to dev..."
pg_restore \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    -d "$DEV_URL" \
    /tmp/prod_dump.backup 2>/dev/null || true
echo "       Done"

echo "[4/4] Verifying..."
DEV_TABLES=$(psql "$DEV_URL" -t -q -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" 2>/dev/null | tr -d ' ')
DEV_USERS=$(psql "$DEV_URL" -t -q -c "SELECT COUNT(*) FROM \"user\";" 2>/dev/null | tr -d ' ')
PROD_USERS=$(psql "$PROD_URL" -t -q -c "SELECT COUNT(*) FROM \"user\";" 2>/dev/null | tr -d ' ')

echo ""
echo "========================================"
echo "  COPY COMPLETE"
echo "========================================"
echo "  Tables copied:  $DEV_TABLES"
echo "  Dev users:      $DEV_USERS"
echo "  Prod users:     $PROD_USERS"
echo "  Match:          $([ "$DEV_USERS" = "$PROD_USERS" ] && echo 'YES' || echo 'NO - check logs')"
echo "  Finished:       $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

rm -f /tmp/prod_dump.backup
