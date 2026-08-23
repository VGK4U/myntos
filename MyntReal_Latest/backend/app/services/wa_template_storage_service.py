"""
WhatsApp Scheduler Template Management Service
Stores, retrieves, and updates custom template text overrides for all automated WhatsApp scheduler jobs.
Persists templates in data/wa_scheduler_templates.json.
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

TEMPLATES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wa_scheduler_templates.json")

# Default template strings for each scheduler job
DEFAULT_TEMPLATES = {
    "vgk_member_morning_statement": (
        "🌅 *నమస్కారం! మీ VGK4U DAILY REVENUE & PROGRESS UPDATE*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 *Member Name*: {member_name} ({user_code})\n"
        "📱 *Phone*: {phone}\n"
        "🏷️ *Designation*: {designation}\n"
        "📌 *Payout Status*: {payout_status_label}\n\n"
        "💰 *FINANCIAL REVENUE BREAKUP*\n"
        "• Overall Earned (Gross): ₹{overall_gross_earned}\n"
        "• Earned Till Date (Released): ₹{earned_till_date_net}\n"
        "• Potential Earnings: ₹{potential_earnings}\n"
        "• L0 Bonus & Extra Value: ₹{bonus_extra_value}\n"
        "• Active Files Advance: ₹{active_files_advance_paid}\n"
        "• Gross Pending (Draft + Pending): ₹{gross_pending}\n"
        "• Lost Lead Adv. Deductions: ₹{lost_lead_adv_deducted_pending}\n"
        "• Net Pending Payable: ₹{net_pending}\n\n"
        "📂 *STAGE-WISE FILE BREAKUP*\n"
        "• Total Sourced Files: {total_files}\n"
        "• Stage 1 Adv. Paid: {stage1_files} files (₹{stage1_total_adv})\n"
        "• Stage 2 Adv. Paid: {stage2_files} files (₹{stage2_total_adv})\n"
        "• Stage 3 Completed: {stage3_completed_files} files (₹{stage3_total_comm})\n"
        "• L0 Bonus & Extra Entries: {bonus_entries_count} entries (₹{bonus_total_amt})\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 _ఈ రోజు మీకు విజయవంతంగా సాగాలని ఆశిస్తున్నాము!_\n"
        "💬 _Auto-generated VGK4U Executive Member Revenue Report_"
    ),
    "vgk_member_zero_lead_motivational": (
        "{theme_header}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "నమస్కారం *{member_name}* గారు ({user_code}),\n\n"
        "{theme_quote}\n\n"
        "💡 *ఈరోజే యాక్షన్ ఎందుకు తీసుకోవాలి?*\n"
        "• *{active_earning_partners}+ Active Partners* మన VGK4U లో ఆల్రెడీ సక్సెస్ ఫుల్ గా ఇన్ కమ్ ఎర్న్ చేస్తున్నారు!\n"
        "• *₹{total_gross_earned} Total Gross Earnings* మన నెట్‌వర్క్ పార్టనర్స్‌కి పంపిణీ చేయబడ్డాయి!\n"
        "• *₹{total_pipeline_val} Active Opportunity* మన పైప్‌లైన్‌లో అందుబాటులో ఉంది!\n\n"
        "🔥 *CHALLENGE*: {active_earning_partners}+ యాక్టివ్ పార్టనర్స్ ఆల్రెడీ ఎర్న్ చేస్తున్నారు — మరి మీరు ఎప్పుడు మొదలుపెడుతున్నారు?\n\n"
        "🎯 *Mee Next Step*: {theme_focus}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *REFER AND EARN — మీ మొదటి లీడ్‌ని ఈరోజే సబ్మిట్ చేయండి! (Solar, Insurance & EV)*\n"
        "👉 Submit lead now: https://vgk4u.com/partner-portal\n"
        "💬 _Auto-generated VGK4U Member Motivation_"
    ),
    "wa_daily_morning_wish": (
        "🌅 *Good Morning, {customer_name}!*\n\n"
        "Wishing you a bright, energetic, and successful day ahead from the team at VGK Solar & Mynt Real!\n"
        "If you have any questions regarding your solar project or property estimations, we are here to support you.\n\n"
        "Have a great day! ☀️"
    ),
    "vgk4u_morning_wish": (
        "🌅 *VGK4U COMMUNITY MORNING WISH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good morning to all VGK Community Members & Official Partners!\n"
        "Let's make today impactful, productive, and full of success!\n\n"
        "💬 _VGK4U Community Outreach_"
    ),
    "wa_bihourly_sales_perf_report": (
        "📊 *BI-HOURLY SALES PERFORMANCE UPDATE*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Total Leads Sourced Today: {today_leads}\n"
        "• Validated Site Visits: {site_visits}\n"
        "• Conversions / Bookings: {conversions}\n\n"
        "Keep up the momentum! 🔥"
    ),
    "field_staff_journey_report": (
        "📍 *FIELD JOURNEY & LOCATION PERFORMANCE UPDATE*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Total Active Executives in Field: {active_executives}\n"
        "• Check-Ins Completed: {checkins_count}\n"
        "• Distance Covered: {distance_km} km\n\n"
        "Great work in the field today! 🚀"
    ),
    "missed_call_ack": (
        "📞 *MISSED CALL AUTO-ACKNOWLEDGEMENT*\n\n"
        "Hello {customer_name}, we noticed we missed your call!\n"
        "Our team will call you back shortly. Thank you for connecting with VGK Real Estate & Solar."
    ),
    "service_summary": (
        "🛠️ *DAILY SERVICE TICKET SUMMARY REPORT*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Open Tickets: {open_tickets}\n"
        "• Resolved Today: {resolved_today}\n"
        "• Pending Inspection: {pending_inspection}\n\n"
        "Thank you for maintaining service excellence!"
    )
}

AVAILABLE_VARIABLES = {
    "vgk_member_morning_statement": [
        "{member_name}", "{user_code}", "{phone}", "{designation}", "{payout_status_label}",
        "{overall_gross_earned}", "{earned_till_date_net}", "{potential_earnings}", "{bonus_extra_value}",
        "{active_files_advance_paid}", "{gross_pending}", "{lost_lead_adv_deducted_pending}", "{net_pending}",
        "{total_files}", "{stage1_files}", "{stage1_total_adv}", "{stage2_files}", "{stage2_total_adv}",
        "{stage3_completed_files}", "{stage3_total_comm}", "{bonus_entries_count}", "{bonus_total_amt}"
    ],
    "vgk_member_zero_lead_motivational": [
        "{member_name}", "{user_code}", "{phone}", "{active_earning_partners}", "{total_gross_earned}",
        "{total_pipeline_val}", "{theme_header}", "{theme_quote}", "{theme_focus}"
    ],
    "wa_daily_morning_wish": ["{customer_name}", "{phone}"],
    "vgk4u_morning_wish": ["{group_name}"],
    "wa_bihourly_sales_perf_report": ["{today_leads}", "{site_visits}", "{conversions}"],
    "field_staff_journey_report": ["{active_executives}", "{checkins_count}", "{distance_km}"],
    "missed_call_ack": ["{customer_name}", "{phone}"],
    "service_summary": ["{open_tickets}", "{resolved_today}", "{pending_inspection}"]
}


def _load_templates_file() -> Dict[str, str]:
    try:
        os.makedirs(os.path.dirname(TEMPLATES_FILE), exist_ok=True)
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as exc:
        logger.error(f"[WA-TEMPLATES] Error loading templates file: {exc}")
    return {}


def _save_templates_file(data: Dict[str, str]):
    try:
        os.makedirs(os.path.dirname(TEMPLATES_FILE), exist_ok=True)
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"[WA-TEMPLATES] Error saving templates file: {exc}")


def get_job_template(job_id: str) -> str:
    stored = _load_templates_file()
    if job_id in stored and stored[job_id].strip():
        return stored[job_id]
    return DEFAULT_TEMPLATES.get(job_id, "Hello {name}, here is your automated update.")


def save_job_template(job_id: str, template_text: str) -> Dict[str, Any]:
    stored = _load_templates_file()
    stored[job_id] = template_text.strip()
    _save_templates_file(stored)
    logger.info(f"✅ [WA-TEMPLATES] Successfully saved custom template for job '{job_id}'")
    return {
        "success": True,
        "job_id": job_id,
        "template_text": stored[job_id],
        "message": "Template updated successfully and persisted for all future dispatches."
    }


def get_all_job_templates_metadata() -> Dict[str, Any]:
    stored = _load_templates_file()
    res = {}
    for job_id, default_text in DEFAULT_TEMPLATES.items():
        curr = stored.get(job_id, default_text)
        res[job_id] = {
            "job_id": job_id,
            "template_text": curr,
            "is_customized": job_id in stored,
            "available_variables": AVAILABLE_VARIABLES.get(job_id, [])
        }
    return res
