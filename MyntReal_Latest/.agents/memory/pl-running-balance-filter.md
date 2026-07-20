---
name: Party Ledger filter + balance display
description: Fixes for RUDRA 0-entry filter bug, SURYANSH duplicates, and running_balance chain display in party ledger.
---

# Party Ledger filter + running_balance display

## Rule 1: filterRefType must reset on every party select
`selectParty()` and `selectCustomParty()` in `frontend/staff_accounts_party_ledger.html` must set `filterRefType = ""` whenever a party is selected. If this is omitted, the filter value from a previous party search persists invisibly and causes 0 entries to be returned (as happened for RUDRA ENERGY — all entries are JOURNAL type, but filter was stuck on PURCHASE_INVOICE).

**Why:** The reference_type filter is not reset by the search/pagination flow — only by explicit party selection.

**How to apply:** Any time party selection logic is touched, confirm both `selectParty` and `selectCustomParty` clear `filterRefType` to `""`.

## Rule 2: Client-side running_balance recompute (DC-PL-BAL-CLIENT-001)
The backend stores `running_balance` in insertion order (ORDER BY id DESC in `_get_running_balance()`). Retro entries and backfilled rows break the chain visually. Fix: in `loadLedger()`, after fetching `data.entries`, re-sort in `transaction_date ASC, id ASC` order and recompute `running_balance` from `parseFloat(data.opening_balance)` before passing to `renderTable()`.

**Why:** Server-side rebalance would require touching every party's chain on every backfill. Client-side is safe and instant.

**How to apply:** Any time party ledger rendering logic is changed, ensure DC-PL-BAL-CLIENT-001 block (the recompute loop before `renderTable`) is preserved.

## Rule 3: Duplicate vendor transaction rows — dedup via startup migration
SURYANSH ENERGY SOLUTIONS had 7 duplicate VENDOR_TXN CREDIT rows (IDs 601,602,603,612,613,614,615) caused by two approval batches posting the same dates/amounts. Fixed via DC-PL-SURYANSH-DEDUP-001 startup migration (idempotent, guarded by dc_migrations key `dc_pl_suryansh_dedup_20260530`). After dedup, chain was rebalanced in date+id ASC order.

**Why:** `_create_ledger_entries_on_approval` idempotency check is per reference_id — separate transaction records for same invoice go through unchecked.

**How to apply:** If similar dedup is needed for other parties, follow the same pattern: DELETE specific IDs by dc_migrations guard, then window-function UPDATE to rebalance only that party's chain.
