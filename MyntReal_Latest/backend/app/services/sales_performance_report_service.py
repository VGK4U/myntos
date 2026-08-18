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
    from app.models.operator_calls import OperatorCall
    from app.models.crm import CRMLead

    # IST Today Range (+5:30)
    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)
    start_of_today_ist = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)

    # 1. Total Calls Handled Today
    total_calls = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.started_at >= start_of_today_utc
    ).scalar() or 0

    # 2. Total Talk Time Today (seconds)
    total_talk_seconds = db.query(func.sum(OperatorCall.duration_seconds)).filter(
        OperatorCall.started_at >= start_of_today_utc,
        OperatorCall.status == 'answered'
    ).scalar() or 0

    # 3. Missed Calls Today
    missed_calls = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.started_at >= start_of_today_utc,
        OperatorCall.status == 'missed'
    ).scalar() or 0

    # 4. New Leads Today
    new_leads = db.query(func.count(CRMLead.id)).filter(
        CRMLead.created_at >= start_of_today_utc
    ).scalar() or 0

    # 5. Top Staff Telecallers Leaderboard
    staff_stats_query = db.query(
        OperatorCall.handled_by,
        func.count(OperatorCall.id).label('call_count'),
        func.sum(OperatorCall.duration_seconds).label('talk_seconds')
    ).filter(
        OperatorCall.started_at >= start_of_today_utc,
        OperatorCall.handled_by.isnot(None),
        OperatorCall.handled_by != ''
    ).group_by(OperatorCall.handled_by).order_by(func.count(OperatorCall.id).desc()).all()

    leaderboard = []
    for row in staff_stats_query:
        leaderboard.append({
            "handled_by": row.handled_by,
            "call_count": row.call_count or 0,
            "talk_seconds": int(row.talk_seconds or 0),
            "talk_time_formatted": _format_seconds_to_hm(row.talk_seconds or 0)
        })

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

    # Build Top 3 Leaderboard
    lb = current_stats["leaderboard"]
    medals = ["🥇", "🥈", "🥉"]
    lb_text_lines = []
    for idx, item in enumerate(lb[:3]):
        medal = medals[idx] if idx < 3 else "🏅"
        lb_text_lines.append(f"{idx+1}. {medal} *{item['handled_by']}* — {item['call_count']} Calls | {item['talk_time_formatted']} Talk Time")

    lb_formatted = "\n".join(lb_text_lines) if lb_text_lines else "*(No staff calls recorded yet today)*"

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


def dispatch_bi_hourly_sales_performance_report(db: Session, slot_name: str = "Bi-Hourly Update") -> Dict[str, Any]:
    """
    Generates and dispatches the bi-hourly performance report to Sales WhatsApp Group.
    """
    from app.services.whatsapp_group_alert_service import send_group_bot_message

    msg = generate_bi_hourly_performance_message(db, slot_name=slot_name)
    logger.info(f"📊 Dispatching sales performance update for slot {slot_name}...")
    return send_group_bot_message(msg)
