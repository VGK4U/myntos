"""
DC_SALES_PERF_REPORT_001 — Bi-Hourly Sales Performance Report & Leaderboard Generator
Generates bi-hourly updates (9:30 AM - 7:30 PM IST) with comparison against previous updates.
"""

import os
import json
import logging
import datetime
from datetime import timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "sales_perf_snapshots.json")


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


def get_today_sales_performance_stats(db: Session) -> Dict[str, Any]:
    """
    Aggregates today's sales performance statistics up to the current moment.
    """
    from sqlalchemy import text
    from app.models.crm import CRMLead

    # IST Today Range (+5:30)
    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)
    start_of_today_ist = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)
    date_str = ist_now.strftime("%Y-%m-%d")

    from app.models.operator_calls import OperatorCall

    # 1. Tele Sales / Telecaller Department Staff (Strictly excluding Freelancers & Non-Telecaller Departments)
    staff_rows = db.execute(text("""
        SELECT e.id, e.full_name, e.emp_code
        FROM staff_employees e
        LEFT JOIN staff_departments d ON d.id = e.department_id
        LEFT JOIN staff_employee_departments ed ON ed.employee_id = e.id
        LEFT JOIN staff_departments ad ON ad.id = ed.department_id
        LEFT JOIN staff_roles r ON r.id = e.role_id
        WHERE (
            LOWER(d.name) LIKE '%tele%' 
            OR LOWER(ad.name) LIKE '%tele%'
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
        GROUP BY e.id, e.full_name, e.emp_code
    """)).fetchall()

    leaderboard = []
    total_calls = 0
    total_talk_seconds = 0
    missed_calls = 0

    for s in staff_rows:
        # Mobile call logs (Call Tracker App)
        m_row = db.execute(text("""
            SELECT COUNT(id) as cnt, COALESCE(SUM(duration_seconds), 0) as dur,
                   COUNT(CASE WHEN UPPER(call_type) IN ('MISSED', 'REJECTED', 'NO_ANSWER') THEN 1 END) as missed
            FROM staff_call_logs WHERE staff_id = :sid AND call_date = :d
        """), {"sid": s.id, "d": date_str}).fetchone()

        m_cnt = m_row.cnt if m_row else 0
        m_dur = int(m_row.dur or 0) if m_row else 0
        m_missed = m_row.missed if m_row else 0

        # Operator Cloud Calls (MyOperator virtual numbers)
        words = [w for w in s.full_name.replace('.', ' ').split() if len(w) >= 3 and w.lower() not in ('ms', 'mrs', 'mr', 'dr')]
        filters = [OperatorCall.handled_by.ilike(f'%{w}%') for w in words]
        op_calls = db.query(OperatorCall).filter(
            OperatorCall.started_at >= start_of_today_utc,
            or_(*filters)
        ).all() if filters else []

        op_cnt = len(op_calls)
        op_dur = sum(c.duration_seconds or 0 for c in op_calls if c.status == 'answered')
        op_missed = sum(1 for c in op_calls if c.status == 'missed')

        staff_tot_calls = m_cnt + op_cnt
        staff_tot_talk = m_dur + op_dur
        staff_tot_missed = m_missed + op_missed

        total_calls += staff_tot_calls
        total_talk_seconds += staff_tot_talk
        missed_calls += staff_tot_missed

        leaderboard.append({
            "handled_by": s.full_name,
            "call_count": staff_tot_calls,
            "missed_count": staff_tot_missed,
            "talk_seconds": staff_tot_talk,
            "talk_time_formatted": _format_seconds_to_hm(staff_tot_talk)
        })

    leaderboard.sort(key=lambda x: (x["call_count"], x["talk_seconds"]), reverse=True)

    # 3. New Leads Intake Today
    new_leads = db.query(func.count(CRMLead.id)).filter(
        CRMLead.created_at >= start_of_today_utc
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

    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)
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
        lb_text_lines.append(f"{idx+1}. {medal} *{staff_name}* — {item['call_count']} Calls{missed_str} | {item['talk_time_formatted']} Talk Time{staff_delta_str}")

    if not active_staff:
        lb_text_lines.append("*(No staff calls recorded yet today)*")

    if idle_staff:
        lb_text_lines.append("\n📋 *TELE SALES TEAM MEMBERS (0 Calls Today)*:")
        for item in idle_staff:
            lb_text_lines.append(f"• *{item['handled_by']}* — 0 Calls | 00m Talk Time")

    lb_formatted = "\n".join(lb_text_lines)

    is_evening_closing = "07:30" in slot_name or "Closing" in slot_name or ist_now.hour >= 19
    header_title = "📊 *DAILY SALES FINAL CLOSING REPORT*" if is_evening_closing else f"📊 *SALES TEAM 2-HOUR UPDATE ({current_stats['time_str']})*"

    msg = (
        f"{header_title}\n"
        f"📅 *Date*: {current_stats['date_str']}\n\n"
        f"📞 *Total Calls Handled*: {current_stats['total_calls']} calls{delta_calls_str}\n"
        f"🗣️ *Total Talk Time*: {current_stats['total_talk_formatted']}{delta_talk_str}\n"
        f"🔴 *Missed Calls Received*: {current_stats['missed_calls']} calls{delta_missed_str} *(100% WA ACK Sent)*\n"
        f"🎯 *New Leads Intake*: {current_stats['new_leads']} leads{delta_leads_str}\n\n"
        f"🏆 *STAFF LEADERBOARD TODAY*:\n"
        f"{lb_formatted}\n\n"
        f"{'Great effort today team! Have a peaceful evening! 🌙' if is_evening_closing else 'Keep up the strong momentum team! Next update in 2 hours! 🚀'}"
    )

    return msg


def dispatch_bi_hourly_sales_performance_report(
    db: Session,
    slot_name: str = "Bi-Hourly Update",
    trigger_type: str = "AUTO_SCHEDULER",
    triggered_by: str = "System Cron"
) -> Dict[str, Any]:
    """
    Generates and dispatches the bi-hourly performance report to Sales WhatsApp Group.
    """
    from app.services.whatsapp_group_alert_service import send_group_bot_message
    from app.services.whatsapp_audit_service import log_wa_trigger_execution

    msg = generate_bi_hourly_performance_message(db, slot_name=slot_name)
    logger.info(f"📊 Dispatching sales performance update for slot {slot_name}...")
    res = send_group_bot_message(msg)
    is_succ = isinstance(res, dict) and res.get("success") is True

    targets = [
        {"id": "t1", "type": "group", "name": "Mynt Sales New Group", "identifier": "9053899899"},
        {"id": "t2", "type": "group", "name": "Executive Team Announcements", "identifier": "7702830269"}
    ]

    log_wa_trigger_execution(
        job_id="wa_bihourly_sales_perf_report",
        job_name="Sales Team 2-Hour Report & Leaderboard",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        targets=targets,
        sent_count=1 if is_succ else 0,
        failed_count=0 if is_succ else 1,
        status="SUCCESS" if is_succ else "FAILED",
        error_message=res.get("error") if not is_succ else None,
        detail_data=res
    )

    return res
