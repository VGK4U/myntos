---
name: Incentive employee-view fields
description: Why employee Live Achievement / My Earning Capacity showed ₹0 while admin showed correct data — two distinct root causes.
---

## Rule 1 — show_all must be False for employee-scoped endpoints (DC-LIVE-ACH-SELF-001)

`get_incentive_achievements(employee_id=X, show_all=True)` returns ALL active employees
in `d.data` (sorted by incentive desc, then name). The frontend takes `d.data[0]`.
When the employee earns ₹0 (target not met) they sort into the alphabetical tail — a
different employee ends up at index 0.

**How to apply:** `/performance/my-incentive-achievements` must pass `show_all=False`
so `d.data` contains exactly the logged-in employee (or is empty).

## Rule 2 — use telecaller_id / field_staff_id, never handler_id (DC-INCENTIVE-TELE-FIELD-ONLY-001)

`crm_leads.handler_id` is `VARCHAR(50)`, NOT a FK to `staff_employees`. It is not
systematically populated. Staff CRM assignments go through:
- `telecaller_id` — `INTEGER FK → staff_employees.id`
- `field_staff_id` — `INTEGER FK → staff_employees.id`

Matching `handler_id = str(employee.id)` returns 0 rows for virtually all employees.
Always query `l.telecaller_id::TEXT = :eid` UNION `l.field_staff_id::TEXT = :eid`.

**How to apply:** Any new incentive or report query must use telecaller_id + field_staff_id,
never handler_id. `my-earning-capacity` was the last endpoint with the handler_id bug;
it is now fixed.

## Rule 3 — always use actual_close_date, never updated_at (DC-CLOSE-DATE-001)

`updated_at` bumps on any field edit, smuggling closed leads into later months.
Use `COALESCE(l.actual_close_date, l.updated_at)` as the date filter.
ETC students use `training_completed_date` (separate EXISTS subquery).

**Why:** A lead closed in March but edited in May would appear in May's incentive window.
