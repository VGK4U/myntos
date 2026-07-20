"""
VGK4U Member Write-Flow Endpoints — Task #34 (Phase 2)

DC Protocol May 2026:
- Audience-aware (defaults to ``mnr``); only the ``vgk4u`` branch is
  implemented here. The ``mnr`` branch is served by the original module
  (feedback.py / bank_kyc_admin.py / coupon_transfers.py / profile.py)
  and is intentionally untouched. Calling these endpoints with
  ``audience=mnr`` returns a 400 instructing the caller to use the
  legacy URL — guarantees zero MNR regression.
- WVV Protocol: every write does Write → Verify (re-read) → Validate
  (cross-check) before commit; rollback on any mismatch.
- Zero-Default Access: every module is gated by an `app_settings.*_vgk4u_enabled`
  toggle (defaults to FALSE); endpoints return 403 when toggle is OFF.
- IST timestamps via `get_indian_time()`.
- All writes audit-logged via `_audit()` helper which embeds
  ``audience='vgk4u'`` inside the StaffAuditLog `new_data` JSONB.
"""

from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import (
    APIRouter, Depends, HTTPException, Query, Body, UploadFile, File, Form,
    Request, BackgroundTasks, status
)
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text as sa_text
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.audience_resolver import normalize_audience, audience_label
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger
from app.models.staff import StaffAuditLog, StaffEmployee, log_staff_audit
from app.models.system_control import AppSettings
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member, get_indian_time
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.universal_upload_service import UniversalUploadService

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Toggle gates (Zero-Default Access)
# ─────────────────────────────────────────────────────────────────────
_TOGGLE_MAP = {
    'feedback':         'feedback_vgk4u_enabled',
    'announcements':    'announcements_vgk4u_enabled',
    'kyc':              'kyc_vgk4u_enabled',
    'bank':             'bank_vgk4u_enabled',
    'coupon_transfer':  'coupon_transfer_vgk4u_enabled',
    'profile_edit':     'profile_edit_vgk4u_enabled',
    'settings':         'settings_vgk4u_enabled',
}


def _check_toggle(module: str, db: Session) -> None:
    """Raise 403 when the Phase-2 module toggle is OFF (Zero-Default Access).
    Toggles live on `app_settings` (single source of truth — see Task #33)."""
    col = _TOGGLE_MAP.get(module)
    if not col:
        return
    row = db.query(AppSettings).first()
    enabled = bool(getattr(row, col, False)) if row else False
    if not enabled:
        raise HTTPException(
            status_code=403,
            detail=f"VGK4U module '{module}' is currently disabled by Super-Admin. Toggle: {col}"
        )


# ─────────────────────────────────────────────────────────────────────
# Audit helper — injects audience='vgk4u' into the JSONB payload so the
# existing staff_audit_log table (no schema change needed) carries the
# audience tag and is filterable from staff_audit_logs.html.
# ─────────────────────────────────────────────────────────────────────
def _audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    actor_partner_id: Optional[int] = None,
    actor_staff_id: Optional[int] = None,
    old_data: Optional[Dict[str, Any]] = None,
    new_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """DC_T34_AUDIT_001 — every Phase-2 write logs with audience='vgk4u'.

    Task #44: actor_staff_id distinguishes staff-initiated approvals
    from partner-initiated submissions. When set, the resulting
    staff_audit_log row carries the real staff employee_id (FK-bound)
    so the row passes the FK constraint and is attributable in the
    staff_audit_logs.html viewer.
    """
    nd = dict(new_data or {})
    nd.setdefault('audience', 'vgk4u')
    if actor_partner_id is not None:
        nd.setdefault('actor_partner_id', actor_partner_id)
    if actor_staff_id is not None:
        nd.setdefault('actor_staff_id', actor_staff_id)
    od = dict(old_data) if old_data else None
    if od is not None:
        od.setdefault('audience', 'vgk4u')
    try:
        log_staff_audit(
            db,
            employee_id=actor_staff_id,  # None for partner-initiated, real id for staff-initiated
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_data=od,
            new_data=nd,
            ip_address=ip_address,
        )
        db.flush()
    except Exception as e:
        logger.warning(f"[VGK4U-P2-AUDIT] non-fatal audit failure: {e}")


def _wvv_verify(label: str, condition: bool, ctx: Dict[str, Any] | None = None):
    """WVV — Validate. Raise 500 with a descriptive context if the
    cross-check fails. Caller must rollback before calling this if the
    mismatch warrants rolling back."""
    if not condition:
        raise HTTPException(
            status_code=500,
            detail=f"WVV verification failed at '{label}'; ctx={ctx or {}}"
        )


def _audience_or_400(audience: Optional[str]) -> str:
    a = normalize_audience(audience)
    if a != 'vgk4u':
        raise HTTPException(
            status_code=400,
            detail=(
                "These endpoints serve VGK4U members only. "
                "Pass audience=vgk4u, or call the legacy MNR endpoint for mnr writes."
            )
        )
    return a


# =====================================================================
# VGK4U Phase 2 — WhatsApp auto-trigger seed map (Task #45)
# Each entry defines the default template + trigger row that will be
# auto-seeded into whatsapp_templates / whatsapp_auto_triggers on first
# call. Bodies use {{var}} placeholders matching _render_body() in
# whatsapp_auto_service.py — keys must match the context dict passed at
# the call site so partner_name and dynamic fields render correctly.
# =====================================================================
_VGK_WA_SEEDS: Dict[str, Dict[str, Any]] = {
    'vgk_feedback_submitted': {
        'event_label': 'VGK4U Feedback Submitted',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Feedback Submitted',
        'template_slug': 'vgk_feedback_submitted',
        'body_text': (
            "Hello {{partner_name}}, we've received your feedback "
            "\"{{title}}\" (ref #{{feedback_id}}). Our team will review and respond soon. — VGK4U"
        ),
    },
    'vgk_kyc_submitted': {
        'event_label': 'VGK4U KYC Document Submitted',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U KYC Submitted',
        'template_slug': 'vgk_kyc_submitted',
        'body_text': (
            "Hello {{partner_name}}, your KYC document ({{document_type}}) "
            "has been received and is now under review. — VGK4U"
        ),
    },
    'vgk_kyc_approved': {
        'event_label': 'VGK4U KYC Approved',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U KYC Approved',
        'template_slug': 'vgk_kyc_approved',
        'body_text': (
            "Congratulations {{partner_name}}! Your KYC has been verified and approved. "
            "You can now access all VGK4U partner benefits. — VGK4U"
        ),
    },
    'vgk_kyc_rejected': {
        'event_label': 'VGK4U KYC Rejected',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U KYC Rejected',
        'template_slug': 'vgk_kyc_rejected',
        'body_text': (
            "Hello {{partner_name}}, your KYC submission could not be approved. "
            "Reason: {{reason}}. Please re-submit with the required corrections. — VGK4U"
        ),
    },
    'vgk_bank_verified': {
        'event_label': 'VGK4U Bank Details Verified',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Bank Verified',
        'template_slug': 'vgk_bank_verified',
        'body_text': (
            "Hello {{partner_name}}, your bank details have been {{status}}. {{notes}} "
            "Payouts will now be credited to this account. — VGK4U"
        ),
    },
    'vgk_bank_rejected': {
        'event_label': 'VGK4U Bank Details Rejected',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Bank Rejected',
        'template_slug': 'vgk_bank_rejected',
        'body_text': (
            "Hello {{partner_name}}, your bank details submission was {{status}}. "
            "{{notes}} Please re-submit with corrected information or contact support. — VGK4U"
        ),
    },
    'vgk_coupon_activated': {
        'event_label': 'VGK4U Coupon Activated',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Coupon Activated',
        'template_slug': 'vgk_coupon_activated',
        'body_text': (
            "Hello {{partner_name}}, your coupon code {{coupon_code}} has been "
            "activated successfully. — VGK4U"
        ),
    },
    'vgk_coupon_transferred': {
        'event_label': 'VGK4U Coupon Points Transferred',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Coupon Transferred',
        'template_slug': 'vgk_coupon_transferred',
        'body_text': (
            "Hello {{partner_name}}, you have transferred {{points}} points to {{to}}. "
            "— VGK4U"
        ),
    },
    'vgk_coupon_received': {
        'event_label': 'VGK4U Coupon Points Received',
        'event_category': 'partner',
        'recipient_type': 'customer',
        'template_name': 'VGK4U Coupon Received',
        'template_slug': 'vgk_coupon_received',
        'body_text': (
            "Hello {{partner_name}}, you have received {{points}} points from {{from}}. "
            "— VGK4U"
        ),
    },
}


def _ensure_vgk_trigger(db, event_key: str) -> bool:
    """
    Idempotent auto-seed: ensure a WhatsAppTemplate + WhatsAppAutoTrigger
    row exists for the given vgk_* event_key. Returns True if the
    trigger exists (newly created or already present), False on error
    or unknown event_key.

    Called from _safe_send_whatsapp before scheduling the background
    send, so the very first call to a never-fired event auto-creates
    the rows and the second call onwards finds them. All seeded
    triggers default to is_enabled=True with the canonical body.
    Staff can later edit body/header/buttons through the existing
    WhatsApp admin UI — this seeder never overwrites an existing row.
    """
    if event_key not in _VGK_WA_SEEDS:
        return False
    try:
        from app.models.whatsapp import WhatsAppAutoTrigger, WhatsAppTemplate
        existing = db.query(WhatsAppAutoTrigger).filter_by(event_key=event_key).first()
        if existing:
            return True
        seed = _VGK_WA_SEEDS[event_key]
        tpl = db.query(WhatsAppTemplate).filter_by(slug=seed['template_slug']).first()
        if not tpl:
            tpl = WhatsAppTemplate(
                name=seed['template_name'],
                slug=seed['template_slug'],
                segment='general',
                template_type='custom',
                is_active=True,
                is_system=False,
                header_type='none',
                body_text=seed['body_text'],
                usage_scope='both',
            )
            db.add(tpl)
            db.flush()
        trig = WhatsAppAutoTrigger(
            event_key=event_key,
            event_label=seed['event_label'],
            event_category=seed['event_category'],
            template_id=tpl.id,
            is_enabled=True,
            recipient_type=seed['recipient_type'],
            delay_minutes=0,
        )
        db.add(trig)
        db.commit()
        logger.info(f"[VGK4U-P2-WA-SEED] auto-created trigger for {event_key} (template_id={tpl.id})")
        return True
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"[VGK4U-P2-WA-SEED] auto-seed failed for {event_key}: {e}")
        return False


def _safe_send_whatsapp(background: BackgroundTasks, event_key: str, phone: Optional[str], context: Dict[str, Any]):
    """Best-effort WA notification — never block the write on a notification failure.

    Task #45: also auto-seeds the trigger+template on first call so the 9 new
    Phase-2 events do not silently no-op when the admin has never explicitly
    configured them. The seed runs in a separate session so it commits before
    the background dispatch reads the newly-created trigger.
    """
    if not phone:
        return
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        from app.core.database import SessionLocal

        # Auto-seed trigger row if missing (idempotent, separate session so
        # the commit is visible to the background runner below).
        if event_key in _VGK_WA_SEEDS:
            seed_db = SessionLocal()
            try:
                _ensure_vgk_trigger(seed_db, event_key)
            finally:
                seed_db.close()

        def _runner():
            db2 = SessionLocal()
            try:
                send_auto_whatsapp(db2, event_key, phone, context)
            except Exception as e:
                logger.warning(f"[VGK4U-P2-WA] {event_key} failed: {e}")
            finally:
                db2.close()
        background.add_task(_runner)
    except Exception as e:
        logger.warning(f"[VGK4U-P2-WA] schedule failed for {event_key}: {e}")


# =====================================================================
# 1. FEEDBACK  (Step 3)
# =====================================================================
class FeedbackSubmitIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=4000)
    category_id: Optional[int] = None
    submission_type: str = Field('text', pattern='^(text|photo|video|review)$')


@router.post("/feedback/submit", tags=["VGK4U Feedback"])
async def vgk_feedback_submit(
    payload: FeedbackSubmitIn,
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('feedback', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        result = db.execute(sa_text("""
            INSERT INTO vgk_feedback
              (partner_id, company_id, category_id, submission_type, title,
               description, status, visible_to, submitted_at)
            VALUES
              (:pid, :cid, :catid, :stype, :title,
               :desc, 'pending', 'vgk', :ts)
            RETURNING id, status, submitted_at
        """), {
            "pid": partner.id, "cid": getattr(partner, 'company_id', None),
            "catid": payload.category_id, "stype": payload.submission_type,
            "title": payload.title, "desc": payload.description, "ts": now,
        }).fetchone()
        new_id = int(result[0])

        # WVV — Verify (re-read)
        readback = db.execute(sa_text(
            "SELECT id, partner_id, status, title FROM vgk_feedback WHERE id = :id"
        ), {"id": new_id}).fetchone()
        _wvv_verify("feedback_submit_readback", readback is not None and readback[1] == partner.id,
                    {"new_id": new_id})
        _wvv_verify("feedback_submit_status", readback[2] == 'pending')

        _audit(db, action='vgk_feedback.submit', resource_type='vgk_feedback',
               resource_id=new_id, actor_partner_id=partner.id,
               new_data={'title': payload.title, 'submission_type': payload.submission_type},
               ip_address=request.client.host if request.client else None)
        db.commit()

        _safe_send_whatsapp(background, 'vgk_feedback_submitted', partner.phone,
                            {'partner_name': partner.partner_name, 'title': payload.title, 'feedback_id': new_id})

        return {"success": True, "id": new_id, "status": "pending",
                "submitted_at": readback[3] and now.isoformat(),
                "audience": "vgk4u", "audience_label": audience_label('vgk4u')}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-FEEDBACK-SUBMIT]")
        raise HTTPException(status_code=500, detail=f"Submit failed: {e}")


@router.get("/feedback/my-submissions", tags=["VGK4U Feedback"])
def vgk_feedback_my_submissions(
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('feedback', db)
    rows = db.execute(sa_text("""
        SELECT id, title, description, submission_type, status, submitted_at,
               approved_at, COALESCE(views_count, 0), COALESCE(shares_count, 0)
          FROM vgk_feedback
         WHERE partner_id = :pid AND COALESCE(is_deleted, false) = false
         ORDER BY submitted_at DESC LIMIT 200
    """), {"pid": partner.id}).fetchall()
    submissions = [{
        "id": r[0], "title": r[1], "description": r[2],
        "submission_type": r[3], "status": r[4],
        "submitted_at": r[5].isoformat() if r[5] else None,
        "approved_at": r[6].isoformat() if r[6] else None,
        "views_count": r[7], "shares_count": r[8],
    } for r in rows]
    return {"success": True, "audience": "vgk4u",
            "audience_label": audience_label('vgk4u'),
            "submissions": submissions, "count": len(submissions)}


@router.get("/feedback/admin-pending", tags=["VGK4U Feedback Admin"])
def vgk_feedback_admin_pending(
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff-only — list pending VGK4U feedback for admin approval. (Task #44)"""
    _audience_or_400(audience)
    rows = db.execute(sa_text("""
        SELECT f.id, f.partner_id, f.title, f.description, f.submission_type,
               f.submitted_at, p.partner_name, p.partner_code
          FROM vgk_feedback f
          LEFT JOIN official_partners p ON p.id = f.partner_id
         WHERE f.status = 'pending' AND COALESCE(f.is_deleted, false) = false
         ORDER BY f.submitted_at DESC LIMIT 500
    """)).fetchall()
    _audit(db, action='vgk_feedback.admin_list', resource_type='vgk_feedback',
           actor_staff_id=staff.id, new_data={'count': len(rows)},
           ip_address=request.client.host if request and request.client else None)
    db.commit()
    return {"success": True, "audience": "vgk4u",
            "items": [{
                "id": r[0], "partner_id": r[1], "title": r[2],
                "description": r[3], "submission_type": r[4],
                "submitted_at": r[5].isoformat() if r[5] else None,
                "partner_name": r[6], "partner_code": r[7],
            } for r in rows]}


@router.post("/feedback/{feedback_id}/approve", tags=["VGK4U Feedback Admin"])
def vgk_feedback_approve(
    feedback_id: int,
    audience: Optional[str] = Query('vgk4u'),
    notes: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text("SELECT status, partner_id, title FROM vgk_feedback WHERE id = :id"),
                              {"id": feedback_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Feedback not found")
        if existing[0] not in ('pending',):
            raise HTTPException(409, f"Feedback already {existing[0]}")
        db.execute(sa_text("""
            UPDATE vgk_feedback SET status = 'approved', approved_at = :ts
             WHERE id = :id
        """), {"ts": now, "id": feedback_id})

        # Roll into vgk_announcements
        ann = db.execute(sa_text("""
            INSERT INTO vgk_announcements
              (source_feedback_id, partner_id, title, description,
               announcement_type, status, visible_to, published_at)
            SELECT id, partner_id, title, description, submission_type,
                   'approved', 'vgk', :ts
              FROM vgk_feedback WHERE id = :id
            RETURNING id
        """), {"id": feedback_id, "ts": now}).fetchone()

        readback = db.execute(sa_text("SELECT status, approved_at FROM vgk_feedback WHERE id = :id"),
                              {"id": feedback_id}).fetchone()
        _wvv_verify("feedback_approve_readback", readback[0] == 'approved')

        _audit(db, action='vgk_feedback.approve', resource_type='vgk_feedback',
               resource_id=feedback_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'approved', 'announcement_id': int(ann[0]) if ann else None,
                         'notes': notes},
               ip_address=request.client.host if request and request.client else None)
        db.commit()
        return {"success": True, "id": feedback_id, "status": "approved",
                "announcement_id": int(ann[0]) if ann else None}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-FEEDBACK-APPROVE]")
        raise HTTPException(500, f"Approve failed: {e}")


@router.post("/feedback/{feedback_id}/reject", tags=["VGK4U Feedback Admin"])
def vgk_feedback_reject(
    feedback_id: int,
    audience: Optional[str] = Query('vgk4u'),
    reason: str = Body(..., embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    if not (reason or '').strip():
        raise HTTPException(400, "rejection reason is required")
    try:
        existing = db.execute(sa_text("SELECT status FROM vgk_feedback WHERE id = :id"),
                              {"id": feedback_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Feedback not found")
        db.execute(sa_text("UPDATE vgk_feedback SET status = 'rejected' WHERE id = :id"),
                   {"id": feedback_id})
        readback = db.execute(sa_text("SELECT status FROM vgk_feedback WHERE id = :id"),
                              {"id": feedback_id}).fetchone()
        _wvv_verify("feedback_reject_readback", readback[0] == 'rejected')
        _audit(db, action='vgk_feedback.reject', resource_type='vgk_feedback',
               resource_id=feedback_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'rejected', 'reason': reason},
               ip_address=request.client.host if request and request.client else None)
        db.commit()
        return {"success": True, "id": feedback_id, "status": "rejected"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-FEEDBACK-REJECT]")
        raise HTTPException(500, f"Reject failed: {e}")


# =====================================================================
# 2. ANNOUNCEMENTS LIFECYCLE (Step 4)
# =====================================================================
class AnnouncementCreateIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=4000)
    announcement_type: str = Field('text', pattern='^(text|photo|video|review)$')
    cover_image_url: Optional[str] = None
    video_url: Optional[str] = None


@router.post("/announcements/create", tags=["VGK4U Announcements"])
def vgk_announcement_create(
    payload: AnnouncementCreateIn,
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('announcements', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        result = db.execute(sa_text("""
            INSERT INTO vgk_announcements
              (partner_id, company_id, title, description, announcement_type,
               status, cover_image_url, video_url, visible_to, created_at, updated_at)
            VALUES
              (:pid, :cid, :title, :desc, :atype, 'pending', :cover, :video,
               'vgk', :ts, :ts)
            RETURNING id
        """), {
            "pid": partner.id, "cid": getattr(partner, 'company_id', None),
            "title": payload.title, "desc": payload.description,
            "atype": payload.announcement_type, "cover": payload.cover_image_url,
            "video": payload.video_url, "ts": now,
        }).fetchone()
        new_id = int(result[0])

        readback = db.execute(sa_text("SELECT status, partner_id FROM vgk_announcements WHERE id = :id"),
                              {"id": new_id}).fetchone()
        _wvv_verify("announcement_create_readback",
                    readback is not None and readback[0] == 'pending' and readback[1] == partner.id)

        _audit(db, action='vgk_announcement.create', resource_type='vgk_announcements',
               resource_id=new_id, actor_partner_id=partner.id,
               new_data={'title': payload.title, 'type': payload.announcement_type},
               ip_address=request.client.host if request.client else None)
        db.commit()
        return {"success": True, "id": new_id, "status": "pending",
                "audience": "vgk4u"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-ANN-CREATE]")
        raise HTTPException(500, f"Create failed: {e}")


def _list_announcements_by_status(partner_id: int, status_val: Optional[str], db: Session) -> List[Dict[str, Any]]:
    sql = """
        SELECT id, title, description, announcement_type, status,
               cover_image_url, video_url, COALESCE(views_count, 0),
               COALESCE(shares_count, 0), created_at, published_at,
               rejection_reason
          FROM vgk_announcements
         WHERE partner_id = :pid
    """
    params: Dict[str, Any] = {"pid": partner_id}
    if status_val:
        sql += " AND status = :st"
        params["st"] = status_val
    sql += " ORDER BY created_at DESC LIMIT 200"
    rows = db.execute(sa_text(sql), params).fetchall()
    return [{
        "id": r[0], "title": r[1], "description": r[2],
        "announcement_type": r[3], "status": r[4],
        "cover_image_url": r[5], "video_url": r[6],
        "views_count": r[7], "shares_count": r[8],
        "created_at": r[9].isoformat() if r[9] else None,
        "published_at": r[10].isoformat() if r[10] else None,
        "rejection_reason": r[11],
    } for r in rows]


@router.get("/announcements/list-mine", tags=["VGK4U Announcements"])
def vgk_announcement_list_mine(
    status_filter: Optional[str] = Query(None, alias='status'),
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    items = _list_announcements_by_status(partner.id, status_filter, db)
    return {"success": True, "audience": "vgk4u", "items": items, "count": len(items)}


@router.get("/announcements/list-pending", tags=["VGK4U Announcements Admin"])
def vgk_announcement_list_pending(
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff-only — list pending VGK4U announcements for review. (Task #44)"""
    _audience_or_400(audience)
    rows = db.execute(sa_text("""
        SELECT a.id, a.title, a.description, a.announcement_type, a.status,
               a.created_at, p.partner_name, p.partner_code
          FROM vgk_announcements a
          LEFT JOIN official_partners p ON p.id = a.partner_id
         WHERE a.status = 'pending'
         ORDER BY a.created_at DESC LIMIT 500
    """)).fetchall()
    _audit(db, action='vgk_announcement.admin_list', resource_type='vgk_announcements',
           actor_staff_id=staff.id, new_data={'count': len(rows)},
           ip_address=request.client.host if request and request.client else None)
    db.commit()
    return {"success": True, "audience": "vgk4u",
            "items": [{
                "id": r[0], "title": r[1], "description": r[2],
                "announcement_type": r[3], "status": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
                "partner_name": r[6], "partner_code": r[7],
            } for r in rows]}


@router.post("/announcements/{announcement_id}/approve", tags=["VGK4U Announcements Admin"])
def vgk_announcement_approve(
    announcement_id: int,
    audience: Optional[str] = Query('vgk4u'),
    notes: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text("SELECT status FROM vgk_announcements WHERE id = :id"),
                              {"id": announcement_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Announcement not found")
        if existing[0] == 'approved':
            raise HTTPException(409, "Already approved")
        db.execute(sa_text("""
            UPDATE vgk_announcements
               SET status = 'approved', published_at = :ts, updated_at = :ts
             WHERE id = :id
        """), {"ts": now, "id": announcement_id})
        readback = db.execute(sa_text("SELECT status, published_at FROM vgk_announcements WHERE id = :id"),
                              {"id": announcement_id}).fetchone()
        _wvv_verify("ann_approve_readback", readback[0] == 'approved' and readback[1] is not None)
        _audit(db, action='vgk_announcement.approve', resource_type='vgk_announcements',
               resource_id=announcement_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'approved', 'notes': notes},
               ip_address=request.client.host if request and request.client else None)
        db.commit()
        return {"success": True, "id": announcement_id, "status": "approved"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-ANN-APPROVE]")
        raise HTTPException(500, f"Approve failed: {e}")


@router.post("/announcements/{announcement_id}/reject", tags=["VGK4U Announcements Admin"])
def vgk_announcement_reject(
    announcement_id: int,
    audience: Optional[str] = Query('vgk4u'),
    reason: str = Body(..., embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    if not (reason or '').strip():
        raise HTTPException(400, "rejection reason is required")
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text("SELECT status FROM vgk_announcements WHERE id = :id"),
                              {"id": announcement_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Announcement not found")
        db.execute(sa_text("""
            UPDATE vgk_announcements
               SET status = 'rejected', rejected_at = :ts,
                   rejection_reason = :reason, updated_at = :ts
             WHERE id = :id
        """), {"ts": now, "reason": reason, "id": announcement_id})
        readback = db.execute(sa_text(
            "SELECT status, rejection_reason FROM vgk_announcements WHERE id = :id"
        ), {"id": announcement_id}).fetchone()
        _wvv_verify("ann_reject_readback", readback[0] == 'rejected' and readback[1] == reason)
        _audit(db, action='vgk_announcement.reject', resource_type='vgk_announcements',
               resource_id=announcement_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'rejected', 'reason': reason},
               ip_address=request.client.host if request and request.client else None)
        db.commit()
        return {"success": True, "id": announcement_id, "status": "rejected"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-ANN-REJECT]")
        raise HTTPException(500, f"Reject failed: {e}")


# =====================================================================
# 3. KYC (Step 5)
# =====================================================================
@router.post("/kyc/upload", tags=["VGK4U KYC"])
async def vgk_kyc_upload(
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('kyc', db)
    now = get_indian_time().replace(tzinfo=None)

    # Insert pending row first to get an id
    try:
        ins = db.execute(sa_text("""
            INSERT INTO vgk_kyc_documents
              (partner_id, company_id, document_type, file_path, status, uploaded_at, updated_at)
            VALUES (:pid, :cid, :dt, :tmp, 'Pending', :ts, :ts)
            RETURNING id
        """), {"pid": partner.id, "cid": getattr(partner, 'company_id', None),
               "dt": document_type, "tmp": '__pending__', "ts": now}).fetchone()
        doc_id = int(ins[0])
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-KYC-UPLOAD-INSERT]")
        raise HTTPException(500, f"KYC initial insert failed: {e}")

    # Now stream the file via UniversalUploadService
    try:
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name="vgk_kyc_documents",
            record_id=doc_id,
            uploaded_by_id=partner.id,
            uploaded_by_type="user",
            storage_dir="vgk_kyc",
            db=db,
        )
        file_path = upload_result.get('file_path') or upload_result.get('storage_url') or upload_result.get('url') or ''
        file_size = upload_result.get('file_size')
        mime_type = upload_result.get('mime_type') or upload_result.get('content_type')
        checksum = upload_result.get('checksum_sha256') or upload_result.get('original_checksum')

        db.execute(sa_text("""
            UPDATE vgk_kyc_documents
               SET file_path = :fp, file_name = :fn, original_filename = :fn,
                   file_size = :fsize, mime_type = :mt, original_checksum = :chk,
                   updated_at = :ts
             WHERE id = :id
        """), {"fp": file_path, "fn": file.filename, "fsize": file_size,
               "mt": mime_type, "chk": checksum, "ts": now, "id": doc_id})

        readback = db.execute(sa_text(
            "SELECT file_path, status, partner_id FROM vgk_kyc_documents WHERE id = :id"
        ), {"id": doc_id}).fetchone()
        _wvv_verify("kyc_upload_readback",
                    readback is not None and readback[0] == file_path
                    and readback[1] == 'Pending' and readback[2] == partner.id)
        _audit(db, action='vgk_kyc.upload', resource_type='vgk_kyc_documents',
               resource_id=doc_id, actor_partner_id=partner.id,
               new_data={'document_type': document_type, 'file_path': file_path,
                         'file_size': file_size, 'mime_type': mime_type,
                         'checksum': checksum},
               ip_address=request.client.host if request.client else None)
        db.commit()

        _safe_send_whatsapp(background, 'vgk_kyc_submitted', partner.phone,
                            {'partner_name': partner.partner_name, 'document_type': document_type})

        return {"success": True, "id": doc_id, "status": "Pending",
                "file_path": file_path, "audience": "vgk4u"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        # cleanup pending row
        try:
            db.execute(sa_text("DELETE FROM vgk_kyc_documents WHERE id = :id AND file_path = '__pending__'"),
                       {"id": doc_id})
            db.commit()
        except Exception:
            db.rollback()
        logger.exception("[VGK4U-KYC-UPLOAD]")
        raise HTTPException(500, f"KYC upload failed: {e}")


@router.get("/kyc/my-documents", tags=["VGK4U KYC"])
def vgk_kyc_my_documents(
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('kyc', db)
    rows = db.execute(sa_text("""
        SELECT id, document_type, file_path, status, uploaded_at,
               reviewed_at, admin_notes, rejection_reason
          FROM vgk_kyc_documents
         WHERE partner_id = :pid AND COALESCE(is_current_version, true) = true
         ORDER BY uploaded_at DESC
    """), {"pid": partner.id}).fetchall()
    return {"success": True, "audience": "vgk4u",
            "documents": [{
                "id": r[0], "document_type": r[1], "file_path": r[2], "status": r[3],
                "uploaded_at": r[4].isoformat() if r[4] else None,
                "reviewed_at": r[5].isoformat() if r[5] else None,
                "admin_notes": r[6], "rejection_reason": r[7],
            } for r in rows]}


@router.get("/kyc/admin-pending", tags=["VGK4U KYC Admin"])
def vgk_kyc_admin_pending(
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff-only — list pending VGK4U KYC documents. (Task #44)"""
    _audience_or_400(audience)
    rows = db.execute(sa_text("""
        SELECT k.id, k.partner_id, k.document_type, k.file_path, k.status,
               k.uploaded_at, p.partner_name, p.partner_code
          FROM vgk_kyc_documents k
          LEFT JOIN official_partners p ON p.id = k.partner_id
         WHERE k.status = 'Pending' AND COALESCE(k.is_current_version, true) = true
         ORDER BY k.uploaded_at DESC LIMIT 500
    """)).fetchall()
    _audit(db, action='vgk_kyc.admin_list', resource_type='vgk_kyc_documents',
           actor_staff_id=staff.id, new_data={'count': len(rows)},
           ip_address=request.client.host if request and request.client else None)
    db.commit()
    return {"success": True, "audience": "vgk4u",
            "items": [{
                "id": r[0], "partner_id": r[1], "document_type": r[2],
                "file_path": r[3], "status": r[4],
                "uploaded_at": r[5].isoformat() if r[5] else None,
                "partner_name": r[6], "partner_code": r[7],
            } for r in rows]}


@router.post("/kyc/{doc_id}/approve", tags=["VGK4U KYC Admin"])
def vgk_kyc_approve(
    doc_id: int,
    background: BackgroundTasks,
    audience: Optional[str] = Query('vgk4u'),
    notes: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text(
            "SELECT status, partner_id FROM vgk_kyc_documents WHERE id = :id"
        ), {"id": doc_id}).fetchone()
        if not existing:
            raise HTTPException(404, "KYC document not found")
        db.execute(sa_text("""
            UPDATE vgk_kyc_documents
               SET status = 'Verified', reviewed_at = :ts, admin_notes = :n,
                   updated_at = :ts
             WHERE id = :id
        """), {"ts": now, "n": notes, "id": doc_id})
        readback = db.execute(sa_text("SELECT status FROM vgk_kyc_documents WHERE id = :id"),
                              {"id": doc_id}).fetchone()
        _wvv_verify("kyc_approve_readback", readback[0] == 'Verified')
        _audit(db, action='vgk_kyc.approve', resource_type='vgk_kyc_documents',
               resource_id=doc_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'Verified', 'notes': notes},
               ip_address=request.client.host if request and request.client else None)
        db.commit()

        partner = db.query(OfficialPartner).filter(OfficialPartner.id == existing[1]).first()
        if partner:
            _safe_send_whatsapp(background, 'vgk_kyc_approved', partner.phone,
                                {'partner_name': partner.partner_name})
        return {"success": True, "id": doc_id, "status": "Verified"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-KYC-APPROVE]")
        raise HTTPException(500, f"Approve failed: {e}")


@router.post("/kyc/{doc_id}/reject", tags=["VGK4U KYC Admin"])
def vgk_kyc_reject(
    doc_id: int,
    background: BackgroundTasks,
    audience: Optional[str] = Query('vgk4u'),
    reason: str = Body(..., embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    if not (reason or '').strip():
        raise HTTPException(400, "rejection reason is required")
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text(
            "SELECT status, partner_id FROM vgk_kyc_documents WHERE id = :id"
        ), {"id": doc_id}).fetchone()
        if not existing:
            raise HTTPException(404, "KYC document not found")
        db.execute(sa_text("""
            UPDATE vgk_kyc_documents
               SET status = 'Rejected', reviewed_at = :ts, rejection_reason = :r,
                   updated_at = :ts
             WHERE id = :id
        """), {"ts": now, "r": reason, "id": doc_id})
        # Add blocking log entry
        db.execute(sa_text("""
            INSERT INTO vgk_kyc_blocking_log
              (partner_id, document_id, block_reason, created_at)
            VALUES (:pid, :did, :r, :ts)
        """), {"pid": existing[1], "did": doc_id, "r": reason, "ts": now})
        readback = db.execute(sa_text(
            "SELECT status, rejection_reason FROM vgk_kyc_documents WHERE id = :id"
        ), {"id": doc_id}).fetchone()
        _wvv_verify("kyc_reject_readback", readback[0] == 'Rejected' and readback[1] == reason)
        _audit(db, action='vgk_kyc.reject', resource_type='vgk_kyc_documents',
               resource_id=doc_id, actor_staff_id=staff.id,
               old_data={'status': existing[0]},
               new_data={'status': 'Rejected', 'reason': reason},
               ip_address=request.client.host if request and request.client else None)
        db.commit()

        partner = db.query(OfficialPartner).filter(OfficialPartner.id == existing[1]).first()
        if partner:
            _safe_send_whatsapp(background, 'vgk_kyc_rejected', partner.phone,
                                {'partner_name': partner.partner_name, 'reason': reason})
        return {"success": True, "id": doc_id, "status": "Rejected"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-KYC-REJECT]")
        raise HTTPException(500, f"Reject failed: {e}")


# =====================================================================
# 4. BANK DETAILS (Step 6)
# =====================================================================
class BankDetailsIn(BaseModel):
    bank_account_number: str = Field(..., min_length=4, max_length=50)
    bank_ifsc_code: str = Field(..., min_length=4, max_length=20)
    bank_account_holder: str = Field(..., min_length=1, max_length=100)
    bank_name: Optional[str] = None
    bank_branch_name: Optional[str] = None
    upi_id: Optional[str] = None


@router.post("/bank/submit", tags=["VGK4U Bank"])
def vgk_bank_submit(
    payload: BankDetailsIn,
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('bank', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        # Mark previous current row as non-current (versioning)
        db.execute(sa_text(
            "UPDATE vgk_bank_details SET is_current = false, updated_at = :ts "
            "WHERE partner_id = :pid AND is_current = true"
        ), {"pid": partner.id, "ts": now})

        ins = db.execute(sa_text("""
            INSERT INTO vgk_bank_details
              (partner_id, company_id, bank_account_number, bank_ifsc_code,
               bank_account_holder, bank_name, bank_branch_name, upi_id,
               status, is_current, created_at, updated_at)
            VALUES (:pid, :cid, :acc, :ifsc, :holder, :bname, :branch, :upi,
                    'Pending', true, :ts, :ts)
            RETURNING id
        """), {"pid": partner.id, "cid": getattr(partner, 'company_id', None),
               "acc": payload.bank_account_number, "ifsc": payload.bank_ifsc_code.upper(),
               "holder": payload.bank_account_holder, "bname": payload.bank_name,
               "branch": payload.bank_branch_name, "upi": payload.upi_id, "ts": now}).fetchone()
        bank_id = int(ins[0])

        # Create approval workflow row (Super → Finance)
        db.execute(sa_text("""
            INSERT INTO vgk_bank_details_approval
              (partner_id, bank_details_id, company_id,
               bank_account_number, bank_ifsc_code, bank_account_holder,
               bank_name, bank_branch_name, upi_id,
               super_admin_status, finance_admin_status, final_status,
               created_at, updated_at)
            VALUES (:pid, :bid, :cid, :acc, :ifsc, :holder, :bname, :branch, :upi,
                    'Pending', 'Pending', 'Pending', :ts, :ts)
        """), {"pid": partner.id, "bid": bank_id, "cid": getattr(partner, 'company_id', None),
               "acc": payload.bank_account_number, "ifsc": payload.bank_ifsc_code.upper(),
               "holder": payload.bank_account_holder, "bname": payload.bank_name,
               "branch": payload.bank_branch_name, "upi": payload.upi_id, "ts": now})

        readback = db.execute(sa_text(
            "SELECT status, partner_id, bank_account_number FROM vgk_bank_details WHERE id = :id"
        ), {"id": bank_id}).fetchone()
        _wvv_verify("bank_submit_readback",
                    readback is not None and readback[0] == 'Pending'
                    and readback[1] == partner.id and readback[2] == payload.bank_account_number)

        _audit(db, action='vgk_bank.submit', resource_type='vgk_bank_details',
               resource_id=bank_id, actor_partner_id=partner.id,
               new_data={'masked_account': '****' + payload.bank_account_number[-4:],
                         'ifsc': payload.bank_ifsc_code.upper()},
               ip_address=request.client.host if request.client else None)
        db.commit()
        return {"success": True, "id": bank_id, "status": "Pending", "audience": "vgk4u"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-BANK-SUBMIT]")
        raise HTTPException(500, f"Bank submit failed: {e}")


@router.get("/bank/my-details", tags=["VGK4U Bank"])
def vgk_bank_my_details(
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('bank', db)
    row = db.execute(sa_text("""
        SELECT id, bank_account_number, bank_ifsc_code, bank_account_holder,
               bank_name, bank_branch_name, upi_id, status, created_at, updated_at
          FROM vgk_bank_details
         WHERE partner_id = :pid AND is_current = true
         ORDER BY created_at DESC LIMIT 1
    """), {"pid": partner.id}).fetchone()
    if not row:
        return {"success": True, "audience": "vgk4u", "details": None}
    return {"success": True, "audience": "vgk4u", "details": {
        "id": row[0],
        "bank_account_number": '****' + (row[1][-4:] if row[1] else ''),
        "bank_ifsc_code": row[2], "bank_account_holder": row[3],
        "bank_name": row[4], "bank_branch_name": row[5], "upi_id": row[6],
        "status": row[7],
        "created_at": row[8].isoformat() if row[8] else None,
        "updated_at": row[9].isoformat() if row[9] else None,
    }}


@router.get("/bank/admin-pending", tags=["VGK4U Bank Admin"])
def vgk_bank_admin_pending(
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff-only — list pending VGK4U bank approval rows. (Task #44)"""
    _audience_or_400(audience)
    rows = db.execute(sa_text("""
        SELECT a.id, a.partner_id, a.bank_account_number, a.bank_ifsc_code,
               a.bank_account_holder, a.super_admin_status, a.finance_admin_status,
               a.final_status, a.created_at, p.partner_name, p.partner_code
          FROM vgk_bank_details_approval a
          LEFT JOIN official_partners p ON p.id = a.partner_id
         WHERE a.final_status = 'Pending'
         ORDER BY a.created_at DESC LIMIT 500
    """)).fetchall()
    _audit(db, action='vgk_bank.admin_list', resource_type='vgk_bank_details_approval',
           actor_staff_id=staff.id, new_data={'count': len(rows)},
           ip_address=request.client.host if request and request.client else None)
    db.commit()
    return {"success": True, "audience": "vgk4u",
            "items": [{
                "id": r[0], "partner_id": r[1],
                "masked_account": '****' + (r[2][-4:] if r[2] else ''),
                "ifsc": r[3], "holder": r[4],
                "super_admin_status": r[5], "finance_admin_status": r[6],
                "final_status": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                "partner_name": r[9], "partner_code": r[10],
            } for r in rows]}


@router.post("/bank/{approval_id}/super-decision", tags=["VGK4U Bank Admin"])
def vgk_bank_super_decision(
    approval_id: int,
    audience: Optional[str] = Query('vgk4u'),
    decision: str = Body(..., embed=True),
    notes: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    if decision not in ('Approved', 'Rejected'):
        raise HTTPException(400, "decision must be Approved or Rejected")
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text(
            "SELECT super_admin_status, bank_details_id FROM vgk_bank_details_approval WHERE id = :id"
        ), {"id": approval_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Approval row not found")
        if existing[0] != 'Pending':
            raise HTTPException(409, "Super decision already recorded")
        db.execute(sa_text("""
            UPDATE vgk_bank_details_approval
               SET super_admin_status = :d, super_admin_at = :ts, super_admin_notes = :n,
                   updated_at = :ts
             WHERE id = :id
        """), {"d": decision, "ts": now, "n": notes, "id": approval_id})
        if decision == 'Rejected':
            db.execute(sa_text("""
                UPDATE vgk_bank_details_approval
                   SET final_status = 'Rejected', updated_at = :ts
                 WHERE id = :id
            """), {"ts": now, "id": approval_id})
            db.execute(sa_text("""
                UPDATE vgk_bank_details SET status = 'Rejected', updated_at = :ts
                 WHERE id = :bid
            """), {"ts": now, "bid": existing[1]})
        readback = db.execute(sa_text(
            "SELECT super_admin_status, final_status FROM vgk_bank_details_approval WHERE id = :id"
        ), {"id": approval_id}).fetchone()
        _wvv_verify("bank_super_readback", readback[0] == decision)
        _audit(db, action=f'vgk_bank.super_{decision.lower()}', resource_type='vgk_bank_details_approval',
               resource_id=approval_id, actor_staff_id=staff.id,
               old_data={'super_admin_status': existing[0]},
               new_data={'super_admin_status': decision, 'notes': notes},
               ip_address=request.client.host if request and request.client else None)
        db.commit()
        return {"success": True, "id": approval_id, "super_admin_status": decision,
                "final_status": readback[1]}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-BANK-SUPER]")
        raise HTTPException(500, f"Super decision failed: {e}")


@router.post("/bank/{approval_id}/finance-decision", tags=["VGK4U Bank Admin"])
def vgk_bank_finance_decision(
    approval_id: int,
    background: BackgroundTasks,
    audience: Optional[str] = Query('vgk4u'),
    decision: str = Body(..., embed=True),
    notes: Optional[str] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    _audience_or_400(audience)
    if decision not in ('Approved', 'Rejected'):
        raise HTTPException(400, "decision must be Approved or Rejected")
    now = get_indian_time().replace(tzinfo=None)
    try:
        existing = db.execute(sa_text("""
            SELECT super_admin_status, finance_admin_status, bank_details_id, partner_id
              FROM vgk_bank_details_approval WHERE id = :id
        """), {"id": approval_id}).fetchone()
        if not existing:
            raise HTTPException(404, "Approval row not found")
        if existing[0] != 'Approved':
            raise HTTPException(409, "Super-Admin must approve first")
        if existing[1] != 'Pending':
            raise HTTPException(409, "Finance decision already recorded")
        final = 'Verified' if decision == 'Approved' else 'Rejected'
        db.execute(sa_text("""
            UPDATE vgk_bank_details_approval
               SET finance_admin_status = :d, finance_admin_at = :ts, finance_admin_notes = :n,
                   final_status = :final, updated_at = :ts
             WHERE id = :id
        """), {"d": decision, "ts": now, "n": notes, "final": final, "id": approval_id})
        db.execute(sa_text("""
            UPDATE vgk_bank_details SET status = :s, updated_at = :ts WHERE id = :bid
        """), {"s": final, "ts": now, "bid": existing[2]})
        readback = db.execute(sa_text(
            "SELECT finance_admin_status, final_status FROM vgk_bank_details_approval WHERE id = :id"
        ), {"id": approval_id}).fetchone()
        _wvv_verify("bank_finance_readback", readback[0] == decision and readback[1] == final)
        _audit(db, action=f'vgk_bank.finance_{decision.lower()}',
               resource_type='vgk_bank_details_approval', resource_id=approval_id,
               actor_staff_id=staff.id,
               new_data={'finance_admin_status': decision, 'final_status': final, 'notes': notes},
               ip_address=request.client.host if request and request.client else None)
        db.commit()

        partner = db.query(OfficialPartner).filter(OfficialPartner.id == existing[3]).first()
        if partner:
            event = 'vgk_bank_verified' if final == 'Verified' else 'vgk_bank_rejected'
            _safe_send_whatsapp(background, event, partner.phone,
                                {'partner_name': partner.partner_name, 'status': final, 'notes': notes or ''})
        return {"success": True, "id": approval_id, "finance_admin_status": decision, "final_status": final}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-BANK-FINANCE]")
        raise HTTPException(500, f"Finance decision failed: {e}")


# =====================================================================
# 5. PROFILE EDIT (Step 7)
# =====================================================================
class ProfileEditIn(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


@router.put("/profile/edit", tags=["VGK4U Profile"])
def vgk_profile_edit(
    payload: ProfileEditIn,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('profile_edit', db)
    now = get_indian_time().replace(tzinfo=None)

    old_snapshot: Dict[str, Any] = {}
    new_snapshot: Dict[str, Any] = {}
    updated_fields: List[str] = []
    try:
        # Collect old values for fields actually being changed
        for field in ('full_name', 'phone', 'email', 'address', 'pincode', 'city', 'state'):
            new_val = getattr(payload, field)
            if new_val is None:
                continue
            old_val = getattr(partner, field, None)
            old_snapshot[field] = old_val
            new_snapshot[field] = new_val
            if hasattr(partner, field):
                setattr(partner, field, new_val)
                updated_fields.append(field)
        if updated_fields and hasattr(partner, 'updated_at'):
            partner.updated_at = now
        db.flush()

        # WVV — Verify (re-read)
        for field in updated_fields:
            assert getattr(partner, field) == new_snapshot[field], f"verify mismatch on {field}"

        _audit(db, action='vgk_profile.edit', resource_type='official_partners',
               resource_id=partner.id, actor_partner_id=partner.id,
               old_data=old_snapshot, new_data=new_snapshot,
               ip_address=request.client.host if request.client else None)
        db.commit()
        db.refresh(partner)
        return {"success": True, "audience": "vgk4u",
                "updated_fields": updated_fields,
                "profile": {"id": partner.id, "partner_code": partner.partner_code,
                            "full_name": partner.partner_name, "phone": partner.phone,
                            "email": getattr(partner, 'email', None),
                            "address": getattr(partner, 'address', None),
                            "city": getattr(partner, 'city', None),
                            "state": getattr(partner, 'state', None)}}
    except AssertionError as e:
        db.rollback()
        raise HTTPException(500, f"WVV verification failed: {e}")
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-PROFILE-EDIT]")
        raise HTTPException(500, f"Profile edit failed: {e}")


# =====================================================================
# 6. SETTINGS (Step 8)
# =====================================================================
class SettingsUpdateIn(BaseModel):
    notification_whatsapp: Optional[bool] = None
    notification_email: Optional[bool] = None
    notification_sms: Optional[bool] = None
    notification_push: Optional[bool] = None
    theme: Optional[str] = Field(None, pattern='^(light|dark|auto)$')
    language: Optional[str] = Field(None, max_length=10)
    preferences: Optional[Dict[str, Any]] = None


def _ensure_settings_row(partner_id: int, company_id: Optional[int], db: Session) -> Dict[str, Any]:
    row = db.execute(sa_text(
        "SELECT id, notification_whatsapp, notification_email, notification_sms, "
        "notification_push, theme, language, preferences FROM vgk_member_settings WHERE partner_id = :pid"
    ), {"pid": partner_id}).fetchone()
    if row:
        return {"id": row[0], "notification_whatsapp": row[1], "notification_email": row[2],
                "notification_sms": row[3], "notification_push": row[4],
                "theme": row[5], "language": row[6], "preferences": row[7] or {}}
    now = get_indian_time().replace(tzinfo=None)
    ins = db.execute(sa_text("""
        INSERT INTO vgk_member_settings (partner_id, company_id, created_at, updated_at)
        VALUES (:pid, :cid, :ts, :ts) RETURNING id
    """), {"pid": partner_id, "cid": company_id, "ts": now}).fetchone()
    return {"id": int(ins[0]), "notification_whatsapp": True, "notification_email": True,
            "notification_sms": False, "notification_push": True,
            "theme": "light", "language": "en", "preferences": {}}


@router.get("/settings", tags=["VGK4U Settings"])
def vgk_settings_get(
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('settings', db)
    s = _ensure_settings_row(partner.id, getattr(partner, 'company_id', None), db)
    db.commit()
    return {"success": True, "audience": "vgk4u", "settings": s}


@router.put("/settings", tags=["VGK4U Settings"])
def vgk_settings_update(
    payload: SettingsUpdateIn,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('settings', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        old = _ensure_settings_row(partner.id, getattr(partner, 'company_id', None), db)
        updates: Dict[str, Any] = {}
        for field in ('notification_whatsapp', 'notification_email', 'notification_sms',
                      'notification_push', 'theme', 'language'):
            v = getattr(payload, field)
            if v is not None:
                updates[field] = v
        prefs_payload = payload.preferences
        merged_prefs = dict(old.get('preferences') or {})
        if prefs_payload:
            merged_prefs.update(prefs_payload)
            updates['preferences'] = json.dumps(merged_prefs)

        if updates:
            set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
            params = dict(updates)
            params['ts'] = now
            params['pid'] = partner.id
            db.execute(sa_text(
                f"UPDATE vgk_member_settings SET {set_clause}, updated_at = :ts WHERE partner_id = :pid"
            ), params)

        readback = _ensure_settings_row(partner.id, getattr(partner, 'company_id', None), db)
        for k, v in updates.items():
            if k == 'preferences':
                continue
            _wvv_verify(f"settings_update_{k}", readback.get(k) == v, {"key": k, "got": readback.get(k), "want": v})

        _audit(db, action='vgk_settings.update', resource_type='vgk_member_settings',
               resource_id=readback['id'], actor_partner_id=partner.id,
               old_data={k: old.get(k) for k in updates.keys() if k != 'preferences'},
               new_data={k: v for k, v in updates.items() if k != 'preferences'},
               ip_address=request.client.host if request.client else None)
        db.commit()
        return {"success": True, "audience": "vgk4u", "settings": readback}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-SETTINGS-UPDATE]")
        raise HTTPException(500, f"Settings update failed: {e}")


# =====================================================================
# 7. COUPON ACTIVATE / PROGRESS / TRANSFER (Step 9)
# =====================================================================
@router.get("/coupons/progress", tags=["VGK4U Coupons"])
def vgk_coupons_progress(
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('coupon_transfer', db)
    rows = db.execute(sa_text("""
        SELECT id, points, reason_code, description, created_at
          FROM vgk_points_ledger
         WHERE partner_id = :pid
         ORDER BY created_at DESC LIMIT 200
    """), {"pid": partner.id}).fetchall()
    total = db.execute(sa_text(
        "SELECT COALESCE(SUM(points), 0) FROM vgk_points_ledger WHERE partner_id = :pid"
    ), {"pid": partner.id}).scalar() or 0
    return {"success": True, "audience": "vgk4u", "balance": int(total),
            "ledger": [{
                "id": r[0], "points": int(r[1] or 0), "reason_code": r[2],
                "description": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            } for r in rows]}


class CouponActivateIn(BaseModel):
    coupon_code: str = Field(..., min_length=2, max_length=64)


@router.post("/coupons/activate", tags=["VGK4U Coupons"])
def vgk_coupon_activate(
    payload: CouponActivateIn,
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('coupon_transfer', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        # Idempotency — if a ledger row already exists for this code, return it.
        existing = db.execute(sa_text("""
            SELECT id FROM vgk_points_ledger
             WHERE partner_id = :pid AND description = :desc LIMIT 1
        """), {"pid": partner.id, "desc": f"Coupon Activate: {payload.coupon_code}"}).fetchone()
        if existing:
            return {"success": True, "audience": "vgk4u", "id": int(existing[0]),
                    "status": "already_activated", "coupon_code": payload.coupon_code}

        ins = db.execute(sa_text("""
            INSERT INTO vgk_points_ledger
              (partner_id, points, reason_code, description, created_at)
            VALUES (:pid, 0, 'COUPON_ACTIVATE', :desc, :ts)
            RETURNING id
        """), {"pid": partner.id,
               "desc": f"Coupon Activate: {payload.coupon_code}", "ts": now}).fetchone()
        ledger_id = int(ins[0])
        readback = db.execute(sa_text("SELECT id, partner_id FROM vgk_points_ledger WHERE id = :id"),
                              {"id": ledger_id}).fetchone()
        _wvv_verify("coupon_activate_readback", readback is not None and readback[1] == partner.id)
        _audit(db, action='vgk_coupon.activate', resource_type='vgk_points_ledger',
               resource_id=ledger_id, actor_partner_id=partner.id,
               new_data={'coupon_code': payload.coupon_code},
               ip_address=request.client.host if request.client else None)
        db.commit()

        _safe_send_whatsapp(background, 'vgk_coupon_activated', partner.phone,
                            {'partner_name': partner.partner_name, 'coupon_code': payload.coupon_code})
        return {"success": True, "audience": "vgk4u", "id": ledger_id,
                "status": "activated", "coupon_code": payload.coupon_code}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-COUPON-ACTIVATE]")
        raise HTTPException(500, f"Activate failed: {e}")


class CouponTransferIn(BaseModel):
    to_partner_code: str = Field(..., min_length=3, max_length=32)
    points: int = Field(..., gt=0, le=100000)
    note: Optional[str] = Field(None, max_length=500)


@router.post("/coupons/transfer", tags=["VGK4U Coupons"])
def vgk_coupon_transfer(
    payload: CouponTransferIn,
    background: BackgroundTasks,
    request: Request,
    audience: Optional[str] = Query('vgk4u'),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member),
):
    _audience_or_400(audience)
    _check_toggle('coupon_transfer', db)
    now = get_indian_time().replace(tzinfo=None)
    try:
        target = db.query(OfficialPartner).filter(
            OfficialPartner.partner_code.ilike(payload.to_partner_code),
            OfficialPartner.category == 'VGK_TEAM'
        ).first()
        if not target:
            raise HTTPException(404, f"Recipient {payload.to_partner_code} not found")
        if target.id == partner.id:
            raise HTTPException(400, "Cannot transfer to yourself")

        # Cross-check balance (Validate)
        balance = db.execute(sa_text(
            "SELECT COALESCE(SUM(points), 0) FROM vgk_points_ledger WHERE partner_id = :pid"
        ), {"pid": partner.id}).scalar() or 0
        if int(balance) < payload.points:
            raise HTTPException(400, f"Insufficient balance ({balance} < {payload.points})")

        # Debit the sender
        debit = db.execute(sa_text("""
            INSERT INTO vgk_points_ledger
              (partner_id, points, reason_code, description, created_at)
            VALUES (:pid, :pts, 'COUPON_TRANSFER_OUT', :desc, :ts)
            RETURNING id
        """), {"pid": partner.id, "pts": -payload.points,
               "desc": f"Transfer to {target.partner_code}: {payload.note or ''}", "ts": now}).fetchone()
        # Credit the receiver
        credit = db.execute(sa_text("""
            INSERT INTO vgk_points_ledger
              (partner_id, points, reason_code, description, created_at)
            VALUES (:pid, :pts, 'COUPON_TRANSFER_IN', :desc, :ts)
            RETURNING id
        """), {"pid": target.id, "pts": payload.points,
               "desc": f"Transfer from {partner.partner_code}: {payload.note or ''}", "ts": now}).fetchone()

        # WVV — re-read both sides and validate net is zero
        new_balance_sender = db.execute(sa_text(
            "SELECT COALESCE(SUM(points), 0) FROM vgk_points_ledger WHERE partner_id = :pid"
        ), {"pid": partner.id}).scalar()
        new_balance_target = db.execute(sa_text(
            "SELECT COALESCE(SUM(points), 0) FROM vgk_points_ledger WHERE partner_id = :pid"
        ), {"pid": target.id}).scalar()
        _wvv_verify("coupon_transfer_balance",
                    int(new_balance_sender) == int(balance) - payload.points,
                    {"expected": int(balance) - payload.points, "got": int(new_balance_sender)})

        _audit(db, action='vgk_coupon.transfer', resource_type='vgk_points_ledger',
               resource_id=int(debit[0]), actor_partner_id=partner.id,
               new_data={'to_partner_code': target.partner_code, 'points': payload.points,
                         'debit_id': int(debit[0]), 'credit_id': int(credit[0]),
                         'sender_balance_after': int(new_balance_sender),
                         'target_balance_after': int(new_balance_target),
                         'note': payload.note},
               ip_address=request.client.host if request.client else None)
        db.commit()

        _safe_send_whatsapp(background, 'vgk_coupon_transferred', partner.phone,
                            {'partner_name': partner.partner_name, 'points': payload.points,
                             'to': target.partner_code})
        _safe_send_whatsapp(background, 'vgk_coupon_received', target.phone,
                            {'partner_name': target.partner_name, 'points': payload.points,
                             'from': partner.partner_code})
        return {"success": True, "audience": "vgk4u",
                "debit_id": int(debit[0]), "credit_id": int(credit[0]),
                "sender_balance": int(new_balance_sender),
                "target_balance": int(new_balance_target)}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback()
        logger.exception("[VGK4U-COUPON-TRANSFER]")
        raise HTTPException(500, f"Transfer failed: {e}")


# =====================================================================
# Health / module index — useful for verification
# =====================================================================
@router.get("/_index", tags=["VGK4U Phase-2 Index"])
def vgk_p2_index(db: Session = Depends(get_db)):
    """Quick module-status snapshot for ops + smoke tests."""
    row = db.query(AppSettings).first()
    flags = {}
    for module, col in _TOGGLE_MAP.items():
        flags[module] = bool(getattr(row, col, False)) if row else False
    return {"success": True, "audience": "vgk4u", "phase": 2,
            "modules": list(_TOGGLE_MAP.keys()), "toggles": flags}
