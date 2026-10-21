"""
WhatsApp Request Lifecycle Service — MyntOS
Automates instant WhatsApp notifications to the requester when a support request or application is:
- CLAIMED / ACCEPTED
- COMPLETED / PROCESSED / RESOLVED
- CANCELLED
- UPDATED / IN PROGRESS

Delivery Strategy:
1. Attempts delivery via Meta WhatsApp Cloud API using registered UTILITY templates.
2. If Meta Cloud API is unavailable, unapproved, or returns an error, automatically
   falls back to the Scanned WhatsApp Bot Gateway / local SIM queue.
"""

import os
import re
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.timezone import get_indian_time

logger = logging.getLogger(__name__)

# Registered Meta UTILITY Template Slugs
TEMPLATE_MAP = {
    "CLAIMED": {
        "meta_name": "mnr_request_claimed_v1",
        "slug": "request_claimed_notification",
        "text_template": "Dear {name}, your {request_code} has been accepted by {staff_name}. To reach your assigned support executive, please contact {phone} Ext: {ext} for immediate assistance."
    },
    "COMPLETED": {
        "meta_name": "mnr_request_completed_v1",
        "slug": "request_completed_notification",
        "text_template": "Dear {name}, your {request_code} has been completed by {staff_name}. For any further assistance, please contact {phone} Ext: {ext}. Thank you for reaching out."
    },
    "CANCELLED": {
        "meta_name": "mnr_request_cancelled_v1",
        "slug": "request_cancelled_notification",
        "text_template": "Dear {name}, your {request_code} has been cancelled. Reason: {notes}. For any queries, please contact {phone} Ext: {ext} for assistance."
    },
    "UPDATED": {
        "meta_name": "mnr_request_update_v1",
        "slug": "request_update_notification",
        "text_template": "Dear {name}, update on your {request_code}: {notes}. Executive {staff_name} is handling your request. Contact {phone} for queries."
    },
    "WAITING_FOR_DETAILS": {
        "meta_name": "mnr_request_waiting_details_v1",
        "slug": "request_waiting_details_notification",
        "text_template": "Dear {name}, we require additional details for your {request_code}: {notes}. Assigned executive: {staff_name} (Phone: {phone} Ext: {ext}). Once provided, tap to confirm: {action_link}"
    }
}


def normalize_phone_number(phone_raw: str) -> Optional[str]:
    """Normalize phone string into 10-digit Indian mobile number."""
    if not phone_raw:
        return None
    digits = re.sub(r'\D', '', str(phone_raw).strip())
    if digits.startswith('91') and len(digits) == 12:
        return digits[2:]
    if len(digits) == 10 and digits[0] in '6789':
        return digits
    if len(digits) == 11 and digits.startswith('0'):
        return digits[1:]
    if len(digits) >= 10:
        return digits[-10:]
    return None


def resolve_staff_contact_details(db: Session, staff_employee: Any, company_id: int = 1) -> Dict[str, str]:
    """Extract display name, contact phone, and active extension for staff member."""
    from app.services.whatsapp_auto_service import resolve_staff_extension

    staff_name = ""
    staff_phone = "+91 85858 52738"
    staff_ext = "101"

    if staff_employee:
        staff_name = (
            getattr(staff_employee, "full_name", "")
            or getattr(staff_employee, "username", "")
            or getattr(staff_employee, "name", "")
            or ""
        ).strip()
        phone_val = getattr(staff_employee, "phone", None)
        if phone_val and len(re.sub(r'\D', '', str(phone_val))) >= 10:
            clean_p = re.sub(r'\D', '', str(phone_val))[-10:]
            staff_phone = f"+91 {clean_p}"

        try:
            resolved_ext = resolve_staff_extension(db, staff_employee, company_id=company_id)
            if resolved_ext and str(resolved_ext).strip():
                staff_ext = str(resolved_ext).strip()
        except Exception as ext_err:
            logger.debug(f"[REQ-NOTIF] Staff extension lookup note: {ext_err}")

    if not staff_name:
        staff_name = "Support Executive"

    return {
        "staff_name": staff_name,
        "staff_phone": staff_phone,
        "staff_ext": staff_ext
    }


def send_request_lifecycle_whatsapp_notification(
    db: Session,
    recipient_phone: str,
    recipient_name: str,
    event_type: str,
    request_code: str,
    staff_employee: Optional[Any] = None,
    notes: Optional[str] = None,
    company_id: int = 1,
    job_id: Optional[str] = None,
    action_link: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends life-cycle notification to the requester via Meta Cloud API with fallback to Scanned Bot.
    """
    clean_phone_10 = normalize_phone_number(recipient_phone)
    if not clean_phone_10:
        logger.warning(f"[REQ-NOTIF] Invalid recipient phone '{recipient_phone}' — skipping notification")
        return {"success": False, "reason": "invalid_phone"}

    event_key = event_type.upper().strip()
    if event_key in ("CLAIM", "CLAIMED", "ACCEPTED", "ACKNOWLEDGE", "ACKNOWLEDGED"):
        norm_event = "CLAIMED"
    elif event_key in ("COMPLETED", "PROCESSED", "RESOLVED", "COMPLETE", "CLOSE", "CLOSED"):
        norm_event = "COMPLETED"
    elif event_key in ("CANCEL", "CANCELLED", "REJECTED"):
        norm_event = "CANCELLED"
    elif event_key in ("WAITING_FOR_DETAILS", "WAITING", "DETAILS_REQUIRED", "HOLD"):
        norm_event = "WAITING_FOR_DETAILS"
    else:
        norm_event = "UPDATED"

    cfg = TEMPLATE_MAP.get(norm_event, TEMPLATE_MAP["UPDATED"])
    staff_info = resolve_staff_contact_details(db, staff_employee, company_id=company_id)
    clean_name = (recipient_name or "Valued Member").strip()
    clean_notes = (notes or ("Cancelled as requested" if norm_event == "CANCELLED" else ("Additional details required" if norm_event == "WAITING_FOR_DETAILS" else "In progress"))).strip()
    clean_notes = re.sub(r'[\r\n]+', ' ', clean_notes)[:120]
    effective_link = action_link or f"https://www.myntreal.com/req/{request_code.split()[-1]}/details-given"

    # Format text for scanned/fallback
    rendered_text = cfg["text_template"].format(
        name=clean_name,
        request_code=request_code,
        staff_name=staff_info["staff_name"],
        phone=staff_info["staff_phone"],
        ext=staff_info["staff_ext"],
        notes=clean_notes,
        action_link=effective_link
    )

    # Build Meta Cloud API parameters
    meta_name = cfg["meta_name"]
    if norm_event in ("CLAIMED", "COMPLETED"):
        body_vars = [
            clean_name,
            request_code,
            staff_info["staff_name"],
            staff_info["staff_phone"],
            staff_info["staff_ext"]
        ]
    elif norm_event == "CANCELLED":
        body_vars = [
            clean_name,
            request_code,
            clean_notes,
            staff_info["staff_phone"],
            staff_info["staff_ext"]
        ]
    elif norm_event == "WAITING_FOR_DETAILS":
        body_vars = [
            clean_name,
            request_code,
            clean_notes,
            staff_info["staff_name"],
            staff_info["staff_phone"],
            staff_info["staff_ext"],
            effective_link
        ]
    else:  # UPDATED
        body_vars = [
            clean_name,
            request_code,
            clean_notes,
            staff_info["staff_name"],
            staff_info["staff_phone"]
        ]

    components = [
        {
            "type": "body",
            "parameters": [{"type": "text", "text": str(v)} for v in body_vars]
        }
    ]

    recipient_full = f"91{clean_phone_10}"
    target_jid = f"{recipient_full}@s.whatsapp.net"

    # Attempt 1: Meta WhatsApp Cloud API via WhatsAppCanonicalService
    try:
        from app.services.whatsapp_canonical_service import WhatsAppCanonicalService
        meta_res = WhatsAppCanonicalService.send_meta_template_message(
            db=db,
            phone=recipient_full,
            template_name=meta_name,
            language_code="en",
            components=components,
            user_name=clean_name,
            staff_id=getattr(staff_employee, "id", None),
            sent_by_name=staff_info["staff_name"],
            sender_type="staff" if staff_employee else "system",
            message_type=f"request_{norm_event.lower()}",
            company_id=company_id,
            raw_body_fallback=rendered_text
        )

        if meta_res.get("success") and not meta_res.get("fallback"):
            logger.info(f"[REQ-NOTIF] Successfully sent {norm_event} notification to {recipient_full} via Meta API (WAMID: {meta_res.get('wamid')})")
            return {"success": True, "channel": "meta_api", "wamid": meta_res.get("wamid")}
        elif meta_res.get("fallback") and meta_res.get("success"):
            logger.info(f"[REQ-NOTIF] Meta failed; fallback to scanned successful for {recipient_full}")
            return {"success": True, "channel": "scanned_fallback", "detail": meta_res}
    except Exception as meta_err:
        logger.warning(f"[REQ-NOTIF] Meta Cloud API invocation note: {meta_err}")

    # Attempt 2: Direct Scanned WhatsApp Bot Gateway / Queue Fallback
    try:
        from app.services.whatsapp_auto_service import dispatch_scanned_lead_fallback
        fb_res = dispatch_scanned_lead_fallback(
            db=db,
            phone=recipient_full,
            message=rendered_text,
            staff_id=getattr(staff_employee, "id", None),
            event_key=f"request_{norm_event.lower()}",
            reason=f"Meta template failover to scanned for {norm_event}"
        )
        if fb_res.get("success"):
            logger.info(f"[REQ-NOTIF] Scanned fallback dispatched to {recipient_full}")
            return {"success": True, "channel": "scanned_direct", "result": fb_res}
    except Exception as sc_err:
        logger.warning(f"[REQ-NOTIF] Scanned direct fallback error: {sc_err}")

    # Attempt 3: Guaranteed Enqueue to PostgreSQL whatsapp_bot_queue
    try:
        from app.models.whatsapp import MessageLog
        now_ist = get_indian_time()
        actual_job_id = job_id or f"qa_{norm_event.lower()}_requester_notif"
        q_res = db.execute(
            text("""
                INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, job_id)
                VALUES ('individual', :target_jid, :msg, 'pending', :now_ist, :job_id)
                RETURNING id
            """),
            {
                "target_jid": target_jid,
                "msg": rendered_text,
                "now_ist": now_ist,
                "job_id": actual_job_id
            }
        )
        queue_id = q_res.fetchone()[0]
        db.commit()
        logger.info(f"[REQ-NOTIF] Guaranteed enqueued to whatsapp_bot_queue (ID #{queue_id}) for {recipient_full}")
        return {"success": True, "channel": "scanned_queue", "queue_id": queue_id}
    except Exception as q_err:
        logger.error(f"[REQ-NOTIF] Queue enqueue error: {q_err}")
        return {"success": False, "error": str(q_err)}


def send_ticket_lifecycle_whatsapp_notification(
    db: Session,
    ticket: Any,
    event_type: str,
    staff_employee: Optional[Any] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience helper to send lifecycle WhatsApp notification for a ServiceTicket.
    Resolves recipient from partner_id, user_id, or billing snapshot.
    """
    if not ticket:
        return {"success": False, "reason": "no_ticket"}

    recipient_phone = None
    recipient_name = None

    # 1. Check partner
    if getattr(ticket, "partner_id", None):
        try:
            from app.models.official_partner import OfficialPartner
            p = db.query(OfficialPartner).filter(OfficialPartner.id == ticket.partner_id).first()
            if p:
                recipient_phone = p.phone or p.whatsapp_number
                recipient_name = p.partner_name or p.contact_person
        except Exception:
            pass

    # 2. Check user
    if not recipient_phone and getattr(ticket, "user_id", None):
        try:
            from app.models.user import User
            u = db.query(User).filter(User.id == ticket.user_id).first()
            if u:
                recipient_phone = getattr(u, "phone", None) or getattr(u, "mobile", None)
                recipient_name = getattr(u, "name", None) or getattr(u, "username", None)
        except Exception:
            pass

    # 3. Check billing customer snapshot
    if not recipient_phone and getattr(ticket, "billing", None):
        recipient_phone = getattr(ticket.billing, "billing_customer_phone", None)
        recipient_name = getattr(ticket.billing, "billing_customer_name", None)

    if not recipient_phone:
        logger.debug(f"[REQ-NOTIF] No recipient phone found for Ticket #{getattr(ticket, 'ticket_id', getattr(ticket, 'id', ''))}")
        return {"success": False, "reason": "no_recipient_phone"}

    req_code = f"Support Ticket {getattr(ticket, 'ticket_id', getattr(ticket, 'id', ''))}"
    cid = getattr(ticket, "company_id", 1) or 1

    return send_request_lifecycle_whatsapp_notification(
        db=db,
        recipient_phone=recipient_phone,
        recipient_name=recipient_name or "Valued Customer",
        event_type=event_type,
        request_code=req_code,
        staff_employee=staff_employee,
        notes=notes,
        company_id=cid,
        job_id="support_ticket_requester_notif"
    )


def send_details_received_notifications(
    db: Session,
    alert: Any,
    staff_employee: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Flashes instant notification to:
    1. The Staff WhatsApp Group (e.g. Mynt Sales New)
    2. The specific assigned staff member's direct WhatsApp
    when a member/customer confirms details have been submitted.
    """
    results = {"group": None, "staff": None}
    if not alert:
        return results

    now_ist = get_indian_time()
    type_label = "Member Application" if getattr(alert, "alert_type", "") == "APPLICATION" else "Support Request"
    req_code = getattr(alert, "alert_code", "")
    partner_name = getattr(alert, "partner_name", "Partner")
    partner_phone = getattr(alert, "partner_phone", "")

    staff_name = "Assigned Executive"
    staff_phone = None
    if not staff_employee and getattr(alert, "claimed_by_staff_id", None):
        try:
            from app.models.staff import StaffEmployee
            staff_employee = db.query(StaffEmployee).filter(StaffEmployee.id == alert.claimed_by_staff_id).first()
        except Exception:
            pass

    if staff_employee:
        staff_name = (
            getattr(staff_employee, "full_name", "")
            or getattr(staff_employee, "name", "")
            or getattr(staff_employee, "username", "")
            or "Assigned Executive"
        ).strip()
        staff_phone = getattr(staff_employee, "phone", None) or getattr(staff_employee, "mobile", None)

    # 1. Staff WhatsApp Group Broadcast
    group_msg = (
        f"🔔 *DETAILS RECEIVED: {type_label} {req_code}*\n\n"
        f"👤 *Partner:* {partner_name} ({partner_phone})\n"
        f"👨‍💼 *Assigned To:* {staff_name}\n"
        f"⏰ *Time:* {now_ist.strftime('%I:%M %p IST')}\n"
        f"▶️ *Clock Resumed:* Status updated to RUNNING / IN PROGRESS.\n\n"
        f"Please check your Live Desk to proceed with this request."
    )

    try:
        from app.services.whatsapp_group_alert_service import send_group_bot_message
        grp_res = send_group_bot_message(
            message_text=group_msg,
            group_name="Mynt Sales New",
            group_id="120363410784518818@g.us",
            job_id="qa_details_received_notif",
            trigger_type="quick_alert_details_received",
            db=db,
            force_queue=True
        )
        if grp_res.get("success"):
            results["group"] = True
            logger.info(f"[REQ-NOTIF] Group details-received notification enqueued successfully")
    except Exception as g_err:
        logger.warning(f"[REQ-NOTIF] Group details-received error: {g_err}")

    # 2. Direct WhatsApp Notification to Specific Assigned Staff Member
    if staff_phone:
        clean_staff_phone = normalize_phone_number(staff_phone)
        if clean_staff_phone:
            staff_jid = f"91{clean_staff_phone}@s.whatsapp.net"
            staff_direct_msg = (
                f"👋 *Hi {staff_name}!* Requested details have been received.\n\n"
                f"📋 *Request:* {type_label} *{req_code}*\n"
                f"👤 *Partner:* {partner_name} ({partner_phone})\n"
                f"▶️ The request has been resumed to *IN PROGRESS* in your Live Desk queue. Please review and continue processing."
            )
            try:
                db.execute(
                    text("""
                        INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, job_id)
                        VALUES ('individual', :target_jid, :msg, 'pending', :now_ist, 'qa_details_received_notif')
                    """),
                    {"target_jid": staff_jid, "msg": staff_direct_msg, "now_ist": now_ist}
                )
                db.commit()
                results["staff"] = True
                logger.info(f"[REQ-NOTIF] Staff direct details-received notification enqueued to {staff_jid}")
            except Exception as s_err:
                logger.warning(f"[REQ-NOTIF] Staff direct details-received error: {s_err}")

    return results

