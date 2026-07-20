---
name: party_ledger contamination pattern
description: How name/ID mismatches arise in party_ledger, the fix approach, and balance chain recompute
---

## Root Cause
When a vendor in `vendor_master` is renamed (e.g. SURYANSH ENERGY SOLUTIONS renamed to RUDRA ENERGY but same id=26), existing `party_ledger` rows keep the old `party_name` but correct `party_id=26`. New entries from that vendor get the new name `RUDRA ENERGY` with `party_id=26`. Result: two chains share the same `party_id` but different `party_name` — balance queries using only name OR only id split them incorrectly.

## The Three Code Fixes (all in staff_accounts_service.py)

1. **DC-PL-BAL-002** (`_get_party_balance`): when `party_id > 0`, filter by BOTH `party_name AND party_id` — not just name. Prevents balance chain contamination across name variants.

2. **DC-JV-VENDOR-LOOKUP-001** (JV party resolution): use JSONB `@>` company filter + UPPER/TRIM exact match + `ORDER BY id ASC`. Ensures deterministic, company-scoped vendor resolution.

3. **DC-PARTY-NAME-LOCK-001** (PAYMENT/RECEIPT/CONTRA): when `party_id > 0` is supplied, ALWAYS re-derive `party_name` from `vendor_master` by ID — never trust the stale free-text field. Prevents new entries from inheriting stale names.

## Data Fix Pattern
- **Class A**: `party_id > 0` but `party_name != vendor_master.vendor_name` → update `party_name` to match master
- **Class B**: `party_id = 0` with exact vendor_master name match for applicable company → set `party_id = vm.id`
- After each fix group: recompute `running_balance` chains in `ORDER BY id ASC` for all affected `(company_id, party_type, party_name, party_id)` tuples

## Migration Script
`backend/scripts/fix_party_ledger_contamination.py` — idempotent, covers both classes, recomputes chains.
