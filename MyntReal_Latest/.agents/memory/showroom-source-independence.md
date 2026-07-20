---
name: Showroom vs Source must stay independent
description: L1 (Source/associated_partner_id) and L6 (Showroom/showroom_vgk_id) are distinct commission roles; a field-editor for one must never write the other.
---

Editing the Showroom (L6) team-role slot on a lead must never change the lead's Source (L1 / `associated_partner_id`), and vice versa — even if they happen to be the same partner today.

**Why:** An inline table-cell editor (`type === 'handler_showroom'` in `staff_mnr_leads_master.html`) predates the multi-role Team Assignment modal. When `showroom_vgk_id` was later added as its own column, the old code path kept writing `associated_partner_id` too "for convenience," so picking a partner-type Showroom via that cell silently overwrote a Source that had already been correctly set elsewhere. Confirmed via `crm_lead_audit_log` showing only ONE write ever recorded for `associated_partner_id` (never the value shown as "Source" in the UI) plus `source_ref_id/name/type` (captured at lead creation, never touched by this bug) disagreeing with `associated_partner_id`.

**How to apply:** When auditing or building any lead-role editor (Source, Showroom, Senior/Extended/Core partner, Field Support, etc.), verify the save payload only ever includes the field(s) for the role actually being edited. Use `source_ref_id/source_ref_name/source_ref_type` as an independent ground-truth signal for what the Source *should* be when investigating suspected cross-contamination — it's the original value captured at creation and isn't part of the later multi-role team-assignment machinery. `showroom_vgk_id` is not written to `crm_lead_audit_log` at all, so audit history alone won't reveal this class of bug — cross-check against `source_ref_*` or DB state instead.
