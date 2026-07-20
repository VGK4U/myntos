---
name: Category tables created_by_id is VARCHAR
description: expense_main_category, expense_sub_category, income_sub_category all use VARCHAR for created_by_id — 'SYSTEM' is valid.
---

`expense_main_category.created_by_id`, `expense_sub_category.created_by_id`, and `income_sub_category.created_by_id` are all `VARCHAR` columns (stores MNR employee codes or 'SYSTEM').

**Why:** Designed to allow both staff employee codes (e.g. 'MNR182371007') and system-generated entries ('SYSTEM').

**How to apply:** Passing `'SYSTEM'` as `created_by_id` in these tables is correct and expected for seeder/migration rows.
