---
name: VGK income stale-snapshot pattern — one-off backfill migrations and field-correction timing
description: Income entries generated against a stale partner snapshot (before field correction) are never auto-cleaned because idempotency skips existing levels.
---

## Rule
`generate_vgk_cash_income_drafts()` is per-level idempotent: if a level row already exists it is skipped unconditionally regardless of whether the partner or amount has since changed. Any backfill migration that runs once (dc_migrations key) or any retrigger that fires before a field correction will bake in a stale partner chain permanently.

## Why
Three confirmed cases (2026-07-11):
1. **Lead 249** — hardcoded one-off startup migration `DC-VGK-CI-BACKFILL-249-001` ran with `associated_partner_id=216`; partner later corrected to 97, but entries never regenerated. Nookunaidu (parent of 216) received wrong L2 commission indefinitely.
2. **Lead 7660** — L5 generated with `vgk_field_support_id=None` (defaulted to partner 31); field later set to 122; retrigger skipped L5 because row already existed.
3. **Lead 7703** — advance mirror entries became orphaned when `associated_partner_id` was cleared to NULL; DC-HCI-001 never fires when new value is NULL (guard requires both old and new to be truthy).

## How to apply
- When correcting any team-role field (`associated_partner_id`, `team_senior/extended/core_partner_id`, `vgk_field_support_id`, `showroom_vgk_id`) on a lead that already has income entries:
  - Use `handle_handler_change_income_correction()` (cancels old + regenerates) for `associated_partner_id` changes (X→Y where both are non-null).
  - For specific level corrections (field_support_id → stale L5): cancel the stale level row directly, reverse its wallet credit, then call `generate_vgk_cash_income_drafts()` to regenerate only the missing level.
  - For partner cleared to NULL: cancel orphaned mirror entries directly (no wallet reversal if entries are ADVANCE kind already settled via VSCA pipeline).
- DC-HCI-001 trigger condition in `crm.py` requires `_pre_update_partner_id` (old) to be truthy — it does NOT fire for NULL→X or X→NULL transitions. This is a known gap.
- Run the standard sweep after any bulk correction: query active COMMISSION entries, recompute expected partner per level, diff.
