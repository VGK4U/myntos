# DC Protocol: Approval Workflow Analysis
## Date: November 2, 2025

## Critical Question: Do Materialized Views Handle ALL Approval Workflows?

### Two Approval Paths (Active from Nov 1st)

#### Path 1: Manual Multi-Level Approval
```
Pending (midnight calc)
   ↓
Admin Verified (Admin approval)
   ↓
Super Admin Verified (Super Admin approval)
   ↓
Accounts Paid (Finance Admin payment)
```

#### Path 2: Auto-Approval (VGK Skip-Level)
```
Pending (midnight calc)
   ↓
Accounts Paid (system auto-approves, skips all levels)
```
**Code**: `scheduler.py:50` - Sets status directly to 'Accounts Paid'

### Materialized View Definitions

#### user_earning_wallet_balance (Unpaid Income)
```sql
WHERE verification_status IN (
    'Pending',
    'Admin Verified', 
    'Super Admin Verified',
    'Super Admin Approved'
)
```

#### user_withdrawable_wallet_balance (Paid Income)
```sql
WHERE verification_status IN (
    'Finance Paid',
    'Accounts Paid'
)
```

### Analysis: BOTH Workflows Covered ✅

**Path 1 (Manual)**:
- Pending → **Earning Wallet** ✅
- Admin Verified → **Earning Wallet** ✅
- Super Admin Verified → **Earning Wallet** ✅
- Accounts Paid → **Withdrawable Wallet** ✅

**Path 2 (Auto-Approval)**:
- Pending → **Earning Wallet** ✅
- Accounts Paid → **Withdrawable Wallet** ✅

### Potential Issue: 'Finance Paid' Status

The withdrawable wallet view includes 'Finance Paid' but we haven't seen any records with this status in production. Let me verify if this is used:

**Production Data (Nov 1st onwards)**:
- Pending: 2 records (₹2,694)
- Finance Paid: 77 records (₹766,800)
- Accounts Paid: 1 record (₹54)

**Finding**: 'Finance Paid' IS being used! Need to understand the difference between 'Finance Paid' vs 'Accounts Paid'.

### Question: What's the difference between 'Finance Paid' and 'Accounts Paid'?

Checking the code...
