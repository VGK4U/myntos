---
name: DVR_ADVANCE kind constraint
description: vgk_solar_cibil_advances CHECK constraint was missing DVR_ADVANCE, silently blocking all DVR advance creation.
---

## Rule
Always ensure `vgk_solar_cibil_advances_kind_check` includes ALL used kind values: `('ADVANCE','BRAND_ADVANCE','DVR_ADVANCE')`.

**Why:** DC-VGK-MULTI-ADV-001 set the constraint to `('ADVANCE','BRAND_ADVANCE')` only. DVR_ADVANCE was added in a later migration (`DC-SOLAR-DVR-ADV-20260701-001`) which added columns but never updated the CHECK. Every `check_and_create_dvr_advance()` call silently failed with CheckViolation — the function caught the exception and returned `{'created': False, 'reason': '...CheckViolation...'}`, so no DVR advances existed in the DB.

**How to apply:** When adding a new `kind` value to any table with a CHECK constraint, always update the constraint in the same migration. Use `DO $$ BEGIN ... ALTER TABLE ... DROP CONSTRAINT IF EXISTS ...; ALTER TABLE ... ADD CONSTRAINT ...; EXCEPTION WHEN others THEN NULL; END $$` pattern to make it idempotent. Fixed via `DC-ADV-KIND-CONSTRAINT-001` (Jul 2026).
