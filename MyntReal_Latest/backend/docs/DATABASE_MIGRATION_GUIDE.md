# Database Migration Guide: Development → Production

## 📋 Overview

This guide explains how to migrate your database from **Development** to **Production** in Replit.

---

## ⚠️ IMPORTANT: Understanding Replit Databases

### Key Facts:
- **Development DB** and **Production DB** are **completely separate**
- Republishing your app **ONLY deploys code**, NOT database changes
- You must manually migrate data from Dev → Production
- Production database is on PostgreSQL 16 (Neon-hosted)

---

## 🔄 Migration Methods

### Method 1: SQL Script Migration (Recommended) ✅

**Best for**: Data resets, bulk updates, configuration changes

#### Step-by-Step:

**1. Create Migration Script in Development**
```sql
-- Example: Your reset script or data update
BEGIN;

UPDATE pending_income SET gross_amount = 0 WHERE gross_amount > 0;
UPDATE "user" SET earning_wallet = 0 WHERE earning_wallet > 0;
-- ... more updates

COMMIT;
```

**2. Test in Development First**
- Run script in **Development** database
- Verify results
- Fix any errors

**3. Apply to Production**
- Switch to **Production** database in Replit
- Run the same script
- Verify results

---

### Method 2: pg_dump/pg_restore (Full Database Copy) 🔄

**Best for**: Complete database migration, initial production setup

#### Requirements:
- PostgreSQL client tools installed
- Access to database credentials

#### Step-by-Step:

**1. Get Database Credentials**

In Replit:
- Go to **Database** tool
- Click on **Development** database
- Note down credentials:
  ```
  PGHOST: <dev-host>
  PGPORT: <dev-port>
  PGUSER: <dev-user>
  PGPASSWORD: <dev-password>
  PGDATABASE: <dev-database>
  ```

- Switch to **Production** database
- Note down production credentials

**2. Export Development Database**
```bash
# From your local machine or Replit shell
pg_dump -h <dev-host> \
        -p <dev-port> \
        -U <dev-user> \
        -d <dev-database> \
        -F c \
        -f development_backup.dump

# Or export as SQL:
pg_dump -h <dev-host> \
        -p <dev-port> \
        -U <dev-user> \
        -d <dev-database> \
        -f development_backup.sql
```

**3. Import to Production**
```bash
# Restore custom format:
pg_restore -h <prod-host> \
           -p <prod-port> \
           -U <prod-user> \
           -d <prod-database> \
           -c \
           development_backup.dump

# Or restore SQL:
psql -h <prod-host> \
     -p <prod-port> \
     -U <prod-user> \
     -d <prod-database> \
     -f development_backup.sql
```

---

### Method 3: Selective Data Migration (Table-by-Table) 📊

**Best for**: Migrating specific tables or partial data

#### Step-by-Step:

**1. Export Specific Table from Development**
```bash
pg_dump -h <dev-host> \
        -p <dev-port> \
        -U <dev-user> \
        -d <dev-database> \
        -t pending_income \
        -t "user" \
        -f specific_tables.sql
```

**2. Import to Production**
```bash
psql -h <prod-host> \
     -p <prod-port> \
     -U <prod-user> \
     -d <prod-database> \
     -f specific_tables.sql
```

---

### Method 4: Using Replit's Database Tool 🔧

**Best for**: Small data changes, quick fixes

#### Step-by-Step:

**1. Export from Development**
- Go to **Database** tool → **Development**
- Use SQL Console to query data:
  ```sql
  SELECT * FROM pending_income;
  ```
- Copy results

**2. Import to Production**
- Switch to **Production** database
- Use INSERT statements:
  ```sql
  INSERT INTO pending_income (user_id, income_type, gross_amount, ...)
  VALUES ('BEV1800001', 'Direct Referral', 12000, ...);
  ```

---

## 🎯 Recommended Workflow for Your Current Situation

### Your Case: Reset All Earnings to ₹0

Since you want to **reset data** (not copy), here's the best approach:

#### Option A: Use Your Reset Script (Fastest) ⚡

1. **Already done in Development** ✅
2. **Run same script in Production**:
   - Open `backend/PRODUCTION_RESET_SCRIPT.sql`
   - Switch to **Production** database in Replit
   - Copy & paste entire script
   - Run it
   - Type `COMMIT;` to save

**Time**: ~2 minutes  
**Risk**: Low (uses transactions, can rollback)

#### Option B: Export Clean Dev DB → Import to Production

1. **After resetting Development**:
   ```bash
   # Export clean development DB
   pg_dump -h <dev-host> -U <dev-user> -d <dev-db> -f clean_db.sql
   ```

2. **Import to Production**:
   ```bash
   # Clear production first
   psql -h <prod-host> -U <prod-user> -d <prod-db> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   
   # Import clean data
   psql -h <prod-host> -U <prod-user> -d <prod-db> -f clean_db.sql
   ```

**Time**: ~10-15 minutes  
**Risk**: Medium (drops all production data)

---

## 🛡️ Safety Checklist

Before migrating to production:

- [ ] **Backup Production** - Use Replit's Restore tool to create a restore point
- [ ] **Test in Development** - Always test scripts/migrations in dev first
- [ ] **Use Transactions** - Wrap changes in `BEGIN;` ... `COMMIT;` for rollback capability
- [ ] **Verify Results** - Check data after migration
- [ ] **Notify Users** - Inform users of potential downtime

---

## 🔍 Verification After Migration

### 1. Check Record Counts
```sql
-- Development
SELECT 'Development' as env, COUNT(*) FROM pending_income;

-- Production
SELECT 'Production' as env, COUNT(*) FROM pending_income;
```

### 2. Check Data Integrity
```sql
-- Verify all earnings are ₹0
SELECT 
    COUNT(*) FILTER (WHERE gross_amount > 0) as non_zero_records,
    SUM(gross_amount) as total_gross
FROM pending_income;
-- Should return: non_zero_records = 0, total_gross = 0.00
```

### 3. Test Application
- Login to https://app.bevseries.com
- Check earnings summary
- Verify all pages show ₹0

---

## 📝 Common Issues & Solutions

### Issue 1: "Permission Denied"
**Solution**: Ensure you're using correct credentials for production database

### Issue 2: "Table already exists"
**Solution**: Use `--clean` flag with pg_restore or DROP tables first

### Issue 3: "Foreign key violation"
**Solution**: Import in correct order (parent tables first) or use `--disable-triggers`

### Issue 4: Connection timeout
**Solution**: Split large migrations into smaller batches

---

## 🚀 Quick Reference Commands

### Get Database Connection String
```bash
# In Replit shell
echo $DATABASE_URL
```

### Test Database Connection
```bash
psql $DATABASE_URL -c "SELECT version();"
```

### Quick Table Export
```bash
psql $DATABASE_URL -c "COPY pending_income TO STDOUT CSV HEADER" > data.csv
```

### Quick Table Import
```bash
psql $PRODUCTION_DATABASE_URL -c "COPY pending_income FROM STDIN CSV HEADER" < data.csv
```

---

## 📊 Your Next Steps

For your current task (reset production to ₹0):

1. ✅ **Development Reset** - Already done
2. ⏳ **Production Reset** - Use `PRODUCTION_RESET_SCRIPT.sql`
3. ⏳ **Field Allowance Exception** - After production reset
4. ✅ **Verify** - Test on app.bevseries.com

---

## 💡 Future Migrations

For schema changes (adding columns, tables):

1. **Update Models** in `backend/app/models/`
2. **Create Migration** - Drizzle or manual SQL
3. **Test in Development**
4. **Apply to Production** - Carefully!
5. **Deploy Code** - Republish app

---

**Last Updated**: October 11, 2025  
**Replit Docs**: [Database Documentation](https://docs.replit.com)
