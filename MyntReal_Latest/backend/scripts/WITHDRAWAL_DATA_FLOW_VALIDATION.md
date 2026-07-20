# Withdrawal Data Flow Validation System

**Created:** October 27, 2025  
**Purpose:** Ensure systematic data flow and consistency between user dashboards and all admin panels

---

## 🎯 **CORE PRINCIPLE: Single Source of Truth**

**ALL withdrawal data MUST come from the `withdrawal_request` table**

```
User Dashboard ──┐
Admin Dashboard ─┼──→ withdrawal_request table (SINGLE SOURCE)
Finance Admin   ─┤
Super Admin     ─┤
RVZ Admin       ─┘
```

---

## 📊 **Data Flow Architecture**

### **1. Income Verification Flow (pending_income table)**

```
Income Earned → Pending → Admin Verified → Super Admin Approved → Finance Paid
                  ↓            ↓                    ↓                  ↓
               Visible    Admin Panel        Super Admin        Credited to
               to User      Review              Review          earning_wallet
```

**Status Values:** `Pending`, `Admin Verified`, `Super Admin Approved`, `Finance Paid`

**Key Point:** `Finance Paid` means income is **approved and credited to wallet**, NOT sent to bank!

---

### **2. Wallet Distribution Flow (user table)**

**After income is "Finance Paid":**

```
Net Income → earning_wallet (70%) + upgrade_wallet (30%)
              ↓
         Daily Sync (3 AM)
              ↓
         withdrawable_wallet (if KYC approved)
```

**Wallet Types:**
- `earning_wallet`: Accumulates 70% of net income
- `withdrawable_wallet`: Synced from earning_wallet for KYC-approved users
- `upgrade_wallet`: 30% of net income for package upgrades

---

### **3. Withdrawal Request Flow (withdrawal_request table)**

```
Auto-Generation (7 AM Mon-Sat)
         ↓
   User has ≥ ₹2,000 in withdrawable_wallet?
         ↓ YES
Create withdrawal_request (status: Pending)
         ↓
   Admin Verification
         ↓
   status: Admin Verified
         ↓
   Super Admin Approval
         ↓
   status: Super Admin Approved
         ↓
   Finance Bank Send
         ↓
   status: Bank Sent
         ↓
   Payment Confirmation
         ↓
   status: Completed ✅
```

**Status Values:** `Pending`, `Admin Verified`, `Super Admin Approved`, `Bank Sent`, `Completed`, `Cancelled`, `Rejected`

---

## 🔄 **Data Consistency Rules**

### **Rule 1: Withdrawal Display Logic**

**User Dashboard "Paid to Bank":**
```sql
SELECT SUM(final_payout) 
FROM withdrawal_request 
WHERE user_id = ? AND status = 'Completed'
```

**User Dashboard "Overall Pending":**
```sql
SELECT SUM(final_payout) 
FROM withdrawal_request 
WHERE user_id = ? AND status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent')
```

**User Dashboard "Admin Pending":**
```sql
SELECT SUM(final_payout) 
FROM withdrawal_request 
WHERE user_id = ? AND status = 'Pending'
```

---

### **Rule 2: Admin Dashboard Filtering**

**ALL admin dashboards MUST use identical queries:**

```python
# Admin Withdrawal Queue (Pending)
query = db.query(WithdrawalRequest).filter(
    WithdrawalRequest.status == 'Pending'
)

# Finance Admin (Admin Verified)
query = db.query(WithdrawalRequest).filter(
    WithdrawalRequest.status == 'Admin Verified'
)

# Super Admin (Super Admin Approved)
query = db.query(WithdrawalRequest).filter(
    WithdrawalRequest.status == 'Super Admin Approved'
)
```

**CRITICAL:** Use exact status values with proper capitalization!

---

### **Rule 3: Auto-Withdrawal Generation Validation**

**Before creating a withdrawal, verify:**

1. ✅ User has KYC approved
2. ✅ User's `withdrawable_wallet` ≥ ₹2,000
3. ✅ No existing pending withdrawal for user
4. ✅ Amount doesn't exceed ₹50,000 (VGK configurable)
5. ✅ Day is Monday-Saturday (not Sunday)

**DO NOT create withdrawal if:**
- ❌ User already has a pending withdrawal
- ❌ Withdrawable wallet < ₹2,000
- ❌ KYC not approved

---

## 🛡️ **Validation Checks**

### **Check 1: User-Admin Data Consistency**

**For each user, verify:**

```sql
-- User Dashboard displays
SELECT 
  u.id,
  u.name,
  u.earning_wallet,
  u.withdrawable_wallet,
  -- Calculated from withdrawal_request
  COALESCE(SUM(CASE WHEN wr.status = 'Completed' THEN wr.final_payout ELSE 0 END), 0) as paid_to_bank,
  COALESCE(SUM(CASE WHEN wr.status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent') THEN wr.final_payout ELSE 0 END), 0) as overall_pending
FROM "user" u
LEFT JOIN withdrawal_request wr ON u.id = wr.user_id
GROUP BY u.id, u.name, u.earning_wallet, u.withdrawable_wallet;
```

**MUST MATCH admin dashboard for same user!**

---

### **Check 2: No Duplicate Pending Withdrawals**

```sql
-- Each user should have MAX 1 pending withdrawal
SELECT user_id, COUNT(*) as pending_count
FROM withdrawal_request
WHERE status = 'Pending'
GROUP BY user_id
HAVING COUNT(*) > 1;
-- Result: Should be EMPTY
```

---

### **Check 3: Status Value Integrity**

```sql
-- Verify all status values are valid
SELECT DISTINCT status, COUNT(*) 
FROM withdrawal_request 
GROUP BY status;

-- Expected results ONLY:
-- Pending
-- Admin Verified
-- Super Admin Approved
-- Bank Sent
-- Completed
-- Cancelled
-- Rejected
```

**NO other status values allowed!**

---

### **Check 4: Income vs Withdrawal Consistency**

```sql
-- Verify wallet balances match withdrawal history
SELECT 
  u.id,
  u.withdrawable_wallet,
  -- Total income credited
  COALESCE(SUM(CASE WHEN pi.verification_status = 'Finance Paid' THEN pi.net_amount ELSE 0 END), 0) as total_income,
  -- Total withdrawn (completed)
  COALESCE(SUM(CASE WHEN wr.status = 'Completed' THEN wr.withdrawal_amount ELSE 0 END), 0) as total_withdrawn,
  -- Pending withdrawals
  COALESCE(SUM(CASE WHEN wr.status IN ('Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent') THEN wr.withdrawal_amount ELSE 0 END), 0) as pending_amount
FROM "user" u
LEFT JOIN pending_income pi ON u.id = pi.user_id
LEFT JOIN withdrawal_request wr ON u.id = wr.user_id
GROUP BY u.id, u.withdrawable_wallet;

-- Validate: withdrawable_wallet + total_withdrawn + pending_amount ≈ total_income * 0.7
```

---

## 🔧 **API Endpoint Standards**

### **User Endpoints (Must be identical for all users)**

**GET `/api/v1/withdrawals/summary`**
- Returns: `total_earned`, `total_paid`, `overall_pending`, `admin_pending`
- Source: `withdrawal_request` table
- Cache: NO CACHE headers

**GET `/api/v1/withdrawals/income-transactions`**
- Returns: All income records for user
- Source: `pending_income` table  
- Cache: NO CACHE headers

---

### **Admin Endpoints (Must use correct parameter names)**

**GET `/api/v1/withdrawals/admin/withdrawal-report?status_filter=Pending`**
- Parameter: `status_filter` (NOT `status`)
- Filter: Exact match with proper capitalization
- Cache: NO CACHE headers

**GET `/api/v1/withdrawals/admin/withdrawal-report?user_id=MNR123`**
- Filter: Specific user
- Cache: NO CACHE headers

---

## 🚨 **Common Issues & Prevention**

### **Issue 1: Invalid Auto-Generated Withdrawals**

**Symptom:** User shows "all paid" but admin shows pending withdrawal

**Root Cause:** Auto-withdrawal created even when income already processed

**Prevention:**
```python
# In auto-withdrawal scheduler (7 AM job)
def generate_withdrawals():
    # Check if user already has pending withdrawal
    existing = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == user_id,
        WithdrawalRequest.status.in_(['Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent'])
    ).first()
    
    if existing:
        logger.warning(f"User {user_id} already has pending withdrawal #{existing.id}, skipping")
        return  # DO NOT create duplicate
    
    # Only create if withdrawable_wallet >= 2000
    if user.withdrawable_wallet < 2000:
        return
```

---

### **Issue 2: Browser Cache Showing Stale Data**

**Symptom:** User/admin sees old data even after refresh

**Prevention:**
```python
# Add to ALL financial API endpoints
def add_no_cache_headers(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
```

```javascript
// Add cache-busting timestamp to frontend
fetch(`/api/v1/withdrawals/admin/withdrawal-report?status_filter=Pending&_t=${Date.now()}`)
```

---

### **Issue 3: Status Filter Case Mismatch**

**Symptom:** Filter returns all records instead of filtered subset

**Root Cause:** Frontend sends `status=PENDING`, backend expects `Pending`

**Prevention:**
- Always use exact capitalization: `Pending`, `Admin Verified`, `Super Admin Approved`
- Use backend parameter name: `status_filter` not `status`
- Test filters with SQL queries first

---

## 📋 **Daily Validation Script**

**File:** `backend/scripts/validate_withdrawal_data.py`

Run this daily to ensure data consistency:

```python
#!/usr/bin/env python3
"""
Daily validation script to ensure withdrawal data consistency
Run: python backend/scripts/validate_withdrawal_data.py
"""

from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

def validate_data():
    with engine.connect() as conn:
        # Check 1: No duplicate pending withdrawals
        result = conn.execute(text("""
            SELECT user_id, COUNT(*) as count
            FROM withdrawal_request
            WHERE status = 'Pending'
            GROUP BY user_id
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        if duplicates:
            print(f"❌ CRITICAL: {len(duplicates)} users have duplicate pending withdrawals!")
            for row in duplicates:
                print(f"   User {row[0]}: {row[1]} pending withdrawals")
        else:
            print("✅ No duplicate pending withdrawals")
        
        # Check 2: Status value integrity
        result = conn.execute(text("""
            SELECT DISTINCT status FROM withdrawal_request
        """))
        valid_statuses = {'Pending', 'Admin Verified', 'Super Admin Approved', 'Bank Sent', 'Completed', 'Cancelled', 'Rejected'}
        actual_statuses = {row[0] for row in result.fetchall()}
        invalid = actual_statuses - valid_statuses
        if invalid:
            print(f"❌ CRITICAL: Invalid status values found: {invalid}")
        else:
            print("✅ All status values are valid")
        
        # Check 3: Summary statistics
        result = conn.execute(text("""
            SELECT status, COUNT(*), SUM(withdrawal_amount)
            FROM withdrawal_request
            GROUP BY status
        """))
        print("\n📊 Withdrawal Summary:")
        for row in result.fetchall():
            print(f"   {row[0]}: {row[1]} requests, ₹{row[2]:,.0f}")

if __name__ == '__main__':
    validate_data()
```

---

## 🔗 **Related Documentation**

- `DATA_CONNECTION_MAP.md` - Complete API endpoint mapping
- `DATA_CONSISTENCY_CHECKLIST.md` - Manual validation checklist
- `STATUS_FILTER_BUG_FIX.md` - Case sensitivity fix details
- `PRODUCTION_RESET_COMPLETE.md` - Production data reset logic

---

## ✅ **Deployment Checklist**

Before deploying any withdrawal-related changes:

- [ ] All admin endpoints use `status_filter` parameter
- [ ] All status values use exact capitalization
- [ ] No-cache headers added to all financial endpoints
- [ ] Cache-busting timestamps in frontend API calls
- [ ] Auto-withdrawal logic checks for existing pending withdrawals
- [ ] Validation script runs successfully with no errors
- [ ] User dashboard matches admin dashboard for test users
- [ ] Browser hard refresh clears all cached data

---

**Last Updated:** October 27, 2025  
**Status:** ✅ System Validated - All Data Flows Consistent
