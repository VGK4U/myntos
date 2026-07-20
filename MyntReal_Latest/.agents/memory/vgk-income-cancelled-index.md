---
name: VGK income entry unique index must exclude CANCELLED
description: uq_vgk_cash_income_lead_partner_level_kind on vgk_cash_income_entries must be a partial index or regenerating a cancelled level fails.
---

`vgk_cash_income_entries` has a uniqueness rule on `(company_id, source_lead_id, partner_id, level, kind)`. If that's a plain (non-partial) unique index/constraint, cancelling an entry and then regenerating the income chain for that same lead/partner/level (e.g. after a handler/source correction) throws a duplicate-key `IntegrityError`, because the CANCELLED row still occupies the slot.

**Why:** Found while backfilling leads whose Source partner had been corrected — `generate_vgk_cash_income_drafts` tried to insert a fresh DRAFT at a level where an old CANCELLED entry for the same partner already existed, and failed with `uq_vgk_cash_income_lead_partner_level_kind` violation even though the conflicting row was CANCELLED.

**How to apply:** The index must be created as `CREATE UNIQUE INDEX ... WHERE status != 'CANCELLED'` (drop the plain constraint form first via `ALTER TABLE ... DROP CONSTRAINT`, since a constraint-backed index can't be dropped directly). Before assuming this is already correct, verify with `pg_indexes`/`pg_get_constraintdef` — don't trust code comments claiming it's partial.
