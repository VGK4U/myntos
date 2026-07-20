"""
Expense & Income Category Management — In & Out Cat.
Hierarchical category system: Main Category → Sub Category
DC Protocol: JWT-based authentication - supports both Staff and MNR tokens
DC Protocol Dec 2025: Updated to support staff portal access
DC Protocol May 2026: Added Income Category (In & Out Cat.) support
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.staff import StaffEmployee
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter()

class MainCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SubCategoryCreate(BaseModel):
    name: str
    parent_id: int
    description: Optional[str] = None

def validate_super_admin_or_rvz(user: User) -> User:
    """Validate Super Admin or RVZ ID access"""
    if user.user_type not in ['Super Admin', 'RVZ ID', 'Admin']:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: Category Management is exclusive to Super Admin, Admin, and RVZ ID"
        )
    return user

def get_user_id_from_staff_or_mnr(request: Request, db: Session) -> str:
    """
    DC Protocol: Hybrid authentication - tries staff token first, falls back to MNR token.
    Returns a string user ID suitable for created_by_id field.
    NOTE: get_current_user is async/DI-only; MNR fallback uses SecurityManager directly (sync).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    # 1. Try staff token (synchronous)
    try:
        staff_user = get_current_staff_user(request, db)
        return f"STAFF_{staff_user.emp_code}"
    except HTTPException:
        pass

    # 2. MNR fallback — synchronous inline decode (get_current_user is async DI-only)
    try:
        from app.core.security import SecurityManager
        token = auth_header.split(" ")[1]
        payload = SecurityManager.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        mnr_user = SecurityManager.get_user_by_id(db, user_id)
        if not mnr_user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        validate_super_admin_or_rvz(mnr_user)
        return str(mnr_user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

@router.get("/expense-categories", response_class=HTMLResponse)
async def expense_categories_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Expense Category Management page - Super Admin & RVZ ID ONLY"""
    try:
        validate_super_admin_or_rvz(current_user)
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>In & Out Cat. - MNR</title>
            <meta http-equiv="refresh" content="0;url=/admin/expense-categories">
        </head>
        <body>
            <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
                <h2>Redirecting to Frontend...</h2>
                <p>This page is now served by the frontend.</p>
                <p>If not redirected, <a href="/admin/expense-categories">click here</a>.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────
# EXPENSE CATEGORY CRUD
# ─────────────────────────────────────────────────────────────

@router.post("/expense-categories/main/create")
async def create_main_category(
    request: Request,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create new expense main category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        existing = db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.name == data.name.strip(),
            ExpenseMainCategory.is_active == True
        ).first()
        
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Main category '{data.name}' already exists"}
            )
        
        main_category = ExpenseMainCategory(
            name=data.name.strip(),
            description=data.description,
            created_by_id=user_id
        )
        
        db.add(main_category)
        db.commit()
        db.refresh(main_category)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Main category '{data.name}' created successfully",
            "category_id": main_category.id
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.post("/expense-categories/sub/create")
async def create_sub_category(
    request: Request,
    data: SubCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create new expense sub category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        main_category = db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.id == data.parent_id,
            ExpenseMainCategory.is_active == True
        ).first()
        
        if not main_category:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Main category not found"}
            )
        
        existing = db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.name == data.name.strip(),
            ExpenseSubCategory.main_category_id == data.parent_id,
            ExpenseSubCategory.is_active == True
        ).first()
        
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Sub category '{data.name}' already exists in this main category"}
            )
        
        sub_category = ExpenseSubCategory(
            name=data.name.strip(),
            description=data.description,
            main_category_id=data.parent_id,
            created_by_id=user_id
        )
        
        db.add(sub_category)
        db.commit()
        db.refresh(sub_category)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Sub category '{data.name}' created under '{main_category.name}'",
            "category_id": sub_category.id
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.post("/expense-categories/main/update/{category_id}")
async def update_main_category(
    request: Request,
    category_id: int,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Update expense main category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        category = db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.id == category_id,
            ExpenseMainCategory.is_active == True
        ).first()
        
        if not category:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Main category not found"}
            )
        
        category.name = data.name.strip()
        category.description = data.description
        category.updated_by_id = user_id
        category.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Main category updated to '{data.name}'"
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.post("/expense-categories/sub/update/{category_id}")
async def update_sub_category(
    request: Request,
    category_id: int,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Update expense sub category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        category = db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.id == category_id,
            ExpenseSubCategory.is_active == True
        ).first()
        
        if not category:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Sub category not found"}
            )
        
        category.name = data.name.strip()
        category.description = data.description
        category.updated_by_id = user_id
        category.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Sub category updated to '{data.name}'"
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.delete("/expense-categories/main/{category_id}")
async def delete_main_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete expense main category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        category = db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.id == category_id,
            ExpenseMainCategory.is_active == True
        ).first()
        
        if not category:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Main category not found"}
            )
        
        sub_count = db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.main_category_id == category_id,
            ExpenseSubCategory.is_active == True
        ).count()
        
        if sub_count > 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Cannot delete. {sub_count} sub-categories still exist."}
            )
        
        category.is_active = False
        category.updated_by_id = user_id
        category.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Main category '{category.name}' deleted"
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.delete("/expense-categories/sub/{category_id}")
async def delete_sub_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete expense sub category"""
    try:
        user_id = get_user_id_from_staff_or_mnr(request, db)
        
        category = db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.id == category_id,
            ExpenseSubCategory.is_active == True
        ).first()
        
        if not category:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Sub category not found"}
            )
        
        category.is_active = False
        category.updated_by_id = user_id
        category.updated_at = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Sub category '{category.name}' deleted"
        })
            
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.get("/expense-categories/list")
async def list_categories(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all active expense & income categories — used by ExpCatPicker and journal voucher"""
    try:
        get_user_id_from_staff_or_mnr(request, db)
        main_categories = db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.is_active == True
        ).order_by(ExpenseMainCategory.name).all()
        
        main_list = []
        sub_list = []
        
        for main_cat in main_categories:
            main_list.append({
                'id': main_cat.id,
                'name': main_cat.name
            })
            
            sub_categories = db.query(ExpenseSubCategory).filter(
                ExpenseSubCategory.main_category_id == main_cat.id,
                ExpenseSubCategory.is_active == True
            ).order_by(ExpenseSubCategory.name).all()
            
            for sub in sub_categories:
                sub_list.append({
                    'id': sub.id,
                    'name': sub.name,
                    'parent_id': main_cat.id
                })

        # --- Income categories ---
        from app.models.income_category import IncomeMainCategory, IncomeSubCategory

        inc_main_list = []
        inc_sub_list = []

        inc_mains = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.is_active == True
        ).order_by(IncomeMainCategory.name).all()

        for im in inc_mains:
            inc_main_list.append({'id': im.id, 'name': im.name})
            inc_subs = db.query(IncomeSubCategory).filter(
                IncomeSubCategory.main_category_id == im.id,
                IncomeSubCategory.is_active == True
            ).order_by(IncomeSubCategory.name).all()
            for s in inc_subs:
                inc_sub_list.append({'id': s.id, 'name': s.name, 'parent_id': im.id})
        
        return JSONResponse(content={
            "success": True,
            "main_categories": main_list,
            "sub_categories": sub_list,
            "income_main_categories": inc_main_list,
            "income_sub_categories": inc_sub_list
        })
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ─────────────────────────────────────────────────────────────
# INCOME CATEGORY CRUD
# ─────────────────────────────────────────────────────────────

@router.post("/income-categories/main/create")
async def create_income_main_category(
    request: Request,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create new income main category"""
    try:
        from app.models.income_category import IncomeMainCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        existing = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.name == data.name.strip(),
            IncomeMainCategory.is_active == True
        ).first()

        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Income category '{data.name}' already exists"}
            )

        cat = IncomeMainCategory(
            name=data.name.strip(),
            description=data.description,
            created_by_id=user_id
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

        return JSONResponse(content={
            "success": True,
            "message": f"Income category '{data.name}' created successfully",
            "category_id": cat.id
        })
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/income-categories/sub/create")
async def create_income_sub_category(
    request: Request,
    data: SubCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create new income sub category"""
    try:
        from app.models.income_category import IncomeMainCategory, IncomeSubCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        main_cat = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.id == data.parent_id,
            IncomeMainCategory.is_active == True
        ).first()

        if not main_cat:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Income main category not found"}
            )

        existing = db.query(IncomeSubCategory).filter(
            IncomeSubCategory.name == data.name.strip(),
            IncomeSubCategory.main_category_id == data.parent_id,
            IncomeSubCategory.is_active == True
        ).first()

        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Sub category '{data.name}' already exists in this main category"}
            )

        sub = IncomeSubCategory(
            name=data.name.strip(),
            description=data.description,
            main_category_id=data.parent_id,
            created_by_id=user_id
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        return JSONResponse(content={
            "success": True,
            "message": f"Sub category '{data.name}' created under '{main_cat.name}'",
            "category_id": sub.id
        })
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/income-categories/main/update/{category_id}")
async def update_income_main_category(
    request: Request,
    category_id: int,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Update income main category"""
    try:
        from app.models.income_category import IncomeMainCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        cat = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.id == category_id,
            IncomeMainCategory.is_active == True
        ).first()

        if not cat:
            return JSONResponse(status_code=404, content={"success": False, "message": "Income main category not found"})

        cat.name = data.name.strip()
        cat.description = data.description
        cat.updated_by_id = user_id
        cat.updated_at = datetime.utcnow()
        db.commit()

        return JSONResponse(content={"success": True, "message": f"Category updated to '{data.name}'"})
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/income-categories/sub/update/{category_id}")
async def update_income_sub_category(
    request: Request,
    category_id: int,
    data: MainCategoryCreate,
    db: Session = Depends(get_db)
):
    """Update income sub category"""
    try:
        from app.models.income_category import IncomeSubCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        cat = db.query(IncomeSubCategory).filter(
            IncomeSubCategory.id == category_id,
            IncomeSubCategory.is_active == True
        ).first()

        if not cat:
            return JSONResponse(status_code=404, content={"success": False, "message": "Income sub category not found"})

        cat.name = data.name.strip()
        cat.description = data.description
        cat.updated_by_id = user_id
        cat.updated_at = datetime.utcnow()
        db.commit()

        return JSONResponse(content={"success": True, "message": f"Sub category updated to '{data.name}'"})
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.delete("/income-categories/main/{category_id}")
async def delete_income_main_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete income main category"""
    try:
        from app.models.income_category import IncomeMainCategory, IncomeSubCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        cat = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.id == category_id,
            IncomeMainCategory.is_active == True
        ).first()

        if not cat:
            return JSONResponse(status_code=404, content={"success": False, "message": "Income main category not found"})

        sub_count = db.query(IncomeSubCategory).filter(
            IncomeSubCategory.main_category_id == category_id,
            IncomeSubCategory.is_active == True
        ).count()

        if sub_count > 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Cannot delete. {sub_count} sub-categories still exist."}
            )

        cat.is_active = False
        cat.updated_by_id = user_id
        cat.updated_at = datetime.utcnow()
        db.commit()

        return JSONResponse(content={"success": True, "message": f"Income category '{cat.name}' deleted"})
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.delete("/income-categories/sub/{category_id}")
async def delete_income_sub_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete income sub category"""
    try:
        from app.models.income_category import IncomeSubCategory
        user_id = get_user_id_from_staff_or_mnr(request, db)

        cat = db.query(IncomeSubCategory).filter(
            IncomeSubCategory.id == category_id,
            IncomeSubCategory.is_active == True
        ).first()

        if not cat:
            return JSONResponse(status_code=404, content={"success": False, "message": "Income sub category not found"})

        cat.is_active = False
        cat.updated_by_id = user_id
        cat.updated_at = datetime.utcnow()
        db.commit()

        return JSONResponse(content={"success": True, "message": f"Sub category '{cat.name}' deleted"})
    except HTTPException as he:
        db.rollback()
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.get("/income-categories/list")
async def list_income_categories(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all active income categories — direct access endpoint"""
    try:
        from app.models.income_category import IncomeMainCategory, IncomeSubCategory
        get_user_id_from_staff_or_mnr(request, db)

        mains = db.query(IncomeMainCategory).filter(
            IncomeMainCategory.is_active == True
        ).order_by(IncomeMainCategory.name).all()

        main_list = []
        sub_list = []

        for m in mains:
            main_list.append({'id': m.id, 'name': m.name, 'description': m.description})
            subs = db.query(IncomeSubCategory).filter(
                IncomeSubCategory.main_category_id == m.id,
                IncomeSubCategory.is_active == True
            ).order_by(IncomeSubCategory.name).all()
            for s in subs:
                sub_list.append({'id': s.id, 'name': s.name, 'parent_id': m.id, 'description': s.description})

        return JSONResponse(content={
            "success": True,
            "main_categories": main_list,
            "sub_categories": sub_list
        })
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.get("/expense-categories/amounts-summary")
async def expense_amounts_summary(
    request: Request,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Return total expense amounts grouped by main and sub category — DC-EXPCAT-AMT-001"""
    try:
        get_user_id_from_staff_or_mnr(request, db)
        from app.models.staff_accounts import ExpenseEntry
        from sqlalchemy import func as _func

        q_main = (
            db.query(
                ExpenseEntry.main_category_id,
                _func.sum(ExpenseEntry.amount).label("total"),
                _func.count(ExpenseEntry.id).label("count")
            )
            .filter(ExpenseEntry.main_category_id.isnot(None))
        )
        q_sub = (
            db.query(
                ExpenseEntry.sub_category_id,
                _func.sum(ExpenseEntry.amount).label("total"),
                _func.count(ExpenseEntry.id).label("count")
            )
            .filter(ExpenseEntry.sub_category_id.isnot(None))
        )
        if company_id:
            q_main = q_main.filter(ExpenseEntry.company_id == company_id)
            q_sub  = q_sub.filter(ExpenseEntry.company_id == company_id)

        rows_main = q_main.group_by(ExpenseEntry.main_category_id).all()
        rows_sub  = q_sub.group_by(ExpenseEntry.sub_category_id).all()

        return JSONResponse(content={
            "success": True,
            "main": {str(r.main_category_id): {"total": float(r.total or 0), "count": r.count} for r in rows_main},
            "sub":  {str(r.sub_category_id):  {"total": float(r.total or 0), "count": r.count} for r in rows_sub}
        })
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.get("/income-categories/amounts-summary")
async def income_amounts_summary(
    request: Request,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Return total income amounts grouped by main and sub income category via JournalVoucher tags — DC-INCCAT-AMT-001"""
    try:
        get_user_id_from_staff_or_mnr(request, db)
        from app.models.staff_accounts import JournalVoucher
        from app.models.income_category import IncomeSubCategory
        from sqlalchemy import func as _func

        q = (
            db.query(
                JournalVoucher.income_category_id,
                _func.sum(JournalVoucher.amount).label("total"),
                _func.count(JournalVoucher.id).label("count")
            )
            .filter(
                JournalVoucher.income_category_id.isnot(None),
                JournalVoucher.status == 'POSTED'
            )
        )
        if company_id:
            q = q.filter(JournalVoucher.company_id == company_id)

        rows_sub = q.group_by(JournalVoucher.income_category_id).all()

        sub_result = {str(r.income_category_id): {"total": float(r.total or 0), "count": r.count} for r in rows_sub}

        sub_ids = [r.income_category_id for r in rows_sub]
        main_map: dict = {}
        if sub_ids:
            subs = db.query(IncomeSubCategory).filter(IncomeSubCategory.id.in_(sub_ids)).all()
            sub_to_main = {s.id: s.main_category_id for s in subs}
            for r in rows_sub:
                mid = sub_to_main.get(r.income_category_id)
                if mid:
                    key = str(mid)
                    if key not in main_map:
                        main_map[key] = {"total": 0.0, "count": 0}
                    main_map[key]["total"] += float(r.total or 0)
                    main_map[key]["count"] += r.count

        return JSONResponse(content={
            "success": True,
            "main": main_map,
            "sub":  sub_result
        })
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
