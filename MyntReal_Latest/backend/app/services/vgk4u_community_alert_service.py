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


import os

POSTER_IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "poster-celebration-template.jpg"))

def extract_invite_code(url_or_code: str) -> str:
    """Extract clean WhatsApp Group or Channel invite code from URL or raw string."""
    if not url_or_code:
        return ""
    code = str(url_or_code).strip()
    if 'whatsapp.com/channel/' in code:
        code = code.split('whatsapp.com/channel/')[1].split('?')[0].split('#')[0].strip('/')
    elif 'chat.whatsapp.com/' in code:
        code = code.split('chat.whatsapp.com/')[1].split('?')[0].split('#')[0].strip('/')
    return code


def get_dynamic_time_wish_quote() -> str:
    """Generates a dynamic greeting quote matching the current IST time of day (Morning/Afternoon/Evening)."""
    now_utc = datetime.datetime.utcnow()
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    hour = now_ist.hour

    if 5 <= hour < 12:
        greeting_head = "🌅 *శుభోదయం / Good Morning VGK4U Family!* ☀️"
        sub_text = "May your day be filled with positive energy, new lead conversions, and prosperity!"
    elif 12 <= hour < 17:
        greeting_head = "☀️ *శుభ మధ్యాహ్నం / Good Afternoon VGK4U Family!* 🌤️"
        sub_text = "Keep up the great momentum! Wishing all our Elite Partners maximum success and progress this afternoon!"
    elif 17 <= hour < 22:
        greeting_head = "🌆 *శుభ సాయంత్రం / Good Evening VGK4U Family!* 🌇"
        sub_text = "Great work today! Team VGK4U celebrates your hard work and achievements today!"
    else:
        greeting_head = "🌟 *శుభ రాత్రి / Good Night / Evening Wishes VGK4U Family!* ✨"
        sub_text = "Rest well and recharge for another inspiring and profitable day tomorrow!"

    quotes_pool = [
        f"{greeting_head}\n\n_\"విజయం అనేది ప్రతిరోజూ మనం చేసే చిన్న ప్రయత్నాల కలయిక!\"_\n\n{sub_text} Best wishes from *VGK4U & MyntReal*. 🚀⚡",
        f"{greeting_head}\n\n_\"మీ ఆలోచనలే మీ గమ్యాన్ని నిర్దేశిస్తాయి.\"_\n\n{sub_text} Best wishes from *VGK4U*. 💡🌿",
        f"{greeting_head}\n\n_\"పరిశుభ్రమైన సోలార్ శక్తితో మన సమాజానికి వెలుగును ఇద్దాం!\"_\n\n{sub_text} Let us lead the solar energy revolution together! ☀️🏆",
        f"{greeting_head}\n\n_\"సాధించే ప్రతి విజయం మీ భవిష్యత్తుకు గొప్ప పునాది!\"_\n\n{sub_text} Team *VGK4U* is proud of our strong community of partners! 🚀💵"
    ]
    return random.choice(quotes_pool)


def send_vgk4u_group_bot_message(
    message_text: str,
    invite_code: str = ELITE_GROUP_INVITE_CODE,
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    clean_code = extract_invite_code(invite_code)
    img_to_use = image_path

    payload = {
        "message": message_text,
        "inviteCode": clean_code or invite_code
    }
    if img_to_use:
        payload["imagePath"] = img_to_use
    
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
            resp = requests.post(url, json=payload, timeout=12)
            raw = resp.json()
            if resp.status_code == 200 and raw.get("success"):
                return {"success": True, "data": raw}
            else:
                logger.warning(f"VGK4U Group Bot API response from {url}: {resp.status_code} - {resp.text}")
                return {"success": False, "error": raw.get("error") or resp.text, "data": raw}
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(f"Could not connect to VGK4U Group Bot Gateway: {last_exc}")
    return {"success": False, "error": f"WhatsApp Group Bot service offline on port 5002 ({last_exc})."}


def dispatch_daily_vgk4u_morning_wish(db: Session, invite_code: str = ELITE_GROUP_INVITE_CODE) -> Dict[str, Any]:
    """
    Dispatches dynamic time-of-day wish (Morning / Afternoon / Evening) to all configured VGK4U targets.
    """
    from app.api.v1.endpoints.whatsapp import _load_targets_from_db
    quote = get_dynamic_time_wish_quote()
    logger.info("🌅 Dispatching dynamic VGK4U time-of-day wish...")

    active_targets = _load_targets_from_db(db)
    target_groups = active_targets.get("vgk4u_morning_wish", [])
    if not target_groups:
        return send_vgk4u_group_bot_message(quote, invite_code=invite_code, image_path=None)

    results = []
    success_count = 0
    failed_count = 0

    for tg in target_groups:
        ident = tg.get("identifier", "").strip()
        if not ident:
            continue
        clean_code = extract_invite_code(ident)
        if not clean_code:
            continue
        res = send_vgk4u_group_bot_message(quote, invite_code=clean_code)
        results.append(res)
        if res.get("success"):
            success_count += 1
        else:
            failed_count += 1

    overall_success = success_count > 0 and failed_count == 0

    if success_count > 0:
        try:
            from app.models.whatsapp import MessageLog
            import uuid
            log_entry = MessageLog(
                message_sid=f"vgk4u_{uuid.uuid4().hex[:12]}",
                mobile_number="GROUP:VGK4U",
                message_type="vgk4u_wish",
                message_body=quote[:500],
                initial_status="sent",
                current_status="sent" if overall_success else "partial_failed",
                sent_at=datetime.datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_e:
            logger.warning("[VGK4U-WISH] Failed to write MessageLog: %s", log_e)

    return {
        "success": overall_success,
        "dispatched_groups": success_count,
        "failed_groups": failed_count,
        "results": results
    }


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
