"""
Member Lifecycle Tracker API Endpoints
DC Protocol: Staff-only access for tracking MNR member lifecycle stages
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, and_, func, desc, asc
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.member_lifecycle import MemberLifecycleTracker
from app.models.user import User
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.base import get_indian_time
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier
from app.models.bonanza import DynamicBonanzaHistory
from app.models.myntreal_incentive import MNRAccidentalInsurance
from app.models.ved_team import VedTeamMember

router = APIRouter(prefix="/staff/member-lifecycle", tags=["Member Lifecycle Tracker"])


def _resolve_staff_id(staff_user):
    if hasattr(staff_user, 'emp_code') and staff_user.emp_code:
        return staff_user.emp_code
    return str(staff_user.id)


@router.get("/trackers")
async def list_trackers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    stage_filter: Optional[str] = Query(None),
    activation_status: Optional[str] = Query(None),
    package_filter: Optional[str] = Query(None),
    reg_start: Optional[str] = Query(None),
    reg_end: Optional[str] = Query(None),
    act_start: Optional[str] = Query(None),
    act_end: Optional[str] = Query(None),
    referrer_search: Optional[str] = Query(None),
    ved_owner_search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query('created_at'),
    sort_order: Optional[str] = Query('desc'),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    query = db.query(MemberLifecycleTracker)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                MemberLifecycleTracker.user_id.ilike(search_term),
                MemberLifecycleTracker.user_name.ilike(search_term)
            )
        )

    if status_filter == 'ALL_COMPLETED':
        for field in MemberLifecycleTracker.STAGE_FIELDS:
            stage_col = getattr(MemberLifecycleTracker, f'{field}_status')
            query = query.filter(stage_col == 'COMPLETED')
    elif status_filter == 'HAS_PENDING':
        conditions = []
        for field in MemberLifecycleTracker.STAGE_FIELDS:
            stage_col = getattr(MemberLifecycleTracker, f'{field}_status')
            conditions.append(stage_col == 'PENDING')
        if conditions:
            query = query.filter(or_(*conditions))
    elif status_filter in ('PENDING', 'IN_PROGRESS', 'COMPLETED') and stage_filter:
        stage_col = getattr(MemberLifecycleTracker, f'{stage_filter}_status', None)
        if stage_col is not None:
            query = query.filter(stage_col == status_filter.upper())

    needs_user_join = False
    user_filters = []

    if activation_status:
        needs_user_join = True
        if activation_status == 'activated':
            user_filters.append(User.activation_date.isnot(None))
        elif activation_status == 'not_activated':
            user_filters.append(User.activation_date.is_(None))

    if package_filter:
        needs_user_join = True
        pkg_map = {'Platinum': 1.0, 'Diamond': 0.5, 'Star': 0.067}
        if package_filter == 'Platinum':
            user_filters.append(User.package_points >= 1.0)
        elif package_filter == 'Diamond':
            user_filters.append(User.package_points >= 0.5)
            user_filters.append(User.package_points < 1.0)
        elif package_filter in ('Star', 'Star / Loyal'):
            user_filters.append(User.package_points > 0)
            user_filters.append(User.package_points < 0.5)

    if reg_start:
        try:
            reg_start_dt = datetime.strptime(reg_start, '%Y-%m-%d')
            query = query.filter(MemberLifecycleTracker.created_at >= reg_start_dt)
        except ValueError:
            pass
    if reg_end:
        try:
            reg_end_dt = datetime.strptime(reg_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(MemberLifecycleTracker.created_at <= reg_end_dt)
        except ValueError:
            pass

    if act_start:
        needs_user_join = True
        try:
            act_start_dt = datetime.strptime(act_start, '%Y-%m-%d')
            user_filters.append(User.activation_date >= act_start_dt)
        except ValueError:
            pass
    if act_end:
        needs_user_join = True
        try:
            act_end_dt = datetime.strptime(act_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            user_filters.append(User.activation_date <= act_end_dt)
        except ValueError:
            pass

    if referrer_search:
        needs_user_join = True
        ref_term = f"%{referrer_search}%"
        user_filters.append(User.referrer_id.ilike(ref_term))

    if ved_owner_search:
        ved_term = f"%{ved_owner_search}%"
        ved_member_ids = db.query(VedTeamMember.member_id).filter(
            VedTeamMember.ved_owner_id.ilike(ved_term),
            VedTeamMember.is_active == True
        ).all()
        ved_member_id_list = [v.member_id for v in ved_member_ids]
        query = query.filter(MemberLifecycleTracker.user_id.in_(ved_member_id_list))

    if needs_user_join:
        query = query.outerjoin(User, MemberLifecycleTracker.user_id == User.id)
        for uf in user_filters:
            query = query.filter(uf)

    total = query.count()

    user_sort_fields = {'activation_date': User.activation_date, 'phone_number': User.phone_number}
    if sort_by in user_sort_fields:
        if not needs_user_join:
            query = query.outerjoin(User, MemberLifecycleTracker.user_id == User.id)
        sort_col = user_sort_fields[sort_by]
    else:
        sort_col = getattr(MemberLifecycleTracker, sort_by, MemberLifecycleTracker.created_at)
    if sort_order == 'asc':
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    offset = (page - 1) * page_size
    trackers = query.offset(offset).limit(page_size).all()

    user_ids = [t.user_id for t in trackers]
    users_map = {}
    insurance_map = {}
    insurance_eligibility_map = {}
    if user_ids:
        users = db.query(User.id, User.phone_number, User.activation_date, User.package_points, User.account_status, User.is_welcome_coupon, User.referrer_id, User.coupon_status, User.coupon_status_changed_at).filter(User.id.in_(user_ids)).all()
        for u in users:
            if getattr(u, 'is_welcome_coupon', False):
                pkg = 'Welcome Coupon'
            else:
                pkg = 'Eligible'
                pp = u.package_points or 0
                if pp >= 1.0: pkg = 'Platinum'
                elif pp >= 0.5: pkg = 'Diamond'
                elif pp > 0: pkg = 'Star/Loyal'
            users_map[u.id] = {
                'phone_number': u.phone_number,
                'activation_date': u.activation_date.isoformat() if u.activation_date else None,
                'activation_date_raw': u.activation_date,
                'package_type': pkg,
                'account_status': u.account_status,
                'referrer_id': u.referrer_id,
                'is_welcome_coupon': getattr(u, 'is_welcome_coupon', False),
                'coupon_status': u.coupon_status,
                'coupon_status_changed_at': u.coupon_status_changed_at,
            }

        referrer_ids = list(set(u.referrer_id for u in users if u.referrer_id))
        referrer_names_map = {}
        if referrer_ids:
            ref_users = db.query(User.id, User.name).filter(User.id.in_(referrer_ids)).all()
            for ru in ref_users:
                referrer_names_map[ru.id] = ru.name
        for uid, udata in users_map.items():
            ref_id = udata.get('referrer_id')
            udata['referrer_name'] = referrer_names_map.get(ref_id, '') if ref_id else ''

        from app.models.ved_team import VedTeamMember
        ved_records = db.query(VedTeamMember.member_id, VedTeamMember.ved_owner_id).filter(
            VedTeamMember.member_id.in_(user_ids),
            VedTeamMember.is_active == True
        ).all()
        ved_owner_by_member = {v.member_id: v.ved_owner_id for v in ved_records}
        ved_owner_ids_set = list(set(ved_owner_by_member.values()))
        ved_owner_names_map = {}
        if ved_owner_ids_set:
            vo_users = db.query(User.id, User.name).filter(User.id.in_(ved_owner_ids_set)).all()
            ved_owner_names_map = {vo.id: vo.name for vo in vo_users}
        for uid, udata in users_map.items():
            vo_id = ved_owner_by_member.get(uid, '')
            udata['ved_owner_id'] = vo_id
            udata['ved_owner_name'] = ved_owner_names_map.get(vo_id, '') if vo_id else ''

        ins_records = db.query(
            MNRAccidentalInsurance.user_id,
            MNRAccidentalInsurance.status,
            MNRAccidentalInsurance.policy_number
        ).filter(MNRAccidentalInsurance.user_id.in_(user_ids)).all()
        for ins in ins_records:
            insurance_map[ins.user_id] = {
                'insurance_status': ins.status,
                'policy_number': ins.policy_number
            }

        INSURANCE_ELIGIBILITY_DATE = datetime(2026, 2, 3, 0, 0, 0)
        REQUIRED_REFERRALS = 2
        WELCOME_COUPON_REFERRALS = 2

        Referral = aliased(User)
        referral_counts_rows = db.query(
            Referral.referrer_id,
            func.count(Referral.id)
        ).filter(
            Referral.referrer_id.in_(user_ids),
            Referral.coupon_status.in_(['Active', 'Activated']),
            Referral.is_welcome_coupon.is_(False),
            or_(
                Referral.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                and_(
                    Referral.activation_date == None,
                    Referral.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                )
            )
        ).group_by(Referral.referrer_id).all()
        referral_map = {row[0]: row[1] for row in referral_counts_rows}

        for uid, udata in users_map.items():
            existing_ins = insurance_map.get(uid)
            if existing_ins and existing_ins['insurance_status'] in ('Active', 'Issued'):
                insurance_eligibility_map[uid] = 'Issued'
                continue

            coupon_status = udata.get('coupon_status')
            if coupon_status not in ('Active', 'Activated'):
                insurance_eligibility_map[uid] = 'Not Eligible'
                continue

            is_wc = udata.get('is_welcome_coupon', False)
            activation_date = udata.get('activation_date_raw') or udata.get('coupon_status_changed_at')

            if is_wc:
                ref_count = referral_map.get(uid, 0)
                if ref_count >= WELCOME_COUPON_REFERRALS:
                    insurance_eligibility_map[uid] = 'Eligible'
                else:
                    insurance_eligibility_map[uid] = 'Not Eligible'
            elif activation_date and activation_date >= INSURANCE_ELIGIBILITY_DATE:
                insurance_eligibility_map[uid] = 'Eligible'
            elif referral_map.get(uid, 0) >= REQUIRED_REFERRALS:
                insurance_eligibility_map[uid] = 'Eligible'
            else:
                insurance_eligibility_map[uid] = 'Not Eligible'

        from app.services.sql_utils import check_key_eligibility_bulk
        key_elig_map = check_key_eligibility_bulk(db, user_ids)

    enriched = []
    for t in trackers:
        d = t.to_dict()
        user_info = users_map.get(t.user_id, {})
        d['phone_number'] = user_info.get('phone_number')
        d['activation_date'] = user_info.get('activation_date')
        d['package_type'] = user_info.get('package_type', 'Eligible')
        d['account_status'] = user_info.get('account_status', 'Active')
        d['referrer_id'] = user_info.get('referrer_id', '')
        d['referrer_name'] = user_info.get('referrer_name', '')
        d['ved_owner_id'] = user_info.get('ved_owner_id', '')
        d['ved_owner_name'] = user_info.get('ved_owner_name', '')
        d['insurance_status'] = insurance_eligibility_map.get(t.user_id, 'Not Eligible')
        d['policy_number'] = insurance_map.get(t.user_id, {}).get('policy_number')
        d['is_key_eligible'] = key_elig_map.get(t.user_id, False) if user_ids else False
        enriched.append(d)

    pending_count = db.query(func.count(MemberLifecycleTracker.id)).filter(
        MemberLifecycleTracker.overall_progress < 100
    ).scalar() or 0
    completed_count = db.query(func.count(MemberLifecycleTracker.id)).filter(
        MemberLifecycleTracker.overall_progress >= 100
    ).scalar() or 0

    return {
        "success": True,
        "trackers": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 1,
        "summary": {
            "total_members": total,
            "pending": pending_count,
            "completed": completed_count
        },
        "stage_labels": MemberLifecycleTracker.STAGE_LABELS,
        "stage_fields": MemberLifecycleTracker.STAGE_FIELDS
    }


@router.patch("/trackers/{tracker_id}/stage")
async def update_stage(
    tracker_id: int,
    stage: str = Body(..., embed=True),
    status: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    tracker = db.query(MemberLifecycleTracker).filter_by(id=tracker_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    if stage not in MemberLifecycleTracker.STAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED']
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    staff_id = _resolve_staff_id(current_user)
    now = get_indian_time()

    setattr(tracker, f'{stage}_status', status.upper())
    setattr(tracker, f'{stage}_updated_by', staff_id)
    setattr(tracker, f'{stage}_updated_at', now)
    if notes is not None:
        setattr(tracker, f'{stage}_notes', notes)

    tracker.calculate_progress()
    tracker.updated_at = now

    db.commit()
    db.refresh(tracker)

    return {
        "success": True,
        "message": f"{MemberLifecycleTracker.STAGE_LABELS.get(stage, stage)} updated to {status.upper()}",
        "tracker": tracker.to_dict()
    }


@router.post("/trackers/bulk-update")
async def bulk_update_stage(
    tracker_ids: list = Body(..., embed=True),
    stage: str = Body(..., embed=True),
    status: str = Body(..., embed=True),
    notes: Optional[str] = Body(None, embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    if stage not in MemberLifecycleTracker.STAGE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED']
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status")

    staff_id = _resolve_staff_id(current_user)
    now = get_indian_time()
    updated = 0

    trackers = db.query(MemberLifecycleTracker).filter(
        MemberLifecycleTracker.id.in_(tracker_ids)
    ).all()

    for tracker in trackers:
        setattr(tracker, f'{stage}_status', status.upper())
        setattr(tracker, f'{stage}_updated_by', staff_id)
        setattr(tracker, f'{stage}_updated_at', now)
        if notes is not None:
            setattr(tracker, f'{stage}_notes', notes)
        tracker.calculate_progress()
        tracker.updated_at = now
        updated += 1

    db.commit()

    return {
        "success": True,
        "message": f"Updated {updated} trackers",
        "updated_count": updated
    }


@router.get("/trackers/{user_id}/detailed-view")
async def get_detailed_user_view(
    user_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Comprehensive user view for lifecycle tracker - referrer, referrals, group performance, awards, bonanza"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    tracker = db.query(MemberLifecycleTracker).filter_by(user_id=user_id).first()

    referrer_info = None
    if user.referrer_id:
        referrer = db.query(User.id, User.name, User.phone_number, User.activation_date).filter(User.id == user.referrer_id).first()
        if referrer:
            referrer_info = {
                'id': referrer.id,
                'name': referrer.name,
                'phone_number': referrer.phone_number,
                'activation_date': referrer.activation_date.isoformat() if referrer.activation_date else None
            }

    total_referrals = db.query(func.count(User.id)).filter(User.referrer_id == user_id).scalar() or 0
    active_referrals = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id,
        User.activation_date.isnot(None)
    ).scalar() or 0

    from datetime import datetime as dt
    fresh_date = dt(2025, 10, 21)

    group_a_total = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id, User.position == 'LEFT'
    ).scalar() or 0
    group_a_active = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id, User.position == 'LEFT',
        User.activation_date.isnot(None)
    ).scalar() or 0
    group_a_points = db.query(func.coalesce(func.sum(User.package_points), 0)).filter(
        User.referrer_id == user_id, User.position == 'LEFT',
        User.activation_date.isnot(None), User.activation_date >= fresh_date,
        User.package_points > 0
    ).scalar() or 0

    group_b_total = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id, User.position == 'RIGHT'
    ).scalar() or 0
    group_b_active = db.query(func.count(User.id)).filter(
        User.referrer_id == user_id, User.position == 'RIGHT',
        User.activation_date.isnot(None)
    ).scalar() or 0
    group_b_points = db.query(func.coalesce(func.sum(User.package_points), 0)).filter(
        User.referrer_id == user_id, User.position == 'RIGHT',
        User.activation_date.isnot(None), User.activation_date >= fresh_date,
        User.package_points > 0
    ).scalar() or 0

    direct_awards = db.query(UserAwardProgress).filter(UserAwardProgress.user_id == user_id).all()
    direct_award_list = []
    for a in direct_awards:
        tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == a.award_tier_id).first()
        direct_award_list.append({
            'tier_name': tier.award_name if tier else f'Tier {a.award_tier_id}',
            'required': tier.cumulative_required if tier else None,
            'status': a.processed_status or 'Pending',
            'achievement_date': a.achievement_date.isoformat() if a.achievement_date else None
        })

    matching_awards = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.user_id == user_id).all()
    matching_award_list = []
    for a in matching_awards:
        tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == a.matching_award_tier_id).first()
        matching_award_list.append({
            'tier_name': tier.award_name if tier else f'Tier {a.matching_award_tier_id}',
            'required': tier.cumulative_required if tier else None,
            'status': a.processed_status or 'Pending',
            'achievement_date': a.achievement_date.isoformat() if a.achievement_date else None
        })

    bonanza_claims = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.user_id == user_id
    ).all()
    bonanza_list = []
    for b in bonanza_claims:
        bonanza_list.append({
            'bonanza_name': b.bonanza_name if hasattr(b, 'bonanza_name') else 'Bonanza',
            'status': b.processed_status or 'Claimed',
            'claimed_at': b.claimed_at.isoformat() if hasattr(b, 'claimed_at') and b.claimed_at else None
        })

    pkg = user.get_package_type() if hasattr(user, 'get_package_type') else 'Eligible'

    wallet_balance = user.wallet_balance or 0
    upgrade_wallet = user.upgrade_wallet_balance or 0

    insurance_record = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id == user_id
    ).first()
    insurance_data = None
    if insurance_record:
        insurance_data = {
            'status': insurance_record.status,
            'policy_number': insurance_record.policy_number,
            'insurer_name': insurance_record.insurer_name,
            'insured_amount': insurance_record.insured_amount,
            'insured_date': insurance_record.insured_date.isoformat() if insurance_record.insured_date else None,
            'expiry_date': insurance_record.expiry_date.isoformat() if insurance_record.expiry_date else None,
            'eligibility_type': insurance_record.eligibility_type,
            'eligibility_met_at': insurance_record.eligibility_met_at.isoformat() if insurance_record.eligibility_met_at else None,
            'issued_at': insurance_record.issued_at.isoformat() if insurance_record.issued_at else None,
            'notes': insurance_record.notes,
        }

    return {
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "phone_number": user.phone_number,
            "email": user.email,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "activation_date": user.activation_date.isoformat() if user.activation_date else None,
            "package_type": pkg,
            "package_points": float(user.package_points or 0),
            "kyc_status": user.kyc_status,
            "coupon_status": user.coupon_status,
            "account_status": user.account_status,
            "placement_status": user.placement_status,
            "is_ved": user.is_ved,
            "ved_owner_id": (db.query(VedTeamMember.ved_owner_id).filter(VedTeamMember.member_id == user_id, VedTeamMember.is_active == True).scalar() or ''),
            "ved_owner_name": (lambda vo_id: db.query(User.name).filter(User.id == vo_id).scalar() if vo_id else None)(db.query(VedTeamMember.ved_owner_id).filter(VedTeamMember.member_id == user_id, VedTeamMember.is_active == True).scalar()),
            "is_welcome_coupon": getattr(user, 'is_welcome_coupon', False),
            "is_red_coupon": user.is_red_coupon,
            "wallet_balance": float(wallet_balance),
            "upgrade_wallet_balance": float(upgrade_wallet),
        },
        "referrer": referrer_info,
        "referral_stats": {
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "inactive_referrals": total_referrals - active_referrals,
        },
        "group_performance": {
            "group_a": {
                "total": group_a_total,
                "active": group_a_active,
                "fresh_points": float(group_a_points)
            },
            "group_b": {
                "total": group_b_total,
                "active": group_b_active,
                "fresh_points": float(group_b_points)
            },
            "both_sides_eligible": float(group_a_points) >= 1.0 and float(group_b_points) >= 1.0
        },
        "awards": {
            "direct": direct_award_list,
            "matching": matching_award_list,
            "direct_achieved": len([a for a in direct_award_list if a['status'] not in ('Pending', None)]),
            "matching_achieved": len([a for a in matching_award_list if a['status'] not in ('Pending', None)]),
        },
        "bonanza": {
            "claims": bonanza_list,
            "total_claims": len(bonanza_list)
        },
        "insurance": insurance_data,
        "lifecycle": tracker.to_dict() if tracker else None
    }


@router.get("/trackers/{user_id}")
async def get_tracker_by_user(
    user_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    tracker = db.query(MemberLifecycleTracker).filter_by(user_id=user_id).first()
    if not tracker:
        raise HTTPException(status_code=404, detail=f"No lifecycle tracker found for user {user_id}")

    return {
        "success": True,
        "tracker": tracker.to_dict()
    }


@router.post("/trackers/seed-existing")
async def seed_existing_members(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    existing_tracker_ids = {t[0] for t in db.query(MemberLifecycleTracker.user_id).all()}

    users = db.query(User.id, User.name, User.registration_date, User.kyc_status,
                     User.bank_details_status, User.activation_date, User.coupon_status).all()

    created = 0
    for user in users:
        if user.id in existing_tracker_ids:
            continue

        tracker = MemberLifecycleTracker(
            user_id=user.id,
            user_name=user.name,
            registration_date=user.registration_date,
        )

        if user.kyc_status and user.kyc_status.lower() in ('approved', 'verified', 'completed'):
            tracker.kyc_status = 'COMPLETED'
        if user.bank_details_status and user.bank_details_status.lower() in ('approved', 'verified', 'completed'):
            tracker.bank_details_status = 'COMPLETED'
        if user.activation_date:
            tracker.package_activation_status = 'COMPLETED'
        if user.coupon_status and user.coupon_status.lower() in ('delivered', 'completed', 'active'):
            tracker.coupon_delivery_status = 'COMPLETED'

        tracker.calculate_progress()
        db.add(tracker)
        created += 1

    if created > 0:
        db.commit()

    return {
        "success": True,
        "message": f"Created {created} lifecycle trackers for existing members",
        "created_count": created,
        "skipped_count": len(existing_tracker_ids)
    }


@router.get("/summary")
async def lifecycle_summary(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    total = db.query(func.count(MemberLifecycleTracker.id)).scalar() or 0

    stage_stats = {}
    for field in MemberLifecycleTracker.STAGE_FIELDS:
        col = getattr(MemberLifecycleTracker, f'{field}_status')
        pending = db.query(func.count(MemberLifecycleTracker.id)).filter(col == 'PENDING').scalar() or 0
        in_progress = db.query(func.count(MemberLifecycleTracker.id)).filter(col == 'IN_PROGRESS').scalar() or 0
        completed = db.query(func.count(MemberLifecycleTracker.id)).filter(col == 'COMPLETED').scalar() or 0
        stage_stats[field] = {
            'label': MemberLifecycleTracker.STAGE_LABELS.get(field, field),
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed
        }

    return {
        "success": True,
        "total_members": total,
        "stage_stats": stage_stats
    }
