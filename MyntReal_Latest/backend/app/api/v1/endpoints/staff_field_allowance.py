"""
Staff Field Allowance Management Endpoints
DC Protocol Feb 2026 - Staff Portal exclusive field allowance management
Mirrors bonanza eligibility tracking pattern with monthly payout workflow
Computes LIVE eligibility from actual user data (same as user-facing pages)
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional, Dict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.base import get_indian_time
from app.models.user import User
from app.models.field_allowance import (
    FieldAllowanceEligibility,
    CarAllowanceEligibility,
    FieldAllowanceProgress
)
from app.services.field_allowance_service import FieldAllowanceService, FIELD_ALLOWANCE_CUTOFF_DATE

router = APIRouter(prefix="/staff/field-allowances", tags=["Staff Field Allowance"])


def _get_start_date_for_user(user) -> Optional[datetime]:
    """Same logic as FieldAllowanceService._get_field_allowance_start_date"""
    activation_date = getattr(user, 'activation_date', None)
    if not activation_date:
        return datetime.combine(FIELD_ALLOWANCE_CUTOFF_DATE, datetime.min.time())
    activation_date_only = activation_date.date() if isinstance(activation_date, datetime) else activation_date
    if activation_date_only >= FIELD_ALLOWANCE_CUTOFF_DATE:
        return activation_date
    else:
        return datetime.combine(FIELD_ALLOWANCE_CUTOFF_DATE, datetime.min.time())


def _compute_standard_status(direct_points: float, start_date, now, std_rec) -> Dict:
    """Compute standard allowance status from live data, matching user-facing logic"""
    std_directs_required = 7
    is_opportunity_missed = False

    if std_rec and std_rec.overall_status == 'Active':
        return {
            "status": "Active",
            "current": float(direct_points),
            "required": std_directs_required,
            "pct": min(100, round((direct_points / max(1, std_directs_required)) * 100, 1)),
            "monthly_current": getattr(std_rec, 'monthly_achieved_matchings', 0) or 0,
            "monthly_required": 20,
            "monthly_pct": 0,
            "months_completed": getattr(std_rec, 'months_completed', 0) or 0,
            "total_paid": float(getattr(std_rec, 'total_paid_to_date', 0) or 0),
            "deadline": None,
            "is_frozen": False,
        }

    deadline = start_date + timedelta(days=45) if start_date else None
    deadline_str = deadline.isoformat() if deadline else None

    if deadline and now > deadline and direct_points < std_directs_required:
        is_opportunity_missed = True

    is_eligible = direct_points >= std_directs_required
    if is_eligible:
        status = "Eligible"
    elif is_opportunity_missed:
        status = "Missed"
    else:
        status = "In Progress"

    pct = min(100, round((direct_points / max(1, std_directs_required)) * 100, 1))

    return {
        "status": status,
        "current": float(direct_points),
        "required": std_directs_required,
        "pct": pct,
        "monthly_current": 0,
        "monthly_required": 20,
        "monthly_pct": 0,
        "months_completed": 0,
        "total_paid": 0,
        "deadline": deadline_str,
        "is_frozen": is_opportunity_missed,
    }


def _compute_car_status_fast(user_id, start_date, now, car_rec) -> Dict:
    """Fast car allowance status for list views - uses eligibility records only, no tree traversal"""
    car_points_required = 250

    if car_rec and car_rec.overall_status == 'Active':
        return {
            "status": "Active",
            "current": getattr(car_rec, 'matching_referrals_count', 0) or 0,
            "required": car_points_required,
            "pct": 100,
            "monthly_current": getattr(car_rec, 'monthly_achieved_matchings', 0) or 0,
            "monthly_required": 40,
            "monthly_pct": 0,
            "months_completed": getattr(car_rec, 'months_completed', 0) or 0,
            "total_paid": float(getattr(car_rec, 'total_paid_to_date', 0) or 0),
            "deadline": None,
            "is_frozen": False,
        }

    if car_rec and car_rec.initial_eligibility_met:
        return {
            "status": "Eligible",
            "current": getattr(car_rec, 'matching_referrals_count', 0) or car_points_required,
            "required": car_points_required,
            "pct": 100,
            "monthly_current": 0,
            "monthly_required": 40,
            "monthly_pct": 0,
            "months_completed": 0,
            "total_paid": 0,
            "deadline": None,
            "is_frozen": False,
        }

    deadline = start_date + timedelta(days=90) if start_date else None
    deadline_str = deadline.isoformat() if deadline else None

    is_opportunity_missed = False
    if deadline and now > deadline:
        is_opportunity_missed = True

    return {
        "status": "Missed" if is_opportunity_missed else "In Progress",
        "current": 0,
        "required": car_points_required,
        "pct": 0,
        "monthly_current": 0,
        "monthly_required": 40,
        "monthly_pct": 0,
        "months_completed": 0,
        "total_paid": 0,
        "deadline": deadline_str,
        "is_frozen": is_opportunity_missed,
    }


def _compute_car_status_full(user_id, start_date, now, car_rec, db: Session) -> Dict:
    """Full car allowance status with binary tree traversal - use only for single-user detail views"""
    car_points_required = 250

    if car_rec and car_rec.overall_status == 'Active':
        return {
            "status": "Active",
            "current": getattr(car_rec, 'matching_referrals_count', 0) or 0,
            "required": car_points_required,
            "pct": 100,
            "monthly_current": getattr(car_rec, 'monthly_achieved_matchings', 0) or 0,
            "monthly_required": 40,
            "monthly_pct": 0,
            "months_completed": getattr(car_rec, 'months_completed', 0) or 0,
            "total_paid": float(getattr(car_rec, 'total_paid_to_date', 0) or 0),
            "deadline": None,
            "is_frozen": False,
        }

    try:
        qualification_status = FieldAllowanceService._check_binary_qualification(user_id, db)
        is_qualified = qualification_status.get("qualified", False)
        matching_points = FieldAllowanceService._get_matching_points_with_qualification(
            user_id, db, is_qualified
        )
    except Exception:
        matching_points = 0
        is_qualified = False

    deadline = start_date + timedelta(days=90) if start_date else None
    deadline_str = deadline.isoformat() if deadline else None

    is_opportunity_missed = False
    if deadline and now > deadline and matching_points < car_points_required:
        is_opportunity_missed = True

    display_points = matching_points if (is_qualified and not is_opportunity_missed) else 0

    is_eligible = display_points >= car_points_required
    if is_eligible:
        status = "Eligible"
    elif is_opportunity_missed:
        status = "Missed"
    elif not is_qualified:
        status = "Not Qualified"
    else:
        status = "In Progress"

    pct = min(100, round((display_points / max(1, car_points_required)) * 100, 1))

    return {
        "status": status,
        "current": display_points,
        "required": car_points_required,
        "pct": pct,
        "monthly_current": 0,
        "monthly_required": 40,
        "monthly_pct": 0,
        "months_completed": 0,
        "total_paid": 0,
        "deadline": deadline_str,
        "is_frozen": is_opportunity_missed,
    }


@router.get("/all-eligibility")
async def get_all_field_allowance_eligibility(
    allowance_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db)
):
    """
    Get all MNR users' field allowance eligibility status.
    Computes LIVE data from actual user referrals (same as user-facing pages).
    Staff Portal exclusive endpoint.
    """
    now = get_indian_time()

    std_by_user = {}
    car_by_user = {}
    std_records = db.query(FieldAllowanceEligibility).all()
    for r in std_records:
        std_by_user[r.user_id] = r
    car_records = db.query(CarAllowanceEligibility).all()
    for r in car_records:
        car_by_user[r.user_id] = r

    users_query = db.query(User).filter(
        User.coupon_status.in_(['Activated', 'Registered'])
    )

    if search:
        search_term = f"%{search}%"
        users_query = users_query.filter(
            (User.id.ilike(search_term)) | (User.name.ilike(search_term))
        )

    total_count = users_query.count()

    if sort_by == "std_progress":
        sort_subq = text("""
            SELECT r.referrer_id, COALESCE(SUM(r.package_points), 0) as pts
            FROM "user" r WHERE r.coupon_status = 'Activated' AND r.referrer_id IS NOT NULL
            GROUP BY r.referrer_id
        """)
        sort_sub = db.execute(sort_subq).fetchall()
        sort_map = {row[0]: float(row[1]) for row in sort_sub}

        all_user_ids_rows = users_query.with_entities(User.id).all()
        all_user_ids_list = [(uid[0], sort_map.get(str(uid[0]), 0)) for uid in all_user_ids_rows]
        all_user_ids_list.sort(key=lambda x: x[1], reverse=(sort_dir == "desc"))

        page_ids = [uid[0] for uid in all_user_ids_list[(page - 1) * per_page: page * per_page]]
        users = db.query(User).filter(User.id.in_(page_ids)).all()
        id_order = {uid: idx for idx, uid in enumerate(page_ids)}
        users.sort(key=lambda u: id_order.get(u.id, 0))
    else:
        users = users_query.order_by(User.name).offset((page - 1) * per_page).limit(per_page).all()

    user_ids = [str(u.id) for u in users]
    referral_points_map = {}
    if user_ids:
        referral_sql = text("""
            SELECT u.referrer_id, COALESCE(SUM(u.package_points), 0) as total_points
            FROM "user" u
            WHERE u.referrer_id = ANY(:ids) AND u.coupon_status = 'Activated'
            GROUP BY u.referrer_id
        """)
        referral_rows = db.execute(referral_sql, {"ids": user_ids}).fetchall()
        for row in referral_rows:
            referral_points_map[row[0]] = float(row[1])

    global_summary_sql = text("""
        SELECT
            COUNT(CASE WHEN ref_pts.total_points >= 7 THEN 1 END) as eligible_standard,
            COUNT(CASE WHEN fae.overall_status = 'Active' THEN 1 END) as active_standard,
            COUNT(CASE WHEN cae.overall_status = 'Active' THEN 1 END) as active_car,
            COUNT(CASE WHEN cae.initial_eligibility_met = true THEN 1 END) as eligible_car
        FROM "user" u
        LEFT JOIN (
            SELECT r.referrer_id, COALESCE(SUM(r.package_points), 0) as total_points
            FROM "user" r WHERE r.coupon_status = 'Activated' AND r.referrer_id IS NOT NULL
            GROUP BY r.referrer_id
        ) ref_pts ON u.id = ref_pts.referrer_id
        LEFT JOIN field_allowance_eligibility fae ON u.id = fae.user_id
        LEFT JOIN car_allowance_eligibility cae ON u.id = cae.user_id
        WHERE u.coupon_status IN ('Activated', 'Registered')
    """)
    global_summary_row = db.execute(global_summary_sql).fetchone()
    global_eligible_std = global_summary_row[0] if global_summary_row else 0
    global_active_std = global_summary_row[1] if global_summary_row else 0
    global_active_car = global_summary_row[2] if global_summary_row else 0
    global_eligible_car = global_summary_row[3] if global_summary_row else 0

    eligibility_data = []

    for user in users:
        user_id = str(user.id)

        is_activated = (getattr(user, 'coupon_status', '') == 'Activated')
        kyc_status = getattr(user, 'kyc_status', 'pending') or 'pending'
        kyc_approved = kyc_status.lower() == 'approved'
        activation_date = getattr(user, 'activation_date', None)

        start_date = _get_start_date_for_user(user)

        direct_points = referral_points_map.get(user_id, 0)

        std_rec = std_by_user.get(user_id)
        std_data = _compute_standard_status(direct_points, start_date, now, std_rec)

        car_rec = car_by_user.get(user_id)
        car_data = _compute_car_status_fast(user_id, start_date, now, car_rec)


        if allowance_type == "standard" and std_data["status"] in ["Not Started", "Not Eligible", "Missed"]:
            continue
        if allowance_type == "car" and car_data["status"] in ["Not Started", "Not Eligible", "Not Qualified", "Missed"]:
            continue

        if status_filter == "eligible" and std_data["status"] != "Active" and car_data["status"] != "Active":
            continue
        if status_filter == "not_eligible" and (std_data["status"] == "Active" or car_data["status"] == "Active"):
            continue

        active_allowance = None
        if car_data["status"] == "Active":
            active_allowance = "car"
        elif std_data["status"] == "Active":
            active_allowance = "standard"

        eligibility_data.append({
            "user_id": user_id,
            "user_name": user.name or "Unknown",
            "package": user.get_package_type() if hasattr(user, 'get_package_type') else (
                'Platinum' if (user.package_points or 0) >= 1.0 else
                'Diamond' if (user.package_points or 0) >= 0.5 else
                'Star/Loyal' if (user.package_points or 0) > 0 else 'Eligible'
            ),
            "activation_date": activation_date.isoformat() if activation_date else None,
            "eligibility_criteria": {
                "is_activated": is_activated,
                "kyc_approved": kyc_approved,
            },
            "standard_allowance": {
                "status": std_data["status"],
                "monthly_amount": 10000,
                "tenure_months": 18,
                "initial_progress": {
                    "current": std_data["current"],
                    "required": std_data["required"],
                    "percentage": std_data["pct"],
                },
                "monthly_progress": {
                    "current": std_data["monthly_current"],
                    "required": std_data["monthly_required"],
                    "percentage": std_data["monthly_pct"],
                },
                "months_completed": std_data["months_completed"],
                "total_paid": std_data["total_paid"],
                "deadline": std_data["deadline"],
            },
            "car_allowance": {
                "status": car_data["status"],
                "monthly_amount": 25000,
                "tenure_months": 72,
                "initial_progress": {
                    "current": car_data["current"],
                    "required": car_data["required"],
                    "percentage": car_data["pct"],
                },
                "monthly_progress": {
                    "current": car_data["monthly_current"],
                    "required": car_data["monthly_required"],
                    "percentage": car_data["monthly_pct"],
                },
                "months_completed": car_data["months_completed"],
                "total_paid": car_data["total_paid"],
                "deadline": car_data["deadline"],
            },
            "active_allowance": active_allowance,
        })

    if sort_by == "std_progress":
        eligibility_data.sort(
            key=lambda x: x["standard_allowance"]["initial_progress"]["current"],
            reverse=(sort_dir == "desc")
        )
    elif sort_by == "car_progress":
        eligibility_data.sort(
            key=lambda x: x["car_allowance"]["initial_progress"]["current"],
            reverse=(sort_dir == "desc")
        )

    summary = {
        "total_users": total_count,
        "eligible_standard": global_eligible_std,
        "eligible_car": global_eligible_car,
        "active_standard": global_active_std,
        "active_car": global_active_car,
        "not_eligible": max(0, total_count - (global_eligible_std + global_eligible_car))
    }

    return {
        "success": True,
        "summary": summary,
        "eligibility_data": eligibility_data,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total_count + per_page - 1) // per_page)
    }


@router.get("/payouts")
async def get_field_allowance_payouts(
    allowance_type: Optional[str] = None,
    payout_status: Optional[str] = None,
    month: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get monthly payout tracking for eligible field allowance users.
    Computes LIVE eligibility from actual user referral data.
    Users with 7+ direct referral POINTS = Standard eligible.
    Car eligibility from eligibility table records or 250+ matching points.
    Three-stage workflow: Pending -> Validated -> Payout Completed
    """
    now = get_indian_time()
    current_month = now.strftime("%Y-%m")

    progress_records = db.query(FieldAllowanceProgress).order_by(
        FieldAllowanceProgress.id.desc()
    ).all()
    progress_map = {}
    for p in progress_records:
        key = f"{p.user_id}_{p.allowance_type}"
        if key not in progress_map:
            progress_map[key] = p

    eligible_users_data = []

    if not allowance_type or allowance_type == "standard":
        std_eligible_sql = text("""
            SELECT u.id as user_id, u.name, u.activation_date, u.package_points,
                   COALESCE(ref.total_points, 0) as direct_points
            FROM "user" u
            LEFT JOIN (
                SELECT r.referrer_id, SUM(r.package_points) as total_points
                FROM "user" r
                WHERE r.coupon_status = 'Activated' AND r.referrer_id IS NOT NULL
                GROUP BY r.referrer_id
            ) ref ON u.id = ref.referrer_id
            WHERE u.coupon_status = 'Activated'
              AND COALESCE(ref.total_points, 0) >= 7
            ORDER BY ref.total_points DESC
        """)
        std_eligible_rows = db.execute(std_eligible_sql).fetchall()

        for row in std_eligible_rows:
            user_id = row[0]
            user_name = row[1] or "Unknown"
            direct_points = float(row[4])

            if search:
                if search.upper() not in user_id.upper() and search.lower() not in user_name.lower():
                    continue

            progress = progress_map.get(f"{user_id}_standard")
            payout_st = progress.status if progress else "Pending"

            if payout_status and payout_st != payout_status:
                continue

            months_completed = 0
            total_paid = 0.0
            std_progress_records = [p for p in progress_records
                                    if p.user_id == user_id and p.allowance_type == 'standard'
                                    and p.status == 'Payout Completed']
            months_completed = len(std_progress_records)
            total_paid = sum(float(p.amount_paid or 0) for p in std_progress_records)

            eligible_users_data.append({
                "user_id": user_id,
                "user_name": user_name,
                "allowance_type": "Standard",
                "monthly_amount": 10000,
                "tenure_months": 18,
                "months_completed": months_completed,
                "months_remaining": max(0, 18 - months_completed),
                "total_paid": total_paid,
                "total_value": 180000,
                "monthly_target": 20,
                "monthly_achieved": 0,
                "monthly_target_met": False,
                "current_month": current_month,
                "payout_status": payout_st,
                "last_payment_date": None,
                "progress_id": progress.id if progress else None,
                "overall_status": "Eligible",
                "is_claimable": True,
                "months_missed": 0,
                "direct_points": direct_points
            })

    if not allowance_type or allowance_type == "car":
        car_records = db.query(CarAllowanceEligibility).filter(
            CarAllowanceEligibility.initial_eligibility_met == True
        ).all()

        for record in car_records:
            user_id = record.user_id
            user = db.query(User).filter(User.id == user_id).first()
            if search:
                if search.upper() not in user_id.upper() and (not user or search.lower() not in (user.name or "").lower()):
                    continue

            progress = progress_map.get(f"{user_id}_car")
            payout_st = progress.status if progress else "Pending"

            if payout_status and payout_st != payout_status:
                continue

            eligible_users_data.append({
                "user_id": user_id,
                "user_name": user.name if user else "Unknown",
                "allowance_type": "Car",
                "monthly_amount": 25000,
                "tenure_months": 72,
                "months_completed": record.months_completed or 0,
                "months_remaining": max(0, 72 - (record.months_completed or 0)),
                "total_paid": float(record.total_paid_to_date or 0),
                "total_value": 1800000,
                "monthly_target": 40,
                "monthly_achieved": record.monthly_achieved_matchings or 0,
                "monthly_target_met": record.monthly_target_met if hasattr(record, 'monthly_target_met') else False,
                "current_month": current_month,
                "payout_status": payout_st,
                "last_payment_date": record.payment_date.isoformat() if hasattr(record, 'payment_date') and record.payment_date else None,
                "progress_id": progress.id if progress else None,
                "overall_status": record.overall_status or "Eligible",
                "is_claimable": record.is_claimable if hasattr(record, 'is_claimable') else True,
                "months_missed": record.months_missed if hasattr(record, 'months_missed') else 0
            })

    payout_summary = {
        "total_eligible": len(eligible_users_data),
        "pending": sum(1 for d in eligible_users_data if d["payout_status"] == "Pending"),
        "validated": sum(1 for d in eligible_users_data if d["payout_status"] == "Validated"),
        "payout_completed": sum(1 for d in eligible_users_data if d["payout_status"] == "Payout Completed"),
        "total_paid_all": sum(d["total_paid"] for d in eligible_users_data)
    }

    return {
        "success": True,
        "summary": payout_summary,
        "payouts": eligible_users_data,
        "total": len(eligible_users_data)
    }


@router.get("/contributors/{user_id}")
async def get_user_contributors(
    user_id: str,
    contributor_type: str = Query("standard", regex="^(standard|car|monthly_standard|monthly_car)$"),
    db: Session = Depends(get_db)
):
    """
    Get contributor list for a user's field allowance progress.
    standard = direct referrals (who they referred, contributing to 7-point target)
    car = matching contributors from binary tree (left/right legs)
    monthly_standard = direct referrals activated in the current month only
    monthly_car = matching contributors from binary tree activated in the current month only
    """
    now = get_indian_time()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if contributor_type == "standard":
        sql = text("""
            SELECT r.id, r.name, r.package_points, r.activation_date, r.coupon_status
            FROM "user" r
            WHERE r.referrer_id = :uid AND r.coupon_status = 'Activated'
            ORDER BY r.activation_date DESC
        """)
        rows = db.execute(sql, {"uid": user_id}).fetchall()
        contributors = []
        for row in rows:
            contributors.append({
                "id": row[0],
                "name": row[1] or "Unknown",
                "points": float(row[2] or 0),
                "date": row[3].strftime("%d %b %Y") if row[3] else "N/A",
                "status": row[4] or "Unknown"
            })
        total_points = sum(c["points"] for c in contributors)
        return {
            "success": True,
            "user_id": user_id,
            "type": "standard",
            "total_points": total_points,
            "required": 7,
            "contributors": contributors
        }

    elif contributor_type == "monthly_standard":
        sql = text("""
            SELECT r.id, r.name, r.package_points, r.activation_date, r.coupon_status
            FROM "user" r
            WHERE r.referrer_id = :uid AND r.coupon_status = 'Activated'
              AND r.activation_date >= :month_start
            ORDER BY r.activation_date DESC
        """)
        rows = db.execute(sql, {"uid": user_id, "month_start": month_start}).fetchall()
        contributors = []
        for row in rows:
            contributors.append({
                "id": row[0],
                "name": row[1] or "Unknown",
                "points": float(row[2] or 0),
                "date": row[3].strftime("%d %b %Y") if row[3] else "N/A",
                "status": row[4] or "Unknown"
            })
        total_points = sum(c["points"] for c in contributors)
        month_label = now.strftime("%B %Y")
        return {
            "success": True,
            "user_id": user_id,
            "type": "monthly_standard",
            "month": month_label,
            "total_points": total_points,
            "required": 20,
            "contributors": contributors
        }

    elif contributor_type == "monthly_car":
        sql = text("""
            SELECT r.id, r.name, r.package_points, r.activation_date, r.coupon_status
            FROM "user" r
            WHERE r.referrer_id = :uid AND r.coupon_status = 'Activated'
              AND r.activation_date >= :month_start
            ORDER BY r.activation_date DESC
        """)
        rows = db.execute(sql, {"uid": user_id, "month_start": month_start}).fetchall()
        contributors = []
        for row in rows:
            contributors.append({
                "id": row[0],
                "name": row[1] or "Unknown",
                "points": float(row[2] or 0),
                "date": row[3].strftime("%d %b %Y") if row[3] else "N/A",
                "status": row[4] or "Unknown"
            })
        total_points = sum(c["points"] for c in contributors)
        month_label = now.strftime("%B %Y")
        return {
            "success": True,
            "user_id": user_id,
            "type": "monthly_car",
            "month": month_label,
            "total_points": total_points,
            "required": 40,
            "contributors": contributors
        }

    else:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        left_id = getattr(user, 'left_child_id', None)
        right_id = getattr(user, 'right_child_id', None)

        contributors = []
        for leg_label, leg_id in [("Group A", left_id), ("Group B", right_id)]:
            if not leg_id:
                continue
            leg_user = db.query(User).filter(User.id == leg_id).first()
            if leg_user and getattr(leg_user, 'coupon_status', '') == 'Activated':
                contributors.append({
                    "id": leg_id,
                    "name": leg_user.name or "Unknown",
                    "points": float(leg_user.package_points or 0),
                    "date": leg_user.activation_date.strftime("%d %b %Y") if leg_user.activation_date else "N/A",
                    "leg": leg_label
                })

        return {
            "success": True,
            "user_id": user_id,
            "type": "car",
            "contributors": contributors
        }


@router.put("/payout/{progress_id}/status")
async def update_payout_status(
    progress_id: int,
    status_update: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update payout status: Pending -> Validated -> Payout Completed
    Staff Portal exclusive action
    """
    new_status = status_update.get("status")
    notes = status_update.get("notes", "")

    if new_status not in ["Pending", "Validated", "Payout Completed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be: Pending, Validated, or Payout Completed")

    progress = db.query(FieldAllowanceProgress).filter(
        FieldAllowanceProgress.id == progress_id
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")

    if new_status == "Validated":
        progress.status = "Validated"
        progress.eligibility_checked_at = get_indian_time()
    elif new_status == "Payout Completed":
        progress.status = "Payout Completed"
        progress.paid_at = get_indian_time()
    elif new_status == "Pending":
        progress.status = "Pending"
        progress.paid_at = None

    db.commit()

    return {
        "success": True,
        "message": f"Payout status updated to {new_status}",
        "progress_id": progress_id,
        "new_status": new_status
    }
