"""
DC_WA_GROUP_ALERT_001 — WhatsApp Group Alert Dispatcher
Sends messages to Sales Team WhatsApp Group via Self-Hosted WhatsApp Web Bot (port 5002).
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.timezone import get_indian_time, IST

logger = logging.getLogger(__name__)

DEFAULT_INVITE_CODE = "LfX8mGootXa7SpwNIz7P5C"


def extract_invite_code(url_or_code: str) -> str:
    """Extract clean WhatsApp Group invite code from URL or raw string."""
    if not url_or_code:
        return ""
    code = str(url_or_code).strip()
    if 'chat.whatsapp.com/' in code:
        code = code.split('chat.whatsapp.com/')[-1].split('?')[0].split('#')[0].strip('/')
    return code


def send_group_bot_message(
    message_text: str,
    invite_code: str = DEFAULT_INVITE_CODE,
    group_name: Optional[str] = None,
    group_id: Optional[str] = None,
    job_id: Optional[str] = None,
    job_name: Optional[str] = None,
    trigger_type: Optional[str] = None,
    db: Optional[Session] = None,
    execution_id: Optional[str] = None,
    force_queue: bool = False
) -> Dict[str, Any]:
    """
    Sends message payload to WhatsApp Web Group Bot Gateway with IPv4/IPv6 & env-var fallback.
    If force_queue is True or if the bot HTTP gateway is unreachable and a database session is provided,
    falls back safely to enqueuing directly into PostgreSQL whatsapp_bot_queue.
    """
    clean_code = extract_invite_code(invite_code)

    # Fast-path directly into PostgreSQL queue if force_queue requested
    if force_queue and db is not None:
        try:
            from sqlalchemy import text
            import json
            target_jid = group_id or clean_code or invite_code or "120363410784518818@g.us"
            rp = {"job_id": job_id, "job_name": job_name, "trigger_type": trigger_type, "execution_id": execution_id}
            clean_rp = {k: v for k, v in rp.items() if v is not None}
            res = db.execute(text("""
                INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, result_payload, job_id, execution_id)
                VALUES ('group', :target_jid, :msg, 'pending', NOW(), CAST(:rp AS jsonb), :job_id, :execution_id)
                RETURNING id
            """), {
                "target_jid": target_jid,
                "msg": message_text,
                "rp": json.dumps(clean_rp) if clean_rp else None,
                "job_id": job_id,
                "execution_id": execution_id
            })
            db.commit()
            queue_id = res.fetchone()[0]
            logger.info(f"[WA-GROUP-ALERT] Force queued directly to whatsapp_bot_queue (ID #{queue_id})")
            return {"success": True, "queued": True, "queue_id": queue_id, "message": "Enqueued directly to PostgreSQL queue"}
        except Exception as db_err:
            db.rollback()
            logger.warning(f"[WA-GROUP-ALERT] DB force-queue note: {db_err}")
            return {"success": False, "error": str(db_err)}

    payload = {
        "message": message_text,
        "inviteCode": clean_code or invite_code
    }
    if group_name:
        payload["groupName"] = group_name
    if group_id:
        payload["groupId"] = group_id
    if job_id:
        payload["job_id"] = job_id
    if job_name:
        payload["job_name"] = job_name
    if trigger_type:
        payload["trigger_type"] = trigger_type
    if execution_id:
        payload["execution_id"] = execution_id

    env_url = os.getenv("WHATSAPP_BOT_URL") or os.getenv("WA_BOT_URL") or os.getenv("WA_GROUP_BOT_URL")
    urls = []
    if env_url:
        urls.append(env_url)
    urls.extend([
        "http://127.0.0.1:5002/api/send-group-message",
        "http://localhost:5002/api/send-group-message"
    ])

    last_exc = None
    for url in urls:
        try:
            resp = requests.post(url, json=payload, timeout=15)
            raw = resp.json()
            if resp.status_code == 200 and raw.get("success"):
                return {"success": True, "data": raw}
            else:
                logger.warning(f"Group Bot API response from {url}: {resp.status_code} - {resp.text}")
                return {"success": False, "error": raw.get("error") or resp.text}
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(f"Could not connect to WhatsApp Group Bot Gateway: {last_exc}")

    # Fallback directly to PostgreSQL queue if DB session available
    if db is not None:
        try:
            from sqlalchemy import text
            import json
            target_jid = group_id or clean_code or invite_code or "120363410784518818@g.us"
            rp = {"job_id": job_id, "job_name": job_name, "trigger_type": trigger_type, "execution_id": execution_id}
            clean_rp = {k: v for k, v in rp.items() if v is not None}
            res = db.execute(text("""
                INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, result_payload, job_id, execution_id)
                VALUES ('group', :target_jid, :msg, 'pending', NOW(), CAST(:rp AS jsonb), :job_id, :execution_id)
                RETURNING id
            """), {
                "target_jid": target_jid,
                "msg": message_text,
                "rp": json.dumps(clean_rp) if clean_rp else None,
                "job_id": job_id,
                "execution_id": execution_id
            })
            db.commit()
            queue_id = res.fetchone()[0]
            logger.info(f"[WA-GROUP-ALERT] Gateway offline; safely enqueued directly to whatsapp_bot_queue (ID #{queue_id})")
            return {"success": True, "queued": True, "queue_id": queue_id, "message": "Enqueued directly to PostgreSQL queue"}
        except Exception as db_err:
            db.rollback()
            logger.warning(f"[WA-GROUP-ALERT] DB fallback enqueue note: {db_err}")

    return {"success": False, "error": f"WhatsApp Group Bot service is currently offline on port 5002 ({last_exc}). Please start the WhatsApp Bot daemon on the server."}


def send_instant_new_lead_group_alert(db: Session, lead_id: int, force_queue: bool = False) -> Dict[str, Any]:
    """
    Formats and dispatches instant New Lead notification into Sales WhatsApp Group.
    DC Protocol Apr 2026: Uses Meta lead generation date/time (IST) and captures all form fields (Electricity Bill, Property Type, Pincode, etc.)
    DC-SELF-LEAD-001: Staff Self Leads are private workflows and MUST NOT trigger shared Sales Group notifications.
    """
    import json
    import pytz
    from app.models.crm import CRMLead, SELF_LEAD_SOURCE_NAME

    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        return {"success": False, "reason": "lead_not_found"}

    # DC-SELF-LEAD-001 / DC-STAFF-LEAD-001: Suppress group alert for staff-related / private / manually added staff leads
    lead_source = (getattr(lead, 'source', '') or '').strip()
    created_by_type = (getattr(lead, 'created_by_type', '') or '').strip().lower()
    source_ref_type = (getattr(lead, 'source_ref_type', '') or '').strip().lower()
    if (
        created_by_type == 'staff'
        or source_ref_type in ('staff', 'self', 'mn_staff')
        or lead_source.lower() == 'self lead'
        or lead_source == SELF_LEAD_SOURCE_NAME
    ):
        logger.info(f"[SCOUT-ALERT] Suppressing Sales Group notification for Staff-created / Private Lead #{lead.id} (Internal Staff Lead)")
        return {"success": True, "skipped": True, "reason": "staff_lead_suppressed"}

    lead_name = (getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Valued Prospect').strip()
    phone = getattr(lead, 'phone', 'N/A') or 'N/A'
    city = getattr(lead, 'city', '') or getattr(lead, 'location', '') or 'Not Specified'
    pincode = getattr(lead, 'pincode', '') or ''
    source = getattr(lead, 'source', '') or 'Direct Intake'
    interest = getattr(lead, 'product_interest', '') or getattr(lead, 'requirement', '') or 'Solar Rooftop (PM Surya Ghar)'
    description = getattr(lead, 'description', '') or ''

    # Parse source_details for Meta created_time and raw_fields
    source_details_raw = getattr(lead, 'source_details', '') or ''
    sd = {}
    if isinstance(source_details_raw, str) and source_details_raw.startswith('{'):
        try:
            sd = json.loads(source_details_raw)
        except Exception:
            pass
    elif isinstance(source_details_raw, dict):
        sd = source_details_raw

    # Meta Lead Generation Time (IST)
    meta_created_str = sd.get('created_time')
    time_str = None
    if meta_created_str:
        try:
            dt_utc = datetime.datetime.fromisoformat(meta_created_str.replace('+0000', '+00:00'))
            indian_tz = pytz.timezone('Asia/Kolkata')
            dt_ist = dt_utc.astimezone(indian_tz)
            time_str = dt_ist.strftime("%d %b %Y, %I:%M %p IST")
        except Exception:
            pass

    if not time_str:
        created_at = getattr(lead, 'created_at', None)
        if created_at:
            time_str = created_at.strftime("%d %b %Y, %I:%M %p IST")
        else:
            ist_now = get_indian_time()
            time_str = ist_now.strftime("%d %b %Y, %I:%M %p IST")

    # Extract form questions & answers
    raw_fields = sd.get('raw_fields') or {}
    electricity_bill = (
        raw_fields.get('what_is_your_monthly_electricity_bill?') or
        raw_fields.get('electricity_bill') or
        raw_fields.get('monthly_electricity_bill') or
        raw_fields.get('bill_amount') or None
    )
    property_type = (
        raw_fields.get('type_of_property') or
        raw_fields.get('property_type') or None
    )
    if not pincode:
        pincode = raw_fields.get('post_code') or raw_fields.get('zip_code') or raw_fields.get('pincode') or ''

    # Source page name fallback
    page_name = sd.get('page_name') or ''
    if page_name and 'Facebook' not in source:
        source = f"Facebook Lead Ads ({page_name})"

    # Extract category / product interest
    category_name = None
    if getattr(lead, 'category_id', None):
        try:
            from sqlalchemy import text
            c_row = db.execute(text("SELECT name FROM signup_categories WHERE id = :cid"), {"cid": lead.category_id}).fetchone()
            if c_row and c_row[0]:
                category_name = str(c_row[0]).strip()
        except Exception as _cat_sql_err:
            logger.warning(f"[WA-GROUP-ALERT] Category SQL lookup note: {_cat_sql_err}")
    if not category_name and getattr(lead, 'category_id', None):
        try:
            from app.models.signup_category import SignupCategory
            cat = db.query(SignupCategory).get(lead.category_id)
            if cat:
                category_name = cat.name
        except Exception:
            pass
    if not category_name:
        category_name = (
            getattr(lead, 'looking_for', '') or 
            getattr(lead, 'requirements', '') or 
            getattr(lead, 'product_interest', '') or 
            sd.get('ivr_option') or 
            sd.get('category') or 
            None
        )

    # Comments / Notes
    recent_comments = (getattr(lead, 'recent_comments', '') or '').strip()

    # MyOperator Missed By / Dialed Operator lookup
    missed_by = sd.get('missed_by') or sd.get('operator_name') or sd.get('handled_by') or None
    if not missed_by and phone and phone != 'N/A':
        try:
            from app.models.operator_call import OperatorCall
            clean_p = ''.join(c for c in str(phone) if c.isdigit())[-10:]
            if clean_p:
                op_call = db.query(OperatorCall).filter(
                    (OperatorCall.crm_lead_id == lead.id) | 
                    (OperatorCall.caller_number.endswith(clean_p))
                ).order_by(OperatorCall.id.desc()).first()
                if op_call:
                    missed_by = op_call.handled_by or op_call.operator_name
        except Exception:
            pass

    # Staff assignment
    assigned_name = "Unassigned / Telecaller Team"
    if getattr(lead, 'assigned_to_emp_id', None):
        try:
            from app.models.staff import StaffUser
            emp = db.query(StaffUser).get(lead.assigned_to_emp_id)
            if emp:
                assigned_name = getattr(emp, 'full_name', '') or getattr(emp, 'username', '')
        except Exception:
            pass

    # Company name resolution
    company_name = None
    if getattr(lead, 'company_id', None):
        if lead.company_id == 2:
            company_name = "Zynova Mobility (Zynovia)"
        elif lead.company_id == 4:
            company_name = "MyntReal"
        elif lead.company_id == 1:
            company_name = "Real Dreams"

    # Phone masking & softphone secure call link
    clean_digits = ''.join(c for c in str(phone) if c.isdigit())[-10:]
    if len(clean_digits) == 10:
        masked_phone = f"+91 {clean_digits[:5]} *****"
    else:
        masked_phone = phone

    softphone_call_link = f"https://www.myntreal.com/staff/softphone?lead_id={lead.id}&auto_dial=1"

    # Build structured alert text
    msg_lines = [
        "🚨 *NEW LEAD RECEIVED!* 🚨\n",
        f"👤 *Customer Name*: {lead_name}",
        f"📱 *Phone*: {masked_phone} 🔒 _(Masked for Security)_",
        f"📍 *Location*: {city}" + (f" (PIN: {pincode})" if pincode else ""),
    ]

    if company_name:
        msg_lines.append(f"🏢 *Company*: {company_name}")
    if category_name:
        msg_lines.append(f"🎯 *Service / Category*: {category_name}")
    if electricity_bill:
        msg_lines.append(f"⚡ *Monthly Bill*: {electricity_bill}")
    if property_type:
        msg_lines.append(f"🏠 *Property Type*: {property_type}")

    msg_lines.append(f"🏷️ *Source*: {source}")
    if missed_by:
        msg_lines.append(f"📞 *Missed By / Operator*: {missed_by}")
    msg_lines.append(f"⏰ *Lead Generated*: {time_str}")

    if recent_comments:
        msg_lines.append(f"\n💬 *Comments / Notes*: {recent_comments}")

    # Build Q&A summary for basic other details
    qa_parts = []
    if electricity_bill: qa_parts.append(f"• Monthly Electricity Bill: {electricity_bill}")
    if property_type:    qa_parts.append(f"• Property Type: {property_type}")
    if pincode:          qa_parts.append(f"• Pincode: {pincode}")

    _known_keys = {
        'full_name', 'name', 'first_name', 'last_name', 'email', 'phone_number', 'phone',
        'city', 'location', 'state', 'post_code', 'zip_code', 'pincode', 'phone_number_verified',
        'what_is_your_monthly_electricity_bill?', 'electricity_bill', 'monthly_electricity_bill', 'bill_amount',
        'type_of_property', 'property_type',
        # Technical ad/campaign keys omitted per user instruction
        'ad_id', 'adset_id', 'campaign_id', 'form_id', 'page_id', 'page_segment', 'created_time', 'is_organic', 'platform', 'lead_id'
    }
    for k, v in raw_fields.items():
        if k not in _known_keys and v:
            lbl = k.replace('_', ' ').replace('-', ' ').title()
            qa_parts.append(f"• {lbl}: {v}")

    if qa_parts:
        msg_lines.append("\n📋 *Captured Form Details*:")
        msg_lines.extend(qa_parts)

    msg_lines.append(f"\n👉 *Assigned Staff*: {assigned_name}")
    msg_lines.append(f"📞 *Direct Softphone Call*: {softphone_call_link}")
    msg_lines.append(f"🔗 *View Lead in CRM*: https://www.myntreal.com/staff/leads")

    message_text = "\n".join(msg_lines)
    return send_group_bot_message(
        message_text,
        invite_code="LfX8mGootXa7SpwNIz7P5C",
        group_name="Mynt Sales New",
        group_id="120363410784518818@g.us",
        db=db,
        force_queue=force_queue
    )
