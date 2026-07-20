"""
DC Protocol Feb 2026: Award Status Auto-Sync Service

Ensures processed_status and achievement_date in the database
stay synchronized with the dynamically calculated achievement state.

Logic:
- Compute effective counts (referrals/matching pairs) after bonanza deductions
- Apply Oct 21, 2025 reset date for pre-reset users
- Promote: Pending → Pending Approval (+ set achievement_date) when achieved
- Demote: Pending Approval / Admin Approved → Pending (+ clear achievement_date) when no longer achieved
- Never demote physical-action statuses (Delivered, Dispatched, Procurement Pending, Processed for Dispatch)
- For Delivered awards consumed by bonanza: track as "delivered_debt" for future deduction visibility
"""

from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
import logging

from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier, AwardAuditLog
from app.services.award_service import AwardService
from app.core.scheduler import get_indian_time

logger = logging.getLogger(__name__)

AWARDS_RESET_DATE = date(2025, 10, 21)

PROMOTABLE_STATUS = 'Pending'
PROMOTED_STATUS = 'Pending Approval'
DEMOTABLE_STATUSES = {'Pending Approval', 'Admin Approved'}
NON_DEMOTABLE_STATUSES = {'Delivered', 'Dispatched', 'Procurement Pending', 'Processed for Dispatch', 'Rejected'}


def sync_user_award_statuses(db: Session, user_id: str) -> Dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"synced": False, "reason": "user_not_found"}

    direct_changes = _sync_direct_awards(db, user)
    matching_changes = _sync_matching_awards(db, user)

    if direct_changes["promoted"] or direct_changes["demoted"] or matching_changes["promoted"] or matching_changes["demoted"]:
        db.commit()

    return {
        "synced": True,
        "user_id": user_id,
        "direct": direct_changes,
        "matching": matching_changes,
    }


def _get_referral_cutoff(user) -> Optional[date]:
    user_activation_date = user.activation_date
    if isinstance(user_activation_date, datetime):
        user_activation_date = user_activation_date.date()
    if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
        return AWARDS_RESET_DATE
    return None


def _sync_direct_awards(db: Session, user) -> Dict:
    user_id = user.id
    referral_cutoff = _get_referral_cutoff(user)

    base_filter = [
        User.referrer_id == user_id,
        User.coupon_status == 'Activated',
    ]
    if referral_cutoff:
        base_filter.append(User.activation_date >= referral_cutoff)

    total_points = db.query(func.sum(User.package_points)).filter(*base_filter).scalar() or 0.0

    exempted_filter = [
        User.referrer_id == user_id,
        User.coupon_status == 'Activated',
        or_(User.is_welcome_coupon == True, User.package_points == 0),
    ]
    if referral_cutoff:
        exempted_filter.append(User.activation_date >= referral_cutoff)
    exempted_count = db.query(func.count(User.id)).filter(*exempted_filter).scalar() or 0

    award_service = AwardService(db)
    bonanza_data = award_service.get_bonanza_deduction(user_id, 'direct')
    total_deduction = bonanza_data.get('total_deduction', 0)
    effective_points = max(0, total_points - total_deduction)

    eligibility = award_service.check_universal_eligibility(user_id)
    is_eligible = eligibility.get('is_eligible', False)

    tiers = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required.asc()).all()
    progress_records = db.query(UserAwardProgress).filter(
        UserAwardProgress.user_id == user_id
    ).all()

    promoted = 0
    demoted = 0

    for tier in tiers:
        existing = next((p for p in progress_records if p.award_tier_id == tier.id), None)
        if not existing:
            continue

        has_referrals = effective_points >= tier.cumulative_required
        fully_achieved = has_referrals and is_eligible

        if fully_achieved and existing.processed_status == PROMOTABLE_STATUS:
            old_status = existing.processed_status
            existing.processed_status = PROMOTED_STATUS
            if not existing.achievement_date:
                existing.achievement_date = get_indian_time()
            promoted += 1
            ec_note = f' (EC adj: +{exempted_count})' if exempted_count > 0 else ''
            db.add(AwardAuditLog(
                entity_type='direct_award', entity_id=existing.id,
                action='auto_sync_promoted', old_status=old_status, new_status=PROMOTED_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Auto-promoted: effective {effective_points} >= {tier.cumulative_required}, eligible (tier: {tier.award_name}){ec_note}'
            ))
            logger.info(f"[AWARD-SYNC] PROMOTED direct award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_points} >= {tier.cumulative_required}, EC={exempted_count})")

        elif has_referrals and not is_eligible and existing.processed_status == PROMOTABLE_STATUS and not existing.achievement_date:
            existing.achievement_date = get_indian_time()
            promoted += 1
            db.add(AwardAuditLog(
                entity_type='direct_award', entity_id=existing.id,
                action='auto_sync_achievement_marked', old_status=PROMOTABLE_STATUS, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Referral target met (effective {effective_points} >= {tier.cumulative_required}) but eligibility pending (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] MARKED direct award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, refs met but eligibility pending)")

        elif not fully_achieved and existing.processed_status in DEMOTABLE_STATUSES:
            old_status = existing.processed_status
            existing.processed_status = PROMOTABLE_STATUS
            existing.achievement_date = None
            demoted += 1
            db.add(AwardAuditLog(
                entity_type='direct_award', entity_id=existing.id,
                action='auto_sync_demoted', old_status=old_status, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Auto-demoted: effective {effective_points} < {tier.cumulative_required} or not eligible (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] DEMOTED direct award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_points} < {tier.cumulative_required})")

        elif not has_referrals and existing.processed_status == PROMOTABLE_STATUS and existing.achievement_date is not None:
            existing.achievement_date = None
            demoted += 1
            db.add(AwardAuditLog(
                entity_type='direct_award', entity_id=existing.id,
                action='auto_sync_stale_cleared', old_status=PROMOTABLE_STATUS, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Cleared stale achievement_date: effective {effective_points} < {tier.cumulative_required} (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] CLEARED stale direct award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_points} < {tier.cumulative_required})")

    return {"promoted": promoted, "demoted": demoted}


def _sync_matching_awards(db: Session, user) -> Dict:
    user_id = user.id
    referral_cutoff = _get_referral_cutoff(user)

    from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
    reset_date_str = referral_cutoff.isoformat() if referral_cutoff else None
    matching_result = get_matching_pairs_with_reset_logic_sql(db, user_id, reset_date_str)
    lifetime_matching = matching_result['matching_pairs']

    award_service = AwardService(db)
    bonanza_data = award_service.get_bonanza_deduction(user_id, 'matching')
    total_deduction = bonanza_data.get('total_deduction', 0)
    effective_matching = max(0, lifetime_matching - total_deduction)

    eligibility = award_service.check_universal_eligibility(user_id)
    is_eligible = eligibility.get('is_eligible', False)

    tiers = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required.asc()).all()
    progress_records = db.query(UserMatchingAwardProgress).filter(
        UserMatchingAwardProgress.user_id == user_id
    ).all()

    promoted = 0
    demoted = 0

    for tier in tiers:
        existing = next((p for p in progress_records if p.matching_award_tier_id == tier.id), None)
        if not existing:
            continue

        has_referrals = effective_matching >= tier.cumulative_required
        fully_achieved = has_referrals and is_eligible

        if fully_achieved and existing.processed_status == PROMOTABLE_STATUS:
            old_status = existing.processed_status
            existing.processed_status = PROMOTED_STATUS
            if not existing.achievement_date:
                existing.achievement_date = get_indian_time()
            promoted += 1
            db.add(AwardAuditLog(
                entity_type='matching_award', entity_id=existing.id,
                action='auto_sync_promoted', old_status=old_status, new_status=PROMOTED_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Auto-promoted: effective {effective_matching} >= {tier.cumulative_required}, eligible (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] PROMOTED matching award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_matching} >= {tier.cumulative_required})")

        elif has_referrals and not is_eligible and existing.processed_status == PROMOTABLE_STATUS and not existing.achievement_date:
            existing.achievement_date = get_indian_time()
            promoted += 1
            db.add(AwardAuditLog(
                entity_type='matching_award', entity_id=existing.id,
                action='auto_sync_achievement_marked', old_status=PROMOTABLE_STATUS, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Referral target met (effective {effective_matching} >= {tier.cumulative_required}) but eligibility pending (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] MARKED matching award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, refs met but eligibility pending)")

        elif not fully_achieved and existing.processed_status in DEMOTABLE_STATUSES:
            old_status = existing.processed_status
            existing.processed_status = PROMOTABLE_STATUS
            existing.achievement_date = None
            demoted += 1
            db.add(AwardAuditLog(
                entity_type='matching_award', entity_id=existing.id,
                action='auto_sync_demoted', old_status=old_status, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Auto-demoted: effective {effective_matching} < {tier.cumulative_required} or not eligible (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] DEMOTED matching award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_matching} < {tier.cumulative_required})")

        elif not has_referrals and existing.processed_status == PROMOTABLE_STATUS and existing.achievement_date is not None:
            existing.achievement_date = None
            demoted += 1
            db.add(AwardAuditLog(
                entity_type='matching_award', entity_id=existing.id,
                action='auto_sync_stale_cleared', old_status=PROMOTABLE_STATUS, new_status=PROMOTABLE_STATUS,
                actor_role='System', actor_id='award_sync_service',
                notes=f'Cleared stale achievement_date: effective {effective_matching} < {tier.cumulative_required} (tier: {tier.award_name})'
            ))
            logger.info(f"[AWARD-SYNC] CLEARED stale matching award {existing.id} for {user_id} "
                        f"(tier={tier.award_name}, effective={effective_matching} < {tier.cumulative_required})")

    return {"promoted": promoted, "demoted": demoted}


def backfill_all_award_statuses(db: Session) -> Dict:
    direct_user_ids = db.query(UserAwardProgress.user_id).distinct().all()
    matching_user_ids = db.query(UserMatchingAwardProgress.user_id).distinct().all()
    all_user_ids = set(uid for (uid,) in direct_user_ids) | set(uid for (uid,) in matching_user_ids)

    total_promoted = 0
    total_demoted = 0
    errors = 0

    for user_id in all_user_ids:
        try:
            result = sync_user_award_statuses(db, user_id)
            if result.get("synced"):
                total_promoted += result["direct"]["promoted"] + result["matching"]["promoted"]
                total_demoted += result["direct"]["demoted"] + result["matching"]["demoted"]
        except Exception as e:
            logger.error(f"[AWARD-SYNC] Backfill error for {user_id}: {e}")
            errors += 1

    return {
        "users_processed": len(all_user_ids),
        "total_promoted": total_promoted,
        "total_demoted": total_demoted,
        "errors": errors,
    }
