# 🚨 USER BEV1800143 - Matching Earnings Calculation ERROR

**Date:** October 12, 2025  
**Issue:** Dashboard showing WRONG matching count due to STALE cache

---

## 📊 DATA COMPARISON

### **ACTUAL Binary Tree (CORRECT):**
```
Left Active:  74
Right Active: 32
Left Points:  74.00
Right Points: 32.00
Expected Matching: min(74, 32) = 32 ✓
```

### **user_leg_metrics Cache (WRONG/STALE):**
```
Left Active:  47  ❌ (should be 74)
Right Active: 59  ❌ (should be 32)
Left Points:  56  ❌ (should be 74)
Right Points: 24  ❌ (should be 32)
Dashboard Matching: 24  ❌ (should be 32)
```

---

## 🔍 ROOT CAUSE

**The `user_leg_metrics` cache table is STALE!**

The cache was last updated: `2025-10-12 07:12:30` by `scheduler`

But the actual binary tree has:
- **74 left active** (not 47)
- **32 right active** (not 59)

This means:
1. ❌ Dashboard pulls matching count from STALE cache (shows 24)
2. ✓ Dashboard pulls leg counts from actual tree (shows 74/32)
3. 🐛 Result: User sees "Left 74, Right 32" but matching shows 24 instead of 32

---

## 🔧 WHAT NEEDS TO BE FIXED

### **Issue 1: Cache Not Updated**
The `user_leg_metrics` cache is not being updated when:
- New placements are made
- Users activate their packages
- Team structure changes

### **Issue 2: Inconsistent Data Sources**
Different parts of dashboard pull from different sources:
- Leg counts: From actual tree calculation (CORRECT)
- Matching count: From stale cache (WRONG)

### **Issue 3: Scheduler Not Running or Failing**
The cache update scheduler may be:
- Not running at all
- Running but failing to update BEV1800143
- Running but using wrong calculation logic

---

## ✅ REQUIRED FIXES

### **Fix 1: Refresh user_leg_metrics for BEV1800143**
Update the cache with correct values:
```sql
UPDATE user_leg_metrics
SET 
    left_active_count = 74,
    right_active_count = 32,
    left_points = 74.00,
    right_points = 32.00,
    effective_matching_count = 32,  -- min(74, 32)
    updated_at = NOW(),
    calculation_source = 'manual_fix'
WHERE user_id = 'BEV1800143';
```

### **Fix 2: Ensure Consistent Data Sources**
ALL dashboard metrics should use the SAME source (either all cache or all real-time):
- Option A: Use cache for everything (but keep it updated!)
- Option B: Calculate everything real-time (no cache)

### **Fix 3: Fix Cache Update Mechanism**
Ensure user_leg_metrics updates when:
- New user placed under BEV1800143
- Team member activates package
- Scheduler runs (daily/hourly)

---

## 🧪 VERIFICATION QUERY

Run this to verify the fix:
```sql
SELECT 
    'user_leg_metrics' as source,
    left_active_count as left_active,
    right_active_count as right_active,
    effective_matching_count as matching_count
FROM user_leg_metrics
WHERE user_id = 'BEV1800143'

UNION ALL

SELECT 
    'actual_tree' as source,
    (SELECT COUNT(*) FROM ...) as left_active,
    (SELECT COUNT(*) FROM ...) as right_active,
    (SELECT MIN(...)) as matching_count
```

Both should show:
- Left: 74
- Right: 32
- Matching: 32

---

## 📋 END-TO-END FIX PLAN

1. ✅ **Immediate Fix:** Update user_leg_metrics for BEV1800143
2. ✅ **Identify Issue:** Check why cache is stale
3. ✅ **Fix Root Cause:** Repair cache update mechanism
4. ✅ **Verify All Users:** Check if other users have stale cache
5. ✅ **Test:** Confirm dashboard shows 74/32/32
