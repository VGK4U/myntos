"""
VGK4U — PO Management API (Phase 2)
DC Protocol: company_id enforced. WVV: atomic PO creation + dispatch.
Public: PO creation (no auth). Staff: list, view, dispatch, procurement.
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.marketplace import (
    MarketspareItem, MarketplacePurchaseOrder, MarketplacePOItem,
    MarketplacePODispatch, MarketplaceProcurementRequest, MarketplaceCategoryConfig,
    MarketplacePromoCode, MarketplaceSegment,
)
from app.models.crm import CRMLeadTransaction
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry, IncomeEntry, IncomeSourceType
from app.services.marketplace_sync import run_sync
from app.services.vgk_commission import _next_vgk_entry_number, get_indian_time

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class POBasketItem(BaseModel):
    sku: str
    product_name: str
    category_name: Optional[str] = None
    brand: Optional[str] = None
    specifications: Optional[str] = None
    speciality: Optional[str] = None
    color: Optional[str] = None
    warranty_details: Optional[str] = None
    ordered_qty: int = Field(ge=1)
    dealer_price: float = 0
    discount_amount: float = 0
    net_price: float = 0
    gst_percent: float = 18
    gst_amount: float = 0
    unit_final_price: float = 0
    line_total: float = 0


class CreatePORequest(BaseModel):
    customer_name: str = Field(min_length=2)
    customer_phone: str = Field(min_length=7)
    customer_email: Optional[str] = None
    mnr_id: Optional[str] = None
    partner_code: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    discount_mode: Optional[str] = None
    discount_name: Optional[str] = None
    # Discount coupon tracking — March 2026
    discount_coupon_id: Optional[str] = None
    coupon_entered_by_staff_id: Optional[int] = None
    # Bill To / Ship To — March 2026
    bill_name: Optional[str] = None
    bill_phone: Optional[str] = None
    bill_address: Optional[str] = None
    ship_name: Optional[str] = None
    ship_phone: Optional[str] = None
    ship_address: Optional[str] = None
    ship_same_as_bill: bool = True
    items: List[POBasketItem] = Field(min_length=1)
    company_id: int = 1


class POAddressUpdate(BaseModel):
    bill_name: Optional[str] = None
    bill_phone: Optional[str] = None
    bill_address: Optional[str] = None
    ship_name: Optional[str] = None
    ship_phone: Optional[str] = None
    ship_address: Optional[str] = None
    ship_same_as_bill: Optional[bool] = None


class DispatchItemUpdate(BaseModel):
    po_item_id: int
    dispatched_qty: int = Field(ge=0)
    revenue_collected: float = Field(ge=0)
    dispatch_notes: Optional[str] = None
    courier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None


class DispatchRequest(BaseModel):
    items: List[DispatchItemUpdate]


class ProcurementStatusUpdate(BaseModel):
    status: str
    procurement_notes: Optional[str] = None
    received_qty: Optional[int] = None
    store_manager_id: Optional[int] = None


class POStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    store_manager_id: Optional[int] = None


class AssignManagerRequest(BaseModel):
    store_manager_id: int


class POPaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_mode: str = 'cash'
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    transaction_date: Optional[str] = None


class StockUpdateRequest(BaseModel):
    available_qty: int = Field(ge=0)
    notes: Optional[str] = None


class POItemAddRequest(BaseModel):
    sku: str
    product_name: str
    category_name: Optional[str] = None
    brand: Optional[str] = None
    specifications: Optional[str] = None
    speciality: Optional[str] = None
    color: Optional[str] = None
    warranty_details: Optional[str] = None
    ordered_qty: int = Field(ge=1, default=1)
    dealer_price: float = Field(ge=0, default=0)
    gst_percent: float = Field(ge=0, default=18)


class POItemUpdateRequest(BaseModel):
    ordered_qty: Optional[int] = Field(None, ge=1)
    dealer_price: Optional[float] = Field(None, ge=0)
    gst_percent: Optional[float] = Field(None, ge=0)


class CatalogSearchResponse(BaseModel):
    id: int
    sku: str
    name: str
    category_name: str
    company_name: str
    available_qty: int
    dealer_price: float
    discount_pct: float
    discount_amount: float
    net_before_tax: float
    gst_amount: float
    final_price: float
    gst_percent: float
    hsn_code: Optional[str]
    image_url: Optional[str]
    specifications: Optional[str] = None
    speciality: Optional[str] = None
    color: Optional[str] = None
    warranty_details: Optional[str] = None


class POCouponUpdate(BaseModel):
    discount_coupon_id: Optional[str] = None
    discount_mode: Optional[str] = None
    discount_name: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _generate_po_number(db: Session, company_id: int) -> tuple[str, int]:
    """Generate unique ZYPO-YYYYMM-NNNN number. Returns (po_number, count)."""
    ym = datetime.utcnow().strftime('%Y%m')
    prefix = f'ZYPO-{ym}-'
    db.execute(text("SET LOCAL statement_timeout = '60s'"))  # DC: override any shorter global timeout
    count_row = db.execute(text(
        "SELECT COUNT(*)+1 FROM marketplace_purchase_orders WHERE po_number LIKE :pfx AND company_id = :cid"
    ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
    count = int(count_row[0]) if count_row else 1
    po_number = f'{prefix}{count:04d}'
    # Guard against race condition
    while db.query(MarketplacePurchaseOrder).filter_by(po_number=po_number).first():
        count += 1
        po_number = f'{prefix}{count:04d}'
    return po_number, count


def _generate_proc_number(db: Session, company_id: int) -> str:
    """Generate unique ZYPR-YYYYMM-NNNN procurement number."""
    ym = datetime.utcnow().strftime('%Y%m')
    prefix = f'ZYPR-{ym}-'
    db.execute(text("SET LOCAL statement_timeout = '60s'"))  # DC: override any shorter global timeout
    count_row = db.execute(text(
        "SELECT COUNT(*)+1 FROM marketplace_procurement_requests WHERE procurement_number LIKE :pfx AND company_id = :cid"
    ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
    count = int(count_row[0]) if count_row else 1
    proc_number = f'{prefix}{count:04d}'
    while db.query(MarketplaceProcurementRequest).filter_by(procurement_number=proc_number).first():
        count += 1
        proc_number = f'{prefix}{count:04d}'
    return proc_number


def _determine_customer_type(mnr_id, partner_code, discount_mode=None) -> str:
    if mnr_id:
        return 'mnr_member'
    if discount_mode == 'vgk':
        return 'vgk_member'
    if partner_code:
        return 'partner'
    return 'public'


def _compute_po_totals(items: List[POBasketItem]):
    total_items = len(items)
    total_ordered_qty = sum(i.ordered_qty for i in items)
    total_value = sum(i.line_total for i in items)
    return total_items, total_ordered_qty, total_value


def _get_dispatch_summary(db: Session, po_id: int):
    """Compute dispatched totals and revenue per PO."""
    db.execute(text("SET LOCAL statement_timeout = '60s'"))
    rows = db.execute(text("""
        SELECT
            SUM(d.dispatched_qty) as total_dispatched,
            SUM(d.revenue_collected) as total_revenue
        FROM marketplace_po_dispatch d
        WHERE d.po_id = :po_id
    """), {'po_id': po_id}).fetchone()
    return {
        'total_dispatched': int(rows[0] or 0),
        'total_revenue': float(rows[1] or 0),
    }


def _get_item_dispatch_summary(db: Session, po_item_ids: List[int]):
    """Per-item dispatched qty and revenue."""
    if not po_item_ids:
        return {}
    db.execute(text("SET LOCAL statement_timeout = '60s'"))
    rows = db.execute(text("""
        SELECT po_item_id,
               SUM(dispatched_qty) as disp,
               SUM(revenue_collected) as rev
        FROM marketplace_po_dispatch
        WHERE po_item_id = ANY(:ids)
        GROUP BY po_item_id
    """), {'ids': po_item_ids}).fetchall()
    return {r[0]: {'dispatched_qty': int(r[1] or 0), 'revenue_collected': float(r[2] or 0)} for r in rows}


# ── GET /catalog-search — Staff catalog search ───────────────────────────────

@router.get('/catalog-search', response_model=List[CatalogSearchResponse], tags=['marketplace-po'])
def catalog_search(
    q: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    limit: int = Query(300, ge=1, le=500),
    discount_mode: Optional[str] = Query(None), # mnr/dealer/student/partner
    discount_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Staff catalog search with real-time pricing based on discount mode.
    When company_id is omitted, searches across all companies (global catalog).
    Discount %: mnr=3, student=10, dealer=12, partner=12
    Price: net=dealer_price*(1-disc%), final=net*(1+gst_pct/100)
    """
    query = db.query(MarketspareItem).filter(MarketspareItem.is_active == True)
    if company_id is not None:
        query = query.filter(MarketspareItem.company_id == company_id)

    if q:
        search_filter = f'%{q}%'
        query = query.filter(
            MarketspareItem.name.ilike(search_filter) |
            MarketspareItem.sku.ilike(search_filter) |
            MarketspareItem.category_name.ilike(search_filter)
        )
        query = query.order_by(
            text(f"CASE WHEN name ILIKE :q THEN 0 ELSE 1 END").bindparams(q=search_filter),
            MarketspareItem.name.asc()
        )
    else:
        query = query.order_by(MarketspareItem.name.asc())

    spares = query.limit(limit).all()

    # Get category configs for GST and HSN — prefer the item's own company, fall back to company 1
    cat_names = list(set(s.category_name for s in spares))
    config_filter = MarketplaceCategoryConfig.category_name.in_(cat_names)
    all_configs = db.query(MarketplaceCategoryConfig).filter(config_filter).all()
    # Build map: prefer the specific company's config, else take any available
    config_map: dict = {}
    for c in all_configs:
        if c.category_name not in config_map or c.company_id == (company_id or 1):
            config_map[c.category_name] = c

    # Discount logic
    discount_pct = 0
    if discount_mode == 'mnr':
        discount_pct = 3
    elif discount_mode == 'student':
        discount_pct = 10
    elif discount_mode in ['dealer', 'partner']:
        discount_pct = 12
    elif discount_mode == 'vgk':
        discount_pct = 3

    results = []
    for s in spares:
        conf = config_map.get(s.category_name)
        gst_pct = float(s.gst_percent if s.gst_percent is not None else (conf.gst_percent if conf else 18))
        hsn = s.speciality if hasattr(s, 'hsn_code') and getattr(s, 'hsn_code') else (conf.hsn_code if conf else None)
        # Note: speciality is used for HSN in some parts of the system or it might be a separate col.
        # Checking model: speciality exists, hsn_code exists in CategoryConfig.
        # MarketspareItem does NOT have hsn_code in its definition above.

        dealer_price = float(s.dealer_price or 0)
        disc_amount = dealer_price * (discount_pct / 100)
        net_before_tax = dealer_price - disc_amount
        gst_amount = net_before_tax * (gst_pct / 100)
        final_price = net_before_tax + gst_amount

        results.append({
            'id': s.id,
            'sku': s.sku,
            'name': s.name,
            'category_name': s.category_name,
            'company_name': s.company_name or '',
            'available_qty': int(s.available_qty or 0),
            'dealer_price': dealer_price,
            'discount_pct': float(discount_pct),
            'discount_amount': disc_amount,
            'net_before_tax': net_before_tax,
            'gst_amount': gst_amount,
            'final_price': final_price,
            'gst_percent': gst_pct,
            'hsn_code': hsn,
            'image_url': s.image_url,
            'specifications': s.specifications or '',
            'speciality': s.speciality or '',
            'color': s.color or '',
            'warranty_details': s.warranty_details or '',
        })

    return results


# ── GET /public/validate-discount-id — Validate discount ID (no auth) ──────────
@router.get('/public/validate-discount-id', tags=['marketplace-po'])
def validate_public_discount_id(id: str = Query(...), db: Session = Depends(get_db)):
    """
    Validate a discount ID for the public service ticket form.
    Detects type by prefix and validates against DB.
    MNR1823XXXXX → MNR Member 3% | VGK0710XXXX → VGK Member 3% | VGK18080XXX → ETC Student 10% | DLAP... → Partner 12%
    No auth required. Read-only.
    """
    id_clean = id.strip()
    if not id_clean:
        return {'valid': False, 'error': 'Please enter an ID'}

    if id_clean.upper().startswith('MNR'):
        row = db.execute(
            text("SELECT id, name FROM \"user\" WHERE id = :mid LIMIT 1"),
            {'mid': id_clean}
        ).fetchone()
        if row:
            return {'valid': True, 'discount_mode': 'mnr', 'discount_pct': 3,
                    'label': 'MNR Member', 'name': row.name or ''}
        return {'valid': False, 'error': 'MNR ID not found in the system'}

    if id_clean.upper().startswith('VGK0710'):
        row = db.execute(
            text("SELECT id, partner_name, is_paid_activation FROM official_partners WHERE UPPER(partner_code) = :sid AND category = 'VGK_TEAM' LIMIT 1"),
            {'sid': id_clean.upper()}
        ).fetchone()
        if row:
            # DC Protocol Apr 2026: eligibility gated by points balance (not is_active flag)
            pb = db.execute(
                text("SELECT current_balance FROM mnr_points_balance WHERE user_id = :uid LIMIT 1"),
                {'uid': id_clean.upper()}
            ).fetchone()
            if not pb or (pb.current_balance is not None and pb.current_balance <= 0):
                return {'valid': False, 'error': 'Insufficient points balance for discount'}
            _vgk_disc = 3 if row.is_paid_activation else 2
            return {'valid': True, 'discount_mode': 'vgk', 'discount_pct': _vgk_disc,
                    'label': 'VGK Member', 'name': row.partner_name or '',
                    'is_paid_activation': bool(row.is_paid_activation)}
        return {'valid': False, 'error': 'VGK member code not found'}

    if id_clean.upper().startswith('VGK'):
        row = db.execute(
            text("SELECT id, name FROM etc_students WHERE student_id = :sid AND is_active = TRUE LIMIT 1"),
            {'sid': id_clean}
        ).fetchone()
        if row:
            return {'valid': True, 'discount_mode': 'student', 'discount_pct': 10,
                    'label': 'ETC Student', 'name': row.name or ''}
        return {'valid': False, 'error': 'Student ID not found or inactive'}

    row = db.execute(
        text("SELECT id, partner_name FROM official_partners WHERE partner_code ILIKE :pc LIMIT 1"),
        {'pc': id_clean}
    ).fetchone()
    if row:
        return {'valid': True, 'discount_mode': 'partner', 'discount_pct': 12,
                'label': 'Partner/Dealer', 'name': row.partner_name or ''}
    return {'valid': False, 'error': 'ID not recognised. Check and try again.'}


# ── GET /public/catalog-search — Public catalog search (no auth, VGK4U default) ──
@router.get('/public/catalog-search', tags=['marketplace-po'])
def public_catalog_search(
    q: Optional[str] = Query(None),
    company_id: int = Query(1),
    discount_mode: Optional[str] = Query(None),
    discount_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Public catalog search — no auth required.
    Used by public service ticket form (Spare Parts mode).
    discount_id: if provided, auto-detects discount_mode from ID type/DB validation.
    Returns brand, specifications for product spec view.
    DC Protocol: company_id defaults to 1 (Zynova).
    """
    if discount_id and discount_id.strip():
        id_clean = discount_id.strip()
        if id_clean.upper().startswith('MNR'):
            row = db.execute(text("SELECT id FROM \"user\" WHERE id = :mid LIMIT 1"), {'mid': id_clean}).fetchone()
            if row:
                discount_mode = 'mnr'
        elif id_clean.upper().startswith('VGK0710'):
            row = db.execute(text("SELECT id FROM official_partners WHERE UPPER(partner_code) = :sid AND category = 'VGK_TEAM' AND is_active = TRUE LIMIT 1"), {'sid': id_clean.upper()}).fetchone()
            if row:
                discount_mode = 'vgk'
        elif id_clean.upper().startswith('VGK'):
            row = db.execute(text("SELECT id FROM etc_students WHERE student_id = :sid AND is_active = TRUE LIMIT 1"), {'sid': id_clean}).fetchone()
            if row:
                discount_mode = 'student'
        else:
            row = db.execute(text("SELECT id FROM official_partners WHERE partner_code ILIKE :pc LIMIT 1"), {'pc': id_clean}).fetchone()
            if row:
                discount_mode = 'partner'

    query = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True
    )
    if q:
        search_filter = f'%{q}%'
        query = query.filter(
            MarketspareItem.name.ilike(search_filter) |
            MarketspareItem.sku.ilike(search_filter) |
            MarketspareItem.category_name.ilike(search_filter)
        )
        query = query.order_by(
            text("CASE WHEN name ILIKE :q THEN 0 ELSE 1 END").bindparams(q=search_filter),
            MarketspareItem.name.asc()
        )
    else:
        query = query.order_by(MarketspareItem.name.asc())

    spares = query.limit(30).all()

    cat_names = list(set(s.category_name for s in spares))
    configs = db.query(MarketplaceCategoryConfig).filter(
        MarketplaceCategoryConfig.category_name.in_(cat_names),
        MarketplaceCategoryConfig.company_id == company_id
    ).all()
    config_map = {c.category_name: c for c in configs}

    discount_pct = 0
    if discount_mode == 'mnr':
        discount_pct = 3
    elif discount_mode == 'student':
        discount_pct = 10
    elif discount_mode in ['dealer', 'partner']:
        discount_pct = 12
    elif discount_mode == 'vgk':
        discount_pct = 3

    results = []
    for s in spares:
        conf = config_map.get(s.category_name)
        gst_pct = float(s.gst_percent if s.gst_percent is not None else (conf.gst_percent if conf else 18))
        hsn = (conf.hsn_code if conf else None)
        dealer_price = float(s.dealer_price or 0)
        disc_amount = dealer_price * (discount_pct / 100)
        net_before_tax = dealer_price - disc_amount
        gst_amount = net_before_tax * (gst_pct / 100)
        final_price = net_before_tax + gst_amount
        results.append({
            'id': s.id,
            'sku': s.sku,
            'name': s.name,
            'category_name': s.category_name,
            'brand': s.brand or '',
            'specifications': s.specifications or '',
            'speciality': s.speciality or '',
            'color': s.color or '',
            'warranty_details': s.warranty_details or '',
            'dealer_price': dealer_price,
            'discount_pct': float(discount_pct),
            'discount_amount': round(disc_amount, 2),
            'net_before_tax': round(net_before_tax, 2),
            'gst_amount': round(gst_amount, 2),
            'final_price': round(final_price, 2),
            'gst_percent': gst_pct,
            'hsn_code': hsn,
            'image_url': s.image_url,
        })
    return results


# ── POST /pos/ — Create PO (public, no auth) ──────────────────────────────────

@router.post('/pos/', tags=['marketplace-po'])
def create_purchase_order(request: Request, payload: CreatePORequest = Body(...), db: Session = Depends(get_db)):
    """
    Create a PO from basket. Public endpoint — no auth required.
    WVV: atomic — PO header + items + procurement records in one transaction.
    Stock check: if item.stock_qty < ordered_qty → create procurement record.
    VGK discount mode requires staff authentication.
    """
    if payload.discount_mode == 'vgk':
        from app.api.v1.endpoints.staff_auth import get_current_staff_user
        try:
            get_current_staff_user(request, db)
        except Exception:
            raise HTTPException(status_code=401, detail='Staff authentication required for VGK discount')
    company_id = payload.company_id or 1

    try:
        po_number, po_count = _generate_po_number(db, company_id)
        total_items, total_ordered_qty, total_value = _compute_po_totals(payload.items)
        customer_type = _determine_customer_type(payload.mnr_id, payload.partner_code, payload.discount_mode)

        # Create PO header
        # Resolve bill_name / bill_phone (fall back to customer_name / customer_phone)
        _bill_name  = payload.bill_name  or payload.customer_name
        _bill_phone = payload.bill_phone or payload.customer_phone
        _bill_addr  = payload.bill_address or payload.delivery_address
        if payload.ship_same_as_bill:
            _ship_name  = _bill_name
            _ship_phone = _bill_phone
            _ship_addr  = _bill_addr
        else:
            _ship_name  = payload.ship_name  or _bill_name
            _ship_phone = payload.ship_phone or _bill_phone
            _ship_addr  = payload.ship_address or _bill_addr

        po = MarketplacePurchaseOrder(
            po_number=po_number,
            po_count=po_count,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            customer_email=payload.customer_email,
            mnr_id=payload.mnr_id,
            partner_code=payload.partner_code,
            delivery_address=_bill_addr,
            customer_type=customer_type,
            discount_mode=payload.discount_mode,
            discount_name=payload.discount_name,
            discount_coupon_id=payload.discount_coupon_id,
            coupon_entered_by_staff_id=payload.coupon_entered_by_staff_id,
            coupon_entered_at=datetime.utcnow() if payload.discount_coupon_id else None,
            total_items=total_items,
            total_ordered_qty=total_ordered_qty,
            total_value=total_value,
            notes=payload.notes,
            status='confirmed',
            bill_name=_bill_name,
            bill_phone=_bill_phone,
            bill_address=_bill_addr,
            ship_name=_ship_name,
            ship_phone=_ship_phone,
            ship_address=_ship_addr,
            ship_same_as_bill=payload.ship_same_as_bill,
            company_id=company_id,
        )
        db.add(po)
        db.flush()  # get po.id without committing

        # ── Store task hook: add phase for this PO ──────────────────────────
        from app.services.store_task_service import add_po_phase as _add_po_phase
        _add_po_phase(db, po, company_id)
        # ───────────────────────────────────────────────────────────────────

        # Increment times_used on promo code when a PO is placed
        if payload.discount_mode == 'promo' and payload.discount_name:
            pc = db.query(MarketplacePromoCode).filter(
                MarketplacePromoCode.code == payload.discount_name.strip().upper(),
                MarketplacePromoCode.company_id == company_id,
            ).first()
            if not pc:
                # discount_name may be the label rather than the code; try matching the assocInput value
                pc = db.query(MarketplacePromoCode).filter(
                    MarketplacePromoCode.label == payload.discount_name,
                    MarketplacePromoCode.company_id == company_id,
                ).first()
            if pc:
                pc.times_used = (pc.times_used or 0) + 1

        procurement_records = []
        po_items_created = []

        for item in payload.items:
            # Stock availability check — uses available_qty (sheet col 23, synced per sync)
            spare = db.query(MarketspareItem).filter_by(sku=item.sku, company_id=company_id).first()
            stock_available = int(spare.available_qty or 0) if spare else 0
            procurement_required = stock_available < item.ordered_qty

            # Enrich specs/warranty from live catalog if basket didn't supply them
            _spec      = item.specifications or (spare.specifications if spare else None)
            _speciality= item.speciality     or (spare.speciality     if spare else None)
            _warranty  = item.warranty_details or (spare.warranty_details if spare else None)

            po_item = MarketplacePOItem(
                po_id=po.id,
                sku=item.sku,
                product_name=item.product_name,
                category_name=item.category_name,
                brand=item.brand,
                specifications=_spec,
                speciality=_speciality,
                color=item.color,
                warranty_details=_warranty,
                ordered_qty=item.ordered_qty,
                dealer_price=item.dealer_price,
                discount_amount=item.discount_amount,
                net_price=item.net_price,
                gst_percent=item.gst_percent,
                gst_amount=item.gst_amount,
                unit_final_price=item.unit_final_price,
                line_total=item.line_total,
                stock_available=stock_available,
                procurement_required=procurement_required,
                company_id=company_id,
            )
            db.add(po_item)
            db.flush()

            po_items_created.append(po_item)

            if procurement_required:
                shortfall = item.ordered_qty - stock_available
                proc_number = _generate_proc_number(db, company_id)
                proc = MarketplaceProcurementRequest(
                    procurement_number=proc_number,
                    po_id=po.id,
                    po_item_id=po_item.id,
                    sku=item.sku,
                    product_name=item.product_name,
                    ordered_qty=item.ordered_qty,
                    available_qty=stock_available,
                    shortfall_qty=shortfall,
                    status='pending',
                    company_id=company_id,
                )
                db.add(proc)
                db.flush()

                # ── Store task hook: add phase for this PR ──────────────────
                from app.services.store_task_service import add_pr_phase as _add_pr_phase
                _add_pr_phase(db, proc, company_id)
                # ────────────────────────────────────────────────────────────

                procurement_records.append({
                    'procurement_number': proc_number,
                    'sku': item.sku,
                    'product_name': item.product_name,
                    'ordered_qty': item.ordered_qty,
                    'available_qty': stock_available,
                    'shortfall_qty': shortfall,
                })

        if payload.discount_mode == 'vgk' and payload.partner_code:
            # DC Protocol Mar 2026: Paid-aware VGK spares discount (10% paid, 3% non-paid)
            _vgk_partner_pre = db.query(OfficialPartner).filter(
                OfficialPartner.partner_code == payload.partner_code,
                OfficialPartner.category == 'VGK_TEAM',
            ).first()
            _is_paid_pre = bool(getattr(_vgk_partner_pre, 'is_paid_activation', False)) if _vgk_partner_pre else False
            if _is_paid_pre:
                _seg = db.query(MarketplaceSegment).filter(
                    MarketplaceSegment.company_id == company_id,
                    MarketplaceSegment.is_active == True,
                ).order_by(MarketplaceSegment.sort_order).first()
                _vgk_pct = float(_seg.vgk_pct) if _seg and _seg.vgk_pct is not None else 3.0
            else:
                _vgk_pct = 2.0
            vgk_discount_pct = Decimal(str(_vgk_pct / 100))
            total_discount = (Decimal(str(total_value)) * vgk_discount_pct).quantize(Decimal('0.01'))
            if total_discount > 0:
                vgk_partner = db.query(OfficialPartner).filter(
                    OfficialPartner.partner_code == payload.partner_code,
                    OfficialPartner.category == 'VGK_TEAM',
                ).first()
                if not vgk_partner:
                    raise HTTPException(status_code=400, detail='Invalid VGK member code for discount')
                current_balance = vgk_partner.vgk_points_balance or Decimal('0')
                if current_balance < total_discount:
                    raise HTTPException(
                        status_code=400,
                        detail=f'Insufficient VGK points balance ({float(current_balance):.0f}) for discount ({float(total_discount):.0f})'
                    )
                now = get_indian_time()
                debit_entry_no = _next_vgk_entry_number(db, company_id, prefix='VGKM')
                debit = VGKTeamIncomeEntry(
                    company_id=company_id,
                    entry_number=debit_entry_no,
                    partner_id=vgk_partner.id,
                    source_lead_id=None,
                    source_transaction_id=None,
                    category_id=None,
                    level=0,
                    revenue_amount=Decimal(str(total_value)),
                    commission_pct=Decimal('3'),
                    commission_amount=total_discount,
                    bonus_amount=Decimal('0'),
                    status='CONFIRMED',
                    notes=f'DEBIT: Marketplace Discount on PO {po_number} (3% level discount)',
                    confirmed_at=now,
                    confirmed_by=None,
                    created_at=now,
                    updated_at=now
                )
                db.add(debit)
                vgk_partner.vgk_points_balance = current_balance - total_discount
                vgk_partner.updated_at = now
                logger.info(f'[VGK-MKT-DEBIT] Partner {payload.partner_code}: {total_discount} pts debited for PO {po_number}')
                from app.api.v1.endpoints.vgk_team import _check_and_apply_auto_refill
                _check_and_apply_auto_refill(vgk_partner, db, now)

        # DC_PARTNER_STOCK_AUTOSYNC_001: auto stock-IN for dealer/partner orders
        if payload.discount_mode in ('dealer', 'partner') and payload.partner_code:
            try:
                _dealer = db.execute(text(
                    "SELECT id FROM official_partners WHERE partner_code=:code AND is_active=TRUE LIMIT 1"
                ), {"code": payload.partner_code.strip().upper()}).fetchone()
                if _dealer:
                    from app.services.partner_stock_service import auto_partner_stock_sync
                    _sync_items = [
                        {
                            "item_name": it.product_name,
                            "item_code": it.sku,
                            "marketplace_sku": it.sku,
                            "qty": float(it.ordered_qty),
                            "selling_price": float(it.dealer_price) if it.dealer_price else None,
                        }
                        for it in payload.items
                    ]
                    auto_partner_stock_sync(
                        db=db,
                        partner_id=_dealer[0],
                        items=_sync_items,
                        adj_type="PURCHASE_IN",
                        ref_doc_type="MARKETPLACE_PO",
                        ref_doc_id=po.id,
                        ref_doc_number=po_number,
                        reason=f"Auto: Marketplace purchase via dealer code {payload.partner_code}",
                        created_by="marketplace_po",
                    )
            except Exception as _e:
                logger.warning(f"[AUTO_STOCK_SYNC] Marketplace PO hook skipped: {_e}")

        db.commit()

        logger.info(f'[PO-CREATE] {po_number} — {total_items} items, ₹{total_value:.2f}, '
                    f'{len(procurement_records)} procurement records')

        return {
            'success': True,
            'po_number': po_number,
            'po_count': po_count,
            'po_id': po.id,
            'total_items': total_items,
            'total_ordered_qty': total_ordered_qty,
            'total_value': float(total_value),
            'procurement_required': len(procurement_records) > 0,
            'procurement_records': procurement_records,
            'message': f'PO {po_number} created successfully.',
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'[PO-CREATE] Failed: {e}')
        raise HTTPException(status_code=500, detail=f'PO creation failed: {str(e)}')


# ── GET /pos/ — List POs (staff auth) ─────────────────────────────────────────

@router.get('/pos/', tags=['marketplace-po'])
def list_purchase_orders(
    company_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    customer_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query('created_at'),
    sort_dir: str = Query('desc'),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    q = db.query(MarketplacePurchaseOrder)
    if company_id is not None:
        q = q.filter(MarketplacePurchaseOrder.company_id == company_id)
    if source_type:
        q = q.filter(MarketplacePurchaseOrder.source_type == source_type)
    if status:
        q = q.filter(MarketplacePurchaseOrder.status == status)
    if customer_type:
        q = q.filter(MarketplacePurchaseOrder.customer_type == customer_type)
    if search:
        s = f'%{search}%'
        q = q.filter(
            MarketplacePurchaseOrder.po_number.ilike(s) |
            MarketplacePurchaseOrder.customer_name.ilike(s) |
            MarketplacePurchaseOrder.customer_phone.ilike(s) |
            MarketplacePurchaseOrder.mnr_id.ilike(s) |
            MarketplacePurchaseOrder.partner_code.ilike(s)
        )
    if date_from:
        try:
            q = q.filter(MarketplacePurchaseOrder.created_at >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            q = q.filter(MarketplacePurchaseOrder.created_at <= datetime.fromisoformat(date_to + 'T23:59:59'))
        except Exception:
            pass

    # Sorting
    allowed_sort = {'created_at', 'po_number', 'customer_name', 'total_value', 'status', 'total_ordered_qty'}
    sort_col = sort_by if sort_by in allowed_sort else 'created_at'
    sort_attr = getattr(MarketplacePurchaseOrder, sort_col)
    if sort_dir == 'asc':
        q = q.order_by(sort_attr.asc())
    else:
        q = q.order_by(sort_attr.desc())

    total = q.count()
    pos = q.offset((page - 1) * per_page).limit(per_page).all()

    # Bulk-fetch store manager names
    mgr_ids = {po.store_manager_id for po in pos if po.store_manager_id}
    mgr_name_map = {}
    if mgr_ids:
        mgr_rows = db.query(StaffEmployee.id, StaffEmployee.full_name).filter(
            StaffEmployee.id.in_(mgr_ids)
        ).all()
        mgr_name_map = {r.id: r.full_name for r in mgr_rows}

    # DC-POS-BATCH-001: Bulk-fetch dispatch summaries and procurement counts in 2
    # queries instead of 2×N individual queries (was causing 57-second timeouts at
    # per_page=100).
    po_ids = [po.id for po in pos]
    dispatch_map: dict = {}
    proc_map: dict = {}
    if po_ids:
        disp_rows = db.execute(text("""
            SELECT po_id,
                   COALESCE(SUM(dispatched_qty), 0)     AS total_dispatched,
                   COALESCE(SUM(revenue_collected), 0)  AS total_revenue
            FROM marketplace_po_dispatch
            WHERE po_id = ANY(:ids)
            GROUP BY po_id
        """), {'ids': po_ids}).fetchall()
        dispatch_map = {r[0]: {'total_dispatched': int(r[1]), 'total_revenue': float(r[2])} for r in disp_rows}

        proc_rows = db.execute(text("""
            SELECT po_id, COUNT(*) AS cnt
            FROM marketplace_procurement_requests
            WHERE po_id = ANY(:ids)
            GROUP BY po_id
        """), {'ids': po_ids}).fetchall()
        proc_map = {r[0]: int(r[1]) for r in proc_rows}

    # Attach dispatch summary to each PO
    result_pos = []
    for po in pos:
        d = po.to_dict()
        summary = dispatch_map.get(po.id, {'total_dispatched': 0, 'total_revenue': 0.0})
        d['total_dispatched'] = summary['total_dispatched']
        d['revenue_collected'] = summary['total_revenue']
        d['balance_qty'] = d['total_ordered_qty'] - summary['total_dispatched']
        d['balance_revenue'] = float(d['total_value']) - summary['total_revenue']
        d['store_manager_name'] = mgr_name_map.get(po.store_manager_id) if po.store_manager_id else None
        d['procurement_count'] = proc_map.get(po.id, 0)
        result_pos.append(d)

    return {
        'pos': result_pos,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


# ── GET /pos/staff-list — Active staff list for manager assignment ─────────────

@router.get('/pos/staff-list', tags=['marketplace-po'])
def get_staff_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Returns active staff list for store manager assignment dropdowns."""
    rows = db.query(
        StaffEmployee.id,
        StaffEmployee.full_name,
        StaffEmployee.emp_code,
        StaffEmployee.designation,
    ).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False,
    ).order_by(StaffEmployee.full_name).all()
    return [
        {'id': r.id, 'full_name': r.full_name, 'emp_code': r.emp_code or '', 'designation': r.designation or ''}
        for r in rows
    ]


# ── GET /pos/{po_id} — PO detail (staff auth) ─────────────────────────────────

@router.get('/pos/{po_id}', tags=['marketplace-po'])
def get_purchase_order(
    po_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    # Use PO's own company_id for catalog lookups
    _cid = po.company_id or company_id or 1

    po_data = po.to_dict()
    items = db.query(MarketplacePOItem).filter_by(po_id=po_id).all()
    item_ids = [i.id for i in items]
    dispatch_map = _get_item_dispatch_summary(db, item_ids)

    # Bulk-fetch full catalog data for all SKUs — used for fallback enrichment + hsn_code
    skus = [i.sku for i in items if i.sku]
    spare_rows = db.query(
        MarketspareItem.sku,
        MarketspareItem.model_compat,
        MarketspareItem.specifications,
        MarketspareItem.speciality,
        MarketspareItem.warranty_details,
        MarketspareItem.category_name,
    ).filter(
        MarketspareItem.sku.in_(skus), MarketspareItem.company_id == _cid
    ).all()
    spare_map = {r.sku: r for r in spare_rows}

    # Bulk-fetch HSN codes from category config
    cat_names = list({r.category_name for r in spare_rows if r.category_name})
    cat_configs = db.query(
        MarketplaceCategoryConfig.category_name,
        MarketplaceCategoryConfig.hsn_code,
    ).filter(
        MarketplaceCategoryConfig.category_name.in_(cat_names),
        MarketplaceCategoryConfig.company_id == _cid,
    ).all()
    hsn_map = {c.category_name: c.hsn_code for c in cat_configs}

    # Fetch coupon-entered-by staff name if present
    coupon_staff_name = None
    if po.coupon_entered_by_staff_id:
        cs = db.query(StaffEmployee.full_name).filter_by(id=po.coupon_entered_by_staff_id).first()
        coupon_staff_name = cs.full_name if cs else None
    po_data['coupon_entered_by_name'] = coupon_staff_name

    items_data = []
    total_dispatched = 0
    total_revenue = 0

    for item in items:
        d = item.to_dict()
        disp = dispatch_map.get(item.id, {'dispatched_qty': 0, 'revenue_collected': 0})
        d['dispatched_qty'] = disp['dispatched_qty']
        d['revenue_collected'] = disp['revenue_collected']
        d['balance_qty'] = item.ordered_qty - disp['dispatched_qty']
        d['balance_revenue'] = float(item.line_total) - disp['revenue_collected']
        spare = spare_map.get(item.sku)
        d['model_compat'] = spare.model_compat if spare else ''
        # Fallback enrichment: fill from live catalog if PO snapshot is empty (old POs)
        if not d.get('specifications') and spare:
            d['specifications'] = spare.specifications or ''
        if not d.get('speciality') and spare:
            d['speciality'] = spare.speciality or ''
        if not d.get('warranty_details') and spare:
            d['warranty_details'] = spare.warranty_details or ''
        # HSN code lookup via category config
        cat = spare.category_name if spare else item.category_name
        d['hsn_code'] = hsn_map.get(cat) if cat else None
        total_dispatched += disp['dispatched_qty']
        total_revenue += disp['revenue_collected']
        items_data.append(d)

    po_data['items'] = items_data
    po_data['summary'] = {
        'total_items': po.total_items,
        'total_ordered_qty': po.total_ordered_qty,
        'total_dispatched': total_dispatched,
        'total_revenue_collected': total_revenue,
        'balance_qty': po.total_ordered_qty - total_dispatched,
        'balance_revenue': float(po.total_value) - total_revenue,
        'total_value': float(po.total_value),
    }

    # Procurement records
    procs = db.query(MarketplaceProcurementRequest).filter_by(po_id=po_id).all()
    po_data['procurement_records'] = [p.to_dict() for p in procs]

    return po_data


# ── PUT /pos/{po_id}/dispatch — Staff dispatch update ─────────────────────────

@router.put('/pos/{po_id}/dispatch', tags=['marketplace-po'])
def update_dispatch(
    po_id: int,
    payload: DispatchRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    WVV: dispatched_qty per item cannot exceed ordered_qty.
    Each call appends a new dispatch record; totals are computed from all records.
    """
    db.execute(text("SET LOCAL statement_timeout = '60s'"))
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    staff_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    errors = []

    for upd in payload.items:
        item = db.query(MarketplacePOItem).filter_by(id=upd.po_item_id, po_id=po_id).first()
        if not item:
            errors.append(f'Item {upd.po_item_id} not found')
            continue

        # Validate: total dispatched must not exceed ordered
        existing_disp = db.execute(text(
            'SELECT COALESCE(SUM(dispatched_qty),0) FROM marketplace_po_dispatch WHERE po_item_id=:id'
        ), {'id': upd.po_item_id}).scalar() or 0

        if existing_disp + upd.dispatched_qty > item.ordered_qty:
            errors.append(
                f'Item {item.sku}: dispatched ({existing_disp + upd.dispatched_qty}) '
                f'would exceed ordered ({item.ordered_qty})'
            )
            continue

        disp = MarketplacePODispatch(
            po_id=po_id,
            po_item_id=upd.po_item_id,
            dispatched_qty=upd.dispatched_qty,
            revenue_collected=upd.revenue_collected,
            dispatch_notes=upd.dispatch_notes,
            dispatched_by=staff_id,
            courier_name=upd.courier_name,
            tracking_number=upd.tracking_number,
            vehicle_number=upd.vehicle_number,
            driver_name=upd.driver_name,
            company_id=company_id,
        )
        db.add(disp)

    if errors:
        db.rollback()
        raise HTTPException(status_code=400, detail={'errors': errors})

    # Update PO status
    all_items = db.query(MarketplacePOItem).filter_by(po_id=po_id).all()
    db.flush()
    all_fully_dispatched = True
    any_dispatched = False
    for item in all_items:
        total_d = db.execute(text(
            'SELECT COALESCE(SUM(dispatched_qty),0) FROM marketplace_po_dispatch WHERE po_item_id=:id'
        ), {'id': item.id}).scalar() or 0
        if total_d > 0:
            any_dispatched = True
        if total_d < item.ordered_qty:
            all_fully_dispatched = False

    if all_fully_dispatched:
        po.status = 'dispatched'
    elif any_dispatched:
        po.status = 'partial_dispatch'

    po.updated_at = datetime.utcnow()
    db.commit()

    summary = _get_dispatch_summary(db, po_id)
    return {
        'success': True,
        'po_id': po_id,
        'po_status': po.status,
        'total_dispatched': summary['total_dispatched'],
        'revenue_collected': summary['total_revenue'],
    }


# ── GET /procurement/ — List procurement requests (staff auth) ─────────────────

@router.get('/procurement/', tags=['marketplace-po'])
def list_procurement_requests(
    company_id: int = Query(1),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    po_id: Optional[int] = Query(None),
    source_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query('desc'),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    MPR = MarketplaceProcurementRequest
    q = db.query(MPR).filter_by(company_id=company_id)
    if status:
        q = q.filter(MPR.status == status)
    if source_type:
        q = q.filter(MPR.source_type == source_type)
    if po_id:
        q = q.filter(MPR.po_id == po_id)
    if search:
        s = f'%{search}%'
        matched_po_ids = db.query(MarketplacePurchaseOrder.id).filter(
            MarketplacePurchaseOrder.po_number.ilike(s),
            MarketplacePurchaseOrder.company_id == company_id,
        ).subquery()
        q = q.filter(
            MPR.procurement_number.ilike(s) |
            MPR.sku.ilike(s) |
            MPR.product_name.ilike(s) |
            MPR.po_id.in_(matched_po_ids)
        )
    _sort_map = {
        'proc_number': MPR.procurement_number,
        'po_id':       MPR.po_id,
        'sku':         MPR.sku,
        'product':     MPR.product_name,
        'ordered':     MPR.ordered_qty,
        'available':   MPR.available_qty,
        'shortfall':   MPR.shortfall_qty,
        'status':      MPR.status,
        'source':      MPR.source_type,
        'created':     MPR.created_at,
    }
    sort_col = _sort_map.get(sort_by, MPR.created_at)
    q = q.order_by(sort_col.asc() if sort_order == 'asc' else sort_col.desc())
    total = q.count()
    recs = q.offset((page - 1) * per_page).limit(per_page).all()
    po_ids = {r.po_id for r in recs if r.po_id}
    po_number_map = {}
    if po_ids:
        rows = db.query(MarketplacePurchaseOrder.id, MarketplacePurchaseOrder.po_number).filter(
            MarketplacePurchaseOrder.id.in_(po_ids)
        ).all()
        po_number_map = {r.id: r.po_number for r in rows}
    # Bulk-fetch spec/color/model from MarketspareItem by SKU
    rec_skus = list({r.sku for r in recs})
    spare_meta = db.query(
        MarketspareItem.sku,
        MarketspareItem.specifications,
        MarketspareItem.color,
        MarketspareItem.model_compat,
    ).filter(MarketspareItem.sku.in_(rec_skus), MarketspareItem.company_id == company_id).all()
    spare_meta_map = {r.sku: r for r in spare_meta}

    # Bulk-fetch store manager names for procurement
    proc_mgr_ids = {r.store_manager_id for r in recs if r.store_manager_id}
    proc_mgr_map = {}
    if proc_mgr_ids:
        proc_mgr_rows = db.query(StaffEmployee.id, StaffEmployee.full_name).filter(
            StaffEmployee.id.in_(proc_mgr_ids)
        ).all()
        proc_mgr_map = {r.id: r.full_name for r in proc_mgr_rows}

    records = []
    for r in recs:
        d = {**r.to_dict(), 'po_number': po_number_map.get(r.po_id)}
        meta = spare_meta_map.get(r.sku)
        d['specifications'] = (meta.specifications or '') if meta else ''
        d['color']          = (meta.color or '')          if meta else ''
        d['model_compat']   = (meta.model_compat or '')   if meta else ''
        d['store_manager_name'] = proc_mgr_map.get(r.store_manager_id) if r.store_manager_id else None
        records.append(d)

    return {
        'records': records,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


# ── PUT /procurement/{req_id} — Update procurement status (staff auth) ─────────
# Full lifecycle: pending → confirmed → payment_received → procurement → ordered → received → completed | cancelled

@router.put('/procurement/{req_id}', tags=['marketplace-po'])
def update_procurement(
    req_id: int,
    payload: ProcurementStatusUpdate = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    valid_statuses = {
        'pending', 'confirmed', 'payment_received', 'procurement',
        'ordered', 'received', 'completed', 'cancelled',
        # Extended lifecycle — March 2026
        'accepted', 'in_progress', 'under_procurement',
        'quality_check_pending', 'quality_confirmed', 'quality_failed',
        'added_to_stock', 'hold',
    }
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f'Invalid status. Must be one of: {sorted(valid_statuses)}')

    rec = db.query(MarketplaceProcurementRequest).filter_by(id=req_id, company_id=company_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail='Procurement record not found')

    actor_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    rec.status = payload.status
    if payload.procurement_notes:
        rec.procurement_notes = payload.procurement_notes
    rec.actioned_by = actor_id
    rec.actioned_at = datetime.utcnow()
    rec.updated_at = datetime.utcnow()

    if payload.received_qty is not None and payload.received_qty >= 0:
        rec.received_qty = payload.received_qty
    if payload.store_manager_id is not None:
        rec.store_manager_id = payload.store_manager_id

    # ── Store task hook: sync PR phase status ──────────────────────────────
    from app.services.store_task_service import sync_pr_phase_status as _sync_pr
    _sync_pr(db, rec.id, None, payload.status, company_id)
    # ───────────────────────────────────────────────────────────────────────

    db.commit()

    return {'success': True, 'id': req_id, 'status': rec.status, 'received_qty': int(rec.received_qty or 0)}


# ── PUT /pos/{po_id}/status — PO lifecycle actions (staff auth) ────────────────
# Statuses: confirmed → payment_received | procurement | dispatched | completed | cancelled

@router.put('/pos/{po_id}/status', tags=['marketplace-po'])
def update_po_status(
    po_id: int,
    payload: POStatusUpdate = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """WVV: Update PO lifecycle status. Records timestamp per stage."""
    valid_statuses = {
        'draft', 'procurement_pending',
        'confirmed', 'payment_received', 'procurement',
        'dispatched', 'partial_dispatch', 'completed', 'cancelled',
        # Extended lifecycle — March 2026
        'accepted', 'in_progress', 'under_procurement',
        'received', 'payment_pending', 'hold',
    }
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f'Invalid status. Must be one of: {sorted(valid_statuses)}')

    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    actor_id = current_user.id if hasattr(current_user, 'id') else None
    now = datetime.utcnow()

    po.status = payload.status
    if payload.notes:
        po.notes = (po.notes or '') + f'\n[{now.date()}] {payload.status}: {payload.notes}'

    if payload.status == 'confirmed' and not po.confirmed_at:
        po.confirmed_by_staff_id = actor_id
        po.confirmed_at = now
    elif payload.status == 'payment_received' and not po.payment_received_at:
        po.payment_received_at = now
    elif payload.status == 'completed' and not po.completed_at:
        po.completed_at = now

    if payload.store_manager_id is not None:
        po.store_manager_id = payload.store_manager_id
        po.store_manager_assigned_at = now

    po.updated_at = now

    # ── Store task hook: sync PO phase status ──────────────────────────────
    from app.services.store_task_service import sync_po_phase_status as _sync_po
    _sync_po(db, po_id, payload.status, company_id)
    # ───────────────────────────────────────────────────────────────────────

    db.commit()

    # ── WhatsApp auto-trigger on PO status change ─────────────────────────
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        _po_wa_map = {
            'confirmed': 'po_confirmed',
            'payment_received': 'po_payment_received',
            'dispatched': 'po_dispatched',
            'completed': 'po_completed',
        }
        _po_event = _po_wa_map.get(payload.status)
        _po_phone = getattr(po, 'bill_phone', None) or getattr(po, 'ship_phone', None)
        if _po_event and _po_phone:
            send_auto_whatsapp(
                db=db, event_key=_po_event, phone=_po_phone,
                context={
                    'name': getattr(po, 'bill_name', '') or '',
                    'po_number': po.po_number,
                    'status': payload.status,
                },
            )
    except Exception as _wa_ex:
        print(f"[WA-AUTO] PO hook error: {_wa_ex}")
    # ─────────────────────────────────────────────────────────────────────

    return {
        'success': True,
        'po_id': po_id,
        'po_number': po.po_number,
        'status': po.status,
        'store_manager_id': po.store_manager_id,
        'confirmed_at': po.confirmed_at.isoformat() if po.confirmed_at else None,
        'payment_received_at': po.payment_received_at.isoformat() if po.payment_received_at else None,
        'completed_at': po.completed_at.isoformat() if po.completed_at else None,
    }


# ── PATCH /pos/{po_id}/addresses — Staff update Bill To / Ship To ───────────────

@router.patch('/pos/{po_id}/addresses', tags=['marketplace-po'])
def update_po_addresses(
    po_id: int,
    payload: POAddressUpdate = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Staff can update Bill To / Ship To addresses on any PO."""
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    if payload.bill_name is not None:
        po.bill_name = payload.bill_name
    if payload.bill_phone is not None:
        po.bill_phone = payload.bill_phone
    if payload.bill_address is not None:
        po.bill_address = payload.bill_address
    if payload.ship_same_as_bill is not None:
        po.ship_same_as_bill = payload.ship_same_as_bill
    if payload.ship_same_as_bill:
        po.ship_name    = po.bill_name
        po.ship_phone   = po.bill_phone
        po.ship_address = po.bill_address
    else:
        if payload.ship_name is not None:
            po.ship_name = payload.ship_name
        if payload.ship_phone is not None:
            po.ship_phone = payload.ship_phone
        if payload.ship_address is not None:
            po.ship_address = payload.ship_address

    po.updated_at = datetime.utcnow()
    db.commit()
    return {'success': True, 'po_id': po_id, 'po_number': po.po_number}


# ── PATCH /pos/{po_id}/coupon — Staff apply/update discount coupon on PO ────────

_COUPON_MODE_PCT = {
    'mnr': 3.0,
    'vgk': 3.0,
    'student': 10.0,
    'partner': 12.0,
}
_COUPON_MODE_LABEL = {
    'mnr':     'MNR Member (3%)',
    'vgk':     'VGK Member (3%)',
    'student':  'ETC Student (10%)',
    'partner':  'Partner/Dealer (12%)',
    'promo':    'Promo Code',
}


def _recalc_po_items(db, po_id: int, discount_pct: float) -> float:
    """Recalculate all POItem prices for given discount % and return new total_value."""
    items = db.query(MarketplacePOItem).filter_by(po_id=po_id).all()
    total = 0.0
    for item in items:
        dealer = float(item.dealer_price or 0)
        disc   = round(dealer * discount_pct / 100, 2)
        net    = round(dealer - disc, 2)
        gst_p  = float(item.gst_percent or 18)
        gst_a  = round(net * gst_p / 100, 2)
        unit_f = round(net + gst_a, 2)
        qty    = int(item.ordered_qty or 1)
        line   = round(unit_f * qty, 2)
        item.discount_amount  = disc
        item.net_price        = net
        item.gst_amount       = gst_a
        item.unit_final_price = unit_f
        item.line_total       = line
        total += line
    return round(total, 2)


@router.patch('/pos/{po_id}/coupon', tags=['marketplace-po'])
def update_po_coupon(
    po_id: int,
    payload: POCouponUpdate = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Staff: apply or update a discount coupon/ID on an existing PO.
    Recalculates all line-item prices (discount_amount, net_price, GST, line_total)
    and updates PO total_value. Records who entered it and when.
    """
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    staff_id = getattr(current_user, 'id', None)
    removing = not payload.discount_coupon_id

    po.discount_coupon_id         = payload.discount_coupon_id
    po.coupon_entered_by_staff_id = staff_id if not removing else None
    po.coupon_entered_at          = datetime.utcnow() if not removing else None

    if removing:
        po.discount_mode = None
        po.discount_name = None
        discount_pct = 0.0
    else:
        mode = payload.discount_mode or ''
        po.discount_mode = mode or None

        # Auto-derive discount_name from mode if frontend didn't send one
        if payload.discount_name is not None:
            po.discount_name = payload.discount_name
        elif mode in _COUPON_MODE_LABEL:
            po.discount_name = _COUPON_MODE_LABEL[mode]

        # Resolve discount % — for 'promo' look up the actual code
        if mode == 'promo' and payload.discount_coupon_id:
            promo = db.query(MarketplacePromoCode).filter_by(
                code=payload.discount_coupon_id.strip().upper(),
                status='active'
            ).first()
            if not promo:
                promo = db.query(MarketplacePromoCode).filter(
                    MarketplacePromoCode.code.ilike(payload.discount_coupon_id.strip())
                ).first()
            discount_pct = float(promo.default_discount_pct or 0) if promo else 0.0
            if promo:
                po.discount_name = f"Promo: {promo.label or promo.code} ({discount_pct}%)"
        else:
            discount_pct = _COUPON_MODE_PCT.get(mode, 0.0)

    # Recalculate all item prices and get new PO total
    new_total = _recalc_po_items(db, po_id, discount_pct)
    po.total_value = new_total
    po.updated_at  = datetime.utcnow()
    db.commit()

    staff_name = None
    if staff_id:
        s = db.query(StaffEmployee.full_name).filter_by(id=staff_id).first()
        staff_name = s.full_name if s else None

    return {
        'success': True,
        'po_id': po_id,
        'discount_coupon_id': po.discount_coupon_id,
        'discount_mode': po.discount_mode,
        'discount_name': po.discount_name,
        'discount_pct': discount_pct,
        'new_total_value': new_total,
        'coupon_entered_by_name': staff_name,
        'coupon_entered_at': po.coupon_entered_at.isoformat() if po.coupon_entered_at else None,
    }


# ── POST /pos/{po_id}/generate-invoice — Issue Tax Invoice (PI number) ──────────

_INVOICE_TERMINAL = {'dispatched', 'partial_dispatch', 'completed'}
_INVOICE_LOCK_ID  = 20260318  # advisory lock for sequential PI number


@router.post('/pos/{po_id}/generate-invoice', tags=['marketplace-po'])
def generate_po_invoice(
    po_id: int,
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    WVV: Idempotent — if pi_number already set, return existing.
    Only allowed for terminal statuses (dispatched / partial_dispatch / completed).
    Advisory-lock protected: ZYPI-YYYYMM-NNNN — company-scoped sequential.
    """
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    if po.status not in _INVOICE_TERMINAL:
        raise HTTPException(
            status_code=400,
            detail=f'Invoice can only be generated for terminal POs (dispatched / partial_dispatch / completed). Current status: {po.status}',
        )

    # Idempotent — return existing PI number if already issued
    if po.pi_number:
        return {'success': True, 'po_id': po_id, 'po_number': po.po_number, 'pi_number': po.pi_number, 'already_existed': True}

    # Advisory lock: prevent race on sequential number generation
    lock_acquired = db.execute(text('SELECT pg_try_advisory_xact_lock(:id)'), {'id': _INVOICE_LOCK_ID}).scalar()
    if not lock_acquired:
        raise HTTPException(status_code=409, detail='Invoice generation in progress. Please retry in a moment.')

    # Generate next PI number: ZYPI-YYYYMM-NNNN (company-scoped)
    from app.models.base import get_indian_time
    now = get_indian_time()
    prefix = now.strftime('%Y%m')
    last = db.execute(text(
        "SELECT pi_number FROM marketplace_purchase_orders "
        "WHERE company_id = :cid AND pi_number LIKE :pat ORDER BY pi_number DESC LIMIT 1"
    ), {'cid': company_id, 'pat': f'ZYPI-{prefix}-%'}).scalar()
    if last:
        try:
            seq = int(last.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    pi_number = f'ZYPI-{prefix}-{seq:04d}'

    # WVV: Write
    po.pi_number  = pi_number
    po.updated_at = now
    # Verify
    db.flush()
    assert po.pi_number == pi_number, 'PI number write verification failed'
    db.commit()

    logger.info('[PI] Generated %s for PO %s (company=%s)', pi_number, po.po_number, company_id)
    return {'success': True, 'po_id': po_id, 'po_number': po.po_number, 'pi_number': pi_number, 'already_existed': False}


# ── Helpers: item-level price calculation and PO total refresh ──────────────────

def _calc_item_prices(dealer_price: float, ordered_qty: int, gst_percent: float):
    """Compute derived price fields from base inputs. No discount applied here."""
    net_price       = dealer_price
    gst_amount      = round(net_price * gst_percent / 100, 2)
    unit_final      = round(net_price + gst_amount, 2)
    line_total      = round(unit_final * ordered_qty, 2)
    return dict(
        net_price=net_price,
        gst_amount=gst_amount,
        unit_final_price=unit_final,
        line_total=line_total,
    )


def _refresh_po_totals(db: Session, po) -> None:
    """Recompute PO header totals from live item rows."""
    items = db.query(MarketplacePOItem).filter_by(po_id=po.id).all()
    po.total_items        = len(items)
    po.total_ordered_qty  = sum(i.ordered_qty for i in items)
    po.total_value        = sum(float(i.line_total or 0) for i in items)


# ── POST /pos/{po_id}/items — Add item to existing PO ──────────────────────────

@router.post('/pos/{po_id}/items', tags=['marketplace-po'])
def add_po_item(
    po_id: int,
    payload: POItemAddRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Staff: add a catalog product or custom item to an existing PO."""
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    prices = _calc_item_prices(payload.dealer_price, payload.ordered_qty, payload.gst_percent)

    # Stock check + catalog enrichment
    spare = db.query(MarketspareItem).filter_by(sku=payload.sku, company_id=company_id).first()
    stock_available      = int(spare.available_qty or 0) if spare else 0
    procurement_required = stock_available < payload.ordered_qty

    _spec      = payload.specifications or (spare.specifications if spare else None)
    _speciality= payload.speciality     or (spare.speciality     if spare else None)
    _warranty  = payload.warranty_details or (spare.warranty_details if spare else None)

    po_item = MarketplacePOItem(
        po_id=po_id,
        sku=payload.sku,
        product_name=payload.product_name,
        category_name=payload.category_name,
        brand=payload.brand,
        specifications=_spec,
        speciality=_speciality,
        color=payload.color,
        warranty_details=_warranty,
        ordered_qty=payload.ordered_qty,
        dealer_price=payload.dealer_price,
        discount_amount=0,
        gst_percent=payload.gst_percent,
        stock_available=stock_available,
        procurement_required=procurement_required,
        company_id=company_id,
        **prices,
    )
    db.add(po_item)
    db.flush()

    # Create procurement record if stock is insufficient
    if procurement_required:
        shortfall   = payload.ordered_qty - stock_available
        proc_number = _generate_proc_number(db, company_id)
        proc = MarketplaceProcurementRequest(
            procurement_number=proc_number,
            po_id=po_id,
            po_item_id=po_item.id,
            sku=payload.sku,
            product_name=payload.product_name,
            ordered_qty=payload.ordered_qty,
            available_qty=stock_available,
            shortfall_qty=shortfall,
            status='pending',
            company_id=company_id,
        )
        db.add(proc)
        db.flush()
        # ── Store task hook ──────────────────────────────────────────────
        from app.services.store_task_service import add_pr_phase as _add_pr_itm
        _add_pr_itm(db, proc, company_id)
        # ────────────────────────────────────────────────────────────────

    _refresh_po_totals(db, po)
    po.updated_at = datetime.utcnow()
    db.commit()

    return {'success': True, 'item': po_item.to_dict(), 'procurement_required': procurement_required}


# ── PATCH /pos/{po_id}/items/{item_id} — Update qty / price ────────────────────

@router.patch('/pos/{po_id}/items/{item_id}', tags=['marketplace-po'])
def update_po_item(
    po_id: int,
    item_id: int,
    payload: POItemUpdateRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Staff: update ordered_qty or dealer_price on an existing PO line item."""
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    item = db.query(MarketplacePOItem).filter_by(id=item_id, po_id=po_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')

    if payload.ordered_qty is not None:
        item.ordered_qty = payload.ordered_qty
    if payload.dealer_price is not None:
        item.dealer_price = payload.dealer_price
    if payload.gst_percent is not None:
        item.gst_percent = payload.gst_percent

    prices = _calc_item_prices(
        float(item.dealer_price),
        item.ordered_qty,
        float(item.gst_percent),
    )
    item.net_price        = prices['net_price']
    item.gst_amount       = prices['gst_amount']
    item.unit_final_price = prices['unit_final_price']
    item.line_total       = prices['line_total']

    # Refresh stock / procurement state
    spare = db.query(MarketspareItem).filter_by(sku=item.sku, company_id=company_id).first()
    stock_available           = int(spare.available_qty or 0) if spare else int(item.stock_available or 0)
    item.stock_available      = stock_available
    item.procurement_required = stock_available < item.ordered_qty

    _refresh_po_totals(db, po)
    po.updated_at = datetime.utcnow()
    db.commit()

    return {'success': True, 'item': item.to_dict()}


# ── DELETE /pos/{po_id}/items/{item_id} — Remove line item ─────────────────────

@router.delete('/pos/{po_id}/items/{item_id}', tags=['marketplace-po'])
def delete_po_item(
    po_id: int,
    item_id: int,
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Staff: remove a line item from a PO (also deletes its procurement records)."""
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    item = db.query(MarketplacePOItem).filter_by(id=item_id, po_id=po_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')

    # Cascaded DELETE on procurement records handled by FK cascade in DB.
    db.delete(item)
    db.flush()

    _refresh_po_totals(db, po)
    po.updated_at = datetime.utcnow()
    db.commit()

    return {'success': True, 'deleted_item_id': item_id}


# ── PUT /pos/{po_id}/assign-manager — Assign store manager to PO ───────────────

@router.put('/pos/{po_id}/assign-manager', tags=['marketplace-po'])
def assign_po_manager(
    po_id: int,
    payload: AssignManagerRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    po = db.query(MarketplacePurchaseOrder).filter_by(id=po_id, company_id=company_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    emp = db.query(StaffEmployee).filter_by(id=payload.store_manager_id, status='active').first()
    if not emp:
        raise HTTPException(status_code=404, detail='Staff member not found')
    po.store_manager_id = payload.store_manager_id
    po.store_manager_assigned_at = datetime.utcnow()
    po.updated_at = datetime.utcnow()
    db.commit()
    return {'success': True, 'po_id': po_id, 'store_manager_id': po.store_manager_id,
            'store_manager_name': emp.full_name}


# ── PUT /procurement/{req_id}/assign-manager — Assign store manager ────────────

@router.put('/procurement/{req_id}/assign-manager', tags=['marketplace-po'])
def assign_procurement_manager(
    req_id: int,
    payload: AssignManagerRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    rec = db.query(MarketplaceProcurementRequest).filter_by(id=req_id, company_id=company_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail='Procurement record not found')
    emp = db.query(StaffEmployee).filter_by(id=payload.store_manager_id, status='active').first()
    if not emp:
        raise HTTPException(status_code=404, detail='Staff member not found')
    rec.store_manager_id = payload.store_manager_id
    rec.updated_at = datetime.utcnow()
    db.commit()
    return {'success': True, 'id': req_id, 'store_manager_id': rec.store_manager_id,
            'store_manager_name': emp.full_name}


# ── GET /pos/{po_id}/transactions — Fetch all payment transactions for a PO ──

@router.get('/pos/{po_id}/transactions', tags=['marketplace-po'])
def get_po_transactions(
    po_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Return all payment transactions recorded against a PO, with income entry status."""
    po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')

    txns = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.po_id == po_id
    ).order_by(CRMLeadTransaction.transaction_date).all()

    total_paid = sum(t.amount for t in txns)

    # Fetch income entry statuses
    ie_ids = [t.income_entry_id for t in txns if t.income_entry_id]
    ie_map = {}
    if ie_ids:
        ies = db.query(IncomeEntry).filter(IncomeEntry.id.in_(ie_ids)).all()
        ie_map = {ie.id: {'number': ie.entry_number, 'status': ie.status} for ie in ies}

    return {
        'po_id': po_id,
        'po_number': po.po_number,
        'total_value': float(po.total_value or 0),
        'total_paid': round(total_paid, 2),
        'balance': round(float(po.total_value or 0) - total_paid, 2),
        'po_status': po.status,
        'transactions': [
            {
                'id': t.id,
                'amount': t.amount,
                'payment_mode': t.payment_mode,
                'transaction_date': t.transaction_date.isoformat() if t.transaction_date else None,
                'reference_number': t.reference_number,
                'notes': t.notes,
                'validation_status': t.validation_status,
                'income_entry_id': t.income_entry_id,
                'income_entry_number': ie_map.get(t.income_entry_id, {}).get('number'),
                'income_entry_status': ie_map.get(t.income_entry_id, {}).get('status'),
            }
            for t in txns
        ],
    }


# ── POST /pos/{po_id}/payment — Record payment against a PO ───────────────────

@router.post('/pos/{po_id}/payment', tags=['marketplace-po'])
def record_po_payment(
    po_id: int,
    payload: POPaymentRequest = Body(...),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Records a payment transaction against a PO using the existing CRM transaction table.
    lead_id is NULL; po_id links the transaction to the PO.
    WVV: validates PO exists; payment_mode must be a valid value.
    Allowed for all PO statuses except 'cancelled'.
    """
    po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail='PO not found')
    if po.status == 'cancelled':
        raise HTTPException(status_code=400, detail='Cannot record payment for a cancelled PO')
    company_id = po.company_id or company_id or 1

    valid_modes = {'cash', 'upi', 'neft', 'rtgs', 'cheque', 'card', 'dd', 'other'}
    mode = (payload.payment_mode or 'cash').lower()
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f'Invalid payment_mode. Must be one of: {sorted(valid_modes)}')

    now = datetime.utcnow()
    try:
        txn_date = datetime.fromisoformat(payload.transaction_date) if payload.transaction_date else now
    except ValueError:
        txn_date = now

    staff_id = current_user.id if hasattr(current_user, 'id') else None

    from sqlalchemy import text as _text
    import decimal

    # ── Create IncomeEntry (PENDING — Accounts must confirm) ────────────────
    # Map PO payment modes to IncomeEntry allowed values
    IE_MODE_MAP = {
        'cash': 'CASH', 'upi': 'UPI', 'neft': 'NEFT', 'rtgs': 'RTGS',
        'cheque': 'CHEQUE', 'card': 'CARD', 'dd': 'DD',
        'bank': 'BANK', 'other': 'BANK',  # OTHER → BANK (bank transfer fallback)
    }
    ie_payment_mode = IE_MODE_MAP.get(mode, 'BANK')

    income_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == 'SALES', IncomeSourceType.is_active == True
    ).first()
    income_entry_id = None
    ie_number = None
    if income_source:
        year_prefix = f"IE-{datetime.utcnow().year}-"
        row = db.execute(_text("SELECT COUNT(*) FROM income_entries WHERE entry_number LIKE :pfx"),
                         {'pfx': year_prefix + '%'}).fetchone()
        ie_number = f"{year_prefix}{(int(row[0]) if row else 0) + 1:05d}"
        income_entry = IncomeEntry(
            entry_number=ie_number,
            company_id=company_id,
            income_source_id=income_source.id,
            income_date=txn_date.date(),
            amount=decimal.Decimal(str(round(payload.amount, 2))),
            reference_type='PO',
            reference_id=po.po_number,
            payment_mode=ie_payment_mode,
            payment_reference=payload.reference_number,
            payment_date=txn_date.date(),
            payer_name=po.customer_name or po.bill_name,
            payer_contact=po.customer_phone or po.bill_phone,
            narration=f'PO payment: {po.po_number}'
                      + (f' | {po.customer_name}' if po.customer_name else '')
                      + (f' | Ref: {payload.reference_number}' if payload.reference_number else ''),
            created_by_id=staff_id,
            status='PENDING',
        )
        db.add(income_entry)
        db.flush()
        income_entry_id = income_entry.id

    txn = CRMLeadTransaction(
        company_id=company_id,
        lead_id=None,
        po_id=po_id,
        transaction_date=txn_date,
        amount=payload.amount,
        transaction_type='partial',
        payment_mode=mode,
        collected_by_id=staff_id,
        reference_number=payload.reference_number,
        notes=payload.notes or f'PO payment: {po.po_number}',
        validation_status='pending',
        income_entry_id=income_entry_id,
        created_by_id=staff_id,
        created_at=now,
        updated_at=now,
    )
    db.add(txn)

    # Auto-advance PO status to payment_received if currently at payment_pending
    if po.status == 'payment_pending':
        po.status = 'payment_received'
        po.payment_received_at = po.payment_received_at or now
        po.updated_at = now

    db.commit()
    db.refresh(txn)

    # Return all transactions for this PO
    all_txns = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.po_id == po_id
    ).order_by(CRMLeadTransaction.transaction_date).all()

    return {
        'success': True,
        'transaction_id': txn.id,
        'po_id': po_id,
        'po_number': po.po_number,
        'amount': txn.amount,
        'payment_mode': txn.payment_mode,
        'po_status': po.status,
        'income_entry_number': ie_number,
        'message': f'Payment of ₹{txn.amount:,.2f} recorded for {po.po_number}' + (f' | IE: {ie_number} (awaiting Accounts)' if ie_number else ''),
        'transactions': [
            {
                'id': t.id,
                'amount': t.amount,
                'payment_mode': t.payment_mode,
                'transaction_date': t.transaction_date.isoformat() if t.transaction_date else None,
                'reference_number': t.reference_number,
                'notes': t.notes,
                'validation_status': t.validation_status,
                'income_entry_id': t.income_entry_id,
            }
            for t in all_txns
        ],
    }


# ── POST /pos/sync-sheet — Re-run catalog sync (staff auth) ───────────────────

@router.post('/pos/sync-sheet', tags=['marketplace-po'])
def sync_catalog_sheet(
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """Re-runs the Google Sheet catalog sync — always updates prices, GST, available_qty (stock counts)."""
    try:
        result = run_sync(db, company_id=company_id, triggered_by='po-page-manual')
        return {'success': True, **result}
    except Exception as e:
        logger.error(f'[PO-SYNC] Sheet sync failed: {e}')
        raise HTTPException(status_code=500, detail=f'Sync failed: {str(e)}')


# ── GET /stock-analysis — Stock overview per product (staff auth) ──────────────

@router.get('/stock-analysis', tags=['marketplace-po'])
def get_stock_analysis(
    company_id: int = Query(1),
    filter_category: Optional[str] = Query(None),
    filter_company: Optional[str] = Query(None),
    filter_status: Optional[str] = Query(None),   # all | ok | low | out
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Returns stock summary cards + full items list for Stock Analysis tab.
    Status: out=available_qty==0, low=1-5, ok=>5
    DC Protocol: scoped to company_id.
    """
    q = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    )
    if filter_category:
        q = q.filter(MarketspareItem.category_name.ilike(f'%{filter_category}%'))
    if filter_company:
        q = q.filter(MarketspareItem.company_name.ilike(f'%{filter_company}%'))

    items = q.order_by(MarketspareItem.available_qty.asc(), MarketspareItem.category_name).all()

    def _status(aq: int) -> str:
        if aq == 0:   return 'out'
        if aq <= 5:   return 'low'
        return 'ok'

    rows = []
    for item in items:
        aq = int(item.available_qty or 0)
        st = _status(aq)
        if filter_status and filter_status != 'all' and st != filter_status:
            continue
        has_image = bool(item.image_url or (item.image_data and len(item.image_data) > 0))
        rows.append({
            'id':            item.id,
            'sku':           item.sku,
            'name':          item.name,
            'category_name': item.category_name,
            'company_name':  item.company_name or '',
            'available_qty': aq,
            'stock_qty':     int(item.stock_qty or 0),
            'status':        st,
            'image_url':     item.image_url or '',
            'has_image':     has_image,
            'speciality':    item.speciality or '',
            'dealer_price':  float(item.dealer_price or 0),
            'specifications': item.specifications or '',
            'color':         item.color or '',
            'model_compat':  item.model_compat or '',
        })

    total    = len(rows)
    out_qty  = sum(1 for r in rows if r['status'] == 'out')
    low_qty  = sum(1 for r in rows if r['status'] == 'low')
    ok_qty   = sum(1 for r in rows if r['status'] == 'ok')
    companies = sorted(set(r['company_name'] for r in rows if r['company_name']))
    categories = sorted(set(r['category_name'] for r in rows))

    return {
        'summary': {
            'total_skus':    total,
            'in_stock':      ok_qty,
            'low_stock':     low_qty,
            'out_of_stock':  out_qty,
            'companies':     companies,
            'categories':    categories,
        },
        'items': rows,
    }


# ── PUT /products/{id}/stock — Inline qty update WVV (staff auth) ──────────────

@router.put('/products/{product_id}/stock', tags=['marketplace-po'])
def update_product_stock(
    product_id: int,
    payload: StockUpdateRequest = Body(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    WVV inline stock update: Read → Verify → Write.
    Updates available_qty for a single product.
    """
    # READ
    item = db.query(MarketspareItem).filter_by(id=product_id, company_id=company_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    # VERIFY
    if payload.available_qty < 0:
        raise HTTPException(status_code=422, detail='available_qty must be >= 0')

    old_qty = int(item.available_qty or 0)

    # WRITE
    item.available_qty = payload.available_qty
    item.updated_at    = datetime.utcnow()
    db.commit()

    staff_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    logger.info(f'[STOCK-UPDATE] product_id={product_id} sku={item.sku} '
                f'{old_qty}→{payload.available_qty} by={staff_id} notes={payload.notes}')

    return {
        'success':       True,
        'id':            item.id,
        'sku':           item.sku,
        'name':          item.name,
        'available_qty': int(item.available_qty),
        'old_qty':       old_qty,
    }


# ── POST /procurement/raise-for-sku — Manual raise procurement for one SKU ────

@router.post('/procurement/raise-for-sku', tags=['marketplace-po'])
def raise_procurement_for_sku(
    product_id: int = Query(...),
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Raise a procurement request for a specific product (from Stock Analysis tab).
    Creates a pending record with triggered_by='manual'.
    DC Protocol: company_id enforced.
    """
    item = db.query(MarketspareItem).filter_by(id=product_id, company_id=company_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    # Check for existing open procurement
    existing = db.query(MarketplaceProcurementRequest).filter(
        MarketplaceProcurementRequest.sku == item.sku,
        MarketplaceProcurementRequest.company_id == company_id,
        MarketplaceProcurementRequest.status.in_(['pending', 'ordered']),
    ).first()
    if existing:
        return {
            'success': False,
            'message': f'Open procurement already exists: {existing.procurement_number}',
            'procurement_number': existing.procurement_number,
        }

    proc_number = _generate_proc_number(db, company_id)
    staff_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    proc = MarketplaceProcurementRequest(
        procurement_number=proc_number,
        po_id=None,
        po_item_id=None,
        sku=item.sku,
        product_name=item.name,
        ordered_qty=0,
        available_qty=int(item.available_qty or 0),
        shortfall_qty=0,
        status='pending',
        triggered_by='manual',
        procurement_notes=f'Manually raised from Stock Analysis by {staff_id}',
        company_id=company_id,
    )
    db.add(proc)
    db.flush()
    # ── Store task hook: manual procurement raise ────────────────────────────
    from app.services.store_task_service import add_pr_phase as _add_pr_manual
    _add_pr_manual(db, proc, company_id)
    # ─────────────────────────────────────────────────────────────────────────
    db.commit()

    return {
        'success': True,
        'procurement_number': proc_number,
        'sku': item.sku,
        'product_name': item.name,
        'message': f'Procurement {proc_number} raised.',
    }


# ── POST /procurement/raise-all-out — Bulk raise for all zero-qty items ─────

@router.post('/procurement/raise-all-out', tags=['marketplace-po'])
def raise_all_out_of_stock(
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Bulk-raise procurement requests for all products with available_qty == 0
    that have no existing open procurement.
    DC Protocol: company_id enforced.
    """
    from app.services.marketplace_sync import _auto_raise_procurement
    staff_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user)
    try:
        raised = _auto_raise_procurement(db, company_id)
        logger.info(f'[PROC-BULK] {raised} procurement(s) raised by {staff_id}')
        return {
            'success': True,
            'raised': raised,
            'message': f'{raised} procurement request(s) raised for out-of-stock items.',
        }
    except Exception as e:
        db.rollback()
        logger.error(f'[PROC-BULK] Failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /products/{id}/generate-image — AI image generation (staff auth) ─────

@router.post('/products/{product_id}/generate-image', tags=['marketplace-po'])
def generate_product_image(
    product_id: int,
    company_id: int = Query(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    On-demand AI image generation for a single product using Gemini.
    Stores result in image_data JSONB.
    """
    import os, json, urllib.request, urllib.error

    item = db.query(MarketspareItem).filter_by(id=product_id, company_id=company_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    api_key = os.getenv('GOOGLE_API_KEY', '')
    if not api_key:
        raise HTTPException(status_code=503, detail='GOOGLE_API_KEY not configured')

    prompt = (
        f'High quality product photograph of an EV electric vehicle spare part: '
        f'{item.name}, category: {item.category_name}. '
        f'Clean white background, studio lighting, professional product shot.'
    )
    if item.specifications:
        prompt += f' Specifications: {item.specifications}.'
    if item.color:
        prompt += f' Color: {item.color}.'

    try:
        api_url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'gemini-2.0-flash-exp:generateContent?key={api_key}'
        )
        body = json.dumps({
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']},
        }).encode('utf-8')
        req = urllib.request.Request(
            api_url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp_data = json.loads(r.read().decode())

        # Extract inline image data from response
        image_b64 = None
        for part in resp_data.get('candidates', [{}])[0].get('content', {}).get('parts', []):
            if 'inlineData' in part:
                image_b64 = part['inlineData'].get('data')
                break

        if not image_b64:
            raise HTTPException(status_code=502, detail='No image returned by AI')

        # Store as data URL in image_data
        data_url = f'data:image/png;base64,{image_b64}'
        item.image_data = [{'url': data_url, 'thumb': data_url, 'source': 'gemini_ai'}]
        item.updated_at = datetime.utcnow()
        db.commit()

        return {
            'success': True,
            'id': item.id,
            'sku': item.sku,
            'message': 'AI image generated and saved.',
            'has_image': True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'[AI-IMG] generate failed for product_id={product_id}: {e}')
        raise HTTPException(status_code=500, detail=f'Image generation failed: {str(e)}')
