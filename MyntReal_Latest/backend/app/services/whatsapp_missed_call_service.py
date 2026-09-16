"""
DC_WA_MISSED_CALL_ACK_001 — Instant WhatsApp Missed Call Auto-Acknowledgement Service
Handles:
1. Auto-seeding and submitting `missed_call_ack_v1` template to Meta API.
2. Real-time trigger on MyOperator missed calls.
3. 6-Hour Deduplication Spam Guard (max 1 ACK message per number per 6 hours).
4. Auto-creating a new CRM lead if caller is unknown.
"""

import logging
import requests
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from app.core.timezone import get_indian_time, IST

logger = logging.getLogger(__name__)

MISSED_CALL_TEMPLATE = {
    "slug": "missed_call_ack_v1",
    "meta_name": "missed_call_ack_v1",
    "name": "Missed Call Auto-Acknowledgement",
    "meta_category": "UTILITY",
    "body_text": (
        "📱 *We missed your call! / మేము మీ కాల్‌ను స్వీకరించలేకపోయాము!*\n\n"
        "Hello {{name}},\n\n"
        "Thank you for calling *MyntReal - Har Ghar Solar*! ☀️\n\n"
        "Our team is currently occupied assisting other clients. *We will call you back as soon as possible!*\n\n"
        "💡 *In the meantime, you can explore PM Surya Ghar ₹78,000 Subsidy & zero electricity bill options:*\n\n"
        "⚡ *ఉచిత సలహా & ₹78,000 సబ్సిడీ వివరాల కోసం క్రింది బటన్ ద్వారా మా వెబ్‌సైట్‌ను చూడండి.*\n\n"
        "Warm regards,\n"
        "*Team MyntReal*"
    ),
    "footer_text": "MyntReal.com",
    "example_values": ["Valued Customer"],
    "buttons": [
        {"type": "URL", "text": "Explore Solar Plans", "url": "https://myntreal.com"},
        {"type": "URL", "text": "Customer Support", "url": "https://myntreal.com/support"}
    ]
}


def seed_and_submit_missed_call_template(db: Session) -> Dict[str, Any]:
    """
    Ensures missed_call_ack_v1 template exists in DB and submits to Meta API.
    """
    from app.models.whatsapp import WhatsAppTemplate
    from app.services.wa_credentials import get_wa_credentials

    slug = MISSED_CALL_TEMPLATE["slug"]
    meta_name = MISSED_CALL_TEMPLATE["meta_name"]

    tpl = db.query(WhatsAppTemplate).filter(
        or_(WhatsAppTemplate.slug == slug, WhatsAppTemplate.meta_template_name == meta_name)
    ).first()

    if not tpl:
        tpl = WhatsAppTemplate(
            slug=slug,
            name=MISSED_CALL_TEMPLATE["name"],
            body_text=MISSED_CALL_TEMPLATE["body_text"],
            footer_text=MISSED_CALL_TEMPLATE["footer_text"],
            segment="leads",
            template_type="utility",
            meta_template_name=meta_name,
            meta_template_language="en",
            meta_category="UTILITY",
            header_type="none",
            buttons=MISSED_CALL_TEMPLATE["buttons"],
            is_active=True,
            is_meta_approved=True,
            created_at=get_indian_time()
        )
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
    else:
        tpl.name = MISSED_CALL_TEMPLATE["name"]
        tpl.body_text = MISSED_CALL_TEMPLATE["body_text"]
        tpl.footer_text = MISSED_CALL_TEMPLATE["footer_text"]
        tpl.buttons = MISSED_CALL_TEMPLATE["buttons"]
        tpl.meta_template_name = meta_name
        tpl.is_meta_approved = True
        tpl.is_active = True
        db.commit()

    creds = get_wa_credentials(db)
    access_token = creds.get("access_token") or ""
    waba_id = creds.get("business_account_id") or ""

    meta_submitted = False
    meta_response = None

    if access_token and waba_id:
        try:
            meta_body = MISSED_CALL_TEMPLATE["body_text"].replace("{{name}}", "{{1}}")
            meta_payload = {
                "name": meta_name,
                "language": "en",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "BODY",
                        "text": meta_body,
                        "example": {"body_text": [["Valued Customer"]]}
                    },
                    {
                        "type": "FOOTER",
                        "text": MISSED_CALL_TEMPLATE["footer_text"]
                    },
                    {
                        "type": "BUTTONS",
                        "buttons": [
                            {
                                "type": "URL",
                                "text": "Explore Solar Plans",
                                "url": "https://myntreal.com"
                            },
                            {
                                "type": "URL",
                                "text": "Customer Support",
                                "url": "https://myntreal.com/support"
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

    return {
        "success": True,
        "template_id": tpl.id,
        "meta_submitted": meta_submitted,
        "meta_response": meta_response
    }


def handle_missed_call_whatsapp_ack(
    db: Session,
    caller_phone: str,
    caller_name: Optional[str] = None,
    lead_id: Optional[int] = None,
    call_type: Optional[str] = "inbound",
    company_id: Optional[int] = None,
    execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Triggers instant WhatsApp ACK for a missed call:
    - Formats caller phone
    - Guard 1: Inbound Calls Only Guard (skips outbound dialer attempts)
    - Guard 2: 24-Hour Deduplication Window Guard (max 1 ACK per 24 hours per caller)
    - Guard 3: Already Contacted Today Guard (skips if staff already spoke to caller today)
    - Matches or auto-creates CRM lead with scoped tenancy and locking
    - Dispatches missed_call_ack_v1 template
    """
    from app.models.crm import CRMLead
    from app.models.whatsapp import MessageLog
    from app.models.operator_calls import OperatorCall
    from app.services.whatsapp_auto_service import _is_valid_phone
    from app.services.wa_credentials import get_wa_credentials

    # ── Guard 1: Inbound Calls Only Guard ──────────────────────────────────────
    if call_type and str(call_type).lower() in ('outbound', 'outgoing'):
        logger.info(f"⏭️ Skipping missed call ACK for {caller_phone} — Outbound call attempt.")
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=caller_phone,
                recipient_name=caller_name or "Valued Customer",
                status="SKIPPED",
                error_message="Outbound call attempt"
            )
        return {"success": True, "reason": "skipped_outbound_call", "phone": caller_phone}

    if not caller_phone or not _is_valid_phone(caller_phone):
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=caller_phone or "",
                recipient_name=caller_name or "Valued Customer",
                status="FAILED",
                error_message="invalid_phone"
            )
        return {"success": False, "reason": "invalid_phone", "phone": caller_phone}

    phone_digits = ''.join(c for c in caller_phone if c.isdigit())
    if len(phone_digits) == 10:
        phone_formatted = f"91{phone_digits}"
    elif len(phone_digits) == 12 and phone_digits.startswith("91"):
        phone_formatted = phone_digits
    else:
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=caller_phone,
                recipient_name=caller_name or "Valued Customer",
                status="FAILED",
                error_message="unsupported_phone_format"
            )
        return {"success": False, "reason": "unsupported_phone_format", "phone": caller_phone}

    phone_core = phone_digits[-10:]

    # Start of today IST for "spoken today" checks
    ist_now = get_indian_time()
    start_of_today_ist = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Guard 2: 24-Hour Deduplication Window ──────────────────────────────────
    twenty_four_hours_ago = ist_now - timedelta(hours=24)
    recent_ack = db.query(MessageLog).filter(
        MessageLog.mobile_number == phone_formatted,
        MessageLog.sent_at >= twenty_four_hours_ago
    ).first()

    if recent_ack:
        logger.info(f"⏭️ Skipping missed call ACK for {phone_formatted} — ACK already sent within 24 hours.")
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=phone_formatted,
                recipient_name=caller_name or "Valued Customer",
                status="SKIPPED",
                error_message="ACK already sent within 24 hours"
            )
        return {"success": True, "reason": "skipped_dedup_24h", "phone": phone_formatted}

    # ── Guard 3: Already Spoken / Contacted Today Guard ───────────────────────
    answered_today = db.query(OperatorCall).filter(
        OperatorCall.caller_number.like(f"%{phone_core}"),
        OperatorCall.status == 'answered',
        OperatorCall.started_at >= start_of_today_ist
    ).first()

    if answered_today:
        logger.info(f"⏭️ Skipping missed call ACK for {phone_formatted} — Staff already spoke with caller today.")
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=phone_formatted,
                recipient_name=caller_name or "Valued Customer",
                status="SKIPPED",
                error_message="Staff already spoke with caller today"
            )
        return {"success": True, "reason": "skipped_already_contacted_today", "phone": phone_formatted}

    # ── Lead Match or Auto-Create ─────────────────────────────────────────
    lead = None
    if lead_id:
        lead = db.query(CRMLead).get(lead_id)

    if not lead and company_id:
        from app.models.staff_accounts import AssociatedCompany
        from app.services.crm_dedup_service import find_phone_duplicate
        comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        tenant_id = comp.client_id if comp else None
        if tenant_id:
            lead = find_phone_duplicate(
                db=db,
                tenant_id=tenant_id,
                company_id=company_id,
                phone=phone_formatted,
                with_lock=True
            )

    if lead and lead.last_contact_date and lead.last_contact_date >= start_of_today_ist:
        logger.info(f"⏭️ Skipping missed call ACK for {phone_formatted} — Lead contacted today in CRM.")
        if execution_id:
            from app.services.automation_tracking_service import record_dispatch
            record_dispatch(
                db=db,
                execution_id=execution_id,
                job_id="missed_call_ack",
                recipient_type="CUSTOMER_LEAD",
                recipient_identifier=phone_formatted,
                recipient_name=caller_name or "Valued Customer",
                target_entity_type="crm_lead",
                target_entity_id=lead.id,
                status="SKIPPED",
                error_message="Lead contacted today in CRM"
            )
        return {"success": True, "reason": "skipped_already_contacted_today", "phone": phone_formatted}

    if not lead and company_id:
        # DC_DID_STAFF_GUARD: Do not auto-create leads for company DID trunks or staff personal phones
        clean_core = re.sub(r'[^\d]', '', str(phone_core or ''))[-10:]
        is_did_or_staff = db.execute(text("""
            SELECT 1 FROM telephony_did_mappings WHERE RIGHT(REGEXP_REPLACE(did_number, '[^0-9]', '', 'g'), 10) = :phone AND is_active = true
            UNION
            SELECT 1 FROM staff_employees WHERE RIGHT(REGEXP_REPLACE(phone, '[^0-9]', '', 'g'), 10) = :phone AND status = 'active'
        """), {"phone": clean_core}).scalar()
        if is_did_or_staff:
            logger.info(f"⏭️ Dropping missed call lead creation for {phone_formatted} — Caller is a company DID or staff mobile.")
            return {"success": True, "reason": "dropped_internal_did_or_staff", "phone": phone_formatted}

        from app.models.staff_accounts import AssociatedCompany
        comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        tenant_id = comp.client_id if comp else None
        if tenant_id:
            # Auto-create new lead from missed call with explicit tenant_id and company_id
            lead_display_name = (caller_name or f"Missed Call {phone_core}").strip()
            lead = CRMLead(
                tenant_id=tenant_id,
                company_id=company_id,
                name=lead_display_name,
                phone=phone_formatted,
                status="New",
                source="Missed Call (MyOperator)",
                created_at=ist_now,
                updated_at=ist_now
            )
            db.add(lead)
            db.flush()
            from app.services.crm_phone_sync_service import sync_lead_phone_identities
            sync_lead_phone_identities(
                db=db,
                lead=lead,
                phone_raw=lead.phone,
                source_channel='whatsapp_missed_call',
                source_ref=f"missed_call_{phone_core}",
                with_lock=True
            )
            db.commit()
            db.refresh(lead)
        else:
            logger.warning(f"⏭️ Skipped auto-create lead for missed call {phone_formatted}: Company {company_id} has no tenant_id")
    elif not lead:
        logger.warning(f"⏭️ Skipped auto-create lead for missed call {phone_formatted}: No authoritative company_id provided (fail closed)")

    display_name = (getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or caller_name or 'Valued Customer').strip()
    if display_name.lower().startswith('missed call'):
        display_name = "Valued Customer"

    # ── 3. Meta WhatsApp API Dispatch (Canonical Real WAMID) ────────────────
    from app.services.whatsapp_canonical_service import WhatsAppCanonicalService

    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": display_name}
            ]
        }
    ]

    res = WhatsAppCanonicalService.send_meta_template_message(
        db=db,
        phone=phone_formatted,
        template_name="missed_call_ack_v1",
        language_code="en",
        components=components,
        message_type="missed_call_ack",
        user_name=display_name,
        sender_type="auto",
        company_id=4,
        idempotency_key=f"missed_call_ack:{phone_formatted}:{int(ist_now.timestamp() // 21600)}",
        raw_body_fallback=MISSED_CALL_TEMPLATE["body_text"].replace("{{name}}", display_name),
        job_id="missed_call_ack",
        execution_id=execution_id
    )

    sent_success = res.get("success", False)
    error_msg = res.get("reason") if not sent_success else None

    if execution_id:
        from app.services.automation_tracking_service import record_dispatch
        record_dispatch(
            db=db,
            execution_id=execution_id,
            job_id="missed_call_ack",
            recipient_type="CUSTOMER_LEAD",
            recipient_identifier=phone_formatted,
            recipient_name=display_name,
            target_entity_type="crm_lead" if lead else None,
            target_entity_id=lead.id if lead else None,
            message_log_id=res.get("message_log_id"),
            provider_message_id=res.get("wamid"),
            status="SENT" if sent_success else "FAILED",
            error_message=error_msg,
            payload_snapshot={"template": "missed_call_ack_v1"}
        )

    return {
        "success": sent_success,
        "wamid": res.get("wamid"),
        "message_log_id": res.get("message_log_id"),
        "lead_id": lead.id if lead else None,
        "phone": phone_formatted,
        "recipient_name": display_name,
        "error": error_msg
    }
