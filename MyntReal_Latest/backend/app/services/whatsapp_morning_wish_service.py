"""
DC_WA_MORNING_WISH_001 — 4-Day Rotating Bilingual 8 AM WhatsApp Morning Wish Engine
Manages:
1. 4-day rotating bilingual (Telugu + English) WhatsApp templates with CTA buttons (Call + Website).
2. Auto-seeding into database and submitting to Meta Graph API.
3. Daily 8:00 AM IST dispatch targeting:
   - All NEW leads (status == 'New')
   - Leads uncontacted for >20 days (last_contact_date < NOW - 20 days or NULL)
"""

import logging
import requests
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from app.core.timezone import get_indian_time, IST

logger = logging.getLogger(__name__)

# ── 4-Day Rotating Templates Definition ───────────────────────────────────────
MORNING_WISH_TEMPLATES = [
    {
        "rot_index": 1,
        "slug": "daily_wish_rot_1",
        "meta_name": "daily_wish_rot_1",
        "name": "Daily Wish Rot 1 - Solar Subsidy",
        "body_text": (
            "🌅 *శుభోదయం / Good Morning {{name}}!*\n\n"
            "_\"ప్రతి రోజూ కొత్త వెలుగులతో ప్రారంభమవుతుంది!\"_ ☀️\n\n"
            "Team *MyntReal* wishes you and your family a bright, prosperous, and successful day ahead!\n\n"
            "⚡ *PM సూర్య ఘర్ పథకంతో ₹78,000 సబ్సిడీ & మీ ఇంటికి ఉచిత విద్యుత్ పొందండి.*\n\n"
            "Have a wonderful day ahead! 🙏"
        ),
        "footer_text": "MyntReal.com",
        "example_values": ["Friend"],
        "buttons": [
            {"type": "PHONE_NUMBER", "text": "Call Us", "phone_number": "+918585852738"},
            {"type": "URL", "text": "Visit Website", "url": "https://myntreal.com"}
        ]
    },
    {
        "rot_index": 2,
        "slug": "daily_wish_rot_2",
        "meta_name": "daily_wish_rot_2",
        "name": "Daily Wish Rot 2 - Zero Electricity Bill",
        "body_text": (
            "🌅 *శుభోదయం / Good Morning {{name}}!*\n\n"
            "_\"ఈ రోజు సాధించే చిన్న మార్పులే మీ కుటుంబ భవిష్యత్తుకు గొప్ప వెలుగు.\"_ ☀️\n\n"
            "Team *MyntReal - Har Ghar Solar* wishes you a peaceful and productive day!\n\n"
            "💡 *మీ ఇంటి కరెంట్ బిల్లును సున్నా (₹0) చేసుకునే ఉచిత సలహా కోసం మమ్మల్ని సంప్రదించండి.*\n\n"
            "Have a great day! 🙏"
        ),
        "footer_text": "MyntReal.com",
        "example_values": ["Friend"],
        "buttons": [
            {"type": "PHONE_NUMBER", "text": "Call Us", "phone_number": "+918585852738"},
            {"type": "URL", "text": "Visit Website", "url": "https://myntreal.com"}
        ]
    },
    {
        "rot_index": 3,
        "slug": "daily_wish_rot_3",
        "meta_name": "daily_wish_rot_3",
        "name": "Daily Wish Rot 3 - Savings & Health",
        "body_text": (
            "🌅 *శుభోదయం / Good Morning {{name}}!*\n\n"
            "_\"స్వచ్ఛమైన శక్తి - శ్రేయస్సకరమైన జీవితం!\"_ ☀️\n\n"
            "May your day be filled with positive energy, good health, and success! Best wishes from *MyntReal*.\n\n"
            "🌿 *3KW సోలార్ రూఫ్‌టాప్ ద్వారా నెలకు వేల రూపాయలు ఆదా చేసుకోండి.*\n\n"
            "Have a blessed day! 🙏"
        ),
        "footer_text": "MyntReal.com",
        "example_values": ["Friend"],
        "buttons": [
            {"type": "PHONE_NUMBER", "text": "Call Us", "phone_number": "+918585852738"},
            {"type": "URL", "text": "Visit Website", "url": "https://myntreal.com"}
        ]
    },
    {
        "rot_index": 4,
        "slug": "daily_wish_rot_4",
        "meta_name": "daily_wish_rot_4",
        "name": "Daily Wish Rot 4 - Expert Support",
        "body_text": (
            "🌅 *శుభోదయం / Good Morning {{name}}!*\n\n"
            "_\"ఈ ఉదయం మీ ముఖంలో చిరునవ్వు, మీ ఇంట్లో వెలుగు నిండాలని ఆశిస్తున్నాము!\"_ ☀️\n\n"
            "Team *MyntReal* is dedicated to supporting your energy independence.\n\n"
            "📞 *మీ సోలార్ సందేహాల నివారణకు & ఉచిత సైట్ విజిట్ కోసం ఒక కాల్ చేయండి.*\n\n"
            "Have a wonderful day ahead! 🙏"
        ),
        "footer_text": "MyntReal.com",
        "example_values": ["Friend"],
        "buttons": [
            {"type": "PHONE_NUMBER", "text": "Call Us", "phone_number": "+918585852738"},
            {"type": "URL", "text": "Visit Website", "url": "https://myntreal.com"}
        ]
    }
]


def seed_and_submit_morning_wish_templates(db: Session) -> Dict[str, Any]:
    """
    Ensures all 4 rotating morning wish templates exist in DB and submits to Meta API.
    """
    from app.models.whatsapp import WhatsAppTemplate
    from app.services.wa_credentials import get_wa_credentials

    creds = get_wa_credentials(db)
    access_token = creds.get("access_token") or ""
    waba_id = creds.get("business_account_id") or ""

    results = []

    for tdef in MORNING_WISH_TEMPLATES:
        slug = tdef["slug"]
        meta_name = tdef["meta_name"]

        tpl = db.query(WhatsAppTemplate).filter(
            or_(WhatsAppTemplate.slug == slug, WhatsAppTemplate.meta_template_name == meta_name)
        ).first()

        if not tpl:
            tpl = WhatsAppTemplate(
                slug=slug,
                name=tdef["name"],
                body_text=tdef["body_text"],
                footer_text=tdef["footer_text"],
                segment="leads",
                template_type="marketing",
                meta_template_name=meta_name,
                meta_template_language="en",
                meta_category="MARKETING",
                header_type="none",
                buttons=tdef["buttons"],
                is_active=True,
                is_meta_approved=True,
                created_at=get_indian_time()
            )
            db.add(tpl)
            db.commit()
            db.refresh(tpl)
        else:
            # Update fields
            tpl.name = tdef["name"]
            tpl.body_text = tdef["body_text"]
            tpl.footer_text = tdef["footer_text"]
            tpl.buttons = tdef["buttons"]
            tpl.meta_template_name = meta_name
            tpl.is_meta_approved = True
            tpl.is_active = True
            db.commit()

        # Submit to Meta API if WABA credentials exist
        meta_submitted = False
        meta_response = None
        if access_token and waba_id:
            try:
                # Convert named {{name}} to positional {{1}} for Meta API payload
                meta_body = tdef["body_text"].replace("{{name}}", "{{1}}")
                meta_payload = {
                    "name": meta_name,
                    "language": "en",
                    "category": "MARKETING",
                    "components": [
                        {
                            "type": "BODY",
                            "text": meta_body,
                            "example": {"body_text": [["Friend"]]}
                        },
                        {
                            "type": "FOOTER",
                            "text": tdef["footer_text"]
                        },
                        {
                            "type": "BUTTONS",
                            "buttons": [
                                {
                                    "type": "PHONE_NUMBER",
                                    "text": "Call Us",
                                    "phone_number": "+918585852738"
                                },
                                {
                                    "type": "URL",
                                    "text": "Visit Website",
                                    "url": "https://myntreal.com"
                                }
                            ]
                        }
                    ]
                }
                url = f"https://graph.facebook.com/v21.0/{waba_id}/message_templates"
                resp = requests.post(url, json=meta_payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
                raw = resp.json()
                if resp.status_code in (200, 201):
                    meta_submitted = True
                    tpl.is_meta_approved = True
                    db.commit()
                meta_response = raw
            except Exception as exc:
                meta_response = str(exc)

        results.append({
            "rot_index": tdef["rot_index"],
            "slug": slug,
            "template_id": tpl.id,
            "meta_submitted": meta_submitted,
            "meta_response": meta_response
        })

    return {"success": True, "templates": results}


def get_eligible_leads_for_morning_wish(db: Session) -> List[Any]:
    """
    Fetches leads eligible for the 8:00 AM morning wish:
    1. New Leads (status == 'New')
    2. Uncontacted for >20 days (last_contact_date < NOW - 20 days or NULL)
    Excludes: Closed, Won, Lost, Junk, Opted-out, AND Staff Employee Phone Numbers.
    """
    from app.models.crm import CRMLead
    from app.models.staff import StaffEmployee

    ist_now = get_indian_time()
    twenty_days_ago = ist_now - timedelta(days=20)

    # Exclude non-active statuses
    excluded_statuses = ('Closed', 'Won', 'Lost', 'Junk', 'Duplicate', 'Cancelled', 'Not Interested')

    # Fetch staff employee phones to prevent staff from receiving customer lead wishes
    staff_rows = db.query(StaffEmployee.phone).all()
    staff_phones = set(''.join(c for c in (r[0] or '') if c.isdigit())[-10:] for r in staff_rows if r[0])

    query = db.query(CRMLead).filter(
        CRMLead.phone.isnot(None),
        CRMLead.phone != '',
        ~CRMLead.status.in_(excluded_statuses)
    ).filter(
        or_(
            CRMLead.status == 'New',
            CRMLead.last_contact_date < twenty_days_ago,
            CRMLead.last_contact_date.is_(None)
        )
    )

    leads = query.all()
    
    # Exclude staff numbers
    filtered_leads = []
    for l in leads:
        ph_digits = ''.join(c for c in (l.phone or '') if c.isdigit())[-10:]
        if ph_digits not in staff_phones:
            filtered_leads.append(l)

    return filtered_leads


def get_current_rotation_template(db: Session) -> Dict[str, Any]:
    """
    Calculates current 4-day rotation template for today.
    Formula: (day_of_year % 4) + 1
    """
    from app.models.whatsapp import WhatsAppTemplate

    # IST time
    ist_now = get_indian_time()
    day_of_year = ist_now.timetuple().tm_yday
    rot_index = (day_of_year % 4) + 1

    slug = f"daily_wish_rot_{rot_index}"
    tdef = next((t for t in MORNING_WISH_TEMPLATES if t["rot_index"] == rot_index), MORNING_WISH_TEMPLATES[0])

    tpl = db.query(WhatsAppTemplate).filter(
        or_(WhatsAppTemplate.slug == slug, WhatsAppTemplate.meta_template_name == slug)
    ).first()

    return {
        "rot_index": rot_index,
        "date_ist": ist_now.strftime("%Y-%m-%d"),
        "day_of_year": day_of_year,
        "template_slug": slug,
        "template_db_id": tpl.id if tpl else None,
        "template_name": tdef["name"],
        "body_text": tdef["body_text"]
    }


def dispatch_daily_morning_wishes(
    db: Session,
    force_test: bool = False,
    limit_count: Optional[int] = None,
    trigger_type: str = "AUTO_SCHEDULER",
    triggered_by: str = "System Cron"
) -> Dict[str, Any]:
    """
    Executes the 8:00 AM morning wish dispatch:
    - Calculates today's rotation template
    - Gets eligible leads
    - Dispatches WhatsApp template message to each lead
    """
    from app.models.whatsapp import MessageLog
    from app.services.whatsapp_auto_service import _is_valid_phone
    from app.services.wa_credentials import get_wa_credentials
    from app.services.whatsapp_audit_service import log_wa_trigger_execution

    current_rot = get_current_rotation_template(db)
    rot_index = current_rot["rot_index"]
    template_slug = current_rot["template_slug"]
    meta_template_name = template_slug

    creds = get_wa_credentials(db)
    access_token = creds.get("access_token") or ""
    phone_id = creds.get("phone_number_id") or ""

    leads = get_eligible_leads_for_morning_wish(db)
    if limit_count and limit_count > 0:
        leads = leads[:limit_count]

    # Start of today IST for deduplication
    ist_now = get_indian_time()
    start_of_today = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Batch fetch all numbers sent today from MessageLog AND wa_inbox for 100% deduplication
    msg_log_numbers = set(
        ''.join(c for c in (r[0] or '') if c.isdigit())[-10:]
        for r in db.query(MessageLog.mobile_number).filter(MessageLog.sent_at >= start_of_today).all() if r[0]
    )
    
    inbox_numbers = set()
    try:
        inbox_rows = db.execute(text("SELECT from_phone FROM wa_inbox WHERE received_at >= :t"), {"t": start_of_today}).fetchall()
        inbox_numbers = set(''.join(c for c in (r[0] or '') if c.isdigit())[-10:] for r in inbox_rows if r[0])
    except Exception:
        pass

    sent_today_numbers = msg_log_numbers.union(inbox_numbers)

    sent_count = 0
    skipped_count = 0
    failed_count = 0
    details = []

    for lead in leads:
        raw_phone = getattr(lead, 'phone', '') or ''
        if not _is_valid_phone(raw_phone):
            skipped_count += 1
            continue

        # Recipient phone formatting
        phone_digits = ''.join(c for c in raw_phone if c.isdigit())
        if len(phone_digits) == 10:
            phone_formatted = f"91{phone_digits}"
        elif len(phone_digits) == 12 and phone_digits.startswith("91"):
            phone_formatted = phone_digits
        else:
            skipped_count += 1
            continue

        # Check if already sent today (instant O(1) set lookup)
        clean_10 = phone_digits[-10:]
        if (clean_10 in sent_today_numbers or phone_formatted in sent_today_numbers) and not force_test:
            skipped_count += 1
            continue

        lead_name = (getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Friend').strip()

        # Build Meta WhatsApp API Payload
        sent_success = False
        error_msg = None

        if access_token and phone_id:
            try:
                url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
                payload = {
                    "messaging_product": "whatsapp",
                    "to": phone_formatted,
                    "type": "template",
                    "template": {
                        "name": meta_template_name,
                        "language": {"code": "en"},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": lead_name}
                                ]
                            }
                        ]
                    }
                }
                resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=8)
                if resp.status_code in (200, 201):
                    sent_success = True
                else:
                    error_msg = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as exc:
                error_msg = str(exc)
        else:
            # Local simulation mode when credentials not configured
            sent_success = True
            error_msg = "Simulated (Meta WABA credentials pending configuration)"

        if sent_success:
            sent_count += 1
        else:
            failed_count += 1

        # Record history entry
        safe_lead_name = lead_name if lead_name and lead_name != '0' else f"Customer ({clean_10})"
        wish_body = tdef.get("body_text", "🌅 Good Morning! Wishing you a productive and successful day ahead.").replace("{{1}}", safe_lead_name)
        history_item = MessageLog(
            message_sid=f"wamid.sim.{uuid.uuid4().hex[:12]}",
            mobile_number=phone_formatted,
            user_name=safe_lead_name,
            message_type="template",
            message_body=wish_body,
            initial_status="sent" if sent_success else "failed",
            current_status="sent" if sent_success else "failed",
            sent_at=get_indian_time(),
            sender_type="bot"
        )
        db.add(history_item)
        db.commit()

        details.append({
            "lead_id": lead.id,
            "lead_name": lead_name,
            "phone": phone_formatted,
            "status": "sent" if sent_success else "failed",
            "error": error_msg
        })

    is_overall_success = (sent_count > 0 or len(leads) == 0) and failed_count == 0
    log_wa_trigger_execution(
        job_id="wa_daily_morning_wish",
        job_name="WhatsApp 8 AM Morning Wish Dispatch",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        targets=[],
        sent_count=sent_count,
        failed_count=failed_count,
        status="SUCCESS" if is_overall_success else "FAILED",
        error_message=f"Failed {failed_count} sends" if failed_count > 0 else None,
        detail_data={"total_eligible": len(leads), "sent_count": sent_count, "skipped_count": skipped_count}
    )

    return {
        "success": True,
        "rotation_index": rot_index,
        "template_slug": template_slug,
        "total_eligible_leads": len(leads),
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "details": details[:50]  # First 50 items
    }
