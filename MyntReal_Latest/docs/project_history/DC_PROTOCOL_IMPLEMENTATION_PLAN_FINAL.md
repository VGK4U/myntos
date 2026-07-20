# DC Protocol Implementation Plan - FINAL (Architect Approved)
**BeV 2.0 Reference Program - Complete Data Consistency Remediation**

## Executive Summary
Complete DC Protocol enforcement across all 20 modules with architect oversight at every phase. This plan implements single-source-of-truth architecture for ALL data, with primary focus on financial integrity (wallets, income, withdrawals).

---

## ARCHITECT DECISIONS (Binding)

### Question 1: Ved Income Table Architecture
**Decision**: ✅ **KEEP `ved_income` as analytical/event table BUT bind to `pending_income` via FK**
- `ved_income` = Ved relationship analytics (member → owner linkage, percentages)
- `pending_income` = Final income ledger (authoritative amounts)
- **Action**: Add `pending_income_id` foreign key to `ved_income` table

### Question 2: Bank Details Status Single Source
**Decision**: ✅ **`bank_details.status` is authoritative, `kyc_documents` provides evidence only**
- Single source: `bank_details_approval.status` (if separate table exists) OR `user.bank_details_status`
- `kyc_documents` = Identity verification documents only, not bank approval
- **Action**: Clarify bank approval workflow and designate single source

### Question 3: KYC Documents Data Duplication
**Decision**: ✅ **REMOVE duplicate name/contact columns from `kyc_documents`**
- Source: `user.name`, `user.phone_number`, `user.email`
- `kyc_documents` should store ONLY: `user_id` (FK), document images, approval status
- **Action**: Delete duplicate columns, use FK references

### Question 4: System Control vs App Settings
**Decision**: ✅ **MERGE into unified configuration service with namespaced keys**
- New architecture: Single `system_config` table with namespaced keys
- Example: `kyc.processing.enabled`, `income.calculation.enabled`
- **Action**: Create migration plan, configuration governance document

### Question 5: Expense Reimbursement Flow
**Decision**: ✅ **Route expense reimbursements through `pending_income`**
- Create `pending_income` records with `income_type='Expense Reimbursement'`
- Maintains single cash ledger alignment
- **Action**: Verify current expense flow, create migration if needed

---

## PRIORITY ADJUSTMENTS (Architect Mandated)

### ELEVATE TO P0 (Critical - Cash Exposure)
- **V9.2**: Field allowance payout duplication → **NOW P0**
- **KYC Bypass Wallet Sync**: Manual bypass creates wallet inconsistency → **NOW P0**

### DEMOTE FROM P1
- **V5.1**: Award progress cache cleanups → **NOW P2** (after ledger risks contained)

### UPDATED P0 LIST (5 Critical Violations)
1. **V3.1**: Income amounts duplicated (pending_income → transaction → wallets)
2. **V4.1**: Withdrawal amounts duplicated
3. **V9.2**: Field allowance payments duplicated (ELEVATED)
4. **V14.1**: VGK manual wallet adjustments + finance_admin ledger edits
5. **KYC Bypass Wallet Sync**: Emergency approval wallet credits

---

## PHASE 1: CRITICAL FINANCIAL DATA (P0 Violations)
**Duration**: 3 weeks
**Architect Checkpoints**: Before start, midpoint (day 10), completion

### Step 1.1: Technical RFC & Design (Days 1-3)
**Deliverables**:
1. **Wallet View Definitions** (SQL)
   ```sql
   -- Materialized view for earning wallet
   CREATE MATERIALIZED VIEW user_earning_wallet_balance AS
   SELECT 
       user_id,
       COALESCE(SUM(net_amount), 0) as earning_balance
   FROM pending_income
   WHERE verification_status = 'Pending'
   GROUP BY user_id;
   
   -- Materialized view for withdrawable wallet
   CREATE MATERIALIZED VIEW user_withdrawable_wallet_balance AS
   SELECT 
       u.id as user_id,
       COALESCE(
           (SELECT SUM(net_amount) FROM pending_income 
            WHERE user_id = u.id 
            AND verification_status IN ('Finance Paid', 'Accounts Paid')), 
           0
       ) - COALESCE(
           (SELECT SUM(final_payout) FROM withdrawal_requests 
            WHERE user_id = u.id 
            AND status IN ('Bank Sent', 'Completed')), 
           0
       ) as withdrawable_balance
   FROM user u;
   
   -- Indexes for performance
   CREATE INDEX idx_pending_income_user_status ON pending_income(user_id, verification_status);
   CREATE INDEX idx_withdrawal_user_status ON withdrawal_requests(user_id, status);
   ```

2. **Shadow Mode Telemetry**
   - Log comparison: computed_value vs stored_value
   - Track mismatches with user_id, amount_diff, timestamp
   - Alert on > 0.05% variance

3. **Rollback Plan**
   - Retain legacy columns as nullable
   - Feature toggle: `USE_COMPUTED_WALLETS` (default: false)
   - Rollback SOP: disable toggle, verify stored values unchanged

**Architect Review**: Sign-off on RFC before proceeding

---

### Step 1.2: Reconciliation Dataset Build (Days 4-6)
**Deliverables**:
```python
# scripts/dc_reconciliation.py
def build_reconciliation_dataset():
    """
    Compare all financial data sources:
    1. pending_income ledger
    2. transactions table
    3. withdrawal_requests
    4. user wallet columns (current stored values)
    5. VGK manual adjustments (audit log)
    6. Field allowance payments
    """
    
    for user in all_users:
        # Calculate from single sources
        computed_earning = sum(pending_income WHERE user_id=X AND status='Pending')
        computed_withdrawable = sum(pending_income WHERE paid) - sum(withdrawals WHERE completed)
        
        # Compare to stored
        stored_earning = user.earning_wallet
        stored_withdrawable = user.withdrawable_wallet
        
        # Log discrepancies
        if abs(computed_earning - stored_earning) > 0.01:
            log_mismatch('earning_wallet', user.id, computed, stored, diff)
        
        if abs(computed_withdrawable - stored_withdrawable) > 0.01:
            log_mismatch('withdrawable_wallet', user.id, computed, stored, diff)
    
    # Generate reconciliation report
    return {
        'total_users': count,
        'perfect_matches': count where diff=0,
        'minor_variance': count where diff < ₹1,
        'major_variance': count where diff >= ₹1,
        'match_percentage': (perfect + minor) / total * 100
    }
```

**Success Criteria**: ≥ 99.95% match rate
**Architect Review**: Review reconciliation results, approve outliers

---

### Step 1.3: Database Materialized Views Implementation (Days 7-9)
**Deliverables**:
1. Create materialized views (SQL from Step 1.1)
2. Add refresh schedule:
   ```python
   # In scheduler
   @scheduler.scheduled_job('cron', hour=3, minute=45)  # After wallet sync
   def refresh_wallet_views():
       db.execute("REFRESH MATERIALIZED VIEW user_earning_wallet_balance")
       db.execute("REFRESH MATERIALIZED VIEW user_withdrawable_wallet_balance")
   ```

3. ORM Computed Properties:
   ```python
   # backend/app/models/user.py
   @property
   def earning_wallet_balance(self):
       """DC Protocol: Computed from pending_income (single source)"""
       result = db.query(UserEarningWalletBalance).filter_by(user_id=self.id).first()
       return float(result.earning_balance) if result else 0.0
   
   @property
   def withdrawable_wallet_balance(self):
       """DC Protocol: Computed from pending_income - withdrawals"""
       result = db.query(UserWithdrawableWalletBalance).filter_by(user_id=self.id).first()
       return float(result.withdrawable_balance) if result else 0.0
   ```

**Testing**: Verify views return same values as Python calculations

---

### Step 1.4: Shadow Mode Deployment (Days 10-14)
**Deliverables**:
1. Update ALL endpoints to dual-read (stored + computed):
   ```python
   # backend/app/api/v1/endpoints/users.py
   @router.get("/user/{user_id}/wallet")
   def get_wallet_balance(user_id: str):
       user = get_user(user_id)
       
       # Current (stored)
       stored_earning = user.earning_wallet
       stored_withdrawable = user.withdrawable_wallet
       
       # Computed (DC Protocol)
       computed_earning = user.earning_wallet_balance  # property
       computed_withdrawable = user.withdrawable_wallet_balance
       
       # Log discrepancy
       if abs(computed_earning - stored_earning) > 0.01:
           logger.warning(f"Wallet mismatch user={user_id} earning: stored={stored_earning} computed={computed_earning}")
       
       # Return stored for now (shadow mode)
       return {
           "earning_wallet": stored_earning,
           "withdrawable_wallet": stored_withdrawable,
           "_shadow_computed_earning": computed_earning,  # for monitoring
           "_shadow_computed_withdrawable": computed_withdrawable
       }
   ```

2. Monitor shadow metrics for 3 days
3. Daily reconciliation reports

**Architect Midpoint Review**: Review shadow mode metrics, approve for cutover

---

### Step 1.5: Write-Lock Legacy Columns (Days 15-16)
**Deliverables**:
1. Database triggers to prevent writes:
   ```sql
   CREATE OR REPLACE FUNCTION prevent_wallet_writes()
   RETURNS TRIGGER AS $$
   BEGIN
       IF (NEW.earning_wallet IS DISTINCT FROM OLD.earning_wallet) OR
          (NEW.withdrawable_wallet IS DISTINCT FROM OLD.withdrawable_wallet) THEN
           RAISE EXCEPTION 'DC Protocol: Direct wallet writes forbidden. Use pending_income ledger.';
       END IF;
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;
   
   CREATE TRIGGER block_wallet_updates
   BEFORE UPDATE ON "user"
   FOR EACH ROW
   EXECUTE FUNCTION prevent_wallet_writes();
   ```

2. Remove all wallet write operations from code:
   ```python
   # BEFORE (REMOVE):
   user.earning_wallet += income_amount
   user.withdrawable_wallet -= withdrawal_amount
   
   # AFTER (DC Protocol):
   # Wallet automatically computed from pending_income
   # No manual writes needed
   ```

**Testing**: Verify all wallet updates fail, computed properties work

---

### Step 1.6: Cutover to Computed Values (Days 17-19)
**Deliverables**:
1. Enable feature toggle: `USE_COMPUTED_WALLETS = True`
2. Update all endpoints to return computed values:
   ```python
   return {
       "earning_wallet": user.earning_wallet_balance,  # Computed
       "withdrawable_wallet": user.withdrawable_wallet_balance  # Computed
   }
   ```

3. Remove shadow monitoring code
4. Full regression testing:
   - Income approval updates balance ✓
   - Withdrawal request deducts balance ✓
   - Dashboard shows correct values ✓
   - Daily sync still works ✓

**Architect Review**: Final review before declaring Phase 1 complete

---

### Step 1.7: Delete Duplicate Columns (Days 20-21)
**Deliverables**:
1. Mark columns as deprecated (nullable):
   ```sql
   ALTER TABLE "user" ALTER COLUMN earning_wallet DROP NOT NULL;
   ALTER TABLE "user" ALTER COLUMN withdrawable_wallet DROP NOT NULL;
   ```

2. After 1 week stability period, DROP columns:
   ```sql
   -- ONLY after 99.95%+ reconciliation AND 1 week stability
   ALTER TABLE "user" DROP COLUMN earning_wallet;
   ALTER TABLE "user" DROP COLUMN withdrawable_wallet;
   ```

3. Update ORM models - remove fields
4. Delete transaction.amount column (replace with computed property)

**Completion Criteria**:
- ✅ 99.95%+ reconciliation rate
- ✅ 1 week zero incidents in production
- ✅ Executive sign-off
- ✅ Rollback plan tested

---

## PHASE 2: USER & TEAM DATA (Remaining P1)
**Duration**: 2 weeks
**Architect Checkpoints**: Before start, completion

### Modules: Authentication (1), Binary Tree (2), Awards (5), KYC (7)

### Step 2.1: Position Fields (V2.2)
- DELETE `user.position`, `user.position_id`
- Compute from `placement` table

### Step 2.2: Coupon & Package (V6.1, V6.2)
- DELETE `user.coupon_status`, `user.package_points`
- Compute from `coupon` table

### Step 2.3: KYC Status (V7.1)
- DELETE `user.kyc_status`
- Compute from `kyc_documents.status`
- Remove duplicate name/contact from kyc_documents

### Step 2.4: Award Eligibility (V5.1 - now P2)
- DELETE stored progress fields
- Calculate eligibility on-demand from `user_leg_metrics`

**Architect Review**: After completion

---

## PHASE 3: SUPPORTING MODULES (P2)
**Duration**: 1 week
**Architect Checkpoints**: After completion

### Modules: Red Coupon (17), Expense (19), System Config (12)

### Step 3.1: Red Coupon Status
- Compute from `red_coupon_approval` latest status

### Step 3.2: Expense Reimbursements
- Create `pending_income` records for reimbursements
- income_type='Expense Reimbursement'

### Step 3.3: System Configuration Merge
- Unified `system_config` table with namespaced keys
- Migration from `system_control` + `app_settings`

**Architect Review**: After completion

---

## PHASE 4: DOCUMENTATION & VALIDATION (P3)
**Duration**: 1 week

### Step 4.1: Cache Documentation
- Document `user_leg_metrics` cache refresh triggers
- Document reporting cache patterns

### Step 4.2: Configuration Governance
- Namespace conventions
- Migration SOP

### Step 4.3: Final DC Validation
- Run complete DC audit
- Verify zero duplicate amounts
- Performance benchmarks

**Architect Review**: Final sign-off

---

## PERFORMANCE OPTIMIZATION

### Required Indexes
```sql
-- Income ledger queries
CREATE INDEX idx_pending_income_user_status ON pending_income(user_id, verification_status);
CREATE INDEX idx_pending_income_business_date ON pending_income(business_date);

-- Withdrawal queries  
CREATE INDEX idx_withdrawal_user_status ON withdrawal_requests(user_id, status);

-- Placement queries
CREATE INDEX idx_placement_parent ON placement(parent_id);
CREATE INDEX idx_placement_user ON placement(user_id);
```

### Materialized View Refresh Strategy
- **Frequency**: Every 15 minutes during business hours, hourly off-hours
- **Method**: CONCURRENTLY to avoid locks
- **Trigger**: After major batch operations (income calc, withdrawals)

### API Response Caching
```python
# Cache wallet balances for 5 minutes
@cache(ttl=300)
def get_user_wallet_balance(user_id: str):
    return user.earning_wallet_balance, user.withdrawable_wallet_balance
```

---

## SUCCESS METRICS

### Data Integrity
- ✅ 100% reconciliation: computed = stored (within ₹0.01)
- ✅ Zero duplicate amount fields in database schema
- ✅ All financial queries use `pending_income` as single source

### Performance
- ✅ Wallet balance queries < 100ms (p95)
- ✅ Dashboard load time < 500ms (p95)
- ✅ No query degradation vs baseline

### Code Quality
- ✅ Zero direct wallet writes in codebase
- ✅ All computed properties tested
- ✅ DC Protocol enforced via database triggers

### Audit & Compliance
- ✅ Complete audit trail for all wallet changes
- ✅ Rollback plan validated
- ✅ Executive sign-off obtained

---

## RISK MITIGATION

### Risk 1: Reconciliation Failures
**Mitigation**:
- 99.95% threshold (allow 0.05% outliers for manual review)
- Executive waiver process for known discrepancies
- Retain stored values for rollback

### Risk 2: Performance Degradation
**Mitigation**:
- Materialized views for aggregation
- Comprehensive indexing strategy
- API response caching
- Performance regression tests before cutover

### Risk 3: VGK Manual Adjustments
**Mitigation**:
- VGK adjustments MUST create `pending_income` records
- No direct wallet writes allowed (trigger-enforced)
- Audit log for all VGK operations

### Risk 4: Rollback Complexity
**Mitigation**:
- Feature toggle for instant rollback
- Retain nullable legacy columns during transition
- Validated rollback procedure

---

## GOVERNANCE

### Architect Review Gates
1. **Pre-Phase 1**: RFC sign-off (Day 3)
2. **Mid-Phase 1**: Shadow mode metrics (Day 10)
3. **Post-Phase 1**: Cutover approval (Day 19)
4. **Pre-Phase 2**: User data strategy (Week 4)
5. **Final**: Complete DC validation (Week 7)

### Executive Approvals
1. Reconciliation outliers > 0.05%
2. Column deletion (after 1 week stability)
3. Production cutover timing

### Configuration Changes
- All config changes via PR review
- Namespace conventions enforced
- Migration scripts tested in dev first

---

**Status**: Ready for Phase 1 implementation
**Last Updated**: November 2, 2025
**Architect Approval**: Required before proceeding
**Estimated Completion**: 6-7 weeks total
