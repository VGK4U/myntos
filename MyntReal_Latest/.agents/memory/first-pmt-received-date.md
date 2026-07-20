---
name: first_payment_received_date vs first_dvr_confirmed_at
description: first_dvr_confirmed_at is set to now_ist when DVR advance is created (unreliable); first_payment_received_date is the correct column for date-window filtering.
---

## The Bug (DC-FIRST-PMT-001)

`crm_leads.first_dvr_confirmed_at` is set in `vgk_solar_advance.py` as:
```python
first_dvr_at = now_ist  # ← system clock at advance creation, NOT payment date
```

A bulk run on 2026-07-11 stamped ALL eligible leads with `first_dvr_confirmed_at = 2026-07-11`
regardless of when the actual first payment was received (some payments dated Apr/May/Jun 2026).

## The Fix

Added `first_payment_received_date DATE` to `crm_leads`:
- Backfilled from `MIN(crm_lead_transactions.transaction_date)` WHERE `validation_status='validated'`
- Updated live in `validate_transaction()` in `crm.py` when a transaction is validated
- Migration key: `first_payment_received_date_20260712`

## Where each column belongs

| Column | Meaning | Use for |
|--------|---------|---------|
| `first_dvr_confirmed_at` | System timestamp when DVR advance record created | Advance pipeline internals only |
| `first_payment_received_date` | Actual date money was first received (from crm_lead_transactions) | All date filters + bonanza counting |

## Impact

- **DVR filter** (all 3 endpoints: list_leads, get_leads_analytics, executive_analytics): now uses `first_payment_received_date`
- **Bonanza member tracking** `else` branch: replaced crm_lead_deals query with `first_payment_received_date` window query
- **`_count_solar_advances_for_bonanza`** DVR/BOTH basis: uses `first_payment_received_date` not `first_dvr_confirmed_at`

**Why:** `first_dvr_confirmed_at` is not event-driven — it's a system clock stamp at advance creation time, useless as a payment-received date filter.
