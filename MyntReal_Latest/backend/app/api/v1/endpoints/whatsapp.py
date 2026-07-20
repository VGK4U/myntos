"""
WhatsApp Messaging API Endpoints
Handles WhatsApp OTP sending, message logging, and delivery tracking via Meta Cloud API
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid, get_current_user_any, get_current_staff_user_from_hybrid
from app.models.user import User
from app.models.whatsapp import WhatsAppControl, MessageLog
from app.models.system_control import AppSettings
from app.models.staff import StaffEmployee
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
import logging
import os
import requests

logger = logging.getLogger(__name__)

def _require_staff(current_user=Depends(get_current_user_hybrid), db: Session = Depends(get_db)):
    """Dependency: resolve to StaffEmployee or raise 401."""
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if staff is None:
        raise HTTPException(status_code=401, detail="Staff authentication required")
    return staff

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Messaging"])


# ===== Pydantic Schemas =====

class SendOTPRequest(BaseModel):
    mobile_number: str
    otp_code: str
    user_name: Optional[str] = None


class WhatsAppControlUpdate(BaseModel):
    action: str  # 'pause' or 'resume'
    reason: Optional[str] = "Development/Testing"


class MessageStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message_sid: Optional[str] = None
    mobile_number: Optional[str] = None
    message_type: Optional[str] = None
    current_status: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ===== WhatsApp Messaging Service =====

class WhatsAppService:
    """WhatsApp messaging service using Meta Cloud API"""
    
    def __init__(self, db: Session):
        self.db = db
        # [DC-WA-CREDS] Load from DB first, fallback to env vars
        from app.services.wa_credentials import get_wa_credentials
        creds = get_wa_credentials(db)
        self.access_token = creds["access_token"] or os.environ.get("META_WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = creds["phone_number_id"] or os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID")
        self.business_phone_number = "+918585852738"
    
    def is_whatsapp_paused(self):
        """Check if WhatsApp is paused by RVZ ID"""
        control = self.db.query(WhatsAppControl).first()
        return control.is_paused if control else False
    
    def send_otp(self, mobile_number: str, otp_code: str, user_name: str = None):
        """Send OTP via WhatsApp using Meta Cloud API"""
        
        if self.is_whatsapp_paused():
            return {
                'success': False,
                'message': 'WhatsApp messaging is paused for development/testing'
            }
        
        settings = self.db.query(AppSettings).first()
        if settings and not getattr(settings, 'whatsapp_enabled', True):
            return {
                'success': False,
                'message': 'WhatsApp messaging is globally disabled'
            }
        
        if self.access_token and self.phone_number_id:
            return self._send_via_meta_api(mobile_number, otp_code, user_name)
        else:
            print(f"📱 MOCK WHATSAPP: OTP {otp_code} to {mobile_number}")
            return {
                'success': True,
                'message': f'MOCK: WhatsApp OTP sent to {mobile_number}',
                'provider': 'MOCK_WHATSAPP'
            }
    
    def _normalize_phone(self, mobile_number: str) -> str:
        """[DC-OTP-TEMPLATE-001] Normalize phone to E.164 digits for Meta API (no + prefix).
        Indian 10-digit numbers (starting 6-9) are prefixed with country code 91.
        Already-international numbers (>10 digits or + prefix) are passed through unchanged.
        """
        digits = mobile_number.lstrip('+').strip()
        if len(digits) == 10 and digits[0] in '6789':
            digits = '91' + digits
        return digits

    def _send_via_meta_api(self, mobile_number: str, otp_code: str, user_name: str = None):
        """[DC-OTP-TEMPLATE-001] Send OTP via Meta Cloud API using approved AUTHENTICATION template 'otp'.
        Uses template instead of plain text — bypasses 24-hour session window restriction,
        ensuring delivery to all recipients including first-time contacts (signup, registration, password reset).
        Template body: *{{1}}* is your verification code. For your security, do not share this code.
        AUTHENTICATION category templates require the OTP in both the body component AND the
        button (sub_type=url, index=0) component that Meta auto-attaches as a "Copy Code" button.
        """
        recipient = self._normalize_phone(mobile_number)

        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # [DC-OTP-AUTH-FORMAT] AUTHENTICATION templates always have a Copy Code button.
        # Meta Cloud API requires the OTP code to be passed in both the body and the button component.
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": "otp",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": otp_code}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [
                            {"type": "text", "text": otp_code}
                        ]
                    }
                ]
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                # [DC-OTP-DEBUG] Log the full Meta error body for diagnosis
                logger.error(f"[DC-OTP-TEMPLATE-001] Meta API error body for {mobile_number}: {response.text}")
            response.raise_for_status()
            data = response.json()

            wamid = data.get("messages", [{}])[0].get("id", "")

            message_log = MessageLog(
                message_sid=wamid,
                message_type='whatsapp_otp',
                mobile_number=mobile_number,
                user_name=user_name,
                from_number=self.business_phone_number,
                to_number=mobile_number,
                provider='META_WHATSAPP',
                initial_status='sent',
                current_status='sent',
                sent_at=datetime.utcnow()
            )
            self.db.add(message_log)
            self.db.commit()

            return {
                'success': True,
                'message': f'WhatsApp OTP sent successfully to {mobile_number}',
                'message_sid': wamid,
                'delivery_status': 'sent'
            }
        except Exception as e:
            logger.error(f"[DC-OTP-TEMPLATE-001] Meta API OTP send failed for {mobile_number}: {e}")
            return {
                'success': False,
                'message': f'Failed to send WhatsApp OTP: {str(e)}'
            }


# ===== USER ENDPOINTS =====

@router.post("/send-otp")
async def send_whatsapp_otp(
    request: SendOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send OTP via WhatsApp"""
    service = WhatsAppService(db)
    result = service.send_otp(
        request.mobile_number,
        request.otp_code,
        request.user_name
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    return result


@router.get("/my-messages", response_model=List[MessageStatusResponse])
async def get_my_messages(
    limit: int = 100,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_any)
):
    """Get WhatsApp message history for the logged-in user's phone number.
    
    Works for both staff (StaffEmployee.phone) and MNR users (User.phone_number).
    Returns empty list when no phone is found instead of exposing full message log.
    """
    user_phone = (
        getattr(current_user, 'phone', None) or
        getattr(current_user, 'phone_number', None)
    )

    if not user_phone:
        return []

    norm = user_phone.lstrip('+')
    q = (
        db.query(MessageLog)
        .filter(
            (MessageLog.mobile_number == user_phone) |
            (MessageLog.mobile_number == ('+' + norm)) |
            (MessageLog.mobile_number == norm)
        )
    )
    if status:
        q = q.filter(MessageLog.current_status == status)
    if date_from:
        try:
            from datetime import datetime
            q = q.filter(MessageLog.sent_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            pass
    if date_to:
        try:
            from datetime import datetime, timedelta
            q = q.filter(MessageLog.sent_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except Exception:
            pass
    messages = q.order_by(desc(MessageLog.sent_at)).limit(limit).all()
    return messages


# ===== ADMIN ENDPOINTS =====

@router.post("/control")
async def control_whatsapp(
    control_request: WhatsAppControlUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Pause or resume WhatsApp messaging (RVZ ID only)"""
    
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
        raise HTTPException(
            status_code=403,
            detail="Only RVZ ID users can control WhatsApp messaging"
        )
    
    control = db.query(WhatsAppControl).first()
    if not control:
        control = WhatsAppControl()
        db.add(control)
    
    if control_request.action == 'pause':
        control.is_paused = True
        control.paused_by_user_id = current_user.id
        control.paused_at = datetime.utcnow()
        control.pause_reason = control_request.reason
        message = f"WhatsApp messaging paused by {current_user.name}"
    else:
        control.is_paused = False
        control.resumed_by_user_id = current_user.id
        control.resumed_at = datetime.utcnow()
        message = f"WhatsApp messaging resumed by {current_user.name}"
    
    db.commit()
    db.refresh(control)
    
    return {
        'success': True,
        'message': message,
        'is_paused': control.is_paused
    }


@router.get("/control/status")
async def get_whatsapp_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get current WhatsApp messaging status"""
    control = db.query(WhatsAppControl).first()
    
    if not control:
        return {
            'enabled': True,
            'paused': False,
            'status': 'Active - No controls set'
        }
    
    result = {
        'enabled': True,
        'paused': control.is_paused,
        'paused_at': control.paused_at,
        'resumed_at': control.resumed_at,
        'pause_reason': control.pause_reason
    }
    
    if control.paused_by_user_id:
        paused_by = db.query(User).filter(User.id == control.paused_by_user_id).first()
        result['paused_by'] = paused_by.name if paused_by else 'Unknown'
    
    if control.resumed_by_user_id:
        resumed_by = db.query(User).filter(User.id == control.resumed_by_user_id).first()
        result['resumed_by'] = resumed_by.name if resumed_by else 'Unknown'
    
    return result


@router.get("/messages/all")
async def get_all_messages(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all WhatsApp messages (Admin)"""
    query = db.query(MessageLog)
    
    if status_filter:
        query = query.filter(MessageLog.current_status == status_filter)
    
    messages = query.order_by(desc(MessageLog.sent_at)).offset(offset).limit(limit).all()
    
    return {
        'total': query.count(),
        'messages': messages
    }


@router.get("/messages/stats")
async def get_message_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    message_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get WhatsApp messaging statistics with optional date and type filters"""
    from datetime import datetime, timedelta

    def _base_q():
        q = db.query(func.count(MessageLog.id))
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
        if message_type:
            q = q.filter(MessageLog.message_type == message_type)
        return q

    total_sent = _base_q().scalar()
    delivered = _base_q().filter(MessageLog.current_status == 'delivered').scalar()
    failed = _base_q().filter(MessageLog.current_status == 'failed').scalar()
    pending = _base_q().filter(MessageLog.current_status.in_(['queued', 'sent'])).scalar()
    read_count = _base_q().filter(MessageLog.current_status == 'read').scalar()

    return {
        'total_sent': total_sent,
        'delivered': delivered,
        'failed': failed,
        'pending': pending,
        'read': read_count,
        'delivery_rate': round((delivered / total_sent * 100), 2) if total_sent > 0 else 0
    }


# ===== WEBHOOK ENDPOINTS =====

@router.get("/webhook/status")
async def meta_webhook_verify(request: Request):
    """
    Meta webhook verification endpoint (GET).
    Responds to Meta's hub challenge handshake to activate the webhook.
    Public endpoint - no authentication required.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    verify_token = os.environ.get("META_WHATSAPP_VERIFY_TOKEN", "")
    
    if mode == "subscribe" and token == verify_token:
        print(f"✅ Meta webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    print(f"❌ Meta webhook verification failed: mode={mode}, token_match={token == verify_token}")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook/status")
async def meta_status_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Meta Cloud API webhook for message status updates (POST).
    Processes delivery status from Meta's JSON body format.
    Public endpoint - no authentication required.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "invalid_body"}
    
    # Meta sends: entry[].changes[].value.statuses[]
    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            statuses = value.get("statuses", [])
            for status_update in statuses:
                wamid = status_update.get("id")
                meta_status = status_update.get("status")
                
                if not wamid or not meta_status:
                    continue
                
                # Map Meta status values to our stored status field
                status_map = {
                    "sent": "sent",
                    "delivered": "delivered",
                    "read": "read",
                    "failed": "failed"
                }
                mapped_status = status_map.get(meta_status, meta_status)
                
                message_log = db.query(MessageLog).filter(
                    MessageLog.message_sid == wamid
                ).first()
                
                if not message_log:
                    print(f"⚠️ Webhook: message not found for wamid {wamid}")
                    continue
                
                message_log.current_status = mapped_status
                message_log.last_status_update = datetime.utcnow()
                
                if mapped_status == 'delivered':
                    message_log.delivered_at = datetime.utcnow()
                elif mapped_status == 'failed':
                    message_log.failed_at = datetime.utcnow()
                    errors = status_update.get("errors", [])
                    if errors:
                        message_log.error_code = str(errors[0].get("code", ""))
                        message_log.error_message = errors[0].get("message", "")
                
                print(f"📨 Webhook: {wamid} → {mapped_status}")
    
    db.commit()
    return {"status": "success"}


# ── META CANONICAL WEBHOOK (path Meta actually calls) ──────────────────────────

@router.get("/webhook")
async def meta_webhook_verify_canonical(request: Request, db: Session = Depends(get_db)):
    """
    Meta canonical webhook verification — GET /api/v1/whatsapp/webhook
    Reads verify_token from DB first, falls back to env var.
    """
    from app.services.wa_credentials import get_wa_credentials
    params = request.query_params
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    db_creds = get_wa_credentials(db)
    verify_token = (
        (db_creds.get("verify_token") or "").strip()
        or os.environ.get("META_WHATSAPP_VERIFY_TOKEN", "")
    )

    print(f"[WA-WEBHOOK] verify attempt | mode={mode} | token_match={token == verify_token} | stored='{verify_token}'")

    if mode == "subscribe" and token == verify_token:
        print(f"[WA-WEBHOOK] ✅ Webhook verified")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook")
async def meta_webhook_status_canonical(request: Request, db: Session = Depends(get_db)):
    """
    Meta canonical webhook — POST /api/v1/whatsapp/webhook
    Handles BOTH delivery status updates AND incoming messages.
    DC Protocol Apr 2026: wa_inbox table captures all inbound messages.
    """
    import json as _json
    try:
        body = await request.json()
    except Exception:
        return {"status": "invalid_body"}

    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # ── 1. Delivery status updates ─────────────────────────────────
            for su in value.get("statuses", []):
                wamid       = su.get("id")
                meta_status = su.get("status")
                if not wamid or not meta_status:
                    continue
                status_map = {"sent": "sent", "delivered": "delivered", "read": "read", "failed": "failed"}
                mapped = status_map.get(meta_status, meta_status)
                ml = db.query(MessageLog).filter(MessageLog.message_sid == wamid).first()
                if not ml:
                    print(f"[WA-WEBHOOK] ⚠️ wamid not found: {wamid}")
                    continue
                ml.current_status     = mapped
                ml.last_status_update = datetime.utcnow()
                ml.last_updated       = datetime.utcnow()
                if mapped == "delivered":
                    ml.delivered_at = datetime.utcnow()
                elif mapped == "failed":
                    ml.failed_at = datetime.utcnow()
                    errs = su.get("errors", [])
                    if errs:
                        ml.error_code    = str(errs[0].get("code", ""))
                        ml.error_message = errs[0].get("message", "")
                print(f"[WA-WEBHOOK] 📨 {wamid} → {mapped}")

            # ── 2. Incoming messages ────────────────────────────────────────
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                try:
                    from app.models.whatsapp import WAInbox
                    from app.models.crm import CRMLead
                    wamid_in    = msg.get("id")
                    from_phone  = msg.get("from", "")
                    from_name   = contacts.get(from_phone)
                    msg_type    = msg.get("type", "text")
                    body_text   = None
                    media_url   = None
                    media_mime  = None

                    if msg_type == "text":
                        body_text = msg.get("text", {}).get("body", "")
                    elif msg_type in ("image", "video", "audio", "document", "sticker"):
                        media_info = msg.get(msg_type, {})
                        media_url  = media_info.get("id")   # Media ID (fetch separately if needed)
                        media_mime = media_info.get("mime_type")
                        body_text  = media_info.get("caption", "")
                    elif msg_type == "interactive":
                        reply = msg.get("interactive", {})
                        body_text = (reply.get("button_reply") or reply.get("list_reply") or {}).get("title", "")
                    else:
                        body_text = _json.dumps(msg)

                    # Skip duplicate
                    if wamid_in and db.query(WAInbox).filter_by(wamid=wamid_in).first():
                        continue

                    # Auto-link to CRM lead by phone
                    clean = from_phone.lstrip("91") if from_phone.startswith("91") and len(from_phone) == 12 else from_phone
                    lead = db.query(CRMLead).filter(
                        CRMLead.phone.in_([from_phone, clean, "91" + clean])
                    ).order_by(CRMLead.id.desc()).first()

                    inbox = WAInbox(
                        wamid=wamid_in,
                        from_phone=from_phone,
                        from_name=from_name,
                        message_type=msg_type,
                        body_text=body_text,
                        media_url=media_url,
                        media_mime_type=media_mime,
                        lead_id=lead.id if lead else None,
                        is_read=False,
                        received_at=datetime.utcnow(),
                        raw_payload=_json.dumps(msg),
                    )
                    db.add(inbox)
                    db.flush()  # get inbox.id before auto-reply check
                    # ── Auto-reply: once per 24h per phone ─────────────────
                    try:
                        from app.services.whatsapp_auto_service import _send_meta as _sm, _is_valid_phone as _ivp
                        from datetime import timedelta as _td
                        _cutoff = datetime.utcnow() - _td(hours=24)
                        _already = db.query(WAInbox).filter(
                            WAInbox.from_phone == from_phone,
                            WAInbox.auto_replied == True,
                            WAInbox.auto_replied_at >= _cutoff,
                            WAInbox.id != inbox.id,
                        ).first()
                        if not _already and _ivp(from_phone):
                            _ar_msg = (
                                "Thank you for contacting Myntreal! 🙏\n"
                                "Our team will connect with you shortly."
                            )
                            _ar = _sm(from_phone, _ar_msg, db=db)
                            if _ar.get("success"):
                                inbox.auto_replied    = True
                                inbox.auto_replied_at = datetime.utcnow()
                                print(f"[WA-INBOX] ✅ Auto-reply sent to {from_phone}")
                    except Exception as _are:
                        print(f"[WA-INBOX] ⚠️ Auto-reply error: {_are}")
                    print(f"[WA-INBOX] ✅ Incoming from {from_phone}: {(body_text or '')[:60]}")
                except Exception as _msg_err:
                    print(f"[WA-INBOX] ⚠️ Error saving message: {_msg_err}")

    db.commit()
    return {"status": "success"}


# ── INBOX API ───────────────────────────────────────────────────────────────────

import re as _re_phone


def _resolve_contact_info(db: Session, phone: str) -> dict:
    """
    Resolve best display name and system presence for a WhatsApp phone number.
    Priority: CRM Leads → Walk-ins (partner_walkins) → Staff Contacts (staff_call_logs).
    Returns: {resolved_name, existing_in: [{type, label, id?, status?, with_whom?}]}
    """
    if not phone:
        return {"resolved_name": None, "existing_in": [{"type": "new", "label": "New"}]}

    digits = _re_phone.sub(r'[^\d]', '', str(phone))
    last10 = digits[-10:] if len(digits) >= 10 else digits
    if not last10:
        return {"resolved_name": None, "existing_in": [{"type": "new", "label": "New"}]}

    from sqlalchemy import text as _t
    p10 = f"%{last10}"
    existing_in = []
    resolved_name = None

    # 1. CRM Leads (highest priority)
    try:
        crm = db.execute(_t("""
            SELECT cl.id, cl.name, cl.status, cl.handler_type, cl.handler_id,
                   TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS owner_name
            FROM crm_leads cl
            LEFT JOIN staff_employees se ON se.emp_code = cl.handler_id AND cl.handler_type = 'staff'
            WHERE cl.phone LIKE :p OR cl.alternate_phone LIKE :p
            ORDER BY cl.id DESC LIMIT 1
        """), {"p": p10}).fetchone()
        if crm:
            resolved_name = crm[1]
            with_whom = (crm[5] or "").strip() or crm[4] or None
            existing_in.append({
                "type": "crm", "label": "CRM",
                "id": crm[0], "status": crm[2], "with_whom": with_whom,
            })
    except Exception:
        pass

    # 2. Walk-ins (partner_walkins)
    try:
        wi = db.execute(_t("""
            SELECT id, customer_name, assigned_to, status
            FROM partner_walkins
            WHERE customer_phone LIKE :p OR alternate_phone LIKE :p
            ORDER BY id DESC LIMIT 1
        """), {"p": p10}).fetchone()
        if wi:
            if not resolved_name:
                resolved_name = wi[1]
            existing_in.append({
                "type": "walkin", "label": "Walk-in",
                "id": wi[0], "status": wi[3], "with_whom": wi[2] or None,
            })
    except Exception:
        pass

    # 3. Service Tickets
    try:
        st = db.execute(_t("""
            SELECT st.id, st.status, st.ticket_id,
                   TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS tech_name
            FROM service_ticket st
            LEFT JOIN staff_employees se ON se.id = st.service_technician_id
            WHERE st.customer_phone LIKE :p
            ORDER BY st.id DESC LIMIT 1
        """), {"p": p10}).fetchone()
        if st:
            with_whom = (st[3] or "").strip() or None
            existing_in.append({
                "type": "service", "label": "Service",
                "id": st[0], "ticket_ref": st[2], "status": st[1], "with_whom": with_whom,
            })
    except Exception:
        pass

    # 4. Staff Contacts (phone book synced from staff mobile)
    try:
        sc = db.execute(_t("""
            SELECT scl.contact_name,
                   TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS staff_name
            FROM staff_call_logs scl
            LEFT JOIN staff_employees se ON se.id = scl.staff_id
            WHERE scl.phone_number LIKE :p AND scl.contact_name IS NOT NULL
            ORDER BY scl.id DESC LIMIT 1
        """), {"p": p10}).fetchone()
        if sc:
            if not resolved_name:
                resolved_name = sc[0]
            with_whom = (sc[1] or "").strip() or None
            existing_in.append({
                "type": "contacts", "label": "Contacts",
                "contact_name": sc[0], "with_whom": with_whom,
            })
    except Exception:
        pass

    if not existing_in:
        existing_in.append({"type": "new", "label": "New"})

    return {"resolved_name": resolved_name, "existing_in": existing_in}


@router.get("/inbox/me-info")
def get_inbox_me_info(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(_require_staff),
):
    """Return current staff identity + role info for the inbox page."""
    role = current_user.role
    return {
        "success": True,
        "id": current_user.id,
        "emp_code": current_user.emp_code,
        "name": (current_user.full_name or "").strip() or current_user.emp_code,
        "role_code": role.role_code if role else None,
        "role_name": role.role_name if role else None,
        "hierarchy_level": role.hierarchy_level if role else 0,
    }


@router.get("/inbox/my-team")
def get_my_team(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(_require_staff),
):
    """
    Return all staff employees under the current user's reporting hierarchy.
    Goes 3 levels deep (direct reports + their reports + their reports).
    """
    from sqlalchemy import text as _t
    from app.models.staff import StaffEmployee as SE
    try:
        team_rows = db.execute(_t("""
            WITH RECURSIVE team AS (
                SELECT id, emp_code,
                       TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')) AS full_name,
                       reporting_manager_id, 1 AS depth
                FROM staff_employees
                WHERE reporting_manager_id = :mgr_id AND status = 'active'
                UNION ALL
                SELECT se.id, se.emp_code,
                       TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS full_name,
                       se.reporting_manager_id, t.depth + 1
                FROM staff_employees se
                JOIN team t ON se.reporting_manager_id = t.id
                WHERE se.status = 'active' AND t.depth < 4
            )
            SELECT id, emp_code, full_name, depth FROM team ORDER BY depth, full_name
        """), {"mgr_id": current_user.id}).fetchall()
        return {
            "success": True,
            "data": [{"id": r[0], "emp_code": r[1], "name": r[2] or r[1], "depth": r[3]}
                     for r in team_rows]
        }
    except Exception as _e:
        print(f"[WA-TEAM] Error: {_e}")
        return {"success": True, "data": []}


@router.get("/inbox")
def get_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    unread_only: bool = Query(False),
    phone: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    dept_code: Optional[str] = Query(None),
    category_code: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    assigned: Optional[bool] = Query(None),
    my_leads: bool = Query(False),
    team_emp_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(_require_staff),
):
    """
    Thread-grouped WhatsApp inbox — one row per unique phone (conversation).
    Includes resolved contact name (CRM → Walk-in → Staff Contacts priority),
    Existing In presence chips, and stats for the stat cards.
    """
    from sqlalchemy import text as _t

    # ── Build base WHERE clause (phone/date filters applied before grouping) ──
    base_conds = ["1=1"]
    params: dict = {}

    if phone:
        base_conds.append("from_phone LIKE :phone_filter")
        params["phone_filter"] = f"%{phone.strip()}%"
    if from_date:
        base_conds.append("received_at >= :from_date")
        params["from_date"] = from_date.strip()
    if to_date:
        base_conds.append("received_at <= :to_date")
        params["to_date"] = to_date.strip() + " 23:59:59"

    # ── [DC-LEADS-TEAM-001] My Leads filter: assigned to me OR CRM handler ──
    if my_leads:
        try:
            ml_phones = db.execute(_t("""
                SELECT DISTINCT from_phone FROM wa_inbox WHERE assigned_to_emp_id = :eid
                UNION
                SELECT DISTINCT cl.phone FROM crm_leads cl
                WHERE cl.handler_id = :ecode AND cl.handler_type = 'staff'
                  AND cl.phone IS NOT NULL
            """), {"eid": current_user.id, "ecode": current_user.emp_code}).fetchall()
            phone_list = [r[0] for r in ml_phones if r[0]]
        except Exception:
            phone_list = []
        if phone_list:
            base_conds.append("from_phone = ANY(:ml_phones)")
            params["ml_phones"] = phone_list
        else:
            base_conds.append("1=0")  # No leads → empty result

    # ── [DC-LEADS-TEAM-001] Team filter: conversations assigned to a specific team member ──
    if team_emp_id:
        try:
            te_row = db.execute(_t(
                "SELECT emp_code FROM staff_employees WHERE id = :eid LIMIT 1"
            ), {"eid": team_emp_id}).fetchone()
            te_code = te_row[0] if te_row else None
            te_phones = db.execute(_t("""
                SELECT DISTINCT from_phone FROM wa_inbox WHERE assigned_to_emp_id = :eid
                UNION
                SELECT DISTINCT cl.phone FROM crm_leads cl
                WHERE cl.handler_id = :ecode AND cl.handler_type = 'staff'
                  AND cl.phone IS NOT NULL
            """), {"eid": team_emp_id, "ecode": te_code or ""}).fetchall()
            te_phone_list = [r[0] for r in te_phones if r[0]]
        except Exception:
            te_phone_list = []
        if te_phone_list:
            base_conds.append("from_phone = ANY(:te_phones)")
            params["te_phones"] = te_phone_list
        else:
            base_conds.append("1=0")

    base_where = " AND ".join(base_conds)

    # ── Thread-level HAVING clause (applied after GROUP BY) ──────────────────
    having_parts = []
    if unread_only:
        having_parts.append(
            "SUM(CASE WHEN is_read = false AND message_type != 'outbound' THEN 1 ELSE 0 END) > 0"
        )
    if status:
        having_parts.append(
            "(ARRAY_REMOVE(ARRAY_AGG(status ORDER BY received_at DESC), NULL))[1] = :status_filter"
        )
        params["status_filter"] = status.strip()
    if dept_code:
        having_parts.append(
            "(ARRAY_REMOVE(ARRAY_AGG(dept_code ORDER BY received_at DESC), NULL))[1] = :dept_filter"
        )
        params["dept_filter"] = dept_code.strip()
    if category_code:
        having_parts.append(
            "(ARRAY_REMOVE(ARRAY_AGG(category_code ORDER BY received_at DESC), NULL))[1] = :cat_filter"
        )
        params["cat_filter"] = category_code.strip()
    if assigned is True:
        having_parts.append("MAX(assigned_to_emp_id) IS NOT NULL")
    elif assigned is False:
        having_parts.append("MAX(assigned_to_emp_id) IS NULL")

    having_sql = ("HAVING " + " AND ".join(having_parts)) if having_parts else ""

    # ── Stats (always computed from base WHERE, no thread-level filters) ─────
    try:
        stats_sql = f"""
            SELECT
                COUNT(DISTINCT from_phone) AS all_threads,
                COUNT(DISTINCT CASE
                    WHEN SUM(CASE WHEN is_read=false AND message_type!='outbound' THEN 1 ELSE 0 END) OVER (PARTITION BY from_phone) > 0
                    THEN from_phone END) AS unread_dummy
            FROM wa_inbox WHERE {base_where}
        """
        # Simpler approach: run aggregated subquery
        stats_row = db.execute(_t(f"""
            SELECT
                COUNT(*) AS all_threads,
                SUM(CASE WHEN unread_c > 0 THEN 1 ELSE 0 END) AS unread,
                SUM(CASE WHEN t_status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN t_status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN assigned_emp IS NOT NULL THEN 1 ELSE 0 END) AS assigned
            FROM (
                SELECT from_phone,
                    SUM(CASE WHEN is_read=false AND message_type!='outbound' THEN 1 ELSE 0 END) AS unread_c,
                    (ARRAY_REMOVE(ARRAY_AGG(status ORDER BY received_at DESC), NULL))[1] AS t_status,
                    MAX(assigned_to_emp_id) AS assigned_emp
                FROM wa_inbox
                WHERE {base_where}
                GROUP BY from_phone
            ) agg
        """), {k: v for k, v in params.items()
               if k not in ("status_filter", "dept_filter", "cat_filter", "limit", "offset")}).fetchone()
        stats = {
            "all":       int(stats_row[0] or 0),
            "unread":    int(stats_row[1] or 0),
            "pending":   int(stats_row[2] or 0),
            "completed": int(stats_row[3] or 0),
            "assigned":  int(stats_row[4] or 0),
        }
    except Exception as _se:
        print(f"[WA-INBOX] Stats error: {_se}")
        stats = {"all": 0, "unread": 0, "pending": 0, "completed": 0, "assigned": 0}

    # ── Count total threads matching all filters ───────────────────────────────
    try:
        total_row = db.execute(_t(f"""
            SELECT COUNT(*) FROM (
                SELECT from_phone FROM wa_inbox
                WHERE {base_where}
                GROUP BY from_phone
                {having_sql}
            ) t
        """), params).fetchone()
        total = int(total_row[0] or 0)
    except Exception:
        total = 0

    # ── Paginated thread query ────────────────────────────────────────────────
    params["limit"]  = page_size
    params["offset"] = (page - 1) * page_size

    try:
        thread_rows = db.execute(_t(f"""
            SELECT
                from_phone,
                COUNT(*)                                                                     AS message_count,
                SUM(CASE WHEN is_read=false AND message_type!='outbound' THEN 1 ELSE 0 END) AS unread_count,
                MAX(received_at)                                                             AS last_activity,
                MAX(id)                                                                      AS latest_msg_id,
                (ARRAY_REMOVE(ARRAY_AGG(status        ORDER BY received_at DESC), NULL))[1] AS thread_status,
                (ARRAY_REMOVE(ARRAY_AGG(dept_code     ORDER BY received_at DESC), NULL))[1] AS dept_code,
                (ARRAY_REMOVE(ARRAY_AGG(category_code ORDER BY received_at DESC), NULL))[1] AS category_code,
                (ARRAY_REMOVE(ARRAY_AGG(crm_lead_id   ORDER BY received_at DESC), NULL))[1] AS crm_lead_id,
                (ARRAY_REMOVE(ARRAY_AGG(service_ticket_id ORDER BY received_at DESC), NULL))[1] AS service_ticket_id,
                (ARRAY_REMOVE(ARRAY_AGG(assigned_to_emp_id ORDER BY received_at DESC), NULL))[1] AS assigned_to_emp_id,
                (ARRAY_REMOVE(ARRAY_AGG(from_name     ORDER BY received_at DESC), NULL))[1] AS wa_name
            FROM wa_inbox
            WHERE {base_where}
            GROUP BY from_phone
            {having_sql}
            ORDER BY MAX(received_at) DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
    except Exception as _te:
        print(f"[WA-INBOX] Thread query error: {_te}")
        thread_rows = []

    # ── Batch-fetch latest message body for each thread ───────────────────────
    latest_msg_ids = [r[4] for r in thread_rows if r[4]]
    latest_msgs: dict = {}
    if latest_msg_ids:
        try:
            lm_rows = db.execute(_t(
                "SELECT id, body_text, message_type FROM wa_inbox WHERE id = ANY(:ids)"
            ), {"ids": latest_msg_ids}).fetchall()
            latest_msgs = {r[0]: {"body": r[1], "type": r[2]} for r in lm_rows}
        except Exception:
            pass

    # ── [DC-SENT-TRACK-001] Batch-fetch last outbound sender from message_log ──
    last_sent_by_map: dict = {}
    if thread_rows:
        phones_last10 = list({
            r[0][-10:] if len(r[0]) >= 10 else r[0]
            for r in thread_rows
        })
        try:
            sent_rows = db.execute(_t("""
                SELECT DISTINCT ON (RIGHT(REGEXP_REPLACE(mobile_number,'[^0-9]','','g'), 10))
                    RIGHT(REGEXP_REPLACE(mobile_number,'[^0-9]','','g'), 10) AS last10,
                    sent_by_name,
                    sender_type,
                    sent_at
                FROM message_log
                WHERE RIGHT(REGEXP_REPLACE(mobile_number,'[^0-9]','','g'), 10) = ANY(:phones)
                ORDER BY RIGHT(REGEXP_REPLACE(mobile_number,'[^0-9]','','g'), 10), sent_at DESC
            """), {"phones": phones_last10}).fetchall()
            for sr in sent_rows:
                last_sent_by_map[sr[0]] = {
                    "name": sr[1],
                    "type": sr[2],
                    "at":   sr[3].isoformat() if sr[3] else None,
                }
        except Exception as _lse:
            print(f"[WA-INBOX] last_sent_by batch error: {_lse}")

    # ── Build thread response objects ─────────────────────────────────────────
    data = []
    for r in thread_rows:
        from_phone    = r[0]
        latest_msg_id = r[4]
        lm            = latest_msgs.get(latest_msg_id, {})
        contact_info  = _resolve_contact_info(db, from_phone)
        wa_name       = r[11]
        resolved_name = contact_info["resolved_name"] or wa_name
        fp_digits     = _re_phone.sub(r'[^\d]', '', from_phone)
        fp_last10     = fp_digits[-10:] if len(fp_digits) >= 10 else fp_digits

        data.append({
            "from_phone":       from_phone,
            "message_count":    int(r[1] or 0),
            "unread_count":     int(r[2] or 0),
            "last_activity":    r[3].isoformat() if r[3] else None,
            "latest_msg_id":    latest_msg_id,
            "status":           r[5] or "new",
            "dept_code":        r[6],
            "category_code":    r[7],
            "crm_lead_id":      r[8],
            "service_ticket_id": r[9],
            "assigned_to_emp_id": r[10],
            "from_name":        wa_name,
            "resolved_name":    resolved_name,
            "last_message":     lm.get("body"),
            "last_message_type": lm.get("type"),
            "existing_in":      contact_info["existing_in"],
            "last_sent_by":     last_sent_by_map.get(fp_last10),
        })

    return {
        "success":   True,
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "stats":     stats,
        "data":      data,
    }


@router.get("/inbox/unread-count")
def inbox_unread_count(db: Session = Depends(get_db), current_user: StaffEmployee = Depends(_require_staff)):
    """Return count of unread inbox messages."""
    from app.models.whatsapp import WAInbox
    count = db.query(WAInbox).filter(WAInbox.is_read == False).count()
    return {"success": True, "unread": count}


@router.patch("/inbox/{inbox_id}/read")
def mark_inbox_read(inbox_id: int, db: Session = Depends(get_db), current_user: StaffEmployee = Depends(_require_staff)):
    """Mark a message as read."""
    from app.models.whatsapp import WAInbox
    msg = db.query(WAInbox).filter(WAInbox.id == inbox_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_read = True
    db.commit()
    return {"success": True}


@router.patch("/inbox/mark-all-read")
def mark_all_inbox_read(db: Session = Depends(get_db), current_user: StaffEmployee = Depends(_require_staff)):
    """Mark all messages as read."""
    from app.models.whatsapp import WAInbox
    db.query(WAInbox).filter(WAInbox.is_read == False).update({"is_read": True})
    db.commit()
    return {"success": True}


@router.post("/inbox/{inbox_id}/reply")
def reply_to_inbox(
    inbox_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(_require_staff),
):
    """Reply to an incoming WhatsApp message (free-form text, within 24h window)."""
    from app.models.whatsapp import WAInbox
    from app.services.whatsapp_auto_service import _send_meta, _is_valid_phone
    msg = db.query(WAInbox).filter(WAInbox.id == inbox_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    reply_text = (payload.get("text") or "").strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="Reply text is required")
    if not _is_valid_phone(msg.from_phone):
        raise HTTPException(status_code=400, detail="Invalid phone number")
    result = _send_meta(msg.from_phone, reply_text, db=db)
    if result.get("success"):
        now = datetime.utcnow()
        msg.replied       = True
        msg.replied_at    = now
        msg.replied_by_id = current_user.id
        msg.is_read       = True
        # Store outbound reply as a wa_inbox row so thread view shows it
        try:
            from app.models.whatsapp import WAInbox as _WAI
            outbound = _WAI(
                wamid          = result.get("wamid"),
                from_phone     = msg.from_phone,
                from_name      = msg.from_name,
                message_type   = "outbound",
                body_text      = reply_text,
                is_read        = True,
                replied        = False,
                replied_by_id  = current_user.id,
                received_at    = now,
                status         = msg.status or "new",
                dept_code      = msg.dept_code,
                assigned_to_emp_id = msg.assigned_to_emp_id,
                crm_lead_id    = msg.crm_lead_id,
            )
            db.add(outbound)
        except Exception as _oe:
            print(f"[WA-REPLY] ⚠️ Outbound row insert error: {_oe}")
        db.commit()
        return {"success": True, "wamid": result.get("wamid")}
    raise HTTPException(status_code=502, detail=result.get("reason", "Failed to send reply"))


# ── CRM INBOX: Departments, Categories, Thread, Assign, Status ───────────────

WA_INBOX_CATEGORIES = [
    {"code": "enquiry",     "label": "Enquiry"},
    {"code": "support",     "label": "Support"},
    {"code": "complaint",   "label": "Complaint"},
    {"code": "appointment", "label": "Appointment"},
    {"code": "general",     "label": "General"},
    {"code": "sales",       "label": "Sales"},
]


@router.get("/inbox/categories")
def get_inbox_categories(current_user=Depends(_require_staff)):
    """Return the static list of WA inbox categories."""
    return {"success": True, "data": WA_INBOX_CATEGORIES}


@router.get("/inbox/departments")
def get_inbox_departments(db: Session = Depends(get_db), current_user=Depends(_require_staff)):
    """Return all active departments from staff_departments."""
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        "SELECT id, name, department_code FROM staff_departments WHERE is_active = TRUE ORDER BY name"
    )).fetchall()
    return {"success": True, "data": [{"id": r[0], "name": r[1], "dept_code": r[2]} for r in rows]}


@router.get("/inbox/dept-employees")
def get_dept_employees(
    dept_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_require_staff),
):
    """Search active employees by department; cross-company, irrespective of company."""
    from sqlalchemy import text as _text
    sql = """
        SELECT DISTINCT se.id, se.emp_code, se.first_name, se.last_name, se.email,
               sd.id AS dept_id, sd.name AS dept_name
        FROM staff_employees se
        JOIN staff_employee_departments sed ON sed.employee_id = se.id
        JOIN staff_departments sd ON sd.id = sed.department_id
        WHERE se.status = 'active'
    """
    params: dict = {}
    if dept_id:
        sql += " AND sd.id = :dept_id"
        params["dept_id"] = dept_id
    if search:
        sql += " AND (se.first_name ILIKE :s OR se.last_name ILIKE :s OR se.emp_code ILIKE :s)"
        params["s"] = f"%{search}%"
    sql += " ORDER BY se.first_name LIMIT 50"
    rows = db.execute(_text(sql), params).fetchall()
    return {"success": True, "data": [
        {"id": r[0], "emp_code": r[1], "name": f"{r[2] or ''} {r[3] or ''}".strip(),
         "email": r[4], "dept_id": r[5], "dept_name": r[6]}
        for r in rows
    ]}


@router.get("/inbox/thread/{phone}")
def get_inbox_thread(
    phone: str,
    db: Session = Depends(get_db),
    current_user=Depends(_require_staff),
):
    """
    Return full conversation thread (all messages) for a phone number.
    DC Protocol Apr 2026: Also returns contact_info (resolved name + existing_in),
    full CRM lead detail, walk-in records, service tickets, and staff contact info
    for the ALL POSSIBLE DETAILS panel in the thread modal.
    """
    from app.models.whatsapp import WAInbox
    from sqlalchemy import text as _t
    clean = phone.strip()
    alt   = clean.lstrip("91") if clean.startswith("91") and len(clean) == 12 else ("91" + clean[-10:])
    msgs  = db.query(WAInbox).filter(
        WAInbox.from_phone.in_([clean, alt])
    ).order_by(WAInbox.received_at.asc()).all()

    # Mark all inbound messages as read
    for m in msgs:
        if not m.is_read and m.message_type != "outbound":
            m.is_read = True
    db.commit()

    # Resolve contact info
    contact_info = _resolve_contact_info(db, clean)

    digits = _re_phone.sub(r'[^\d]', '', clean)
    last10 = digits[-10:] if len(digits) >= 10 else digits
    p10    = f"%{last10}"

    # Full CRM lead records (all, not just latest)
    crm_leads_detail = []
    try:
        crm_rows = db.execute(_t("""
            SELECT cl.id, cl.name, cl.phone, cl.email, cl.status, cl.source,
                   cl.category_id, cl.created_at,
                   TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS owner_name,
                   cl.handler_type, cl.handler_id, cl.next_followup_date,
                   cl.recent_comments, cl.budget_min, cl.budget_max, cl.city, cl.state,
                   cl.deal_value, cl.description
            FROM crm_leads cl
            LEFT JOIN staff_employees se ON se.emp_code = cl.handler_id AND cl.handler_type = 'staff'
            WHERE cl.phone LIKE :p OR cl.alternate_phone LIKE :p
            ORDER BY cl.id DESC LIMIT 5
        """), {"p": p10}).fetchall()
        for r in crm_rows:
            crm_leads_detail.append({
                "id": r[0], "name": r[1], "phone": r[2], "email": r[3],
                "status": r[4], "source": r[5], "category_id": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "owner_name": (r[8] or "").strip() or r[10] or None,
                "handler_type": r[9], "handler_id": r[10],
                "next_followup_date": r[11].isoformat() if r[11] else None,
                "recent_comments": r[12], "budget_min": r[13], "budget_max": r[14],
                "city": r[15], "state": r[16], "deal_value": r[17], "description": r[18],
            })
    except Exception as _e:
        print(f"[WA-THREAD] CRM detail error: {_e}")

    # Walk-in records
    walkin_detail = []
    try:
        wi_rows = db.execute(_t("""
            SELECT id, customer_name, visit_date, visit_purpose, visit_outcome,
                   status, assigned_to, notes, customer_type, is_returning,
                   product_interest, created_at
            FROM partner_walkins
            WHERE customer_phone LIKE :p OR alternate_phone LIKE :p
            ORDER BY id DESC LIMIT 5
        """), {"p": p10}).fetchall()
        for r in wi_rows:
            walkin_detail.append({
                "id": r[0], "customer_name": r[1],
                "visit_date": str(r[2]) if r[2] else None,
                "visit_purpose": r[3], "visit_outcome": r[4],
                "status": r[5], "assigned_to": r[6], "notes": r[7],
                "customer_type": r[8], "is_returning": r[9],
                "product_interest": r[10],
                "created_at": r[11].isoformat() if r[11] else None,
            })
    except Exception as _e:
        print(f"[WA-THREAD] Walk-in detail error: {_e}")

    # Service ticket records
    service_detail = []
    try:
        st_rows = db.execute(_t("""
            SELECT st.id, st.ticket_id, st.status, st.sub_status,
                   st.issue_category, st.issue_description, st.priority,
                   st.created_date,
                   TRIM(COALESCE(se_tech.first_name,'') || ' ' || COALESCE(se_tech.last_name,'')) AS tech_name,
                   TRIM(COALESCE(se_mgr.first_name,'') || ' ' || COALESCE(se_mgr.last_name,'')) AS mgr_name
            FROM service_ticket st
            LEFT JOIN staff_employees se_tech ON se_tech.id = st.service_technician_id
            LEFT JOIN staff_employees se_mgr  ON se_mgr.id  = st.service_manager_id
            WHERE st.customer_phone LIKE :p
            ORDER BY st.id DESC LIMIT 5
        """), {"p": p10}).fetchall()
        for r in st_rows:
            service_detail.append({
                "id": r[0], "ticket_id": r[1], "status": r[2], "sub_status": r[3],
                "issue_category": r[4], "issue_description": r[5], "priority": r[6],
                "created_date": r[7].isoformat() if r[7] else None,
                "technician": (r[8] or "").strip() or None,
                "manager": (r[9] or "").strip() or None,
            })
    except Exception as _e:
        print(f"[WA-THREAD] Service detail error: {_e}")

    # Staff contacts
    contacts_detail = []
    try:
        sc_rows = db.execute(_t("""
            SELECT scl.contact_name, scl.phone_number,
                   TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS staff_name,
                   se.emp_code
            FROM staff_call_logs scl
            LEFT JOIN staff_employees se ON se.id = scl.staff_id
            WHERE scl.phone_number LIKE :p AND scl.contact_name IS NOT NULL
            GROUP BY scl.contact_name, scl.phone_number, se.first_name, se.last_name, se.emp_code
            ORDER BY MAX(scl.id) DESC LIMIT 5
        """), {"p": p10}).fetchall()
        for r in sc_rows:
            contacts_detail.append({
                "contact_name": r[0], "phone": r[1],
                "saved_by": (r[2] or "").strip() or None, "emp_code": r[3],
            })
    except Exception as _e:
        print(f"[WA-THREAD] Contacts detail error: {_e}")

    # ── [DC-SENT-TRACK-001] Outbound messages from message_log for this number ──
    ml_outbound = []
    try:
        ml_rows = db.execute(_t("""
            SELECT id, message_body, sent_at, sender_type, sent_by_name,
                   message_type, current_status
            FROM message_log
            WHERE RIGHT(REGEXP_REPLACE(mobile_number,'[^0-9]','','g'), 10) = :last10
               OR to_number LIKE :p10_to
            ORDER BY sent_at ASC
        """), {"last10": last10, "p10_to": f"%{last10}"}).fetchall()
        for row in ml_rows:
            ml_outbound.append({
                "id":           f"ml_{row[0]}",
                "wamid":        None,
                "from_phone":   clean,
                "from_name":    None,
                "message_type": "outbound",
                "body_text":    row[1] or f"[{row[5] or 'message'}]",
                "media_url":    None,
                "media_mime_type": None,
                "lead_id":      None,
                "is_read":      True,
                "replied":      False,
                "replied_at":   None,
                "received_at":  row[2].isoformat() if row[2] else None,
                "dept_code":    None,
                "assigned_to_emp_id": None,
                "assigned_at":  None,
                "target_date":  None,
                "category_code": None,
                "status":       row[6],
                "crm_lead_id":  None,
                "service_ticket_id": None,
                "assigned_notes": None,
                "auto_replied": False,
                "auto_replied_at": None,
                # Extra fields for sent-by display
                "sender_type":  row[3],
                "sent_by_name": row[4],
                "_source":      "message_log",
            })
    except Exception as _e:
        print(f"[WA-THREAD] message_log outbound error: {_e}")

    # Merge wa_inbox messages + message_log outbound, sort by received_at
    inbox_dicts = [m.to_dict() for m in msgs]

    # ── Enrich wa_inbox messages with replied_by_name ─────────────────────────
    try:
        replied_ids = list({
            d["replied_by_id"] for d in inbox_dicts
            if d.get("replied_by_id") and d.get("message_type") == "outbound"
        })
        if replied_ids:
            staff_name_rows = db.execute(_t("""
                SELECT id,
                       TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')) AS full_name,
                       emp_code
                FROM staff_employees WHERE id = ANY(:ids)
            """), {"ids": replied_ids}).fetchall()
            staff_name_map = {r[0]: (r[1].strip() or r[2] or str(r[0])) for r in staff_name_rows}
            for d in inbox_dicts:
                if d.get("replied_by_id") and d.get("message_type") == "outbound":
                    d["replied_by_name"] = staff_name_map.get(d["replied_by_id"])
    except Exception as _e:
        print(f"[WA-THREAD] replied_by_name lookup error: {_e}")

    all_msgs = sorted(
        inbox_dicts + ml_outbound,
        key=lambda x: x.get("received_at") or ""
    )

    return {
        "success": True,
        "phone": clean,
        "total": len(all_msgs),
        "data": all_msgs,
        "contact_info": contact_info,
        "crm_leads": crm_leads_detail,
        "walkins": walkin_detail,
        "service_tickets": service_detail,
        "staff_contacts": contacts_detail,
    }


@router.post("/inbox/{inbox_id}/assign")
def assign_inbox_message(
    inbox_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(_require_staff),
):
    """
    Assign a WA inbox message to a department + employee with a target date.
    DC Protocol Apr 2026 CRM Extension:
    - If dept=Sales: create/link CRM lead
    - If dept=Service: immediately raise service ticket
    - Always: update existing CRM lead notes/followup if already linked
    """
    from app.models.whatsapp import WAInbox
    msg = db.query(WAInbox).filter(WAInbox.id == inbox_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    dept_code       = (payload.get("dept_code") or "").strip()
    dept_id         = payload.get("dept_id")
    emp_id          = payload.get("emp_id")
    emp_code        = (payload.get("emp_code") or "").strip()
    target_date_str = (payload.get("target_date") or "").strip()
    category_code   = (payload.get("category_code") or "").strip()
    notes           = (payload.get("notes") or "").strip()

    from datetime import date as _date
    target_date = None
    if target_date_str:
        try:
            target_date = _date.fromisoformat(target_date_str)
        except Exception:
            pass

    # ── Update wa_inbox assignment fields ─────────────────────────────────────
    incoming_status = (payload.get("status") or "").strip().lower()
    valid_statuses  = {"new", "pending", "completed"}

    msg.dept_code          = dept_code or None
    msg.assigned_to_emp_id = emp_id or None
    msg.assigned_at        = datetime.utcnow()
    msg.target_date        = target_date
    msg.category_code      = category_code or None
    msg.assigned_notes     = notes or None
    msg.status             = incoming_status if incoming_status in valid_statuses else "pending"
    msg.is_read            = True

    result_extras: dict = {}

    # ── Sales dept → create or link CRM lead ──────────────────────────────────
    dept_upper = dept_code.upper() if dept_code else ""
    if "SALES" in dept_upper:
        lead_action = payload.get("lead_action")  # "new" | "existing" | None
        if lead_action == "new":
            try:
                from sqlalchemy import text as _t
                lead_name  = (payload.get("lead_name") or msg.from_name or msg.from_phone).strip()
                lead_phone = (payload.get("lead_phone") or msg.from_phone).strip()
                lead_email = payload.get("lead_email") or None
                cat_id     = payload.get("lead_category_id") or None
                assigned_emp_code = emp_code or None
                row = db.execute(_t("""
                    INSERT INTO crm_leads (name, phone, email, category_id, handler_type, handler_id,
                                          lead_source, status, phone_primary_whatsapp, created_at, updated_at)
                    VALUES (:nm, :ph, :em, :cid, :ht, :hid, :src, 'new', TRUE, NOW(), NOW())
                    RETURNING id
                """), {
                    "nm": lead_name, "ph": lead_phone, "em": lead_email,
                    "cid": cat_id,
                    "ht": "staff" if assigned_emp_code else "unassigned",
                    "hid": assigned_emp_code,
                    "src": "whatsapp_inbox",
                }).fetchone()
                if row:
                    msg.crm_lead_id = row[0]
                    result_extras["lead_id"] = row[0]
                    print(f"[WA-ASSIGN] ✅ Created new lead #{row[0]} from WA inbox #{inbox_id}")
            except Exception as _le:
                print(f"[WA-ASSIGN] ⚠️ Lead create error: {_le}")

        elif lead_action == "existing":
            existing_lead_id = payload.get("lead_id")
            if existing_lead_id:
                msg.crm_lead_id = int(existing_lead_id)
                result_extras["lead_id"] = existing_lead_id

    # ── Link or update CRM lead notes if already auto-linked ─────────────────
    active_lead_id = msg.crm_lead_id or msg.lead_id
    if active_lead_id and notes:
        try:
            from sqlalchemy import text as _t2
            db.execute(_t2("""
                INSERT INTO crm_lead_notes (lead_id, note, created_by_type, created_by_id, created_at, updated_at)
                VALUES (:lid, :nt, 'staff', :cby, NOW(), NOW())
            """), {"lid": active_lead_id, "nt": f"[WA Inbox] {notes}", "cby": current_user.id})
        except Exception as _ne:
            print(f"[WA-ASSIGN] ⚠️ Note insert error: {_ne}")

    # ── Service dept → immediately raise service ticket ───────────────────────
    if "SERVICE" in dept_upper:
        try:
            from app.services.ticket_service import TicketService
            cname  = msg.from_name or msg.from_phone
            cphone = msg.from_phone
            cdesc  = notes or (msg.body_text or "WhatsApp inquiry")[:500]
            ticket = TicketService.create_service_ticket(
                db=db,
                user_id=None,
                issue_category="WhatsApp Inquiry",
                issue_description=cdesc,
                priority="Medium",
                ticket_type="service",
                source_channel="whatsapp",
                customer_name=cname,
                customer_phone=cphone,
                staff_id=current_user.id if hasattr(current_user, "id") else None,
            )
            if ticket and hasattr(ticket, "id"):
                msg.service_ticket_id = ticket.id
                result_extras["ticket_id"] = ticket.id
                print(f"[WA-ASSIGN] ✅ Service ticket #{ticket.id} raised for WA inbox #{inbox_id}")
        except Exception as _te:
            print(f"[WA-ASSIGN] ⚠️ Service ticket error: {_te}")

    db.commit()
    return {"success": True, "inbox_id": inbox_id, **result_extras}


@router.patch("/inbox/{inbox_id}/status")
def update_inbox_status(
    inbox_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(_require_staff),
):
    """Update status and/or category of a WA inbox message."""
    from app.models.whatsapp import WAInbox
    msg = db.query(WAInbox).filter(WAInbox.id == inbox_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if "status" in payload:
        msg.status = payload["status"]
    if "category_code" in payload:
        msg.category_code = payload["category_code"]
    db.commit()
    return {"success": True, "status": msg.status, "category_code": msg.category_code}
