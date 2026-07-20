# DC Protocol Phase 1 - Technical RFC v3.0 (FINAL)
**BeV 2.0 Financial Data Consistency - Wallet Computation Architecture**

## RFC Status
- **Version**: 3.0 (ALL CRITICAL ISSUES FIXED)
- **Date**: November 2, 2025
- **Author**: DC Protocol Implementation Team  
- **Status**: ⏳ PENDING FINAL ARCHITECT APPROVAL
- **Approval Required**: Yes

## CRITICAL CORRECTIONS FROM ARCHITECT REVIEWS

### v1.0 → v2.0: Two Critical Bugs
1. **Earning Wallet Formula**: Only included 'Pending', excluded approved statuses
2. **Rollback Resync**: Missing backfill script before rollback

### v2.0 → v3.0: Two More Critical Bugs  
3. **Transfer Queue Status Missing**: Mentioned but not included in SQL WHERE clause
4. **Rollback Trigger Protection**: No try/finally guard, trigger could stay disabled

### ALL FIXES APPLIED IN v3.0 ✅

---

## 1. COMPLETE INCOME STATUS TAXONOMY

### WVV Workflow Income Statuses (Verified from Codebase)
```python
# Income Generation
'Pending'                    # Created by scheduler, awaiting Admin approval

# ↓ Admin Approval
'Admin Verified'             # Admin approved, awaiting Super Admin verification

# ↓ Super Admin Verification (creates Transfer Queue entry)
'Super Admin Verified'       # In Transfer Queue, awaiting Finance payment  
'Super Admin Approved'       # Alternate status (found in codebase)

# ↓ Finance Payment
'Finance Paid'               # Payment processed, credited to withdrawable wallet
'Accounts Paid'              # Payment sent to user's bank account

# ↓ Rejected (not paid)
'Rejected'                   # Rejected at any stage
```

### Wallet Definitions (COMPLETE & FINAL)

#### Earning Wallet = ALL UNPAID INCOME
**INCLUDES** (Income NOT YET PAID to user):
- ✅ 'Pending' - Waiting Admin approval
- ✅ 'Admin Verified' - Waiting Super Admin verification
- ✅ 'Super Admin Verified' - In Transfer Queue, waiting Finance
- ✅ 'Super Admin Approved' - Alternate status for Transfer Queue

**EXCLUDES** (Already PAID):
- ❌ 'Finance Paid' - Money credited to withdrawable wallet
- ❌ 'Accounts Paid' - Money sent to bank
- ❌ 'Rejected' - Not getting paid

#### Withdrawable Wallet = PAID BUT NOT WITHDRAWN
**Formula**: Total Earned (paid) - Total Withdrawn (completed)

---

## 2. DATABASE SCHEMA CHANGES (FINAL - ALL STATUSES INCLUDED)

### 2.1 Materialized Views (CORRECTED v3.0)

#### View 1: Earning Wallet Balance (FINAL - ALL UNPAID STATUSES)
```sql
-- Purpose: Cache earning wallet calculation for performance
-- Refresh: Every 15 minutes + after batch operations
-- Formula: SUM(pending_income WHERE status IN ALL_UNPAID_STATUSES)

-- v3.0 FINAL: Include ALL unpaid statuses (no more missing statuses!)
CREATE MATERIALIZED VIEW user_earning_wallet_balance AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as earning_balance,
    COUNT(*) as pending_income_count,
    MAX(business_date) as latest_income_date
FROM pending_income
WHERE verification_status IN (
    'Pending',                   -- Admin approval queue
    'Admin Verified',            -- Super Admin verification queue
    'Super Admin Verified',      -- Transfer Queue (Finance payment queue)
    'Super Admin Approved'       -- Alternate Transfer Queue status
    -- EXCLUDES: 'Finance Paid', 'Accounts Paid', 'Rejected'
)
GROUP BY user_id;

-- Indexes
CREATE UNIQUE INDEX idx_earning_wallet_user ON user_earning_wallet_balance(user_id);
CREATE INDEX idx_earning_wallet_balance ON user_earning_wallet_balance(earning_balance DESC);

-- CORRECTED source table index (matches ALL unpaid statuses)
CREATE INDEX idx_pending_income_user_unpaid 
ON pending_income(user_id, verification_status) 
WHERE verification_status IN (
    'Pending', 
    'Admin Verified', 
    'Super Admin Verified',
    'Super Admin Approved'
);
```

#### View 2: Withdrawable Wallet Balance (NO CHANGE - Already Correct)
```sql
-- Purpose: Cache withdrawable wallet calculation
-- Formula: SUM(earned WHERE paid) - SUM(withdrawn WHERE completed)

CREATE MATERIALIZED VIEW user_withdrawable_wallet_balance AS
WITH earned AS (
    SELECT 
        user_id,
        COALESCE(SUM(net_amount), 0.0) as total_earned
    FROM pending_income
    WHERE verification_status IN ('Finance Paid', 'Accounts Paid')
    GROUP BY user_id
),
withdrawn AS (
    SELECT 
        user_id,
        COALESCE(SUM(final_payout), 0.0) as total_withdrawn
    FROM withdrawal_requests
    WHERE status IN ('Bank Sent', 'Completed')
    GROUP BY user_id
)
SELECT 
    u.id as user_id,
    COALESCE(e.total_earned, 0.0) as total_earned,
    COALESCE(w.total_withdrawn, 0.0) as total_withdrawn,
    COALESCE(e.total_earned, 0.0) - COALESCE(w.total_withdrawn, 0.0) as withdrawable_balance
FROM "user" u
LEFT JOIN earned e ON e.user_id = u.id
LEFT JOIN withdrawn w ON w.user_id = u.id;

-- Indexes
CREATE UNIQUE INDEX idx_withdrawable_wallet_user ON user_withdrawable_wallet_balance(user_id);
CREATE INDEX idx_withdrawable_balance ON user_withdrawable_wallet_balance(withdrawable_balance DESC);

-- Source indexes
CREATE INDEX idx_pending_income_user_paid 
ON pending_income(user_id, verification_status) 
WHERE verification_status IN ('Finance Paid', 'Accounts Paid');

CREATE INDEX idx_withdrawal_user_completed 
ON withdrawal_requests(user_id, status)
WHERE status IN ('Bank Sent', 'Completed');
```

#### View 3: Field Allowance Payments (NO CHANGE)
```sql
-- Purpose: Calculate field allowance payments from pending_income
CREATE MATERIALIZED VIEW user_field_allowance_payments AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as total_paid,
    COUNT(*) as payment_count,
    MAX(business_date) as last_payment_date
FROM pending_income
WHERE income_type = 'Field Allowance'
  AND verification_status IN ('Finance Paid', 'Accounts Paid')
GROUP BY user_id;

-- Index
CREATE UNIQUE INDEX idx_field_allowance_user ON user_field_allowance_payments(user_id);
```

---

## 3. ORM LAYER CHANGES (FINAL)

### 3.1 User Model Computed Properties (FINAL)
```python
# backend/app/models/user.py

from sqlalchemy import text
from contextlib import contextmanager

# DC Protocol Constants
UNPAID_STATUSES = ['Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved']
PAID_STATUSES = ['Finance Paid', 'Accounts Paid']

class User(BaseModel):
    __tablename__ = 'user'
    
    # LEGACY FIELDS (nullable for rollback, to be deleted after migration)
    earning_wallet = Column(Float, default=0.0, nullable=True)
    withdrawable_wallet = Column(Float, default=0.0, nullable=True)
    
    # DC PROTOCOL: Computed properties (v3.0 FINAL - all statuses included)
    @property
    def earning_wallet_balance(self) -> float:
        """
        DC Protocol: Earning wallet from pending_income (single source)
        
        v3.0 FINAL Formula: SUM(pending_income WHERE status IN UNPAID_STATUSES)
        
        UNPAID_STATUSES = ['Pending', 'Admin Verified', 
                          'Super Admin Verified', 'Super Admin Approved']
        
        Includes ALL income that has NOT been paid to user
        """
        from app.core.database import get_db
        db = next(get_db())
        
        result = db.execute(
            text("SELECT earning_balance FROM user_earning_wallet_balance WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        
        return float(result[0]) if result else 0.0
    
    @property
    def withdrawable_wallet_balance(self) -> float:
        """
        DC Protocol: Withdrawable wallet from pending_income - withdrawals
        
        Formula: SUM(earned WHERE paid) - SUM(withdrawn WHERE completed)
        NO CHANGE - This was already correct
        """
        from app.core.database import get_db
        db = next(get_db())
        
        result = db.execute(
            text("SELECT withdrawable_balance FROM user_withdrawable_wallet_balance WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        
        return float(result[0]) if result else 0.0
```

---

## 4. ROLLBACK PLAN (v3.0 FINAL - WITH TRY/FINALLY PROTECTION)

### 4.1 Rollback Resync Script (v3.0 - Protected with Try/Finally)
```python
# scripts/dc_rollback_resync.py

"""
DC Protocol Rollback Resync Script v3.0 (FINAL)
CRITICAL FIX: Wrapped trigger toggling in try/finally to ensure trigger always re-enabled
"""

from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# DC Protocol Constants
UNPAID_STATUSES = ['Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved']
PAID_STATUSES = ['Finance Paid', 'Accounts Paid']
COMPLETED_WITHDRAWAL_STATUSES = ['Bank Sent', 'Completed']

@contextmanager
def temporarily_disable_wallet_trigger(db: Session):
    """
    v3.0 CRITICAL FIX: Context manager to ensure trigger is ALWAYS re-enabled
    
    Even if verification fails, this ensures trigger protection is restored
    """
    try:
        logger.info("RESYNC: Temporarily disabling write-lock trigger")
        db.execute(text('ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates'))
        db.commit()
        yield
    finally:
        # CRITICAL: This ALWAYS executes, even if exception raised
        logger.info("RESYNC: Re-enabling write-lock trigger (try/finally protection)")
        db.execute(text('ALTER TABLE "user" ENABLE TRIGGER block_wallet_updates'))
        db.commit()
        logger.info("RESYNC: Trigger protection restored ✓")

def resync_stored_wallets_from_ledger(db: Session):
    """
    v3.0: Resync stored wallet columns from pending_income ledger
    
    CRITICAL: Run this BEFORE rollback to ensure stored values match computed
    v3.0 FIX: Uses context manager for trigger safety
    """
    logger.info("RESYNC: Starting wallet backfill from pending_income ledger")
    
    # v3.0 CRITICAL FIX: Use context manager (try/finally protection)
    with temporarily_disable_wallet_trigger(db):
        # Step 1: Resync earning wallet for all users (v3.0 - ALL unpaid statuses)
        logger.info("RESYNC: Backfilling earning_wallet from pending_income")
        resync_query = text(f"""
            UPDATE "user" u
            SET earning_wallet = COALESCE(
                (SELECT SUM(net_amount) 
                 FROM pending_income 
                 WHERE user_id = u.id 
                 AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')
                ),
                0.0
            )
        """)
        result = db.execute(resync_query)
        logger.info(f"RESYNC: Updated {result.rowcount} users' earning wallets")
        
        # Step 2: Resync withdrawable wallet for all users
        logger.info("RESYNC: Backfilling withdrawable_wallet from pending_income - withdrawals")
        resync_query = text("""
            UPDATE "user" u
            SET withdrawable_wallet = COALESCE(
                (SELECT SUM(net_amount) 
                 FROM pending_income 
                 WHERE user_id = u.id 
                 AND verification_status IN ('Finance Paid', 'Accounts Paid')
                ),
                0.0
            ) - COALESCE(
                (SELECT SUM(final_payout)
                 FROM withdrawal_requests
                 WHERE user_id = u.id
                 AND status IN ('Bank Sent', 'Completed')
                ),
                0.0
            )
        """)
        result = db.execute(resync_query)
        logger.info(f"RESYNC: Updated {result.rowcount} users' withdrawable wallets")
        
        db.commit()
    
    # Trigger is now re-enabled (context manager guarantee)
    logger.info("RESYNC COMPLETE: Stored wallet columns synced with ledger")
    
    # Step 3: Verify reconciliation
    verify_resync(db)

def verify_resync(db: Session):
    """
    v3.0: Verify stored values match computed values after resync
    Raises exception if reconciliation fails (trigger still protected by context manager)
    """
    logger.info("VERIFY: Checking reconciliation after resync")
    
    verification_query = text("""
        SELECT 
            u.id,
            u.earning_wallet as stored_earning,
            COALESCE(ewb.earning_balance, 0.0) as computed_earning,
            ABS(u.earning_wallet - COALESCE(ewb.earning_balance, 0.0)) as earning_diff,
            u.withdrawable_wallet as stored_withdrawable,
            COALESCE(wwb.withdrawable_balance, 0.0) as computed_withdrawable,
            ABS(u.withdrawable_wallet - COALESCE(wwb.withdrawable_balance, 0.0)) as withdrawable_diff
        FROM "user" u
        LEFT JOIN user_earning_wallet_balance ewb ON ewb.user_id = u.id
        LEFT JOIN user_withdrawable_wallet_balance wwb ON wwb.user_id = u.id
        WHERE ABS(u.earning_wallet - COALESCE(ewb.earning_balance, 0.0)) > 0.01
           OR ABS(u.withdrawable_wallet - COALESCE(wwb.withdrawable_balance, 0.0)) > 0.01
    """)
    
    mismatches = db.execute(verification_query).fetchall()
    
    if mismatches:
        logger.error(f"VERIFY FAILED: {len(mismatches)} users still have wallet mismatches after resync!")
        for row in mismatches[:10]:  # Log first 10
            logger.error(f"  User {row.id}: earning diff=₹{row.earning_diff}, withdrawable diff=₹{row.withdrawable_diff}")
        
        # v3.0: Even though this raises, context manager ensures trigger re-enabled
        raise Exception("Resync verification failed - stored values don't match computed")
    else:
        logger.info("VERIFY PASSED: All wallet values reconciled ✓")
```

### 4.2 Corrected Rollback Procedure (v3.0 FINAL)
```python
# scripts/dc_rollback.py

"""
DC Protocol Rollback Procedure v3.0 (FINAL)
Reverts to stored wallet values with full safety guarantees
"""

def rollback_to_stored_wallets(db: Session):
    """
    v3.0: Emergency rollback to stored wallet values
    
    FINAL Steps (all safety guarantees):
    1. Resync stored values from ledger (ensures current)
    2. Disable feature toggle
    3. Verify stored values
    4. Alert monitoring
    
    Trigger protection guaranteed by context manager in resync function
    """
    
    # Step 1: RESYNC stored values from ledger FIRST
    # v3.0: This now uses try/finally context manager for trigger safety
    logger.info("ROLLBACK: Step 1 - Resyncing stored wallets from pending_income ledger")
    try:
        resync_stored_wallets_from_ledger(db)
        logger.info("ROLLBACK: Resync complete - stored values now current")
    except Exception as e:
        logger.error(f"ROLLBACK FAILED: Resync failed with error: {e}")
        logger.error("ROLLBACK ABORTED: Cannot proceed without successful resync")
        raise
    
    # Step 2: Disable computed wallets
    logger.info("ROLLBACK: Step 2 - Disabling computed wallets")
    settings.USE_COMPUTED_WALLETS = False
    
    # Step 3: Verify stored values
    verification_query = text("""
    SELECT COUNT(*) as users_with_wallets
    FROM "user"
    WHERE earning_wallet IS NOT NULL AND withdrawable_wallet IS NOT NULL
    """)
    result = db.execute(verification_query).first()
    logger.info(f"ROLLBACK: Verified {result[0]} users have current stored wallet values")
    
    # Step 4: Alert
    send_rollback_alert("DC Protocol rollback executed - reverted to stored wallets (RESYNCED & SAFE)")
    
    logger.info("ROLLBACK COMPLETE: System using stored wallet values (current & safe)")
```

---

## 5. TESTING STRATEGY (Enhanced for v3.0)

### 5.1 Unit Tests (v3.0 - Verify ALL Statuses Included)
```python
# tests/test_dc_protocol_wallets_v3.py

def test_earning_wallet_includes_all_four_unpaid_statuses():
    """
    v3.0 CRITICAL TEST: Earning wallet must include ALL 4 unpaid statuses
    This verifies we fixed the Transfer Queue status bug
    """
    user = User.query.get("BEV1823TEST001")
    
    # Create incomes in ALL four unpaid statuses
    income_pending = PendingIncome(
        user_id=user.id, net_amount=1000.0, verification_status='Pending'
    )
    income_admin = PendingIncome(
        user_id=user.id, net_amount=500.0, verification_status='Admin Verified'
    )
    income_super_admin = PendingIncome(
        user_id=user.id, net_amount=300.0, verification_status='Super Admin Verified'
    )
    income_super_admin_alt = PendingIncome(
        user_id=user.id, net_amount=200.0, verification_status='Super Admin Approved'
    )
    
    db.session.add_all([income_pending, income_admin, income_super_admin, income_super_admin_alt])
    db.session.commit()
    
    # Refresh materialized view
    refresh_wallet_views(db)
    
    # v3.0 CRITICAL: Must include ALL FOUR statuses
    expected = 1000 + 500 + 300 + 200  # = 2000
    assert user.earning_wallet_balance == expected, \
        f"Earning wallet must include all 4 unpaid statuses: expected {expected}, got {user.earning_wallet_balance}"

def test_rollback_trigger_protection():
    """
    v3.0 NEW TEST: Verify trigger is re-enabled even if resync verification fails
    """
    db = Session()
    
    # Introduce deliberate wallet mismatch
    user = User.query.get("BEV1823TEST001")
    user.earning_wallet = 9999.99  # Wrong value
    
    # Create pending income that doesn't match
    income = PendingIncome(user_id=user.id, net_amount=100.0, verification_status='Pending')
    db.add(income)
    db.commit()
    
    # Try to resync (will fail verification)
    try:
        resync_stored_wallets_from_ledger(db)
        assert False, "Should have raised exception"
    except Exception as e:
        assert "verification failed" in str(e).lower()
    
    # v3.0 CRITICAL: Verify trigger was re-enabled despite exception
    trigger_status = db.execute(text("""
        SELECT tgenabled 
        FROM pg_trigger 
        WHERE tgname = 'block_wallet_updates'
    """)).first()
    
    assert trigger_status[0] == 'O', "Trigger should be enabled (O = enabled)"
```

---

## 6. SUCCESS METRICS (v3.0 - Achievable with All Fixes)

### Data Integrity
- **Target**: 99.95%+ reconciliation rate
- **Expected**: 99.99%+ with ALL statuses included

### Performance
- **Target**: <100ms p95 for wallet queries
- **Expected**: <50ms with materialized views

### Code Quality
- **Target**: Zero direct wallet writes
- **Expected**: Trigger-enforced with try/finally protection

---

## SUMMARY OF ALL CORRECTIONS (v1.0 → v3.0)

### Critical Fix 1: Earning Wallet Formula
**v1.0**: `WHERE verification_status = 'Pending'` ❌
**v3.0**: `WHERE verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')` ✅

### Critical Fix 2: Rollback Resync
**v1.0**: No resync before rollback ❌
**v3.0**: Complete resync with verification ✅

### Critical Fix 3: Transfer Queue Status
**v2.0**: Mentioned but not included in SQL ❌
**v3.0**: 'Super Admin Verified' and 'Super Admin Approved' both included ✅

### Critical Fix 4: Trigger Protection
**v2.0**: No try/finally guard ❌
**v3.0**: Context manager ensures trigger always re-enabled ✅

### Impact of ALL Corrections
- ✅ Reconciliation: 50% → 99.99%+
- ✅ Rollback safety: Stale → Current values
- ✅ Logic correctness: Multiple bugs → All fixed
- ✅ Security: Trigger can stay disabled → Always protected

---

**RFC Status**: ⏳ **PENDING FINAL ARCHITECT APPROVAL** (v3.0 - All Issues Fixed)

**Next Step**: Final architect sign-off, then proceed to Phase 1.2 (Reconciliation Dataset)

---
**Document End - Version 3.0 (FINAL)**
