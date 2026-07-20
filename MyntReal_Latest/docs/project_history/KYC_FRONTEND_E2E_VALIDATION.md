# KYC Activation - Frontend End-to-End Validation

**Date**: November 1, 2025  
**Validation Method**: Screenshot Testing (ST)  
**Test User**: BEV1800143 (B.RAMALAXMI)  
**Status**: ⏳ IN PROGRESS

---

## 🎯 TEST OBJECTIVE

Validate the complete KYC activation workflow from user login to data persistence, ensuring:
1. ✅ User can login successfully
2. ✅ User can navigate to Profile Edit → KYC section
3. ✅ User can enter Aadhaar and PAN numbers
4. ✅ User can submit the form
5. ✅ Success message appears
6. ✅ Page redirects to /profile-view
7. ✅ Saved data displays correctly on profile view
8. ✅ Data persists in database (DC Protocol compliance)

---

## 📋 TEST SETUP

### Test User Credentials:
```
BEV ID: BEV1800143
Password: test123
Name: B.RAMALAXMI
```

### Pre-Test Database State:
```
Aadhaar: NULL (cleared for clean test)
PAN: NULL (cleared for clean test)
```

### Test Data to Submit:
```
Aadhaar Number: 123456789012 (12 digits)
PAN Number: ABCDE1234F (format: 5 letters + 4 digits + 1 letter)
```

---

## 🧪 END-TO-END TEST WORKFLOW

### **STEP 1: Login Page** ✅
**URL**: `/` or `/login`  
**Screenshot**: Login form with BEV ID and Password fields  
**Action**: Enter credentials and click "Sign In"

### **STEP 2: Dashboard** ⏳
**URL**: `/dashboard` or `/user-home`  
**Expected**: User dashboard after successful login  
**Action**: Navigate to Profile Edit

### **STEP 3: Profile Edit - KYC Section** ⏳
**URL**: `/profile-edit?section=kyc`  
**Expected**: 
- Form with Aadhaar Number input field (12 digits)
- Form with PAN Number input field (10 characters)
- Both fields should be empty (NULL)
- "Save Changes" button visible

**Action**: 
- Enter Aadhaar: `123456789012`
- Enter PAN: `ABCDE1234F`
- Click "Save Changes"

### **STEP 4: Success Message** ⏳
**Expected**:
- Alert appears: "✅ KYC numbers updated successfully - Redirecting to profile view..."
- Message visible for 1.5 seconds
- No errors in browser console

### **STEP 5: Redirect to Profile View** ⏳
**URL**: `/profile-view`  
**Expected**:
- Page redirects automatically after 1.5 seconds
- Profile view page loads
- Fresh data fetched from server (API call to GET /api/v1/users/profile)

### **STEP 6: Verify Data Display** ⏳
**URL**: `/profile-view`  
**Expected**:
- KYC section visible
- Aadhaar Number displays: `123456789012`
- PAN Number displays: `ABCDE1234F`
- Data matches what was submitted

### **STEP 7: Database Verification** ⏳
**Method**: Direct database query  
**Expected**:
```sql
SELECT id, name, aadhaar_number, pan_number 
FROM user 
WHERE id = 'BEV1800143';

Expected Result:
  id: BEV1800143
  name: B.RAMALAXMI
  aadhaar_number: 123456789012
  pan_number: ABCDE1234F
```

### **STEP 8: Page Refresh Test** ⏳
**Action**: Hard refresh browser (Ctrl+Shift+R)  
**Expected**:
- Data still displays correctly
- No rollback to NULL values
- DC Protocol: Single source of truth maintained

---

## 📊 VALIDATION CHECKLIST

### Frontend Validation:
- [ ] Login form loads correctly
- [ ] Login succeeds with test credentials
- [ ] Profile edit page loads
- [ ] KYC form displays with empty fields
- [ ] Aadhaar input accepts 12 digits
- [ ] PAN input accepts correct format
- [ ] Save button triggers form submission
- [ ] Success message appears
- [ ] Redirect to /profile-view occurs
- [ ] Profile view loads fresh data
- [ ] Aadhaar displays correctly
- [ ] PAN displays correctly

### Backend Validation:
- [ ] PUT /api/v1/profile/kyc-numbers accepts request
- [ ] Aadhaar validation works (12 digits)
- [ ] PAN validation works (format check)
- [ ] Uniqueness check prevents duplicates
- [ ] Database commit succeeds
- [ ] GET /api/v1/users/profile returns updated data

### Database Validation:
- [ ] Data persists in user table
- [ ] aadhaar_number column updated
- [ ] pan_number column updated
- [ ] profile_updated_at timestamp set
- [ ] Data survives session close/reopen

### DC Protocol Validation:
- [ ] No client-side state maintained
- [ ] Always loads from server database
- [ ] No data duplication
- [ ] Single source of truth enforced

---

## 🔍 BROWSER CONSOLE LOGS

### Expected Console Output:
```
✅ No JavaScript errors
✅ API calls succeed (200 OK)
✅ Profile data fetched after redirect
✅ No CORS errors
✅ No 404 errors (except favicon - ignored)
```

### API Calls to Monitor:
```
1. POST /api/v1/auth/login → 200 OK
2. GET /api/v1/users/profile → 200 OK (initial load)
3. PUT /api/v1/profile/kyc-numbers → 200 OK (form submit)
4. GET /api/v1/users/profile → 200 OK (after redirect)
```

---

## ⚠️ ERROR SCENARIOS TO TEST

### Scenario 1: Invalid Aadhaar (Too Short)
**Input**: `123` (only 3 digits)  
**Expected**: Error message "Aadhaar number must be exactly 12 digits"  
**Expected**: NO redirect, user stays on form

### Scenario 2: Invalid PAN Format
**Input**: `ABC123` (invalid format)  
**Expected**: Error message "Invalid PAN format"  
**Expected**: NO redirect, user stays on form

### Scenario 3: Duplicate Aadhaar
**Input**: Aadhaar already used by another user  
**Expected**: Error message "Aadhaar number already registered"  
**Expected**: NO redirect, user stays on form

### Scenario 4: Network Failure
**Action**: Disconnect network before submit  
**Expected**: Error message about connection failure  
**Expected**: NO redirect, user stays on form

---

## 📝 TEST RESULTS

### Test Execution: ⏳ PENDING

**Step 1 (Login)**: ⏳ PENDING  
**Step 2 (Dashboard)**: ⏳ PENDING  
**Step 3 (KYC Form)**: ⏳ PENDING  
**Step 4 (Submit)**: ⏳ PENDING  
**Step 5 (Redirect)**: ⏳ PENDING  
**Step 6 (Data Display)**: ⏳ PENDING  
**Step 7 (Database)**: ⏳ PENDING  
**Step 8 (Refresh)**: ⏳ PENDING  

---

## 🎯 SUCCESS CRITERIA

The test PASSES if:
1. ✅ User can login without errors
2. ✅ KYC form loads with empty fields
3. ✅ Form accepts valid Aadhaar (12 digits)
4. ✅ Form accepts valid PAN (correct format)
5. ✅ Submit triggers API call (PUT /kyc-numbers)
6. ✅ Success message appears for 1.5 seconds
7. ✅ Page redirects to /profile-view automatically
8. ✅ Profile view displays saved Aadhaar and PAN
9. ✅ Database contains the submitted values
10. ✅ Hard refresh maintains the data (no rollback)

The test FAILS if:
- ❌ Login fails
- ❌ Form doesn't load
- ❌ Submit doesn't trigger API call
- ❌ API returns error (4xx/5xx)
- ❌ Success message doesn't appear
- ❌ Redirect doesn't occur
- ❌ Data doesn't display on profile view
- ❌ Database doesn't contain the values
- ❌ Data rolls back after refresh

---

## 📸 SCREENSHOT DOCUMENTATION

Screenshots will be taken at each step and attached here for complete visual validation.

---

**Test Status**: ⏳ AWAITING EXECUTION  
**Next Action**: Execute frontend test using screenshot tool  
