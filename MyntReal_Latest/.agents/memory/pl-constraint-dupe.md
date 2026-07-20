---
name: party_ledger duplicate constraints
description: party_ledger can accumulate duplicate pg_catalog constraint entries from schema migrations; they may appear in pg_constraint but not be enforced by the heap — test with an actual INSERT not just pg_constraint count.
---

# party_ledger duplicate constraint problem

## The rule
When adding or replacing CHECK constraints on party_ledger, always DROP by name first (which removes ALL copies), then ADD once. Never rely on `pg_constraint` row count to confirm constraint state — the catalog can show stale entries that aren't enforced.

**Why:** PostgreSQL schema migration pattern in this project adds new constraints without always dropping old copies. Result: `pg_constraint` shows 2 copies of the same constraint name, but DDL can only find constraints by name (not OID), so `DROP CONSTRAINT IF EXISTS` drops all copies at once. After a fresh ADD, there is only one copy. Old "ghost" entries in pg_constraint do not block inserts.

**How to apply:** After any constraint migration on party_ledger, verify with an actual rollback'd INSERT test (see DC-PL-CONSTRAINT-FIX-001 pattern), not by counting pg_constraint rows.

## Current expanded allowed values (as of 2026-06-03)
- **party_type**: VENDOR, EMPLOYEE, MNR_USER, CUSTOMER, COMPANY, EXTERNAL, PARTNER, USER
- **reference_type**: VENDOR_TXN, INCOME, EXPENSE, FUND_TRANSFER, STOCK_TRANSFER, RETURN, OPENING, CRM_REVENUE, SALES_INVOICE, PURCHASE_INVOICE, MANUAL, TALLY_IMPORT, JOURNAL, OPENING_BALANCE
- **entry_type**: DEBIT, CREDIT

## _ensure_party_ledger_master silent failure
This helper has a try/except that swallows errors. If a DB-level constraint violation fires during autoflush inside this call, the session enters aborted state. All subsequent `db.add()` / `db.execute()` calls in the same request silently fail. Fix: the expanded constraints prevent the violation from occurring in the first place.
