# STF PROTOCOL SUMMARY
## Selenium Testing Frontend Protocol

---

## What is STF Protocol?

**STF (Selenium Testing Frontend) Protocol** is the mandatory testing standard for all frontend features in the MNR Reference Program. It ensures that features are tested through actual user workflows using browser automation, not just API endpoint testing.

---

## Core Principle

**API 200 OK ≠ Working Feature**

A feature is only "complete" when:
1. ✅ Selenium test passes with real browser automation
2. ✅ All user roles tested (VGK, Admin, Super Admin, Finance)
3. ✅ Screenshots captured at critical steps
4. ✅ Database state verified after operations
5. ✅ Test data completely cleaned up
6. ✅ Architect review completed

---

## 5-Step STF Protocol

### Step 1: Functional Testing ✅
- Create test data with unique timestamps
- Test complete user journey through UI
- Verify database state after each step
- Complete cleanup verification

### Step 2: Code Consolidation ✅
- Identify duplicate endpoints/functions
- Consolidate to single source of truth (DC Protocol)
- Delete redundant code
- Update all references

### Step 3: Frontend/Backend Contract Validation ✅
- Verify parameter names match
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
- Run cleanup scripts

---

## Test Credentials

All passwords: `TestPass123!`

| Role | User ID | Access |
|------|---------|--------|
| RVZ Admin | MNR182364369 | Full system control |
| Super Admin | MNR182371007 | Supreme approvals |
| Finance Admin | MNR182371010 | Payment processing |
| Regular Admin | MNR182322707 | Standard admin ops |
| Test Parent | MNR1900000 | Test user creation |

---

## Quick Commands

```bash
# Setup test environment
./scripts/testing/selenium_test_setup.sh

# Run Selenium tests
python selenium_frontend_test.py

# Cleanup test data
./scripts/testing/selenium_test_cleanup.sh
```

---

## Test User Management

- **Test Parent**: `MNR1900000`
- **Test Users**: `MNR19XXXXX` (auto-generated)
- **Password**: `TestPass123!` (all accounts)

```bash
# Create test users
python scripts/testing/test_user_manager.py create 10

# List test users
python scripts/testing/test_user_manager.py list

# Cleanup test users
python scripts/testing/test_user_manager.py cleanup
```

---

## Success Criteria

A feature passes STF Protocol when:

✅ Feature works end-to-end in browser  
✅ Single implementation (no duplicates)  
✅ DC Protocol compliant  
✅ All roles tested  
✅ Zero test artifacts remaining  
✅ Architect approved  

---

## Integration with Other Protocols

- **DC Protocol**: Single source of truth
- **R Logs Protocol**: Real-time log verification
- **WVV Protocol**: Withdrawal validation
- **MFR Protocol**: Mandatory fix resolution
- **Architect Review Mandate**: Code review required

---

## File Locations

- **Full Protocol**: `tests/STF_PROTOCOL.md`
- **Quick Reference**: `scripts/testing/QUICK_REFERENCE.md`
- **Test User Manager**: `scripts/testing/test_user_manager.py`
- **Setup Script**: `scripts/testing/selenium_test_setup.sh`
- **Cleanup Script**: `scripts/testing/selenium_test_cleanup.sh`

---

## Example Selenium Test Structure

```python
def test_feature():
    # 1. Login as appropriate role
    driver.get(f"{BASE_URL}/login")
    login(driver, TEST_CREDENTIALS)
    
    # 2. Navigate to feature page
    driver.get(f"{BASE_URL}/feature-page")
    
    # 3. Take screenshot before action
    driver.save_screenshot("before_action.png")
    
    # 4. Perform user action
    element.click()
    
    # 5. Take screenshot after action
    driver.save_screenshot("after_action.png")
    
    # 6. Verify database state
    verify_database_state()
    
    # 7. Cleanup test data
    cleanup_test_data()
```

---

**Protocol**: STF (Selenium Testing Frontend)  
**Version**: 2.1  
**Status**: ✅ Active  
**Last Updated**: November 16, 2025
