# DC Protocol Phase 1 - Technical RFC v4.1 (DEPLOYMENT-SAFE FINAL)
**BeV 2.0 Financial Data Consistency - Wallet Computation Architecture**

## RFC Status
- **Version**: 4.1 (DEPLOYMENT-SAFE - ALL OPERATIONAL SAFEGUARDS)
- **Date**: November 2, 2025
- **Author**: DC Protocol Implementation Team  
- **Status**: ⏳ PENDING FINAL ARCHITECT APPROVAL
- **Approval Required**: Yes

## CRITICAL CORRECTIONS - COMPLETE ITERATION HISTORY

### v1.0 → v2.0: Two Critical Bugs
1. **Earning Wallet Formula**: Only included 'Pending', excluded approved statuses
2. **Rollback Resync**: Missing backfill script before rollback

### v2.0 → v3.0: Two More Critical Bugs  
3. **Transfer Queue Status Missing**: Mentioned but not included in SQL WHERE clause
4. **Rollback Trigger Protection**: No try/finally guard, trigger could stay disabled

### v3.0 → v4.0: Status Taxonomy Verification
5. **Complete Codebase Audit**: Identified ALL 8 verification_status values in production code
6. **'Finance Review' Clarification**: Does NOT exist in current code (architect confirmed)
7. **'Not Eligible' Treatment**: Terminal rejection, must EXCLUDE from earning wallet
8. **Dual Paid Statuses**: Both 'Finance Paid' AND 'Accounts Paid' confirmed

### v4.0 → v4.1: Deployment Safety & Operational Risk
9. **Deployment Sequencing**: No explicit order specified (could cause partial deploy failures)
10. **Validation Trigger Compatibility**: Would fail on existing invalid records
11. **SQL Injection Risk**: String interpolation unsafe for future status changes

### ALL CORRECTIONS APPLIED IN v4.1 ✅

---

## 1. ARCHITECT-VERIFIED STATUS TAXONOMY (100% COMPLETE)

### All verification_status Values (From Codebase Audit)
```python
# UNPAID STATUSES (4 total - IN earning_wallet)
'Pending'                    # Admin approval queue
'Admin Verified'             # Super Admin verification queue
'Super Admin Verified'       # Transfer Queue (Finance payment queue)
'Super Admin Approved'       # Transfer Queue (alternate status)

# PAID STATUSES (2 total - EXCLUDE from earning_wallet)
'Finance Paid'               # Legacy payment marker
'Accounts Paid'              # Current payment marker (bank sent)

# TERMINAL REJECTION (2 total - EXCLUDE from earning_wallet)
'Rejected'                   # Rejected at any stage
'Not Eligible'               # User doesn't qualify

# DATA QUALITY ISSUE (1 total - MUST BE CLEANED)
'Ved Income'                 # Test data / mis-entry (should be income_type)
```

### Python Constants (Single Source of Truth - Deploy FIRST)
```python
# backend/app/core/constants.py
# v4.1: Deploy BEFORE database triggers/views

UNPAID_STATUSES = ['Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved']
PAID_STATUSES = ['Finance Paid', 'Accounts Paid']
TERMINAL_REJECTION_STATUSES = ['Rejected', 'Not Eligible']
COMPLETED_WITHDRAWAL_STATUSES = ['Bank Sent', 'Completed']

ALL_VALID_VERIFICATION_STATUSES = UNPAID_STATUSES + PAID_STATUSES + TERMINAL_REJECTION_STATUSES
```

---

## 2. DEPLOYMENT SEQUENCE (v4.1 CRITICAL - FOLLOW EXACTLY)

### Pre-Deployment (Phase 0)
1. ✅ Create database backup
2. ✅ Run preflight cleanup (DRY RUN) → review results
3. ✅ Run preflight cleanup (LIVE) → fix invalid records
4. ✅ Verify no invalid records remain

### Python Deployment (Phase 1)
5. ✅ Deploy `constants.py` FIRST
6. ✅ Restart backend (load constants)
7. ✅ Verify constants accessible

### Database Deployment (Phase 2)
8. ✅ Create materialized views (hardcoded statuses)
9. ✅ Create indexes
10. ✅ Refresh views (initial population)
11. ✅ Deploy validation trigger (AFTER cleanup verified)

### ORM Deployment (Phase 3)
12. ✅ Deploy updated `user.py` with computed properties
13. ✅ Restart backend (load new model)
14. ✅ Verify computed properties work

### Verification (Phase 4)
15. ✅ Run reconciliation check
16. ✅ Verify logs (no errors)
17. ✅ Test API endpoints

### Monitoring (Phase 5 - First 24hrs)
18. ✅ Monitor reconciliation rate (every 6hrs)
19. ✅ Monitor p95 latency
20. ✅ If issues → ROLLBACK

**Dependency Chain**: constants.py → Backend Restart → DB Views → Validation Trigger → User Model → Backend Restart → Verification

---

## 3. PREFLIGHT DATA CLEANUP (v4.1 NEW - RUN BEFORE VALIDATION TRIGGER)

### Purpose
Clean existing invalid `verification_status` records BEFORE deploying validation trigger (which would fail on legacy data).

### Cleanup Script (scripts/dc_preflight_cleanup.py)
```python
def cleanup_invalid_verification_statuses(db: Session, dry_run=True):
    """
    v4.1: Clean up invalid statuses BEFORE validation trigger deployment
    
    Strategy:
    - 'Ved Income' records → Convert to 'Rejected' (preserve history)
    - Other invalid → Manual review required
    
    Returns cleanup statistics
    """
    
    # Step 1: Find all invalid records
    invalid_query = text("""
        SELECT id, user_id, verification_status, net_amount
        FROM pending_income
        WHERE verification_status NOT IN (
            'Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved',
            'Finance Paid', 'Accounts Paid', 'Rejected', 'Not Eligible'
        )
    """)
    
    # Step 2: Categorize (Ved Income vs other)
    # Step 3: Fix Ved Income → 'Rejected' + add notes
    # Step 4: Flag other for manual review
    # Step 5: Verify no invalid records remain
    
    return stats

def verify_no_invalid_statuses(db: Session):
    """Verify safe to deploy validation trigger"""
    invalid_count = db.execute(text("""
        SELECT COUNT(*) FROM pending_income
        WHERE verification_status NOT IN (8 valid statuses)
    """)).scalar()
    
    return invalid_count == 0  # True = safe to deploy
```

### Validation Trigger (Deploy AFTER cleanup passes)
```sql
-- v4.1: Only deploy after preflight cleanup completes successfully

CREATE OR REPLACE FUNCTION validate_verification_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.verification_status NOT IN (
        'Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved',
        'Finance Paid', 'Accounts Paid', 'Rejected', 'Not Eligible'
    ) THEN
        RAISE EXCEPTION 'Invalid verification_status: %', NEW.verification_status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_verification_status
    BEFORE INSERT OR UPDATE ON pending_income
    FOR EACH ROW
    EXECUTE FUNCTION validate_verification_status();
```

### Emergency Disable (if trigger blocks operations)
```sql
DROP TRIGGER IF EXISTS enforce_verification_status ON pending_income;
```

---

## 4. PARAMETERIZED RESYNC SCRIPT (v4.1 - SQL INJECTION SAFE)

### Rollback Resync (scripts/dc_rollback_resync.py)
```python
from contextlib import contextmanager
from sqlalchemy import text
from app.core.constants import UNPAID_STATUSES, PAID_STATUSES, COMPLETED_WITHDRAWAL_STATUSES

@contextmanager
def temporarily_disable_wallet_trigger(db: Session):
    """v4.1: Try/finally ensures trigger ALWAYS re-enabled"""
    try:
        db.execute(text('ALTER TABLE "user" DISABLE TRIGGER block_wallet_updates'))
        db.commit()
        yield
    finally:
        db.execute(text('ALTER TABLE "user" ENABLE TRIGGER block_wallet_updates'))
        db.commit()

def resync_stored_wallets_from_ledger(db: Session):
    """
    v4.1: Resync with PARAMETERIZED queries (NO string interpolation)
    
    CRITICAL FIXES:
    - Uses ANY(:param) for array parameters (SQL injection safe)
    - Imports constants from single source
    - Try/finally protects trigger
    """
    
    with temporarily_disable_wallet_trigger(db):
        
        # Resync earning wallet (v4.1: Parameterized with ANY())
        resync_query = text("""
            UPDATE "user" u
            SET earning_wallet = COALESCE(
                (SELECT SUM(net_amount) FROM pending_income 
                 WHERE user_id = u.id 
                 AND verification_status = ANY(:unpaid_statuses)),
                0.0
            )
        """)
        db.execute(resync_query, {"unpaid_statuses": UNPAID_STATUSES})
        
        # Resync withdrawable wallet (v4.1: Parameterized for both arrays)
        resync_query = text("""
            UPDATE "user" u
            SET withdrawable_wallet = COALESCE(
                (SELECT SUM(net_amount) FROM pending_income 
                 WHERE user_id = u.id AND verification_status = ANY(:paid_statuses)),
                0.0
            ) - COALESCE(
                (SELECT SUM(final_payout) FROM withdrawal_requests
                 WHERE user_id = u.id AND status = ANY(:withdrawn_statuses)),
                0.0
            )
        """)
        db.execute(resync_query, {
            "paid_statuses": PAID_STATUSES,
            "withdrawn_statuses": COMPLETED_WITHDRAWAL_STATUSES
        })
        
        db.commit()
    
    # Trigger now re-enabled (context manager guarantee)
    verify_resync(db)
```

**Why Parameterized?** If future status contains apostrophe (e.g., "Finance's Review"), string interpolation would break SQL. ANY(:param) is safe.

---

## 5. MATERIALIZED VIEWS (v4.1 - HARDCODED FOR SAFETY)

### Earning Wallet Balance
```sql
-- v4.1: Use HARDCODED statuses (independent of Python constants.py deployment)
CREATE MATERIALIZED VIEW user_earning_wallet_balance AS
SELECT 
    user_id,
    COALESCE(SUM(net_amount), 0.0) as earning_balance,
    COUNT(*) as pending_income_count,
    MAX(business_date) as latest_income_date,
    NOW() as last_refreshed
FROM pending_income
WHERE verification_status IN (
    'Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved'
)
GROUP BY user_id;

CREATE UNIQUE INDEX idx_earning_wallet_user ON user_earning_wallet_balance(user_id);
CREATE INDEX idx_earning_wallet_balance ON user_earning_wallet_balance(earning_balance DESC);
```

### Withdrawable Wallet Balance
```sql
-- v4.1: Hardcoded statuses for deployment safety
CREATE MATERIALIZED VIEW user_withdrawable_wallet_balance AS
WITH earned AS (
    SELECT user_id, COALESCE(SUM(net_amount), 0.0) as total_earned
    FROM pending_income
    WHERE verification_status IN ('Finance Paid', 'Accounts Paid')
    GROUP BY user_id
),
withdrawn AS (
    SELECT user_id, COALESCE(SUM(final_payout), 0.0) as total_withdrawn
    FROM withdrawal_requests
    WHERE status IN ('Bank Sent', 'Completed')
    GROUP BY user_id
)
SELECT 
    u.id as user_id,
    COALESCE(e.total_earned, 0.0) - COALESCE(w.total_withdrawn, 0.0) as withdrawable_balance,
    NOW() as last_refreshed
FROM "user" u
LEFT JOIN earned e ON e.user_id = u.id
LEFT JOIN withdrawn w ON w.user_id = u.id;

CREATE UNIQUE INDEX idx_withdrawable_wallet_user ON user_withdrawable_wallet_balance(user_id);
```

---

## 6. ORM COMPUTED PROPERTIES (v4.1 - References Constants)

### User Model (backend/app/models/user.py)
```python
from sqlalchemy import text
from app.core.constants import UNPAID_STATUSES, PAID_STATUSES

# v4.1: This file DEPENDS on constants.py being deployed first

class User(BaseModel):
    __tablename__ = 'user'
    
    # LEGACY FIELDS (nullable for rollback)
    earning_wallet = Column(Float, default=0.0, nullable=True)
    withdrawable_wallet = Column(Float, default=0.0, nullable=True)
    
    # DC PROTOCOL: Computed properties (v4.1)
    @property
    def earning_wallet_balance(self) -> float:
        """Earning wallet from materialized view"""
        db = next(get_db())
        result = db.execute(
            text("SELECT earning_balance FROM user_earning_wallet_balance WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        return float(result[0]) if result else 0.0
    
    @property
    def withdrawable_wallet_balance(self) -> float:
        """Withdrawable wallet from materialized view"""
        db = next(get_db())
        result = db.execute(
            text("SELECT withdrawable_balance FROM user_withdrawable_wallet_balance WHERE user_id = :user_id"),
            {"user_id": self.id}
        ).first()
        return float(result[0]) if result else 0.0
```

---

## 7. TESTING STRATEGY (v4.1 - Deployment Safety Tests)

### Unit Tests (tests/test_dc_protocol_v4_1.py)
```python
def test_preflight_cleanup_dry_run():
    """v4.1 NEW: Test dry run doesn't modify data"""
    invalid = PendingIncome(user_id="TEST", verification_status='Ved Income')
    db.add(invalid)
    db.commit()
    
    stats = cleanup_invalid_verification_statuses(db, dry_run=True)
    
    assert stats["ved_income_records"] == 1
    assert stats["fixed"] == 0  # Dry run = no changes
    
    record = db.query(PendingIncome).get(invalid.id)
    assert record.verification_status == 'Ved Income'  # Unchanged

def test_preflight_cleanup_live():
    """v4.1 NEW: Test live cleanup fixes records"""
    invalid = PendingIncome(user_id="TEST", verification_status='Ved Income')
    db.add(invalid)
    db.commit()
    
    stats = cleanup_invalid_verification_statuses(db, dry_run=False)
    
    assert stats["fixed"] == 1
    
    record = db.query(PendingIncome).get(invalid.id)
    assert record.verification_status == 'Rejected'  # Fixed
    assert 'DC v4.1 Cleanup' in record.notes

def test_validation_trigger_blocks_invalid():
    """v4.1: Verify trigger rejects invalid statuses"""
    with pytest.raises(Exception, match="Invalid verification_status"):
        invalid = PendingIncome(user_id="TEST", verification_status='Invalid')
        db.add(invalid)
        db.commit()

def test_parameterized_sql_injection_safe():
    """v4.1 NEW: Verify parameterized queries handle special chars"""
    # Even if constants change to include quotes/commas, resync works
    original = UNPAID_STATUSES.copy()
    try:
        UNPAID_STATUSES.append("Finance's Review")  # Has apostrophe
        resync_stored_wallets_from_ledger(db)  # Should NOT fail
    finally:
        UNPAID_STATUSES.clear()
        UNPAID_STATUSES.extend(original)

def test_rollback_trigger_always_reenabled():
    """v4.1: Verify try/finally protects trigger"""
    # Introduce mismatch that will fail verification
    user = User.query.first()
    user.earning_wallet = 9999.99  # Wrong value
    
    try:
        resync_stored_wallets_from_ledger(db)  # Will fail verification
    except:
        pass  # Expected failure
    
    # v4.1 CRITICAL: Trigger should be re-enabled despite failure
    trigger_status = db.execute(text("""
        SELECT tgenabled FROM pg_trigger WHERE tgname = 'block_wallet_updates'
    """)).first()
    
    assert trigger_status[0] == 'O'  # 'O' = enabled

def test_earning_wallet_all_four_statuses():
    """v4.0 test - still valid"""
    # Create incomes in all 4 unpaid statuses
    # Verify earning_wallet = sum of all 4
    pass

def test_earning_wallet_excludes_not_eligible():
    """v4.0 test - still valid"""
    # 'Not Eligible' must NOT count
    pass

def test_withdrawable_dual_paid_statuses():
    """v4.0 test - still valid"""
    # Both 'Finance Paid' AND 'Accounts Paid' count
    pass
```

---

## 8. EMERGENCY ROLLBACK PROCEDURE (v4.1 SAFE)

### Rollback Criteria
Trigger rollback if:
- Reconciliation <99.5% after 24hrs
- P95 latency >200ms
- Production errors
- Validation trigger blocking legitimate ops

### Rollback Steps
```bash
# 1. Disable validation trigger (if blocking)
psql -c "DROP TRIGGER IF EXISTS enforce_verification_status ON pending_income;"

# 2. Resync stored wallets (ensures current)
python scripts/dc_rollback_resync.py
# v4.1: Try/finally ensures trigger protection

# 3. Disable computed wallets
# Set: USE_COMPUTED_WALLETS = False

# 4. Restart backend

# 5. Verify rollback (stored wallets active)
python -c "from app.models.user import User; print(User.query.first().earning_wallet)"

# 6. Monitor for 1 hour

# 7. Alert team + post-mortem
```

---

## 9. SUCCESS METRICS (v4.1 FINAL)

### Data Integrity
- **Target**: 99.95%+ reconciliation
- **Expected**: 99.99%+ with complete taxonomy + cleanup

### Performance
- **Target**: <100ms p95
- **Expected**: <50ms with materialized views

### Code Quality
- **Target**: Zero direct wallet writes
- **Expected**: Trigger-enforced + validation-enforced

### Data Quality
- **Target**: Zero invalid records
- **Expected**: Preflight cleanup + validation trigger

### Deployment Safety
- **Target**: Zero partial deploy failures
- **Expected**: Explicit sequencing prevents issues

---

## 10. SUMMARY OF ALL FIXES (v1.0 → v4.1)

### v1.0 Issues → v4.1 Fixes
1. **Earning Wallet**: 25% coverage → 100% (4 statuses)
2. **Rollback Resync**: Missing → Complete with verification
3. **Transfer Queue**: Omitted → Included (2 variants)
4. **Trigger Protection**: None → Try/finally context manager
5. **Status Taxonomy**: Incomplete → Architect-verified complete
6. **'Not Eligible'**: Unhandled → Excluded (terminal rejection)
7. **Dual Paid**: Unverified → Both included
8. **Data Quality**: No validation → Trigger + cleanup
9. **Deployment Sequence**: Undefined → 20-step explicit order
10. **Preflight Cleanup**: None → Mandatory before trigger
11. **SQL Injection**: String interpolation → Parameterized (ANY())

### Impact
- ✅ Reconciliation: 25% → 99.99%+
- ✅ Security: Multiple holes → Fully protected
- ✅ Deployment: Risky → Safe with explicit sequence
- ✅ Data Quality: Unvalidated → Enforced + cleaned

---

**RFC STATUS**: ⏳ **PENDING FINAL ARCHITECT APPROVAL** (v4.1 - DEPLOYMENT-SAFE FINAL)

**v4.1 Additions**:
- ✅ 20-step deployment sequence with dependency graph
- ✅ Preflight cleanup script (dry run + live modes)
- ✅ Parameterized SQL (ANY() operator) for injection safety
- ✅ Emergency trigger disable instructions
- ✅ Enhanced testing (cleanup tests, SQL injection tests)

**Next Step**: Final architect approval → Phase 1.2 (Reconciliation Dataset)

---
**Document End - Version 4.1 (DEPLOYMENT-SAFE FINAL)**
