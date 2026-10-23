"""
DC_HAR_GHAR_SUPPORT_REPORT_001 — Har Ghar Support WhatsApp Group Report Service
Generates and dispatches the Executive Solar Pipeline & Status Report to the
"Har ghar support" WhatsApp group via Scanned WhatsApp Bot (port 5002):
- Scheduled automatically every day at 9:00 AM and 8:00 PM IST (without manual entry).
- Triggerable manually from the Executive Dashboard (with interactive selection for:
  2. People On Ground & 3. Expected Payments From Bank).
"""

import logging
import datetime
import pytz
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_, and_, case

from app.core.timezone import get_indian_time
from app.services.whatsapp_group_alert_service import send_group_bot_message

logger = logging.getLogger(__name__)

HAR_GHAR_GROUP_NAME = "Har ghar support"
JOB_ID_HAR_GHAR_REPORT = "har_ghar_support_report"


def _get_ist_now() -> datetime.datetime:
    """Returns current naive datetime in Asia/Kolkata (IST)."""
    return datetime.datetime.now(pytz.timezone("Asia/Kolkata")).replace(tzinfo=None)


def _format_inr_short(val: float) -> str:
    """Formats INR currency concisely (e.g. ₹14.00L, ₹1.25Cr, ₹45,000)."""
    val = float(val or 0)
    if val <= 0:
        return "₹0"
    if val >= 10000000:
        return f"₹{val / 10000000:.2f}Cr"
    if val >= 100000:
        return f"₹{val / 100000:.2f}L"
    return f"₹{int(round(val)):,}"


def get_har_ghar_support_report_metrics(db: Session) -> Dict[str, Any]:
    """
    Computes live Har Ghar Solar pipeline & status metrics for the Executive Report.
    """
    from app.models.crm import CRMLead

    ist_now = _get_ist_now()
    today = ist_now.date()
    month_start_date = datetime.date(today.year, today.month, 1)
    month_start_dt = datetime.datetime.combine(month_start_date, datetime.time.min)
    month_label = month_start_date.strftime("%b %Y")

    POST_WON = ["won", "order_placed", "dispatched", "delivered", "installed", "completed"]
    EXCL_WON_PS = [
        "loan_rejected",
        "documents_issue",
        "not_interested",
        "cancelled",
        "different_vendor",
        "bank_not_interested",
    ]
    INSTALLED_PS = [
        "installed",
        "dcr_pending",
        "discom_pending",
        "net_meter_pending",
        "balance_pending",
        "balance_received",
        "subsidy_pending",
        "completed",
    ]

    # 1. No. of Leads At Bank (Won/active pipeline leads currently at bank)
    leads_at_bank = (
        db.query(func.count(CRMLead.id))
        .filter(
            CRMLead.solar_pipeline_status == "pending_with_bank",
            CRMLead.status.in_(POST_WON),
        )
        .scalar()
        or 0
    )
    leads_at_bank_all = (
        db.query(func.count(CRMLead.id))
        .filter(
            CRMLead.solar_pipeline_status == "pending_with_bank",
            ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
        )
        .scalar()
        or 0
    )

    # 4. New VGK Members (Current Month)
    new_vgk_members_current_month = 0
    try:
        new_vgk_members_current_month = (
            db.execute(
                text(
                    """
                    SELECT COUNT(id)
                    FROM official_partners
                    WHERE category = 'VGK_TEAM'
                      AND (partner_type IS NULL OR partner_type != 'FREELANCER')
                      AND (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') >= :m_start
                    """
                ),
                {"m_start": month_start_dt},
            ).scalar()
            or 0
        )
    except Exception as e:
        logger.warning(f"[HAR-GHAR-REPORT] Error querying new VGK members: {e}")
        db.rollback()

    # Fetch all solar pipeline leads & current-month won leads for revenue, files, and installation counts
    eff_dv_expr = case(
        (
            and_(
                CRMLead.confirmed_final_value.isnot(None),
                CRMLead.confirmed_final_value > 0,
            ),
            CRMLead.confirmed_final_value,
        ),
        (
            and_(CRMLead.deal_value_total.isnot(None), CRMLead.deal_value_total > 0),
            CRMLead.deal_value_total,
        ),
        else_=func.coalesce(CRMLead.deal_value, 0),
    )

    solar_leads = (
        db.query(
            CRMLead.id,
            CRMLead.status,
            CRMLead.solar_pipeline_status,
            CRMLead.solar_pipeline_status_updated_at,
            CRMLead.submit_date,
            CRMLead.installation_date,
            CRMLead.complete_date,
            CRMLead.actual_close_date,
            CRMLead.created_at,
            CRMLead.source,
            CRMLead.source_ref_type,
            CRMLead.source_ref_id,
            CRMLead.associated_partner_id,
            CRMLead.created_by_type,
            CRMLead.deal_value_received,
            eff_dv_expr.label("eff_dv"),
        )
        .filter(
            or_(
                CRMLead.solar_pipeline_status.isnot(None),
                CRMLead.status.in_(POST_WON),
            )
        )
        .all()
    )

    revenue_submitted_month = 0.0
    revenue_won_month = 0.0
    revenue_collected_month = 0.0

    files_from_vgk = 0
    files_from_company = 0
    files_from_staff = 0

    overall_completed_installations = 0
    this_month_installations = 0

    pending_for_installations = 0
    second_payment_pending = 0
    discom_pending = 0
    dcr_pending = 0
    eb_cust = 0
    eb_staff = 0

    for l in solar_leads:
        st = (l.status or "").strip().lower()
        ps = (l.solar_pipeline_status or "").strip().lower() if l.solar_pipeline_status else None
        dv = float(l.eff_dv or 0.0)
        recv = float(l.deal_value_received or 0.0)

        c_date = l.created_at.date() if (l.created_at and hasattr(l.created_at, "date")) else l.created_at
        tr_date = l.submit_date or c_date
        cl_date = (
            l.actual_close_date.date()
            if (l.actual_close_date and hasattr(l.actual_close_date, "date"))
            else l.actual_close_date
        )
        won_date = l.submit_date or cl_date or tr_date
        ps_upd_date = (
            l.solar_pipeline_status_updated_at.date()
            if (l.solar_pipeline_status_updated_at and hasattr(l.solar_pipeline_status_updated_at, "date"))
            else l.solar_pipeline_status_updated_at
        )
        inst_date = l.installation_date or ps_upd_date or l.complete_date or tr_date

        is_won = (st in POST_WON) and (ps is None or ps not in EXCL_WON_PS)
        is_not_dead = st not in ("lost", "cancelled")

        # Current month Won Revenue
        if is_won and won_date and won_date >= month_start_date:
            revenue_won_month += dv
            revenue_collected_month += recv

        # Current month Submitted Files & Submitted Revenue
        if ps is not None and ps not in ("cancelled", "not_interested", "bank_not_interested"):
            if tr_date and tr_date >= month_start_date:
                revenue_submitted_month += dv

                # Classify file origin: VGK Member vs Staff vs Company
                src_str = (l.source or "").strip().lower()
                sref_type = (l.source_ref_type or "").strip().lower()

                is_vgk_file = (
                    sref_type in ("vgk", "vgk_partner", "partner", "vgk4u")
                    or l.associated_partner_id is not None
                    or "vgk" in src_str
                    or "partner" in src_str
                )
                is_staff_file = not is_vgk_file and (
                    sref_type in ("staff", "self", "mn_staff", "staff_personal")
                    or src_str in ("self lead", "staff personal", "staff lead", "self", "staff")
                    or "self" in src_str
                )

                if is_vgk_file:
                    files_from_vgk += 1
                elif is_staff_file:
                    files_from_staff += 1
                else:
                    files_from_company += 1

        # Installations (Overall vs Current Month)
        is_installed_lead = (
            ps in INSTALLED_PS
            or l.installation_date is not None
        ) and (st in POST_WON)

        if is_installed_lead:
            overall_completed_installations += 1
            if inst_date and inst_date >= month_start_date:
                this_month_installations += 1

        # Active Solar Stage Counts
        if is_not_dead and ps:
            if ps == "installation_pending":
                pending_for_installations += 1
            elif ps == "balance_pending":
                second_payment_pending += 1
            elif ps == "discom_pending":
                discom_pending += 1
            elif ps == "dcr_pending":
                dcr_pending += 1
            elif ps in ("eb_cust", "electricity_bill_change"):
                eb_cust += 1
            elif ps == "eb_staff":
                eb_staff += 1

    # Primary current month revenue: use submitted_value if > 0 (matches Monthly Trend SUB VALUE ₹14.00L), fallback to won_value
    primary_month_revenue = revenue_submitted_month if revenue_submitted_month > 0 else revenue_won_month

    # Member Interaction SLAs (Members with active files: 3-day zero calls & 24-hour <5m talktime)
    members_with_files_total = 0
    members_no_interaction_3d_count = 0
    members_no_interaction_3d_names: List[str] = []
    members_low_talktime_24h_count = 0
    members_low_talktime_24h_names: List[str] = []

    try:
        dt_3d = ist_now - datetime.timedelta(days=3)
        dt_24h = ist_now - datetime.timedelta(hours=24)

        sql_sla = text(
            """
            WITH partner_files AS (
                SELECT 
                    p.id, 
                    p.partner_name, 
                    p.phone,
                    RIGHT(REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g'), 10) AS clean_phone,
                    COUNT(l.id) AS files_count
                FROM official_partners p
                JOIN crm_leads l ON l.associated_partner_id = p.id
                WHERE p.category = 'VGK_TEAM' 
                  AND (p.is_blocked IS NOT TRUE)
                  AND l.status NOT IN ('lost', 'cancelled')
                  AND p.phone IS NOT NULL AND p.phone != ''
                GROUP BY p.id, p.partner_name, p.phone
                HAVING COUNT(l.id) > 0
            ),
            partner_calls_3d AS (
                SELECT 
                    RIGHT(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g'), 10) AS phone10,
                    duration_seconds,
                    call_datetime AS call_time
                FROM staff_call_logs
                WHERE call_datetime >= :dt_3d
                  AND phone_number IS NOT NULL AND phone_number != ''
            ),
            op_calls_3d AS (
                SELECT
                    RIGHT(REGEXP_REPLACE(COALESCE(called_number, caller_number), '[^0-9]', '', 'g'), 10) AS phone10,
                    duration_seconds,
                    started_at AS call_time
                FROM operator_calls
                WHERE started_at >= :dt_3d
                  AND (called_number IS NOT NULL OR caller_number IS NOT NULL)
            ),
            combined_calls AS (
                SELECT * FROM partner_calls_3d
                UNION ALL
                SELECT * FROM op_calls_3d
            ),
            aggregated_partner_interactions AS (
                SELECT 
                    pf.id,
                    pf.partner_name,
                    pf.files_count,
                    COUNT(cc.phone10) AS total_calls_3d,
                    COALESCE(SUM(CASE WHEN cc.call_time >= :dt_24h THEN cc.duration_seconds ELSE 0 END), 0) AS talktime_24h_sec
                FROM partner_files pf
                LEFT JOIN combined_calls cc ON cc.phone10 = pf.clean_phone
                GROUP BY pf.id, pf.partner_name, pf.files_count
            )
            SELECT 
                id, partner_name, files_count, total_calls_3d, talktime_24h_sec
            FROM aggregated_partner_interactions
            ORDER BY files_count DESC, partner_name ASC
            """
        )

        rows_sla = db.execute(sql_sla, {"dt_3d": dt_3d, "dt_24h": dt_24h}).fetchall()
        members_with_files_total = len(rows_sla)

        for r in rows_sla:
            p_name = (r[1] or "").strip()
            calls_3d = r[3] or 0
            tt_24h = r[4] or 0

            if calls_3d == 0:
                members_no_interaction_3d_count += 1
                if p_name and p_name not in members_no_interaction_3d_names:
                    members_no_interaction_3d_names.append(p_name)

            if tt_24h < 300:  # < 5 minutes (300 seconds) talktime in last 24h
                members_low_talktime_24h_count += 1
                if p_name and p_name not in members_low_talktime_24h_names:
                    members_low_talktime_24h_names.append(p_name)

    except Exception as e:
        logger.warning(f"[HAR-GHAR-REPORT] Error querying member interaction SLAs: {e}")
        db.rollback()

    return {
        "month_label": month_label,
        "timestamp_ist": ist_now.strftime("%d %b %Y, %I:%M %p"),
        "leads_at_bank": leads_at_bank,
        "leads_at_bank_all": leads_at_bank_all,
        "new_vgk_members_current_month": new_vgk_members_current_month,
        "revenue_current_month": primary_month_revenue,
        "revenue_current_month_formatted": _format_inr_short(primary_month_revenue),
        "revenue_won_month": revenue_won_month,
        "revenue_won_month_formatted": _format_inr_short(revenue_won_month),
        "revenue_collected_month": revenue_collected_month,
        "revenue_collected_month_formatted": _format_inr_short(revenue_collected_month),
        "files_from_vgk": files_from_vgk,
        "files_from_company": files_from_company,
        "files_from_staff": files_from_staff,
        "total_files_current_month": files_from_vgk + files_from_company + files_from_staff,
        "overall_completed_installations": overall_completed_installations,
        "this_month_installations": this_month_installations,
        "pending_for_installations": pending_for_installations,
        "second_payment_pending": second_payment_pending,
        "discom_pending": discom_pending,
        "dcr_pending": dcr_pending,
        "eb_cust": eb_cust,
        "eb_staff": eb_staff,
        "members_with_files_total": members_with_files_total,
        "members_no_interaction_3d_count": members_no_interaction_3d_count,
        "members_no_interaction_3d_names": members_no_interaction_3d_names,
        "members_low_talktime_24h_count": members_low_talktime_24h_count,
        "members_low_talktime_24h_names": members_low_talktime_24h_names,
    }


def search_active_members_for_ground(db: Session, query_str: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    """
    Searches active Staff Employees and active VGK Members/Partners for '2. People On Ground' selection.
    """
    q = (query_str or "").strip()
    results: List[Dict[str, Any]] = []

    # 1. Active Staff Employees
    try:
        sql_staff = """
            SELECT e.id, e.emp_code, e.full_name, e.phone, COALESCE(d.name, 'Staff') AS dept_name
            FROM staff_employees e
            LEFT JOIN staff_departments d ON d.id = e.department_id
            WHERE (e.status IS NULL OR e.status = 'active')
              AND (e.is_deleted IS NOT TRUE)
              AND e.full_name IS NOT NULL AND e.full_name != ''
        """
        params: Dict[str, Any] = {"lim": limit}
        if q:
            sql_staff += " AND (e.full_name ILIKE :q OR e.emp_code ILIKE :q OR COALESCE(e.phone, '') ILIKE :q)"
            params["q"] = f"%{q}%"
        sql_staff += " ORDER BY e.full_name ASC LIMIT :lim"
        staff_rows = db.execute(text(sql_staff), params).fetchall()
        for r in staff_rows:
            results.append(
                {
                    "id": f"staff_{r.id}",
                    "code": r.emp_code or f"EMP#{r.id}",
                    "name": (r.full_name or "").strip(),
                    "type": "Staff",
                    "dept": r.dept_name or "Staff",
                    "phone": r.phone or "",
                }
            )
    except Exception as e:
        logger.warning(f"[HAR-GHAR-REPORT] Staff search error: {e}")
        db.rollback()

    # 2. Active VGK Team Members
    try:
        sql_vgk = """
            SELECT id, partner_code, partner_name, phone, COALESCE(city, district, '') AS loc
            FROM official_partners
            WHERE category = 'VGK_TEAM'
              AND (is_blocked IS NOT TRUE)
              AND partner_name IS NOT NULL AND partner_name != ''
        """
        params_v: Dict[str, Any] = {"lim": limit}
        if q:
            sql_vgk += " AND (partner_name ILIKE :q OR partner_code ILIKE :q OR COALESCE(phone, '') ILIKE :q)"
            params_v["q"] = f"%{q}%"
        sql_vgk += " ORDER BY partner_name ASC LIMIT :lim"
        vgk_rows = db.execute(text(sql_vgk), params_v).fetchall()
        for r in vgk_rows:
            results.append(
                {
                    "id": f"vgk_{r.id}",
                    "code": r.partner_code or f"VGK#{r.id}",
                    "name": (r.partner_name or "").strip(),
                    "type": "VGK Member",
                    "dept": r.loc or "VGK Team",
                    "phone": r.phone or "",
                }
            )
    except Exception as e:
        logger.warning(f"[HAR-GHAR-REPORT] VGK member search error: {e}")
        db.rollback()

    return results[:limit]


def search_expected_bank_customers(db: Session, query_str: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    """
    Searches CRM Leads (prioritizing leads 'pending_with_bank' / Solar leads) for
    '3. Expected Payments From Bank' customer selection.
    """
    from app.models.crm import CRMLead

    q = (query_str or "").strip()
    base = db.query(CRMLead).filter(
        ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"])
    )
    if q:
        base = base.filter(
            or_(
                CRMLead.name.ilike(f"%{q}%"),
                CRMLead.phone.ilike(f"%{q}%"),
                CRMLead.loan_bank.ilike(f"%{q}%"),
                CRMLead.bank_branch.ilike(f"%{q}%"),
                CRMLead.city.ilike(f"%{q}%"),
            )
        )
    else:
        # When no search term is typed yet, show leads currently At Bank first
        base = base.filter(CRMLead.solar_pipeline_status == "pending_with_bank")

    priority_order = case(
        (CRMLead.solar_pipeline_status == "pending_with_bank", 0),
        (CRMLead.solar_pipeline_status.isnot(None), 1),
        else_=2,
    )
    rows = (
        base.order_by(priority_order, CRMLead.updated_at.desc(), CRMLead.id.desc())
        .limit(limit)
        .all()
    )

    customers: List[Dict[str, Any]] = []
    for l in rows:
        customers.append(
            {
                "id": l.id,
                "name": (l.name or f"Lead #{l.id}").strip(),
                "phone": l.phone or "",
                "loan_bank": l.loan_bank or "",
                "bank_branch": l.bank_branch or "",
                "solar_pipeline_status": l.solar_pipeline_status or l.status or "",
                "city": l.city or l.area or "",
                "deal_value": float(l.confirmed_final_value or l.deal_value_total or l.deal_value or 0),
            }
        )
    return customers


def format_har_ghar_support_whatsapp_message(
    metrics: Dict[str, Any],
    people_on_ground: Optional[List[str]] = None,
    expected_bank_customers: Optional[List[str]] = None,
    include_manual: bool = False,
    slot_label: Optional[str] = None,
) -> str:
    """
    Formats the WhatsApp message for 'Har ghar support' group.
    - Contiguous serial numbering (1 to 14) for all core pipeline & installation metrics.
    - Separate section below for Field & Bank Operations (People On Ground & Expected Payments From Bank).
    - Separate section below for Member Interaction SLAs (3-day zero calls & 24h <5m talktime).
    """
    ist_now = _get_ist_now()
    date_str = ist_now.strftime("%d %b %Y")
    time_str = ist_now.strftime("%I:%M %p")
    header_slot = f" ({slot_label})" if slot_label else ""

    clean_people = [str(p).strip() for p in (people_on_ground or []) if str(p).strip()]
    clean_custs = [str(c).strip() for c in (expected_bank_customers or []) if str(c).strip()]

    lines = [
        f"☀️ *HAR GHAR SOLAR — STATUS REPORT{header_slot}*",
        f"📅 *{date_str}* | ⏰ *{time_str} IST*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"1. No. of Leads At Bank - *{metrics.get('leads_at_bank', 0)}*",
        f"2. New VGK Members (Current Month) - *{metrics.get('new_vgk_members_current_month', 0)}*",
        f"3. Files From VGK members - *{metrics.get('files_from_vgk', 0)}*",
        f"4. Files from the Company - *{metrics.get('files_from_company', 0)}*",
        f"5. Files from Staff - *{metrics.get('files_from_staff', 0)}*",
        f"6. Overall Completed Installations - *{metrics.get('overall_completed_installations', 0)}*",
        f"7. This Month Installations - *{metrics.get('this_month_installations', 0)}*",
        f"8. Pending for Installations - *{metrics.get('pending_for_installations', 0)}*",
        f"9. 2nd payment pending - *{metrics.get('second_payment_pending', 0)}*",
        f"10. Discom Pending - *{metrics.get('discom_pending', 0)}*",
        f"11. DCR Pending - *{metrics.get('dcr_pending', 0)}*",
        f"12. EB Cust. - *{metrics.get('eb_cust', 0)}*",
        f"13. EB Staff - *{metrics.get('eb_staff', 0)}*",
    ]

    # Separate section below: Field & Bank Operations (People On Ground & Expected Payments From Bank)
    if include_manual or clean_people or clean_custs:
        people_cnt = len(clean_people)
        people_names_str = f" ({', '.join(clean_people)})" if clean_people else ""
        cust_cnt = len(clean_custs)
        cust_names_str = f" ({', '.join(clean_custs)})" if clean_custs else ""

        lines.extend(
            [
                "━━━━━━━━━━━━━━━━━━━━━━━━",
                "👥 *FIELD & BANK OPERATIONS:*",
                f"• People On Ground - *{people_cnt}*{people_names_str}",
                f"• Expected Payments From Bank - *{cust_cnt}*{cust_names_str}",
            ]
        )

    # Separate section below: Member Interactions SLA (Members with Active Files)
    no_int_3d = metrics.get("members_no_interaction_3d_count", 0)
    low_tt_24h = metrics.get("members_low_talktime_24h_count", 0)

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "📞 *MEMBER INTERACTIONS (With Active Files):*",
            f"• Members Without Interaction (Last 3 Days) - *{no_int_3d}*",
            f"• Members With <5 Mins Talktime (Last 24 Hours) - *{low_tt_24h}*",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
    )

    return "\n".join(lines)


def dispatch_har_ghar_support_report(
    db: Session,
    people_on_ground: Optional[List[str]] = None,
    expected_bank_customers: Optional[List[str]] = None,
    include_manual: bool = False,
    slot_label: Optional[str] = None,
    trigger_type: str = "SCHEDULED",
    triggered_by: str = "APScheduler",
    group_name: str = HAR_GHAR_GROUP_NAME,
    custom_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes live metrics, formats the Har Ghar Support WhatsApp message, and dispatches
    it to the 'Har ghar support' WhatsApp group via Scanned WhatsApp Bot.
    """
    metrics = get_har_ghar_support_report_metrics(db)
    message_text = (
        custom_message.strip()
        if (custom_message and custom_message.strip())
        else format_har_ghar_support_whatsapp_message(
            metrics=metrics,
            people_on_ground=people_on_ground,
            expected_bank_customers=expected_bank_customers,
            include_manual=include_manual,
            slot_label=slot_label,
        )
    )

    # Check if custom targets are configured in automation_target_configs
    target_group_name = group_name or HAR_GHAR_GROUP_NAME
    target_invite_code = ""
    try:
        row = db.execute(
            text("SELECT targets_json FROM automation_target_configs WHERE job_id = :jid"),
            {"jid": JOB_ID_HAR_GHAR_REPORT},
        ).fetchone()
        if row and row[0]:
            import json

            targets = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if isinstance(targets, list) and len(targets) > 0:
                t0 = targets[0]
                if t0.get("name"):
                    target_group_name = t0["name"]
                ident = (t0.get("identifier") or "").strip()
                if ident and ("@g.us" in ident or "chat.whatsapp.com" in ident):
                    target_invite_code = ident
    except Exception:
        db.rollback()

    ist_now = _get_ist_now()
    idemp_key = f"har_ghar_support_{ist_now.strftime('%Y%m%d_%H%M')}_{trigger_type}"

    bot_res = send_group_bot_message(
        message_text=message_text,
        invite_code=target_invite_code,
        group_name=target_group_name,
        job_id=JOB_ID_HAR_GHAR_REPORT,
        job_name="Har Ghar Support Daily Status Report (9 AM & 8 PM)",
        trigger_type=trigger_type,
        db=db,
        idempotency_key=idemp_key,
    )

    is_ok = bool(bot_res.get("success"))
    return {
        "success": is_ok,
        "group_name": target_group_name,
        "trigger_type": trigger_type,
        "triggered_by": triggered_by,
        "message_text": message_text,
        "metrics": metrics,
        "bot_response": bot_res,
        "error": None if is_ok else (bot_res.get("error") or "Failed to dispatch to WhatsApp group"),
    }


def get_har_ghar_parameter_drilldown(db: Session, parameter: str, limit: int = 200) -> Dict[str, Any]:
    """
    Returns rich, detailed records for ANY Har Ghar Report parameter for interactive drilldown.
    Supported parameters:
    - 'no_interaction_3d': Members with files having 0 calls in last 3 days
    - 'low_talktime_24h': Members with files having <5 mins talktime in last 24h
    - 'new_vgk_members': VGK team members created in current month
    - 'leads_at_bank': Leads pending with bank
    - 'overall_completed_installations': Installed leads
    - 'this_month_installations': Installed leads in current month
    - 'pending_for_installations': Leads with solar_pipeline_status = 'installation_pending'
    - 'second_payment_pending': Leads with solar_pipeline_status = 'balance_pending'
    - 'discom_pending': Leads with solar_pipeline_status = 'discom_pending'
    - 'dcr_pending': Leads with solar_pipeline_status = 'dcr_pending'
    - 'eb_cust': Leads with solar_pipeline_status in ('eb_cust', 'electricity_bill_change')
    - 'eb_staff': Leads with solar_pipeline_status = 'eb_staff'
    - 'files_from_vgk': Current month submitted files from VGK
    - 'files_from_company': Current month submitted files from Company
    - 'files_from_staff': Current month submitted files from Staff
    """
    param = (parameter or "").strip().lower()
    ist_now = _get_ist_now()
    today = ist_now.date()
    month_start_date = datetime.date(today.year, today.month, 1)
    month_start_dt = datetime.datetime.combine(month_start_date, datetime.time.min)

    POST_WON = ["won", "order_placed", "dispatched", "delivered", "installed", "completed"]
    INSTALLED_PS = [
        "installed",
        "dcr_pending",
        "discom_pending",
        "net_meter_pending",
        "balance_pending",
        "balance_received",
        "subsidy_pending",
        "completed",
    ]

    records: List[Dict[str, Any]] = []
    title = "Parameter Details"
    record_type = "lead"

    # 1. Member Interaction: No Interaction in last 3 days
    if param in ("no_interaction_3d", "members_no_interaction_3d", "no_int_3d"):
        record_type = "member"
        title = "Members Without Interaction (Last 3 Days)"
        dt_3d = ist_now - datetime.timedelta(days=3)
        sql = text(
            """
            WITH partner_files AS (
                SELECT 
                    p.id, 
                    p.partner_code,
                    p.partner_name, 
                    p.phone,
                    COALESCE(p.city, p.district, '') AS location,
                    RIGHT(REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g'), 10) AS clean_phone,
                    COUNT(l.id) AS files_count,
                    STRING_AGG(DISTINCT l.name, ', ') AS lead_names
                FROM official_partners p
                JOIN crm_leads l ON l.associated_partner_id = p.id
                WHERE p.category = 'VGK_TEAM' 
                  AND (p.is_blocked IS NOT TRUE)
                  AND l.status NOT IN ('lost', 'cancelled')
                  AND p.phone IS NOT NULL AND p.phone != ''
                GROUP BY p.id, p.partner_code, p.partner_name, p.phone, p.city, p.district
                HAVING COUNT(l.id) > 0
            ),
            partner_calls_all AS (
                SELECT 
                    RIGHT(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g'), 10) AS phone10,
                    duration_seconds,
                    call_datetime AS call_time
                FROM staff_call_logs
                WHERE phone_number IS NOT NULL AND phone_number != ''
            ),
            aggregated AS (
                SELECT 
                    pf.id,
                    pf.partner_code,
                    pf.partner_name,
                    pf.phone,
                    pf.location,
                    pf.files_count,
                    pf.lead_names,
                    COUNT(CASE WHEN pc.call_time >= :dt_3d THEN 1 END) AS calls_3d,
                    MAX(pc.call_time) AS last_call_time
                FROM partner_files pf
                LEFT JOIN partner_calls_all pc ON pc.phone10 = pf.clean_phone
                GROUP BY pf.id, pf.partner_code, pf.partner_name, pf.phone, pf.location, pf.files_count, pf.lead_names
            )
            SELECT 
                id, partner_code, partner_name, phone, location, files_count, calls_3d, last_call_time, lead_names
            FROM aggregated
            WHERE calls_3d = 0
            ORDER BY files_count DESC, partner_name ASC
            LIMIT :lim
            """
        )
        rows = db.execute(sql, {"dt_3d": dt_3d, "lim": limit}).fetchall()
        for r in rows:
            last_c = r[7].strftime("%d %b %Y, %I:%M %p") if r[7] else "No calls logged"
            records.append({
                "id": r[0],
                "code": r[1] or f"VGK#{r[0]}",
                "name": (r[2] or "").strip(),
                "phone": r[3] or "",
                "location": r[4] or "—",
                "files_count": r[5] or 0,
                "calls_count": r[6] or 0,
                "status_badge": "0 Calls (72h)",
                "status_color": "#dc2626",
                "last_interaction": last_c,
                "lead_names": r[8] or "",
            })

    # 2. Member Interaction: <5 mins talktime in last 24h
    elif param in ("low_talktime_24h", "members_low_talktime_24h", "low_tt_24h"):
        record_type = "member"
        title = "Members With <5 Mins Talktime (Last 24 Hours)"
        dt_24h = ist_now - datetime.timedelta(hours=24)
        sql = text(
            """
            WITH partner_files AS (
                SELECT 
                    p.id, 
                    p.partner_code,
                    p.partner_name, 
                    p.phone,
                    COALESCE(p.city, p.district, '') AS location,
                    RIGHT(REGEXP_REPLACE(p.phone, '[^0-9]', '', 'g'), 10) AS clean_phone,
                    COUNT(l.id) AS files_count,
                    STRING_AGG(DISTINCT l.name, ', ') AS lead_names
                FROM official_partners p
                JOIN crm_leads l ON l.associated_partner_id = p.id
                WHERE p.category = 'VGK_TEAM' 
                  AND (p.is_blocked IS NOT TRUE)
                  AND l.status NOT IN ('lost', 'cancelled')
                  AND p.phone IS NOT NULL AND p.phone != ''
                GROUP BY p.id, p.partner_code, p.partner_name, p.phone, p.city, p.district
                HAVING COUNT(l.id) > 0
            ),
            partner_calls_all AS (
                SELECT 
                    RIGHT(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g'), 10) AS phone10,
                    duration_seconds,
                    call_datetime AS call_time
                FROM staff_call_logs
                WHERE phone_number IS NOT NULL AND phone_number != ''
            ),
            aggregated AS (
                SELECT 
                    pf.id,
                    pf.partner_code,
                    pf.partner_name,
                    pf.phone,
                    pf.location,
                    pf.files_count,
                    pf.lead_names,
                    COALESCE(SUM(CASE WHEN pc.call_time >= :dt_24h THEN pc.duration_seconds ELSE 0 END), 0) AS talktime_24h_sec,
                    COUNT(CASE WHEN pc.call_time >= :dt_24h THEN 1 END) AS calls_24h,
                    MAX(pc.call_time) AS last_call_time
                FROM partner_files pf
                LEFT JOIN partner_calls_all pc ON pc.phone10 = pf.clean_phone
                GROUP BY pf.id, pf.partner_code, pf.partner_name, pf.phone, pf.location, pf.files_count, pf.lead_names
            )
            SELECT 
                id, partner_code, partner_name, phone, location, files_count, talktime_24h_sec, calls_24h, last_call_time, lead_names
            FROM aggregated
            WHERE talktime_24h_sec < 300
            ORDER BY files_count DESC, partner_name ASC
            LIMIT :lim
            """
        )
        rows = db.execute(sql, {"dt_24h": dt_24h, "lim": limit}).fetchall()
        for r in rows:
            sec = r[6] or 0
            tt_fmt = f"{sec // 60}m {sec % 60}s" if sec >= 60 else f"{sec}s"
            last_c = r[8].strftime("%d %b %Y, %I:%M %p") if r[8] else "No calls logged"
            records.append({
                "id": r[0],
                "code": r[1] or f"VGK#{r[0]}",
                "name": (r[2] or "").strip(),
                "phone": r[3] or "",
                "location": r[4] or "—",
                "files_count": r[5] or 0,
                "calls_count": r[7] or 0,
                "talktime_formatted": tt_fmt,
                "status_badge": f"{tt_fmt} (<5m)",
                "status_color": "#d97706",
                "last_interaction": last_c,
                "lead_names": r[9] or "",
            })

    # 3. New VGK Members (Current Month)
    elif param in ("new_vgk_members", "new_vgk_members_current_month"):
        record_type = "member"
        title = "2. New VGK Members (Current Month)"
        sql = text(
            """
            SELECT id, partner_code, partner_name, phone, COALESCE(city, district, '') AS loc, created_at
            FROM official_partners
            WHERE category = 'VGK_TEAM'
              AND (partner_type IS NULL OR partner_type != 'FREELANCER')
              AND (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') >= :m_start
            ORDER BY created_at DESC
            LIMIT :lim
            """
        )
        rows = db.execute(sql, {"m_start": month_start_dt, "lim": limit}).fetchall()
        for r in rows:
            c_at = r[5].strftime("%d %b %Y") if r[5] else "—"
            records.append({
                "id": r[0],
                "code": r[1] or f"VGK#{r[0]}",
                "name": (r[2] or "").strip(),
                "phone": r[3] or "",
                "location": r[4] or "—",
                "status_badge": "Joined this month",
                "status_color": "#16a34a",
                "last_interaction": c_at,
            })

    # 4. All Other Lead-Based Parameters
    else:
        record_type = "lead"
        from app.models.crm import CRMLead

        base_query = db.query(CRMLead)
        if param in ("leads_at_bank", "leads_at_bank_all"):
            title = "1. Leads At Bank"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "pending_with_bank",
                CRMLead.status.in_(POST_WON),
            )
        elif param in ("overall_completed_installations", "installations_overall"):
            title = "7. Overall Completed Installations"
            base_query = base_query.filter(
                CRMLead.status.in_(POST_WON),
                or_(
                    CRMLead.solar_pipeline_status.in_(INSTALLED_PS),
                    CRMLead.installation_date.isnot(None),
                ),
            )
        elif param in ("this_month_installations", "installations_month"):
            title = "8. This Month Installations"
            base_query = base_query.filter(
                CRMLead.status.in_(POST_WON),
                or_(
                    CRMLead.solar_pipeline_status.in_(INSTALLED_PS),
                    CRMLead.installation_date.isnot(None),
                ),
                or_(
                    CRMLead.installation_date >= month_start_date,
                    CRMLead.complete_date >= month_start_date,
                ),
            )
        elif param in ("pending_for_installations", "pending_installations"):
            title = "9. Pending for Installations"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "installation_pending",
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param in ("second_payment_pending", "2nd_payment_pending"):
            title = "10. 2nd Payment Pending"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "balance_pending",
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param == "discom_pending":
            title = "11. Discom Pending"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "discom_pending",
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param == "dcr_pending":
            title = "12. DCR Pending"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "dcr_pending",
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param in ("eb_cust", "electricity_bill_cust"):
            title = "13. Electricity Bill Cust."
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status.in_(["eb_cust", "electricity_bill_change"]),
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param in ("eb_staff", "electricity_bill_staff"):
            title = "14. Electricity Bill Staff"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status == "eb_staff",
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )
        elif param in ("files_from_vgk", "vgk_files"):
            title = "4. Files From VGK Members (Current Month)"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status.isnot(None),
                ~CRMLead.solar_pipeline_status.in_(["cancelled", "not_interested", "bank_not_interested"]),
                or_(
                    CRMLead.submit_date >= month_start_date,
                    and_(CRMLead.submit_date.is_(None), func.date(CRMLead.created_at) >= month_start_date),
                ),
                or_(
                    CRMLead.associated_partner_id.isnot(None),
                    func.lower(CRMLead.source).ilike("%vgk%"),
                    func.lower(CRMLead.source).ilike("%partner%"),
                ),
            )
        elif param in ("files_from_staff", "staff_files"):
            title = "6. Files From Staff (Current Month)"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status.isnot(None),
                ~CRMLead.solar_pipeline_status.in_(["cancelled", "not_interested", "bank_not_interested"]),
                or_(
                    CRMLead.submit_date >= month_start_date,
                    and_(CRMLead.submit_date.is_(None), func.date(CRMLead.created_at) >= month_start_date),
                ),
                CRMLead.associated_partner_id.is_(None),
                or_(
                    func.lower(CRMLead.source).ilike("%staff%"),
                    func.lower(CRMLead.source).ilike("%self%"),
                ),
            )
        elif param in ("files_from_company", "company_files"):
            title = "5. Files From Company (Current Month)"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status.isnot(None),
                ~CRMLead.solar_pipeline_status.in_(["cancelled", "not_interested", "bank_not_interested"]),
                or_(
                    CRMLead.submit_date >= month_start_date,
                    and_(CRMLead.submit_date.is_(None), func.date(CRMLead.created_at) >= month_start_date),
                ),
                CRMLead.associated_partner_id.is_(None),
                ~func.lower(func.coalesce(CRMLead.source, "")).ilike("%staff%"),
                ~func.lower(func.coalesce(CRMLead.source, "")).ilike("%self%"),
                ~func.lower(func.coalesce(CRMLead.source, "")).ilike("%vgk%"),
            )
        else:
            title = f"Parameter Details: {param}"
            base_query = base_query.filter(
                CRMLead.solar_pipeline_status.isnot(None),
                ~func.lower(func.coalesce(CRMLead.status, "")).in_(["lost", "cancelled"]),
            )

        leads_list = base_query.order_by(CRMLead.updated_at.desc(), CRMLead.id.desc()).limit(limit).all()
        for l in leads_list:
            dv = float(l.confirmed_final_value or l.deal_value_total or l.deal_value or 0)
            st_text = (l.solar_pipeline_status or l.status or "Active").replace("_", " ").title()
            dt_show = (
                l.submit_date.strftime("%d %b %Y")
                if l.submit_date
                else (l.created_at.strftime("%d %b %Y") if l.created_at else "—")
            )
            records.append({
                "id": l.id,
                "code": f"LEAD#{l.id}",
                "name": (l.name or f"Lead #{l.id}").strip(),
                "phone": l.phone or "",
                "location": l.city or l.area or "—",
                "deal_value_formatted": _format_inr_short(dv),
                "deal_value": dv,
                "status_badge": st_text,
                "status_color": "#0284c7" if "Bank" in st_text else "#059669",
                "bank": l.loan_bank or "",
                "branch": l.bank_branch or "",
                "submit_date": dt_show,
            })

    return {
        "success": True,
        "parameter": param,
        "title": title,
        "record_type": record_type,
        "total": len(records),
        "records": records,
    }
