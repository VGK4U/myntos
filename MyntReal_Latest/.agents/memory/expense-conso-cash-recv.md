---
name: Expense Consolidated cash-received ledger
description: How the expense consolidated view handles field-staff who receive cash from customers via IE destination_employee
---

# DC_CONSO_CASH_RECV_001 — Expense Consolidated Cash Received

**Rule:** The expense consolidated endpoint (`GET /expense-consolidated`) must aggregate three independent pools:
1. Fund allocations (`fund_allocations` table — from Accounts dept)
2. Expense entries (`expense_entries` table — staff submitting expenses)
3. Cash received from customers (`income_entries` where `destination_type='EMPLOYEE'`)

**Why:** Field staff like MR10019 (Linga Swami) receive customer cash payments as IE destination_employee. They have no fund allocation and no expense entries yet, so the old `if fa is None and ex is None: continue` guard silently excluded them from the consolidated view.

**How to apply:** 
- Add `ie_map` query grouped by `IncomeEntry.destination_employee_id` filtered by `destination_type='EMPLOYEE'`, `reference_type != 'JOURNAL_VOUCHER'`, `is_deleted=False`
- Change skip guard to `if fa is None and ex is None and ir is None: continue`
- Add `cash_received`, `cash_receipt_count`, `cash_balance` fields to row dict
- Frontend: add "Cash Received (IN)" and "Cash Balance" columns to header, tbody, tfoot, and stats bar
- `cash_balance = cash_received - approved_amount` (customer cash minus approved expenses)

**IE employee-wise fix (related):** `renderEmployee()` in income_entries.html must fall back to `destination_employee_name` (not just `collected_by_name`) when `destination_type === 'EMPLOYEE'`. `collected_by_id` is NULL on all manually created IEs.
