---
name: VGK Solar Commission Stage Gate
description: DC-SOLAR-STAGE-GATE-001 placement, category scope, and DC-SHOWROOM-CLEAR-001 ordering rules
---

## Rule
`generate_vgk_cash_income_drafts` has an internal solar pipeline gate (DC-SOLAR-STAGE-GATE-001, extended by DC-SOLAR-GATE-ALLCAT-001):
- Gate applies to ANY lead that has a non-null, non-empty `solar_pipeline_status` — not just `category_id == 6`
- Formula: `_is_solar = (category_id == 6) OR bool(solar_pipeline_status)`
- If `_is_solar` AND `solar_pipeline_status NOT IN {balance_received, subsidy_pending, completed}` → returns 0 DRAFTs
- Covers all callers: two previously ungated call sites (crm.py CRM transaction hook, staff_accounts_service.py income confirmation) had no solar check

DC-SHOWROOM-CLEAR-001 (L6 orphan cleanup when showroom cleared) is placed BEFORE the solar gate:
- If placed after the gate, it never runs for solar leads at pre-balance stages
- It uses `_showroom_id_early = getattr(lead, 'showroom_vgk_id', None)` resolved inline

**Why:** Original gate (DC-SOLAR-STAGE-GATE-001) only checked `category_id == 6`. Leads with other categories (e.g. cat=19) that went through the solar pipeline had no gate — premature COMMISSION DRAFTs were created at installation_pending/subsidy_pending stages. Extended gate (DC-SOLAR-GATE-ALLCAT-001) closes this gap by keying off `solar_pipeline_status` presence rather than category_id alone.

**How to apply:** Any future placement of cancellation/cleanup logic that must run for ALL solar stages must be placed BEFORE the solar gate block (~line 141 in vgk_cash_income.py), not after it.
