---
name: Incentive handler gate — _sup SQL
description: DC-HANDLER-CONFIRM-GATE-001 — how has_support is derived in staff_performance.py incentive calculation.
---

## Rule (DC-HANDLER-CONFIRM-GATE-001)
`has_support` for a CRM lead = 1 (company rate + bonus eligible) ONLY when:
1. `source != 'Self Lead'` — and
2. ALL assigned handler slots have `*_supported = TRUE`

Null id = slot unassigned = passes automatically (no confirmation required for unassigned handlers).

## SQL pattern
```sql
CASE
    WHEN l.source = 'Self Lead' THEN 0
    WHEN (
        (l.guru_id           IS NULL OR l.guru_supported            = TRUE)
        AND (l.z_guru_id     IS NULL OR l.z_guru_supported          = TRUE)
        AND (l.adi_guru_id   IS NULL OR l.adi_guru_supported        = TRUE)
        AND (l.field_support_ref_id IS NULL OR l.field_support_supported = TRUE)
        AND (l.telecaller_id IS NULL OR l.telecaller_supported      = TRUE)
        AND ((l.field_staff_id IS NULL AND l.associated_partner_id IS NULL)
             OR l.showroom_supported = TRUE)
        AND (l.technical_id  IS NULL OR l.technical_supported       = TRUE)
    ) THEN 1
    ELSE 0
END
```

## DVR formula (unchanged)
`COALESCE(NULLIF(l.deal_value_received, 0), l.deal_value, 0)` — validated transactions primary, deal_value fallback.

**Why:** User confirmed deal_value must remain as fallback for leads with no payment recorded yet.

## DB columns (all on crm_leads, confirmed crm.py lines 245-251)
guru_supported, z_guru_supported, adi_guru_supported, telecaller_supported, showroom_supported, technical_supported, field_support_supported — all Boolean nullable, added April 2026 DC Protocol.
