---
name: field_allowance_progress user_id column type
description: fap.user_id is VARCHAR (emp_code), not an integer FK to user table
---

## Rule
`field_allowance_progress.user_id` is **character varying**, storing the `emp_code` value (e.g. "MR10001").
The correct JOIN is `JOIN staff_employees se ON se.emp_code = fap.user_id`.

**Why:** The `user` table has no `full_name` or `emp_code` columns. Its `id` column is also varchar.
The `staff_employees` table has both `full_name` and `emp_code` (varchar) and `id` (integer serial).
No FK constraint is declared on `fap.user_id`, making the join target non-obvious from schema alone.

**How to apply:** Any query that enriches field_allowance_progress rows with user name/code must
use `staff_employees` not `"user"`. Protocol: DC-FIELD-ALLOW-SQL-002 (Jun 2026).
