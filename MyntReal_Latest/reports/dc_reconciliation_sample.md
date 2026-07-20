# DC Protocol Phase 1.2: Reconciliation Analysis Report

**Generated**: 2025-11-02T16:38:34.686463
**RFC Version**: 4.1

## Executive Summary

- **Total Users Analyzed**: 100
- **Perfect Matches**: 88
- **Reconciliation Rate**: 88.0000%
- **Target Rate**: 99.95%
- **Meets Target**: ✗ NO

## Discrepancy Breakdown

- **Total Discrepancies**: 12
- **Earning Wallet Mismatches**: 12
- **Withdrawable Wallet Mismatches**: 11
- **Both Wallets Mismatched**: 11

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
| BEV1800145 | 40480.00 | 17200.00 | 57680.00 |
| BEV1800160 | 31680.00 | 17016.91 | 48696.91 |
| BEV1800228 | 14080.00 | 23992.20 | 38072.20 |
| BEV1800299 | 10560.00 | 25110.00 | 35670.00 |
| BEV1800377 | 8800.00 | 24856.20 | 33656.20 |
| BEV1800369 | 8800.00 | 21076.20 | 29876.20 |
| BEV1800611 | 7040.00 | 20617.20 | 27657.20 |
| BEV1800149 | 1760.00 | 11912.72 | 13672.72 |
| BEV1800470 | 1890.00 | 3510.00 | 5400.00 |
| BEV1800526 | 1890.00 | 3510.00 | 5400.00 |

## Next Steps

✗ Reconciliation rate below 99.95% target.
✗ Investigate discrepancies before proceeding.
✗ Review income_breakdown and withdrawal_breakdown in full JSON report.
