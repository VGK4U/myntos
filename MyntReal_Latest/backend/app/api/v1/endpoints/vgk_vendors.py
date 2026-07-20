"""
VGK Vendor Master System — API Endpoints (DC Protocol Mar 2026)

Staff:   /staff/vgk/vendors/*      — CRUD, KYC, agreements, QR, transaction approvals
Vendor:  /vendor/*                  — Vendor portal login + self-management
Member:  /vgk/vendor/*             — Directory browse, QR scan, purchase submission
"""

import io
import uuid
import logging
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _staff_cid(u) -> int:
    cid = getattr(u, 'base_company_id', None) or getattr(u, 'company_id', None)
    if not cid:
        raise HTTPException(status_code=400, detail="Cannot resolve company_id for staff user")
    return int(cid)

def _generate_qr_base64(content: str) -> str:
    """Return base64-encoded PNG of QR code for given content string."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=3)
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        logger.warning(f"[VGK-VENDOR] QR generation failed: {e}")
        return ""

def _next_vendor_code(db: Session, company_id: int) -> str:
    from app.models.vgk_vendor import VGKVendor
    # Search GLOBALLY (all companies) — vendor_code has a global unique constraint,
    # so per-company lookup causes collisions when a new company creates its first vendor.
    last = db.query(VGKVendor).filter(
        VGKVendor.vendor_code.like('VND%')
    ).order_by(VGKVendor.id.desc()).first()
    if last and last.vendor_code and last.vendor_code.startswith('VND'):
        try:
            num = int(last.vendor_code[3:]) + 1
        except Exception:
            num = 1001
    else:
        num = 1001
    # Guard against gaps / concurrent inserts: increment until the code is free
    while db.query(VGKVendor).filter(VGKVendor.vendor_code == f"VND{num:04d}").first():
        num += 1
    return f"VND{num:04d}"

def _is_vgk_privileged(user) -> bool:
    """DC-VGK-MKT-ENHANCE-001: Category create/approve restricted to MR10001, Accounts dept, EA role."""
    emp_code = (getattr(user, 'emp_code', '') or '').strip().upper()
    dept = (getattr(user, 'department', '') or '').strip().lower()
    role_code = (getattr(user, 'role_code', '') or '').strip().upper()
    return emp_code == 'MR10001' or 'accounts' in dept or role_code == 'EA'


def _next_txn_number(db: Session, company_id: int) -> str:
    from app.models.vgk_vendor import VGKVendorTransaction
    count = db.query(VGKVendorTransaction).filter(
        VGKVendorTransaction.company_id == company_id
    ).count()
    from app.models.base import get_indian_time
    now = get_indian_time()
    return f"VVTXN/{now.year}/{now.month:02d}/{count + 1:05d}"

def _get_vendor_auth(token: str, db: Session):
    """Decode vendor JWT and return VGKVendorLogin + VGKVendor."""
    from jose import jwt, JWTError
    from app.models.vgk_vendor import VGKVendorLogin, VGKVendor
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("user_type") != "vgk_vendor":
            raise HTTPException(status_code=401, detail="Invalid token type")
        vendor_login_id = int(payload.get("sub"))
        vl = db.query(VGKVendorLogin).filter(VGKVendorLogin.id == vendor_login_id).first()
        if not vl or not vl.is_active:
            raise HTTPException(status_code=401, detail="Vendor account not active")
        vendor = db.query(VGKVendor).filter(VGKVendor.id == vl.vendor_id).first()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return vl, vendor
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — CATEGORY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/staff/vgk/vendors/categories")
def list_vendor_categories(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorCategory
    cid = _staff_cid(current_user)
    cats = db.query(VGKVendorCategory).filter(
        VGKVendorCategory.company_id == cid
    ).order_by(VGKVendorCategory.display_order, VGKVendorCategory.name).all()
    return [
        {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon,
         "description": c.description, "display_order": c.display_order,
         "is_active": c.is_active}
        for c in cats
    ]


@router.post("/staff/vgk/vendors/categories")
def create_vendor_category(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorCategory
    cid = _staff_cid(current_user)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name required")
    import re
    slug = payload.get("slug") or re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    cat = VGKVendorCategory(
        company_id=cid,
        name=name,
        slug=slug,
        icon=payload.get("icon") or "fas fa-store",
        description=payload.get("description"),
        display_order=int(payload.get("display_order") or 0),
        is_active=True
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"success": True, "id": cat.id, "name": cat.name, "slug": cat.slug}


@router.put("/staff/vgk/vendors/categories/{cat_id}")
def update_vendor_category(
    cat_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorCategory
    cid = _staff_cid(current_user)
    cat = db.query(VGKVendorCategory).filter(
        VGKVendorCategory.id == cat_id,
        VGKVendorCategory.company_id == cid
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for f in ("name", "icon", "description", "display_order", "is_active"):
        if f in payload:
            setattr(cat, f, payload[f])
    db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — VENDOR CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/staff/vgk/vendors")
def list_vendors(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, le=100),
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    pincode: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor, VGKVendorCategory
    cid = _staff_cid(current_user)
    q = db.query(VGKVendor).filter(VGKVendor.company_id == cid)
    if status:
        q = q.filter(VGKVendor.status == status.upper())
    if category_id:
        q = q.filter(VGKVendor.category_id == category_id)
    if pincode:
        q = q.filter(VGKVendor.pincode == pincode.strip())
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(
            VGKVendor.vendor_name.ilike(s),
            VGKVendor.vendor_code.ilike(s),
            VGKVendor.phone.ilike(s),
            VGKVendor.gst_number.ilike(s),
            VGKVendor.city.ilike(s)
        ))
    total = q.count()
    vendors = q.order_by(VGKVendor.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [
            {
                "id": v.id, "vendor_code": v.vendor_code, "vendor_name": v.vendor_name,
                "category_name": v.category_name, "phone": v.phone, "city": v.city,
                "pincode": v.pincode, "status": v.status, "is_active": v.is_active,
                "flat_discount_pct": float(v.flat_discount_pct or 0),
                "total_transactions": v.total_transactions or 0,
                "total_business_value": float(v.total_business_value or 0),
                "total_discount_given": float(v.total_discount_given or 0),
                "marketplace_opted": v.marketplace_opted,
                "has_login": v.has_login,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in vendors
        ]
    }


@router.post("/staff/vgk/vendors")
def create_vendor(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor, VGKVendorCategory
    cid = _staff_cid(current_user)
    vendor_name = (payload.get("vendor_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    cat_id = int(payload.get("category_id") or 0)
    if not vendor_name or not phone or not cat_id:
        raise HTTPException(status_code=400, detail="vendor_name, phone, category_id required")
    cat = db.query(VGKVendorCategory).filter(
        VGKVendorCategory.id == cat_id,
        VGKVendorCategory.company_id == cid
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    vendor_code = _next_vendor_code(db, cid)
    qr_token = uuid.uuid4().hex

    vendor = VGKVendor(
        company_id=cid,
        vendor_code=vendor_code,
        vendor_name=vendor_name,
        category_id=cat_id,
        category_name=cat.name,
        gst_number=payload.get("gst_number"),
        pan_number=payload.get("pan_number"),
        shop_description=payload.get("shop_description"),
        established_year=payload.get("established_year"),
        contact_person=payload.get("contact_person"),
        phone=phone,
        alternate_phone=payload.get("alternate_phone"),
        email=payload.get("email"),
        whatsapp_number=payload.get("whatsapp_number"),
        address_line1=payload.get("address_line1"),
        address_line2=payload.get("address_line2"),
        city=payload.get("city"),
        state=payload.get("state"),
        pincode=payload.get("pincode"),
        map_link=payload.get("map_link"),
        flat_discount_pct=Decimal(str(payload.get("flat_discount_pct") or 0)),
        qr_token=qr_token,
        status="PENDING",
        is_active=False,
        marketplace_opted=bool(payload.get("marketplace_opted") or False),
        created_by_staff_id=getattr(current_user, 'id', None),
        notes=payload.get("notes"),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {"success": True, "id": vendor.id, "vendor_code": vendor.vendor_code, "qr_token": vendor.qr_token}


@router.get("/staff/vgk/vendors/{vendor_id}")
def get_vendor_detail(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor, VGKVendorKYC, VGKVendorAgreement, VGKVendorProductCategory
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    kyc = db.query(VGKVendorKYC).filter(VGKVendorKYC.vendor_id == vendor_id).all()
    agreement = db.query(VGKVendorAgreement).filter(
        VGKVendorAgreement.vendor_id == vendor_id,
        VGKVendorAgreement.is_current == True
    ).first()
    prod_cats = db.query(VGKVendorProductCategory).filter(
        VGKVendorProductCategory.vendor_id == vendor_id,
        VGKVendorProductCategory.is_active == True
    ).order_by(VGKVendorProductCategory.display_order).all()

    qr_url = f"https://vgk4u.com/v/{v.qr_token}"
    qr_b64 = _generate_qr_base64(qr_url)

    return {
        "id": v.id, "vendor_code": v.vendor_code, "vendor_name": v.vendor_name,
        "category_id": v.category_id, "category_name": v.category_name,
        "gst_number": v.gst_number, "pan_number": v.pan_number,
        "shop_description": v.shop_description, "established_year": v.established_year,
        "contact_person": v.contact_person, "phone": v.phone,
        "alternate_phone": v.alternate_phone, "email": v.email,
        "whatsapp_number": v.whatsapp_number, "address_line1": v.address_line1,
        "address_line2": v.address_line2, "city": v.city, "state": v.state,
        "pincode": v.pincode, "map_link": v.map_link,
        "flat_discount_pct": float(v.flat_discount_pct or 0),
        "qr_token": v.qr_token, "qr_url": qr_url, "qr_b64": qr_b64,
        "status": v.status, "is_active": v.is_active,
        "marketplace_opted": v.marketplace_opted, "has_login": v.has_login,
        "total_transactions": v.total_transactions or 0,
        "total_business_value": float(v.total_business_value or 0),
        "total_discount_given": float(v.total_discount_given or 0),
        "notes": v.notes,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "activated_at": v.activated_at.isoformat() if v.activated_at else None,
        "kyc": [
            {"id": k.id, "doc_type": k.doc_type, "doc_label": k.doc_label,
             "doc_url": k.doc_url, "doc_number": k.doc_number,
             "verified": k.verified, "notes": k.notes}
            for k in kyc
        ],
        "agreement": {
            "id": agreement.id, "terms_version": agreement.terms_version,
            "agreed_discount_pct": float(agreement.agreed_discount_pct),
            "valid_from": agreement.valid_from.isoformat() if agreement.valid_from else None,
            "valid_till": agreement.valid_till.isoformat() if agreement.valid_till else None,
            "signed_at": agreement.signed_at.isoformat() if agreement.signed_at else None,
            "signed_by_name": agreement.signed_by_name,
            "is_current": agreement.is_current,
        } if agreement else None,
        "product_categories": [
            {"id": pc.id, "category_name": pc.category_name,
             "category_prefix": pc.category_prefix or "",
             "gst_pct": float(pc.gst_pct or 0),
             "discount_pct": float(pc.discount_pct) if pc.discount_pct is not None else None,
             "description": pc.description, "display_order": pc.display_order,
             "is_active": pc.is_active}
            for pc in prod_cats
        ]
    }


@router.put("/staff/vgk/vendors/{vendor_id}")
def update_vendor(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    editable = [
        "vendor_name", "gst_number", "pan_number", "shop_description", "established_year",
        "contact_person", "phone", "alternate_phone", "email", "whatsapp_number",
        "address_line1", "address_line2", "city", "state", "pincode", "map_link",
        "flat_discount_pct", "marketplace_opted", "notes",
        "logo_url", "banner_url",
    ]
    for f in editable:
        if f in payload:
            val = payload[f]
            if f == "flat_discount_pct" and val is not None:
                val = Decimal(str(val))
            setattr(v, f, val)
    db.commit()
    return {"success": True}


@router.post("/staff/vgk/vendors/{vendor_id}/activate")
def activate_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.status = "ACTIVE"
    v.is_active = True
    v.activated_by_staff_id = getattr(current_user, 'id', None)
    v.activated_at = get_indian_time()
    db.commit()
    return {"success": True, "status": "ACTIVE"}


@router.post("/staff/vgk/vendors/{vendor_id}/suspend")
def suspend_vendor(
    vendor_id: int,
    payload: dict = Body({}),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.status = "SUSPENDED"
    v.is_active = False
    if payload.get("notes"):
        v.notes = (v.notes or "") + f"\n[SUSPENDED] {payload['notes']}"
    db.commit()
    return {"success": True, "status": "SUSPENDED"}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — KYC
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/staff/vgk/vendors/{vendor_id}/kyc")
def add_vendor_kyc(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorKYC, VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    k = VGKVendorKYC(
        company_id=cid, vendor_id=vendor_id,
        doc_type=payload.get("doc_type", "OTHER"),
        doc_label=payload.get("doc_label"),
        doc_url=payload.get("doc_url"),
        doc_number=payload.get("doc_number"),
        notes=payload.get("notes"),
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    return {"success": True, "id": k.id}


@router.put("/staff/vgk/vendors/kyc/{kyc_id}")
def update_vendor_kyc(
    kyc_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorKYC
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    k = db.query(VGKVendorKYC).filter(
        VGKVendorKYC.id == kyc_id,
        VGKVendorKYC.company_id == cid
    ).first()
    if not k:
        raise HTTPException(status_code=404, detail="KYC record not found")
    for f in ("doc_url", "doc_number", "doc_label", "notes"):
        if f in payload:
            setattr(k, f, payload[f])
    if payload.get("verified") is True:
        k.verified = True
        k.verified_by_staff_id = getattr(current_user, 'id', None)
        k.verified_at = get_indian_time()
    db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — AGREEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/staff/vgk/vendors/{vendor_id}/agreement")
def create_vendor_agreement(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorAgreement, VGKVendor
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    disc_pct = Decimal(str(payload.get("agreed_discount_pct") or 0))
    if disc_pct <= 0:
        raise HTTPException(status_code=400, detail="agreed_discount_pct must be > 0")

    # Expire current agreement if any
    db.query(VGKVendorAgreement).filter(
        VGKVendorAgreement.vendor_id == vendor_id,
        VGKVendorAgreement.is_current == True
    ).update({"is_current": False})

    valid_till = None
    if payload.get("valid_till"):
        try:
            valid_till = datetime.fromisoformat(payload["valid_till"])
        except Exception:
            pass

    a = VGKVendorAgreement(
        company_id=cid,
        vendor_id=vendor_id,
        terms_version=payload.get("terms_version") or "V1.0",
        agreed_discount_pct=disc_pct,
        valid_from=get_indian_time(),
        valid_till=valid_till,
        signed_by_name=payload.get("signed_by_name"),
        signed_by_designation=payload.get("signed_by_designation"),
        signed_at=get_indian_time(),
        is_current=True,
    )
    db.add(a)
    # Update vendor's flat_discount_pct to match
    v.flat_discount_pct = disc_pct
    db.commit()
    db.refresh(a)
    return {"success": True, "id": a.id}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — PRODUCT CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/staff/vgk/vendors/{vendor_id}/product-categories")
def add_vendor_product_category(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorProductCategory, VGKVendor
    if not _is_vgk_privileged(current_user):
        raise HTTPException(status_code=403, detail="Category creation restricted to MR10001, Accounts dept, or EA role")
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    cat_name = (payload.get("category_name") or "").strip()
    if not cat_name:
        raise HTTPException(status_code=400, detail="category_name required")
    disc = payload.get("discount_pct")
    prefix_raw = (payload.get("category_prefix") or "").strip().upper()
    pc = VGKVendorProductCategory(
        company_id=cid, vendor_id=vendor_id,
        category_name=cat_name,
        category_prefix=prefix_raw or None,
        gst_pct=Decimal(str(payload.get("gst_pct") or 0)),
        discount_pct=Decimal(str(disc)) if disc is not None else None,
        description=payload.get("description"),
        display_order=int(payload.get("display_order") or 0),
        is_active=True
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return {"success": True, "id": pc.id, "category_prefix": pc.category_prefix}


@router.put("/staff/vgk/vendors/product-categories/{cat_id}")
def update_vendor_product_category(
    cat_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorProductCategory
    if not _is_vgk_privileged(current_user):
        raise HTTPException(status_code=403, detail="Category update restricted to MR10001, Accounts dept, or EA role")
    cid = _staff_cid(current_user)
    pc = db.query(VGKVendorProductCategory).filter(
        VGKVendorProductCategory.id == cat_id,
        VGKVendorProductCategory.company_id == cid
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Product category not found")
    for f in ("category_name", "description", "display_order", "is_active"):
        if f in payload:
            setattr(pc, f, payload[f])
    if "category_prefix" in payload:
        pc.category_prefix = (payload["category_prefix"] or "").strip().upper() or None
    if "gst_pct" in payload:
        pc.gst_pct = Decimal(str(payload["gst_pct"]))
    if "discount_pct" in payload:
        pc.discount_pct = Decimal(str(payload["discount_pct"])) if payload["discount_pct"] is not None else None
    db.commit()
    return {"success": True}


@router.delete("/staff/vgk/vendors/product-categories/{cat_id}")
def delete_vendor_product_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorProductCategory
    if not _is_vgk_privileged(current_user):
        raise HTTPException(status_code=403, detail="Category deletion restricted to MR10001, Accounts dept, or EA role")
    cid = _staff_cid(current_user)
    pc = db.query(VGKVendorProductCategory).filter(
        VGKVendorProductCategory.id == cat_id,
        VGKVendorProductCategory.company_id == cid
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Not found")
    pc.is_active = False
    db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — PORTAL LOGIN MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/staff/vgk/vendors/{vendor_id}/portal-login")
def set_vendor_portal_login(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorLogin, VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    raw_pw = (payload.get("password") or "").strip()
    username = (payload.get("username") or v.phone or "").strip()
    if not raw_pw or not username:
        raise HTTPException(status_code=400, detail="username and password required")

    existing = db.query(VGKVendorLogin).filter(VGKVendorLogin.vendor_id == vendor_id).first()
    pw_hash = SecurityManager.get_password_hash(raw_pw)
    if existing:
        existing.username = username
        existing.password_hash = pw_hash
        existing.is_active = True
        existing.failed_login_attempts = 0
    else:
        vl = VGKVendorLogin(
            company_id=cid, vendor_id=vendor_id,
            username=username, password_hash=pw_hash
        )
        db.add(vl)
    v.has_login = True
    db.commit()
    return {"success": True, "username": username}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — TRANSACTIONS (ACCOUNTS TEAM APPROVALS)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/staff/vgk/vendor-transactions")
def list_vendor_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, le=100),
    status: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorTransaction
    cid = _staff_cid(current_user)
    q = db.query(VGKVendorTransaction).filter(VGKVendorTransaction.company_id == cid)
    if status:
        q = q.filter(VGKVendorTransaction.status == status.upper())
    if vendor_id:
        q = q.filter(VGKVendorTransaction.vendor_id == vendor_id)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(
            VGKVendorTransaction.txn_number.ilike(s),
            VGKVendorTransaction.invoice_number.ilike(s),
            VGKVendorTransaction.vendor_name.ilike(s),
        ))
    total = q.count()
    rows = q.order_by(VGKVendorTransaction.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "data": [_txn_dict(t) for t in rows]
    }


def _txn_dict(t):
    return {
        "id": t.id, "txn_number": t.txn_number,
        "vendor_id": t.vendor_id, "vendor_name": t.vendor_name,
        "member_partner_id": t.member_partner_id,
        "product_category_name": t.product_category_name,
        "invoice_number": t.invoice_number,
        "invoice_date": t.invoice_date.isoformat() if t.invoice_date else None,
        "amount_excl_tax": float(t.amount_excl_tax),
        "gst_amount": float(t.gst_amount or 0),
        "amount_total": float(t.amount_total),
        "discount_pct": float(t.discount_pct),
        "discount_amount": float(t.discount_amount),
        "wallet_used_amount": float(t.wallet_used_amount or 0),
        "wallet_debited": t.wallet_debited,
        "cashback_credited": t.cashback_credited,
        "status": t.status,
        "rejection_reason": t.rejection_reason,
        "notes": t.notes,
        "invoice_image_url": t.invoice_image_url,
        "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.post("/staff/vgk/vendor-transactions/{txn_id}/approve")
def approve_vendor_transaction(
    txn_id: int,
    payload: dict = Body({}),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorTransaction, VGKVendor
    from app.models.staff_accounts import OfficialPartner
    from app.models.vgk_wallet_transaction import VGKWalletTransaction
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    txn = db.query(VGKVendorTransaction).filter(
        VGKVendorTransaction.id == txn_id,
        VGKVendorTransaction.company_id == cid,
        VGKVendorTransaction.status == 'PENDING'
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Pending transaction not found")

    member = db.query(OfficialPartner).filter(OfficialPartner.id == txn.member_partner_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    now = get_indian_time()
    staff_id = getattr(current_user, 'id', None)
    errors = []

    # 1. Credit cashback (discount amount) to member wallet
    discount_amt = Decimal(str(txn.discount_amount))
    wallet_before = Decimal(str(member.vgk_cash_wallet or 0))
    member.vgk_cash_wallet = wallet_before + discount_amt
    # log wallet credit
    wt_credit = VGKWalletTransaction(
        company_id=cid,
        partner_id=member.id,
        txn_type='INCOME_CREDIT',
        direction='CR',
        amount=discount_amt,
        wallet_before=wallet_before,
        wallet_after=member.vgk_cash_wallet,
        ref_type='VENDOR_TXN',
        ref_id=txn.id,
        description=f"Vendor cashback from {txn.vendor_name} — Inv {txn.invoice_number}",
        initiated_by_staff_id=staff_id,
    )
    db.add(wt_credit)
    txn.cashback_credited = True

    # 2. Debit wallet if member chose to pay from wallet
    wallet_used = Decimal(str(txn.wallet_used_amount or 0))
    if wallet_used > 0:
        current_bal = Decimal(str(member.vgk_cash_wallet or 0))
        if current_bal < wallet_used:
            wallet_used = current_bal  # cap to available
        if wallet_used > 0:
            wallet_before2 = Decimal(str(member.vgk_cash_wallet or 0))
            member.vgk_cash_wallet = wallet_before2 - wallet_used
            wt_debit = VGKWalletTransaction(
                company_id=cid,
                partner_id=member.id,
                txn_type='VENDOR_DEBIT',
                direction='DR',
                amount=wallet_used,
                wallet_before=wallet_before2,
                wallet_after=member.vgk_cash_wallet,
                ref_type='VENDOR_TXN',
                ref_id=txn.id,
                description=f"Wallet payment at {txn.vendor_name} — Invoice {txn.invoice_number}",
                initiated_by_staff_id=staff_id,
            )
            db.add(wt_debit)
            txn.wallet_debited = True
            txn.wallet_used_amount = wallet_used

    # 3. Update transaction
    txn.status = 'APPROVED'
    txn.reviewed_by_staff_id = staff_id
    txn.reviewed_at = now
    txn.notes = payload.get("notes") or txn.notes

    # 4. Update vendor stats
    vendor = db.query(VGKVendor).filter(VGKVendor.id == txn.vendor_id).first()
    if vendor:
        vendor.total_transactions = (vendor.total_transactions or 0) + 1
        vendor.total_business_value = Decimal(str(vendor.total_business_value or 0)) + Decimal(str(txn.amount_total))
        vendor.total_discount_given = Decimal(str(vendor.total_discount_given or 0)) + discount_amt

    # 5. Auto-deduct vendor stock if transaction linked to a marketplace product
    #    DC-VGK-MKT-ENHANCE-001: marketplace_product_id on transaction enables auto stock movement
    if txn.marketplace_product_id:
        from app.models.vgk_vendor import VGKVendorMarketplaceProduct
        mkt_prod = db.query(VGKVendorMarketplaceProduct).filter(
            VGKVendorMarketplaceProduct.id == txn.marketplace_product_id
        ).first()
        if mkt_prod and (mkt_prod.stock_qty or 0) > 0:
            mkt_prod.stock_qty = max(0, (mkt_prod.stock_qty or 0) - 1)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Approval failed: {e}")

    return {"success": True, "cashback_credited": float(discount_amt), "wallet_debited": float(wallet_used)}


@router.post("/staff/vgk/vendor-transactions/{txn_id}/reject")
def reject_vendor_transaction(
    txn_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorTransaction
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    txn = db.query(VGKVendorTransaction).filter(
        VGKVendorTransaction.id == txn_id,
        VGKVendorTransaction.company_id == cid,
        VGKVendorTransaction.status == 'PENDING'
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Pending transaction not found")
    reason = (payload.get("rejection_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="rejection_reason required")
    txn.status = 'REJECTED'
    txn.rejection_reason = reason
    txn.reviewed_by_staff_id = getattr(current_user, 'id', None)
    txn.reviewed_at = get_indian_time()
    db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — QR CODE
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/staff/vgk/vendors/{vendor_id}/qr")
def get_vendor_qr(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    qr_url = f"https://vgk4u.com/v/{v.qr_token}"
    return {"vendor_code": v.vendor_code, "vendor_name": v.vendor_name,
            "qr_url": qr_url, "qr_b64": _generate_qr_base64(qr_url)}


# ─────────────────────────────────────────────────────────────────────────────
#  STAFF — MARKETPLACE PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/staff/vgk/vendors/marketplace-products/all")
def list_all_vendor_marketplace_products(
    vendor_id: Optional[int] = None,
    segment_slug: Optional[str] = None,
    is_active: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct, VGKVendor
    cid = _staff_cid(current_user)
    q = db.query(VGKVendorMarketplaceProduct, VGKVendor.vendor_name, VGKVendor.city).join(
        VGKVendor, VGKVendor.id == VGKVendorMarketplaceProduct.vendor_id
    ).filter(
        VGKVendorMarketplaceProduct.company_id == cid
    )
    if vendor_id:
        q = q.filter(VGKVendorMarketplaceProduct.vendor_id == vendor_id)
    if segment_slug:
        q = q.filter(VGKVendorMarketplaceProduct.segment_slug == segment_slug)
    if is_active == "true":
        q = q.filter(VGKVendorMarketplaceProduct.is_active == True)
    elif is_active == "false":
        q = q.filter(VGKVendorMarketplaceProduct.is_active == False)
    if search:
        like = f"%{search}%"
        q = q.filter(
            VGKVendorMarketplaceProduct.product_name.ilike(like) |
            VGKVendorMarketplaceProduct.segment_slug.ilike(like) |
            VGKVendor.vendor_name.ilike(like)
        )
    total = q.count()
    rows = q.order_by(VGKVendor.vendor_name, VGKVendorMarketplaceProduct.display_order).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for prod, vnd_name, city in rows:
        d = _product_dict(prod)
        d["vendor_name"] = vnd_name
        d["vendor_city"] = city
        items.append(d)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/staff/vgk/vendors/{vendor_id}/marketplace-products")
def list_vendor_marketplace_products(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    cid = _staff_cid(current_user)
    prods = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.vendor_id == vendor_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).order_by(VGKVendorMarketplaceProduct.display_order).all()
    return [_product_dict(p) for p in prods]


def _product_dict(p):
    return {
        "id": p.id, "vendor_id": p.vendor_id, "segment_slug": p.segment_slug,
        "product_name": p.product_name, "product_kit": p.product_kit,
        "description": p.description,
        "price_excl_tax": float(p.price_excl_tax) if p.price_excl_tax else None,
        "gst_pct": float(p.gst_pct or 0),
        "price_with_tax": float(p.price_with_tax) if p.price_with_tax else None,
        "discount_pct": float(p.discount_pct or 0),
        "image_url_1": p.image_url_1, "image_url_2": p.image_url_2, "image_url_3": p.image_url_3,
        "image_caption_1": p.image_caption_1, "image_caption_2": p.image_caption_2,
        "image_caption_3": p.image_caption_3,
        "approval_status": p.approval_status or "PENDING",
        "stock_qty": int(p.stock_qty or 0),
        "display_order": p.display_order, "is_active": p.is_active, "is_featured": p.is_featured,
        "views_count": p.views_count or 0,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/staff/vgk/vendors/{vendor_id}/marketplace-products")
def add_marketplace_product(
    vendor_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct, VGKVendor
    cid = _staff_cid(current_user)
    v = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.company_id == cid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    p = VGKVendorMarketplaceProduct(
        company_id=cid, vendor_id=vendor_id,
        segment_slug=payload.get("segment_slug") or "general",
        product_name=(payload.get("product_name") or "").strip(),
        product_kit=payload.get("product_kit"),
        description=payload.get("description"),
        price_excl_tax=Decimal(str(payload["price_excl_tax"])) if payload.get("price_excl_tax") is not None else None,
        gst_pct=Decimal(str(payload.get("gst_pct") or 0)),
        price_with_tax=Decimal(str(payload["price_with_tax"])) if payload.get("price_with_tax") is not None else None,
        discount_pct=Decimal(str(payload.get("discount_pct") or 0)),
        image_url_1=payload.get("image_url_1"),
        image_url_2=payload.get("image_url_2"),
        image_url_3=payload.get("image_url_3"),
        image_caption_1=payload.get("image_caption_1"),
        image_caption_2=payload.get("image_caption_2"),
        image_caption_3=payload.get("image_caption_3"),
        stock_qty=int(payload.get("stock_qty") or 0),
        display_order=int(payload.get("display_order") or 0),
        is_featured=bool(payload.get("is_featured") or False),
        is_active=True,
        approval_status="PENDING",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"success": True, "id": p.id}


@router.put("/staff/vgk/vendors/marketplace-products/{prod_id}")
def update_marketplace_product(
    prod_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    cid = _staff_cid(current_user)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    for f in ("segment_slug", "product_name", "product_kit", "description",
              "image_url_1", "image_url_2", "image_url_3",
              "image_caption_1", "image_caption_2", "image_caption_3",
              "display_order", "is_active", "is_featured"):
        if f in payload:
            setattr(p, f, payload[f])
    if "stock_qty" in payload and payload["stock_qty"] is not None:
        p.stock_qty = int(payload["stock_qty"])
    for f in ("price_excl_tax", "gst_pct", "price_with_tax", "discount_pct"):
        if f in payload and payload[f] is not None:
            setattr(p, f, Decimal(str(payload[f])))
    db.commit()
    return {"success": True}


@router.get("/staff/vgk/vendors/{vendor_id}/next-kit-code")
def get_next_kit_code(
    vendor_id: int,
    category_prefix: str = Query(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-VGK-MKT-ENHANCE-001: Return next auto-generated product kit code for given prefix."""
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    from app.models.base import get_indian_time
    cid = _staff_cid(current_user)
    pfx = (category_prefix or "").strip().upper()
    if not pfx:
        raise HTTPException(status_code=400, detail="category_prefix required")
    now = get_indian_time()
    yymm = now.strftime("%y%m")   # e.g. 2507
    like_pat = f"{pfx}{yymm}%"
    count = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.vendor_id == vendor_id,
        VGKVendorMarketplaceProduct.product_kit.like(like_pat)
    ).count()
    kit = f"{pfx}{yymm}{(count + 1):04d}"
    return {"kit_code": kit, "prefix": pfx, "yymm": yymm, "seq": count + 1}


@router.post("/staff/vgk/vendors/marketplace-products/{prod_id}/approve")
def approve_marketplace_product(
    prod_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-VGK-MKT-ENHANCE-001: Approve a marketplace product — restricted to MR10001/Accounts/EA."""
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    from app.models.base import get_indian_time
    if not _is_vgk_privileged(current_user):
        raise HTTPException(status_code=403, detail="Product approval restricted to MR10001, Accounts dept, or EA role")
    cid = _staff_cid(current_user)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.approval_status = "APPROVED"
    p.approved_by_staff_id = getattr(current_user, 'id', None)
    p.approved_at = get_indian_time()
    p.rejection_reason = None
    db.commit()
    return {"success": True, "approval_status": "APPROVED"}


@router.post("/staff/vgk/vendors/marketplace-products/{prod_id}/reject")
def reject_marketplace_product(
    prod_id: int,
    payload: dict = Body({}),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-VGK-MKT-ENHANCE-001: Reject a marketplace product — restricted to MR10001/Accounts/EA."""
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    if not _is_vgk_privileged(current_user):
        raise HTTPException(status_code=403, detail="Product rejection restricted to MR10001, Accounts dept, or EA role")
    cid = _staff_cid(current_user)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.approval_status = "REJECTED"
    p.rejection_reason = payload.get("rejection_reason") or "Rejected by reviewer"
    db.commit()
    return {"success": True, "approval_status": "REJECTED"}


@router.post("/staff/vgk/vendors/marketplace-products/{prod_id}/upload-image")
async def upload_marketplace_product_image(
    prod_id: int,
    slot: int = Form(...),
    caption: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-VGK-MKT-ENHANCE-001: Upload photo for marketplace product via UniversalUploadService."""
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    from app.services.universal_upload_service import UniversalUploadService
    if slot not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="slot must be 1, 2, or 3")
    cid = _staff_cid(current_user)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='vgk_vendor_marketplace_products',
            record_id=prod_id,
            uploaded_by_id=getattr(current_user, 'id', 0),
            uploaded_by_type='staff',
            storage_dir='vendor_products',
            db=db,
            emp_code=getattr(current_user, 'emp_code', None),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    url = f"/storage/{result['file_path']}"
    if slot == 1:
        p.image_url_1 = url
        p.image_caption_1 = caption or None
    elif slot == 2:
        p.image_url_2 = url
        p.image_caption_2 = caption or None
    else:
        p.image_url_3 = url
        p.image_caption_3 = caption or None
    db.commit()
    return {"success": True, "slot": slot, "url": url, "caption": caption}


@router.delete("/staff/vgk/vendors/marketplace-products/{prod_id}")
def delete_marketplace_product(
    prod_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    cid = _staff_cid(current_user)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.company_id == cid
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.is_active = False
    db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
#  VENDOR PORTAL — AUTH
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/vendor/auth/login")
def vendor_login(payload: dict = Body(...), db: Session = Depends(get_db)):
    from app.models.vgk_vendor import VGKVendorLogin, VGKVendor
    from app.models.base import get_indian_time
    from jose import jwt
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    if not username or not password:
        return {"success": False, "message": "Username and password required"}

    vl = db.query(VGKVendorLogin).filter(
        VGKVendorLogin.username == username,
        VGKVendorLogin.is_active == True
    ).first()
    if not vl:
        return {"success": False, "message": "Invalid credentials"}
    if not SecurityManager.verify_password(password, vl.password_hash):
        vl.failed_login_attempts = (vl.failed_login_attempts or 0) + 1
        try:
            db.commit()
        except Exception:
            db.rollback()
        return {"success": False, "message": "Invalid credentials"}

    vendor = db.query(VGKVendor).filter(VGKVendor.id == vl.vendor_id).first()
    if not vendor or not vendor.is_active:
        return {"success": False, "message": "Vendor account not active. Contact administrator."}

    vl.failed_login_attempts = 0
    vl.last_login = get_indian_time()
    try:
        db.commit()
    except Exception:
        db.rollback()

    token_payload = {
        "sub": str(vl.id),
        "user_type": "vgk_vendor",
        "vendor_id": vendor.id,
        "vendor_code": vendor.vendor_code,
        "vendor_name": vendor.vendor_name,
        "company_id": vendor.company_id,
        "exp": get_indian_time() + timedelta(hours=24)
    }
    token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {
        "success": True, "access_token": token,
        "vendor": {
            "id": vendor.id, "vendor_code": vendor.vendor_code,
            "vendor_name": vendor.vendor_name, "category_name": vendor.category_name,
            "city": vendor.city, "status": vendor.status,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
#  VENDOR PORTAL — SELF SERVICE
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vendor/me")
def vendor_me(
    authorization: Optional[str] = None,
    db: Session = Depends(get_db),
    request: Request = None
):
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    qr_url = f"https://vgk4u.com/v/{vendor.qr_token}"
    return {
        "id": vendor.id, "vendor_code": vendor.vendor_code,
        "vendor_name": vendor.vendor_name, "category_name": vendor.category_name,
        "gst_number": vendor.gst_number, "phone": vendor.phone, "email": vendor.email,
        "city": vendor.city, "state": vendor.state, "pincode": vendor.pincode,
        "address_line1": vendor.address_line1, "map_link": vendor.map_link,
        "shop_description": vendor.shop_description,
        "flat_discount_pct": float(vendor.flat_discount_pct or 0),
        "qr_url": qr_url, "qr_b64": _generate_qr_base64(qr_url),
        "marketplace_opted": vendor.marketplace_opted,
        "total_transactions": vendor.total_transactions or 0,
        "total_business_value": float(vendor.total_business_value or 0),
        "total_discount_given": float(vendor.total_discount_given or 0),
        "status": vendor.status,
    }


@router.put("/vendor/me")
def vendor_update_me(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    request: Request = None
):
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    editable = ["shop_description", "address_line1", "address_line2",
                "city", "state", "pincode", "map_link", "whatsapp_number", "email"]
    for f in editable:
        if f in payload:
            setattr(vendor, f, payload[f])
    db.commit()
    return {"success": True}


@router.get("/vendor/me/product-categories")
def vendor_me_product_categories(
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorProductCategory
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    cats = db.query(VGKVendorProductCategory).filter(
        VGKVendorProductCategory.vendor_id == vendor.id,
        VGKVendorProductCategory.is_active == True
    ).order_by(VGKVendorProductCategory.display_order).all()
    return [
        {"id": c.id, "category_name": c.category_name,
         "gst_pct": float(c.gst_pct or 0),
         "discount_pct": float(c.discount_pct) if c.discount_pct is not None else None,
         "description": c.description, "display_order": c.display_order}
        for c in cats
    ]


@router.get("/vendor/me/transactions")
def vendor_me_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=50),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorTransaction
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    q = db.query(VGKVendorTransaction).filter(VGKVendorTransaction.vendor_id == vendor.id)
    if status:
        q = q.filter(VGKVendorTransaction.status == status.upper())
    total = q.count()
    rows = q.order_by(VGKVendorTransaction.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {"total": total, "data": [_txn_dict(t) for t in rows]}


@router.get("/vendor/me/marketplace-products")
def vendor_me_marketplace_products(
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    prods = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.vendor_id == vendor.id
    ).order_by(VGKVendorMarketplaceProduct.display_order).all()
    return [_product_dict(p) for p in prods]


@router.post("/vendor/me/marketplace-products")
def vendor_add_marketplace_product(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    p = VGKVendorMarketplaceProduct(
        company_id=vendor.company_id, vendor_id=vendor.id,
        segment_slug=payload.get("segment_slug") or "general",
        product_name=(payload.get("product_name") or "").strip(),
        product_kit=payload.get("product_kit"),
        description=payload.get("description"),
        price_excl_tax=Decimal(str(payload["price_excl_tax"])) if payload.get("price_excl_tax") is not None else None,
        gst_pct=Decimal(str(payload.get("gst_pct") or 0)),
        price_with_tax=Decimal(str(payload["price_with_tax"])) if payload.get("price_with_tax") is not None else None,
        discount_pct=Decimal(str(payload.get("discount_pct") or 0)),
        image_url_1=payload.get("image_url_1"),
        image_url_2=payload.get("image_url_2"),
        image_url_3=payload.get("image_url_3"),
        display_order=int(payload.get("display_order") or 0),
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"success": True, "id": p.id}


@router.put("/vendor/me/marketplace-products/{prod_id}")
def vendor_update_marketplace_product(
    prod_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.vendor_id == vendor.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    for f in ("segment_slug", "product_name", "product_kit", "description",
              "image_url_1", "image_url_2", "image_url_3", "display_order", "is_active"):
        if f in payload:
            setattr(p, f, payload[f])
    for f in ("price_excl_tax", "gst_pct", "price_with_tax", "discount_pct"):
        if f in payload and payload[f] is not None:
            setattr(p, f, Decimal(str(payload[f])))
    db.commit()
    return {"success": True}


@router.delete("/vendor/me/marketplace-products/{prod_id}")
def vendor_delete_marketplace_product(
    prod_id: int,
    db: Session = Depends(get_db),
    request: Request = None
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)
    p = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.id == prod_id,
        VGKVendorMarketplaceProduct.vendor_id == vendor.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.is_active = False
    db.commit()
    return {"success": True}


@router.get("/vendor/me/service-repairs")
def vendor_me_service_repairs(
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    DC-VENDOR-REPAIR-TRACKER-001: Service spare parts sent to this vendor for repair.
    Used by vendor portal Returns tab. Matches by vendor_name (case-insensitive).
    """
    from app.models.ticket import ServiceTicketSpareRequest
    from app.models.staff_accounts import VendorMaster
    token = _extract_vendor_token(request)
    vl, vendor = _get_vendor_auth(token, db)

    # Match VendorMaster by name to link portal identity → procurement identity
    vm = db.query(VendorMaster).filter(
        VendorMaster.vendor_name.ilike(f"%{vendor.vendor_name}%")
    ).first()

    if not vm:
        return {"success": True, "items": [], "vendor_name": vendor.vendor_name, "matched": False}

    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.vendor_id == vm.id,
        ServiceTicketSpareRequest.vendor_repair_status != None
    ).order_by(ServiceTicketSpareRequest.sent_to_vendor_date.desc()).limit(100).all()

    items = []
    for s in spares:
        items.append({
            "id": s.id,
            "ticket_ref": f"TKT-{s.ticket_id}",
            "item_name": s.spare_item_name,
            "quantity": s.quantity_required or 1,
            "vendor_repair_status": s.vendor_repair_status,
            "sent_date": s.sent_to_vendor_date.isoformat() if s.sent_to_vendor_date else None,
            "expected_return_date": s.expected_return_date.isoformat() if s.expected_return_date else None,
            "return_received_date": s.return_received_date.isoformat() if s.return_received_date else None,
            "courier": s.sent_courier_name,
            "awb": s.sent_awb_number,
            "notes": s.vendor_repair_notes,
        })
    return {"success": True, "items": items, "vendor_name": vendor.vendor_name, "matched": True}


def _extract_vendor_token(request: Request) -> str:
    if request is None:
        raise HTTPException(status_code=401, detail="No request context")
    auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    raise HTTPException(status_code=401, detail="Authorization header missing")


# ─────────────────────────────────────────────────────────────────────────────
#  MEMBER — QR SCAN & DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vgk/vendor/scan/{qr_token}")
def scan_vendor_qr(qr_token: str, db: Session = Depends(get_db)):
    """
    Public endpoint — called when member scans QR (no auth required).
    Returns vendor info + product categories + marketplace products.
    """
    from app.models.vgk_vendor import VGKVendor, VGKVendorProductCategory, VGKVendorMarketplaceProduct
    v = db.query(VGKVendor).filter(
        VGKVendor.qr_token == qr_token,
        VGKVendor.is_active == True
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found or not active")
    prod_cats = db.query(VGKVendorProductCategory).filter(
        VGKVendorProductCategory.vendor_id == v.id,
        VGKVendorProductCategory.is_active == True
    ).order_by(VGKVendorProductCategory.display_order).all()
    # Public marketplace products — no auth needed (browse only)
    mkt_products = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.vendor_id == v.id,
        VGKVendorMarketplaceProduct.is_active == True
    ).order_by(
        VGKVendorMarketplaceProduct.is_featured.desc(),
        VGKVendorMarketplaceProduct.display_order
    ).all()
    # Build product_category lookup for grouping
    cat_lookup = {pc.id: pc.category_name for pc in prod_cats}
    def _prod(p):
        return {
            "id": p.id,
            "product_name": p.product_name,
            "product_kit": p.product_kit,
            "description": p.description,
            "price_excl_tax": float(p.price_excl_tax) if p.price_excl_tax else None,
            "price_with_tax": float(p.price_with_tax) if p.price_with_tax else None,
            "image_url_1": p.image_url_1,
            "image_url_2": p.image_url_2,
            "image_url_3": p.image_url_3,
            "is_featured": p.is_featured,
            "segment_slug": p.segment_slug,
        }
    return {
        "id": v.id,
        "vendor_id": v.id,
        "vendor_name": v.vendor_name,
        "vendor_code": v.vendor_code,
        "category_name": v.category_name,
        "shop_description": v.shop_description,
        "city": v.city,
        "pincode": v.pincode,
        "address_line1": v.address_line1,
        "phone": v.phone,
        "whatsapp_number": v.whatsapp_number,
        "map_link": v.map_link,
        "marketplace_opted": v.marketplace_opted,
        "logo_url": v.logo_url,
        "banner_url": v.banner_url,
        "flat_discount_pct": float(v.flat_discount_pct or 0),
        "product_categories": [
            {
                "id": pc.id,
                "category_name": pc.category_name,
                "gst_pct": float(pc.gst_pct or 0),
                "discount_pct": float(pc.discount_pct) if pc.discount_pct is not None else float(v.flat_discount_pct or 0),
                "description": pc.description,
            }
            for pc in prod_cats
        ],
        "marketplace_products": [_prod(p) for p in mkt_products],
    }


@router.post("/vgk/vendor/transaction")
def member_submit_vendor_transaction(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_vgk_member)
):
    from app.models.vgk_vendor import VGKVendor, VGKVendorTransaction, VGKVendorProductCategory
    from app.models.base import get_indian_time
    cid = current_member.company_id
    invoice_number = (payload.get("invoice_number") or "").strip()
    amount_excl_tax = Decimal(str(payload.get("amount_excl_tax") or 0))
    amount_total = Decimal(str(payload.get("amount_total") or 0))

    # Accept vendor_id OR vendor_qr_token (scan page sends qr_token)
    vendor_id = int(payload.get("vendor_id") or 0)
    vendor_qr_token = (payload.get("vendor_qr_token") or "").strip()
    if vendor_id:
        vendor = db.query(VGKVendor).filter(VGKVendor.id == vendor_id, VGKVendor.is_active == True).first()
    elif vendor_qr_token:
        vendor = db.query(VGKVendor).filter(VGKVendor.qr_token == vendor_qr_token, VGKVendor.is_active == True).first()
    else:
        vendor = None

    if not invoice_number or amount_excl_tax <= 0:
        raise HTTPException(status_code=400, detail="invoice_number and amount_excl_tax required")
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found or not active")
    vendor_id = vendor.id

    # Determine discount %
    product_cat_id = payload.get("product_category_id")
    discount_pct = Decimal(str(vendor.flat_discount_pct or 0))
    product_cat_name = None
    if product_cat_id:
        pc = db.query(VGKVendorProductCategory).filter(
            VGKVendorProductCategory.id == int(product_cat_id),
            VGKVendorProductCategory.vendor_id == vendor_id,
            VGKVendorProductCategory.is_active == True
        ).first()
        if pc:
            if pc.discount_pct is not None:
                discount_pct = Decimal(str(pc.discount_pct))
            product_cat_name = pc.category_name

    discount_amount = (amount_excl_tax * discount_pct / 100).quantize(Decimal('0.01'))
    gst_amount = amount_total - amount_excl_tax if amount_total > amount_excl_tax else Decimal('0')
    # Accept wallet_used_amount OR wallet_deduction_requested (scan page uses latter)
    wallet_used = Decimal(str(payload.get("wallet_used_amount") or payload.get("wallet_deduction_requested") or 0))

    # Validate wallet balance if member wants to pay from wallet
    if wallet_used > 0:
        member_wallet = Decimal(str(current_member.vgk_cash_wallet or 0))
        if wallet_used > member_wallet:
            raise HTTPException(status_code=400, detail=f"Insufficient wallet balance. Available: ₹{member_wallet}")

    txn_number = _next_txn_number(db, cid)
    mkt_product_id = payload.get("marketplace_product_id")
    txn = VGKVendorTransaction(
        company_id=cid,
        txn_number=txn_number,
        vendor_id=vendor_id,
        vendor_name=vendor.vendor_name,
        member_partner_id=current_member.id,
        product_category_id=int(product_cat_id) if product_cat_id else None,
        product_category_name=product_cat_name,
        marketplace_product_id=int(mkt_product_id) if mkt_product_id else None,
        invoice_number=invoice_number,
        invoice_date=get_indian_time(),
        amount_excl_tax=amount_excl_tax,
        gst_amount=gst_amount,
        amount_total=amount_total,
        discount_pct=discount_pct,
        discount_amount=discount_amount,
        wallet_used_amount=wallet_used,
        invoice_image_url=payload.get("invoice_image_url"),
        status='PENDING',
    )
    db.add(txn)
    try:
        db.commit()
        db.refresh(txn)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Submission failed: {e}")

    return {
        "success": True,
        "txn_number": txn_number,
        "discount_pct": float(discount_pct),
        "discount_amount": float(discount_amount),
        "wallet_used_amount": float(wallet_used),
        "message": "Purchase submitted. Accounts team will review and credit your wallet."
    }


@router.get("/vgk/vendor/transactions")
def member_vendor_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=50),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_vgk_member)
):
    from app.models.vgk_vendor import VGKVendorTransaction
    q = db.query(VGKVendorTransaction).filter(
        VGKVendorTransaction.member_partner_id == current_member.id
    )
    if status:
        q = q.filter(VGKVendorTransaction.status == status.upper())
    total = q.count()
    rows = q.order_by(VGKVendorTransaction.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {"total": total, "data": [_txn_dict(t) for t in rows]}


@router.get("/vgk/vendor/directory/categories")
def vendor_directory_categories(
    db: Session = Depends(get_db),
    current_member=Depends(get_current_vgk_member)
):
    from app.models.vgk_vendor import VGKVendorCategory
    cats = db.query(VGKVendorCategory).filter(
        VGKVendorCategory.company_id == current_member.company_id,
        VGKVendorCategory.is_active == True
    ).order_by(VGKVendorCategory.display_order, VGKVendorCategory.name).all()
    return [
        {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon or "fas fa-store"}
        for c in cats
    ]


@router.get("/vgk/vendor/directory")
def vendor_directory(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=50),
    category_id: Optional[int] = Query(None),
    pincode: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("name"),   # name | discount | newest
    db: Session = Depends(get_db),
    current_member=Depends(get_current_vgk_member)
):
    from app.models.vgk_vendor import VGKVendor, VGKVendorProductCategory
    q = db.query(VGKVendor).filter(
        VGKVendor.company_id == current_member.company_id,
        VGKVendor.is_active == True,
        VGKVendor.status == 'ACTIVE'
    )
    if category_id:
        q = q.filter(VGKVendor.category_id == category_id)
    if pincode:
        q = q.filter(VGKVendor.pincode == pincode.strip())
    if segment:
        q = q.filter(VGKVendor.category_name.ilike(f"%{segment}%"))
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(
            VGKVendor.vendor_name.ilike(s),
            VGKVendor.category_name.ilike(s),
            VGKVendor.city.ilike(s),
            VGKVendor.shop_description.ilike(s),
            VGKVendor.pincode.ilike(s),
        ))
    total = q.count()
    if sort_by == "discount":
        q = q.order_by(VGKVendor.flat_discount_pct.desc(), VGKVendor.vendor_name)
    elif sort_by == "newest":
        q = q.order_by(VGKVendor.id.desc())
    elif sort_by == "city":
        q = q.order_by(VGKVendor.city, VGKVendor.vendor_name)
    else:
        q = q.order_by(VGKVendor.vendor_name)
    vendors = q.offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for v in vendors:
        prod_cats = db.query(VGKVendorProductCategory).filter(
            VGKVendorProductCategory.vendor_id == v.id,
            VGKVendorProductCategory.is_active == True
        ).all()
        result.append({
            "id": v.id,
            "vendor_name": v.vendor_name,
            "vendor_code": v.vendor_code,
            "category_name": v.category_name,
            "shop_description": v.shop_description,
            "city": v.city, "pincode": v.pincode,
            "address_line1": v.address_line1,
            "phone": v.phone,
            "whatsapp_number": v.whatsapp_number,
            "map_link": v.map_link,
            "flat_discount_pct": float(v.flat_discount_pct or 0),
            "marketplace_opted": v.marketplace_opted,
            "logo_url": v.logo_url,
            "banner_url": v.banner_url,
            "qr_token": v.qr_token,
            "product_categories": [
                {
                    "id": pc.id,
                    "category_name": pc.category_name,
                    "gst_pct": float(pc.gst_pct or 0),
                    "discount_pct": float(pc.discount_pct) if pc.discount_pct is not None else float(v.flat_discount_pct or 0),
                }
                for pc in prod_cats
            ]
        })
    return {"total": total, "page": page, "per_page": per_page, "vendors": result}


@router.get("/vgk/vendor/directory/{vendor_id}/products")
def vendor_marketplace_products_public(
    vendor_id: int,
    segment: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_vgk_member)
):
    from app.models.vgk_vendor import VGKVendorMarketplaceProduct, VGKVendor
    vendor = db.query(VGKVendor).filter(
        VGKVendor.id == vendor_id,
        VGKVendor.company_id == current_member.company_id,
        VGKVendor.is_active == True
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    # Increment views
    q = db.query(VGKVendorMarketplaceProduct).filter(
        VGKVendorMarketplaceProduct.vendor_id == vendor_id,
        VGKVendorMarketplaceProduct.is_active == True,
        VGKVendorMarketplaceProduct.approval_status == 'APPROVED'
    )
    if segment:
        q = q.filter(VGKVendorMarketplaceProduct.segment_slug == segment)
    products = q.order_by(
        VGKVendorMarketplaceProduct.is_featured.desc(),
        VGKVendorMarketplaceProduct.display_order
    ).all()
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.vendor_name,
        "products": [_product_dict(p) for p in products]
    }
