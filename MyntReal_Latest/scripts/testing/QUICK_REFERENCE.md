# STF PROTOCOL - QUICK REFERENCE
## Selenium Testing Frontend (STF) Protocol

## 🔑 Test Credentials (All use: TestPass123!)

| Role | User ID | Access Level |
|------|---------|--------------|
| **RVZ Admin** | MNR182364369 | Full system control |
| **Super Admin** | MNR182371007 | Supreme approvals |
| **Finance Admin** | MNR182371010 | Payment processing |
| **Regular Admin** | MNR182322707 | Standard admin |
| **Test Parent** | MNR1900000 | Test user creation |

---

## ⚡ Quick Commands

### Setup & Run Tests
```bash
# 1. Setup environment (one time)
./scripts/testing/selenium_test_setup.sh

# 2. Run tests
python selenium_frontend_test.py
python scripts/testing/selenium_complete_e2e.py
python scripts/testing/selenium_announcements_rating_test.py

# 3. Cleanup after tests
./scripts/testing/selenium_test_cleanup.sh
```

### Test User Management
```bash
# Create 10 test users
python scripts/testing/test_user_manager.py create 10

# List all test users
python scripts/testing/test_user_manager.py list

# Delete all test users
python scripts/testing/test_user_manager.py cleanup
```

---

## 📸 Test Artifacts

- **Screenshots**: `test_screenshots/`
- **Test Users**: All start with `MNR19XXXXX`
- **Test Parent**: `MNR1900000`

---

## ✅ Testing Checklist

- [ ] Backend running (port 8000)
- [ ] Frontend running (port 5000)
- [ ] Test users created
- [ ] Environment variables set
- [ ] Tests executed successfully
- [ ] Screenshots reviewed
- [ ] Test data cleaned up

---

## 🚨 Important Notes

⚠️ **Always cleanup after testing**  
⚠️ **Test users are in MNR19XXXXX range**  
⚠️ **All test accounts use password: TestPass123!**  
⚠️ **Cleanup script deletes ALL MNR19 users**

---

**Full Protocol**: See `tests/STF_PROTOCOL.md`
