# Comprehensive Workflow Test Plan
**Based on Bonanza Delete Workflow Learnings (Nov 4, 2025)**

## Testing Philosophy Applied
✅ **API endpoint testing ≠ Workflow testing** - Test actual user journeys  
✅ **Always use test data with cleanup** - Leave zero artifacts  
✅ **Role-based smoke tests** - Test VGK/Admin/User perspectives  
✅ **Frontend/backend contract validation** - Verify JSON payloads match  
✅ **Database state verification** - Check DB after each step  

## Test Credentials
- **RVZ ID**: BEV182364369 (actual VGK)
- **Regular User**: BEV1800143  
- **Password**: VGK_TEST_PASSWORD secret (common for all admins)

---

## Priority 1: RVZ Supreme Operations (High Impact)

### 1. ✅ Bonanza Delete Workflow - **COMPLETED**
**Status**: 100% Passing (5/5 steps)
- [x] Create bonanza
- [x] Approve bonanza  
- [x] User sees approved bonanza
- [x] VGK deletes bonanza
- [x] Verify cleanup

**Learnings Applied**:
- Fixed FK constraint (bonanza_progress → bonanza.id)
- Fixed audit log severity values
- Removed secondary password requirement

---

### 2. ⏭️ Bonanza Complete Lifecycle (Next Priority)
**Test**: Create → Approve → User Claims → Process → Delete
**Files**: `tests/bonanza_claim_workflow_test.py`

**Steps**:
1. VGK creates test bonanza (timestamp-based name)
2. VGK approves bonanza
3. Regular user views and claims bonanza
4. Verify claim recorded in bonanza_progress
5. VGK processes claim (if applicable)
6. VGK deletes bonanza
7. Cleanup verification

**Expected Issues to Catch**:
- Claim button not appearing for eligible users
- bonanza_progress FK issues (already fixed!)
- Processing workflow broken
- Delete fails when claims exist

---

### 3. ⏭️ Member Search Multi-Role Access
**Test**: Search across Admin/Super Admin/Finance/VGK roles
**Files**: `tests/member_search_workflow_test.py`

**Steps**:
1. Login as each admin role
2. Test autocomplete (user_id, name, sponsor_id, ved_owner_id)
3. Test advanced filters (dates, package, status)
4. Test pagination (50 per page)
5. Test CSV export (VGK only)
6. Verify role-based theming
7. No test data needed (uses existing users)

**Expected Issues to Catch**:
- Role permissions not enforced
- Autocomplete returning wrong suggestions
- CSV export accessible to non-VGK roles
- Theming not applied correctly

---

### 4. ⏭️ Awards Procurement Workflow
**Test**: Create → Approve → Finance Process → User Wallet
**Files**: `tests/awards_procurement_workflow_test.py`

**Steps**:
1. VGK creates test award for specific user
2. Admin approves award
3. Super Admin approves award
4. Finance processes payment
5. Verify pending_income record created
6. Verify withdrawable wallet updated
7. Delete test award
8. Cleanup verification

**Expected Issues to Catch**:
- Multi-role approval chain broken
- pending_income not created
- Wallet not updated (materialized view issue?)
- Physical vs cash award processing logic

---

### 5. ⏭️ Withdrawal Request Workflow (Option 1)
**Test**: Request → Admin Approve → Bank Sent → Wallet Deduction
**Files**: `tests/withdrawal_workflow_test.py`

**Steps**:
1. Create test user with ₹5,000 withdrawable wallet
2. User requests withdrawal ₹2,000
3. Verify NO wallet deduction at request
4. Admin approves withdrawal
5. Admin marks as "Bank Sent"
6. Verify wallet deduction occurs NOW
7. Test rejection (should fail after bank sent)
8. Cleanup test user data

**Expected Issues to Catch**:
- Wallet deducted at wrong step
- Rejection allowed after bank transfer
- WV Protocol violations (extra deductions)
- Materialized view not refreshing

---

### 6. ⏭️ KYC/Bank Approval Real-Time Sync
**Test**: Approve KYC → Immediate Wallet Transfer
**Files**: `tests/kyc_bank_approval_workflow_test.py`

**Steps**:
1. Create test user with ₹1,500 earning wallet
2. User uploads KYC docs (mock)
3. Finance approves KYC
4. Verify NO transfer yet (bank pending)
5. User uploads bank details
6. Finance approves bank
7. Verify IMMEDIATE transfer to withdrawable
8. Cleanup test user

**Expected Issues to Catch**:
- Real-time sync not triggering
- Transfer waiting for nightly job
- Balance threshold (₹1,000) not enforced
- Both approvals not required

---

## Priority 2: Admin Operations (Medium Impact)

### 7. ⏭️ User Activation Workflow
**Test**: Create → Place in Tree → Activate → Income Calculation
**Files**: `tests/user_activation_workflow_test.py`

**Steps**:
1. Create test user (inactive)
2. Verify binary tree placement (DFS algorithm)
3. Admin activates user
4. Verify sponsor gets direct referral income
5. Verify matching referral calculation
6. Delete test user
7. Cleanup pending_income records

---

### 8. ⏭️ Package Upgrade Workflow
**Test**: Upgrade Package → Wallet Deduction → Income Recalculation
**Files**: `tests/package_upgrade_workflow_test.py`

**Steps**:
1. Create test user with Package 1 (₹30,000)
2. User requests upgrade to Package 2 (₹60,000)
3. Verify ₹30,000 deducted from upgrade wallet
4. Verify package updated
5. Verify income recalculation triggered
6. Cleanup test user

---

## Priority 3: Financial Operations (Critical Data)

### 9. ⏭️ Income Calculation Job
**Test**: Nightly Job → Income Records → Deductions → Wallet Split
**Files**: `tests/income_calculation_job_test.py`

**Steps**:
1. Create test users with referrals
2. Trigger income calculation manually
3. Verify pending_income records created
4. Verify 12% deduction applied
5. Verify wallet split (earning/withdrawable/upgrade)
6. Verify materialized views refreshed
7. Check for duplicate income (DC Protocol)
8. Cleanup test data

---

### 10. ⏭️ Duplicate Prevention System
**Test**: Run Job Multiple Times → No Duplicate Income
**Files**: `tests/duplicate_prevention_test.py`

**Steps**:
1. Create test scenario (direct referral)
2. Run income calculation job
3. Verify 1 income record created
4. Run job again (simulate re-run)
5. Verify STILL only 1 record
6. Check unique indexes preventing duplicates
7. Test all 4 income types
8. Cleanup

---

## Testing Standards (Applied to All Tests)

### ✅ Structure
```python
# 1. Setup test data
# 2. Execute workflow steps
# 3. Verify database state after each step
# 4. Cleanup all test data
# 5. Final verification (zero artifacts)
```

### ✅ Naming Convention
- Test files: `{feature}_workflow_test.py`
- Test data: `TEST_{ENTITY}_{timestamp}`
- Always include cleanup verification

### ✅ Error Handling
- Log detailed errors with step context
- Include API response in failure messages
- Check backend logs for IntegrityErrors
- Verify FK constraints not violated

### ✅ Success Criteria
- All steps pass (no exceptions)
- Database state matches expectations
- Zero test artifacts remaining
- Workflows restart without errors

---

## Next Actions

1. **Immediate**: Test bonanza claim workflow (Priority 1.2)
2. **Short-term**: Test member search multi-role (Priority 1.3)
3. **Medium-term**: Test awards procurement (Priority 1.4)
4. **Long-term**: Complete all Priority 1 & 2 tests

## Documentation
Each test will generate:
- Test script: `tests/{feature}_workflow_test.py`
- Results doc: `{FEATURE}_WORKFLOW_TEST_RESULTS.md`
- Update `replit.md` with findings

---

**Test Execution Command**:
```bash
python3 tests/{feature}_workflow_test.py
```

**Success Output**:
```
🎉 ALL TESTS PASSED - WORKFLOW 100% FUNCTIONAL
```
