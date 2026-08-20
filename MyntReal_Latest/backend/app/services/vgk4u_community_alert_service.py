"""
DC_VGK4U_COMMUNITY_001 — VGK4U Channel & Elite Group Notification Service
Targets:
1. VGK4U WhatsApp Channel: https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m
2. VGK4U Elite Members Group
Features:
- Daily 8 AM Random Inspiring Morning Wishes.
- Partner Lead Addition Congratulatory Alerts.
- Partner Payout / Commission Disbursal Congratulatory Alerts.
"""

import logging
import random
import requests
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ELITE_GROUP_INVITE_CODE = "HNQQoKXFfCm5PQngGdrlcY"  # VGK4U Elite Community Group
VGK4U_CHANNEL_INVITE_CODE = "0029Vb7Vb5f9cDDXf3zWtf0m"  # VGK4U Official WhatsApp Channel

MORNING_QUOTES = [
    "🌅 *శుభోదయం / Good Morning VGK4U Family!* ☀️\n\n_\"విజయం అనేది ప్రతిరోజూ మనం చేసే చిన్న ప్రయత్నాల కలయిక!\"_\n\nTeam *VGK4U & MyntReal* wishes all our Elite Members and Partners a high-energy, successful, and profitable day ahead! 🚀⚡",
    "🌅 *శుభోదయం / Good Morning Champions!* ☀️\n\n_\"మీ ఆలోచనలే మీ గమ్యాన్ని నిర్దేశిస్తాయి. ఈ ఉదయం కొత్త లక్ష్యాలతో ప్రారంభించండి!\"_\n\nMay your day be filled with positive energy, new lead conversions, and prosperity! Best wishes from *VGK4U*. 💡🌿",
    "🌅 *శుభోదయం / Good Morning VGK4U Leaders!* ☀️\n\n_\"పరిశుభ్రమైన సోలార్ శక్తితో మన సమాజానికి వెలుగును ఇద్దాం!\"_\n\nLet us lead the solar energy revolution together. Wishing you all maximum payouts & success today! ☀️🏆",
    "🌅 *శుభోదయం / Good Morning Sunshine!* ☀️\n\n_\"నేడు సాధించే ప్రతి విజయం మీ భవిష్యత్తుకు గొప్ప పునాది!\"_\n\nTeam *VGK4U* is proud of our strong community of partners. Let's make today extraordinary! 🚀💵"
]


def send_vgk4u_group_bot_message(message_text: str, invite_code: str = ELITE_GROUP_INVITE_CODE) -> Dict[str, Any]:
    """
    Dispatches message payload to VGK4U Elite WhatsApp Group via bot gateway with IPv4/IPv6 & env-var fallback.
    """
    payload = {
        "message": message_text,
        "inviteCode": invite_code
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
                logger.warning(f"VGK4U Group Bot API response from {url}: {resp.status_code} - {resp.text}")
                return {"success": False, "error": raw.get("error") or resp.text}
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(f"Could not connect to VGK4U Group Bot Gateway: {last_exc}")
    return {"success": False, "error": str(last_exc)}


def dispatch_daily_vgk4u_morning_wish(db: Session, invite_code: str = ELITE_GROUP_INVITE_CODE) -> Dict[str, Any]:
    """
    Dispatches daily 8:00 AM random inspiring morning wish to VGK4U Elite Group.
    """
    quote = random.choice(MORNING_QUOTES)
    logger.info("🌅 Dispatching daily VGK4U 8 AM morning wish...")
    return send_vgk4u_group_bot_message(quote, invite_code=invite_code)


def send_partner_lead_added_congratulations(
    db: Session,
    partner_name: str,
    lead_name: str,
    city: Optional[str] = None
) -> Dict[str, Any]:
    """
    Posts congratulatory alert in VGK4U Elite group when a partner adds a new lead.
    """
    city_str = f" ({city})" if city else ""
    msg = (
        f"🎉 *CONGRATULATIONS & KUDOS!* 👏\n\n"
        f"Huge shoutout to Elite Partner *{partner_name}* for registering a NEW Solar Rooftop Lead: *{lead_name}*{city_str}! 🌟\n\n"
        f"Thank you for driving green energy growth with VGK4U! Keep shining & earning! 🚀⚡"
    )
    return send_vgk4u_group_bot_message(msg)


def send_partner_payout_disbursed_congratulations(
    db: Session,
    partner_name: str,
    amount: float,
    payout_type: str = "Solar Commission Payout"
) -> Dict[str, Any]:
    """
    Posts congratulatory alert in VGK4U Elite group when a payout/commission is disbursed to a partner.
    """
    formatted_amount = f"₹{amount:,.2f}"
    msg = (
        f"💰 *PAYMENT DISBURSED CELEBRATION!* 🎊\n\n"
        f"Congratulations to Partner *{partner_name}* on receiving a payout of *{formatted_amount}* for *{payout_type}*! 💵✨\n\n"
        f"Your hard work & leadership are truly inspiring! Together towards greater success with VGK4U! 🏆🚀"
    )
    return send_vgk4u_group_bot_message(msg)
