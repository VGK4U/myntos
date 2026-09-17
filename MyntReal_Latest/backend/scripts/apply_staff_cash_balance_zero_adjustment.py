import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Resolve path dynamically relative to current file (System Rule 1)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.staff_accounts import (
    EmployeeFundLedger,
    ExpenseEntry,
    FundAllocation,
    AssociatedCompany
)
from app.models.staff import StaffEmployee


def apply_zero_balance_adjustments():
    db = SessionLocal()
    cutoff_date = date(2026, 9, 16)
    cutoff_time = datetime(2026, 9, 16, 23, 59, 59)
    print("==================================================")
    print(f"APPLYING STAFF CASH BALANCE RESET AS OF {cutoff_date}")
    print("==================================================")

    try:
        # ----------------------------------------------------
        # STEP 1: Process EmployeeFundLedger per (employee, company)
        # ----------------------------------------------------
        emp_cos = db.query(
            EmployeeFundLedger.employee_id,
            EmployeeFundLedger.company_id
        ).distinct().all()

        created_adjustments = []

        for eid, cid in emp_cos:
            last = db.query(EmployeeFundLedger).filter(
                EmployeeFundLedger.employee_id == eid,
                EmployeeFundLedger.company_id == cid,
                EmployeeFundLedger.transaction_date <= cutoff_date
            ).order_by(EmployeeFundLedger.id.desc()).first()

            if not last or last.balance == 0:
                continue

            # Check if an adjustment entry was already posted for this pair on cutoff_date
            existing_adj = db.query(EmployeeFundLedger).filter(
                EmployeeFundLedger.employee_id == eid,
                EmployeeFundLedger.company_id == cid,
                EmployeeFundLedger.transaction_date == cutoff_date,
                EmployeeFundLedger.entry_type == 'ADJUSTMENT'
            ).first()

            if existing_adj:
                print(f"[SKIP] Adjustment already exists for Emp {eid}, Co {cid}: {existing_adj.reference_number}")
                continue

            bal = Decimal(str(last.balance))
            if bal > 0:
                debit_amt = bal
                credit_amt = Decimal('0.00')
            else:
                debit_amt = Decimal('0.00')
                credit_amt = abs(bal)

            emp = db.query(StaffEmployee).filter(StaffEmployee.id == eid).first()
            co = db.query(AssociatedCompany).filter(AssociatedCompany.id == cid).first()
            emp_name = f"{emp.full_name} ({emp.emp_code})" if emp else f"Emp {eid}"
            co_name = co.company_name if co else f"Co {cid}"

            adj_entry = EmployeeFundLedger(
                employee_id=eid,
                company_id=cid,
                transaction_date=cutoff_date,
                entry_type='ADJUSTMENT',
                reference_type='ADJUSTMENT',
                reference_id=0,
                reference_number=f"ADJ-RESET-{eid}-{cid}-20260916",
                debit_amount=debit_amt,
                credit_amount=credit_amt,
                balance=Decimal('0.00'),
                narration="Opening reset / balance cleared to zero as of 16-Sep-2026 per management instruction",
                updated_by_id=1,
                created_at=cutoff_time
            )
            db.add(adj_entry)
            created_adjustments.append({
                'emp': emp_name,
                'company': co_name,
                'prev_bal': bal,
                'debit': debit_amt,
                'credit': credit_amt,
                'ref': adj_entry.reference_number
            })

        db.flush()

        print(f"\n[STEP 1 SUCCESS] Created {len(created_adjustments)} adjustment entries in EmployeeFundLedger:")
        for a in created_adjustments:
            print(f"  * {a['emp']} | {a['company']}: Prev Bal ₹{a['prev_bal']} -> DR ₹{a['debit']}, CR ₹{a['credit']} -> New Bal ₹0.00 ({a['ref']})")

        # ----------------------------------------------------
        # STEP 2: Settle Unspent Historical Fund Allocations (e.g. FA #1)
        # ----------------------------------------------------
        pending_allocs = db.query(FundAllocation).filter(
            FundAllocation.allocation_date <= cutoff_date,
            FundAllocation.status.in_(['PENDING', 'CONFIRMED', 'PARTIALLY_SETTLED']),
            FundAllocation.balance_remaining > 0
        ).all()

        settled_allocs_count = 0
        for fa in pending_allocs:
            prev_rem = fa.balance_remaining
            fa.status = 'SETTLED'
            fa.balance_remaining = Decimal('0.00')
            fa.total_expensed = fa.amount
            fa.settlement_date = cutoff_date
            fa.settlement_remarks = (fa.settlement_remarks or '') + f" [Settled as part of 16-Sep-2026 cutoff reset; cleared remaining balance ₹{prev_rem}]"
            fa.updated_at = cutoff_time
            settled_allocs_count += 1
            print(f"  * Settled Fund Allocation #{fa.id} ({fa.allocation_number}) for Emp {fa.to_employee_id}: cleared remaining ₹{prev_rem}")

        print(f"\n[STEP 2 SUCCESS] Settled {settled_allocs_count} pre-cutoff fund allocations.")

        # ----------------------------------------------------
        # STEP 3: Reconcile Pre-Cutoff SUBMITTED Expenses
        # ----------------------------------------------------
        sub_exps = db.query(ExpenseEntry).filter(
            ExpenseEntry.expense_date <= cutoff_date,
            ExpenseEntry.status == 'SUBMITTED'
        ).all()

        print(f"\n[STEP 3] Reconciling {len(sub_exps)} pre-cutoff SUBMITTED expenses (dated <= 16-Sep-2026)...")
        for e in sub_exps:
            e.status = 'APPROVED'
            e.approved_by_id = 1
            e.approved_at = cutoff_time
            e.updated_at = cutoff_time
            e.narration = (e.narration or '').strip() + " [Cutoff 16-Sep-2026: Reconciled to zero balance]"

        print(f"[STEP 3 SUCCESS] Approved/archived {len(sub_exps)} pre-cutoff expenses without debiting new float.")

        # Commit everything
        db.commit()
        print("\n==================================================")
        print("ALL ADJUSTMENTS COMMITTED TO DATABASE SUCCESSFULLY")
        print("==================================================")

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to apply adjustments: {exc}", file=sys.stderr)
        raise exc
    finally:
        db.close()


if __name__ == '__main__':
    apply_zero_balance_adjustments()
