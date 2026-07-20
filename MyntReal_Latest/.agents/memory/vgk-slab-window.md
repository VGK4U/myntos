---
name: VGK slab bonus window check
description: Bonanza window uses lead.submit_date for ALL three slab-bonanza functions; ADJUSTED/RECOVERED/DEFICIT statuses never count; INCOME_EARNED pts exempt from correction cap.
---

## DC-BONANZA-SUBMITDATE-001 (Jun 2026)
All three slab_wise bonanza functions must use `crm_leads.submit_date` (not
`advance.created_at`) as the window anchor.  NULL submit_date = ineligible.

| Function | File | Status |
|---|---|---|
| `apply_slab_bonus_if_active` | vgk_solar_advance.py | ✅ Fixed |
| `_count_solar_advances_for_bonanza` | bonanza.py | ✅ Fixed Jun 2026 |
| `get_member_reward_files` SQL | bonanza.py | ✅ Fixed Jun 2026 |

**Why:** A lead submitted to the bank in April must not qualify for a May–Jun campaign
even if the advance entry was created or released in June. submit_date is the true
"file date" — the moment the partner physically submitted the bank application.

**How to apply:** JOIN crm_leads on lead_id; use `cl.submit_date` for the date window.
Only count `status IN ('RELEASED','PENDING')`.  ADJUSTED, RECOVERED, DEFICIT are
clawback/reversal statuses — exclude them.  `NULL submit_date` (e.g. loan_rejected
leads) = not eligible.

**Web badge parity:** In the My Earnings > Bonanza Rewards sub-tab (vgk_dashboard.html),
add `if (st.includes('Rejected')) return ...Rejected...` BEFORE the `b.achieved` check.
Mobile statusChip already handles this via line-225 `bnz-chip-clmd` fallback.

## DC_VGK_POINTS_CORRECTION_001 cap rules
Caps non-paid VGK members at:
  `10,000 + CAMPAIGN_BONUS + REFERRAL_BONUS + SIGNUP_BONUS + max(0, net INCOME_EARNED)`

**Why:** INCOME_EARNED points represent real business earnings (advances, commissions,
slab bonuses). They must never be capped — only promotional/welcome bonus excess is removed.

## Startup log timing
Backend startup thread logs from correction jobs appear AFTER
"Application startup complete" in uvicorn logs. Normal — they run in a background thread.
