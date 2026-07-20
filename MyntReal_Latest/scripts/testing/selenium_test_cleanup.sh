#!/bin/bash
# MNR Selenium Test Cleanup Script
# Removes all test data after testing

echo "=========================================="
echo "  MNR SELENIUM TEST CLEANUP"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup test users
echo -e "${YELLOW}► Cleaning up test users...${NC}"
python scripts/testing/test_user_manager.py cleanup

# Remove test screenshots
echo -e "${YELLOW}► Removing test screenshots...${NC}"
if [ -d "test_screenshots" ]; then
    rm -rf test_screenshots/*
    echo -e "${GREEN}✓ Screenshots removed${NC}"
fi

# Remove any test database artifacts
echo -e "${YELLOW}► Cleaning test announcements...${NC}"
python -c "
from backend.app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Delete test announcements
    result = db.execute(text(\"DELETE FROM announcements WHERE title LIKE 'SELENIUM%'\"))
    print(f'  Deleted {result.rowcount} test announcements')
    
    # Delete test ratings
    result = db.execute(text(\"DELETE FROM announcement_ratings WHERE announcement_id NOT IN (SELECT id FROM announcements)\"))
    print(f'  Deleted {result.rowcount} orphaned ratings')
    
    db.commit()
    print('✓ Test announcements cleaned')
except Exception as e:
    print(f'✗ Error cleaning announcements: {e}')
    db.rollback()
finally:
    db.close()
"

echo ""
echo -e "${GREEN}=========================================="
echo "  CLEANUP COMPLETE"
echo "==========================================${NC}"
echo ""
echo "All test data has been removed."
echo ""
