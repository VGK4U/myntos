"""
Expense Management System - Finance Admin creates, Super Admin approves
Complete expense tracking with bill uploads and approval workflow
Uses hierarchical categories from ExpenseMainCategory & ExpenseSubCategory
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.models.transaction import Expense
from app.models.user import User
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid

router = APIRouter(prefix="/expense-management", tags=["Expense Management"])


class ExpenseCreate(BaseModel):
    user_id: str
    expense_date: str
    amount: float
    category: str
    description: str
    vendor: Optional[str] = None
    payment_mode: str
    reference_no: Optional[str] = None


class ExpenseApprove(BaseModel):
    notes: Optional[str] = None


def validate_finance_admin(user_id: str, db: Session) -> User:
    """Validate Finance Admin access"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.user_type not in ['Finance Admin']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Expense Creation is exclusive to Finance Admin"
    #     )
    
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def expense_dashboard(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Expense Management Dashboard - Finance Admin"""
    try:
        user = validate_finance_admin(user_id, db)
        
        total_expenses = db.query(func.count(Expense.id)).filter(
            Expense.created_by_id == user_id,
            Expense.is_deleted == False
        ).scalar() or 0
        
        pending_expenses = db.query(func.count(Expense.id)).filter(
            Expense.created_by_id == user_id,
            Expense.status == 'pending',
            Expense.is_deleted == False
        ).scalar() or 0
        
        approved_expenses = db.query(func.count(Expense.id)).filter(
            Expense.created_by_id == user_id,
            Expense.status == 'approved',
            Expense.is_deleted == False
        ).scalar() or 0
        
        total_amount = db.query(func.sum(Expense.amount)).filter(
            Expense.created_by_id == user_id,
            Expense.is_deleted == False
        ).scalar() or Decimal('0.00')
        
        recent_expenses = db.query(Expense).filter(
            Expense.created_by_id == user_id,
            Expense.is_deleted == False
        ).order_by(Expense.expense_date.desc()).limit(10).all()
        
        # Frontend-only route - redirect to frontend
        from fastapi.responses import HTMLResponse
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Expense Dashboard - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/dashboard">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/dashboard">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/create-form", response_class=HTMLResponse)
async def expense_create_form(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Expense Creation Form - Finance Admin ONLY"""
    try:
        validate_finance_admin(user_id, db)
        
        # Frontend-only route - redirect to frontend
        from fastapi.responses import HTMLResponse
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Create Expense - MNR</title>
            <meta http-equiv="refresh" content="0;url=http://127.0.0.1:5000/create-form">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="http://127.0.0.1:5000/create-form">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db)
):
    """
    Finance Admin creates expense record - uses hierarchical categories
    """
    try:
        user = validate_finance_admin(data.user_id, db)
        
        # Validate payment mode
        valid_payment_modes = ['Cash', 'Bank Transfer', 'UPI', 'Credit Card', 'Debit Card', 'Cheque']
        if data.payment_mode not in valid_payment_modes:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Invalid payment mode. Must be one of: {', '.join(valid_payment_modes)}"}
            )
        
        # Parse expense date
        try:
            expense_date = datetime.strptime(data.expense_date, '%Y-%m-%d')
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}
            )
        
        # Validate amount
        if data.amount <= 0 or data.amount > 999999.99:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Amount must be between ₹0.01 and ₹9,99,999.99"}
            )
        
        expense = Expense(
            expense_date=expense_date,
            amount=Decimal(str(data.amount)),
            category=data.category,
            description=data.description.strip(),
            vendor=data.vendor.strip() if data.vendor else None,
            payment_mode=data.payment_mode,
            reference_no=data.reference_no.strip() if data.reference_no else None,
            created_by_id=user.id,
            status='pending'
        )
        
        db.add(expense)
        db.commit()
        db.refresh(expense)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Expense created successfully! ₹{data.amount} - {data.category}",
            "expense_id": expense.id
        })
        
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/{expense_id}/upload-bill")
async def upload_expense_bill(
    expense_id: int,
    bill: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Upload bill/receipt for expense (Universal Upload: 5MB max, auto-compression)
    Finance Admin only
    """
    # Verify Finance Admin access
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: Bill upload is exclusive to Finance Admin"
    #     )
    
    # Verify expense exists and belongs to current user
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_deleted == False
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.created_by_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only upload bills for your own expenses"
        )
    
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
            uploaded_by_id=current_user.id,
            uploaded_by_type='user',
            storage_dir='expense_bills',
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
                segment_key='expense_bill',
                entity_type='expense',
                entity_id=expense.id,
                attachment_id=expense.id,  # Use expense_id as attachment_id
                uploader_code=current_user.id,  # User.id IS the MNR ID
                original_filename=bill.filename,
                uploaded_at=uploaded_at_ist
            )
            
            expense.download_filename = download_name
            expense.uses_new_naming = True
        except HTTPException:
            raise
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate download filename for expense {expense.id}: {str(e)}")
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
async def get_expense_bill(
    expense_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Retrieve expense bill file
    Access: Finance Admin (own expenses), Super Admin, RVZ ID
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    
    # Verify expense exists
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_deleted == False
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Check access permissions
    is_owner = expense.created_by_id == current_user.id
    is_admin = (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ['Super Admin', 'RVZ ID', 'Admin']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_owner or is_admin):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access denied. You can only view bills for your own expenses."
    #     )
    
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
    
    storage_path = f"expense_bills/{filename}"
    file_data = storage_service.download_file(storage_path)
    
    if file_data:
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    # Fallback: Try local storage (legacy files)
    file_path = Path(f"uploads/expense_bills/{expense_id}/{filename}")
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
    
    raise HTTPException(status_code=404, detail="Bill file not found")


@router.get("/list")
async def list_expenses(
    status: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    List all expenses (filtered by status, category, date range)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(Expense).filter(Expense.is_deleted == False)
    
    if status:
        query = query.filter(Expense.status == status)
    
    if category:
        query = query.filter(Expense.category == category)
    
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(
            and_(
                Expense.expense_date >= start,
                Expense.expense_date <= end
            )
        )
    
    expenses = query.order_by(Expense.expense_date.desc()).limit(limit).all()
    
    return {
        "success": True,
        "expenses": [
            {
                "id": e.id,
                "expense_date": e.expense_date.strftime('%Y-%m-%d'),
                "amount": float(e.amount),
                "category": e.category,
                "description": e.description,
                "vendor": e.vendor,
                "payment_mode": e.payment_mode,
                "reference_no": e.reference_no,
                "bill_filename": e.bill_filename,
                "created_by_id": e.created_by_id,
                "approved_by_id": e.approved_by_id,
                "status": e.status,
                "approved_at": e.approved_at.strftime('%Y-%m-%d %H:%M:%S') if e.approved_at else None,
                "notes": e.notes
            }
            for e in expenses
        ]
    }


@router.get("/pending-approvals")
async def pending_approvals(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Super Admin views pending expense approvals
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Super Admin access required")
    
    pending = db.query(Expense).filter(
        and_(
            Expense.status == 'pending',
            Expense.is_deleted == False
        )
    ).order_by(Expense.expense_date.desc()).all()
    
    return {
        "success": True,
        "pending_approvals": [
            {
                "id": e.id,
                "expense_date": e.expense_date.strftime('%Y-%m-%d'),
                "amount": float(e.amount),
                "category": e.category,
                "description": e.description,
                "vendor": e.vendor,
                "payment_mode": e.payment_mode,
                "reference_no": e.reference_no,
                "bill_filename": e.bill_filename,
                "created_by_id": e.created_by_id
            }
            for e in pending
        ]
    }


@router.post("/approve/{expense_id}")
async def approve_expense(
    expense_id: int,
    data: ExpenseApprove,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Super Admin approves expense
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Super Admin access required")
    
    expense = db.query(Expense).filter(
        and_(Expense.id == expense_id, Expense.is_deleted == False)
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Cannot approve expense with status: {expense.status}")
    
    expense.status = 'approved'
    expense.approved_by_id = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.notes = data.notes
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Expense of ₹{expense.amount} approved successfully"
    }


@router.post("/reject/{expense_id}")
async def reject_expense(
    expense_id: int,
    notes: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Super Admin rejects expense
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Super Admin access required")
    
    expense = db.query(Expense).filter(
        and_(Expense.id == expense_id, Expense.is_deleted == False)
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Cannot reject expense with status: {expense.status}")
    
    expense.status = 'rejected'
    expense.approved_by_id = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.notes = notes
    
    db.commit()
    
    return {
        "success": True,
        "message": "Expense rejected"
    }


@router.get("/{expense_id}")
async def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get detailed expense information
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    expense = db.query(Expense).filter(
        and_(Expense.id == expense_id, Expense.is_deleted == False)
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {
        "success": True,
        "expense": {
            "id": expense.id,
            "expense_date": expense.expense_date.strftime('%Y-%m-%d'),
            "amount": float(expense.amount),
            "category": expense.category,
            "description": expense.description,
            "vendor": expense.vendor,
            "payment_mode": expense.payment_mode,
            "reference_no": expense.reference_no,
            "bill_filename": expense.bill_filename,
            "bill_mime_type": expense.bill_mime_type,
            "bill_size": expense.bill_size,
            "created_by_id": expense.created_by_id,
            "approved_by_id": expense.approved_by_id,
            "status": expense.status,
            "approved_at": expense.approved_at.strftime('%Y-%m-%d %H:%M:%S') if expense.approved_at else None,
            "notes": expense.notes,
            "created_at": expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": expense.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    }


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Soft delete expense (Finance Admin only, only if pending)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Finance Admin access required")
    
    expense = db.query(Expense).filter(
        and_(Expense.id == expense_id, Expense.is_deleted == False)
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.status != 'pending':
        raise HTTPException(status_code=403, detail="Can only delete pending expenses")
    
    expense.is_deleted = True
    db.commit()
    
    return {
        "success": True,
        "message": "Expense deleted successfully"
    }


@router.get("/reports/summary")
async def expense_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Expense summary report by category and status - Hybrid auth for frontend compatibility
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'Admin', 'RVZ ID']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse date range
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
    
    expenses = db.query(Expense).filter(
        and_(
            Expense.expense_date >= start,
            Expense.expense_date <= end,
            Expense.is_deleted == False
        )
    ).all()
    
    # Calculate totals by category
    by_category = {}
    by_status = {
        'pending': 0,
        'approved': 0,
        'rejected': 0
    }
    
    for expense in expenses:
        # By category
        if expense.category not in by_category:
            by_category[expense.category] = 0
        if expense.status == 'approved':
            by_category[expense.category] += float(expense.amount)
        
        # By status
        if expense.status in by_status:
            by_status[expense.status] += float(expense.amount)
    
    total_expenses = sum(float(e.amount) for e in expenses if e.status == 'approved')
    
    return {
        "success": True,
        "period": {
            "start_date": start.strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d')
        },
        "totals": {
            "total_approved_expenses": total_expenses,
            "total_pending": by_status['pending'],
            "total_rejected": by_status['rejected'],
            "total_records": len(expenses)
        },
        "by_category": by_category,
        "by_status": by_status
    }
