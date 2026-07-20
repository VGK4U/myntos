"""
RVZ Expense Management Service - Supreme Authority
Handles full CRUD operations with dual approval workflow:
- Finance creates → RVZ approves
- RVZ creates → Auto-approved (supreme authority)
- Award procurement → Auto-creates expense
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
import json

from app.models.transaction import Expense, ExpenseAuditEvent
from app.models.user import User
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.core.database import get_db


class RVZExpenseService:
    """RVZ Supreme Authority Expense Service"""
    
    @staticmethod
    def create_audit_event(
        db: Session,
        expense_id: int,
        actor_id: str,
        actor_role: str,
        action: str,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Create immutable audit trail event"""
        audit = ExpenseAuditEvent(
            expense_id=expense_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            before_state=json.dumps(before_state) if before_state else None,
            after_state=json.dumps(after_state) if after_state else None,
            action_notes=notes,
            ip_address=ip_address
        )
        db.add(audit)
        db.flush()
        return audit
    
    @staticmethod
    def expense_to_dict(expense: Expense) -> Dict[str, Any]:
        """Convert expense object to dictionary for audit trail"""
        return {
            'id': expense.id,
            'expense_date': expense.expense_date.isoformat() if expense.expense_date else None,
            'amount': float(expense.amount),
            'category': expense.category,
            'description': expense.description,
            'vendor': expense.vendor,
            'payment_mode': expense.payment_mode,
            'reference_no': expense.reference_no,
            'status': expense.status,
            'source_type': expense.source_type,
            'rvz_auto_approved': expense.rvz_auto_approved,
            'is_deleted': expense.is_deleted
        }
    
    @staticmethod
    def create_expense_rvz(
        db: Session,
        rvz_user: User,
        expense_date: date,
        amount: Decimal,
        category: str,
        description: str,
        vendor: Optional[str],
        payment_mode: str,
        reference_no: Optional[str],
        bill_filename: Optional[str] = None,
        bill_mime_type: Optional[str] = None,
        bill_size: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Expense:
        """
        RVZ creates expense - Auto-approved (supreme authority)
        """
        expense = Expense(
            expense_date=expense_date,
            amount=amount,
            category=category,
            description=description,
            vendor=vendor,
            payment_mode=payment_mode,
            reference_no=reference_no,
            bill_filename=bill_filename,
            bill_mime_type=bill_mime_type,
            bill_size=bill_size,
            notes=notes,
            created_by_id=rvz_user.id,
            source_type='rvz_manual',
            rvz_auto_approved=True,
            status='approved',
            rvz_approved_by_id=rvz_user.id,
            rvz_approved_at=datetime.now(),
            approved_by_id=rvz_user.id,
            approved_at=datetime.now()
        )
        
        db.add(expense)
        db.flush()
        
        RVZExpenseService.create_audit_event(
            db=db,
            expense_id=expense.id,
            actor_id=rvz_user.id,
            actor_role='RVZ ID',
            action='create',
            after_state=RVZExpenseService.expense_to_dict(expense),
            notes='RVZ created expense - auto-approved (supreme authority)'
        )
        
        return expense
    
    @staticmethod
    def approve_expense_rvz(
        db: Session,
        expense_id: int,
        rvz_user: User,
        notes: Optional[str] = None
    ) -> Expense:
        """
        RVZ approves Finance-created expense
        """
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.is_deleted == False
        ).first()
        
        if not expense:
            raise ValueError("Expense not found")
        
        if expense.status == 'approved':
            raise ValueError("Expense already approved")
        
        if expense.source_type == 'rvz_manual':
            raise ValueError("RVZ-created expenses are auto-approved")
        
        before_state = RVZExpenseService.expense_to_dict(expense)
        
        expense.status = 'approved'
        expense.rvz_approved_by_id = rvz_user.id
        expense.rvz_approved_at = datetime.now()
        expense.approved_by_id = rvz_user.id
        expense.approved_at = datetime.now()
        if notes:
            expense.notes = notes
        
        db.flush()
        
        RVZExpenseService.create_audit_event(
            db=db,
            expense_id=expense.id,
            actor_id=rvz_user.id,
            actor_role='RVZ ID',
            action='approve',
            before_state=before_state,
            after_state=RVZExpenseService.expense_to_dict(expense),
            notes=notes or 'RVZ approved Finance-created expense'
        )
        
        return expense
    
    @staticmethod
    def reject_expense_rvz(
        db: Session,
        expense_id: int,
        rvz_user: User,
        rejection_reason: str
    ) -> Expense:
        """
        RVZ rejects Finance-created expense
        """
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.is_deleted == False
        ).first()
        
        if not expense:
            raise ValueError("Expense not found")
        
        if expense.status == 'approved':
            raise ValueError("Cannot reject approved expense")
        
        if expense.source_type == 'rvz_manual':
            raise ValueError("Cannot reject RVZ-created expense")
        
        before_state = RVZExpenseService.expense_to_dict(expense)
        
        expense.status = 'rejected'
        expense.notes = rejection_reason
        
        db.flush()
        
        RVZExpenseService.create_audit_event(
            db=db,
            expense_id=expense.id,
            actor_id=rvz_user.id,
            actor_role='RVZ ID',
            action='reject',
            before_state=before_state,
            after_state=RVZExpenseService.expense_to_dict(expense),
            notes=rejection_reason
        )
        
        return expense
    
    @staticmethod
    def update_expense_rvz(
        db: Session,
        expense_id: int,
        rvz_user: User,
        updates: Dict[str, Any]
    ) -> Expense:
        """
        RVZ edits expense - No approval required (supreme authority)
        """
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.is_deleted == False
        ).first()
        
        if not expense:
            raise ValueError("Expense not found")
        
        before_state = RVZExpenseService.expense_to_dict(expense)
        
        allowed_fields = [
            'expense_date', 'amount', 'category', 'description',
            'vendor', 'payment_mode', 'reference_no', 'notes'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(expense, field, value)
        
        expense.updated_at = datetime.now()
        db.flush()
        
        RVZExpenseService.create_audit_event(
            db=db,
            expense_id=expense.id,
            actor_id=rvz_user.id,
            actor_role='RVZ ID',
            action='edit',
            before_state=before_state,
            after_state=RVZExpenseService.expense_to_dict(expense),
            notes='RVZ edited expense (supreme authority - no approval required)'
        )
        
        return expense
    
    @staticmethod
    def delete_expense_rvz(
        db: Session,
        expense_id: int,
        rvz_user: User,
        deletion_reason: str
    ) -> Expense:
        """
        RVZ soft-deletes expense with protection for award-linked expenses
        """
        expense = db.query(Expense).filter(
            Expense.id == expense_id
        ).first()
        
        if not expense:
            raise ValueError("Expense not found")
        
        if expense.is_deleted:
            raise ValueError("Expense already deleted")
        
        if expense.award_reference_id or expense.bonanza_reference_id:
            raise ValueError(
                "Cannot delete expense linked to award/bonanza. "
                "This expense is tied to procurement and must be retained for audit trail."
            )
        
        before_state = RVZExpenseService.expense_to_dict(expense)
        
        expense.is_deleted = True
        expense.deleted_by_id = rvz_user.id
        expense.deleted_at = datetime.now()
        expense.deletion_reason = deletion_reason
        
        db.flush()
        
        RVZExpenseService.create_audit_event(
            db=db,
            expense_id=expense.id,
            actor_id=rvz_user.id,
            actor_role='RVZ ID',
            action='delete',
            before_state=before_state,
            after_state=RVZExpenseService.expense_to_dict(expense),
            notes=deletion_reason
        )
        
        return expense
    
    @staticmethod
    def get_all_expenses(
        db: Session,
        status_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        include_deleted: bool = False
    ) -> List[Expense]:
        """
        Get all expenses with filters
        """
        query = db.query(Expense)
        
        if not include_deleted:
            query = query.filter(Expense.is_deleted == False)
        
        if status_filter:
            query = query.filter(Expense.status == status_filter)
        
        if source_filter:
            query = query.filter(Expense.source_type == source_filter)
        
        if category_filter:
            query = query.filter(Expense.category.like(f'%{category_filter}%'))
        
        if date_from:
            query = query.filter(Expense.expense_date >= date_from)
        
        if date_to:
            query = query.filter(Expense.expense_date <= date_to)
        
        return query.order_by(Expense.expense_date.desc()).all()
    
    @staticmethod
    def get_expense_by_id(db: Session, expense_id: int) -> Optional[Expense]:
        """Get single expense by ID"""
        return db.query(Expense).filter(Expense.id == expense_id).first()
    
    @staticmethod
    def get_audit_trail(db: Session, expense_id: int) -> List[ExpenseAuditEvent]:
        """Get complete audit trail for expense"""
        return db.query(ExpenseAuditEvent).filter(
            ExpenseAuditEvent.expense_id == expense_id
        ).order_by(ExpenseAuditEvent.created_at.desc()).all()
    
    @staticmethod
    def get_expense_summary(db: Session) -> Dict[str, Any]:
        """Get expense summary statistics for RVZ dashboard"""
        total_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False
        ).scalar() or 0
        
        pending_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False,
            Expense.status == 'pending'
        ).scalar() or 0
        
        approved_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False,
            Expense.status == 'approved'
        ).scalar() or 0
        
        total_amount = db.query(func.sum(Expense.amount)).filter(
            Expense.is_deleted == False,
            Expense.status == 'approved'
        ).scalar() or Decimal('0.00')
        
        auto_award_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False,
            Expense.source_type == 'auto_award'
        ).scalar() or 0
        
        rvz_created_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False,
            Expense.source_type == 'rvz_manual'
        ).scalar() or 0
        
        finance_created_count = db.query(func.count(Expense.id)).filter(
            Expense.is_deleted == False,
            Expense.source_type == 'finance_manual'
        ).scalar() or 0
        
        return {
            'total_expenses': total_count,
            'pending_approval': pending_count,
            'approved': approved_count,
            'total_amount': float(total_amount),
            'auto_award_expenses': auto_award_count,
            'rvz_created_expenses': rvz_created_count,
            'finance_created_expenses': finance_created_count
        }
    
    @staticmethod
    def create_award_procurement_expense(
        db: Session,
        award_reference_id: Optional[int],
        award_reference_type: Optional[str],
        bonanza_reference_id: Optional[int],
        bonanza_reference_type: Optional[str],
        actual_cost_paid: Decimal,
        expense_date: date,
        category: str,
        description: str,
        vendor: Optional[str],
        payment_mode: str,
        reference_no: Optional[str],
        rvz_user_id: str
    ) -> Expense:
        """
        Auto-create expense from award procurement
        DC Protocol: Staff processes payments. FK columns reference user table,
        so set to None when actor is staff. Staff identity captured in notes.
        """
        existing = db.query(Expense).filter(
            or_(
                and_(
                    Expense.award_reference_id == award_reference_id,
                    Expense.award_reference_type == award_reference_type
                ) if award_reference_id else False,
                and_(
                    Expense.bonanza_reference_id == bonanza_reference_id,
                    Expense.bonanza_reference_type == bonanza_reference_type
                ) if bonanza_reference_id else False
            ),
            Expense.source_type == 'auto_award'
        ).first()
        
        if existing:
            return existing
        
        is_mnr_user = db.query(User).filter(User.id == rvz_user_id).first() is not None
        
        expense = Expense(
            expense_date=expense_date,
            amount=actual_cost_paid,
            category=category,
            description=description,
            vendor=vendor,
            payment_mode=payment_mode,
            reference_no=reference_no,
            award_reference_id=award_reference_id,
            award_reference_type=award_reference_type,
            bonanza_reference_id=bonanza_reference_id,
            bonanza_reference_type=bonanza_reference_type,
            created_by_id=rvz_user_id if is_mnr_user else None,
            source_type='auto_award',
            rvz_auto_approved=True,
            status='approved',
            rvz_approved_by_id=rvz_user_id if is_mnr_user else None,
            rvz_approved_at=datetime.now(),
            approved_by_id=rvz_user_id if is_mnr_user else None,
            approved_at=datetime.now(),
            notes=f'Staff: {rvz_user_id}' if not is_mnr_user else None
        )
        
        db.add(expense)
        db.flush()
        
        if is_mnr_user:
            RVZExpenseService.create_audit_event(
                db=db,
                expense_id=expense.id,
                actor_id=rvz_user_id,
                actor_role='Staff',
                action='create',
                after_state=RVZExpenseService.expense_to_dict(expense),
                notes=f'Auto-created from award procurement: {description}'
            )
        
        return expense
