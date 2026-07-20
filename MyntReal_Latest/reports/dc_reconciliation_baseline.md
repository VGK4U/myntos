# DC Protocol Phase 1.2: Reconciliation Analysis Report

**Generated**: 2025-11-02T17:01:18.589275
**RFC Version**: 4.1

## Executive Summary

- **Total Users Analyzed**: 1,058
- **Perfect Matches**: 1,051
- **Reconciliation Rate**: 99.3384%
- **Target Rate**: 99.95%
- **Meets Target**: ✗ NO

## Discrepancy Breakdown

- **Total Discrepancies**: 7
- **Earning Wallet Mismatches**: 7
- **Withdrawable Wallet Mismatches**: 2
- **Both Wallets Mismatched**: 2

## RFC v4.1 Formulas Used

### Earning Wallet
```
SUM(pending_income WHERE verification_status IN [
  'Pending',
  'Admin Verified',
  'Super Admin Verified',
  'Super Admin Approved',
])
```

### Withdrawable Wallet
```
SUM(pending_income WHERE status IN ['Finance Paid', 'Accounts Paid'])
- SUM(withdrawal_request WHERE status IN ['Bank Sent', 'Completed'])
```

## Top 10 Largest Discrepancies

| User ID | Earning Diff (₹) | Withdrawable Diff (₹) | Total Diff (₹) |
|---------|------------------|----------------------|----------------|
| BEV1800005 | 9362.12 | 0.00 | 9362.12 |
| BEV1800135 | 6799.47 | 0.00 | 6799.47 |
| BEV1800070 | 4891.19 | 0.00 | 4891.19 |
| BEV1800036 | 4610.14 | 0.00 | 4610.14 |
| BEV1800366 | 2520.00 | 1080.00 | 3600.00 |
| BEV1800388 | 2520.00 | 1080.00 | 3600.00 |
| BEV1800168 | 630.00 | 0.00 | 630.00 |

## Next Steps

✗ Reconciliation rate below 99.95% target.
✗ Investigate discrepancies before proceeding.
✗ Review income_breakdown and withdrawal_breakdown in full JSON report.
