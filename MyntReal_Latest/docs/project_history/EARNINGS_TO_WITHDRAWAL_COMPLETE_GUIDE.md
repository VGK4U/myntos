# BeV EV Reference Program - Complete Earnings to Withdrawal Cycle Guide

**Version:** 2.0 (Verified & Accurate)  
**Last Updated:** October 28, 2025  
**Status:** ✅ Production Ready - WV & DC Protocol Compliant

---

## 📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Package System](#package-system)
3. [Income Types & Calculation](#income-types--calculation)
4. [Deduction Structure](#deduction-structure)
5. [Wallet Management System](#wallet-management-system)
6. [Daily Automated Jobs](#daily-automated-jobs)
7. [Withdrawal Request Flow](#withdrawal-request-flow)
8. [Multi-Role Approval System](#multi-role-approval-system)
9. [WV & DC Protocol Implementation](#wv--dc-protocol-implementation)
10. [API Endpoints Reference](#api-endpoints-reference)
11. [Database Schema](#database-schema)
12. [Frontend Pages Reference](#frontend-pages-reference)
13. [Complete Example Flow](#complete-example-flow)
14. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. System Architecture Overview

### High-Level Flow
```
User Registration → Binary Tree Placement → Income Generation → 
Daily Income Calculation → Deductions Applied → Wallet Split → 
Auto-Approval & Crediting → Wallet Sync → Auto-Withdrawal → 
Multi-Role Approval → Bank Transfer → Completion
```

### Key Components
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Vanilla JavaScript + Bootstrap 5
- **Scheduler**: APScheduler (Daily midnight IST tasks)
- **Authentication**: JWT-based with role-based access control

### Production Start Date
**October 1, 2025** - All income calculations include activities from this date onwards.

---

## 2. Package System

### Package Details & Pricing

| Package | Price | Points | Display |
|---------|-------|--------|---------|
| **Platinum** 🏆 | ₹15,000 | 1.0 | Premium Package |
| **Diamond** 💎 | ₹7,500 | 0.5 | Mid-tier Package |
| **Blue** 🔵 | ₹1,000 | 0 | Entry Package |
| **Loyal** 🟠 | ₹500 | 0 | Starter Package |

### Wallet Split by Package

**CRITICAL:** Wallet split varies by package type

| Package | Earning Wallet<br/>(Withdrawable) | Upgrade Wallet<br/>(Non-withdrawable) |
|---------|-----------------------------------|---------------------------------------|
| **Platinum (1.0)** | **100%** of NET | **0%** |
| **Diamond (0.5)** | **50%** of NET | **50%** of NET |
| **Blue (0)** | **50%** of NET | **50%** of NET |
| **Loyal (0)** | **50%** of NET | **50%** of NET |

**Key Point:** Only Platinum users get 100% of NET income as withdrawable. All other packages split 50/50.

### Referral Bonuses

| Package | Direct Referral Bonus | Max Bonuses |
|---------|----------------------|-------------|
| **Platinum** | ₹3,000 | 1 |
| **Diamond** | ₹1,500 | 2 |
| **Blue** | ₹0 | 2 |
| **Loyal** | ₹0 | 2 |

---

## 3. Income Types & Calculation

### Four Primary Income Streams

#### 1. Direct Referral Income
**Trigger:** When you refer someone who activates a package

**Amount:**
- Platinum referral: ₹3,000 GROSS
- Diamond referral: ₹1,500 GROSS
- Blue/Loyal: ₹0 (no bonus)

**Max Count:**
- Platinum users: 1 referral bonus
- Diamond/Blue/Loyal: 2 referral bonuses

**Status:** Auto-approved immediately

#### 2. Matching Referral Income
**Trigger:** When both left and right legs have points that can be matched

**Amount:** ₹2,000 per 1:1 point match (fixed rate)

**First Match Requirement:**
- Requires 2:1 or 1:2 ratio initially
- Example: 2 points on left, 1 point on right (or vice versa)

**Subsequent Matches:**
- Simple 1:1 matching after first match is achieved
- Every 1 point from left matches with 1 point from right

**Eligibility:**
- At least 1 active referral on left side
- At least 1 active referral on right side
- Minimum 0.5 points on both sides

**Status:** Auto-approved if eligible; 'Pending' if not eligible

#### 3. Ved Income
**Trigger:** When someone in your 3rd level downline activates a package

**Amount:**
- Platinum activation: ₹1,000
- Diamond activation: ₹500
- Blue/Loyal: ₹0

**Status:** Auto-approved immediately

#### 4. Guru Dakshina
**Trigger:** You receive 2% of each direct referral's total daily GROSS earnings

**Amount:** 2% of referral's GROSS earnings

**Special Note:** 
- This income does NOT have Guru Dakshina deduction applied (no recursive deduction)
- Only has Admin (8%) and TDS (2%) deductions = 10% total

**Status:** Auto-approved immediately

---

## 4. Deduction Structure

### Master Deduction Rates

| Deduction Type | Rate | Applied On | When Applied |
|---------------|------|------------|--------------|
| **Guru Dakshina** | 2% | GROSS | All incomes EXCEPT Guru Dakshina income |
| **Admin Charges** | 8% | GROSS | ALL incomes (always) |
| **TDS (Tax)** | 2% | GROSS | ALL incomes (always) |

### Deduction Formulas

**For Regular Income (Direct, Matching, Ved):**
```
GROSS Income                          ₹10,000
- Guru Dakshina (2% of GROSS)        -₹200
- Admin Charges (8% of GROSS)        -₹800
- TDS (2% of GROSS)                  -₹200
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NET Income (88% of GROSS)            ₹8,800
Total Deductions: 12%
```

**For Guru Dakshina Income:**
```
GROSS Income                          ₹200
- Guru Dakshina                      -₹0 (NOT applied - no recursive)
- Admin Charges (8% of GROSS)        -₹16
- TDS (2% of GROSS)                  -₹4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NET Income (90% of GROSS)            ₹180
Total Deductions: 10%
```

### Critical Rules
1. **ALL deductions calculated from ORIGINAL GROSS amount**
2. **Deductions applied ONCE** - at income calculation stage
3. **NO additional deductions at withdrawal stage** (WV Protocol)

---

## 5. Wallet Management System

### Three Wallet Types

#### 1. Earning Wallet
**Purpose:** Accumulates verified NET earnings (withdrawable portion)

**Source:** 
- Platinum: 100% of NET income
- Diamond/Blue/Loyal: 50% of NET income

**Sync to Withdrawable:** Daily (KYC-approved users only)

**Direct Withdrawal:** NO (must sync to Withdrawable Wallet first)

#### 2. Withdrawable Wallet
**Purpose:** Available for immediate withdrawal

**Source:** Daily sync from Earning Wallet (KYC-approved users only)

**Can Withdraw:** YES

**Requirement:** KYC must be approved

#### 3. Upgrade Wallet
**Purpose:** Reserved for package upgrades

**Source:**
- Platinum: 0% of NET income
- Diamond/Blue/Loyal: 50% of NET income

**Can Withdraw:** NO (upgrade purposes only)

### Wallet Flow Diagram

```
Income Calculated (GROSS)
         ↓
Deductions Applied (12% or 10%)
         ↓
NET Income
         ↓
    ┌────────────────────────────┐
    │   Wallet Split by Package  │
    └────────────────────────────┘
         ↓                    ↓
  Earning Wallet        Upgrade Wallet
  (Platinum: 100%)      (Platinum: 0%)
  (Others: 50%)         (Others: 50%)
         ↓
  Daily Sync (KYC required)
         ↓
  Withdrawable Wallet
         ↓
  Withdrawal Request
         ↓
  Bank Transfer
```

---

## 6. Daily Automated Jobs

### Scheduler Configuration
- **Timezone:** Asia/Kolkata (IST)
- **Run Time:** Daily at midnight (00:00 IST)
- **Framework:** APScheduler

### Job 1: Calculate Daily Income

**Function:** `calculate_daily_income()`

**Process:**
1. For each active user, calculate previous day's income:
   - Direct Referral Income
   - Matching Referral Income
   - Ved Income
   - Guru Dakshina

2. For each income:
   ```python
   # Calculate deductions
   guru_dakshina = gross × 2% (if applicable)
   admin_charges = gross × 8%
   tds = gross × 2%
   net = gross - (guru_dakshina + admin_charges + tds)
   
   # Get wallet split based on package
   if package_points == 1.0:  # Platinum
       withdrawable_pct = 100
       upgrade_pct = 0
   else:  # Diamond/Blue/Loyal
       withdrawable_pct = 50
       upgrade_pct = 50
   
   # Calculate wallet amounts
   withdrawal_wallet_amount = net × (withdrawable_pct / 100)
   upgraded_wallet_amount = net × (upgrade_pct / 100)
   ```

3. Create `PendingIncome` record with all calculated values

4. Auto-approve eligible incomes:
   - Direct Referral → Auto-approved
   - Ved Income → Auto-approved
   - Guru Dakshina → Auto-approved
   - Matching Referral → Auto-approved if eligible

5. For auto-approved incomes:
   - Set status to 'Accounts Paid'
   - Credit wallets immediately
   - Create Transaction record
   - Delete PendingIncome (avoid duplicates)

### Job 2: Synchronize Wallets

**Function:** `sync_withdrawable_wallets()`

**Process:**
```python
for each user where kyc_status == 'Approved':
    if earning_wallet > 0:
        withdrawable_wallet += earning_wallet
        earning_wallet = 0
        save()
```

**KYC Requirement:** Only KYC-approved users get wallet sync

**Non-KYC Users:**
- Income accumulates in Earning Wallet
- Cannot transfer to Withdrawable Wallet
- Cannot request withdrawals

### Job 3: Auto-Generate Withdrawal Requests

**Function:** `auto_generate_withdrawal_requests()`

**Criteria:**
1. KYC status = 'Approved'
2. Withdrawable wallet ≥ ₹1,000
3. No existing pending withdrawal
4. Bank details present (from KYC or profile)

**Amount Calculation:**
```python
available = withdrawable_wallet
buffer = 100  # Safety buffer

withdrawal_amount = available - buffer

# Cap at maximum
if withdrawal_amount > 50000:
    withdrawal_amount = 50000

# Minimum check
if withdrawal_amount < 1000:
    skip_user

# WV PROTOCOL: NO ADDITIONAL DEDUCTIONS
admin_charges = 0
tds_amount = 0
final_payout = withdrawal_amount
```

**Database Record Created:**
```sql
INSERT INTO withdrawal_request (
    user_id,
    withdrawal_amount,      -- NET from withdrawable_wallet
    admin_charges,          -- 0 (WV Protocol)
    tds_amount,            -- 0 (WV Protocol)
    final_payout,          -- Same as withdrawal_amount
    status,                -- 'Pending'
    is_auto_generated,     -- TRUE
    bank_name,
    account_number,
    ifsc_code,
    account_holder_name
)
```

---

## 7. Withdrawal Request Flow

### Withdrawal Creation Methods

#### Method 1: Auto-Generated (Scheduler)
- Runs daily at midnight
- Automatic for eligible users
- Threshold: ₹1,000 minimum

#### Method 2: Manual Request (User Action)
- User clicks "Request Withdrawal" button
- System validates eligibility
- Creates withdrawal request

### Withdrawal Status Flow

```
Pending
   ↓ Admin approves
Admin Verified
   ↓ Super Admin approves
Super Admin Approved
   ↓ Finance marks sent
Sent
   ↓ Finance marks paid
Completed

At any stage before Sent:
   ↓ Admin/SA rejects
Rejected
```

### Status Descriptions

| Status | Description | Next Actions |
|--------|-------------|--------------|
| **Pending** | Just created, awaiting Admin review | Admin: Approve/Reject |
| **Admin Verified** | Admin approved, awaiting Super Admin | Super Admin: Approve/Reject |
| **Super Admin Approved** | SA approved, ready for bank transfer | Finance: Mark Sent |
| **Sent** | Finance marked as sent to bank | Finance: Mark Paid |
| **Completed** | Money received confirmation | View only |
| **Rejected** | Rejected at approval stage | View only |

---

## 8. Multi-Role Approval System

### Role Hierarchy & Powers

| Role | Access Level | Capabilities |
|------|-------------|--------------|
| **Super Admin** | Supreme | ALL powers (Admin approve, SA approve, Mark Sent, Mark Paid, Reject) |
| **RVZ ID** | Supreme | ALL powers (Admin approve, SA approve, Mark Sent, Mark Paid, Reject) |
| **Admin** | Standard | Approve (Pending→Admin Verified), Reject |
| **Finance Admin** | Finance | Mark Sent (SA Approved→Sent), Mark Paid (Sent→Completed) |
| **User** | Basic | View own withdrawals, request new withdrawal |

### Context-Aware Actions by Status

**Pending Withdrawals:**
- Admin: ✅ Approve (→Admin Verified), ❌ Reject
- Super Admin: ✅ Approve as Admin (→Admin Verified), ❌ Reject
- RVZ ID: ✅ Approve as Admin (→Admin Verified), ❌ Reject

**Admin Verified Withdrawals:**
- Super Admin: ✅ SA Approve (→SA Approved), ❌ Reject
- RVZ ID: ✅ SA Approve (→SA Approved), ❌ Reject

**Super Admin Approved Withdrawals:**
- Finance Admin: 📤 Mark Sent (→Sent)
- Super Admin: 📤 Mark Sent (→Sent)
- RVZ ID: 📤 Mark Sent (→Sent)

**Sent Withdrawals:**
- Finance Admin: ✅ Mark Paid (→Completed)
- Super Admin: ✅ Mark Paid (→Completed)
- RVZ ID: ✅ Mark Paid (→Completed)

### Frontend Pages by Role

#### Admin Pages
- `/admin/withdrawal/history` - View all, Approve/Reject Pending

#### Super Admin Pages
- `/superadmin/withdrawal/approvals` - Supreme Management (ALL actions, ALL statuses)

#### Finance Admin Pages
- `/finance/withdrawal/queue` - Transfer Queue (SA Approved withdrawals)
- `/finance/withdrawal/history` - Transfer History

#### RVZ ID Pages
- `/rvz/withdrawal/dashboard` - Supreme Dashboard (ALL actions, ALL statuses)

#### User Pages
- `/user/withdrawals` - View own withdrawals, request new

---

## 9. WV & DC Protocol Implementation

### WV Protocol (Withdrawal-Validation Protocol)

**Core Principle:**
> **NET amount at withdrawal = Final payout to bank**  
> **NO additional deductions at withdrawal stage**

**Implementation:**

1. **Income Stage (ONLY place deductions happen):**
```python
# scheduler.py lines 90-135
gross_amount = 10000
guru_dakshina_deduction = gross × 0.02  # 2%
admin_deduction = gross × 0.08          # 8%
tds_deduction = gross × 0.02            # 2%
net_amount = gross - (guru + admin + tds)
```

2. **Withdrawal Stage (NO deductions):**
```python
# scheduler.py lines 2495-2499
withdrawal_amount = withdrawable_wallet_balance
admin_charges = 0  # WV Protocol
tds_amount = 0     # WV Protocol
final_payout = withdrawal_amount
```

3. **Database Schema:**
```sql
withdrawal_request:
  - withdrawal_amount INTEGER  (NET from wallet)
  - admin_charges INTEGER DEFAULT 0
  - tds_amount INTEGER DEFAULT 0
  - final_payout INTEGER  (= withdrawal_amount)
```

**WV Protocol Guarantee:**
✅ User sees NET amount → User receives NET amount to bank  
✅ No surprise deductions at withdrawal time  
✅ Complete transparency

### DC Protocol (Data Consistency Protocol)

**Core Principle:**
> **Single source of truth for withdrawal data**  
> **NO duplicate API calls**

**Implementation Pattern:**

```javascript
// CORRECT - DC Protocol Compliant
async function loadAllData() {
    const [withdrawalData, incomeData, breakdownData] = await Promise.all([
        fetch('/api/v1/withdrawals/admin/withdrawal-report'),
        fetch('/api/v1/withdrawals/income-transactions?user_id=' + userId),
        fetch('/api/v1/withdrawals/admin/withdrawal-income-breakdown/' + id)
    ]);
    
    // Use data once, cache for filtering
    allData = withdrawalData.requests;
}

// WRONG - Duplicate calls
fetch('/api/v1/withdrawals/admin/withdrawal-report')
// ... later ...
fetch('/api/v1/withdrawals/admin/withdrawal-report')  // DUPLICATE!
```

**Data Source Hierarchy:**

1. **Primary:** `withdrawal-report` → User info, bank details, withdrawal amounts, status
2. **Supporting:** `income-transactions` → Earnings summary, income breakdown
3. **Detailed:** `withdrawal-income-breakdown` → Per-income-type GROSS/NET breakdown

**DC Protocol Rules:**
✅ One API call per endpoint  
✅ Promise.all() for parallel execution  
✅ Cache data for filtering/display  
✅ No redundant fetches

---

## 10. API Endpoints Reference

### Withdrawal Management APIs

#### Get Withdrawal Report
```http
GET /api/v1/withdrawals/admin/withdrawal-report
Query Params:
  - status_filter: string (optional) - "Pending", "Admin Verified", etc.
  - user_id: string (optional) - Filter by specific user

Response:
{
  "success": true,
  "requests": [
    {
      "id": 375,
      "user_id": "BEV1800001",
      "user_name": "John Doe",
      "withdrawal_amount": 10000,
      "final_payout": 10000,
      "status": "Completed",
      "account_holder_name": "John Doe",
      "account_number": "1234567890",
      "ifsc_code": "SBIN0001234",
      "bank_name": "State Bank of India",
      "created_at": "2025-10-27T12:00:00",
      "updated_at": "2025-10-27T14:00:00"
    }
  ],
  "total_pending": 5,
  "total_approved": 10,
  "total_completed": 81
}
```

#### Get Income Transactions
```http
GET /api/v1/withdrawals/income-transactions
Query Params:
  - user_id: string (required)

Response:
{
  "success": true,
  "data": {
    "summary": {
      "total_earned_gross": 25000,
      "total_earned_net": 22000,
      "direct_referral_income": 5000,
      "matching_referral_income": 10000,
      "ved_income": 7000,
      "guru_dakshina": 3000
    },
    "transactions": [...]
  }
}
```

#### Get Withdrawal Income Breakdown
```http
GET /api/v1/withdrawals/admin/withdrawal-income-breakdown/{withdrawal_id}

Response:
{
  "success": true,
  "breakdown_by_type": [
    {
      "income_type": "Direct Referral",
      "gross": 5000,
      "guru_dakshina_deduction": 100,
      "admin_deduction": 400,
      "tds_deduction": 100,
      "total_deductions": 600,
      "net": 4400
    }
  ],
  "totals": {
    "gross": 25000,
    "guru_dakshina_deduction": 500,
    "admin_deduction": 2000,
    "tds_deduction": 500,
    "total_deductions": 3000,
    "net": 22000
  }
}
```

### Withdrawal Action APIs

#### Admin Process Withdrawal
```http
POST /api/v1/withdrawals/admin/process/{withdrawal_id}
Body: {
  "action": "approve" | "reject",
  "admin_notes": "Optional notes"
}

Effect:
  - approve: Pending → Admin Verified
  - reject: Any status → Rejected
```

#### Super Admin Process Withdrawal
```http
POST /api/v1/withdrawals/superadmin/process/{withdrawal_id}
Body: {
  "action": "approve" | "reject"
}

Effect:
  - approve: Admin Verified → Super Admin Approved
  - reject: Any status → Rejected
```

#### Finance Process Transfer
```http
POST /api/v1/withdrawals/finance/process-transfer/{withdrawal_id}
Body: {
  "action": "sent" | "paid",
  "payment_reference": "Optional bank reference"
}

Effect:
  - sent: Super Admin Approved → Sent
  - paid: Sent → Completed
```

---

## 11. Database Schema

### Core Tables

#### `user` Table
```sql
CREATE TABLE "user" (
  id VARCHAR(12) PRIMARY KEY,           -- e.g., BEV1800001
  name VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(20),
  package_points FLOAT DEFAULT 0.0,     -- 1.0, 0.5, or 0
  kyc_status VARCHAR(20),               -- 'Approved', 'Pending', 'Rejected'
  earning_wallet FLOAT DEFAULT 0.0,     -- Withdrawable portion
  withdrawable_wallet FLOAT DEFAULT 0.0, -- Available for withdrawal
  upgrade_wallet_balance FLOAT DEFAULT 0.0, -- Upgrade portion
  sponsor_id VARCHAR(12),
  created_at TIMESTAMP
);
```

#### `withdrawal_request` Table
```sql
CREATE TABLE withdrawal_request (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(12) REFERENCES "user"(id),
  withdrawal_amount INTEGER NOT NULL,   -- NET from withdrawable_wallet
  admin_charges INTEGER DEFAULT 0,      -- Always 0 (WV Protocol)
  tds_amount INTEGER DEFAULT 0,         -- Always 0 (WV Protocol)
  final_payout INTEGER NOT NULL,        -- Same as withdrawal_amount
  request_date DATE,
  status VARCHAR(30) DEFAULT 'Pending',
  is_auto_generated BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP,
  processed_at TIMESTAMP,
  payment_reference VARCHAR(255),
  paid_date TIMESTAMP,
  bank_name VARCHAR(255),
  account_number VARCHAR(255),
  ifsc_code VARCHAR(255),
  account_holder_name VARCHAR(255)
);
```

#### `pending_income` Table
```sql
CREATE TABLE pending_income (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(12) REFERENCES "user"(id),
  income_type VARCHAR(50),              -- 'Direct Referral', 'Matching Referral', etc.
  gross_amount NUMERIC(12,2),           -- Before deductions
  guru_dakshina_deduction NUMERIC(12,2) DEFAULT 0.0,  -- 2% or 0%
  admin_deduction NUMERIC(12,2),        -- 8% of gross
  tds_deduction NUMERIC(12,2),          -- 2% of gross
  net_amount NUMERIC(12,2),             -- After all deductions
  withdrawal_wallet_amount NUMERIC(12,2), -- Goes to earning_wallet
  upgraded_wallet_amount NUMERIC(12,2),   -- Goes to upgrade_wallet
  verification_status VARCHAR(30),      -- 'Pending', 'Auto-Approved', 'Accounts Paid'
  business_date DATE,                   -- Date income was earned
  created_at TIMESTAMP,
  verified_at TIMESTAMP,
  super_admin_verified_at TIMESTAMP,
  accounts_paid_at TIMESTAMP
);
```

---

## 12. Frontend Pages Reference

### Admin Pages

#### `/admin/withdrawal/history`
**Features:**
- View all withdrawal requests
- Filter by: Status, User ID, Date Range
- Stats cards: Completed, Pending, Cancelled
- Actions: Approve (Pending→Admin Verified), Reject
- View detailed breakdown modal with WV Protocol notice

### Finance Admin Pages

#### `/finance/withdrawal/queue`
**Features:**
- View "Super Admin Approved" withdrawals
- Ready for bank transfer
- Action: Mark Sent (→Sent)
- View withdrawal details with deduction breakdown

#### `/finance/withdrawal/history`
**Features:**
- View all transfer history
- Filter by: Status, User ID, Date Range
- Stats cards: Completed, Pending, Cancelled
- View detailed transaction records

### Super Admin Pages

#### `/superadmin/withdrawal/approvals` - Supreme Management
**Features:**
- **ONE unified page** with ALL powers
- 6 Status tracking cards (Pending, Admin Verified, SA Approved, Sent, Completed, Rejected)
- Dynamic filters (Status, User ID, Date Range)
- **Context-aware actions:**
  - Pending: Approve (as Admin), Reject
  - Admin Verified: SA Approve, Reject
  - SA Approved: Mark Sent
  - Sent: Mark Paid
  - Completed/Rejected: View only
- View detailed breakdown modal

### RVZ ID Pages

#### `/rvz/withdrawal/dashboard` - RVZ Supreme Dashboard
**Features:**
- **Supreme oversight** of ALL withdrawals
- 6 Status tracking cards with counts and amounts
- Dynamic filters (Status, User ID, Date Range)
- **FULL ACTION POWERS** (same as Super Admin):
  - Pending: Approve (as Admin), Reject
  - Admin Verified: SA Approve, Reject
  - SA Approved: Mark Sent
  - Sent: Mark Paid
  - Completed/Rejected: View only
- View detailed breakdown modal

### User Pages

#### `/user/withdrawals`
**Features:**
- View own withdrawal history
- Request new withdrawal
- View bank details
- Update bank information
- See wallet balances

---

## 13. Complete Example Flow

### Example: Platinum User Journey

**User Profile:**
- Package: Platinum (₹15,000)
- Package Points: 1.0
- KYC: Approved

### Day 1: Income Generation (October 26, 2025)

**Activities:**
- Direct referral activates (Platinum): ₹3,000 GROSS
- Ved income (3rd downline activates Platinum): ₹1,000 GROSS
- Matching income (1 pair matched): ₹2,000 GROSS
- Guru Dakshina (from referral's earnings): ₹200 GROSS

**Total GROSS earned:** ₹6,200

### Day 1 Midnight (October 27, 00:00 IST): Income Calculation

**Scheduler runs:** `calculate_daily_income()`

**1. Direct Referral Income (₹3,000 GROSS):**
```
GROSS: ₹3,000
- Guru Dakshina (2%): ₹60
- Admin (8%): ₹240
- TDS (2%): ₹60
━━━━━━━━━━━━━━━━━━━━━━
NET: ₹2,640

Package: Platinum (1.0)
Split: 100% withdrawable, 0% upgrade
→ Earning Wallet: ₹2,640
→ Upgrade Wallet: ₹0

Status: Auto-approved
```

**2. Ved Income (₹1,000 GROSS):**
```
GROSS: ₹1,000
- Guru Dakshina (2%): ₹20
- Admin (8%): ₹80
- TDS (2%): ₹20
━━━━━━━━━━━━━━━━━━━━━━
NET: ₹880

Split (Platinum 100/0):
→ Earning Wallet: ₹880
→ Upgrade Wallet: ₹0

Status: Auto-approved
```

**3. Matching Income (₹2,000 GROSS):**
```
GROSS: ₹2,000
- Guru Dakshina (2%): ₹40
- Admin (8%): ₹160
- TDS (2%): ₹40
━━━━━━━━━━━━━━━━━━━━━━
NET: ₹1,760

Split (Platinum 100/0):
→ Earning Wallet: ₹1,760
→ Upgrade Wallet: ₹0

Status: Auto-approved
```

**4. Guru Dakshina Income (₹200 GROSS):**
```
GROSS: ₹200
- Guru Dakshina: ₹0 (not applied)
- Admin (8%): ₹16
- TDS (2%): ₹4
━━━━━━━━━━━━━━━━━━━━━━
NET: ₹180

Split (Platinum 100/0):
→ Earning Wallet: ₹180
→ Upgrade Wallet: ₹0

Status: Auto-approved
```

**Total Summary:**
```
Total GROSS: ₹6,200
Total Deductions: ₹740 (11.9%)
Total NET: ₹5,460

Wallets:
Earning Wallet: ₹5,460
Upgrade Wallet: ₹0
```

**Auto-Approval Action:**
- All incomes auto-approved to 'Accounts Paid'
- Wallets credited immediately
- PendingIncome records deleted

### Day 2 Midnight (October 28, 00:00 IST): Wallet Sync

**Scheduler runs:** `sync_withdrawable_wallets()`

**Process:**
```
KYC Status: Approved ✅
Earning Wallet: ₹5,460
Withdrawable Wallet (before): ₹0

Action: Sync
Withdrawable Wallet (after): ₹5,460
Earning Wallet (after): ₹0
```

### Day 2 Midnight (Continued): Auto-Withdrawal Generation

**Scheduler runs:** `auto_generate_withdrawal_requests()`

**Calculation:**
```
Available: ₹5,460
Buffer: ₹100
Withdrawal Amount: ₹5,360

WV PROTOCOL CHECK:
✅ admin_charges = 0
✅ tds_amount = 0
✅ final_payout = ₹5,360
```

**Database Record Created:**
```sql
INSERT INTO withdrawal_request (
  user_id = 'BEV1800001',
  withdrawal_amount = 5360,
  admin_charges = 0,
  tds_amount = 0,
  final_payout = 5360,
  status = 'Pending',
  is_auto_generated = TRUE,
  bank_name = 'State Bank of India',
  account_number = '1234567890',
  ifsc_code = 'SBIN0001234',
  account_holder_name = 'John Doe'
)
```

### Day 2-5: Approval Workflow

**October 28, 09:00 - Admin Approval:**
```
Admin logs in → Views Pending withdrawals
Admin clicks "Approve" on withdrawal #375
Status: Pending → Admin Verified
```

**October 28, 10:00 - Super Admin Approval:**
```
Super Admin logs in → Views Admin Verified withdrawals
SA clicks "SA Approve" on withdrawal #375
Status: Admin Verified → Super Admin Approved
```

**October 28, 11:00 - Finance Marks Sent:**
```
Finance Admin logs in → Views Transfer Queue
Finance clicks "Mark Sent" on withdrawal #375
Enters payment reference: "NEFT/2025/1028/123456"
Status: Super Admin Approved → Sent
```

**October 30, 14:00 - Finance Marks Paid:**
```
Finance Admin logs in → Views Sent withdrawals
Finance clicks "Mark Paid" on withdrawal #375
Status: Sent → Completed
paid_date: October 30, 2025 14:00:00
```

### Final Result

**Bank Transfer:** ₹5,360 received by user ✅

**Complete Flow Summary Table:**

| Stage | GROSS | Deductions | NET | Earning | Withdrawable | Bank |
|-------|-------|------------|-----|---------|--------------|------|
| Income Gen | ₹6,200 | - | - | - | - | - |
| After Deductions | - | ₹740 | ₹5,460 | - | - | - |
| After Wallet Split | - | - | - | ₹5,460 | ₹0 | - |
| After Sync | - | - | - | ₹0 | ₹5,460 | - |
| After Buffer | - | - | - | - | ₹100 | - |
| **Final Transfer** | - | - | - | - | - | **₹5,360** |

**Deduction Breakdown:**
- Direct: ₹360 (12%)
- Ved: ₹120 (12%)
- Matching: ₹240 (12%)
- Guru: ₹20 (10%)
- **Total: ₹740**

---

## 14. Troubleshooting Guide

### Common Issues & Solutions

#### Issue: Withdrawals showing "Loading..." indefinitely
**Cause:** Using wrong status values or wrong data property

**Fix:**
```javascript
// CORRECT
var pending = data.requests.filter(w => w.status === 'Pending');

// WRONG - status values have spaces
var pending = data.requests.filter(w => w.status === 'PENDING');

// WRONG - property name
var pending = data.withdrawals.filter(...);
```

#### Issue: Stats cards showing 0
**Cause:** Filter logic using incorrect status values

**Fix:**
Use exact status values with proper case:
- 'Pending' (not 'PENDING' or 'pending')
- 'Admin Verified' (not 'ADMIN_VERIFIED')
- 'Super Admin Approved' (not 'SA_APPROVED')
- 'Sent' (not 'SENT')
- 'Completed' (not 'COMPLETED')

#### Issue: NET amount ≠ Final Payout
**Cause:** Additional deductions at withdrawal stage (WV Protocol violation)

**Fix:**
```python
# CORRECT - WV Protocol
admin_charges = 0
tds_amount = 0
final_payout = withdrawal_amount

# WRONG - Additional deductions
admin_charges = withdrawal_amount × 0.08  # ❌ NO!
```

#### Issue: Duplicate data in API responses
**Cause:** Multiple fetch calls for same data (DC Protocol violation)

**Fix:**
```javascript
// CORRECT - DC Protocol
const [data1, data2] = await Promise.all([
  fetch('/api/v1/withdrawals/admin/withdrawal-report'),
  fetch('/api/v1/withdrawals/income-transactions?user_id=' + userId)
]);

// WRONG - Duplicate calls
const data1 = await fetch('/api/v1/withdrawals/admin/withdrawal-report');
// ... later ...
const data2 = await fetch('/api/v1/withdrawals/admin/withdrawal-report'); // DUPLICATE!
```

### Verification Checklist

**WV Protocol Compliance:**
- [ ] GROSS and NET amounts both displayed
- [ ] Deduction breakdown shown clearly
- [ ] WV Protocol notice in all modals
- [ ] final_payout = withdrawal_amount (no additional deductions)
- [ ] admin_charges = 0 at withdrawal stage
- [ ] tds_amount = 0 at withdrawal stage

**DC Protocol Compliance:**
- [ ] Single source of truth for withdrawal data
- [ ] Promise.all() used for parallel calls
- [ ] No duplicate API calls
- [ ] Data cached in variables for filtering
- [ ] Access data.requests (not data.withdrawals)

**Functional Requirements:**
- [ ] All status values use proper case with spaces
- [ ] Stats cards update correctly
- [ ] Filters work (Status, User ID, Date Range)
- [ ] Action buttons appear based on status
- [ ] Modal shows complete breakdown
- [ ] Role-based access control working

---

## Summary

### Complete Flow Visualization

```
┌─────────────────────────────────────────────────┐
│ 1. USER REGISTRATION & BINARY TREE PLACEMENT   │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 2. INCOME GENERATION (4 Types)                 │
│    - Direct Referral                           │
│    - Matching Referral                         │
│    - Ved Income                                │
│    - Guru Dakshina                             │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 3. DAILY SCHEDULER (Midnight IST)              │
│    a) Calculate Income                         │
│    b) Apply Deductions (12% or 10%)            │
│       • Guru Dakshina: 2% (if applicable)      │
│       • Admin: 8% (always)                     │
│       • TDS: 2% (always)                       │
│    c) Calculate NET = GROSS - Deductions       │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 4. WALLET DISTRIBUTION                         │
│    Platinum (1.0): 100% Earning, 0% Upgrade    │
│    Others (0.5/0): 50% Earning, 50% Upgrade    │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 5. AUTO-APPROVAL & CREDITING                   │
│    - Set status: 'Accounts Paid'               │
│    - Credit wallets immediately                │
│    - Delete PendingIncome record               │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 6. DAILY WALLET SYNC (KYC Required)            │
│    Earning Wallet → Withdrawable Wallet        │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 7. AUTO-WITHDRAWAL GENERATION                  │
│    Amount = Withdrawable - Buffer              │
│    WV PROTOCOL: admin_charges=0, tds=0         │
│    final_payout = withdrawal_amount            │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 8. MULTI-ROLE APPROVAL WORKFLOW                │
│    Pending → Admin Verified → SA Approved →    │
│    Sent → Completed                            │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 9. BANK TRANSFER & COMPLETION                  │
│    NET amount to user's bank account           │
└─────────────────────────────────────────────────┘
```

### Key Principles

1. **Deductions ONCE** - Applied only at income calculation stage (12% or 10%)
2. **Withdrawals are NET** - No additional deductions (WV Protocol)
3. **Package-Based Splits** - Platinum 100/0, Others 50/50
4. **Single Source of Truth** - One API endpoint per data type (DC Protocol)
5. **Role-Based Powers** - Super Admin & RVZ ID have supreme powers
6. **Daily Automation** - Income calc, wallet sync, auto-withdrawals at midnight IST

---

**Document Version:** 2.0  
**Verification Status:** ✅ Code-Verified & Accurate  
**WV Protocol:** ✅ Compliant  
**DC Protocol:** ✅ Compliant  
**Last Updated:** October 28, 2025

For questions or issues, refer to the troubleshooting section or contact the development team.
