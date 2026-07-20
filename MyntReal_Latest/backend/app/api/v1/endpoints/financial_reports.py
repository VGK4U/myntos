"""
Financial Reports System - Comprehensive Revenue, TDS, and Company Earnings
Super Admin/Finance Admin analytics and reporting endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.transaction import (
    Transaction, CompanyEarnings, TDSPayable, DailyCostCalculation, PendingIncome
)
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/financial-reports", tags=["Financial Reports"])

def _require_staff(current_user):
    """DC Protocol: Financial reports require staff authentication"""
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")


@router.get("/revenue-dashboard")
async def revenue_dashboard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revenue Dashboard - Company earnings, costs, and financial health
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    # Parse date range
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
    
    # Get pending incomes for revenue calculation
    revenue_query = db.query(
        func.sum(PendingIncome.gross_amount).label('total_gross'),
        func.sum(PendingIncome.admin_deduction).label('admin_fees'),
        func.sum(PendingIncome.tds_deduction).label('tds_collected'),
        func.sum(PendingIncome.net_amount).label('total_payouts')
    ).filter(
        and_(
            PendingIncome.business_date >= start,
            PendingIncome.business_date <= end,
            PendingIncome.verification_status == 'Completed'
        )
    ).first()
    
    # Get company earnings from ceiling excess
    company_earnings_total = db.query(
        func.sum(CompanyEarnings.net_company_earnings)
    ).filter(
        and_(
            CompanyEarnings.business_date >= start,
            CompanyEarnings.business_date <= end
        )
    ).scalar() or 0
    
    # Calculate financial metrics
    total_gross = round(float(revenue_query.total_gross or 0))
    admin_fees = round(float(revenue_query.admin_fees or 0))
    tds_collected = round(float(revenue_query.tds_collected or 0))
    total_payouts = round(float(revenue_query.total_payouts or 0))
    company_earnings = round(float(company_earnings_total))
    
    net_revenue = admin_fees + company_earnings - tds_collected
    
    return {
        "success": True,
        "period": {
            "start_date": start.strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d'),
            "days": (end - start).days
        },
        "revenue_summary": {
            "total_gross_income": total_gross,
            "total_payouts": total_payouts,
            "admin_fees_collected": admin_fees,
            "tds_collected": tds_collected,
            "company_earnings_ceiling": company_earnings,
            "net_company_revenue": net_revenue
        },
        "financial_health": {
            "revenue_positive": net_revenue > 0,
            "payout_ratio": round((total_payouts / total_gross * 100) if total_gross > 0 else 0, 2),
            "admin_fee_ratio": round((admin_fees / total_gross * 100) if total_gross > 0 else 0, 2),
            "net_margin": round((net_revenue / total_gross * 100) if total_gross > 0 else 0, 2)
        }
    }


@router.get("/tds-payable")
async def tds_payable_report(
    status: Optional[str] = Query(default=None, regex="^(Pending|Paid|Adjusted)$"),
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    TDS Payable Report - Pending and paid TDS obligations
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    query = db.query(TDSPayable)
    
    if status:
        query = query.filter(TDSPayable.payment_status == status)
    
    if financial_year:
        query = query.filter(TDSPayable.financial_year == financial_year)
    
    tds_records = query.order_by(TDSPayable.business_date.desc()).all()
    
    # Calculate totals
    total_pending = sum(round(float(tds.tds_amount)) for tds in tds_records if tds.payment_status == 'Pending')
    total_paid = sum(round(float(tds.tds_amount)) for tds in tds_records if tds.payment_status == 'Paid')
    
    return {
        "success": True,
        "tds_summary": {
            "total_pending": total_pending,
            "total_paid": total_paid,
            "total_records": len(tds_records)
        },
        "tds_records": [
            {
                "id": tds.id,
                "user_id": tds.user_id,
                "tds_amount": round(float(tds.tds_amount)),
                "source_income_type": tds.source_income_type,
                "source_amount": round(float(tds.source_amount)),
                "business_date": tds.business_date.strftime('%Y-%m-%d'),
                "financial_year": tds.financial_year,
                "quarter": tds.quarter,
                "payment_status": tds.payment_status,
                "payment_date": tds.payment_date.strftime('%Y-%m-%d') if tds.payment_date else None,
                "payment_reference": tds.payment_reference
            }
            for tds in tds_records
        ]
    }


@router.post("/tds-payable/{tds_id}/mark-paid")
async def mark_tds_paid(
    tds_id: int,
    payment_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark TDS as paid with payment reference
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    tds = db.query(TDSPayable).filter(TDSPayable.id == tds_id).first()
    if not tds:
        raise HTTPException(status_code=404, detail="TDS record not found")
    
    tds.payment_status = 'Paid'
    tds.payment_date = datetime.utcnow()
    tds.payment_reference = payment_reference
    
    db.commit()
    
    return {
        "success": True,
        "message": f"TDS payment of ₹{tds.tds_amount} marked as paid",
        "tds_id": tds_id,
        "payment_reference": payment_reference
    }


@router.get("/cost-calculations")
async def cost_calculations_report(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Daily Cost Calculations - Historical cost tracking
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    calculations = db.query(DailyCostCalculation).filter(
        DailyCostCalculation.business_date >= start_date
    ).order_by(DailyCostCalculation.business_date.desc()).all()
    
    # Calculate totals
    total_gross = sum(round(float(calc.gross_payout)) for calc in calculations)
    total_net = sum(round(float(calc.net_payout)) for calc in calculations)
    total_admin = sum(round(float(calc.admin_deduction_total)) for calc in calculations)
    total_tds = sum(round(float(calc.tds_total)) for calc in calculations)
    
    return {
        "success": True,
        "period": {
            "days": days,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        },
        "totals": {
            "total_gross_payout": total_gross,
            "total_net_payout": total_net,
            "total_admin_deductions": total_admin,
            "total_tds_deductions": total_tds
        },
        "calculations": [
            {
                "business_date": calc.business_date.strftime('%Y-%m-%d'),
                "direct_referral_total": round(float(calc.direct_referral_total)),
                "matching_referral_total": round(float(calc.matching_referral_total)),
                "ved_income_total": round(float(calc.ved_income_total)),
                "guru_dakshina_total": round(float(calc.guru_dakshina_total)),
                "gross_payout": round(float(calc.gross_payout)),
                "admin_deduction_total": round(float(calc.admin_deduction_total)),
                "tds_total": round(float(calc.tds_total)),
                "net_payout": round(float(calc.net_payout)),
                "total_users_paid": calc.total_users_paid,
                "status": calc.calculation_status
            }
            for calc in calculations
        ]
    }


@router.get("/company-earnings")
async def company_earnings_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Company Earnings Report - Ceiling excess amounts by user
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    # Parse date range
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
    
    earnings = db.query(CompanyEarnings).filter(
        and_(
            CompanyEarnings.business_date >= start,
            CompanyEarnings.business_date <= end
        )
    ).order_by(CompanyEarnings.business_date.desc()).all()
    
    # Calculate totals
    total_excess = sum(round(float(e.excess_amount)) for e in earnings)
    total_net_earnings = sum(round(float(e.net_company_earnings)) for e in earnings)
    
    return {
        "success": True,
        "period": {
            "start_date": start.strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d')
        },
        "totals": {
            "total_excess_amount": total_excess,
            "total_net_company_earnings": total_net_earnings,
            "total_records": len(earnings)
        },
        "earnings": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "original_amount": round(float(e.original_amount)),
                "excess_amount": round(float(e.excess_amount)),
                "admin_deduction": round(float(e.admin_deduction)),
                "tds_deduction": round(float(e.tds_deduction)),
                "net_company_earnings": round(float(e.net_company_earnings)),
                "income_type": e.income_type,
                "ceiling_limit": float(e.ceiling_limit_applied),
                "business_date": e.business_date.strftime('%Y-%m-%d')
            }
            for e in earnings
        ]
    }


@router.get("/consolidated-report")
async def consolidated_income_report(
    user_id: Optional[str] = None,
    income_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Consolidated Income Report - System-wide income tracking
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    # Parse date range
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
    
    query = db.query(PendingIncome).filter(
        and_(
            PendingIncome.business_date >= start,
            PendingIncome.business_date <= end
        )
    )
    
    if user_id:
        query = query.filter(PendingIncome.user_id == user_id)
    
    if income_type:
        query = query.filter(PendingIncome.income_type == income_type)
    
    if status:
        query = query.filter(PendingIncome.verification_status == status)
    
    incomes = query.order_by(PendingIncome.business_date.desc()).all()
    
    # Calculate totals
    total_gross = sum(round(float(i.gross_amount)) for i in incomes)
    total_admin = sum(round(float(i.admin_deduction)) for i in incomes)
    total_tds = sum(round(float(i.tds_deduction)) for i in incomes)
    total_net = sum(round(float(i.net_amount)) for i in incomes)
    
    # Group by income type
    by_type = {}
    for income in incomes:
        if income.income_type not in by_type:
            by_type[income.income_type] = {
                'count': 0,
                'gross': 0,
                'net': 0
            }
        by_type[income.income_type]['count'] += 1
        by_type[income.income_type]['gross'] += round(float(income.gross_amount))
        by_type[income.income_type]['net'] += round(float(income.net_amount))
    
    return {
        "success": True,
        "period": {
            "start_date": start.strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d')
        },
        "totals": {
            "total_gross": total_gross,
            "total_admin_deductions": total_admin,
            "total_tds_deductions": total_tds,
            "total_net_payout": total_net,
            "total_records": len(incomes)
        },
        "by_income_type": by_type,
        "incomes": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "income_type": i.income_type,
                "gross_amount": round(float(i.gross_amount)),
                "admin_deduction": round(float(i.admin_deduction)),
                "tds_deduction": round(float(i.tds_deduction)),
                "net_amount": round(float(i.net_amount)),
                "verification_status": i.verification_status,
                "business_date": i.business_date.strftime('%Y-%m-%d')
            }
            for i in incomes
        ]
    }


@router.get("/transaction-history")
async def transaction_history(
    user_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transaction History - Detailed transaction records
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    _require_staff(current_user)
    
    query = db.query(Transaction)
    
    if user_id:
        query = query.filter(
            or_(
                Transaction.referrer_id == user_id,
                Transaction.referred_user_id == user_id
            )
        )
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(
            and_(
                Transaction.timestamp >= start,
                Transaction.timestamp <= end
            )
        )
    
    transactions = query.order_by(Transaction.timestamp.desc()).limit(limit).all()
    
    return {
        "success": True,
        "total_records": len(transactions),
        "transactions": [
            {
                "id": t.id,
                "referrer_id": t.referrer_id,
                "referred_user_id": t.referred_user_id,
                "amount": round(float(t.amount)),
                "transaction_type": t.transaction_type,
                "timestamp": t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "referral_type": t.referral_type,
                "referral_id": t.referral_id
            }
            for t in transactions
        ]
    }
