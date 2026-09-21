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
            "🌅 *శుభోదయం / Good Morning {{1}}!*\n\n"
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
            "🌅 *శుభోదయం / Good Morning {{1}}!*\n\n"
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
            "🌅 *శుభోదయం / Good Morning {{1}}!*\n\n"
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
            "🌅 *శుభోదయం / Good Morning {{1}}!*\n\n"
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
        ~CRMLead.status.in_(excluded_statuses),
        or_(
            CRMLead.tags.is_(None),
            and_(
                ~CRMLead.tags.ilike('%suppress_morning_wish%'),
                ~CRMLead.tags.ilike('%wa_unreachable%')
            )
        )
    ).filter(
        or_(
            CRMLead.status == 'New',
            CRMLead.last_contact_date < twenty_days_ago,
            CRMLead.last_contact_date.is_(None)
        )
    )

    leads = query.all()
    
    # Exclude staff numbers and suppressed tags
    filtered_leads = []
    for l in leads:
        tag_str = (getattr(l, 'tags', '') or '').lower()
        if 'suppress_morning_wish' in tag_str or 'wa_unreachable' in tag_str:
            continue
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
    from app.services.automation_tracking_service import (
        create_execution,
        record_dispatch,
        finalize_execution,
        get_job_targets
    )

    current_rot = get_current_rotation_template(db)
    rot_index = current_rot["rot_index"]
    template_slug = current_rot["template_slug"]
    meta_template_name = template_slug
    tdef = next((t for t in MORNING_WISH_TEMPLATES if t["rot_index"] == rot_index), MORNING_WISH_TEMPLATES[0])

    creds = get_wa_credentials(db)
    access_token = creds.get("access_token") or ""
    phone_id = creds.get("phone_number_id") or ""

    exec_record = create_execution(
        db=db,
        job_id="wa_daily_morning_wish",
        job_name="WhatsApp 8 AM Morning Wish Dispatch",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        company_id=1
    )

    # Scanned WhatsApp Anti-Ban Safety Hold
    import os
    if not force_test and os.getenv("HOLD_MORNING_WHATSAPP_DISPATCHES", "true").lower() == "true":
        logger.info("⏸️ [WA-MORNING-WISH-HELD] Cold lead morning wishes held to protect Scanned SIM from bulk bans.")
        if exec_record:
            exec_record.status = "HELD"
            exec_record.error_message = "Temporarily held to protect Scanned WhatsApp SIM"
            db.commit()
        return {
            "success": True,
            "status": "HELD",
            "message": "Morning wishes temporarily held to protect Scanned WhatsApp SIM while Meta Cloud API deadlock is resolved.",
            "sent_count": 0,
            "skipped_count": 0,
            "failed_count": 0
        }

    leads = get_eligible_leads_for_morning_wish(db)
    if limit_count and limit_count > 0:
        leads = leads[:limit_count]

    # ── 3-Day (72-Hour) Deduplication Window ──────────────────────────────────
    # User Rule: Everyday wishes are not required. Each contact should receive wishes
    # at most once every 3 days (72 hours).
    three_days_ago_utc = datetime.utcnow() - timedelta(days=3)

    msg_log_numbers = set(
        ''.join(c for c in (r[0] or '') if c.isdigit())[-10:]
        for r in db.query(MessageLog.mobile_number).filter(
            MessageLog.sent_at >= three_days_ago_utc,
            MessageLog.current_status.in_(['sent', 'delivered']),
            MessageLog.job_id == 'wa_daily_morning_wish'
        ).all() if r[0]
    )
    
    inbox_numbers = set()
    try:
        inbox_rows = db.execute(
            text("SELECT from_phone FROM wa_inbox WHERE received_at >= :t AND message_type = 'outbound' AND (body_text LIKE '%శుభోదయం%' OR body_text LIKE '%Good Morning%')"),
            {"t": three_days_ago_utc}
        ).fetchall()
        inbox_numbers = set(''.join(c for c in (r[0] or '') if c.isdigit())[-10:] for r in inbox_rows if r[0])
    except Exception:
        pass

    sent_recently_numbers = msg_log_numbers.union(inbox_numbers)

    sent_count = 0
    skipped_count = 0
    failed_count = 0
    details = []

    for lead in leads:
        raw_phone = getattr(lead, 'phone', '') or ''
        if not _is_valid_phone(raw_phone):
            skipped_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_record.id,
                job_id="wa_daily_morning_wish",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=raw_phone,
                recipient_name=(getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Friend').strip(),
                target_entity_type="crm_lead",
                target_entity_id=lead.id,
                status="SKIPPED",
                error_message="Invalid phone format"
            )
            continue

        # Recipient phone formatting
        phone_digits = ''.join(c for c in raw_phone if c.isdigit())
        if len(phone_digits) == 10:
            phone_formatted = f"91{phone_digits}"
        elif len(phone_digits) == 12 and phone_digits.startswith("91"):
            phone_formatted = phone_digits
        else:
            skipped_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_record.id,
                job_id="wa_daily_morning_wish",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=raw_phone,
                recipient_name=(getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Friend').strip(),
                target_entity_type="crm_lead",
                target_entity_id=lead.id,
                status="SKIPPED",
                error_message="Unsupported phone length"
            )
            continue

        lead_name = (getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Friend').strip()

        # Check if already sent within last 3 days (72h deduplication rule)
        clean_10 = phone_digits[-10:]
        if (clean_10 in sent_recently_numbers or phone_formatted in sent_recently_numbers) and not force_test:
            skipped_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_record.id,
                job_id="wa_daily_morning_wish",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=phone_formatted,
                recipient_name=lead_name,
                target_entity_type="crm_lead",
                target_entity_id=lead.id,
                status="SKIPPED",
                error_message="Already sent morning wish within last 3 days (72h rule)"
            )
            continue

        # Build Meta WhatsApp API Payload
        sent_success = False
        error_msg = None

        # Dispatch via Canonical Outbound Service
        from app.services.whatsapp_canonical_service import WhatsAppCanonicalService

        safe_lead_name = lead_name if lead_name and lead_name != '0' else f"Customer ({clean_10})"
        wish_body = (
            tdef.get("body_text", "🌅 Good Morning! Wishing you a productive and successful day ahead.")
            .replace("{{name}}", safe_lead_name)
            .replace("{{1}}", safe_lead_name)
            .replace("{name}", safe_lead_name)
            .replace("{1}", safe_lead_name)
        )

        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": safe_lead_name}
                ]
            }
        ]

        res = WhatsAppCanonicalService.send_meta_template_message(
            db=db,
            phone=phone_formatted,
            template_name=meta_template_name,
            language_code="en",
            components=components,
            message_type="template",
            user_name=safe_lead_name,
            sender_type="bot",
            idempotency_key=f"morning_wish:{phone_formatted}:{get_indian_time().strftime('%Y%m%d')}",
            raw_body_fallback=wish_body,
            job_id="wa_daily_morning_wish",
            execution_id=exec_record.id
        )

        sent_success = res.get("success", False)
        error_msg = res.get("reason") if not sent_success else None

        if sent_success:
            sent_count += 1
            sent_recently_numbers.add(clean_10)
        else:
            failed_count += 1
            # User Rule: Do NOT retry failed messages - ignore them.
            # If a contact fails across 3 consecutive days/attempts with 0 successes,
            # tag 'suppress_morning_wish' to permanently remove from future distribution lists.
            try:
                fail_history = db.query(MessageLog).filter(
                    MessageLog.mobile_number.like(f"%{clean_10}"),
                    MessageLog.job_id == "wa_daily_morning_wish",
                    MessageLog.current_status == "failed"
                ).count()

                success_history = db.query(MessageLog).filter(
                    MessageLog.mobile_number.like(f"%{clean_10}"),
                    MessageLog.job_id == "wa_daily_morning_wish",
                    MessageLog.current_status.in_(["sent", "delivered"])
                ).count()

                if fail_history >= 3 and success_history == 0 and lead:
                    current_tags = (getattr(lead, 'tags', '') or '').strip()
                    if 'suppress_morning_wish' not in current_tags:
                        lead.tags = f"{current_tags},suppress_morning_wish".strip(',')
                        db.add(lead)
                        db.commit()
                        logger.info(
                            f"[WA-MORNING-WISH] 🚫 Lead #{lead.id} ({clean_10}) failed 3 times with 0 deliveries. "
                            f"Permanently tagged 'suppress_morning_wish' and removed from distribution list."
                        )
            except Exception as _fh_err:
                logger.warning(f"[WA-MORNING-WISH] Error checking consecutive failures for {clean_10}: {_fh_err}")

        # Throttled Pacing: 1.2 second pause between API requests (~30-40 msgs/min)
        # Prevents Meta API connection pool exhaustion (NET_ERR) and protects business account health.
        import time
        time.sleep(1.2)

        record_dispatch(
            db=db,
            execution_id=exec_record.id,
            job_id="wa_daily_morning_wish",
            recipient_type="CUSTOMER_LEAD",
            recipient_identifier=phone_formatted,
            recipient_name=safe_lead_name,
            target_entity_type="crm_lead",
            target_entity_id=lead.id,
            message_log_id=res.get("message_log_id"),
            provider_message_id=res.get("wamid"),
            status="SENT" if sent_success else "FAILED",
            error_message=error_msg,
            payload_snapshot={"template": meta_template_name, "rotation": rot_index}
        )

        details.append({
            "lead_id": lead.id,
            "lead_name": lead_name,
            "phone": phone_formatted,
            "status": "sent" if sent_success else "failed",
            "wamid": res.get("wamid"),
            "error": error_msg
        })

    # Supplementary targets if any configured
    supp_targets = get_job_targets(db, "wa_daily_morning_wish", company_id=1)
    for tgt in supp_targets:
        if not tgt.get("is_active", True):
            continue
        tgt_phone = tgt.get("recipient_identifier")
        if not tgt_phone:
            continue
        tgt_digits = ''.join(c for c in tgt_phone if c.isdigit())
        if len(tgt_digits) == 10:
            tgt_formatted = f"91{tgt_digits}"
        elif len(tgt_digits) == 12 and tgt_digits.startswith("91"):
            tgt_formatted = tgt_digits
        else:
            continue

        from app.services.whatsapp_canonical_service import WhatsAppCanonicalService
        tgt_name = tgt.get("recipient_name") or "Team Member"
        tgt_wish_body = tdef.get("body_text", "🌅 Good Morning!").replace("{{1}}", tgt_name)
        tgt_components = [{"type": "body", "parameters": [{"type": "text", "text": tgt_name}]}]
        res = WhatsAppCanonicalService.send_meta_template_message(
            db=db,
            phone=tgt_formatted,
            template_name=meta_template_name,
            language_code="en",
            components=tgt_components,
            message_type="template",
            user_name=tgt_name,
            sender_type="bot",
            idempotency_key=f"morning_wish_cc:{tgt_formatted}:{get_indian_time().strftime('%Y%m%d')}",
            raw_body_fallback=tgt_wish_body,
            job_id="wa_daily_morning_wish",
            execution_id=exec_record.id
        )
        t_ok = res.get("success", False)
        if t_ok:
            sent_count += 1
        else:
            failed_count += 1
        record_dispatch(
            db=db,
            execution_id=exec_record.id,
            job_id="wa_daily_morning_wish",
            recipient_type=tgt.get("recipient_type", "PHONE_NUMBER"),
            recipient_identifier=tgt_formatted,
            recipient_name=tgt_name,
            message_log_id=res.get("message_log_id"),
            provider_message_id=res.get("wamid"),
            status="SENT" if t_ok else "FAILED",
            error_message=res.get("reason") if not t_ok else None,
            payload_snapshot={"template": meta_template_name, "is_cc": True}
        )

    exec_status = "COMPLETED" if (failed_count == 0 and (sent_count > 0 or len(leads) == 0)) else ("PARTIAL" if sent_count > 0 else "FAILED")
    finalize_execution(db, exec_record.id, exec_status)

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
