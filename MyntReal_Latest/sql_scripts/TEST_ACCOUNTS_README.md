# MNR Test Accounts - Production

## Overview
Time-limited test accounts with VIEW-ONLY access for demos and testing.

---

## Login Credentials

### 1. STAFF Account
| Field | Value |
|-------|-------|
| **Login URL** | `/staff/login` |
| **Employee ID** | `ViewTEST` |
| **Password** | `CKd65kcemtw3` |
| **Access Level** | VGK4U Supreme (VIEW ONLY) |
| **Companies** | All companies |

### 2. MNR User Account
| Field | Value |
|-------|-------|
| **Login URL** | `/login` |
| **MNR ID** | `MNRTEST001` |
| **Password** | `T6jZH82tVPw0` |
| **Access Level** | Regular User (VIEW ONLY) |

### 3. Partner Accounts

#### Dealer
| Field | Value |
|-------|-------|
| **Login URL** | `/partner/login` |
| **Partner Code** | `VENDTEST_DEALER` |
| **Password** | `xQmz8wLLl@FC` |
| **Category** | DEALER |

#### Distributor
| Field | Value |
|-------|-------|
| **Login URL** | `/partner/login` |
| **Partner Code** | `VENDTEST_DIST` |
| **Password** | `UyOZC8j13FIb` |
| **Category** | DISTRIBUTOR |

#### Vendor
| Field | Value |
|-------|-------|
| **Login URL** | `/partner/login` |
| **Partner Code** | `VENDTEST_VENDOR` |
| **Password** | `OOrTgmzjNJJr` |
| **Category** | VENDOR |

#### Real Dream Partner
| Field | Value |
|-------|-------|
| **Login URL** | `/partner/login` |
| **Partner Code** | `VENDTEST_RD` |
| **Password** | `sHnaYHv!RDtM` |
| **Category** | REAL_DREAM_PARTNER |

---

## SQL Scripts

### Location: `sql_scripts/`

| Script | Purpose |
|--------|---------|
| `production_test_accounts.sql` | Creates all test accounts with VIEW-ONLY access |
| `reactivate_test_accounts.sql` | Reactivates accounts for another 24 hours |
| `deactivate_test_accounts.sql` | Disables all test accounts |

---

## Usage Instructions

### First Time Setup
1. Run `production_test_accounts.sql` in your production database
2. Accounts are now active for 24 hours

### To Extend Access (Another 24 Hours)
1. Run `reactivate_test_accounts.sql` in your production database
2. Accounts are reactivated for another 24 hours

### To Disable Accounts
1. Run `deactivate_test_accounts.sql` in your production database
2. All test accounts will be suspended

---

## Security Notes

- All accounts have **VIEW-ONLY** permissions
- Each account has a **unique password**
- Accounts are clearly marked as "TEST" in their names
- Recommend running deactivation after demo/testing session

---

## DC Protocol Compliance

- Staff account has menu settings for all companies
- Partner accounts have company-specific menu settings
- All settings use `can_view=true, can_edit=false`

---

*Generated: December 20, 2025*
