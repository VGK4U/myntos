"""
VGK Member Daily 8 AM Revenue Statement & Morning Wish Dispatch Service
Dispatches personalized executive revenue & stage file statements to all active VGK Channel Partners / Official Partners
who have AT LEAST 1 lead submitted.
Executed daily at 08:00 AM IST via APScheduler or triggered manually via WhatsApp Center (/staff/whatsapp-center).
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wa_execution_logs.json")


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
            "id": f"log_{datetime.now().strftime('%Y%m%d%H%M%S')}_{job_id}",
            "job_id": job_id,
            "job_name": job_name,
            "timestamp": datetime.now().isoformat(),
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


def run_vgk_member_daily_morning_statement_dispatch(db: Session, trigger_type: str = "SCHEDULED", triggered_by: str = "SYSTEM"):
    """
    Dispatches personalized revenue & pipeline statements to all active VGK members with >= 1 lead.
    """
    from app.api.v1.endpoints.vgk_cash_income import get_member_executive_summary
    from unittest.mock import MagicMock
    from app.services.automation_tracking_service import (
        create_execution,
        record_dispatch,
        finalize_execution,
        get_job_targets
    )

    logger.info("🌅 [VGK-MEMBER-STATEMENT] Starting daily 8 AM member revenue statement dispatch...")

    exec_rec = create_execution(
        db=db,
        job_id="vgk_member_morning_statement",
        job_name="VGK Members Daily 8 AM Revenue Statement",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        company_id=1
    )

    query = text("""
        SELECT p.id, p.partner_name, p.partner_code, p.phone, p.whatsapp_number, COUNT(c.id) AS lead_count
        FROM official_partners p
        JOIN crm_leads c ON (c.associated_partner_id = p.id OR c.primary_owner_id = p.id OR c.source_ref_id = CAST(p.id AS VARCHAR))
        WHERE p.is_active = TRUE
          AND (p.is_blocked IS FALSE OR p.is_blocked IS NULL)
        GROUP BY p.id, p.partner_name, p.partner_code, p.phone, p.whatsapp_number
        HAVING COUNT(c.id) >= 1
        ORDER BY p.id ASC
    """)
    qualifying_members = db.execute(query).fetchall()

    logger.info(f"📊 [VGK-MEMBER-STATEMENT] Found {len(qualifying_members)} qualifying members with >= 1 lead.")

    # Fetch numbers sent today for strict deduplication from message_log AND wa_inbox
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    start_of_today_utc = (ist_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=5, minutes=30))
    
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
        logger.warning(f"[VGK-STATEMENT] Dedup check warning: {e}")

    dispatched_count = 0
    skipped_count = 0
    failed_count = 0
    results = []

    for m in qualifying_members:
        p_id = m[0]
        p_name = m[1] or "Channel Partner"
        p_code = m[2] or f"VGK{p_id:06d}"
        phone = (m[3] or m[4] or "").strip()
        clean_phone = "".join(ch for ch in phone if ch.isdigit())

        if not clean_phone or len(clean_phone) < 10:
            logger.warning(f"⚠️ Member {p_name} ({p_code}) has no valid phone: {phone}")
            failed_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_rec.id,
                job_id="vgk_member_morning_statement",
                recipient_type="PARTNER",
                recipient_identifier=phone,
                recipient_name=p_name,
                target_entity_type="official_partners",
                target_entity_id=p_id,
                status="FAILED",
                error_message="Invalid phone format"
            )
            results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": "Invalid phone"})
            continue

        clean_10 = clean_phone[-10:]
        if trigger_type == "SCHEDULED" and clean_10 in sent_today_numbers:
            logger.info(f"⏩ Member {p_name} ({clean_10}) already received a message today. Skipping.")
            skipped_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_rec.id,
                job_id="vgk_member_morning_statement",
                recipient_type="PARTNER",
                recipient_identifier=clean_phone,
                recipient_name=p_name,
                target_entity_type="official_partners",
                target_entity_id=p_id,
                status="SKIPPED",
                error_message="Already sent today"
            )
            results.append({"member_id": p_id, "name": p_name, "status": "SKIPPED", "reason": "Already sent today"})
            continue

        # Mark as seen in this run to prevent duplicate dispatches if multiple partner records share the same phone
        sent_today_numbers.add(clean_10)

        try:
            summary = get_member_executive_summary(partner_id=str(p_id), db=db, current_employee=MagicMock())
            b = summary.get("financial_buckets", {})
            f = summary.get("files_summary", {})
            st_lbl = summary.get("payout_status_label", "🟢 Eligible for Payout Disbursal")
            desig = summary.get("designation", "Channel Partner")
            from app.services.wa_template_storage_service import get_job_template
            tpl_str = get_job_template("vgk_member_morning_statement")

            msg_text = tpl_str.format(
                member_name=p_name,
                user_code=p_code,
                phone=phone,
                designation=desig,
                payout_status_label=st_lbl,
                overall_gross_earned=f"{int(b.get('overall_gross_earned', 0)):,}",
                earned_till_date_net=f"{int(b.get('earned_till_date_net', 0)):,}",
                potential_earnings=f"{int(b.get('potential_earnings', 0)):,}",
                bonus_extra_value=f"{int(b.get('bonus_extra_value', 0)):,}",
                active_files_advance_paid=f"{int(b.get('active_files_advance_paid', 0)):,}",
                gross_pending=f"{int(b.get('gross_pending', 0)):,}",
                lost_lead_adv_deducted_pending=f"{int(b.get('lost_lead_adv_deducted_pending', 0) or b.get('total_lost_adv_deducted', 0)):,}",
                net_pending=f"{int(b.get('net_pending', 0)):,}",
                total_files=f.get('total_files', 0),
                stage1_files=f.get('stage1_files', 0),
                stage1_total_adv=f"{int(f.get('stage1_total_adv', 0)):,}",
                stage2_files=f.get('stage2_files', 0),
                stage2_total_adv=f"{int(f.get('stage2_total_adv', 0)):,}",
                stage3_completed_files=f.get('stage3_completed_files', 0),
                stage3_total_comm=f"{int(f.get('stage3_total_comm', 0)):,}",
                bonus_entries_count=f.get('bonus_entries_count', 0),
                bonus_total_amt=f"{int(f.get('bonus_total_amt', 0)):,}"
            )

            from app.services.whatsapp_canonical_service import WhatsAppCanonicalService
            from app.core.timezone import get_indian_time
            catalog_link = "https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te"
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p_name or "Partner")},
                        {"type": "text", "text": f"{int(b.get('overall_gross_earned', 0)):,}"},
                        {"type": "text", "text": f"{int(b.get('earned_till_date_net', 0)):,}"},
                        {"type": "text", "text": f"{int(b.get('net_pending', 0)):,}"},
                        {"type": "text", "text": catalog_link}
                    ]
                }
            ]

            wa_res = WhatsAppCanonicalService.send_meta_template_message(
                db=db,
                phone=clean_phone,
                template_name="vgk_partner_morning_statement_v1",
                language_code="en",
                components=components,
                user_name=p_name,
                sender_type="bot",
                idempotency_key=f"morning_statement:{clean_phone}:{get_indian_time().strftime('%Y%m%d')}",
                raw_body_fallback=msg_text,
                job_id="vgk_member_morning_statement",
                execution_id=exec_rec.id
            )

            if wa_res.get("success"):
                dispatched_count += 1
                record_dispatch(
                    db=db,
                    execution_id=exec_rec.id,
                    job_id="vgk_member_morning_statement",
                    recipient_type="PARTNER",
                    recipient_identifier=clean_phone,
                    recipient_name=p_name,
                    target_entity_type="official_partners",
                    target_entity_id=p_id,
                    message_log_id=wa_res.get("message_log_id"),
                    provider_message_id=wa_res.get("message_sid"),
                    status="SENT",
                    payload_snapshot={"member_code": p_code}
                )
                results.append({"member_id": p_id, "name": p_name, "status": "SUCCESS", "phone": clean_phone})
            else:
                failed_count += 1
                err_text = wa_res.get("error") or wa_res.get("reason") or "Dispatch failed"
                record_dispatch(
                    db=db,
                    execution_id=exec_rec.id,
                    job_id="vgk_member_morning_statement",
                    recipient_type="PARTNER",
                    recipient_identifier=clean_phone,
                    recipient_name=p_name,
                    target_entity_type="official_partners",
                    target_entity_id=p_id,
                    status="FAILED",
                    error_message=err_text
                )
                results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": err_text})

        except Exception as exc:
            logger.error(f"❌ Error dispatching morning statement to {p_name}: {exc}")
            failed_count += 1
            record_dispatch(
                db=db,
                execution_id=exec_rec.id,
                job_id="vgk_member_morning_statement",
                recipient_type="PARTNER",
                recipient_identifier=clean_phone,
                recipient_name=p_name,
                target_entity_type="official_partners",
                target_entity_id=p_id,
                status="FAILED",
                error_message=str(exc)
            )
            results.append({"member_id": p_id, "name": p_name, "status": "FAILED", "error": str(exc)})

    # Supplementary targets if any configured
    supp_targets = get_job_targets(db, "vgk_member_morning_statement", company_id=1)
    for tgt in supp_targets:
        if not tgt.get("is_active", True):
            continue
        tgt_phone = tgt.get("recipient_identifier")
        if not tgt_phone:
            continue
        from app.services.whatsapp_auto_service import send_direct_whatsapp
        cc_res = send_direct_whatsapp(
            db=db,
            phone=tgt_phone,
            message=f"📊 [CC Notification] Morning Statement dispatch finished for {dispatched_count} active partners.",
            job_id="vgk_member_morning_statement",
            execution_id=exec_rec.id
        )
        cc_ok = cc_res.get("success", False)
        record_dispatch(
            db=db,
            execution_id=exec_rec.id,
            job_id="vgk_member_morning_statement",
            recipient_type=tgt.get("recipient_type", "PHONE_NUMBER"),
            recipient_identifier=tgt_phone,
            recipient_name=tgt.get("recipient_name", "CC Target"),
            message_log_id=cc_res.get("message_log_id"),
            provider_message_id=cc_res.get("message_sid"),
            status="SENT" if cc_ok else "FAILED",
            error_message=cc_res.get("error") if not cc_ok else None,
            payload_snapshot={"is_cc": True}
        )

    exec_status = "COMPLETED" if (failed_count == 0 and (dispatched_count > 0 or len(qualifying_members) == 0)) else ("PARTIAL" if dispatched_count > 0 else "FAILED")
    finalize_execution(db, exec_rec.id, exec_status)

    payload = {
        "qualifying_members_count": len(qualifying_members),
        "dispatched_count": dispatched_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "detail": results
    }

    if failed_count > 0 and dispatched_count == 0 and len(qualifying_members) > skipped_count:
        status = "FAILED"
    elif dispatched_count == 0 and skipped_count > 0:
        status = "SKIPPED"
    else:
        status = "SUCCESS"

    _record_audit_log(
        job_id="vgk_member_morning_statement",
        job_name="VGK Members Daily 8 AM Revenue Statement",
        payload=payload,
        triggered_by=triggered_by,
        status=status
    )

    return {
        "success": True,
        "job_id": "vgk_member_morning_statement",
        "qualifying_members_count": len(qualifying_members),
        "dispatched_count": dispatched_count,
        "failed_count": failed_count,
        "results": results
    }
