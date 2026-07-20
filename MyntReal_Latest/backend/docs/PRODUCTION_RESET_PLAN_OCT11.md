# 🔄 PRODUCTION RESET PLAN - October 11, 2025

## 📋 OBJECTIVE
Reset all earnings and progress to zero while preserving user data, eligibility, and tree structure.

---

## ✅ VERIFIED CURRENT STATE (Sample: BEV1800143)

**User Data:**
- ID: BEV1800143
- Name: B.RAMALAXMI
- Package: 1.00 (Platinum)
- Activation: 2025-10-02
- Wallets: earning_wallet=0, withdrawable_wallet=0
- first_matching_achieved: TRUE ✓
- referral_bonus_count: 11
- Direct Referrals: 4 active

**Income Records:**
- Direct Referral: ₹12,000 (4 referrals × ₹3,000)
- Matching Referral: ₹64,000 (32 pairs, 2:1 first matching, 64 left/32 right consumed)

**Placement Tree:**
- Left: BEV1800145 (Y.VASUDHA, Platinum)
- Right: BEV1800186 (K.NOOKU NAIDU, Platinum)

---

## 🎯 WHAT WILL BE PRESERVED

### 1. User Master Data (NO CHANGES)
```sql
-- These columns STAY AS IS:
- id, name, email, mobile
- registration_date
- activation_date (KEEP - users stay activated)
- package_points (KEEP - Platinum/Diamond status preserved)
- referrer_id (sponsor tree intact)
- is_ved, ved_owner_id (Ved relationships preserved)
- first_matching_achieved (KEEP if TRUE)
- KYC documents, bank details
- All profile fields
```

### 2. Placement Tree (NO CHANGES)
```sql
-- placement table: ZERO changes
- All parent-child relationships intact
- All left/right positions preserved
```

### 3. Other Data (NO CHANGES)
```sql
-- These tables: NO CHANGES
- bonanza (Bonanza records)
- support_ticket (Support tickets)
- user_leg_metrics (Team metrics)
- banner, popup (Communications)
```

---

## 🔄 WHAT WILL BE RESET

### 1. Income Tables (DELETE ALL RECORDS)
```sql
DELETE FROM pending_income;           -- All pending incomes
DELETE FROM transaction;              -- All transaction history
DELETE FROM ved_income;               -- All Ved income records
DELETE FROM company_earnings;         -- All company earnings
DELETE FROM tds_payable;             -- All TDS records
DELETE FROM daily_cost_calculation;   -- All daily cost records
```

### 2. User Progress Fields (RESET TO 0)
```sql
UPDATE "user" SET
    earning_wallet = 0,
    withdrawable_wallet = 0,
    upgraded_wallet = 0,           -- If this column exists
    earned_total = 0,
    released_total = 0,
    referral_bonus_count = 0;
```

### 3. Financial Records (DELETE)
```sql
DELETE FROM withdrawal_request;       -- All withdrawal requests
-- Any other earning-related tables
```

---

## 📅 SPECIAL HANDLING

### Field Allowance Eligibility
- Start counting from **October 11, 2025**
- Check if logic already implemented in code
- If not, add date-based eligibility check

### Eligibility Preservation
- Users with `first_matching_achieved = TRUE` → Can earn Matching Referral immediately
- Users with 1:1 active direct referrals → Can earn Ved Income immediately
- NO re-qualification needed for already achieved milestones

---

## 🔒 SAFETY MEASURES

### 1. Pre-Reset Backup
```bash
# Already created: database_backup_10th_Oct_Data.sql (6.4 MB)
# Create additional pre-reset backup
pg_dump $DATABASE_URL > database_backup_before_production_reset.sql
```

### 2. Verification Queries (Before Reset)
```sql
-- Count records to be deleted
SELECT 'pending_income' as table_name, COUNT(*) FROM pending_income
UNION ALL
SELECT 'transaction', COUNT(*) FROM transaction
UNION ALL
SELECT 'ved_income', COUNT(*) FROM ved_income;

-- Verify user counts
SELECT COUNT(*) as total_users FROM "user";
SELECT COUNT(*) as activated_users FROM "user" WHERE package_points > 0;
```

### 3. Verification Queries (After Reset)
```sql
-- Verify earnings deleted
SELECT COUNT(*) FROM pending_income;  -- Should be 0
SELECT COUNT(*) FROM transaction;     -- Should be 0

-- Verify wallets reset
SELECT COUNT(*) FROM "user" WHERE earning_wallet != 0;  -- Should be 0
SELECT COUNT(*) FROM "user" WHERE earned_total != 0;    -- Should be 0

-- Verify data preserved
SELECT COUNT(*) FROM "user";  -- Should match pre-reset count
SELECT COUNT(*) FROM placement;  -- Should match pre-reset count
SELECT COUNT(*) FROM "user" WHERE first_matching_achieved = TRUE;  -- Should match
```

---

## 📝 EXECUTION PLAN

### Phase 1: Pre-Reset Verification ✓
- [x] Verify current system state
- [x] Check sample user data (BEV1800143)
- [x] Confirm placement tree intact
- [x] Verify income records exist

### Phase 2: Safety Backup
- [ ] Create pre-reset database backup
- [ ] Verify backup file size and integrity
- [ ] Document pre-reset counts

### Phase 3: Production Reset Execution
- [ ] Run DELETE statements (earnings tables)
- [ ] Run UPDATE statements (user progress fields)
- [ ] Verify consumed points auto-reset (from pending_income deletion)

### Phase 4: Post-Reset Verification
- [ ] Run verification queries
- [ ] Check sample users from frontend
- [ ] Verify users can login
- [ ] Confirm earnings show 0
- [ ] Confirm tree structure intact
- [ ] Test income calculation (should work immediately for eligible users)

### Phase 5: Field Allowance Date Logic
- [ ] Check if Oct 11 eligibility logic exists
- [ ] If not, implement date-based counting
- [ ] Verify field allowance calculation

---

## ⚠️ ROLLBACK PLAN

If anything goes wrong:
```bash
# Option 1: Restore to "10th Oct Data" checkpoint
cd backend && psql $DATABASE_URL < database_backup_10th_Oct_Data.sql

# Option 2: Restore to pre-reset backup
cd backend && psql $DATABASE_URL < database_backup_before_production_reset.sql
```

---

## ✅ SUCCESS CRITERIA

After reset, users should:
1. ✅ Login successfully
2. ✅ See their team/tree intact
3. ✅ See earnings = 0
4. ✅ See wallets = 0
5. ✅ Be able to earn immediately (if eligible)
6. ✅ Not need to re-qualify for already achieved milestones
7. ✅ Field allowance counting from Oct 11 onwards

---

## 🔍 TABLES TO VERIFY

### High Priority (Must Check)
- [x] `user` - Core data preserved, progress reset
- [x] `placement` - Tree intact
- [x] `pending_income` - Deleted
- [x] `transaction` - Deleted

### Medium Priority
- [ ] `ved_income` - Deleted
- [ ] `company_earnings` - Deleted
- [ ] `withdrawal_request` - Deleted
- [ ] `user_leg_metrics` - Check if needs reset

### Low Priority (Likely OK)
- [ ] `bonanza` - Should be preserved
- [ ] `support_ticket` - Should be preserved
- [ ] `banner`, `popup` - Should be preserved
