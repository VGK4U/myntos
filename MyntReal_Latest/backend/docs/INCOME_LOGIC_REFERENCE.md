# INCOME LOGIC REFERENCE DOCUMENT

**⚠️ CRITICAL: This is the authoritative source for ALL income calculations. When user says "income logic", refer to this document.**

---

## 📊 COMPLETE INCOME CALCULATION STRUCTURES

### 1. MATCHING REFERRAL INCOME (Binary Tree Pairs)

**Formula:**
```
Pairs Matched = MIN(Available Left Points, Available Right Points)
Gross Income = Pairs Matched × ₹2,000
```

**Package Points:**
- Platinum: 1.0 point
- Diamond: 0.5 points
- Star/Loyal: 0 points (not eligible)

**Calculation Logic:**

1. **Get Total Leg Points (recursive SQL):**
   - Sum ALL active members' package_points in left leg
   - Sum ALL active members' package_points in right leg
   - Active = activation_date IS NOT NULL OR coupon_status IN ('Active', 'Activated')

2. **Get Consumed Points (from previous incomes):**
   - Sum left_points_consumed from all previous Matching Referral records
   - Sum right_points_consumed from all previous Matching Referral records

3. **Calculate Available Points:**
   - Available Left = Total Left - Consumed Left
   - Available Right = Total Right - Consumed Right

4. **Match Pairs (1:1 matching):**
   - Pairs = MIN(Available Left, Available Right)
   - Each pair consumes 1 point from left AND 1 point from right
   - Calculate Income: Gross = Pairs × ₹2,000
   - Example: 56 left, 24 right → MIN(56, 24) = 24 pairs = ₹48,000

**Deductions:**
- Admin Deduction: 10% of Gross
- Net Amount: Gross - Admin Deduction
- Withdrawal Wallet: 70% of Net
- Upgrade Wallet: 30% of Net

**Prerequisites:**
- User must have package_points > 0

**First Matching Consumption & Display Rule:**
- If Left Total Points > Right Total Points → First matching uses **2:1 ratio**
  - Pairs = MIN(Available Left / 2, Available Right)
  - Consumes: 2 points from left, 1 point from right per pair
- If Right Total Points > Left Total Points → First matching uses **1:2 ratio**
  - Pairs = MIN(Available Left, Available Right / 2)
  - Consumes: 1 point from left, 2 points from right per pair
- If equal → First matching uses **1:1 ratio**
  - Pairs = MIN(Available Left, Available Right)
  - Consumes: 1 point from left, 1 point from right per pair
- **All subsequent pairs: Always use 1:1 consumption (1 from left, 1 from right)**
- **Note:** The 2:1/1:2 ratio applies to BOTH consumption AND display (not display-only)

---

### 2. DIRECT REFERRAL INCOME (Sponsor Bonus)

**Formula:**
When referred user ACTIVATES:
- Platinum activation → Referrer earns ₹3,000
- Diamond activation → Referrer earns ₹1,500
- Star/Loyal activation → ₹0

**Calculation Logic:**

1. **Trigger:** When a user activates (on activation_date)

2. **Check Referrer:**
   - Activated user must have referrer_id
   - Referrer must be activated (package_points > 0)

3. **Bonus Amount:**
   - If activated user has package_points = 1.0 (Platinum) → ₹3,000
   - If activated user has package_points = 0.5 (Diamond) → ₹1,500
   - Otherwise → ₹0

4. **Bonus Count Tracking:**
   - Increment referrer.referral_bonus_count after payment

**Deductions:**
- Same as Matching Referral (10% admin, 70/30 wallet split)

**Example:**
- User BEV001 (Platinum) activates under BEV002
- BEV002 earns ₹3,000 Direct Referral bonus

---

### 3. VED INCOME (3rd Direct Referral Binary Tree)

**Formula:**
When user activates under Ved member's binary tree:
- Platinum activation → Ved Owner earns ₹1,000
- Diamond activation → Ved Owner earns ₹500

**Calculation Logic:**

1. **Ved Member:** User's 3rd direct referral becomes a "Ved"
   - When 3rd direct referral registers, they become Ved member
   - Ved member's is_ved = True
   - Ved member's ved_owner_id = <the person who referred them>

2. **Ved Income Trigger:** When ANY user activates
   - Walk UP the placement tree to find CLOSEST Ved member ancestor
   - If found, Ved member's ved_owner_id earns Ved Income
   - **NO CASCADING:** Only the closest Ved member's owner earns (stops at first Ved found)

3. **Ved Income Amount:**
   - If activated user has package_points >= 1.0 (Platinum) → ₹1,000
   - If activated user has package_points >= 0.5 (Diamond) → ₹500
   - Otherwise → ₹0

**Prerequisites (Ved Owner must have):**
- ✅ 1:1 active direct referrals on both sides (at least 1 left + 1 right)
- ✅ First matching achieved (has earned at least 1 matching income)
- ✅ Ved not paused by admin

**Example:**
- BEV001 has 3 direct referrals: A, B, C (Ved)
- User X activates in C's binary downline
- BEV001 (Ved Owner) earns ₹1,000 if X is Platinum

---

### 4. GURU DAKSHINA (2% of Direct Referrals' Earnings)

**Formula:**
```
Guru Dakshina = 2% × SUM(Direct Referrals' GROSS daily earnings)
```

**Calculation Logic:**

1. **Get All Direct Referrals:** WHERE referrer_id = <user_id>

2. **Sum Their GROSS Earnings for business_date:**
   - Include: Matching Referral, Direct Referral, Ved Income
   - **EXCLUDE:** Guru Dakshina itself (avoid circular dependency)

3. **Calculate 2%:**
   - Guru Dakshina = Total GROSS × 0.02

**Deductions:**
- Same as others (10% admin, 70/30 wallet split)

**Example:**
- User BEV001 has 3 direct referrals
- On Oct 2:
  - Referral A earned ₹10,000 gross (Matching)
  - Referral B earned ₹5,000 gross (Ved)
  - Referral C earned ₹3,000 gross (Direct)
  - Total: ₹18,000
- BEV001's Guru Dakshina: ₹18,000 × 2% = ₹360

---

### 5. FIELD ALLOWANCES (Monthly Recurring)

**Two Types:**

#### A. Standard Field Allowance: ₹5,000/month
**Requirements:**
- ≥7 active direct referrals
- ≥20 effective matching count
- Balanced binary tree (both legs have points)
- Max 72 months

#### B. Car Allowance: ₹25,000/month
**Requirements:**
- ≥250 effective matching count
- Balanced binary tree (both legs have points)
- Max 72 months

**Effective Matching Count:**
Uses a 7.5k multiplier for package values:
- Platinum (₹15,000): counts as 2 effective matches
- Diamond (₹7,500): counts as 1 effective match

---

## 🔒 ELIGIBILITY CRITERIA

### Criteria for Matching, Ved, Field Allowances

**Requirement:**
- 1:1 direct active points AND first active matching 1:2 or 2:1
- If NOT matched → Shows as "Not eligible as Criteria not matched"

**Important Notes:**
- **For Matching and Field Allowances:** Data WILL be calculated, but once criteria meet, these will be UNLOCKED and shown
- System must STRICTLY follow these calculations
- Delete/replace any earlier incorrect logic with this authoritative data

---

**Last Updated:** October 12, 2025
