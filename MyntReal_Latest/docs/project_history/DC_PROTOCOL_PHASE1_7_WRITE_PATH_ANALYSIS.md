# DC Protocol Phase 1.7: Complete Write Path Analysis
## Date: November 2, 2025
## Purpose: Document EVERY wallet write to determine which can be deprecated

## Methodology

### Step 1: Exhaustive Code Search ✅
```bash
# Python property writes
grep -rn "\.earning_wallet\s*=" backend/app --include="*.py" | wc -l  # Result: 2
grep -rn "\.withdrawable_wallet\s*=" backend/app --include="*.py" | wc -l  # Result: 2

# SQL UPDATE statements
grep -rn "UPDATE.*earning_wallet\|UPDATE.*withdrawable_wallet" backend/app --include="*.py"  # Result: 2

# Authorized write locations
grep -rn "SET LOCAL app.wallet_write_allowed" backend/app --include="*.py" | wc -l  # Result: 8
```

### Step 2: Files Containing Wallet Writes
```
1. backend/app/services/award_processing_service.py
2. backend/app/services/wallet_sync_service.py
3. backend/app/services/wallet_service.py
4. backend/app/core/scheduler.py
5. backend/app/api/v1/endpoints/withdrawal.py
```

## Complete Write Path Inventory

### Path 1: Auto-Approve Income (scheduler.py:68)
```python
# Location: scheduler.py, auto_approve_and_credit_wallet(), lines 60-71
current_earning = Decimal(str(getattr(user, 'earning_wallet', 0) or 0))
new_earning = current_earning + Decimal(str(pending_income.withdrawal_wallet_amount))
setattr(user, 'earning_wallet', float(new_earning))
```

**Purpose**: Credit earning_wallet when auto-approving pending_income  
**Trigger**: System auto-approval (skips admin chain)  
**Sets pending_income status**: 'Accounts Paid'  
**DC Protocol Analysis**:
- ✅ Creates pending_income record with 'Accounts Paid' status
- ❌ REDUNDANT: Materialized view computes from pending_income WHERE status IN ('Pending', 'Admin Verified', ...)
- ❌ WRONG VIEW: 'Accounts Paid' is in withdrawable wallet view, not earning wallet view!

**Critical Finding**: This writes to earning_wallet but sets status to 'Accounts Paid' which moves income to withdrawable wallet view. The write is:
1. Wrong wallet (should write withdrawable, not earning)
2. Redundant (materialized view computes from pending_income)

**Recommendation**: ❌ DEPRECATED - Remove wallet write, keep pending_income creation only

---

### Path 2: Create Transaction (wallet_service.py:137)
```python
# Location: wallet_service.py, create_transaction(), lines 132-144
current_earning = Decimal(str(getattr(user, 'earning_wallet', 0) or 0))
setattr(user, 'earning_wallet', current_earning + withdrawable_amount)
setattr(user, 'upgrade_wallet_balance', current_upgraded + upgraded_wallet_amount)
```

**Purpose**: Credit earning_wallet when creating new income transaction  
**Trigger**: Legacy income creation (check if still used)  
**Creates**: Transaction record only (NOT pending_income)  
**DC Protocol Analysis**:
- ❌ Does NOT create pending_income record
- ❌ Transaction table is NOT source of truth for wallet balance
- ❌ Materialized views don't read from Transaction table

**Critical Question**: Is this function still called in production?  
**Recommendation**: 🔍 VERIFY USAGE - Check if endpoint exists that calls this

---

### Path 3: Process Withdrawal (wallet_service.py:442)
```python
# Location: wallet_service.py, process_withdrawal(), lines 445-448
withdrawable_balance = float(getattr(user, 'withdrawable_wallet', 0) or 0)
setattr(user, 'withdrawable_wallet', Decimal(str(withdrawable_balance - withdrawal_amount)))
```

**Purpose**: Deduct from withdrawable_wallet when admin approves withdrawal  
**Trigger**: Admin approves withdrawal request  
**DC Protocol Analysis**:
- ❌ Legacy withdrawal approval system
- ❌ Conflicts with new withdrawal.py endpoints (lines 455-778)

**Critical Question**: Is this method still called by any endpoint?  
**Recommendation**: 🔍 VERIFY USAGE - Search for calls to wallet_service.process_withdrawal()

---

### Path 4: Daily Wallet Sync (wallet_sync_service.py:132)
```python
# Location: wallet_sync_service.py, _process_user_wallet(), lines 134-136
user.withdrawable_wallet = float(withdrawable_before + transfer_amount)
user.earning_wallet = 0.0  # Clear earning wallet after transfer
user.last_wallet_sync_at = sync_timestamp
```

**Purpose**: Daily transfer earning → withdrawable for KYC-approved users  
**Trigger**: Nightly cron job  
**DC Protocol Analysis**:
- ❌ REDUNDANT: Materialized views compute BOTH wallets independently
- ❌ NO TRANSFER NEEDED: Withdrawable view = paid income - withdrawals
- ❌ WRONG CONCEPT: Earnings don't "transfer" - they change status

**Recommendation**: ❌ DEPRECATED - Materialized views eliminate need for sync

---

### Path 5: Award Cash Redemption (award_processing_service.py:819)
```python
# Location: award_processing_service.py, process_finance_approval(), lines 822-827
if user.kyc_status == 'Approved' and getattr(user, 'kyc_bank_verified', False):
    user.withdrawable_wallet = (user.withdrawable_wallet or Decimal('0')) + net_amount
else:
    user.earning_wallet = (user.earning_wallet or Decimal('0')) + net_amount
```

**Purpose**: Credit wallet when Finance Admin approves cash award redemption  
**Trigger**: Finance Admin clicks "Approve" for award payment  
**Creates**: Transaction record (line 806-815)  
**DC Protocol Analysis**:
- ❓ UNCLEAR: Does this create pending_income record?
- ❓ UNCLEAR: How do materialized views see award income?

**Critical Question**: Do awards create pending_income records?  
**Recommendation**: 🔍 MUST VERIFY - Check if awards flow through pending_income table

---

### Path 6: Auto-Withdrawal Deduction (scheduler.py:2574)
```python
# Location: scheduler.py, generate_automatic_withdrawals(), lines 2579-2606
# Step 1: Sync stored column to computed value
UPDATE "user" SET withdrawable_wallet = :computed_balance
# Step 2: Atomic deduction
UPDATE "user" SET withdrawable_wallet = withdrawable_wallet - :amount 
WHERE COALESCE(withdrawable_wallet, 0) >= :amount
```

**Purpose**: Deduct from withdrawable_wallet when creating auto-withdrawal  
**Trigger**: Daily cron job (Mon-Sat 7:00 AM)  
**Creates**: withdrawal_request record  
**DC Protocol Analysis**:
- ✅ UPDATED IN PHASE 1.6: Now syncs stored to computed before deduction
- ✅ NEEDED: Withdrawal deductions must update stored column for atomic guarantee
- ✅ MATERIALIZED VIEW: Subtracts withdrawal_request WHERE status IN ('Bank Sent', 'Completed')

**Recommendation**: ✅ KEEP - Required for atomic withdrawal reservation

---

### Path 7: Withdrawal Rejection Refund (withdrawal.py:459)
```python
# Location: withdrawal.py, update_request(), lines 461-468
UPDATE "user"
SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) + :amount
WHERE id = :user_id
```

**Purpose**: Re-credit withdrawable_wallet when admin rejects withdrawal  
**Trigger**: Admin clicks "Reject" on withdrawal request  
**Updates**: withdrawal_request.status = 'Rejected'  
**DC Protocol Analysis**:
- ✅ NEEDED: Reverses Path 6 deduction
- ✅ ATOMIC: Ensures single re-credit only
- ✅ MATERIALIZED VIEW: Rejections don't count in withdrawal total

**Recommendation**: ✅ KEEP - Required to reverse withdrawal deductions

---

### Path 8: Bulk Withdrawal Rejection (withdrawal.py:763)
```python
# Location: withdrawal.py, update_batch(), lines 765-774
for user_id, amount in rejected_requests:
    UPDATE "user"
    SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) + :amount
    WHERE id = :user_id
```

**Purpose**: Re-credit withdrawable_wallet for bulk rejected withdrawals  
**Trigger**: Admin rejects entire withdrawal batch  
**Updates**: Multiple withdrawal_request.status = 'Rejected'  
**DC Protocol Analysis**:
- ✅ NEEDED: Reverses multiple Path 6 deductions
- ✅ ATOMIC: Ensures single re-credit per request
- ✅ MATERIALIZED VIEW: Rejections don't count in withdrawal total

**Recommendation**: ✅ KEEP - Required for bulk withdrawal reversals

---

## Summary

### ✅ Keep (3 paths - withdrawal operations)
1. **Path 6**: Auto-withdrawal deduction (scheduler.py:2574)
2. **Path 7**: Single withdrawal refund (withdrawal.py:459)
3. **Path 8**: Bulk withdrawal refund (withdrawal.py:763)

**Reason**: Withdrawal system requires atomic deduction/refund operations

### ❌ Deprecated (2 paths - redundant with materialized views)
1. **Path 1**: Auto-approve income credit (scheduler.py:68) - WRONG WALLET + REDUNDANT
2. **Path 4**: Daily wallet sync (wallet_sync_service.py:132) - NO LONGER NEEDED

**Reason**: Materialized views compute both wallets from pending_income

### 🔍 Verification Complete (3 paths)

#### Path 2: Create Transaction (wallet_service.py:137) - ✅ VERIFIED
```bash
grep -rn "wallet_service.create_transaction\|WalletService.*create_transaction" backend/app
# Result: NO CALLS FOUND
```
**Status**: ❌ DEAD CODE - No endpoint calls this function  
**Recommendation**: Remove function entirely

#### Path 3: Process Withdrawal (wallet_service.py:442) - ✅ VERIFIED
```bash
grep -rn "wallet_service.process_withdrawal\|WalletService.*process_withdrawal" backend/app
# Result: 2 calls in admin.py lines 236 & 242
```
**Endpoint**: `/admin/withdrawal-requests/{request_id}/approve` (admin.py:222)  
**Status**: ⚠️ LEGACY ENDPOINT ACTIVE - Conflicts with new withdrawal.py endpoints  
**Database**: 0 users with wallet balance, so likely not used in production  
**Recommendation**: Deprecate and redirect to new withdrawal.py endpoints

#### Path 5: Award Redemption (award_processing_service.py:819) - ✅ VERIFIED
```sql
SELECT COUNT(*) FROM pending_income WHERE income_type LIKE '%Award%';
-- Result: 0 (awards do NOT create pending_income records)

SELECT COUNT(*) FROM transaction WHERE transaction_type LIKE '%Award%';
-- Result: 0 (no paid awards in production)

SELECT COUNT(*) FROM user_award_progress;
-- Result: 120 awards exist, none paid yet
```
**Status**: 🚨 CRITICAL GAP - Awards bypass pending_income entirely  
**Impact**: Awards are NOT included in materialized views  
**Current Flow**: Admin approves → Creates Transaction → Writes wallet directly  
**DC Protocol Violation**: Awards circumvent single source of truth  
**Recommendation**: Refactor awards to create pending_income records

---

## Summary - VERIFIED FINDINGS

### ✅ Keep (3 paths - withdrawal operations)
1. **Path 6**: Auto-withdrawal deduction (scheduler.py:2574)
2. **Path 7**: Single withdrawal refund (withdrawal.py:459)
3. **Path 8**: Bulk withdrawal refund (withdrawal.py:763)

**Reason**: Withdrawal system requires atomic deduction/refund operations

### ❌ Deprecated (2 paths - redundant with materialized views)
1. **Path 1**: Auto-approve income credit (scheduler.py:68) - WRONG WALLET + REDUNDANT
2. **Path 4**: Daily wallet sync (wallet_sync_service.py:132) - NO LONGER NEEDED

**Reason**: Materialized views compute both wallets from pending_income

### ⚠️ Legacy (2 paths - active but should be removed)
1. **Path 2**: Create transaction (wallet_service.py:137) - DEAD CODE
2. **Path 3**: Process withdrawal (wallet_service.py:442) - Legacy endpoint (admin.py:222)

**Reason**: Unused or superseded by new endpoints

### 🚨 Critical Gap (1 path - violates DC Protocol)
1. **Path 5**: Award redemption (award_processing_service.py:819) - BYPASSES pending_income

**Reason**: Awards not included in materialized views, violates single source of truth

---

## Next Steps

### Phase 1.7A: Remove Deprecated Paths (Low Risk)
1. ✅ Remove Path 1 wallet write from auto_approve_and_credit_wallet() (scheduler.py:68)
2. ✅ Remove Path 4 daily wallet sync (wallet_sync_service.py:132)
3. ✅ Keep pending_income record creation only

### Phase 1.7B: Remove Legacy Code (Low Risk)
1. ✅ Remove Path 2: wallet_service.create_transaction() method (dead code)
2. ⚠️ Deprecate Path 3: admin.py withdrawal endpoint → redirect to withdrawal.py

### Phase 1.7C: Fix Award System (HIGH PRIORITY)
1. 🚨 Refactor award_processing_service to create pending_income records
2. 🚨 Remove direct wallet writes from award processing
3. 🚨 Use existing income approval workflow for awards
4. 🚨 Test with 120 existing awards

### Phase 1.7D: Final Validation
1. ✅ Run reconciliation tests
2. ✅ Verify all income flows through pending_income
3. ✅ Get architect review

---
**Analysis Created**: November 2, 2025  
**Verification Complete**: November 2, 2025  
**Status**: Ready for Phase 1.7A implementation  
**Critical Gaps**: Award system requires refactoring (Phase 1.7C)
