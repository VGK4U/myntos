"""
MNR E-Com Lite — Phase 1 API Endpoints
DC Protocol: company_id enforced on all queries.
Strictly non-transactional — Price Intelligence Layer only.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException, Body, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.marketplace import (
    MarketspareItem, MarketplaceSyncLog, MarketplaceCategoryConfig,
    MarketplaceProcurementRequest, MarketplacePurchaseOrder, MarketplaceSegment,
    MarketplacePromoCode, MarketplaceCodeLookup,
)
from app.services.marketplace_sync import run_sync, run_stock_sync, _import_sheet_products_to_stock
from app.services.marketplace_pricing import enrich_product_with_pricing

logger = logging.getLogger(__name__)
router = APIRouter()

PAGE_SIZE = 24

# ── Sync concurrency guard ────────────────────────────────────────────────────
# Set of company_ids currently running a background sync.
_SYNC_RUNNING: set = set()


def _do_sync_background(company_id: int, segment_id, staff_name: str) -> None:
    """Background sync task — creates its own DB session (request session is closed)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        result = run_sync(db, company_id, triggered_by=staff_name, segment_id=segment_id)

        logger.info(f'[MARKETPLACE-SYNC] Background sync finished: company_id={company_id} result={result}')

        # Auto-seed category configs (non-fatal — missing columns in older DBs should not block stock push)
        try:
            seg_filter = [MarketspareItem.company_id == company_id]
            if segment_id:
                seg_filter.append(MarketspareItem.segment_id == segment_id)

            existing_cats = {
                c.category_name for c in db.query(MarketplaceCategoryConfig.category_name)
                .filter(MarketplaceCategoryConfig.company_id == company_id).all()
            }
            all_cats = {
                row.category_name for row in
                db.query(MarketspareItem.category_name)
                .filter(*seg_filter).distinct().all()
            }
            new_cats = all_cats - existing_cats
            for cat in new_cats:
                db.add(MarketplaceCategoryConfig(
                    category_name=cat,
                    markup_percent=15.0,
                    gst_percent=18.0,
                    margin_floor_percent=20.0,
                    updated_by='auto-seeded',
                    segment_id=segment_id or 1,
                    company_id=company_id,
                ))
            if new_cats:
                db.commit()
        except Exception as _cat_e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(f'[MARKETPLACE-SYNC] Category seed step failed (non-fatal): {_cat_e}')

        # DC-STOCK-MKT-002: Push new marketplace items → stock_item_master
        # Makes freshly synced products visible on the Stock Items page. Idempotent.
        try:
            from app.services.marketplace_sync import _import_sheet_products_to_stock
            _import_sheet_products_to_stock(db)
            logger.info(f'[MARKETPLACE-SYNC] DC-STOCK-MKT-002 complete: marketplace → stock_item_master push done')
        except Exception as _mkt2e:
            logger.warning(f'[MARKETPLACE-SYNC] DC-STOCK-MKT-002 step failed (non-fatal): {_mkt2e}')

        # DC-STOCK-MKT-003: stock_ledger → marketplace_spares.available_qty
        # Runs automatically after purchases/sales via _bg_refresh_mkt_qty().
        # Intentionally NOT called here: available_qty already comes from the sheet (correct),
        # and run_stock_sync is O(N) per item which would double the sync time for 298+ rows.

    except Exception as e:
        logger.error(f'[MARKETPLACE-SYNC] Background sync failed: company_id={company_id} error={e}')
    finally:
        db.close()
        _SYNC_RUNNING.discard(company_id)

# DC Protocol Mar 2026: Object Storage image serving
# Images stored in Replit Object Storage persist across deployments.
# URL pattern: /api/v1/marketplace/images/{filename}

_OBJ_STORE_KEY_PREFIX = 'marketplace/product-images'

def _get_obj_client():
    from app.services.object_storage import Client
    return Client()

@router.get('/images/{filename}')
async def serve_product_image(filename: str):
    """
    DC Protocol Mar 2026: Serve marketplace product image from Replit Object Storage.
    This endpoint is deployment-safe — images persist in Object Storage regardless of git state.
    """
    import re
    if not filename or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise HTTPException(status_code=400, detail='Invalid filename')

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
    mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'webp': 'image/webp', 'gif': 'image/gif'}
    content_type = mime_map.get(ext, 'image/png')

    # Try Object Storage first (authoritative in production)
    try:
        client = _get_obj_client()
        data = client.download_as_bytes(f'{_OBJ_STORE_KEY_PREFIX}/{filename}')
        return Response(content=data, media_type=content_type,
                        headers={'Cache-Control': 'public, max-age=31536000, immutable'})
    except Exception:
        pass

    # Fallback: local filesystem (dev convenience)
    local_path = Path('/home/runner/workspace/frontend/public/marketplace/product-images') / filename
    if local_path.exists():
        return Response(content=local_path.read_bytes(), media_type=content_type,
                        headers={'Cache-Control': 'public, max-age=3600'})

    raise HTTPException(status_code=404, detail='Image not found')


def _get_category_config_map(db: Session, company_id: int) -> dict:
    """Build category_name → config dict for fast lookup."""
    configs = db.query(MarketplaceCategoryConfig).filter(
        MarketplaceCategoryConfig.company_id == company_id
    ).all()
    return {c.category_name: c.to_dict() for c in configs}


def _get_segment(db: Session, company_id: int, segment_id: int = None, slug: str = None) -> MarketplaceSegment:
    """Resolve a segment by id or slug. Returns None if not found."""
    q = db.query(MarketplaceSegment).filter(MarketplaceSegment.company_id == company_id)
    if segment_id:
        return q.filter(MarketplaceSegment.id == segment_id).first()
    if slug:
        return q.filter(MarketplaceSegment.slug == slug).first()
    return None


def _get_segment_discount_rates(db: Session, company_id: int, segment_id: int = None, slug: str = None) -> dict:
    """Resolve segment and return its discount rate dict for the pricing engine.
    Returns None if no segment is found (pricing engine will use hardcoded defaults)."""
    seg = None
    if segment_id or slug:
        seg = _get_segment(db, company_id, segment_id=segment_id, slug=slug)
    if not seg:
        seg = db.query(MarketplaceSegment).filter(
            MarketplaceSegment.company_id == company_id
        ).first()
    if seg:
        return {
            'mnr_pct': float(seg.mnr_pct) if seg.mnr_pct is not None else 3.0,
            'partner_pct': float(seg.partner_pct) if seg.partner_pct is not None else 12.0,
            'student_pct': float(seg.student_pct) if seg.student_pct is not None else 10.0,
            'vgk_pct': float(seg.vgk_pct) if seg.vgk_pct is not None else 3.0,
            'allow_vgk': bool(seg.allow_vgk) if seg.allow_vgk is not None else True,
        }
    return None


def _build_segment_rates_cache(db: Session, company_id: int) -> dict:
    """Build a segment_id -> discount rates dict for batch product enrichment."""
    segments = db.query(MarketplaceSegment).filter(
        MarketplaceSegment.company_id == company_id
    ).all()
    cache = {}
    for seg in segments:
        cache[seg.id] = {
            'mnr_pct': float(seg.mnr_pct) if seg.mnr_pct is not None else 3.0,
            'partner_pct': float(seg.partner_pct) if seg.partner_pct is not None else 12.0,
            'student_pct': float(seg.student_pct) if seg.student_pct is not None else 10.0,
            'vgk_pct': float(seg.vgk_pct) if seg.vgk_pct is not None else 3.0,
            'allow_vgk': bool(seg.allow_vgk) if seg.allow_vgk is not None else True,
        }
    return cache


def _log_lookup(db: Session, code_type: str, code_value: str, was_valid: bool, segment_id, company_id: int):
    """Log a discount ID / promo code lookup for analytics. Silent — never raises."""
    try:
        lookup = MarketplaceCodeLookup(
            code_type=code_type,
            code_value=code_value,
            was_valid=was_valid,
            segment_id=segment_id,
            company_id=company_id,
        )
        db.add(lookup)
        db.commit()
    except Exception:
        pass


# ─────────────────────────────────────────────
# PUBLIC: Product listing + price engine
# ─────────────────────────────────────────────

@router.get('/filters')
def get_filter_options(
    company_id: int = Query(...),
    category: Optional[str] = Query(None),
    categories: Optional[str] = Query(None, description='Comma-separated category names'),
    segment_id: Optional[int] = Query(None, description='Phase 3: filter by segment'),
    segment_slug: Optional[str] = Query(None, description='Phase 3: filter by segment slug'),
    db: Session = Depends(get_db),
):
    """Distinct filter values for model, spec. Scoped to category/categories if provided."""
    q = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    )
    # Phase 3: segment filter
    resolved_seg_id = segment_id
    if not resolved_seg_id and segment_slug:
        seg = _get_segment(db, company_id, slug=segment_slug)
        if seg:
            resolved_seg_id = seg.id
    if resolved_seg_id:
        q = q.filter(MarketspareItem.segment_id == resolved_seg_id)

    if categories:
        cat_list = [c.strip().upper() for c in categories.split(',') if c.strip()]
        if cat_list:
            q = q.filter(MarketspareItem.category_name.in_(cat_list))
    elif category:
        q = q.filter(MarketspareItem.category_name == category.upper())

    items = q.all()
    models = sorted({i.model_compat for i in items if i.model_compat})
    specs = sorted({i.specifications for i in items if i.specifications})
    colors = sorted({i.color for i in items if i.color})
    return {'models': models, 'specs': specs, 'colors': colors}


@router.get('/products')
def list_products(
    company_id: int = Query(..., description='DC Protocol: company_id required'),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    categories: Optional[str] = Query(None, description='Comma-separated category names for multi-select'),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    discount_mode: Optional[str] = Query(None, regex='^(mnr|mnr_points|partner|student|vgk)$'),
    model: Optional[str] = Query(None),
    spec: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    segment_id: Optional[int] = Query(None, description='Phase 3: filter by segment id'),
    segment_slug: Optional[str] = Query(None, description='Phase 3: filter by segment slug'),
    db: Session = Depends(get_db),
):
    """
    Public product listing with price engine applied.
    Supports full-text search, category (single), categories (multi, comma-sep),
    model, spec, color filters, price range, pagination.
    discount_mode: 'mnr' (3% off) | 'partner' (12% off) | 'student' (10% off) | None
    """
    q = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    )

    # Phase 3: segment filter — resolve slug → id if needed
    resolved_seg_id = segment_id
    if not resolved_seg_id and segment_slug:
        seg = _get_segment(db, company_id, slug=segment_slug)
        if seg:
            resolved_seg_id = seg.id
    if resolved_seg_id:
        q = q.filter(MarketspareItem.segment_id == resolved_seg_id)

    if search:
        search_clean = search.strip()
        q = q.filter(
            or_(
                MarketspareItem.search_vector.op('@@')(
                    func.plainto_tsquery('english', search_clean)
                ),
                MarketspareItem.name.ilike(f'%{search_clean}%'),
                MarketspareItem.sku.ilike(f'%{search_clean}%'),
                MarketspareItem.model_compat.ilike(f'%{search_clean}%'),
            )
        )

    # Multi-category filter (takes priority over single category)
    if categories:
        cats = [c.strip().upper() for c in categories.split(',') if c.strip()]
        if cats:
            q = q.filter(MarketspareItem.category_name.in_(cats))
    elif category:
        q = q.filter(MarketspareItem.category_name == category.upper())

    if model:
        q = q.filter(MarketspareItem.model_compat == model)

    if spec:
        q = q.filter(MarketspareItem.specifications == spec)

    if color:
        q = q.filter(MarketspareItem.color == color)

    if min_price is not None:
        q = q.filter(MarketspareItem.dealer_price >= min_price)
    if max_price is not None:
        q = q.filter(MarketspareItem.dealer_price <= max_price)

    total = q.count()
    if sort == "price_asc":
        order_col = MarketspareItem.dealer_price.asc()
    elif sort == "price_desc":
        order_col = MarketspareItem.dealer_price.desc()
    else:
        order_col = None
    if order_col is not None:
        items = q.order_by(order_col).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    else:
        items = q.order_by(MarketspareItem.category_name, MarketspareItem.name) \
                 .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

    config_map = _get_category_config_map(db, company_id)
    seg_cache = _build_segment_rates_cache(db, company_id)

    products = [
        enrich_product_with_pricing(
            item.to_dict(),
            config_map.get(item.category_name),
            discount_mode,
            segment_discount_rates=seg_cache.get(item.segment_id),
        )
        for item in items
    ]

    return {
        'products': products,
        'total': total,
        'page': page,
        'per_page': PAGE_SIZE,
        'pages': (total + PAGE_SIZE - 1) // PAGE_SIZE,
        'discount_mode': discount_mode,
    }


@router.get('/products/{product_id}')
def get_product(
    product_id: int,
    company_id: int = Query(...),
    discount_mode: Optional[str] = Query(None, regex='^(mnr|mnr_points|partner|student|vgk)$'),
    db: Session = Depends(get_db),
):
    """Single product with full price breakdown."""
    item = db.query(MarketspareItem).filter(
        MarketspareItem.id == product_id,
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    config_map = _get_category_config_map(db, company_id)
    seg_rates = _get_segment_discount_rates(db, company_id, segment_id=item.segment_id)
    return enrich_product_with_pricing(
        item.to_dict(),
        config_map.get(item.category_name),
        discount_mode,
        segment_discount_rates=seg_rates,
    )


@router.get('/categories')
def list_categories(
    company_id: int = Query(...),
    segment_id: Optional[int] = Query(None, description='Phase 3: filter by segment id'),
    segment_slug: Optional[str] = Query(None, description='Phase 3: filter by segment slug'),
    db: Session = Depends(get_db),
):
    """Distinct active categories with item count. Optionally scoped to segment."""
    q = db.query(
        MarketspareItem.category_name,
        func.count(MarketspareItem.id).label('count'),
    ).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    )
    # Phase 3: segment filter
    resolved_seg_id = segment_id
    if not resolved_seg_id and segment_slug:
        seg = _get_segment(db, company_id, slug=segment_slug)
        if seg:
            resolved_seg_id = seg.id
    if resolved_seg_id:
        q = q.filter(MarketspareItem.segment_id == resolved_seg_id)

    rows = q.group_by(MarketspareItem.category_name).order_by(MarketspareItem.category_name).all()
    return [{'category_name': r.category_name, 'count': r.count} for r in rows]


# ─────────────────────────────────────────────
# PUBLIC: MNR ID validation (for discount)
# ─────────────────────────────────────────────

@router.get('/validate-mnr')
def validate_mnr_id(
    mnr_id: str = Query(...),
    company_id: int = Query(1, description='DC Protocol'),
    segment_id: Optional[int] = Query(None, description='Phase 3: segment for discount rate lookup'),
    db: Session = Depends(get_db),
):
    """
    MNR Discount validation.
    - Active + activated members: MNR Member discount (segment mnr_pct, default 3%).
    - Active + non-activated members: MNR Points discount (fixed 1.5%).
    """
    mnr_member_pct = 3.0
    if segment_id:
        seg = _get_segment(db, company_id, segment_id=segment_id)
        if seg and seg.mnr_pct is not None:
            mnr_member_pct = float(seg.mnr_pct)
    try:
        result = db.execute(text("""
            SELECT u.name, u.id,
                   u.activation_date,
                   COALESCE(pb.current_balance, 0) AS actual_points
            FROM "user" u
            LEFT JOIN mnr_points_balance pb ON pb.user_id = u.id
            WHERE u.id = :mnr_id
              AND u.account_status = 'Active'
            LIMIT 1
        """), {'mnr_id': mnr_id.strip().upper()}).fetchone()

        if not result:
            _log_lookup(db, 'mnr', mnr_id.strip().upper(), False, segment_id, company_id)
            return {'valid': False, 'message': 'MNR ID not found or account not active'}

        is_activated = result.activation_date is not None
        points_balance = float(result.actual_points) if is_activated else 500.0

        _log_lookup(db, 'mnr', mnr_id.strip().upper(), True, segment_id, company_id)
        return {
            'valid': True,
            'name': result.name,
            'mnr_id': result.id,
            'is_activated': is_activated,
            'points_balance': points_balance,
            'mnr_points': points_balance,
            'discount_mode': 'mnr' if is_activated else 'mnr_points',
            'discount_pct': float(mnr_member_pct) if is_activated else 1.5,
        }
    except Exception as e:
        logger.error(f'[MARKETPLACE] MNR validate error: {e}')
        return {'valid': False, 'message': 'Validation error'}


@router.get('/validate-dealer')
def validate_dealer_code(
    dealer_code: str = Query(...),
    company_id: int = Query(1, description='DC Protocol'),
    segment_id: Optional[int] = Query(None, description='Phase 3: segment for discount rate lookup'),
    db: Session = Depends(get_db),
):
    """
    Validate an Official Partner code.
    Discount rate read from segment config (default 12%).
    URL kept as /validate-dealer for backward compatibility.
    """
    partner_pct = 12.0
    if segment_id:
        seg = _get_segment(db, company_id, segment_id=segment_id)
        if seg:
            partner_pct = float(seg.partner_pct or 12.0)
    try:
        result = db.execute(text("""
            SELECT p.partner_name, p.partner_code, p.partner_type
            FROM official_partners p
            WHERE UPPER(p.partner_code) = :code AND p.is_active = true
            LIMIT 1
        """), {'code': dealer_code.strip().upper()}).fetchone()

        if not result:
            _log_lookup(db, 'partner', dealer_code.strip().upper(), False, segment_id, company_id)
            return {'valid': False, 'message': 'Partner code not found or inactive'}

        _log_lookup(db, 'partner', dealer_code.strip().upper(), True, segment_id, company_id)
        return {
            'valid': True,
            'name': result.partner_name,
            'dealer_code': result.partner_code,
            'partner_type': result.partner_type,
            'discount_mode': 'partner',
            'discount_pct': partner_pct,
        }
    except Exception as e:
        logger.error(f'[MARKETPLACE] Partner validate error: {e}')
        return {'valid': False, 'message': 'Validation error'}


# ─────────────────────────────────────────────
# PUBLIC: ETC Student ID validation (10% discount)
# ─────────────────────────────────────────────

@router.get('/validate-student')
def validate_student_discount(
    student_id: str = Query(...),
    company_id: int = Query(1, description='DC Protocol'),
    segment_id: Optional[int] = Query(None, description='Phase 3: segment for discount rate lookup'),
    db: Session = Depends(get_db),
):
    """
    Check if an ETC student ID is active. Returns name if valid.
    Discount rate read from segment config (default 10%).
    """
    student_pct = 10.0
    if segment_id:
        seg = _get_segment(db, company_id, segment_id=segment_id)
        if seg:
            student_pct = float(seg.student_pct or 10.0)
    try:
        result = db.execute(text("""
            SELECT name, student_id, registration_id, batch_no
            FROM etc_students
            WHERE UPPER(student_id) = :sid AND is_active = TRUE
            LIMIT 1
        """), {'sid': student_id.strip().upper()}).fetchone()

        if not result:
            _log_lookup(db, 'student', student_id.strip().upper(), False, segment_id, company_id)
            return {'valid': False, 'message': 'Student ID not found or inactive'}

        _log_lookup(db, 'student', student_id.strip().upper(), True, segment_id, company_id)
        return {
            'valid': True,
            'name': result.name,
            'student_id': result.student_id,
            'batch_no': result.batch_no,
            'discount_mode': 'student',
            'discount_pct': student_pct,
        }
    except Exception as e:
        logger.error(f'[MARKETPLACE] Student validate error: {e}')
        return {'valid': False, 'message': 'Validation error'}


# ─────────────────────────────────────────────
# PUBLIC: VGK Member validation (3% discount)
# ─────────────────────────────────────────────

@router.get('/validate-vgk')
def validate_vgk_member(
    vgk_code: str = Query(..., description='VGK member code (VGK0710XXXX)'),
    db: Session = Depends(get_db),
):
    """
    Validate a VGK Team member code for marketplace discount.
    Discount: 3% flat — available to all VGK members (including non-activated) with points balance.
    No auth required. Read-only.
    """
    try:
        result = db.execute(text("""
            SELECT id, partner_name, partner_code, vgk_points_balance, vgk_activated_at, company_id
            FROM official_partners
            WHERE UPPER(partner_code) = :code AND category = 'VGK_TEAM'
            LIMIT 1
        """), {'code': vgk_code.strip().upper()}).fetchone()

        if not result:
            return {'valid': False, 'message': 'VGK member code not found'}

        if not result.vgk_points_balance or float(result.vgk_points_balance) <= 0:
            return {'valid': False, 'message': 'No VGK points balance available'}

        seg = db.query(MarketplaceSegment).filter(
            MarketplaceSegment.company_id == result.company_id,
            MarketplaceSegment.is_active == True,
        ).order_by(MarketplaceSegment.sort_order).first()
        allow_vgk = bool(seg.allow_vgk) if seg and seg.allow_vgk is not None else True

        if not allow_vgk:
            return {'valid': False, 'message': 'VGK member discount not enabled for this segment'}

        # DC Protocol Mar 2026: Paid-aware VGK discount (3% paid, 2% non-paid).
        # Segment vgk_pct is the override for paid/activated members; non-paid always 2%.
        is_paid = bool(getattr(result, 'is_paid_activation', False))
        if is_paid:
            vgk_pct = float(seg.vgk_pct) if seg and seg.vgk_pct is not None else 3.0
        else:
            vgk_pct = 2.0

        return {
            'valid': True,
            'name': result.partner_name,
            'vgk_id': result.partner_code,
            'discount_mode': 'vgk',
            'discount_pct': vgk_pct,
            'points_balance': float(result.vgk_points_balance),
            'activated': result.vgk_activated_at is not None,
            'is_paid_activation': is_paid,
        }
    except Exception as e:
        logger.error(f'[MARKETPLACE] VGK validate error: {e}')
        return {'valid': False, 'message': 'Validation error'}


# ─────────────────────────────────────────────
# STAFF: Category configuration CRUD
# ─────────────────────────────────────────────

@router.get('/config/categories')
def get_category_configs(
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """List all category configs. Staff only."""
    configs = db.query(MarketplaceCategoryConfig).filter(
        MarketplaceCategoryConfig.company_id == company_id
    ).order_by(MarketplaceCategoryConfig.category_name).all()
    return [c.to_dict() for c in configs]


@router.put('/config/categories/{category_name}')
def upsert_category_config(
    category_name: str,
    payload: dict = Body(...),
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Create or update a category config. Staff only."""
    markup = float(payload.get('markup_percent', 15))
    if not (0 < markup <= 100):
        raise HTTPException(status_code=400, detail='markup_percent must be between 1 and 100')

    gst = float(payload.get('gst_percent', 18))
    floor = float(payload.get('margin_floor_percent', 5))
    hsn = payload.get('hsn_code', '')

    staff_name = getattr(current_user, 'full_name', None) or getattr(current_user, 'employee_name', None) or 'staff'

    existing = db.query(MarketplaceCategoryConfig).filter(
        MarketplaceCategoryConfig.category_name == category_name.upper(),
        MarketplaceCategoryConfig.company_id == company_id,
    ).first()

    if existing:
        existing.markup_percent = markup
        existing.gst_percent = gst
        existing.margin_floor_percent = floor
        existing.hsn_code = hsn
        existing.updated_by = staff_name
    else:
        cfg = MarketplaceCategoryConfig(
            category_name=category_name.upper(),
            markup_percent=markup,
            gst_percent=gst,
            margin_floor_percent=floor,
            hsn_code=hsn,
            updated_by=staff_name,
            company_id=company_id,
        )
        db.add(cfg)

    db.commit()
    return {'status': 'ok', 'category_name': category_name.upper()}


# ─────────────────────────────────────────────
# STAFF: Sheet sync trigger
# ─────────────────────────────────────────────

@router.post('/sync')
def trigger_sync(
    background_tasks: BackgroundTasks,
    company_id: int = Query(...),
    segment_id: Optional[int] = Query(None, description='Phase 3: sync specific segment'),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Trigger Google Sheet sync in the background. Returns immediately.
    DC Protocol: prevents concurrent syncs per company. Poll /sync/status or /sync/logs
    to check completion. Auto-seeds category configs from sheet categories.
    """
    if company_id in _SYNC_RUNNING:
        raise HTTPException(status_code=409, detail='Sync already in progress for this company. Check logs shortly.')

    staff_name = getattr(current_user, 'full_name', None) or 'staff'
    _SYNC_RUNNING.add(company_id)
    background_tasks.add_task(_do_sync_background, company_id, segment_id, staff_name)
    return {
        'status': 'sync_started',
        'message': 'Sync running in background — check logs in a moment',
        'company_id': company_id,
    }


@router.post('/sync-stock')
def trigger_stock_sync(
    background_tasks: BackgroundTasks,
    company_id: int = Query(1),
    current_user=Depends(get_current_user_hybrid),
):
    """
    DC-STOCK-MKT-001: Manually trigger stock_item_master → marketplace sync.
    Also runs the one-time sheet→stock import (DC-STOCK-MKT-002) first.
    Safe to call repeatedly — fully idempotent.
    """
    if company_id in _SYNC_RUNNING:
        raise HTTPException(status_code=409, detail='Sync already in progress for this company.')

    _SYNC_RUNNING.add(company_id)

    def _do_stock_sync_bg(cid: int) -> None:
        from app.core.database import SessionLocal
        _db = SessionLocal()
        try:
            try:
                _import_sheet_products_to_stock(_db)
            except Exception as _ie:
                logger.warning(f'[DC-STOCK-MKT-002] import step error (non-fatal): {_ie}')
            result = run_stock_sync(_db, company_id=cid, triggered_by='manual')
            logger.info(f'[DC-STOCK-MKT-001] Manual sync done: {result}')
        except Exception as e:
            logger.error(f'[DC-STOCK-MKT-001] Manual sync failed: {e}')
        finally:
            _db.close()
            _SYNC_RUNNING.discard(cid)

    background_tasks.add_task(_do_stock_sync_bg, company_id)
    return {
        'status': 'sync_started',
        'message': 'Stock→Marketplace sync running in background',
        'company_id': company_id,
    }


@router.get('/sync/status')
def get_sync_status(
    company_id: int = Query(...),
):
    """Check if a background sync is currently running for this company.
    DC Protocol: No DB session needed — reads in-memory set only.
    Auth intentionally omitted to avoid consuming DB pool connections during heavy polling.
    """
    return {'running': company_id in _SYNC_RUNNING}


@router.get('/sync/logs')
def get_sync_logs(
    company_id: int = Query(...),
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Recent sync audit logs. Staff only."""
    logs = db.query(MarketplaceSyncLog).filter(
        MarketplaceSyncLog.company_id == company_id
    ).order_by(MarketplaceSyncLog.sync_timestamp.desc()).limit(limit).all()
    return [l.to_dict() for l in logs]


# ─────────────────────────────────────────────
# PUBLIC: Segments listing (Phase 3)
# ─────────────────────────────────────────────

@router.get('/segments')
def list_segments(
    company_id: int = Query(..., description='DC Protocol'),
    db: Session = Depends(get_db),
):
    """Return all active segments for the marketplace, ordered by sort_order."""
    segs = db.query(MarketplaceSegment).filter(
        MarketplaceSegment.company_id == company_id,
        MarketplaceSegment.is_active == True,
    ).order_by(MarketplaceSegment.sort_order, MarketplaceSegment.id).all()
    return [s.to_dict() for s in segs]


# ─────────────────────────────────────────────
# STAFF: Segment CRUD (Phase 3 admin)
# ─────────────────────────────────────────────

@router.post('/segments')
def create_segment(
    company_id: int = Query(...),
    name: str = Body(...),
    slug: str = Body(...),
    description: Optional[str] = Body(default=None),
    google_sheet_url: Optional[str] = Body(default=None),
    mnr_pct: float = Body(default=3.0),
    partner_pct: float = Body(default=12.0),
    student_pct: float = Body(default=10.0),
    vgk_pct: float = Body(default=3.0),
    allow_mnr: bool = Body(default=True),
    allow_partner: bool = Body(default=True),
    allow_student: bool = Body(default=True),
    allow_vgk: bool = Body(default=True),
    badge_labels: Optional[list] = Body(default=None),
    sort_order: int = Body(default=0),
    segment_type: Optional[str] = Body(default=None),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Create a new marketplace segment. Staff only."""
    existing = db.query(MarketplaceSegment).filter(
        MarketplaceSegment.company_id == company_id,
        MarketplaceSegment.slug == slug.lower().strip(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f'Segment slug "{slug}" already exists')
    seg = MarketplaceSegment(
        company_id=company_id,
        name=name.strip(),
        slug=slug.lower().strip(),
        description=description,
        google_sheet_url=google_sheet_url,
        mnr_pct=mnr_pct,
        partner_pct=partner_pct,
        student_pct=student_pct,
        vgk_pct=vgk_pct,
        allow_mnr=allow_mnr,
        allow_partner=allow_partner,
        allow_student=allow_student,
        allow_vgk=allow_vgk,
        badge_labels=badge_labels or [],
        sort_order=sort_order,
        segment_type=(segment_type or 'ECOM').upper(),
        is_active=True,
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)
    return seg.to_dict()


@router.put('/segments/{segment_id}')
def update_segment(
    segment_id: int,
    company_id: int = Query(...),
    name: Optional[str] = Body(default=None),
    description: Optional[str] = Body(default=None),
    google_sheet_url: Optional[str] = Body(default=None),
    mnr_pct: Optional[float] = Body(default=None),
    partner_pct: Optional[float] = Body(default=None),
    student_pct: Optional[float] = Body(default=None),
    vgk_pct: Optional[float] = Body(default=None),
    allow_mnr: Optional[bool] = Body(default=None),
    allow_partner: Optional[bool] = Body(default=None),
    allow_student: Optional[bool] = Body(default=None),
    allow_vgk: Optional[bool] = Body(default=None),
    badge_labels: Optional[list] = Body(default=None),
    sort_order: Optional[int] = Body(default=None),
    is_active: Optional[bool] = Body(default=None),
    segment_type: Optional[str] = Body(default=None),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Update a marketplace segment. Staff only."""
    seg = db.query(MarketplaceSegment).filter(
        MarketplaceSegment.id == segment_id,
        MarketplaceSegment.company_id == company_id,
    ).first()
    if not seg:
        raise HTTPException(status_code=404, detail='Segment not found')
    if name is not None: seg.name = name.strip()
    if description is not None: seg.description = description
    if google_sheet_url is not None: seg.google_sheet_url = google_sheet_url
    if mnr_pct is not None: seg.mnr_pct = mnr_pct
    if partner_pct is not None: seg.partner_pct = partner_pct
    if student_pct is not None: seg.student_pct = student_pct
    if vgk_pct is not None: seg.vgk_pct = vgk_pct
    if allow_mnr is not None: seg.allow_mnr = allow_mnr
    if allow_partner is not None: seg.allow_partner = allow_partner
    if allow_student is not None: seg.allow_student = allow_student
    if allow_vgk is not None: seg.allow_vgk = allow_vgk
    if badge_labels is not None: seg.badge_labels = badge_labels
    if sort_order is not None: seg.sort_order = sort_order
    if is_active is not None: seg.is_active = is_active
    if segment_type is not None: seg.segment_type = segment_type.upper()
    db.commit()
    db.refresh(seg)
    return seg.to_dict()


# ─────────────────────────────────────────────
# STAFF: Product management
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# STAFF: Admin product management (images, edits)
# ─────────────────────────────────────────────

@router.get('/admin/products')
def list_admin_products(
    company_id: int = Query(...),
    search: Optional[str] = Query(None),
    company_filter: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    img_filter: Optional[str] = Query(None),
    stock_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    q = db.query(MarketspareItem).filter(MarketspareItem.company_id == company_id)
    if search:
        q = q.filter(or_(
            MarketspareItem.name.ilike(f'%{search}%'),
            MarketspareItem.sku.ilike(f'%{search}%'),
        ))
    if company_filter:
        q = q.filter(MarketspareItem.company_name.ilike(f'%{company_filter}%'))
    if category:
        q = q.filter(MarketspareItem.category_name == category)
    if img_filter == 'missing':
        q = q.filter(or_(MarketspareItem.image_url == None, MarketspareItem.image_url == ''))
    elif img_filter == 'has_image':
        q = q.filter(MarketspareItem.image_url != None, MarketspareItem.image_url != '')
    if stock_filter == 'below_threshold':
        q = q.filter(
            MarketspareItem.min_stock_threshold > 0,
            MarketspareItem.available_qty < MarketspareItem.min_stock_threshold,
        )
    elif stock_filter == 'oos':
        q = q.filter(MarketspareItem.available_qty == 0)
    elif stock_filter == 'in_stock':
        q = q.filter(MarketspareItem.available_qty > 0)

    total = q.count()
    items = q.order_by(
        MarketspareItem.company_name,
        MarketspareItem.category_name,
        MarketspareItem.sku,
    ).offset((page - 1) * per_page).limit(per_page).all()

    # Ordered qty per SKU from open POs (confirmed/processing)
    sku_list = [p.sku for p in items]
    ordered_qty_map = {}
    if sku_list:
        rows = db.execute(text("""
            SELECT poi.sku, COALESCE(SUM(poi.ordered_qty), 0)
            FROM marketplace_po_items poi
            JOIN marketplace_purchase_orders po ON po.id = poi.po_id
            WHERE po.company_id = :cid
              AND po.status IN ('confirmed','processing','pending','new')
              AND poi.sku = ANY(:skus)
            GROUP BY poi.sku
        """), {'cid': company_id, 'skus': sku_list}).fetchall()
        ordered_qty_map = {r[0]: int(r[1]) for r in rows}

    # PO count per SKU — total number of PO line items across all statuses (demand signal)
    po_count_map = {}
    if sku_list:
        po_rows = db.execute(text("""
            SELECT poi.sku, COUNT(poi.id)
            FROM marketplace_po_items poi
            WHERE poi.sku = ANY(:skus)
            GROUP BY poi.sku
        """), {'skus': sku_list}).fetchall()
        po_count_map = {r[0]: int(r[1]) for r in po_rows}

    # Distinct companies for filter dropdown
    companies = [r[0] for r in db.query(MarketspareItem.company_name)
        .filter(MarketspareItem.company_id == company_id)
        .filter(MarketspareItem.company_name != None)
        .distinct().order_by(MarketspareItem.company_name).all()]

    products = []
    for p in items:
        d = p.to_dict()
        d['ordered_qty'] = ordered_qty_map.get(p.sku, 0)
        d['po_count'] = po_count_map.get(p.sku, 0)
        d['below_threshold'] = (
            int(p.min_stock_threshold or 0) > 0 and
            int(p.available_qty or 0) < int(p.min_stock_threshold or 0)
        )
        products.append(d)

    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'companies': companies,
        'products': products,
    }


@router.put('/admin/products/{product_id}')
def update_admin_product(
    product_id: int,
    company_id: int = Query(...),
    payload: dict = Body(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    item = db.query(MarketspareItem).filter(
        MarketspareItem.id == product_id,
        MarketspareItem.company_id == company_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    # Fields that can be edited — available_qty always sheet-authoritative so excluded
    editable = ['name', 'description', 'brand', 'model_compat', 'specifications',
                'color', 'speciality', 'dealer_price', 'company_name',
                'min_stock_threshold']
    protected = set(item.override_fields or [])

    for field in editable:
        if field in payload:
            setattr(item, field, payload[field])
            protected.add(field)  # Mark this field as locally overridden

    item.override_fields = list(protected)
    item.manually_overridden = len(protected) > 0

    # available_qty editable too but NOT protected (sheet stays authoritative)
    if 'available_qty' in payload:
        item.available_qty = int(payload['available_qty'])

    db.commit()
    return {
        'success': True,
        'id': product_id,
        'override_fields': item.override_fields,
    }


@router.post('/admin/products/{product_id}/clear-overrides')
def clear_product_overrides(
    product_id: int,
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Remove all local overrides — next sync will refresh all fields from Google Sheet."""
    item = db.query(MarketspareItem).filter(
        MarketspareItem.id == product_id,
        MarketspareItem.company_id == company_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')
    item.override_fields = []
    item.manually_overridden = False
    db.commit()
    return {'success': True, 'message': 'Overrides cleared — next sync will refresh from Google Sheet'}


@router.post('/admin/products/{product_id}/image')
async def upload_product_image(
    product_id: int,
    company_id: int = Query(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    item = db.query(MarketspareItem).filter(
        MarketspareItem.id == product_id,
        MarketspareItem.company_id == company_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='File too large (max 5MB)')

    sku = item.sku
    ext = (file.filename or '').rsplit('.', 1)[-1].lower()
    if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
        ext = 'png'
    filename = f'{sku}.{ext}'

    # DC Protocol Mar 2026: Save to Replit Object Storage (persistent across deployments)
    try:
        obj_client = _get_obj_client()
        obj_client.upload_from_bytes(f'{_OBJ_STORE_KEY_PREFIX}/{filename}', content)
    except Exception as e:
        logger.warning(f'[MktImg] Object Storage upload failed for {filename}: {e}')

    # Also write to local filesystem for dev convenience
    try:
        img_dir = Path('/home/runner/workspace/frontend/public/marketplace/product-images')
        img_dir.mkdir(parents=True, exist_ok=True)
        (img_dir / filename).write_bytes(content)
    except Exception as e:
        logger.warning(f'[MktImg] Local filesystem write failed for {filename}: {e}')

    image_url = f'/api/v1/marketplace/images/{filename}'
    item.image_url = image_url
    db.commit()
    return {'success': True, 'image_url': image_url}


@router.patch('/products/{product_id}/toggle')
def toggle_product(
    product_id: int,
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """Activate / deactivate a product. Staff only."""
    item = db.query(MarketspareItem).filter(
        MarketspareItem.id == product_id,
        MarketspareItem.company_id == company_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail='Product not found')
    item.is_active = not item.is_active
    db.commit()
    return {'id': product_id, 'is_active': item.is_active}


@router.get('/admin/stock-dashboard')
def stock_dashboard(
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    """
    Executive-level stock intelligence dashboard.
    Returns KPIs, category breakdown, top restock items, and procurement budget estimate.
    """
    all_items = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
    ).all()

    total = len(all_items)
    in_stock = sum(1 for p in all_items if (p.available_qty or 0) > 0)
    zero_stock = sum(1 for p in all_items if (p.available_qty or 0) == 0)
    below_min = sum(1 for p in all_items
                    if (p.min_stock_threshold or 0) > 0
                    and (p.available_qty or 0) < (p.min_stock_threshold or 0))

    # Inventory value = sum(available_qty × dealer_price)
    inventory_value = sum(
        float(p.available_qty or 0) * float(p.dealer_price or 0)
        for p in all_items
    )

    # Procurement budget needed = for items below min level (or zero stock):
    # proc_with_tax × shortfall_qty (at least 1 unit)
    proc_budget_total = 0.0
    for p in all_items:
        if p.proc_with_tax and float(p.proc_with_tax) > 0:
            shortfall = max(
                int(p.min_stock_threshold or 0) - int(p.available_qty or 0),
                1 if (p.available_qty or 0) == 0 else 0
            )
            if shortfall > 0:
                proc_budget_total += float(p.proc_with_tax) * shortfall

    # Open procurement requests
    open_zypr = db.query(MarketplaceProcurementRequest).filter(
        MarketplaceProcurementRequest.company_id == company_id,
        MarketplaceProcurementRequest.status.in_(['pending', 'ordered']),
    ).count()

    # Open purchase orders
    open_po = db.query(MarketplacePurchaseOrder).filter(
        MarketplacePurchaseOrder.company_id == company_id,
        MarketplacePurchaseOrder.status.in_(['confirmed', 'processing', 'pending', 'new']),
    ).count()

    # Category breakdown
    cat_map = {}
    for p in all_items:
        cat = p.category_name or 'UNCATEGORISED'
        if cat not in cat_map:
            cat_map[cat] = {
                'category': cat,
                'total': 0,
                'in_stock': 0,
                'zero_stock': 0,
                'below_min': 0,
                'inventory_value': 0.0,
                'proc_budget': 0.0,
            }
        c = cat_map[cat]
        c['total'] += 1
        qty = int(p.available_qty or 0)
        price = float(p.dealer_price or 0)
        c['inventory_value'] += qty * price
        if qty > 0:
            c['in_stock'] += 1
        else:
            c['zero_stock'] += 1
        threshold = int(p.min_stock_threshold or 0)
        if threshold > 0 and qty < threshold:
            c['below_min'] += 1
        if p.proc_with_tax and float(p.proc_with_tax) > 0:
            shortfall = max(threshold - qty, 1 if qty == 0 else 0)
            if shortfall > 0:
                c['proc_budget'] += float(p.proc_with_tax) * shortfall

    categories = sorted(cat_map.values(), key=lambda x: x['proc_budget'], reverse=True)
    for c in categories:
        c['inventory_value'] = round(c['inventory_value'], 2)
        c['proc_budget'] = round(c['proc_budget'], 2)

    # Top 10 items needing restock (by proc_with_tax DESC, only those with cost data)
    restock_items = []
    for p in all_items:
        if p.proc_with_tax and float(p.proc_with_tax) > 0:
            qty = int(p.available_qty or 0)
            threshold = int(p.min_stock_threshold or 0)
            shortfall = max(threshold - qty, 1 if qty == 0 else 0)
            if shortfall > 0:
                restock_items.append({
                    'id': p.id,
                    'sku': p.sku,
                    'name': p.name,
                    'category_name': p.category_name,
                    'available_qty': qty,
                    'min_stock_threshold': threshold,
                    'shortfall_qty': shortfall,
                    'proc_cost': float(p.proc_cost or 0),
                    'proc_transport': float(p.proc_transport or 0),
                    'proc_ex_tax': float(p.proc_ex_tax or 0),
                    'proc_tax_pct': float(p.proc_tax_pct or 0),
                    'proc_with_tax': float(p.proc_with_tax or 0),
                    'budget_required': round(float(p.proc_with_tax) * shortfall, 2),
                    'image_url': p.image_url or '',
                })
    restock_items.sort(key=lambda x: x['proc_with_tax'], reverse=True)

    return {
        'kpis': {
            'total_products': total,
            'in_stock': in_stock,
            'zero_stock': zero_stock,
            'below_min_level': below_min,
            'open_zypr': open_zypr,
            'open_po': open_po,
            'inventory_value': round(inventory_value, 2),
            'proc_budget_needed': round(proc_budget_total, 2),
        },
        'categories': categories,
        'top_restock': restock_items[:10],
    }


# ─────────────────────────────────────────────
# STAFF: Promo Code CRUD (Codes & Segments — Mar 2026)
# Access: MR10001 only (enforced by menu access; endpoints require staff auth)
# ─────────────────────────────────────────────

@router.get('/promo-codes')
def list_promo_codes(
    company_id: int = Query(...),
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    q = db.query(MarketplacePromoCode).filter(MarketplacePromoCode.company_id == company_id)
    if status:
        q = q.filter(MarketplacePromoCode.status == status)
    codes = q.order_by(MarketplacePromoCode.created_at.desc()).all()
    return [c.to_dict() for c in codes]


@router.post('/promo-codes')
def create_promo_code(
    company_id: int = Query(...),
    code: str = Body(...),
    label: Optional[str] = Body(default=None),
    default_discount_pct: float = Body(default=0),
    segment_discounts: Optional[dict] = Body(default=None),
    valid_from: Optional[str] = Body(default=None),
    valid_to: Optional[str] = Body(default=None),
    usage_limit: Optional[int] = Body(default=None),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    code_upper = code.strip().upper()
    existing = db.query(MarketplacePromoCode).filter(MarketplacePromoCode.code == code_upper).first()
    if existing:
        raise HTTPException(status_code=400, detail=f'Code "{code_upper}" already exists')
    pc = MarketplacePromoCode(
        code=code_upper,
        label=label,
        default_discount_pct=default_discount_pct,
        segment_discounts=segment_discounts or {},
        status='active',
        valid_from=datetime.fromisoformat(valid_from) if valid_from else None,
        valid_to=datetime.fromisoformat(valid_to) if valid_to else None,
        usage_limit=usage_limit,
        times_used=0,
        times_searched=0,
        created_by=str(getattr(current_user, 'mnr_id', '') or getattr(current_user, 'id', '')),
        company_id=company_id,
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc.to_dict()


@router.put('/promo-codes/{code_id}')
def update_promo_code(
    code_id: int,
    company_id: int = Query(...),
    label: Optional[str] = Body(default=None),
    default_discount_pct: Optional[float] = Body(default=None),
    segment_discounts: Optional[dict] = Body(default=None),
    valid_from: Optional[str] = Body(default=None),
    valid_to: Optional[str] = Body(default=None),
    usage_limit: Optional[int] = Body(default=None),
    status: Optional[str] = Body(default=None),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    pc = db.query(MarketplacePromoCode).filter(
        MarketplacePromoCode.id == code_id,
        MarketplacePromoCode.company_id == company_id,
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail='Promo code not found')
    if label is not None:
        pc.label = label
    if default_discount_pct is not None:
        pc.default_discount_pct = default_discount_pct
    if segment_discounts is not None:
        pc.segment_discounts = segment_discounts
    if valid_from is not None:
        pc.valid_from = datetime.fromisoformat(valid_from) if valid_from else None
    if valid_to is not None:
        pc.valid_to = datetime.fromisoformat(valid_to) if valid_to else None
    if usage_limit is not None:
        pc.usage_limit = usage_limit
    if status is not None:
        pc.status = status
    db.commit()
    db.refresh(pc)
    return pc.to_dict()


@router.delete('/promo-codes/{code_id}')
def delete_promo_code(
    code_id: int,
    company_id: int = Query(...),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    pc = db.query(MarketplacePromoCode).filter(
        MarketplacePromoCode.id == code_id,
        MarketplacePromoCode.company_id == company_id,
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail='Promo code not found')
    db.delete(pc)
    db.commit()
    return {'success': True, 'message': 'Code deleted'}


# ─────────────────────────────────────────────
# PUBLIC: Validate promo code at checkout
# ─────────────────────────────────────────────

@router.get('/validate-promo')
def validate_promo_code(
    promo_code: str = Query(...),
    company_id: int = Query(1),
    segment_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    from app.models.base import get_indian_time
    code_val = promo_code.strip().upper()
    pc = db.query(MarketplacePromoCode).filter(
        MarketplacePromoCode.code == code_val,
        MarketplacePromoCode.company_id == company_id,
        MarketplacePromoCode.status == 'active',
    ).first()

    was_valid = False
    discount_pct = 0.0

    if pc:
        now = get_indian_time()
        if pc.valid_from and now < pc.valid_from:
            pc = None
        elif pc.valid_to and now > pc.valid_to:
            pc = None
        elif pc.usage_limit and pc.times_used >= pc.usage_limit:
            pc = None

    if pc:
        was_valid = True
        seg_key = str(segment_id) if segment_id else None
        if seg_key and seg_key in (pc.segment_discounts or {}):
            discount_pct = float(pc.segment_discounts[seg_key])
        else:
            discount_pct = float(pc.default_discount_pct or 0)
        pc.times_searched = (pc.times_searched or 0) + 1
        db.add(MarketplaceCodeLookup(
            code_type='promo', code_value=code_val, was_valid=True,
            segment_id=segment_id, company_id=company_id,
        ))
        db.commit()
    else:
        _log_lookup(db, 'promo', code_val, False, segment_id, company_id)

    if not was_valid:
        return {'valid': False, 'message': 'Promo code not found, expired, or inactive'}

    return {
        'valid': True,
        'code': pc.code,
        'label': pc.label or '',
        'discount_mode': 'promo',
        'discount_pct': discount_pct,
    }


# ─────────────────────────────────────────────
# STAFF: Analytics — code/ID usage (Codes & Segments)
# ─────────────────────────────────────────────

@router.get('/analytics/code-usage')
def get_code_usage_analytics(
    company_id: int = Query(...),
    code_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    segment_id: Optional[int] = Query(None),
    sort_by: str = Query('searches'),
    sort_dir: str = Query('desc'),
    current_user=Depends(get_current_user_hybrid),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    lookup_rows = db.execute(text("""
        SELECT code_type, code_value,
               COUNT(*) AS total_searches,
               SUM(CASE WHEN was_valid THEN 1 ELSE 0 END) AS valid_searches
        FROM marketplace_code_lookups
        WHERE company_id = :cid
          AND (:code_type IS NULL OR code_type = :code_type)
          AND (:dt_from IS NULL OR looked_up_at >= :dt_from)
          AND (:dt_to IS NULL OR looked_up_at <= :dt_to)
          AND (:seg_id IS NULL OR segment_id = :seg_id)
        GROUP BY code_type, code_value
    """), {'cid': company_id, 'code_type': code_type, 'dt_from': dt_from, 'dt_to': dt_to, 'seg_id': segment_id}).fetchall()

    po_mnr = db.execute(text("""
        SELECT 'mnr' AS code_type, mnr_id AS code_value,
               COUNT(*) AS applied,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS purchased,
               COALESCE(SUM(CASE WHEN status = 'completed' THEN total_value ELSE 0 END), 0) AS total_value
        FROM marketplace_purchase_orders
        WHERE company_id = :cid AND mnr_id IS NOT NULL AND mnr_id != ''
          AND (:code_type IS NULL OR :code_type = 'mnr')
          AND (:dt_from IS NULL OR created_at >= :dt_from)
          AND (:dt_to IS NULL OR created_at <= :dt_to)
        GROUP BY mnr_id
    """), {'cid': company_id, 'code_type': code_type, 'dt_from': dt_from, 'dt_to': dt_to}).fetchall()

    po_partner = db.execute(text("""
        SELECT 'partner' AS code_type, partner_code AS code_value,
               COUNT(*) AS applied,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS purchased,
               COALESCE(SUM(CASE WHEN status = 'completed' THEN total_value ELSE 0 END), 0) AS total_value
        FROM marketplace_purchase_orders
        WHERE company_id = :cid AND partner_code IS NOT NULL AND partner_code != ''
          AND (:code_type IS NULL OR :code_type = 'partner')
          AND (:dt_from IS NULL OR created_at >= :dt_from)
          AND (:dt_to IS NULL OR created_at <= :dt_to)
        GROUP BY partner_code
    """), {'cid': company_id, 'code_type': code_type, 'dt_from': dt_from, 'dt_to': dt_to}).fetchall()

    po_promo = db.execute(text("""
        SELECT 'promo' AS code_type, discount_name AS code_value,
               COUNT(*) AS applied,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS purchased,
               COALESCE(SUM(CASE WHEN status = 'completed' THEN total_value ELSE 0 END), 0) AS total_value
        FROM marketplace_purchase_orders
        WHERE company_id = :cid AND discount_mode = 'promo' AND discount_name IS NOT NULL
          AND (:code_type IS NULL OR :code_type = 'promo')
          AND (:dt_from IS NULL OR created_at >= :dt_from)
          AND (:dt_to IS NULL OR created_at <= :dt_to)
        GROUP BY discount_name
    """), {'cid': company_id, 'code_type': code_type, 'dt_from': dt_from, 'dt_to': dt_to}).fetchall()

    result_map = {}
    for row in lookup_rows:
        key = (row.code_type, row.code_value)
        result_map[key] = {
            'code_type': row.code_type,
            'code_value': row.code_value,
            'searches': int(row.total_searches or 0),
            'valid_searches': int(row.valid_searches or 0),
            'applied': 0,
            'purchased': 0,
            'total_value': 0.0,
        }

    for rows in [po_mnr, po_partner, po_promo]:
        for row in rows:
            key = (row.code_type, row.code_value)
            if key not in result_map:
                result_map[key] = {
                    'code_type': row.code_type,
                    'code_value': row.code_value,
                    'searches': 0,
                    'valid_searches': 0,
                    'applied': 0,
                    'purchased': 0,
                    'total_value': 0.0,
                }
            result_map[key]['applied'] = int(row.applied or 0)
            result_map[key]['purchased'] = int(row.purchased or 0)
            result_map[key]['total_value'] = float(row.total_value or 0)

    results = list(result_map.values())
    sort_key_map = {
        'searches': 'searches',
        'applied': 'applied',
        'purchased': 'purchased',
        'value': 'total_value',
    }
    sk = sort_key_map.get(sort_by, 'searches')
    results.sort(key=lambda x: x[sk], reverse=(sort_dir != 'asc'))

    return {'rows': results, 'total': len(results)}
