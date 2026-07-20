---
name: Account Ledger Balance Bugs
description: Three bugs causing Net Balance ≠ Closing Balance in Account/Cash/General Ledger views.
---

## Bug 1 — Frontend: Wrong entry for Grand Total Closing Balance
Entries sorted DATE DESC → entries[0] is NEWEST (current balance), entries[last] is oldest on page (intermediate).
Grand Total "Closing Balance" must use entries[0].running_balance, not entries[last].running_balance.
**Applies to:** renderAlTable, renderCashTable (party_ledger.html), general ledger (general_ledger.html).

## Bug 2 — Frontend: Opening Balance derived backwards
Old code: alOb = entries[0].running_balance - entries[0].debit + entries[0].credit
= balance BEFORE the newest transaction (wrong).
Correct: alOb = alLastBal - (totalDebit - totalCredit)
= current balance minus all transaction net = balance before first ever entry.

## Bug 3 — Backend: JV edit missing _recompute_account_ledger_balances
JournalVoucherService.update() deletes+reposts account_ledger rows but never called
_recompute_account_ledger_balances(). The function already existed (called for manual edits).
Fix: capture old DR/CR account names BEFORE step 2 overwrites jv fields; add step 6 to
recompute old DR, old CR, new DR, new CR accounts after repost.

## Data-heal
After deploying fix, a one-time script recomputed all 91 accounts / 856 rows.
Admin endpoint: POST /api/v1/general-ledger/recompute-all-balances (hierarchy >= 80).

## Invariant
When running_balance chain is correct and entries sorted DATE DESC:
  entries[0].running_balance == total_debit - total_credit (net_balance from backend)
These match because running_balance starts at 0 and OB entries are included in account_ledger.
