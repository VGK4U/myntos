---
name: party_ledger schema facts
description: Actual column names and constraints in party_ledger that trip up raw SQL
---

**Columns:** `debit_amount`, `credit_amount`, `running_balance` — there is NO single `amount` column.

**party_type CHECK:** `VENDOR, EMPLOYEE, MNR_USER, CUSTOMER, COMPANY, EXTERNAL` — 'STAFF' is NOT in the constraint. Any INSERT with party_type='STAFF' will fail. Always normalise STAFF→EMPLOYEE before writing.

**reference_type CHECK includes:** `JOURNAL` — valid for JV-sourced entries.

**Why:** The model file comment lists 'STAFF' as a possible value but the actual DB constraint does not allow it. The normalisation happens in `_add_party()` via `_PL_TYPE_NORM` dict in `staff_accounts_service.py`.

**How to apply:** Whenever writing raw SQL INSERTs into party_ledger, use `debit_amount`/`credit_amount`/`running_balance`, never `amount`. Always map STAFF→EMPLOYEE before any party_ledger operation.
