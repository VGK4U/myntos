---
name: Direct Work detection + per-employee incentive targets
description: How Direct Work leads are detected in lead_q SQL, and how per-employee min-target gates incentive payouts.
---

## Direct Work Detection Rule

In `lead_q` UNION branches (both telecaller_id and field_staff_id arms):

```sql
CASE WHEN (
    (l.source IS NULL OR l.source != 'Self Lead')
    AND l.guru_id IS NULL
    AND l.z_guru_id IS NULL
    AND l.adi_guru_id IS NULL
    AND (l.mnr_handler_id IS NULL OR l.mnr_handler_id = '')
    AND l.associated_partner_id IS NULL
) THEN TRUE ELSE FALSE END AS is_direct_work
```

**Why:** Self Lead with no handlers must stay in the Self bucket, not become Direct Work. Direct Work = company lead with no VGK4U or MNR member in the chain.

**How to apply:** `is_direct_work` takes priority in accumulation: `if is_direct → direct_count/amount; elif has_support → company; else → self`.

## Per-Employee Incentive Min-Target System (DC-INCENTIVE-EMP-TARGETS-001)

Table: `staff_incentive_employee_targets(employee_id, company_id, month, year, category_slug, min_target DEFAULT 2, UNIQUE(employee_id, month, year, category_slug))`

**Gate rule:** For each employee+slug, compute `total = self+company+direct`. If `total < emp_min_target` (and `emp_min_target > 0`) → all three incentive buckets = ₹0. If `emp_min_target = 0` → pay from deal 1.

Default when no row exists = **2.0**. Loaded into `_inc_target_map` before `_calc_employee`.

API endpoints (all under `/api/v1/staff/`):
- `GET /incentive-employee-targets?month=&year=&company_id=` → employees + saved targets
- `POST /incentive-employee-targets/bulk-upsert` → bulk upsert payload
- `POST /incentive-employee-targets/copy-to-next-month` → copies all rows to next month
- `DELETE /incentive-employee-targets/{id}` → delete single row

## Startup Migration Gotcha

In `main.py` startup migration blocks, `text` from SQLAlchemy is NOT in scope at the module-level migration section. Always import locally:

```python
from sqlalchemy import text as _iet_text
```

Never `_iet_text = text` — `text` is not available at that point.
