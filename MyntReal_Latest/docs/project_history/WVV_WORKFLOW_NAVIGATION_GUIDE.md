# 🏦 WVV WORKFLOW - Complete Navigation Guide
## BeV 2.0 Income Verification & Bank Transfer Process

---

## 📋 COMPLETE 8-STEP WVV WORKFLOW

### **Step 1: Income Generation (Automated - Scheduler)**
- **Who**: System (3:00 AM IST daily)
- **What**: Calculates all 4 income types (Direct, Matching, Ved, Guru Dakshina)
- **Result**: Creates records in `pending_income` table with `status='Pending'`
- **Deductions**: 12% total (Guru Dakshina 2%, Admin 8%, TDS 2%) applied here
- **Database**: `pending_income` table

---

### **Step 2: Admin Verification**
- **Who**: Admin
- **Navigation**: 
  ```
  Login as Admin
  → Sidebar → 💰 Withdrawal Management (CLICK to expand)
  → 💰 Income Approval
  ```
- **Action**: Review and verify pending incomes
- **Result**: `status='Admin Verified'` in `pending_income` table
- **Page**: Shows all incomes with `status='Pending'`

---

### **Step 3: Super Admin Verification**
- **Who**: Super Admin or RVZ ID
- **Navigation**: 
  ```
  Login as Super Admin
  → Sidebar → ✅ Withdrawal Approvals (CLICK to expand)
  → 💰 Income Verification
  ```
- **Action**: Review Admin-verified incomes and approve for Finance processing
- **Result**: `status='Super Admin Verified'` in `pending_income` table
- **Page**: Shows all incomes with `status='Admin Verified'`

---

### **Step 4: Finance Admin Payment Processing** ⚠️ **WALLET CREDIT HAPPENS HERE**
- **Who**: Finance Admin or RVZ ID
- **Navigation**: 
  ```
  Login as Finance Admin
  → Sidebar → 🏦 Bank Transfers (CLICK to expand)
  → 💰 Income Payment
  ```
- **Action**: Process Super Admin-verified incomes and credit to user wallets
- **Result**: 
  - Credits NET amount to `users.withdrawable_wallet`
  - `status='Paid'` in `pending_income` table
  - Records stay in `pending_income` permanently (single source of truth)
- **Page**: Shows all incomes with `status='Super Admin Verified'`
- **Important**: NO additional deductions - pays exact NET amount shown

---

### **Step 5: User Withdrawal Request**
- **Who**: User (Members)
- **Navigation**: 
  ```
  Login as User
  → Dashboard → My Earnings
  → Request Withdrawal
  ```
- **Action**: User requests withdrawal from their withdrawable wallet
- **Result**: Creates record in `withdrawal` table with `status='Pending'`
- **Minimum**: ₹1,000 (configurable)

---

### **Step 6: Admin Withdrawal Approval**
- **Who**: Admin
- **Navigation**: 
  ```
  Login as Admin
  → Sidebar → 💰 Withdrawal Management (CLICK to expand)
  → 📝 Pending Withdrawals
  ```
- **Action**: Review and approve user withdrawal requests
- **Result**: `status='Admin Approved'` in `withdrawal` table

---

### **Step 7: Super Admin Withdrawal Approval**
- **Who**: Super Admin
- **Navigation**: 
  ```
  Login as Super Admin
  → Sidebar → ✅ Withdrawal Approvals (CLICK to expand)
  → ✅ Super Admin Approvals
  ```
- **Action**: Final approval before bank transfer
- **Result**: `status='Super Admin Approved'` in `withdrawal` table
- **Ready For**: Bank Transfer Queue

---

### **Step 8: Bank Transfer to User** 🏦 **FINAL STEP**
- **Who**: Finance Admin or RVZ ID
- **Navigation**: 
  ```
  Login as Finance Admin or RVZ ID
  → Sidebar → 🏦 Bank Transfers (CLICK to expand)
  → ⏳ Transfer Queue  ← THIS IS THE BANK TRANSFER PAGE!
  ```
- **Action**: Execute actual bank transfer to user's bank account
- **Shows**: All withdrawals with `status='Super Admin Approved'`
- **Features**:
  - View user bank details
  - Mark as transferred
  - Download transfer report
- **Result**: `status='Paid'` in `withdrawal` table + `users.withdrawable_wallet` reduced

---

## 🎯 QUICK ACCESS GUIDE BY ROLE

### **Admin**
1. **Income Approval**: Withdrawal Management → 💰 Income Approval
2. **Withdrawal Approval**: Withdrawal Management → 📝 Pending Withdrawals

### **Super Admin**
1. **Income Verification**: Withdrawal Approvals → 💰 Income Verification
2. **Withdrawal Approval**: Withdrawal Approvals → ✅ Super Admin Approvals

### **Finance Admin**
1. **Income Payment**: Bank Transfers → 💰 Income Payment
2. **Bank Transfer Queue**: Bank Transfers → ⏳ Transfer Queue ← **BANK TRANSFERS HERE**
3. **Transfer History**: Bank Transfers → 📜 Transfer History

### **RVZ ID (Supreme Admin - Full Access)**
1. **Income Verification**: Bank Transfers → ✅ Income Verification
2. **Income Payment**: Bank Transfers → 💰 Income Payment
3. **Bank Transfer Queue**: Bank Transfers → ⏳ Transfer Queue ← **BANK TRANSFERS HERE**
4. **Transfer History**: Bank Transfers → 📜 Transfer History

---

## ⚠️ CRITICAL WVV PROTOCOL RULES

### **Rule 1: Single Deduction Point**
- ✅ Deductions (12%) applied ONLY at income calculation (Step 1)
- ❌ NO deductions at withdrawal stage
- ✅ Users receive EXACT NET amount shown in Income Payment step

### **Rule 2: Manual Approval Chain**
- ✅ All approvals are MANUAL (no auto-approval)
- ✅ 3-step verification: Admin → Super Admin → Finance
- ❌ Incomes do NOT auto-credit to wallets
- ✅ Only Step 4 (Finance Payment Processing) credits wallets

### **Rule 3: Data Persistence**
- ✅ `pending_income` records NEVER deleted (permanent history)
- ✅ Single source of truth for all earnings
- ✅ Status changes track approval workflow
- ❌ Do NOT calculate totals from transactions - use `pending_income`

### **Rule 4: Wallet Flow**
```
Income Calculation → pending_income (Pending)
     ↓
Admin Verify → pending_income (Admin Verified)
     ↓
Super Admin Verify → pending_income (Super Admin Verified)
     ↓
Finance Payment → withdrawable_wallet CREDITED + pending_income (Paid)
     ↓
User Withdrawal Request → withdrawal (Pending)
     ↓
Admin Approve → withdrawal (Admin Approved)
     ↓
Super Admin Approve → withdrawal (Super Admin Approved)
     ↓
Finance Bank Transfer → withdrawal (Paid) + withdrawable_wallet DEDUCTED
```

---

## 🔍 HOW TO FIND BANK TRANSFER OPTION

### **If you don't see "Transfer Queue":**

1. **Login** as Finance Admin or RVZ ID
2. **Look at left sidebar**
3. **Find** 🏦 Bank Transfers menu header
4. **CLICK** on "Bank Transfers" to expand the menu
5. **You'll see**:
   - ⏳ Transfer Queue ← **THIS IS BANK TRANSFER PAGE**
   - 💰 Income Payment
   - ✅ Income Verification (RVZ ID only)
   - 📜 Transfer History

### **Menu is collapsed by default** - you must click to open it!

---

## 📊 SUMMARY TABLE

| Step | Role | Navigation Path | Database Update | Wallet Impact |
|------|------|----------------|-----------------|---------------|
| 1 | System | Scheduler (3 AM) | `pending_income` status='Pending' | None |
| 2 | Admin | Withdrawal Mgmt → Income Approval | `pending_income` status='Admin Verified' | None |
| 3 | Super Admin | Withdrawal Approvals → Income Verification | `pending_income` status='Super Admin Verified' | None |
| 4 | Finance Admin | Bank Transfers → Income Payment | `pending_income` status='Paid' | ✅ `withdrawable_wallet` INCREASED |
| 5 | User | Dashboard → Request Withdrawal | `withdrawal` status='Pending' | None |
| 6 | Admin | Withdrawal Mgmt → Pending Withdrawals | `withdrawal` status='Admin Approved' | None |
| 7 | Super Admin | Withdrawal Approvals → Super Admin Approvals | `withdrawal` status='Super Admin Approved' | None |
| 8 | Finance Admin | **Bank Transfers → Transfer Queue** | `withdrawal` status='Paid' | ✅ `withdrawable_wallet` DECREASED |

---

## ✅ CHECKLIST FOR BANK TRANSFERS

**Before transferring to bank:**
- [ ] Withdrawal status = 'Super Admin Approved'
- [ ] User has valid bank details (IFSC, Account Number, Name)
- [ ] User KYC status = 'Approved'
- [ ] Amount matches withdrawable wallet balance
- [ ] No pending issues with user account

**After bank transfer:**
- [ ] Mark withdrawal as 'Paid' in Transfer Queue
- [ ] Verify withdrawable_wallet decreased correctly
- [ ] Transaction recorded in Transfer History
- [ ] User receives confirmation

---

**Last Updated**: November 2, 2025
**Frontend Build**: 1762081467113.9814
**Protocol**: WVV (Withdrawal-Validation-Verification) + DC (Data Consistency)
