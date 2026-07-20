---
name: VGK solar income retrigger gate
description: Solar leads never reach status='completed'; retrigger and all income hooks must check solar_pipeline_status, and ADVANCE entries must not block COMMISSION entries at the same level.
---

## Rule
Any code path that triggers `generate_vgk_cash_income_drafts` must gate on:
```python
lead.status == 'completed'
OR lead.solar_pipeline_status in {'balance_received', 'subsidy_pending', 'completed'}
```
NOT just `status == 'completed'` alone.

## Why
Solar leads are marked `status='won'` when the deal is agreed and stay there permanently.
The detailed solar pipeline uses `solar_pipeline_status` for progression through
`balance_received → subsidy_pending → completed`. No solar lead ever transitions
`status → 'completed'`. A gate on `status == 'completed'` alone silently skips every
single solar lead, producing 0 commission entries even when money is confirmed received.

Affected locations fixed (DC-BRP-RETRIGGER-001, Jul 2026):
- `crm.py` DC-TEAM-RETRIGGER-001 block (~line 7237): retrigger for team-assignment edits
- `crm.py` MNR leads master hook (~line 12215): secondary save endpoint

## ADVANCE idempotency (DC-ADV-IDEM-001, Jul 2026)
The idempotency check in `vgk_cash_income.py` (~line 265-272) must exclude `kind='ADVANCE'`:
```python
VGKCashIncomeEntry.kind != 'ADVANCE',
```
An ADVANCE mirror is a pre-payment advance, not the final commission. If an ADVANCE
exists for (partner, lead, level) and the filter has no kind exclusion, the COMMISSION
entry for that level is silently skipped — the partner loses their full commission payout.
ADVANCE and COMMISSION must coexist at the same level.

**How to apply:** Any future idempotency check on `vgk_cash_income_entries` must exclude
both `status='CANCELLED'` AND `kind='ADVANCE'` from the "entry already exists" check.
