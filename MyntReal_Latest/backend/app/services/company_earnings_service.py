"""
Company Earnings Service - DC Protocol Compliant
Single source of truth for all revenue, payout, and expense tracking
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, cast, Date
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any
from app.models.transaction import CompanyEarnings, PendingIncome, Expense, TDSPayable
from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier
from app.models.bonanza import DynamicBonanzaHistory, DynamicBonanzaReward  # DC Protocol: BonanzaProgress deprecated
from app.models.field_allowance import FieldAllowanceEligibility
from app.models.training_claim import TrainingClaim


class CompanyEarningsService:
    """
    DC Protocol compliant service for company earnings tracking
    Integrates all revenue and expense sources from single source tables
    """
    
    @staticmethod
    def get_handling_charges_revenue(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        user_id: Optional[str] = None,
        collection_status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        TAB 1: Get handling charges + GST revenue from company_earnings
        DC Protocol: Single source of truth for handling charges
        """
        # Base query
        query = db.query(
            CompanyEarnings.id,
            CompanyEarnings.user_id,
            User.name.label('user_name'),
            CompanyEarnings.description,
            CompanyEarnings.net_company_earnings.label('total_amount'),
            CompanyEarnings.ceiling_date.label('transaction_date'),
            CompanyEarnings.collection_status,
            CompanyEarnings.collection_updated_at,
            CompanyEarnings.collection_updated_by_id,
            CompanyEarnings.tally_status,
            CompanyEarnings.income_type
        ).join(
            User, CompanyEarnings.user_id == User.id
        ).filter(
            or_(
                CompanyEarnings.description.ilike('%Handling%'),
                CompanyEarnings.description.ilike('%GST%')
            )
        )
        
        # Apply filters
        if from_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            query = query.filter(CompanyEarnings.user_id == user_id)
        if collection_status:
            query = query.filter(CompanyEarnings.collection_status == collection_status)
        
        # Get total count
        total_records = query.count()
        
        # Apply pagination
        query = query.order_by(CompanyEarnings.ceiling_date.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        
        records = query.all()
        
        # Calculate summary
        summary_query = db.query(
            func.count(CompanyEarnings.id).label('total_records'),
            func.sum(CompanyEarnings.net_company_earnings).label('total_amount'),
            func.sum(
                case(
                    (CompanyEarnings.collection_status == 'COLLECTED', CompanyEarnings.net_company_earnings),
                    else_=0
                )
            ).label('collected_amount'),
            func.sum(
                case(
                    (CompanyEarnings.collection_status == 'PENDING', CompanyEarnings.net_company_earnings),
                    else_=0
                )
            ).label('pending_amount')
        ).filter(
            or_(
                CompanyEarnings.description.ilike('%Handling%'),
                CompanyEarnings.description.ilike('%GST%')
            )
        )
        
        if from_date:
            summary_query = summary_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            summary_query = summary_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            summary_query = summary_query.filter(CompanyEarnings.user_id == user_id)
        
        summary = summary_query.first()
        
        return {
            "success": True,
            "records": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "user_name": r.user_name,
                    "description": r.description,
                    "total_amount": float(r.total_amount or 0),
                    "transaction_date": r.transaction_date.isoformat() if r.transaction_date else None,
                    "collection_status": r.collection_status,
                    "collection_date": r.collection_updated_at.isoformat() if r.collection_updated_at else None,
                    "tally_status": r.tally_status,
                    "income_type": r.income_type
                }
                for r in records
            ],
            "summary": {
                "total_records": summary.total_records or 0,
                "total_amount": float(summary.total_amount or 0),
                "collected_amount": float(summary.collected_amount or 0),
                "pending_amount": float(summary.pending_amount or 0)
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit
            }
        }
    
    @staticmethod
    def get_revenue_summary(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        TAB 2: Summary Cards - Overall revenue, payouts, expenses, profit
        DC Protocol: Calculate from source tables
        """
        # 1. REVENUE IN - Package Sales
        package_revenue_query = db.query(
            func.count(User.id).label('total_users'),
            func.sum(
                case(
                    (User.package_points == 1.0, 15000),
                    (User.package_points == 0.5, 7500),
                    (User.package_points == 0.05, 1000),
                    (User.package_points == 0.025, 500),
                    else_=0
                )
            ).label('total_revenue')
        ).filter(
            User.package_points.isnot(None),
            User.package_points > 0
        )
        
        if from_date or to_date:
            package_revenue_query = package_revenue_query.filter(User.activation_date.isnot(None))
            if from_date:
                package_revenue_query = package_revenue_query.filter(func.date(User.activation_date) >= from_date)
            if to_date:
                package_revenue_query = package_revenue_query.filter(func.date(User.activation_date) <= to_date)
        
        package_data = package_revenue_query.first()
        package_revenue = float(package_data.total_revenue or 0)
        
        # 2. REVENUE IN - ALL Company Earnings (Handling Charges + Ceiling Excess)
        # DC Protocol: No filter, ALL company earnings are revenue
        handling_query = db.query(
            func.sum(CompanyEarnings.net_company_earnings).label('total_handling')
        )
        
        if from_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        
        handling_revenue = float(handling_query.scalar() or 0)
        
        # 3. REVENUE IN - Admin Fee 8% (Company keeps this)
        admin_fee_query = db.query(
            func.sum(PendingIncome.admin_deduction).label('admin_fee')
        )
        
        if from_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        admin_fee_revenue = float(admin_fee_query.scalar() or 0)
        
        # 4. PAYOUTS - Income Distributed
        payout_query = db.query(
            func.sum(PendingIncome.net_amount).label('paid'),
            func.sum(
                case(
                    (PendingIncome.verification_status == 'Completed', PendingIncome.net_amount),
                    else_=0
                )
            ).label('paid_completed'),
            func.sum(
                case(
                    (PendingIncome.verification_status != 'Completed', PendingIncome.net_amount),
                    else_=0
                )
            ).label('pending_payout')
        )
        
        if from_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        payout_data = payout_query.first()
        
        # 5. GURU DAKSHINA EXPENSE (2% paid to referrers) - DC Protocol
        guru_dakshina_query = db.query(
            func.sum(
                case(
                    (PendingIncome.verification_status == 'Completed', PendingIncome.gurudakshina_deduction),
                    else_=0
                )
            ).label('guru_dakshina_paid'),
            func.sum(
                case(
                    (PendingIncome.verification_status != 'Completed', PendingIncome.gurudakshina_deduction),
                    else_=0
                )
            ).label('guru_dakshina_pending')
        )
        
        if from_date:
            guru_dakshina_query = guru_dakshina_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            guru_dakshina_query = guru_dakshina_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        guru_dakshina_data = guru_dakshina_query.first()
        
        # 6. TDS EXPENSE (Paid to Government) - DC Protocol
        tds_query = db.query(
            func.sum(
                case(
                    (TDSPayable.payment_status == 'Paid', TDSPayable.tds_amount),
                    else_=0
                )
            ).label('tds_paid'),
            func.sum(
                case(
                    (TDSPayable.payment_status == 'Pending', TDSPayable.tds_amount),
                    else_=0
                )
            ).label('tds_pending')
        )
        
        if from_date:
            tds_query = tds_query.filter(func.date(TDSPayable.business_date) >= from_date)
        if to_date:
            tds_query = tds_query.filter(func.date(TDSPayable.business_date) <= to_date)
        
        tds_data = tds_query.first()
        
        # 7. EXPENSES - All operational expenses
        expense_query = db.query(
            func.sum(
                case(
                    (Expense.status == 'approved', Expense.amount),
                    else_=0
                )
            ).label('paid_expenses'),
            func.sum(
                case(
                    (Expense.status == 'pending', Expense.amount),
                    else_=0
                )
            ).label('pending_expenses')
        ).filter(
            Expense.is_deleted == False
        )
        
        if from_date:
            expense_query = expense_query.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            expense_query = expense_query.filter(func.date(Expense.expense_date) <= to_date)
        
        expense_data = expense_query.first()
        
        # 6. TDS PAYABLE (Pending government payment)
        tds_payable_query = db.query(
            func.sum(PendingIncome.tds_deduction).label('total_tds_payable')
        ).filter(
            PendingIncome.payment_status != 'PAID'
        )
        
        if from_date:
            tds_payable_query = tds_payable_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            tds_payable_query = tds_payable_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        tds_payable = float(tds_payable_query.scalar() or 0)
        
        # 7. FIELD ALLOWANCE - Pending payments
        field_allowance_query = db.query(
            func.sum(FieldAllowanceEligibility.total_value - func.coalesce(FieldAllowanceEligibility.total_paid_to_date, 0)).label('pending_field_allowance')
        ).filter(
            FieldAllowanceEligibility.overall_status == 'Active'
        )
        
        field_allowance_pending = float(field_allowance_query.scalar() or 0)
        
        # 8. TRAINING CLAIMS - Pending
        training_pending_query = db.query(
            func.sum(TrainingClaim.discount_amount + func.coalesce(TrainingClaim.bonus_amount, 0)).label('pending_training')
        ).filter(
            TrainingClaim.claim_status.notin_(['Paid', 'Rejected'])
        )
        
        training_pending = float(training_pending_query.scalar() or 0)
        
        # 9. AWARDS (PAID) - Actual cost from finance-processed awards (DC Protocol)
        awards_paid_query = db.query(
            func.sum(
                func.coalesce(UserAwardProgress.actual_cost_paid, 0) + 
                func.coalesce(UserMatchingAwardProgress.actual_cost_paid, 0)
            ).label('total_awards_paid')
        ).outerjoin(
            UserMatchingAwardProgress, UserAwardProgress.id == UserMatchingAwardProgress.id
        ).filter(
            or_(
                UserAwardProgress.payment_status == 'released',
                UserMatchingAwardProgress.payment_status == 'released'
            )
        )
        
        awards_paid = float(awards_paid_query.scalar() or 0)
        
        # 10. AWARDS (PENDING) - Won but not finance processed yet (DC Protocol)
        # Use budgeted_amount from user_award_progress table (actual commitment)
        awards_pending_direct = db.query(
            func.sum(UserAwardProgress.budgeted_amount).label('pending_cost')
        ).filter(
            UserAwardProgress.processed_status.in_(['Pending', 'Admin Approved', 'Procurement Pending']),
            UserAwardProgress.payment_status != 'released'
        ).scalar()
        
        awards_pending_matching = db.query(
            func.sum(UserMatchingAwardProgress.budgeted_amount).label('pending_cost')
        ).filter(
            UserMatchingAwardProgress.processed_status.in_(['Pending', 'Admin Approved', 'Procurement Pending']),
            UserMatchingAwardProgress.payment_status != 'released'
        ).scalar()
        
        awards_pending = float(awards_pending_direct or 0) + float(awards_pending_matching or 0)
        
        # 11. BONANZA (PAID) - From expense table (DC Protocol)
        bonanza_paid_query = db.query(
            func.sum(Expense.amount).label('bonanza_paid')
        ).filter(
            Expense.category == 'Cash',
            Expense.status == 'approved',
            Expense.is_deleted == False
        )
        
        if from_date:
            bonanza_paid_query = bonanza_paid_query.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            bonanza_paid_query = bonanza_paid_query.filter(func.date(Expense.expense_date) <= to_date)
        
        bonanza_paid = float(bonanza_paid_query.scalar() or 0)
        
        # 12. BONANZA (PENDING) - Claimed but not paid (DC Protocol)
        # DC Protocol: Query DynamicBonanzaHistory (single source of truth)
        bonanza_pending_query = db.query(
            func.sum(func.coalesce(DynamicBonanzaHistory.budgeted_amount, 0)).label('pending_bonanza')
        ).filter(
            DynamicBonanzaHistory.processed_status.in_(['Pending Approval', 'Admin Approved', 'Procurement Pending']),
            DynamicBonanzaHistory.payment_status != 'released'
        )
        
        bonanza_pending = float(bonanza_pending_query.scalar() or 0)
        
        # Calculate totals (DC Protocol: Include ALL revenue and expense sources)
        # REVENUE = Package Sales + Company Earnings (Handling/Ceiling) + Admin Fee 8%
        total_revenue = package_revenue + handling_revenue + admin_fee_revenue
        
        # PAYOUTS = Net income to users (includes Guru Dakshina as it's paid to users)
        total_paid_out = float(payout_data.paid_completed or 0)
        total_pending_payout = float(payout_data.pending_payout or 0)
        guru_dakshina_paid = float(guru_dakshina_data.guru_dakshina_paid or 0)
        guru_dakshina_pending = float(guru_dakshina_data.guru_dakshina_pending or 0)
        
        # EXPENSES = TDS (to govt) + Awards + Bonanza + Field + Training + Ops
        tds_paid = float(tds_data.tds_paid or 0)
        tds_pending = float(tds_data.tds_pending or 0)
        
        total_paid_expenses = (
            float(expense_data.paid_expenses or 0) + 
            awards_paid + 
            bonanza_paid + 
            tds_paid
        )
        total_pending_expenses = (
            float(expense_data.pending_expenses or 0) + 
            tds_pending + 
            field_allowance_pending + 
            training_pending +
            awards_pending +
            bonanza_pending
        )
        
        # Net profit = Revenue - Payouts - Expenses
        net_profit = total_revenue - total_paid_out - total_paid_expenses - total_pending_payout - total_pending_expenses
        
        return {
            "success": True,
            "data": {
                "total_revenue": total_revenue,
                "package_sales": package_revenue,
                "company_earnings_total": handling_revenue,
                "admin_fee_revenue": admin_fee_revenue,
                "total_payouts_paid": total_paid_out,
                "total_payouts_pending": total_pending_payout,
                "total_expenses": total_paid_expenses + total_pending_expenses,
                "expenses_paid": total_paid_expenses,
                "expenses_pending": total_pending_expenses,
                "guru_dakshina_paid": guru_dakshina_paid,
                "guru_dakshina_pending": guru_dakshina_pending,
                "tds_paid": tds_paid,
                "tds_pending": tds_pending,
                "field_allowance_pending": field_allowance_pending,
                "training_pending": training_pending,
                "awards_paid": awards_paid,
                "awards_pending": awards_pending,
                "bonanza_paid": bonanza_paid,
                "bonanza_pending": bonanza_pending,
                "net_profit": net_profit
            }
        }
    
    @staticmethod
    def get_revenue_details(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        TAB 2 - SUB-TAB 1: Revenue In (Package Sales + Handling Charges)
        Individual rows per source type per date
        """
        # Package activations - date-wise
        package_query = db.query(
            cast(User.activation_date, Date).label('transaction_date'),
            func.count(User.id).label('count'),
            func.sum(
                case(
                    (User.package_points == 1.0, 15000),
                    (User.package_points == 0.5, 7500),
                    (User.package_points == 0.05, 1000),
                    (User.package_points == 0.025, 500),
                    else_=0
                )
            ).label('amount')
        ).filter(
            User.activation_date.isnot(None),
            User.package_points.isnot(None),
            User.package_points > 0
        )
        
        if from_date:
            package_query = package_query.filter(func.date(User.activation_date) >= from_date)
        if to_date:
            package_query = package_query.filter(func.date(User.activation_date) <= to_date)
        
        package_query = package_query.group_by(cast(User.activation_date, Date))
        
        # ALL Company Earnings - date-wise (DC Protocol: No filter, ALL earnings count as revenue)
        handling_query = db.query(
            cast(CompanyEarnings.ceiling_date, Date).label('transaction_date'),
            func.count(CompanyEarnings.id).label('count'),
            func.sum(CompanyEarnings.net_company_earnings).label('amount')
        )
        
        if from_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        
        handling_query = handling_query.group_by(cast(CompanyEarnings.ceiling_date, Date))
        
        # Combine results into individual rows
        package_results = package_query.all()
        handling_results = handling_query.all()
        
        # Build individual records (one row per source per date)
        records = []
        
        for row in package_results:
            if row.amount and row.amount > 0:
                records.append({
                    'transaction_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                    'source': 'Package Sales',
                    'category': 'Package Activation',
                    'count': row.count or 0,
                    'amount': float(row.amount or 0)
                })
        
        for row in handling_results:
            if row.amount and row.amount > 0:
                records.append({
                    'transaction_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                    'source': 'Company Earnings',
                    'category': 'Ceiling Income',
                    'count': row.count or 0,
                    'amount': float(row.amount or 0)
                })
        
        # Sort by date descending
        records = sorted(records, key=lambda x: x['transaction_date'], reverse=True)
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate totals
        total_package = sum(r['amount'] for r in records if r['source'] == 'Package Sales')
        total_handling = sum(r['amount'] for r in records if r['source'] == 'Company Earnings')
        
        # Count transactions per source
        count_package = sum(r['count'] for r in records if r['source'] == 'Package Sales')
        count_handling = sum(r['count'] for r in records if r['source'] == 'Company Earnings')
        
        # Calculate admin fee revenue (8% deduction) with same date filters
        admin_fee_query = db.query(
            func.sum(PendingIncome.admin_deduction).label('admin_fee'),
            func.count(PendingIncome.id).label('count')
        ).filter(
            PendingIncome.admin_deduction > 0
        )
        
        if from_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        admin_fee_result = admin_fee_query.first()
        admin_fee_revenue = float(admin_fee_result.admin_fee or 0) if admin_fee_result else 0
        count_admin_fee = admin_fee_result.count if admin_fee_result else 0
        
        # Build dynamic source breakdown
        source_breakdown = []
        
        if total_package > 0:
            source_breakdown.append({
                'source': 'package_sales',
                'amount': total_package,
                'count': count_package
            })
        
        if total_handling > 0:
            source_breakdown.append({
                'source': 'handling_revenue',
                'amount': total_handling,
                'count': count_handling
            })
        
        if admin_fee_revenue > 0:
            source_breakdown.append({
                'source': 'admin_fee',
                'amount': admin_fee_revenue,
                'count': count_admin_fee
            })
        
        return {
            "success": True,
            "data": paginated_records,
            "totals": {
                "total_package_revenue": total_package,
                "total_handling_revenue": total_handling,
                "admin_fee_revenue": admin_fee_revenue,
                "grand_total": total_package + total_handling + admin_fee_revenue,
                
                # Dynamic source breakdown (array)
                "source_breakdown": source_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }
    
    @staticmethod
    def get_payout_details(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        TAB 2 - SUB-TAB 2: Payouts (Income + TDS Payable)
        Date-wise breakdown with paid/pending status
        """
        # Income payouts - date-wise
        payout_query = db.query(
            cast(PendingIncome.business_date, Date).label('transaction_date'),
            PendingIncome.income_type,
            PendingIncome.verification_status,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.net_amount).label('net_amount'),
            func.sum(PendingIncome.tds_deduction).label('tds_amount')
        ).group_by(
            cast(PendingIncome.business_date, Date),
            PendingIncome.income_type,
            PendingIncome.verification_status
        )
        
        if from_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        payout_query = payout_query.order_by(cast(PendingIncome.business_date, Date).desc())
        
        results = payout_query.all()
        
        # Build individual row records (one row per income type per date per status)
        records = []
        
        for row in results:
            is_paid = row.verification_status == 'Completed'
            amount = float(row.net_amount or 0)
            tds = float(row.tds_amount or 0)
            
            if amount > 0 or tds > 0:
                records.append({
                    'business_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                    'income_type': row.income_type or 'N/A',
                    'status': 'Completed' if is_paid else 'Pending',
                    'count': row.count or 0,
                    'net_amount': amount,
                    'tds_deduction': tds
                })
        
        # Sort by date descending
        records = sorted(records, key=lambda x: x['business_date'], reverse=True)
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate status-based totals
        total_paid = sum(r['net_amount'] for r in records if r['status'] == 'Completed')
        total_pending = sum(r['net_amount'] for r in records if r['status'] == 'Pending')
        total_tds_paid = sum(r['tds_deduction'] for r in records if r['status'] == 'Completed')
        total_tds_pending = sum(r['tds_deduction'] for r in records if r['status'] == 'Pending')
        
        # Dynamically calculate income-type-wise totals from data
        income_types = {}
        for r in records:
            income_type = r['income_type']
            if income_type not in income_types:
                income_types[income_type] = {
                    'income_type': income_type,
                    'amount': 0,
                    'count': 0,
                    'tds_amount': 0
                }
            income_types[income_type]['amount'] += r['net_amount']
            income_types[income_type]['count'] += r['count']
            income_types[income_type]['tds_amount'] += r['tds_deduction']
        
        # Add Guru Dakshina as separate income type (TDS from all transactions)
        total_guru_tds = sum(r['tds_deduction'] for r in records)
        total_guru_count = sum(r['count'] for r in records)
        
        # Convert to list for frontend consumption
        income_type_breakdown = list(income_types.values())
        
        # Add Guru Dakshina
        income_type_breakdown.append({
            'income_type': 'guru_dakshina',
            'amount': total_guru_tds,
            'count': total_guru_count,
            'tds_amount': 0
        })
        
        return {
            "success": True,
            "data": paginated_records,
            "totals": {
                # Status-based breakdown
                "total_paid": total_paid,
                "total_pending": total_pending,
                "total_tds_paid": total_tds_paid,
                "total_tds_pending": total_tds_pending,
                "grand_total": total_paid + total_pending,
                
                # Dynamic income-type breakdown (array)
                "income_type_breakdown": income_type_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }
    
    @staticmethod
    def get_expense_details(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        TAB 2 - SUB-TAB 3: Expenses (Awards, Bonanza, Field Allowance, Training, Operations)
        Date-wise breakdown with paid/pending status
        """
        # Expenses from expense table - date-wise
        expense_query = db.query(
            cast(Expense.expense_date, Date).label('transaction_date'),
            Expense.category,
            Expense.status,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('amount')
        ).filter(
            Expense.is_deleted == False
        ).group_by(
            cast(Expense.expense_date, Date),
            Expense.category,
            Expense.status
        )
        
        if from_date:
            expense_query = expense_query.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            expense_query = expense_query.filter(func.date(Expense.expense_date) <= to_date)
        
        expense_results = expense_query.all()
        
        # Build individual row records
        records = []
        
        for row in expense_results:
            is_paid = row.status == 'approved'
            amount = float(row.amount or 0)
            
            if amount > 0:
                records.append({
                    'expense_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                    'category': row.category or 'N/A',
                    'description': f"{row.category} Expense",
                    'status': 'approved' if is_paid else 'pending',
                    'count': row.count or 0,
                    'amount': amount
                })
        
        # Add pending field allowance
        field_allowance_query = db.query(
            func.sum(FieldAllowanceEligibility.total_value - func.coalesce(FieldAllowanceEligibility.total_paid_to_date, 0)).label('pending_amount')
        ).filter(
            FieldAllowanceEligibility.overall_status == 'Active'
        )
        
        field_pending = float(field_allowance_query.scalar() or 0)
        
        if field_pending > 0:
            records.append({
                'expense_date': 'Pending',
                'category': 'Field Allowance',
                'description': 'Pending Field Allowance Commitments',
                'status': 'pending',
                'count': 0,
                'amount': field_pending
            })
        
        # Add pending training claims
        training_pending_query = db.query(
            func.sum(TrainingClaim.discount_amount + func.coalesce(TrainingClaim.bonus_amount, 0)).label('pending_amount')
        ).filter(
            TrainingClaim.claim_status.notin_(['Paid', 'Rejected'])
        )
        
        training_pending = float(training_pending_query.scalar() or 0)
        
        if training_pending > 0:
            records.append({
                'expense_date': 'Pending',
                'category': 'Training Claims',
                'description': 'Pending Training Claims',
                'status': 'pending',
                'count': 0,
                'amount': training_pending
            })
        
        # Add TDS paid to government - DC Protocol
        tds_query = db.query(
            cast(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date), Date).label('transaction_date'),
            TDSPayable.payment_status,
            func.sum(TDSPayable.tds_amount).label('amount'),
            func.count(TDSPayable.id).label('count')
        ).group_by(
            cast(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date), Date),
            TDSPayable.payment_status
        )
        
        if from_date:
            tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) >= from_date)
        if to_date:
            tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) <= to_date)
        
        tds_results = tds_query.all()
        
        for row in tds_results:
            is_paid = row.payment_status == 'Paid'
            amount = float(row.amount or 0)
            
            if amount > 0:
                records.append({
                    'expense_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                    'category': 'TDS',
                    'description': 'TDS paid to Government (2%)',
                    'status': 'approved' if is_paid else 'pending',
                    'count': row.count or 0,
                    'amount': amount
                })
        
        # Sort by date descending (put "Pending" at the end)
        dated_records = [r for r in records if r['expense_date'] != 'Pending']
        pending_records = [r for r in records if r['expense_date'] == 'Pending']
        
        dated_records = sorted(dated_records, key=lambda x: x['expense_date'], reverse=True)
        records = dated_records + pending_records
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate totals
        total_paid = sum(r['amount'] for r in records if r['status'] == 'approved')
        total_pending = sum(r['amount'] for r in records if r['status'] == 'pending')
        
        # Build dynamic category breakdown
        category_totals = {}
        
        for record in records:
            category = record['category']
            if category not in category_totals:
                category_totals[category] = {
                    'amount': 0,
                    'count': 0
                }
            category_totals[category]['amount'] += record['amount']
            category_totals[category]['count'] += record['count']
        
        # Convert to array format
        category_breakdown = []
        for category, data in category_totals.items():
            if data['amount'] > 0:
                # Map category names to consistent keys
                category_key = category.lower().replace(' ', '_')
                category_breakdown.append({
                    'category': category_key,
                    'amount': data['amount'],
                    'count': data['count']
                })
        
        return {
            "success": True,
            "data": paginated_records,
            "summary": {
                "total_paid": total_paid,
                "total_pending": total_pending,
                "grand_total": total_paid + total_pending,
                
                # Dynamic category breakdown (array)
                "category_breakdown": category_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }

    @staticmethod
    def get_revenue_user_details(
        db: Session,
        transaction_date: date,
        source_type: str
    ) -> Dict[str, Any]:
        """
        Get individual user records for revenue transactions on a specific date and source type
        """
        users = []
        
        if source_type == "Package Sales":
            # Get users who activated packages on this date
            package_users = db.query(
                User.id,
                User.name,
                User.package_points,
                User.activation_date
            ).filter(
                func.date(User.activation_date) == transaction_date,
                User.package_points.isnot(None),
                User.package_points > 0
            ).all()
            
            for user in package_users:
                # Calculate package amount from points
                if user.package_points == 1.0:
                    amount = 15000
                elif user.package_points == 0.5:
                    amount = 7500
                elif user.package_points == 0.05:
                    amount = 1000
                elif user.package_points == 0.025:
                    amount = 500
                else:
                    amount = 0
                
                users.append({
                    'user_id': user.id,
                    'user_name': user.name,
                    'amount': float(amount),
                    'details': f"Package Points: {user.package_points}"
                })
        
        elif source_type == "Company Earnings":
            # DC Protocol: Get Company Earnings (Admin Fee 8% + Handling Charges) from CompanyEarnings table
            company_earnings = db.query(
                CompanyEarnings.user_id,
                User.name,
                CompanyEarnings.admin_deduction,
                CompanyEarnings.net_company_earnings,
                CompanyEarnings.description,
                CompanyEarnings.income_type
            ).join(
                User, CompanyEarnings.user_id == User.id
            ).filter(
                func.date(CompanyEarnings.ceiling_date) == transaction_date
            ).all()
            
            for record in company_earnings:
                # DC Protocol: Company Earnings = net_company_earnings only (admin_deduction is separate revenue line from PendingIncome)
                revenue_amount = float(record.net_company_earnings or 0)
                
                details = f"Income Type: {record.income_type}"
                if record.description:
                    details += f" | {record.description}"
                
                users.append({
                    'user_id': record.user_id,
                    'user_name': record.name,
                    'amount': revenue_amount,
                    'details': details
                })
        
        return {
            "success": True,
            "data": users,
            "count": len(users)
        }

    @staticmethod
    def get_payout_user_details(
        db: Session,
        transaction_date: date,
        income_type: str
    ) -> Dict[str, Any]:
        """
        Get individual user records for payout transactions on a specific date and income type
        """
        # Get income records from pending_income table
        income_records = db.query(
            PendingIncome.user_id,
            User.name,
            PendingIncome.net_amount,
            PendingIncome.tds_deduction,
            PendingIncome.gross_amount,
            PendingIncome.verification_status
        ).join(
            User, PendingIncome.user_id == User.id
        ).filter(
            func.date(PendingIncome.business_date) == transaction_date,
            PendingIncome.income_type == income_type
        ).all()
        
        users = []
        for record in income_records:
            gross_amt = float(record.gross_amount or 0)
            tds_amt = float(record.tds_deduction or 0)
            net_amt = float(record.net_amount or 0)
            
            users.append({
                'user_id': record.user_id,
                'user_name': record.name,
                'amount': net_amt,
                'details': f"Gross: ₹{gross_amt:.2f}, TDS: ₹{tds_amt:.2f}, Net: ₹{net_amt:.2f}",
                'status': 'Paid' if record.verification_status == 'Completed' else 'Pending'
            })
        
        return {
            "success": True,
            "data": users,
            "count": len(users)
        }

    @staticmethod
    def get_expense_user_details(
        db: Session,
        transaction_date: date,
        category: str
    ) -> Dict[str, Any]:
        """
        Get individual records for expense transactions on a specific date and category
        - Awards: Shows both winner (user via award_reference) and vendor paid
        - TDS/Field Allowance: Shows user (on whose behalf we paid)
        - Cash/Training/Guru Dakshina: Shows user beneficiary
        """
        users = []
        
        # Import award models for joining
        from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
        
        # Get expenses with optional joins to award/user tables
        expense_records = db.query(
            Expense.id,
            Expense.award_reference_id,
            Expense.award_reference_type,
            Expense.vendor,
            Expense.amount,
            Expense.description,
            Expense.status
        ).filter(
            func.date(Expense.expense_date) == transaction_date,
            Expense.category == category,
            Expense.is_deleted == False
        ).all()
        
        for record in expense_records:
            amount = float(record.amount or 0)
            status = 'Paid' if record.status == 'approved' else 'Pending'
            
            # For Award category: Fetch user from award_reference
            if category == "Award" and record.award_reference_id:
                # Determine which award table to join based on reference type
                if record.award_reference_type == 'Direct Award':
                    award_progress = db.query(
                        UserAwardProgress.user_id,
                        User.name
                    ).join(
                        User, UserAwardProgress.user_id == User.id
                    ).filter(
                        UserAwardProgress.id == record.award_reference_id
                    ).first()
                elif record.award_reference_type == 'Matching Award':
                    award_progress = db.query(
                        UserMatchingAwardProgress.user_id,
                        User.name
                    ).join(
                        User, UserMatchingAwardProgress.user_id == User.id
                    ).filter(
                        UserMatchingAwardProgress.id == record.award_reference_id
                    ).first()
                else:
                    award_progress = None
                
                if award_progress:
                    winner_name = award_progress.name
                    winner_id = award_progress.user_id
                else:
                    winner_name = "Unknown Winner"
                    winner_id = "N/A"
                
                vendor_paid = record.vendor if record.vendor else "Unknown Vendor"
                
                users.append({
                    'user_id': winner_id,
                    'user_name': f"Winner: {winner_name}",
                    'amount': amount,
                    'details': f"Paid to Vendor: {vendor_paid} | {record.description or 'Award'}",
                    'status': status
                })
            
            # For other categories: Use vendor as "user on whose behalf we paid"
            else:
                # Vendor field contains description of who/what this expense is for
                payee_name = record.vendor if record.vendor else record.description or category
                
                users.append({
                    'user_id': "N/A",
                    'user_name': payee_name,
                    'amount': amount,
                    'details': record.description or category,
                    'status': status
                })
        
        return {
            "success": True,
            "data": users,
            "count": len(users)
        }
    
    @staticmethod
    def get_revenue_by_user(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        User-wise revenue aggregation (User → Source → Date drill-down)
        Groups revenue by user showing total amount per user
        """
        # Package Sales - User wise
        package_query = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            func.count(User.id).label('activation_count'),
            func.sum(
                case(
                    (User.package_points == 1.0, 15000),
                    (User.package_points == 0.5, 7500),
                    (User.package_points == 0.05, 1000),
                    (User.package_points == 0.025, 500),
                    else_=0
                )
            ).label('package_amount')
        ).filter(
            User.activation_date.isnot(None),
            User.package_points.isnot(None),
            User.package_points > 0
        )
        
        if from_date:
            package_query = package_query.filter(func.date(User.activation_date) >= from_date)
        if to_date:
            package_query = package_query.filter(func.date(User.activation_date) <= to_date)
        
        package_query = package_query.group_by(User.id, User.name)
        package_results = package_query.all()
        
        # Company Earnings - User wise
        handling_query = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            func.count(CompanyEarnings.id).label('earnings_count'),
            func.sum(CompanyEarnings.net_company_earnings).label('earnings_amount')
        ).join(
            User, CompanyEarnings.user_id == User.id
        )
        
        if from_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            handling_query = handling_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        
        handling_query = handling_query.group_by(User.id, User.name)
        handling_results = handling_query.all()
        
        # Aggregate by user
        user_revenue = {}
        
        for row in package_results:
            user_id = row.user_id
            if user_id not in user_revenue:
                user_revenue[user_id] = {
                    'user_id': user_id,
                    'user_name': row.user_name,
                    'package_amount': 0,
                    'earnings_amount': 0,
                    'total_amount': 0,
                    'transaction_count': 0
                }
            user_revenue[user_id]['package_amount'] += float(row.package_amount or 0)
            user_revenue[user_id]['transaction_count'] += (row.activation_count or 0)
        
        for row in handling_results:
            user_id = row.user_id
            if user_id not in user_revenue:
                user_revenue[user_id] = {
                    'user_id': user_id,
                    'user_name': row.user_name,
                    'package_amount': 0,
                    'earnings_amount': 0,
                    'total_amount': 0,
                    'transaction_count': 0
                }
            user_revenue[user_id]['earnings_amount'] += float(row.earnings_amount or 0)
            user_revenue[user_id]['transaction_count'] += (row.earnings_count or 0)
        
        # Calculate totals
        for user_id in user_revenue:
            user_revenue[user_id]['total_amount'] = (
                user_revenue[user_id]['package_amount'] + 
                user_revenue[user_id]['earnings_amount']
            )
        
        # Convert to list and sort by total amount descending
        records = list(user_revenue.values())
        records = sorted(records, key=lambda x: x['total_amount'], reverse=True)
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate grand totals
        total_package = sum(r['package_amount'] for r in records)
        total_earnings = sum(r['earnings_amount'] for r in records)
        
        # Calculate admin fee revenue (8% deduction) with same date filters and user count
        admin_fee_query = db.query(
            func.sum(PendingIncome.admin_deduction).label('admin_fee'),
            func.count(func.distinct(PendingIncome.user_id)).label('user_count')
        ).filter(
            PendingIncome.admin_deduction > 0
        )
        
        if from_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            admin_fee_query = admin_fee_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        admin_fee_result = admin_fee_query.first()
        admin_fee_revenue = float(admin_fee_result.admin_fee or 0) if admin_fee_result else 0
        admin_fee_user_count = admin_fee_result.user_count if admin_fee_result else 0
        
        # Count unique users per source
        package_user_count = len([r for r in records if r['package_amount'] > 0])
        earnings_user_count = len([r for r in records if r['earnings_amount'] > 0])
        
        # Build dynamic source breakdown
        source_breakdown = []
        
        if total_package > 0:
            source_breakdown.append({
                'source': 'package_sales',
                'amount': total_package,
                'user_count': package_user_count
            })
        
        if total_earnings > 0:
            source_breakdown.append({
                'source': 'handling_revenue',
                'amount': total_earnings,
                'user_count': earnings_user_count
            })
        
        if admin_fee_revenue > 0:
            source_breakdown.append({
                'source': 'admin_fee',
                'amount': admin_fee_revenue,
                'user_count': admin_fee_user_count
            })
        
        return {
            "success": True,
            "data": paginated_records,
            "totals": {
                "total_package_revenue": total_package,
                "total_earnings_revenue": total_earnings,
                "admin_fee_revenue": admin_fee_revenue,
                "grand_total": total_package + total_earnings + admin_fee_revenue,
                
                # Dynamic source breakdown (array)
                "source_breakdown": source_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }
    
    @staticmethod
    def get_payout_by_user(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        User-wise payout aggregation (User → Income Type → Date drill-down)
        Groups payouts by user showing total paid/pending per user
        """
        # Payouts from PendingIncome
        payout_query = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            PendingIncome.verification_status,
            func.count(PendingIncome.id).label('payout_count'),
            func.sum(PendingIncome.net_amount).label('net_amount'),
            func.sum(PendingIncome.tds_deduction).label('tds_amount')
        ).join(
            User, PendingIncome.user_id == User.id
        )
        
        if from_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        payout_query = payout_query.group_by(
            User.id,
            User.name,
            PendingIncome.verification_status
        )
        
        payout_results = payout_query.all()
        
        # Aggregate by user
        user_payouts = {}
        
        for row in payout_results:
            user_id = row.user_id
            if user_id not in user_payouts:
                user_payouts[user_id] = {
                    'user_id': user_id,
                    'user_name': row.user_name,
                    'paid_amount': 0,
                    'pending_amount': 0,
                    'total_amount': 0,
                    'tds_paid': 0,
                    'tds_pending': 0,
                    'transaction_count': 0
                }
            
            is_paid = row.verification_status == 'Completed'
            net_amount = float(row.net_amount or 0)
            tds_amount = float(row.tds_amount or 0)
            
            if is_paid:
                user_payouts[user_id]['paid_amount'] += net_amount
                user_payouts[user_id]['tds_paid'] += tds_amount
            else:
                user_payouts[user_id]['pending_amount'] += net_amount
                user_payouts[user_id]['tds_pending'] += tds_amount
            
            user_payouts[user_id]['transaction_count'] += (row.payout_count or 0)
        
        # Calculate totals
        for user_id in user_payouts:
            user_payouts[user_id]['total_amount'] = (
                user_payouts[user_id]['paid_amount'] + 
                user_payouts[user_id]['pending_amount']
            )
        
        # Convert to list and sort by total amount descending
        records = list(user_payouts.values())
        records = sorted(records, key=lambda x: x['total_amount'], reverse=True)
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate status-based grand totals
        total_paid = sum(r['paid_amount'] for r in records)
        total_pending = sum(r['pending_amount'] for r in records)
        total_tds = sum(r['tds_paid'] + r['tds_pending'] for r in records)
        
        # Dynamically calculate income-type-wise totals by querying PendingIncome directly
        income_type_query = db.query(
            PendingIncome.income_type,
            func.sum(PendingIncome.net_amount).label('total_amount'),
            func.sum(PendingIncome.tds_deduction).label('total_tds'),
            func.count(func.distinct(PendingIncome.user_id)).label('user_count')
        )
        
        if from_date:
            income_type_query = income_type_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            income_type_query = income_type_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        income_type_query = income_type_query.group_by(PendingIncome.income_type)
        income_type_results = income_type_query.all()
        
        # Build dynamic income type breakdown
        income_type_breakdown = []
        total_guru_dakshina = 0
        all_user_ids = set()
        
        for row in income_type_results:
            income_type = row.income_type or 'unknown'
            amount = float(row.total_amount or 0)
            tds = float(row.total_tds or 0)
            user_count = row.user_count or 0
            
            # Add to breakdown
            income_type_breakdown.append({
                'income_type': income_type,
                'amount': amount,
                'user_count': user_count,
                'tds_amount': tds
            })
            
            # Accumulate Guru Dakshina from all types
            total_guru_dakshina += tds
        
        # Get unique user count for Guru Dakshina (all users who have any income)
        guru_user_query = db.query(
            func.count(func.distinct(PendingIncome.user_id)).label('total_users')
        )
        
        if from_date:
            guru_user_query = guru_user_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            guru_user_query = guru_user_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        guru_user_count = guru_user_query.scalar() or 0
        
        # Add Guru Dakshina as separate entry
        income_type_breakdown.append({
            'income_type': 'guru_dakshina',
            'amount': total_guru_dakshina,
            'user_count': guru_user_count,
            'tds_amount': 0
        })
        
        return {
            "success": True,
            "data": paginated_records,
            "totals": {
                # Status-based breakdown
                "total_paid": total_paid,
                "total_pending": total_pending,
                "total_tds": total_tds,
                "grand_total": total_paid + total_pending,
                
                # Dynamic income-type breakdown (array)
                "income_type_breakdown": income_type_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }
    
    @staticmethod
    def get_expense_by_user(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        User-wise expense aggregation (User → Category → Date drill-down)
        Groups expenses by user showing total paid/pending per user
        Note: Only expenses with user_id field can be aggregated
        """
        from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
        
        # Get award expenses with user_id from award progress tables
        award_expenses = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            Expense.status,
            func.count(Expense.id).label('expense_count'),
            func.sum(Expense.amount).label('expense_amount')
        ).join(
            UserAwardProgress, Expense.award_reference_id == UserAwardProgress.id
        ).join(
            User, UserAwardProgress.user_id == User.id
        ).filter(
            Expense.award_reference_type == 'Direct Award',
            Expense.is_deleted == False
        )
        
        if from_date:
            award_expenses = award_expenses.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            award_expenses = award_expenses.filter(func.date(Expense.expense_date) <= to_date)
        
        award_expenses = award_expenses.group_by(User.id, User.name, Expense.status)
        award_results = award_expenses.all()
        
        # Matching award expenses
        matching_award_expenses = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            Expense.status,
            func.count(Expense.id).label('expense_count'),
            func.sum(Expense.amount).label('expense_amount')
        ).join(
            UserMatchingAwardProgress, Expense.award_reference_id == UserMatchingAwardProgress.id
        ).join(
            User, UserMatchingAwardProgress.user_id == User.id
        ).filter(
            Expense.award_reference_type == 'Matching Award',
            Expense.is_deleted == False
        )
        
        if from_date:
            matching_award_expenses = matching_award_expenses.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            matching_award_expenses = matching_award_expenses.filter(func.date(Expense.expense_date) <= to_date)
        
        matching_award_expenses = matching_award_expenses.group_by(User.id, User.name, Expense.status)
        matching_results = matching_award_expenses.all()
        
        # TDS payable - paid on behalf of users
        tds_expenses = db.query(
            User.id.label('user_id'),
            User.name.label('user_name'),
            TDSPayable.payment_status.label('status'),
            func.count(TDSPayable.id).label('expense_count'),
            func.sum(TDSPayable.tds_amount).label('expense_amount')
        ).join(
            User, TDSPayable.user_id == User.id
        )
        
        if from_date:
            tds_expenses = tds_expenses.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) >= from_date)
        if to_date:
            tds_expenses = tds_expenses.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) <= to_date)
        
        tds_expenses = tds_expenses.group_by(User.id, User.name, TDSPayable.payment_status)
        tds_results = tds_expenses.all()
        
        # Aggregate by user
        user_expenses = {}
        
        # Process all results
        all_results = list(award_results) + list(matching_results) + list(tds_results)
        
        for row in all_results:
            user_id = row.user_id
            if user_id not in user_expenses:
                user_expenses[user_id] = {
                    'user_id': user_id,
                    'user_name': row.user_name,
                    'paid_amount': 0,
                    'pending_amount': 0,
                    'total_amount': 0,
                    'transaction_count': 0
                }
            
            # Determine if paid or pending based on status field
            is_paid = row.status in ['approved', 'Completed', 'Paid']
            expense_amount = float(row.expense_amount or 0)
            
            if is_paid:
                user_expenses[user_id]['paid_amount'] += expense_amount
            else:
                user_expenses[user_id]['pending_amount'] += expense_amount
            
            user_expenses[user_id]['transaction_count'] += (row.expense_count or 0)
        
        # Calculate totals
        for user_id in user_expenses:
            user_expenses[user_id]['total_amount'] = (
                user_expenses[user_id]['paid_amount'] + 
                user_expenses[user_id]['pending_amount']
            )
        
        # Convert to list and sort by total amount descending
        records = list(user_expenses.values())
        records = sorted(records, key=lambda x: x['total_amount'], reverse=True)
        
        # Pagination
        total_records = len(records)
        start = (page - 1) * limit
        end = start + limit
        paginated_records = records[start:end]
        
        # Calculate grand totals
        total_paid = sum(r['paid_amount'] for r in records)
        total_pending = sum(r['pending_amount'] for r in records)
        
        # Build dynamic category breakdown
        category_totals = {'awards': 0, 'tds': 0}
        category_user_counts = {'awards': set(), 'tds': set()}
        
        # Count award expenses
        for row in list(award_results) + list(matching_results):
            category_totals['awards'] += float(row.expense_amount or 0)
            category_user_counts['awards'].add(row.user_id)
        
        # Count TDS expenses
        for row in tds_results:
            category_totals['tds'] += float(row.expense_amount or 0)
            category_user_counts['tds'].add(row.user_id)
        
        # Build category breakdown array
        category_breakdown = []
        
        if category_totals['awards'] > 0:
            category_breakdown.append({
                'category': 'awards',
                'amount': category_totals['awards'],
                'user_count': len(category_user_counts['awards'])
            })
        
        if category_totals['tds'] > 0:
            category_breakdown.append({
                'category': 'tds',
                'amount': category_totals['tds'],
                'user_count': len(category_user_counts['tds'])
            })
        
        return {
            "success": True,
            "data": paginated_records,
            "totals": {
                "total_paid": total_paid,
                "total_pending": total_pending,
                "grand_total": total_paid + total_pending,
                
                # Dynamic category breakdown (array)
                "category_breakdown": category_breakdown
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": (total_records + limit - 1) // limit if total_records > 0 else 0
            }
        }
    
    @staticmethod
    def get_revenue_sources_for_user(
        db: Session,
        user_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 2 drill-down: Show revenue sources for a specific user
        Returns Package Sales and Company Earnings breakdowns
        """
        sources = []
        
        # Package Sales for this user
        package_query = db.query(
            func.count(User.id).label('count'),
            func.sum(
                case(
                    (User.package_points == 1.0, 15000),
                    (User.package_points == 0.5, 7500),
                    (User.package_points == 0.05, 1000),
                    (User.package_points == 0.025, 500),
                    else_=0
                )
            ).label('amount')
        ).filter(
            User.id == user_id,
            User.activation_date.isnot(None),
            User.package_points.isnot(None),
            User.package_points > 0
        )
        
        if from_date:
            package_query = package_query.filter(func.date(User.activation_date) >= from_date)
        if to_date:
            package_query = package_query.filter(func.date(User.activation_date) <= to_date)
        
        package_result = package_query.first()
        
        if package_result and package_result.amount and package_result.amount > 0:
            sources.append({
                'source': 'Package Sales',
                'count': package_result.count or 0,
                'amount': float(package_result.amount or 0)
            })
        
        # Company Earnings for this user
        earnings_query = db.query(
            func.count(CompanyEarnings.id).label('count'),
            func.sum(CompanyEarnings.net_company_earnings).label('amount')
        ).filter(
            CompanyEarnings.user_id == user_id
        )
        
        if from_date:
            earnings_query = earnings_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            earnings_query = earnings_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        
        earnings_result = earnings_query.first()
        
        if earnings_result and earnings_result.amount and earnings_result.amount > 0:
            sources.append({
                'source': 'Company Earnings',
                'count': earnings_result.count or 0,
                'amount': float(earnings_result.amount or 0)
            })
        
        return {
            "success": True,
            "data": sources
        }
    
    @staticmethod
    def get_payout_sources_for_user(
        db: Session,
        user_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 2 drill-down: Show payout income types for a specific user
        Returns breakdown by income_type
        """
        payout_query = db.query(
            PendingIncome.income_type,
            PendingIncome.verification_status,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.net_amount).label('net_amount'),
            func.sum(PendingIncome.tds_deduction).label('tds_amount')
        ).filter(
            PendingIncome.user_id == user_id
        )
        
        if from_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        payout_query = payout_query.group_by(
            PendingIncome.income_type,
            PendingIncome.verification_status
        )
        
        payout_results = payout_query.all()
        
        # Aggregate by income type
        income_types = {}
        
        for row in payout_results:
            income_type = row.income_type or 'Unknown'
            if income_type not in income_types:
                income_types[income_type] = {
                    'income_type': income_type,
                    'paid_amount': 0,
                    'pending_amount': 0,
                    'total_amount': 0,
                    'count': 0
                }
            
            is_paid = row.verification_status == 'Completed'
            net_amount = float(row.net_amount or 0)
            
            if is_paid:
                income_types[income_type]['paid_amount'] += net_amount
            else:
                income_types[income_type]['pending_amount'] += net_amount
            
            income_types[income_type]['count'] += (row.count or 0)
        
        # Calculate totals
        for income_type in income_types:
            income_types[income_type]['total_amount'] = (
                income_types[income_type]['paid_amount'] + 
                income_types[income_type]['pending_amount']
            )
        
        # Convert to list
        sources = list(income_types.values())
        
        return {
            "success": True,
            "data": sources
        }
    
    @staticmethod
    def get_expense_sources_for_user(
        db: Session,
        user_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 2 drill-down: Show expense categories for a specific user
        Returns breakdown by category (Awards, TDS, Field Allowance, Training)
        """
        from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
        
        categories = {}
        
        # Awards expenses
        award_query = db.query(
            Expense.status,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('amount')
        ).join(
            UserAwardProgress, Expense.award_reference_id == UserAwardProgress.id
        ).filter(
            UserAwardProgress.user_id == user_id,
            Expense.award_reference_type == 'Direct Award',
            Expense.is_deleted == False
        )
        
        if from_date:
            award_query = award_query.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            award_query = award_query.filter(func.date(Expense.expense_date) <= to_date)
        
        award_query = award_query.group_by(Expense.status)
        award_results = award_query.all()
        
        # Matching awards
        matching_query = db.query(
            Expense.status,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('amount')
        ).join(
            UserMatchingAwardProgress, Expense.award_reference_id == UserMatchingAwardProgress.id
        ).filter(
            UserMatchingAwardProgress.user_id == user_id,
            Expense.award_reference_type == 'Matching Award',
            Expense.is_deleted == False
        )
        
        if from_date:
            matching_query = matching_query.filter(func.date(Expense.expense_date) >= from_date)
        if to_date:
            matching_query = matching_query.filter(func.date(Expense.expense_date) <= to_date)
        
        matching_query = matching_query.group_by(Expense.status)
        matching_results = matching_query.all()
        
        # Combine award results
        all_award_results = list(award_results) + list(matching_results)
        
        if all_award_results:
            categories['Award'] = {
                'category': 'Award',
                'paid_amount': 0,
                'pending_amount': 0,
                'total_amount': 0,
                'count': 0
            }
            
            for row in all_award_results:
                is_paid = row.status == 'approved'
                amount = float(row.amount or 0)
                
                if is_paid:
                    categories['Award']['paid_amount'] += amount
                else:
                    categories['Award']['pending_amount'] += amount
                
                categories['Award']['count'] += (row.count or 0)
            
            categories['Award']['total_amount'] = (
                categories['Award']['paid_amount'] + 
                categories['Award']['pending_amount']
            )
        
        # TDS
        tds_query = db.query(
            TDSPayable.payment_status,
            func.count(TDSPayable.id).label('count'),
            func.sum(TDSPayable.tds_amount).label('amount')
        ).filter(
            TDSPayable.user_id == user_id
        )
        
        if from_date:
            tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) >= from_date)
        if to_date:
            tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) <= to_date)
        
        tds_query = tds_query.group_by(TDSPayable.payment_status)
        tds_results = tds_query.all()
        
        if tds_results:
            categories['TDS'] = {
                'category': 'TDS',
                'paid_amount': 0,
                'pending_amount': 0,
                'total_amount': 0,
                'count': 0
            }
            
            for row in tds_results:
                is_paid = row.payment_status == 'Paid'
                amount = float(row.amount or 0)
                
                if is_paid:
                    categories['TDS']['paid_amount'] += amount
                else:
                    categories['TDS']['pending_amount'] += amount
                
                categories['TDS']['count'] += (row.count or 0)
            
            categories['TDS']['total_amount'] = (
                categories['TDS']['paid_amount'] + 
                categories['TDS']['pending_amount']
            )
        
        # Convert to list
        sources = list(categories.values())
        
        return {
            "success": True,
            "data": sources
        }
    
    @staticmethod
    def get_revenue_dates_for_user_source(
        db: Session,
        user_id: str,
        source: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 3 drill-down: Show dates for a specific user + source combination
        """
        dates = []
        
        if source == 'Package Sales':
            # Get activation dates for this user
            user = db.query(
                cast(User.activation_date, Date).label('transaction_date'),
                case(
                    (User.package_points == 1.0, 15000),
                    (User.package_points == 0.5, 7500),
                    (User.package_points == 0.05, 1000),
                    (User.package_points == 0.025, 500),
                    else_=0
                ).label('amount')
            ).filter(
                User.id == user_id,
                User.activation_date.isnot(None),
                User.package_points.isnot(None),
                User.package_points > 0
            )
            
            if from_date:
                user = user.filter(func.date(User.activation_date) >= from_date)
            if to_date:
                user = user.filter(func.date(User.activation_date) <= to_date)
            
            user_result = user.first()
            
            if user_result and user_result.amount > 0:
                dates.append({
                    'transaction_date': user_result.transaction_date.isoformat() if user_result.transaction_date else 'Unknown',
                    'count': 1,
                    'amount': float(user_result.amount or 0)
                })
        
        elif source == 'Company Earnings':
            # Get company earnings dates for this user
            earnings_query = db.query(
                cast(CompanyEarnings.ceiling_date, Date).label('transaction_date'),
                func.count(CompanyEarnings.id).label('count'),
                func.sum(CompanyEarnings.net_company_earnings).label('amount')
            ).filter(
                CompanyEarnings.user_id == user_id
            )
            
            if from_date:
                earnings_query = earnings_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
            if to_date:
                earnings_query = earnings_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
            
            earnings_query = earnings_query.group_by(cast(CompanyEarnings.ceiling_date, Date))
            earnings_results = earnings_query.all()
            
            for row in earnings_results:
                if row.amount and row.amount > 0:
                    dates.append({
                        'transaction_date': row.transaction_date.isoformat() if row.transaction_date else 'Unknown',
                        'count': row.count or 0,
                        'amount': float(row.amount or 0)
                    })
        
        # Sort by date descending
        dates = sorted(dates, key=lambda x: x['transaction_date'], reverse=True)
        
        return {
            "success": True,
            "data": dates
        }
    
    @staticmethod
    def get_payout_dates_for_user_source(
        db: Session,
        user_id: str,
        income_type: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 3 drill-down: Show dates for a specific user + income_type combination
        """
        payout_query = db.query(
            cast(PendingIncome.business_date, Date).label('transaction_date'),
            PendingIncome.verification_status,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.net_amount).label('net_amount'),
            func.sum(PendingIncome.tds_deduction).label('tds_amount')
        ).filter(
            PendingIncome.user_id == user_id,
            PendingIncome.income_type == income_type
        )
        
        if from_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            payout_query = payout_query.filter(func.date(PendingIncome.business_date) <= to_date)
        
        payout_query = payout_query.group_by(
            cast(PendingIncome.business_date, Date),
            PendingIncome.verification_status
        )
        
        payout_results = payout_query.all()
        
        # Aggregate by date
        dates_dict = {}
        
        for row in payout_results:
            date_str = row.transaction_date.isoformat() if row.transaction_date else 'Unknown'
            if date_str not in dates_dict:
                dates_dict[date_str] = {
                    'transaction_date': date_str,
                    'paid_amount': 0,
                    'pending_amount': 0,
                    'total_amount': 0,
                    'count': 0
                }
            
            is_paid = row.verification_status == 'Completed'
            net_amount = float(row.net_amount or 0)
            
            if is_paid:
                dates_dict[date_str]['paid_amount'] += net_amount
            else:
                dates_dict[date_str]['pending_amount'] += net_amount
            
            dates_dict[date_str]['count'] += (row.count or 0)
        
        # Calculate totals
        for date_str in dates_dict:
            dates_dict[date_str]['total_amount'] = (
                dates_dict[date_str]['paid_amount'] + 
                dates_dict[date_str]['pending_amount']
            )
        
        # Convert to list and sort
        dates = list(dates_dict.values())
        dates = sorted(dates, key=lambda x: x['transaction_date'], reverse=True)
        
        return {
            "success": True,
            "data": dates
        }
    
    @staticmethod
    def get_expense_dates_for_user_source(
        db: Session,
        user_id: str,
        category: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Level 3 drill-down: Show dates for a specific user + category combination
        """
        from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
        
        dates_dict = {}
        
        if category == 'Award':
            # Direct awards
            award_query = db.query(
                cast(Expense.expense_date, Date).label('transaction_date'),
                Expense.status,
                func.count(Expense.id).label('count'),
                func.sum(Expense.amount).label('amount')
            ).join(
                UserAwardProgress, Expense.award_reference_id == UserAwardProgress.id
            ).filter(
                UserAwardProgress.user_id == user_id,
                Expense.award_reference_type == 'Direct Award',
                Expense.is_deleted == False
            )
            
            if from_date:
                award_query = award_query.filter(func.date(Expense.expense_date) >= from_date)
            if to_date:
                award_query = award_query.filter(func.date(Expense.expense_date) <= to_date)
            
            award_query = award_query.group_by(cast(Expense.expense_date, Date), Expense.status)
            award_results = award_query.all()
            
            # Matching awards
            matching_query = db.query(
                cast(Expense.expense_date, Date).label('transaction_date'),
                Expense.status,
                func.count(Expense.id).label('count'),
                func.sum(Expense.amount).label('amount')
            ).join(
                UserMatchingAwardProgress, Expense.award_reference_id == UserMatchingAwardProgress.id
            ).filter(
                UserMatchingAwardProgress.user_id == user_id,
                Expense.award_reference_type == 'Matching Award',
                Expense.is_deleted == False
            )
            
            if from_date:
                matching_query = matching_query.filter(func.date(Expense.expense_date) >= from_date)
            if to_date:
                matching_query = matching_query.filter(func.date(Expense.expense_date) <= to_date)
            
            matching_query = matching_query.group_by(cast(Expense.expense_date, Date), Expense.status)
            matching_results = matching_query.all()
            
            all_results = list(award_results) + list(matching_results)
            
            for row in all_results:
                date_str = row.transaction_date.isoformat() if row.transaction_date else 'Unknown'
                if date_str not in dates_dict:
                    dates_dict[date_str] = {
                        'transaction_date': date_str,
                        'paid_amount': 0,
                        'pending_amount': 0,
                        'total_amount': 0,
                        'count': 0
                    }
                
                is_paid = row.status == 'approved'
                amount = float(row.amount or 0)
                
                if is_paid:
                    dates_dict[date_str]['paid_amount'] += amount
                else:
                    dates_dict[date_str]['pending_amount'] += amount
                
                dates_dict[date_str]['count'] += (row.count or 0)
        
        elif category == 'TDS':
            tds_query = db.query(
                cast(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date), Date).label('transaction_date'),
                TDSPayable.payment_status,
                func.count(TDSPayable.id).label('count'),
                func.sum(TDSPayable.tds_amount).label('amount')
            ).filter(
                TDSPayable.user_id == user_id
            )
            
            if from_date:
                tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) >= from_date)
            if to_date:
                tds_query = tds_query.filter(func.date(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date)) <= to_date)
            
            tds_query = tds_query.group_by(cast(func.coalesce(TDSPayable.last_payment_date, TDSPayable.generated_date), Date), TDSPayable.payment_status)
            tds_results = tds_query.all()
            
            for row in tds_results:
                date_str = row.transaction_date.isoformat() if row.transaction_date else 'Unknown'
                if date_str not in dates_dict:
                    dates_dict[date_str] = {
                        'transaction_date': date_str,
                        'paid_amount': 0,
                        'pending_amount': 0,
                        'total_amount': 0,
                        'count': 0
                    }
                
                is_paid = row.payment_status == 'Paid'
                amount = float(row.amount or 0)
                
                if is_paid:
                    dates_dict[date_str]['paid_amount'] += amount
                else:
                    dates_dict[date_str]['pending_amount'] += amount
                
                dates_dict[date_str]['count'] += (row.count or 0)
        
        # Calculate totals
        for date_str in dates_dict:
            dates_dict[date_str]['total_amount'] = (
                dates_dict[date_str]['paid_amount'] + 
                dates_dict[date_str]['pending_amount']
            )
        
        # Convert to list and sort
        dates = list(dates_dict.values())
        dates = sorted(dates, key=lambda x: x['transaction_date'], reverse=True)
        
        return {
            "success": True,
            "data": dates
        }
