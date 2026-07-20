---
name: Party ledger OR filter — party_id + party_name
description: DC-PL-OR-FILTER-001: when both party_id and party_name are provided to list_entries, use OR so purchase entries with a different name spelling still appear.
---

## Rule

`PartyLedgerService.list_entries()` must use OR logic when both `party_id` and `party_name` are provided:
- `PartyLedger.party_id == party_id  OR  party_name ILIKE '%name%'`

**Why:** Purchase invoices are posted to `party_ledger` with `party_name = VendorMaster.vendor_name` (canonical DB spelling). JV receipts are typed manually and may use a different spelling (e.g. "CHINNI AGANCY" vs "CHINNI AGENCY"). When the frontend opens a party's ledger it sends both `party_id` and `party_name`. The old AND logic hid purchase entries that matched by `party_id` but not by the ILIKE pattern — they were in the DB but invisible on screen.

**How to apply:** Fixed in `PartyLedgerService.list_entries()` with DC-PL-OR-FILTER-001 block. If that method is ever refactored, preserve the OR logic for the dual-identifier case.

## Also related: DC-PL-BACKFILL-001

`backfill_party_ledger_for_purchases()` in `sfms_seed.py` retroactively creates `party_ledger` CREDIT entries for CONFIRMED purchase uploads whose VENDOR_TXN entry was silently missing (pre-date posting code or SAVEPOINT drop). Called at startup — idempotent. When it ran, it found 42 confirmed purchases all already had entries — confirming the root cause was the OR-filter bug, not missing data.
