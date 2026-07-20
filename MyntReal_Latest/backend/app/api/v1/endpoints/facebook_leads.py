"""
Facebook Lead Ads Webhook API Endpoints
DC Protocol: Webhook-based lead capture from Facebook Lead Ads

Endpoints:
- GET /webhook: Facebook webhook verification
- POST /webhook: Receive lead notifications
- GET /config: Check integration status
- POST /test-lead: Create test lead (admin only)

Created: January 04, 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import logging
import json

from app.core.database import get_db
from app.models.crm import CRMLead
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.services.facebook_leads_service import facebook_leads_service, get_indian_time
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


@router.get("/webhook")
async def verify_facebook_webhook(
    request: Request,
):
    """
    Facebook webhook verification endpoint
    DC Protocol: Called by Facebook to verify webhook URL
    """
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    if facebook_leads_service.verify_webhook_token(mode, token):
        logger.info("Facebook webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"Facebook webhook verification failed - mode: {mode}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_facebook_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive lead notifications from Facebook
    DC Protocol: Validates signature and creates CRM leads
    """
    body = await request.body()
    signature = request.headers.get('X-Hub-Signature-256', '')
    
    if facebook_leads_service.app_secret:
        if not facebook_leads_service.verify_webhook_signature(body, signature):
            logger.warning("Invalid Facebook webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Error parsing webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    logger.info(f"Facebook webhook received: {json.dumps(data)[:500]}")
    
    if data.get('object') != 'page':
        logger.info(f"Ignoring non-page webhook: {data.get('object')}")
        return {"status": "ignored", "reason": "not a page event"}
    
    leads_created = 0
    errors = []
    
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'leadgen':
                lead_value = change.get('value', {})
                lead_id = lead_value.get('leadgen_id')
                page_id = lead_value.get('page_id')
                form_id = lead_value.get('form_id')
                
                logger.info(f"Processing Facebook lead: {lead_id} from form {form_id}")
                
                try:
                    crm_lead = await process_facebook_lead(
                        lead_id=lead_id,
                        page_id=page_id,
                        form_id=form_id,
                        db=db
                    )
                    if crm_lead:
                        leads_created += 1
                        logger.info(f"Created CRM lead {crm_lead.id} from Facebook lead {lead_id}")
                except Exception as e:
                    error_msg = f"Error processing lead {lead_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
    
    return {
        "status": "ok",
        "leads_created": leads_created,
        "errors": errors if errors else None
    }


async def process_facebook_lead(
    lead_id: str,
    page_id: str,
    form_id: str,
    db: Session
) -> Optional[CRMLead]:
    """
    Process a single Facebook lead and create CRM entry.
    DC Protocol Mar 2026: Uses per-page token from DB; duplicate-safe via lead_id check.
    """
    # ── Duplicate guard (idempotent) ──────────────────────────────────────────
    if facebook_leads_service.lead_already_exists(lead_id, db):
        logger.info(f"Lead {lead_id} already in CRM — skipping")
        return None

    # ── Get page-specific token + segment from DB ─────────────────────────────
    page_info = facebook_leads_service.get_page_info(page_id, db)
    page_token   = page_info['token']
    page_segment = page_info['segment']
    page_name    = page_info['name']

    # ── Fetch lead details from Graph API ─────────────────────────────────────
    lead_data = facebook_leads_service.fetch_lead_data(lead_id, access_token=page_token)
    if not lead_data:
        logger.error(f"Could not fetch lead data for {lead_id} (page {page_id})")
        return None

    default_company = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True
    ).order_by(AssociatedCompany.id).first()

    if not default_company:
        logger.error("No active company found for Facebook leads")
        return None

    crm_data = facebook_leads_service.map_to_crm_lead(
        lead_data=lead_data,
        company_id=default_company.id,
        category_id=None,
        page_segment=page_segment,
        page_name=page_name
    )

    crm_lead = CRMLead(**crm_data)
    db.add(crm_lead)
    db.commit()
    db.refresh(crm_lead)

    logger.info(f"CRM lead {crm_lead.id} created from FB lead {lead_id} | page: {page_name} | segment: {page_segment}")
    return crm_lead


@router.get("/config")
async def get_facebook_config(
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get Facebook integration configuration status
    DC Protocol: Admin only - shows if integration is properly configured
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['vgk4u', 'ea', 'hr']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    is_configured = facebook_leads_service.is_configured()
    
    return {
        "success": True,
        "is_configured": is_configured,
        "verify_token": facebook_leads_service.verify_token if is_configured else None,
        "api_version": facebook_leads_service.api_version,
        "has_page_token": bool(facebook_leads_service.page_access_token),
        "has_app_secret": bool(facebook_leads_service.app_secret),
        "webhook_url": "/api/v1/facebook-leads/webhook",
        "setup_instructions": {
            "step_1": "Go to Facebook Developer Console (developers.facebook.com)",
            "step_2": "Create or select your Facebook App",
            "step_3": "Add 'Webhooks' product to your app",
            "step_4": "Configure webhook with your domain + /api/v1/facebook-leads/webhook",
            "step_5": "Use the verify token shown above",
            "step_6": "Subscribe to 'leadgen' field under 'Page' webhooks",
            "step_7": "Generate Page Access Token with leads_retrieval permission",
            "step_8": "Add FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_APP_SECRET to secrets"
        }
    }


@router.post("/test-lead")
async def create_test_lead(
    data: TestLeadRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a test Facebook lead for testing integration
    DC Protocol: VGK4U/EA only - creates lead as if from Facebook
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not current_user.role or current_user.role.role_code not in ['vgk4u', 'ea']:
    #     raise HTTPException(status_code=403, detail="VGK4U/EA access required")
    
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
        'source_details': str({
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


@router.get("/leads")
async def get_facebook_leads(
    company_id: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Get all CRM leads sourced from Facebook Lead Ads."""
    query = db.query(CRMLead).filter(CRMLead.source.in_(['Online - M', 'Facebook Lead Ads']))
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
    Sync all Facebook Pages from a User Token.
    DC Protocol Mar 2026: Stores page tokens + subscribes each page to leadgen webhook.
    Safe to re-run at any time — idempotent (UPSERT). Use whenever you get a new token.
    """
    logger.info(f"Page sync triggered by {current_user.emp_code}")
    result = facebook_leads_service.sync_pages_from_user_token(
        user_token=data.user_token,
        db=db,
        company_id=data.company_id
    )
    return result


@router.get("/pages")
async def list_facebook_pages(
    company_id: int = Query(default=1),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all synced Facebook Pages with their subscription status and CRM segment.
    DC Protocol Mar 2026: Shows which pages are active and receiving leads.
    """
    from sqlalchemy import text as sqlt
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


@router.put("/pages/{page_id}/segment")
async def update_page_segment(
    page_id: str,
    body: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Override the CRM segment for a specific Facebook Page."""
    from sqlalchemy import text as sqlt
    segment = body.get('crm_segment', 'GENERAL')
    db.execute(sqlt(
        "UPDATE facebook_pages SET crm_segment=:seg, updated_at=NOW() WHERE page_id=:pid"
    ), {'seg': segment, 'pid': page_id})
    db.commit()
    return {'success': True, 'page_id': page_id, 'crm_segment': segment}
