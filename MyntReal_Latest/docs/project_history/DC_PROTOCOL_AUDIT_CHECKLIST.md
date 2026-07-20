# DC Protocol: Comprehensive Audit Checklist
## Purpose: Ensure ZERO missed workflows, statuses, or data paths

## Methodology: Complete Code Path Tracing

### Phase 1: Map ALL Write Operations

#### 1.1 Find Every Status Change
```bash
# Search for all verification_status assignments
grep -r "verification_status.*=" backend/app --include="*.py"

# Search for all wallet writes
grep -r "earning_wallet.*=" backend/app --include="*.py"
grep -r "withdrawable_wallet.*=" backend/app --include="*.py"
grep -r "upgrade_wallet.*=" backend/app --include="*.py"
```

#### 1.2 Document Every Workflow
For EACH file found:
- [ ] Read complete function context (50 lines before/after)
- [ ] Identify trigger (API endpoint, scheduler job, admin action)
- [ ] Map complete state transition (from → to)
- [ ] Check authorization/role requirements
- [ ] Verify materialized view covers this status
- [ ] Test with production data

#### 1.3 Create Status Transition Matrix
```
Status         | Set By                | Endpoint/Function          | Next Status
---------------|----------------------|----------------------------|-------------
Pending        | Midnight calc        | scheduler.calculate_*      | →Admin Verified / →Accounts Paid
Admin Verified | Admin approval       | /admin/verify              | →Super Admin Verified
...etc
```

### Phase 2: Verify Production Data Coverage

#### 2.1 Query ALL Distinct Statuses
```sql
-- Pending Income statuses
SELECT DISTINCT verification_status, COUNT(*) 
FROM pending_income 
GROUP BY verification_status;

-- Withdrawal statuses  
SELECT DISTINCT status, COUNT(*) 
FROM withdrawal_request 
GROUP BY status;

-- Award statuses
SELECT DISTINCT status, COUNT(*) 
FROM user_award_progress 
GROUP BY status;
```

#### 2.2 Cross-Reference with Code
For EACH status found in production:
- [ ] Find code that creates this status
- [ ] Verify materialized view includes it
- [ ] Test computed value calculation
- [ ] Verify it appears in reconciliation queries

#### 2.3 Find Orphaned Statuses
Statuses in code but NOT in production = potential future bugs  
Statuses in production but NOT in code = legacy data or bugs

### Phase 3: Trace Approval Workflows

#### 3.1 Income Approval Chain
- [ ] Map Pending → Admin Verified (who can approve?)
- [ ] Map Admin Verified → Super Admin Verified (who?)
- [ ] Map Super Admin Verified → Finance Paid (who?)
- [ ] Map any direct transitions (skip-level approvals)
- [ ] Map auto-approval paths (system bypasses)

#### 3.2 Withdrawal Approval Chain
- [ ] Map Pending → Admin Verified
- [ ] Map Admin Verified → Super Admin Approved  
- [ ] Map Super Admin Approved → Bank Sent
- [ ] Map Bank Sent → Completed
- [ ] Map rejection/refund paths

#### 3.3 Award Approval Chain
- [ ] Map application → approval states
- [ ] Map cash redemption workflow
- [ ] Verify wallet credit logic

### Phase 4: Materialized View Coverage Audit

#### 4.1 For Each Materialized View
```sql
-- Get view definition
SELECT definition FROM pg_matviews WHERE matviewname = 'view_name';
```

Then verify:
- [ ] Lists ALL statuses found in production data
- [ ] Lists ALL statuses found in code (even if not used yet)
- [ ] Correct aggregation logic (SUM vs COUNT vs MAX)
- [ ] Correct JOIN conditions
- [ ] Handles NULL values properly
- [ ] Performance (indexed columns, query plan)

#### 4.2 Test Edge Cases
- [ ] User with no income (should return 0, not NULL)
- [ ] User with pending but no paid income
- [ ] User with paid but no pending income
- [ ] User with negative balance (over-withdrawal)
- [ ] User with income in ALL statuses

### Phase 5: Reconciliation Testing

#### 5.1 Compare Stored vs Computed
```sql
-- For EVERY user
SELECT 
    u.id,
    u.earning_wallet as stored,
    COALESCE(e.earning_wallet, 0) as computed,
    ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) as diff
FROM "user" u
LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
WHERE ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) > 0.01;
```

- [ ] Document ALL mismatches
- [ ] Investigate root cause for each
- [ ] Determine if expected (lag) or bug
- [ ] Fix if bug, document if expected

#### 5.2 Verify Totals Match
```sql
-- System-wide totals must match
SELECT 
    SUM(earning_wallet) as stored_total,
    (SELECT SUM(earning_wallet) FROM user_earning_wallet_balance) as computed_total,
    SUM(earning_wallet) - (SELECT SUM(earning_wallet) FROM user_earning_wallet_balance) as difference
FROM "user";
```

### Phase 6: Code Path Coverage Analysis

#### 6.1 Wallet Write Paths
For EACH authorized write path:
- [ ] Document purpose and trigger
- [ ] Verify session variable authorization
- [ ] Check transaction safety (rollback on error?)
- [ ] Verify audit logging
- [ ] Test failure scenarios

#### 6.2 Wallet Read Paths  
For EACH endpoint that reads wallet balances:
- [ ] Verify uses `get_earning_wallet()` or `get_withdrawable_wallet()`
- [ ] NOT reading `user.earning_wallet` directly
- [ ] Test with out-of-sync stored columns
- [ ] Verify error handling

### Phase 7: Integration Testing

#### 7.1 End-to-End Workflow Tests
For EACH workflow (Income, Withdrawal, Award):
- [ ] Create test user
- [ ] Trigger workflow start
- [ ] Verify each status transition
- [ ] Check materialized view updates
- [ ] Verify computed balances correct
- [ ] Test approval/rejection paths
- [ ] Verify audit trail

#### 7.2 Concurrent Operation Tests
- [ ] Multiple users getting income simultaneously
- [ ] Same user income + withdrawal concurrent
- [ ] Materialized view refresh during transactions
- [ ] Write lock under high load

### Phase 8: Documentation Requirements

#### 8.1 Status Definitions Document
For EACH status in the system:
- Status name
- Meaning (what it represents)
- Who can set it (role permissions)
- Trigger (user action, admin action, system auto)
- Which materialized view includes it
- Example production count
- Code location where set

#### 8.2 Workflow Diagrams
- Income approval workflow (all 3 paths)
- Withdrawal processing workflow
- Award redemption workflow
- Wallet sync workflow
- Materialized view refresh workflow

#### 8.3 Reconciliation Playbook
- How to run reconciliation
- Expected vs unexpected mismatches
- How to investigate discrepancies  
- When to escalate as bugs

## Audit Execution Schedule

### Before Every Phase Change
- [ ] Run complete audit checklist
- [ ] Document all findings
- [ ] Get architect review of findings
- [ ] Fix any issues before proceeding

### Before Marking Phase Complete
- [ ] 100% code path coverage verified
- [ ] 100% production status coverage verified
- [ ] 100% reconciliation accuracy (or documented exceptions)
- [ ] All workflows tested end-to-end
- [ ] Architect review PASSED

### Red Flags (Auto-fail audit)
- ❌ Found production status NOT in materialized view
- ❌ Found code path NOT verified
- ❌ Reconciliation accuracy < 99%
- ❌ Any workflow untested
- ❌ Any write path without authorization check

## Continuous Monitoring

### Daily Checks (Production)
```sql
-- Check for new statuses
SELECT DISTINCT verification_status 
FROM pending_income 
WHERE created_at > NOW() - INTERVAL '1 day';

-- Check reconciliation accuracy
SELECT COUNT(*) as mismatches
FROM "user" u
LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
WHERE ABS(u.earning_wallet - COALESCE(e.earning_wallet, 0)) > 0.01;
```

### Weekly Audits
- Review all new code merged
- Check for new wallet reads/writes
- Verify materialized view performance
- Review reconciliation trends

---
**Created**: November 2, 2025  
**Purpose**: Prevent missing critical workflows in DC Protocol implementation  
**Trigger**: Missed Finance Paid workflow in Phase 1.6 analysis  
**Owner**: DC Protocol Implementation Team
