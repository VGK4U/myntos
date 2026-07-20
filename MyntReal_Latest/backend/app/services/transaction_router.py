"""
DC-GTR-001: Global Transaction Router
======================================
Single source of truth for all double-entry ledger postings across modules
(Salaries, Rents, Payouts, Commissions, Incentives).

NEVER hardcode debit_amount/credit_amount directly — always call _add_acct()
with the correct `entry_type` ('DEBIT' or 'CREDIT') and a single `amount`.

DC-AL-SIGN-001 applied automatically by _add_acct:
  DEBIT-NORMAL  accounts (BANK, CASH, UPI, EXPENSE, ASSET) : dr − cr running balance
  CREDIT-NORMAL accounts (DUTIES_TAXES, INCOME, LIABILITY, PARTY): cr − dr running balance

Rates come exclusively from app.core.constants — never repeat them inline.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date as _date
from typing import Optional

from app.core.constants import (
    ADMIN_DEDUCTION_RATE,
    TDS_DEDUCTION_RATE,
    NET_PAYOUT_RATE,
)
from app.services.staff_accounts_service import LedgerPostingService


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _two(amount: Decimal) -> Decimal:
    """Round to 2 decimal places (ROUND_HALF_UP) — statutory compliance."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _post(db, company_id, account_type, account_name, txn_date,
          entry_type, ref_type, ref_id, ref_number, amount,
          narration, voucher_type, particulars, created_by_id, now):
    """Thin wrapper so callers stay readable — all args remain explicit."""
    return LedgerPostingService._add_acct(
        db, company_id, account_type, account_name, txn_date,
        entry_type, ref_type, ref_id, ref_number, amount,
        narration, voucher_type, particulars, created_by_id, now,
    )


# ---------------------------------------------------------------------------
# Public router
# ---------------------------------------------------------------------------

class GlobalTransactionRouter:
    """
    DC-GTR-001 — Unified double-entry transaction dispatcher.

    Usage
    -----
    GlobalTransactionRouter.post(
        db           = db,
        company_id   = 4,
        workflow     = "COMMISSION",          # see WORKFLOW PATHS below
        gross_amount = Decimal("10000.00"),
        party_name   = "John Doe",            # employee / vendor / party name
        bank_account = "HDFC 50200118370918", # actual bank account name in ledger
        ref_type     = "PAYMENT_VOUCHER",
        ref_id       = 123,
        ref_number   = "MRPV2026060001",
        created_by_id= 28,
        txn_date     = date.today(),          # optional; defaults to today
    )

    WORKFLOW PATHS
    ---------------
    SALARY / RENT / PAYOUT
        Dr  <Workflow> Expense A/c       gross
        Cr  <bank_account>               gross

    COMMISSION / INCENTIVE
        Dr  <Workflow> Distribution A/c  gross
        Cr  <bank_account>               gross × 90%  (NET_PAYOUT_RATE)
        Cr  TDS Payable A/c              gross × 2%   (TDS_DEDUCTION_RATE)
        Cr  Admin Processing Charges Received  gross × 8%  (ADMIN_DEDUCTION_RATE)
    """

    OUTFLOW_WORKFLOWS   = {"SALARY", "RENT", "PAYOUT"}
    SPLIT_WORKFLOWS     = {"COMMISSION", "INCENTIVE"}
    ALL_WORKFLOWS       = OUTFLOW_WORKFLOWS | SPLIT_WORKFLOWS

    @staticmethod
    def post(
        db,
        company_id:    int,
        workflow:      str,
        gross_amount:  Decimal,
        party_name:    str,
        bank_account:  str,
        ref_type:      str,
        ref_id:        int,
        ref_number:    str,
        created_by_id: Optional[int],
        txn_date:      Optional[_date] = None,
        voucher_type:  str = "JOURNAL",
        commit:        bool = True,
    ) -> dict:
        """
        Post a balanced double-entry transaction.

        Parameters
        ----------
        commit : bool
            Pass False when the caller already manages the transaction boundary
            (e.g. inside a larger multi-step commit). Default True.

        Returns
        -------
        dict  {"status": "success"|"error", "message": str, "legs": int}
        """
        wf = workflow.strip().upper()
        if wf not in GlobalTransactionRouter.ALL_WORKFLOWS:
            raise ValueError(
                f"Unknown workflow '{wf}'. Valid: {sorted(GlobalTransactionRouter.ALL_WORKFLOWS)}"
            )

        gross = _two(Decimal(str(gross_amount)))
        if gross <= 0:
            raise ValueError(f"gross_amount must be > 0, got {gross}")

        txn_date = txn_date or datetime.now().date()
        now      = datetime.now()
        legs     = 0

        # ── PATH A: Simple outflow (Salary / Rent / Payout) ─────────────────
        if wf in GlobalTransactionRouter.OUTFLOW_WORKFLOWS:
            expense_name = f"{wf.title()} Expense A/c"

            # Leg 1 — Debit Expense
            _post(db, company_id, "EXPENSE", expense_name, txn_date,
                  "DEBIT", ref_type, ref_id, ref_number, gross,
                  f"Automated {wf.lower()} booking for {party_name}",
                  voucher_type, party_name, created_by_id, now)
            legs += 1

            # Leg 2 — Credit Bank (outflow)
            _post(db, company_id, "BANK", bank_account, txn_date,
                  "CREDIT", ref_type, ref_id, ref_number, gross,
                  f"Bank settlement for {wf.lower()} — {party_name}",
                  voucher_type, party_name, created_by_id, now)
            legs += 1

        # ── PATH B: Split posting (Commission / Incentive) ──────────────────
        else:
            admin_amt = _two(gross * ADMIN_DEDUCTION_RATE)
            tds_amt   = _two(gross * TDS_DEDUCTION_RATE)
            net_pay   = gross - admin_amt - tds_amt   # avoids rounding drift
            dist_name = f"{wf.title()} Distribution A/c"

            # Leg 1 — Debit Gross Distribution Expense
            _post(db, company_id, "EXPENSE", dist_name, txn_date,
                  "DEBIT", ref_type, ref_id, ref_number, gross,
                  f"Gross {wf.lower()} distribution — {party_name}",
                  voucher_type, party_name, created_by_id, now)
            legs += 1

            # Leg 2 — Credit Bank: net 90% payout
            _post(db, company_id, "BANK", bank_account, txn_date,
                  "CREDIT", ref_type, ref_id, ref_number, net_pay,
                  f"Net {int(NET_PAYOUT_RATE * 100)}% {wf.lower()} paid — {party_name}",
                  voucher_type, party_name, created_by_id, now)
            legs += 1

            # Leg 3 — Credit TDS Payable (2% statutory withholding)
            if tds_amt > 0:
                _post(db, company_id, "DUTIES_TAXES", "TDS Payable A/c", txn_date,
                      "CREDIT", ref_type, ref_id, ref_number, tds_amt,
                      f"2% TDS retained from {party_name}",
                      voucher_type, "Govt Treasury", created_by_id, now)
                legs += 1

            # Leg 4 — Credit Admin Processing Income (8% platform fee)
            if admin_amt > 0:
                _post(db, company_id, "INCOME", "Admin Processing Charges Received", txn_date,
                      "CREDIT", ref_type, ref_id, ref_number, admin_amt,
                      f"8% admin processing fee retained from {party_name}",
                      voucher_type, "Platform Admin", created_by_id, now)
                legs += 1

            # Sanity: legs must balance (total debit == total credit)
            total_cr = net_pay + tds_amt + admin_amt
            if abs(total_cr - gross) > Decimal("0.02"):
                db.rollback()
                raise ArithmeticError(
                    f"GTR balance assertion failed: gross={gross}, "
                    f"net+tds+admin={total_cr}, diff={gross - total_cr}"
                )

        if commit:
            db.commit()

        return {
            "status":  "success",
            "message": f"DC-GTR-001: {wf} posted cleanly ({legs} legs, gross=₹{gross:,.2f}).",
            "legs":    legs,
        }
