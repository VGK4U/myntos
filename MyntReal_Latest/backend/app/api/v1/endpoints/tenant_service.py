"""
Tenant Service Module Endpoints (DC Protocol Oct 2026)
SaaS Tenant Multi-Company Service Management:
- Dynamic Service Categories derived & synced with Tenant Sign-up Categories
- Strict company_id & tenant_id data isolation
- Service Queue, Ticket Intake, Spares/Procurement workflow, and Executive Service Dashboard
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func, desc

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.ticket import ServiceTicket
from app.models.signup_category import SignupCategory, DEFAULT_SIGNUP_CATEGORIES
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.phone_otp import normalize_phone_10
from app.utils.name_formatter import format_proper_name

logger = logging.getLogger(__name__)
router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _get_company_id(current_user: StaffEmployee) -> int:
    company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Tenant context missing for user.")
    return company_id


def _generate_ticket_code(db: Session, prefix: str = "SRV") -> str:
    """Generate sequential ticket code: SRV-YYMM-XXXX"""
    now = datetime.now(IST)
    yymm = now.strftime('%y%m')
    full_prefix = f"{prefix}-{yymm}"
    
    latest = db.query(ServiceTicket.ticket_id).filter(
        ServiceTicket.ticket_id.like(f"{full_prefix}-%")
    ).order_by(ServiceTicket.ticket_id.desc()).first()

    if latest and latest[0] and len(latest[0]) >= 13:
        try:
            num = int(latest[0].split('-')[-1]) + 1
        except ValueError:
            num = 1
    else:
        num = 1

    return f"{full_prefix}-{num:04d}"


def _ensure_tenant_categories(db: Session, company_id: int) -> List[SignupCategory]:
    """
    Ensures tenant has active signup/service categories.
    If none exist for company_id, seeds default master categories dynamically.
    """
    categories = db.query(SignupCategory).filter(
        SignupCategory.company_id == company_id,
        SignupCategory.is_active == True
    ).order_by(SignupCategory.display_order.asc()).all()

    if not categories:
        # Bootstrap default master categories for tenant company
        for idx, cat_data in enumerate(DEFAULT_SIGNUP_CATEGORIES, start=1):
            new_cat = SignupCategory(
                company_id=company_id,
                name=cat_data['name'],
                slug=f"{cat_data['slug']}-{company_id}",
                description=cat_data.get('description'),
                icon=cat_data.get('icon'),
                display_order=cat_data.get('display_order', idx),
                is_active=True
            )
            db.add(new_cat)
        db.commit()

        categories = db.query(SignupCategory).filter(
            SignupCategory.company_id == company_id,
            SignupCategory.is_active == True
        ).order_by(SignupCategory.display_order.asc()).all()

    return categories


# ===================== ENDPOINTS =====================

@router.get("/service/categories", summary="Get tenant business & service categories")
def get_tenant_service_categories(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Fetch active service categories for tenant company.
    Dynamically seeds default master categories if empty.
    """
    company_id = _get_company_id(current_user)
    categories = _ensure_tenant_categories(db, company_id)

    return {
        "success": True,
        "count": len(categories),
        "data": [cat.to_dict() for cat in categories]
    }


@router.post("/service/tickets", summary="Raise new service ticket for tenant")
def create_tenant_service_ticket(
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create physical/technical service ticket with category linkage and SLA commitment.
    """
    company_id = _get_company_id(current_user)

    category_id = payload.get('category_id')
    issue_category = (payload.get('issue_category') or '').strip()
    issue_description = (payload.get('issue_description') or '').strip()

    if not issue_description:
        raise HTTPException(status_code=400, detail="Issue description is required.")

    # Validate or resolve category name
    if category_id:
        cat_obj = db.query(SignupCategory).filter(
            SignupCategory.id == category_id,
            SignupCategory.company_id == company_id
        ).first()
        if cat_obj and not issue_category:
            issue_category = cat_obj.name

    if not issue_category:
        issue_category = "General Service"

    ticket_code = _generate_ticket_code(db)
    now_utc = datetime.utcnow()
    sla_deadline = now_utc + timedelta(hours=int(payload.get('tat_base_hours') or 24))

    raw_phone = (payload.get('customer_phone') or '').strip()
    cust_phone = normalize_phone_10(raw_phone) or raw_phone if raw_phone else None

    ticket = ServiceTicket(
        ticket_id=ticket_code,
        company_id=company_id,
        tenant_id=getattr(current_user, 'tenant_id', None),
        category_id=category_id,
        issue_category=issue_category,
        issue_description=issue_description,
        priority=(payload.get('priority') or 'Medium').strip().capitalize(),
        status='Open',
        sub_status='new',
        ticket_type=(payload.get('ticket_type') or 'technical').strip().lower(),
        source_channel=(payload.get('source_channel') or 'tenant_portal').strip(),
        customer_name=format_proper_name(payload.get('customer_name') or '') or None,
        customer_phone=cust_phone,
        customer_email=(payload.get('customer_email') or '').strip() or None,
        customer_address=(payload.get('customer_address') or '').strip() or None,
        service_manager_id=current_user.id,
        service_technician_id=payload.get('service_technician_id'),
        tat_base_hours=int(payload.get('tat_base_hours') or 24),
        created_date=now_utc,
        sla_deadline=sla_deadline,
        sla_status='Within SLA'
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": f"Service Ticket {ticket.ticket_id} created successfully.",
        "data": {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "issue_category": ticket.issue_category,
            "priority": ticket.priority,
            "status": ticket.status,
            "sub_status": ticket.sub_status,
            "customer_name": ticket.customer_name,
            "created_date": ticket.created_date.isoformat() if ticket.created_date else None
        }
    }


@router.get("/service/tickets", summary="List service queue tickets for tenant")
def list_tenant_service_tickets(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("all"),
    category_id: Optional[int] = Query(None),
    ticket_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Tenant Service Queue listing with search, category filtering, and SLA status.
    """
    company_id = _get_company_id(current_user)

    query = db.query(ServiceTicket).filter(ServiceTicket.company_id == company_id)

    if status_filter and isinstance(status_filter, str) and status_filter.lower() != 'all':
        query = query.filter(ServiceTicket.status.ilike(status_filter.strip()))

    if category_id and isinstance(category_id, int):
        query = query.filter(ServiceTicket.category_id == category_id)

    if ticket_type and isinstance(ticket_type, str):
        query = query.filter(ServiceTicket.ticket_type == ticket_type.strip().lower())

    if search and isinstance(search, str):
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ServiceTicket.ticket_id.ilike(s),
                ServiceTicket.issue_category.ilike(s),
                ServiceTicket.issue_description.ilike(s),
                ServiceTicket.customer_name.ilike(s),
                ServiceTicket.customer_phone.ilike(s)
            )
        )

    total_count = query.count()
    tickets = query.order_by(desc(ServiceTicket.created_date)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    now_utc = datetime.utcnow()
    for t in tickets:
        is_sla_breached = t.sla_deadline and t.status not in ('Closed', 'Resolved') and t.sla_deadline < now_utc
        items.append({
            "id": t.id,
            "ticket_id": t.ticket_id,
            "issue_category": t.issue_category,
            "issue_description": t.issue_description,
            "priority": t.priority,
            "status": t.status,
            "sub_status": t.sub_status,
            "ticket_type": t.ticket_type,
            "customer_name": t.customer_name,
            "customer_phone": t.customer_phone,
            "service_technician_id": t.service_technician_id,
            "spares_required": t.spares_required,
            "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
            "sla_status": "Breached SLA" if is_sla_breached else t.sla_status,
            "created_date": t.created_date.isoformat() if t.created_date else None
        })

    return {
        "success": True,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "data": items
    }


@router.patch("/service/tickets/{ticket_id}", summary="Update service ticket status & workflow")
def update_tenant_service_ticket(
    ticket_id: str = Path(...),
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update ticket status, sub-status, technician assignment, spares request, or resolution.
    """
    company_id = _get_company_id(current_user)

    ticket = db.query(ServiceTicket).filter(
        ServiceTicket.company_id == company_id,
        or_(ServiceTicket.ticket_id == ticket_id, ServiceTicket.id == int(ticket_id) if ticket_id.isdigit() else False)
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Service ticket not found or access denied.")

    now_utc = datetime.utcnow()

    if 'status' in payload and payload['status']:
        raw_st = payload['status'].strip()
        status_map = {
            'open': 'Open',
            'in progress': 'In Progress',
            'in_progress': 'In Progress',
            'resolved': 'Resolved',
            'closed': 'Closed',
            'cancelled': 'Cancelled',
            'canceled': 'Cancelled'
        }
        st = status_map.get(raw_st.lower(), raw_st.title())
        ticket.status = st
        if st in ('Resolved', 'Closed'):
            ticket.closed_date = now_utc

    if 'sub_status' in payload and payload['sub_status']:
        ticket.sub_status = payload['sub_status'].strip().lower()

    if 'service_technician_id' in payload:
        ticket.service_technician_id = payload['service_technician_id']

    if 'spares_required' in payload:
        ticket.spares_required = bool(payload['spares_required'])
        if ticket.spares_required and not ticket.spare_requested_at:
            ticket.spare_requested_at = now_utc

    if 'diagnosis_notes' in payload:
        ticket.diagnosis_notes = (payload['diagnosis_notes'] or '').strip() or None
        ticket.diagnosed_at = now_utc

    if 'resolution_summary' in payload:
        ticket.resolution_summary = (payload['resolution_summary'] or '').strip() or None

    if 'admin_response' in payload:
        ticket.admin_response = (payload['admin_response'] or '').strip() or None
        ticket.last_response_date = now_utc

    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": f"Service ticket {ticket.ticket_id} updated successfully.",
        "data": {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "sub_status": ticket.sub_status,
            "spares_required": ticket.spares_required,
            "service_technician_id": ticket.service_technician_id
        }
    }


@router.get("/service/dashboard", summary="Executive dashboard analytics for tenant service center")
def get_tenant_service_dashboard(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Executive summary of tenant service center metrics.
    """
    company_id = _get_company_id(current_user)

    total_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.company_id == company_id).scalar() or 0
    open_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.company_id == company_id, ServiceTicket.status == 'Open').scalar() or 0
    in_progress = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.company_id == company_id, ServiceTicket.status == 'In Progress').scalar() or 0
    spares_awaiting = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.company_id == company_id, ServiceTicket.sub_status == 'awaiting_spares').scalar() or 0
    completed = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.company_id == company_id, ServiceTicket.status.in_(['Resolved', 'Closed'])).scalar() or 0

    now_utc = datetime.utcnow()
    sla_breaches = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.company_id == company_id,
        ServiceTicket.status.notin_(['Closed', 'Resolved']),
        ServiceTicket.sla_deadline < now_utc
    ).scalar() or 0

    return {
        "success": True,
        "data": {
            "summary": {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "in_progress": in_progress,
                "spares_awaiting": spares_awaiting,
                "completed": completed,
                "sla_breaches": sla_breaches
            }
        }
    }
