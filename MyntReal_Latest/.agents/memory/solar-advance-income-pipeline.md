---
name: Solar advance and income pipeline rules
description: Stage-1 CIBIL advance, Stage-2 DVR advance, and COMMISSION income generation rules for solar leads.
---

## Pipeline Rules

### Stage-1 CIBIL Advance (vgk_solar_cibil_advances, kind=ADVANCE)
- Tiers: L1 = associated_partner_id (₹1500), L2 = team_senior_partner_id (₹500)
- Eligibility: solar_pipeline_status ∈ ELIGIBLE_STAGES + cibil_confirmed=True + cibil_score>=600
- Trigger: check_and_create_advance() fires when solar_pipeline_status/cibil_confirmed/cibil_score/solar_brand_id changes

### Stage-2 DVR Advance (vgk_solar_cibil_advances, kind=DVR_ADVANCE)
- Tiers: L1 = associated_partner_id (₹500), L2 = vgk_field_support_id (₹1000) — NO senior
- Eligibility: deal_value_received > 0 (DVR > 0)
- Trigger: DC-CFV (balance_received/subsidy_pending), DC-INSTALL-PENDING-DVR-001 (installation_pending), secondary hook (DVR value updated)
- Gate removed: income_row was previously required but blocked by DC-SOLAR-STAGE-GATE-001 (Jul 2026 fix: DC-FIX-DVR-GATE-001)

### COMMISSION Income (vgk_cash_income_entries)
- Created by generate_vgk_cash_income_drafts() — gated by DC-SOLAR-STAGE-GATE-001 to only create at sps=completed
- Retrigger: _RETRIGGER_FIELDS includes 'solar_pipeline_status' (Jul 2026 fix: DC-SPS-RETRIGGER-001)
- Release gate: DC-SOLAR-RELEASE-GATE-001 — release_cash_income() blocks COMMISSION release if sps != 'completed'
- ADVANCE kinds exempt from release gate: ADVANCE, DVR_ADVANCE, BRAND_ADVANCE, SLAB_BONUS, ADJUSTMENT

### Key status distinction
- Solar leads NEVER reach status='completed' — they stay at status='won' forever
- Pipeline progresses via solar_pipeline_status: application_submitted→...→installation_pending→balance_received→subsidy_pending→completed
- All income/advance gates must check solar_pipeline_status, NOT status

**Why:** DC-SOLAR-STAGE-GATE-001 ensures final commissions only pay when balance is truly received. DVR advances are pre-balance payments contingent only on deal_value_received being confirmed.
