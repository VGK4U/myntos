---
name: Bonanza ground-source partner attribution
description: VGK partners stored as source_ref_id (not associated_partner_id) were invisible to bonanza queries — fix pattern and tests.
---

## Rule
When a VGK partner brings a solar lead, the system tries to write their ID into `crm_leads.associated_partner_id`. However, before DC-VGK-PARTNER-SYNC-001 ran on a form save, or when source_ref_type is 'vgk'/'vgk_partner'/'partner', the partner's `official_partners.id` may only exist in `source_ref_id` (VARCHAR) while `associated_partner_id` remains NULL.

**Why:** The DC-VGK-PARTNER-SYNC-001 JS logic fires only on form submit. Older leads pre-dating that logic, or leads entered without the form field filled, have NULL `associated_partner_id` even though the partner is correctly recorded in source_ref_id.

**How to apply:**
- Any query that needs to attribute a lead to a VGK partner for bonanza counting must use:
  ```sql
  COALESCE(
    cl.associated_partner_id,
    CASE WHEN cl.source_ref_type IN ('vgk','vgk_partner','partner')
              AND cl.source_ref_id IS NOT NULL
              AND cl.source_ref_id ~ '^[0-9]+$'
         THEN cl.source_ref_id::int END
  )
  ```
- This COALESCE is now in both the member-tracking query (management view) and `_count_first_pmt_for_bonanza` (claim gate) in bonanza.py.
- A startup backfill migration (`dc_assoc_partner_src_backfill_20260712`) sets `associated_partner_id` from `source_ref_id` for historical leads. Future leads should have it set by the form JS.
- This fix resolved Velaga Ramnath's leads not being counted in the July 2026 Solar Bonanza.
