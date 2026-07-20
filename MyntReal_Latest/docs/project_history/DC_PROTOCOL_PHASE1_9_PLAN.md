# DC Protocol Phase 1.9: Delete Duplicate Wallet Columns - PLAN

**Date:** November 3, 2025  
**Phase:** 1.9 - Final cleanup of Phase 1 (Delete Duplicate Columns)  
**Objective:** Remove deprecated `earning_wallet` and `withdrawable_wallet` from user table

---

## Current State Analysis

### User Table Wallet Columns
```sql
earning_wallet           | double precision | NOT NULL | DEFAULT 0.0
withdrawable_wallet      | double precision | NOT NULL | DEFAULT 0.0
upgrade_wallet_balance   | double precision | NOT NULL | (no default)
```

### Remaining Write Paths
1. ✅ **wallet_sync_service.py** - Real-time KYC approval transfers (LEGITIMATE - MUST PRESERVE)
2. ✅ **withdrawal.py** - NO LONGER WRITES (fixed in Phase 1.7)
3. ✅ **admin_data_access.py** - Manual VGK adjustments (CHECK STATUS)

### Materialized Views (Source of Truth)
1. ✅ **user_earning_wallet_balance** - Computed from pending_income (Pending statuses)
2. ✅ **user_withdrawable_wallet_balance** - Computed from paid income minus withdrawals

---

## Phase 1.9 Strategy

### ⚠️ CRITICAL DECISION: wallet_sync_service.py

The wallet_sync_service handles **KYC-gated transfers**:
- When: Daily at 3 AM IST + Real-time on KYC/Bank approval
- Current: Moves `earning_wallet` → `withdrawable_wallet`
- DC Protocol Goal: Eliminate direct wallet writes

**Two Options:**

#### Option A: Keep wallet_sync_service AS-IS (Temporary Exemption)
- ✅ Pros: Zero risk, maintains current functionality
- ❌ Cons: Violates DC Protocol (direct wallet writes remain)
- **Status:** NOT RECOMMENDED

#### Option B: Refactor wallet_sync to use pending_income status changes
- ✅ Pros: Full DC Protocol compliance
- ✅ Pros: Materialized views automatically update
- ⚠️ Cons: Requires redesign of KYC approval flow
- **Status:** RECOMMENDED (aligned with DC Protocol)

---

## Implementation Steps

### Step 1: Audit All Wallet Write Paths
- [x] wallet_sync_service.py - IDENTIFIED
- [ ] admin_data_access.py - CHECK VGK manual adjustments
- [ ] Any other direct wallet writes

### Step 2: Refactor wallet_sync_service (Option B)
**Current Flow:**
```python
# Direct wallet write (VIOLATES DC PROTOCOL)
user.withdrawable_wallet += amount
user.earning_wallet = 0.0
```

**DC Protocol Flow:**
```python
# Update pending_income verification statuses
db.execute(text("""
    UPDATE pending_income
    SET verification_status = 'Accounts Paid',
        accounts_paid_at = NOW(),
        accounts_paid_by_id = 'SYSTEM'
    WHERE user_id = :user_id
    AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified')
    AND net_amount >= :minimum_amount
"""))

# Materialized view automatically updates:
# - earning_wallet decreases (less Pending income)
# - withdrawable_wallet increases (more Accounts Paid income)
```

### Step 3: Mark Columns as Nullable (Deprecated)
```sql
ALTER TABLE "user" ALTER COLUMN earning_wallet DROP NOT NULL;
ALTER TABLE "user" ALTER COLUMN withdrawable_wallet DROP NOT NULL;

COMMENT ON COLUMN "user".earning_wallet IS 'DEPRECATED: Use user_earning_wallet_balance materialized view';
COMMENT ON COLUMN "user".withdrawable_wallet IS 'DEPRECATED: Use user_withdrawable_wallet_balance materialized view';
```

### Step 4: Update User Model (ORM)
```python
# backend/app/models/user.py
class User(BaseModel):
    # DEPRECATED columns (keep for backward compatibility)
    earning_wallet = Column(Float, nullable=True)  # DEPRECATED
    withdrawable_wallet = Column(Float, nullable=True)  # DEPRECATED
    
    # DC Protocol computed properties (Source of Truth)
    @property
    def earning_wallet_balance(self):
        """Computed from pending_income (DC Protocol compliant)"""
        from app.services.wallet_balance_service import WalletBalanceService
        return WalletBalanceService.get_earning_wallet(self.id)
    
    @property
    def withdrawable_wallet_balance(self):
        """Computed from pending_income - withdrawals (DC Protocol compliant)"""
        from app.services.wallet_balance_service import WalletBalanceService
        return WalletBalanceService.get_withdrawable_wallet(self.id)
```

### Step 5: Update All API Endpoints
Replace ALL references to:
- `user.earning_wallet` → `user.earning_wallet_balance` (computed property)
- `user.withdrawable_wallet` → `user.withdrawable_wallet_balance` (computed property)

### Step 6: Testing & Validation
1. ✅ Verify wallet_sync creates pending_income status changes
2. ✅ Verify materialized views update correctly
3. ✅ Verify API endpoints return correct balances
4. ✅ Run reconciliation: computed vs stored values
5. ✅ Test KYC approval flow end-to-end

### Step 7: Column Deletion (Future - After Stability Period)
```sql
-- ONLY after 2 weeks stability + 100% reconciliation
ALTER TABLE "user" DROP COLUMN earning_wallet;
ALTER TABLE "user" DROP COLUMN withdrawable_wallet;
```

---

## Risks & Mitigation

### Risk 1: wallet_sync Refactor Breaks KYC Flow
**Mitigation:**
- Implement feature toggle: `USE_DC_PROTOCOL_WALLET_SYNC`
- Run shadow mode for 1 week
- Rollback plan: Revert to direct wallet writes

### Risk 2: VGK Manual Adjustments
**Status:** MUST INVESTIGATE admin_data_access.py
**Mitigation:** All VGK adjustments MUST create pending_income records

### Risk 3: Materialized View Refresh Lag
**Mitigation:**
- REFRESH MATERIALIZED VIEW immediately after wallet_sync
- Add monitoring for view staleness

---

## Success Criteria

### Phase 1.9 Complete When:
- ✅ Zero direct writes to earning_wallet/withdrawable_wallet columns
- ✅ wallet_sync_service uses pending_income status changes
- ✅ All API endpoints use computed properties
- ✅ Columns marked as nullable (deprecated)
- ✅ 100% reconciliation: computed = stored (within ₹0.01)
- ✅ 1 week stability period with zero incidents

### Future Phase (2.0):
- ✅ DROP deprecated columns after 2 weeks stability
- ✅ Move to Phase 2: User & Team Data deduplication

---

## Next Steps

1. **Investigate admin_data_access.py** - Check VGK manual adjustment logic
2. **Design wallet_sync refactor** - pending_income status change flow
3. **Implement feature toggle** - DC Protocol wallet sync mode
4. **Run shadow mode** - Validate new flow vs old flow
5. **Mark columns nullable** - Deprecation phase
6. **Full system testing** - End-to-end validation

---

**Status:** PLAN APPROVED - READY FOR IMPLEMENTATION  
**Architect Review:** REQUIRED before refactoring wallet_sync_service
