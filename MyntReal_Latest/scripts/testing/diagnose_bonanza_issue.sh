#!/bin/bash

echo "🔍 BONANZA APPROVAL LOADING ISSUE - DIAGNOSTIC SCRIPT"
echo "======================================================"
echo ""

# Step 1: Create bonanza via API
echo "► STEP 1: Creating test bonanza..."

TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"BEV182371007","password":"superadmin123"}' | jq -r '.access_token')

CREATE_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/bonanza/create" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "DIAGNOSTIC_BONANZA",
    "start_date": "'$(date -u +%Y-%m-%dT%H:%M:%S)'",
    "end_date": "'$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%S)'",
    "criteria_type": "direct_referrals",
    "target_requirement": 10,
    "reward_type": "cash",
    "reward_amount": 5000,
    "is_monetary": true,
    "total_budget": 50000
  }')

BONANZA_ID=$(echo $CREATE_RESP | jq -r '.bonanza_id')

if [ "$BONANZA_ID" != "null" ] && [ -n "$BONANZA_ID" ]; then
  echo "✓ Bonanza created: ID=$BONANZA_ID"
else
  echo "✗ Failed to create bonanza"
  echo "Response: $CREATE_RESP"
  exit 1
fi

echo ""

# Step 2: Test approval with timing
echo "► STEP 2: Testing approval process (Finance Admin)..."
echo ""

FINANCE_TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"BEV182371010","password":"financeadmin123"}' | jq -r '.access_token')

echo "  Measuring approval response time..."
START_TIME=$(date +%s%3N)

APPROVE_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/bonanza/approve/$BONANZA_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FINANCE_TOKEN" \
  -d "{\"bonanza_id\": $BONANZA_ID}" \
  -w '\n%{time_total}')

END_TIME=$(date +%s%3N)
RESPONSE_TIME=$(echo "scale=3; ($END_TIME - $START_TIME) / 1000" | bc)

# Extract response (last line is timing)
APPROVE_MSG=$(echo "$APPROVE_RESP" | head -n -1)
API_TIME=$(echo "$APPROVE_RESP" | tail -n 1)

echo ""
echo "  Response: $APPROVE_MSG"
echo "  API Response Time: ${API_TIME}s"
echo "  Total Time: ${RESPONSE_TIME}s"

# Analyze
SUCCESS=$(echo $APPROVE_MSG | jq -r '.success' 2>/dev/null)
if [ "$SUCCESS" == "true" ]; then
  echo ""
  echo "✓ Approval successful"
  
  # Check if slow
  TIME_CHECK=$(echo "$API_TIME > 5" | bc)
  if [ "$TIME_CHECK" -eq 1 ]; then
    echo "⚠️  WARNING: Response time exceeds 5 seconds (slow)"
  else
    echo "✓ Response time within acceptable range"
  fi
else
  echo "✗ Approval failed"
fi

echo ""

# Step 3: Verify in database
echo "► STEP 3: Verifying in database..."
psql $DATABASE_URL -c "SELECT id, name, status, approved_by FROM bonanza WHERE id = $BONANZA_ID"

echo ""

# Step 4: Check for any pending approvals
echo "► STEP 4: Checking pending approvals..."
PENDING=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM bonanza WHERE status = 'Pending'")
echo "  Pending bonanzas: $PENDING"

echo ""

# Step 5: Performance analysis
echo "► STEP 5: Performance Analysis..."
echo ""
echo "FINDINGS:"

if [ "$SUCCESS" == "true" ]; then
  echo "  ✓ Approval endpoint is functional"
else
  echo "  ✗ Approval endpoint has issues"
fi

TIME_INT=$(printf "%.0f" $API_TIME)
if [ "$TIME_INT" -gt 5 ]; then
  echo "  ⚠️  Backend processing is SLOW (${API_TIME}s)"
  echo ""
  echo "RECOMMENDATIONS:"
  echo "  1. Check database indexes on bonanza table"
  echo "  2. Review approval endpoint logic in bonanza.py"
  echo "  3. Check for unnecessary database queries"
  echo "  4. Consider caching or async processing"
else
  echo "  ✓ Backend performance is acceptable"
fi

echo ""
echo "======================================================"
echo "Diagnostic complete. Bonanza ID=$BONANZA_ID preserved for manual testing."
echo "To delete: psql \$DATABASE_URL -c \"DELETE FROM bonanza WHERE id = $BONANZA_ID\""
