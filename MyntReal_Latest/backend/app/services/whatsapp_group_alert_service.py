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


def send_group_bot_message(message_text: str, invite_code: str = DEFAULT_INVITE_CODE) -> Dict[str, Any]:
    """
    Sends message payload to WhatsApp Web Group Bot Gateway with IPv4/IPv6 & env-var fallback.
    """
    clean_code = extract_invite_code(invite_code)
    payload = {
        "message": message_text,
        "inviteCode": clean_code or invite_code
    }
    
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
    """
    from app.models.crm import CRMLead

    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        return {"success": False, "reason": "lead_not_found"}

    lead_name = (getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Valued Prospect').strip()
    phone = getattr(lead, 'phone', 'N/A') or 'N/A'
    city = getattr(lead, 'city', '') or getattr(lead, 'location', '') or 'Not Specified'
    source = getattr(lead, 'source', '') or 'Direct Intake'
    interest = getattr(lead, 'product_interest', '') or getattr(lead, 'requirement', '') or 'Solar Rooftop (PM Surya Ghar)'
    
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

    # Time formatting in IST (+5:30)
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    time_str = ist_now.strftime("%I:%M %p")

    message_text = (
        "🚨 *NEW LEAD RECEIVED!* 🚨\n\n"
        f"👤 *Customer Name*: {lead_name}\n"
        f"📱 *Phone*: {phone}\n"
        f"📍 *Location*: {city}\n"
        f"⚡ *Interest*: {interest}\n"
        f"🏷️ *Source*: {source}\n"
        f"⏰ *Time*: Today at {time_str} IST\n\n"
        f"👉 *Assigned Staff*: {assigned_name}\n"
        f"🔗 *CRM Link*: https://myntreal.com/staff/leads"
    )

    return send_group_bot_message(message_text)
