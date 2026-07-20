# Production Database Reset Instructions

## 📋 Overview
This guide will help you reset the **production database** at https://app.bevseries.com to ₹0 (matching your development environment).

---

## ⚠️ IMPORTANT: Before You Start

### Backup Checklist
- [ ] Ensure you have a recent database backup
- [ ] Notify users of potential brief downtime (if needed)
- [ ] Verify this is what you want to do (ALL production earnings will reset to ₹0)

### What This Script Does
✅ Resets ALL earnings to ₹0 (682 pending_income records)  
✅ Resets ALL user wallets to ₹0 (earning, withdrawable, etc.)  
✅ Resets ALL awards progress (counters, timestamps, status)  
✅ Resets ALL field allowances to inactive  
✅ Resets ALL transactions to ₹0  
✅ **PRESERVES** user accounts, packages, activation status, binary tree, Ved relationships  

---

## 🚀 Step-by-Step Instructions

### Step 1: Access Production Database
1. Go to your Replit project: https://replit.com/@viswanathm/BeV-20
2. Click on the **"Database"** icon in the left sidebar
3. **IMPORTANT**: Switch to **"Production"** database using the dropdown at the top
   - You should see: `Production database connected`
   - NOT: `Development database connected`

### Step 2: Open the Reset Script
1. In Replit, navigate to: `backend/PRODUCTION_RESET_SCRIPT.sql`
2. This file contains the complete reset script

### Step 3: Copy the Script
1. **Select ALL** the SQL code in `PRODUCTION_RESET_SCRIPT.sql`
2. Copy it (Cmd+C / Ctrl+C)

### Step 4: Execute in Database Console
1. In the Database pane, look for the **SQL Console** or **Query** tab
2. Paste the entire script
3. Click **"Run"** or **"Execute"**

### Step 5: Review Verification Results
The script will show you verification results like this:

```
category                              | records_with_value
--------------------------------------|-------------------
User Wallets (all 6 columns)         | 0
Pending Income                        | 0
Ved Income                            | 0
Direct Award Progress (ALL fields)    | 0
Matching Award Progress (ALL fields)  | 0
Field Allowance (ALL fields)          | 0
Car Allowance (ALL fields)            | 0
Company Earnings                      | 0
Transaction Table                     | 0
TDS Payable                           | 0
Withdrawal Requests                   | 0
Referral Income                       | 0
```

**ALL values should be 0** ✅

### Step 6: Commit or Rollback

#### If ALL verification values = 0 (Success):
```sql
COMMIT;
```
This saves all changes permanently.

#### If ANY value > 0 (Problem):
```sql
ROLLBACK;
```
This undoes all changes - nothing is saved.

---

## 🔍 Post-Reset Verification

After committing, verify on production:

1. **Visit**: https://app.bevseries.com
2. **Login** as any user
3. **Check Earnings Summary page** - should show ₹0
4. **Check Dashboard** - all wallets should show ₹0
5. **Try a hard refresh** (Cmd+Shift+R / Ctrl+Shift+F5) if you still see old values

---

## ✅ Expected Results

### What Changes:
- All earnings: ₹0.00
- All wallets: ₹0.00
- All awards: Reset to "In Progress" / "Pending"
- All allowances: Reset to "Inactive"
- All transactions: ₹0.00

### What's Preserved:
- User accounts (Active/Inactive status)
- User packages (Platinum, Diamond, etc.)
- Activation dates
- Binary tree structure
- Ved relationships
- Bonanza campaigns
- KYC data
- Bank details
- Registration dates

---

## 🆘 Troubleshooting

### Problem: "Table not found" errors
**Solution**: Make sure you're on **Production** database (check dropdown)

### Problem: Script takes too long
**Solution**: This is normal for 682+ records. Wait for completion (~30-60 seconds)

### Problem: Still seeing old values on website
**Solution**: 
1. Clear browser cache completely
2. Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
3. Try incognito/private window

### Problem: Need to undo the reset
**Solution**: 
- If you haven't typed `COMMIT;` yet → Type `ROLLBACK;`
- If already committed → Restore from database backup

---

## 📞 Support

If you encounter any issues:
1. **DO NOT type COMMIT** if verification shows errors
2. Type `ROLLBACK;` to undo changes
3. Contact support or check database logs

---

## 📊 Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Switch to Production DB | 10 sec |
| 2 | Open reset script file | 5 sec |
| 3 | Copy script | 5 sec |
| 4 | Paste & Execute | 10 sec |
| 5 | Review verification | 20 sec |
| 6 | COMMIT or ROLLBACK | 5 sec |
| **Total** | **~1 minute** | |

---

**Last Updated**: October 11, 2025  
**Script File**: `backend/PRODUCTION_RESET_SCRIPT.sql`  
**Development Reset**: ✅ Already completed (Oct 11, 2025)
