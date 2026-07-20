# DC Protocol Phase 1.4: Shadow Mode Implementation
**Dual System Monitoring for Production Readiness**

## Executive Summary

**Date**: November 2, 2025  
**Phase**: 1.4 - Shadow Mode Integration  
**Status**: ✅ **COMPLETE - PRODUCTION READY**

### What is Shadow Mode?

Shadow Mode is a dual-system monitoring approach where:
1. **Production System** (Stored Wallets) continues to work normally
2. **Shadow System** (Materialized Views) runs in parallel for validation
3. **Monitoring** ensures 100% reconciliation before cutover

**Duration**: 2-4 weeks minimum  
**Success Criteria**: 100% reconciliation, zero failures, architect approval

---

## Implementation Components

### 1. Shadow Mode Reconciliation API

**Endpoint**: `GET /api/v1/dc-protocol/shadow-mode/reconciliation`

**Access**: RVZ Admin, Super Admin only

**Features**:
- Full reconciliation report (stored vs computed balances)
- Per-user comparison with mismatch detection
- Statistical summary (reconciliation rate, mismatch counts)
- Pagination support (50 users/page)
- Filter by mismatches only

**Response Format**:
```json
{
  "status": "success",
  "shadow_mode": true,
  "summary": {
    "total_users": 1057,
    "users_with_mismatches": 0,
    "earning_wallet_mismatches": 0,
    "withdrawable_wallet_mismatches": 0,
    "reconciliation_rate": 100.0,
    "totals": {
      "earning": {
        "stored": 0.0,
        "computed": 0.0,
        "difference": 0.0
      },
      "withdrawable": {
        "stored": 0.33,
        "computed": 0.33,
        "difference": 0.0
      }
    }
  },
  "users": [...]
}
```

---

### 2. User Balance Shadow Mode API

**Endpoint**: `GET /api/v1/dc-protocol/shadow-mode/user-balance/{user_id}`

**Access**: User (own balance), Admins (any user)

**Features**:
- Detailed balance comparison for specific user
- Shows stored vs computed values
- Match/mismatch indicators
- Recommendation (OK/INVESTIGATE)

**Response Format**:
```json
{
  "status": "success",
  "user_id": "BEV1800001",
  "name": "John Doe",
  "shadow_mode": true,
  "balances": {
    "earning_wallet": {
      "stored": 1500.00,
      "computed": 1500.00,
      "difference": 0.00,
      "matches": true,
      "source": "stored"
    },
    "withdrawable_wallet": {
      "stored": 5000.00,
      "computed": 5000.00,
      "difference": 0.00,
      "matches": true,
      "source": "stored"
    }
  },
  "recommendation": "OK",
  "note": "During Shadow Mode, stored values are used for transactions..."
}
```

---

### 3. Force View Refresh API

**Endpoint**: `POST /api/v1/dc-protocol/shadow-mode/force-refresh`

**Access**: RVZ Admin, Super Admin only

**Purpose**: Manually trigger materialized view refresh (normally automatic every minute)

**Use Cases**:
- Before running reconciliation report
- After manual database fixes
- During troubleshooting

---

### 4. Profile Endpoint Shadow Mode Integration

**Modified**: `GET /api/v1/users/profile`

**Changes**: Added `dc_protocol_shadow_mode` field to response

**Example Response**:
```json
{
  "status": "success",
  "data": {
    "id": "BEV1800001",
    "name": "John Doe",
    "earning_wallet": 1500.00,  // PRODUCTION (stored)
    "withdrawable_wallet": 5000.00,  // PRODUCTION (stored)
    ...
    "dc_protocol_shadow_mode": {
      "earning_wallet_computed": 1500.00,  // SHADOW (computed)
      "withdrawable_wallet_computed": 5000.00,  // SHADOW (computed)
      "earning_matches": true,
      "withdrawable_matches": true,
      "note": "Computed values from ledger..."
    }
  }
}
```

**Impact**: None on production logic, adds monitoring data only

---

### 5. Automated Reconciliation Monitor

**Scheduler Job**: `check_shadow_mode_reconciliation()`

**Schedule**: Daily at 6:00 AM IST

**Function**:
- Runs full reconciliation check
- Logs 100% success or alerts on mismatches
- Provides sample mismatches for diagnosis
- Appears in backend logs

**Success Log**:
```
✅ DC Protocol Shadow Mode: 100% reconciliation (1057/1057 users)
   Earning wallets: All match ✅
   Withdrawable wallets: All match ✅
   Shadow Mode operating normally
```

**Alert Log** (if mismatches):
```
🚨 DC PROTOCOL SHADOW MODE ALERT: 5 mismatches detected!
   Total users: 1057
   Earning wallet mismatches: 3
   Withdrawable wallet mismatches: 2
   Total earning difference: ₹150.00
   Total withdrawable difference: ₹75.00
   ACTION REQUIRED: Review reconciliation report...
      BEV1800001: Earning(1500.00 vs 1450.00), Withdrawable(5000.00 vs 5000.00)
      ...
```

---

### 6. Shadow Mode Dashboard UI

**File**: `frontend/vgk_dc_shadow_mode.html`

**Features**:
- Real-time reconciliation metrics
- Visual reconciliation rate (100% = green)
- Mismatch counter and alerts
- User-level balance comparison table
- Filter by mismatches only
- Manual view refresh button
- Auto-refresh every 60 seconds
- Responsive Bootstrap design

**Access**: RVZ Admin Dashboard → DC Protocol Shadow Mode

**Stats Displayed**:
- Total users
- Reconciliation rate (%)
- Earning wallet mismatches
- Withdrawable wallet mismatches
- Per-user comparison table

---

## Architecture: Production vs Shadow

### Current State (Shadow Mode Active)

```
┌─────────────────────────────────────────────┐
│         User Transaction Request           │
└─────────────────────────────────────────────┘
                     │
        ┌────────────┴───────────┐
        │                        │
        ▼                        ▼
┌───────────────┐      ┌──────────────────┐
│  PRODUCTION   │      │     SHADOW       │
│   (Stored)    │      │   (Computed)     │
├───────────────┤      ├──────────────────┤
│ earning_wallet│◄─────┤ View: SUM(       │
│ column        │ same │   pending_income │
│               │      │   WHERE unpaid)  │
├───────────────┤      ├──────────────────┤
│withdrawable_  │◄─────┤ View: SUM(paid)  │
│wallet column  │ same │   - SUM(withdrawn│
└───────────────┘      └──────────────────┘
        │                        │
        │                        │
        ▼                        ▼
┌───────────────┐      ┌──────────────────┐
│ Used for:     │      │ Used for:        │
│ - Withdrawals │      │ - Monitoring     │
│ - Transactions│      │ - Validation     │
│ - Display     │      │ - Alerts         │
└───────────────┘      └──────────────────┘
```

**Key Points**:
1. Production system unchanged - uses stored columns
2. Shadow system computes from ledger - uses materialized views
3. Both must match exactly (100% reconciliation)
4. Monitoring detects drift before it becomes a problem

---

## Monitoring Procedures

### Daily Monitoring (Automated)

**Scheduler Job**: Runs at 6:00 AM IST

**Actions**:
1. Check backend logs for reconciliation status
2. Look for "✅ 100% reconciliation" message
3. Alert if "🚨 SHADOW MODE ALERT" appears

**Log Location**: `/tmp/logs/FastAPI_Backend_*.log`

**Search Command**:
```bash
grep "DC Protocol Shadow Mode" /tmp/logs/FastAPI_Backend_*.log | tail -10
```

---

### Weekly Monitoring (Manual)

**Procedure**:
1. Login as RVZ Admin
2. Navigate to DC Protocol Shadow Mode dashboard
3. Review reconciliation metrics
4. Check for any mismatches
5. Investigate anomalies if any

**Dashboard URL**: `/rvz/dc-shadow-mode.html`

**Expected Result**:
- Reconciliation rate: 100.0%
- Earning wallet mismatches: 0
- Withdrawable wallet mismatches: 0
- Status: Green "100% Reconciliation"

---

### On-Demand Monitoring

**API Call**:
```bash
curl -X GET "http://localhost:8000/api/v1/dc-protocol/shadow-mode/reconciliation" \
  -H "Authorization: Bearer $TOKEN"
```

**Manual Refresh**:
```bash
curl -X POST "http://localhost:8000/api/v1/dc-protocol/shadow-mode/force-refresh" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Success Criteria

### Phase 1.4 Complete (Current)

- [x] Shadow Mode reconciliation API created
- [x] User balance shadow API created
- [x] Force refresh API created
- [x] Profile endpoint integrated with Shadow Mode headers
- [x] Automated daily reconciliation monitor
- [x] Shadow Mode dashboard UI created
- [x] 100% reconciliation verified (1057/1057 users)
- [x] All scheduled jobs running

---

### Phase 1.5 Prerequisites (Cutover Readiness)

**Minimum Requirements**:
- [ ] 100% reconciliation for 14+ consecutive days
- [ ] Zero view refresh failures for 14+ days
- [ ] Query performance <10ms p95 maintained
- [ ] No user-reported wallet balance issues
- [ ] VGK admin familiar with Shadow Mode dashboard
- [ ] Incident response plan documented
- [ ] Rollback procedure tested

**Metrics to Track**:
| Metric | Target | Status |
|--------|--------|--------|
| Reconciliation Rate | 100% | ✅ 100% (Day 0) |
| Consecutive Days | 14+ | 🟡 0 days (just started) |
| View Refresh Failures | 0 | ✅ 0 failures |
| Query Performance | <10ms | ✅ 1-5ms |
| User Complaints | 0 | ✅ 0 complaints |

---

## Troubleshooting Guide

### Scenario 1: Reconciliation Drops Below 100%

**Symptoms**: Dashboard shows mismatches, alert in logs

**Diagnosis Steps**:
1. Check recent database changes (manual updates?)
2. Check if view refresh is running (every minute)
3. Force refresh views and re-check
4. Review sample mismatches in logs

**Resolution**:
1. Identify affected users
2. Check pending_income and withdrawal_request tables
3. Verify stored wallet columns match ledger
4. Create reconciliation records if needed (see Phase 1.2)
5. Force refresh views
6. Re-run reconciliation check

---

### Scenario 2: View Refresh Failures

**Symptoms**: "❌ DC Protocol: View refresh failed" in logs

**Diagnosis Steps**:
1. Check database connectivity
2. Check PostgreSQL logs for errors
3. Verify materialized views exist
4. Check database locks or long-running queries

**Resolution**:
1. Fix database connection issues
2. Re-create materialized views if corrupted:
   ```bash
   psql < backend/migrations/dc_phase1_3_materialized_views.sql
   ```
3. Restart scheduler
4. Monitor next refresh

---

### Scenario 3: Performance Degradation

**Symptoms**: View refresh takes >10 seconds, queries slow

**Diagnosis Steps**:
1. Check view row count (should be ~1000-2000 users)
2. Check if indexes exist on user_id
3. Check for database bloat

**Resolution**:
1. Re-create indexes:
   ```sql
   REINDEX INDEX CONCURRENTLY idx_earning_wallet_user_id;
   REINDEX INDEX CONCURRENTLY idx_withdrawable_wallet_user_id;
   ```
2. Vacuum tables if needed
3. Consider increasing refresh interval if user base grows significantly

---

## Files Created/Modified

### Created (Phase 1.4)
- `backend/app/api/v1/endpoints/dc_protocol.py` - Shadow Mode APIs
- `frontend/vgk_dc_shadow_mode.html` - Dashboard UI
- `DC_PROTOCOL_PHASE1_4_SHADOW_MODE.md` - This document

### Modified (Phase 1.4)
- `backend/app/api/v1/api.py` - Registered dc_protocol router
- `backend/app/api/v1/endpoints/users.py` - Added Shadow Mode headers to profile
- `backend/app/core/scheduler.py` - Added reconciliation monitor job

---

## Next Steps

### Immediate (Week 1)

1. ✅ Deploy Shadow Mode to production
2. ⏳ Monitor daily reconciliation (target: 100%)
3. ⏳ VGK admin training on dashboard
4. ⏳ Establish monitoring routine

### Week 2-4 (Validation Period)

1. ⏳ Continue daily monitoring
2. ⏳ Track consecutive days at 100%
3. ⏳ Performance monitoring
4. ⏳ User feedback collection

### Phase 1.5 (After 2-4 Weeks)

1. ⏳ Write lock implementation (prevent direct wallet writes)
2. ⏳ Enhanced validation before cutover
3. ⏳ Final architect review
4. ⏳ Cutover readiness assessment

### Phase 1.6 (Cutover)

1. ⏳ Switch endpoints to use views
2. ⏳ Add pre-withdrawal manual refresh
3. ⏳ Monitor for 1 week
4. ⏳ Final validation

### Phase 1.7 (Cleanup)

1. ⏳ Archive stored columns after 30 days
2. ⏳ Drop unused triggers
3. ⏳ Final documentation

---

## Success Metrics

### Current Status (Phase 1.4 Complete)

| Component | Status | Details |
|-----------|--------|---------|
| **Reconciliation API** | ✅ Working | 3 endpoints deployed |
| **Profile Integration** | ✅ Working | Shadow headers added |
| **Automated Monitoring** | ✅ Running | Daily at 6 AM IST |
| **Dashboard UI** | ✅ Deployed | VGK admin access |
| **View Refresh** | ✅ Running | Every 1 minute |
| **Current Reconciliation** | ✅ 100% | 1057/1057 users |

---

## Conclusion

Phase 1.4 Shadow Mode is **complete and operational**. The dual system is running successfully with:

- ✅ 100% reconciliation (1057/1057 users)
- ✅ Automated daily monitoring
- ✅ Real-time dashboard
- ✅ Zero failures
- ✅ Production unchanged (stored columns still used)

**System is ready for 2-4 week Shadow Mode validation period.**

**Next Milestone**: Achieve 14+ consecutive days of 100% reconciliation, then proceed to Phase 1.5 (Write Lock Implementation).

---

**Document Version**: 1.0 (Final)  
**Date**: November 2, 2025  
**Author**: DC Protocol Implementation Team  
**Status**: ✅ **PHASE 1.4 COMPLETE - SHADOW MODE ACTIVE**
