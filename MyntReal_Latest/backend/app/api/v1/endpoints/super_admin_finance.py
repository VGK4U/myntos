from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.rbac import require_super_admin
from app.models.user import User
from app.models.staff_accounts import AccountLedger, PartyLedger

router = APIRouter()

@router.get("/super-admin/finance/cash-ledger")
def get_cash_ledger(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Returns cash ledger statistics and recent transactions from live DB."""
    try:
        # Sum of debits and credits for Cash accounts
        cash_in = db.query(func.sum(AccountLedger.debit_amount)).filter(
            AccountLedger.account_type == 'CASH',
            AccountLedger.entry_type == 'RECEIPT'
        ).scalar() or 0.0

        cash_out = db.query(func.sum(AccountLedger.credit_amount)).filter(
            AccountLedger.account_type == 'CASH',
            AccountLedger.entry_type == 'PAYMENT'
        ).scalar() or 0.0
        
        recent_txs = db.query(AccountLedger).filter(
            AccountLedger.account_type == 'CASH'
        ).order_by(AccountLedger.created_at.desc()).limit(10).all()
        
        tx_list = []
        for tx in recent_txs:
            tx_list.append({
                "id": f"CSH-{tx.id}",
                "type": 'IN' if tx.entry_type == 'RECEIPT' else 'OUT',
                "source": tx.notes or tx.account_name,
                "amount": float(tx.debit_amount or tx.credit_amount or 0),
                "date": str(tx.created_at.date()),
                "handler": f"User {tx.created_by}",
                "location": "HQ"
            })

        return {
            "success": True,
            "data": {
                "vault_balance": cash_in - cash_out,
                "cash_in_mtd": cash_in,
                "cash_out_mtd": cash_out,
                "last_reconciled": datetime.now().isoformat(),
                "transactions": tx_list
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/super-admin/finance/expenses")
def get_expenses(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Returns company expenses metrics and logs from live DB."""
    try:
        total_expenses = db.query(func.sum(AccountLedger.debit_amount)).filter(
            AccountLedger.account_type == 'EXPENSE'
        ).scalar() or 0.0
        
        recent_expenses = db.query(AccountLedger).filter(
            AccountLedger.account_type == 'EXPENSE'
        ).order_by(AccountLedger.created_at.desc()).limit(10).all()
        
        exp_list = []
        for exp in recent_expenses:
            exp_list.append({
                "id": f"EXP-{exp.id}",
                "date": str(exp.created_at.date()),
                "category": exp.account_name,
                "vendor": exp.notes or "General",
                "amount": float(exp.debit_amount or 0),
                "status": 'Paid'
            })
            
        return {
            "success": True,
            "data": {
                "total_expenses_mtd": float(total_expenses),
                "pending_claims": 0,
                "top_category": "Analytics Needed",
                "transactions": exp_list
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/super-admin/finance/revenue")
def get_revenue(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Returns revenue collection data from live DB."""
    try:
        total_revenue = db.query(func.sum(AccountLedger.credit_amount)).filter(
            AccountLedger.account_type == 'INCOME'
        ).scalar() or 0.0
        
        recent_revenue = db.query(AccountLedger).filter(
            AccountLedger.account_type == 'INCOME'
        ).order_by(AccountLedger.created_at.desc()).limit(10).all()
        
        rev_list = []
        for rev in recent_revenue:
            rev_list.append({
                "id": f"REV-{rev.id}",
                "date": str(rev.created_at.date()),
                "source": rev.account_name,
                "amount": float(rev.credit_amount or 0),
                "status": 'Collected'
            })
            
        return {
            "success": True,
            "data": {
                "total_revenue_mtd": float(total_revenue),
                "target_achievement": 0,
                "top_source": "Analytics Needed",
                "transactions": rev_list
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/super-admin/finance/supreme-analytics")
def get_supreme_analytics(current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Returns supreme analytics and predictions from live DB."""
    try:
        total_revenue = db.query(func.sum(AccountLedger.credit_amount)).filter(
            AccountLedger.account_type == 'INCOME'
        ).scalar() or 0.0
        
        total_expenses = db.query(func.sum(AccountLedger.debit_amount)).filter(
            AccountLedger.account_type == 'EXPENSE'
        ).scalar() or 0.0
        
        profit = float(total_revenue) - float(total_expenses)
        margin = (profit / float(total_revenue) * 100) if float(total_revenue) > 0 else 0
        
        return {
            "success": True,
            "data": {
                "net_profit_margin": round(margin, 2),
                "runway_months": 0,
                "cac": 0,
                "ltv": 0,
                "metrics": [
                    { "metric": "Monthly Recurring Revenue (MRR)", "value": f"₹ {total_revenue}", "trend": "0%" },
                    { "metric": "Total Expenses", "value": f"₹ {total_expenses}", "trend": "0%" },
                    { "metric": "Net Profit", "value": f"₹ {profit}", "trend": "0%" },
                ]
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
