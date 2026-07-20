# Data Consistency Validation Checklist

## 🎯 **When to Run This:**
- After migrating wallet balances
- After batch updating income statuses
- After changing withdrawal request statuses
- Before deploying to production
- After any scheduler job failures

---

## ✅ **STEP-BY-STEP VALIDATION:**

### **1. Validate Income → Wallet Flow**

```sql
-- Check that earning_wallet matches Finance Paid income
SELECT 
    u.id, u.name,
    u.earning_wallet,
    (SELECT SUM(net_amount) FROM pending_income WHERE user_id = u.id AND verification_status = 'Finance Paid') as income_paid,
    CASE 
        WHEN u.package_points = 1.0 AND ABS(u.earning_wallet - (SELECT COALESCE(SUM(net_amount), 0) FROM pending_income WHERE user_id = u.id AND verification_status = 'Finance Paid')) > 1 
        THEN '❌ MISMATCH' ELSE '✅ OK' 
    END as validation
FROM "user" u
WHERE u.earning_wallet > 0
ORDER BY validation, income_paid DESC;
```

**Expected:** All users show ✅ OK

---

### **2. Validate Withdrawal → Wallet Flow**

```sql
-- Check that pending withdrawals don't exceed withdrawable balance
SELECT 
    u.id, u.name,
    u.withdrawable_wallet,
    (SELECT SUM(withdrawal_amount) FROM withdrawal_request WHERE user_id = u.id AND status = 'Pending') as pending_withdrawals,
    CASE 
        WHEN (SELECT COALESCE(SUM(withdrawal_amount), 0) FROM withdrawal_request WHERE user_id = u.id AND status = 'Pending') > u.withdrawable_wallet 
        THEN '❌ INSUFFICIENT' ELSE '✅ OK' 
    END as validation
FROM "user" u
WHERE u.withdrawable_wallet > 0
ORDER BY validation, pending_withdrawals DESC;
```

**Expected:** All users show ✅ OK

---

### **3. Status Distribution Check**

```sql
-- Income statuses (should be all "Finance Paid" for production)
SELECT verification_status, COUNT(*), SUM(net_amount)
FROM pending_income
GROUP BY verification_status;

-- Withdrawal statuses
SELECT status, COUNT(*), SUM(withdrawal_amount)
FROM withdrawal_request
GROUP BY status;
```

**Expected:**
- Income: All "Finance Paid" (or known Pending counts)
- Withdrawals: Pending count matches admin dashboard

---

### **4. Admin Dashboard Cross-Check**

After database validation, verify admin pages show consistent data:

1. **Admin Income Pages:**
   - `/admin/income-pending` → Should show 0 if all Finance Paid
   - `/admin/income-verified` → Should show 0 if all Finance Paid

2. **Admin Withdrawal Pages:**
   - `/admin/withdrawals` (React TSX) → Pending count matches DB
   - `/admin/earnings-withdrawals` (HTML) → User data matches wallets

3. **User Dashboard:**
   - `/user/withdrawals` → Wallet balances match earning_wallet

---

## 🔄 **Complete Data Flow Map:**

```
SCHEDULER (Daily Midnight)
    ↓
pending_income.verification_status = 'Pending'
    ↓
ADMIN VERIFIES
    ↓
pending_income.verification_status = 'Admin Verified'
    ↓
SUPER ADMIN APPROVES
    ↓
pending_income.verification_status = 'Super Admin Approved'
    ↓
FINANCE ADMIN PROCESSES
    ↓
pending_income.verification_status = 'Finance Paid'
WalletService.create_transaction()
    ↓
user.earning_wallet += net_amount (Platinum: 100%, Others: 50%)
user.upgrade_wallet_balance += (Others: 50%, Platinum: 0%)
    ↓
DAILY WALLET SYNC (3 AM)
    ↓
user.withdrawable_wallet = user.earning_wallet (if KYC approved)
    ↓
USER REQUESTS WITHDRAWAL
    ↓
withdrawal_request.status = 'Pending'
user.withdrawable_wallet -= withdrawal_amount (reserved)
    ↓
ADMIN/FINANCE VERIFICATION WORKFLOW
    ↓
withdrawal_request.status = 'Admin Verified' → 'Bank Sent' → 'Completed'
```

---

## 🚨 **Red Flags to Watch:**

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Wallet Mismatch** | earning_wallet ≠ Finance Paid income | Re-run wallet migration script |
| **Insufficient Balance** | Pending withdrawals > withdrawable_wallet | Cancel invalid withdrawals, re-credit |
| **Duplicate Income** | Same business_date + user_id + type | Check scheduler idempotency |
| **Orphaned Withdrawals** | Withdrawal exists but user deleted | Add FK constraints |
| **Stuck Status** | Income in "Pending" for >7 days | Manual finance approval needed |

---

## 🛠️ **Quick Fix Scripts:**

### **Re-Migrate ALL User Wallets:**

```sql
UPDATE "user" u
SET 
    earning_wallet = CASE 
        WHEN u.package_points = 1.0 THEN paid_totals.paid_net
        ELSE paid_totals.paid_net * 0.5
    END,
    upgrade_wallet_balance = CASE 
        WHEN u.package_points = 1.0 THEN 0
        ELSE paid_totals.paid_net * 0.5
    END,
    withdrawable_wallet = CASE 
        WHEN u.kyc_status = 'Approved' AND u.package_points = 1.0 THEN paid_totals.paid_net
        WHEN u.kyc_status = 'Approved' THEN paid_totals.paid_net * 0.5
        ELSE u.withdrawable_wallet
    END
FROM (
    SELECT user_id, SUM(net_amount) as paid_net
    FROM pending_income
    WHERE verification_status = 'Finance Paid'
    GROUP BY user_id
) AS paid_totals
WHERE u.id = paid_totals.user_id;
```

### **Cancel Invalid Withdrawals:**

```sql
-- Find withdrawals exceeding wallet balance
SELECT wr.id, wr.user_id, wr.withdrawal_amount, u.withdrawable_wallet
FROM withdrawal_request wr
INNER JOIN "user" u ON wr.user_id = u.id
WHERE wr.status = 'Pending' 
  AND wr.withdrawal_amount > u.withdrawable_wallet;

-- Cancel and re-credit (run per withdrawal)
UPDATE withdrawal_request SET status = 'Cancelled' WHERE id = ?;
UPDATE "user" SET withdrawable_wallet = withdrawable_wallet + ? WHERE id = ?;
```

---

## 📊 **Automated Monitoring (Future):**

Add to scheduler:
```python
def daily_validation_check():
    """Run at 11 PM daily - before midnight income calculation"""
    # Check wallet consistency
    # Check withdrawal balance validity
    # Alert admin if mismatches found
```

---

## ✅ **Sign-Off Checklist:**

Before marking "Data Migration Complete":
- [ ] Run validation script - all users pass
- [ ] Check admin income pages - show correct counts
- [ ] Check admin withdrawal pages - show correct balances
- [ ] Test user withdrawal flow - balances accurate
- [ ] Verify scheduler jobs - no duplicate income
- [ ] Document any exceptions or known issues
