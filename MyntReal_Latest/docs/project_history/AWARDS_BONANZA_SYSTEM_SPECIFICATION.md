# Awards & Bonanza Management System - Complete Specification

**Version:** 2.0  
**Last Updated:** October 28, 2025  
**Protocols:** WV (Withdrawal-Validation), DC (Data Consistency)

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Database Schema](#database-schema)
3. [Cost Tracking States](#cost-tracking-states)
4. [Multi-Role Access Control](#multi-role-access-control)
5. [Frontend Views by Role](#frontend-views-by-role)
6. [API Endpoints](#api-endpoints)
7. [Implementation Protocols](#implementation-protocols)

---

## 1. System Overview

### Core Principles

#### WV Protocol (Withdrawal-Validation)
- **Awards/Bonanza**: NET amount at achievement = final payout
- **NO additional deductions** at delivery stage
- **Budgeted amount** shown to Finance/VGK for procurement
- **Actual cost** tracked for variance analysis

#### DC Protocol (Data Consistency)
- **Single Source of Truth**:
  - Award/Bonanza Progress tables → Achievement & Approval status
  - Expense table → Procurement & Cost tracking
  - User tables → Metric deduction tracking
- **No duplicate data** across tables

### Three-State Cost Model

| State | Description | Visibility | Impact |
|-------|-------------|------------|--------|
| **Achieved (Pending)** | User achieved, awaiting procurement | Finance/VGK only | Cost Impact (unrealized) |
| **Purchased (In-Transit)** | Item purchased, awaiting delivery | Finance/VGK only | Cost Impact (unrealized) |
| **Delivered (Incurred)** | User received item | All roles | Cost Incurred (realized) |

---

## 2. Database Schema

### 2.1 UserAwardProgress (Direct Awards)

```sql
CREATE TABLE user_award_progress (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(12) REFERENCES "user"(id),
    award_tier_id INTEGER REFERENCES direct_award_tier(id),
    
    -- Progress tracking
    current_referrals INTEGER DEFAULT 0,
    required_referrals INTEGER NOT NULL,
    award_amount NUMERIC(12,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'In Progress',
    
    -- Achievement dates
    achieved_at TIMESTAMP,
    awarded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Eligibility
    is_eligible BOOLEAN DEFAULT TRUE,
    processed_date TIMESTAMP,
    processed_by VARCHAR(12),
    admin_notes TEXT,
    
    -- Bonanza tracking (metric deduction)
    achieved_via_bonanza BOOLEAN DEFAULT FALSE,
    bonanza_name VARCHAR(255),
    bonanza_deductions_applied INTEGER DEFAULT 0,
    
    -- Cumulative tracking
    cumulative_target_adjustment INTEGER DEFAULT 0,
    effective_progress_count INTEGER DEFAULT 0,
    lifetime_achievement_status VARCHAR(50) DEFAULT 'Active',
    achievement_date TIMESTAMP,
    initial_qualification_met BOOLEAN DEFAULT FALSE,
    requires_balanced_growth BOOLEAN DEFAULT FALSE,
    
    -- Verification status
    award_status VARCHAR(50) DEFAULT 'pending',
    processed_status VARCHAR(50) DEFAULT 'Pending',
    
    -- Multi-role approval tracking
    admin_approved_by VARCHAR(12),
    admin_approved_at TIMESTAMP,
    
    super_admin_decision_by VARCHAR(12),
    super_admin_decision_at TIMESTAMP,
    super_admin_decision VARCHAR(50),  -- 'approved', 'rejected'
    super_admin_notes TEXT,
    
    finance_processed_by VARCHAR(12),
    finance_processed_at TIMESTAMP,
    payment_status VARCHAR(50),  -- 'queued', 'released', 'failed'
    transaction_id INTEGER,
    
    vgk_action_by VARCHAR(12),
    vgk_action_at TIMESTAMP,
    vgk_action_type VARCHAR(50),  -- 'override', 'hold', 'release'
    vgk_notes TEXT,
    
    -- ✅ NEW: Cost variance tracking
    budgeted_amount NUMERIC(12,2),
    actual_cost_paid NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    
    -- ✅ NEW: Procurement fields
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    
    -- ✅ NEW: Delivery tracking
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE,
    
    -- Batch processing
    bulk_batch_id VARCHAR(255),
    rejection_reason TEXT
);
```

### 2.2 UserMatchingAwardProgress (Matching Awards)

```sql
CREATE TABLE user_matching_award_progress (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(12) REFERENCES "user"(id),
    matching_award_tier_id INTEGER REFERENCES matching_award_tier(id),
    
    -- Progress tracking
    current_matches INTEGER DEFAULT 0,
    required_matches INTEGER DEFAULT 0,
    is_eligible BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'Pending',
    
    -- Processing
    processed_date TIMESTAMP,
    processed_by VARCHAR(12),
    admin_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Bonanza tracking
    achieved_via_bonanza BOOLEAN DEFAULT FALSE,
    bonanza_name VARCHAR(255),
    bonanza_deductions_applied INTEGER DEFAULT 0,
    
    -- Cumulative tracking
    cumulative_target_adjustment INTEGER DEFAULT 0,
    effective_progress_count INTEGER DEFAULT 0,
    lifetime_achievement_status VARCHAR(50) DEFAULT 'Active',
    achievement_date TIMESTAMP,
    initial_qualification_met BOOLEAN DEFAULT FALSE,
    requires_balanced_growth BOOLEAN DEFAULT FALSE,
    qualification_start_date TIMESTAMP,
    
    -- Verification status
    award_status VARCHAR(50) DEFAULT 'pending',
    processed_status VARCHAR(50) DEFAULT 'Pending',
    
    -- Multi-role approval tracking
    admin_approved_by VARCHAR(12),
    admin_approved_at TIMESTAMP,
    
    super_admin_decision_by VARCHAR(12),
    super_admin_decision_at TIMESTAMP,
    super_admin_decision VARCHAR(50),
    super_admin_notes TEXT,
    
    finance_processed_by VARCHAR(12),
    finance_processed_at TIMESTAMP,
    payment_status VARCHAR(50),
    transaction_id INTEGER,
    
    vgk_action_by VARCHAR(12),
    vgk_action_at TIMESTAMP,
    vgk_action_type VARCHAR(50),
    vgk_notes TEXT,
    
    -- ✅ NEW: Cost variance tracking
    budgeted_amount NUMERIC(12,2),
    actual_cost_paid NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    
    -- ✅ NEW: Procurement fields
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    
    -- ✅ NEW: Delivery tracking
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE,
    
    -- Batch processing
    bulk_batch_id VARCHAR(255),
    rejection_reason TEXT
);
```

### 2.3 BonanzaProgress (Bonanza Rewards)

```sql
CREATE TABLE bonanza_progress (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    bonanza_id INTEGER REFERENCES dynamic_bonanza(id),
    user_id VARCHAR(12) REFERENCES "user"(id),
    reward_id INTEGER REFERENCES dynamic_bonanza_reward(id),
    
    -- Progress tracking
    current_progress INTEGER DEFAULT 0,
    achievement_status VARCHAR(50) DEFAULT 'In Progress',
    achieved_date TIMESTAMP,
    
    -- Delivery/Processing tracking
    reward_given BOOLEAN DEFAULT FALSE,
    reward_given_date TIMESTAMP,
    processed_status VARCHAR(50) DEFAULT 'Pending',
    processed_date TIMESTAMP,
    processed_by VARCHAR(12),
    
    -- Notes
    notes TEXT,
    admin_notes TEXT,
    
    -- Multi-role approval tracking
    admin_approved_by VARCHAR(12),
    admin_approved_at TIMESTAMP,
    
    super_admin_decision_by VARCHAR(12),
    super_admin_decision_at TIMESTAMP,
    super_admin_decision VARCHAR(50),
    super_admin_notes TEXT,
    
    finance_processed_by VARCHAR(12),
    finance_processed_at TIMESTAMP,
    payment_status VARCHAR(50),
    transaction_id INTEGER,
    
    vgk_action_by VARCHAR(12),
    vgk_action_at TIMESTAMP,
    vgk_action_type VARCHAR(50),
    vgk_notes TEXT,
    
    -- ✅ NEW: Cost variance tracking
    budgeted_amount NUMERIC(12,2),
    actual_cost_paid NUMERIC(12,2),
    cost_variance NUMERIC(12,2),
    cost_variance_reason TEXT,
    
    -- ✅ NEW: Procurement fields
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    
    -- ✅ NEW: Delivery tracking
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE,
    
    -- Batch processing
    bulk_batch_id VARCHAR(255),
    rejection_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.4 Expense (Updated with Award/Bonanza Linkage)

```sql
CREATE TABLE expense (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Core expense details
    expense_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    category VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    vendor VARCHAR(200),
    
    -- Payment details
    payment_mode VARCHAR(20) NOT NULL,
    reference_no VARCHAR(100),
    
    -- Bill upload details
    bill_filename VARCHAR(255),
    bill_mime_type VARCHAR(100),
    bill_size INTEGER,
    
    -- ✅ NEW: Award/Bonanza linkage
    award_reference_id INTEGER,  -- Links to user_award_progress or user_matching_award_progress
    award_reference_type VARCHAR(50),  -- 'Direct Award', 'Matching Award'
    bonanza_reference_id INTEGER,  -- Links to bonanza_progress
    bonanza_reference_type VARCHAR(50),  -- 'Cash Bonanza', 'Physical Bonanza'
    
    -- User relationships and workflow
    created_by_id VARCHAR(12) REFERENCES "user"(id),
    approved_by_id VARCHAR(12) REFERENCES "user"(id),
    
    -- Status and workflow
    status VARCHAR(20) DEFAULT 'pending',
    approved_at TIMESTAMP,
    notes TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**New Expense Categories:**
- `Awards - Direct`
- `Awards - Matching`
- `Bonanza - Cash`
- `Bonanza - Physical`

---

## 3. Cost Tracking States

### State Machine Flow

```
┌──────────────────────────────────────────────────────────┐
│ STATE 1: ACHIEVED (PENDING)                              │
├──────────────────────────────────────────────────────────┤
│ Trigger: Scheduler detects achievement                   │
│ Status: processed_status = 'Achieved - Pending Admin'    │
│                                                           │
│ Data Created:                                            │
│ ├─ UserAwardProgress/BonanzaProgress record             │
│ │  └─ budgeted_amount = tier_price                      │
│ └─ NO expense record yet                                │
│                                                           │
│ Cost Impact: PENDING (unrealized)                        │
│ Visibility: Finance/VGK see budgeted amount             │
└──────────────────────────────────────────────────────────┘
                        ↓ Admin Approves
┌──────────────────────────────────────────────────────────┐
│ STATE 2: ADMIN APPROVED                                  │
├──────────────────────────────────────────────────────────┤
│ Trigger: Admin clicks "Approve"                          │
│ Status: processed_status = 'Admin Approved'              │
│                                                           │
│ Data Updated:                                            │
│ └─ admin_approved_by, admin_approved_at                 │
│                                                           │
│ Cost Impact: PENDING (unrealized)                        │
│ Visibility: Finance/VGK see budgeted amount             │
└──────────────────────────────────────────────────────────┘
                        ↓ Super Admin Approves
┌──────────────────────────────────────────────────────────┐
│ STATE 3: SUPER ADMIN APPROVED                            │
├──────────────────────────────────────────────────────────┤
│ Trigger: Super Admin clicks "Approve"                    │
│ Status: processed_status = 'Super Admin Approved'        │
│                                                           │
│ Data Updated:                                            │
│ └─ super_admin_decision_by, super_admin_decision_at     │
│                                                           │
│ Cost Impact: APPROVED FOR PURCHASE (unrealized)          │
│ Visibility: Finance queue for procurement               │
└──────────────────────────────────────────────────────────┘
                        ↓ Finance Purchases
┌──────────────────────────────────────────────────────────┐
│ STATE 4: PURCHASED (IN-TRANSIT)                          │
├──────────────────────────────────────────────────────────┤
│ Trigger: Finance records purchase                        │
│ Status: processed_status = 'Purchased - Pending Delivery'│
│                                                           │
│ Data Updated:                                            │
│ ├─ actual_cost_paid = actual_amount                     │
│ ├─ cost_variance = budgeted - actual                    │
│ ├─ vendor_name, payment_mode, payment_reference         │
│ ├─ bill_upload_path                                      │
│ └─ finance_processed_by, finance_processed_at           │
│                                                           │
│ Expense Record Created:                                  │
│ ├─ category = 'Awards - Direct' (or relevant)           │
│ ├─ amount = actual_cost_paid                            │
│ ├─ award_reference_id = progress.id                     │
│ ├─ vendor, payment_mode, reference_no                   │
│ └─ bill_filename, bill_mime_type                        │
│                                                           │
│ Cost Impact: INCURRED (realized - item purchased)        │
│ Visibility: Finance/VGK see actual cost                 │
└──────────────────────────────────────────────────────────┘
                        ↓ Finance Delivers
┌──────────────────────────────────────────────────────────┐
│ STATE 5: DELIVERED (COMPLETED)                           │
├──────────────────────────────────────────────────────────┤
│ Trigger: Finance marks as delivered                       │
│ Status: processed_status = 'Delivered - Completed'       │
│                                                           │
│ Data Updated:                                            │
│ ├─ reward_given = TRUE                                  │
│ ├─ reward_given_date = NOW()                            │
│ ├─ delivered_by, delivered_at                           │
│ ├─ delivery_proof_path                                   │
│ └─ user_acknowledgment = TRUE                           │
│                                                           │
│ Cost Impact: COMPLETED (realized - delivered to user)    │
│ Visibility: All roles see delivery status               │
└──────────────────────────────────────────────────────────┘
```

### Cost Impact Summary

| State | DB Status | Cost Impact | Shown To | Amount Field |
|-------|-----------|-------------|----------|--------------|
| Achieved | `Achieved - Pending Admin` | Pending (Unrealized) | Finance/VGK | budgeted_amount |
| Admin Approved | `Admin Approved` | Pending (Unrealized) | Finance/VGK | budgeted_amount |
| SA Approved | `Super Admin Approved` | Approved for Purchase | Finance/VGK | budgeted_amount |
| Purchased | `Purchased - Pending Delivery` | **Incurred** (Realized) | Finance/VGK | actual_cost_paid |
| Delivered | `Delivered - Completed` | **Completed** | All | actual_cost_paid |

**Note:** Cost becomes "Incurred" at PURCHASE stage, NOT at delivery. Delivery just confirms completion.

---

## 4. Multi-Role Access Control

### Role Permissions Matrix

| Feature | Admin | Super Admin | Finance Admin | RVZ ID |
|---------|-------|-------------|---------------|--------|
| **View Achievements** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **View User Details** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Status** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **View Cost Data** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **View Budgeted Amount** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **View Actual Cost** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **View Vendor Details** | ❌ NO | ❌ NO | ✅ YES | ✅ YES |
| **Approve (Admin)** | ✅ Yes | ✅ Yes | ❌ NO | ✅ Yes |
| **Approve (SA)** | ❌ NO | ✅ Yes | ❌ NO | ✅ Yes |
| **Purchase/Pay** | ❌ NO | ❌ NO | ✅ YES | ✅ Yes |
| **Upload Bills** | ❌ NO | ❌ NO | ✅ YES | ✅ Yes |
| **Mark Delivered** | ❌ NO | ❌ NO | ✅ YES | ✅ Yes |
| **Override Any** | ❌ NO | ❌ NO | ❌ NO | ✅ YES |

### Data Visibility Rules

#### Admin & Super Admin Views
```javascript
// Fields VISIBLE to Admin/SA
{
  id,
  user_id,
  user_name,
  award_tier_name,
  current_progress,
  required_target,
  achieved_date,
  processed_status,
  admin_approved_by,
  admin_approved_at,
  super_admin_decision,
  super_admin_decision_by,
  super_admin_decision_at,
  reward_given,
  reward_given_date,
  // ❌ NO COST DATA
}
```

#### Finance Admin & VGK Views
```javascript
// Fields VISIBLE to Finance/VGK (ALL FIELDS)
{
  id,
  user_id,
  user_name,
  award_tier_name,
  current_progress,
  required_target,
  achieved_date,
  processed_status,
  admin_approved_by,
  admin_approved_at,
  super_admin_decision,
  super_admin_decision_by,
  super_admin_decision_at,
  // ✅ COST DATA
  budgeted_amount,
  actual_cost_paid,
  cost_variance,
  cost_variance_reason,
  vendor_name,
  payment_mode,
  payment_reference,
  bill_upload_path,
  delivered_by,
  delivered_at,
  delivery_proof_path,
  reward_given,
  reward_given_date
}
```

---

## 5. Frontend Views by Role

### 5.1 Admin View: `/admin/awards/direct`

**Purpose:** Verify direct award achievements and approve for Super Admin review

**Visible Columns:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Direct Awards - Pending Admin Approval                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Filters: [Date Range ▼] [Status ▼] [Award Type ▼] [Search User]           │
├─────┬──────────┬──────────────┬──────────┬─────────────┬────────┬──────────┤
│ ID  │ User     │ Award        │ Progress │ Achieved    │ Status │ Actions  │
├─────┼──────────┼──────────────┼──────────┼─────────────┼────────┼──────────┤
│ 123 │ BEV18001 │ Royal Enfield│ 10/10    │ Oct 25 2025 │ Pending│ [Approve]│
│     │ John Doe │ Bike         │ ✅        │ 2:30 PM     │        │ [Reject] │
├─────┼──────────┼──────────────┼──────────┼─────────────┼────────┼──────────┤
│ 124 │ BEV18002 │ Honda Activa │ 5/5      │ Oct 26 2025 │ Pending│ [Approve]│
│     │ Jane     │              │ ✅        │ 9:15 AM     │        │ [Reject] │
└─────┴──────────┴──────────────┴──────────┴─────────────┴────────┴──────────┘
```

**Filter Options:**
- **Date Range:** Last 7 Days, Last 30 Days, Custom Range
- **Status:** Pending, Admin Approved, SA Approved, All
- **Award Type:** Direct Awards, Matching Awards, All

**Actions Available:**
- ✅ **Approve** → Move to Super Admin queue
- ❌ **Reject** → End flow with reason

**NO COST DATA VISIBLE**

---

### 5.2 Super Admin View: `/super-admin/awards/approval`

**Purpose:** Final approval before procurement

**Visible Columns:**
```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Awards - Super Admin Approval Queue                                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Filters: [Date Range ▼] [Status ▼] [Award Type ▼] [Approved By ▼]              │
├─────┬──────────┬──────────────┬──────────┬─────────────┬──────────────┬─────────┤
│ ID  │ User     │ Award        │ Progress │ Admin       │ Status       │ Actions │
│     │          │              │          │ Approved    │              │         │
├─────┼──────────┼──────────────┼──────────┼─────────────┼──────────────┼─────────┤
│ 123 │ BEV18001 │ Royal Enfield│ 10/10 ✅ │ BEV18003    │ Admin        │[Approve]│
│     │ John Doe │ Bike         │          │ Oct 25 3PM  │ Approved     │[Reject] │
├─────┼──────────┼──────────────┼──────────┼─────────────┼──────────────┼─────────┤
│ 124 │ BEV18002 │ Honda Activa │ 5/5 ✅   │ BEV18003    │ Admin        │[Approve]│
│     │ Jane     │              │          │ Oct 26 10AM │ Approved     │[Reject] │
└─────┴──────────┴──────────────┴──────────┴─────────────┴──────────────┴─────────┘
```

**Filter Options:**
- **Date Range:** Last 7 Days, Last 30 Days, Custom Range
- **Status:** Admin Approved (Pending SA), SA Approved, Rejected, All
- **Award Type:** Direct Awards, Matching Awards, Bonanza, All
- **Approved By:** Filter by which admin approved

**Actions Available:**
- ✅ **SA Approve** → Move to Finance procurement queue
- ❌ **Reject** → End flow with reason
- 📝 **Add Notes** → Add approval notes

**NO COST DATA VISIBLE**

---

### 5.3 Finance Admin View: `/finance/awards/procurement`

**Purpose:** Purchase awards, record costs, manage delivery

**Visible Columns WITH COST DATA:**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Awards - Procurement & Delivery Management                                                     │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Filters: [Date ▼] [Status ▼] [Type ▼] [Cost Impact ▼]                                        │
├────┬────────┬─────────────┬─────────┬──────────┬──────────┬───────────┬────────┬────────────┤
│ ID │ User   │ Award       │ Budget  │ Actual   │ Variance │ Status    │ Impact │ Actions    │
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼───────────┼────────┼────────────┤
│123 │BEV1801 │Royal        │₹2,00,000│    -     │    -     │SA         │Pending │[Purchase]  │
│    │John    │Enfield Bike │         │          │          │Approved   │        │            │
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼───────────┼────────┼────────────┤
│124 │BEV1802 │Honda Activa │₹80,000  │₹78,000   │+₹2,000   │Purchased  │Incurred│[Deliver]   │
│    │Jane    │             │         │          │(saved)   │           │        │[Upload Proof]│
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼───────────┼────────┼────────────┤
│125 │BEV1803 │Maruti Swift │₹7,00,000│₹6,95,000 │+₹5,000   │Delivered  │Completed│[View]     │
│    │Ram     │Car          │         │          │(saved)   │✅         │        │            │
└────┴────────┴─────────────┴─────────┴──────────┴──────────┴───────────┴────────┴────────────┘
```

**Filter Options:**
- **Date Range:** Achievement Date, Purchase Date, Delivery Date
- **Status:** SA Approved (To Purchase), Purchased (To Deliver), Delivered
- **Award Type:** Direct Awards, Matching Awards, Cash Bonanza, Physical Bonanza
- **Cost Impact:** Pending, Incurred, Completed

**Actions Available:**

#### For "SA Approved" Status:
**[Purchase] Button** → Opens modal:
```
┌─────────────────────────────────────────────────────────┐
│ Record Award Purchase                                    │
├─────────────────────────────────────────────────────────┤
│ User: BEV18001 - John Doe                               │
│ Award: Royal Enfield Bike                               │
│ Budgeted Amount: ₹2,00,000                              │
│                                                          │
│ Vendor Name:     [____________________]                 │
│ Actual Cost:     [____________________]                 │
│ Payment Mode:    [Bank Transfer ▼]                      │
│ Payment Ref:     [____________________]                 │
│ Upload Bill:     [Choose File] [__________.pdf]         │
│ Variance Reason: [____________________]                 │
│                  (If actual ≠ budgeted)                 │
│                                                          │
│         [Cancel]              [Save & Mark Purchased]   │
└─────────────────────────────────────────────────────────┘
```

#### For "Purchased" Status:
**[Deliver] Button** → Opens modal:
```
┌─────────────────────────────────────────────────────────┐
│ Mark Award as Delivered                                  │
├─────────────────────────────────────────────────────────┤
│ User: BEV18002 - Jane                                   │
│ Award: Honda Activa                                      │
│ Purchase Cost: ₹78,000                                   │
│                                                          │
│ Delivery Date:   [___________] (auto-filled)            │
│ Delivered To:    User's Address (from profile)          │
│ Upload Proof:    [Choose File] [delivery_proof.jpg]     │
│ User Signed:     [☑] User acknowledged receipt          │
│ Notes:           [____________________]                 │
│                                                          │
│         [Cancel]              [Mark as Delivered]       │
└─────────────────────────────────────────────────────────┘
```

**✅ FULL COST DATA VISIBLE**

---

### 5.4 RVZ ID View: `/rvz/awards/oversight`

**Purpose:** Supreme oversight with full cost visibility and override powers

**Visible Columns WITH ALL DATA:**
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ VGK Awards & Bonanza - Supreme Oversight Dashboard                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Filters: [Date ▼] [Status ▼] [Type ▼] [Role ▼] [Cost Impact ▼]                                    │
│                                                                                                      │
│ Summary Cards:                                                                                       │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐                                      │
│ │ Pending      │ Incurred     │ Completed    │ Total Saved  │                                      │
│ │ ₹15,00,000   │ ₹3,85,000    │ ₹12,50,000   │ ₹25,000      │                                      │
│ └──────────────┴──────────────┴──────────────┴──────────────┘                                      │
├────┬────────┬─────────────┬─────────┬──────────┬──────────┬──────────┬────────┬──────┬────────────┤
│ ID │ User   │ Award       │ Budget  │ Actual   │ Variance │ Status   │ Impact │ Role │ Actions    │
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼──────────┼────────┼──────┼────────────┤
│123 │BEV1801 │Royal        │₹2,00,000│    -     │    -     │Pending   │Pending │Admin │[Override]  │
│    │John    │Enfield Bike │         │          │          │Admin     │        │      │[Approve SA]│
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼──────────┼────────┼──────┼────────────┤
│124 │BEV1802 │Honda Activa │₹80,000  │₹78,000   │+₹2,000   │Purchased │Incurred│Finance│[View]     │
│    │Jane    │             │         │          │(saved)   │          │        │       │[Override] │
├────┼────────┼─────────────┼─────────┼──────────┼──────────┼──────────┼────────┼──────┼────────────┤
│125 │BEV1803 │Maruti Swift │₹7,00,000│₹6,95,000 │+₹5,000   │Delivered │Complete│Finance│[View]     │
│    │Ram     │Car          │         │          │(saved)   │✅        │        │       │            │
└────┴────────┴─────────────┴─────────┴──────────┴──────────┴──────────┴────────┴──────┴────────────┘
```

**Additional VGK Features:**
- 📊 **Cost Analytics Dashboard** - Budget utilization, variance trends
- 📈 **Approval Flow Visualization** - See where items are stuck
- 🔍 **Audit Trail** - Complete history of all actions
- ⚡ **Override Powers** - Approve/Reject at any stage

**✅ FULL COST DATA + SUPREME POWERS**

---

### 5.5 Bonanza Views (Same Structure)

#### Admin/SA View: `/admin/bonanza/approvals`
- Same as Awards (NO cost data)

#### Finance View: `/finance/bonanza/procurement`
- Same as Awards (WITH cost data)
- Separate handling for Cash vs Physical bonanza

**Cash Bonanza Flow:**
```
[SA Approved] → [Finance: Process Payment] → [Completed]
                       ↓
               Wallet credited directly
               (No delivery tracking needed)
```

**Physical Bonanza Flow:**
```
[SA Approved] → [Finance: Purchase] → [Finance: Deliver] → [Completed]
                       ↓                      ↓
                Vendor purchase       User receives item
```

---

## 6. API Endpoints

### 6.1 Admin Endpoints

```
GET  /api/v1/admin/awards/direct
     - List direct awards pending admin approval
     - Filter: date, status, user
     - Response: NO cost data

GET  /api/v1/admin/awards/matching
     - List matching awards pending admin approval
     - Response: NO cost data

POST /api/v1/admin/awards/{id}/approve
     - Approve award for SA review
     - Body: { notes: "Verified genuine achievement" }

POST /api/v1/admin/awards/{id}/reject
     - Reject award
     - Body: { reason: "Duplicate entry" }

GET  /api/v1/admin/bonanza/approvals
     - List bonanza achievements
     - Response: NO cost data
```

### 6.2 Super Admin Endpoints

```
GET  /api/v1/super-admin/awards/pending
     - List awards pending SA approval
     - Filter: date, status, admin_approved_by
     - Response: NO cost data

POST /api/v1/super-admin/awards/{id}/approve
     - Final approval for procurement
     - Body: { notes: "Approved for purchase" }

POST /api/v1/super-admin/awards/{id}/reject
     - Reject award at SA level
     - Body: { reason: "Budget constraints" }

GET  /api/v1/super-admin/bonanza/pending
     - List bonanza pending SA approval
     - Response: NO cost data
```

### 6.3 Finance Admin Endpoints

```
GET  /api/v1/finance/awards/procurement
     - List awards for procurement
     - Filter: date, status, cost_impact
     - Response: ✅ WITH cost data
     - Cost fields: budgeted_amount, actual_cost_paid, cost_variance

POST /api/v1/finance/awards/{id}/purchase
     - Record award purchase
     - Body: {
         vendor_name,
         actual_cost_paid,
         payment_mode,
         payment_reference,
         bill_file (multipart),
         cost_variance_reason
       }
     - Creates expense record

POST /api/v1/finance/awards/{id}/deliver
     - Mark award as delivered
     - Body: {
         delivery_proof (multipart),
         user_acknowledgment,
         notes
       }

GET  /api/v1/finance/bonanza/procurement
     - List bonanza for payment/purchase
     - Response: ✅ WITH cost data

POST /api/v1/finance/bonanza/{id}/pay
     - Process cash bonanza payment
     - Body: {
         payment_mode,
         payment_reference,
         actual_amount
       }

POST /api/v1/finance/bonanza/{id}/purchase
     - Purchase physical bonanza reward
     - Same as awards purchase

GET  /api/v1/finance/cost-summary
     - Cost analytics dashboard
     - Response: {
         total_pending,
         total_incurred,
         total_completed,
         awards_cost,
         bonanza_cost,
         variance_analysis
       }
```

### 6.4 RVZ ID Endpoints

```
GET  /api/v1/rvz/awards/oversight
     - Supreme oversight view
     - Response: ✅ ALL data including cost
     - Filter by any field

POST /api/v1/rvz/awards/{id}/override
     - Override any decision
     - Body: {
         action: 'approve' | 'reject' | 'hold',
         notes
       }

GET  /api/v1/rvz/cost-analytics
     - Comprehensive cost analytics
     - Budget utilization
     - Variance trends
     - Approval flow metrics

GET  /api/v1/rvz/audit-trail/{id}
     - Complete audit trail for award/bonanza
     - All state changes
     - All approvals/rejections
```

---

## 7. Implementation Protocols

### 7.1 WV Protocol (Withdrawal-Validation)

**Principle:** NET amount at achievement = final payout (NO additional deductions)

**Application to Awards/Bonanza:**

```javascript
// CORRECT: Cost determined at achievement
budgeted_amount = award_tier.actual_price  // e.g., ₹2,00,000

// Finance purchases at actual cost
actual_cost_paid = vendor_invoice_amount   // e.g., ₹1,95,000

// Cost variance tracked
cost_variance = budgeted_amount - actual_cost_paid  // ₹5,000 saved

// ✅ NO ADDITIONAL DEDUCTIONS at delivery
// User receives: Royal Enfield Bike (full item)
// Company pays: ₹1,95,000 (actual cost)
```

**For Cash Bonanza:**
```javascript
// Bonanza reward amount
reward_amount = ₹10,000  // Defined in campaign

// Deductions ONLY at income stage (if applicable)
// - Guru Dakshina: 2% (for cash bonanza)
// - Admin: 8%
// - TDS: 2%
// NET = ₹8,800 (if all deductions apply)

// Finance pays NET to wallet
// ✅ NO ADDITIONAL DEDUCTIONS at payment stage
```

### 7.2 DC Protocol (Data Consistency)

**Principle:** Single source of truth for each data type

**Implementation:**

```
┌─────────────────────────────────────────────────────────┐
│ DATA SOURCE MAPPING                                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ UserAwardProgress / BonanzaProgress:                    │
│ └─ SOURCE OF TRUTH for:                                │
│    ├─ Achievement status                               │
│    ├─ Approval workflow state                          │
│    ├─ Budgeted amount                                  │
│    ├─ Actual cost paid                                 │
│    └─ Delivery status                                  │
│                                                          │
│ Expense Table:                                          │
│ └─ SOURCE OF TRUTH for:                                │
│    ├─ Vendor details                                   │
│    ├─ Payment mode & reference                         │
│    ├─ Bill upload details                              │
│    └─ Expense approval workflow                        │
│    (Links to progress via award_reference_id)          │
│                                                          │
│ User Table:                                             │
│ └─ SOURCE OF TRUTH for:                                │
│    ├─ Metric deductions                                │
│    │  (bonanza_deductions_applied)                     │
│    └─ Effective award progress                         │
│       (effective_progress_count)                        │
└─────────────────────────────────────────────────────────┘
```

**Query Pattern:**
```sql
-- ✅ CORRECT: Single query joins sources
SELECT 
    -- From progress table (achievement data)
    uap.id,
    uap.user_id,
    uap.processed_status,
    uap.budgeted_amount,
    uap.actual_cost_paid,
    uap.cost_variance,
    
    -- From expense table (procurement data)
    e.vendor,
    e.payment_mode,
    e.reference_no,
    e.bill_filename
    
FROM user_award_progress uap
LEFT JOIN expense e ON e.award_reference_id = uap.id
WHERE uap.processed_status = 'Super Admin Approved'
```

**❌ INCORRECT: Duplicate data**
```sql
-- Don't store vendor details in BOTH tables
-- Don't store cost in BOTH tables
-- ALWAYS link via foreign key
```

### 7.3 Multiple Bonanza Achievement

**Scenario:** User achieves 10 direct referrals

**Bonanza Campaign Setup:**
```
Campaign: "Diwali Mega Bonanza 2025"
├─ Reward 1: 5 referrals → ₹10,000 cash
├─ Reward 2: 10 referrals → ₹25,000 cash
└─ Reward 3: 10 referrals → Honda Activa (₹80,000)
```

**Processing Logic:**
```python
# Scheduler at midnight
def calculate_bonanza_income(business_date):
    # Find all eligible rewards for user
    user_progress = 10  # 10 direct referrals
    
    eligible_rewards = [
        Reward1 (5 refs),   # ✅ Eligible
        Reward2 (10 refs),  # ✅ Eligible  
        Reward3 (10 refs)   # ✅ Eligible
    ]
    
    # Create SEPARATE progress record for each
    for reward in eligible_rewards:
        create_bonanza_progress(
            user_id=user_id,
            reward_id=reward.id,
            current_progress=10,
            achievement_status='Achieved - Eligible'
        )
    
    # User can claim ALL THREE
    # But ONCE ANY is claimed, apply metric deduction
    
    # Example: User claims Reward 3 (Honda Activa)
    # Deduct 10 referrals from award progress
    user_award_progress.bonanza_deductions_applied += 10
    user_award_progress.effective_progress_count = 
        current_referrals - bonanza_deductions_applied
    
    # Now user has:
    # - BonanzaProgress for all 3 rewards (separate dispatches)
    # - Award progress reduced by 10
```

**Dispatch Tracking:**
```
User BEV18001:
├─ Bonanza Progress #1 (₹10,000) - Status: Eligible
├─ Bonanza Progress #2 (₹25,000) - Status: Eligible
└─ Bonanza Progress #3 (Honda Activa) - Status: Admin Approved → SA Approved → Purchased → Delivered
```

**Metric Deduction (on FIRST claim):**
```
Award Progress Before: 10 direct referrals
User claims bonanza #3
Award Progress After: 10 - 10 = 0 effective referrals

Now user needs NEW referrals to achieve awards
(Same achievement cannot earn both bonanza AND award)
```

---

## 8. Database Migration Script

```sql
-- Add procurement fields to user_award_progress
ALTER TABLE user_award_progress ADD COLUMN IF NOT EXISTS 
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE;

-- Add procurement fields to user_matching_award_progress
ALTER TABLE user_matching_award_progress ADD COLUMN IF NOT EXISTS 
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE;

-- Add procurement fields to bonanza_progress
ALTER TABLE bonanza_progress ADD COLUMN IF NOT EXISTS 
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(50),
    payment_reference VARCHAR(255),
    bill_upload_path VARCHAR(500),
    delivered_by VARCHAR(12) REFERENCES "user"(id),
    delivered_at TIMESTAMP,
    delivery_proof_path VARCHAR(500),
    user_acknowledgment BOOLEAN DEFAULT FALSE;

-- Add award/bonanza linkage to expense
ALTER TABLE expense ADD COLUMN IF NOT EXISTS 
    award_reference_id INTEGER,
    award_reference_type VARCHAR(50),
    bonanza_reference_id INTEGER,
    bonanza_reference_type VARCHAR(50);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_expense_award_ref ON expense(award_reference_id);
CREATE INDEX IF NOT EXISTS idx_expense_bonanza_ref ON expense(bonanza_reference_id);
CREATE INDEX IF NOT EXISTS idx_award_progress_status ON user_award_progress(processed_status);
CREATE INDEX IF NOT EXISTS idx_bonanza_progress_status ON bonanza_progress(processed_status);
```

---

## 9. Summary

### ✅ Implementation Checklist

- [x] Database schema updated with procurement & delivery fields
- [x] Expense table linked to awards/bonanza
- [ ] Scheduler creates expense records on purchase
- [ ] Admin pages show NO cost data
- [ ] Finance pages show ALL cost data
- [ ] VGK pages show ALL data + override powers
- [ ] Dynamic filters implemented (date, status, type)
- [ ] Cost impact tracking (Pending → Incurred → Completed)
- [ ] Multiple bonanza achievement support
- [ ] Metric deduction on claim

### 🔑 Key Principles

1. **WV Protocol:** NET amount = final payout (NO additional deductions)
2. **DC Protocol:** Single source of truth per data type
3. **Cost States:** Pending (unrealized) → Incurred (realized at purchase) → Completed
4. **Role Visibility:** Admin/SA see NO cost | Finance/VGK see ALL cost
5. **Multiple Bonanza:** Same achievement can qualify for multiple bonanzas
6. **Metric Deduction:** Applied to awards when bonanza claimed

---

**Document Status:** ✅ Complete Specification  
**Ready for Implementation:** YES  
**Protocols Followed:** WV (Withdrawal-Validation), DC (Data Consistency)
