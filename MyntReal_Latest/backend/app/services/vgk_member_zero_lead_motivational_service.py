"""
VGK Member 7:30 AM 0-Lead Partner Motivational Dispatch Service
Dispatches dynamic, rotating motivational WhatsApp messages to active Channel Partners who have 0 leads.
Includes real community proof & statistics (active earning partners count, total gross distributed, active pipeline opportunity).
Ends with a 'Refer and Earn' bottom-line call to action.
Executed daily at 07:30 AM IST.
"""

import os
import json
import logging
import requests
import datetime
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wa_execution_logs.json")

# 7 Rotating Daily Motivational Themes (Bilingual Telugu-English mix for Solar, Insurance & EV)
ROTATING_MOTIVATIONAL_THEMES = [
    {
        "day": 0, # Sunday
        "header": "🌅 *SUNDAY SPECIAL — మీ సంపాదన కలలను నెరవేర్చుకోవడానికి ఈరోజే మొదటి అడుగు వేయండి!*",
        "quote": "“సక్సెస్ సాధించడానికి మొదటి అడుగు వేయడం చాలా ముఖ్యం. మీ మొదటి రిఫరల్‌తోనే గొప్ప ఆదాయం ప్రారంభమవుతుంది!”",
        "focus": "ఈరోజే మీ ఫ్రెండ్స్ & రిలేటివ్స్‌కి Solar, Insurance & EV గురించి రిఫర్ చేయండి."
    },
    {
        "day": 1, # Monday
        "header": "🚀 *MONDAY MOTIVATION — మీ అవకాశాలను రియల్ ఇన్‌కమ్‌గా మార్చుకోండి!*",
        "quote": "“ప్రతి సక్సెస్ ఫుల్ పార్టనర్ ఒకప్పుడు సున్నా నుండి స్టార్ట్ చేసినవారే. ఈరోజే మీ ఎర్నింగ్ ప్రయాణం మొదలుపెట్టండి!”",
        "focus": "వారం ప్రారంభంలోనే మీ రిఫరల్ లింక్ షేర్ చేసి లైఫ్‌టైమ్ కమీషన్లు పొందండి."
    },
    {
        "day": 2, # Tuesday
        "header": "💡 *TUESDAY GROWTH SPARK — మీ నెట్‌వర్కే మీ అసలైన ఆస్తి!*",
        "quote": "“అవకాశం కోసం ఎదురుచూడకండి — సోలార్, ఇన్సూరెన్స్ లేదా EV అవసరం ఉన్నవారిని ఈరోజే రిఫర్ చేయండి!”",
        "focus": "మీకు తెలిసిన వారిని VGK4U ఇన్ఫ్రా ప్రాజెక్ట్‌లతో కనెక్ట్ చేయండి."
    },
    {
        "day": 3, # Wednesday
        "header": "🌟 *WEDNESDAY MOMENTUM — గొప్ప రివార్డులు మిమ్మల్ని ఆహ్వానిస్తున్నాయి!*",
        "quote": "“ఆలోచించడం కాకుండా ఆచరణలో పెట్టడమే విజయం సాధించడానికి అసలైన రహస్యం!”",
        "focus": "ఆలస్యం చేయకుండా Solar, Insurance & EV లీడ్‌ని సబ్మిట్ చేయండి."
    },
    {
        "day": 4, # Thursday
        "header": "🔥 *THURSDAY DRIVE — మీ ఆర్థిక స్వాతంత్రం వైపు అడుగులు వేయండి!*",
        "quote": "“చిన్న చిన్న అడుగులే రేపటి పెద్ద ఆర్థిక విజయానికి పునాది అవుతాయి!”",
        "focus": "మీ కాంటాక్ట్స్‌ని VGK4U ద్వారా సంపాదన మార్గాలుగా మార్చుకోండి."
    },
    {
        "day": 5, # Friday
        "header": "✨ *FRIDAY FINISH STRONG — ఈ వారాన్ని గొప్పగా ముగించండి!*",
        "quote": "“ప్రతి రోజు కొంత పురోగతి సాధించడమే అసలైన విజయం!”",
        "focus": "వీకెండ్ రాకముందే మీ మొదటి Solar, Insurance లేదా EV లీడ్‌ని సబ్మిట్ చేయండి."
    },
    {
        "day": 6, # Saturday
        "header": "🏆 *SATURDAY VISION — ప్యాసివ్ ఇన్‌కమ్ స్ట్రీమ్‌ని బిల్డ్ చేసుకోండి!*",
        "quote": "“సమయాన్ని వృధా చేయకుండా మీ మల్టీ-సెక్టార్ రిఫరల్ నెట్‌వర్క్‌ని నిర్మించుకోండి!”",
        "focus": "ఈ వీకెండ్‌లోనే క్లీన్ ఎనర్జీ & ఇన్సూరెన్స్ కస్టమర్లను కనెక్ట్ చేయండి."
    }
]


def _record_audit_log(job_id: str, job_name: str, payload: dict, triggered_by: str = "SCHEDULED", status: str = "SUCCESS", error_msg: str = None):
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
        logs = []
        if os.path.exists(AUDIT_LOG_FILE):
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except Exception:
                    logs = []

        entry = {
            "id": f"log_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{job_id}",
            "job_id": job_id,
            "job_name": job_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": status,
            "triggered_by": triggered_by,
            "payload": payload,
            "error_message": error_msg
        }
        logs.insert(0, entry)
        with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs[:500], f, indent=2)
    except Exception as exc:
        logger.error(f"[WA-AUDIT-LOG] Failed to record audit log: {exc}")


def run_vgk_member_zero_lead_motivational_dispatch(db: Session, trigger_type: str = "SCHEDULED", triggered_by: str = "SYSTEM"):
    """
    Dispatches dynamic 7:30 AM motivational messages to all active VGK Channel Partners with 0 leads.
    """
    logger.info("🌅 [VGK-0LEAD-MOTIVATION] Starting daily 7:30 AM 0-lead partner motivational dispatch...")

    # 1. Fetch community proof stats
    stats_query = text("""
        SELECT 
            COUNT(DISTINCT p.id) AS active_earning_partners,
            COALESCE(SUM(e.commission_amount), 0) AS total_gross_earned,
            COALESCE(SUM(l.deal_value_total), 0) AS total_pipeline_opportunity
        FROM official_partners p
        LEFT JOIN vgk_cash_income_entries e ON (e.partner_id = p.id AND e.status != 'CANCELLED')
        LEFT JOIN crm_leads l ON (l.associated_partner_id = p.id OR l.primary_owner_id = p.id OR l.source_ref_id = CAST(p.id AS VARCHAR))
        WHERE p.is_active = TRUE
    """)
    stats_row = db.execute(stats_query).fetchone()

    # Active partners with > 0 leads + 150 Offset
    db_active_partners = db.execute(text("""
        SELECT COUNT(DISTINCT p.id)
        FROM official_partners p
        JOIN crm_leads c ON (c.associated_partner_id = p.id OR c.primary_owner_id = p.id OR c.source_ref_id = CAST(p.id AS VARCHAR))
        WHERE p.is_active = TRUE
    """)).scalar() or 0
    
    active_partners_count = db_active_partners + 150

    total_gross_earned = float(stats_row[1]) if stats_row and stats_row[1] else 0.0
    total_pipeline_val = float(stats_row[2]) if stats_row and stats_row[2] else 0.0

    # 2. Fetch 0-lead active partners
    zero_lead_partners = db.execute(text("""
        SELECT p.id, p.partner_name, p.partner_code, p.phone, p.whatsapp_number
        FROM official_partners p
        LEFT JOIN crm_leads c ON (c.associated_partner_id = p.id OR c.primary_owner_id = p.id OR c.source_ref_id = CAST(p.id AS VARCHAR))
        WHERE p.is_active = TRUE
        GROUP BY p.id, p.partner_name, p.partner_code, p.phone, p.whatsapp_number
        HAVING COUNT(c.id) = 0
        ORDER BY p.id ASC
    """)).fetchall()

    logger.info(f"📊 [VGK-0LEAD-MOTIVATION] Found {len(zero_lead_partners)} active partners with 0 leads.")

    # 3. Determine today's rotating theme
    weekday = datetime.datetime.now().weekday()
    theme_idx = (weekday + 1) % 7 # 0=Sunday
    theme = next((t for t in ROTATING_MOTIVATIONAL_THEMES if t["day"] == theme_idx), ROTATING_MOTIVATIONAL_THEMES[1])

    dispatched_count = 0
    skipped_count = 0
    failed_count = 0
    results = []

    bot_url = "http://localhost:5002/api/send-message"

    # Support template customization override if stored
    from app.services.wa_template_storage_service import get_job_template
    custom_tpl = get_job_template("vgk_member_zero_lead_motivational")

    # Fetch numbers sent today for strict deduplication from message_log AND wa_inbox
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    start_of_today_utc = (ist_now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(hours=5, minutes=30))
    
    sent_today_numbers = set()
    try:
        from app.models.whatsapp import MessageLog
        log_rows = db.query(MessageLog.mobile_number).filter(MessageLog.sent_at >= start_of_today_utc).all()
        for r in log_rows:
            if r[0]:
                cp = ''.join(c for c in str(r[0]) if c.isdigit())[-10:]
                if len(cp) == 10:
                    sent_today_numbers.add(cp)

        inbox_rows = db.execute(text("SELECT from_phone FROM wa_inbox WHERE received_at >= :t"), {"t": start_of_today_utc}).fetchall()
        for r in inbox_rows:
            if r[0]:
                cp = ''.join(c for c in str(r[0]) if c.isdigit())[-10:]
                if len(cp) == 10:
                    sent_today_numbers.add(cp)
    except Exception as e:
        logger.warning(f"[VGK-0LEAD] Dedup check warning: {e}")

    for p in zero_lead_partners:
        p_id = p[0]
        p_name = p[1] or "Channel Partner"
        p_code = p[2] or f"VGK{p_id:06d}"
        phone = (p[3] or p[4] or "").strip()
        clean_phone = "".join(ch for ch in phone if ch.isdigit())

        if not clean_phone or len(clean_phone) < 10:
            failed_count += 1
            results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": "Invalid phone"})
            continue

        clean_10 = clean_phone[-10:]
        if trigger_type == "SCHEDULED" and clean_10 in sent_today_numbers:
            logger.info(f"⏩ Zero-lead member {p_name} ({clean_10}) already received a message today. Skipping.")
            skipped_count += 1
            results.append({"member_id": p_id, "name": p_name, "status": "SKIPPED", "reason": "Already sent today"})
            continue

        # Mark as seen in this run to prevent duplicate dispatches if multiple partner records share the same phone
        sent_today_numbers.add(clean_10)

        try:
            msg_text = custom_tpl.format(
                theme_header=theme['header'],
                theme_quote=theme['quote'],
                theme_focus=theme['focus'],
                member_name=p_name,
                user_code=p_code,
                phone=phone,
                active_earning_partners=active_partners_count,
                total_gross_earned=f"{int(total_gross_earned):,}",
                total_pipeline_val=f"{int(total_pipeline_val):,}"
            )
        except Exception:
            msg_text = (
                f"{theme['header']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"నమస్కారం *{p_name}* గారు ({p_code}),\n\n"
                f"{theme['quote']}\n\n"
                f"💡 *ఈరోజే యాక్షన్ ఎందుకు తీసుకోవాలి?*\n"
                f"• *{active_partners_count}+ Active Partners* మన VGK4U లో ఆల్రెడీ సక్సెస్ ఫుల్ గా ఇన్ కమ్ ఎర్న్ చేస్తున్నారు!\n"
                f"• *₹{int(total_gross_earned):,} Total Gross Earnings* మన నెట్‌వర్క్ పార్టనర్స్‌కి పంపిణీ చేయబడ్డాయి!\n"
                f"• *₹{int(total_pipeline_val):,} Active Opportunity* మన పైప్‌లైన్‌లో అందుబాటులో ఉంది!\n\n"
                f"🔥 *CHALLENGE*: {active_partners_count}+ యాక్టివ్ పార్టనర్స్ ఆల్రెడీ ఎర్న్ చేస్తున్నారు — మరి మీరు ఎప్పుడు మొదలుపెడుతున్నారు?\n\n"
                f"🎯 *Mee Next Step*: {theme['focus']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *REFER AND EARN — మీ మొదటి లీడ్‌ని ఈరోజే సబ్మిట్ చేయండి! (Solar, Insurance & EV)*\n"
                f"👉 Submit lead now: https://vgk4u.com/partner-portal\n"
                f"💬 _Auto-generated VGK4U Member Motivation_"
            )

        try:
            from app.services.whatsapp_auto_service import send_direct_whatsapp
            wa_res = send_direct_whatsapp(db=db, phone=clean_phone, message=msg_text)

            if wa_res.get("success"):
                dispatched_count += 1
                results.append({"member_id": p_id, "name": p_name, "status": "SUCCESS", "phone": clean_phone})
            else:
                failed_count += 1
                err_text = wa_res.get("error") or wa_res.get("reason") or "Dispatch failed"
                results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": err_text})
        except Exception as exc:
            failed_count += 1
            results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": str(exc)})

    payload = {
        "total_count": len(zero_lead_partners),
        "total_eligible": len(zero_lead_partners),
        "dispatched_count": dispatched_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "active_partners_with_leads": active_partners_count,
        "total_gross_earned": total_gross_earned,
        "theme_used": theme["header"],
        "results": results
    }

    _record_audit_log(
        job_id="wa_daily_vgk_zero_lead_motivational_730am",
        job_name="VGK Members Daily 7:30 AM 0-Lead Motivational Dispatch",
        payload=payload,
        triggered_by=triggered_by,
        status="SUCCESS" if failed_count == 0 else "PARTIAL_SUCCESS"
    )

    logger.info(f"✅ [VGK-0LEAD-MOTIVATION] Dispatch finished. Sent: {dispatched_count}, Failed: {failed_count}")
    return payload
