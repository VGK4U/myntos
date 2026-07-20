"""
Admin Earnings & Withdrawals endpoints for FastAPI
Real database operations for payout management and financial oversight
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, or_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_admin_user, get_current_user_hybrid
from app.models.user import User
from app.models.transaction import Transaction
from app.models.base import get_indian_time

router = APIRouter()

@router.get("/payout-summary")
async def get_payout_summary(
    date_range: Optional[str] = Query("month", description="Date range: today, week, month, all"),
    current_user: dict = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive payout summary with real transaction data
    """
    try:
        # Calculate date filter
        now = datetime.now()
        if date_range == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "week":
            start_date = now - timedelta(days=7)
        elif date_range == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = None
        
        # Build base query for transactions
        base_query = db.query(Transaction)
        if start_date:
            base_query = base_query.filter(Transaction.timestamp >= start_date)
        
        # Calculate overall statistics
        total_transactions = base_query.count()
        
        # Get total amounts by transaction type
        credit_amount = base_query.filter(Transaction.transaction_type.like('%Credit%')).with_entities(
            func.sum(Transaction.amount)
        ).scalar() or Decimal('0')
        
        debit_amount = base_query.filter(Transaction.transaction_type.like('%Debit%')).with_entities(
            func.sum(Transaction.amount)
        ).scalar() or Decimal('0')
        
        # Calculate today's processed amount
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_processed = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.timestamp >= today_start,
                Transaction.transaction_type.like('%Credit%')
            )
        ).scalar() or Decimal('0')
        
        today_count = db.query(func.count(Transaction.id)).filter(
            Transaction.timestamp >= today_start
        ).scalar() or 0
        
        # Get breakdown by income type
        income_types = [
            'Direct Referral',
            'Matching Referral', 
            'Ved Income',
            'Guru Dakshina'
        ]
        
        payout_breakdown = {}
        for income_type in income_types:
            count = base_query.filter(Transaction.transaction_type == income_type).count()
            amount = base_query.filter(Transaction.transaction_type == income_type).with_entities(
                func.sum(Transaction.amount)
            ).scalar() or Decimal('0')
            
            payout_breakdown[income_type.lower().replace(' ', '_')] = {
                "count": count,
                "amount": float(amount)
            }
        
        # Get monthly trend (last 6 months)
        monthly_trend = []
        for i in range(6):
            month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_count = db.query(func.count(Transaction.id)).filter(
                and_(
                    Transaction.timestamp >= month_start,
                    Transaction.timestamp <= month_end
                )
            ).scalar() or 0
            
            month_amount = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.timestamp >= month_start,
                    Transaction.timestamp <= month_end,
                    Transaction.transaction_type.like('%Credit%')
                )
            ).scalar() or Decimal('0')
            
            monthly_trend.append({
                "month": month_start.strftime("%b %Y"),
                "payouts": month_count,
                "amount": float(month_amount)
            })
        
        monthly_trend.reverse()  # Show oldest to newest
        
        # Get recent payouts
        recent_payouts = base_query.order_by(desc(Transaction.timestamp)).limit(10).all()
        recent_payouts_data = []
        
        for transaction in recent_payouts:
            # Get user details
            user = db.query(User).filter(User.id == transaction.referrer_id).first()
            
            recent_payouts_data.append({
                "id": f"PO{transaction.id:03d}",
                "user_id": transaction.referrer_id,
                "user_name": user.name if user else "Unknown",
                "income_type": transaction.transaction_type,
                "amount": float(transaction.amount),
                "status": "Processed",  # All transactions in DB are completed
                "request_date": transaction.timestamp.isoformat(),
                "processed_date": transaction.timestamp.isoformat(),
                "processor": "System"
            })
        
        summary = {
            "total_payouts": total_transactions,
            "total_amount": float(credit_amount),
            "pending_payouts": 0,  # No pending system in current model
            "pending_amount": 0,
            "processed_today": today_count,
            "processed_amount_today": float(today_processed),
            "payout_breakdown": payout_breakdown,
            "monthly_trend": monthly_trend
        }
        
        return {
            "success": True,
            "summary": summary,
            "recent_payouts": recent_payouts_data,
            "generated_at": get_indian_time().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payout summary: {str(e)}"
        )

@router.get("/balance-report")
async def get_balance_report(
    search: Optional[str] = Query(None, description="Search users by name, ID, or email"),
    balance_range: Optional[str] = Query(None, description="Filter by balance range"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive balance report for all users with real wallet data
    """
    try:
        # Build user query with search
        user_query = db.query(User)
        if search:
            search_term = f"%{search}%"
            user_query = user_query.filter(
                or_(
                    User.name.ilike(search_term),
                    User.id.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        # Apply balance range filter
        if balance_range and balance_range != 'all':
            if balance_range == '0-1000':
                user_query = user_query.filter(User.wallet_balance <= 1000)
            elif balance_range == '1000-5000':
                user_query = user_query.filter(and_(User.wallet_balance > 1000, User.wallet_balance <= 5000))
            elif balance_range == '5000-10000':
                user_query = user_query.filter(and_(User.wallet_balance > 5000, User.wallet_balance <= 10000))
            elif balance_range == '10000-25000':
                user_query = user_query.filter(and_(User.wallet_balance > 10000, User.wallet_balance <= 25000))
            elif balance_range == '25000+':
                user_query = user_query.filter(User.wallet_balance > 25000)
        
        total_users = user_query.count()
        users = user_query.offset(offset).limit(limit).all()
        
        # Calculate user balance details
        user_balances = []
        for user in users:
            # Get user's transaction breakdown
            user_transactions = db.query(Transaction).filter(Transaction.referrer_id == user.id)
            
            # Calculate earnings by type
            direct_earnings = user_transactions.filter(Transaction.transaction_type == 'Direct Referral').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or Decimal('0')
            
            matching_earnings = user_transactions.filter(Transaction.transaction_type == 'Matching Referral').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or Decimal('0')
            
            ved_earnings = user_transactions.filter(Transaction.transaction_type == 'Ved Income').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or Decimal('0')
            
            guru_earnings = user_transactions.filter(Transaction.transaction_type == 'Guru Dakshina').with_entities(
                func.sum(Transaction.amount)
            ).scalar() or Decimal('0')
            
            total_earned = float(direct_earnings + matching_earnings + ved_earnings + guru_earnings)
            
            # Get last transaction
            last_transaction = user_transactions.order_by(desc(Transaction.timestamp)).first()
            
            # Calculate wallet breakdown (simplified for now)
            wallets = {
                "main_wallet": float(user.wallet_balance or 0),
                "referral_bonus": float(direct_earnings),
                "matching_referral": float(matching_earnings), 
                "ved_income": float(ved_earnings),
                "guru_dakshina": float(guru_earnings),
                "field_allowance": 0  # Not tracked separately in current model
            }
            
            user_balances.append({
                "user_id": user.id,
                "user_name": user.name,
                "email": user.email,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "wallets": wallets,
                "total_balance": float(user.wallet_balance or 0),
                "total_earned": total_earned,
                "total_withdrawn": 0,  # Not tracked in current model
                "pending_withdrawals": 0,  # Not tracked in current model
                "last_transaction_date": last_transaction.timestamp.isoformat() if last_transaction else None
            })
        
        # Calculate overall statistics
        total_balance = db.query(func.sum(User.wallet_balance)).scalar() or Decimal('0')
        total_earned_lifetime = db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(['Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina'])
        ).scalar() or Decimal('0')
        
        active_users = db.query(func.count(User.id)).filter(User.wallet_balance > 0).scalar() or 0
        
        # Balance distribution
        distribution = {
            '0-1000': db.query(func.count(User.id)).filter(User.wallet_balance <= 1000).scalar() or 0,
            '1000-5000': db.query(func.count(User.id)).filter(and_(User.wallet_balance > 1000, User.wallet_balance <= 5000)).scalar() or 0,
            '5000-10000': db.query(func.count(User.id)).filter(and_(User.wallet_balance > 5000, User.wallet_balance <= 10000)).scalar() or 0,
            '10000-25000': db.query(func.count(User.id)).filter(and_(User.wallet_balance > 10000, User.wallet_balance <= 25000)).scalar() or 0,
            '25000+': db.query(func.count(User.id)).filter(User.wallet_balance > 25000).scalar() or 0
        }
        
        overview = {
            "total_users": total_users,
            "total_balance_in_system": float(total_balance),
            "total_pending_withdrawals": 0,  # Not implemented
            "total_earned_lifetime": float(total_earned_lifetime),
            "total_withdrawn_lifetime": 0,  # Not implemented
            "active_earners": active_users,
            "balance_distribution": distribution
        }
        
        return {
            "success": True,
            "users": user_balances,
            "overview": overview,
            "pagination": {
                "total": total_users,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_users
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch balance report: {str(e)}"
        )

@router.get("/wallet-transactions")
async def get_wallet_transactions(
    search: Optional[str] = Query(None, description="Search transactions"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: credit, debit"),
    income_type: Optional[str] = Query(None, description="Filter by income type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed wallet transaction history with real data
    """
    try:
        # Build transaction query
        transaction_query = db.query(Transaction).join(User, Transaction.referrer_id == User.id)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            transaction_query = transaction_query.filter(
                or_(
                    User.name.ilike(search_term),
                    User.id.ilike(search_term),
                    Transaction.transaction_type.ilike(search_term)
                )
            )
        
        if income_type and income_type != 'all':
            transaction_query = transaction_query.filter(Transaction.transaction_type == income_type)
        
        total_transactions = transaction_query.count()
        transactions = transaction_query.order_by(desc(Transaction.timestamp)).offset(offset).limit(limit).all()
        
        # Format transaction data
        transactions_data = []
        for transaction in transactions:
            user = db.query(User).filter(User.id == transaction.referrer_id).first()
            related_user = db.query(User).filter(User.id == transaction.referred_user_id).first()
            
            # Determine transaction direction
            transaction_direction = 'credit'  # Most Reference System transactions are credits
            
            transactions_data.append({
                "id": f"WTX{transaction.id:03d}",
                "user_id": transaction.referrer_id,
                "user_name": user.name if user else "Unknown",
                "transaction_type": transaction_direction,
                "wallet_type": transaction.transaction_type.lower().replace(' ', '_'),
                "amount": float(transaction.amount),
                "balance_before": 0,  # Not tracked in current model
                "balance_after": float(user.wallet_balance) if user else 0,
                "description": f"{transaction.transaction_type} - {float(transaction.amount)}",
                "reference_id": transaction.referral_id,
                "related_user_id": transaction.referred_user_id,
                "related_user_name": related_user.name if related_user else None,
                "created_at": transaction.timestamp.isoformat(),
                "status": "completed"
            })
        
        # Calculate summary statistics
        total_credits = db.query(func.sum(Transaction.amount)).scalar() or Decimal('0')
        total_debits = Decimal('0')  # Not tracked separately in current model
        net_flow = total_credits - total_debits
        
        # Today's activity
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        transactions_today = db.query(func.count(Transaction.id)).filter(
            Transaction.timestamp >= today
        ).scalar() or 0
        
        volume_today = db.query(func.sum(Transaction.amount)).filter(
            Transaction.timestamp >= today
        ).scalar() or Decimal('0')
        
        # Wallet-wise volume (by transaction type)
        wallet_volume = {}
        income_types = ['Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina']
        
        for income_type in income_types:
            volume = db.query(func.sum(Transaction.amount)).filter(
                Transaction.transaction_type == income_type
            ).scalar() or Decimal('0')
            
            wallet_key = income_type.lower().replace(' ', '_')
            wallet_volume[wallet_key] = float(volume)
        
        # Add main wallet (total of all)
        wallet_volume['main_wallet'] = float(total_credits)
        wallet_volume['field_allowance'] = 0  # Not implemented yet
        
        summary = {
            "total_transactions": total_transactions,
            "total_credits": float(total_credits),
            "total_debits": float(total_debits),
            "net_flow": float(net_flow),
            "transactions_today": transactions_today,
            "volume_today": float(volume_today),
            "wallet_wise_volume": wallet_volume
        }
        
        return {
            "success": True,
            "transactions": transactions_data,
            "summary": summary,
            "pagination": {
                "total": total_transactions,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_transactions
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch wallet transactions: {str(e)}"
        )