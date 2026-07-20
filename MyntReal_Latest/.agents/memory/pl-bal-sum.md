---
name: Party ledger balance — SUM not running_balance
description: _get_party_balance uses SUM(debit-credit) over all rows, not the last running_balance. After bulk edits, always rebalance the chain.
---

`LedgerPostingService._get_party_balance()` computes balance as `SUM(debit_amount - credit_amount)` over all matching rows (DC-PL-BAL-003). It does NOT read the last `running_balance` stored value.

**Why:** Prevents stale running_balance from poisoning new entries after bulk fixes.

**How to apply:** After any bulk UPDATE to party_ledger rows (party_type, party_id, transaction_date changes), always run the window-function rebalance:

```sql
WITH chain AS (
    SELECT id,
           SUM(debit_amount - credit_amount)
               OVER (ORDER BY transaction_date ASC, id ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
               AS new_bal
    FROM party_ledger
    WHERE company_id = :co AND party_type = :pt AND party_id = :pid
)
UPDATE party_ledger pl SET running_balance = chain.new_bal FROM chain WHERE pl.id = chain.id;
```
