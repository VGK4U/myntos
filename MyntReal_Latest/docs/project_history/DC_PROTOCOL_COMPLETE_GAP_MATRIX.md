# DC Protocol Complete Gap Matrix - BeV 2.0 Reference Program
**COMPREHENSIVE Data Consistency Audit Across ALL 20 Modules**

## DC Protocol Enforcement Rules
1. **Database is King** - Database is the PRIMARY source of truth
2. **Single Source per Data Type** - One authoritative table per category
3. **No Duplication** - Calculate/compute from source, never store duplicates
4. **Delete After Migration** - Remove duplicate fields after validation
5. **Architect Review** - Every phase reviewed before implementation

---

## MODULE 1: AUTHENTICATION & USER MANAGEMENT

### Current State Analysis
**Tables**: `user`, `super_admin_session`, `custom_role`

**DC Violations Found**:

#### V1.1: User Profile Fields Duplicated
- **Issue**: User name/email stored in multiple places
- **Tables**: `user.name`, `kyc_documents.name`, `bank_details.account_holder_name`
- **DC Status**: ❌ **VIOLATION** - Name duplicated across 3 tables
- **Single Source**: `user.name` should be ONLY source
- **Fix**: 
  - `kyc_documents` → Add `user_id` foreign key reference only
  - `bank_details.account_holder_name` → Should reference `user.name`
  - Remove duplicate name storage

#### V1.2: User Status Fields Duplicated
- **Issue**: Multiple status fields tracking same state
- **Fields**: 
  - `user.account_status` ('Active', 'Inactive', 'Locked')
  - `user.account_locked` (Boolean)
  - `user.kyc_bypass_active` (Boolean)
- **DC Status**: ⚠️ **REVIEW NEEDED** - These may track different states
- **Action**: Architect review to determine if these are truly duplicates or separate concerns

#### V1.3: Password Reset Fields
- **Issue**: Multiple token fields for password reset
- **Fields**:
  - `user.password_reset_token`
  - `user.reset_code`
  - `user.reset_code_expires`
- **DC Status**: ✅ **COMPLIANT** - Different mechanisms (token vs OTP code)

**Priority**: P1 (High)
**Owner**: Authentication Module Team

---

## MODULE 2: TEAM & BINARY TREE

### Current State Analysis
**Tables**: `placement`, `user_leg_metrics`, `placement_request`, `placement_log`

**DC Violations Found**:

#### V2.1: Team Count Caching
- **Issue**: Team counts in multiple places
- **Tables**:
  - `placement.left_child` / `placement.right_child` (SOURCE - tree structure)
  - `user_leg_metrics.left_team_count` / `right_team_count` (CACHE)
- **DC Status**: ✅ **COMPLIANT** - This is proper performance caching
- **Architecture**: 
  - Source: `placement` table (actual tree structure)
  - Cache: `user_leg_metrics` (computed aggregates)
  - Refresh: Triggered on new placements
- **Action**: Document cache invalidation triggers

#### V2.2: Position Fields Duplicated
- **Issue**: Position tracking in multiple tables
- **Fields**:
  - `user.position` ('Left', 'Right')
  - `user.position_id` (parent user ID)
  - `placement.parent_id`, `placement.position`
- **DC Status**: ❌ **VIOLATION** - Position duplicated
- **Single Source**: `placement` table should be ONLY source
- **Fix**:
  - Remove `user.position` and `user.position_id`
  - Add computed property: `user.placement_position` → query from `placement`

**Priority**: P1 (High)
**Owner**: Team Management Module

---

## MODULE 3: INCOME CALCULATION

### Current State Analysis
**Tables**: `pending_income`, `transaction`, `ved_income`, `company_earnings`, `daily_cost_calculation`

**DC Violations Found**:

#### V3.1: Income Amounts Duplicated ⚠️ CRITICAL
- **Issue**: Income amounts stored in 3 places
- **Tables**:
  - `pending_income.net_amount` (SOURCE - ✅ single source of truth)
  - `transaction.amount` (DUPLICATE)
  - `user.earning_wallet` (DUPLICATE)
- **DC Status**: ❌ **CRITICAL VIOLATION**
- **Single Source**: `pending_income` is the ONLY authoritative source
- **Fix**:
  - `transaction.amount` → DELETE, replace with computed property from `pending_income_id` foreign key
  - `user.earning_wallet` → DELETE, replace with computed property:
    ```python
    @property
    def earning_wallet_balance(self):
        return sum(pending_income WHERE status='Pending')
    ```

#### V3.2: Ved Income Tracking Duplicated
- **Issue**: Ved income in multiple tables
- **Tables**:
  - `ved_income` (detailed ved calculations)
  - `pending_income` (where ved income also recorded as income_type='Ved Income')
- **DC Status**: ⚠️ **REVIEW NEEDED**
- **Question**: Are these tracking different aspects?
  - `ved_income` = Ved relationship details (member → owner linkage)
  - `pending_income` = Final income amount after all calculations
- **Architect Review Required**: Determine if `ved_income.ceiling_applied_amount` should be computed from `pending_income` or vice versa

#### V3.3: Guru Dakshina Tracking
- **Issue**: Guru Dakshina amounts in multiple places
- **Fields**:
  - `pending_income.gurudakshina_deduction` (2% deducted FROM earner)
  - `pending_income` records with `income_type='Guru Dakshina'` (2% paid TO referrer)
- **DC Status**: ✅ **COMPLIANT** - Different perspectives of same transaction
- **Architecture**: Deduction from user A = Income for user B (referrer)

**Priority**: P0 (Critical)
**Owner**: Income Calculation Module

---

## MODULE 4: WITHDRAWAL & PAYMENT

### Current State Analysis
**Tables**: `withdrawal_requests`, `transaction`, `transfer_queue`

**DC Violations Found**:

#### V4.1: Withdrawal Amounts Duplicated ⚠️ CRITICAL
- **Issue**: Withdrawal amounts stored in 3 places
- **Tables**:
  - `withdrawal_requests.final_payout` (SOURCE)
  - `transaction.amount` (DUPLICATE)
  - `user.withdrawable_wallet` (DUPLICATE - decremented)
- **DC Status**: ❌ **CRITICAL VIOLATION**
- **Single Source**: `withdrawal_requests` should be authoritative
- **Fix**:
  - `transaction.amount` → DELETE, compute from `withdrawal_id` foreign key
  - `user.withdrawable_wallet` → DELETE, compute as:
    ```python
    @property
    def withdrawable_wallet_balance(self):
        total_earned = sum(pending_income WHERE status IN ['Finance Paid', 'Accounts Paid'])
        total_withdrawn = sum(withdrawal_requests WHERE status IN ['Bank Sent', 'Completed'])
        return total_earned - total_withdrawn
    ```

#### V4.2: Transfer Queue vs Withdrawal Tracking
- **Issue**: Transfer queue as intermediate table
- **Tables**:
  - `withdrawal_requests` (user withdrawal requests)
  - `transfer_queue` (admin approval bridge)
  - `pending_income` (linked income records)
- **DC Status**: ✅ **COMPLIANT** - Different workflow stages
- **Architecture**: Proper workflow state tracking (3-stage approval)

**Priority**: P0 (Critical)
**Owner**: Withdrawal Module

---

## MODULE 5: AWARDS & BONANZA

### Current State Analysis
**Tables**: `user_award_progress`, `user_matching_award_progress`, `direct_award_tier`, `matching_award_tier`, `dynamic_bonanza`, `bonanza_progress`

**DC Violations Found**:

#### V5.1: Award Eligibility Stored vs Calculated
- **Issue**: Award progress/eligibility stored instead of calculated
- **Tables**:
  - `user_award_progress.current_progress` (STORED)
  - `user_leg_metrics.direct_referrals` (SOURCE for calculation)
  - `direct_award_tier.referral_count` (REQUIREMENTS)
- **DC Status**: ❌ **VIOLATION**
- **Single Source**: Award eligibility should be CALCULATED on-demand
- **Fix**:
  - Keep `user_award_progress.claim_status` ONLY (whether user claimed)
  - DELETE `user_award_progress.current_progress`, `percentage_complete`, `is_eligible`
  - Compute eligibility: `user_leg_metrics.direct_referrals >= direct_award_tier.referral_count`

#### V5.2: Bonanza Progress Tracking
- **Issue**: Bonanza progress stored vs calculated
- **Tables**:
  - `bonanza_progress.current_points` (STORED)
  - Source data should be `user_leg_metrics` or `pending_income`
- **DC Status**: ❌ **VIOLATION**
- **Fix**: Calculate bonanza points from source metrics, don't store

**Priority**: P1 (High)
**Owner**: Awards Module

---

## MODULE 6: COUPON & PIN

### Current State Analysis
**Tables**: `coupon`, `enhanced_coupon`, `coupon_activation_tracker`, `pin_purchase_request`, `coupon_transfer`

**DC Violations Found**:

#### V6.1: Coupon Status Duplicated
- **Issue**: Coupon status in multiple places
- **Fields**:
  - `coupon.status` ('Active', 'Used', 'Expired') - SOURCE
  - `user.coupon_status` ('Activated', 'Inactive') - DUPLICATE
  - `coupon_activation_tracker.activated_at` - EVENT LOG
- **DC Status**: ❌ **VIOLATION**
- **Single Source**: `coupon.status` should be authoritative
- **Fix**:
  - DELETE `user.coupon_status`
  - Add computed property:
    ```python
    @property
    def coupon_activation_status(self):
        coupon = Coupon.query.filter_by(assigned_to=self.id).first()
        return coupon.status if coupon else 'No Coupon'
    ```

#### V6.2: Package Points Tracking
- **Issue**: Package points in multiple places
- **Fields**:
  - `user.package_points` (1.0, 0.5, 0.0) - STORED
  - `coupon.package_type` ('Platinum', 'Diamond', 'Blue') - SOURCE
- **DC Status**: ❌ **VIOLATION**
- **Single Source**: Coupon package type determines points
- **Fix**:
  - DELETE `user.package_points`
  - Compute from coupon package type:
    ```python
    @property
    def package_points(self):
        mapping = {'Platinum': 1.0, 'Diamond': 0.5, 'Blue': 0.0, 'Loyal': 0.0}
        coupon = Coupon.query.filter_by(assigned_to=self.id).first()
        return mapping.get(coupon.package_type, 0.0) if coupon else 0.0
    ```

**Priority**: P1 (High)
**Owner**: Coupon Module

---

## MODULE 7: KYC & BANK APPROVAL

### Current State Analysis
**Tables**: `user`, `kyc_documents`, `bank_details_approval`

**DC Violations Found**:

#### V7.1: KYC Status Duplicated
- **Issue**: KYC approval status in 2 places
- **Fields**:
  - `user.kyc_status` ('Pending', 'Approved', 'Rejected') - DUPLICATE
  - `kyc_documents.status` ('Pending', 'Approved', 'Rejected') - SOURCE
- **DC Status**: ❌ **VIOLATION**
- **Single Source**: `kyc_documents` should be authoritative
- **Fix**:
  - DELETE `user.kyc_status` column
  - Add computed property:
    ```python
    @property
    def kyc_approval_status(self):
        latest_doc = KYCDocument.query.filter_by(user_id=self.id)\
            .order_by(KYCDocument.created_at.desc()).first()
        return latest_doc.status if latest_doc else 'Not Submitted'
    ```

#### V7.2: Bank Details Status Duplicated
- **Issue**: Bank approval status duplicated
- **Fields**:
  - `user.bank_details_status` - DUPLICATE
  - `bank_details_approval.approval_status` - SOURCE?
- **DC Status**: ⚠️ **REVIEW NEEDED**
- **Architect Review**: Determine single source of truth for bank approval

#### V7.3: KYC Document Information Duplication
- **Issue**: User info duplicated in KYC docs
- **Fields**:
  - `user.name`, `user.aadhaar_number`, `user.pan_number` - SOURCE
  - `kyc_documents` likely contains same info
- **DC Status**: ⚠️ **REVIEW NEEDED**
- **Action**: Review kyc_documents schema to ensure it only links to user, not duplicates data

**Priority**: P1 (High)
**Owner**: KYC Module

---

## MODULE 8: EV & TRAINING CLAIMS

### Current State Analysis
**Tables**: `ev_model`, `ev_coupon_claim`, `training_course`, `training_claim`, `ev`, `purchase`, `franchise_purchase`

**DC Violations Found**:

#### V8.1: EV Benefit Tracking
- **Issue**: EV discount amounts tracked separately
- **Tables**:
  - `ev_coupon_claim.discount_amount` (STORED)
  - `ev_model.base_price` (REFERENCE)
  - `user.package_points` (determines discount %)
- **DC Status**: ✅ **ACCEPTABLE** - Discount locked at claim time
- **Rationale**: Discount % may change, but claimed amount should be immutable

#### V8.2: Training Course Enrollment
- **Issue**: Training enrollment status
- **Tables**:
  - `training_claim.claim_status`
  - User enrollment tracking
- **DC Status**: ✅ **COMPLIANT** - Claim table is source

**Priority**: P3 (Low)
**Owner**: EV Benefits Module

---

## MODULE 9: FIELD ALLOWANCE

### Current State Analysis
**Tables**: `field_allowance_eligibility`, `car_allowance_eligibility`, `field_allowance_progress`, `allowance_scheme_selector`, `allowance_tier_definition`

**DC Violations Found**:

#### V9.1: Field Allowance Progress Duplicated
- **Issue**: Progress metrics stored in multiple tables
- **Tables**:
  - `field_allowance_eligibility.direct_referrals_count` (STORED)
  - `field_allowance_eligibility.monthly_achieved_matchings` (STORED)
  - SOURCE should be `user_leg_metrics` and actual matching counts
- **DC Status**: ❌ **VIOLATION**
- **Fix**:
  - DELETE stored counts
  - Calculate eligibility from `user_leg_metrics` real-time

#### V9.2: Payment Tracking Duplicated
- **Issue**: Allowance payment amounts in multiple places
- **Fields**:
  - `field_allowance_eligibility.total_paid_to_date` (STORED)
  - `field_allowance_progress.total_allowance_paid` (STORED)
  - SOURCE should be `pending_income` records WHERE `income_type='Field Allowance'`
- **DC Status**: ❌ **VIOLATION**
- **Fix**:
  - DELETE stored payment totals
  - Calculate from pending_income:
    ```python
    total_paid = sum(pending_income WHERE user_id=X AND income_type='Field Allowance' AND status='Accounts Paid')
    ```

**Priority**: P1 (High)
**Owner**: Field Allowance Module

---

## MODULE 10: FINANCE & REPORTING

### Current State Analysis
**Tables**: `company_earnings`, `daily_cost_calculation`, `tds_payable`

**DC Violations Found**:

#### V10.1: Daily Cost Aggregates
- **Issue**: Daily totals stored vs calculated
- **Fields**:
  - `daily_cost_calculation.direct_referral_total` (STORED)
  - `daily_cost_calculation.matching_referral_total` (STORED)
  - SOURCE: `pending_income` grouped by date and income_type
- **DC Status**: ✅ **ACCEPTABLE** - This is reporting cache for performance
- **Rationale**: Daily reports need fast access, computed from source on generation

#### V10.2: TDS Deduction Tracking
- **Issue**: TDS amounts in multiple places
- **Fields**:
  - `pending_income.tds_deduction` (2% per income record) - SOURCE
  - `daily_cost_calculation.tds_total` (daily aggregate) - CACHE
  - `tds_payable` table (government remittance tracking) - SEPARATE CONCERN
- **DC Status**: ✅ **COMPLIANT** - Different purposes

**Priority**: P3 (Low - reporting caches acceptable)
**Owner**: Finance Module

---

## MODULE 11: BANNERS & COMMUNICATION

### Current State Analysis
**Tables**: `banner`, `custom_banner`, `popup_message`, `birthday_message`, `user_coupon_acceptance`, `email_template`

**DC Violations Found**:

#### V11.1: Banner Display Tracking
- **Issue**: User banner interactions
- **Tables**:
  - `user_coupon_acceptance` (whether user accepted banner offer)
  - Banner display logic
- **DC Status**: ✅ **COMPLIANT** - Event tracking

**Priority**: P4 (Very Low)
**Owner**: Communications Module

---

## MODULE 12: SYSTEM CONTROL & CONFIGURATION

### Current State Analysis
**Tables**: `system_control`, `app_settings`, VGK configuration tables

**DC Violations Found**:

#### V12.1: System Configuration Overlap
- **Issue**: System settings in multiple tables
- **Tables**:
  - `system_control` (toggles, flags)
  - `app_settings` (configuration values)
- **DC Status**: ⚠️ **REVIEW NEEDED**
- **Action**: Architect review to determine if these should be merged

**Priority**: P2 (Medium)
**Owner**: System Configuration Module

---

## MODULE 13: WHATSAPP MESSAGING

### Current State Analysis
**Tables**: `whatsapp_control`, `message_log`

**DC Violations Found**:

#### V13.1: Message Delivery Tracking
- **Issue**: Message status tracking
- **Tables**:
  - `message_log` (Twilio delivery status) - SOURCE
- **DC Status**: ✅ **COMPLIANT** - Event log only

**Priority**: P4 (Very Low)
**Owner**: WhatsApp Module

---

## MODULE 14: VGK SUPREME ADMIN

### Current State Analysis
**Tables**: All tables (VGK has supreme access)

**DC Violations Found**:

#### V14.1: VGK Emergency Wallet Adjustments
- **Issue**: Manual wallet adjustments bypassing DC Protocol
- **Concern**: VGK can directly modify `user.earning_wallet` / `withdrawable_wallet`
- **DC Status**: ⚠️ **SECURITY CONCERN**
- **Fix**: Even VGK adjustments should:
  1. Create `pending_income` record with `income_type='VGK Manual Adjustment'`
  2. Let computed wallets reflect the change
  3. Maintain audit trail

**Priority**: P0 (Critical - security)
**Owner**: VGK Module

---

## MODULE 15: AUDIT & LOGGING

### Current State Analysis
**Tables**: `system_log`, `scheduler_log`, `data_change_log`, `audit_mixin`

**DC Violations Found**:

#### V15.1: Audit Trail Architecture
- **Issue**: None - logs are append-only event streams
- **DC Status**: ✅ **COMPLIANT**

**Priority**: N/A
**Owner**: Audit Module

---

## MODULE 16: SCHEDULER & AUTOMATION

### Current State Analysis
**Tables**: `scheduler_log`

**DC Violations Found**:

#### V16.1: Scheduler State Tracking
- **Issue**: Job execution state
- **Tables**:
  - APScheduler in-memory state (runtime)
  - `scheduler_log` (historical execution records)
- **DC Status**: ✅ **COMPLIANT** - Different purposes

**Priority**: N/A
**Owner**: Scheduler Module

---

## MODULE 17: RED COUPON VOTING

### Current State Analysis
**Tables**: `red_coupon_approval`, `user` (red coupon fields)

**DC Violations Found**:

#### V17.1: Red Coupon Status Duplicated
- **Issue**: Red coupon status in multiple places
- **Fields**:
  - `user.is_red_coupon` (Boolean) - DUPLICATE
  - `user.red_coupon_locked` (Boolean) - DUPLICATE
  - `red_coupon_approval.approval_status` - SOURCE
- **DC Status**: ❌ **VIOLATION**
- **Fix**:
  - DELETE `user.is_red_coupon`, `user.red_coupon_locked`
  - Compute from `red_coupon_approval` latest status

**Priority**: P2 (Medium)
**Owner**: Red Coupon Module

---

## MODULE 18: SUPPORT TICKETS

### Current State Analysis
**Tables**: `ticket`

**DC Violations Found**:

#### V18.1: Ticket Assignment Tracking
- **Issue**: None detected
- **DC Status**: ✅ **COMPLIANT**

**Priority**: N/A
**Owner**: Support Module

---

## MODULE 19: EXPENSE MANAGEMENT

### Current State Analysis
**Tables**: `expense_category`, `expense`

**DC Violations Found**:

#### V19.1: Expense Amount Tracking
- **Issue**: Expense amounts and reimbursements
- **Tables**:
  - `expense.amount` (expense recorded)
  - Reimbursement through `pending_income`?
- **DC Status**: ⚠️ **REVIEW NEEDED**
- **Action**: Verify if expense reimbursements create `pending_income` records or separate flow

**Priority**: P2 (Medium)
**Owner**: Expense Module

---

## MODULE 20: ADMIN PASSWORD RESET

### Current State Analysis
**Tables**: Uses `user` table password fields

**DC Violations Found**:

#### V20.1: Password Reset Token Tracking
- **Issue**: Already covered in Module 1
- **DC Status**: ✅ **COMPLIANT**

**Priority**: N/A
**Owner**: Admin Module

---

## SUMMARY: DC PROTOCOL VIOLATIONS BY PRIORITY

### 🔴 P0 - CRITICAL (Must Fix Immediately)
1. **V3.1**: Income amounts duplicated (pending_income vs transaction vs wallets)
2. **V4.1**: Withdrawal amounts duplicated (withdrawal_requests vs transaction vs wallets)
3. **V14.1**: VGK manual wallet adjustments bypass DC Protocol

### 🟠 P1 - HIGH (Fix in Phase 1)
4. **V1.1**: User profile fields duplicated
5. **V2.2**: Position fields duplicated (user vs placement)
6. **V5.1**: Award eligibility stored vs calculated
7. **V6.1**: Coupon status duplicated
8. **V6.2**: Package points duplicated
9. **V7.1**: KYC status duplicated
10. **V9.1**: Field allowance progress duplicated
11. **V9.2**: Field allowance payment tracking duplicated

### 🟡 P2 - MEDIUM (Fix in Phase 2)
12. **V1.2**: User status fields (review needed)
13. **V7.2**: Bank details status (review needed)
14. **V12.1**: System configuration overlap (review needed)
15. **V17.1**: Red coupon status duplicated
16. **V19.1**: Expense reimbursement flow (review needed)

### 🟢 P3 - LOW (Acceptable caches, fix later)
17. **V2.1**: Team count caching (document only)
18. **V10.1**: Daily cost aggregates (reporting cache)

### ✅ COMPLIANT MODULES
- Module 13: WhatsApp Messaging
- Module 15: Audit & Logging
- Module 16: Scheduler & Automation
- Module 18: Support Tickets

---

## ARCHITECT REVIEW REQUIRED

### Critical Questions for Architect:
1. **V3.2**: Ved Income - Should `ved_income` table be merged with `pending_income`?
2. **V7.2**: Bank Details - What is the single source for bank approval status?
3. **V7.3**: KYC Documents - Does kyc_documents duplicate user data?
4. **V12.1**: System Control - Should `system_control` and `app_settings` be merged?
5. **V19.1**: Expenses - How do expense reimbursements flow into income system?

### Migration Strategy Questions:
1. Should we use database materialized views for computed wallets?
2. Should we implement read-only triggers on legacy wallet columns?
3. What's the reconciliation threshold for shadow mode (99.9% match)?
4. How to handle VGK emergency wallet adjustments in DC-compliant way?

---

## IMPLEMENTATION PHASES WITH ARCHITECT CHECKPOINTS

### Phase 1: Critical Financial Data (P0 + High-Impact P1)
**Scope**: Modules 3, 4, 6, 9, 14
**Duration**: 2 weeks
**Architect Review**: Before, midpoint, and after

### Phase 2: User & Team Data (Remaining P1)
**Scope**: Modules 1, 2, 5, 7
**Duration**: 2 weeks
**Architect Review**: Before and after

### Phase 3: Supporting Modules (P2)
**Scope**: Modules 12, 17, 19
**Duration**: 1 week
**Architect Review**: After completion

### Phase 4: Documentation & Optimization (P3)
**Scope**: Document caching patterns, optimize queries
**Duration**: 1 week
**Architect Review**: Final review

---

**Total Violations Found**: 20+ across all modules
**Critical Violations**: 3 (financial data integrity)
**High Priority**: 8 (user data consistency)
**Modules Fully Compliant**: 4

**Status**: Complete gap matrix ready for architect review
**Last Updated**: November 2, 2025
