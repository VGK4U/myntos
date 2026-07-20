---
name: VGK wallet txn_type constraint — missing HANDLER_CHANGE types
description: vgk_wallet_transactions CHECK constraint was missing HANDLER_CHANGE_ADJUSTMENT and HANDLER_CHANGE_REVERSAL, silently aborting DC-HCI-001 corrections.
---

## Rule
`vgk_wallet_transactions_txn_type_check` must include ALL txn_type values used in the codebase. When adding new txn_type strings anywhere in `app/services/`, always update the DB constraint in the same change (ALTER TABLE DROP + ADD CONSTRAINT).

## Why
`HANDLER_CHANGE_REVERSAL` and `HANDLER_CHANGE_ADJUSTMENT` (used in `vgk_income_correction.py`) were missing from the constraint. Postgres raises `CheckViolation` on INSERT, which **aborts the entire transaction at DB level** even when caught in Python as "non-fatal". Every subsequent statement in the same session then fails with `PendingRollbackError`, silently killing the correction (cancel + regenerate never completed). This caused DC-HCI-001 to be a silent no-op for any lead that had existing DRAFT/PENDING/RELEASED entries at the time of a partner reassignment.

## How to apply
- Fixed 2026-07-11 by ALTER TABLE to add the two missing values.
- Full allowed list now: `INCOME_CREDIT, INCOME_DEDUCTION, SERVICE_DEBIT, VENDOR_DEBIT, WITHDRAWAL, ADJUSTMENT, SOLAR_ADVANCE_CREDIT, SLAB_BONUS_CREDIT, SOLAR_ADVANCE_RECOVERY, SOLAR_ADV_PAYOUT, SLAB_BONUS_PAYOUT, COMPANY_PAYOUT, COMPANY_PAYOUT_DEDUCT, BONANZA_CASH_PAYOUT, ADVANCE_CASH_PAID, HANDLER_CHANGE_ADJUSTMENT, HANDLER_CHANGE_REVERSAL`.
- When adding future txn_type values: grep `txn_type=` in `app/services/` and diff against constraint definition before deploying.
