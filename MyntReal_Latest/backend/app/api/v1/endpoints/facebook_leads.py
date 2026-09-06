"""
Facebook Lead Ads Webhook API Endpoints — Production Hardened Edition
DC Protocol Mar 2026: Webhook-based lead capture from Facebook Lead Ads
Atomic Transactions, Database-Enforced Idempotency, Fail-Closed Security,
Graph API v24.0, Complete Pagination & Database-Driven Multi-Tenant Form Routing.

Endpoints:
- GET /webhook: Facebook webhook verification
- POST /webhook: Receive lead notifications
- GET /config: Check integration status
- POST /test-lead: Create test lead (admin only)
- GET /leads: List Facebook CRM leads
- POST /sync-pages: Bulk sync Facebook Pages from User Token
- GET /pages: List synced Facebook Pages
- PUT /pages/{page_id}/segment: Update page segment
- GET /forms: List all configured form routing mappings
- POST /forms/map: Dynamically register/update a Meta Form routing mapping
- POST /pull-leads: Manual pull / backfill from Graph API v24.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, Body, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text as sqlt
from typing import Optional, List
from pydantic import BaseModel
import logging
import json

from app.core.database import get_db
from app.models.crm import CRMLead
from app.models.meta_attribution import MetaLeadsAttribution
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.services.facebook_leads_service import (
    facebook_leads_service,
    get_indian_time,
    GRAPH_API_VERSION
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)
router = APIRouter()


class FacebookLeadConfig(BaseModel):
    """Configuration for Facebook lead mapping"""
    default_company_id: int
    default_category_id: Optional[int] = None
    auto_assign_telecaller_id: Optional[int] = None


class TestLeadRequest(BaseModel):
    """Test lead creation request"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_id: int
    category_id: Optional[int] = None


class FormMappingRequest(BaseModel):
    """Request schema for dynamic form routing registration"""
    page_id: str
    form_id: str
    company_id: int
    category_id: Optional[int] = None
    form_name: Optional[str] = None
    crm_segment: str = "GENERAL"
    segment_tag: Optional[str] = None
    looking_for: Optional[str] = None
    is_active: bool = True


# ── Webhook Verification (GET) ────────────────────────────────────────────────
@router.get("/webhook")
async def verify_facebook_webhook(
    request: Request,
):
    """
    Facebook webhook verification endpoint.
    Called by Meta to verify webhook URL subscription.
    """
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    if facebook_leads_service.verify_webhook_token(mode, token):
        logger.info("[META-WEBHOOK-VERIFY] Webhook verified successfully with Meta challenge.")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"[META-WEBHOOK-VERIFY-FAIL] Verification failed — mode: {mode}")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


# ── Webhook Ingestion (POST) ──────────────────────────────────────────────────
@router.post("/webhook")
async def receive_facebook_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive real-time lead notifications from Meta Lead Ads.
    Fail-closed HMAC-SHA256 signature validation.
    Atomic DB transaction for lead ingestion and attribution.
    """
    body = await request.body()
    signature = request.headers.get('X-Hub-Signature-256', '')

    # 1. Fail-closed HMAC signature verification
    if not facebook_leads_service.app_secret:
        logger.error("[META-WEBHOOK-SECURITY] FACEBOOK_APP_SECRET is not configured on server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server webhook authentication is not configured"
        )

    if not facebook_leads_service.verify_webhook_signature(body, signature):
        logger.warning("[META-WEBHOOK-SECURITY] Rejecting Meta webhook: Invalid or missing HMAC signature.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    # 2. Parse JSON payload
    try:
        data = json.loads(body.decode('utf-8'))
    except Exception as e:
        logger.error(f"[META-WEBHOOK-ERROR] Error parsing webhook JSON: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    if data.get('object') != 'page':
        logger.info(f"[META-WEBHOOK] Ignoring non-page webhook object: {data.get('object')}")
        return {"status": "ignored", "reason": "not a page event"}

    leads_created = 0
    duplicates_skipped = 0
    errors = []

    # 3. Process each leadgen change atomically
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'leadgen':
                lead_value = change.get('value', {})
                lead_id = lead_value.get('leadgen_id')
                page_id = lead_value.get('page_id')
                form_id = lead_value.get('form_id')

                if not lead_id:
                    logger.warning(f"[META-WEBHOOK] Empty leadgen_id in change entry: {change}")
                    continue

                logger.info(f"[META-WEBHOOK-INCOMING] Processing Meta lead {lead_id} from page {page_id}, form {form_id}")

                try:
                    crm_lead = await process_facebook_lead(
                        lead_id=str(lead_id),
                        page_id=str(page_id) if page_id else None,
                        form_id=str(form_id) if form_id else None,
                        db=db
                    )
                    if crm_lead:
                        leads_created += 1
                    else:
                        duplicates_skipped += 1
                except Exception as e:
                    error_msg = f"Error processing lead {lead_id}: {str(e)}"
                    logger.exception(f"[META-WEBHOOK-ERROR] {error_msg}")
                    errors.append(error_msg)

    return {
        "status": "ok",
        "leads_created": leads_created,
        "duplicates_skipped": duplicates_skipped,
        "errors": errors if errors else None
    }


# ── Atomic Lead Ingestion Processor ───────────────────────────────────────────
async def process_facebook_lead(
    lead_id: str,
    page_id: Optional[str],
    form_id: Optional[str],
    db: Session
) -> Optional[CRMLead]:
    """
    Process a single Facebook lead atomically into CRMLead and MetaLeadsAttribution.
    Enforces DB-level idempotency and transactional consistency.
    """
    # ── 1. Fast Duplicate Guard (Idempotency) ──────────────────────────────────
    if facebook_leads_service.lead_already_exists(lead_id, db):
        logger.info(f"[META-DEDUP] Lead {lead_id} already exists in CRM. Skipping.")
        return None

    # ── 2. Resolve Page Token & Segment from DB ────────────────────────────────
    page_info = facebook_leads_service.get_page_info(page_id, db) if page_id else {}
    page_token   = page_info.get('token') or facebook_leads_service._legacy_token
    page_segment = page_info.get('segment', 'GENERAL')
    page_name    = page_info.get('name', '')
    page_cid     = page_info.get('company_id')  # None if page is unknown or not configured in DB

    # ── 3. Fetch Lead Data from Meta Graph API v24.0 ──────────────────────────
    lead_data = facebook_leads_service.fetch_lead_data(lead_id, access_token=page_token)
    if not lead_data:
        logger.error(f"[META-FETCH-FAIL] Could not fetch lead data for lead_id={lead_id} (page {page_id})")
        return None

    # ── 4. Map to CRM Lead Schema (Database-Driven Dynamic Routing) ────────────
    crm_data = facebook_leads_service.map_to_crm_lead(
        lead_data=lead_data,
        company_id=page_cid,
        category_id=None,
        page_segment=page_segment,
        page_name=page_name,
        form_id=form_id,
        page_id=page_id,
        db=db
    )
    if not crm_data:
        logger.warning(f"[META-REJECT] Lead {lead_id} mapping returned empty data.")
        return None

    # ── 5. Single Atomic Transaction: CRMLead + MetaLeadsAttribution ───────────
    try:
        crm_lead = CRMLead(**crm_data)
        db.add(crm_lead)
        db.flush()  # Generates crm_lead.id within active transaction

        attribution = MetaLeadsAttribution(
            company_id=crm_lead.company_id,  # 🔒 Fixed P0 NameError: Authoritative company identity
            lead_id=crm_lead.id,
            meta_lead_id=str(lead_id),
            meta_campaign_id=str(lead_data.get('campaign_id') or '') or None,
            meta_campaign_name=str(lead_data.get('campaign_name') or '') or None,
            meta_adset_id=str(lead_data.get('adset_id') or '') or None,
            meta_adset_name=str(lead_data.get('adset_name') or '') or None,
            meta_ad_id=str(lead_data.get('ad_id') or '') or None,
            meta_ad_name=str(lead_data.get('ad_name') or '') or None,
            meta_form_id=str(lead_data.get('form_id') or form_id or '') or None,
            meta_form_name=str(page_name) if page_name else None
        )
        db.add(attribution)
        db.commit()
        db.refresh(crm_lead)
        logger.info(f"[META-INGESTION-SUCCESS] CRM Lead #{crm_lead.id} created atomically with attribution for Meta lead {lead_id} (Company: {crm_lead.company_id})")

    except IntegrityError as ie:
        db.rollback()
        err_str = str(ie).lower()
        existing_att = db.query(MetaLeadsAttribution).filter(
            MetaLeadsAttribution.meta_lead_id == str(lead_id)
        ).first()
        if existing_att:
            logger.info(f"[META-CONCURRENT-DEDUP] Meta lead {lead_id} was ingested concurrently. Rollback complete, returning existing lead #{existing_att.lead_id}.")
            return db.query(CRMLead).filter(CRMLead.id == existing_att.lead_id).first()
        if "uq_meta_leads_attribution_meta_lead_id" in err_str or "meta_lead_id" in err_str:
            return None
        logger.error(f"[DB-INTEGRITY-ERROR] Integrity error ingesting lead {lead_id}: {ie}")
        raise ie

    except Exception as ex:
        db.rollback()
        logger.exception(f"[CRITICAL-INGESTION-ERROR] Failed to atomically persist Meta lead {lead_id}: {ex}")
        raise ex

    # ── 6. Auto WhatsApp Welcome Message & Group Alert (Post-Commit) ──────────
    try:
        from app.services.whatsapp_auto_service import send_lead_welcome
        from app.services.whatsapp_group_alert_service import send_instant_new_lead_group_alert

        if crm_lead.phone:
            send_lead_welcome(
                db=db,
                phone=crm_lead.phone,
                lead_name=crm_lead.name,
                lead_id=crm_lead.id
            )

        send_instant_new_lead_group_alert(db, crm_lead.id)
    except Exception as wa_err:
        logger.warning(f"[POST-INGESTION-TRIGGER] Auto WhatsApp triggers exception for lead {crm_lead.id}: {wa_err}")

    return crm_lead


# ── Configuration Status (GET) ────────────────────────────────────────────────
@router.get("/config")
async def get_facebook_config(
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get Facebook integration configuration status.
    """
    is_configured = facebook_leads_service.is_configured()
    
    return {
        "success": True,
        "is_configured": is_configured,
        "verify_token": facebook_leads_service.verify_token if is_configured else None,
        "api_version": facebook_leads_service.api_version,
        "has_page_token": bool(facebook_leads_service._legacy_token),
        "has_app_secret": bool(facebook_leads_service.app_secret),
        "webhook_url": "/api/v1/facebook-leads/webhook",
        "security_mode": "FAIL_CLOSED_HMAC_SHA256"
    }


# ── Test Lead Endpoint ────────────────────────────────────────────────────────
@router.post("/test-lead")
async def create_test_lead(
    data: TestLeadRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a test Facebook lead for testing integration (Staff only).
    """
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.id == data.company_id,
        AssociatedCompany.is_active == True
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    test_lead_data = {
        'company_id': data.company_id,
        'name': data.name,
        'email': data.email,
        'phone': data.phone,
        'source': 'Online - M',
        'source_details': json.dumps({
            'lead_id': f'test_{int(get_indian_time().timestamp())}',
            'form_id': 'test_form',
            'is_test': True,
            'created_by': current_user.emp_code
        }),
        'status': 'new',
        'priority': 'high',
        'handler_type': 'unassigned',
        'description': 'Test lead created for Facebook integration testing',
        'created_by_type': 'staff',
        'created_by_id': str(current_user.id)
    }
    
    if data.category_id:
        test_lead_data['category_id'] = data.category_id
    
    crm_lead = CRMLead(**test_lead_data)
    db.add(crm_lead)
    db.commit()
    db.refresh(crm_lead)
    
    logger.info(f"Test Facebook lead created: {crm_lead.id} by {current_user.emp_code}")
    
    return {
        "success": True,
        "message": "Test lead created successfully",
        "lead_id": crm_lead.id,
        "lead_name": crm_lead.name
    }


# ── List CRM Facebook Leads ───────────────────────────────────────────────────
@router.get("/leads")
async def get_facebook_leads(
    company_id: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get all CRM leads sourced from Facebook Lead Ads."""
    query = db.query(CRMLead).filter(CRMLead.source.in_(['Online - M', 'Facebook Lead Ads', 'Social Media']))
    if company_id:
        query = query.filter(CRMLead.company_id == company_id)
    total = query.count()
    leads = query.order_by(CRMLead.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "success": True,
        "total": total,
        "leads": [lead.to_dict() for lead in leads],
        "has_more": (offset + limit) < total
    }


# ── Bulk Sync Facebook Pages ──────────────────────────────────────────────────
class SyncPagesRequest(BaseModel):
    user_token: str
    company_id: int = 1


@router.post("/sync-pages")
async def sync_facebook_pages(
    data: SyncPagesRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Sync all Facebook Pages from a User Token into database with AES-256-GCM encryption.
    """
    logger.info(f"Page sync triggered by {current_user.emp_code}")
    result = facebook_leads_service.sync_pages_from_user_token(
        user_token=data.user_token,
        db=db,
        company_id=data.company_id
    )
    return result


# ── List Facebook Pages ───────────────────────────────────────────────────────
@router.get("/pages")
async def list_facebook_pages(
    company_id: int = Query(default=1),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all synced Facebook Pages with their subscription status and CRM segment.
    """
    rows = db.execute(sqlt("""
        SELECT page_id, page_name, page_category, crm_segment,
               is_active, leads_subscribed, subscription_error, updated_at
        FROM facebook_pages
        WHERE company_id = :cid
        ORDER BY page_name
    """), {'cid': company_id}).fetchall()

    pages = [{
        'page_id':           r[0],
        'page_name':         r[1],
        'page_category':     r[2],
        'crm_segment':       r[3],
        'is_active':         r[4],
        'leads_subscribed':  r[5],
        'subscription_error':r[6],
        'updated_at':        str(r[7]) if r[7] else None,
    } for r in rows]

    subscribed = sum(1 for p in pages if p['leads_subscribed'])
    return {
        'success': True,
        'total': len(pages),
        'subscribed': subscribed,
        'pages': pages
    }


# ── Update Page Segment ───────────────────────────────────────────────────────
@router.put("/pages/{page_id}/segment")
async def update_page_segment(
    page_id: str,
    body: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Override the CRM segment for a specific Facebook Page."""
    segment = body.get('crm_segment', 'GENERAL')
    db.execute(sqlt(
        "UPDATE facebook_pages SET crm_segment=:seg, updated_at=NOW() WHERE page_id=:pid"
    ), {'seg': segment, 'pid': page_id})
    db.commit()
    return {'success': True, 'page_id': page_id, 'crm_segment': segment}


# ── List / Register Form Routing Mappings ──────────────────────────────────────
@router.get("/forms")
async def list_form_mappings(
    company_id: Optional[int] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all configured Meta Lead Form routing mappings from meta_form_mappings.
    """
    query = "SELECT id, page_id, form_id, form_name, company_id, category_id, crm_segment, segment_tag, looking_for, is_active, updated_at FROM meta_form_mappings"
    params = {}
    if company_id:
        query += " WHERE company_id = :cid"
        params['cid'] = company_id
    query += " ORDER BY id ASC"

    rows = db.execute(sqlt(query), params).fetchall()
    mappings = [{
        'id': r[0],
        'page_id': r[1],
        'form_id': r[2],
        'form_name': r[3],
        'company_id': r[4],
        'category_id': r[5],
        'crm_segment': r[6],
        'segment_tag': r[7],
        'looking_for': r[8],
        'is_active': r[9],
        'updated_at': str(r[10]) if r[10] else None
    } for r in rows]
    return {'success': True, 'total': len(mappings), 'mappings': mappings}


@router.post("/forms/map")
async def map_meta_form(
    data: FormMappingRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Register or update a Meta Lead Form routing mapping dynamically without code changes.
    """
    res = facebook_leads_service.register_or_update_form_mapping(
        db=db,
        page_id=data.page_id,
        form_id=data.form_id,
        company_id=data.company_id,
        category_id=data.category_id,
        form_name=data.form_name,
        crm_segment=data.crm_segment,
        segment_tag=data.segment_tag,
        looking_for=data.looking_for,
        is_active=data.is_active
    )
    return res


# ── Manual Pull / Historical Backfill ─────────────────────────────────────────
@router.post("/pull-leads")
async def pull_meta_leads(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Manually pull/sync leads from Meta Graph API v24.0 for all active pages and leadgen forms.
    Uses cursor pagination, exponential backoff, and atomic CRMLead + MetaLeadsAttribution commits.
    """
    from app.core.security_encryption import decrypt_credential_safe

    pages = db.execute(sqlt(
        "SELECT page_id, page_name, access_token, crm_segment, company_id FROM facebook_pages WHERE is_active = True AND access_token IS NOT NULL AND access_token != ''"
    )).fetchall()

    ingested_count = 0
    skipped_count = 0
    errors = []

    for p in pages:
        page_id, page_name, enc_token, segment, page_cid = p[0], p[1], p[2], p[3], p[4]
        token = decrypt_credential_safe(enc_token)
        if not token:
            continue

        # 1. Fetch leadgen forms with Graph API v24.0
        forms_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/leadgen_forms"
        forms_data = facebook_leads_service._execute_graph_api_request(
            forms_url,
            params={'access_token': token, 'fields': 'id,name,status', 'limit': 100},
            timeout=15
        )
        if not forms_data:
            errors.append(f"Page {page_name} ({page_id}): Failed to fetch leadgen forms.")
            continue

        forms = forms_data.get('data', [])
        for f in forms:
            f_id = f.get('id')
            f_name = f.get('name')

            # 2. Fetch leads with cursor pagination
            leads_data = facebook_leads_service.fetch_form_leads(
                form_id=str(f_id),
                access_token=token,
                max_leads=500
            )

            for ld in leads_data:
                lead_id = str(ld.get('id', ''))
                if not lead_id:
                    continue

                if facebook_leads_service.lead_already_exists(lead_id, db):
                    skipped_count += 1
                    continue

                try:
                    crm_data = facebook_leads_service.map_to_crm_lead(
                        lead_data=ld,
                        company_id=page_cid or 1,
                        category_id=None,
                        page_segment=segment,
                        page_name=page_name,
                        form_id=str(f_id),
                        page_id=str(page_id),
                        db=db
                    )
                    if not crm_data:
                        continue

                    # Atomic single-commit insertion
                    crm_lead = CRMLead(**crm_data)
                    db.add(crm_lead)
                    db.flush()

                    attribution = MetaLeadsAttribution(
                        company_id=crm_lead.company_id,  # 🔒 Authoritative company identity
                        lead_id=crm_lead.id,
                        meta_lead_id=lead_id,
                        meta_campaign_id=str(ld.get('campaign_id') or '') or None,
                        meta_adset_id=str(ld.get('adset_id') or '') or None,
                        meta_ad_id=str(ld.get('ad_id') or '') or None,
                        meta_form_id=str(f_id),
                        meta_form_name=str(f_name)
                    )
                    db.add(attribution)
                    db.commit()
                    db.refresh(crm_lead)

                    # Post-commit triggers
                    try:
                        from app.services.whatsapp_auto_service import send_lead_welcome
                        if crm_lead.phone:
                            send_lead_welcome(
                                db=db,
                                phone=crm_lead.phone,
                                lead_name=crm_lead.name,
                                lead_id=crm_lead.id
                            )
                    except Exception as wa_err:
                        logger.warning(f"Pull welcome WhatsApp trigger exception for lead {crm_lead.id}: {wa_err}")

                    ingested_count += 1

                except IntegrityError as ie:
                    db.rollback()
                    logger.info(f"Duplicate Meta lead {lead_id} caught by unique constraint during pull: {ie}")
                    skipped_count += 1
                except Exception as ex:
                    db.rollback()
                    logger.exception(f"Error ingesting lead {lead_id} during pull: {ex}")
                    errors.append(f"Lead {lead_id}: {str(ex)}")

    return {
        "success": True,
        "ingested_count": ingested_count,
        "skipped_count": skipped_count,
        "errors": errors if errors else None,
        "message": f"Successfully pulled {ingested_count} new Meta lead submissions ({skipped_count} duplicates skipped)."
    }
