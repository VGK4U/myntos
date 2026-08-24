"""
DC_FIELD_JOURNEY_REPORT_001 — Field Staff Journey Tracking & Performance Report Service
Generates bi-hourly updates (9:30 AM - 7:30 PM IST) for WhatsApp group:
https://chat.whatsapp.com/BctONtnv8431uxxybKBEtS

Includes:
- Total active/completed staff in journey today
- KM distance (total & WVV validated) with KM delta (+X.X KMs since last update)
- Tagged CRM Leads / Installation details
- In-app photo check-ins count & timestamp
- 2-Hour Inactivity Alerts sent to Employee AND Reporting Manager for active journeys
"""

import os
import json
import logging
import datetime
from datetime import timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "field_journey_snapshots.json")
FIELD_REPORT_GROUP_INVITE = "https://chat.whatsapp.com/BctONtnv8431uxxybKBEtS"


def _format_minutes_to_hm(total_minutes: float) -> str:
    total_minutes = int(total_minutes or 0)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes}m"


def get_today_field_journey_stats(db: Session) -> Dict[str, Any]:
    """
    Aggregates today's field staff journey statistics and calculates distance deltas + GPS locations.
    """
    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)
    date_str = ist_now.strftime("%Y-%m-%d")
    time_str = ist_now.strftime("%I:%M %p")

    # Calculate UTC bounds for today
    start_of_today_ist = datetime.datetime(ist_now.year, ist_now.month, ist_now.day, 0, 0, 0)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)
    end_of_today_utc = start_of_today_utc + timedelta(days=1)

    # Load ALL journeys for today (active, completed, paused, ended)
    rows = db.execute(text("""
        SELECT 
            j.id as journey_id,
            j.employee_id,
            e.full_name as staff_name,
            e.emp_code,
            e.phone as staff_phone,
            e.reporting_manager_id,
            mgr.phone as manager_phone,
            j.status as journey_status,
            j.purpose,
            j.purpose_description,
            j.total_distance_km,
            j.reimbursable_distance_km,
            j.total_duration_minutes,
            j.start_time,
            j.end_time,
            j.start_latitude,
            j.start_longitude,
            j.start_address,
            j.end_latitude,
            j.end_longitude,
            j.end_address,
            j.lead_id,
            l.name as lead_name,
            l.phone as lead_phone,
            l.area as lead_area,
            l.city as lead_city,
            (
                SELECT COUNT(c.id) 
                FROM staff_journey_checkins c 
                WHERE c.journey_id = j.id
            ) as photo_count,
            (
                SELECT MAX(c.created_at) 
                FROM staff_journey_checkins c 
                WHERE c.journey_id = j.id
            ) as latest_photo_time,
            (
                SELECT c.address 
                FROM staff_journey_checkins c 
                WHERE c.journey_id = j.id AND c.address IS NOT NULL AND c.address != ''
                ORDER BY c.created_at DESC 
                LIMIT 1
            ) as latest_checkin_address,
            (
                SELECT c.latitude 
                FROM staff_journey_checkins c 
                WHERE c.journey_id = j.id AND c.latitude IS NOT NULL
                ORDER BY c.created_at DESC 
                LIMIT 1
            ) as latest_checkin_lat,
            (
                SELECT c.longitude 
                FROM staff_journey_checkins c 
                WHERE c.journey_id = j.id AND c.longitude IS NOT NULL
                ORDER BY c.created_at DESC 
                LIMIT 1
            ) as latest_checkin_lng,
            (
                SELECT t.address 
                FROM staff_journey_track_points t 
                WHERE t.journey_id = j.id AND t.address IS NOT NULL AND t.address != ''
                ORDER BY t.timestamp DESC 
                LIMIT 1
            ) as latest_track_address,
            (
                SELECT t.latitude 
                FROM staff_journey_track_points t 
                WHERE t.journey_id = j.id AND t.latitude IS NOT NULL
                ORDER BY t.timestamp DESC 
                LIMIT 1
            ) as latest_track_lat,
            (
                SELECT t.longitude 
                FROM staff_journey_track_points t 
                WHERE t.journey_id = j.id AND t.longitude IS NOT NULL
                ORDER BY t.timestamp DESC 
                LIMIT 1
            ) as latest_track_lng,
            (
                SELECT att.gps_status
                FROM staff_attendance att
                WHERE att.employee_id = j.employee_id AND att.date = j.date
                LIMIT 1
            ) as live_gps_status
        FROM staff_journeys j
        JOIN staff_employees e ON e.id = j.employee_id
        LEFT JOIN staff_employees mgr ON mgr.id = e.reporting_manager_id
        LEFT JOIN crm_leads l ON l.id = j.lead_id
        WHERE (
            j.date::text LIKE :d_pattern
            OR (j.start_time >= :start_utc AND j.start_time < :end_utc)
        )
          AND (e.status IS NULL OR e.status = 'active')
          AND (e.is_deleted IS NOT TRUE)
        ORDER BY j.status DESC, j.total_distance_km DESC
    """), {
        "d_pattern": f"{date_str}%",
        "start_utc": start_of_today_utc,
        "end_utc": end_of_today_utc
    }).fetchall()

    # Load previous snapshot for KM delta calculation
    prev_snapshot = {}
    current_snapshot_journeys = {}
    all_ended_report_sent = False
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r") as f:
                data = json.load(f)
                if data.get("date") == date_str:
                    prev_snapshot = data.get("journeys", {})
                    all_ended_report_sent = data.get("all_ended_report_sent", False)
        except Exception as exc:
            logger.warning("[FIELD-REPORT] Failed to read snapshot file: %s", exc)

    # ── Aggregate by Employee ID (1 Row per Staff Member per Day) ────────────────
    staff_map = {}


    for r in rows:
        emp_id = r.employee_id
        dist = float(r.total_distance_km or 0)
        wvv_dist = float(r.reimbursable_distance_km or dist)
        st = (r.journey_status or '').lower()
        is_act = ('progress' in st or st == 'in_progress' or st == 'started' or st == 'active')

        # KM Delta calculation per journey
        prev_km = float(prev_snapshot.get(str(r.journey_id), 0.0))
        km_delta = round(dist - prev_km, 1)
        if km_delta < 0:
            km_delta = 0.0

        current_snapshot_journeys[str(r.journey_id)] = dist

        # Photo check-in calculation
        latest_photo_formatted = "None"
        photo_inactivity_mins = 9999
        if r.latest_photo_time:
            p_time_ist = r.latest_photo_time + timedelta(hours=5, minutes=30)
            latest_photo_formatted = p_time_ist.strftime("%I:%M %p")
            photo_inactivity_mins = int((ist_now - p_time_ist).total_seconds() / 60)
        elif r.start_time:
            start_ist = r.start_time + timedelta(hours=5, minutes=30) if isinstance(r.start_time, datetime.datetime) else ist_now
            photo_inactivity_mins = int((ist_now - start_ist).total_seconds() / 60)

        alert_flag = ""
        needs_warning_alert = False
        if is_act:
            if photo_inactivity_mins >= 240:
                alert_flag = f"🔴 No update in last 4 hours (Alert Sent)"
                needs_warning_alert = True
            elif photo_inactivity_mins >= 120:
                alert_flag = f"⚠️ Photo check-in pending (>2h)"
                needs_warning_alert = True

        # GPS Location Resolution
        lat = r.latest_checkin_lat or r.latest_track_lat or r.start_latitude or r.end_latitude
        lng = r.latest_checkin_lng or r.latest_track_lng or r.start_longitude or r.end_longitude
        lead_loc = ", ".join(filter(None, [getattr(r, 'lead_area', None), getattr(r, 'lead_city', None)]))
        location_address = (
            r.latest_checkin_address or 
            r.latest_track_address or 
            r.start_address or 
            r.end_address or 
            lead_loc or 
            ""
        ).strip()
        if not location_address and lat and lng:
            location_address = f"GPS ({round(float(lat), 4)}, {round(float(lng), 4)})"
        maps_url = f"https://maps.google.com/?q={lat},{lng}" if (lat and lng) else ""
        purpose_str = (r.purpose or 'other').lower()
        is_inst = 'installation' in purpose_str
        is_lead = bool(r.lead_id) and not is_inst
        if emp_id not in staff_map:
            staff_map[emp_id] = {
                "employee_id": emp_id,
                "staff_name": r.staff_name,
                "emp_code": r.emp_code,
                "staff_phone": r.staff_phone,
                "manager_phone": r.manager_phone,
                "total_distance_km": 0.0,
                "reimbursable_distance_km": 0.0,
                "km_delta_total": 0.0,
                "total_duration_minutes": 0.0,
                "journey_count": 0,
                "lead_visits": 0,
                "installations": 0,
                "photo_count": 0,
                "latest_photo_formatted": "None",
                "photo_inactivity_mins": 9999,
                "is_active": False,
                "needs_warning_alert": False,
                "alert_flag": "",
                "lead_names": [],
                "purposes": []
            }
        s = staff_map[emp_id]
        s["journey_count"] += 1
        s["total_distance_km"] += dist
        s["reimbursable_distance_km"] += wvv_dist
        s["km_delta_total"] += km_delta
        s["total_duration_minutes"] += float(r.total_duration_minutes or 0)
        s["photo_count"] += (r.photo_count or 0)
        if is_act:
            s["is_active"] = True
            if needs_warning_alert:
                s["needs_warning_alert"] = True
                s["alert_flag"] = alert_flag
        if is_inst:
            s["installations"] += 1
        elif is_lead:
            s["lead_visits"] += 1
        if latest_photo_formatted != "None" and (s["latest_photo_formatted"] == "None" or photo_inactivity_mins < s["photo_inactivity_mins"]):
            s["latest_photo_formatted"] = latest_photo_formatted
            s["photo_inactivity_mins"] = photo_inactivity_mins
        lead_title = r.lead_name or r.purpose_description or "General Field Visit"
        if lead_title not in s["lead_names"]:
            s["lead_names"].append(lead_title)
        purp_title = (r.purpose or "General Visit").replace('_', ' ').title()
        if purp_title not in s["purposes"]:
            s["purposes"].append(purp_title)
    # Convert aggregated staff_map to sorted journey_list (1 row per staff member)
    journey_list = []
    total_active_staff = 0
    total_completed_staff = 0
    total_km_overall = 0.0
    total_wvv_km_overall = 0.0
    tagged_crm_leads_count = 0
    installations_count = 0
    sorted_staff = sorted(staff_map.values(), key=lambda x: (1 if x["is_active"] else 0, x["total_distance_km"]), reverse=True)
    for s in sorted_staff:
        if s["is_active"]:
            total_active_staff += 1
            status_text = "🟢 Active"
        else:
            total_completed_staff += 1
            status_text = "🏁 Completed"
        dist = round(s["total_distance_km"], 1)
        wvv_dist = round(s["reimbursable_distance_km"], 1)
        total_km_overall += dist
        total_wvv_km_overall += wvv_dist
        tagged_crm_leads_count += s["lead_visits"]
        installations_count += s["installations"]
        lead_summary = ", ".join(s["lead_names"]) if s["lead_names"] else "General Field Visit"
        journey_list.append({
            "employee_id": s["employee_id"],
            "staff_name": s["staff_name"],
            "emp_code": s["emp_code"],
            "staff_phone": s["staff_phone"],
            "manager_phone": s["manager_phone"],
            "status_text": status_text,
            "is_active": (st == 'in_progress'),
            "purpose": r.purpose or "General Visit",
            "purpose_description": r.purpose_description or "",
            "distance_km": round(dist, 1),
            "wvv_distance_km": round(wvv_dist, 1),
            "km_delta": km_delta,
            "duration_formatted": _format_minutes_to_hm(r.total_duration_minutes or 0),
            "lead_name": r.lead_name or r.purpose_description or "General Field Visit",
            "lead_area": r.lead_area or "",
            "photo_count": r.photo_count or 0,
            "latest_photo_formatted": latest_photo_formatted,
            "photo_inactivity_mins": photo_inactivity_mins,
            "alert_flag": alert_flag,
            "needs_warning_alert": needs_warning_alert,
            "location_address": location_address,
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
            "maps_url": maps_url,
            "gps_status": r.live_gps_status or "ENABLED",
            "is_active": s["is_active"],
            "journey_count": s["journey_count"],
            "distance_km": dist,
            "wvv_distance_km": wvv_dist,
            "km_delta": round(s["km_delta_total"], 1),
            "duration_formatted": _format_minutes_to_hm(s["total_duration_minutes"]),
            "lead_name": lead_summary,
            "purpose": ", ".join(s["purposes"]) if s["purposes"] else "General Visit",
            "photo_count": s["photo_count"],
            "latest_photo_formatted": s["latest_photo_formatted"],
            "photo_inactivity_mins": s["photo_inactivity_mins"],
            "alert_flag": s["alert_flag"],
            "needs_warning_alert": s["needs_warning_alert"]        })

    # Save new snapshot
    try:
        is_all_ended = (total_active_staff == 0 and total_completed_staff > 0)
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        with open(SNAPSHOT_FILE, "w") as f:
            json.dump({
                "date": date_str,
                "updated_at": time_str,
                "all_ended_report_sent": is_all_ended,
                "journeys": current_snapshot_journeys
            }, f, indent=2)
    except Exception as exc:
        logger.warning("[FIELD-REPORT] Failed to write snapshot: %s", exc)

    return {
        "date_str": date_str,
        "time_str": time_str,
        "total_participated": len(staff_map),
        "total_active": total_active_staff,
        "total_completed": total_completed_staff,
        "all_ended_report_sent": all_ended_report_sent,
        "total_km": round(total_km_overall, 1),
        "total_wvv_km": round(total_wvv_km_overall, 1),
        "tagged_crm_leads_count": tagged_crm_leads_count,
        "installations_count": installations_count,
        "journeys": journey_list
    }


def format_field_journey_whatsapp_message(stats: Dict[str, Any]) -> str:
    """
    Formats the WhatsApp Field Journey Performance Leaderboard Report.
    """
    date_str = stats.get("date_str", "")
    time_str = stats.get("time_str", "")
    total_participated = stats.get("total_participated", 0)
    active_cnt = stats.get("total_active", 0)
    comp_cnt = stats.get("total_completed", 0)
    total_km = stats.get("total_km", 0.0)
    wvv_km = stats.get("total_wvv_km", 0.0)
    crm_cnt = stats.get("tagged_crm_leads_count", 0)
    inst_cnt = stats.get("installations_count", 0)
    journeys = stats.get("journeys", [])

    is_daily_closing = ("09:00 PM" in time_str or "21:00" in time_str or "closing" in str(stats.get("report_type", "")).lower())

    lines = [
        f"🚜 *FIELD JOURNEY PERFORMANCE REPORT*",
        f"📅 Date: {date_str} | 🕒 Update Time: {time_str}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👥 Total Staff Today: {total_participated} | 🟢 Active Now: {active_cnt} | 🏁 Completed: {comp_cnt}",
        f"🚗 Total Distance: *{total_km} KMs* (WVV Validated: {wvv_km} KMs)",
        f"📌 CRM Lead Visits: {crm_cnt} | 🔧 Installations: {inst_cnt}",
        f"",
        f"🏆 *FIELD STAFF LEADERBOARD & JOURNEY STATUS:*"
    ]

    if not journeys:
        lines.append("   _No staff journeys recorded today yet._")
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, j in enumerate(journeys):
            prefix = medals[idx] if idx < 3 else f"{idx+1}."
            name_code = f"{j['staff_name']} ({j['emp_code']})"
            delta_str = f" (📈 +{j['km_delta']} KMs)" if j['km_delta'] > 0 else ""
            
            lines.append(f"{prefix} *{name_code}* — *{j['distance_km']} KMs*{delta_str} | {j['duration_formatted']}")
            lines.append(f"   📍 Lead: *{j['lead_name']}* ({j['purpose'].replace('_', ' ').title()})")
            # GPS Location & Live Map Link
            gps_status = j.get('gps_status') or 'ACTIVE'
            if j.get('maps_url'):
                loc_title = j.get('location_address') or "Live Tracked"
                lines.append(f"   🗺️ GPS Loc: {loc_title} (📍 {j['maps_url']})")
            elif j.get('location_address'):
                lines.append(f"   🗺️ GPS Loc: {j['location_address']}")
            else:
                lines.append(f"   🗺️ GPS Loc: Active ({j['distance_km']} KMs tracked)")
            lines.append(f"   📍 Lead: *{j['lead_name']}* ({j['purpose']})")
            lines.append(f"   📸 Photos: {j['photo_count']} (Latest: {j['latest_photo_formatted']}) | {j['status_text']}")
            if j['alert_flag']:
                lines.append(f"   {j['alert_flag']}")
            lines.append("")

    footer = "💬 _Auto-generated daily closing field operations report_" if is_daily_closing else "💬 _Auto-generated 90-minute field operations update_"
    lines.append(footer)
    return "\n".join(lines)


def dispatch_field_journey_photo_inactivity_alerts_only(db: Session) -> Dict[str, Any]:
    """
    Executes ONLY 30-min active journey photo check-in audit & alert dispatches.
    DOES NOT dispatch the WhatsApp group performance report!
    """
    from app.services.whatsapp_auto_service import send_direct_whatsapp

    stats = get_today_field_journey_stats(db)
    alerts_sent = 0
    for j in stats.get("journeys", []):
        if j.get("is_active") and j.get("needs_warning_alert"):
            staff_phone = j.get("staff_phone")
            mgr_phone = j.get("manager_phone")

            alert_msg = (
                f"⚠️ *FIELD JOURNEY CHECK-IN REMINDER*\n\n"
                f"Hello *{j['staff_name']}*,\n"
                f"Your active journey (*{j['lead_name']}*) has had no photo check-in for over {j['photo_inactivity_mins'] // 60} hours.\n\n"
                f"📌 *Action Required:* Please open the Staff Portal App (/staff/journeys) and upload a live camera check-in photo immediately with location enabled.\n\n"
                f"Thank you!"
            )

            if staff_phone:
                try:
                    send_direct_whatsapp(db=db, phone=staff_phone, message=alert_msg)
                    alerts_sent += 1
                except Exception as e:
                    logger.warning("[FIELD-REPORT] Could not send alert to staff %s: %s", staff_phone, e)

            if mgr_phone:
                mgr_alert_msg = (
                    f"🔔 *MANAGER ALERT: FIELD CHECK-IN PENDING*\n\n"
                    f"Team Member: *{j['staff_name']}* ({j['emp_code']})\n"
                    f"Journey: *{j['lead_name']}*\n"
                    f"Inactivity: No photo check-in for *{j['photo_inactivity_mins'] // 60} hours*.\n\n"
                    f"A reminder has been dispatched to the employee."
                )
                try:
                    send_direct_whatsapp(db=db, phone=mgr_phone, message=mgr_alert_msg)
                    alerts_sent += 1
                except Exception as e:
                    logger.warning("[FIELD-REPORT] Could not send alert to manager %s: %s", mgr_phone, e)

    return {"success": True, "alerts_sent": alerts_sent}


def dispatch_field_journey_whatsapp_reports_and_alerts(
    db: Session,
    trigger_type: str = "AUTO_SCHEDULER",
    triggered_by: str = "System Cron"
) -> Dict[str, Any]:
    """
    Main trigger function executed at scheduled hourly intervals starting at 09:30 AM IST (09:30 AM - 09:00 PM IST):
    1. Sends Group Summary Report to target WhatsApp group.
    2. Sends direct 2-Hour Photo Inactivity Warning alerts ONLY to employees currently in an active journey.
    """
    from app.services.whatsapp_group_alert_service import send_group_bot_message
    from app.services.whatsapp_auto_service import send_direct_whatsapp
    from app.services.whatsapp_audit_service import log_wa_trigger_execution

    stats = get_today_field_journey_stats(db)

    total_participated = stats.get("total_participated", 0)
    total_active = stats.get("total_active", 0)
    total_completed = stats.get("total_completed", 0)
    all_ended_sent = stats.get("all_ended_report_sent", False)

    # 1. Active staff check: For automated scheduler, skip sending if 0 staff active/logged journeys today
    if trigger_type == "AUTO_SCHEDULER" and total_participated == 0 and total_active == 0:
        logger.info("[FIELD-REPORT] No active field staff or journeys logged today. Skipping automated hourly report.")
        log_wa_trigger_execution(
            job_id="field_staff_journey_report",
            job_name="Field Journey Performance & Leaderboard Report",
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            targets=[{"type": "group", "name": "Field Updates", "identifier": "BctONtnv8431uxxybKBEtS"}],
            sent_count=0,
            failed_count=0,
            status="SKIPPED",
            error_message="No active field staff or journeys today",
            detail_data={"reason": "no_active_journeys"}
        )
        return {
            "success": True,
            "skipped": True,
            "reason": "No active field staff or journeys today",
            "active_journeys_count": 0
        }

    # 2. Journeys ended check: Skip if all staff completed/ended their journeys for today and final report was already dispatched
    if trigger_type == "AUTO_SCHEDULER" and total_active == 0 and total_completed > 0 and all_ended_sent:
        logger.info("[FIELD-REPORT] All field journeys ended for today (%d completed). Final report already dispatched. Skipping automated hourly report.", total_completed)
        log_wa_trigger_execution(
            job_id="field_staff_journey_report",
            job_name="Field Journey Performance & Leaderboard Report",
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            targets=[{"type": "group", "name": "Field Updates", "identifier": "BctONtnv8431uxxybKBEtS"}],
            sent_count=0,
            failed_count=0,
            status="SKIPPED",
            error_message="All field journeys ended for today",
            detail_data={"reason": "all_journeys_ended", "total_completed": total_completed}
        )
        return {
            "success": True,
            "skipped": True,
            "reason": "All field journeys ended for today",
            "active_journeys_count": 0,
            "completed_journeys_count": total_completed
        }

    report_msg = format_field_journey_whatsapp_message(stats)

    # 1. Post to Target WhatsApp Group (BctONtnv8431uxxybKBEtS)
    group_result = False
    group_res = send_group_bot_message(message_text=report_msg, invite_code="BctONtnv8431uxxybKBEtS")
    if group_res.get("success"):
        group_result = True
        logger.info("[FIELD-REPORT] Successfully posted report to WhatsApp group BctONtnv8431uxxybKBEtS")
    else:
        logger.warning("[FIELD-REPORT] Group bot response: %s", group_res)

    try:
        from app.models.whatsapp import MessageLog
        import uuid
        log_entry = MessageLog(
            message_sid=f"field_journey_{uuid.uuid4().hex[:12]}",
            mobile_number="GROUP:Field Updates",
            message_type="field_journey",
            message_body=report_msg[:500],
            initial_status="sent" if group_result else "failed",
            current_status="sent" if group_result else "failed",
            sent_at=datetime.datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as log_e:
        logger.warning("[FIELD-REPORT] Failed to write MessageLog: %s", log_e)

    # 2. Dispatch Individual Inactivity Alerts
    alerts_res = dispatch_field_journey_photo_inactivity_alerts_only(db)
    alerts_sent = alerts_res.get("alerts_sent", 0)

    targets = [{"type": "group", "name": "Field Updates", "identifier": "BctONtnv8431uxxybKBEtS"}]
    err_text = None if group_result else ((group_res or {}).get("error") or "WhatsApp Bot Gateway disconnected")

    log_wa_trigger_execution(
        job_id="field_staff_journey_report",
        job_name="Field Journey Performance & Leaderboard Report",
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        targets=targets,
        sent_count=1 if group_result else 0,
        failed_count=0 if group_result else 1,
        status="SUCCESS" if group_result else "FAILED",
        error_message=err_text,
        detail_data={"group_posted": group_result, "alerts_sent": alerts_sent, "active_journeys": stats.get("total_active", 0)}
    )

    return {
        "success": True,
        "group_posted": group_result,
        "group_response": group_res,
        "alerts_sent": alerts_sent,
        "active_journeys_count": stats.get("total_active", 0)
    }

