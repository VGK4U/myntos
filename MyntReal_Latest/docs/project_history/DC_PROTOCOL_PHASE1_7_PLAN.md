# DC Protocol Phase 1.7: Write Deprecation Plan
## Status: PLANNING
## Date: November 2, 2025

## Overview
Now that Phase 1.6 has migrated ALL wallet reads to computed values from materialized views, Phase 1.7 will deprecate stored column writes to establish materialized views as the ONLY source of truth for wallet balances.

## Current State After Phase 1.6

### Read Operations ✅
- ✅ ALL wallet reads use `get_earning_wallet()` and `get_withdrawable_wallet()`
- ✅ Materialized views (`user_earning_wallet_balance`, `user_withdrawable_wallet_balance`) operational
- ✅ 99.81% reconciliation accuracy (1,056/1,058 users match)
- ✅ Real user traffic verified working

### Write Operations (Still Active)
8 authorized write paths still updating stored columns:

| Path | File | Purpose | Analysis |
|------|------|---------|----------|
| 1 | `scheduler.py:71` | Auto-approve → credit earning wallet | **DEPRECATED**: Materialized view auto-computes from pending_income |
| 2 | `scheduler.py:2564` | Auto-withdrawal deduction | **KEEP**: Withdrawal deductions not in pending_income |
| 3 | `wallet_sync_service.py:135` | Nightly sync: earning → withdrawable | **DEPRECATED**: Materialized views compute both wallets |
| 4 | `award_processing_service.py:822` | Award cash redemption | **ANALYSIS NEEDED**: Check if awards use pending_income |
| 5 | `wallet_service.py:132` | Credit earning wallet for new income | **DEPRECATED**: pending_income is source of truth |
| 6 | `wallet_service.py:437` | Withdrawal deduction | **KEEP**: Withdrawal reduces withdrawable wallet |
| 7 | `withdrawal.py:461` | Refund on rejection | **KEEP**: Reverses withdrawal deduction |
| 8 | `withdrawal.py:765` | Bulk refund on rejection | **KEEP**: Reverses bulk withdrawal deductions |

## Phase 1.7 Strategy

### Goal
Transform from "dual source" (stored + computed) to "single source" (computed only) for wallet balances.

### Approach: Incremental Deprecation
Rather than removing all writes at once, deprecate incrementally:

**Phase 1.7.1**: Remove redundant earning wallet writes (Paths 1, 3, 5)
**Phase 1.7.2**: Analyze award processing (Path 4)
**Phase 1.7.3**: Refactor withdrawal operations (Paths 2, 6, 7, 8)
**Phase 1.7.4**: Final cleanup and validation

## Detailed Analysis

### Path 1: Auto-Approve Income (SAFE TO REMOVE)
**File**: `scheduler.py:71`
**Current**: Writes to `earning_wallet` after creating `pending_income` record
**Problem**: Redundant - materialized view computes from `pending_income`
**Solution**: Remove wallet write, keep `pending_income` creation only

**Impact**: None - all reads use computed values
**Risk**: Low - materialized view already computing this

### Path 3: Nightly Wallet Sync (SAFE TO REMOVE)
**File**: `wallet_sync_service.py:135`
**Current**: Transfers earning → withdrawable daily
**Problem**: Redundant - materialized views compute both separately
**Solution**: Deprecate entire sync service

**Impact**: None - withdrawable wallet computed from transactions
**Risk**: Low - but need to verify withdrawal tracking logic

### Path 5: Income Credit (SAFE TO REMOVE)
**File**: `wallet_service.py:132`
**Current**: Credits `earning_wallet` when creating transactions
**Problem**: Redundant - materialized view sums from `pending_income`
**Solution**: Remove wallet write, keep transaction logging

**Impact**: None - all reads use computed values
**Risk**: Low - materialized view already computing this

### Paths 2, 6, 7, 8: Withdrawal Operations (REQUIRES ANALYSIS)
**Files**: `scheduler.py:2564`, `wallet_service.py:437`, `withdrawal.py:461, 765`
**Current**: Deduct from `withdrawable_wallet` on withdrawal, refund on rejection
**Question**: How do withdrawals interact with materialized views?

**Analysis Needed**:
1. Does `user_withdrawable_wallet_balance` view account for withdrawals?
2. Are withdrawals tracked in `pending_income` or separate table?
3. If separate, how does materialized view compute net withdrawable balance?

**Current Hypothesis**:
- Withdrawals likely in separate `withdrawal_request` table
- Materialized view probably computes: `SUM(pending_income) - SUM(withdrawals)`
- If correct, writes still needed OR view formula needs update

### Path 4: Award Processing (REQUIRES ANALYSIS)
**File**: `award_processing_service.py:822`
**Current**: Credits wallet when awards/bonanza approved
**Question**: Are awards tracked in `pending_income` table?

**Analysis Needed**:
1. Check if award redemptions create `pending_income` records
2. Verify materialized view includes awards in computation
3. Determine if write is redundant or necessary

## Implementation Plan

### Phase 1.7.1: Remove Redundant Earning Wallet Writes
**Target Paths**: 1, 3, 5
**Estimated Time**: 2-3 hours
**Steps**:
1. Analyze materialized view query to confirm it computes from `pending_income`
2. Remove wallet write from `scheduler.py:71` (auto-approve)
3. Remove wallet write from `wallet_service.py:132` (income credit)
4. Deprecate `wallet_sync_service.py` nightly sync
5. Test with R Logs Protocol
6. Run reconciliation to verify 100% accuracy
7. Architect review

**Risks**:
- Low - All reads already use computed values
- Materialized views already operational

**Rollback**: Re-enable writes if issues discovered

### Phase 1.7.2: Analyze Award Processing
**Target Path**: 4
**Estimated Time**: 1 hour
**Steps**:
1. Read `award_processing_service.py` lines 800-850
2. Check if awards create `pending_income` records
3. Query database for award-related pending_income
4. Verify materialized view computation includes awards
5. Document findings
6. Determine if write can be removed

### Phase 1.7.3: Analyze Withdrawal Operations
**Target Paths**: 2, 6, 7, 8
**Estimated Time**: 2 hours
**Steps**:
1. Read `user_withdrawable_wallet_balance` materialized view definition
2. Identify how withdrawals are tracked (separate table?)
3. Verify view formula accounts for withdrawals
4. Determine if writes are redundant or necessary
5. If necessary, document why they must remain
6. If redundant, plan removal strategy

### Phase 1.7.4: Final Cleanup
**Estimated Time**: 1 hour
**Steps**:
1. Remove any remaining redundant writes
2. Update write lock documentation
3. Run comprehensive reconciliation (expect 100%)
4. Performance testing
5. Architect final review
6. Update DC Protocol documentation

## Success Criteria

### Functional
- ✅ All wallet reads from materialized views (already done in Phase 1.6)
- ✅ Zero redundant writes to stored columns
- ✅ 100% reconciliation accuracy
- ✅ Real user traffic working correctly
- ✅ All income/withdrawal operations functioning

### Performance
- ✅ Materialized view refresh < 1 second
- ✅ Wallet queries < 100ms
- ✅ No performance degradation vs current

### Safety
- ✅ Write lock remains active (prevents accidental writes)
- ✅ Rollback plan documented and tested
- ✅ Architect review passed
- ✅ R Logs Protocol testing passed

## Open Questions

### Question 1: Materialized View Refresh Strategy
**Issue**: If we stop writing to stored columns, when do materialized views refresh?
**Options**:
A. Keep current nightly refresh schedule
B. Add real-time refresh on income/withdrawal events
C. Use REFRESH MATERIALIZED VIEW CONCURRENTLY on-demand

**Recommendation**: Option A (nightly refresh) + Option C (on-demand for admin tools)

### Question 2: Withdrawal Tracking
**Issue**: How are withdrawals currently tracked in materialized views?
**Need**: Read `user_withdrawable_wallet_balance` view definition
**Action**: Query `pg_views` for view SQL

### Question 3: Emergency Rollback
**Issue**: If materialized views fail, can we roll back to stored columns?
**Current**: Stored columns still populated (lag behind but present)
**Future**: If we stop writes, stored columns freeze at last sync
**Recommendation**: Keep stored columns as "last known good" snapshot

## Timeline

**Total Estimated Time**: 6-7 hours

1. **Phase 1.7.1**: 2-3 hours (remove redundant earning writes)
2. **Phase 1.7.2**: 1 hour (analyze awards)
3. **Phase 1.7.3**: 2 hours (analyze withdrawals)
4. **Phase 1.7.4**: 1 hour (cleanup and validation)

**Autonomous Execution**: Can proceed without user approval between phases, but MUST:
- Run R Logs Protocol testing after EVERY change
- Call architect for review after EVERY phase
- Document all findings
- Maintain 100% system uptime

## Next Steps

### Immediate (Now)
1. Call architect to review Phase 1.7 plan
2. Get feedback on approach and risks
3. Prioritize which analysis to do first

### After Architect Approval
1. Start with Phase 1.7.2 (Analyze awards) - safest, read-only
2. Then Phase 1.7.3 (Analyze withdrawals) - critical to understand
3. Then Phase 1.7.1 (Remove redundant writes) - once we understand full system

---
**Document Status**: DRAFT - Pending Architect Review
**Created**: November 2, 2025
**Last Updated**: November 2, 2025
