# DC Protocol Phase 1 - Technical RFC
**BeV 2.0 Financial Data Consistency - Wallet Computation Architecture**

## RFC Status
- **Version**: 1.0
- **Date**: November 2, 2025
- **Author**: DC Protocol Implementation Team
- **Status**: ⏳ PENDING ARCHITECT REVIEW
- **Approval Required**: Yes (Architect sign-off before implementation)

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

## 2. CURRENT STATE ANALYSIS

### DC Protocol Violations
```
VIOLATION V3.1: Income amounts duplicated
├─ pending_income.net_amount (SOURCE ✅)
├─ transaction.amount (DUPLICATE ❌)
└─ user.earning_wallet (DUPLICATE ❌)

VIOLATION V4.1: Withdrawal amounts duplicated
├─ withdrawal_requests.final_payout (SOURCE ✅)
├─ transaction.amount (DUPLICATE ❌)
└─ user.withdrawable_wallet (DUPLICATE ❌)

VIOLATION V9.2: Field allowance payments duplicated
├─ pending_income WHERE income_type='Field Allowance' (SOURCE ✅)
└─ field_allowance_eligibility.total_paid_to_date (DUPLICATE ❌)
```

### Current Wallet Update Flow (PROBLEMATIC)
```python
# Income Calculation (scheduler)
income = calculate_income(user)
pending_income = PendingIncome(net_amount=income)  # Record 1
db.session.add(pending_income)

# Income Approval (admin)
pending_income.verification_status = 'Admin Verified'
user.earning_wallet += pending_income.net_amount  # Record 2 (DUPLICATE!)

# Transaction Record (audit)
transaction = Transaction(amount=pending_income.net_amount)  # Record 3 (DUPLICATE!)

# Result: Same amount stored in 3 places!
```

### Data Consistency Risks
1. **Race Conditions**: Multiple processes updating wallets simultaneously
2. **Audit Trail Gaps**: Manual wallet adjustments bypass pending_income
3. **Reconciliation Failures**: Stored wallet ≠ sum(pending_income) due to bugs
4. **VGK Emergency Edits**: Direct wallet modifications without ledger entries

---

## 3. PROPOSED SOLUTION

### Architecture: Single Source of Truth
```
pending_income (SOURCE)
    ↓
Materialized Views (CACHE - refreshed every 15 min)
    ↓
ORM Computed Properties (API LAYER)
    ↓
Frontend Display
```

### Core Principle
**Database is King**: `pending_income` table is the ONLY authoritative source for all earnings. Wallets are COMPUTED, never stored.

---

## 4. DATABASE SCHEMA CHANGES

### 4.1 Materialized Views (Performance Layer)

#### View 1: Earning Wallet Balance
```sql
-- Purpose: Cache earning wallet calculation for performance
-- Refresh: Every 15 minutes + after batch operations
-- Formula: SUM(pending_income WHERE status='Pending')

CREATE MATERIALIZED VIEW user_earning_wallet_balance AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as earning_balance,
    COUNT(*) as pending_income_count,
    MAX(business_date) as latest_income_date
FROM pending_income
WHERE verification_status = 'Pending'
GROUP BY user_id;

-- Indexes for fast lookups
CREATE UNIQUE INDEX idx_earning_wallet_user ON user_earning_wallet_balance(user_id);
CREATE INDEX idx_earning_wallet_balance ON user_earning_wallet_balance(earning_balance DESC);
```

#### View 2: Withdrawable Wallet Balance
```sql
-- Purpose: Cache withdrawable wallet calculation
-- Refresh: Every 15 minutes + after withdrawals
-- Formula: SUM(earned) - SUM(withdrawn)

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
```

#### View 3: Field Allowance Payments (V9.2 Fix)
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
  AND verification_status IN ('Finance Paid', 'Accounts Paid')
GROUP BY user_id;

-- Index
CREATE UNIQUE INDEX idx_field_allowance_user ON user_field_allowance_payments(user_id);
```

### 4.2 Source Table Indexes (Performance Critical)
```sql
-- pending_income table (most critical for queries)
CREATE INDEX idx_pending_income_user_status 
ON pending_income(user_id, verification_status) 
WHERE verification_status IN ('Pending', 'Finance Paid', 'Accounts Paid');

CREATE INDEX idx_pending_income_type_status 
ON pending_income(income_type, verification_status);

CREATE INDEX idx_pending_income_business_date 
ON pending_income(business_date DESC);

-- withdrawal_requests table
CREATE INDEX idx_withdrawal_user_status 
ON withdrawal_requests(user_id, status)
WHERE status IN ('Bank Sent', 'Completed');

CREATE INDEX idx_withdrawal_status_date 
ON withdrawal_requests(status, created_at DESC);
```

### 4.3 Materialized View Refresh Strategy
```sql
-- Concurrent refresh to avoid locking
REFRESH MATERIALIZED VIEW CONCURRENTLY user_earning_wallet_balance;
REFRESH MATERIALIZED VIEW CONCURRENTLY user_withdrawable_wallet_balance;
REFRESH MATERIALIZED VIEW CONCURRENTLY user_field_allowance_payments;
```

**Refresh Schedule**:
- **Every 15 minutes**: Scheduled refresh (business hours)
- **Immediately after**: Income approval, withdrawal processing, field allowance payment
- **Manual trigger**: VGK operations, bulk operations

---

## 5. ORM LAYER CHANGES

### 5.1 User Model Computed Properties
```python
# backend/app/models/user.py

from sqlalchemy import select
from sqlalchemy.orm import column_property

class User(BaseModel):
    __tablename__ = 'user'
    
    # ... existing fields ...
    
    # LEGACY FIELDS (to be deleted after migration)
    earning_wallet = Column(Float, default=0.0, nullable=True)  # Will be removed
    withdrawable_wallet = Column(Float, default=0.0, nullable=True)  # Will be removed
    
    # DC PROTOCOL: Computed properties from materialized views
    @property
    def earning_wallet_balance(self) -> float:
        """
        DC Protocol: Earning wallet computed from pending_income (single source)
        
        Formula: SUM(pending_income.net_amount WHERE status='Pending')
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
        
        Formula: SUM(earned) - SUM(withdrawn)
        Where:
          - earned = pending_income WHERE status IN ('Finance Paid', 'Accounts Paid')
          - withdrawn = withdrawal_requests WHERE status IN ('Bank Sent', 'Completed')
        """
        from app.core.database import get_db
        db = next(get_db())
        
        result = db.execute(
            text("SELECT withdrawable_balance FROM user_withdrawable_wallet_balance WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        
        return float(result[0]) if result else 0.0
    
    @property
    def total_field_allowance_paid(self) -> float:
        """
        DC Protocol: Field allowance payments from pending_income (V9.2 fix)
        
        Replaces: field_allowance_eligibility.total_paid_to_date
        """
        from app.core.database import get_db
        db = next(get_db())
        
        result = db.execute(
            text("SELECT total_paid FROM user_field_allowance_payments WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        
        return float(result[0]) if result else 0.0
```

### 5.2 Transaction Model Changes
```python
# backend/app/models/transaction.py

class Transaction(BaseModel):
    __tablename__ = 'transaction'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    referred_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # LEGACY FIELD (to be deleted)
    amount = Column(Numeric(12, 2), nullable=True)  # Will be removed
    
    # DC PROTOCOL: Link to source records
    pending_income_id = Column(Integer, ForeignKey('pending_income.id'), nullable=True)
    withdrawal_id = Column(Integer, ForeignKey('withdrawal_requests.id'), nullable=True)
    
    transaction_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    
    # DC PROTOCOL: Computed amount from source
    @property
    def transaction_amount(self) -> float:
        """
        DC Protocol: Transaction amount from source record, not stored
        
        If income transaction → get from pending_income.net_amount
        If withdrawal transaction → get from withdrawal_requests.final_payout
        """
        if self.pending_income_id and self.pending_income:
            return float(self.pending_income.net_amount)
        elif self.withdrawal_id and self.withdrawal:
            return float(self.withdrawal.final_payout)
        return 0.0
    
    # Relationships
    pending_income = relationship("PendingIncome", foreign_keys=[pending_income_id])
    withdrawal = relationship("WithdrawalRequest", foreign_keys=[withdrawal_id])
```

---

## 6. SHADOW MODE IMPLEMENTATION

### 6.1 Shadow Mode Architecture
```
Request → Endpoint
    ↓
Dual-Read: stored_value AND computed_value
    ↓
Compare: |stored - computed| > threshold?
    ↓
Log Discrepancy → Monitoring Dashboard
    ↓
Return: stored_value (shadow mode = no impact)
```

### 6.2 Shadow Mode Endpoint Pattern
```python
# backend/app/api/v1/endpoints/users.py

from app.core.shadow_mode import ShadowModeMonitor

shadow_monitor = ShadowModeMonitor()

@router.get("/user/{user_id}/wallet")
async def get_user_wallet_balance(user_id: str, db: Session = Depends(get_db)):
    """
    Get user wallet balance with DC Protocol shadow mode monitoring
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # STORED VALUES (legacy)
    stored_earning = user.earning_wallet
    stored_withdrawable = user.withdrawable_wallet
    
    # COMPUTED VALUES (DC Protocol)
    computed_earning = user.earning_wallet_balance
    computed_withdrawable = user.withdrawable_wallet_balance
    
    # SHADOW MODE: Compare and log discrepancies
    shadow_monitor.compare_and_log(
        user_id=user_id,
        field="earning_wallet",
        stored=stored_earning,
        computed=computed_earning,
        threshold=0.01  # ₹0.01 tolerance
    )
    
    shadow_monitor.compare_and_log(
        user_id=user_id,
        field="withdrawable_wallet",
        stored=stored_withdrawable,
        computed=computed_withdrawable,
        threshold=0.01
    )
    
    # RETURN STORED VALUES (shadow mode - no behavioral change)
    return {
        "user_id": user_id,
        "earning_wallet": stored_earning,
        "withdrawable_wallet": stored_withdrawable,
        # Shadow metrics (internal monitoring only)
        "_shadow": {
            "computed_earning": computed_earning,
            "computed_withdrawable": computed_withdrawable,
            "earning_diff": abs(stored_earning - computed_earning),
            "withdrawable_diff": abs(stored_withdrawable - computed_withdrawable)
        }
    }
```

### 6.3 Shadow Mode Monitor Service
```python
# backend/app/core/shadow_mode.py

from datetime import datetime
import logging
from sqlalchemy import Column, String, Float, DateTime, Integer
from app.models.base import BaseModel

logger = logging.getLogger(__name__)

class ShadowModeLog(BaseModel):
    """Shadow mode discrepancy logging"""
    __tablename__ = 'shadow_mode_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), nullable=False)
    field_name = Column(String(50), nullable=False)  # 'earning_wallet', 'withdrawable_wallet'
    stored_value = Column(Float, nullable=False)
    computed_value = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    percentage_diff = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

class ShadowModeMonitor:
    """Monitor discrepancies between stored and computed values"""
    
    def compare_and_log(self, user_id: str, field: str, stored: float, computed: float, threshold: float = 0.01):
        """
        Compare stored vs computed value and log if discrepancy exceeds threshold
        
        Args:
            user_id: User ID
            field: Field name (e.g., 'earning_wallet')
            stored: Stored value (legacy)
            computed: Computed value (DC Protocol)
            threshold: Discrepancy threshold (default ₹0.01)
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
            
            # Alert if major discrepancy (>₹10 or >1%)
            if diff > 10 or pct_diff > 1.0:
                logger.error(
                    f"MAJOR DISCREPANCY: user={user_id} field={field} diff=₹{diff}"
                )
                # Send alert to monitoring system
                self._send_alert(user_id, field, stored, computed, diff)
    
    def _send_alert(self, user_id, field, stored, computed, diff):
        """Send alert for major discrepancies"""
        # TODO: Integrate with monitoring system (Slack, email, etc.)
        pass
```

### 6.4 Shadow Mode Dashboard Query
```sql
-- Daily reconciliation report
SELECT 
    DATE(timestamp) as report_date,
    field_name,
    COUNT(*) as discrepancy_count,
    AVG(difference) as avg_difference,
    MAX(difference) as max_difference,
    AVG(percentage_diff) as avg_percentage_diff
FROM shadow_mode_log
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp), field_name
ORDER BY report_date DESC, field_name;

-- Users with discrepancies
SELECT 
    user_id,
    field_name,
    stored_value,
    computed_value,
    difference,
    percentage_diff,
    timestamp
FROM shadow_mode_log
WHERE difference > 1.0  -- >₹1 discrepancy
ORDER BY difference DESC
LIMIT 100;
```

---

## 7. WRITE-LOCK IMPLEMENTATION

### 7.1 Database Trigger to Prevent Wallet Writes
```sql
-- Trigger function to block direct wallet modifications
CREATE OR REPLACE FUNCTION prevent_wallet_writes()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if earning_wallet or withdrawable_wallet changed
    IF (NEW.earning_wallet IS DISTINCT FROM OLD.earning_wallet) THEN
        RAISE EXCEPTION 'DC Protocol Violation: Direct writes to earning_wallet forbidden. Use pending_income ledger. User: %, Old: %, New: %', 
            NEW.id, OLD.earning_wallet, NEW.earning_wallet
        USING HINT = 'Create pending_income record instead of modifying wallet directly';
    END IF;
    
    IF (NEW.withdrawable_wallet IS DISTINCT FROM OLD.withdrawable_wallet) THEN
        RAISE EXCEPTION 'DC Protocol Violation: Direct writes to withdrawable_wallet forbidden. Wallets are computed. User: %, Old: %, New: %',
            NEW.id, OLD.withdrawable_wallet, NEW.withdrawable_wallet
        USING HINT = 'Wallets are automatically computed from pending_income and withdrawals';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to user table
CREATE TRIGGER block_wallet_updates
BEFORE UPDATE ON "user"
FOR EACH ROW
EXECUTE FUNCTION prevent_wallet_writes();

-- Disable trigger during migration/rollback if needed
-- ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates;
-- ALTER TABLE "user" ENABLE TRIGGER block_wallet_updates;
```

### 7.2 VGK Emergency Adjustment Enforcement
```python
# backend/app/api/v1/endpoints/emergency_wallet.py

@router.post("/rvz/emergency-wallet-adjustment")
async def vgk_emergency_wallet_adjustment(
    user_id: str,
    amount: float,
    reason: str,
    current_vgk: User = Depends(get_current_vgk_user),
    db: Session = Depends(get_db)
):
    """
    VGK Emergency Wallet Adjustment - DC PROTOCOL COMPLIANT
    
    Creates pending_income record instead of direct wallet modification
    """
    # DC PROTOCOL: Create pending_income record
    adjustment = PendingIncome(
        user_id=user_id,
        income_type='VGK Manual Adjustment',
        gross_amount=amount,
        gurudakshina_deduction=0.0,
        admin_deduction=0.0,
        tds_deduction=0.0,
        net_amount=amount,  # No deductions for manual adjustments
        business_date=get_indian_time(),
        verification_status='Accounts Paid',  # Immediately paid (VGK override)
        notes=f"VGK Emergency Adjustment by {current_vgk.id}: {reason}",
        accounts_paid_by_id=current_vgk.id,
        accounts_paid_at=get_indian_time()
    )
    
    db.add(adjustment)
    db.commit()
    
    # Audit log
    logger.info(f"VGK Emergency Adjustment: user={user_id} amount={amount} by={current_vgk.id}")
    
    # Refresh materialized view
    refresh_wallet_views(db)
    
    return {
        "success": True,
        "message": "Emergency adjustment recorded in pending_income ledger",
        "pending_income_id": adjustment.id,
        "new_balance": User.query.get(user_id).withdrawable_wallet_balance
    }
```

---

## 8. ROLLBACK PLAN

### 8.1 Feature Toggle System
```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # DC Protocol Feature Toggles
    USE_COMPUTED_WALLETS: bool = False  # Default: shadow mode only
    ENABLE_WALLET_WRITE_LOCKS: bool = False  # Default: allow writes
    SHADOW_MODE_LOGGING: bool = True  # Always log discrepancies

settings = Settings()
```

### 8.2 Rollback Procedure
```python
# scripts/dc_rollback.py

"""
DC Protocol Rollback Procedure
Reverts to stored wallet values if computed values cause issues
"""

def rollback_to_stored_wallets(db: Session):
    """
    Emergency rollback to stored wallet values
    
    Steps:
    1. Disable feature toggle
    2. Disable write-lock trigger
    3. Verify stored values unchanged
    4. Alert monitoring
    """
    
    # Step 1: Disable computed wallets
    logger.info("ROLLBACK: Disabling computed wallets")
    settings.USE_COMPUTED_WALLETS = False
    
    # Step 2: Disable write-lock trigger
    logger.info("ROLLBACK: Disabling wallet write locks")
    db.execute(text('ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates'))
    db.commit()
    
    # Step 3: Verify stored values
    verification_query = """
    SELECT COUNT(*) as users_with_wallets
    FROM "user"
    WHERE earning_wallet IS NOT NULL AND withdrawable_wallet IS NOT NULL
    """
    result = db.execute(text(verification_query)).first()
    logger.info(f"ROLLBACK: Verified {result[0]} users have stored wallet values")
    
    # Step 4: Alert
    send_rollback_alert("DC Protocol rollback executed - reverted to stored wallets")
    
    logger.info("ROLLBACK COMPLETE: System using stored wallet values")
```

### 8.3 Rollback Validation Checklist
- [ ] Feature toggle disabled (`USE_COMPUTED_WALLETS = False`)
- [ ] Write-lock trigger disabled
- [ ] Stored wallet values verified unchanged
- [ ] All API endpoints returning stored values
- [ ] Dashboard displays stored values
- [ ] Withdrawal processing using stored values
- [ ] No errors in application logs
- [ ] Monitoring alerts acknowledged

---

## 9. TESTING STRATEGY

### 9.1 Unit Tests
```python
# tests/test_dc_protocol_wallets.py

import pytest
from app.models.user import User
from app.models.transaction import PendingIncome

def test_earning_wallet_computation():
    """Test earning wallet computed from pending_income"""
    user = User.query.get("BEV1823TEST001")
    
    # Create pending income
    income1 = PendingIncome(user_id=user.id, net_amount=1000.0, verification_status='Pending')
    income2 = PendingIncome(user_id=user.id, net_amount=500.0, verification_status='Pending')
    db.session.add_all([income1, income2])
    db.session.commit()
    
    # Refresh materialized view
    refresh_wallet_views(db)
    
    # Assert computed = sum of pending income
    assert user.earning_wallet_balance == 1500.0

def test_withdrawable_wallet_computation():
    """Test withdrawable wallet = earned - withdrawn"""
    user = User.query.get("BEV1823TEST001")
    
    # Create paid income
    income = PendingIncome(user_id=user.id, net_amount=5000.0, verification_status='Finance Paid')
    db.session.add(income)
    
    # Create withdrawal
    withdrawal = WithdrawalRequest(user_id=user.id, final_payout=2000.0, status='Bank Sent')
    db.session.add(withdrawal)
    db.session.commit()
    
    # Refresh
    refresh_wallet_views(db)
    
    # Assert: 5000 earned - 2000 withdrawn = 3000
    assert user.withdrawable_wallet_balance == 3000.0

def test_wallet_write_lock():
    """Test that direct wallet writes are blocked"""
    user = User.query.get("BEV1823TEST001")
    
    # Try to modify wallet directly
    with pytest.raises(Exception, match="DC Protocol Violation"):
        user.earning_wallet = 9999.99
        db.session.commit()
```

### 9.2 Integration Tests
```python
# tests/test_dc_protocol_integration.py

def test_complete_income_flow():
    """Test end-to-end income → wallet → withdrawal flow"""
    user = User.query.get("BEV1823TEST001")
    
    # Step 1: Income calculation creates pending_income
    income = calculate_income(user)
    assert income.verification_status == 'Pending'
    
    # Step 2: Admin approval
    approve_income(income.id, admin_user)
    assert income.verification_status == 'Admin Verified'
    
    # Step 3: Super Admin verification
    verify_income(income.id, super_admin_user)
    
    # Step 4: Finance payment
    process_payment(income.id, finance_user)
    assert income.verification_status == 'Accounts Paid'
    
    # Step 5: Verify wallet updated (computed)
    refresh_wallet_views(db)
    assert user.withdrawable_wallet_balance >= income.net_amount
    
    # Step 6: User withdraws
    withdrawal = create_withdrawal_request(user.id, income.net_amount)
    process_withdrawal(withdrawal.id, finance_user)
    
    # Step 7: Verify wallet decreased
    refresh_wallet_views(db)
    assert user.withdrawable_wallet_balance == 0.0
```

### 9.3 Performance Tests
```python
# tests/test_dc_protocol_performance.py

def test_wallet_query_performance():
    """Test wallet balance query performance"""
    import time
    
    # Test 100 sequential queries
    start = time.time()
    for i in range(100):
        user = User.query.get(f"BEV1823{i:06d}")
        balance = user.earning_wallet_balance
    end = time.time()
    
    avg_time = (end - start) / 100
    assert avg_time < 0.1, f"Wallet query too slow: {avg_time:.3f}s (target: <0.1s)"

def test_bulk_reconciliation_performance():
    """Test reconciliation performance on all users"""
    import time
    
    start = time.time()
    results = reconcile_all_wallets()
    end = time.time()
    
    total_time = end - start
    assert total_time < 60, f"Reconciliation too slow: {total_time:.1f}s (target: <60s for all users)"
```

---

## 10. MIGRATION TIMELINE

### Days 1-3: RFC & Design ✓ (THIS DOCUMENT)
- [x] Database schema design
- [x] Shadow mode architecture
- [x] Rollback plan
- [ ] **ARCHITECT REVIEW REQUIRED**

### Days 4-6: Reconciliation Dataset
- [ ] Build reconciliation script
- [ ] Run on all users
- [ ] Identify discrepancies
- [ ] Executive review of outliers

### Days 7-9: Database Implementation
- [ ] Create materialized views
- [ ] Create indexes
- [ ] Add ORM computed properties
- [ ] Verify query performance

### Days 10-14: Shadow Mode
- [ ] Deploy dual-read endpoints
- [ ] Monitor discrepancies
- [ ] Daily reconciliation reports
- [ ] **ARCHITECT MIDPOINT REVIEW**

### Days 15-16: Write Locks
- [ ] Deploy database triggers
- [ ] Remove wallet write operations
- [ ] Verify VGK adjustments compliant
- [ ] Test rollback procedure

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

## 11. RISK ASSESSMENT

### Critical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Reconciliation < 99.95% | Medium | High | Extended shadow mode, manual review of outliers |
| Performance degradation | Low | High | Materialized views, caching, indexes |
| Rollback complexity | Low | Critical | Feature toggle, retain legacy columns |
| VGK emergency breaks | Medium | Medium | DC-compliant VGK adjustment endpoint |

### Rollback Triggers
- Reconciliation rate < 99.95%
- Query performance > 100ms p95
- Production errors > 5 per hour
- Executive decision

---

## 12. APPROVAL CHECKLIST

### Architect Review
- [ ] SQL materialized view definitions approved
- [ ] Shadow mode architecture approved
- [ ] Rollback plan validated
- [ ] Performance strategy approved
- [ ] Testing approach sufficient

### Executive Approval
- [ ] Migration timeline approved
- [ ] Rollback triggers defined
- [ ] Success criteria agreed
- [ ] Budget allocated (if needed)

---

## 13. SUCCESS METRICS

### Data Integrity
- **Target**: 99.95%+ reconciliation rate
- **Current**: TBD (measured in Phase 1.2)

### Performance
- **Target**: <100ms p95 for wallet queries
- **Baseline**: TBD (measured in Phase 1.3)

### Code Quality
- **Target**: Zero direct wallet writes
- **Current**: Multiple wallet write operations (to be removed)

### Reliability
- **Target**: Zero production incidents
- **Rollback**: Tested and validated

---

## APPENDIX A: SQL Migration Scripts

### Create Materialized Views
```sql
-- See Section 4.1 for full definitions
```

### Create Indexes
```sql
-- See Section 4.2 for full definitions
```

### Create Triggers
```sql
-- See Section 7.1 for full definitions
```

---

## APPENDIX B: Monitoring Queries

### Shadow Mode Reconciliation
```sql
-- See Section 6.4 for full queries
```

---

**RFC Status**: ⏳ **PENDING ARCHITECT REVIEW**

**Next Step**: Architect sign-off on this RFC before implementation begins.

---
**Document End**
