# WVV PROTOCOL - WITHDRAWAL & VED STRUCTURE EXPLAINED

**Date**: November 2, 2025  
**Document Type**: Business Rules & System Architecture

---

## PART 1: WITHDRAWAL VALIDATION PROTOCOL (WVV)

### ❌ CURRENT ISSUE: Auto-Approval Setting "Accounts Paid"

**Problem**: Income calculation is using `auto_approve_and_credit_wallet()` which:
- Sets `verification_status = 'Accounts Paid'`
- Credits wallets IMMEDIATELY
- Bypasses manual admin approval workflow

**User Requirement**: All incomes should stay as **'Pending'** and go through manual admin approval workflow.

### ✅ CORRECT WVV WORKFLOW:

```
Step 1: Income Calculation (Daily Scheduler)
   ↓
   - Create pending_income records
   - Status: 'Pending'
   - Wallets: NOT credited yet
   
Step 2: Admin Dashboard Review
   ↓
   - Admin verifies income details
   - Admin approves/rejects
   
Step 3: Manual Approval
   ↓
   - Admin clicks "Approve"
   - Status: 'Pending' → 'Admin Verified'
   
Step 4: Super Admin Approval
   ↓
   - Super Admin final approval
   - Status: 'Admin Verified' → 'Super Admin Verified'
   
Step 5: Accounts Payment
   ↓
   - Finance team marks as paid
   - Status: 'Super Admin Verified' → 'Accounts Paid'
   - Wallets: NOW credited
   
Step 6: User Sees Income
   ↓
   - Earnings page shows record
   - User can withdraw (if in withdrawable_wallet)
```

### 🔧 REQUIRED FIX:

**File**: `backend/app/core/scheduler.py`

**Change**:
```python
# ❌ WRONG: Auto-approve and credit immediately
auto_approve_and_credit_wallet(db, pending_income)

# ✅ CORRECT: Keep as Pending
pending_income.verification_status = 'Pending'
# Do NOT credit wallets
# Do NOT create transaction records
# Admin will approve manually
```

---

## PART 2: VED TEAM STRUCTURE

### 📚 Ved Program Roles

#### 1. VED OWNER (Earns Ved Income)
**Criteria**: Must have **3+ direct referrals** (activated with package)

**Example**: 
- BEV182311701 has 8 direct referrals
- ✅ BEV182311701 IS a Ved Owner

**Income**: Earns Ved Income when Ved Team members activate

---

#### 2. VED HEAD (3rd Direct Referral)
**Criteria**: The **3rd person** referred directly by Ved Owner

**How it works**:
```
Ved Owner: BEV182311701 (has 8 direct referrals)
   ↓
Referral 1: BEV001 (NOT Ved Head)
Referral 2: BEV002 (NOT Ved Head)
Referral 3: BEV003 ← VED HEAD (3rd referral)
Referral 4: BEV004 (NOT Ved Head)
...
```

**Important**: ONLY the 3rd referral becomes Ved Head, not all referrals!

---

#### 3. VED TEAM MEMBER (Generates Ved Income)
**Criteria**: Must be in **PLACEMENT TREE** (binary tree) under Ved Head

**CRITICAL RULE**: 
- ❌ NOT referral tree
- ✅ PLACEMENT TREE (binary tree for matching income)

**Example**:
```
Ved Owner: BEV182311701
Ved Head: BEV003 (3rd referral)

PLACEMENT TREE under BEV003:
       BEV003 (Ved Head)
       /           \
   BEV050        BEV051  ← Ved Team Members
   /    \        /    \
BEV100 BEV101  BEV102 BEV103  ← Ved Team Members
```

**Ved Income Trigger**: When anyone in the placement tree under BEV003 activates:
- BEV182311701 earns Ved Income (Ved Owner)
- Income = Based on activated member's package

---

### 🔍 WHY IS BEV182389662 NOT A VED MEMBER?

**User Details**:
```
ID: BEV182389662
Referrer: BEV182311701 (Ved Owner with 8 referrals)
Package: 1.0 points (Platinum)
Activated: November 1, 2025
Ved Team Status: ❌ NOT a Ved Team Member
```

**Analysis**:
1. ✅ Referrer BEV182311701 IS a Ved Owner (8 direct referrals)
2. ✅ BEV182311701 has a Ved Head (3rd referral)
3. ❌ BEV182389662 is NOT in the placement tree under the Ved Head

**Reason**: BEV182389662 must be:
- **PLACED** (in binary tree) under BEV182311701's 3rd referral (Ved Head)
- NOT just **REFERRED** by BEV182311701

**Example**:
```
Scenario A (Ved Member):
  Ved Owner: BEV182311701
  Ved Head: BEV003 (3rd referral)
  BEV182389662 PLACED under BEV003
     → ✅ Ved Team Member
     → Ved Income for BEV182311701

Scenario B (NOT Ved Member):
  Ved Owner: BEV182311701
  Ved Head: BEV003 (3rd referral)
  BEV182389662 PLACED under someone else
     → ❌ NOT Ved Team Member
     → NO Ved Income for BEV182311701
```

**Current Status**: BEV182389662 is likely in Scenario B - placed somewhere else in the binary tree, not under the Ved Head.

---

### 📊 Ved Team Member Table

The `ved_team_member` table explicitly tracks Ved Team membership:

```sql
SELECT * FROM ved_team_member WHERE member_id = 'BEV182389662';
-- Result: ❌ No records found

-- This confirms: BEV182389662 is NOT in any Ved Team
```

**What this means**:
- BEV182389662's activation does NOT generate Ved Income
- They are a regular direct referral (generates Direct Referral bonus)
- To become Ved member: Must be placed under a Ved Head in binary tree

---

### 🎯 SUMMARY

#### Withdrawal Validation (WVV):
- ❌ Auto-approval currently sets "Accounts Paid" and credits wallets
- ✅ Should create "Pending" records for manual admin approval
- ✅ Keep records in pending_income table (DC Protocol)
- ✅ Admin approves → Super Admin approves → Accounts pays → Wallet credited

#### Ved Team Structure:
- **Ved Owner**: 3+ direct referrals (earns Ved Income)
- **Ved Head**: 3rd direct referral of Ved Owner
- **Ved Team**: Placement tree under Ved Head (NOT referral tree)
- **BEV182389662**: Direct referral of Ved Owner, but NOT in Ved Team placement tree
- **Result**: No Ved Income generated (only Direct Referral bonus)

---

## NEXT STEPS

1. **Fix Auto-Approval**: Remove auto-approval, keep incomes as 'Pending'
2. **Verify Ved Team**: Check who is BEV182311701's 3rd referral (Ved Head)
3. **Check Placement**: Verify where BEV182389662 is placed in binary tree
4. **Test Workflow**: Ensure admin can manually approve pending incomes

---

**Document Version**: 1.0  
**Last Updated**: November 2, 2025
