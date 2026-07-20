---
name: Incentive completion date — actual_close_date not updated_at
description: DC-CLOSE-DATE-001 — use actual close date for incentive month bucketing, not updated_at
---

## Rule
Never use `l.updated_at BETWEEN :df AND :dt` to determine which month a CRM lead counts toward for incentives. `updated_at` is bumped whenever **any field** on the lead changes (telecaller reassignment, deal value edit, etc.), causing leads completed in prior months to appear in the current month's incentive calculation.

**Why:** A lead marked completed in April but edited in June gets `updated_at = June`, making it count for June incentives — wrong month, inflated count.

## Correct date expression (DC-CLOSE-DATE-001)
```sql
COALESCE(l.actual_close_date, l.updated_at)
```
- **All CRM leads** (solar, B2B, regular): use `actual_close_date`. Fallback to `updated_at` only for legacy rows where `actual_close_date` is NULL.
- **ETC leads**: use `etc_students.training_completed_date` via the EXISTS subquery — handled separately and correctly.
- Do NOT use `submit_date` or `solar_pipeline_status_updated_at` for solar — solar uses `actual_close_date` like all other leads.

## How to apply
This expression must be used in **all three** places in `staff_performance.py`:
1. Main `_comp_where` (incentive accumulation loop) — as `_close_date_expr`
2. ETC drilldown `_etc_comp` — as `_drl_close` (must match main to show same records)
3. Standard CRM drilldown `_comp_where` — as `_drl_close2`

Also use for the **displayed** `comp_date` column in both drilldown queries so the date shown to the admin matches the date used for filtering.
