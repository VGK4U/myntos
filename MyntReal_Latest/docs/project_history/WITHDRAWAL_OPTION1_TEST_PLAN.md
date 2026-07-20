# Withdrawal Option 1 Flow - Testing Plan

## Test Environment Note
**DC Protocol Protection:** Direct SQL wallet updates are blocked by design. Testing requires either:
1. Using the admin UI with real user data
2. Creating pending_income records that flow through the system naturally
3. Temporarily bypassing the trigger (not recommended)

## Test Scenarios

### **Test 1: Auto-Withdrawal Creation (No Wallet Deduction)**
**Setup:**
- User with ₹10,000+ withdrawable wallet balance
- KYC approved, bank details verified

**Steps:**
1. Wait for auto-withdrawal scheduler (Mon-Sat 7 AM IST) OR trigger manually
2. Check withdrawal_request table for new record with status='Pending'
3. Verify user's withdrawable_wallet is UNCHANGED (₹10,000 still there)

**Expected Result:**
✅ Withdrawal request created with status='Pending'
✅ Withdrawable wallet NOT deducted
✅ Request shows in admin panel as "Pending"

---

### **Test 2: Admin Approval (No Wallet Deduction)**
**Setup:**
- Existing withdrawal with status='Pending' from Test 1

**Steps:**
1. Admin logs in and navigates to Withdrawals
2. Clicks "Approve" button on pending withdrawal
3. Check withdrawal status changes to 'Admin Verified'
4. Verify user's withdrawable_wallet is STILL UNCHANGED

**Expected Result:**
✅ Status changes: Pending → Admin Verified
✅ Withdrawable wallet STILL NOT deducted
✅ "Send to Bank" button now available

---

### **Test 3: Send to Bank (Wallet Deducted)**
**Setup:**
- Withdrawal with status='Admin Verified' from Test 2
- User has ₹10,000 withdrawable wallet

**Steps:**
1. Finance Admin/Super Admin clicks "Send to Bank"
2. Check withdrawal status changes to 'Bank Sent'
3. **VERIFY: User's withdrawable_wallet is NOW DEDUCTED (₹10,000 → ₹7,000 if ₹3,000 withdrawal)**
4. Check processed_at timestamp is set

**Expected Result:**
✅ Status changes: Admin Verified → Bank Sent
✅ Withdrawable wallet DEDUCTED at this point
✅ Processed timestamp recorded
✅ Success message: "₹X,XXX deducted from wallet"

---

### **Test 4: Rejection from Pending (No Wallet Changes)**
**Setup:**
- Create new pending withdrawal

**Steps:**
1. Admin clicks "Reject" on Pending withdrawal
2. Check status changes to 'Rejected'
3. Verify withdrawable wallet is UNCHANGED (no re-credit needed)

**Expected Result:**
✅ Status: Pending → Rejected
✅ No wallet changes (funds were never deducted)
✅ Message: "no wallet changes - funds never deducted"

---

### **Test 5: Rejection from Admin Verified (No Wallet Changes)**
**Setup:**
- Withdrawal with status='Admin Verified'

**Steps:**
1. Admin clicks "Reject"
2. Check status changes to 'Rejected'
3. Verify withdrawable wallet is UNCHANGED

**Expected Result:**
✅ Status: Admin Verified → Rejected
✅ No wallet changes (funds not yet deducted)
✅ Message: "no wallet deduction to reverse"

---

### **Test 6: Rejection from Bank Sent (BLOCKED)**
**Setup:**
- Withdrawal with status='Bank Sent'

**Steps:**
1. Admin tries to click "Reject"
2. System should show error

**Expected Result:**
❌ Rejection BLOCKED
❌ Error message: "Cannot reject withdrawal after bank transfer. Use reversal process instead."
✅ Status remains 'Bank Sent'
✅ Wallet remains deducted

---

### **Test 7: Batch Completion (Deduct All Wallets)**
**Setup:**
- Multiple withdrawals in 'Admin Verified' status
- All users have sufficient withdrawable balance

**Steps:**
1. Create batch from Admin Verified withdrawals
2. Click "Complete Batch"
3. **VERIFY: ALL user wallets are deducted atomically**
4. Check all withdrawal statuses change to 'Bank Sent'

**Expected Result:**
✅ All wallets deducted before status change
✅ All statuses: Admin Verified → Bank Sent
✅ Message shows total amount deducted
✅ If ANY user has insufficient balance, entire batch rolls back

---

### **Test 8: Batch Rejection Before Bank Sent**
**Setup:**
- Batch with withdrawals in 'Pending' or 'Admin Verified'

**Steps:**
1. Click "Reject Batch"
2. Check all requests change to 'Rejected'
3. Verify NO wallet changes

**Expected Result:**
✅ All requests rejected
✅ No wallet re-credits (funds never deducted)
✅ Message: "no wallet changes - funds never deducted"

---

### **Test 9: Batch Rejection After Bank Sent (BLOCKED)**
**Setup:**
- Batch where some requests are already 'Bank Sent'

**Steps:**
1. Try to click "Reject Batch"
2. System should block rejection

**Expected Result:**
❌ Rejection BLOCKED
❌ Error: "Cannot reject batch: X request(s) already sent to bank"
✅ No changes to any requests
✅ Wallets remain as-is

---

### **Test 10: Insufficient Balance (Send to Bank)**
**Setup:**
- Withdrawal for ₹5,000
- User has only ₹3,000 withdrawable balance

**Steps:**
1. Try to "Send to Bank"
2. System should fail with error

**Expected Result:**
❌ Send to Bank FAILS
❌ Error: "Insufficient wallet balance. Required: ₹5,000"
✅ Status reverts to 'Admin Verified'
✅ No wallet deduction
✅ Automatic rollback

---

## Key Validation Points

### ✅ **Wallet Deduction Timing**
- Pending: NO deduction
- Admin Verified: NO deduction
- **Bank Sent: DEDUCTED** ✓
- Completed: Already deducted (from Bank Sent)

### ✅ **Rejection Rules**
- Can reject: Pending, Admin Verified
- **Cannot reject: Bank Sent, Completed**

### ✅ **Wallet Re-Credit Rules**
- **NEW FLOW:** Never re-credit on rejection (funds never deducted until Bank Sent)
- Rejections from Pending/Admin Verified: No wallet changes

### ✅ **Atomic Operations**
- Send to Bank: Wallet deduction is atomic with status change
- Batch Complete: All-or-nothing (if one fails, all rollback)
- Rejection: Safe to reject multiple times (idempotent)

---

## Historical Data Preservation

**CRITICAL:** All existing withdrawal records BEFORE Option 1 implementation are untouched:
- Old completed withdrawals remain as-is
- Historical wallet deductions are preserved
- No retroactive changes to any data

**Only NEW withdrawals created AFTER Option 1 deployment follow the new flow.**

---

## Database Verification Queries

```sql
-- Check withdrawal status distribution
SELECT status, COUNT(*) as count, SUM(withdrawal_amount) as total
FROM withdrawal_request
GROUP BY status
ORDER BY status;

-- Verify no wallet changes for Pending/Admin Verified rejections
SELECT wr.id, wr.user_id, wr.status, u.withdrawable_wallet
FROM withdrawal_request wr
JOIN "user" u ON u.id = wr.user_id
WHERE wr.status = 'Rejected'
AND wr.created_at > '2025-11-03 00:00:00' -- After Option 1 deployment
ORDER BY wr.created_at DESC;

-- Check Bank Sent withdrawals have matching wallet deductions
SELECT wr.user_id, wr.withdrawal_amount, u.withdrawable_wallet, wr.created_at
FROM withdrawal_request wr
JOIN "user" u ON u.id = wr.user_id
WHERE wr.status = 'Bank Sent'
AND wr.created_at > '2025-11-03 00:00:00'
ORDER BY wr.created_at DESC;
```

---

## Production Monitoring

After deployment, monitor:
1. **Backend logs:** Check for wallet deduction errors or rollbacks
2. **Withdrawal success rate:** Ensure no increase in failures
3. **User complaints:** Watch for balance discrepancies
4. **Admin feedback:** Ensure new flow is clear to finance team

---

## Deployment Checklist

- [x] Code changes deployed
- [x] Backend restarted successfully
- [x] DC Protocol wallet trigger active
- [ ] Finance team briefed on new flow
- [ ] Admin UI tested in production
- [ ] First week: Daily reconciliation checks
- [ ] Update admin documentation/runbooks
