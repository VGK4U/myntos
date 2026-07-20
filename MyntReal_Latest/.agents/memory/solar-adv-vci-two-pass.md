---
name: Solar advance VCI two-pass migration pattern
description: Per-row commit pattern in startup migrations can leave dependent rows (VCI) unfixed if the key INSERT fails; a second migration is needed.
---

## Rule
When a startup migration commits per-row (e.g. `_fix4k_db.commit()` inside the loop) and the final `INSERT INTO dc_migrations` fails, the first migration's per-row work IS committed but the key is NOT. On the next restart, the migration re-runs and may find the target rows already fixed (WHERE clause excludes them), then stamps the key — leaving any dependent rows (VCI entries) still broken.

**Why:** The `dc_advance_4000_fix_20260711` migration updated VSCA `advance_amount` per-row (committed) but the VCI UPDATE failed silently because the matching WHERE clause didn't fire (or the bare `text()` NameError caused early failure). On restart 3, VSCA rows were already at 1000 so WHERE `advance_amount > 1000` matched 0 rows — key was stamped, VCI still at 4000.

**How to apply:**
- Always verify BOTH the primary table AND the dependent table after a migration runs
- If dependent rows are unfixed, add a second migration with a different key that directly targets those rows
- Fee formula for VGK ADVANCE VCI: commission → admin=8%, tds=2%, net=90%
- SLAB_BONUS VCI: same 8%/2%/90% formula; use `_next_entry_number(db, company_id)` from vgk_cash_income.py
