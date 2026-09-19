"""
WhatsApp Auto-Message Service
Handles automatic WhatsApp sends triggered by system events (CRM, PO, ZXtickets, etc.)
All sends are non-blocking BackgroundTasks and respect VGK pause controls.
"""

import os
import re
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Meta Cloud API config ──────────────────────────────────────────────────────
# [DC-WA-CREDS] Credentials are loaded dynamically from DB (with env var fallback)
# Module-level constants kept as fallback for legacy callers
_ACCESS_TOKEN = os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
_PHONE_NUMBER_ID = os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", "")
_META_BASE = f"https://graph.facebook.com/v21.0/{_PHONE_NUMBER_ID}/messages"

# In-memory dedup cache: { dedup_key: datetime_sent }
# Prevents duplicate auto-sends within a short window (e.g. CRM welcome messages)
_sent_cache: dict = {}


def _get_meta_creds(db=None):
    """Get live Meta credentials from DB or env vars."""
    if db is not None:
        try:
            from app.services.wa_credentials import get_wa_credentials
            creds = get_wa_credentials(db)
            if creds["access_token"]:
                return creds["access_token"], creds["phone_number_id"]
        except Exception:
            pass
    return _ACCESS_TOKEN, _PHONE_NUMBER_ID

# ── Sentinel: track recently sent event+lead combos (in-process dedup) ─────────
# Key = "event_key:lead_id:phone" → datetime sent
_recent_sends: Dict[str, datetime] = {}
_DEDUP_WINDOW_MINUTES = 60  # don't re-send same event for same lead within 1 hour


def _is_paused(db: Session) -> bool:
    """Check VGK pause state."""
    try:
        from app.models.whatsapp import WhatsAppControl
        ctrl = db.query(WhatsAppControl).first()
        return ctrl.is_paused if ctrl else False
    except Exception:
        return False


def get_channel_business_contacts(channel: str = "whatsapp") -> Dict[str, str]:
    """
    Centralized authority for channel-specific business contact numbers and branding.

    Channels:
    - 'whatsapp' (WhatsApp API & WhatsApp Scan):
        Primary:   +91 85858 52738
        Secondary: +91 8897797667
        Display:   📞 +91 85858 52738 | +91 8897797667
    - 'ivy' / 'ivr' / 'telephony':
        Primary:   +91 85858 52738
        Secondary: +91 80317 28899
        Display:   📞 +91 85858 52738 | +91 80317 28899
    """
    ch = (channel or "whatsapp").strip().lower()
    is_ivy = ch in ("ivy", "ivr", "telephony", "plivo")
    try:
        from app.core.config import settings
        if is_ivy:
            primary = getattr(settings, "IVY_PRIMARY_BUSINESS_NUMBER", "+91 85858 52738")
            secondary = getattr(settings, "IVY_SECONDARY_BUSINESS_NUMBER", "+91 80317 28899")
            company = getattr(settings, "IVY_BUSINESS_SIGNATURE_COMPANY", "Mynt Real")
        else:
            primary = getattr(settings, "WHATSAPP_PRIMARY_BUSINESS_NUMBER", "+91 85858 52738")
            secondary = getattr(settings, "WHATSAPP_SECONDARY_BUSINESS_NUMBER", "+91 8897797667")
            company = getattr(settings, "WHATSAPP_BUSINESS_SIGNATURE_COMPANY", "Mynt Real")
    except Exception:
        if is_ivy:
            primary = "+91 85858 52738"
            secondary = "+91 80317 28899"
            company = "Mynt Real"
        else:
            primary = "+91 85858 52738"
            secondary = "+91 8897797667"
            company = "Mynt Real"

    combined = f"{primary} | {secondary}"
    return {
        "channel": "ivy" if is_ivy else "whatsapp",
        "primary": primary,
        "secondary": secondary,
        "company": company,
        "combined_formatted": combined,
        "canonical_display": f"📞 {combined}",
    }


def get_whatsapp_business_contacts() -> Dict[str, str]:
    """WhatsApp business contact authority (backward-compatible wrapper)."""
    return get_channel_business_contacts("whatsapp")


def get_ivy_business_contacts() -> Dict[str, str]:
    """Ivy / IVR business contact authority."""
    return get_channel_business_contacts("ivy")


def build_channel_customer_signature(
    channel: str = "whatsapp",
    sender_name: Optional[str] = None,
    extension: Optional[str] = None,
    include_icon: bool = False
) -> str:
    """
    Authoritative channel-specific customer signature builder.
    channel: 'whatsapp' or 'ivy'
    include_icon: whether to prefix numbers with 📞
    """
    contacts = get_channel_business_contacts(channel)
    display_name = str(sender_name).strip() if sender_name and str(sender_name).strip() else contacts["company"]
    phone_line = contacts["canonical_display"] if include_icon else contacts["combined_formatted"]

    sig_lines = ["Regards,", display_name, phone_line]
    clean_ext = str(extension or "").strip()
    if clean_ext and clean_ext.lower() not in ("none", "null", "undefined", "n/a"):
        sig_lines.append(f"Ext: {clean_ext}")

    return "\n".join(sig_lines)


def build_whatsapp_customer_signature(
    sender_name: Optional[str] = None,
    extension: Optional[str] = None,
    include_icon: bool = False
) -> str:
    """WhatsApp API customer signature builder (backward-compatible wrapper)."""
    return build_channel_customer_signature(
        "whatsapp",
        sender_name=sender_name,
        extension=extension,
        include_icon=include_icon
    )


def strip_staff_whatsapp_signature(message: str) -> str:
    """
    Removes any existing staff signature block from the message body
    (e.g., when forwarding, replying, or re-formatting to prevent stacked signatures).
    Handles single number (8585852738, +91 85858 52738), dual numbers (+91 85858 52738 | +91 8897797667 or +91 85858 52738 | +91 80317 28899),
    extensions, dashes ('—', '--'), employee codes, titles/designations, and multiple stacked signatures.
    """
    if not message:
        return ""
    pattern = r'(?:\r?\n|^)\s*(?:[—\-–_]+\s*)?(?:Regards|Warm regards|Best regards|Kind regards|Thanks & regards|Thanks and regards),\s*(?:\r?\n|$)[\s\S]*$'
    cleaned = re.sub(pattern, '', message.strip(), flags=re.IGNORECASE)
    return cleaned.strip()


def resolve_staff_extension(
    db: Session,
    staff: Any,
    company_id: Optional[int] = None,
    called_did: Optional[str] = None
) -> Optional[str]:
    """
    Dynamically resolves the active extension assigned to a staff employee
    from the company's published call flow version.
    Returns None if no active extension slot is assigned.
    """
    if not staff or db is None:
        return None
    staff_id = getattr(staff, "id", None) if not isinstance(staff, (int, str)) else int(staff)
    if not staff_id:
        return None

    target_cid = company_id
    if not target_cid and hasattr(staff, "base_company_id"):
        target_cid = getattr(staff, "base_company_id", None)
    if not target_cid:
        target_cid = 1

    try:
        from app.services.telephony.flow_interpreter import CallFlowInterpreter
        return CallFlowInterpreter.get_staff_configured_extension(
            db=db,
            company_id=int(target_cid),
            staff_id=int(staff_id),
            called_did=called_did
        )
    except Exception as e:
        logger.warning(f"[WA-EXT] Failed to resolve dynamic extension for staff {staff_id}: {e}")
        return None


def format_staff_whatsapp_message(
    message: str,
    staff_name: str,
    contact_number: Optional[str] = None,
    extension: Optional[str] = None,
    channel: str = "whatsapp"
) -> str:
    """
    Authoritative staff signature composer.
    Appends:

    Regards,
    <Staff Name>
    +91 85858 52738 | +91 8897797667  (for WhatsApp)
    Ext: <X>   (ONLY when extension is configured)

    Or for Ivy/IVR:
    +91 85858 52738 | +91 80317 28899

    If employee does NOT have an extension:
    - Include staff name
    - Include contact numbers
    - Do NOT display empty extension, "Ext: N/A", or placeholder.

    Guards against stacked or double signatures by stripping prior signature blocks.
    When contact_number is explicitly passed, respects the argument for backward compatibility.
    """
    if not message:
        return ""
    clean_msg = message.strip()
    if not staff_name or not str(staff_name).strip():
        return clean_msg

    # Strip existing trailing signature if present to ensure idempotency
    clean_msg = strip_staff_whatsapp_signature(clean_msg)

    # Use channel dual numbers if not explicitly overridden
    if contact_number is None:
        contacts = get_channel_business_contacts(channel)
        contact_str = contacts["combined_formatted"]
    else:
        contact_str = str(contact_number).strip()

    # Build signature block
    sig_lines = ["Regards,", str(staff_name).strip()]
    if contact_str:
        sig_lines.append(contact_str)

    clean_ext = str(extension or "").strip()
    if clean_ext and clean_ext.lower() not in ("none", "null", "undefined", "n/a"):
        sig_lines.append(f"Ext: {clean_ext}")

    signature = "\n".join(sig_lines)
    return f"{clean_msg}\n\n{signature}"


def _render_body(body_text: str, context: Dict[str, Any]) -> str:
    """Replace {{variable}} and {{1}}, {{2}} placeholders in template body."""
    if not body_text:
        return ""
    import re as _re
    result = body_text

    # 1. Direct key replacement
    for key, value in context.items():
        val_str = str(value) if value is not None else ""
        result = result.replace(f"{{{{{key}}}}}", val_str)
        result = result.replace(f"{{{key}}}", val_str)

    # 2. Positional aliases if 'name' is in context
    lead_name = context.get("name") or context.get("customer_name") or context.get("lead_name")
    if lead_name:
        result = result.replace("{{1}}", str(lead_name))
        result = result.replace("{1}", str(lead_name))
        result = result.replace("{{name}}", str(lead_name))
        result = result.replace("{name}", str(lead_name))

    # 3. Clean up any remaining unpopulated placeholders like {{1}}, {{name}}
    result = _re.sub(r'\{\{(?:1|name|customer_name)\}\}', 'Valued Customer', result)
    result = _re.sub(r'\{\{[0-9]+\}\}', '', result)
    return result


def _is_valid_phone(phone: str) -> bool:
    """
    DC-FIX-INVPHONE-001: Reject obviously invalid / placeholder phone numbers
    before hitting the Meta API. Saves API quota and avoids 131026 errors.
    Rules:
    - Must have exactly 10 digits after stripping country code (+91/91)
    - Must not have any single digit dominating ≥8 of 10 positions
      (catches 9999999999, 9999999901, 1111111111, 0000000000, etc.)
    """
    import re as _re
    from collections import Counter
    digits = _re.sub(r'\D', '', phone)
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if len(digits) < 10:
        return False
    core = digits[-10:]
    if max(Counter(core).values()) >= 8:
        return False
    return True


def _build_template_components(template, context: Dict[str, Any]) -> list:
    """
    DC-TMPL-COMPONENTS-001: Build Meta API components array for approved templates.
    Extracts named variables from body_text in order → positional {{1}}, {{2}}, …
    Adds image header component if header_type == 'image' and media URL is set.
    Adds URL button components for each button of type 'url'.
    """
    import re as _re
    components = []

    # ── Header (image) ───────────────────────────────────────────────────────
    if getattr(template, 'header_type', 'none') == 'image':
        img_url = getattr(template, 'header_media_url', None) or ""
        if img_url.startswith("http"):
            components.append({
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": img_url}}]
            })

    # ── Body parameters (named vars in appearance order → positional) ────────
    body_text = getattr(template, 'body_text', '') or ''
    var_names = list(dict.fromkeys(_re.findall(r'\{\{(\w+)\}\}', body_text)))
    if var_names and context:
        body_params = []
        for var in var_names:
            # Resolve named variable or positional variable {{1}} -> name
            val = str(context.get(var, '') or (context.get('name', '') if var == '1' else '') or '').strip() or 'Customer'
            body_params.append({"type": "text", "text": val})
        if body_params:
            components.append({"type": "body", "parameters": body_params})

    # ── Buttons (URL type with dynamic variable parameter) ────────────────────
    buttons = getattr(template, 'buttons', None) or []
    for i, btn in enumerate(buttons):
        if isinstance(btn, dict) and btn.get('type') == 'url':
            url_val = btn.get('url', '')
            if '{{' in url_val:
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": str(i),
                    "parameters": [{"type": "text", "text": url_val}]
                })

    return components


def _send_meta(phone: str, message: str, template=None, db=None,
               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Send via Meta Cloud API.
    If template has meta_template_name + is_meta_approved → use template type with
    full components (image header, body params, URL buttons).
    FAIL-CLOSED: If template is missing or unapproved, REJECTS freeform text fallback
    to prevent Meta 131047 re-engagement errors on cold outbound customer outreach.
    """
    # Reject invalid/placeholder numbers
    if not _is_valid_phone(phone):
        logger.warning("[WA-AUTO] Skipping invalid/placeholder phone: %s", phone)
        return {"success": False, "reason": "invalid_phone_number", "error_code": "INV_PHONE"}

    # 1. Template-based send validation
    if template:
        if not getattr(template, 'meta_template_name', None) or not getattr(template, 'is_meta_approved', False):
            tmpl_id = getattr(template, 'id', 'None')
            tmpl_name = getattr(template, 'name', 'Selected template')
            status = getattr(template, 'meta_approval_status', 'UNAPPROVED')
            logger.warning(
                f"[WA-AUTO] Unapproved template (ID: {tmpl_id}, Name: {tmpl_name}, Status: {status}). "
                f"Cannot dispatch unapproved template via Meta Cloud API."
            )
            return {
                "success": False,
                "reason": f"Template '{tmpl_name}' is not approved by Meta (status: {status or 'UNAPPROVED'}). Please select an approved Meta template or send via Scanned WhatsApp.",
                "error_code": "TMPL_NOT_APPROVED"
            }
    else:
        # 2. Freeform text send validation (Meta 24-Hour Customer Service Window)
        is_window_open = False
        if db:
            try:
                from app.models.whatsapp import WAInbox
                from datetime import datetime, timedelta
                cutoff_24h = datetime.utcnow() - timedelta(hours=24)
                clean_10 = phone[-10:] if len(phone) >= 10 else phone
                inbound_msg = db.query(WAInbox).filter(
                    WAInbox.from_phone.like(f"%{clean_10}%"),
                    WAInbox.message_type != "outbound",
                    WAInbox.received_at >= cutoff_24h
                ).order_by(WAInbox.received_at.desc()).first()
                if inbound_msg:
                    is_window_open = True
            except Exception as _we:
                logger.warning(f"[WA-AUTO] Error checking 24h service window: {_we}")

        if not is_window_open:
            logger.warning(
                f"[WA-AUTO] Cold outbound text to {phone} suppressed: "
                f"Recipient has not messaged within Meta 24-hour service window. "
                f"Baileys Bot fallback for customer 1-to-1 outreach is strictly disabled to prevent SIM restriction."
            )
            return {
                "success": False,
                "reason": "Meta 24-hour customer service window has expired. Direct 1-to-1 customer messaging via Baileys is disabled to protect SIM accounts.",
                "error_code": "WINDOW_EXPIRED"
            }

    # [DC-WA-CREDS] Get live credentials from DB if available
    token, phone_id = _get_meta_creds(db)
    if not token or not phone_id:
        logger.warning("[WA-AUTO] No Meta credentials — skipping send to %s", phone)
        return {"success": False, "reason": "no_credentials", "error_code": "NO_CREDS"}

    meta_base = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    import re as _re
    _digits = _re.sub(r'\D', '', phone)
    if _digits.startswith('91') and len(_digits) == 12:
        recipient = _digits
    else:
        recipient = '91' + _digits[-10:]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if template:
        tpl_payload: Dict[str, Any] = {
            "name": template.meta_template_name,
            "language": {"code": template.meta_template_language or "en"},
        }
        components = _build_template_components(template, context or {})
        if components:
            tpl_payload["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": tpl_payload,
        }
    else:
        # Freeform text inside 24h window
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message}
        }

    try:
        resp = requests.post(meta_base, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code in (200, 201):
            wamid = data.get("messages", [{}])[0].get("id", "")
            if not wamid:
                logger.error("[WA-AUTO] Meta returned HTTP 200 without WAMID: %s", data)
                return {"success": False, "reason": "Missing WAMID in Meta response", "error_code": "NO_WAMID"}
            return {"success": True, "wamid": wamid}
        else:
            err_obj = data.get("error", {})
            err_code = str(err_obj.get("code") or resp.status_code)[:10]
            error = err_obj.get("message", "Unknown error")
            logger.error("[WA-AUTO] Meta API error for %s (%s): %s", phone, err_code, error)
            return {"success": False, "reason": error, "error_code": err_code}
    except Exception as e:
        logger.error("[WA-AUTO] Send exception for %s: %s", phone, str(e))
        return {"success": False, "reason": str(e), "error_code": "NET_ERR"}


def _log_message(db: Session, phone: str, message: str, result: Dict, event_key: str,
                 lead_id: Optional[int] = None, staff_id: Optional[int] = None,
                 template_id: Optional[int] = None,
                 sent_by_name: Optional[str] = None, sender_type: Optional[str] = None,
                 message_type: Optional[str] = None,
                 job_id: Optional[str] = None, execution_id: Optional[str] = None):
    """Log auto-send to message_log table with genuine WAMID only."""
    try:
        from app.models.whatsapp import MessageLog
        if staff_id and not sent_by_name:
            try:
                from app.models.staff import StaffEmployee
                se = db.query(StaffEmployee).get(staff_id)
                if se:
                    sent_by_name = f"{getattr(se,'first_name','')} {getattr(se,'last_name','')}".strip() or getattr(se,'name','') or f"Staff #{staff_id}"
            except Exception:
                sent_by_name = f"Staff #{staff_id}"
        if not sent_by_name:
            sent_by_name = "System/Auto"
        if not sender_type:
            sender_type = "staff" if staff_id else "auto"

        resolved_message_type = message_type if message_type is not None else f"auto_{event_key}"
        wamid = result.get("wamid")
        is_succ = bool(result.get("success") and wamid)

        now_utc = datetime.utcnow()
        clean_phone = phone[-10:] if len(phone) >= 10 else phone
        fallback_id = f"failed_{event_key}_{int(now_utc.timestamp())}_{clean_phone}"

        err_code = str(result.get("error_code") or "")[:10] if not is_succ else None
        err_msg = str(result.get("reason") or "")[:95] if not is_succ else None

        log = MessageLog(
            message_sid=wamid or fallback_id,
            message_type=resolved_message_type,
            mobile_number=phone,
            message_body=message,
            to_number=phone,
            provider="META_WHATSAPP",
            initial_status="sent" if is_succ else "failed",
            current_status="sent" if is_succ else "failed",
            status_source="SYSTEM",
            sent_at=now_utc if is_succ else None,
            failed_at=now_utc if not is_succ else None,
            error_code=err_code,
            error_message=err_msg,
            failure_reason=err_msg,
            sent_by_staff_id=staff_id,
            sent_by_name=sent_by_name,
            sender_type=sender_type,
            job_id=job_id,
            execution_id=execution_id
        )
        db.add(log)

        # Dual-write to wa_inbox if genuine WAMID exists
        if is_succ and wamid:
            try:
                from app.models.whatsapp import WAInbox
                inbox_item = WAInbox(
                    wamid=wamid,
                    from_phone=clean_phone,
                    from_name=sent_by_name or "System Outbound",
                    message_type="outbound",
                    body_text=message,
                    is_read=True,
                    received_at=now_utc,
                    status='new',
                    replied=False,
                )
                db.add(inbox_item)
            except Exception as _ie:
                logger.warning("[WA-AUTO] Dual-write wa_inbox error: %s", str(_ie))

        db.commit()
        return log.id
    except Exception as e:
        logger.error("[WA-AUTO] Log exception: %s", str(e))
        db.rollback()
        return None


def _log_to_crm_note(db: Session, lead_id: int, message: str, event_key: str,
                     staff_id: Optional[int] = None, wamid: Optional[str] = None):
    """Append WhatsApp send as a note in crm_lead_notes (lead history)."""
    try:
        from app.models.crm import CRMLead, CRMLeadNote
        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        if not lead:
            return
            
        note_text = (
            f"📱 WhatsApp auto-message sent [{event_key}]\n"
            f"{message[:300]}{'...' if len(message) > 300 else ''}"
        )
        if wamid:
            note_text += f"\nDelivery ID: {wamid}"
            
        created_by_id = None
        created_by_type = None
        if staff_id:
            from app.models.staff import StaffEmployee
            staff = db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first()
            if staff:
                created_by_id = staff.emp_code
                created_by_type = "staff"
                
        note = CRMLeadNote(
            company_id=lead.company_id,
            lead_id=lead_id,
            note=note_text,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
            created_at=datetime.utcnow(),
        )
        db.add(note)
        db.commit()
    except Exception as e:
        logger.error("[WA-AUTO] CRM note exception: %s", str(e))


def _dedup_key(event_key: str, identifier: str) -> str:
    return f"{event_key}:{identifier}"


def _is_duplicate(key: str) -> bool:
    """Return True if this event was sent recently (within dedup window)."""
    now = datetime.utcnow()
    _recent_sends.update({k: v for k, v in _recent_sends.items()
                           if now - v < timedelta(minutes=_DEDUP_WINDOW_MINUTES)})
    return key in _recent_sends


def _mark_sent(key: str):
    _recent_sends[key] = datetime.utcnow()


# ── Main public function ───────────────────────────────────────────────────────

def send_auto_whatsapp(
    db: Session,
    event_key: str,
    phone: str,
    context: Dict[str, Any],
    lead_id: Optional[int] = None,
    staff_id: Optional[int] = None,
):
    """
    Fire-and-forget auto WhatsApp send for a system event.
    Call this as a FastAPI BackgroundTask — it does NOT block the response.

    Args:
        db: SQLAlchemy session
        event_key: e.g. 'crm_status_won', 'po_dispatched', 'ticket_raised'
        phone: recipient phone (10-digit or +91 format)
        context: variables for template rendering: {name, status, order_no, ...}
        lead_id: CRM lead ID (for note logging)
        staff_id: initiating staff ID
    """
    if not phone or len(phone.strip()) < 10:
        return

    if _is_paused(db):
        logger.info("[WA-AUTO] Paused — skipping %s for %s", event_key, phone)
        return

    # Dedup check
    dedup = _dedup_key(event_key, f"{lead_id or phone}")
    if _is_duplicate(dedup):
        logger.info("[WA-AUTO] Dedup skip %s", dedup)
        return

    # Find trigger config
    try:
        from app.models.whatsapp import WhatsAppAutoTrigger, WhatsAppTemplate
        trigger = db.query(WhatsAppAutoTrigger).filter_by(
            event_key=event_key, is_enabled=True
        ).first()

        if not trigger:
            logger.debug("[WA-AUTO] No active trigger for %s", event_key)
            return

        template = trigger.template
        if not template or not template.is_active:
            logger.debug("[WA-AUTO] No active template for trigger %s", event_key)
            return

        # Render message
        message = _render_body(template.body_text, context)

        # Send — pass context so Meta template components can be built
        result = _send_meta(phone, message, template, db=db, context=context)
        _mark_sent(dedup)

        # Log
        _log_message(db, phone, message, result, event_key, lead_id, staff_id, template.id)
        if lead_id and result.get("success"):
            _log_to_crm_note(db, lead_id, message, event_key, staff_id, result.get("wamid"))

        if not result.get("success") and (lead_id or event_key.startswith("crm_lead_")):
            logger.warning(
                "[WA-AUTO] Meta API failed for lead event '%s' (%s). Executing Scanned WhatsApp fallback with pacing delay...",
                event_key, phone
            )
            fb_res = dispatch_scanned_lead_fallback(
                db=db,
                phone=phone,
                message=message,
                lead_id=lead_id,
                staff_id=staff_id,
                event_key=event_key,
                reason=result.get("reason")
            )
            return fb_res

        logger.info("[WA-AUTO] %s → %s: %s", event_key, phone, "OK" if result.get("success") else "FAIL")

    except Exception as e:
        logger.error("[WA-AUTO] Exception for %s / %s: %s", event_key, phone, str(e))


# ── Direct send (from CRM WhatsApp button / test page) ───────────────────────

def send_direct_whatsapp(
    db: Session,
    phone: str,
    message: str,
    template_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    campaign_log_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
    execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Directly send a WhatsApp message (test page, CRM button, campaign, automation).
    Returns result dict with message_log_id. Logs to message_log and CRM note if lead_id provided.
    """
    if _is_paused(db):
        return {"success": False, "reason": "WhatsApp is paused by VGK control"}

    # [DC-VGK-BLOCKED-001] Avoid sending communications to blocked members
    try:
        clean_p = ''.join(c for c in str(phone or '') if c.isdigit())[-10:]
        if len(clean_p) == 10:
            is_blocked = db.execute(text("""
                SELECT 1 FROM official_partners 
                WHERE (is_blocked = TRUE OR member_status = 'BLOCKED')
                  AND RIGHT(REGEXP_REPLACE(COALESCE(phone, whatsapp_number, ''), '[^0-9]', '', 'g'), 10) = :p
                LIMIT 1
            """), {"p": clean_p}).scalar()
            if is_blocked:
                logger.info(f"[WA-DIRECT-SEND] Suppressing message to blocked partner phone {clean_p}")
                return {
                    "success": False,
                    "reason": "blocked_member",
                    "message": "Recipient is a Blocked Channel Partner. Communications are strictly suppressed."
                }
    except Exception as _b_err:
        logger.warning(f"[WA-DIRECT-SEND] Block check error: {_b_err}")

    template = None
    if template_id:
        try:
            from app.models.whatsapp import WhatsAppTemplate
            template = db.query(WhatsAppTemplate).get(template_id)
        except Exception:
            pass

    result = _send_meta(phone, message, template, db=db, context=context)

    # Log with sender info and automation linkage
    ml_id = _log_message(db, phone, message, result, "direct_send", lead_id, staff_id, template_id,
                         sender_type="staff" if staff_id else "system",
                         job_id=job_id, execution_id=execution_id)
    if ml_id:
        result["message_log_id"] = ml_id

    if lead_id and result.get("success"):
        _log_to_crm_note(db, lead_id, message, "direct_send", staff_id, result.get("wamid"))

    # Update campaign log if applicable
    if campaign_log_id and result.get("success"):
        try:
            from app.models.whatsapp import WhatsAppCampaignLog
            log = db.query(WhatsAppCampaignLog).get(campaign_log_id)
            if log:
                log.status = "sent"
                log.wamid = result.get("wamid")
                log.sent_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error("[WA-DIRECT] Campaign log update error: %s", str(e))

    return result


# ── Staff daily morning reminder ───────────────────────────────────────────────

def send_staff_morning_reminder(db: Session, staff_employee, portal_base_url: str = "https://www.myntreal.com"):
    """
    Send a personalised morning WhatsApp to one staff member.
    Called by APScheduler job at 8AM IST every weekday.
    DC-FIX-TRIGGER-001: Respects the is_enabled toggle — if the trigger is disabled
    in the Auto-Triggers UI, this function skips the send entirely.
    DC-FIX-DUPWA-001: Caller (run_staff_morning_reminders) holds a PG advisory lock,
    so this is invoked by only one worker process.
    """
    phone = getattr(staff_employee, 'phone', None)
    name  = getattr(staff_employee, 'full_name', None) or getattr(staff_employee, 'name', 'Team Member')

    if not phone:
        return {"success": False, "reason": "no_phone"}

    if _is_paused(db):
        logger.info("[WA-MORNING] Skipped (paused) for %s", name)
        return {"success": False, "reason": "paused"}

    if not _is_valid_phone(phone):
        logger.warning("[WA-MORNING] Skipping invalid phone %s for %s", phone, name)
        return {"success": False, "reason": "invalid_phone_number"}

    today_ist = datetime.utcnow()
    today_str = today_ist.strftime('%A, %d %B %Y')

    try:
        from app.models.whatsapp import WhatsAppAutoTrigger
        # DC-FIX-TRIGGER-001: Look up trigger without is_enabled filter so we can
        # detect disabled state and skip, rather than falling back to hardcoded text.
        trigger = db.query(WhatsAppAutoTrigger).filter_by(
            event_key='staff_morning_reminder'
        ).first()

        if not trigger:
            logger.warning("[WA-MORNING] No trigger configured for staff_morning_reminder — skipping %s", name)
            return {"success": False, "reason": "no_trigger_configured"}

        if not trigger.is_enabled:
            logger.info("[WA-MORNING] Trigger disabled — skipping %s", name)
            return {"success": False, "reason": "trigger_disabled"}

        template = trigger.template if (trigger.template and trigger.template.is_active) else None

        if template:
            message = _render_body(template.body_text, {
                'name': name,
                'date': today_str,
                'kra_link': f"{portal_base_url}/staff/kra-status",
                'tasks_link': f"{portal_base_url}/staff/tasks",
                'timesheet_link': f"{portal_base_url}/staff/timesheet",
                'dashboard_link': f"{portal_base_url}/staff/dashboard",
            })
        else:
            message = (
                f"🌅 Good morning, {name}!\n\n"
                f"📅 *{today_str}*\n\n"
                f"Here are your quick links for today:\n"
                f"📊 KRA Status: {portal_base_url}/staff/kra-status\n"
                f"✅ My Tasks: {portal_base_url}/staff/tasks\n"
                f"⏱ Timesheet: {portal_base_url}/staff/timesheet\n"
                f"📋 Dashboard: {portal_base_url}/staff/dashboard\n\n"
                f"Have a productive day! 💪"
            )

        result = _send_meta(phone, message, template, db=db)
        _log_message(db, phone, message, result, "staff_morning_reminder", staff_id=staff_employee.id)
        logger.info("[WA-MORNING] %s (%s): %s", name, phone, "OK" if result.get("success") else result.get("reason","FAIL"))
        return result

    except Exception as e:
        logger.error("[WA-MORNING] Error for %s: %s", name, str(e))
        return {"success": False, "reason": str(e)}


def dispatch_scanned_lead_fallback(
    db: Session,
    phone: str,
    message: str,
    lead_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    event_key: str = "lead_welcome",
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    DC Anti-Ban Protocol Apr 2026:
    When Meta WhatsApp Cloud API fails for a new lead message (e.g., Error 131031 deadlock,
    unapproved template, 24h window expiry, or network error), safely failover to dispatch
    the same message via Scanned WhatsApp Bot Gateway (port 5002) or whatsapp_bot_queue.

    Enforces:
    - Canonical 10-digit phone normalization and target JID generation (91XXXXXXXXXX@s.whatsapp.net).
    - Gateway health check with safe fallback to PostgreSQL whatsapp_bot_queue if bot is offline.
    - Pacing delay / time gap to prevent instant burst spam triggers on the scanned SIM.
    - Full persistence into MessageLog with provider="SCANNED_FALLBACK" or "SCANNED_QUEUE".
    - Logging failover note into CRM lead history.
    """
    import os
    import re as _re
    import time
    from datetime import datetime
    import json
    from sqlalchemy import text

    clean_digits = _re.sub(r'\D', '', str(phone or ''))
    if len(clean_digits) < 10:
        logger.warning("[WA-LEAD-FALLBACK] Invalid phone '%s' — skipping fallback", phone)
        return {"success": False, "reason": "invalid_phone_number"}

    clean_10 = clean_digits[-10:]
    clean_p = "91" + clean_10
    target_jid = f"{clean_p}@s.whatsapp.net"
    now_ts = int(datetime.utcnow().timestamp())
    exec_id = f"lead_fb_{clean_10}_{now_ts}"

    logger.info(
        "[WA-LEAD-FALLBACK] Initiating Scanned WhatsApp fallback for lead #%s (%s). Reason: %s",
        lead_id or "N/A", clean_10, reason or "Meta API failed"
    )

    # 1. Fast Gateway Health Check
    env_url = os.getenv("WHATSAPP_BOT_URL") or os.getenv("WA_BOT_URL")
    urls = []
    if env_url:
        urls.append(env_url if env_url.endswith("/api/send-message") else f"{env_url.rstrip('/')}/api/send-message")
    urls.extend([
        "http://127.0.0.1:5002/api/send-message",
        "http://localhost:5002/api/send-message"
    ])

    gateway_online = False
    can_send_now = False
    status_urls = ["http://127.0.0.1:5002/status", "http://localhost:5002/status"]
    for s_url in status_urls:
        try:
            s_resp = requests.get(s_url, timeout=1.5)
            if s_resp.status_code == 200:
                gateway_online = True
                s_data = s_resp.json()
                can_send_now = bool(s_data.get("can_send_now")) or (s_data.get("connection_state") == "connected")
                break
        except Exception:
            continue

    dispatched = False
    last_err = None
    wamid = None

    if gateway_online and can_send_now:
        # Enforce anti-ban pacing delay before dispatching to port 5002
        time.sleep(3.0)
        for bot_url in urls:
            try:
                bot_payload = {
                    "phone": clean_p,
                    "message": message,
                    "lead_id": lead_id,
                    "job_id": "lead_welcome_fallback",
                    "execution_id": exec_id,
                    "skip_backend_log": True
                }
                resp = requests.post(bot_url, json=bot_payload, timeout=12)
                if resp.status_code == 200:
                    raw = resp.json()
                    if raw.get("success"):
                        dispatched = True
                        wamid = raw.get("message_id") or (raw.get("key") or {}).get("id") or exec_id
                        break
                    else:
                        last_err = raw.get("error") or "Bot rejected message"
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_err = str(e)
                continue
    else:
        last_err = "Scanned WhatsApp bot offline / disconnected / standby mode"

    now_utc = datetime.utcnow()
    from app.models.whatsapp import MessageLog

    if dispatched and wamid:
        try:
            ml = MessageLog(
                message_sid=wamid,
                message_type=f"fallback_{event_key}",
                mobile_number=clean_10,
                message_body=message,
                from_number="8897797667",
                to_number=f"+{clean_p}",
                provider="SCANNED_FALLBACK",
                initial_status="sent",
                current_status="sent",
                status_source="LEAD_FALLBACK_API",
                sent_at=now_utc,
                sent_by_staff_id=staff_id,
                sent_by_name="System/Fallback",
                sender_type="system",
                job_id="lead_welcome_fallback",
                execution_id=exec_id
            )
            db.add(ml)
            if lead_id:
                _log_to_crm_note(
                    db, lead_id,
                    f"📲 [Meta API Failover] Sent via Scanned WhatsApp (Paced). WAMID: {wamid}",
                    event_key, staff_id=staff_id, wamid=wamid
                )
            db.commit()
            logger.info("✅ [WA-LEAD-FALLBACK] Successfully dispatched to %s via Scanned Bot", clean_10)
            return {"success": True, "wamid": wamid, "channel": "scanned_fallback", "via": "direct_gateway"}
        except Exception as _log_e:
            db.rollback()
            logger.warning("[WA-LEAD-FALLBACK] MessageLog write warning: %s", _log_e)
            return {"success": True, "wamid": wamid, "channel": "scanned_fallback", "via": "direct_gateway"}

    # Scanned bot offline or direct dispatch failed -> Safely enqueue into PostgreSQL whatsapp_bot_queue!
    try:
        rp = {
            "phone": clean_10,
            "clean_phone": clean_p,
            "source": "lead_fallback",
            "lead_id": lead_id,
            "event_key": event_key,
            "enqueued_reason": last_err or reason or "Meta API failure failover",
            "enqueued_at": now_utc.isoformat()
        }
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (
                target_type, target_jid, message, status, created_at, result_payload, job_id, execution_id
            ) VALUES (
                'direct', :target_jid, :message, 'pending', NOW(), CAST(:rp AS jsonb), 'lead_welcome_fallback', :execution_id
            )
        """), {
            "target_jid": target_jid,
            "message": message,
            "rp": json.dumps(rp),
            "execution_id": exec_id
        })

        ml = MessageLog(
            message_sid=exec_id,
            message_type=f"fallback_{event_key}",
            mobile_number=clean_10,
            message_body=message,
            from_number="8897797667",
            to_number=f"+{clean_p}",
            provider="SCANNED_QUEUE",
            initial_status="queued",
            current_status="queued",
            status_source="LEAD_FALLBACK_QUEUE",
            sent_by_staff_id=staff_id,
            sent_by_name="System/FallbackQueue",
            sender_type="system",
            job_id="lead_welcome_fallback",
            execution_id=exec_id
        )
        db.add(ml)
        if lead_id:
            _log_to_crm_note(
                db, lead_id,
                f"⏳ [Meta API Failover] Queued in Scanned WhatsApp queue (will auto-send with safe pacing once connected). Exec: {exec_id}",
                event_key, staff_id=staff_id, wamid=exec_id
            )
        db.commit()
        logger.info("⏳ [WA-LEAD-FALLBACK] Enqueued into whatsapp_bot_queue for %s (will auto-send with pacing)", clean_10)
        return {"success": True, "queued": True, "execution_id": exec_id, "channel": "scanned_fallback", "via": "bot_queue"}
    except Exception as q_err:
        db.rollback()
        logger.error("[WA-LEAD-FALLBACK] Failed to enqueue into whatsapp_bot_queue: %s", q_err)
        return {"success": False, "reason": str(q_err), "error_code": "FALLBACK_QUEUE_ERROR"}


def send_lead_welcome(
    db,
    phone: str,
    lead_name: str,
    lead_id: int,
    partner_phone: Optional[str] = None,
    staff_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    DC Protocol Apr 2026: Send bilingual (EN+TE) welcome message to every new lead.
    - partner_phone provided  → use 'lead_welcome_walkin' template (includes showroom number)
    - partner_phone is None   → use 'lead_welcome_general' template (company number hardcoded)
    Non-fatal: any failure is logged but does not break lead creation.
    """
    try:
        if not _is_valid_phone(phone):
            logger.warning("[WA-WELCOME] Invalid phone %s — skipping", phone)
            return {"success": False, "reason": "invalid_phone"}

        # Detect Solar lead or ETC Training lead
        is_etc_training = False
        is_solar = False
        if lead_id:
            try:
                from app.models.crm import CRMLead
                lead_obj = db.query(CRMLead).get(lead_id)
                if lead_obj:
                    if lead_obj.category_id == 16 or lead_obj.company_id == 2 or 'etc' in (lead_obj.tags or '').lower() or 'training' in (lead_obj.tags or '').lower():
                        is_etc_training = True
                    if (getattr(lead_obj, 'company_id', None) == 4 or
                        'solar' in (getattr(lead_obj, 'tags', None) or '').lower() or
                        getattr(lead_obj, 'solar_pipeline_status', None) or
                        getattr(lead_obj, 'solar_brand_id', None) or
                        getattr(lead_obj, 'solar_capacity', None)):
                        is_solar = True
            except Exception:
                pass

        if is_solar:
            event_key = "lead_welcome_solar"
        elif is_etc_training:
            event_key = "lead_welcome_etc_training"
        elif partner_phone:
            event_key = "lead_welcome_walkin"
        else:
            event_key = "lead_welcome_general"

        # Persistent Dedup: Check DB if welcome was already sent in last 7 days
        from sqlalchemy import or_
        from app.models.whatsapp import MessageLog
        import re as _re

        clean_phone_10 = _re.sub(r'\D', '', str(phone or ''))[-10:]
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # 1. In-memory check first
        dedup = _dedup_key(event_key, str(lead_id or clean_phone_10))
        if dedup in _sent_cache:
            return {"success": False, "reason": "already_sent_cache"}

        # 2. Persistent MessageLog check (covers server restarts / multi-worker)
        try:
            if clean_phone_10:
                existing_log = db.query(MessageLog).filter(
                    MessageLog.sent_at >= seven_days_ago,
                    MessageLog.current_status.in_(['sent', 'delivered']),
                    MessageLog.mobile_number.like(f"%{clean_phone_10}"),
                    or_(
                        MessageLog.message_type.like('%welcome%'),
                        MessageLog.message_type.like('%thankyou%'),
                        MessageLog.message_body.like('%Welcome to%'),
                        MessageLog.message_body.like('%ధన్యవాదాలు%'),
                        MessageLog.message_body.like('%స్వాగతం%')
                    )
                ).first()

                if existing_log:
                    logger.info(
                        f"[WA-WELCOME] Lead #{lead_id} ({clean_phone_10}) already received welcome message "
                        f"on {existing_log.sent_at} (ID: {existing_log.id}) — skipping to prevent spam."
                    )
                    return {"success": False, "reason": "already_sent_db", "message_log_id": existing_log.id}
        except Exception as _dedup_err:
            logger.warning(f"[WA-WELCOME] Error querying persistent dedup: {_dedup_err}")

        from app.models.whatsapp import WhatsAppTemplate
        template = db.query(WhatsAppTemplate).filter_by(slug=event_key, is_active=True).first()
        if not template:
            if event_key == "lead_welcome_solar":
                _sol_body = (
                    "Hello {{name}}! ☀️\n\n"
                    "Welcome to *MyntReal Har Ghar Solar* — India's trusted clean energy platform.\n\n"
                    "Explore our official Digital Catalog & Subsidy Calculator:\n"
                    "👉 https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te\n\n"
                    "⚡ Key Highlights:\n"
                    "• 90% power bill reduction\n"
                    "• ₹78,000 Central Govt Subsidy (PM Surya Ghar)\n"
                    "• ₹1 Solar Scheme & Zero-Down Payment Bank Loans\n"
                    "• Tier-1 Brands (Tata, Adani, Waaree, Goldi) with 25-Year Warranty\n\n"
                    "Our Solar Specialist will connect with you shortly for your free site survey.\n\n"
                    "📞 Helpline: +91 85858 52738\n"
                    "🌐 www.myntreal.com\n\n"
                    "———————————————\n"
                    "నమస్కారం {{name}}! ☀️\n\n"
                    "*MyntReal హర్ ఘర్ సోలార్* కు స్వాగతం.\n\n"
                    "మా డిజిటల్ క్యాటలాగ్ & సబ్సిడీ కాలిక్యులేటర్ లింక్ ఇక్కడ చూడండి:\n"
                    "👉 https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te\n\n"
                    "కరెంట్ బిల్లు 90% వరకు ఆదా, ₹78,000 కేంద్ర సబ్సిడీ మరియు ₹1 కే సోలార్ వివరాలను పై లింక్ ద్వారా తెలుసుకోండి. మా సోలార్ స్పెషలిస్ట్ త్వరలోనే మిమ్మల్ని సంప్రదిస్తారు!\n\n"
                    "📞 సంప్రదించండి: +91 85858 52738\n\n"
                    "*— టీమ్ MyntReal Har Ghar Solar*"
                )
                template = WhatsAppTemplate(
                    slug="lead_welcome_solar",
                    name="Lead Welcome — Solar Rooftop Inquiry",
                    segment="solar",
                    template_type="text",
                    body_text=_sol_body,
                    meta_template_name="myntreal_lead_welcome_solar",
                    meta_template_language="en",
                    is_meta_approved=False,
                    is_active=True
                )
            else:
                # Fallback to general template if specific template is missing
                template = db.query(WhatsAppTemplate).filter_by(slug="lead_welcome_general", is_active=True).first()

        # Fallback to approved myntreal_lead_thankyou_general if template is missing or unapproved
        if not template or not getattr(template, 'is_meta_approved', False):
            if (event_key in ("lead_welcome_general", "lead_welcome_solar") or not template or not getattr(template, 'is_meta_approved', False)):
                fallback = db.query(WhatsAppTemplate).filter_by(slug="myntreal_lead_thankyou_general", is_active=True).first()
                if fallback and getattr(fallback, 'is_meta_approved', False):
                    logger.info(
                        "[WA-WELCOME] Falling back from unapproved/missing '%s' to approved 'myntreal_lead_thankyou_general'",
                        event_key
                    )
                    template = fallback
                    event_key = "myntreal_lead_thankyou_general"

        if not template:
            logger.warning("[WA-WELCOME] Template '%s' not found — skipping", event_key)
            return {"success": False, "reason": "template_not_found"}

        safe_lead_name = (lead_name or "there").strip()
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        context = {
            "1": safe_lead_name,
            "name": safe_lead_name,
            "lead_name": safe_lead_name,
            "customer_name": safe_lead_name,
            "lead_ref": f"#{lead_id}" if lead_id else "LEAD",
            "catalog_url": "https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te",
            "date": now_ist.strftime("%d-%m-%Y")
        }
        if partner_phone:
            context["partner_phone"] = partner_phone
        message = _render_body(template.body_text, context)

        result = _send_meta(phone, message, template, db=db, context=context)
        _log_message(db, phone, message, result, event_key, lead_id=lead_id, staff_id=staff_id, template_id=template.id)

        if result.get("success"):
            _sent_cache[dedup] = datetime.utcnow()
            logger.info("[WA-WELCOME] %s → %s: OK", event_key, phone)
            return result
        else:
            logger.warning(
                "[WA-WELCOME] Meta API failed for %s (%s). Executing Scanned WhatsApp fallback with anti-ban pacing...",
                phone, result.get("reason")
            )
            fb_res = dispatch_scanned_lead_fallback(
                db=db,
                phone=phone,
                message=message,
                lead_id=lead_id,
                staff_id=staff_id,
                event_key=event_key,
                reason=result.get("reason")
            )
            if fb_res.get("success"):
                _sent_cache[dedup] = datetime.utcnow()
            return fb_res
    except Exception as e:
        logger.error("[WA-WELCOME] Exception for %s: %s", phone, str(e))
        return {"success": False, "reason": str(e)}


# ── DC_WA_TEMPLATES_SEED_001: Event-specific auto-send helpers ─────────────────

def send_ticket_created_wa(db: Session, ticket) -> Dict[str, Any]:
    """
    Send WhatsApp to customer when a service ticket is created.
    event_key: ticket_created_customer
    Non-fatal: any failure is logged but never raises.
    """
    try:
        phone = getattr(ticket, 'customer_phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_phone"}
        name = getattr(ticket, 'customer_name', None) or 'Customer'
        ticket_id = getattr(ticket, 'ticket_id', None) or str(getattr(ticket, 'id', ''))
        issue = getattr(ticket, 'issue_category', '') or ''
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='ticket_created_customer',
            phone=phone,
            context={'name': name, 'ticket_id': ticket_id, 'issue': issue, 'date': today_str},
        )
    except Exception as e:
        logger.error("[WA-TICKET-CREATE] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_ticket_closed_wa(db: Session, ticket) -> Dict[str, Any]:
    """
    Send WhatsApp to customer when a service ticket is closed.
    event_key: ticket_closed_customer
    """
    try:
        phone = getattr(ticket, 'customer_phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_phone"}
        name = getattr(ticket, 'customer_name', None) or 'Customer'
        ticket_id = getattr(ticket, 'ticket_id', None) or str(getattr(ticket, 'id', ''))
        issue = getattr(ticket, 'issue_category', '') or ''
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='ticket_closed_customer',
            phone=phone,
            context={'name': name, 'ticket_id': ticket_id, 'issue': issue, 'date': today_str},
        )
    except Exception as e:
        logger.error("[WA-TICKET-CLOSE] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_lead_assigned_staff_wa(
    db: Session,
    lead,
    staff,
    triggered_by_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Notify assigned staff via WhatsApp when a new lead is assigned to them.
    event_key: lead_assigned_staff
    """
    try:
        phone = getattr(staff, 'phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_staff_phone"}
        staff_name = getattr(staff, 'full_name', None) or getattr(staff, 'name', '') or 'Team Member'
        lead_name = getattr(lead, 'name', '') or 'Unknown'
        lead_phone = getattr(lead, 'phone', '') or '—'
        source = getattr(lead, 'source', '') or 'General'
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='lead_assigned_staff',
            phone=phone,
            context={
                'staff_name': staff_name,
                'lead_name': lead_name,
                'phone': lead_phone,
                'source': source.replace('_', ' ').title(),
                'date': today_str,
            },
            staff_id=triggered_by_id,
        )
    except Exception as e:
        logger.error("[WA-LEAD-ASSIGN] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_staff_morning_leadership(
    db: Session,
    staff_employee,
    portal_base_url: str = "https://www.myntreal.com",
) -> Dict[str, Any]:
    """
    Send morning leadership summary WhatsApp to Key Leadership / EA / VGK Supreme staff.
    Queries real-time DB stats for team snapshot.
    event_key: staff_morning_leadership
    """
    phone = getattr(staff_employee, 'phone', None)
    name = getattr(staff_employee, 'full_name', None) or getattr(staff_employee, 'name', 'Leader')

    if not phone or not _is_valid_phone(phone):
        return {"success": False, "reason": "no_valid_phone"}

    if _is_paused(db):
        return {"success": False, "reason": "paused"}

    try:
        from sqlalchemy import text as _text
        today_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        today_date = today_ist.date()
        today_str = today_ist.strftime('%a, %d %b %Y')
        today_midnight_utc = (today_ist.replace(hour=0, minute=0, second=0, microsecond=0)
                              - timedelta(hours=5, minutes=30))

        stats = db.execute(_text("""
            SELECT
                (SELECT COUNT(*) FROM staff_employees WHERE status='active') AS active_staff,
                (SELECT COUNT(*) FROM staff_tasks
                    WHERE status NOT IN ('completed','cancelled')) AS open_tasks,
                (SELECT COUNT(*) FROM staff_tasks
                    WHERE due_date < :today AND status NOT IN ('completed','cancelled')) AS overdue_tasks,
                (SELECT COUNT(*) FROM crm_leads
                    WHERE status NOT IN ('won','lost')) AS open_leads,
                (SELECT COUNT(*) FROM crm_leads
                    WHERE next_followup_date < :now_utc AND status NOT IN ('won','lost')) AS overdue_leads,
                (SELECT COUNT(*) FROM service_ticket
                    WHERE sub_status NOT IN ('closed')) AS open_tickets,
                (SELECT COUNT(*) FROM service_ticket
                    WHERE sub_status='closed' AND closed_date >= :today_midnight) AS closed_today
        """), {
            'today': today_date,
            'now_utc': datetime.utcnow(),
            'today_midnight': today_midnight_utc,
        }).fetchone()

        context = {
            'name': name,
            'date': today_str,
            'active_staff': str(stats[0] if stats else 0),
            'open_tasks': str(stats[1] if stats else 0),
            'overdue_tasks': str(stats[2] if stats else 0),
            'open_leads': str(stats[3] if stats else 0),
            'overdue_leads': str(stats[4] if stats else 0),
            'open_tickets': str(stats[5] if stats else 0),
            'closed_today': str(stats[6] if stats else 0),
            'portal_url': f"{portal_base_url}/staff/dashboard",
        }

        result = send_auto_whatsapp(
            db=db,
            event_key='staff_morning_leadership',
            phone=phone,
            context=context,
            staff_id=getattr(staff_employee, 'id', None),
        )
        logger.info("[WA-LEADERSHIP-MORNING] %s (%s): %s", name, phone,
                    "OK" if result.get("success") else result.get("reason", "FAIL"))
        return result

    except Exception as e:
        logger.error("[WA-LEADERSHIP-MORNING] Error for %s: %s", name, e)
        return {"success": False, "reason": str(e)}
