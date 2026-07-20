"""
RVZ Expense Management Endpoints - Supreme Authority
Full CRUD operations with dual approval workflow
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import os

from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.services.rvz_expense_service import RVZExpenseService

router = APIRouter(prefix="/rvz/expenses", tags=["RVZ Expenses"])


class ExpenseCreateRequest(BaseModel):
    expense_date: str
    amount: float
    category: str
    description: str
    vendor: Optional[str] = None
    payment_mode: str
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class ExpenseUpdateRequest(BaseModel):
    expense_date: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    payment_mode: Optional[str] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class ExpenseApproveRequest(BaseModel):
    notes: Optional[str] = None


class ExpenseRejectRequest(BaseModel):
    rejection_reason: str


class ExpenseDeleteRequest(BaseModel):
    deletion_reason: str


def validate_rvz_user(user_id: str, db: Session) -> User:
    """Validate RVZ ID access"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.user_type not in ['RVZ ID']:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Expense Management with supreme authority is exclusive to RVZ ID"
        )
    
    return user


@router.get("/summary")
async def get_expense_summary(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get expense summary statistics"""
    try:
        user = validate_rvz_user(user_id, db)
        summary = RVZExpenseService.get_expense_summary(db)
        
        return JSONResponse(content={
            "success": True,
            "data": summary
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_all_expenses(
    user_id: str = Query(...),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all expenses with filters"""
    try:
        user = validate_rvz_user(user_id, db)
        
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None
        
        expenses = RVZExpenseService.get_all_expenses(
            db=db,
            status_filter=status,
            source_filter=source,
            category_filter=category,
            date_from=date_from_obj,
            date_to=date_to_obj,
            include_deleted=include_deleted
        )
        
        expenses_data = []
        for exp in expenses:
            expenses_data.append({
                'id': exp.id,
                'expense_date': exp.expense_date.isoformat(),
                'amount': float(exp.amount),
                'category': exp.category,
                'description': exp.description,
                'vendor': exp.vendor,
                'payment_mode': exp.payment_mode,
                'reference_no': exp.reference_no,
                'status': exp.status,
                'source_type': exp.source_type,
                'rvz_auto_approved': exp.rvz_auto_approved,
                'created_by_id': exp.created_by_id,
                'created_at': exp.created_at.isoformat(),
                'rvz_approved_by_id': exp.rvz_approved_by_id,
                'rvz_approved_at': exp.rvz_approved_at.isoformat() if exp.rvz_approved_at else None,
                'is_deleted': exp.is_deleted,
                'deleted_at': exp.deleted_at.isoformat() if exp.deleted_at else None,
                'notes': exp.notes,
                'bill_filename': exp.bill_filename,
                'award_reference_id': exp.award_reference_id,
                'award_reference_type': exp.award_reference_type,
                'bonanza_reference_id': exp.bonanza_reference_id,
                'bonanza_reference_type': exp.bonanza_reference_type
            })
        
        return JSONResponse(content={
            "success": True,
            "count": len(expenses_data),
            "expenses": expenses_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{expense_id}")
async def get_expense_details(
    expense_id: int,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get single expense details with audit trail"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expense = RVZExpenseService.get_expense_by_id(db, expense_id)
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        audit_trail = RVZExpenseService.get_audit_trail(db, expense_id)
        
        audit_events = []
        for event in audit_trail:
            audit_events.append({
                'id': event.id,
                'actor_id': event.actor_id,
                'actor_role': event.actor_role,
                'action': event.action,
                'action_notes': event.action_notes,
                'created_at': event.created_at.isoformat()
            })
        
        return JSONResponse(content={
            "success": True,
            "expense": {
                'id': expense.id,
                'expense_date': expense.expense_date.isoformat(),
                'amount': float(expense.amount),
                'category': expense.category,
                'description': expense.description,
                'vendor': expense.vendor,
                'payment_mode': expense.payment_mode,
                'reference_no': expense.reference_no,
                'status': expense.status,
                'source_type': expense.source_type,
                'rvz_auto_approved': expense.rvz_auto_approved,
                'created_by_id': expense.created_by_id,
                'created_at': expense.created_at.isoformat(),
                'rvz_approved_by_id': expense.rvz_approved_by_id,
                'rvz_approved_at': expense.rvz_approved_at.isoformat() if expense.rvz_approved_at else None,
                'is_deleted': expense.is_deleted,
                'notes': expense.notes,
                'bill_filename': expense.bill_filename,
                'award_reference_id': expense.award_reference_id,
                'bonanza_reference_id': expense.bonanza_reference_id
            },
            "audit_trail": audit_events
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_expense(
    request: ExpenseCreateRequest,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """RVZ creates expense - Auto-approved (supreme authority)"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expense_date = datetime.strptime(request.expense_date, '%Y-%m-%d').date()
        
        expense = RVZExpenseService.create_expense_rvz(
            db=db,
            rvz_user=user,
            expense_date=expense_date,
            amount=Decimal(str(request.amount)),
            category=request.category,
            description=request.description,
            vendor=request.vendor,
            payment_mode=request.payment_mode,
            reference_no=request.reference_no,
            notes=request.notes
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Expense created successfully by RVZ (auto-approved - supreme authority)",
            "expense_id": expense.id,
            "status": expense.status
        })
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{expense_id}/upload-bill")
async def upload_rvz_expense_bill(
    expense_id: int,
    bill: UploadFile = File(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Upload bill/receipt for RVZ expense (Universal Upload: 5MB max, auto-compression)
    RVZ ID and Finance Admin can upload bills
    """
    from app.models.transaction import Expense
    
    # Validate user access (RVZ or Finance Admin)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.user_type not in ['RVZ ID', 'Finance Admin']:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Bill upload requires RVZ or Finance Admin access"
        )
    
    # Verify expense exists
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_deleted == False
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # DC Protocol: Validate file size BEFORE creating DB records
    file_content = await bill.read()
    file_size = len(file_content)
    bill.file.seek(0)  # Reset for UniversalUploadService (synchronous seek)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Universal Upload System: 5MB limit for images/documents
    MAX_FILE_SIZE = 5000000  # 5MB (will be auto-compressed)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({round(file_size/1024, 2)}KB) exceeds maximum allowed size (5MB)"
        )
    
    # Universal Upload System: DC Protocol atomic transaction
    from app.services.universal_upload_service import UniversalUploadService
    
    try:
        # Upload file using Universal Upload System
        # DC Protocol: defer_scheduler=True ensures compression job only scheduled AFTER db.commit()
        upload_result = await UniversalUploadService.handle_upload(
            file=bill,
            table_name='expense',
            record_id=expense.id,
            uploaded_by_id=user.id,
            uploaded_by_type='user',
            storage_dir='rvz_expense_bills',
            db=db,
            defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
        )
        
        # Update expense with bill file path
        expense.bill_filename = upload_result['file_name']
        
        # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
        try:
            import pytz
            from datetime import datetime
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='rvz_expense',
                entity_type='rvz_expense',
                entity_id=expense.id,
                attachment_id=expense.id,  # Use expense_id as attachment_id
                uploader_code=user.id,  # User.id IS the MNR ID
                original_filename=bill.filename,
                uploaded_at=uploaded_at_ist
            )
            
            expense.download_filename = download_name
            expense.uses_new_naming = True
        except HTTPException:
            raise
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate download filename for RVZ expense {expense.id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate semantic filename: {str(e)}")
        
        # DC Protocol: Single commit for expense update (atomic operation)
        # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Bill uploaded successfully",
            "bill_filename": upload_result['file_name'],
            "expense_id": expense.id
        })
        
    except HTTPException as e:
        # DC PROTOCOL: Preserve validation errors
        db.rollback()
        raise e
    except Exception as upload_error:
        # DC Protocol: Transaction rollback
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload bill: {str(upload_error)}"
        )


@router.get("/{expense_id}/bill/{filename}")
async def get_rvz_expense_bill(
    expense_id: int,
    filename: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Retrieve RVZ expense bill file
    Access: RVZ ID, Finance Admin, Super Admin
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.models.transaction import Expense
    
    # Validate user access
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.user_type not in ['RVZ ID', 'Finance Admin', 'Super Admin', 'Admin']:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Requires RVZ, Finance Admin, or Admin access."
        )
    
    # Verify expense exists
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_deleted == False
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # DC Protocol: Try Object Storage first (new uploads)
    from app.services.object_storage import storage_service
    from fastapi.responses import StreamingResponse
    import io
    
    # Determine content type
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'pdf': 'application/pdf'
    }
    media_type = content_types.get(ext, 'application/octet-stream')
    
    storage_path = f"rvz_expense_bills/{filename}"
    file_data = storage_service.download_file(storage_path)
    
    if file_data:
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    # Fallback: Try local storage (legacy files)
    file_path = Path(f"uploads/rvz_expense_bills/{expense_id}/{filename}")
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
    
    raise HTTPException(status_code=404, detail="Bill file not found")


@router.put("/{expense_id}/update")
async def update_expense(
    expense_id: int,
    request: ExpenseUpdateRequest,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """RVZ edits expense - No approval required (supreme authority)"""
    try:
        user = validate_rvz_user(user_id, db)
        
        updates = {}
        if request.expense_date:
            updates['expense_date'] = datetime.strptime(request.expense_date, '%Y-%m-%d').date()
        if request.amount is not None:
            updates['amount'] = Decimal(str(request.amount))
        if request.category:
            updates['category'] = request.category
        if request.description:
            updates['description'] = request.description
        if request.vendor is not None:
            updates['vendor'] = request.vendor
        if request.payment_mode:
            updates['payment_mode'] = request.payment_mode
        if request.reference_no is not None:
            updates['reference_no'] = request.reference_no
        if request.notes is not None:
            updates['notes'] = request.notes
        
        expense = RVZExpenseService.update_expense_rvz(
            db=db,
            expense_id=expense_id,
            rvz_user=user,
            updates=updates
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Expense updated by RVZ (no approval required - supreme authority)",
            "expense_id": expense.id
        })
        
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    request: ExpenseApproveRequest,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """RVZ approves Finance-created expense"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expense = RVZExpenseService.approve_expense_rvz(
            db=db,
            expense_id=expense_id,
            rvz_user=user,
            notes=request.notes
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Expense approved by RVZ (ID: {expense.id})",
            "expense_id": expense.id,
            "amount": float(expense.amount)
        })
        
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: int,
    request: ExpenseRejectRequest,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """RVZ rejects Finance-created expense"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expense = RVZExpenseService.reject_expense_rvz(
            db=db,
            expense_id=expense_id,
            rvz_user=user,
            rejection_reason=request.rejection_reason
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Expense rejected by RVZ (ID: {expense.id})",
            "expense_id": expense.id
        })
        
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{expense_id}/delete")
async def delete_expense(
    expense_id: int,
    request: ExpenseDeleteRequest,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """RVZ soft-deletes expense (protected if linked to awards)"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expense = RVZExpenseService.delete_expense_rvz(
            db=db,
            expense_id=expense_id,
            rvz_user=user,
            deletion_reason=request.deletion_reason
        )
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Expense deleted by RVZ (ID: {expense.id})",
            "expense_id": expense.id
        })
        
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending/list")
async def get_pending_expenses(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get all expenses pending RVZ approval (Finance-created)"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expenses = RVZExpenseService.get_all_expenses(
            db=db,
            status_filter='pending',
            source_filter='finance_manual'
        )
        
        expenses_data = []
        for exp in expenses:
            expenses_data.append({
                'id': exp.id,
                'expense_date': exp.expense_date.isoformat(),
                'amount': float(exp.amount),
                'category': exp.category,
                'description': exp.description,
                'vendor': exp.vendor,
                'payment_mode': exp.payment_mode,
                'created_by_id': exp.created_by_id,
                'created_at': exp.created_at.isoformat(),
                'notes': exp.notes
            })
        
        return JSONResponse(content={
            "success": True,
            "count": len(expenses_data),
            "pending_expenses": expenses_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-award/list")
async def get_auto_award_expenses(
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get all auto-created expenses from award procurement"""
    try:
        user = validate_rvz_user(user_id, db)
        
        expenses = RVZExpenseService.get_all_expenses(
            db=db,
            source_filter='auto_award'
        )
        
        expenses_data = []
        for exp in expenses:
            expenses_data.append({
                'id': exp.id,
                'expense_date': exp.expense_date.isoformat(),
                'amount': float(exp.amount),
                'category': exp.category,
                'description': exp.description,
                'vendor': exp.vendor,
                'award_reference_id': exp.award_reference_id,
                'award_reference_type': exp.award_reference_type,
                'bonanza_reference_id': exp.bonanza_reference_id,
                'bonanza_reference_type': exp.bonanza_reference_type,
                'created_at': exp.created_at.isoformat()
            })
        
        return JSONResponse(content={
            "success": True,
            "count": len(expenses_data),
            "auto_award_expenses": expenses_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
