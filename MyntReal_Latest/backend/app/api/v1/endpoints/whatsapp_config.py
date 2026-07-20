"""
WhatsApp Configuration Center API
Endpoints for template management, auto-trigger config, test sends,
bulk campaigns, message history, and CRM lead send.
Access: VGK4u (vgk4u_supreme) + Key Leadership (key_leadership) + EA (ea role)
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_hybrid, get_current_staff_user_from_hybrid

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Access gate ────────────────────────────────────────────────────────────────
WHATSAPP_CONFIG_ROLES = {"vgk4u", "key_leadership", "ea", "leadership_role"}
WHATSAPP_SEND_ROLES = {"vgk4u", "key_leadership", "ea", "leadership_role", "sales", "team_leader", "senior_executive", "manager"}


def _get_role_code(staff) -> Optional[str]:
    """Safely extract role_code from StaffEmployee (role is a relationship, not a column)."""
    if not staff:
        return None
    role_obj = getattr(staff, 'role', None)
    if role_obj:
        return getattr(role_obj, 'role_code', None)
    return getattr(staff, 'role_code', None)


async def require_wa_config(
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = await get_current_user_hybrid(request, db)
    staff = get_current_staff_user_from_hybrid(current_user, db)
    role = _get_role_code(staff)
    if role not in WHATSAPP_CONFIG_ROLES:
        raise HTTPException(status_code=403, detail="WhatsApp Config access restricted")
    return current_user


async def require_wa_send(
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = await get_current_user_hybrid(request, db)
    staff = get_current_staff_user_from_hybrid(current_user, db)
    role = _get_role_code(staff)
    if role not in WHATSAPP_SEND_ROLES:
        raise HTTPException(status_code=403, detail="WhatsApp Send access restricted")
    return current_user


def _get_staff_id(user) -> Optional[int]:
    return getattr(user, 'staff_id', None) or getattr(user, 'id', None)


# ── Single source of truth: segment → variable → default example value ─────────
# Used at template creation/update time to auto-seed example_values.
# Any variable key not present here is "unknown" and must be provided explicitly.
WA_SEGMENT_DEFAULTS: dict = {
    "vgk": {
        "1": "Rahul Sharma", "2": "VGK07012345",
        "3": "Welcome@VGK1", "4": "500", "5": "https://vgk4u.com/vgk/login",
        "name": "Rahul Sharma", "member_id": "VGK07012345",
        "Password": "Welcome@VGK1", "password": "Welcome@VGK1",
        "points balance": "500", "points_balance": "500",
        "login_url": "https://vgk4u.com/vgk/login",
    },
    "general": {
        "1": "Rahul Sharma", "2": "VGK07012345",
        "3": "https://vgk4u.com/vgk/login", "4": "10,000",
        "name": "Rahul Kumar", "partner_phone": "+91 98765 43210", "otp": "123456",
    },
    "system": {
        "name": "Rahul Kumar", "ticket_id": "TKT2001", "status": "In Progress",
        "po_number": "PO-2025-001", "pending_count": "5", "meetings": "3", "1": "123456",
    },
    "ev_b2b":      {"name": "Business Owner", "1": "Business Owner"},
    "ev_b2c":      {"name": "Rahul Kumar",    "1": "Rahul Kumar"},
    "real_estate": {"name": "Rahul Kumar",    "1": "Rahul Kumar"},
    "etc_training":{"name": "Rahul Kumar",    "1": "Rahul Kumar"},
}


def _derive_example_values(body_text: str, segment: str,
                            provided: Optional[list] = None) -> tuple[list, list]:
    """
    Extract {{vars}} from body_text in order, fill from:
      1. provided list (if given), else
      2. WA_SEGMENT_DEFAULTS for the segment.
    Returns (example_values_list, missing_var_keys_list).
    missing_var_keys_list contains variable keys that had no default and no provided value.
    """
    seen: set = set()
    vars_in_order: list = []
    for m in re.finditer(r'\{\{([a-zA-Z_][a-zA-Z0-9_ ]*|\d+)\}\}', body_text or ''):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            vars_in_order.append(v)

    if not vars_in_order:
        return [], []

    defaults = WA_SEGMENT_DEFAULTS.get(segment or "general", WA_SEGMENT_DEFAULTS.get("general", {}))
    examples: list = []
    missing: list = []

    # Build a case-insensitive lookup for defaults so {{PASSWORD}} matches 'Password'
    defaults_ci = {k.lower(): val for k, val in defaults.items()}

    for i, v in enumerate(vars_in_order):
        # Priority 1: explicitly provided list
        if provided and i < len(provided) and str(provided[i]).strip():
            examples.append(str(provided[i]))
        # Priority 2: segment defaults — exact match first, then case-insensitive
        elif v in defaults:
            examples.append(defaults[v])
        elif v.lower() in defaults_ci:
            examples.append(defaults_ci[v.lower()])
        else:
            examples.append("")
            missing.append(v)

    return examples, missing


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class TemplateCreateSchema(BaseModel):
    name: str
    slug: Optional[str] = None
    segment: str = "general"
    template_type: str = "custom"
    header_type: str = "none"
    header_text: Optional[str] = None
    header_media_url: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None
    buttons: Optional[list] = []
    meta_template_name: Optional[str] = None
    meta_template_language: Optional[str] = "en"
    is_meta_approved: Optional[bool] = False
    is_active: Optional[bool] = True
    usage_scope: Optional[str] = "both"  # 'meta', 'internal', 'both'
    example_values: Optional[List[str]] = None


class TemplateUpdateSchema(BaseModel):
    name: Optional[str] = None
    segment: Optional[str] = None
    template_type: Optional[str] = None
    header_type: Optional[str] = None
    header_text: Optional[str] = None
    header_media_url: Optional[str] = None
    body_text: Optional[str] = None
    footer_text: Optional[str] = None
    buttons: Optional[list] = None
    meta_template_name: Optional[str] = None
    meta_template_language: Optional[str] = None
    is_meta_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    usage_scope: Optional[str] = None  # 'meta', 'internal', 'both'
    example_values: Optional[List[str]] = None


class TriggerUpdateSchema(BaseModel):
    template_id: Optional[int] = None
    is_enabled: bool
    recipient_type: Optional[str] = "customer"
    delay_minutes: Optional[int] = 0


class TestSendSchema(BaseModel):
    phone: str
    template_id: Optional[int] = None
    custom_message: Optional[str] = None
    lead_id: Optional[int] = None
    context_vars: Optional[dict] = {}
    send_type: Optional[str] = "meta"   # "meta" | "text" | "both"


class DirectLeadSendSchema(BaseModel):
    phone: str
    template_id: Optional[int] = None
    custom_message: Optional[str] = None
    context_vars: Optional[dict] = {}
    variable_values: Optional[Dict[str, str]] = {}   # positional {{1}},{{2}} from frontend fill-in
    send_mode: Optional[str] = 'company'             # 'company' | 'direct'


class DirectLogSchema(BaseModel):
    phone: str
    message_preview: Optional[str] = None
    message_body: Optional[str] = None
    template_id: Optional[int] = None


class CampaignCreateSchema(BaseModel):
    name: str
    template_id: int
    filters: dict = {}
    notes: Optional[str] = None
    daily_limit: Optional[int] = 1000
    sends_per_minute: Optional[int] = 50


# ── TEMPLATES ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(
    segment: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    from app.models.whatsapp import WhatsAppTemplate
    q = db.query(WhatsAppTemplate)
    if segment:
        q = q.filter_by(segment=segment)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    templates = q.order_by(WhatsAppTemplate.segment, WhatsAppTemplate.name).all()
    return {"success": True, "templates": [t.to_dict() for t in templates]}


@router.get("/templates/approved")
async def list_approved_templates(
    segment: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """DC-WA-TRACK-001: Returns Meta-APPROVED templates for CRM WA send modal."""
    from app.models.whatsapp import WhatsAppTemplate
    q = db.query(WhatsAppTemplate).filter(
        WhatsAppTemplate.is_active == True,
        WhatsAppTemplate.meta_approval_status == 'APPROVED'
    )
    if segment:
        q = q.filter(WhatsAppTemplate.segment == segment)
    if category:
        q = q.filter(WhatsAppTemplate.meta_category == category.upper())
    templates = q.order_by(WhatsAppTemplate.segment, WhatsAppTemplate.name).all()
    return {"success": True, "templates": [t.to_dict() for t in templates], "total": len(templates)}


@router.post("/track/generate")
def generate_tracking_link(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """DC-WA-TRACK-001: Create a trackable redirect link. Returns tracking URL."""
    import secrets
    from sqlalchemy import text as _t
    target_url = (payload.get("url") or "").strip()
    if not target_url or not target_url.startswith("http"):
        raise HTTPException(400, "Valid URL required")
    token = secrets.token_urlsafe(24)
    db.execute(_t("""
        INSERT INTO wa_link_tracks (token, target_url, title, lead_id, staff_id, source_type)
        VALUES (:token, :url, :title, :lead_id, :staff_id, :src)
    """), {
        "token": token, "url": target_url,
        "title": payload.get("title") or None,
        "lead_id": payload.get("lead_id") or None,
        "staff_id": _get_staff_id(current_user),
        "src": payload.get("source_type") or "crm_wa",
    })
    db.commit()
    base = payload.get("base_url") or "https://mnrteam.com"
    return {"success": True, "token": token, "tracking_url": f"{base}/api/v1/wa-redirect/{token}"}


@router.get("/track/{token}/stats")
def get_track_stats(
    token: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """DC-WA-TRACK-001: View click stats for a tracking token."""
    from sqlalchemy import text as _t
    row = db.execute(_t(
        "SELECT token, title, target_url, click_count, first_clicked_at, last_clicked_at, created_at FROM wa_link_tracks WHERE token=:t"
    ), {"t": token}).fetchone()
    if not row:
        raise HTTPException(404, "Tracking token not found")
    return {"success": True, "stats": {
        "token": row[0], "title": row[1], "target_url": row[2],
        "click_count": row[3], "first_clicked_at": str(row[4]) if row[4] else None,
        "last_clicked_at": str(row[5]) if row[5] else None, "created_at": str(row[6]),
    }}


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    from app.models.whatsapp import WhatsAppTemplate
    t = db.query(WhatsAppTemplate).get(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return {"success": True, "template": t.to_dict()}


@router.post("/templates")
def create_template(
    data: TemplateCreateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppTemplate
    slug = data.slug or re.sub(r'[^a-z0-9_]', '_', data.name.lower().strip())[:100]
    # Ensure uniqueness
    existing = db.query(WhatsAppTemplate).filter_by(slug=slug).first()
    if existing:
        slug = f"{slug}_{int(datetime.utcnow().timestamp())}"

    # Auto-derive example_values from segment defaults + any provided values
    derived_examples, missing_vars = _derive_example_values(
        data.body_text, data.segment or "general", data.example_values
    )
    final_examples = derived_examples if derived_examples else (data.example_values or None)

    t = WhatsAppTemplate(
        name=data.name, slug=slug, segment=data.segment,
        template_type=data.template_type, header_type=data.header_type,
        header_text=data.header_text, header_media_url=data.header_media_url,
        body_text=data.body_text, footer_text=data.footer_text,
        buttons=data.buttons or [], meta_template_name=data.meta_template_name,
        meta_template_language=data.meta_template_language or "en",
        is_meta_approved=data.is_meta_approved or False,
        is_active=data.is_active if data.is_active is not None else True,
        usage_scope=data.usage_scope or 'both',
        example_values=final_examples,
        created_by_staff_id=_get_staff_id(current_user),
        updated_by_staff_id=_get_staff_id(current_user),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    resp = {"success": True, "template": t.to_dict()}
    if missing_vars:
        resp["missing_examples"] = missing_vars
        resp["warning"] = f"No default examples for: {', '.join('{{'+v+'}}'  for v in missing_vars)}. Please add them manually."
    return resp


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    data: TemplateUpdateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppTemplate
    t = db.query(WhatsAppTemplate).get(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    if t.is_system:
        raise HTTPException(403, "System templates cannot be modified")

    update_data = data.dict(exclude_none=True)
    for field, val in update_data.items():
        setattr(t, field, val)

    # Re-derive example_values if body_text or segment changed
    body = update_data.get("body_text", t.body_text)
    segment = update_data.get("segment", t.segment) or "general"
    provided = update_data.get("example_values", t.example_values)
    derived, missing_vars = _derive_example_values(body, segment, provided)
    if derived:
        t.example_values = derived

    t.updated_by_staff_id = _get_staff_id(current_user)
    t.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    resp = {"success": True, "template": t.to_dict()}
    if missing_vars:
        resp["missing_examples"] = missing_vars
        resp["warning"] = f"No default examples for: {', '.join('{{'+v+'}}'  for v in missing_vars)}. Please add them manually."
    return resp


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppTemplate
    t = db.query(WhatsAppTemplate).get(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    if t.is_system:
        raise HTTPException(403, "System templates cannot be deleted")
    db.delete(t)
    db.commit()
    return {"success": True, "message": "Template deleted"}


# ── META TEMPLATE SYNC ────────────────────────────────────────────────────────

@router.get("/meta-templates/fetch")
def fetch_meta_templates(
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    """
    Fetch all approved message templates directly from Meta WhatsApp Business API.
    Uses the stored WABA (Business Account) ID and access token.
    """
    import os as _os
    import requests as _req
    from app.services.wa_credentials import get_wa_credentials

    creds = get_wa_credentials(db)
    access_token = (creds.get("access_token") or "").strip() or _os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    waba_id = (creds.get("business_account_id") or "").strip() or _os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="WhatsApp access token not configured. Go to API Credentials tab.")
    if not waba_id:
        raise HTTPException(status_code=400, detail="WhatsApp Business Account ID (WABA ID) not configured. Go to API Credentials tab.")

    try:
        url = f"https://graph.facebook.com/v21.0/{waba_id}/message_templates"
        resp = _req.get(url, params={
            "limit": 200,
            "fields": "name,status,language,category,components"
        }, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except _req.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Meta API error: {detail or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Meta API: {str(e)}")

    all_tpls = raw.get("data", [])
    approved = []
    for t in all_tpls:
        body_text = ""
        for comp in (t.get("components") or []):
            if comp.get("type") == "BODY":
                body_text = comp.get("text", "")
                break
        approved.append({
            "name": t.get("name"),
            "status": t.get("status"),
            "language": t.get("language"),
            "category": t.get("category"),
            "body_preview": body_text[:120] + ("…" if len(body_text) > 120 else ""),
        })

    approved.sort(key=lambda x: (0 if x["status"] == "APPROVED" else 1, x["name"] or ""))
    return {"success": True, "templates": approved, "total": len(all_tpls)}


class MetaTemplateLinkSchema(BaseModel):
    meta_template_name: str
    meta_template_language: str = "en"
    myntreal_template_id: Optional[int] = None


@router.post("/meta-templates/link")
def link_meta_template(
    data: MetaTemplateLinkSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    """
    Link a Meta-approved template name to an existing MyntReal template.
    Sets meta_template_name, meta_template_language, is_meta_approved=True.
    """
    from app.models.whatsapp import WhatsAppTemplate
    if not data.myntreal_template_id:
        raise HTTPException(status_code=400, detail="myntreal_template_id is required")
    tpl = db.query(WhatsAppTemplate).get(data.myntreal_template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="MyntReal template not found")
    tpl.meta_template_name = data.meta_template_name.strip()
    tpl.meta_template_language = data.meta_template_language or "en"
    tpl.is_meta_approved = True
    tpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tpl)
    return {"success": True, "template": tpl.to_dict()}


# ── DC-WA-META-SUBMIT-001: AI DRAFT + META SUBMIT + STATUS SYNC ───────────────

class AIDraftRequest(BaseModel):
    brief: str
    category: str = "MARKETING"
    tone: str = "friendly_professional"
    language: str = "en"


@router.post("/media-upload")
async def upload_wa_media(
    file: UploadFile = File(...),
    current_user=Depends(require_wa_config),
):
    """DC-WA-MEDIA-001: Upload image/video/PDF for use as WhatsApp template header. Returns public URL."""
    import uuid, shutil
    from pathlib import Path

    ALLOWED = {
        "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
        "image/gif": "gif", "image/webp": "webp",
        "video/mp4": "mp4", "video/mpeg": "mp4",
        "application/pdf": "pdf",
    }
    MAX_SIZES = {
        "jpg": 5 * 1024 * 1024,   # 5 MB
        "jpeg": 5 * 1024 * 1024,
        "png": 5 * 1024 * 1024,
        "gif": 5 * 1024 * 1024,
        "webp": 5 * 1024 * 1024,
        "mp4": 16 * 1024 * 1024,  # 16 MB
        "pdf": 100 * 1024 * 1024, # 100 MB
    }

    ct = (file.content_type or "").lower()
    # Fallback: detect by extension when content_type is generic
    if ct not in ALLOWED and file.filename:
        ext_guess = file.filename.rsplit(".", 1)[-1].lower()
        ct_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                  "gif": "image/gif", "webp": "image/webp",
                  "mp4": "video/mp4", "pdf": "application/pdf"}
        ct = ct_map.get(ext_guess, ct)

    if ct not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ct}'. Allowed: JPG, PNG, GIF, WebP, MP4, PDF."
        )

    ext = ALLOWED[ct]
    data = await file.read()
    size = len(data)
    max_size = MAX_SIZES.get(ext, 5 * 1024 * 1024)
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size // 1024} KB). Max for {ext.upper()}: {max_size // 1024 // 1024} MB."
        )

    # ── Try Object Storage first ────────────────────────────────────────────
    filename = f"{uuid.uuid4().hex}.{ext}"
    storage_path = f"wa_media/{filename}"
    public_url: str | None = None

    try:
        from app.services.object_storage import storage_service
        ok = storage_service.upload_file(storage_path, data)
        if ok:
            public_url = f"/storage/{storage_path}"
    except Exception:
        ok = False

    # ── Fallback: local storage ─────────────────────────────────────────────
    if not public_url:
        local_dir = Path(__file__).parent.parent.parent.parent.parent / "frontend" / "storage" / "wa_media"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / filename
        local_file.write_bytes(data)
        public_url = f"/storage/{storage_path}"

    # ── Upload to Meta's Resumable Upload API (DC-WA-MEDIA-001) ────────────
    # Meta's servers can't reach Replit dev domain — upload to Meta directly
    # and use the returned handle in template submission instead of a URL.
    meta_handle: str | None = None
    meta_error: str | None = None
    try:
        import httpx as _hx
        from app.services.wa_credentials import get_wa_credentials
        from app.core.database import SessionLocal as _SL
        _db2 = _SL()
        try:
            _creds = get_wa_credentials(_db2)
        finally:
            _db2.close()
        _token = (_creds.get("access_token") or "").strip() or __import__("os").environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
        # DC-WA-MEDIA-002: Use stored Facebook App ID (most reliable)
        _app_id = (_creds.get("facebook_app_id") or "").strip() or __import__("os").environ.get("META_FACEBOOK_APP_ID", "")
        if _token:
            if not _app_id:
                meta_error = ("Facebook App ID not configured. "
                              "Go to API Credentials tab → enter your Facebook App ID "
                              "(found in Meta for Developers → Your App → Settings → Basic → App ID).")
            if _app_id:
                async with _hx.AsyncClient(timeout=30) as _cli:
                    # Step 2: create upload session
                    _sess_r = await _cli.post(
                        f"https://graph.facebook.com/v21.0/{_app_id}/uploads",
                        params={
                            "file_name": filename,
                            "file_length": str(size),
                            "file_type": ct,
                            "upload_type": "attachment",
                            "access_token": _token,
                        },
                    )
                    _sess_id = _sess_r.json().get("id") if _sess_r.is_success else None

                    if _sess_id:
                        # Step 3: upload file bytes
                        _up_r = await _cli.post(
                            f"https://graph.facebook.com/v21.0/{_sess_id}",
                            content=data,
                            headers={
                                "Authorization": f"OAuth {_token}",
                                "file_offset": "0",
                                "Content-Type": ct,
                            },
                        )
                        if _up_r.is_success:
                            meta_handle = _up_r.json().get("h")
                        else:
                            meta_error = _up_r.text[:200]
                    else:
                        meta_error = f"Session create failed: {_sess_r.text[:200]}"
        else:
            meta_error = "No Meta access token configured"
    except Exception as _me_ex:
        meta_error = str(_me_ex)[:200]

    return {
        "url": public_url,
        "filename": filename,
        "size_kb": round(size / 1024, 1),
        "type": ext.upper(),
        "meta_handle": meta_handle,          # use this in template submission — 100% accessible
        "meta_upload_error": meta_error,     # shown in UI if handle retrieval failed
    }


@router.get("/templates/ai-draft/status")
def ai_draft_status(current_user=Depends(require_wa_config)):
    """Check whether the AI draft assistant is available (Google Gemini key configured)."""
    import os
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    return {
        "available": bool(key),
        "message": "" if key else "AI Draft is not available — the Google API key has not been configured. Type your message manually in the body field.",
    }


@router.post("/templates/ai-draft")
def ai_draft_template(
    data: AIDraftRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config),
):
    """DC-WA-META-SUBMIT-001: Gemini 2.0 Flash drafts a Meta-ready WA template from a brief."""
    import os, httpx, json as _json
    google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not google_key:
        raise HTTPException(status_code=400, detail="Google API key not configured. Ask your admin to set GOOGLE_API_KEY.")

    # Separate instruction from template body if brief contains "Rewrite/improve" prefix
    import re as _re_ai
    raw_brief = data.brief.strip()
    _modify_match = _re_ai.match(
        r'^(?:Rewrite/improve this message:\s*)(.+?)(?:\n\s*\n)([\s\S]+)$',
        raw_brief, _re_ai.IGNORECASE | _re_ai.DOTALL
    )
    if _modify_match:
        _instruction = _modify_match.group(1).strip()
        _existing_body = _modify_match.group(2).strip()
        task_block = (
            f"EXISTING TEMPLATE TO MODIFY:\n{_existing_body}\n\n"
            f"MODIFICATION INSTRUCTION: {_instruction}\n\n"
            f"Apply the instruction to the existing template. Keep all content that was not mentioned "
            f"in the instruction. Convert any {{{{name}}}}-style variables to positional {{{{1}}}}, {{{{2}}}}... format."
        )
    else:
        task_block = f"CREATE A NEW TEMPLATE FOR: {raw_brief}"

    prompt = f"""You are a Meta WhatsApp Business API template writer for an Indian business.

{task_block}

CATEGORY: {data.category}
TONE: {data.tone}
LANGUAGE: {data.language}

Rules:
- Use {{{{1}}}}, {{{{2}}}}, {{{{3}}}} for dynamic values (NOT {{{{name}}}} or %name%)
- WhatsApp formatting: *bold*, _italic_ — no HTML
- Max body 1024 chars; header max 60 chars; footer max 60 chars
- No banned content (no lotteries, medical claims, threats)
- Variables must match Meta's positional format exactly
- No raw URLs in body text — use a {{{{N}}}} variable for URLs

Return ONLY valid JSON (no markdown, no extra text):
{{
  "template_name": "snake_case_name_max_60_chars",
  "body_text": "body with {{{{1}}}}, {{{{2}}}} etc.",
  "footer_text": "optional footer or empty string",
  "header_text": "optional header or empty string",
  "placeholders": {{"1": "what variable 1 represents", "2": "what variable 2 represents"}},
  "example_values": ["actual sample value for 1", "actual sample value for 2"],
  "suggestions": "brief note for editor"
}}

IMPORTANT for example_values: provide REAL sample data — e.g. a person's name like "Rahul Kumar", a member ID like "VGK070001", a password like "Welcome@VGK1", a rupee amount like "₹500", a URL like "https://vgk4u.com/login". These are shown to Meta as proof the template works. Do NOT use placeholder descriptions like "Customer Name" — use actual realistic values."""

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash"
        f":generateContent?key={google_key}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1300},
    }
    # Network call — separate from response parsing so HTTPException doesn't get swallowed
    try:
        resp = httpx.post(gemini_url, json=payload, timeout=25)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Gemini network error: {str(e)}")

    # Non-200 handling — outside try so raise propagates directly
    if resp.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="AI draft quota exceeded — the Google Gemini API daily limit has been reached. "
                   "Please try again later or ask your admin to check the API quota."
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini API error {resp.status_code}: {resp.text[:300]}")

    # Parse response
    try:
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]
        result = _json.loads(raw.strip())
        return {"success": True, **result}
    except _json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI draft failed: {str(e)}")


def _meta_error_explanation(code, message: str) -> str:
    code_int = int(str(code)) if str(code).lstrip('-').isdigit() else 0
    table = {
        1:       "Generic Meta server error — most commonly caused by: (1) Video/Image header URL is a YouTube/social media link instead of a direct CDN/file URL, (2) Template content violates Meta policies, (3) Account permission issue.",
        192: "Duplicate template — this name already exists in this language in your WABA.",
        100: "Invalid parameter — the request payload has a field Meta doesn't accept.",
        131030: "Template name already in use for this WABA.",
        2388001: "Template name invalid — use only lowercase letters, digits, and underscores.",
        2388053: "Template body too long — max 1024 characters.",
        2388055: "Variable format wrong — must use {{1}}, {{2}} (numbered, not named).",
        2388057: "Header text too long — max 60 characters.",
        2388058: "Footer text too long — max 60 characters.",
        2388023: "Your account is not yet approved for MARKETING templates.",
        2388012: "Invalid language code (e.g. use 'en' or 'en_IN').",
        2388060: "Too many templates submitted recently — Meta has a rate limit. Wait and retry.",
        2388003: "Template category mismatch — body content doesn't match the selected category.",
    }
    if code_int in table:
        return table[code_int]
    msg_l = message.lower()
    if "duplicate" in msg_l or "already exists" in msg_l:
        return "A template with this name already exists in Meta Business Manager."
    if "permission" in msg_l or "oauth" in msg_l:
        return "Your access token lacks permission to create templates. Use a System User permanent token."
    if "limit" in msg_l:
        return "You've hit Meta's template creation rate limit. Wait a few minutes and retry."
    return f"Meta rejected the submission: {message}"


def _meta_error_fix(code, name: str) -> str:
    code_int = int(str(code)) if str(code).lstrip('-').isdigit() else 0
    if code_int == 1:
        return (
            "Most likely cause: your Video/Image header URL is a YouTube or social media link — "
            "Meta requires a direct public URL to the file (e.g. ending in .mp4, .jpg, .png hosted on a CDN). "
            "Remove the header OR replace the URL with a direct CDN link, then re-submit."
        )
    if code_int == 192 or code_int == 131030:
        return f"Try renaming to '{name}_v2' or delete the existing template in Meta Business Manager first."
    if code_int == 2388055:
        return "Use {{1}}, {{2}} format — click 'Draft with AI' to auto-correct."
    if code_int == 2388023:
        return "Try UTILITY category first to build your account standing, then switch to MARKETING."
    if code_int in (2388001, 2388053, 2388057, 2388058):
        return "Shorten the highlighted field and re-submit."
    if code_int == 100:
        return "Template name must be lowercase letters, digits, underscores only — no spaces or special chars."
    if code_int == 2388003:
        return "Ensure your body content matches the selected category (e.g. UTILITY = transactional, not promotional)."
    return "Review the error above, correct your template, and re-submit."


class MetaButtonSchema(BaseModel):
    """One CTA or Quick-Reply button for a WhatsApp template."""
    button_type: str = "url"          # url | quick_reply | phone_number
    text: str                          # button label (max 25 chars)
    url: Optional[str] = None          # required when button_type == 'url'
    phone_number: Optional[str] = None # required when button_type == 'phone_number'
    url_type: str = "static"           # static | dynamic


class MetaSubmitRequest(BaseModel):
    name: str
    category: str = "MARKETING"
    language: str = "en"
    body_text: Optional[str] = None         # not used for AUTHENTICATION
    header_text: Optional[str] = None
    header_type: Optional[str] = None       # text | image | video | document
    header_media_url: Optional[str] = None  # used when header_type is image/video/document
    header_meta_handle: Optional[str] = None  # DC-WA-MEDIA-001: Meta upload handle (preferred over header_url)
    footer_text: Optional[str] = None
    buttons: Optional[List[MetaButtonSchema]] = None  # DC-WA-TRACK-001: CTA buttons
    myntreal_template_id: Optional[int] = None
    example_values: Optional[List[str]] = None
    # AUTHENTICATION-specific
    add_security_recommendation: bool = False
    code_expiration_minutes: Optional[int] = None  # e.g. 5
    otp_type: str = "COPY_CODE"             # COPY_CODE | ONE_TAP | ZERO_TAP


@router.post("/meta-templates/submit")
def submit_to_meta(
    data: MetaSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config),
):
    """DC-WA-META-SUBMIT-001: Create template in Meta BM directly from portal."""
    import os, requests as _req
    from app.services.wa_credentials import get_wa_credentials
    from app.models.whatsapp import WhatsAppTemplate

    creds = get_wa_credentials(db)
    access_token = (creds.get("access_token") or "").strip() or os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    waba_id = (creds.get("business_account_id") or "").strip() or os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="WhatsApp access token not configured — go to API Credentials tab.")
    if not waba_id:
        raise HTTPException(status_code=400, detail="WhatsApp Business Account ID not configured — go to API Credentials tab.")

    name = re.sub(r'[^a-z0-9_]', '_', data.name.strip().lower())[:60]
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required.")

    category_upper = data.category.upper()
    components = []

    if category_upper == "AUTHENTICATION":
        # ── AUTHENTICATION: Meta fixed format — NO custom text body allowed ──────
        # Meta controls the body text ("{{1}} is your verification code.")
        # Body component only accepts add_security_recommendation
        body_comp: dict = {"type": "BODY"}
        if data.add_security_recommendation:
            body_comp["add_security_recommendation"] = True
        components.append(body_comp)

        # Footer for auth = code_expiration_minutes (NOT text)
        if data.code_expiration_minutes and data.code_expiration_minutes > 0:
            components.append({"type": "FOOTER", "code_expiration_minutes": data.code_expiration_minutes})

        # OTP button is required for AUTHENTICATION
        otp_type = data.otp_type or "COPY_CODE"
        components.append({
            "type": "BUTTONS",
            "buttons": [{"type": "OTP", "otp_type": otp_type}],
        })

    else:
        # ── MARKETING / UTILITY: full custom format ───────────────────────────────
        if not data.body_text or not data.body_text.strip():
            raise HTTPException(status_code=400, detail="Message body is required for MARKETING/UTILITY templates.")

        ht = (data.header_type or "").lower().strip()
        if ht == "text" and data.header_text and data.header_text.strip():
            components.append({"type": "HEADER", "format": "TEXT", "text": data.header_text.strip()[:60]})
        elif ht in ("image", "video", "document"):
            fmt_map = {"image": "IMAGE", "video": "VIDEO", "document": "DOCUMENT"}
            _handle = (data.header_meta_handle or "").strip()
            _url = (data.header_media_url or "").strip()
            if _handle:
                # DC-WA-MEDIA-001: Prefer Meta-uploaded handle — 100% accessible by Meta servers
                components.append({
                    "type": "HEADER",
                    "format": fmt_map[ht],
                    "example": {"header_handle": [_handle]},
                })
            elif _url:
                components.append({
                    "type": "HEADER",
                    "format": fmt_map[ht],
                    "example": {"header_url": [_url]},
                })

        # ── Variable normalisation ────────────────────────────────────────────
        # Meta requires POSITIONAL vars {{1}},{{2}} — convert named vars first
        import re as _re
        raw_body = data.body_text.strip()
        named_vars = _re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_ ]*)\}\}', raw_body)
        if named_vars:
            # Replace named vars in order of first appearance → {{1}}, {{2}}, …
            seen: dict = {}
            counter = [0]
            def _replace_named(m):
                vname = m.group(1)
                if vname not in seen:
                    counter[0] += 1
                    seen[vname] = counter[0]
                return f"{{{{{seen[vname]}}}}}"
            raw_body = _re.sub(r'\{\{([a-zA-Z_][a-zA-Z0-9_ ]*)\}\}', _replace_named, raw_body)

        positional_count = len(_re.findall(r'\{\{\d+\}\}', raw_body))
        examples_given = [v for v in (data.example_values or []) if v.strip()]

        if positional_count > 0:
            if not examples_given:
                raise HTTPException(status_code=400, detail=(
                    f"Your message body has {positional_count} variable(s) ({{{{1}}}}, {{{{2}}}}, …). "
                    f"Please provide {positional_count} example value(s) in the 'Example Values' field "
                    f"(comma-separated, one per variable)."
                ))
            if len(examples_given) < positional_count:
                raise HTTPException(status_code=400, detail=(
                    f"Body has {positional_count} variable(s) but only {len(examples_given)} example value(s) provided. "
                    f"Add {positional_count - len(examples_given)} more example value(s)."
                ))
            # Trim extras silently
            examples_given = examples_given[:positional_count]

        body_comp2: dict = {"type": "BODY", "text": raw_body}
        if positional_count > 0 and examples_given:
            body_comp2["example"] = {"body_text": [examples_given]}
        components.append(body_comp2)

        if data.footer_text and data.footer_text.strip():
            components.append({"type": "FOOTER", "text": data.footer_text.strip()[:60]})

        # DC-WA-TRACK-001: CTA / Quick-Reply buttons (up to 10, Meta allows up to 3 URL + 10 QR)
        if data.buttons:
            meta_buttons = []
            for btn in data.buttons[:10]:
                bt = btn.button_type.lower()
                label = btn.text[:25]
                if bt == "url" and btn.url and btn.url.strip():
                    b = {"type": "URL", "text": label, "url": btn.url.strip()}
                    if btn.url_type == "dynamic":
                        b["example"] = [btn.url.strip()]
                    meta_buttons.append(b)
                elif bt == "quick_reply":
                    meta_buttons.append({"type": "QUICK_REPLY", "text": label})
                elif bt == "phone_number" and btn.phone_number:
                    meta_buttons.append({"type": "PHONE_NUMBER", "text": label, "phone_number": btn.phone_number})
            if meta_buttons:
                components.append({"type": "BUTTONS", "buttons": meta_buttons})

    payload = {
        "name": name,
        "language": data.language,
        "category": category_upper,
        "components": components,
    }

    try:
        url = f"https://graph.facebook.com/v21.0/{waba_id}/message_templates"
        resp = _req.post(url, json=payload,
                         headers={"Authorization": f"Bearer {access_token}"}, timeout=60)
        raw = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Meta API: {str(e)}")

    if resp.status_code not in (200, 201):
        err = raw.get("error", {})
        code = err.get("code", 0)
        msg = err.get("message", "Unknown Meta error")
        explanation = _meta_error_explanation(code, msg)
        fix = _meta_error_fix(code, name)
        raise HTTPException(status_code=422, detail={
            "meta_error": True,
            "code": code,
            "message": msg,
            "user_title": err.get("error_user_title", ""),
            "user_msg": err.get("error_user_msg", msg),
            "explanation": explanation,
            "fix_hint": fix,
        })

    meta_id = raw.get("id", "")
    meta_status = raw.get("status", "PENDING")

    # Upsert local template record
    from app.models.whatsapp import WhatsAppTemplate
    tpl = None
    if data.myntreal_template_id:
        tpl = db.query(WhatsAppTemplate).get(data.myntreal_template_id)
    if not tpl:
        tpl = db.query(WhatsAppTemplate).filter(WhatsAppTemplate.meta_template_name == name).first()
    _safe_body = (data.body_text or "").strip() or "{{1}} is your verification code."
    if not tpl:
        slug = name + "_" + str(int(datetime.utcnow().timestamp()))[-6:]
        tpl = WhatsAppTemplate(
            name=name.replace("_", " ").title(),
            slug=slug, body_text=_safe_body,
            footer_text=data.footer_text or "", segment="general",
            template_type="custom", is_system=False, is_active=True,
            created_by_staff_id=_get_staff_id(current_user),
        )
        db.add(tpl)

    tpl.meta_template_name = name
    tpl.meta_template_language = data.language
    tpl.meta_approval_status = meta_status
    tpl.meta_template_id = meta_id
    tpl.meta_category = data.category.upper()
    tpl.meta_submitted_at = datetime.utcnow()
    tpl.is_meta_approved = (meta_status == "APPROVED")
    if data.body_text and data.body_text.strip():
        tpl.body_text = data.body_text.strip()
    if data.header_text:
        tpl.header_text = data.header_text
    if data.footer_text:
        tpl.footer_text = data.footer_text
    if data.example_values:
        tpl.example_values = [v for v in data.example_values if v.strip()]
    tpl.updated_at = datetime.utcnow()
    tpl.updated_by_staff_id = _get_staff_id(current_user)
    db.commit()
    db.refresh(tpl)

    note = ("MARKETING templates typically take 1-5 minutes for Meta to review."
            if data.category.upper() == "MARKETING" else
            "AUTHENTICATION/UTILITY templates are usually approved within seconds.")
    return {
        "success": True,
        "meta_template_id": meta_id,
        "status": meta_status,
        "message": f"✅ Template '{name}' submitted to Meta. Status: {meta_status}.",
        "note": note,
        "template": tpl.to_dict(),
    }


@router.post("/meta-templates/sync-status")
def sync_meta_template_status(
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config),
):
    """DC-WA-META-SUBMIT-001: Fetch all template statuses from Meta, update local DB."""
    import os, requests as _req
    from app.services.wa_credentials import get_wa_credentials
    from app.models.whatsapp import WhatsAppTemplate

    creds = get_wa_credentials(db)
    access_token = (creds.get("access_token") or "").strip() or os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    waba_id = (creds.get("business_account_id") or "").strip() or os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="WhatsApp access token not configured.")
    if not waba_id:
        raise HTTPException(status_code=400, detail="WhatsApp Business Account ID not configured.")

    try:
        url = f"https://graph.facebook.com/v21.0/{waba_id}/message_templates"
        resp = _req.get(url, params={
            "limit": 200,
            "fields": "id,name,status,language,category,components,quality_score,rejected_reason",
        }, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except _req.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Meta API error: {detail or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Meta API: {str(e)}")

    # Build lookup by (name, language) — keyed by lowercase name::lang
    all_meta: dict = {}
    for t in raw.get("data", []):
        key = f"{t.get('name','').lower()}::{t.get('language','en').lower()}"
        all_meta[key] = t

    local_templates = db.query(WhatsAppTemplate).filter(
        WhatsAppTemplate.meta_template_name != None  # noqa
    ).all()

    updated, not_found = [], []
    matched_meta_names: set = set()

    for t in local_templates:
        meta_name = (t.meta_template_name or "").strip().lower()
        lang = (t.meta_template_language or "en").strip().lower()
        key = f"{meta_name}::{lang}"
        meta_t = all_meta.get(key) or all_meta.get(f"{meta_name}::en") or next(
            (v for k, v in all_meta.items() if k.startswith(meta_name + "::")), None
        )
        if meta_t:
            matched_meta_names.add(meta_t.get("name", "").lower())
            old_status = t.meta_approval_status
            new_status = meta_t.get("status", old_status)
            raw_reason = meta_t.get("rejected_reason", "") or ""
            rejected_reason = "" if raw_reason.upper() in ("NONE", "") else raw_reason
            t.meta_approval_status = new_status
            t.meta_template_id = meta_t.get("id") or t.meta_template_id
            t.is_meta_approved = (new_status == "APPROVED")
            t.meta_rejected_reason = rejected_reason or None  # DC-WA-REJECTED-001: persist
            t.updated_at = datetime.utcnow()
            updated.append({
                "id": t.id, "name": t.name,
                "meta_name": t.meta_template_name,
                "old_status": old_status, "new_status": new_status,
                "changed": old_status != new_status,
                "rejected_reason": rejected_reason,
            })
        else:
            not_found.append({
                "id": t.id,
                "name": t.name,
                "meta_name": t.meta_template_name,
                "meta_category": t.meta_category or "",
                "meta_submitted_at": t.meta_submitted_at.isoformat() if t.meta_submitted_at else None,
            })

    # DC-WA-REJECTED-001: Orphan capture — Meta templates with no matching local record
    def _extract_meta_body(meta_t: dict) -> str:
        for comp in meta_t.get("components", []):
            if comp.get("type", "").upper() == "BODY":
                return comp.get("text", "") or ""
        return ""

    orphans_captured = []
    for meta_key, meta_t in all_meta.items():
        meta_name_lower = meta_t.get("name", "").lower()
        if meta_name_lower in matched_meta_names:
            continue
        existing = db.query(WhatsAppTemplate).filter(
            WhatsAppTemplate.meta_template_name == meta_name_lower
        ).first()
        if existing:
            matched_meta_names.add(meta_name_lower)
            continue
        raw_reason = meta_t.get("rejected_reason", "") or ""
        rej_reason = None if raw_reason.upper() in ("NONE", "") else raw_reason
        _body = _extract_meta_body(meta_t) or meta_name_lower.replace("_", " ").title()
        _slug_base = meta_name_lower + "_" + (meta_t.get("language", "en") or "en")
        # Ensure slug uniqueness
        from app.models.whatsapp import WhatsAppTemplate as _WATpl
        slug_exists = db.query(_WATpl).filter(_WATpl.slug == _slug_base).first()
        _slug = _slug_base if not slug_exists else _slug_base + "_meta"
        new_tpl = WhatsAppTemplate(
            name=meta_t.get("name", "").replace("_", " ").title(),
            slug=_slug,
            body_text=_body or "{{1}}",
            segment="general", template_type="custom",
            is_system=False, is_active=True,
            meta_template_name=meta_name_lower,
            meta_template_language=meta_t.get("language", "en"),
            meta_template_id=str(meta_t.get("id", "")) or None,
            meta_approval_status=meta_t.get("status", ""),
            meta_category=meta_t.get("category", ""),
            meta_rejected_reason=rej_reason,
            is_meta_approved=(meta_t.get("status", "") == "APPROVED"),
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db.add(new_tpl)
        orphans_captured.append({"name": meta_t.get("name", ""), "status": meta_t.get("status", "")})
        matched_meta_names.add(meta_name_lower)

    db.commit()
    newly_approved = [u for u in updated if u["new_status"] == "APPROVED" and u.get("changed")]
    return {
        "success": True,
        "total_synced": len(updated),
        "not_found_in_meta": len(not_found),
        "newly_approved": len(newly_approved),
        "orphans_captured": len(orphans_captured),
        "updated": updated,
        "not_found": not_found,
        "message": (
            f"Synced {len(updated)} templates. "
            f"{len(newly_approved)} newly approved. "
            f"{len(orphans_captured)} new from Meta."
        ),
    }


# ── AUTO-TRIGGERS ─────────────────────────────────────────────────────────────

@router.get("/triggers")
def list_triggers(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppAutoTrigger
    q = db.query(WhatsAppAutoTrigger)
    if category:
        q = q.filter_by(event_category=category)
    triggers = q.order_by(WhatsAppAutoTrigger.event_category, WhatsAppAutoTrigger.event_key).all()
    return {"success": True, "triggers": [t.to_dict() for t in triggers]}


@router.put("/triggers/{trigger_id}")
def update_trigger(
    trigger_id: int,
    data: TriggerUpdateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppAutoTrigger
    trigger = db.query(WhatsAppAutoTrigger).get(trigger_id)
    if not trigger:
        raise HTTPException(404, "Trigger not found")

    trigger.is_enabled = data.is_enabled
    if data.template_id is not None:
        trigger.template_id = data.template_id
    if data.recipient_type:
        trigger.recipient_type = data.recipient_type
    if data.delay_minutes is not None:
        trigger.delay_minutes = data.delay_minutes
    trigger.updated_by_staff_id = _get_staff_id(current_user)
    trigger.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(trigger)
    return {"success": True, "trigger": trigger.to_dict()}


# ── TEST SEND ─────────────────────────────────────────────────────────────────

@router.post("/test-send")
def test_send(
    data: TestSendSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    from app.services.whatsapp_auto_service import send_direct_whatsapp, _render_body
    from app.models.whatsapp import WhatsAppTemplate
    context_vars = data.context_vars or {}
    send_type = (data.send_type or "meta").lower()

    message = data.custom_message or ""
    tpl = None
    if data.template_id:
        tpl = db.query(WhatsAppTemplate).get(data.template_id)
        if tpl and not message:
            message = _render_body(tpl.body_text, context_vars) if context_vars else tpl.body_text

    if not message:
        raise HTTPException(400, "Provide a template or custom message")

    # send_type="text" → force plain text path even if template is Meta-approved
    effective_template_id = data.template_id if send_type != "text" else None

    # First send (always happens)
    result = send_direct_whatsapp(
        db=db,
        phone=data.phone,
        message=message,
        template_id=effective_template_id,
        lead_id=data.lead_id,
        staff_id=_get_staff_id(current_user),
        context=context_vars or None,
    )

    # "both" → also send as plain text after the template send
    text_result = None
    if send_type == "both" and effective_template_id:
        text_result = send_direct_whatsapp(
            db=db,
            phone=data.phone,
            message=message,
            template_id=None,   # force text
            lead_id=data.lead_id,
            staff_id=_get_staff_id(current_user),
            context=None,
        )

    return {
        "success": result.get("success"),
        "wamid": result.get("wamid"),
        "reason": result.get("reason"),
        "text_result": text_result,
        "send_type": send_type,
    }


# ── CRM LEAD DIRECT SEND ───────────────────────────────────────────────────────

@router.post("/crm-lead-send/{lead_id}")
def crm_lead_send(
    lead_id: int,
    data: DirectLeadSendSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """
    Send WhatsApp to a CRM lead directly from the CRM view.
    Logs the message in crm_lead_notes (lead history).
    """
    from app.services.whatsapp_auto_service import send_direct_whatsapp, _render_body
    from app.models.crm import CRMLead
    from app.models.whatsapp import WhatsAppTemplate

    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

    phone = data.phone or getattr(lead, 'phone', None) or getattr(lead, 'mobile', None)
    if not phone:
        raise HTTPException(400, "No phone number available for this lead")

    # Resolve staff name for activity notes
    staff_id = _get_staff_id(current_user)
    staff_full_name = "Staff"
    try:
        from sqlalchemy import text as _tn
        _srow = db.execute(_tn("SELECT full_name FROM staff_employees WHERE id = :sid"), {"sid": staff_id}).fetchone()
        if _srow:
            staff_full_name = _srow[0] or staff_full_name
    except Exception:
        pass

    # Render template or use custom message
    message = data.custom_message or ""
    template = None
    template_name = None
    if data.template_id:
        template = db.query(WhatsAppTemplate).get(data.template_id)
        if template:
            # DC-CRM-WA-APPROVAL: Guard — company send requires Meta-approved template
            if (data.send_mode or 'company') == 'company' and template.meta_approval_status != 'APPROVED':
                return {
                    "success": False,
                    "reason": f"Template '{template.name}' is not Meta-approved (status: {template.meta_approval_status or 'not submitted'}). "
                              "Select an approved template or switch to Direct WA."
                }
            template_name = template.name
            context = {
                "name": getattr(lead, 'name', '') or getattr(lead, 'customer_name', ''),
                "phone": phone,
                "status": getattr(lead, 'status', ''),
                **(data.context_vars or {}),
                **(data.variable_values or {}),   # positional {{1}},{{2}} override
            }
            message = _render_body(template.body_text, context)

    if not message:
        raise HTTPException(400, "Provide a template or custom message")

    result = send_direct_whatsapp(
        db=db,
        phone=phone,
        message=message,
        template_id=data.template_id,
        lead_id=lead_id,
        staff_id=staff_id,
    )

    # DC-WA-TRACK-001: Log send to crm_wa_sends + crm_lead_notes
    if result.get("success"):
        try:
            from sqlalchemy import text as _t
            db.execute(_t("""
                INSERT INTO crm_wa_sends
                  (lead_id, template_id, staff_id, phone_used, wamid, send_method, status)
                VALUES
                  (:lead_id, :tid, :sid, :phone, :wamid, :method, 'sent')
            """), {
                "lead_id": lead_id,
                "tid": data.template_id,
                "sid": staff_id,
                "phone": phone,
                "wamid": result.get("wamid"),
                "method": "crm_manual",
            })
            # Write activity note to lead history
            note_text = (
                f"📲 WhatsApp sent (Company) via template '{template_name or 'custom'}' "
                f"to {phone} by {staff_full_name}. WAMID: {result.get('wamid') or 'N/A'}"
            )
            db.execute(_t("""
                INSERT INTO crm_lead_notes (company_id, lead_id, note, created_by_type, created_by_id)
                VALUES (:cid, :lid, :note, 'staff', :sid)
            """), {"cid": lead.company_id, "lid": lead_id, "note": note_text, "sid": str(staff_id)})
            db.commit()
        except Exception as _log_err:
            logger.warning(f"[DC-WA-TRACK-001] crm_wa_sends/note log failed (non-fatal): {_log_err}")

    return {"success": result.get("success"), "wamid": result.get("wamid"), "reason": result.get("reason")}


@router.post("/crm-lead-send/{lead_id}/log-direct")
def log_direct_wa(
    lead_id: int,
    data: DirectLogSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """DC-CRM-WA-DIRECT: Log a Direct WA open action to crm_lead_notes (no Meta API call)."""
    from app.models.crm import CRMLead
    from sqlalchemy import text as _t

    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")

    staff_id = _get_staff_id(current_user)
    staff_full_name = "Staff"
    try:
        _srow = db.execute(_t("SELECT full_name FROM staff_employees WHERE id = :sid"), {"sid": staff_id}).fetchone()
        if _srow:
            staff_full_name = _srow[0] or staff_full_name
    except Exception:
        pass

    preview = (data.message_preview or "")[:200]
    body_full = data.message_body or data.message_preview or ""
    note_text = (
        f"📱 WhatsApp opened (Direct) to {data.phone} by {staff_full_name}. "
        f"Message preview: {preview!r}"
    )
    try:
        db.execute(_t("""
            INSERT INTO crm_lead_notes (company_id, lead_id, note, created_by_type, created_by_id)
            VALUES (:cid, :lid, :note, 'staff', :sid)
        """), {"cid": lead.company_id, "lid": lead_id, "note": note_text, "sid": str(staff_id)})
        # DC-CRM-WA-DIRECT-LOG: also record in crm_wa_sends so it appears in delivery log
        db.execute(_t("""
            INSERT INTO crm_wa_sends (lead_id, staff_id, phone_used, send_method, body_sent, status, template_id)
            VALUES (:lid, :sid, :phone, 'direct_wa', :body, 'direct_sent', :tpl)
        """), {
            "lid": lead_id,
            "sid": staff_id,
            "phone": (data.phone or "")[:20],
            "body": body_full,
            "tpl": data.template_id,
        })
        db.commit()
    except Exception as _err:
        logger.warning(f"[DC-CRM-WA-DIRECT] note log failed (non-fatal): {_err}")

    return {"success": True}


# ── CAMPAIGNS ─────────────────────────────────────────────────────────────────

@router.get("/campaigns")
def list_campaigns(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaign
    q = db.query(WhatsAppCampaign)
    if status:
        q = q.filter_by(status=status)
    campaigns = q.order_by(WhatsAppCampaign.created_at.desc()).limit(100).all()
    return {"success": True, "campaigns": [c.to_dict() for c in campaigns]}


@router.post("/campaigns")
def create_campaign(
    data: CampaignCreateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaign, WhatsAppTemplate
    t = db.query(WhatsAppTemplate).get(data.template_id)
    if not t:
        raise HTTPException(404, "Template not found")

    campaign = WhatsAppCampaign(
        name=data.name, template_id=data.template_id,
        filters=data.filters or {}, notes=data.notes,
        daily_limit=data.daily_limit or 1000,
        sends_per_minute=data.sends_per_minute or 50,
        created_by_staff_id=_get_staff_id(current_user),
        status="draft",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"success": True, "campaign": campaign.to_dict()}


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaign
    c = db.query(WhatsAppCampaign).get(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    return {"success": True, "campaign": c.to_dict()}


@router.post("/campaigns/{campaign_id}/preview")
def preview_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    """Preview recipients for a campaign before launch."""
    from app.models.whatsapp import WhatsAppCampaign
    from app.models.crm import CRMLead

    campaign = db.query(WhatsAppCampaign).get(campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    filters = campaign.filters or {}
    q = db.query(CRMLead)

    # Apply filters
    if filters.get("segment"):
        segs = filters["segment"] if isinstance(filters["segment"], list) else [filters["segment"]]
        q = q.filter(CRMLead.segment.in_(segs))
    if filters.get("status"):
        statuses = filters["status"] if isinstance(filters["status"], list) else [filters["status"]]
        q = q.filter(CRMLead.status.in_(statuses))
    if filters.get("date_from"):
        q = q.filter(CRMLead.created_at >= filters["date_from"])
    if filters.get("date_to"):
        q = q.filter(CRMLead.created_at <= filters["date_to"])
    if filters.get("telecaller_id"):
        q = q.filter(CRMLead.assigned_telecaller_id == filters["telecaller_id"])

    leads_with_phone = [l for l in q.all() if getattr(l, 'phone', None) or getattr(l, 'mobile', None)]
    total = len(leads_with_phone)
    sample = leads_with_phone[:5]

    return {
        "success": True,
        "total_recipients": total,
        "sample": [
            {
                "id": l.id,
                "name": getattr(l, 'name', '') or getattr(l, 'customer_name', ''),
                "phone": getattr(l, 'phone', '') or getattr(l, 'mobile', ''),
                "status": l.status,
            }
            for l in sample
        ]
    }


@router.post("/campaigns/{campaign_id}/launch")
def launch_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    """Launch a campaign — builds recipient list and queues sends via background task."""
    from app.models.whatsapp import WhatsAppCampaign, WhatsAppCampaignLog, WhatsAppTemplate
    from app.models.crm import CRMLead

    campaign = db.query(WhatsAppCampaign).get(campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.status not in ("draft", "paused"):
        raise HTTPException(400, f"Campaign is already {campaign.status}")

    template = db.query(WhatsAppTemplate).get(campaign.template_id)
    if not template or not template.is_active:
        raise HTTPException(400, "Campaign template is not active")

    # Build recipient list
    filters = campaign.filters or {}
    q = db.query(CRMLead)
    if filters.get("segment"):
        segs = filters["segment"] if isinstance(filters["segment"], list) else [filters["segment"]]
        q = q.filter(CRMLead.segment.in_(segs))
    if filters.get("status"):
        statuses = filters["status"] if isinstance(filters["status"], list) else [filters["status"]]
        q = q.filter(CRMLead.status.in_(statuses))
    if filters.get("telecaller_id"):
        q = q.filter(CRMLead.assigned_telecaller_id == filters["telecaller_id"])

    # Custom phones override
    custom_phones = filters.get("custom_phones", [])
    if custom_phones:
        recipients = [{"phone": p, "name": "", "lead_id": None} for p in custom_phones]
    else:
        leads = [l for l in q.all() if getattr(l, 'phone', None) or getattr(l, 'mobile', None)]
        recipients = [{
            "phone": getattr(l, 'phone', None) or getattr(l, 'mobile', None),
            "name": getattr(l, 'name', '') or getattr(l, 'customer_name', ''),
            "lead_id": l.id,
        } for l in leads]

    # Queue logs
    for r in recipients:
        log = WhatsAppCampaignLog(
            campaign_id=campaign.id,
            template_id=template.id,
            phone=r["phone"],
            recipient_name=r["name"],
            lead_id=r.get("lead_id"),
            status="queued",
        )
        db.add(log)

    campaign.status = "running"
    campaign.total_recipients = len(recipients)
    campaign.pending_count = len(recipients)
    campaign.started_at = datetime.utcnow()
    db.commit()

    # Launch background send
    background_tasks.add_task(_execute_campaign, campaign_id)

    return {"success": True, "message": f"Campaign launched. {len(recipients)} recipients queued."}


def _execute_campaign(campaign_id: int):
    """Background task: send all queued campaign messages at rate limit."""
    import time
    from app.core.database import SessionLocal
    from app.models.whatsapp import WhatsAppCampaign, WhatsAppCampaignLog, WhatsAppTemplate
    from app.services.whatsapp_auto_service import send_direct_whatsapp, _render_body

    db = SessionLocal()
    try:
        campaign = db.query(WhatsAppCampaign).get(campaign_id)
        if not campaign:
            return

        template = db.query(WhatsAppTemplate).get(campaign.template_id)
        queued = db.query(WhatsAppCampaignLog).filter_by(
            campaign_id=campaign_id, status="queued"
        ).all()

        sends_per_minute = campaign.sends_per_minute or 50
        delay_seconds = 60.0 / sends_per_minute

        for log in queued:
            if campaign.status not in ("running",):
                break

            context = {"name": log.recipient_name or ""}
            message = _render_body(template.body_text, context) if template else ""

            result = send_direct_whatsapp(
                db=db, phone=log.phone, message=message,
                template_id=log.template_id, lead_id=log.lead_id,
                campaign_log_id=log.id,
            )

            if result.get("success"):
                campaign.sent_count = (campaign.sent_count or 0) + 1
                campaign.pending_count = max(0, (campaign.pending_count or 1) - 1)
            else:
                campaign.failed_count = (campaign.failed_count or 0) + 1
                campaign.pending_count = max(0, (campaign.pending_count or 1) - 1)

            db.commit()
            time.sleep(delay_seconds)

        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error("[WA-CAMPAIGN] Execute error: %s", str(e))
        try:
            campaign = db.query(WhatsAppCampaign).get(campaign_id)
            if campaign:
                campaign.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaign
    c = db.query(WhatsAppCampaign).get(campaign_id)
    if not c:
        raise HTTPException(404, "Not found")
    c.status = "paused"
    c.paused_at = datetime.utcnow()
    db.commit()
    return {"success": True}


@router.post("/campaigns/{campaign_id}/cancel")
def cancel_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaign
    c = db.query(WhatsAppCampaign).get(campaign_id)
    if not c:
        raise HTTPException(404, "Not found")
    c.status = "cancelled"
    db.commit()
    return {"success": True}


@router.get("/campaigns/{campaign_id}/logs")
def get_campaign_logs(
    campaign_id: int,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import WhatsAppCampaignLog
    q = db.query(WhatsAppCampaignLog).filter_by(campaign_id=campaign_id)
    if status:
        q = q.filter_by(status=status)
    total = q.count()
    logs = q.order_by(WhatsAppCampaignLog.queued_at.desc()).offset(offset).limit(limit).all()
    return {
        "success": True, "total": total,
        "logs": [{
            "id": l.id, "phone": l.phone, "recipient_name": l.recipient_name,
            "status": l.status, "wamid": l.wamid, "error_message": l.error_message,
            "sent_at": l.sent_at.isoformat() if l.sent_at else None,
            "delivered_at": l.delivered_at.isoformat() if l.delivered_at else None,
        } for l in logs]
    }


# ── MESSAGE HISTORY ─────────────────────────────────────────────────────────────

@router.get("/history")
def message_history(
    phone: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    message_type: Optional[str] = None,
    sent_by: Optional[str] = None,
    sender_type: Optional[str] = None,
    mine_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    from app.models.whatsapp import MessageLog
    from datetime import datetime, timedelta
    q = db.query(MessageLog)
    if phone:
        q = q.filter(MessageLog.mobile_number.contains(phone.strip()))
    if search:
        q = q.filter(
            (MessageLog.message_body.ilike(f'%{search}%')) |
            (MessageLog.mobile_number.contains(search)) |
            (MessageLog.user_name.ilike(f'%{search}%')) |
            (MessageLog.sent_by_name.ilike(f'%{search}%'))
        )
    if status:
        q = q.filter(MessageLog.current_status == status)
    if message_type:
        q = q.filter(MessageLog.message_type == message_type)
    if sent_by:
        q = q.filter(MessageLog.sent_by_name.ilike(f'%{sent_by}%'))
    if sender_type:
        q = q.filter(MessageLog.sender_type == sender_type)
    if mine_only:
        staff_id = getattr(current_user, 'id', None)
        if staff_id:
            q = q.filter(MessageLog.sent_by_staff_id == staff_id)
    if date_from:
        try:
            q = q.filter(MessageLog.sent_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            pass
    if date_to:
        try:
            q = q.filter(MessageLog.sent_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except Exception:
            pass

    total = q.count()
    messages = q.order_by(MessageLog.sent_at.desc()).offset(offset).limit(limit).all()

    return {
        "success": True, "total": total,
        "messages": [{
            "id": m.id,
            "message_type": m.message_type,
            "mobile_number": m.mobile_number,
            "user_name": m.user_name,
            "message_body": m.message_body,
            "current_status": m.current_status,
            "provider": m.provider,
            "wamid": m.message_sid,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
           "error_message": m.error_message,
            "error_code": m.error_code,
            "sent_by_name": m.sent_by_name or "System",
            "sender_type": m.sender_type or "auto",
            "sent_by_staff_id": m.sent_by_staff_id,
        } for m in messages]
    }


# ── COMBINED DELIVERY LOG (message_log + crm_wa_sends) ──────────────────────────

@router.get("/delivery-log")
def delivery_log(
    phone: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    message_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_send)
):
    """DC-DELIVERY-LOG-001: Combined delivery status from message_log + crm_wa_sends."""
    from datetime import datetime, timedelta
    conditions_ml = ["1=1"]
    conditions_cws = ["1=1"]
    params = {}
    if phone:
        p = f"%{phone.strip()}%"
        conditions_ml.append("(ml.mobile_number LIKE :phone OR ml.to_number LIKE :phone)")
        conditions_cws.append("cws.phone_used LIKE :phone")
        params["phone"] = p
    if search:
        s = f"%{search}%"
        conditions_ml.append("(ml.message_body ILIKE :s OR ml.user_name ILIKE :s OR ml.sent_by_name ILIKE :s OR ml.mobile_number LIKE :s)")
        conditions_cws.append("(cws.body_sent ILIKE :s OR cws.phone_used LIKE :s)")
        params["s"] = s
    if status:
        conditions_ml.append("ml.current_status = :status")
        conditions_cws.append("cws.status = :status")
        params["status"] = status
    if message_type:
        conditions_ml.append("ml.message_type = :mtype")
        conditions_cws.append("cws.send_method = :mtype")
        params["mtype"] = message_type
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            conditions_ml.append("ml.sent_at >= :df")
            conditions_cws.append("cws.sent_at >= :df")
            params["df"] = df
        except Exception: pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            conditions_ml.append("ml.sent_at < :dt")
            conditions_cws.append("cws.sent_at < :dt")
            params["dt"] = dt
        except Exception: pass

    ml_where = " AND ".join(conditions_ml)
    cws_where = " AND ".join(conditions_cws)

    ml_query = f"""
        SELECT
            ml.id::text AS id,
            'message_log' AS source,
            ml.message_type,
            COALESCE(ml.mobile_number, ml.to_number) AS phone,
            ml.user_name AS contact_name,
            ml.message_body AS body,
            ml.current_status AS status,
            ml.message_sid AS wamid,
            ml.sent_at,
            ml.delivered_at,
            ml.failed_at,
            ml.error_code,
            ml.error_message,
            COALESCE(ml.sent_by_name, 'System') AS sent_by,
            ml.sender_type,
            NULL::text AS template_name
        FROM message_log ml
        WHERE {ml_where}
    """
    cws_query = f"""
        SELECT
            cws.id::text AS id,
            'crm_wa_sends' AS source,
            COALESCE(cws.send_method, 'template') AS message_type,
            cws.phone_used AS phone,
            COALESCE(se.full_name, 'Staff #' || cws.staff_id::text) AS contact_name,
            cws.body_sent AS body,
            COALESCE(ml_live.current_status, cws.status) AS status,
            cws.wamid,
            cws.sent_at,
            ml_live.delivered_at,
            ml_live.failed_at,
            ml_live.error_code,
            COALESCE(ml_live.error_message, cws.notes) AS error_message,
            COALESCE(se.full_name, 'Staff') AS sent_by,
            'staff' AS sender_type,
            wt.name AS template_name
        FROM crm_wa_sends cws
        LEFT JOIN staff_employees se ON se.id = cws.staff_id
        LEFT JOIN whatsapp_templates wt ON wt.id = cws.template_id
        LEFT JOIN LATERAL (
            SELECT current_status, delivered_at, failed_at, error_code, error_message
            FROM message_log
            WHERE message_sid = cws.wamid AND cws.wamid IS NOT NULL
            ORDER BY id DESC LIMIT 1
        ) ml_live ON true
        WHERE {cws_where}
    """

    if source == 'message_log':
        union_sql = ml_query
    elif source == 'crm_wa_sends':
        union_sql = cws_query
    else:
        union_sql = f"({ml_query}) UNION ALL ({cws_query})"

    from sqlalchemy import text
    count_sql = f"SELECT COUNT(*) FROM ({union_sql}) _u"
    total = db.execute(text(count_sql), params).scalar() or 0

    offset = (page - 1) * page_size
    data_sql = f"SELECT * FROM ({union_sql}) _u ORDER BY sent_at DESC NULLS LAST LIMIT :lim OFFSET :off"
    rows = db.execute(text(data_sql), {**params, "lim": page_size, "off": offset}).fetchall()

    def _iso(v):
        return v.isoformat() if v else None

    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": [{
            "id": r.id,
            "source": r.source,
            "message_type": r.message_type,
            "phone": r.phone,
            "contact_name": r.contact_name,
            "body": r.body,
            "status": r.status,
            "wamid": r.wamid,
            "sent_at": _iso(r.sent_at),
            "delivered_at": _iso(r.delivered_at),
            "failed_at": _iso(r.failed_at),
            "error_code": r.error_code,
            "error_message": r.error_message,
            "sent_by": r.sent_by,
            "sender_type": r.sender_type,
            "template_name": r.template_name,
        } for r in rows]
    }


# ── TOKEN HEALTH CHECK ──────────────────────────────────────────────────────────

@router.get("/token-status")
async def token_status(
    request: Request,
    db: Session = Depends(get_db),
):
    """Check Meta WhatsApp access token validity. DB credentials take priority over env vars."""
    import requests as rq, os as _os
    from app.services.wa_credentials import get_wa_credentials
    # Prefer DB credentials; fall back to env vars
    db_creds = get_wa_credentials(db)
    token = (db_creds.get("access_token") or "").strip() or _os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    phone_id = (db_creds.get("phone_number_id") or "").strip() or _os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", "")
    source = "db" if (db_creds.get("access_token") or "").strip() else "env"
    if not token:
        return {"status": "missing", "message": "No access token configured (neither in DB credentials nor environment)"}
    if not phone_id:
        return {"status": "missing", "message": "No Phone Number ID configured"}
    try:
        resp = rq.get(
            f"https://graph.facebook.com/v21.0/{phone_id}",
            params={"access_token": token, "fields": "display_phone_number,verified_name"},
            timeout=8
        )
        data = resp.json()
        if resp.status_code == 200:
            return {
                "status": "valid",
                "phone_number": data.get("display_phone_number", ""),
                "display_name": data.get("verified_name", ""),
                "phone_id": phone_id,
                "source": source,
            }
        else:
            err = data.get("error", {})
            return {
                "status": "expired",
                "message": err.get("message", "Token invalid or expired"),
                "error_code": err.get("code"),
                "error_subcode": err.get("error_subcode"),
                "source": source,
            }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ── COSTING STATS ──────────────────────────────────────────────────────────────

@router.get("/costing-stats")
def costing_stats(
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config)
):
    """Aggregate message counts + estimated Meta API cost for executive costing view."""
    from app.models.whatsapp import MessageLog
    from sqlalchemy import text as _text
    from datetime import date

    today = date.today()
    month_start = today.replace(day=1)

    def q(extra_where=""):
        return db.execute(_text(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN current_status IN ('sent','delivered','read') THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN current_status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN current_status = 'read' THEN 1 ELSE 0 END) as read_cnt,
                SUM(CASE WHEN current_status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN message_type LIKE 'auto_%' THEN 1 ELSE 0 END) as triggered,
                SUM(CASE WHEN message_type = 'direct_send' THEN 1 ELSE 0 END) as manual_sent
            FROM message_log
            {extra_where}
        """)).fetchone()

    all_r = q()
    month_r = q(f"WHERE sent_at >= '{month_start}'")

    # Meta India pricing (approx): template message ≈ $0.0047 each, free-form ≈ $0.0042
    # Simplified: ~$0.004 per message as a conservative estimate
    COST_PER_MSG = 0.0047
    USD_TO_INR = 83.5

    def row_to_dict(r, cost_per=COST_PER_MSG):
        total = int(r[0] or 0)
        sent = int(r[1] or 0)
        delivered = int(r[2] or 0)
        read_cnt = int(r[3] or 0)
        failed = int(r[4] or 0)
        triggered = int(r[5] or 0)
        manual = int(r[6] or 0)
        cost_usd = round(sent * cost_per, 2)
        cost_inr = round(cost_usd * USD_TO_INR, 0)
        delivery_rate = round(delivered / sent * 100, 1) if sent else 0
        return {
            "total": total, "sent": sent, "delivered": delivered,
            "read": read_cnt, "failed": failed, "triggered": triggered,
            "manual": manual, "cost_usd": cost_usd, "cost_inr": int(cost_inr),
            "delivery_rate": delivery_rate,
        }

    # Daily breakdown last 30 days
    daily = db.execute(_text("""
        SELECT DATE(sent_at) as d, COUNT(*) as cnt
        FROM message_log
        WHERE sent_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(sent_at) ORDER BY d
    """)).fetchall()

    # Top templates (by count)
    top_tpl = db.execute(_text("""
        SELECT message_type, COUNT(*) as cnt
        FROM message_log GROUP BY message_type ORDER BY cnt DESC LIMIT 8
    """)).fetchall()

    return {
        "success": True,
        "all_time": row_to_dict(all_r),
        "this_month": row_to_dict(month_r),
        "daily": [{"date": str(r[0]), "count": int(r[1])} for r in daily],
        "top_types": [{"type": r[0], "count": int(r[1])} for r in top_tpl],
    }


# ── SEGMENTS LOOKUP ─────────────────────────────────────────────────────────────

@router.get("/segments")
async def list_segments(current_user=Depends(require_wa_send)):
    return {
        "success": True,
        "segments": [
            {"value": "ev_b2b", "label": "EV B2B"},
            {"value": "ev_b2c", "label": "EV B2C"},
            {"value": "etc_training", "label": "ETC Training"},
            {"value": "real_estate", "label": "Real Estate"},
            {"value": "general", "label": "MNR General"},
            {"value": "system", "label": "System"},
        ]
    }


# ── Credentials Management ──────────────────────────────────────────────────────

@router.get("/credentials", summary="Get WhatsApp API Credentials (masked)")
async def get_wa_credentials_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    _auth=Depends(require_wa_config),
):
    """Return current credentials with token masked. Admin-only."""
    try:
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT access_token, phone_number_id, verify_token, business_account_id, updated_at, updated_by, facebook_app_id "
            "FROM whatsapp_api_config ORDER BY id DESC LIMIT 1"
        )).fetchone()
        if row and row[0]:
            token = row[0]
            masked = token[:10] + "..." + token[-10:] if len(token) > 20 else "***"
            return {
                "has_credentials": True,
                "access_token_masked": masked,
                "phone_number_id": row[1] or "",
                "verify_token": row[2] or "",
                "business_account_id": row[3] or "",
                "updated_at": row[4].isoformat() if row[4] else None,
                "updated_by": row[5] or "",
                "facebook_app_id": row[6] or "",
                "source": "database",
            }
    except Exception:
        pass
    import os
    token_env = os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    return {
        "has_credentials": bool(token_env),
        "access_token_masked": (token_env[:10] + "...***") if token_env else "",
        "phone_number_id": os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", ""),
        "verify_token": os.environ.get("META_WHATSAPP_VERIFY_TOKEN", ""),
        "business_account_id": os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        "updated_at": None,
        "updated_by": "",
        "source": "env_var",
    }


@router.put("/credentials", summary="Update WhatsApp API Credentials")
async def update_wa_credentials(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_wa_config),
):
    """Upsert credentials into whatsapp_api_config."""
    from sqlalchemy import text
    import datetime

    access_token = (payload.get("access_token") or "").strip()
    phone_number_id = (payload.get("phone_number_id") or "").strip()
    verify_token = (payload.get("verify_token") or "").strip()
    business_account_id = (payload.get("business_account_id") or "").strip()
    facebook_app_id = (payload.get("facebook_app_id") or "").strip()

    if not access_token:
        raise HTTPException(status_code=400, detail="access_token is required")
    if not phone_number_id:
        raise HTTPException(status_code=400, detail="phone_number_id is required")

    updater = getattr(current_user, 'employee_id', None) or getattr(current_user, 'name', 'staff')
    now = datetime.datetime.now()

    db.execute(text("DELETE FROM whatsapp_api_config"))
    db.execute(text(
        "INSERT INTO whatsapp_api_config "
        "(access_token, phone_number_id, verify_token, business_account_id, facebook_app_id, updated_at, updated_by) "
        "VALUES (:tok, :pid, :vt, :baid, :appid, :now, :by)"
    ), {"tok": access_token, "pid": phone_number_id, "vt": verify_token, "baid": business_account_id,
        "appid": facebook_app_id or None, "now": now, "by": str(updater)})
    db.commit()

    try:
        import requests as _req
        r = _req.get(
            f"https://graph.facebook.com/v21.0/{phone_number_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=8
        )
        d = r.json()
        if r.status_code == 200:
            return {
                "success": True,
                "message": "Credentials saved and verified ✅",
                "phone_display": d.get("display_phone_number", ""),
                "verified_name": d.get("verified_name", ""),
            }
        else:
            err = d.get("error", {}).get("message", "Unknown error")
            return {"success": True, "message": f"Credentials saved but API verification failed: {err}", "warning": True}
    except Exception as e:
        return {"success": True, "message": f"Credentials saved (verification check failed: {e})", "warning": True}
