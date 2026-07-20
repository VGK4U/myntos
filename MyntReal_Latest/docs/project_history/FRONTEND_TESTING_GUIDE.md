# 🧪 RVZ Supreme Workflow - Frontend Testing Guide

## ✅ SYSTEM STATUS
- **Backend**: Running ✅ (FastAPI on port 8000)
- **Frontend**: Running ✅ (Node.js on port 5000)
- **Login Page**: Accessible ✅
- **VGK Pages**: Authentication-Protected ✅ (Correct security behavior)

---

## 📋 MANUAL TESTING CHECKLIST

### **Test 1: Login Flow**
1. **Navigate to**: https://bev-ev-reference-program.replit.app/login
2. **Enter credentials**:
   - BEV ID: `BEV182364369` (or your RVZ ID)
   - Password: Your VGK password
3. **Expected Result**: Redirect to dashboard
4. **✅ Status**: Login page loads correctly

---

### **Test 2: RVZ Supreme Income Approval**
**URL**: `/rvz/income-supreme`

#### **Workflow**: Income → Wallet → Withdrawal (AUTO)

1. **Navigate to RVZ Supreme Income page**
2. **View pending incomes** (should load from API)
3. **Select income records** to approve
4. **Click "SUPREME APPROVE"** button
5. **Expected Results**:
   ```
   ✅ Income marked as 'Accounts Paid'
   ✅ Wallet synced (withdrawable_wallet credited)
   ✅ Auto-withdrawal created:
      - If ≥ ₹1,000 → Status: "Pending" (ready for payment)
      - If < ₹1,000 → Status: "On Hold" (waiting for more income)
   ✅ Success message shows:
      - Approved count
      - Wallet sync amount
      - Withdrawal ID
   ```

#### **Package Split Verification**:
| Package | Withdrawable Wallet | Upgrade Wallet |
|---------|-------------------|----------------|
| Diamond | 50% | 50% |
| Star    | 50% | 50% |
| Loyal   | 50% | 50% |
| Platinum| 100% | 0% |

---

### **Test 3: VGK ONE-CLICK Payment**
**URL**: `/rvz/withdrawal-supreme`

#### **Workflow**: Pending → Bank Sent (INSTANT)

1. **Navigate to RVZ Supreme Withdrawal page**
2. **View pending withdrawals** (status = "Pending", amount ≥ ₹1,000)
3. **Select withdrawal records** to pay
4. **Click "SUPREME PAY NOW"** button (ONE-CLICK)
5. **Expected Results**:
   ```
   ✅ Status changed: "Pending" → "Bank Sent"
   ✅ Wallet deducted INSTANTLY (atomic operation)
   ✅ Payment timestamp recorded
   ✅ Success message shows:
      - Paid count
      - Total amount sent to bank
   ```

---

### **Test 4: Dashboard Sync**
**URL**: `/dashboard` (or user-specific dashboard)

1. **Navigate to dashboard after workflow completion**
2. **Verify wallet balances updated**:
   - Earning wallet (should decrease after sync)
   - Withdrawable wallet (should increase after approval)
   - Withdrawable wallet (should decrease after payment)
3. **Check income history**:
   - Status shows "Accounts Paid"
4. **Check withdrawal history**:
   - New auto-withdrawal visible
   - Status shows "Pending" or "On Hold"

---

## 🔍 VERIFICATION POINTS

### **Income Approval**
- [ ] Income status changes to "Accounts Paid"
- [ ] Withdrawable wallet increases by correct amount
- [ ] Package split respected (50/50 or 100/0)
- [ ] Auto-withdrawal created
- [ ] Withdrawal has correct status (Pending/On Hold)

### **₹1,000 Minimum Rule**
- [ ] Withdrawals ≥ ₹1,000 → Status: "Pending"
- [ ] Withdrawals < ₹1,000 → Status: "On Hold"
- [ ] "On Hold" withdrawals NOT shown in payment queue

### **ONE-CLICK Payment**
- [ ] Only "Pending" withdrawals can be paid
- [ ] Wallet deducted ONLY when payment sent
- [ ] Status changes to "Bank Sent"
- [ ] Amount matches wallet deduction

---

## 🆚 STANDARD vs VGK SUPREME COMPARISON

| Feature | Standard Flow | RVZ Supreme Flow |
|---------|--------------|------------------|
| **Income Approval** | Admin → Super Admin → Finance | ⚡ ONE-CLICK Supreme Approve |
| **Scope** | Selected incomes only | All pending for user |
| **Wallet Sync** | Manual (Finance only) | 🔄 INSTANT (real-time) |
| **Auto-Withdrawal** | ✅ Yes | ✅ Yes |
| **Payment** | Finance sends to bank | ⚡ ONE-CLICK Supreme Pay |
| **Approval Chain** | 3 levels | Skip-level (VGK power) |

---

## 📊 SAMPLE TEST DATA

### **Test User Profile**
```
User ID: BEV1800001 (example)
Package: Diamond
Pending Income: ₹2,500 (Direct Referral)
```

### **Expected Results**:
```
STEP 1: VGK approves income
├─ Income: ₹2,500 → "Accounts Paid"
├─ Deductions (12% total):
│  ├─ Guru Dakshina: ₹50 (2%)
│  ├─ Admin: ₹200 (8%)
│  └─ TDS: ₹50 (2%)
├─ Net: ₹2,200
└─ Package Split (Diamond 50/50):
   ├─ Withdrawable: ₹1,100
   └─ Upgrade: ₹1,100

STEP 2: Auto-withdrawal created
├─ Withdrawal Amount: ₹1,100
└─ Status: "Pending" (≥ ₹1,000)

STEP 3: VGK ONE-CLICK payment
├─ Wallet Deduction: ₹1,100
└─ Status: "Pending" → "Bank Sent"
```

---

## 🚨 TROUBLESHOOTING

### **Issue**: Pages redirect to login
**Solution**: This is CORRECT behavior - pages are authentication-protected

### **Issue**: No pending incomes shown
**Solution**: 
1. Check if incomes exist with status = "Pending"
2. Run income calculation job if needed
3. Check API logs for errors

### **Issue**: Wallet not updating
**Solution**:
1. Verify materialized views exist (`user_withdrawable_wallet_balance`)
2. Check backend logs for wallet sync errors
3. Refresh materialized views if needed

### **Issue**: Auto-withdrawal not created
**Solution**:
1. Check if wallet sync succeeded
2. Verify KYC/Bank approval status (if global skip is disabled)
3. Check minimum balance (₹1,000 rule)

---

## 🔐 AUTHENTICATION NOTES

- VGK pages use **hybrid authentication** (session cookies + JWT)
- Login endpoint: `POST /api/v1/auth/login`
- Session stored in cookies (httpOnly, secure)
- Pages automatically redirect if not authenticated

---

## ✅ EXPECTED API ENDPOINTS

### **Income Approval**
```
POST /api/v1/rvz-supreme/income/supreme-approve
Body: { "pending_income_ids": [123, 456, 789] }
Response: {
  "approved_count": 3,
  "workflow_results": [
    {
      "user_id": "BEV1800001",
      "status": "complete_workflow",
      "income_approved": 2500.00,
      "wallet_synced": 1100.00,
      "withdrawal_created": 789,
      "withdrawal_status": "Pending"
    }
  ]
}
```

### **ONE-CLICK Payment**
```
POST /api/v1/rvz-supreme/withdrawal/supreme-approve-and-pay
Body: { "withdrawal_ids": [789] }
Response: {
  "paid_count": 1,
  "total_paid": 1100.00
}
```

---

## 📝 TEST COMPLETION CHECKLIST

After completing all tests, verify:

- [ ] ✅ Login page loads and accepts credentials
- [ ] ✅ RVZ Supreme Income page loads (after login)
- [ ] ✅ Income approval triggers wallet sync
- [ ] ✅ Auto-withdrawal created with correct status
- [ ] ✅ Package wallet splits respected
- [ ] ✅ ₹1,000 minimum rule enforced
- [ ] ✅ VGK ONE-CLICK payment works
- [ ] ✅ Wallet deducted only when payment sent
- [ ] ✅ Dashboard shows updated balances
- [ ] ✅ No errors in browser console

---

## 🎯 READY FOR TESTING!

**Your workflows are LIVE and ready for real-world testing!**

Navigate to: https://bev-ev-reference-program.replit.app/login

Start with Test 1 (Login Flow) and proceed through the checklist.

All backend endpoints are running and tested. The only step left is manual UI verification with real credentials! 🚀
