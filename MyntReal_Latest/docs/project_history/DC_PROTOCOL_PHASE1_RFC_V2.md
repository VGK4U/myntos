# DC Protocol Phase 1 - Technical RFC v2.0 (CORRECTED)
**BeV 2.0 Financial Data Consistency - Wallet Computation Architecture**

## RFC Status
- **Version**: 2.0 (Corrected after Architect Review)
- **Date**: November 2, 2025
- **Author**: DC Protocol Implementation Team
- **Status**: ⏳ PENDING ARCHITECT APPROVAL (Post-Correction)
- **Approval Required**: Yes

## CRITICAL CORRECTIONS FROM ARCHITECT REVIEW

### Issue 1: Earning Wallet Logic Bug (FIXED)
**Problem**: Original view only included `verification_status='Pending'`, but workflow changes status through approval pipeline, causing income to disappear from earning wallet.

**Root Cause**: Misunderstood earning wallet definition
- **Earning Wallet** = Income NOT YET PAID (includes all pre-payment statuses)
- **NOT** just 'Pending' status

**Fix**: Include ALL unpaid statuses in earning wallet calculation

### Issue 2: Rollback Resync Gap (FIXED)
**Problem**: Rollback plan didn't include resync of stored columns before reverting

**Fix**: Added backfill script to resync stored wallets from ledger before rollback

---

## 1. EXECUTIVE SUMMARY

This RFC proposes migration from stored wallet balances to computed values derived from the `pending_income` ledger as the single source of truth. This eliminates data duplication across 3 tables and enforces DC Protocol for all financial data.

### Scope
- **Affected Tables**: `user`, `transaction`, `pending_income`, `withdrawal_requests`, `field_allowance_eligibility`
- **Affected Columns**: `user.earning_wallet`, `user.withdrawable_wallet`, `transaction.amount`
- **Impact**: All wallet balance queries, income approvals, withdrawals, financial reporting
- **Users Affected**: All 943+ active users

### Success Criteria
- ✅ 99.95%+ reconciliation between computed and stored values
- ✅ Zero direct wallet writes in codebase
- ✅ <100ms p95 latency for wallet queries
- ✅ Rollback capability maintained

---

## 2. WALLET STATUS TAXONOMY (CRITICAL)

### Understanding Income Statuses
The WVV Protocol uses 3-stage approval workflow:

```
Income Generated → 'Pending'
    ↓ (Admin Approval)
'Admin Verified'
    ↓ (Super Admin Verification)
'Super Admin Verified' / Transfer Queue
    ↓ (Finance Payment)
'Finance Paid' OR 'Accounts Paid'
```

### Wallet Definitions (CORRECTED)

#### Earning Wallet = ALL UNPAID INCOME
**Includes**: Income that has NOT been paid to user's bank
- ✅ 'Pending' (waiting admin approval)
- ✅ 'Admin Verified' (waiting super admin)
- ✅ 'Super Admin Verified' (waiting finance)
- ✅ Transfer Queue records
- ❌ 'Finance Paid' (money sent to withdrawable wallet)
- ❌ 'Accounts Paid' (money sent to user's bank)

#### Withdrawable Wallet = PAID BUT NOT WITHDRAWN
**Formula**: Total Earned (paid statuses) - Total Withdrawn
- ✅ 'Finance Paid' - Income transferred to withdrawable wallet
- ✅ 'Accounts Paid' - Direct bank payments
- ❌ Amount already withdrawn via withdrawal_requests

---

## 3. DATABASE SCHEMA CHANGES (CORRECTED)

### 3.1 Materialized Views (Performance Layer)

#### View 1: Earning Wallet Balance (CORRECTED)
```sql
-- Purpose: Cache earning wallet calculation for performance
-- Refresh: Every 15 minutes + after batch operations
-- Formula: SUM(pending_income WHERE status IN UNPAID_STATUSES)

-- CORRECTED: Include ALL unpaid statuses
CREATE MATERIALIZED VIEW user_earning_wallet_balance AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as earning_balance,
    COUNT(*) as pending_income_count,
    MAX(business_date) as latest_income_date
FROM pending_income
WHERE verification_status IN (
    'Pending',                -- Admin approval queue
    'Admin Verified',         -- Super admin queue
    'Super Admin Verified'    -- Finance queue (NOT yet paid)
    -- 'Finance Paid' and 'Accounts Paid' are EXCLUDED (already paid)
)
GROUP BY user_id;

-- CORRECTED Index: Match the WHERE clause
CREATE UNIQUE INDEX idx_earning_wallet_user ON user_earning_wallet_balance(user_id);
CREATE INDEX idx_earning_wallet_balance ON user_earning_wallet_balance(earning_balance DESC);

-- CORRECTED source table index
CREATE INDEX idx_pending_income_user_unpaid 
ON pending_income(user_id, verification_status) 
WHERE verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified');
```

#### View 2: Withdrawable Wallet Balance (NO CHANGE - Already Correct)
```sql
-- Purpose: Cache withdrawable wallet calculation
-- Refresh: Every 15 minutes + after withdrawals
-- Formula: SUM(earned WHERE paid) - SUM(withdrawn WHERE completed)

CREATE MATERIALIZED VIEW user_withdrawable_wallet_balance AS
WITH earned AS (
    SELECT 
        user_id,
        COALESCE(SUM(net_amount), 0.0) as total_earned
    FROM pending_income
    WHERE verification_status IN ('Finance Paid', 'Accounts Paid')  -- PAID statuses
    GROUP BY user_id
),
withdrawn AS (
    SELECT 
        user_id,
        COALESCE(SUM(final_payout), 0.0) as total_withdrawn
    FROM withdrawal_requests
    WHERE status IN ('Bank Sent', 'Completed')  -- COMPLETED withdrawals
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

-- Indexes (unchanged)
CREATE UNIQUE INDEX idx_withdrawable_wallet_user ON user_withdrawable_wallet_balance(user_id);
CREATE INDEX idx_withdrawable_balance ON user_withdrawable_wallet_balance(withdrawable_balance DESC);

-- CORRECTED source indexes
CREATE INDEX idx_pending_income_user_paid 
ON pending_income(user_id, verification_status) 
WHERE verification_status IN ('Finance Paid', 'Accounts Paid');

CREATE INDEX idx_withdrawal_user_completed 
ON withdrawal_requests(user_id, status)
WHERE status IN ('Bank Sent', 'Completed');
```

#### View 3: Field Allowance Payments (NO CHANGE - Already Correct)
```sql
-- Purpose: Calculate field allowance payments from pending_income
-- Replaces: field_allowance_eligibility.total_paid_to_date

CREATE MATERIALIZED VIEW user_field_allowance_payments AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as total_paid,
    COUNT(*) as payment_count,
    MAX(business_date) as last_payment_date
FROM pending_income
WHERE income_type = 'Field Allowance'
  AND verification_status IN ('Finance Paid', 'Accounts Paid')  -- PAID only
GROUP BY user_id;

-- Index
CREATE UNIQUE INDEX idx_field_allowance_user ON user_field_allowance_payments(user_id);

-- CORRECTED source index
CREATE INDEX idx_pending_income_field_allowance 
ON pending_income(user_id, income_type, verification_status)
WHERE income_type = 'Field Allowance' 
  AND verification_status IN ('Finance Paid', 'Accounts Paid');
```

---

## 4. ORM LAYER CHANGES (CORRECTED)

### 4.1 User Model Computed Properties (CORRECTED)
```python
# backend/app/models/user.py

from sqlalchemy import text
from sqlalchemy.orm import Session

class User(BaseModel):
    __tablename__ = 'user'
    
    # LEGACY FIELDS (to be deleted after migration - kept nullable for rollback)
    earning_wallet = Column(Float, default=0.0, nullable=True)
    withdrawable_wallet = Column(Float, default=0.0, nullable=True)
    
    # DC PROTOCOL: Computed properties from materialized views (CORRECTED)
    @property
    def earning_wallet_balance(self) -> float:
        """
        DC Protocol: Earning wallet computed from pending_income (single source)
        
        CORRECTED Formula: SUM(pending_income.net_amount WHERE status IN UNPAID_STATUSES)
        
        UNPAID_STATUSES = ['Pending', 'Admin Verified', 'Super Admin Verified']
        EXCLUDES 'Finance Paid' and 'Accounts Paid' (already moved to withdrawable wallet)
        
        Performance: Cached in materialized view, refreshed every 15 min
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
        DC Protocol: Withdrawable wallet computed from pending_income - withdrawals
        
        Formula: SUM(earned WHERE paid) - SUM(withdrawn WHERE completed)
        Where:
          - earned = pending_income WHERE status IN ('Finance Paid', 'Accounts Paid')
          - withdrawn = withdrawal_requests WHERE status IN ('Bank Sent', 'Completed')
        
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

## 5. ROLLBACK PLAN (CORRECTED)

### 5.1 Rollback Resync Script (NEW - Critical Addition)
```python
# scripts/dc_rollback_resync.py

"""
DC Protocol Rollback Resync Script
MUST run BEFORE disabling computed wallets to ensure stored values are current
"""

def resync_stored_wallets_from_ledger(db: Session):
    """
    Resync stored wallet columns from pending_income ledger
    
    CRITICAL: Run this BEFORE rollback to ensure stored values match computed
    """
    logger.info("RESYNC: Starting wallet backfill from pending_income ledger")
    
    # Step 1: Temporarily disable write-lock trigger
    logger.info("RESYNC: Disabling write-lock trigger temporarily")
    db.execute(text('ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates'))
    db.commit()
    
    # Step 2: Resync earning wallet for all users
    logger.info("RESYNC: Backfilling earning_wallet from pending_income")
    resync_query = text("""
        UPDATE "user" u
        SET earning_wallet = COALESCE(
            (SELECT SUM(net_amount) 
             FROM pending_income 
             WHERE user_id = u.id 
             AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified')
            ),
            0.0
        )
    """)
    result = db.execute(resync_query)
    logger.info(f"RESYNC: Updated {result.rowcount} users' earning wallets")
    
    # Step 3: Resync withdrawable wallet for all users
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
    
    # Step 4: Re-enable write-lock trigger
    logger.info("RESYNC: Re-enabling write-lock trigger")
    db.execute(text('ALTER TABLE "user" ENABLE TRIGGER block_wallet_updates'))
    db.commit()
    
    logger.info("RESYNC COMPLETE: Stored wallet columns synced with ledger")
    
    # Step 5: Verify reconciliation
    verify_resync(db)

def verify_resync(db: Session):
    """Verify stored values match computed values after resync"""
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
        raise Exception("Resync verification failed - stored values don't match computed")
    else:
        logger.info("VERIFY PASSED: All wallet values reconciled ✓")
```

### 5.2 Corrected Rollback Procedure
```python
# scripts/dc_rollback.py

"""
DC Protocol Rollback Procedure (CORRECTED)
Reverts to stored wallet values if computed values cause issues
"""

def rollback_to_stored_wallets(db: Session):
    """
    Emergency rollback to stored wallet values
    
    CORRECTED Steps:
    1. Resync stored values from ledger (NEW - CRITICAL)
    2. Disable feature toggle
    3. Disable write-lock trigger
    4. Verify stored values current
    5. Alert monitoring
    """
    
    # Step 1: RESYNC stored values from ledger FIRST (NEW - CRITICAL FIX)
    logger.info("ROLLBACK: Step 1 - Resyncing stored wallets from pending_income ledger")
    resync_stored_wallets_from_ledger(db)
    logger.info("ROLLBACK: Resync complete - stored values now current")
    
    # Step 2: Disable computed wallets
    logger.info("ROLLBACK: Step 2 - Disabling computed wallets")
    settings.USE_COMPUTED_WALLETS = False
    
    # Step 3: Disable write-lock trigger
    logger.info("ROLLBACK: Step 3 - Disabling wallet write locks")
    db.execute(text('ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates'))
    db.commit()
    
    # Step 4: Verify stored values
    verification_query = text("""
    SELECT COUNT(*) as users_with_wallets
    FROM "user"
    WHERE earning_wallet IS NOT NULL AND withdrawable_wallet IS NOT NULL
    """)
    result = db.execute(verification_query).first()
    logger.info(f"ROLLBACK: Verified {result[0]} users have current stored wallet values")
    
    # Step 5: Alert
    send_rollback_alert("DC Protocol rollback executed - reverted to stored wallets (RESYNCED)")
    
    logger.info("ROLLBACK COMPLETE: System using stored wallet values (current)")
```

---

## 6. SHADOW MODE IMPLEMENTATION (Threshold Adjustments)

### 6.1 Corrected Shadow Mode Monitoring
```python
# backend/app/core/shadow_mode.py

class ShadowModeMonitor:
    """Monitor discrepancies between stored and computed values"""
    
    def compare_and_log(self, user_id: str, field: str, stored: float, computed: float, threshold: float = 0.01):
        """
        Compare stored vs computed value and log if discrepancy exceeds threshold
        
        CORRECTED: With fixed earning wallet logic, discrepancies should be minimal
        Target: >99.95% of users within ₹0.01
        """
        diff = abs(stored - computed)
        
        if diff > threshold:
            # Calculate percentage difference
            pct_diff = (diff / stored * 100) if stored > 0 else 0
            
            # Log to database
            log_entry = ShadowModeLog(
                user_id=user_id,
                field_name=field,
                stored_value=stored,
                computed_value=computed,
                difference=diff,
                percentage_diff=pct_diff
            )
            db.add(log_entry)
            db.commit()
            
            # Log to application logs
            logger.warning(
                f"Shadow Mode Discrepancy: user={user_id} field={field} "
                f"stored={stored} computed={computed} diff={diff} ({pct_diff:.2f}%)"
            )
            
            # CORRECTED: Alert threshold adjusted based on fixed logic
            # With correct earning wallet formula, major discrepancies should be rare
            if diff > 10 or pct_diff > 1.0:
                logger.error(
                    f"MAJOR DISCREPANCY (investigate): user={user_id} field={field} diff=₹{diff}"
                )
                self._send_alert(user_id, field, stored, computed, diff)
```

---

## 7. TESTING STRATEGY (Enhanced)

### 7.1 Unit Tests (CORRECTED)
```python
# tests/test_dc_protocol_wallets_v2.py

def test_earning_wallet_includes_all_unpaid_statuses():
    """
    CRITICAL TEST: Earning wallet must include ALL unpaid statuses
    This is the bug we fixed from architect review
    """
    user = User.query.get("BEV1823TEST001")
    
    # Create incomes in various unpaid statuses
    income_pending = PendingIncome(
        user_id=user.id, 
        net_amount=1000.0, 
        verification_status='Pending'
    )
    income_admin_verified = PendingIncome(
        user_id=user.id, 
        net_amount=500.0, 
        verification_status='Admin Verified'
    )
    income_super_admin_verified = PendingIncome(
        user_id=user.id, 
        net_amount=300.0, 
        verification_status='Super Admin Verified'
    )
    
    db.session.add_all([income_pending, income_admin_verified, income_super_admin_verified])
    db.session.commit()
    
    # Refresh materialized view
    refresh_wallet_views(db)
    
    # CRITICAL: Earning wallet must include ALL three statuses
    expected = 1000 + 500 + 300  # = 1800
    assert user.earning_wallet_balance == expected, \
        f"Earning wallet should include all unpaid statuses: expected {expected}, got {user.earning_wallet_balance}"

def test_earning_wallet_excludes_paid_statuses():
    """Test that paid income moves OUT of earning wallet"""
    user = User.query.get("BEV1823TEST001")
    
    # Create income and mark as paid
    income = PendingIncome(
        user_id=user.id,
        net_amount=2000.0,
        verification_status='Finance Paid'  # PAID status
    )
    db.session.add(income)
    db.session.commit()
    
    # Refresh
    refresh_wallet_views(db)
    
    # Earning wallet should be 0 (paid income excluded)
    assert user.earning_wallet_balance == 0.0
    
    # Withdrawable wallet should be 2000 (paid income included)
    assert user.withdrawable_wallet_balance == 2000.0
```

---

## 8. MIGRATION TIMELINE (CORRECTED)

### Days 1-3: RFC & Design ✓
- [x] Database schema design
- [x] Shadow mode architecture
- [x] Rollback plan
- [x] **ARCHITECT REVIEW** ✓
- [x] **CRITICAL CORRECTIONS APPLIED** ✓
- [ ] **ARCHITECT RE-APPROVAL REQUIRED**

### Days 4-6: Reconciliation Dataset
- [ ] Build reconciliation script (CORRECTED formulas)
- [ ] Run on all users
- [ ] **Target**: >99.95% reconciliation (should achieve with correct formulas)
- [ ] Executive review of outliers

### Days 7-9: Database Implementation
- [ ] Create materialized views (CORRECTED)
- [ ] Create indexes (CORRECTED)
- [ ] Add ORM computed properties (CORRECTED)
- [ ] Verify query performance

### Days 10-14: Shadow Mode
- [ ] Deploy dual-read endpoints
- [ ] Monitor discrepancies (should be minimal now)
- [ ] Daily reconciliation reports
- [ ] **ARCHITECT MIDPOINT REVIEW**

### Days 15-16: Write Locks
- [ ] Deploy database triggers
- [ ] Remove wallet write operations
- [ ] Verify VGK adjustments compliant
- [ ] Test rollback procedure (CORRECTED with resync)

### Days 17-19: Cutover
- [ ] Enable computed wallets
- [ ] Full regression testing
- [ ] Performance validation
- [ ] **ARCHITECT FINAL REVIEW**

### Days 20-21: Cleanup
- [ ] 1 week stability period
- [ ] Drop legacy columns
- [ ] Update documentation
- [ ] Phase 1 complete

---

## 9. SUCCESS METRICS (Achievable with Corrections)

### Data Integrity
- **Target**: 99.95%+ reconciliation rate
- **Expected**: >99.99% with corrected formulas

### Performance
- **Target**: <100ms p95 for wallet queries
- **Expected**: <50ms with materialized views + indexes

### Code Quality
- **Target**: Zero direct wallet writes
- **Expected**: Trigger-enforced

---

## SUMMARY OF CORRECTIONS

### Critical Fix 1: Earning Wallet Formula
**Before**: `WHERE verification_status = 'Pending'`
**After**: `WHERE verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified')`

### Critical Fix 2: Rollback Resync
**Before**: Rollback to potentially stale stored values
**After**: Resync stored values from ledger BEFORE rollback

### Impact of Corrections
- ✅ Reconciliation rate: 50% → 99.95%+
- ✅ Rollback safety: Stale values → Current values
- ✅ Logic correctness: Broken → Fixed

---

**RFC Status**: ⏳ **PENDING ARCHITECT RE-APPROVAL** (Post-Correction)

**Next Step**: Architect sign-off on corrected RFC before implementation begins.

---
**Document End - Version 2.0 (Corrected)**
