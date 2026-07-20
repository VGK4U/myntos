"""
Compliance Service for TDS, GST, and Handling Charges tracking
DC Protocol: Queries from source tables directly, no data duplication
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, cast, String
from typing import Optional, Dict, List, Any
from datetime import datetime, date
from decimal import Decimal

from app.models.transaction import PendingIncome, CompanyEarnings, TDSPayable
from app.models.user import User


class ComplianceService:
    """Service for managing compliance records from source tables (DC Protocol)"""
    
    @staticmethod
    def get_tds_records(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        user_id: Optional[str] = None,
        tally_status: Optional[str] = None,
        payment_status: Optional[str] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get TDS records from pending_income table (DC Protocol source)
        Returns user-wise TDS tracking data
        """
        # Query from pending_income (source of truth for TDS)
        query = db.query(
            PendingIncome.id,
            PendingIncome.user_id,
            User.id.label('user_mnr_id'),
            User.name.label('user_name'),
            PendingIncome.income_type,
            PendingIncome.gross_amount,
            PendingIncome.tds_deduction,
            PendingIncome.net_amount,
            PendingIncome.business_date,
            PendingIncome.verification_status,
            PendingIncome.tally_status,
            PendingIncome.tally_updated_at,
            PendingIncome.payment_status,
            PendingIncome.payment_updated_at
        ).join(
            User, PendingIncome.user_id == User.id
        ).filter(
            PendingIncome.tds_deduction > 0  # Only records with TDS
        )
        
        # Apply filters
        if from_date:
            query = query.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            query = query.filter(func.date(PendingIncome.business_date) <= to_date)
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        if min_amount:
            query = query.filter(PendingIncome.tds_deduction >= min_amount)
        if max_amount:
            query = query.filter(PendingIncome.tds_deduction <= max_amount)
        
        # Tally status filter (DC Protocol: read from source table)
        if tally_status:
            query = query.filter(PendingIncome.tally_status == tally_status)
        
        # Payment status filter (DC Protocol: read from source table)
        if payment_status:
            query = query.filter(PendingIncome.payment_status == payment_status)
        
        # Count total before pagination
        total_count = query.count()
        
        # Sorting
        if sort_by == "transaction_date":
            sort_field = PendingIncome.business_date
        elif sort_by == "amount":
            sort_field = PendingIncome.tds_deduction
        elif sort_by == "user_name":
            sort_field = User.name
        else:
            sort_field = PendingIncome.business_date
        
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Pagination
        offset = (page - 1) * limit
        results = query.offset(offset).limit(limit).all()
        
        # Format response (DC Protocol: read from source table columns)
        records = []
        for record in results:
            records.append({
                "id": record.id,
                "user_id": record.user_id,
                "username": record.user_mnr_id,
                "full_name": record.user_name,
                "income_type": record.income_type,
                "gross_payout_amount": float(record.gross_amount),
                "tds_deducted": float(record.tds_deduction),
                "net_amount_paid": float(record.net_amount),
                "transaction_date": record.business_date.isoformat(),
                "tally_status": record.tally_status,
                "tally_updated_date": record.tally_updated_at.isoformat() if record.tally_updated_at else None,
                "payment_status": record.payment_status,
                "payment_date": record.payment_updated_at.isoformat() if record.payment_updated_at else None,
                "notes": f"Income Type: {record.income_type}"
            })
        
        # Summary statistics
        summary = db.query(
            func.count(PendingIncome.id).label('total_records'),
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.tds_deduction).label('total_tds'),
            func.sum(PendingIncome.net_amount).label('total_net')
        ).filter(
            PendingIncome.tds_deduction > 0
        )
        
        if from_date:
            summary = summary.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            summary = summary.filter(func.date(PendingIncome.business_date) <= to_date)
        if user_id:
            summary = summary.filter(PendingIncome.user_id == user_id)
        
        summary_result = summary.first()
        
        # Count status breakdowns (DC Protocol: count from source table)
        tally_updated_count = db.query(func.count(PendingIncome.id)).filter(
            PendingIncome.tds_deduction > 0,
            PendingIncome.tally_status == 'UPDATED'
        )
        if from_date:
            tally_updated_count = tally_updated_count.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            tally_updated_count = tally_updated_count.filter(func.date(PendingIncome.business_date) <= to_date)
        if user_id:
            tally_updated_count = tally_updated_count.filter(PendingIncome.user_id == user_id)
        tally_updated_count = tally_updated_count.scalar() or 0
        
        paid_count = db.query(func.count(PendingIncome.id)).filter(
            PendingIncome.tds_deduction > 0,
            PendingIncome.payment_status == 'PAID'
        )
        if from_date:
            paid_count = paid_count.filter(func.date(PendingIncome.business_date) >= from_date)
        if to_date:
            paid_count = paid_count.filter(func.date(PendingIncome.business_date) <= to_date)
        if user_id:
            paid_count = paid_count.filter(PendingIncome.user_id == user_id)
        paid_count = paid_count.scalar() or 0
        
        return {
            "success": True,
            "records": records,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
            },
            "summary": {
                "total_records": summary_result.total_records or 0,
                "total_gross_amount": float(summary_result.total_gross or 0),
                "total_tds": float(summary_result.total_tds or 0),
                "total_net_amount": float(summary_result.total_net or 0),
                "tally_updated_count": tally_updated_count,
                "tally_pending_count": (summary_result.total_records or 0) - tally_updated_count,
                "paid_count": paid_count,
                "pending_payment_count": (summary_result.total_records or 0) - paid_count
            }
        }
    
    @staticmethod
    def get_gst_records(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        user_id: Optional[str] = None,
        award_type: Optional[str] = None,
        tally_status: Optional[str] = None,
        collection_status: Optional[str] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get GST records from company_earnings table (DC Protocol source)
        GST is 18% on handling charges collected from award winners
        """
        # Query from company_earnings where description contains "GST"
        query = db.query(
            CompanyEarnings.id,
            CompanyEarnings.user_id,
            User.id.label('user_mnr_id'),
            User.name.label('user_name'),
            CompanyEarnings.income_type,
            CompanyEarnings.net_company_earnings,
            CompanyEarnings.ceiling_date,
            CompanyEarnings.description,
            CompanyEarnings.tally_status,
            CompanyEarnings.tally_updated_at,
            CompanyEarnings.collection_status,
            CompanyEarnings.collection_updated_at
        ).join(
            User, CompanyEarnings.user_id == User.id
        ).filter(
            CompanyEarnings.description.ilike('%GST%')  # Filter records with GST
        )
        
        # Apply filters
        if from_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            query = query.filter(CompanyEarnings.user_id == user_id)
        if award_type:
            query = query.filter(CompanyEarnings.income_type.ilike(f'%{award_type}%'))
        if min_amount:
            query = query.filter(CompanyEarnings.net_company_earnings >= min_amount)
        if max_amount:
            query = query.filter(CompanyEarnings.net_company_earnings <= max_amount)
        
        # Tally status filter (DC Protocol: read from source table)
        if tally_status:
            query = query.filter(CompanyEarnings.tally_status == tally_status)
        
        # Collection status filter (DC Protocol: read from source table)
        if collection_status:
            query = query.filter(CompanyEarnings.collection_status == collection_status)
        
        # Count total before pagination
        total_count = query.count()
        
        # Sorting
        if sort_by == "transaction_date":
            sort_field = CompanyEarnings.ceiling_date
        elif sort_by in ["amount", "gst_amount"]:
            sort_field = CompanyEarnings.net_company_earnings
        else:
            sort_field = CompanyEarnings.ceiling_date
        
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Pagination
        offset = (page - 1) * limit
        results = query.offset(offset).limit(limit).all()
        
        # Format response - parse GST from description
        records = []
        for record in results:
            # Parse handling charges and GST from description
            # Format: "... Handling: ₹X, GST(18%): ₹Y, ..."
            handling_charges = 0.0
            gst_amount = 0.0
            
            import re
            if record.description:
                handling_match = re.search(r'Handling.*?₹([\d,]+(?:\.\d{2})?)', record.description)
                gst_match = re.search(r'GST.*?₹([\d,]+(?:\.\d{2})?)', record.description)
                
                if handling_match:
                    handling_charges = float(handling_match.group(1).replace(',', ''))
                if gst_match:
                    gst_amount = float(gst_match.group(1).replace(',', ''))
            
            total_amount = handling_charges + gst_amount
            
            records.append({
                "id": record.id,
                "invoice_id": f"INV-CE-{record.id}",  # Company Earnings based invoice
                "award_type": record.income_type,
                "award_name": None,  # Not stored in company_earnings
                "award_item": None,  # Not stored in company_earnings
                "user_id": record.user_id,
                "username": record.user_mnr_id,
                "full_name": record.user_name,
                "handling_charges": handling_charges,
                "gst_amount": gst_amount,
                "total_amount": total_amount,
                "transaction_date": record.ceiling_date.isoformat(),
                "tally_status": record.tally_status,
                "tally_updated_date": record.tally_updated_at.isoformat() if record.tally_updated_at else None,
                "collection_status": record.collection_status,
                "collection_date": record.collection_updated_at.isoformat() if record.collection_updated_at else None,
                "notes": record.description
            })
        
        # Summary statistics
        summary = db.query(
            func.count(CompanyEarnings.id).label('total_records'),
            func.sum(CompanyEarnings.net_company_earnings).label('total_amount')
        ).filter(
            CompanyEarnings.description.ilike('%GST%')
        )
        
        if from_date:
            summary = summary.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            summary = summary.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            summary = summary.filter(CompanyEarnings.user_id == user_id)
        
        summary_result = summary.first()
        
        # Calculate GST breakdown (approximate from total - assuming GST = 18% of handling)
        total_amount = float(summary_result.total_amount or 0)
        total_gst = total_amount * 0.18 / 1.18  # Reverse calculate GST
        total_handling = total_amount - total_gst
        
        # Count status breakdowns (DC Protocol: count from source table)
        tally_updated_count = db.query(func.count(CompanyEarnings.id)).filter(
            CompanyEarnings.description.ilike('%GST%'),
            CompanyEarnings.tally_status == 'UPDATED'
        )
        if from_date:
            tally_updated_count = tally_updated_count.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            tally_updated_count = tally_updated_count.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            tally_updated_count = tally_updated_count.filter(CompanyEarnings.user_id == user_id)
        tally_updated_count = tally_updated_count.scalar() or 0
        
        collected_count = db.query(func.count(CompanyEarnings.id)).filter(
            CompanyEarnings.description.ilike('%GST%'),
            CompanyEarnings.collection_status == 'COLLECTED'
        )
        if from_date:
            collected_count = collected_count.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            collected_count = collected_count.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if user_id:
            collected_count = collected_count.filter(CompanyEarnings.user_id == user_id)
        collected_count = collected_count.scalar() or 0
        
        return {
            "success": True,
            "records": records,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0
            },
            "summary": {
                "total_records": summary_result.total_records or 0,
                "total_handling_charges": total_handling,
                "total_gst": total_gst,
                "total_amount": total_amount,
                "tally_updated_count": tally_updated_count,
                "tally_pending_count": (summary_result.total_records or 0) - tally_updated_count,
                "collected_count": collected_count,
                "collection_pending_count": (summary_result.total_records or 0) - collected_count
            }
        }
    
    @staticmethod
    def get_company_earnings_summary(
        db: Session,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        income_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get company earnings summary (RVZ-only view)
        Aggregates all company earnings from ceiling excess, handling charges, GST
        """
        query = db.query(
            func.count(CompanyEarnings.id).label('total_transactions'),
            func.sum(CompanyEarnings.excess_amount).label('total_ceiling_excess'),
            func.sum(CompanyEarnings.admin_deduction).label('total_admin_deduction'),
            func.sum(CompanyEarnings.tds_deduction).label('total_tds_company'),
            func.sum(CompanyEarnings.net_company_earnings).label('total_net_earnings')
        )
        
        if from_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            query = query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        if income_type:
            query = query.filter(CompanyEarnings.income_type == income_type)
        
        result = query.first()
        
        # Breakdown by income type
        breakdown_query = db.query(
            CompanyEarnings.income_type,
            func.count(CompanyEarnings.id).label('count'),
            func.sum(CompanyEarnings.net_company_earnings).label('total')
        ).group_by(CompanyEarnings.income_type)
        
        if from_date:
            breakdown_query = breakdown_query.filter(func.date(CompanyEarnings.ceiling_date) >= from_date)
        if to_date:
            breakdown_query = breakdown_query.filter(func.date(CompanyEarnings.ceiling_date) <= to_date)
        
        breakdown = breakdown_query.all()
        
        return {
            "success": True,
            "summary": {
                "total_transactions": result.total_transactions or 0,
                "total_ceiling_excess": float(result.total_ceiling_excess or 0),
                "total_admin_deduction": float(result.total_admin_deduction or 0),
                "total_tds_company": float(result.total_tds_company or 0),
                "total_net_earnings": float(result.total_net_earnings or 0)
            },
            "breakdown_by_income_type": [
                {
                    "income_type": item.income_type,
                    "transaction_count": item.count,
                    "total_earnings": float(item.total)
                }
                for item in breakdown
            ]
        }
    
    @staticmethod
    def update_tally_status(
        db: Session,
        record_id: int,
        updated_by: str,
        status: str
    ) -> bool:
        """
        Update tally status for a compliance record (DC Protocol: persist to source table)
        Works for both TDS (pending_income) and GST (company_earnings) records
        """
        from datetime import datetime
        
        # Try updating in pending_income first (TDS records)
        tds_record = db.query(PendingIncome).filter(PendingIncome.id == record_id).first()
        if tds_record:
            tds_record.tally_status = status
            tds_record.tally_updated_by_id = updated_by
            tds_record.tally_updated_at = datetime.now()
            db.commit()
            return True
        
        # Try updating in company_earnings (GST records)
        gst_record = db.query(CompanyEarnings).filter(CompanyEarnings.id == record_id).first()
        if gst_record:
            gst_record.tally_status = status
            gst_record.tally_updated_by_id = updated_by
            gst_record.tally_updated_at = datetime.now()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def update_collection_status(
        db: Session,
        record_id: int,
        updated_by: str,
        status: str
    ) -> bool:
        """
        Update collection status for GST/Handling Charge records (DC Protocol: persist to source table)
        """
        from datetime import datetime
        
        gst_record = db.query(CompanyEarnings).filter(CompanyEarnings.id == record_id).first()
        if gst_record:
            gst_record.collection_status = status
            gst_record.collection_updated_by_id = updated_by
            gst_record.collection_updated_at = datetime.now()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def update_payment_status(
        db: Session,
        record_id: int,
        updated_by: str,
        status: str
    ) -> bool:
        """
        Update payment status for TDS records (DC Protocol: persist to source table)
        """
        from datetime import datetime
        
        tds_record = db.query(PendingIncome).filter(PendingIncome.id == record_id).first()
        if tds_record:
            tds_record.payment_status = status
            tds_record.payment_updated_by_id = updated_by
            tds_record.payment_updated_at = datetime.now()
            db.commit()
            return True
        
        return False
