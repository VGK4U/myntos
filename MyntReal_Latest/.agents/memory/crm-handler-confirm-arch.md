---
name: CRM handler confirmation architecture
description: HC_CONFIG variants, L1-L5 upliner chain, Core own DB fields, auto_fetch flag, page-to-config mapping.
---

## Handler Chain (L1–L5)

| Level | Label    | DB fields                          | How set                         | Confirmation col    |
|-------|----------|------------------------------------|---------------------------------|---------------------|
| L1    | Source   | guru_id / guru_name                | Manual entry                    | guru_supported      |
| L2    | Senior   | z_guru_id / z_guru_name            | Auto-fetch (upliner of Source)  | z_guru_supported    |
| L3    | Extended | adi_guru_id / adi_guru_name        | Auto-fetch (upliner of Senior)  | adi_guru_supported  |
| L4    | Core     | core_id / core_name                | Auto-fetch (upliner of Extended)| core_supported      |
| L5    | Support  | field_staff_id OR associated_partner_id (fallback) | Manual | showroom_supported  |

**Showroom is DIFFERENT** — `showroom_vgk_id` (FK → official_partners) is the VGK showroom commission concept, entirely separate from Support L5.

## HC_CONFIG Variants

- **HC_CONFIG_STANDARD** — default for standard lead pages
- **HC_CONFIG_MASTER** — used in `staff_mnr_leads_master.html` (Source, Senior, Extended, Core, Field Support, Telecaller, Support, Technical)
- **HC_CONFIG_STAFF_UPGRADED** — used in `staff_leads.html` (same minus Technical)
- **HC_CONFIG_ETC** — ETC Training direct student modal (3 roles only)

## auto_fetch flag

`auto_fetch: true` on Senior / Extended / Core rows → blue **AUTO** badge shown next to name; no manual search input; "Auto — not resolved" when empty. Yes/Pending/No confirmation buttons still active.

## DB columns for Core (L4)

`core_id` VARCHAR(12) FK → user.id ON DELETE SET NULL (same pattern as guru_id/z_guru_id/adi_guru_id).
`core_name` VARCHAR(200) plain text (same pattern as guru_name/z_guru_name).
Added via `_handler_confirm_sqls` in main.py (runs 10/10 migrations idempotently).

**Why:** Core must have its own FK so the FK guard in `update_lead` validates it independently and batch name enrichment resolves it from User table.

## Incentive Gate (DC-HANDLER-CONFIRM-GATE-001)

All assigned handler slots must be TRUE before incentive pays. NULL slots pass. Self Lead always 0.

## Deal fields section in mnr-leads-master

The Deal fields section is OUTSIDE `solarSection` — visible for ALL category tabs. Only `solarSection` (bank app, co-applicant, CIBIL) is toggled Solar-only.

## ETC Training CRM edit flow (DC-ETC-CRM-EDIT-001)

ETC tab shows `etc_students` (not `crm_leads`). CRM-linked rows (isCrm=true) use `openCrmEditForEtc(crmLeadId)`. Direct student rows use `openEtcEdit(sid)`.
