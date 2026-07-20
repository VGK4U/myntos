# BeV EV Reference Program - Complete System Analysis
## BEFORE Documentation Update - Verification Report

**Generated:** October 28, 2025  
**Purpose:** Comprehensive point-wise analysis as per WV & DC Protocol

---

## 📊 PACKAGE-WISE BREAKDOWN

### Package Details & Wallet Split

| Package | Price | Points | Withdrawable | Upgrade Wallet | Referrer Bonus | Max Bonuses |
|---------|-------|--------|--------------|----------------|----------------|-------------|
| **Platinum** 🏆 | ₹15,000 | 1.0 | **100%** | **0%** | ₹3,000 | 1 |
| **Diamond** 💎 | ₹7,500 | 0.5 | **50%** | **50%** | ₹1,500 | 2 |
| **Blue** 🔵 | ₹1,000 | 0 | **50%** | **50%** | ₹0 | 2 |
| **Loyal** 🟠 | ₹500 | 0 | **50%** | **50%** | ₹0 | 2 |

**KEY FINDING:** 
- ✅ Platinum users: 100% of NET goes to Earning Wallet (fully withdrawable)
- ✅ Other packages: 50/50 split between Earning and Upgrade wallets
- ❌ **WRONG in previous docs**: 70/30 split does NOT exist

---

## 💰 DEDUCTION STRUCTURE

### Master Deduction Rates

| Deduction Type | Rate | Applied On | When |
|---------------|------|------------|------|
| **Guru Dakshina** | 2% | GROSS | All incomes EXCEPT Guru Dakshina income itself |
| **Admin Charges** | 8% | GROSS | All incomes (always) |
| **TDS (Tax)** | 2% | GROSS | All incomes (always) |
| **Total Deductions** | 12% | GROSS | When Guru Dakshina applies |
| **Total Deductions** | 10% | GROSS | For Guru Dakshina income (no recursive GD) |

### Deduction Calculation Formula

```
CASE 1: Regular Income (with Guru Dakshina)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROSS Income                           ₹10,000
- Guru Dakshina (2% of GROSS)         -₹200
- Admin Charges (8% of GROSS)         -₹800
- TDS (2% of GROSS)                   -₹200
─────────────────────────────────────────────
NET Income (88% of GROSS)             ₹8,800

Then wallet split:
- Platinum: ₹8,800 → Earning Wallet
- Diamond/Blue/Loyal: ₹4,400 → Earning + ₹4,400 → Upgrade

CASE 2: Guru Dakshina Income (no recursive GD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROSS Income (from referral's GD)     ₹200
- Guru Dakshina                       -₹0 (NOT applied)
- Admin Charges (8% of GROSS)         -₹16
- TDS (2% of GROSS)                   -₹4
─────────────────────────────────────────────
NET Income (90% of GROSS)             ₹180
```

---

## 📈 EARNINGS FLOW - GROSS TO NET TO WITHDRAWAL

### Stage 1: Income Generation

**Four Income Types:**

1. **Direct Referral Income**
   - Platinum referral: ₹3,000 GROSS (paid to referrer)
   - Diamond referral: ₹1,500 GROSS (paid to referrer)
   - Blue/Loyal: ₹0 (no bonus)

2. **Matching Referral Income**
   - Fixed rate: ₹2,000 per 1:1 point match
   - First match requirement: 2:1 or 1:2 ratio
   - After first match: Simple 1:1 matching

3. **Ved Income**
   - Platinum activation: ₹1,000 to 3rd upline
   - Diamond activation: ₹500 to 3rd upline
   - Blue/Loyal: ₹0

4. **Guru Dakshina**
   - 2% of each direct referral's total GROSS earnings
   - Paid to referrer
   - Does NOT have Guru Dakshina deduction (no recursive)

### Stage 2: Income Calculation (Daily Midnight IST)

**Scheduler Job:** `calculate_daily_income()`

**Process:**
```
For each user:
  1. Calculate GROSS income for previous day
  2. Apply deductions:
     - Guru Dakshina: 2% of GROSS (if applicable)
     - Admin: 8% of GROSS
     - TDS: 2% of GROSS
  3. Calculate NET = GROSS - Total Deductions
  4. Get wallet split based on package points:
     - Platinum (1.0): 100/0
     - Diamond (0.5): 50/50
     - Blue/Loyal (0): 50/50
  5. Calculate amounts:
     - withdrawal_wallet_amount = NET × (withdrawable%)
     - upgraded_wallet_amount = NET × (upgrade%)
  6. Create PendingIncome record with:
     - gross_amount
     - guru_dakshina_deduction
     - admin_deduction
     - tds_deduction
     - net_amount
     - withdrawal_wallet_amount
     - upgraded_wallet_amount
     - verification_status: 'Auto-Approved' or 'Pending'
```

**Auto-Approval:**
- Direct Referral: Auto-approved immediately
- Ved Income: Auto-approved immediately
- Guru Dakshina: Auto-approved immediately
- Matching Referral: Auto-approved if eligible; else 'Pending'

### Stage 3: Wallet Crediting

**Auto-Approval Process:**
```
1. Set verification_status = 'Accounts Paid'
2. Credit wallets:
   - earning_wallet += withdrawal_wallet_amount
   - upgrade_wallet_balance += upgraded_wallet_amount
3. Create Transaction record (amount = net_amount)
4. DELETE PendingIncome record (avoid duplicates)
```

**Manual Approval Process (for non-auto-approved):**
```
Status Flow: Pending → Admin Verified → Super Admin Approved → Accounts Paid
Then same wallet crediting as above
```

### Stage 4: Wallet Synchronization (Daily Midnight IST)

**Scheduler Job:** `sync_withdrawable_wallets()`

**Process:**
```
For each KYC-approved user:
  1. Check earning_wallet balance
  2. If balance > 0:
     - withdrawable_wallet += earning_wallet
     - earning_wallet = 0
  3. Save changes

For non-KYC users:
  - Income accumulates in earning_wallet
  - CANNOT transfer to withdrawable_wallet
  - CANNOT withdraw
```

**KYC Requirement:** CRITICAL for withdrawal eligibility

### Stage 5: Withdrawal Request Creation

**Scheduler Job:** `auto_generate_withdrawal_requests()`

**Auto-Generation Criteria:**
```
1. KYC status = 'Approved'
2. withdrawable_wallet >= ₹1,000 (minimum threshold)
3. No existing pending withdrawal
4. Bank details present (from KYC or profile)
```

**Withdrawal Amount Calculation:**
```python
available = withdrawable_wallet
withdrawal_amount = available - buffer_amount (₹100)

# Cap at max limit
if withdrawal_amount > ₹50,000:
    withdrawal_amount = ₹50,000

# Minimum check
if withdrawal_amount < ₹1,000:
    Skip user

# WV PROTOCOL: NO ADDITIONAL DEDUCTIONS
admin_charges = 0
tds_amount = 0
final_payout = withdrawal_amount
```

**Database Record:**
```sql
INSERT INTO withdrawal_request (
  user_id,
  withdrawal_amount,     -- NET amount from withdrawable_wallet
  admin_charges,         -- 0 (already deducted at income stage)
  tds_amount,           -- 0 (already deducted at income stage)
  final_payout,         -- Same as withdrawal_amount
  status,               -- 'Pending'
  is_auto_generated,    -- TRUE
  bank_name,
  account_number,
  ifsc_code,
  account_holder_name
)
```

---

## 🔄 WITHDRAWAL APPROVAL WORKFLOW

### Status Flow

```
Pending 
   ↓ (Admin Action: Approve)
Admin Verified
   ↓ (Super Admin Action: Approve)
Super Admin Approved
   ↓ (Finance Action: Mark Sent)
Sent
   ↓ (Finance Action: Mark Paid)
Completed

At any stage before Sent:
   → (Admin/SA Action: Reject) → Rejected
```

### Role-Based Powers

| Role | Status Access | Actions Available |
|------|--------------|-------------------|
| **Admin** | All | Approve (Pending→Admin Verified), Reject |
| **Super Admin** | All | ALL powers (Admin approve, SA approve, Mark Sent, Mark Paid, Reject) |
| **Finance Admin** | SA Approved, Sent, Completed | Mark Sent, Mark Paid |
| **RVZ ID** | All | ALL powers (Admin approve, SA approve, Mark Sent, Mark Paid, Reject) |

### API Endpoints by Role

**Admin Actions:**
```
POST /api/v1/withdrawals/admin/process/{id}
Body: {
  "action": "approve" | "reject",
  "admin_notes": "Optional"
}
Effect:
  - approve: Pending → Admin Verified
  - reject: Any → Rejected
```

**Super Admin Actions:**
```
POST /api/v1/withdrawals/superadmin/process/{id}
Body: {
  "action": "approve" | "reject"
}
Effect:
  - approve: Admin Verified → Super Admin Approved
  - reject: Any → Rejected
```

**Finance Actions:**
```
POST /api/v1/withdrawals/finance/process-transfer/{id}
Body: {
  "action": "sent" | "paid",
  "payment_reference": "Optional"
}
Effect:
  - sent: Super Admin Approved → Sent
  - paid: Sent → Completed
```

---

## 🛡️ WV PROTOCOL (Withdrawal-Validation Protocol)

### Core Principle
> **NET amount at withdrawal stage = Final payout to bank**  
> **NO additional deductions at withdrawal stage**

### Implementation Verification

**At Income Calculation Stage:**
```python
# Line 90-135 in scheduler.py
guru_dakshina_deduction = gross × 2%
admin_deduction = gross × 8%
tds_deduction = gross × 2%
net_amount = gross - (guru + admin + tds)
```

**At Withdrawal Creation Stage:**
```python
# Line 2495-2499 in scheduler.py
# VERIFIED: NO ADDITIONAL DEDUCTIONS
admin_charges = 0
tds_amount = 0
final_payout = withdrawal_amount
```

**Database Schema:**
```sql
withdrawal_request:
  - withdrawal_amount (NET from withdrawable_wallet)
  - admin_charges (0)
  - tds_amount (0)
  - final_payout (= withdrawal_amount)
```

### WV Protocol Compliance Checklist

- [x] All deductions happen at income calculation stage
- [x] admin_charges = 0 at withdrawal stage
- [x] tds_amount = 0 at withdrawal stage
- [x] final_payout = withdrawal_amount (no reduction)
- [x] Withdrawable wallet contains already NET amounts
- [x] User receives full withdrawable balance (minus buffer)

**✅ WV PROTOCOL: FULLY COMPLIANT**

---

## 🔐 DC PROTOCOL (Data Consistency Protocol)

### Core Principle
> **Single source of truth for withdrawal data**  
> **NO duplicate API calls**

### Data Source Hierarchy

**Primary Source:** `/api/v1/withdrawals/admin/withdrawal-report`
```json
{
  "requests": [
    {
      "id": 375,
      "user_id": "BEV1800001",
      "user_name": "John Doe",
      "withdrawal_amount": 10000,
      "final_payout": 10000,
      "status": "Completed",
      "bank_name": "SBI",
      "account_number": "1234567890",
      "ifsc_code": "SBIN001234",
      "account_holder_name": "John Doe",
      "created_at": "2025-10-27T12:00:00"
    }
  ]
}
```

**Supporting Source:** `/api/v1/withdrawals/income-transactions?user_id={id}`
```json
{
  "summary": {
    "total_earned_gross": 25000,
    "total_earned_net": 22000,
    "direct_referral_income": 5000,
    "matching_referral_income": 10000
  }
}
```

**Detailed Source:** `/api/v1/withdrawals/admin/withdrawal-income-breakdown/{id}`
```json
{
  "breakdown_by_type": [
    {
      "income_type": "Direct Referral",
      "gross": 5000,
      "guru_dakshina_deduction": 100,
      "admin_deduction": 400,
      "tds_deduction": 100,
      "net": 4400
    }
  ],
  "totals": {
    "gross": 25000,
    "total_deductions": 3000,
    "net": 22000
  }
}
```

### DC Protocol Implementation Pattern

**CORRECT (Single call):**
```javascript
Promise.all([
  fetch('/api/v1/withdrawals/admin/withdrawal-report'),
  fetch('/api/v1/withdrawals/income-transactions?user_id=' + userId),
  fetch('/api/v1/withdrawals/admin/withdrawal-income-breakdown/' + withdrawalId)
]).then(([data1, data2, data3]) => {
  // Use data once
});
```

**WRONG (Duplicate calls):**
```javascript
// Call 1
fetch('/api/v1/withdrawals/admin/withdrawal-report')
// ...later in code...
// Call 2 - DUPLICATE!
fetch('/api/v1/withdrawals/admin/withdrawal-report')
```

### DC Protocol Compliance Checklist

- [x] Single API call per data source
- [x] Promise.all() for parallel execution
- [x] Data cached in variables for filtering
- [x] No redundant fetches
- [x] Primary source: withdrawal-report
- [x] Supporting sources called only once

**✅ DC PROTOCOL: FULLY COMPLIANT**

---

## 📊 COMPLETE EARNINGS TO WITHDRAWAL EXAMPLE

### Example: Platinum User Journey

**User Profile:**
- Package: Platinum (₹15,000)
- Package Points: 1.0
- KYC: Approved

**Day 1: Income Generation**
```
Direct Referral (Platinum): ₹3,000 GROSS
Ved Income: ₹1,000 GROSS
Matching Income: ₹2,000 GROSS
Guru Dakshina: ₹200 GROSS

Total GROSS: ₹6,200
```

**Day 1 Midnight: Income Calculation**
```
Direct Referral Income:
  GROSS: ₹3,000
  - Guru Dakshina (2%): ₹60
  - Admin (8%): ₹240
  - TDS (2%): ₹60
  NET: ₹2,640
  Wallet split (Platinum 100/0):
    → Earning Wallet: ₹2,640
    → Upgrade Wallet: ₹0

Ved Income:
  GROSS: ₹1,000
  - Guru Dakshina (2%): ₹20
  - Admin (8%): ₹80
  - TDS (2%): ₹20
  NET: ₹880
  Wallet split:
    → Earning Wallet: ₹880
    → Upgrade Wallet: ₹0

Matching Income:
  GROSS: ₹2,000
  - Guru Dakshina (2%): ₹40
  - Admin (8%): ₹160
  - TDS (2%): ₹40
  NET: ₹1,760
  Wallet split:
    → Earning Wallet: ₹1,760
    → Upgrade Wallet: ₹0

Guru Dakshina Income:
  GROSS: ₹200
  - Guru Dakshina: ₹0 (not applied)
  - Admin (8%): ₹16
  - TDS (2%): ₹4
  NET: ₹180
  Wallet split:
    → Earning Wallet: ₹180
    → Upgrade Wallet: ₹0

═══════════════════════════════════════
Total GROSS: ₹6,200
Total NET: ₹5,460
Total Earning Wallet: ₹5,460
Total Upgrade Wallet: ₹0
```

**Day 2 Midnight: Wallet Sync**
```
KYC Approved? YES
earning_wallet: ₹5,460
withdrawable_wallet before: ₹0

Action: Sync
withdrawable_wallet after: ₹5,460
earning_wallet after: ₹0
```

**Day 2 Midnight: Auto-Withdrawal Generation**
```
Available: ₹5,460
Buffer: ₹100
Withdrawal Amount: ₹5,360

WV PROTOCOL:
  admin_charges: ₹0
  tds_amount: ₹0
  final_payout: ₹5,360

Status: Pending
```

**Day 3: Approval Workflow**
```
09:00 - Admin approves: Pending → Admin Verified
10:00 - SA approves: Admin Verified → Super Admin Approved
11:00 - Finance marks sent: SA Approved → Sent
Day 5 - Finance marks paid: Sent → Completed
```

**Final Bank Transfer: ₹5,360** ✅

### Summary Table

| Stage | GROSS | Deductions | NET | Withdrawable |
|-------|-------|------------|-----|--------------|
| Income Generation | ₹6,200 | - | - | - |
| After Deductions | - | ₹740 (12%) | ₹5,460 | - |
| After Wallet Split | - | - | ₹5,460 | ₹0 |
| After Sync | - | - | ₹0 | ₹5,460 |
| After Buffer | - | - | - | ₹5,360 |
| **Bank Transfer** | - | - | - | **₹5,360** |

**Deduction Breakdown:**
- Direct: ₹60 + ₹240 + ₹60 = ₹360
- Ved: ₹20 + ₹80 + ₹20 = ₹120
- Matching: ₹40 + ₹160 + ₹40 = ₹240
- Guru: ₹0 + ₹16 + ₹4 = ₹20
- **Total: ₹740 (11.9% of GROSS)**

---

## 🎯 KEY TAKEAWAYS

### ✅ Correct Facts

1. **Package-wise wallet splits:**
   - Platinum: 100% withdrawable, 0% upgrade
   - Diamond/Blue/Loyal: 50% withdrawable, 50% upgrade

2. **Deduction rates:**
   - Guru Dakshina: 2% of GROSS (when applicable)
   - Admin: 8% of GROSS (always)
   - TDS: 2% of GROSS (always)
   - Total: 12% (with GD) or 10% (without GD)

3. **Deductions applied ONCE:**
   - At income calculation stage ONLY
   - NO additional deductions at withdrawal stage

4. **WV Protocol:**
   - NET amount = Final payout
   - admin_charges = 0 at withdrawal
   - tds_amount = 0 at withdrawal
   - Fully compliant ✅

5. **DC Protocol:**
   - Single source of truth: withdrawal-report
   - No duplicate API calls
   - Promise.all() for parallel fetches
   - Fully compliant ✅

6. **Role powers:**
   - Super Admin: Supreme (all powers)
   - RVZ ID: Supreme (all powers) ✅ JUST GRANTED
   - Finance: Mark Sent/Paid only
   - Admin: Approve/Reject Pending only

### ❌ Previous Errors (Now Corrected)

1. ~~70/30 wallet split~~ → **100/0 for Platinum, 50/50 for others**
2. ~~VGK view-only~~ → **VGK has full supreme powers** ✅

---

## 📝 NEXT STEPS

1. ✅ **Granted RVZ ID full supreme powers** (DONE)
2. ⏳ **Update comprehensive documentation** with correct data
3. ⏳ **Verify all frontend pages** show correct split percentages
4. ⏳ **Final testing** of complete flow

---

**Document Status:** ✅ Analysis Complete - Ready for Documentation Update  
**Verified Against:** Actual backend implementation in scheduler.py, constants.py, withdrawal.py  
**Compliance:** WV Protocol ✅ | DC Protocol ✅
