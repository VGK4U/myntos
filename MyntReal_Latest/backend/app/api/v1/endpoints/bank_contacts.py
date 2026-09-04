"""
Bank Branch Contacts API Endpoints
Manages personnel contact details for bank branches (Branch Manager, Field Officer, Custom Officers)
Supports multi-tenant segregation, staff audit trail, and WebRTC softphone dialing.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.models.bank_branch_contact import BankBranchContact, get_indian_time

logger = logging.getLogger(__name__)

router = APIRouter()


class BankBranchContactCreate(BaseModel):
    bank_name: str
    branch_name: str
    company_id: Optional[int] = 4
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None
    manager_alt_phone: Optional[str] = None
    officer_name: Optional[str] = None
    officer_phone: Optional[str] = None
    officer_alt_phone: Optional[str] = None
    custom_designation: Optional[str] = None
    custom_name: Optional[str] = None
    custom_phone: Optional[str] = None
    custom_alt_phone: Optional[str] = None
    google_maps_url: Optional[str] = None
    branch_address: Optional[str] = None
    notes: Optional[str] = None
    staff_name: Optional[str] = None
    staff_id: Optional[int] = None


@router.get("/bank-branch-contacts", response_model=Dict[str, Any])
def get_bank_branch_contacts(
    bank_name: Optional[str] = Query(None),
    branch_name: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Fetch all bank branch contacts, indexed for fast UI lookup."""
    query = db.query(BankBranchContact)
    if bank_name:
        query = query.filter(func.lower(BankBranchContact.bank_name) == bank_name.strip().lower())
    if branch_name:
        query = query.filter(func.lower(BankBranchContact.branch_name) == branch_name.strip().lower())
    if company_id:
        query = query.filter(BankBranchContact.company_id == company_id)

    contacts = query.order_by(BankBranchContact.updated_at.desc()).all()
    
    # Build dictionary map keyed by \"bank_name:::branch_name\" in lowercase for instant frontend access
    contact_map = {}
    contacts_list = []
    for c in contacts:
        d = c.to_dict()
        contacts_list.append(d)
        key = f"{c.bank_name.strip().lower()}:::{c.branch_name.strip().lower()}"
        contact_map[key] = d

    return {
        "success": True,
        "count": len(contacts_list),
        "data": contacts_list,
        "map": contact_map
    }


@router.post("/bank-branch-contacts", response_model=Dict[str, Any])
def upsert_bank_branch_contact(
    request: Request,
    payload: BankBranchContactCreate = Body(...),
    db: Session = Depends(get_db)
):
    """Create or update contact information for a specific bank and branch."""
    b_name = (payload.bank_name or "").strip()
    br_name = (payload.branch_name or "").strip()
    if not b_name or not br_name:
        raise HTTPException(status_code=400, detail="Both bank_name and branch_name are required.")

    # Find existing contact record for this bank + branch
    contact = db.query(BankBranchContact).filter(
        func.lower(BankBranchContact.bank_name) == b_name.lower(),
        func.lower(BankBranchContact.branch_name) == br_name.lower()
    ).first()

    staff_id = payload.staff_id
    staff_name = payload.staff_name

    # Try resolving current staff from token if not explicitly provided
    if not staff_name:
        try:
            from app.api.v1.endpoints.staff_auth import get_current_staff_user
            st_user = get_current_staff_user(request, db)
            if st_user:
                staff_id = staff_id or st_user.id
                staff_name = staff_name or st_user.full_name or st_user.username
        except Exception:
            pass

    if not contact:
        contact = BankBranchContact(
            bank_name=b_name,
            branch_name=br_name,
            company_id=payload.company_id or 4,
            created_at=get_indian_time()
        )
        db.add(contact)

    contact.company_id = payload.company_id or contact.company_id or 4
    contact.manager_name = (payload.manager_name or "").strip() or None
    contact.manager_phone = (payload.manager_phone or "").strip() or None
    contact.manager_alt_phone = (payload.manager_alt_phone or "").strip() or None

    contact.officer_name = (payload.officer_name or "").strip() or None
    contact.officer_phone = (payload.officer_phone or "").strip() or None
    contact.officer_alt_phone = (payload.officer_alt_phone or "").strip() or None

    contact.custom_designation = (payload.custom_designation or "").strip() or None
    contact.custom_name = (payload.custom_name or "").strip() or None
    contact.custom_phone = (payload.custom_phone or "").strip() or None
    contact.custom_alt_phone = (payload.custom_alt_phone or "").strip() or None

    contact.google_maps_url = (payload.google_maps_url or "").strip() or None
    contact.branch_address = (payload.branch_address or "").strip() or None

    contact.notes = (payload.notes or "").strip() or None
    contact.updated_by_staff_id = staff_id
    contact.updated_by_staff_name = staff_name or "Staff Member"
    contact.updated_at = get_indian_time()

    db.commit()
    db.refresh(contact)

    return {
        "success": True,
        "message": f"Branch contacts for {b_name} ({br_name}) saved successfully.",
        "data": contact.to_dict()
    }


@router.delete("/bank-branch-contacts/{contact_id}", response_model=Dict[str, Any])
def delete_bank_branch_contact(
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Delete bank branch contact record."""
    contact = db.query(BankBranchContact).get(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Bank branch contact not found.")
    
    db.delete(contact)
    db.commit()
    return {"success": True, "message": "Branch contact deleted successfully."}
