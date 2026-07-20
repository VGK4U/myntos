# Complete Data Connection Map
## DC (Data Consistency) Protocol - ALL Admin Roles See SAME Data as Users

**Last Updated:** October 27, 2025  
**Purpose:** Ensure ALL admin dashboards (Admin, Finance Admin, Super Admin, RVZ ID) show IDENTICAL data from the SAME database tables as users

---

## 🎯 **SINGLE SOURCE OF TRUTH:**

| Data Type | Database Table | API Endpoint (Source) | User Pages | Admin Pages (ALL Roles) |
|-----------|----------------|----------------------|------------|-------------------------|
| **Income Records** | `pending_income` | `/api/v1/income-verification/*` | `/user/income/*` | `/admin_income_pending.html`<br>`/admin_income_verified.html` |
| **Wallet Balances** | `user.earning_wallet`<br>`user.withdrawable_wallet` | `/api/v1/withdrawals/withdrawal-summary` | `/user/withdrawals` | `/admin_earnings_withdrawals.html`<br>`/admin/earnings-balance-report` |
| **Withdrawal Requests** | `withdrawal_request` | `/api/v1/withdrawals/admin/withdrawal-report` | `/user/withdrawals` | `/admin/withdrawals/page.tsx`<br>`/admin_earnings_withdrawals.html` |

---

## 📊 **DATA FLOW DIAGRAM:**

```
SCHEDULER (Daily Midnight)
    ↓
pending_income (NEW RECORD)
    verification_status = 'Pending'
    ↓
┌─────────────────────────────────────┐
│  ADMIN VERIFICATION WORKFLOW        │
├─────────────────────────────────────┤
│  1. Admin → 'Admin Verified'        │
│  2. Super Admin → 'Super Admin      │
│     Approved'                       │
│  3. Finance Admin → 'Finance Paid'  │
│                                     │
│  RVZ ID can skip ALL levels         │
└─────────────────────────────────────┘
    ↓
pending_income.verification_status = 'Finance Paid'
WalletService.create_transaction()
    ↓
user.earning_wallet += net_amount
    (Platinum: 100%, Others: 50%)
user.upgrade_wallet_balance += 
    (Platinum: 0%, Others: 50%)
    ↓
DAILY WALLET SYNC (3 AM)
    ↓
user.withdrawable_wallet = earning_wallet
    (if kyc_status = 'Approved')
    ↓
USER WITHDRAWAL REQUEST
    ↓
withdrawal_request (NEW RECORD)
    status = 'Pending'
    withdrawable_wallet -= withdrawal_amount
    ↓
┌─────────────────────────────────────┐
│  WITHDRAWAL APPROVAL WORKFLOW       │
├─────────────────────────────────────┤
│  1. Admin → 'Admin Verified'        │
│  2. Super Admin → 'Super Admin      │
│     Approved'                       │
│  3. Finance Admin → 'Bank Sent'     │
│  4. Bank Transfer → 'Completed'     │
└─────────────────────────────────────┘
    ↓
withdrawal_request.status = 'Completed'
    (withdrawable_wallet already deducted)
```

---

## 🔗 **API ENDPOINT MAPPING:**

### **Income Data (pending_income table)**

| Admin Role | Page | API Endpoint | Status Filter | Data Shown |
|-----------|------|--------------|---------------|------------|
| **Admin** | `admin_income_pending.html` | `GET /api/v1/income-verification/admin/pending-incomes` | `verification_status = 'Pending'` | Records awaiting Admin verification |
| **Super Admin** | `admin_income_verified.html` | `GET /api/v1/super-admin/pending-incomes` | `verification_status = 'Admin Verified'` | Records awaiting Super Admin approval |
| **Finance Admin** | `admin_income_verified.html` | `GET /api/v1/finance-admin/verified-incomes` | `verification_status = 'Super Admin Approved'` | Records awaiting Finance payment |
| **RVZ ID** | `admin_earnings_withdrawals.html` | `GET /api/v1/withdrawals/admin/user-earnings` | All statuses | Can approve from ANY status |
| **User** | `/user/income/` | `GET /api/v1/user/income/*` | `user_id = current_user` | Own income records only |

### **Wallet Data (user table)**

| Admin Role | Page | API Endpoint | Fields Returned | Cache Control |
|-----------|------|--------------|-----------------|---------------|
| **ALL Admins** | `admin_earnings_withdrawals.html` | `GET /api/v1/withdrawals/admin/user-earnings?user_id={id}` | `earning_wallet`, `withdrawable_wallet`, income summary | **NO-CACHE** ✅ |
| **RVZ ID** | `/admin/earnings-balance-report` | `GET /api/v1/rvz/user-wallets` | All user wallets | **NO-CACHE** ✅ |
| **User** | `/user/withdrawals` | `GET /api/v1/withdrawals/withdrawal-summary` | Own wallet only | **NO-CACHE** ✅ |

### **Withdrawal Requests (withdrawal_request table)**

| Admin Role | Page | API Endpoint | Status Filter | Cache Control |
|-----------|------|--------------|---------------|---------------|
| **ALL Admins** | `/admin/withdrawals/page.tsx` | `GET /api/v1/withdrawals/admin/withdrawal-report` | Filterable by status | **NO-CACHE** ✅ |
| **Finance Admin** | `/admin/withdrawal-batches` | `GET /api/v1/withdrawals/admin/batches` | All batches | **NO-CACHE** ✅ |
| **User** | `/user/withdrawals` | `GET /api/v1/withdrawals/withdrawal-requests` | `user_id = current_user` | **NO-CACHE** ✅ |

---

## 🚨 **CACHE BUSTING STRATEGY:**

### **Problem:** Browser caches API responses → Admins see STALE data even after DB updates

### **Solution:** ALL admin and user financial endpoints now include:

```python
def add_no_cache_headers(response: Response):
    """Prevent browser caching of financial data"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
```

### **Applied To:**
✅ `/api/v1/income-verification/admin/pending-incomes`  
✅ `/api/v1/super-admin/pending-incomes`  
✅ `/api/v1/finance-admin/verified-incomes`  
✅ `/api/v1/withdrawals/admin/withdrawal-report`  
✅ `/api/v1/withdrawals/admin/user-earnings`  
✅ `/api/v1/withdrawals/withdrawal-summary`  
✅ `/api/v1/withdrawals/withdrawal-requests`

---

## ✅ **DATA CONSISTENCY VALIDATION:**

### **RULE 1: Income → Wallet Consistency**

```sql
-- ALL users must have: earning_wallet = SUM(Finance Paid income)
SELECT u.id, u.earning_wallet,
    (SELECT SUM(net_amount) FROM pending_income WHERE user_id = u.id AND verification_status = 'Finance Paid') as income_paid
FROM "user" u
WHERE u.package_points = 1.0 -- Platinum users (100% to earning_wallet)
  AND ABS(u.earning_wallet - (SELECT COALESCE(SUM(net_amount), 0) FROM pending_income WHERE user_id = u.id AND verification_status = 'Finance Paid')) > 1;

-- Expected: 0 rows (perfect match)
```

### **RULE 2: Withdrawal → Balance Consistency**

```sql
-- Pending withdrawals CANNOT exceed withdrawable_wallet
SELECT u.id, u.withdrawable_wallet,
    (SELECT SUM(withdrawal_amount) FROM withdrawal_request WHERE user_id = u.id AND status = 'Pending') as pending
FROM "user" u
WHERE (SELECT COALESCE(SUM(withdrawal_amount), 0) FROM withdrawal_request WHERE user_id = u.id AND status = 'Pending') > u.withdrawable_wallet;

-- Expected: 0 rows (sufficient balance)
```

### **RULE 3: Admin View = User View**

```sql
-- What USER sees
SELECT SUM(net_amount) as user_total_paid
FROM pending_income
WHERE user_id = 'MNR1800143' AND verification_status = 'Finance Paid';

-- What ADMIN sees (MUST BE IDENTICAL)
SELECT SUM(net_amount) as admin_total_paid
FROM pending_income
WHERE user_id = 'MNR1800143' AND verification_status = 'Finance Paid';

-- Expected: user_total_paid = admin_total_paid
```

---

## 📋 **ADMIN ROLE PERMISSIONS:**

| Role | Income Verification | Withdrawal Approval | Wallet View | User Management |
|------|-------------------|-------------------|-------------|-----------------|
| **Admin** | Verify (Pending → Admin Verified) | Verify (Pending → Admin Verified) | View specific users | Limited |
| **Super Admin** | Approve (Admin Verified → Super Admin Approved) | Approve (Admin Verified → Super Admin Approved) | View all users | Full |
| **Finance Admin** | Process (Super Admin Approved → Finance Paid) | Process (Super Admin Approved → Bank Sent → Completed) | View all users | Limited |
| **RVZ ID** | **Skip-Level Approve (ANY → Finance Paid)** | Skip-Level Approve | View all users | Full |

**Note:** RVZ ID has HIGHEST privileges - can bypass all approval stages

---

## 🛡️ **DATA INTEGRITY CHECKS:**

### **Daily Automated Checks (Run at 11 PM):**

1. **Income-Wallet Match:** Verify all users' earning_wallet matches Finance Paid totals
2. **Withdrawal-Balance Match:** Ensure no pending withdrawals exceed available balance
3. **Status Distribution:** Alert if ANY income stuck in "Pending" for >7 days
4. **Orphaned Records:** Check for withdrawal_requests without valid user_id

### **Manual Validation (After Major Changes):**

```bash
# Run this script after any wallet migration or batch approval
psql $DATABASE_URL -f backend/scripts/validate_data_consistency.sql
```

---

## 📝 **CHANGE LOG:**

| Date | Change | Impact |
|------|--------|--------|
| Oct 27, 2025 | Added no-cache headers to ALL admin APIs | Prevents stale data in admin dashboards |
| Oct 26, 2025 | Fixed wallet migration for 62 users | All wallets now match Finance Paid income |
| Oct 25, 2025 | Cancelled 4 invalid withdrawals | Re-credited ₹126,700 to user wallets |

---

## 🚀 **TESTING CHECKLIST:**

Before marking any data migration as complete:

- [ ] Run SQL validation: `backend/scripts/validate_data_consistency.sql`
- [ ] Hard refresh ALL admin pages (Ctrl+Shift+R)
- [ ] Verify user dashboard shows ₹0 pending (if all Finance Paid)
- [ ] Check admin income pages show 0 pending records
- [ ] Verify admin withdrawal pages match user wallet balances
- [ ] Cross-check: Pick 3 random users, verify admin view = user view
- [ ] Test RVZ ID skip-level approval workflow
- [ ] Confirm no browser console errors on any admin page

---

## 📞 **SUPPORT:**

If admin pages show different data than user pages:
1. Check browser cache - hard refresh (Ctrl+Shift+R)
2. Verify API responses have `Cache-Control: no-cache` headers
3. Run data validation SQL script
4. Check database status distribution (should all be "Finance Paid" if migration complete)
5. Review audit logs for recent changes
