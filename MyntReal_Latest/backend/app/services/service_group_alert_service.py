"""
DC_SERVICE_GROUP_ALERT_001 — Service WhatsApp Group Notification Service
Target Group Invite Code: EyuAwaVoF6E6nQqC0QfiBe
Manages:
1. Instant New Service Ticket Alerts.
2. Daily 7:30 PM Service SLA & Ticket Summary Report.
"""

import logging
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

import os
import logging
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

SERVICE_GROUP_INVITE_CODE = "EyuAwaVoF6E6nQqC0QfiBe"


def send_service_group_bot_message(message_text: str) -> Dict[str, Any]:
    """
    Dispatches message payload to Service WhatsApp Group via bot gateway with IPv4/IPv6 & env-var fallback.
    """
    payload = {
        "message": message_text,
        "inviteCode": SERVICE_GROUP_INVITE_CODE
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
                logger.warning(f"Service Group Bot API response from {url}: {resp.status_code} - {resp.text}")
                return {"success": False, "error": raw.get("error") or resp.text}
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(f"Could not connect to Service Group Bot Gateway: {last_exc}")
    return {"success": False, "error": f"WhatsApp Group Bot service is currently offline on port 5002 ({last_exc}). Please start the WhatsApp Bot daemon on the server."}


def send_instant_service_ticket_alert(db: Session, ticket_db_id: int) -> Dict[str, Any]:
    """
    Dispatches instant notification when a new service ticket is created.
    """
    from app.models.ticket import ServiceTicket
    from app.models.user import User

    ticket = db.query(ServiceTicket).get(ticket_db_id)
    if not ticket:
        return {"success": False, "reason": "ticket_not_found"}

    cust_name = "Valued Customer"
    cust_phone = "N/A"
    if ticket.user_id:
        cust = db.query(User).filter(User.id == ticket.user_id).first()
        if cust:
            cust_name = getattr(cust, 'name', '') or getattr(cust, 'full_name', '') or cust_name
            cust_phone = getattr(cust, 'phone', '') or getattr(cust, 'mobile_number', '') or cust_phone

    assigned_tech = "Unassigned / Service Pool"
    if ticket.assigned_to:
        tech = db.query(User).filter(User.id == ticket.assigned_to).first()
        if tech:
            assigned_tech = getattr(tech, 'name', '') or getattr(tech, 'full_name', '') or assigned_tech

    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    time_str = ist_now.strftime("%I:%M %p")

    msg = (
        f"🛠️ *NEW SERVICE TICKET RAISED!* 🛠️\n\n"
        f"🎫 *Ticket ID*: #{ticket.ticket_id}\n"
        f"👤 *Customer*: {cust_name} ({cust_phone})\n"
        f"⚡ *Category*: {ticket.issue_category or 'General Solar/EV Service'}\n"
        f"📝 *Issue*: {(ticket.issue_description or 'No description')[:120]}\n"
        f"🔥 *Priority*: {ticket.priority or 'Medium'}\n"
        f"⏰ *Raised At*: Today at {time_str} IST\n\n"
        f"👉 *Assigned Technician*: {assigned_tech}\n"
        f"🔗 *Manage Ticket*: https://myntreal.com/staff/service-tickets"
    )

    return send_service_group_bot_message(msg)


def send_daily_service_summary_report(db: Session) -> Dict[str, Any]:
    """
    Generates and posts daily 7:30 PM service ticket summary to Service Group.
    """
    from app.models.ticket import ServiceTicket

    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    start_of_today_utc = (ist_now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=5, minutes=30))

    new_today = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.created_date >= start_of_today_utc
    ).scalar() or 0

    resolved_today = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.resolved_date >= start_of_today_utc
    ).scalar() or 0

    open_total = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.status.in_(['Open', 'In Progress', 'Diagnosing', 'Procuring'])
    ).scalar() or 0

    msg = (
        f"📊 *DAILY SERVICE & SLA SUMMARY REPORT* 📊\n"
        f"📅 *Date*: {ist_now.strftime('%d %B %Y')}\n\n"
        f"🛠️ *New Tickets Raised Today*: {new_today}\n"
        f"✅ *Tickets Resolved Today*: {resolved_today}\n"
        f"⏳ *Active Open Tickets*: {open_total}\n\n"
        f"Great dedication today team! Thank you for delivering excellent customer support! 🌟"
    )

    return send_service_group_bot_message(msg)
