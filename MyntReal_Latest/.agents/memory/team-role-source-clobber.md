---
name: Team role auto-derive must gate on actual change, not payload presence
description: CRM lead PUT handler pattern — auto-derive blocks tied to a sibling field's *presence* in payload (not its *change*) silently clobber manually-entered values when the frontend always resends that sibling field.
---

Any "auto-derive field X from field Y" block on an update endpoint must trigger on `Y actually changed` (compare new vs. currently-stored value), never on `Y is present in the request payload`. If a save form always resends Y alongside every edit (common for "full edit" modals that serialize the whole form), a presence-based gate fires on every save and overwrites any manually-entered override of X — even when the user never touched Y.

**Why:** Found in `crm.py` PUT /leads/{id}: an upline-chain auto-derive for `team_senior/extended/core_partner_id` fired whenever `source_ref_id`+`source_ref_type` were present in `update_data`, but the full Edit-Lead modal always includes those fields on every save. This silently discarded manually-selected Senior/Extended/Core partners, replacing them with the auto-computed chain from Source's own `parent_partner_id` — looked to the user like "my changes aren't saving."

**How to apply:** When auditing or writing any "derive field A when field B changes" logic on a PUT/PATCH handler, check whether the trigger condition is `'B' in payload` (presence — usually wrong) vs `payload['B'] != current_stored_B` (actual change — usually right). Also check whether `crm_lead_audit_log`'s `_AUDIT_FIELD_MAP` covers the fields involved — team_senior/extended/core_partner_id and showroom_vgk_id are NOT tracked there, so these clobber bugs leave no audit trail and must be diagnosed by cross-referencing `official_partners.parent_partner_id` chains against current DB state.
