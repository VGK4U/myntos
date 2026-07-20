---
name: Party Ledger Balance Calculation
description: Why _get_party_balance() uses SUM, not stored running_balance; and how rebalance CTEs must be ordered.
---

# Party Ledger Balance Calculation

## Rule
`_get_party_balance()` computes the closing balance as `SUM(debit_amount) - SUM(credit_amount)`, NOT by reading the stored `running_balance` of the last-by-ID row.

**Why:** Backdated entries (inserted after chronologically later rows) have a higher ID than entries with later dates. The old approach (last running_balance by ID) returned the backdated entry's intermediate balance, not the true closing balance. SUM is always mathematically correct regardless of insertion order.

**How to apply:** Any time a new party_ledger entry is inserted via `_add_party()`, the new `running_balance` = current SUM result + this row's debit - credit. Do not use `last.running_balance` from `order_by(desc(id))`.

## Rebalance CTE Order
All rebalance CTEs (in migrations and the UPDATE path) must use `ORDER BY transaction_date ASC, id ASC` — this matches the DESC display sort and ensures per-row running_balance is visually correct. Using `ORDER BY id` alone causes the running_balance to be out of chronological sync for backdated entries.

## Key code location
- `_get_party_balance()` — `backend/app/services/staff_accounts_service.py` (search for `DC-PL-BAL-003`)
- Rebalance in UPDATE path — same file, search for `DC-JV-VENDOR-LOOKUP-002`
- Startup data migration — `backend/app/main.py`, key `dc_pl_reattrib_rudra_suryansh_20260527`
