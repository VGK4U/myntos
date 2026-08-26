"""
DC_WA_GROUP_ALERT_001 — WhatsApp Group Alert Dispatcher
Sends messages to Sales Team WhatsApp Group via Self-Hosted WhatsApp Web Bot (port 5002).
"""

import logging
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

import os
import logging
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

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
    group_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends message payload to WhatsApp Web Group Bot Gateway with IPv4/IPv6 & env-var fallback.
    """
    clean_code = extract_invite_code(invite_code)
    payload = {
        "message": message_text,
        "inviteCode": clean_code or invite_code
    }
    if group_name:
        payload["groupName"] = group_name
    if group_id:
        payload["groupId"] = group_id
    
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
            resp = requests.post(url, json=payload, timeout=8)
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
    return {"success": False, "error": f"WhatsApp Group Bot service is currently offline on port 5002 ({last_exc}). Please start the WhatsApp Bot daemon on the server."}


def send_instant_new_lead_group_alert(db: Session, lead_id: int) -> Dict[str, Any]:
    """
    Formats and dispatches instant New Lead notification into Sales WhatsApp Group.
    DC Protocol Apr 2026: Uses Meta lead generation date/time (IST) and captures all form fields (Electricity Bill, Property Type, Pincode, etc.)
    """
    import json
    import pytz
    from app.models.crm import CRMLead

    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        return {"success": False, "reason": "lead_not_found"}

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
            ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
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
            from app.models.crm import CRMCategory
            cat = db.query(CRMCategory).get(lead.category_id)
            if cat:
                category_name = cat.name
        except Exception:
            pass
    if not category_name:
        category_name = getattr(lead, 'looking_for', '') or getattr(lead, 'requirement', '') or sd.get('ivr_option') or sd.get('category') or None

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

    # Build structured alert text
    msg_lines = [
        "🚨 *NEW LEAD RECEIVED!* 🚨\n",
        f"👤 *Customer Name*: {lead_name}",
        f"📱 *Phone*: {phone}",
        f"📍 *Location*: {city}" + (f" (PIN: {pincode})" if pincode else ""),
    ]

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

    # Build Q&A summary
    qa_parts = []
    if electricity_bill: qa_parts.append(f"• Monthly Electricity Bill: {electricity_bill}")
    if property_type:    qa_parts.append(f"• Property Type: {property_type}")
    if pincode:          qa_parts.append(f"• Pincode: {pincode}")

    _known_keys = {
        'full_name', 'name', 'first_name', 'last_name', 'email', 'phone_number', 'phone',
        'city', 'location', 'state', 'post_code', 'zip_code', 'pincode', 'phone_number_verified',
        'what_is_your_monthly_electricity_bill?', 'electricity_bill', 'monthly_electricity_bill', 'bill_amount',
        'type_of_property', 'property_type'
    }
    for k, v in raw_fields.items():
        if k not in _known_keys and v:
            lbl = k.replace('_', ' ').replace('-', ' ').title()
            qa_parts.append(f"• {lbl}: {v}")

    if qa_parts:
        msg_lines.append("\n📋 *Captured Form Details*:")
        msg_lines.extend(qa_parts)

    msg_lines.append(f"\n👉 *Assigned Staff*: {assigned_name}")
    msg_lines.append("🔗 *CRM Link*: https://myntreal.com/staff/leads")

    message_text = "\n".join(msg_lines)
    return send_group_bot_message(message_text, group_name="Mynt sales new")
