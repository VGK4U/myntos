# DC Protocol Phase 1.2: Execution Guide
**100% Perfect Reconciliation Analysis**

## Overview
Phase 1.2 builds the reconciliation dataset by comparing stored wallet values with computed values using RFC v4.1 formulas. This establishes the baseline reconciliation rate before implementing any database changes.

## Prerequisites

### 1. RFC v4.1 Approved ✓
- Architect-approved technical specification
- Complete status taxonomy verified (4 unpaid + 2 paid + 2 rejected)
- Deployment sequence defined

### 2. Environment Ready
- Python 3.8+
- SQLAlchemy installed
- Database accessible (DATABASE_URL configured)
- Logs and reports directories writable

### 3. Database State
- All tables exist: `user`, `pending_income`, `withdrawal_requests`
- Required columns present
- Production data intact

## Execution Steps

### Step 1: Pre-Flight Validation (5 minutes)

**Purpose**: Verify environment, database, and formulas before analysis

```bash
cd /path/to/bev2.0

# Run validator
python scripts/dc_phase1_2_validator.py
```

**Expected Output**:
```
DC PROTOCOL PHASE 1.2: RECONCILIATION SCRIPT VALIDATOR
100% Perfect Validation Before Execution
======================================================================

Validating environment...
  ✓ Python version: 3.11
  ✓ Module 'sqlalchemy' available
  ✓ Module 'psycopg2' available

Validating database connection...
  ✓ Database connection successful

Validating required tables...
  ✓ Table 'user' exists
  ✓ Table 'pending_income' exists
  ✓ Table 'withdrawal_requests' exists

Validating required columns...
  ✓ Column 'user.id' exists
  ✓ Column 'user.earning_wallet' exists
  ✓ Column 'user.withdrawable_wallet' exists
  ✓ Column 'pending_income.user_id' exists
  ✓ Column 'pending_income.net_amount' exists
  ✓ Column 'pending_income.verification_status' exists
  ✓ Column 'withdrawal_requests.user_id' exists
  ✓ Column 'withdrawal_requests.final_payout' exists
  ✓ Column 'withdrawal_requests.status' exists

Validating verification_status values...
  Found 8 unique verification_status values:
    ✓ 'Pending' (valid)
    ✓ 'Admin Verified' (valid)
    ✓ 'Super Admin Verified' (valid)
    ✓ 'Super Admin Approved' (valid)
    ✓ 'Finance Paid' (valid)
    ✓ 'Accounts Paid' (valid)
    ✓ 'Rejected' (valid)
    ✓ 'Not Eligible' (valid)

Validating RFC v4.1 formulas with sample user...
  Testing with user: BEV1823000001
    Earning wallet: ₹0.0
    Withdrawable wallet: ₹0.0
  ✓ Formulas execute successfully

Validating output directories...
  ✓ Directory 'logs' exists
    ✓ Directory 'logs' is writable
  ✓ Directory 'reports' exists
    ✓ Directory 'reports' is writable

======================================================================
VALIDATION SUMMARY
======================================================================
✓ ALL VALIDATIONS PASSED
✓ Safe to run reconciliation analysis

Next step:
  python scripts/dc_phase1_2_reconciliation.py --output reports/dc_reconciliation_baseline.json
```

**If Validation Fails**:
- Review error messages
- Fix issues before proceeding
- Re-run validator until all checks pass

### Step 2: Test Run with Sample (10 minutes)

**Purpose**: Test reconciliation logic with small sample before full analysis

```bash
# Analyze first 100 users only
python scripts/dc_phase1_2_reconciliation.py \
  --output reports/dc_reconciliation_sample.json \
  --sample 100
```

**Expected Output**:
```
======================================================================
DC PROTOCOL PHASE 1.2: RECONCILIATION DATASET BUILD
RFC Version: v4.1 (Architect-Approved Final)
======================================================================
Analyzing SAMPLE: First 100 users
Total users to analyze: 100
Progress: 100/100 users analyzed...

======================================================================
RECONCILIATION ANALYSIS COMPLETE
======================================================================
Total Users Analyzed:     100
Perfect Matches:          98 (98.00%)
Total Discrepancies:      2
  - Earning Mismatches:   1
  - Withdrawable Mismatches: 1
  - Both Mismatched:      0

Reconciliation Rate:      98.0000%
Target Rate:              99.95%
Meets Target:             ✗ NO
======================================================================

Report saved to: reports/dc_reconciliation_sample.json
Top 10 discrepancies saved to: reports/dc_reconciliation_sample_top10.json
Human-readable report saved to: reports/dc_reconciliation_sample.md
```

**Review Sample Results**:
```bash
# View human-readable report
cat reports/dc_reconciliation_sample.md

# View top 10 discrepancies
cat reports/dc_reconciliation_sample_top10.json | jq '.top_10_discrepancies'
```

### Step 3: Full Production Analysis (30-60 minutes)

**Purpose**: Analyze ALL users to establish official baseline

```bash
# Full analysis (no --sample flag)
python scripts/dc_phase1_2_reconciliation.py \
  --output reports/dc_reconciliation_baseline.json
```

**Expected Output** (for ~1000 users):
```
======================================================================
DC PROTOCOL PHASE 1.2: RECONCILIATION DATASET BUILD
RFC Version: v4.1 (Architect-Approved Final)
======================================================================
Analyzing ALL users
Total users to analyze: 1,234
Progress: 100/1,234 users analyzed...
Progress: 200/1,234 users analyzed...
...
Progress: 1,200/1,234 users analyzed...

======================================================================
RECONCILIATION ANALYSIS COMPLETE
======================================================================
Total Users Analyzed:     1,234
Perfect Matches:          1,232 (99.84%)
Total Discrepancies:      2
  - Earning Mismatches:   1
  - Withdrawable Mismatches: 1
  - Both Mismatched:      0

Reconciliation Rate:      99.8381%
Target Rate:              99.95%
Meets Target:             ✗ NO
======================================================================

Report saved to: reports/dc_reconciliation_baseline.json
Top 10 discrepancies saved to: reports/dc_reconciliation_baseline_top10.json
Human-readable report saved to: reports/dc_reconciliation_baseline.md
```

**Exit Codes**:
- `0` = Success (reconciliation ≥ 99.95%)
- `1` = Warning (reconciliation < 99.95%)
- `2` = Error (script failure)

### Step 4: Review Results (15 minutes)

**View Human-Readable Report**:
```bash
cat reports/dc_reconciliation_baseline.md
```

**Analyze Discrepancies** (if any):
```bash
# View full JSON with income/withdrawal breakdowns
cat reports/dc_reconciliation_baseline.json | jq '.discrepancies[] | {
  user_id,
  earning_diff: .differences.earning_wallet,
  withdrawable_diff: .differences.withdrawable_wallet,
  income_breakdown,
  withdrawal_breakdown
}'
```

**Example Discrepancy Analysis**:
```json
{
  "user_id": "BEV1823000042",
  "earning_diff": 100.00,
  "withdrawable_diff": 0.00,
  "income_breakdown": {
    "Pending": {"count": 1, "total_amount": 100.00},
    "Finance Paid": {"count": 5, "total_amount": 2500.00}
  },
  "withdrawal_breakdown": {
    "Bank Sent": {"count": 2, "total_amount": 2500.00}
  }
}
```

**Common Discrepancy Patterns**:
1. **Manual wallet adjustments** (VGK overrides)
2. **Ledger gaps** (missing pending_income records)
3. **Status inconsistencies** (paid but not in PAID_STATUSES)

### Step 5: Decision Gate

#### Scenario A: Reconciliation ≥ 99.95% ✓

**Action**: Proceed to Phase 1.3 (Materialized Views)

```bash
# Archive baseline report
mkdir -p reports/archive
cp reports/dc_reconciliation_baseline.json reports/archive/baseline_$(date +%Y%m%d_%H%M%S).json

# Move to Phase 1.3
# (Next phase: Create materialized views)
```

#### Scenario B: Reconciliation < 99.95% ⚠

**Action**: Investigate discrepancies before proceeding

**Investigation Steps**:
1. **Review Top 10** discrepancies in detail
2. **Categorize** discrepancies:
   - Data quality issues (fixable)
   - Business logic edge cases (expected)
   - Formula bugs (critical - fix RFC)
3. **Document** findings
4. **Fix** data quality issues OR
5. **Accept** expected discrepancies and document rationale

**Escalation**:
- If formula bugs found → Update RFC, get architect re-approval
- If data quality issues → Run data cleanup scripts
- If business logic edge cases → Document and proceed with caution

## Output Files

### Primary Outputs

1. **`reports/dc_reconciliation_baseline.json`**
   - Complete reconciliation dataset
   - All discrepancies with full breakdowns
   - ~1-10 MB depending on discrepancy count

2. **`reports/dc_reconciliation_baseline.md`**
   - Human-readable summary
   - Top 10 discrepancies table
   - Executive summary with next steps

3. **`reports/dc_reconciliation_baseline_top10.json`**
   - Quick reference for largest discrepancies
   - Includes income/withdrawal breakdowns

### Logs

4. **`logs/dc_reconciliation.log`**
   - Detailed execution log
   - Progress updates every 100 users
   - Error traces (if any)

## Success Criteria

### Mandatory
- ✓ Validator passes all checks
- ✓ Sample run completes without errors
- ✓ Full analysis completes successfully
- ✓ All output files generated

### Target
- ✓ Reconciliation rate ≥ 99.95%
- ✓ Discrepancies documented and understood
- ✓ Architect review completed

### Recommended
- ✓ Sample and full results consistent
- ✓ Top discrepancies explainable
- ✓ No formula bugs identified

## Troubleshooting

### Issue: Validator fails on database connection

**Solution**:
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"

# Verify backend can connect
cd backend && python -c "from app.core.database import get_db; next(get_db())"
```

### Issue: Invalid verification_status found

**Output**:
```
⚠ WARNING: 15 invalid status values found
⚠ Run preflight cleanup before deploying validation trigger
```

**Solution**: This is expected! Phase 1.2 identifies these for later cleanup in RFC v4.1 deployment (Phase 0 preflight cleanup).

### Issue: Reconciliation script crashes mid-execution

**Solution**:
```bash
# Check logs
tail -100 logs/dc_reconciliation.log

# Re-run from checkpoint (if implemented)
# Or re-run with smaller sample to isolate issue
python scripts/dc_phase1_2_reconciliation.py --sample 10
```

### Issue: Memory usage too high

**Solution**:
```bash
# Process in batches (modify script to add batch processing)
# OR increase system memory
# OR run on more powerful machine
```

## Next Phase

Upon successful completion of Phase 1.2:

→ **Phase 1.3**: Create database materialized views using RFC v4.1 SQL
→ **Phase 1.4**: Implement shadow mode (computed + stored side-by-side)
→ **Phase 1.5**: Deploy validation triggers
→ **Phase 1.6**: Cutover to computed-only
→ **Phase 1.7**: Cleanup (delete stored columns)

---

**Document Status**: 100% Perfect Execution Guide
**Last Updated**: November 2, 2025
**RFC Version**: v4.1 (Architect-Approved)
