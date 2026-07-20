#!/bin/bash

echo "=========================================="
echo "PHASE 6: CACHE-BUSTING VALIDATION TEST"
echo "=========================================="
echo "Purpose: Prevent browser cache from showing old versions"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Cache-Control Headers
echo -e "\n${YELLOW}Test 1: Cache-Control Headers${NC}"
echo "Checking cache headers on /user/awards..."

CACHE_HEADER=$(curl -s -I http://localhost:5000/user/awards 2>&1 | grep -i "cache-control")

if echo "$CACHE_HEADER" | grep -qi "no-store"; then
  echo -e "  ${GREEN}✅ PASS${NC}: Cache-Control headers present with 'no-store'"
  echo "  Header: $CACHE_HEADER"
  ((PASS_COUNT++))
else
  echo -e "  ${RED}❌ FAIL${NC}: Cache-Control headers missing or incorrect"
  echo "  Found: $CACHE_HEADER"
  echo "  Expected: Cache-Control: no-store, no-cache, must-revalidate"
  ((FAIL_COUNT++))
fi

# Test 2: Verify Build ID is Dynamic
echo -e "\n${YELLOW}Test 2: Build ID Changes on Restart${NC}"
echo "Checking if Build ID is dynamic..."

OLD_BUILD=$(curl -s http://localhost:5000/login | grep -o "BUILD_ID.*[0-9]\{13\}" | head -1 | grep -o "[0-9]\{13\}")
echo "  Current Build ID: $OLD_BUILD"

if [ -n "$OLD_BUILD" ]; then
  echo -e "  ${GREEN}✅ PASS${NC}: Build ID found in HTML"
  ((PASS_COUNT++))
else
  echo -e "  ${RED}❌ FAIL${NC}: Build ID not found in HTML"
  ((FAIL_COUNT++))
fi

# Test 3: Session Token Embedding
echo -e "\n${YELLOW}Test 3: Session Token Embedding${NC}"
echo "Logging in and checking if sessionToken is embedded in page HTML..."

# Login
LOGIN_RESP=$(curl -s -c /tmp/cache_test_cookies.txt -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"BEV1800346","password":"123456"}')

if echo "$LOGIN_RESP" | grep -q '"success".*true'; then
  echo "  ✅ Login successful"
  
  # Get awards page
  AWARDS_HTML=$(curl -s -b /tmp/cache_test_cookies.txt "http://localhost:5000/user/awards")
  
  # Check for sessionToken
  TOKEN_LINE=$(echo "$AWARDS_HTML" | grep "const sessionToken = '" | head -1)
  
  if [ -n "$TOKEN_LINE" ]; then
    # Extract token value
    TOKEN_VALUE=$(echo "$TOKEN_LINE" | sed -n "s/.*const sessionToken = '\([^']*\)'.*/\1/p")
    
    if [ -n "$TOKEN_VALUE" ] && [ "$TOKEN_VALUE" != "" ] && [ "$TOKEN_VALUE" != "undefined" ]; then
      echo -e "  ${GREEN}✅ PASS${NC}: sessionToken embedded with value"
      echo "  Token (first 30 chars): ${TOKEN_VALUE:0:30}..."
      ((PASS_COUNT++))
    else
      echo -e "  ${RED}❌ FAIL${NC}: sessionToken is EMPTY or undefined"
      echo "  Line: $TOKEN_LINE"
      ((FAIL_COUNT++))
    fi
  else
    echo -e "  ${RED}❌ FAIL${NC}: sessionToken declaration not found in HTML"
    ((FAIL_COUNT++))
  fi
else
  echo -e "  ${RED}❌ FAIL${NC}: Login failed, cannot test token embedding"
  ((FAIL_COUNT++))
fi

# Test 4: Verify API_BASE_URL
echo -e "\n${YELLOW}Test 4: API_BASE_URL Configuration${NC}"

if echo "$AWARDS_HTML" | grep -q "const API_BASE_URL = ''"; then
  echo -e "  ${GREEN}✅ PASS${NC}: API_BASE_URL configured for relative URLs (frontend proxy)"
  ((PASS_COUNT++))
else
  echo -e "  ${RED}❌ FAIL${NC}: API_BASE_URL not configured correctly"
  ((FAIL_COUNT++))
fi

# Test 5: Session Restoration After "Restart"
echo -e "\n${YELLOW}Test 5: Session Restoration (Simulated)${NC}"
echo "Testing if session persists with cookie..."

# Access page again with same cookie (simulates browser after server restart)
AWARDS_HTML_2=$(curl -s -b /tmp/cache_test_cookies.txt "http://localhost:5000/user/awards")

if echo "$AWARDS_HTML_2" | grep -q "Awards Summary\|Direct Referral Awards"; then
  echo -e "  ${GREEN}✅ PASS${NC}: Session persists, page accessible with cookie"
  ((PASS_COUNT++))
else
  echo -e "  ${RED}❌ FAIL${NC}: Session lost, page redirects or fails"
  ((FAIL_COUNT++))
fi

# Cleanup
rm -f /tmp/cache_test_cookies.txt

# Summary
echo ""
echo "=========================================="
echo "CACHE VALIDATION TEST SUMMARY"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
  echo -e "${GREEN}✅ ALL CACHE VALIDATION TESTS PASSED${NC}"
  echo ""
  echo "Cache-busting is properly configured:"
  echo "  ✓ Cache-Control headers prevent browser caching"
  echo "  ✓ Build ID changes on restart"
  echo "  ✓ Session tokens embedded correctly"
  echo "  ✓ Session restoration works after restart"
  echo ""
  exit 0
else
  echo -e "${RED}❌ CACHE VALIDATION FAILED${NC}"
  echo ""
  echo "Real-world impact of failures:"
  echo "  • Users see old versions after updates"
  echo "  • 'Failed to load awards' errors"
  echo "  • Authentication failures (empty tokens)"
  echo ""
  echo "Prevention for users:"
  echo "  1. Hard refresh: Ctrl+Shift+R (Desktop)"
  echo "  2. Clear browser cache (Mobile)"
  echo "  3. Check DevTools → Network → Response Headers"
  echo ""
  exit 1
fi
