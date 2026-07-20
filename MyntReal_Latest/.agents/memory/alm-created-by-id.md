---
name: ALM created_by_id type
description: account_ledger_masters.created_by_id is INTEGER not VARCHAR — passing 'SYSTEM' causes InvalidTextRepresentation error
---

`account_ledger_masters.created_by_id` is an `INTEGER` FK (references staff_employees.id).

**Why:** The column was designed to track which staff member created the ledger master. Passing `'SYSTEM'` (a string) causes `psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type integer`.

**How to apply:** For system-seeded ALM rows, omit `created_by_id` from the INSERT column list entirely (it defaults to NULL) or pass `NULL` explicitly. Do NOT pass `'SYSTEM'` or any string.

Contrast: `expense_main_category.created_by_id`, `expense_sub_category.created_by_id`, and `income_sub_category.created_by_id` are all `VARCHAR` — passing `'SYSTEM'` is fine there.
