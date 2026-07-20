# STF PROTOCOL (Selenium Testing Frontend)
## MNR Reference Program - Frontend Testing Protocol
**Version 2.1** | **Last Updated**: November 16, 2025

---

## 🎯 Testing Philosophy
**API endpoint 200 OK ≠ Working feature**  
Must test actual user journeys through UI before claiming "working"

**STF Protocol = Complete Frontend Validation**
- Test with real browser automation (Selenium)
- Verify actual user workflows, not just API endpoints
- Screenshot capture at every critical step
- Database state verification after each operation
- Complete test data cleanup after testing

---

## 🔑 Test Login Credentials

### RVZ Admin (Supreme Admin)
- **User ID**: `MNR182364369`
- **Password**: `TestPass123!`
- **Access Level**: Full system control, RVZ Supreme approvals, system configuration

### Super Admin
- **User ID**: `MNR182371007`
- **Password**: `TestPass123!`
- **Access Level**: Supreme approvals, user management, system oversight

### Finance Admin
- **User ID**: `MNR182371010`
- **Password**: `TestPass123!`
- **Access Level**: Payment processing, award procurement, financial operations

### Regular Admin
- **User ID**: `MNR182322707`
- **Password**: `TestPass123!`
- **Access Level**: Standard admin operations, income verification, KYC approval

### Test Parent User (For Creating Test Users)
- **User ID**: `MNR1900000`
- **Password**: `TestPass123!`
- **Purpose**: Parent account for creating test user hierarchies
- **Note**: All test users created under this account will be auto-cleaned after testing

---

## 5-Step Testing Protocol

### Step 1: Functional Testing ✅
- Create test data with unique timestamps
- Test complete user journey (not just API)
- Verify database state after each step
- Complete cleanup verification

### Step 2: Code Consolidation Analysis 🔍 **NEW**
During each workflow test, identify:

**Duplicate Functionality**
- [ ] Multiple endpoints doing same thing?
- [ ] Redundant business logic scattered across files?
- [ ] Old + new versions of same feature?

**Consolidation Criteria**
1. **Identify most advanced implementation**
   - Better error handling
   - More features
   - Cleaner code structure
   - Better DC Protocol compliance

2. **Merge features from old → new**
   - Extract any unique logic from old version
   - Add missing features to advanced version
   - Preserve all functional requirements

3. **Delete redundant code permanently**
   - Remove old endpoints
   - Delete duplicate functions
   - Clean up unused imports
   - Update route registrations

**Example: Withdrawal System**
- Found: Multiple withdrawal approval flows
- Advanced: Option 1 flow (manual approval, wallet deduction on bank send)
- Action: Consolidate all withdrawal features into Option 1, delete alternatives
- Result: Single source of truth (DC Protocol)

### Step 3: Frontend/Backend Contract Validation ✅
- Verify parameter names match (q/field not term)
- Check response structure matches expectations
- Validate error handling on both sides

### Step 4: Multi-Role Access Testing ✅
- Test with actual credentials for each role
- Verify role-based permissions
- Check theming and feature access

### Step 5: Documentation & Cleanup ✅
- Document bugs found and fixed
- Update replit.md with learnings
- Remove test artifacts from database
- Run cleanup script to delete all test users (MNR19XXXXX range)
- Verify no orphaned records in related tables

## Code Consolidation Workflow

### Discovery Phase
```
1. Search for duplicate endpoints/functions
2. Compare implementations side-by-side
3. Document differences and features
```

### Analysis Phase
```
1. Rate each implementation:
   - Feature completeness
   - Code quality
   - DC Protocol compliance
   - Error handling
   - Performance

2. Choose "winner" (most advanced)
```

### Consolidation Phase
```
1. Extract unique features from deprecated versions
2. Merge into advanced implementation
3. Test merged functionality
4. Delete old code
5. Update all references
6. Restart workflows and verify
```

### Verification Phase
```
1. Run end-to-end test with consolidated code
2. Check no regressions
3. Verify database still consistent
4. Document consolidation in replit.md
```

## Testing Checklist Per Workflow

- [ ] **Functional**: User journey passes end-to-end
- [ ] **Consolidation**: No duplicate code found (or consolidated)
- [ ] **Contract**: Frontend/backend parameters match
- [ ] **Multi-Role**: All roles tested (where applicable)
- [ ] **Cleanup**: Test data removed, docs updated
- [ ] **Architect Review**: Code reviewed before completion

## Common Duplication Patterns to Watch For

1. **Withdrawal Systems**: Multiple approval flows
2. **Income Calculation**: Scattered calculation logic
3. **User Search**: Multiple search endpoints
4. **Awards/Bonanza**: Overlapping procurement systems
5. **KYC/Bank Approval**: Duplicate validation logic
6. **Admin Dashboards**: Redundant statistics endpoints

## Success Criteria

✅ Feature works end-to-end  
✅ Single implementation (no duplicates)  
✅ DC Protocol compliant (single source of truth)  
✅ All roles tested  
✅ Zero test artifacts  
✅ Architect approved  

---

## 🧪 Test User Management

### Setup Test Environment
```bash
# Run setup script to prepare testing environment
./scripts/testing/selenium_test_setup.sh

# This will:
# - Verify backend/frontend are running
# - Create test parent user (MNR1900000)
# - Create 5 test users for testing
# - Set environment variables
```

### Create Test Users Manually
```bash
# Create 10 test users
python scripts/testing/test_user_manager.py create 10

# List all test users
python scripts/testing/test_user_manager.py list

# Ensure parent user exists
python scripts/testing/test_user_manager.py ensure-parent
```

### Cleanup After Testing
```bash
# Run cleanup script (removes all test data)
./scripts/testing/selenium_test_cleanup.sh

# Or cleanup manually
python scripts/testing/test_user_manager.py cleanup
```

### Test User Naming Convention
- **Test Parent**: `MNR1900000` (parent for all test users)
- **Test Users**: `MNR19XXXXXX` (all start with MNR19)
- **Password**: `TestPass123!` (same for all test accounts)

### Important Notes
- ⚠️ All test users are created under parent `MNR1900000`
- ⚠️ Test users are in the `MNR19XXXXX` range for easy identification
- ⚠️ Cleanup script will delete ALL users starting with `MNR19`
- ⚠️ Always run cleanup after testing to maintain database hygiene
- ⚠️ Test users inherit binary tree placement from parent

---

## Integration with Existing Protocols

- **DC Protocol**: Consolidation ensures single source of truth
- **R Logs Protocol**: Check logs after consolidation
- **FT Protocol**: Test frontend with consolidated backend
- **WV Protocol**: Ensure withdrawal validation still works

---

## 🚀 Quick Testing Workflow

```bash
# 1. Setup test environment
./scripts/testing/selenium_test_setup.sh

# 2. Run Selenium tests
python selenium_frontend_test.py
python scripts/testing/selenium_complete_e2e.py
python scripts/testing/selenium_announcements_rating_test.py

# 3. Review results
ls -lh test_screenshots/

# 4. Cleanup test data
./scripts/testing/selenium_test_cleanup.sh
```

---

## 🏆 STF Protocol Compliance Checklist

Before marking any feature as "complete", ensure:

- [ ] ✅ **Selenium Test Created**: Automated browser test exists
- [ ] ✅ **All Roles Tested**: VGK, Admin, Super Admin, Finance tested
- [ ] ✅ **Screenshots Captured**: Visual proof of functionality
- [ ] ✅ **Database Verified**: Data consistency confirmed
- [ ] ✅ **Test Data Cleaned**: All test users/data removed
- [ ] ✅ **No JavaScript Errors**: Console logs are clean
- [ ] ✅ **Architect Reviewed**: Code review completed

---

**Protocol**: STF (Selenium Testing Frontend)  
**Version**: 2.1  
**Last Updated**: November 16, 2025  
**Test User Manager**: Active  
**Status**: ✅ Active
