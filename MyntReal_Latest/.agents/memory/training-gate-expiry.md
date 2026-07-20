---
name: Training gate grace period expiry
description: How DC_TRAINING_VIDEOS_001 training gate works, what breaks when it expires, and how to recover.
---

## Rule
When the 7-day grace period in `dc_migrations` (key `training_gate_deployed_at`) expires, `get_training_status` returns `is_gated: true` for every employee who has not completed all training videos. The sidebar JS (`applyTrainingGate`) then replaces `allowedMenuPaths` with only `{'/staff/training-videos'}`, causing the sidebar to show only 4 hardcoded pinned items + the STAFF DASHBOARD section (which contains the Training Videos item) — exactly 5 visible items.

## Why
`is_gated = not is_exempt and not grace_active and not all_done`. Grace expires silently at `deployed_at + 7 days`. Nobody gets a warning, so it looks like menus "disappeared" rather than a gate activating.

## How to apply
- **Diagnosis**: staff see only "Progress / Task Planner / KRA Status / Time Sheet / Staff Dashboard" → immediately suspect training gate. Check `dc_migrations WHERE key = 'training_gate_deployed_at'` and compare `created_at + 7 days` to NOW.
- **Immediate fix**: `UPDATE dc_migrations SET created_at = NOW() WHERE key = 'training_gate_deployed_at';` → resets the 7-day window. All staff regain full menus instantly without touching menu grants.
- **Code bug fixed**: `is_exempt` was checking nonexistent attribute `employee_code`; correct attribute is `emp_code`. MR10001 exemption was silently broken.
- **Grace logic fix**: anchor = `max(deployed_at, emp_created)` so new hires always get their own 7-day window. Use `_tv_ist_now()` (not `utcnow()`) for comparison, consistent with IST naive datetime convention.
- **No menu grants are touched** — this is a sidebar JS override, fully separate from `staff_employee_menu_settings`.
