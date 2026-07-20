#!/bin/bash
# MNR Selenium Test Setup Script
# Prepares environment for Selenium testing

echo "=========================================="
echo "  MNR SELENIUM TEST SETUP"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if backend is running
echo -e "${YELLOW}► Checking backend...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running! Start it first.${NC}"
    exit 1
fi

# 2. Check if frontend is running
echo -e "${YELLOW}► Checking frontend...${NC}"
if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend is not running! Start it first.${NC}"
    exit 1
fi

# 3. Ensure test parent user exists
echo -e "${YELLOW}► Ensuring test parent user exists...${NC}"
python scripts/testing/test_user_manager.py ensure-parent

# 4. Create test users if needed
echo -e "${YELLOW}► Creating test users...${NC}"
python scripts/testing/test_user_manager.py create 5

# 5. Set environment variables
export VGK_TEST_USERNAME='MNR182364369'
export ADMIN_TEST_USERNAME='MNR182322707'
export SUPER_ADMIN_TEST_USERNAME='MNR182371007'
export FINANCE_ADMIN_TEST_USERNAME='MNR182371010'
export TEST_USER_PASSWORD='TestPass123!'

echo ""
echo -e "${GREEN}=========================================="
echo "  SETUP COMPLETE - READY FOR TESTING"
echo "==========================================${NC}"
echo ""
echo "Test Credentials:"
echo "  VGK Admin:      MNR182364369"
echo "  Super Admin:    MNR182371007"
echo "  Finance Admin:  MNR182371010"
echo "  Regular Admin:  MNR182322707"
echo "  Password (all): TestPass123!"
echo ""
echo "Run tests with:"
echo "  python selenium_frontend_test.py"
echo "  python scripts/testing/selenium_complete_e2e.py"
echo "  python scripts/testing/selenium_announcements_rating_test.py"
echo ""
echo "After testing, cleanup with:"
echo "  python scripts/testing/test_user_manager.py cleanup"
echo ""
