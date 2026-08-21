"""
DC_WA_GROUP_ALERT_001 — WhatsApp Group Alert Dispatcher
Sends messages to Sales Team WhatsApp Group via Self-Hosted WhatsApp Web Bot (port 5002).
"""

import logging
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BOT_API_URL = "http://localhost:5002/api/send-group-message"
DEFAULT_INVITE_CODE = "LfX8mGootXa7SpwNIz7P5C"


def send_group_bot_message(message_text: str, invite_code: str = DEFAULT_INVITE_CODE) -> Dict[str, Any]:
    """
    Sends message payload to local WhatsApp Web Group Bot Gateway (port 5002).
    """
    try:
        payload = {
            "message": message_text,
            "inviteCode": invite_code
        }
        resp = requests.post(BOT_API_URL, json=payload, timeout=8)
        raw = resp.json()
        if resp.status_code == 200 and raw.get("success"):
            return {"success": True, "data": raw}
        else:
            logger.warning(f"Group Bot API response: {resp.status_code} - {resp.text}")
            return {"success": False, "error": raw.get("error") or resp.text}
    except requests.exceptions.ConnectionError:
        logger.warning("Could not connect to WhatsApp Group Bot Gateway — Service offline on port 5002")
        return {"success": False, "error": "WhatsApp Group Bot service is currently offline on port 5002. Please start the WhatsApp Bot daemon on the server."}
    except Exception as exc:
        logger.warning(f"Could not connect to WhatsApp Group Bot Gateway (port 5002): {exc}")
        return {"success": False, "error": str(exc)}


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
