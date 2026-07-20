# R Logs Protocol (Real-time Logs Testing)

## Purpose
The R Logs Protocol mandates continuous checking of backend, frontend, and browser console logs during development and after EVERY change to ensure no errors are introduced. This protocol is critical for maintaining system stability during the DC Protocol implementation.

## When to Use R Logs Protocol
**MANDATORY after:**
1. ✅ ANY code change to backend or frontend
2. ✅ Database schema modifications  
3. ✅ API endpoint updates or refactoring
4. ✅ Before marking any task as complete
5. ✅ Before architect review
6. ✅ After workflow restart

## Testing Steps

### Step 1: Refresh All Logs
```bash
# Use refresh_all_logs tool to capture latest state
refresh_all_logs()
```

### Step 2: Check Backend Logs for Errors
```bash
# Search for errors, exceptions, 500 status codes
grep -E "(ERROR|500|exception|Exception)" /tmp/logs/FastAPI_Backend_*.log | tail -50
```

**What to look for:**
- ❌ ERROR messages with stack traces
- ❌ 500 Internal Server Error responses
- ❌ Unhandled exceptions
- ❌ Database errors (IntegrityError, etc.)
- ✅ All endpoints returning 200 OK
- ✅ No Traceback lines

### Step 3: Check Frontend Server Logs
```bash
# Check frontend server for routing or session issues
cat /tmp/logs/Frontend_Server_*.log | tail -100
```

**What to look for:**
- ❌ Route not found errors
- ❌ Session/authentication failures
- ❌ Static file 404s
- ✅ Successful page access logs
- ✅ Valid session token checks

### Step 4: Check Browser Console Logs
```bash
# Use screenshot tool to capture browser console
screenshot(path="/user-home")
```

**What to look for:**
- ❌ JavaScript errors (TypeError, ReferenceError)
- ❌ Failed to load resource (404, 500)
- ❌ CORS errors
- ❌ Uncaught exceptions
- ✅ Successful API calls
- ✅ Clean console with only log messages

### Step 5: Verify All Critical Endpoints

**User Endpoints** (Must return 200 OK when authenticated):
```bash
# Profile
GET /api/v1/users/profile

# Dashboard
GET /api/v1/users/dashboard-data-fast

# Wallet
GET /api/v1/users/wallet-summary

# Team
GET /api/v1/users/team/all-members?page=1&page_size=50
GET /api/v1/users/team/direct-referrals-filtered?page=1&page_size=50

# Income
GET /api/v1/financial-operations/income/{bev_id}/comprehensive-day-wise?limit=30

# Withdrawals
GET /api/v1/withdrawals/withdrawal-requests
GET /api/v1/withdrawals/withdrawal-summary
GET /api/v1/withdrawals/income-transactions

# Awards
GET /api/v1/awards-fast/user/{bev_id}/direct
GET /api/v1/awards-fast/user/{bev_id}/matching

# Bonanza
GET /api/v1/bonanza/my-bonanzas
GET /api/v1/bonanza/my-claimed
```

### Step 6: Document Findings

**For each test session, document:**
1. ✅ Date/time of testing
2. ✅ What was changed
3. ✅ All errors found (with line numbers)
4. ✅ All endpoints tested
5. ✅ Resolution steps taken
6. ✅ Final verification status

## Error Classification

### Critical Errors (MUST FIX IMMEDIATELY)
- 🔴 500 Internal Server Error on any user endpoint
- 🔴 Unhandled exceptions in backend
- 🔴 Database write lock violations
- 🔴 Data inconsistencies (DC Protocol violations)
- 🔴 Authentication/authorization failures
- 🔴 Type errors causing crashes

### Warning Errors (Fix before next deployment)
- 🟡 Deprecated API usage
- 🟡 Console warnings
- 🟡 Missing error handling
- 🟡 Performance warnings

### Informational (Monitor)
- 🟢 Expected validation errors (user input)
- 🟢 Debug logging
- 🟢 Cache misses

## Integration with DC Protocol

**During DC Protocol implementation:**
1. Test BEFORE making changes (baseline)
2. Test AFTER each change (regression check)
3. Test AFTER architect review (final verification)
4. Document all findings in DC Protocol session notes

## Checklist for Task Completion

Before marking ANY task complete:
- [ ] Backend logs checked - no errors
- [ ] Frontend logs checked - no errors  
- [ ] Browser console checked - no errors
- [ ] All affected endpoints tested - 200 OK
- [ ] No new errors introduced
- [ ] All changes documented
- [ ] Architect review completed
- [ ] R Logs Protocol documented in task notes

## Common Issues and Solutions

### Issue: Profile Endpoint 500 Error
**Symptom:** `TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'`
**Root Cause:** Type mismatch in comparison logic
**Solution:** Convert Decimal to float before arithmetic operations
```python
# ❌ BAD
abs(wallet_data.get('earning_wallet', 0) - computed_earning) <= 0.01

# ✅ GOOD
abs(wallet_data.get('earning_wallet', 0) - float(computed_earning)) <= 0.01
```

### Issue: Write Lock Trigger Blocking Legitimate Writes
**Symptom:** `Wallet column update blocked by write lock`
**Root Cause:** Missing session variable authorization
**Solution:** Set authorization before write operations
```python
# Set authorization
db.execute(text("SET LOCAL app.wallet_write_allowed = 'wallet_sync'"))
# Perform write
user.earning_wallet = new_value
db.commit()
```

## Protocol History

### Session 2025-11-02
- **Change:** Fixed profile endpoint type mismatch (Decimal vs float)
- **Testing:** R Logs Protocol used to identify and verify fix
- **Result:** ✅ Profile endpoint now returns 200 OK
- **Errors Found:** 1 critical (500 error)
- **Errors Fixed:** 1 critical
- **Status:** All user endpoints working
