"""
Signup Categories API Endpoints
DC Protocol: Categories are managed by RVZ and EA roles with strict company_id segregation
All admin endpoints require company_id query parameter (DC Protocol standard)
Authorization: Validates staff has access to requested company before any operation
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.database import get_db
from app.models.signup_category import SignupCategory, DEFAULT_SIGNUP_CATEGORIES
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from datetime import datetime
import pytz


router = APIRouter()


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def validate_company_access(db: Session, company_id: int, current_user: StaffEmployee):
    """
    DC Protocol: Validate that staff has access to the requested company.
    
    Authorization Rules:
    - VGK4U Supreme (hierarchy >= 150): Access to all companies
    - Key Leadership/HR/Leadership (hierarchy >= 85): Access to all companies
    - Other roles: Access DENIED - raise 403 Forbidden
    
    Returns the company if access is granted, raises HTTPException otherwise.
    """
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.id == company_id,
        AssociatedCompany.is_active == True
    ).first()
    
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ID {company_id} not found or inactive"
        )
    
    hierarchy_level = 0
    if current_user.role:
        hierarchy_level = current_user.role.hierarchy_level or 0
    
    if hierarchy_level >= 85:
        return company
    
    raise HTTPException(
        status_code=403,
        detail="Access denied: You do not have permission to manage signup categories. Requires Key Leadership, HR, or higher role."
    )


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    requires_documents: bool = False
    document_types: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    requires_documents: Optional[bool] = None
    document_types: Optional[str] = None


@router.get("/list")
async def get_categories(
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all signup categories (public endpoint for signup form)
    DC Protocol: Requires company_id parameter - public access for signup forms
    """
    query = db.query(SignupCategory).filter(SignupCategory.company_id == company_id)
    
    if not include_inactive:
        query = query.filter(SignupCategory.is_active == True)
    
    categories = query.order_by(SignupCategory.display_order, SignupCategory.name).all()
    
    return {
        "success": True,
        "categories": [c.to_dict() for c in categories],
        "total": len(categories)
    }


@router.get("/admin")
async def get_categories_admin(
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    include_inactive: bool = True,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all signup categories for admin management
    DC Protocol: RVZ and EA access only, strictly filtered by company_id query param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    query = db.query(SignupCategory).filter(SignupCategory.company_id == company_id)
    
    if not include_inactive:
        query = query.filter(SignupCategory.is_active == True)
    
    categories = query.order_by(SignupCategory.display_order, SignupCategory.name).all()
    
    active_count = db.query(func.count(SignupCategory.id)).filter(
        SignupCategory.company_id == company_id,
        SignupCategory.is_active == True
    ).scalar() or 0
    
    inactive_count = db.query(func.count(SignupCategory.id)).filter(
        SignupCategory.company_id == company_id,
        SignupCategory.is_active == False
    ).scalar() or 0
    
    return {
        "success": True,
        "categories": [c.to_dict() for c in categories],
        "total": len(categories),
        "active_count": active_count,
        "inactive_count": inactive_count,
        "company_id": company_id
    }


@router.post("/create")
async def create_category(
    data: CategoryCreate,
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a new signup category
    DC Protocol: RVZ and EA access only, strictly scoped to company_id query param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    existing = db.query(SignupCategory).filter(
        SignupCategory.company_id == company_id,
        ((SignupCategory.name == data.name) | (SignupCategory.slug == data.slug))
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name or slug already exists for your company")
    
    category = SignupCategory(
        company_id=company_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        icon=data.icon,
        display_order=data.display_order,
        requires_documents=data.requires_documents,
        document_types=data.document_types,
        created_by_id=current_user.id
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "message": "Category created successfully",
        "category": category.to_dict()
    }


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update a signup category
    DC Protocol: RVZ and EA access only, validates company ownership via company_id param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    category = db.query(SignupCategory).filter_by(id=category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied: Category belongs to different company")
    
    if data.name is not None:
        existing = db.query(SignupCategory).filter(
            SignupCategory.company_id == company_id,
            SignupCategory.name == data.name,
            SignupCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        category.name = data.name
    
    if data.slug is not None:
        existing = db.query(SignupCategory).filter(
            SignupCategory.company_id == company_id,
            SignupCategory.slug == data.slug,
            SignupCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category with this slug already exists")
        category.slug = data.slug
    
    if data.description is not None:
        category.description = data.description
    if data.icon is not None:
        category.icon = data.icon
    if data.display_order is not None:
        category.display_order = data.display_order
    if data.is_active is not None:
        category.is_active = data.is_active
    if data.requires_documents is not None:
        category.requires_documents = data.requires_documents
    if data.document_types is not None:
        category.document_types = data.document_types
    
    db.commit()
    db.refresh(category)
    
    return {
        "success": True,
        "message": "Category updated successfully",
        "category": category.to_dict()
    }


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a signup category (set inactive)
    DC Protocol: RVZ and EA access only, validates company ownership via company_id param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    category = db.query(SignupCategory).filter_by(id=category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied: Category belongs to different company")
    
    category.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": f"Category '{category.name}' deactivated"
    }


@router.post("/{category_id}/toggle")
async def toggle_category(
    category_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Toggle category active/inactive status
    DC Protocol: RVZ and EA access only, validates company ownership via company_id param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    category = db.query(SignupCategory).filter_by(id=category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied: Category belongs to different company")
    
    category.is_active = not category.is_active
    db.commit()
    
    status = "activated" if category.is_active else "deactivated"
    return {
        "success": True,
        "message": f"Category '{category.name}' {status}",
        "is_active": category.is_active
    }


@router.post("/reorder")
async def reorder_categories(
    request: Request,
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reorder categories by updating display_order
    DC Protocol: RVZ and EA access only, strictly scoped to company_id query param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    body = await request.json()
    order_list = body.get('order', [])
    
    if not order_list:
        raise HTTPException(status_code=400, detail="Order list is required")
    
    for cat_id in order_list:
        category = db.query(SignupCategory).filter_by(id=cat_id).first()
        if category and category.company_id != company_id:
            raise HTTPException(status_code=403, detail=f"Access denied: Category {cat_id} belongs to different company")
    
    for i, cat_id in enumerate(order_list):
        category = db.query(SignupCategory).filter(
            SignupCategory.id == cat_id,
            SignupCategory.company_id == company_id
        ).first()
        if category:
            category.display_order = i + 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reordered {len(order_list)} categories"
    }


@router.post("/seed-defaults")
async def seed_default_categories(
    company_id: int = Query(..., description="Company ID for DC Protocol filtering"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Seed default signup categories
    DC Protocol: RVZ and EA access only, strictly scoped to company_id query param
    Authorization: Validates staff has access to the requested company
    """
    validate_company_access(db, company_id, current_user)
    
    created_count = 0
    
    for cat in DEFAULT_SIGNUP_CATEGORIES:
        existing = db.query(SignupCategory).filter(
            SignupCategory.company_id == company_id,
            SignupCategory.slug == cat['slug']
        ).first()
        if not existing:
            db.add(SignupCategory(
                company_id=company_id,
                name=cat['name'],
                slug=cat['slug'],
                description=cat['description'],
                icon=cat['icon'],
                display_order=cat['display_order'],
                created_by_id=current_user.id
            ))
            created_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Seeded {created_count} default categories",
        "created_count": created_count
    }
