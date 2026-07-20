#!/bin/bash

# Comprehensive VGK VM Menu Testing Script
# Tests all 22 VM menu pages for proper routing and functionality

echo "========================================="
echo "VGK VM MENU - COMPREHENSIVE TEST"
echo "========================================="
echo ""

# Color codes for output
GREEN='\033[0.32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_route() {
  local route=$1
  local expected_status=$2
  local description=$3
  
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5000${route})
  
  if [ "$STATUS" = "$expected_status" ]; then
    echo -e "${GREEN}✅ PASS${NC} - $description"
    echo "   Route: $route (Status: $STATUS)"
    ((PASSED++))
  else
    echo -e "${RED}❌ FAIL${NC} - $description"
    echo "   Route: $route (Expected: $expected_status, Got: $STATUS)"
    ((FAILED++))
  fi
  echo ""
}

echo "Testing VM Menu Pages (unauthenticated - should redirect to login)..."
echo "-----------------------------------------------------------------------"
echo ""

# Test all VM menu routes (should return 302 for unauthenticated users)
test_route "/admin/unified-approval-system" "302" "Pending Approvals"
test_route "/vgk/brand-level-management" "302" "Content Management (Brand/Level)"
test_route "/vgk/popup-control" "302" "Popup Control"
test_route "/vgk/bulk-user-edit" "302" "Bulk User Edit"
test_route "/vgk/user-activation-control" "302" "User Activation Control"
test_route "/vgk/reactivate-reassign" "302" "Reactivate/Reassign"
test_route "/vgk/user-update-approvals" "302" "User Update Approvals"
test_route "/vgk/change-user-password" "302" "Change User Password"
test_route "/vgk/password-change" "302" "VGK Password Change"
test_route "/vgk/secondary-password-setup" "302" "Secondary Password Setup"
test_route "/admin/delete-management" "302" "Delete Management"
test_route "/admin/data-recovery" "302" "Data Recovery Center"
test_route "/vgk/add-packages" "302" "Add Packages"
test_route "/vgk/role-management" "302" "Role Management"
test_route "/vgk/award-management" "302" "Award Management"
test_route "/vgk/system-controls" "302" "System Controls"
test_route "/vgk/rate-configuration" "302" "Rate Configuration"
test_route "/vgk/daily-ceiling" "302" "Daily Ceiling"
test_route "/vgk/emergency-wallet" "302" "Emergency Wallet"
test_route "/expense-categories" "302" "Expense Categories"
test_route "/vgk/menu-configuration" "302" "Menu Configuration"
test_route "/vgk/scheduler-dashboard" "302" "Scheduler Dashboard"

echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo "Total Tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "${RED}Failed: $FAILED${NC}"
else
  echo "Failed: $FAILED"
fi
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
  exit 0
else
  echo -e "${RED}❌ SOME TESTS FAILED${NC}"
  exit 1
fi
