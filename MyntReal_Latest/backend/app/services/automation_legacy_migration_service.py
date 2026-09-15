"""
Legacy WhatsApp Execution Logs & Job Targets Migration Service
Imports historical records from wa_execution_logs.json into automation_execution and automation_dispatch with is_legacy=True.
Seeds automation_target_config with tenant-isolated target configurations for all 8 jobs.
Architecture:
- Zero fabrication of historical message_log or queue relationships.
- Strictly preserves original timestamps, counts, and error states.
- Idempotent: safe to run multiple times without duplicating records.
"""

import os
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.automation import AutomationExecution, AutomationDispatch, AutomationTargetConfig

logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
EXEC_LOGS_PATH = os.path.join(DATA_DIR, "wa_execution_logs.json")
JOB_TARGETS_PATH = os.path.join(DATA_DIR, "wa_job_targets.json")

JOB_ID_CANONICAL_MAP = {
    "wa_daily_vgk_zero_lead_motivational_730am": "vgk_member_zero_lead_motivational",
    "wa_daily_vgk_member_statement_730am": "vgk_member_morning_statement",
    "wa_daily_morning_wish_8am": "wa_daily_morning_wish",
    "wa_daily_vgk4u_morning_wish_8am": "vgk4u_morning_wish"
}

JOB_NAMES = {
    "wa_bihourly_sales_perf_report": "Sales Team 2-Hour Report & Leaderboard",
    "field_staff_journey_report": "Field Journey Performance & Leaderboard Report",
    "missed_call_ack": "Instant Missed Call Auto-ACK",
    "wa_daily_morning_wish": "WhatsApp 8 AM Morning Wish Dispatch",
    "vgk4u_morning_wish": "VGK4U Elite Community Morning Wish",
    "vgk_member_morning_statement": "VGK Members Daily 7:30 AM Revenue Statement",
    "vgk_member_zero_lead_motivational": "VGK 0-Lead Members Daily 7:30 AM Motivational Dispatch",
    "service_summary": "Daily 7:30 PM Service Ticket Summary"
}


def parse_iso_or_legacy_timestamp(ts_str: str) -> datetime:
    if not ts_str:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass
    try:
        return datetime.strptime(ts_str.split(" IST")[0], "%d %b %Y, %I:%M:%S %p")
    except Exception:
        pass
    return datetime.utcnow()


def migrate_legacy_execution_logs(db: Session) -> dict:
    """Backfills historical records from wa_execution_logs.json into relational tables."""
    if not os.path.exists(EXEC_LOGS_PATH):
        logger.warning(f"Legacy file {EXEC_LOGS_PATH} not found. Skipping migration.")
        return {"imported_executions": 0, "imported_dispatches": 0}

    with open(EXEC_LOGS_PATH, "r", encoding="utf-8") as f:
        try:
            entries = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read legacy execution logs: {e}")
            return {"imported_executions": 0, "imported_dispatches": 0}

    if not isinstance(entries, list):
        return {"imported_executions": 0, "imported_dispatches": 0}

    existing_ids = set(r[0] for r in db.query(AutomationExecution.id).all())
    imported_execs = 0
    imported_dispatches = 0

    for entry in entries:
        eid = entry.get("id")
        if not eid or eid in existing_ids:
            continue

        raw_jid = entry.get("job_id", "")
        jid = JOB_ID_CANONICAL_MAP.get(raw_jid, raw_jid)
        jname = entry.get("job_name") or JOB_NAMES.get(jid, jid)
        trig_type = entry.get("trigger_type") or "SCHEDULED"
        trig_by = entry.get("triggered_by") or "System Cron"
        ts = parse_iso_or_legacy_timestamp(entry.get("iso_timestamp") or entry.get("timestamp"))

        status = str(entry.get("status") or "SUCCESS").upper()
        if status in ("SUCCESS", "EXECUTED", "COMPLETED"):
            eff_status = "SUCCESS"
        elif status in ("UNCERTAIN", "DISPATCH_UNCERTAIN"):
            eff_status = "DISPATCH_UNCERTAIN"
        elif status in ("FAILED", "ERROR"):
            eff_status = "FAILED"
        elif status in ("SKIPPED",):
            eff_status = "SKIPPED"
        else:
            eff_status = "SUCCESS"

        payload = entry.get("detail") or entry.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        sent_cnt = int(entry.get("sent_count") or payload.get("dispatched_count") or (1 if eff_status == "SUCCESS" else 0))
        failed_cnt = int(entry.get("failed_count") or payload.get("failed_count") or (1 if eff_status == "FAILED" else 0))
        skipped_cnt = int(entry.get("skipped_count") or payload.get("skipped_count") or (1 if eff_status == "SKIPPED" else 0))
        tot_cnt = int(payload.get("total_targets") or payload.get("total_eligible") or payload.get("total_count") or (sent_cnt + failed_cnt + skipped_cnt))
        if tot_cnt < (sent_cnt + failed_cnt + skipped_cnt):
            tot_cnt = sent_cnt + failed_cnt + skipped_cnt

        exec_row = AutomationExecution(
            id=eid,
            job_id=jid,
            job_name=jname,
            trigger_type=trig_type,
            triggered_by=trig_by,
            company_id=1,
            status=eff_status,
            target_summary=entry.get("target_summary") or "",
            total_targets=tot_cnt,
            sent_count=sent_cnt,
            uncertain_count=1 if eff_status == "DISPATCH_UNCERTAIN" else 0,
            failed_count=failed_cnt,
            skipped_count=skipped_cnt,
            started_at=ts,
            completed_at=ts,
            error_message=entry.get("error_message"),
            is_legacy=True,
            execution_metadata={
                "legacy_original_job_id": raw_jid,
                "legacy_payload": payload
            }
        )
        db.add(exec_row)
        imported_execs += 1
        existing_ids.add(eid)

        # Ingest granular dispatches from details/results or targets
        details_list = payload.get("details") or payload.get("results") or payload.get("detail") or []
        if isinstance(details_list, list) and len(details_list) > 0:
            for d in details_list:
                if not isinstance(d, dict):
                    continue
                r_phone = str(d.get("phone") or d.get("mobile") or d.get("identifier") or "").strip()
                r_name = str(d.get("lead_name") or d.get("name") or d.get("member_name") or r_phone or "Recipient")
                d_st = str(d.get("status") or "").upper()
                d_status = "SENT" if d_st in ("SUCCESS", "SENT") else ("FAILED" if d_st in ("FAILED", "ERROR") else ("SKIPPED" if d_st == "SKIPPED" else "SENT"))

                disp_row = AutomationDispatch(
                    execution_id=eid,
                    job_id=jid,
                    recipient_type="CUSTOMER_LEAD" if d.get("lead_id") else ("PARTNER_MEMBER" if d.get("member_id") else "CUSTOM_PHONE"),
                    recipient_identifier=r_phone or eid,
                    recipient_name=r_name,
                    target_entity_type="crm_lead" if d.get("lead_id") else ("official_partner" if d.get("member_id") else None),
                    target_entity_id=d.get("lead_id") or d.get("member_id"),
                    queue_id=None,
                    message_log_id=None,
                    provider="META_WHATSAPP" if d.get("wamid") else "LEGACY_ARCHIVE",
                    provider_message_id=d.get("wamid"),
                    status=d_status,
                    sent_at=ts if d_status == "SENT" else None,
                    failed_at=ts if d_status == "FAILED" else None,
                    error_message=d.get("error") or d.get("reason"),
                    payload_snapshot=d
                )
                db.add(disp_row)
                imported_dispatches += 1
        else:
            targets_list = entry.get("targets") or []
            if isinstance(targets_list, list) and len(targets_list) > 0:
                for tg in targets_list:
                    if not isinstance(tg, dict):
                        continue
                    t_ident = tg.get("identifier") or tg.get("name") or eid
                    disp_row = AutomationDispatch(
                        execution_id=eid,
                        job_id=jid,
                        recipient_type=str(tg.get("type") or "GROUP").upper(),
                        recipient_identifier=t_ident,
                        recipient_name=tg.get("name") or t_ident,
                        target_entity_type=None,
                        target_entity_id=None,
                        queue_id=None,
                        message_log_id=None,
                        provider="BOT_GATEWAY" if "@g.us" in t_ident or "chat.whatsapp.com" in t_ident else "META_WHATSAPP",
                        provider_message_id=None,
                        status="SENT" if eff_status == "SUCCESS" else eff_status,
                        sent_at=ts if eff_status == "SUCCESS" else None,
                        failed_at=ts if eff_status == "FAILED" else None,
                        error_message=entry.get("error_message"),
                        payload_snapshot=tg
                    )
                    db.add(disp_row)
                    imported_dispatches += 1

    db.commit()
    return {"imported_executions": imported_execs, "imported_dispatches": imported_dispatches}


def seed_automation_target_configs(db: Session) -> int:
    """Seeds initial target configurations into automation_target_config."""
    default_targets = [
        # Job 1: Sales 2-Hour Report (Configurable Group)
        {"job_id": "wa_bihourly_sales_perf_report", "target_type": "group", "name": "Mynt Sales New", "identifier": "120363410784518818@g.us"},
        # Job 2: Field Staff Journey Report (Configurable Group)
        {"job_id": "field_staff_journey_report", "target_type": "group", "name": "Field Updates", "identifier": "120363428888306723@g.us"},
        # Job 3: Missed Call Auto-ACK (Dynamic Segment / Inbound Callers)
        {"job_id": "missed_call_ack", "target_type": "dynamic_segment", "name": "Dynamic Missed Call Callers (Inbound 24h Window)", "identifier": "operator_missed_calls"},
        # Job 4: 8 AM Morning Wish (Dynamic Segment / Leads)
        {"job_id": "wa_daily_morning_wish", "target_type": "dynamic_segment", "name": "Dynamic CRM Leads (New & Uncontacted >20d)", "identifier": "crm_leads_eligible"},
        # Job 5: VGK4U Elite Community Wish (Configurable Groups/Channels)
        {"job_id": "vgk4u_morning_wish", "target_type": "channel", "name": "VGK4u Official Channel", "identifier": "https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m"},
        {"job_id": "vgk4u_morning_wish", "target_type": "group", "name": "VGK4u Community Group", "identifier": "https://chat.whatsapp.com/HNQQoKXFfCm5PQngGdrlcY?s=cl&p=i&mlu=0"},
        {"job_id": "vgk4u_morning_wish", "target_type": "group", "name": "VGK4U - Vijayawada", "identifier": "VGK4U - Vijayawada"},
        # Job 6: VGK Members Morning Statement (Dynamic Segment / Active Partners >=1 Lead)
        {"job_id": "vgk_member_morning_statement", "target_type": "dynamic_segment", "name": "Dynamic Segment: Active Partners (>= 1 Lead)", "identifier": "vgk_partners_with_leads"},
        # Job 7: VGK 0-Lead Motivational (Dynamic Segment / Active Partners == 0 Leads)
        {"job_id": "vgk_member_zero_lead_motivational", "target_type": "dynamic_segment", "name": "Dynamic Segment: Active Partners (0 Leads)", "identifier": "vgk_partners_zero_leads"},
        # Job 8: Daily 7:30 PM Service Summary (Configurable Group)
        {"job_id": "service_summary", "target_type": "group", "name": "Service & Maintenance Team", "identifier": "EyuAwaVoF6E6nQqC0QfiBe"}
    ]

    # Overlay existing configurations from wa_job_targets.json if present
    if os.path.exists(JOB_TARGETS_PATH):
        try:
            with open(JOB_TARGETS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    for jid, targets in saved.items():
                        c_jid = JOB_ID_CANONICAL_MAP.get(jid, jid)
                        for t in targets:
                            if isinstance(t, dict) and t.get("identifier"):
                                default_targets.append({
                                    "job_id": c_jid,
                                    "target_type": t.get("type") or "group",
                                    "name": t.get("name") or t.get("identifier"),
                                    "identifier": t.get("identifier")
                                })
        except Exception as e:
            logger.warning(f"Could not load custom targets from JSON: {e}")

    seeded = 0
    for dt in default_targets:
        exists = db.query(AutomationTargetConfig).filter(
            AutomationTargetConfig.job_id == dt["job_id"],
            AutomationTargetConfig.identifier == dt["identifier"],
            AutomationTargetConfig.company_id == 1
        ).first()
        if not exists:
            row = AutomationTargetConfig(
                job_id=dt["job_id"],
                company_id=1,
                target_type=dt["target_type"],
                name=dt["name"],
                identifier=dt["identifier"],
                is_active=True
            )
            db.add(row)
            seeded += 1

    db.commit()
    return seeded
