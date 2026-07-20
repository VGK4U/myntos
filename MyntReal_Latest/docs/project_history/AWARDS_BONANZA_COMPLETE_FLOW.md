# Awards & Bonanza Management - Complete End-to-End Flow

**Version:** 1.0  
**Last Updated:** October 28, 2025  
**Status:** System Analysis & Implementation Guide

---

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Award System Flow](#award-system-flow)
3. [Bonanza System Flow](#bonanza-system-flow)
4. [Cost Tracking & Company Impact](#cost-tracking--company-impact)
5. [Multi-Role Approval Workflow](#multi-role-approval-workflow)
6. [Current Implementation Status](#current-implementation-status)
7. [Required Enhancements](#required-enhancements)

---

## 1. System Overview

### Two Parallel Systems

| System | Type | Trigger | Payment Type |
|--------|------|---------|--------------|
| **Awards** | Automatic achievement-based | User reaches referral/matching milestones | Physical items (bikes, cars, etc.) |
| **Bonanza** | Campaign-based with eligibility | User achieves campaign targets | Cash OR Physical rewards |

### Key Difference
- **Awards**: Permanent tiers, one-time achievements
- **Bonanza**: Time-bound campaigns with eligibility criteria

---

## 2. Award System Flow

### 2.1 Award Types

#### A. Direct Awards (Referral-Based)
**Trigger:** Based on cumulative direct referral count

**Example Tiers:**
```
Tier 1: 5 referrals   → Royal Enfield Bike (₹2,00,000)
Tier 2: 10 referrals  → Honda Activa (₹80,000)
Tier 3: 25 referrals  → Maruti Swift Car (₹7,00,000)
Tier 4: 50 referrals  → Tata Nexon EV (₹15,00,000)
```

#### B. Matching Awards (Point-Based)
**Trigger:** Based on matching pairs achieved (DECIMAL POINTS)

**Point System:**
- Platinum user match = 1.0 point
- Diamond user match = 0.5 point
- Blue/Loyal match = 0 points (not counted)

**Example Tiers:**
```
Tier 1: 10 points   → Gold Coin (₹50,000)
Tier 2: 25 points   → Diamond Ring (₹1,50,000)
Tier 3: 50 points   → Gold Necklace (₹3,00,000)
Tier 4: 100 points  → Luxury Watch (₹5,00,000)
```

### 2.2 Complete Award Flow: Achievement → Delivery

#### Stage 1: ACHIEVEMENT (Automated - Daily Scheduler)

**When:** Daily at midnight (00:00 IST)

**Process:**
```python
# Scheduler Job: calculate_awards_income()
1. Bulk SQL query finds users who crossed tier thresholds
2. For each NEW achievement:
   - Create UserAwardProgress record
   - Status: 'Achieved'
   - processed_status: 'Pending'
   - current_referrals: User's total count
   - required_referrals: Tier threshold
   - award_amount: Tier price (budgeted amount)
   - achieved_at: Current timestamp
```

**Database Record Created:**
```sql
INSERT INTO user_award_progress (
    user_id,
    award_tier_id,
    current_referrals,
    required_referrals,
    award_amount,           -- Budgeted cost (₹2,00,000)
    status,                 -- 'Achieved'
    processed_status,       -- 'Pending'
    achieved_at,
    is_eligible             -- TRUE
)
```

**Cost Impact (MISSING - NEEDS IMPLEMENTATION):**
```
⚠️ CURRENTLY: No cost tracking at achievement
✅ REQUIRED: Create pending expense record

INSERT INTO company_earnings (
    expense_type: 'Awards - Pending',
    category: 'Direct Award' or 'Matching Award',
    user_id: User who achieved,
    award_tier_id: Reference to tier,
    budgeted_amount: Tier price,
    actual_cost: NULL (not yet purchased),
    status: 'Unrealized',
    achievement_date: Today,
    notes: 'User BEV1800001 achieved Tier 1 - Royal Enfield'
)
```

#### Stage 2: ADMIN VERIFICATION

**Who:** Admin role

**Actions Available:**
- ✅ **Approve** → Move to Super Admin queue
- ❌ **Reject** → End flow (user doesn't receive award)

**Process:**
```
Admin logs in → Views Pending Awards
→ Verifies user eligibility
→ Checks if user genuinely achieved milestone
→ Clicks "Approve" or "Reject"
```

**Database Update:**
```sql
UPDATE user_award_progress
SET 
    processed_status = 'Admin Approved',
    admin_approved_by = 'BEV1800002',
    admin_approved_at = CURRENT_TIMESTAMP
WHERE id = 123;
```

**Cost Impact:**
```
No change - Still unrealized expense
```

#### Stage 3: SUPER ADMIN DECISION

**Who:** Super Admin or RVZ ID

**Actions Available:**
- ✅ **Approve** → Move to Finance queue (procurement)
- ❌ **Reject** → End flow

**Process:**
```
Super Admin reviews Admin-approved awards
→ Final verification of legitimacy
→ Budget approval check
→ Clicks "SA Approve" or "Reject"
```

**Database Update:**
```sql
UPDATE user_award_progress
SET 
    processed_status = 'Super Admin Approved',
    super_admin_decision = 'approved',
    super_admin_decision_by = 'BEV1800000',
    super_admin_decision_at = CURRENT_TIMESTAMP,
    super_admin_notes = 'Approved for procurement'
WHERE id = 123;
```

**Cost Impact:**
```
Status changes from 'Unrealized' to 'Approved for Purchase'

UPDATE company_earnings
SET 
    status = 'Approved - Pending Purchase',
    approved_by = 'BEV1800000',
    approved_at = CURRENT_TIMESTAMP
WHERE award_progress_id = 123;
```

#### Stage 4: FINANCE PROCUREMENT (CRITICAL - COST TRACKING)

**Who:** Finance Admin

**Actions:**
1. **Purchase Award** from vendor
2. **Update Actual Cost** (may differ from budget)
3. **Upload Bill/Receipt**
4. **Record Payment Details**

**Process:**
```
Finance Admin logs in
→ Views "SA Approved" awards in procurement queue
→ Purchases Royal Enfield bike from dealer
→ Actual cost: ₹1,95,000 (₹5,000 less than budget)
→ Uploads dealer invoice
→ Records:
   - Vendor: "Royal Enfield Showroom"
   - Payment Mode: "Bank Transfer"
   - Reference: "INV/2025/12345"
   - Bill Upload: "invoice_RE_001.pdf"
```

**Database Update:**
```sql
UPDATE user_award_progress
SET 
    processed_status = 'Purchased - Pending Delivery',
    finance_processed_by = 'BEV1800003',
    finance_processed_at = CURRENT_TIMESTAMP,
    payment_status = 'paid',
    actual_cost_paid = 195000,              -- ✅ NEW FIELD NEEDED
    cost_variance = 5000,                   -- Budget - Actual
    cost_variance_reason = 'Dealer discount',
    vendor_name = 'RE Showroom',            -- ✅ NEW FIELD NEEDED
    payment_reference = 'INV/2025/12345',   -- ✅ NEW FIELD NEEDED
    bill_upload_path = 'uploads/...'        -- ✅ NEW FIELD NEEDED
WHERE id = 123;
```

**Cost Impact - Create ACTUAL Expense:**
```sql
-- Update pending expense to actual
UPDATE company_earnings
SET 
    status = 'Realized - Purchased',
    actual_cost = 195000,
    cost_variance = 5000,
    cost_variance_reason = 'Dealer discount',
    vendor_name = 'Royal Enfield Showroom',
    payment_mode = 'Bank Transfer',
    payment_reference = 'INV/2025/12345',
    bill_upload_path = 'uploads/awards/invoice_RE_001.pdf',
    realized_date = CURRENT_TIMESTAMP
WHERE award_progress_id = 123;

-- ALSO create record in expense table
INSERT INTO expense (
    expense_date,
    amount,                 -- ₹1,95,000 (actual)
    category,               -- 'Awards'
    description,            -- 'Direct Award Tier 1 - Royal Enfield for BEV1800001'
    vendor,                 -- 'Royal Enfield Showroom'
    payment_mode,           -- 'Bank Transfer'
    reference_no,           -- 'INV/2025/12345'
    bill_filename,          -- 'invoice_RE_001.pdf'
    created_by_id,          -- Finance Admin ID
    status,                 -- 'approved' (auto-approved)
    award_reference_id,     -- 123 (links to award progress) ✅ NEW FIELD NEEDED
    award_reference_type    -- 'Direct Award' ✅ NEW FIELD NEEDED
)
```

#### Stage 5: DELIVERY & HANDOVER

**Who:** Finance Admin or Logistics Team

**Actions:**
1. **Arrange Delivery** to user
2. **Get Delivery Proof** (signature, photo, etc.)
3. **Mark as Delivered**

**Process:**
```
Finance coordinates delivery
→ User receives Royal Enfield bike
→ User signs delivery acknowledgment
→ Photo proof captured
→ Finance marks as "Delivered"
```

**Database Update:**
```sql
UPDATE user_award_progress
SET 
    processed_status = 'Delivered - Completed',
    reward_given = TRUE,
    reward_given_date = CURRENT_TIMESTAMP,
    delivery_proof_path = 'uploads/delivery/proof_123.jpg',  -- ✅ NEW
    delivery_notes = 'Delivered to user home address',
    delivered_by = 'BEV1800003',                             -- ✅ NEW
    user_acknowledgment = TRUE                                -- ✅ NEW
WHERE id = 123;
```

**Cost Impact:**
```sql
UPDATE company_earnings
SET 
    status = 'Completed - Delivered',
    delivery_date = CURRENT_TIMESTAMP,
    final_status = 'Closed'
WHERE award_progress_id = 123;
```

### 2.3 Award Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ STAGE 1: ACHIEVEMENT (Automated)                             │
├──────────────────────────────────────────────────────────────┤
│ Daily Scheduler runs at midnight                             │
│ ↓                                                             │
│ Bulk SQL finds users who crossed thresholds                  │
│ ↓                                                             │
│ Create UserAwardProgress record                              │
│   - Status: 'Achieved'                                        │
│   - processed_status: 'Pending'                              │
│   - award_amount: ₹2,00,000 (budgeted)                       │
│ ↓                                                             │
│ ⚠️ MISSING: Create pending expense in company_earnings       │
│   - expense_type: 'Awards - Pending'                         │
│   - budgeted_amount: ₹2,00,000                               │
│   - status: 'Unrealized'                                     │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STAGE 2: ADMIN VERIFICATION                                  │
├──────────────────────────────────────────────────────────────┤
│ Admin views pending awards                                    │
│ ↓                                                             │
│ Verifies user eligibility                                     │
│ ↓                                                             │
│ Actions: ✅ Approve  OR  ❌ Reject                            │
│ ↓                                                             │
│ UPDATE processed_status = 'Admin Approved'                   │
│ ↓                                                             │
│ Cost Status: Still 'Unrealized'                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STAGE 3: SUPER ADMIN DECISION                                │
├──────────────────────────────────────────────────────────────┤
│ Super Admin reviews Admin-approved awards                     │
│ ↓                                                             │
│ Final verification + Budget check                             │
│ ↓                                                             │
│ Actions: ✅ SA Approve  OR  ❌ Reject                         │
│ ↓                                                             │
│ UPDATE processed_status = 'Super Admin Approved'             │
│ ↓                                                             │
│ UPDATE company_earnings status = 'Approved for Purchase'    │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STAGE 4: FINANCE PROCUREMENT ⚠️ CRITICAL COST TRACKING       │
├──────────────────────────────────────────────────────────────┤
│ Finance Admin purchases award from vendor                     │
│ ↓                                                             │
│ Records:                                                      │
│   - Actual cost: ₹1,95,000 (may differ from budget)          │
│   - Vendor: "Royal Enfield Showroom"                         │
│   - Payment reference: "INV/2025/12345"                      │
│   - Upload invoice/bill                                       │
│ ↓                                                             │
│ UPDATE user_award_progress:                                  │
│   - actual_cost_paid = 195000                                │
│   - cost_variance = 5000                                     │
│   - vendor_name, payment_reference                           │
│   - bill_upload_path                                          │
│ ↓                                                             │
│ UPDATE company_earnings:                                     │
│   - status = 'Realized - Purchased'                          │
│   - actual_cost = 195000                                     │
│ ↓                                                             │
│ CREATE expense record:                                       │
│   - amount = 195000                                          │
│   - category = 'Awards'                                      │
│   - vendor, payment details, bill upload                     │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STAGE 5: DELIVERY & HANDOVER                                 │
├──────────────────────────────────────────────────────────────┤
│ Finance/Logistics arranges delivery to user                   │
│ ↓                                                             │
│ User receives award (bike/car/jewelry)                        │
│ ↓                                                             │
│ Delivery proof captured (signature, photo)                    │
│ ↓                                                             │
│ UPDATE processed_status = 'Delivered - Completed'            │
│   - reward_given = TRUE                                      │
│   - delivery_proof uploaded                                   │
│ ↓                                                             │
│ UPDATE company_earnings:                                     │
│   - status = 'Completed - Delivered'                         │
│   - final_status = 'Closed'                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Bonanza System Flow

### 3.1 Bonanza Campaign Types

#### Campaign Structure
```
DynamicBonanza (Campaign)
  ├─ Start Date: Oct 1, 2025
  ├─ End Date: Dec 31, 2025
  ├─ Target: 10 direct referrals OR 20 matching points
  ├─ Eligibility: Must have 1:1 active direct + first matching
  └─ Rewards:
      ├─ Tier 1: 5 achievements  → ₹10,000 cash
      ├─ Tier 2: 10 achievements → ₹25,000 cash
      └─ Tier 3: 20 achievements → Honda Activa (₹80,000)
```

#### Reward Types
- **Cash Bonanza**: Direct payment to wallet (has Guru Dakshina 2%)
- **Physical Rewards**: Bikes, gifts, awards (NO Guru Dakshina)

### 3.2 Complete Bonanza Flow: Campaign → Claim → Delivery

#### Stage 0: CAMPAIGN CREATION (VGK/Super Admin)

**Who:** RVZ ID or Super Admin

**Process:**
```
VGK creates bonanza campaign
→ Define criteria (direct/matching targets)
→ Define rewards (cash or physical)
→ Set campaign period (start/end dates)
→ Set budget allocation
→ Status: 'Draft'
```

**Database Record:**
```sql
INSERT INTO dynamic_bonanza (
    bonanza_name,           -- "Diwali Mega Bonanza 2025"
    description,
    start_date,             -- 2025-10-01
    end_date,               -- 2025-12-31
    has_direct_target,      -- TRUE
    has_matching_target,    -- FALSE
    status,                 -- 'draft'
    total_budget_allocated, -- ₹50,00,000
    created_by              -- RVZ ID
)
```

**Rewards Definition:**
```sql
INSERT INTO dynamic_bonanza_reward (
    bonanza_id,
    reward_name,            -- "Tier 1 Cash Reward"
    criteria_type,          -- 'achievement_count'
    criteria_value,         -- 5
    criteria_operator,      -- '>='
    reward_type,            -- 'cash'
    reward_amount,          -- 10000
    is_monetary,            -- TRUE
    max_recipients          -- 100 (limit)
)
```

**Cost Impact at Creation:**
```sql
-- No expense created yet, only budget reservation
-- Budget tracked in dynamic_bonanza.total_budget_allocated
```

#### Stage 1: ACHIEVEMENT TRACKING (Daily Scheduler)

**When:** Daily at midnight (00:00 IST)

**Process:**
```python
# Scheduler: calculate_bonanza_income()
1. Find active bonanza campaigns (today between start_date and end_date)
2. For each campaign, find eligible users using Bulk SQL:
   - User has achieved target (e.g., 10 direct referrals)
   - User has NOT claimed this bonanza before
3. Check ELIGIBILITY CRITERIA:
   - Has 1:1 active direct referrals (at least 1 on each side)
   - Has first matching achieved (2:1 or 1:2 ratio)
4. If ELIGIBLE:
   - Create/Update BonanzaProgress
   - Calculate reward based on tier achieved
   - Apply METRIC DEDUCTION (prevent double benefits)
5. If NOT ELIGIBLE:
   - Create BonanzaProgress but mark as 'Locked'
```

**Database Record:**
```sql
-- User achieved target and IS eligible
INSERT INTO bonanza_progress (
    bonanza_id,
    user_id,
    reward_id,              -- Which tier reward
    current_progress,       -- 10 (direct referrals)
    achievement_status,     -- 'Achieved - Eligible'
    achieved_date,
    processed_status,       -- 'Pending'
    is_eligible             -- TRUE
)

-- User achieved target but NOT eligible
INSERT INTO bonanza_progress (
    bonanza_id,
    user_id,
    reward_id,
    current_progress,       -- 10
    achievement_status,     -- 'Locked - Requirements Not Met'
    notes,                  -- 'Missing: 1:1 active direct referrals'
    processed_status,       -- 'Locked'
    is_eligible             -- FALSE
)
```

**Metric Deduction (Prevent Double Benefits):**
```sql
-- If bonanza used 10 direct referrals for reward:
-- DEDUCT from regular Direct Award progress

UPDATE user_award_progress
SET 
    bonanza_deductions_applied = 10,
    effective_progress_count = current_referrals - 10
WHERE user_id = 'BEV1800001';

-- Record deduction in history
INSERT INTO dynamic_bonanza_history (
    user_id,
    bonanza_id,
    claimed_reward_id,
    direct_count_achieved,              -- 10
    deduction_applied_to_direct_awards, -- TRUE
    deduction_amount_direct             -- 10
)
```

**Cost Impact for ELIGIBLE Users:**
```sql
-- Create pending expense (unrealized)
INSERT INTO company_earnings (
    expense_type,           -- 'Bonanza - Pending'
    category,               -- 'Cash Bonanza' or 'Physical Bonanza'
    user_id,
    bonanza_id,
    bonanza_progress_id,    -- Reference
    budgeted_amount,        -- ₹10,000
    actual_cost,            -- NULL (not yet paid)
    status,                 -- 'Unrealized'
    achievement_date,
    notes                   -- 'Tier 1 Cash Reward for 10 referrals'
)
```

#### Stage 2: ADMIN VERIFICATION

**Who:** Admin

**Process:**
```
Admin views bonanza achievements (Pending)
→ Verifies user genuinely met criteria
→ Checks eligibility flags
→ Approves or Rejects
```

**Database Update:**
```sql
UPDATE bonanza_progress
SET 
    processed_status = 'Admin Approved',
    admin_approved_by = 'BEV1800002',
    admin_approved_at = CURRENT_TIMESTAMP
WHERE id = 456;
```

**Cost Impact:**
```
No change - Still unrealized
```

#### Stage 3: SUPER ADMIN DECISION

**Who:** Super Admin or RVZ ID

**Process:**
```
Super Admin reviews bonanza claims
→ Final verification
→ Budget check (within allocated budget?)
→ Approves or Rejects
```

**Database Update:**
```sql
UPDATE bonanza_progress
SET 
    processed_status = 'Super Admin Approved',
    super_admin_decision = 'approved',
    super_admin_decision_by = 'BEV1800000',
    super_admin_decision_at = CURRENT_TIMESTAMP
WHERE id = 456;
```

**Cost Impact:**
```sql
UPDATE company_earnings
SET 
    status = 'Approved for Payment/Purchase',
    approved_by = 'BEV1800000',
    approved_at = CURRENT_TIMESTAMP
WHERE bonanza_progress_id = 456;
```

#### Stage 4A: FINANCE PAYMENT (Cash Bonanza)

**Who:** Finance Admin

**Process:**
```
Finance processes cash payment
→ Transfer to user's wallet OR bank account
→ Record transaction reference
```

**Database Update:**
```sql
UPDATE bonanza_progress
SET 
    processed_status = 'Paid - Completed',
    finance_processed_by = 'BEV1800003',
    finance_processed_at = CURRENT_TIMESTAMP,
    payment_status = 'released',
    transaction_id = 789,               -- Reference to payment transaction
    actual_cost_paid = 10000,           -- Exact amount paid
    reward_given = TRUE,
    reward_given_date = CURRENT_TIMESTAMP
WHERE id = 456;
```

**Cost Impact:**
```sql
-- Update company_earnings
UPDATE company_earnings
SET 
    status = 'Realized - Paid',
    actual_cost = 10000,
    cost_variance = 0,                  -- Budget matched
    payment_reference = 'TXN/2025/67890',
    realized_date = CURRENT_TIMESTAMP
WHERE bonanza_progress_id = 456;

-- Create expense record
INSERT INTO expense (
    expense_date,
    amount,                 -- ₹10,000
    category,               -- 'Bonanza - Cash'
    description,            -- 'Tier 1 Cash Bonanza for BEV1800001'
    payment_mode,           -- 'Wallet Credit' or 'Bank Transfer'
    reference_no,           -- 'TXN/2025/67890'
    created_by_id,
    status,                 -- 'approved'
    bonanza_reference_id,   -- 456 ✅ NEW FIELD
    bonanza_reference_type  -- 'Cash Bonanza' ✅ NEW FIELD
)
```

#### Stage 4B: FINANCE PROCUREMENT (Physical Bonanza)

**Same as Award Stage 4** - Purchase item, record actual cost, upload bill

**Process:**
```
Finance purchases Honda Activa from dealer
→ Actual cost: ₹78,000
→ Upload invoice
→ Record vendor details
```

**Database Update:**
```sql
UPDATE bonanza_progress
SET 
    processed_status = 'Purchased - Pending Delivery',
    finance_processed_by = 'BEV1800003',
    finance_processed_at = CURRENT_TIMESTAMP,
    payment_status = 'paid',
    actual_cost_paid = 78000,
    budgeted_amount = 80000,
    cost_variance = 2000,
    cost_variance_reason = 'Dealer discount',
    vendor_name = 'Honda Showroom',     -- ✅ NEW
    payment_reference = 'INV/2025/54321'
WHERE id = 456;
```

**Cost Impact:**
```sql
-- Same as Award procurement
UPDATE company_earnings + CREATE expense
```

#### Stage 5: DELIVERY (Physical Bonanza Only)

**Same as Award Stage 5** - Deliver to user, capture proof

---

## 4. Cost Tracking & Company Impact

### 4.1 Current State (What Exists)

**CompanyEarnings Table:**
- ✅ Tracks daily ceiling excess (Ved + Matching income > ₹50k)
- ✅ Tracks admin deductions (8%)
- ✅ Tracks TDS deductions (2%)
- ❌ Does NOT track Awards costs
- ❌ Does NOT track Bonanza costs

**Expense Table:**
- ✅ Tracks regular company expenses
- ✅ Categories: Office, Travel, Salaries, etc.
- ❌ Does NOT integrate with Awards
- ❌ Does NOT integrate with Bonanza

### 4.2 Required State (What's Needed)

#### A. Expand CompanyEarnings to Track ALL Financial Impact

**New Fields Needed:**
```sql
ALTER TABLE company_earnings ADD COLUMN:
    expense_type VARCHAR(50),           -- 'Income Ceiling', 'Awards', 'Bonanza'
    category VARCHAR(50),               -- 'Direct Award', 'Cash Bonanza', etc.
    reference_type VARCHAR(50),         -- 'award_progress', 'bonanza_progress'
    reference_id INTEGER,               -- Links to specific record
    budgeted_amount NUMERIC(15,2),      -- Original budget
    actual_cost NUMERIC(15,2),          -- Actual cost paid
    cost_variance NUMERIC(15,2),        -- Difference
    cost_variance_reason TEXT,
    status VARCHAR(30),                 -- 'Unrealized', 'Approved', 'Realized'
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    achievement_date DATE,
    approved_by VARCHAR(12),
    approved_at TIMESTAMP,
    realized_date TIMESTAMP
```

#### B. Link Expense Table to Awards/Bonanza

**New Fields in Expense Table:**
```sql
ALTER TABLE expense ADD COLUMN:
    award_reference_id INTEGER,         -- Links to user_award_progress
    award_reference_type VARCHAR(50),   -- 'Direct Award', 'Matching Award'
    bonanza_reference_id INTEGER,       -- Links to bonanza_progress
    bonanza_reference_type VARCHAR(50)  -- 'Cash Bonanza', 'Physical Bonanza'
```

#### C. Add Cost Fields to Award/Bonanza Progress Tables

**UserAwardProgress:**
```sql
ALTER TABLE user_award_progress ADD COLUMN:
    actual_cost_paid NUMERIC(12,2),
    budgeted_amount NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    vendor_name VARCHAR(255),
    payment_reference VARCHAR(255),
    payment_mode VARCHAR(50),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12),
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN
```

**BonanzaProgress:**
```sql
-- Already has some fields, add missing:
ALTER TABLE bonanza_progress ADD COLUMN:
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12),
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN
```

### 4.3 Complete Cost Flow

```
┌─────────────────────────────────────────────────────────────┐
│ ACHIEVEMENT                                                  │
│ Budget Reserved: ₹2,00,000                                   │
│                                                              │
│ company_earnings:                                           │
│   expense_type: 'Awards - Pending'                          │
│   budgeted_amount: 200000                                   │
│   actual_cost: NULL                                         │
│   status: 'Unrealized'                                      │
│                                                              │
│ Company P&L Impact: -₹2,00,000 (unrealized expense)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ADMIN APPROVAL                                               │
│ No cost change - Still unrealized                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPER ADMIN APPROVAL                                         │
│ Budget confirmed for purchase                                │
│                                                              │
│ company_earnings:                                           │
│   status: 'Approved for Purchase'                           │
│   approved_by: 'BEV1800000'                                 │
│                                                              │
│ Company P&L Impact: Still -₹2,00,000 (unrealized)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FINANCE PROCUREMENT                                          │
│ Actual Purchase: ₹1,95,000 (₹5k less than budget)           │
│                                                              │
│ company_earnings:                                           │
│   status: 'Realized - Purchased'                            │
│   actual_cost: 195000                                       │
│   cost_variance: 5000 (saved)                               │
│   realized_date: Today                                      │
│                                                              │
│ expense table:                                              │
│   amount: 195000                                            │
│   category: 'Awards'                                        │
│   status: 'approved'                                        │
│   award_reference_id: 123                                   │
│                                                              │
│ Company P&L Impact: -₹1,95,000 (realized expense)           │
│ Budget Saving: +₹5,000                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ DELIVERY                                                     │
│ Item delivered to user                                       │
│                                                              │
│ company_earnings:                                           │
│   status: 'Completed - Delivered'                           │
│   delivery_date: Today                                      │
│   final_status: 'Closed'                                    │
│                                                              │
│ Company P&L Impact: Final = -₹1,95,000                      │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Reporting & Analytics

#### Daily Cost Summary Report

**Query Structure:**
```sql
SELECT 
    expense_type,
    category,
    COUNT(*) as total_count,
    SUM(budgeted_amount) as total_budgeted,
    SUM(actual_cost) as total_actual,
    SUM(cost_variance) as total_variance,
    SUM(CASE WHEN status = 'Unrealized' THEN budgeted_amount ELSE 0 END) as pending_expenses,
    SUM(CASE WHEN status LIKE '%Realized%' THEN actual_cost ELSE 0 END) as realized_expenses
FROM company_earnings
WHERE achievement_date = CURRENT_DATE
GROUP BY expense_type, category;
```

**Example Output:**
```
expense_type     | category         | total_count | total_budgeted | total_actual | total_variance | pending_expenses | realized_expenses
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Awards - Pending | Direct Award     | 5           | 1000000        | 0            | 0              | 1000000          | 0
Awards - Pending | Matching Award   | 3           | 500000         | 0            | 0              | 500000           | 0
Bonanza - Pending| Cash Bonanza     | 10          | 100000         | 0            | 0              | 100000           | 0
Awards           | Direct Award     | 2           | 400000         | 385000       | 15000          | 0                | 385000
Bonanza          | Physical Bonanza | 1           | 80000          | 78000        | 2000           | 0                | 78000
```

#### P&L Impact Dashboard

**Categories:**
```
INCOME SIDE:
✅ User Earnings (Direct, Matching, Ved, Guru Dakshina)
✅ Admin Deductions (8% of all income)
✅ TDS Collections (2% of all income)
✅ Ceiling Excess (Ved + Matching > ₹50k daily limit)

EXPENSE SIDE:
✅ Operational Expenses (Office, Salaries, etc.)
✅ Awards Costs (Direct + Matching)          ← NEW
✅ Bonanza Costs (Cash + Physical)           ← NEW
```

**Report Format:**
```
COMPANY EARNINGS SUMMARY
Date: October 28, 2025

INCOME:
  Admin Deductions:          ₹5,00,000
  TDS Collections:           ₹1,25,000
  Ceiling Excess:            ₹2,00,000
  ───────────────────────────────────
  Total Income:              ₹8,25,000

EXPENSES:
  Operational:               ₹3,00,000
  Awards (Realized):         ₹3,85,000     ← NEW
  Bonanza (Realized):        ₹78,000       ← NEW
  ───────────────────────────────────
  Total Realized Expenses:   ₹7,63,000

PENDING EXPENSES (Unrealized):
  Awards Pending:            ₹15,00,000    ← NEW
  Bonanza Pending:           ₹1,00,000     ← NEW
  ───────────────────────────────────
  Total Pending:             ₹16,00,000

NET POSITION:
  Current Net:               ₹62,000 (Income - Realized Expenses)
  If All Pending Realized:   -₹15,38,000 (potential liability)
```

---

## 5. Multi-Role Approval Workflow

### 5.1 Role-Based Powers

| Role | Awards | Bonanza | Actions |
|------|--------|---------|---------|
| **Admin** | ✅ View All<br/>✅ Approve (Pending→Admin Approved)<br/>❌ Reject | ✅ View All<br/>✅ Approve (Pending→Admin Approved)<br/>❌ Reject | Verification only |
| **Super Admin** | ✅ All Admin Powers<br/>✅ SA Approve (Admin Approved→SA Approved)<br/>✅ Reject at any stage<br/>✅ Budget Override | ✅ All Admin Powers<br/>✅ SA Approve<br/>✅ Reject<br/>✅ Budget Override | Final decision + Budget |
| **Finance Admin** | ✅ View SA Approved<br/>✅ Purchase & Record Cost<br/>✅ Upload Bills<br/>✅ Mark Delivered | ✅ View SA Approved<br/>✅ Pay Cash/Purchase Physical<br/>✅ Record Cost<br/>✅ Mark Delivered | Procurement & Payment |
| **RVZ ID** | ✅ Supreme Powers<br/>✅ All SA Powers<br/>✅ Override Any Status<br/>✅ Budget Management | ✅ Supreme Powers<br/>✅ Create Campaigns<br/>✅ All SA Powers<br/>✅ Override | Supreme oversight |

### 5.2 Status Transition Rules

**Awards:**
```
Achieved (Auto)
   ↓ Admin: Approve
Admin Approved
   ↓ SA: Approve
Super Admin Approved
   ↓ Finance: Purchase + Record Cost
Purchased - Pending Delivery
   ↓ Finance: Mark Delivered
Delivered - Completed

At any stage before Delivery:
   ↓ Admin/SA/VGK: Reject
Rejected (End)
```

**Bonanza:**
```
Achieved - Eligible (Auto)
   ↓ Admin: Approve
Admin Approved
   ↓ SA: Approve
Super Admin Approved
   ↓ Finance: Pay (Cash) OR Purchase (Physical)
Paid/Purchased
   ↓ Finance: Mark Delivered (Physical only)
Completed

Locked Status (Not eligible):
   User shown as "Locked - Requirements Not Met"
   Once eligible criteria met → Automatically moves to Pending
```

---

## 6. Current Implementation Status

### ✅ What's Working

1. **Achievement Detection**
   - ✅ Daily scheduler calculates awards
   - ✅ Daily scheduler calculates bonanza eligibility
   - ✅ Bulk SQL optimization (50x faster)
   - ✅ Metric deduction logic (prevent double benefits)

2. **Database Models**
   - ✅ UserAwardProgress table
   - ✅ UserMatchingAwardProgress table
   - ✅ BonanzaProgress table
   - ✅ DynamicBonanza & Rewards tables

3. **Approval Workflow Fields**
   - ✅ Multi-role approval tracking
   - ✅ Admin/SA/Finance approval fields
   - ✅ Status transitions

4. **Cost Variance Tracking**
   - ✅ BonanzaProgress has budgeted_amount, actual_cost_paid
   - ✅ Cost variance fields exist

### ❌ What's Missing (CRITICAL)

1. **Cost Tracking Integration**
   - ❌ NO integration with CompanyEarnings at achievement
   - ❌ NO pending expense creation
   - ❌ NO expense table linkage

2. **Procurement Workflow**
   - ❌ NO vendor management
   - ❌ NO bill upload functionality
   - ❌ NO payment reference tracking
   - ❌ Missing fields: vendor_name, payment_mode, bill_upload_path

3. **Delivery Management**
   - ❌ NO delivery proof capture
   - ❌ NO user acknowledgment tracking
   - ❌ Missing fields: delivered_by, delivery_proof_path

4. **Reporting**
   - ❌ NO Award costs in company earnings
   - ❌ NO Bonanza costs in company earnings
   - ❌ NO P&L impact dashboard
   - ❌ NO unrealized expense tracking

---

## 7. Required Enhancements

### Phase 1: Database Schema Updates

**Priority: CRITICAL**

```sql
-- 1. Expand company_earnings for Awards/Bonanza tracking
ALTER TABLE company_earnings ADD COLUMN
    expense_type VARCHAR(50),
    category VARCHAR(50),
    reference_type VARCHAR(50),
    reference_id INTEGER,
    budgeted_amount NUMERIC(15,2),
    actual_cost NUMERIC(15,2),
    cost_variance NUMERIC(15,2),
    cost_variance_reason TEXT,
    status VARCHAR(30),
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    achievement_date DATE,
    approved_by VARCHAR(12),
    approved_at TIMESTAMP,
    realized_date TIMESTAMP,
    delivery_date TIMESTAMP,
    final_status VARCHAR(30);

-- 2. Link expense table to Awards/Bonanza
ALTER TABLE expense ADD COLUMN
    award_reference_id INTEGER,
    award_reference_type VARCHAR(50),
    bonanza_reference_id INTEGER,
    bonanza_reference_type VARCHAR(50);

-- 3. Add procurement fields to user_award_progress
ALTER TABLE user_award_progress ADD COLUMN
    actual_cost_paid NUMERIC(12,2),
    budgeted_amount NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    vendor_name VARCHAR(255),
    payment_reference VARCHAR(255),
    payment_mode VARCHAR(50),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12),
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN;

-- 4. Add procurement fields to bonanza_progress
ALTER TABLE bonanza_progress ADD COLUMN
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12),
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN;

-- 5. Add procurement fields to user_matching_award_progress
ALTER TABLE user_matching_award_progress ADD COLUMN
    actual_cost_paid NUMERIC(12,2),
    budgeted_amount NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    vendor_name VARCHAR(255),
    payment_reference VARCHAR(255),
    payment_mode VARCHAR(50),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12),
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN;
```

### Phase 2: Scheduler Integration

**Update:** `calculate_awards_income()` and `calculate_bonanza_income()`

**Add after creating progress records:**
```python
# Create pending expense in company_earnings
company_expense = CompanyEarnings(
    expense_type='Awards - Pending',
    category='Direct Award' if award_type == 'direct' else 'Matching Award',
    reference_type='user_award_progress',
    reference_id=new_progress.id,
    user_id=user_id,
    budgeted_amount=award_amount,
    actual_cost=None,
    status='Unrealized',
    achievement_date=business_date,
    description=f"{award_name} achieved by {user_id}"
)
db.add(company_expense)
```

### Phase 3: Finance Procurement UI

**New Pages Needed:**
1. `/finance/awards/procurement` - Purchase awards
2. `/finance/bonanza/procurement` - Purchase bonanza rewards
3. `/finance/delivery/management` - Track deliveries

**Features:**
- Upload bill/invoice (PDF, images)
- Record vendor details
- Enter actual cost paid
- Payment reference entry
- Delivery proof upload
- User acknowledgment capture

### Phase 4: Reporting Dashboard

**New Reports:**
1. **Cost Summary Dashboard**
   - Total pending expenses (unrealized)
   - Total realized expenses
   - Budget vs actual variance
   - Category-wise breakdown

2. **P&L Impact Report**
   - Income side (deductions, ceiling excess)
   - Expense side (operational + awards + bonanza)
   - Net position
   - Pending liability

3. **Award/Bonanza Analytics**
   - Most expensive awards delivered
   - Cost variance trends
   - Budget utilization %
   - Delivery timeline metrics

---

## 8. Summary

### Complete Flow at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWARDS & BONANZA LIFECYCLE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. ACHIEVEMENT (Automated - Scheduler)                          │
│    ├─ User crosses threshold                                    │
│    ├─ Create progress record (status: Achieved)                 │
│    └─ ✅ CREATE pending expense in company_earnings             │
│                                                                  │
│ 2. ADMIN VERIFICATION                                            │
│    ├─ Admin reviews achievement                                 │
│    ├─ Approve → Admin Approved                                  │
│    └─ Cost status: Still unrealized                             │
│                                                                  │
│ 3. SUPER ADMIN DECISION                                          │
│    ├─ Final verification + budget check                         │
│    ├─ Approve → Super Admin Approved                            │
│    └─ ✅ UPDATE expense status: Approved for Purchase           │
│                                                                  │
│ 4. FINANCE PROCUREMENT                                           │
│    ├─ Purchase from vendor (Awards/Physical Bonanza)            │
│    ├─ OR Process payment (Cash Bonanza)                         │
│    ├─ Record actual cost                                        │
│    ├─ Upload bill/invoice                                        │
│    ├─ ✅ UPDATE expense status: Realized                        │
│    └─ ✅ CREATE expense table record                            │
│                                                                  │
│ 5. DELIVERY & COMPLETION                                         │
│    ├─ Deliver to user                                           │
│    ├─ Capture delivery proof                                    │
│    ├─ User acknowledgment                                       │
│    └─ ✅ UPDATE expense status: Completed - Delivered           │
│                                                                  │
│ COST TRACKING AT EACH STAGE:                                    │
│ ├─ Achievement: Unrealized expense (budget reserved)            │
│ ├─ Admin: No change                                             │
│ ├─ SA: Approved for purchase                                    │
│ ├─ Finance: Realized expense (actual cost recorded)             │
│ └─ Delivery: Completed (final cost confirmed)                   │
│                                                                  │
│ COMPANY P&L IMPACT:                                             │
│ └─ All awards/bonanza costs tracked in company_earnings         │
│    Shown as unrealized → approved → realized → completed        │
└─────────────────────────────────────────────────────────────────┘
```

---

**Document Status:** ✅ Complete Analysis  
**Implementation Status:** 🔴 Requires Database & Code Changes  
**Priority:** HIGH - Cost tracking is critical for financial management
