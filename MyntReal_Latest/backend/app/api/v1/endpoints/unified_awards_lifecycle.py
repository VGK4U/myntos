"""
DC Protocol: Unified Awards Lifecycle API
Complete lifecycle management for Direct, Matching, and Bonanza awards

Provides:
- Unified filtering across all award types
- Dynamic action buttons based on status + role
- Procurement workflow (record → dispatch → deliver)
- Full audit trail

Author: MNR Development Team
Date: Nov 11, 2025
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, and_, func, desc, exists, select
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel
import logging
import traceback
import time
import hashlib
import json

logger = logging.getLogger(__name__)

_awards_cache = {
    'data': None,
    'timestamp': 0,
    'cache_key': None,
}
AWARDS_CACHE_TTL = 300

def invalidate_awards_cache():
    _awards_cache['data'] = None
    _awards_cache['timestamp'] = 0
    _awards_cache['cache_key'] = None
    logger.info("[AWARDS-CACHE] Cache invalidated")

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid
from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier, AwardAuditLog
from app.models.bonanza import DynamicBonanzaHistory, DynamicBonanza, Bonanza
from app.constants.award_statuses import AwardStatus
from app.services.award_actions_service import AwardActionsService
from app.services.unified_award_status_manager import UnifiedAwardStatusManager
from app.services.rvz_expense_service import RVZExpenseService
from app.core.scheduler import check_direct_referrals_both_sides, get_user_eligibility_status

router = APIRouter(prefix="/unified-awards", tags=["Unified Awards Lifecycle"])


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


# ========== PYDANTIC MODELS ==========

class ApprovalAction(BaseModel):
    award_id: int
    award_type: str  # 'direct', 'matching', 'bonanza'
    notes: Optional[str] = None


class RejectionAction(BaseModel):
    award_id: int
    award_type: str
    rejection_reason: str


class ProcurementData(BaseModel):
    award_id: int
    award_type: str
    actual_cost_paid: float
    vendor_name: str
    payment_mode: str  # 'Cash', 'UPI', 'Card', 'Bank Transfer'
    payment_reference: Optional[str] = None
    bill_upload_path: Optional[str] = None
    handling_charges: Optional[float] = 0.0
    gst_amount: Optional[float] = None  # Auto-calculated if not provided
    tax_amount: Optional[float] = 0.0  # Collected from winner (physical awards)
    transport_charges: Optional[float] = 0.0  # Collected from winner
    cost_variance_reason: Optional[str] = None


class DispatchData(BaseModel):
    award_id: int
    award_type: str
    dispatch_date: date
    courier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    delivery_notes: Optional[str] = None


class DeliveryData(BaseModel):
    award_id: int
    award_type: str
    received_date: date
    delivery_notes: Optional[str] = None
    delivery_proof_path: Optional[str] = None


class SimplifiedStatusUpdate(BaseModel):
    award_id: int
    award_type: str
    new_status: str
    comment: Optional[str] = None


SIMPLIFIED_STATUS_MAP = {
    'Approved': AwardStatus.ADMIN_APPROVED,
    'Processed': AwardStatus.PROCESSED_FOR_DISPATCH,
    'Completed': AwardStatus.DELIVERED,
    'Rejected': AwardStatus.REJECTED,
}

SIMPLIFIED_DISPLAY_MAP = {
    'Pending': 'Pending',
    'Pending Approval': 'Pending Approval',
    'Admin Approved': 'Approved',
    'Procurement Pending': 'Processed',
    'Processed for Dispatch': 'Processed',
    'Dispatched': 'Processed',
    'Delivered': 'Completed',
    'Rejected': 'Rejected',
}


# ========== UNIFIED FILTERING ENDPOINT ==========

@router.get("/list")
async def get_unified_awards_list(
    award_types: Optional[str] = Query('all', description="Comma-separated: 'direct,matching,bonanza' or 'all'"),
    statuses: Optional[str] = Query(None, description="Comma-separated status filters"),
    user_id_search: Optional[str] = Query(None, description="Search by user ID (partial match)"),
    user_name_search: Optional[str] = Query(None, description="Search by user name (partial match)"),
    gift_name_search: Optional[str] = Query(None, description="Search by gift/award name"),
    date_from: Optional[date] = Query(None, description="Filter by achievement date (from)"),
    date_to: Optional[date] = Query(None, description="Filter by achievement date (to)"),
    include_eligibility: bool = Query(False, description="Include expensive eligibility calculations (default: false for faster loading)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    audience: Optional[str] = Query(None, description="DC_AUDIENCE_001: 'mnr' (default) | 'vgk4u' | 'both'"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified awards list with comprehensive filtering
    
    Returns awards from all types with:
    - Normalized status values
    - Available actions based on user role
    - User-friendly display labels
    - Pagination support

    DC_AUDIENCE_001 (audit #35 follow-up, Phase A1):
    - Default ``audience=None`` returns the existing MNR awards list with the
      pre-A1 response shape (zero behaviour change for existing callers).
    - ``audience='vgk4u'`` short-circuits to an empty awards list — VGK4U has
      no award programme yet (separate roadmap). Envelope keys
      ``audience``/``audience_label`` are added so clients can render labels.
    - ``audience='both'`` returns the MNR list with the envelope keys added.
    """
    # DC_AUDIENCE_001 — handle non-MNR audiences before doing any expensive work.
    if audience is not None:
        from app.core.audience_resolver import normalize_audience, audience_label, is_vgk4u_enabled
        aud = normalize_audience(audience)
        if aud == 'vgk4u':
            envelope: Dict[str, Any] = {
                "awards": [],
                "total_count": 0,
                "filtered_count": 0,
                "summary": {"direct_total": 0, "matching_total": 0, "bonanza_total": 0},
                "audience": aud,
                "audience_label": audience_label(aud),
                "vgk4u_enabled": is_vgk4u_enabled(db),
                "note": "VGK4U award programme not yet implemented (Phase A1 read-only stub).",
            }
            return envelope
        # 'mnr' or 'both' — fall through to existing MNR pipeline; envelope
        # keys are appended at the end of the function.
    # Check permissions - DC Protocol (Feb 2026): Staff access via page-level permissions
    allowed_roles = ['Finance Admin', 'Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in allowed_roles:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    # DC_AUDIENCE_001: include audience in cache key to prevent cross-contamination.
    # Use '__omitted__' sentinel when caller did not pass `audience` so the omitted
    # variant gets its own cache slot — this preserves the byte-identical pre-A1
    # response shape contract on the omitted path even after explicit-audience
    # callers have populated the cache. For explicit audience values, canonicalize
    # via normalize_audience so equivalent inputs share a cache slot (e.g.,
    # 'MNR'/'mnr'/invalid-token-that-falls-back-to-mnr).
    if audience is None:
        _aud_for_cache = '__omitted__'
    else:
        from app.core.audience_resolver import normalize_audience as _norm_aud
        _aud_for_cache = _norm_aud(audience)
    cache_key_parts = f"{award_types}|{statuses}|{user_id_search}|{user_name_search}|{gift_name_search}|{date_from}|{date_to}|{include_eligibility}|{skip}|{limit}|{_aud_for_cache}"
    cache_key = hashlib.md5(cache_key_parts.encode()).hexdigest()
    
    now = time.time()
    if (
        _awards_cache['data'] is not None
        and _awards_cache['cache_key'] == cache_key
        and (now - _awards_cache['timestamp']) < AWARDS_CACHE_TTL
    ):
        logger.info(f"[AWARDS-CACHE] Serving cached awards list (age: {int(now - _awards_cache['timestamp'])}s)")
        return _awards_cache['data']
    
    _query_start = time.time()
    
    # Parse award types filter
    if award_types == 'all':
        include_direct = include_matching = include_bonanza = True
    else:
        types_list = [t.strip().lower() for t in award_types.split(',')]
        include_direct = 'direct' in types_list
        include_matching = 'matching' in types_list
        include_bonanza = 'bonanza' in types_list
    
    # Parse status filters
    status_filters = []
    if statuses:
        status_filters = [s.strip() for s in statuses.split(',')]
    
    # DC PROTOCOL: Production start date for eligibility
    PRODUCTION_START_DATE = date(2025, 10, 21)
    
    
    unified_awards = []
    direct_total = 0
    matching_total = 0
    bonanza_total = 0
    
    group_eligibility_cache = {}
    
    def _get_user_eligibility(uid):
        if uid not in group_eligibility_cache:
            try:
                elig = check_direct_referrals_both_sides(db, uid, return_details=True)
                if elig.get('is_eligible'):
                    grp = 'Yes'
                elif elig.get('group_a_points', 0) < 1.0 and elig.get('group_b_points', 0) < 1.0:
                    grp = 'No'
                elif elig.get('group_a_points', 0) < 1.0:
                    grp = 'Group A Missing'
                else:
                    grp = 'Group B Missing'
                
                user_obj = db.query(User).filter(User.id == uid).first()
                full_elig = get_user_eligibility_status(db, user_obj) if user_obj else {}
                group_eligibility_cache[uid] = {
                    'group_eligibility': grp,
                    'eligibility_criteria': {
                        'is_eligible': full_elig.get('is_eligible', False),
                        'is_activated': full_elig.get('is_activated', False),
                        'kyc_approved': (full_elig.get('kyc_status', 'pending') or 'pending').lower() == 'approved',
                        'program_utilisation_completed': full_elig.get('program_utilisation_completed', False),
                        'group_a_ok': full_elig.get('group_a_points', 0) >= 1.0,
                        'group_b_ok': full_elig.get('group_b_points', 0) >= 1.0,
                    }
                }
            except Exception:
                group_eligibility_cache[uid] = {'group_eligibility': 'Unknown', 'eligibility_criteria': None}
        return group_eligibility_cache[uid]
    
    # ========== DIRECT AWARDS ==========
    if include_direct:
        # Create alias for subquery to avoid correlation issues
        ReferralUser = aliased(User)
        
        query = db.query(
            UserAwardProgress,
            User,
            DirectAwardTier
        ).join(
            User, UserAwardProgress.user_id == User.id
        ).join(
            DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
        )
        
        # DC PROTOCOL: Only show awards for users with eligible referrals (activated on/after Oct 21, 2025)
        # This ensures data consistency and prevents invalid awards from appearing
        eligible_referral_subquery = exists(
            select(ReferralUser.id).where(
                and_(
                    ReferralUser.referrer_id == UserAwardProgress.user_id,
                    ReferralUser.activation_date >= PRODUCTION_START_DATE
                )
            )
        )
        query = query.filter(eligible_referral_subquery)
        
        # DC Protocol Feb 2026: Achievement date filter
        # Show awards with achievement_date >= production start OR NULL achievement_date with non-Pending status
        # Also show Pending awards that have achievement_date set (achieved but eligibility not met yet)
        query = query.filter(
            or_(
                UserAwardProgress.achievement_date >= PRODUCTION_START_DATE,
                and_(
                    UserAwardProgress.achievement_date.is_(None),
                    UserAwardProgress.processed_status != 'Pending'
                )
            )
        )
        
        # DC Protocol Feb 2026: Removed blanket bonanza user exclusion.
        # Bonanza deductions are now handled by award_sync_service which adjusts
        # effective counts and demotes awards below threshold back to 'Pending'.
        # Awards that remain 'Pending Approval' or beyond have legitimately met
        # their requirements AFTER bonanza deductions.
        
        # Apply filters
        if status_filters:
            query = query.filter(UserAwardProgress.processed_status.in_(status_filters))
        if user_id_search:
            query = query.filter(User.id.ilike(f'%{user_id_search}%'))
        if user_name_search:
            query = query.filter(User.name.ilike(f'%{user_name_search}%'))
        if gift_name_search:
            query = query.filter(DirectAwardTier.award_description.ilike(f'%{gift_name_search}%'))
        if date_from:
            query = query.filter(UserAwardProgress.achievement_date >= date_from)
        if date_to:
            query = query.filter(UserAwardProgress.achievement_date <= date_to)
        
        direct_total = query.count()
        results = query.order_by(desc(UserAwardProgress.achievement_date)).offset(skip).limit(limit).all()
        
        direct_user_ids = list(set(r[1].id for r in results))
        direct_ref_counts = {}
        direct_bonanza_deductions = {}
        direct_exempted_counts = {}
        if direct_user_ids:
            ReferralCount = aliased(User)
            ref_counts = db.query(
                ReferralCount.referrer_id,
                func.count(ReferralCount.id)
            ).filter(
                ReferralCount.referrer_id.in_(direct_user_ids),
                ReferralCount.coupon_status == 'Activated',
                ReferralCount.activation_date >= PRODUCTION_START_DATE
            ).group_by(ReferralCount.referrer_id).all()
            direct_ref_counts = {r[0]: r[1] for r in ref_counts}
            
            ExemptedRef = aliased(User)
            exempt_counts = db.query(
                ExemptedRef.referrer_id,
                func.count(ExemptedRef.id)
            ).filter(
                ExemptedRef.referrer_id.in_(direct_user_ids),
                ExemptedRef.coupon_status == 'Activated',
                ExemptedRef.activation_date >= PRODUCTION_START_DATE,
                or_(ExemptedRef.is_welcome_coupon == True, ExemptedRef.package_points == 0)
            ).group_by(ExemptedRef.referrer_id).all()
            direct_exempted_counts = {r[0]: r[1] for r in exempt_counts}
            
            deduction_rows = db.query(
                DynamicBonanzaHistory.user_id,
                func.sum(DynamicBonanzaHistory.deduction_amount_direct)
            ).filter(
                DynamicBonanzaHistory.user_id.in_(direct_user_ids),
                DynamicBonanzaHistory.deduction_applied_to_direct_awards == True,
                DynamicBonanzaHistory.claimed_at.isnot(None)
            ).group_by(DynamicBonanzaHistory.user_id).all()
            direct_bonanza_deductions = {r[0]: int(r[1] or 0) for r in deduction_rows}
        
        for award, user, tier in results:
            raw_count = direct_ref_counts.get(user.id, 0)
            bonanza_deducted = direct_bonanza_deductions.get(user.id, 0)
            exempted_count = direct_exempted_counts.get(user.id, 0)
            actual_achieved = max(0, raw_count - bonanza_deducted) + exempted_count
            adjusted_tier_required = tier.cumulative_required + exempted_count
            if include_eligibility:
                user_elig = _get_user_eligibility(user.id)
            else:
                user_elig = {'group_eligibility': None, 'eligibility_criteria': None}
            unified_awards.append({
                'award_id': award.id,
                'award_type': 'direct',
                'user_id': user.id,
                'user_name': user.name,
                'kyc_status': user.kyc_status or 'Pending',
                'is_activated': bool(user.activation_date),
                'rank_name': tier.award_name,
                'gift_name': tier.award_description,
                'tier_required': adjusted_tier_required,
                'achieved_count': actual_achieved,
                'exempted_coupon_count': exempted_count,
                'budgeted_amount': float(tier.actual_price) if tier.actual_price else 0.0,
                'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                'processed_status': award.processed_status,
                'simplified_status': SIMPLIFIED_DISPLAY_MAP.get(award.processed_status, award.processed_status),
                'status_display': AwardActionsService.get_status_display_label(award.processed_status),
                'status_color': AwardActionsService.get_status_badge_color(award.processed_status),
                'achievement_date': award.achievement_date.isoformat() if award.achievement_date else None,
                'approved_date': (award.admin_approved_at.isoformat() if hasattr(award, 'admin_approved_at') and award.admin_approved_at else None),
                'completed_date': (award.received_date.isoformat() if award.received_date else None),
                'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                'received_date': award.received_date.isoformat() if award.received_date else None,
                'group_eligibility': user_elig.get('group_eligibility'),
                'eligibility_criteria': user_elig.get('eligibility_criteria'),
                'available_actions': AwardActionsService.get_available_actions(
                    award.processed_status,
                    (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
                    'direct'
                )
            })
    
    # ========== MATCHING AWARDS ==========
    if include_matching:
        # Create alias for subquery to avoid correlation issues
        ReferralUser = aliased(User)
        
        query = db.query(
            UserMatchingAwardProgress,
            User,
            MatchingAwardTier
        ).join(
            User, UserMatchingAwardProgress.user_id == User.id
        ).join(
            MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
        )
        
        # DC PROTOCOL: Only show awards for users with eligible referrals (activated on/after Oct 21, 2025)
        eligible_referral_subquery = exists(
            select(ReferralUser.id).where(
                and_(
                    ReferralUser.referrer_id == UserMatchingAwardProgress.user_id,
                    ReferralUser.activation_date >= PRODUCTION_START_DATE
                )
            )
        )
        query = query.filter(eligible_referral_subquery)
        
        # DC Protocol Feb 2026: Achievement date filter
        query = query.filter(
            or_(
                UserMatchingAwardProgress.achievement_date >= PRODUCTION_START_DATE,
                and_(
                    UserMatchingAwardProgress.achievement_date.is_(None),
                    UserMatchingAwardProgress.processed_status != 'Pending'
                )
            )
        )
        
        # Apply filters
        if status_filters:
            query = query.filter(UserMatchingAwardProgress.processed_status.in_(status_filters))
        if user_id_search:
            query = query.filter(User.id.ilike(f'%{user_id_search}%'))
        if user_name_search:
            query = query.filter(User.name.ilike(f'%{user_name_search}%'))
        if gift_name_search:
            query = query.filter(MatchingAwardTier.award_description.ilike(f'%{gift_name_search}%'))
        if date_from:
            query = query.filter(UserMatchingAwardProgress.achievement_date >= date_from)
        if date_to:
            query = query.filter(UserMatchingAwardProgress.achievement_date <= date_to)
        
        matching_total = query.count()
        results = query.order_by(desc(UserMatchingAwardProgress.achievement_date)).offset(skip).limit(limit).all()
        
        matching_user_ids = list(set(r[1].id for r in results))
        matching_bonanza_deductions = {}
        if matching_user_ids:
            m_deduction_rows = db.query(
                DynamicBonanzaHistory.user_id,
                func.sum(DynamicBonanzaHistory.deduction_amount_matching)
            ).filter(
                DynamicBonanzaHistory.user_id.in_(matching_user_ids),
                DynamicBonanzaHistory.deduction_applied_to_matching_awards == True,
                DynamicBonanzaHistory.claimed_at.isnot(None)
            ).group_by(DynamicBonanzaHistory.user_id).all()
            matching_bonanza_deductions = {r[0]: int(r[1] or 0) for r in m_deduction_rows}
        
        for award, user, tier in results:
            stored_progress = award.effective_progress_count or award.current_matches or 0
            bonanza_deducted = matching_bonanza_deductions.get(user.id, 0)
            actual_matching = max(0, stored_progress - bonanza_deducted)
            if include_eligibility:
                user_elig = _get_user_eligibility(user.id)
            else:
                user_elig = {'group_eligibility': None, 'eligibility_criteria': None}
            unified_awards.append({
                'award_id': award.id,
                'award_type': 'matching',
                'user_id': user.id,
                'user_name': user.name,
                'kyc_status': user.kyc_status or 'Pending',
                'is_activated': bool(user.activation_date),
                'rank_name': tier.award_name,
                'gift_name': tier.award_description,
                'tier_required': tier.cumulative_required,
                'achieved_count': actual_matching,
                'budgeted_amount': float(tier.actual_price) if tier.actual_price else 0.0,
                'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                'processed_status': award.processed_status,
                'simplified_status': SIMPLIFIED_DISPLAY_MAP.get(award.processed_status, award.processed_status),
                'status_display': AwardActionsService.get_status_display_label(award.processed_status),
                'status_color': AwardActionsService.get_status_badge_color(award.processed_status),
                'achievement_date': award.achievement_date.isoformat() if award.achievement_date else None,
                'approved_date': (award.admin_approved_at.isoformat() if hasattr(award, 'admin_approved_at') and award.admin_approved_at else None),
                'completed_date': (award.received_date.isoformat() if award.received_date else None),
                'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                'received_date': award.received_date.isoformat() if award.received_date else None,
                'group_eligibility': user_elig.get('group_eligibility'),
                'eligibility_criteria': user_elig.get('eligibility_criteria'),
                'available_actions': AwardActionsService.get_available_actions(
                    award.processed_status,
                    (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
                    'matching'
                )
            })
    
    # ========== BONANZA AWARDS ==========
    if include_bonanza:
        # Create alias for subquery to avoid correlation issues
        ReferralUser = aliased(User)
        
        query = db.query(
            DynamicBonanzaHistory,
            User,
            Bonanza
        ).join(
            User, DynamicBonanzaHistory.user_id == User.id
        ).outerjoin(
            Bonanza, DynamicBonanzaHistory.bonanza_id == Bonanza.id
        )
        
        eligible_referral_subquery = exists(
            select(ReferralUser.id).where(
                and_(
                    ReferralUser.referrer_id == DynamicBonanzaHistory.user_id,
                    ReferralUser.activation_date >= PRODUCTION_START_DATE
                )
            )
        )
        query = query.filter(eligible_referral_subquery)
        
        if status_filters:
            query = query.filter(DynamicBonanzaHistory.processed_status.in_(status_filters))
        if user_id_search:
            query = query.filter(User.id.ilike(f'%{user_id_search}%'))
        if user_name_search:
            query = query.filter(User.name.ilike(f'%{user_name_search}%'))
        if gift_name_search:
            query = query.filter(
                or_(
                    DynamicBonanzaHistory.award_name.ilike(f'%{gift_name_search}%'),
                    and_(Bonanza.name != None, Bonanza.name.ilike(f'%{gift_name_search}%'))
                )
            )
        if date_from:
            query = query.filter(DynamicBonanzaHistory.claimed_at >= date_from)
        if date_to:
            query = query.filter(DynamicBonanzaHistory.claimed_at <= date_to)
        
        bonanza_total = query.count()
        results = query.order_by(desc(DynamicBonanzaHistory.claimed_at)).offset(skip).limit(limit).all()
        
        for history, user, bonanza in results:
            bonanza_target = bonanza.target_requirement if bonanza and hasattr(bonanza, 'target_requirement') else 0
            bonanza_achieved = history.direct_count_achieved or history.matching_count_achieved or 0
            if include_eligibility:
                user_elig = _get_user_eligibility(user.id)
            else:
                user_elig = {'group_eligibility': None, 'eligibility_criteria': None}
            unified_awards.append({
                'award_id': history.id,
                'award_type': 'bonanza',
                'user_id': user.id,
                'user_name': user.name,
                'kyc_status': user.kyc_status or 'Pending',
                'is_activated': bool(user.activation_date),
                'rank_name': bonanza.name if bonanza else 'Bonanza',
                'gift_name': history.award_name or (bonanza.award_name if bonanza else None) or 'Cash Reward',
                'tier_required': bonanza_target,
                'achieved_count': bonanza_achieved,
                'budgeted_amount': float(history.budgeted_amount) if history.budgeted_amount else 0.0,
                'actual_cost_paid': float(history.actual_cost_paid) if history.actual_cost_paid else None,
                'processed_status': history.processed_status,
                'simplified_status': 'Claimed' if SIMPLIFIED_DISPLAY_MAP.get(history.processed_status, '') == 'Pending' else SIMPLIFIED_DISPLAY_MAP.get(history.processed_status, history.processed_status),
                'status_display': AwardActionsService.get_status_display_label(history.processed_status),
                'status_color': AwardActionsService.get_status_badge_color(history.processed_status),
                'achievement_date': history.claimed_at.isoformat() if history.claimed_at else None,
                'approved_date': (history.admin_approved_at.isoformat() if hasattr(history, 'admin_approved_at') and history.admin_approved_at else None),
                'completed_date': (history.received_date.isoformat() if history.received_date else None),
                'dispatch_date': history.dispatch_date.isoformat() if history.dispatch_date else None,
                'received_date': history.received_date.isoformat() if history.received_date else None,
                'group_eligibility': user_elig.get('group_eligibility'),
                'eligibility_criteria': user_elig.get('eligibility_criteria'),
                'available_actions': AwardActionsService.get_available_actions(
                    history.processed_status,
                    (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
                    'bonanza'
                ),
                'direct_contributors_snapshot': history.direct_contributors_snapshot if history.direct_contributors_snapshot else None,
                'matching_contributors_snapshot': history.matching_contributors_snapshot if history.matching_contributors_snapshot else None
            })
    
    unified_awards.sort(key=lambda x: x.get('achievement_date') or '', reverse=True)
    
    total_count = direct_total + matching_total + bonanza_total
    
    _query_elapsed = time.time() - _query_start
    logger.info(f"[AWARDS-PERF] Query took {_query_elapsed:.2f}s for {len(unified_awards)} awards (eligibility={'ON' if include_eligibility else 'OFF'})")
    
    result = {
        'success': True,
        'total_count': total_count,
        'returned_count': len(unified_awards),
        'skip': skip,
        'limit': limit,
        'awards': unified_awards,
        'cached': False,
        'query_time_ms': int(_query_elapsed * 1000)
    }

    # DC_AUDIENCE_001 — append envelope keys ONLY when caller passed `audience`
    # explicitly. Omitted param -> byte-identical pre-A1 response shape.
    if audience is not None:
        from app.core.audience_resolver import normalize_audience, audience_label
        aud = normalize_audience(audience)
        result['audience'] = aud
        result['audience_label'] = audience_label(aud)

    _awards_cache['data'] = {**result, 'cached': True}
    _awards_cache['timestamp'] = time.time()
    _awards_cache['cache_key'] = cache_key
    
    return result


@router.get("/user-eligibility/{user_id}")
async def get_user_eligibility_detail(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    from app.models.staff import StaffEmployee
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not isinstance(current_user, StaffEmployee):
    #     raise HTTPException(status_code=403, detail="Staff access required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    elig = check_direct_referrals_both_sides(db, user.id, return_details=True)
    if elig.get('is_eligible'):
        group_eligibility = 'Yes'
    elif elig.get('group_a_points', 0) < 1.0 and elig.get('group_b_points', 0) < 1.0:
        group_eligibility = 'No'
    elif elig.get('group_a_points', 0) < 1.0:
        group_eligibility = 'Group A Missing'
    else:
        group_eligibility = 'Group B Missing'
    
    full_elig = get_user_eligibility_status(db, user)
    
    return {
        'success': True,
        'user_id': user_id,
        'group_eligibility': group_eligibility,
        'eligibility_criteria': {
            'is_eligible': full_elig.get('is_eligible', False),
            'is_activated': full_elig.get('is_activated', False),
            'kyc_approved': (full_elig.get('kyc_status', 'pending') or 'pending').lower() == 'approved',
            'program_utilisation_completed': full_elig.get('program_utilisation_completed', False),
            'group_a_ok': full_elig.get('group_a_points', 0) >= 1.0,
            'group_b_ok': full_elig.get('group_b_points', 0) >= 1.0,
        }
    }


# ========== ACTION ENDPOINTS ==========

@router.post("/finance-approve")
async def finance_approve_award(
    data: ApprovalAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Finance Admin approves award"""
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'Finance Admin':
    #     raise HTTPException(status_code=403, detail="Only Finance Admin can approve")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # Update status
    award.processed_status = AwardStatus.ADMIN_APPROVED
    award.admin_approved_by = _resolve_actor_id(current_user)
    award.admin_approved_at = datetime.utcnow()
    if data.notes:
        award.admin_notes = data.notes
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='finance_approved',
        old_status=AwardStatus.PENDING_APPROVAL,
        new_status=AwardStatus.ADMIN_APPROVED,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=data.notes or 'Finance approved'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Award approved by Finance', 'new_status': AwardStatus.ADMIN_APPROVED}


@router.post("/rvz-direct-approve")
async def rvz_direct_approve_award(
    data: ApprovalAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ Supreme direct approval (skips Finance) - DC Protocol (Feb 2026): Staff access enabled"""
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # RVZ direct approval: skip Finance, go straight to RVZ Approved (Procurement Pending)
    award.processed_status = AwardStatus.PROCUREMENT_PENDING
    award.rvz_action_by = _resolve_actor_id(current_user)
    award.rvz_action_at = datetime.utcnow()
    award.rvz_action_type = 'direct_approve'
    award.rvz_notes = data.notes or 'RVZ Supreme Authority - Direct Approval (Finance step bypassed)'
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='rvz_direct_approved',
        old_status=AwardStatus.PENDING_APPROVAL,
        new_status=AwardStatus.PROCUREMENT_PENDING,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes='RVZ Supreme direct approval - Finance step bypassed'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'RVZ direct approval successful', 'new_status': AwardStatus.PROCUREMENT_PENDING}


@router.post("/rvz-approve")
async def rvz_approve_award(
    data: ApprovalAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """RVZ approves after Finance approval - DC Protocol (Feb 2026): Staff access enabled"""
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # Update status
    award.processed_status = AwardStatus.PROCUREMENT_PENDING
    award.rvz_action_by = _resolve_actor_id(current_user)
    award.rvz_action_at = datetime.utcnow()
    award.rvz_action_type = 'approve'
    award.rvz_notes = data.notes
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='rvz_approved',
        old_status=AwardStatus.ADMIN_APPROVED,
        new_status=AwardStatus.PROCUREMENT_PENDING,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=data.notes or 'RVZ approved'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'RVZ approval successful', 'new_status': AwardStatus.PROCUREMENT_PENDING}


@router.post("/reject")
async def reject_award(
    data: RejectionAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reject award (Finance or RVZ)
    DC PROTOCOL: Reverses bonanza deductions when bonanza claims are rejected
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    old_status = award.processed_status
    award.processed_status = AwardStatus.REJECTED
    award.rejection_reason = data.rejection_reason
    
    # DC PROTOCOL: Reverse bonanza deductions for rejected bonanza claims (IDEMPOTENT + SAFE)
    if data.award_type == 'bonanza':
        user_id = award.user_id
        deduction_direct = award.deduction_amount_direct or 0
        deduction_matching = award.deduction_amount_matching or 0
        
        # IDEMPOTENCY CHECK: Only reverse if flags indicate deductions were applied
        if award.deductions_applied_direct > 0 or award.deductions_applied_matching > 0:
            # Reverse DIRECT award deductions (iterate to avoid over-reversal)
            if deduction_direct > 0:
                remaining_direct_to_reverse = deduction_direct
                direct_awards = db.query(UserAwardProgress).filter(
                    UserAwardProgress.user_id == user_id,
                    UserAwardProgress.bonanza_deductions_applied > 0
                ).all()
                
                for record in direct_awards:
                    if remaining_direct_to_reverse <= 0:
                        break
                    # Reverse only up to what was deducted, clamped at zero
                    reversal_amount = min(remaining_direct_to_reverse, record.bonanza_deductions_applied)
                    record.bonanza_deductions_applied -= reversal_amount
                    record.effective_progress_count = record.current_referrals - record.bonanza_deductions_applied
                    remaining_direct_to_reverse -= reversal_amount
            
            # Reverse MATCHING award deductions
            if deduction_matching > 0:
                from app.models.awards import UserMatchingAwardProgress
                remaining_matching_to_reverse = deduction_matching
                matching_awards = db.query(UserMatchingAwardProgress).filter(
                    UserMatchingAwardProgress.user_id == user_id,
                    UserMatchingAwardProgress.bonanza_deductions_applied > 0
                ).all()
                
                for record in matching_awards:
                    if remaining_matching_to_reverse <= 0:
                        break
                    reversal_amount = min(remaining_matching_to_reverse, record.bonanza_deductions_applied)
                    record.bonanza_deductions_applied -= reversal_amount
                    record.effective_progress_count = record.current_matches - record.bonanza_deductions_applied
                    remaining_matching_to_reverse -= reversal_amount
            
            # Reset deduction flags (prevents double-reversal - idempotency)
            award.deductions_applied_direct = 0
            award.deductions_applied_matching = 0
            
            # Audit log for deduction reversal
            reversal_audit = AwardAuditLog(
                entity_type='bonanza_deduction_reversal',
                entity_id=data.award_id,
                action='deductions_reversed',
                old_status=f'Direct: {deduction_direct}, Matching: {deduction_matching}',
                new_status='Deductions: 0 (Idempotent)',
                actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
                actor_id=_resolve_actor_id(current_user),
                notes=f'Reversed {deduction_direct} direct + {deduction_matching} matching deductions due to rejection'
            )
            db.add(reversal_audit)
    
    # Create rejection audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='rejected',
        old_status=old_status,
        new_status=AwardStatus.REJECTED,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=data.rejection_reason
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Award rejected', 'new_status': AwardStatus.REJECTED}


@router.post("/record-procurement")
async def record_procurement(
    data: ProcurementData,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Record procurement details - DC Protocol (Feb 2026): Staff access enabled"""
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # Auto-calculate GST if not provided
    if data.gst_amount is None and data.handling_charges:
        data.gst_amount = round(data.handling_charges * 0.18, 2)
    
    # Update procurement fields
    award.actual_cost_paid = data.actual_cost_paid
    award.vendor_name = data.vendor_name
    award.payment_mode = data.payment_mode
    award.payment_reference = data.payment_reference
    award.bill_upload_path = data.bill_upload_path
    award.handling_charges = data.handling_charges
    award.gst_amount = data.gst_amount
    award.tax_amount = data.tax_amount
    award.transport_charges = data.transport_charges
    
    # Calculate cost variance
    budgeted_amount = award.budgeted_amount or 0
    award.cost_variance = budgeted_amount - data.actual_cost_paid
    award.cost_variance_reason = data.cost_variance_reason
    
    # Update status to Processed for Dispatch
    award.processed_status = AwardStatus.PROCESSED_FOR_DISPATCH
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='procurement_recorded',
        old_status=AwardStatus.PROCUREMENT_PENDING,
        new_status=AwardStatus.PROCESSED_FOR_DISPATCH,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=f'Procurement recorded: {data.vendor_name}, ₹{data.actual_cost_paid}'
    )
    db.add(audit)
    
    # Auto-create expense record (RVZ Expense System)
    try:
        expense_service = RVZExpenseService(db)
        expense_service.create_award_procurement_expense(
            award_id=data.award_id,
            award_type=data.award_type,
            actual_cost_paid=data.actual_cost_paid,
            vendor_name=data.vendor_name,
            payment_reference=data.payment_reference,
            created_by_user_id=_resolve_actor_id(current_user)
        )
    except Exception as e:
        # Log error but don't fail the procurement
        import logging
        logging.error(f"Failed to create expense record: {str(e)}")
    
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Procurement recorded successfully', 'new_status': AwardStatus.PROCESSED_FOR_DISPATCH}


@router.post("/mark-dispatched")
async def mark_dispatched(
    data: DispatchData,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark award as dispatched (shipped, in transit) - DC Protocol (Feb 2026): Staff access enabled"""
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # DC PROTOCOL: Update status to Dispatched (shipped, in transit)
    old_status = award.processed_status
    award.processed_status = AwardStatus.DISPATCHED
    
    # Update dispatch fields
    award.dispatch_date = data.dispatch_date
    award.courier_name = data.courier_name
    award.tracking_number = data.tracking_number
    
    if data.delivery_notes:
        if award.delivery_notes:
            award.delivery_notes += f" | {data.delivery_notes}"
        else:
            award.delivery_notes = data.delivery_notes
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='marked_dispatched',
        old_status=old_status,
        new_status=AwardStatus.DISPATCHED,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=f'Dispatched via {data.courier_name or "courier"} on {data.dispatch_date}'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Dispatch information recorded - Award shipped', 'new_status': AwardStatus.DISPATCHED}


@router.post("/mark-delivered")
async def mark_delivered(
    data: DeliveryData,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark award as delivered (final stage) - DC Protocol (Feb 2026): Staff access enabled"""
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # DC PROTOCOL: Update status to Delivered
    old_status = award.processed_status
    award.processed_status = AwardStatus.DELIVERED
    
    # Update delivery fields
    award.received_date = data.received_date
    award.delivered_by = _resolve_actor_id(current_user)
    award.delivered_at = datetime.utcnow()
    award.delivery_proof_path = data.delivery_proof_path
    
    if data.delivery_notes:
        if award.delivery_notes:
            award.delivery_notes += f" | {data.delivery_notes}"
        else:
            award.delivery_notes = data.delivery_notes
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='marked_delivered',
        old_status=old_status,
        new_status=AwardStatus.DELIVERED,
        actor_role=(getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))),
        actor_id=_resolve_actor_id(current_user),
        notes=f'Delivered on {data.received_date}'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Award marked as delivered - Final stage', 'new_status': AwardStatus.DELIVERED}


# ========== DC PROTOCOL FEB 2026: ALIASED ENDPOINTS FOR STAFF PORTAL ==========

@router.post("/validate")
async def validate_award(
    data: ApprovalAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Validate award (move from Pending to Pending Approval)
    Staff can validate achieved awards for approval review
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    old_status = award.processed_status
    award.processed_status = AwardStatus.PENDING_APPROVAL
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='validated',
        old_status=old_status,
        new_status=AwardStatus.PENDING_APPROVAL,
        actor_role=user_type,
        actor_id=_resolve_actor_id(current_user),
        notes=data.notes or 'Award validated for approval'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Award validated', 'new_status': str(AwardStatus.PENDING_APPROVAL)}


@router.post("/approve")
async def approve_award(
    data: ApprovalAction,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Approve award (move from Pending Approval to Procurement Pending)
    Staff can approve validated awards for procurement - mirrors rvz-direct-approve logic
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    old_status = award.processed_status
    award.processed_status = AwardStatus.PROCUREMENT_PENDING
    
    # Set approval metadata - match rvz-direct-approve logic
    user_id = current_user.id
    if isinstance(user_id, int):
        award.rvz_action_by = user_id
    award.rvz_action_at = datetime.utcnow()
    award.rvz_action_type = 'staff_approve'
    award.rvz_notes = data.notes or 'Staff Portal - Award approved for procurement'
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='approved',
        old_status=old_status,
        new_status=AwardStatus.PROCUREMENT_PENDING,
        actor_role=user_type,
        actor_id=_resolve_actor_id(current_user),
        notes=data.notes or 'Award approved for procurement'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Award approved', 'new_status': str(AwardStatus.PROCUREMENT_PENDING)}


@router.post("/process-procurement")
async def process_procurement(
    data: ProcurementData,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Process procurement (mirrors record-procurement logic)
    Full procurement processing for staff portal
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Finance Admin', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)
    
    # Auto-calculate GST if not provided
    if data.gst_amount is None and data.handling_charges:
        data.gst_amount = round(data.handling_charges * 0.18, 2)
    
    # Update all procurement fields - match record-procurement logic
    award.actual_cost_paid = data.actual_cost_paid
    award.vendor_name = data.vendor_name
    award.payment_mode = data.payment_mode
    award.payment_reference = data.payment_reference
    award.bill_upload_path = data.bill_upload_path
    award.handling_charges = data.handling_charges
    award.gst_amount = data.gst_amount
    award.tax_amount = data.tax_amount
    award.transport_charges = data.transport_charges
    
    # Calculate cost variance
    budgeted_amount = award.budgeted_amount or 0
    award.cost_variance = budgeted_amount - data.actual_cost_paid
    award.cost_variance_reason = data.cost_variance_reason
    
    # Update status to Processed for Dispatch
    old_status = award.processed_status
    award.processed_status = AwardStatus.PROCESSED_FOR_DISPATCH
    
    # Create audit log
    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action='procurement_processed',
        old_status=old_status,
        new_status=AwardStatus.PROCESSED_FOR_DISPATCH,
        actor_role=user_type,
        actor_id=_resolve_actor_id(current_user),
        notes=f'Procurement: {data.vendor_name}, ₹{data.actual_cost_paid}'
    )
    db.add(audit)
    
    # Auto-create expense record (RVZ Expense System)
    try:
        user_id = current_user.id if isinstance(current_user.id, int) else None
        if user_id:
            expense_service = RVZExpenseService(db)
            expense_service.create_award_procurement_expense(
                award_id=data.award_id,
                award_type=data.award_type,
                actual_cost_paid=data.actual_cost_paid,
                vendor_name=data.vendor_name,
                payment_reference=data.payment_reference,
                created_by_user_id=user_id
            )
    except Exception as e:
        import logging
        logging.error(f"Failed to create expense record: {str(e)}")
    
    db.commit()
    invalidate_awards_cache()
    
    return {'success': True, 'message': 'Procurement processed', 'new_status': str(AwardStatus.PROCESSED_FOR_DISPATCH)}


# ========== DC PROTOCOL FEB 2026: SIMPLIFIED STATUS MANAGEMENT ==========

@router.post("/update-status")
async def simplified_status_update(
    data: SimplifiedStatusUpdate = Body(...),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Simplified status update for staff portal.
    Maps simplified statuses (Approved/Processed/Completed/Rejected) to DB values.
    Logs comment to audit trail.
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['staff', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'Admin', 'Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Access denied - staff only")

    if data.new_status not in SIMPLIFIED_STATUS_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(SIMPLIFIED_STATUS_MAP.keys())}")

    db_status = SIMPLIFIED_STATUS_MAP[data.new_status]

    manager = UnifiedAwardStatusManager(db)
    model_class, award = manager.get_award_model_and_instance(data.award_id, data.award_type)

    old_status = award.processed_status
    old_display = SIMPLIFIED_DISPLAY_MAP.get(old_status, old_status)

    if data.new_status == 'Approved' and old_status == 'Pending' and data.award_type in ('direct', 'matching'):
        award_user_id = award.user_id
        from app.services.award_service import AwardService
        award_svc = AwardService(db)
        elig = award_svc.check_universal_eligibility(award_user_id)
        if not elig.get('is_eligible', False):
            failed = elig.get('failed_checks', [])
            reasons = '; '.join(failed) if failed else 'Group eligibility criteria not met'
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve this award yet. {reasons}. The award will be auto-promoted to 'Pending Approval' once all eligibility criteria are fulfilled."
            )
        award.processed_status = AwardStatus.PENDING_APPROVAL
        if not award.achievement_date:
            award.achievement_date = datetime.utcnow()
        approve_audit = AwardAuditLog(
            entity_type=f'{data.award_type}_award',
            entity_id=data.award_id,
            action='staff_promoted_to_pending_approval',
            old_status=old_status,
            new_status='Pending Approval',
            actor_role=user_type,
            actor_id=_resolve_actor_id(current_user),
            notes=data.comment or 'Staff manually promoted Pending → Pending Approval (eligibility verified)'
        )
        db.add(approve_audit)
        db.commit()
        invalidate_awards_cache()
        return {
            'success': True,
            'message': 'Award promoted to Pending Approval (eligibility verified). You can now approve it for procurement.',
            'old_status': old_display,
            'new_status': 'Pending Approval',
            'db_status': 'Pending Approval'
        }

    if data.new_status == 'Rejected' and data.award_type == 'bonanza':
        award.processed_status = AwardStatus.REJECTED
        award.rejection_reason = data.comment or 'Rejected by staff'

        user_id = award.user_id
        deduction_direct = award.deduction_amount_direct or 0
        deduction_matching = award.deduction_amount_matching or 0

        if award.deductions_applied_direct > 0 or award.deductions_applied_matching > 0:
            if deduction_direct > 0:
                remaining = deduction_direct
                direct_awards = db.query(UserAwardProgress).filter(
                    UserAwardProgress.user_id == user_id,
                    UserAwardProgress.bonanza_deductions_applied > 0
                ).all()
                for record in direct_awards:
                    if remaining <= 0:
                        break
                    reversal = min(remaining, record.bonanza_deductions_applied)
                    record.bonanza_deductions_applied -= reversal
                    record.effective_progress_count = record.current_referrals - record.bonanza_deductions_applied
                    remaining -= reversal

            if deduction_matching > 0:
                remaining = deduction_matching
                matching_awards = db.query(UserMatchingAwardProgress).filter(
                    UserMatchingAwardProgress.user_id == user_id,
                    UserMatchingAwardProgress.bonanza_deductions_applied > 0
                ).all()
                for record in matching_awards:
                    if remaining <= 0:
                        break
                    reversal = min(remaining, record.bonanza_deductions_applied)
                    record.bonanza_deductions_applied -= reversal
                    record.effective_progress_count = record.current_matches - record.bonanza_deductions_applied
                    remaining -= reversal

            award.deductions_applied_direct = 0
            award.deductions_applied_matching = 0

            reversal_audit = AwardAuditLog(
                entity_type='bonanza_deduction_reversal',
                entity_id=data.award_id,
                action='deductions_reversed',
                old_status=f'Direct: {deduction_direct}, Matching: {deduction_matching}',
                new_status='Deductions: 0 (Reversed)',
                actor_role=user_type,
                actor_id=_resolve_actor_id(current_user),
                notes=f'Reversed deductions due to rejection: {data.comment or ""}'
            )
            db.add(reversal_audit)
    else:
        award.processed_status = db_status

    actor_id_str = getattr(current_user, 'emp_code', None) or str(current_user.id)

    if data.new_status == 'Approved':
        award.admin_approved_at = datetime.utcnow()
        award.admin_approved_by = actor_id_str
        if data.comment:
            award.admin_notes = data.comment

    if data.new_status == 'Completed':
        award.received_date = date.today()
        award.delivered_at = datetime.utcnow()
        award.delivered_by = _resolve_actor_id(current_user)

    if data.new_status == 'Rejected' and data.award_type != 'bonanza':
        award.rejection_reason = data.comment or 'Rejected by staff'

    audit = AwardAuditLog(
        entity_type=f'{data.award_type}_award',
        entity_id=data.award_id,
        action=f'status_updated_to_{data.new_status.lower()}',
        old_status=old_status,
        new_status=db_status.value,
        actor_role=user_type,
        actor_id=actor_id_str,
        notes=data.comment or f'Status changed from {old_display} to {data.new_status}'
    )
    db.add(audit)
    db.commit()
    invalidate_awards_cache()

    return {
        'success': True,
        'message': f'Status updated to {data.new_status}',
        'old_status': old_display,
        'new_status': data.new_status,
        'db_status': db_status.value
    }


@router.get("/status-history/{award_type}/{award_id}")
async def get_status_history(
    award_type: str,
    award_id: int,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Get full status change history for an award with comments.
    Returns timeline of all status changes with actor, timestamp, and notes.
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    allowed_roles = ['staff', 'RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'Admin', 'Finance Admin']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in allowed_roles:
    #     raise HTTPException(status_code=403, detail="Access denied")

    entity_type = f'{award_type}_award'
    logs = db.query(AwardAuditLog).filter(
        AwardAuditLog.entity_type == entity_type,
        AwardAuditLog.entity_id == award_id
    ).order_by(AwardAuditLog.timestamp.asc()).all()

    history = []
    for log in logs:
        old_display = SIMPLIFIED_DISPLAY_MAP.get(log.old_status, log.old_status) if log.old_status else None
        new_display = SIMPLIFIED_DISPLAY_MAP.get(log.new_status, log.new_status)
        history.append({
            'id': log.id,
            'action': log.action,
            'old_status': old_display,
            'new_status': new_display,
            'actor_role': log.actor_role,
            'actor_id': log.actor_id,
            'comment': log.notes,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
        })

    return {
        'success': True,
        'award_type': award_type,
        'award_id': award_id,
        'history': history
    }
