"""
Finance Admin Endpoints - Financial Operations & Reporting
Handles TDS management, payout processing, cost calculations, revenue analysis
"""

from typing import Optional
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from decimal import Decimal
from app.core.constants import TDS_DEDUCTION_RATE
import io
import csv

from app.core.database import get_db
from app.core.rbac import require_finance_admin_hybrid
from app.models.user import User
from app.models.transaction import Transaction
from app.models.coupon import PINPurchaseRequest
from app.models.base import get_indian_time
from app.models.api_response import success_response
from app.core.audit import AuditLogger

router = APIRouter()

# ===== DAILY COST CALCULATIONS =====

@router.get("/finance/cost-calculations/daily")
async def get_daily_cost_calculation(
    calculation_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get daily cost calculation"""
    try:
        if calculation_date:
            target_date = datetime.fromisoformat(calculation_date).date()
        else:
            target_date = get_indian_time().date()
        
        # Calculate pending costs for the day
        cost_breakdown = {
            "calculation_date": target_date.isoformat(),
            "direct_awards": {"cost": 0.0, "count": 0},
            "matching_awards": {"cost": 0.0, "count": 0},
            "bonanza_rewards": {"cost": 0.0, "count": 0},
            "field_allowances": {"cost": 0.0, "recipients": 0},
            "car_allowances": {"cost": 0.0, "recipients": 0},
            "total_pending_cost": 0.0
        }
        
        # Get field allowance recipients
        field_allowance_users = db.query(User).filter(
            User.activation_date.isnot(None),
            User.field_allowance_eligible == True
        ).count()
        
        cost_breakdown["field_allowances"] = {
            "cost": field_allowance_users * 10000,  # ₹10,000 per user
            "recipients": field_allowance_users
        }
        
        cost_breakdown["total_pending_cost"] = sum([
            cost_breakdown["direct_awards"]["cost"],
            cost_breakdown["matching_awards"]["cost"],
            cost_breakdown["bonanza_rewards"]["cost"],
            cost_breakdown["field_allowances"]["cost"],
            cost_breakdown["car_allowances"]["cost"]
        ])
        
        return success_response(
            message="Daily cost calculation retrieved successfully",
            data=cost_breakdown
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== COMPANY REVENUE CALCULATION =====

@router.get("/finance/revenue/calculate")
async def calculate_company_revenue(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    days: int = Query(30, description="Number of days if dates not specified"),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Calculate company revenue for specified period"""
    try:
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = get_indian_time()
            start_dt = end_dt - timedelta(days=days)
        
        # Calculate total received (coupons, PINs)
        total_coupons = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Coupon Purchase',
                Transaction.timestamp.between(start_dt, end_dt)
            )
        ).scalar() or 0
        
        # Calculate total payouts
        total_payouts = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance', 'Withdrawal'
                ]),
                Transaction.timestamp.between(start_dt, end_dt)
            )
        ).scalar() or 0
        
        # Calculate TDS (2% of payouts)
        tds_rate = 0.02
        payable_tds = round(float(total_payouts)) * tds_rate
        
        # Calculate net revenue
        net_revenue = round(float(total_coupons)) - round(float(total_payouts)) - payable_tds
        
        revenue_data = {
            "calculation_period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "days": (end_dt - start_dt).days
            },
            "total_received": round(float(total_coupons)),
            "total_payouts": round(float(total_payouts)),
            "payable_tds": payable_tds,
            "net_revenue": net_revenue,
            "details": {
                "received": {
                    "coupon_purchases": round(float(total_coupons))
                },
                "payouts": {
                    "total_earnings": round(float(total_payouts))
                },
                "tds": {
                    "rate": tds_rate,
                    "amount": payable_tds
                }
            }
        }
        
        return success_response(
            message="Company revenue calculated successfully",
            data=revenue_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== COST TREND ANALYSIS =====

@router.get("/finance/cost-trend")
async def get_cost_trend(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get cost trend analysis"""
    try:
        end_date = get_indian_time()
        start_date = end_date - timedelta(days=days)
        
        # Calculate daily costs for the period
        daily_costs = []
        current_date = start_date.date()
        
        while current_date <= end_date.date():
            daily_total = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.transaction_type.in_([
                        'Direct Referral', 'Matching Referral', 'Ved',
                        'Guru Dakshina', 'Field Allowance'
                    ]),
                    func.date(Transaction.timestamp) == current_date
                )
            ).scalar() or 0
            
            daily_costs.append({
                "date": current_date.isoformat(),
                "total_cost": round(float(daily_total))
            })
            
            current_date += timedelta(days=1)
        
        # Calculate summary
        total_costs = [cost["total_cost"] for cost in daily_costs if cost["total_cost"] > 0]
        
        trend_data = {
            "period_days": days,
            "calculations_count": len(daily_costs),
            "trend_data": daily_costs,
            "summary": {
                "total_cost_range": {
                    "min": min(total_costs) if total_costs else 0,
                    "max": max(total_costs) if total_costs else 0,
                    "average": sum(total_costs) / len(total_costs) if total_costs else 0
                }
            }
        }
        
        return success_response(
            message="Cost trend analysis retrieved successfully",
            data=trend_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== TDS MANAGEMENT =====

@router.get("/finance/tds/summary")
async def get_tds_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get TDS summary for specified period"""
    try:
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = get_indian_time()
            start_dt = end_dt - timedelta(days=30)
        
        # Calculate total earnings subject to TDS
        total_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance'
                ]),
                Transaction.timestamp.between(start_dt, end_dt)
            )
        ).scalar() or 0
        
        # TDS rate: 2%
        tds_rate = 0.02
        total_tds = round(float(total_earnings)) * tds_rate
        
        tds_summary = {
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            },
            "total_earnings": round(float(total_earnings)),
            "tds_rate": tds_rate,
            "total_tds": total_tds,
            "net_payable": round(float(total_earnings)) - total_tds
        }
        
        return success_response(
            message="TDS summary retrieved successfully",
            data=tds_summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== PAYOUT PROCESSING =====

class ProcessPayoutRequest(BaseModel):
    user_ids: list[str]
    payout_date: Optional[str] = None

@router.post("/finance/payout/process")
async def process_payout(
    payout_data: ProcessPayoutRequest,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Process payout for selected users"""
    try:
        payout_date = datetime.fromisoformat(payout_data.payout_date) if payout_data.payout_date else get_indian_time()
        
        processed_count = 0
        total_amount = 0.0
        failed_users = []
        
        for user_id in payout_data.user_ids:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.wallet_balance > 0:
                    # Create payout transaction
                    payout_amount = round(float(user.wallet_balance))
                    
                    transaction = Transaction(
                        user_id=user_id,
                        transaction_type='Payout',
                        amount=Decimal(str(payout_amount)),
                        description=f'Payout processed by Finance Admin',
                        timestamp=payout_date
                    )
                    db.add(transaction)
                    
                    # Update user wallet
                    user.wallet_balance = Decimal('0.0')
                    user.released_total = (user.released_total or Decimal('0.0')) + Decimal(str(payout_amount))
                    
                    processed_count += 1
                    total_amount += payout_amount
                else:
                    failed_users.append({"user_id": user_id, "reason": "No balance or user not found"})
            except Exception as e:
                failed_users.append({"user_id": user_id, "reason": str(e)})
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='PAYOUT_PROCESSING',
            resource_type='Transaction',
            details={
                "processed_count": processed_count,
                "total_amount": total_amount,
                "failed_count": len(failed_users)
            }
        )
        
        return success_response(
            message=f"Payout processing completed: {processed_count} users processed",
            data={
                "processed_count": processed_count,
                "total_amount": total_amount,
                "failed_count": len(failed_users),
                "failed_users": failed_users
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== PIN PURCHASE CSV EXPORT =====

@router.get("/finance/pin-general.csv")
async def export_pin_general_csv(
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Export all PIN purchase requests to CSV for finance admin"""
    try:
        # Get all PIN purchase requests
        requests = db.query(PINPurchaseRequest).join(
            User, PINPurchaseRequest.user_id == User.id
        ).order_by(PINPurchaseRequest.request_date.desc()).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Request ID', 'User ID', 'User Name', 'User Email', 
            'Package Type', 'Quantity', 'Total Amount', 'Transaction ID',
            'Status', 'Request Date', 'Super Admin Approved By', 
            'Super Admin Approved Date', 'Finance Validated By', 
            'Finance Validated Date', 'Rejection Reason'
        ])
        
        # Write data rows
        for req in requests:
            user = db.query(User).filter(User.id == req.user_id).first()
            
            total_amount_val = req.total_amount
            writer.writerow([
                req.id,
                req.user_id,
                user.name if user else 'Unknown',
                user.email if user else 'Unknown',
                req.package_type or '',
                req.quantity or 0,
                round(float(total_amount_val)) if total_amount_val is not None else 0.0,
                req.transaction_id or '',
                req.status or '',
                req.request_date.isoformat() if req.request_date is not None else '',
                req.superadmin_approved_by or '',
                req.superadmin_approved_date.isoformat() if req.superadmin_approved_date is not None else '',
                req.finance_validated_by or '',
                req.finance_validated_date.isoformat() if req.finance_validated_date is not None else '',
                req.rejection_reason or ''
            ])
        
        # Prepare response
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pin_purchase_requests.csv"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )

# ===== FINANCIAL DASHBOARD =====

@router.get("/finance/dashboard", response_class=HTMLResponse)
async def get_finance_dashboard(
    request: Request,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Finance Admin Dashboard - Main HTML page"""
    
    
    try:
        today = get_indian_time().date()
        month_start = today.replace(day=1)
        
        # Today's stats
        today_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                func.date(Transaction.timestamp) == today,
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance'
                ])
            )
        ).scalar() or 0
        
        # Month stats
        month_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.timestamp >= month_start,
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance'
                ])
            )
        ).scalar() or 0
        
        # Wallet stats
        total_wallet_balance = db.query(func.sum(User.wallet_balance)).filter(
            User.activation_date.isnot(None)
        ).scalar() or 0
        
        # Pending withdrawals
        pending_withdrawals = db.query(Transaction).filter(
            and_(
                Transaction.transaction_type == 'Withdrawal',
                Transaction.status == 'Pending'
            )
        ).count()
        
        dashboard_data = {
            "earnings": {
                "today": round(float(today_earnings)),
                "this_month": round(float(month_earnings))
            },
            "wallets": {
                "total_balance": round(float(total_wallet_balance)),
                "pending_withdrawals": pending_withdrawals
            },
            "tds": {
                "month_tds": round(float(month_earnings)) * float(TDS_DEDUCTION_RATE)
            }
        }
        
        # Frontend-only route - redirect to frontend
        from fastapi.responses import HTMLResponse
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Finance Admin Dashboard - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/finance-admin/dashboard">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/finance-admin/dashboard">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/finance-admin/dashboard-stats")
async def get_finance_admin_dashboard_stats(
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    Finance Admin Dashboard - DC Protocol Compliant
    Shows: User stats, pending income payments, procurement queue (SA-approved awards)
    """
    try:
        from sqlalchemy import func, and_, desc, or_, case
        from datetime import datetime
        from app.models.awards import UserAwardProgress
        from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
        from app.models.withdrawal import WithdrawalRequest
        from app.models.transaction import Transaction
        
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        
        # User Statistics - DC Protocol: Single source = user table
        # OPTIMIZED: Single query with conditional aggregation instead of 5 separate queries
        user_stats_query = db.query(
            func.count(User.id).label('total_users'),
            func.count(case((User.account_status == 'Active', 1))).label('active_users'),
            func.count(case((User.account_status == 'Inactive', 1))).label('inactive_users'),
            func.count(case((and_(User.registration_date >= today_start, User.registration_date <= today_end), 1))).label('users_today'),
            func.count(case((User.registration_date >= month_start, 1))).label('users_this_month')
        ).first()
        
        total_users = user_stats_query.total_users or 0
        active_users = user_stats_query.active_users or 0
        inactive_users = user_stats_query.inactive_users or 0
        users_today = user_stats_query.users_today or 0
        users_this_month = user_stats_query.users_this_month or 0
        
        # Total Income Earned - DC Protocol: All income transactions
        # Production date filter: October 1, 2025
        production_start = datetime(2025, 10, 1)
        income_types = ['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance']
        
        # Note: Transactions represent earned income (no "pending" status on transactions)
        # Pending payouts are tracked via withdrawal_request table
        total_income_amount = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_(income_types),
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        
        income_transaction_count = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.transaction_type.in_(income_types),
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        
        # Procurement Queue - Awards approved by both Admin AND Super Admin, awaiting cost recording
        awards_procurement_queue = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.isnot(None),
                UserAwardProgress.super_admin_decision == 'approved',
                UserAwardProgress.finance_processed_by.is_(None)
            )
        ).scalar() or 0
        # DC Protocol: Query bonanza procurement queue from DynamicBonanzaHistory
        bonanza_procurement_queue = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.isnot(None),
                DynamicBonanzaHistory.super_admin_decision == 'approved',
                DynamicBonanzaHistory.finance_processed_by.is_(None)
            )
        ).scalar() or 0
        
        # Pending Withdrawals
        pending_withdrawals = db.query(func.count(WithdrawalRequest.id)).filter(
            WithdrawalRequest.status == 'Pending'
        ).scalar() or 0
        
        dashboard_data = {
            "user_stats": {
                "all_time": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": inactive_users
                },
                "today": {
                    "total_users": users_today,
                    "active_users": users_today
                },
                "this_month": {
                    "total_users": users_this_month,
                    "active_users": users_this_month
                }
            },
            "pending_income": {
                "amount": float(total_income_amount),
                "count": income_transaction_count
            },
            "procurement": {
                "total_queue": awards_procurement_queue + bonanza_procurement_queue,
                "awards_queue": awards_procurement_queue,
                "bonanza_queue": bonanza_procurement_queue
            },
            "withdrawals": {
                "pending": pending_withdrawals
            }
        }
        
        return success_response(
            message="Finance Admin dashboard statistics retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        import traceback
        print(f"❌ Finance Admin Dashboard Error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard statistics"
        )


# ===== COMPLIANCE MANAGEMENT ENDPOINTS =====

@router.get("/compliance/tds")
async def get_tds_records(
    page: int = Query(1, gt=0),
    limit: int = Query(50, gt=0, le=100),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tally_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get TDS records for compliance tracking"""
    try:
        # Return empty records for now (placeholder implementation with complete structure)
        return {
            "success": True,
            "message": "TDS records retrieved successfully",
            "records": [],
            "summary": {
                "total_records": 0,
                "total_tds": 0.0,
                "paid_tds": 0.0,
                "pending_tds": 0.0,
                "tally_updated_count": 0,
                "tally_pending_count": 0
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": 0,
                "total_pages": 0
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve TDS records: {str(e)}"
        )


@router.get("/compliance/gst")
async def get_gst_records(
    page: int = Query(1, gt=0),
    limit: int = Query(50, gt=0, le=100),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tally_status: Optional[str] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get GST records for compliance tracking"""
    try:
        # Return empty records for now (placeholder implementation with complete structure)
        return {
            "success": True,
            "message": "GST records retrieved successfully",
            "records": [],
            "summary": {
                "total_records": 0,
                "total_gst": 0.0,
                "paid_gst": 0.0,
                "pending_gst": 0.0,
                "tally_updated_count": 0
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": 0,
                "total_pages": 0
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve GST records: {str(e)}"
        )


@router.get("/compliance/handling")
async def get_handling_charges(
    page: int = Query(1, gt=0),
    limit: int = Query(50, gt=0, le=100),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get handling charges records for compliance tracking"""
    try:
        # Return empty records for now (placeholder implementation with complete structure)
        return {
            "success": True,
            "message": "Handling charges records retrieved successfully",
            "records": [],
            "summary": {
                "total_records": 0,
                "total_handling_charges": 0.0,
                "collected_charges": 0.0,
                "pending_charges": 0.0
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": 0,
                "total_pages": 0
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve handling charges: {str(e)}"
        )
