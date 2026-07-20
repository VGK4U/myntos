---
name: VGK income CANCELLED entries block retrigger
description: Two compounding bugs in vgk_cash_income_entries that cause retrigger to silently produce 0 new drafts when old entries were cancelled.
---

## The Rule
The idempotency check in `generate_vgk_cash_income_drafts` must always filter `status != 'CANCELLED'`. The DB unique index on `(company_id, partner_id, source_lead_id, level)` must be a **partial** index excluding CANCELLED rows.

**Why:** CANCELLED entries are historical/voided records. They must not block re-generation at the same (lead, partner, level) slot. Without these two fixes:
1. Python idempotency check returns `exists=True` for a CANCELLED row → silently `continue`s → 0 new entries.
2. Even if the Python check is fixed, the DB full unique constraint fires a violation on INSERT → transaction rolls back → 0 new entries.

Both gates must be open simultaneously or retrigger is blocked.

**How to apply:**
- `vgk_cash_income.py` idempotency query: always include `.filter(VGKCashIncomeEntry.status != 'CANCELLED')`.
- DB constraint: `CREATE UNIQUE INDEX ... WHERE status != 'CANCELLED'` (partial). The old `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE (...)` form applies to ALL rows including CANCELLED — never use that form for this table.
- Migration key: `vgk_cash_income_partial_unique_20260627` (already applied).
- If a wrong-rate entry is CANCELLED and regenerated: the new entry gets the correct rate from the currently-active config (DC-ALL-PAID-001 ensures Activated config is always used). The old CANCELLED entry is preserved as audit history.

## Confirmed state (Jun 2026)
- Partial index `uq_vgk_cash_income_lead_partner_level` applied, old constraint dropped.
- Lead 146 recovered: 5 DRAFT entries (L1–L5) at correct Activated config rates.
- L6 still pending — requires `showroom_vgk_id` to be set on the lead in CRM.
