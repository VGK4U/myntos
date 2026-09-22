"""
DC_SALES_PERF_REPORT_001 — Bi-Hourly Sales Performance Report & Leaderboard Generator
Generates bi-hourly updates (9:30 AM - 7:30 PM IST) with comparison against previous updates.
"""

import os
import re
import json
import logging
import datetime
import pytz
from datetime import timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

logger = logging.getLogger(__name__)

SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "sales_perf_snapshots.json")


def _get_ist_now() -> datetime.datetime:
    """Returns current naive datetime in Asia/Kolkata (IST)."""
    return datetime.datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)


def _clean_name_tokens(name_str: str) -> List[str]:
    """Extracts lowercase tokens of at least 3 chars excluding common titles/stopwords for precise matching."""
    if not name_str:
        return []
    words = re.sub(r'[^a-zA-Z0-9\s]', ' ', name_str).lower().split()
    return [w for w in words if len(w) >= 3 and w not in ('mrs', 'mr', 'ms', 'dr', 'agent', 'team', 'vgk', 'supreme')]


def _format_seconds_to_hhmmss(total_seconds: int) -> str:
    total_seconds = int(total_seconds or 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"


def _format_seconds_to_hm(total_seconds: int) -> str:
    total_seconds = int(total_seconds or 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes}m"


def _format_seconds_to_smart_time(total_seconds: int) -> str:
    total_seconds = int(total_seconds or 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {seconds:02d}s" if seconds > 0 else f"{minutes}m"
    if seconds > 0:
        return f"{seconds}s"
    return "00m"


def get_today_sales_performance_stats(db: Session, start_date=None, end_date=None, period_label="Today") -> Dict[str, Any]:
    """
    Aggregates sales performance statistics for a date range or today.
    """
    from sqlalchemy import text
    from app.models.crm import CRMLead

    # IST Today Range
    ist_now = _get_ist_now()
    if not end_date:
        end_date = ist_now.date()
    if not start_date:
        start_date = ist_now.date()

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # Authoritative IST bounds: PostgreSQL columns (voip_call_sessions.created_at, operator_calls.started_at,
    # crm_leads.created_at) store naive datetimes in IST (Asia/Kolkata).
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)

    if start_date == end_date:
        if start_date == ist_now.date():
            date_display = ist_now.strftime("%d %B %Y")
        else:
            date_display = start_date.strftime("%d %B %Y")
    else:
        date_display = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"

    from app.models.operator_calls import OperatorCall
    from app.models.voip_call_session import VoIPCallSession

    # 1. Tele Sales / Telecaller Department Staff (Authoritative database attributes, strictly excluding Freelancers & Service/Non-caller staff)
    staff_rows = db.execute(text("""
        SELECT e.id, e.full_name, e.emp_code
        FROM staff_employees e
        LEFT JOIN staff_departments d ON d.id = e.department_id
        LEFT JOIN staff_employee_departments ed ON ed.employee_id = e.id
        LEFT JOIN staff_departments ad ON ad.id = ed.department_id
        LEFT JOIN staff_roles r ON r.id = e.role_id
        LEFT JOIN staff_employees mgr ON mgr.id = e.reporting_manager_id
        LEFT JOIN staff_departments mgr_d ON mgr_d.id = mgr.department_id
        WHERE (
            LOWER(d.name) = 'tele sales'
            OR LOWER(ad.name) = 'tele sales'
            OR (LOWER(d.name) = 'sales' AND (
                LOWER(mgr_d.name) = 'tele sales'
                OR EXISTS (SELECT 1 FROM voip_call_sessions v WHERE v.operator_id = e.id)
                OR EXISTS (SELECT 1 FROM staff_call_logs cl WHERE cl.staff_id = e.id)
            ))
            OR LOWER(COALESCE(r.role_code, '')) LIKE '%tele%'
            OR LOWER(COALESCE(r.role_name, '')) LIKE '%tele%'
          )
          AND (e.status IS NULL OR e.status = 'active')
          AND (e.is_deleted IS NOT TRUE)
          AND e.full_name IS NOT NULL
          AND e.full_name != ''
          AND e.emp_code NOT ILIKE 'FL%'
          AND e.emp_code NOT ILIKE 'FP%'
          AND LOWER(COALESCE(e.employment_type, '')) NOT IN ('freelancer', 'external', 'partner_freelancer', 'contractor_freelancer', 'partner')
          AND LOWER(COALESCE(r.role_code, '')) NOT LIKE '%freelancer%'
          AND LOWER(COALESCE(r.role_name, '')) NOT LIKE '%freelancer%'
          AND COALESCE(e.staff_type, '') != 'FREELANCER'
        GROUP BY e.id, e.full_name, e.emp_code
    """)).fetchall()

    # Pre-fetch pure Cloud Operator Calls (MyOperator virtual numbers)
    # Strictly exclude softphone/WebRTC mirrors (call_id prefixed with plivo_, webrtc_, mock_, vcs_)
    pure_op_calls = db.query(OperatorCall).filter(
        OperatorCall.started_at >= start_dt,
        OperatorCall.started_at <= end_dt,
        ~OperatorCall.call_id.like('plivo_%'),
        ~OperatorCall.call_id.like('webrtc_%'),
        ~OperatorCall.call_id.like('mock_%'),
        ~OperatorCall.call_id.like('vcs_%')
    ).all()

    # Pre-fetch Browser Softphone (VoIP / Plivo / WebRTC in-app calls)
    day_voip_calls = db.query(VoIPCallSession).filter(
        VoIPCallSession.created_at >= start_dt,
        VoIPCallSession.created_at <= end_dt
    ).all()

    leaderboard = []
    total_calls = 0
    total_talk_seconds = 0
    missed_calls = 0

    for s in staff_rows:
        # Mobile call logs (Call Tracker App)
        m_row = db.execute(text("""
            SELECT COUNT(id) as cnt, COALESCE(SUM(duration_seconds), 0) as dur,
                   COUNT(CASE WHEN UPPER(call_type) IN ('MISSED', 'REJECTED', 'NO_ANSWER') THEN 1 END) as missed
            FROM staff_call_logs 
            WHERE staff_id = :sid 
              AND call_date >= :sd 
              AND call_date <= :ed
              AND (source IS NULL OR LOWER(source) NOT IN ('softphone', 'plivo', 'voip'))
              AND (matched_lead_id IS NOT NULL OR LOWER(COALESCE(source, '')) IN ('dialer', 'autodialer') OR device_call_id LIKE 'vcs_%' OR device_call_id LIKE 'dialer_%')
        """), {"sid": s.id, "sd": start_date_str, "ed": end_date_str}).fetchone()

        m_cnt = m_row.cnt if m_row else 0
        m_dur = int(m_row.dur or 0) if m_row else 0
        m_missed = m_row.missed if m_row else 0

        # Operator Cloud Calls (MyOperator virtual numbers) with disambiguated staff name matching
        s_tokens = set(_clean_name_tokens(s.full_name))
        staff_op_calls = []
        for opc in pure_op_calls:
            hb = opc.handled_by or ''
            hb_tokens = _clean_name_tokens(hb)
            if hb_tokens and all(w in s_tokens for w in hb_tokens):
                staff_op_calls.append(opc)

        op_cnt = len(staff_op_calls)
        op_dur = sum(c.duration_seconds or 0 for c in staff_op_calls if c.status == 'answered')
        op_missed = sum(1 for c in staff_op_calls if c.status == 'missed')

        # 3. Browser Softphone (VoIP / Plivo / WebRTC in-app calls)
        staff_voip_calls = []
        for vc in day_voip_calls:
            if vc.operator_id == s.id:
                staff_voip_calls.append(vc)
            elif not vc.operator_id and vc.operator_name:
                vc_tokens = _clean_name_tokens(vc.operator_name)
                if vc_tokens and all(w in s_tokens for w in vc_tokens):
                    staff_voip_calls.append(vc)

        v_cnt = len(staff_voip_calls)
        v_dur = sum(v.duration_seconds or 0 for v in staff_voip_calls if (v.duration_seconds or 0) > 0)
        v_missed = sum(1 for v in staff_voip_calls if (v.duration_seconds or 0) == 0 and v.status in ('no_answer', 'failed', 'busy', 'cancelled', 'ended', 'dialing', 'rejected', 'missed'))

        staff_tot_calls = m_cnt + op_cnt + v_cnt
        staff_tot_talk = m_dur + op_dur + v_dur
        staff_tot_missed = m_missed + op_missed + v_missed

        total_calls += staff_tot_calls
        total_talk_seconds += staff_tot_talk
        missed_calls += staff_tot_missed

        leaderboard.append({
            "handled_by": s.full_name,
            "call_count": staff_tot_calls,
            "missed_count": staff_tot_missed,
            "talk_seconds": staff_tot_talk,
            "talk_time_formatted": _format_seconds_to_hm(staff_tot_talk),
            "sim_call_count": m_cnt,
            "sim_talk_seconds": m_dur,
            "operator_call_count": op_cnt,
            "operator_talk_seconds": op_dur,
            "softphone_call_count": v_cnt,
            "softphone_talk_seconds": v_dur,
            "softphone_talk_formatted": _format_seconds_to_smart_time(v_dur),
            "softphone_missed_count": v_missed
        })

    leaderboard.sort(key=lambda x: (x["talk_seconds"], x["call_count"]), reverse=True)

    # 3. New Leads Intake
    new_leads = db.query(func.count(CRMLead.id)).filter(
        CRMLead.created_at >= start_dt,
        CRMLead.created_at <= end_dt
    ).scalar() or 0


    return {
        "timestamp_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "date_str": ist_now.strftime("%d %B %Y"),
        "time_str": ist_now.strftime("%I:%M %p"),
        "total_calls": total_calls,
        "total_talk_seconds": int(total_talk_seconds),
        "total_talk_formatted": _format_seconds_to_hhmmss(total_talk_seconds),
        "missed_calls": missed_calls,
        "new_leads": new_leads,
        "leaderboard": leaderboard
    }


def _load_previous_snapshot(date_key: str) -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(SNAPSHOT_FILE):
            with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(date_key)
    except Exception as exc:
        logger.warning(f"Could not read snapshot file: {exc}")
    return None


def _save_current_snapshot(date_key: str, stats: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        data = {}
        if os.path.exists(SNAPSHOT_FILE):
            with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        data[date_key] = stats
        with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.warning(f"Could not save snapshot file: {exc}")


def generate_bi_hourly_performance_message(db: Session, slot_name: str = "Bi-Hourly Update") -> str:
    """
    Generates formatted bi-hourly update message with previous update comparison.
    """
    current_stats = get_today_sales_performance_stats(db)

    ist_now = _get_ist_now()
    date_key = ist_now.strftime("%Y-%m-%d")
    previous_stats = _load_previous_snapshot(date_key)

    # Calculate Deltas
    prev_calls = previous_stats.get("total_calls", 0) if previous_stats else 0
    prev_talk = previous_stats.get("total_talk_seconds", 0) if previous_stats else 0
    prev_missed = previous_stats.get("missed_calls", 0) if previous_stats else 0
    prev_leads = previous_stats.get("new_leads", 0) if previous_stats else 0

    delta_calls = current_stats["total_calls"] - prev_calls
    delta_talk_sec = current_stats["total_talk_seconds"] - prev_talk
    delta_missed = current_stats["missed_calls"] - prev_missed
    delta_leads = current_stats["new_leads"] - prev_leads

    # Save current stats as baseline for next 2-hour comparison
    _save_current_snapshot(date_key, current_stats)

    delta_calls_str = f" *(📈 +{delta_calls} since last update)*" if previous_stats and delta_calls >= 0 else ""
    delta_talk_str = f" *(📈 +{_format_seconds_to_hm(delta_talk_sec)} since last update)*" if previous_stats and delta_talk_sec > 0 else ""
    delta_missed_str = f" *(+{delta_missed} since last update)*" if previous_stats and delta_missed > 0 else ""
    delta_leads_str = f" *(📈 +{delta_leads} since last update)*" if previous_stats and delta_leads >= 0 else ""

    # Build per-staff previous talk time map for deltas
    prev_staff_map = {}
    if previous_stats and isinstance(previous_stats.get("leaderboard"), list):
        for p_item in previous_stats["leaderboard"]:
            prev_staff_map[p_item.get("handled_by")] = p_item.get("talk_seconds", 0)

    # Build Tele Sales Leaderboard & Team Member List
    lb = current_stats["leaderboard"]
    medals = ["🥇", "🥈", "🥉"]
    lb_text_lines = []
    
    active_staff = [item for item in lb if item['call_count'] > 0]
    idle_staff = [item for item in lb if item['call_count'] == 0]

    for idx, item in enumerate(active_staff):
        medal = medals[idx] if idx < 3 else "🏅"
        staff_name = item['handled_by']
        prev_talk_sec = prev_staff_map.get(staff_name)
        staff_delta_str = ""
        if previous_stats and prev_talk_sec is not None:
            s_diff = item['talk_seconds'] - prev_talk_sec
            if s_diff >= 0:
                staff_delta_str = f" *(📈 +{_format_seconds_to_hm(s_diff)} since last update)*"

        missed_str = f" *(🔴 {item['missed_count']} Missed)*" if item.get('missed_count', 0) > 0 else ""
        
        # Multi-medium breakdown for transparent reporting across all mediums
        medium_parts = []
        if item.get('softphone_call_count', 0) > 0:
            medium_parts.append(f"💻 Softphone: {item['softphone_call_count']} Calls · {item['softphone_talk_formatted']}")
        if item.get('sim_call_count', 0) > 0:
            medium_parts.append(f"📱 SIM: {item['sim_call_count']} Calls · {_format_seconds_to_smart_time(item.get('sim_talk_seconds', 0))}")
        if item.get('operator_call_count', 0) > 0:
            medium_parts.append(f"☁️ Operator: {item['operator_call_count']} Calls · {_format_seconds_to_smart_time(item.get('operator_talk_seconds', 0))}")

        breakdown_str = f" *({' | '.join(medium_parts)})*" if medium_parts else ""

        lb_text_lines.append(f"{idx+1}. {medal} *{staff_name}* — {item['call_count']} Calls{missed_str} | {item['talk_time_formatted']} Talk Time{breakdown_str}{staff_delta_str}")

    if not active_staff:
        lb_text_lines.append("*(No staff calls recorded yet today)*")

    if idle_staff:
        lb_text_lines.append("\n📋 *TELE SALES TEAM MEMBERS (0 Calls Today)*:")
        for item in idle_staff:
            lb_text_lines.append(f"• *{item['handled_by']}* — 0 Calls | 00m Talk Time")

    lb_formatted = "\n".join(lb_text_lines)

    # DC-SOLAR-PEOPLE-001: Build SOLAR PEOPLE section for bi-hourly update
    solar_section = format_solar_people_section(db)

    is_evening_closing = "07:30" in slot_name or "Closing" in slot_name or ist_now.hour >= 19
    header_title = "📊 *DAILY SALES FINAL CLOSING REPORT*" if is_evening_closing else f"📊 *SALES TEAM 2-HOUR UPDATE ({current_stats['time_str']})*"

    msg = (
        f"{header_title}\n"
        f"📅 *Date*: {current_stats['date_str']}\n\n"
        f"🏆 *STAFF LEADERBOARD TODAY*:\n"
        f"{lb_formatted}\n\n"
        f"{solar_section}\n\n"
        f"{'Great effort today team! Have a peaceful evening! 🌙' if is_evening_closing else 'Keep up the strong momentum team! Next update in 2 hours! 🚀'}"
    )

    return msg


def get_today_solar_people_stats(db: Session, target_date=None) -> Dict[str, Any]:
    """
    DC-SOLAR-PEOPLE-001: Aggregates today's Solar Application KRA activity.
    Queries active and completed Solar Application Work Intervals & Instances for today.
    """
    from sqlalchemy import text
    from app.models.staff import StaffEmployee
    from app.models.crm import CRMLead
    from app.models.staff_work_interval import StaffWorkInterval
    from app.models.staff_kra import StaffKRADailyInstance, StaffKRATemplate

    ist_now = _get_ist_now()
    if not target_date:
        target_date = ist_now.date()

    target_date_str = target_date.strftime("%Y-%m-%d")

    # Fetch Solar KRA template IDs
    solar_tpl_rows = db.execute(text("""
        SELECT id FROM staff_kra_templates
        WHERE kra_code = 'KRA-SOLAR-APP'
           OR LOWER(title) LIKE '%solar application%'
           OR LOWER(title) LIKE '%solar%'
    """)).fetchall()

    solar_tpl_ids = [t[0] for t in solar_tpl_rows] if solar_tpl_rows else [-1]

    # Query all work_intervals for today linked to Solar KRA or lead_id
    intervals = db.execute(text("""
        SELECT 
            wi.id, wi.employee_id, wi.kra_entry_id, wi.lead_id,
            wi.interval_start, wi.interval_end, wi.duration_minutes, wi.status,
            e.full_name as staff_name, e.emp_code,
            l.name as lead_name, l.phone as lead_phone, l.application_no, l.status as lead_status
        FROM staff_work_intervals wi
        JOIN staff_employees e ON e.id = wi.employee_id
        LEFT JOIN staff_kra_daily_instances ki ON ki.id = wi.kra_entry_id
        LEFT JOIN crm_leads l ON l.id = COALESCE(wi.lead_id, ki.lead_id)
        WHERE DATE(wi.interval_start AT TIME ZONE 'Asia/Kolkata') = :tdate
          AND (
            ki.kra_template_id IN :tpl_ids 
            OR wi.activity_type = 'solar'
            OR LOWER(COALESCE(wi.activity_title, '')) LIKE '%solar%'
            OR wi.lead_id IS NOT NULL
          )
        ORDER BY e.full_name, wi.interval_start ASC
    """), {"tdate": target_date_str, "tpl_ids": tuple(solar_tpl_ids)}).fetchall()

    if not intervals:
        return {"has_activity": False, "employee_groups": [], "overall_total_seconds": 0}

    # Aggregate by employee
    emp_map = {}
    overall_total_sec = 0

    for row in intervals:
        emp_id = row.employee_id
        staff_name = (row.staff_name or "").strip() or row.emp_code or f"Staff #{row.employee_id}"
        if emp_id not in emp_map:
            emp_map[emp_id] = {
                "staff_name": staff_name,
                "emp_code": row.emp_code,
                "total_seconds": 0,
                "items": []
            }

        # Determine interval duration
        if row.interval_end:
            sec = max(0, int((row.interval_end - row.interval_start).total_seconds()))
            is_active = False
        else:
            # Active interval — calculate live elapsed time
            start_dt = row.interval_start
            if not start_dt.tzinfo:
                start_dt = pytz.timezone('Asia/Kolkata').localize(start_dt)
            sec = max(0, int((pytz.timezone('Asia/Kolkata').localize(ist_now) - start_dt).total_seconds()))
            is_active = True

        emp_map[emp_id]["total_seconds"] += sec
        overall_total_sec += sec

        lead_label = row.lead_name or (f"Application #{row.application_no}" if row.application_no else (f"Lead #{row.lead_id}" if row.lead_id else "Solar Application"))
        
        emp_map[emp_id]["items"].append({
            "lead_name": lead_label,
            "duration_seconds": sec,
            "duration_formatted": _format_seconds_to_hm(sec),
            "status": "ACTIVE" if is_active else "COMPLETED"
        })

    emp_list = []
    for emp_id, data in emp_map.items():
        data["total_formatted"] = _format_seconds_to_hm(data["total_seconds"])
        emp_list.append(data)

    return {
        "has_activity": True,
        "employee_groups": emp_list,
        "overall_total_seconds": overall_total_sec,
        "overall_total_formatted": _format_seconds_to_hm(overall_total_sec)
    }


def format_solar_people_section(db: Session) -> str:
    """
    Renders ☀️ SOLAR PEOPLE section for bi-hourly sales update.
    Returns zero state '☀️ SOLAR PEOPLE: 0' if no activity today.
    """
    stats = get_today_solar_people_stats(db)
    if not stats["has_activity"] or not stats["employee_groups"]:
        return "☀️ *SOLAR PEOPLE: 0*"

    lines = ["☀️ *SOLAR PEOPLE*\n"]
    for emp in stats["employee_groups"]:
        lines.append(f"*{emp['staff_name']} — Total: {emp['total_formatted']}*")
        for item in emp["items"]:
            lines.append(f"• {item['lead_name']} — {item['duration_formatted']} — {item['status']}")
        lines.append("")

    lines.append(f"*Total Solar Time Today: {stats['overall_total_formatted']}*")
    return "\n".join(lines).strip()


def dispatch_bi_hourly_sales_performance_report(
    db: Session,
    slot_name: str = "Bi-Hourly Update",
    trigger_type: str = "AUTO_SCHEDULER",
    triggered_by: str = "System Cron"
) -> Dict[str, Any]:
    """
    Generates and dispatches the bi-hourly performance report to configured Sales WhatsApp Groups.
    Integrates canonically with automation_execution and automation_dispatch.
    """
    from app.services.whatsapp_group_alert_service import send_group_bot_message
    from app.services.whatsapp_audit_service import log_wa_trigger_execution
    from app.services.automation_tracking_service import (
        create_execution, record_dispatch, finalize_execution, get_job_targets
    )

    msg = generate_bi_hourly_performance_message(db, slot_name=slot_name)
    logger.info(f"📊 Dispatching sales performance update for slot {slot_name}...")

    # Load targets dynamically from persistent relational target store
    targets = get_job_targets(db, "wa_bihourly_sales_perf_report", company_id=1, active_only=True)
    if not targets:
        # Fallback default target
        target_list = [{"id": 0, "target_type": "group", "name": "Mynt Sales New", "identifier": "120363410784518818@g.us"}]
    else:
        target_list = [{"id": t.id, "target_type": t.target_type, "name": t.name, "identifier": t.identifier} for t in targets]

    summary_str = ", ".join(t["name"] for t in target_list)
    execution = create_execution(
        db=db,
        job_id="wa_bihourly_sales_perf_report",
        job_name="Sales Team 2-Hour Report & Leaderboard",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        target_summary=summary_str,
        metadata={"slot_name": slot_name}
    )

    last_res = None
    for tg in target_list:
        ident = tg["identifier"]
        is_jid = "@g.us" in ident
        res = send_group_bot_message(
            message_text=msg,
            invite_code="" if is_jid else ident,
            group_name=tg["name"],
            group_id=ident if is_jid else None,
            job_id="wa_bihourly_sales_perf_report",
            job_name="Sales Team 2-Hour Report & Leaderboard",
            trigger_type=trigger_type,
            db=db,
            execution_id=execution.id
        )
        last_res = res
        is_succ = isinstance(res, dict) and res.get("success") is True and not res.get("queued")
        is_queued = isinstance(res, dict) and res.get("queued") is True
        d_status = "SENT" if is_succ else ("UNCERTAIN" if is_queued else "FAILED")
        d_err = res.get("error") if not is_succ and not is_queued else None

        record_dispatch(
            db=db,
            execution_id=execution.id,
            job_id="wa_bihourly_sales_perf_report",
            recipient_type=tg["target_type"].upper(),
            recipient_identifier=ident,
            recipient_name=tg["name"],
            queue_id=res.get("queue_id"),
            provider="BOT_GATEWAY",
            provider_message_id=(res.get("data") or {}).get("messageId"),
            status=d_status,
            error_message=d_err,
            payload_snapshot={"slot_name": slot_name, "group_name": tg["name"]}
        )

    finalized_exec = finalize_execution(db, execution.id)

    # Legacy audit mirror
    try:
        log_wa_trigger_execution(
            job_id="wa_bihourly_sales_perf_report",
            job_name="Sales Team 2-Hour Report & Leaderboard",
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            targets=target_list,
            sent_count=finalized_exec.sent_count,
            failed_count=finalized_exec.failed_count,
            status=finalized_exec.status,
            error_message=finalized_exec.error_message,
            detail_data=last_res or {}
        )
    except Exception as e:
        logger.warning(f"Legacy audit log note: {e}")

    # MessageLog audit entry linked with execution_id
    try:
        from app.models.whatsapp import MessageLog
        import uuid
        log_entry = MessageLog(
            message_sid=f"sales_perf_{uuid.uuid4().hex[:12]}",
            mobile_number="GROUP:sales_perf"[:20],
            user_name=f"{triggered_by}"[:100],
            sent_by_name=f"{triggered_by}"[:100],
            sender_type="system" if trigger_type == "AUTO_SCHEDULER" else "staff",
            message_type="sales_performance",
            message_body=f"Sales Performance Report ({slot_name} by {triggered_by})",
            initial_status="sent" if finalized_exec.sent_count > 0 else "failed",
            current_status="sent" if finalized_exec.sent_count > 0 else "failed",
            sent_at=datetime.utcnow(),
            job_id="wa_bihourly_sales_perf_report",
            execution_id=execution.id
        )
        db.add(log_entry)
        db.commit()
    except Exception as log_e:
        db.rollback()
        logger.warning("[SALES-PERF] Failed to write MessageLog: %s", log_e)

    return {
        "success": finalized_exec.status in ("SUCCESS", "PARTIAL_SUCCESS"),
        "execution_id": execution.id,
        "sent_count": finalized_exec.sent_count,
        "uncertain_count": finalized_exec.uncertain_count,
        "failed_count": finalized_exec.failed_count,
        "status": finalized_exec.status,
        "data": last_res
    }
