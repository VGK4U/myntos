---
name: DVR advance level 5 + ADVANCE VCI coexist rule
description: DVR_ADVANCE field-support partner earns at level 5 (not 2); ADVANCE and DVR_ADVANCE must coexist at the same VCI level.
---

## Rule
- `check_and_create_dvr_advance`: L1 tier = direct partner (level=1, ₹500); L5 tier = field-support partner (level=5, ₹1000). The old code incorrectly used level=2 for field support.
- `record_solar_advance_as_income_row` conflict guard (DC-ADV-MIRROR-CONFLICT-001) must exclude both `ADVANCE` and `DVR_ADVANCE` from the blocking kinds. Original guard excluded only `ADVANCE`, which caused `DVR_ADVANCE` at level=1 to silently block the `ADVANCE` L1 VCI mirror.

**Why:** Stage-1 (ADVANCE) and Stage-2 (DVR_ADVANCE) are parallel award types for the same partner on the same lead. Both legitimately occupy level=1 for the direct partner. There is no DB unique index on (company_id, partner_id, source_lead_id, level) — the guard is a code-level idempotency check, and it must allow these two kinds to coexist.

**How to apply:**
- Any new advance kind that can coexist with ADVANCE or DVR_ADVANCE at the same level must be added to the NOT IN list in the conflict check in `record_solar_advance_as_income_row`.
- Migrations that backfill ADVANCE VCIs for leads that already have DVR_ADVANCE must run `record_solar_advance_as_income_row` AFTER the fix is deployed (it was silently failing before DC-DVR-L1-COEXIST-001).
- For leads where associated_partner == vgk_field_support (same partner is both L1 and L5), the DVR_ADVANCE creates two entries for the same partner: lv=1 (₹500) + lv=5 (₹1000).
