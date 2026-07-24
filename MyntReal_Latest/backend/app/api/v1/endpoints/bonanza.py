"""
Bonanza System Endpoints - Time-bound reward campaigns
Super Admin creates, Finance Admin approves, Users track progress
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.models.bonanza import Bonanza, DynamicBonanzaHistory, BonanzaSlab  # DC Protocol: BonanzaProgress deprecated
from app.models.crm import CRMLeadDeal
from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_user_hybrid_with_partner, get_current_vgk_partner_any, require_kyc_approval
from app.core.scheduler import calculate_effective_matching_count
from app.core.rvz_protection import (
    verify_rvz_access,
    verify_rvz_secondary_password,
    create_deletion_audit_log,
    create_restore_audit_log
)
from app.constants.award_statuses import AwardStatus  # DC Protocol: Unified status constants

router = APIRouter(prefix="/bonanza", tags=["Bonanza System"])
logger = logging.getLogger(__name__)


def _compress_bonanza_img(data: bytes, content_type: str):
    """
    DC_BONANZA_IMG_COMPRESS_001: Compress bonanza image to WebP before storage.
    Resizes to max 800px wide, quality 75. Falls back to original on failure.
    Returns (compressed_bytes, ext_string).
    """
    try:
        import io as _io
        from PIL import Image as _Image
        img = _Image.open(_io.BytesIO(data))
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA' if img.mode in ('P', 'LA') else 'RGB')
        if img.width > 800:
            new_h = int(img.height * 800 / img.width)
            img = img.resize((800, new_h), _Image.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format='WEBP', quality=75, method=4)
        compressed = buf.getvalue()
        logger.info(
            f'[BNZ-IMG-COMPRESS] {len(data)//1024}KB → {len(compressed)//1024}KB '
            f'({round((1 - len(compressed)/len(data))*100)}% saved)'
        )
        return compressed, 'webp'
    except Exception as _e:
        logger.warning(f'[BNZ-IMG-COMPRESS] fallback to original — {_e}')
        ext = (content_type or '').split('/')[-1].replace('jpeg', 'jpg') or 'jpg'
        return data, ext


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


class BonanzaUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_requirement: Optional[int] = None
    max_winners: Optional[int] = None
    award_name: Optional[str] = None
    reward_amount: Optional[float] = None
    counts_towards_regular: Optional[bool] = None
    consume_achievements: Optional[bool] = None
    portal: Optional[str] = None
    grace_days: Optional[int] = None
    lead_source_id: Optional[int] = None
    segment_id: Optional[int] = None  # DC Protocol: VGK segment filter (FK signup_categories)
    registered_target_bonus: Optional[int] = None  # DC Protocol: extra deals required for registered (non-activated) VGK members
    image_url: Optional[str] = None  # DC-BONANZA-IMG-001: promo image URL
    reward_text: Optional[str] = None
    # DC_BONANZA_SLABWISE_001
    slab_extra_amount: Optional[float] = None
    slab_base_reference: Optional[float] = None
    # DC-SOLAR-DVR-ADV-20260701-001: 'CIBIL'|'DVR'|'BOTH'
    advance_count_basis: Optional[str] = None
    # DC-EXTRA-COMM-001
    trigger_event: Optional[str] = None
    ec_l1_amount: Optional[float] = None
    ec_l2_amount: Optional[float] = None
    ec_l3_amount: Optional[float] = None
    ec_l4_amount: Optional[float] = None
    ec_l5_amount: Optional[float] = None
    category_filter_ids: Optional[List[int]] = None
    # DC-AWARD-TRIGGER-001
    award_level_notes: Optional[dict] = None
    # DC-EC-PER-LEVEL-TRIGGER-001: per-level trigger events (all trigger-capable types)
    ec_l1_trigger: Optional[str] = None
    ec_l2_trigger: Optional[str] = None
    ec_l3_trigger: Optional[str] = None
    ec_l4_trigger: Optional[str] = None
    ec_l5_trigger: Optional[str] = None


class BonanzaCreate(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    criteria_type: str
    target_requirement: int
    counts_towards_regular: bool = False
    consume_achievements: bool = False  # Prevent reusing achievements for other bonanzas
    
    # Reward details - supports both monetary and non-monetary (awards/gifts)
    reward_type: str = 'cash'  # 'cash', 'bonus', 'award', 'gift'
    reward_amount: Optional[float] = None  # Null for award/gift types
    award_name: Optional[str] = None  # Required for award/gift types
    is_monetary: bool = True  # False for awards/gifts
    
    reward_text: Optional[str] = None
    reward_file: Optional[str] = None
    total_budget: Optional[float] = None
    
    # Winners limit (First Come First Served)
    max_winners: int = 50  # Default: Top 50 winners

    # DC Protocol: Portal + deal-eligibility config
    portal: str = 'MNR'  # 'MNR' or 'VGK'
    grace_days: int = 15  # days after bonanza END date for physical completion (VGK default)
    lead_source_id: Optional[int] = None  # FK crm_lead_sources.id — restrict to this source
    segment_id: Optional[int] = None  # FK signup_categories.id — VGK segment filter (Solar/EV/etc)
    registered_target_bonus: Optional[int] = None  # DC Protocol: extra deals required for registered (non-activated) VGK members; NULL = disabled

    # DC_BONANZA_SLABWISE_001: Slab Wise fields
    # slab_extra_amount  — the bonus this campaign pays on top of the base (e.g. ₹3000); required for slab_wise reward_type
    # slab_base_reference — display-only base the member already gets from Solar File Advance (e.g. ₹1000); shown on earner card
    slab_extra_amount: Optional[float] = None
    slab_base_reference: Optional[float] = None

    # DC-SOLAR-DVR-ADV-20260701-001: which advance kind counts toward this bonanza's target.
    # 'CIBIL' (default) = only CIBIL-cleared advances (kind='ADVANCE').
    # 'DVR'             = only first-payment DVR advances (kind='DVR_ADVANCE').
    # 'BOTH'            = either type (DISTINCT lead_id, no double-count).
    advance_count_basis: Optional[str] = 'CIBIL'

    # DC-EXTRA-COMM-001 (Jul 2026): Special Bonanza — per-file extra commission fields.
    # Required when reward_type = 'extra_commission'.
    trigger_event: Optional[str] = None          # 'file_submitted'|'first_payment'|'file_completed' (global fallback)
    ec_l1_amount: Optional[float] = None
    ec_l2_amount: Optional[float] = None
    ec_l3_amount: Optional[float] = None
    ec_l4_amount: Optional[float] = None
    ec_l5_amount: Optional[float] = None
    category_filter_ids: Optional[List[int]] = None  # NULL = all categories; also used by cash/bonus triggers

    # DC-AWARD-TRIGGER-001 (Jul 2026): Award/Gift trigger config.
    # Required when reward_type in ('award','gift') AND trigger_event is set.
    # {"1": {"participate": true, "note": "..."}, "2": {"participate": false}, ...}
    award_level_notes: Optional[dict] = None

    # DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): per-level trigger events — all trigger-capable types.
    # Each level fires at its own configured trigger. NULL = use global trigger_event as fallback.
    ec_l1_trigger: Optional[str] = None
    ec_l2_trigger: Optional[str] = None
    ec_l3_trigger: Optional[str] = None
    ec_l4_trigger: Optional[str] = None
    ec_l5_trigger: Optional[str] = None


class BonanzaApprove(BaseModel):
    approval_comments: Optional[str] = None  # DC Protocol: Optional approval notes


class BonanzaDeleteRequest(BaseModel):
    deletion_reason: str  # MANDATORY: RVZ must provide reason for deletion


class BonanzaSelection(BaseModel):
    bonanza_id: int


class BonanzaProcessing(BaseModel):
    progress_id: int
    admin_notes: Optional[str] = None


@router.post("/create")
async def create_bonanza(
    data: BonanzaCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Super Admin creates bonanza campaign
    Supports both monetary (cash/bonus) and non-monetary (award/gift) rewards
    """
    user_type = str((getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')))
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Only Super Admin can create bonanzas"
    #     )
    
    # Validation: For award/gift types, award_name is required
    if data.reward_type in ['award', 'gift'] and not data.award_name:
        raise HTTPException(
            status_code=400, 
            detail="Award name is required for award/gift type bonanzas"
        )
    
    # DC_BONANZA_SLABWISE_001: For slab_wise, slab_extra_amount is required; reward_amount is not used
    if data.reward_type == 'slab_wise' and not data.slab_extra_amount:
        raise HTTPException(
            status_code=400,
            detail="Slab extra amount is required for Slab Wise bonanzas"
        )

    # DC-EC-PER-LEVEL-TRIGGER-001: validate trigger events for all trigger-capable types
    _valid_triggers = {'file_submitted', 'first_payment', 'file_completed'}
    _all_trigger_fields = [
        data.ec_l1_trigger, data.ec_l2_trigger, data.ec_l3_trigger,
        data.ec_l4_trigger, data.ec_l5_trigger, data.trigger_event,
    ]
    for _t in _all_trigger_fields:
        if _t and _t not in _valid_triggers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger value: '{_t}'. Must be one of: {sorted(_valid_triggers)}"
            )

    # DC-EXTRA-COMM-001 + DC-EC-PER-LEVEL-TRIGGER-001: extra_commission requires at least one trigger + amount
    if data.reward_type == 'extra_commission':
        _per_level_triggers = [
            data.ec_l1_trigger, data.ec_l2_trigger, data.ec_l3_trigger,
            data.ec_l4_trigger, data.ec_l5_trigger,
        ]
        _has_any_trigger = any(_per_level_triggers) or data.trigger_event
        if not _has_any_trigger:
            raise HTTPException(
                status_code=400,
                detail=f"At least one trigger must be configured for extra_commission bonanzas: "
                       f"set a global trigger_event or per-level ec_l1_trigger … ec_l5_trigger. "
                       f"Valid values: {sorted(_valid_triggers)}"
            )
        _ec_amounts = [
            data.ec_l1_amount, data.ec_l2_amount, data.ec_l3_amount,
            data.ec_l4_amount, data.ec_l5_amount,
        ]
        if not any(_ec_amounts):
            raise HTTPException(
                status_code=400,
                detail="At least one level amount (ec_l1_amount … ec_l5_amount) must be set "
                       "for extra_commission bonanzas"
            )

    # DC_BONANZA_SLABWISE_AUTO_001: One active Slab Wise per segment — no overlapping campaigns
    if data.reward_type == 'slab_wise':
        from sqlalchemy import text as _t
        if data.segment_id is None:
            _dup = db.execute(_t("""
                SELECT id, name FROM bonanza
                WHERE reward_type = 'slab_wise'
                  AND status IN ('Pending', 'Approved')
                  AND portal = 'VGK'
                  AND segment_id IS NULL
                LIMIT 1
            """)).fetchone()
        else:
            _dup = db.execute(_t("""
                SELECT id, name FROM bonanza
                WHERE reward_type = 'slab_wise'
                  AND status IN ('Pending', 'Approved')
                  AND portal = 'VGK'
                  AND segment_id = :sid
                LIMIT 1
            """), {'sid': data.segment_id}).fetchone()
        if _dup:
            _seg_label = f'segment #{data.segment_id}' if data.segment_id else 'All Segments'
            raise HTTPException(
                status_code=400,
                detail=f"A Slab Wise campaign already exists for {_seg_label}: '{_dup.name}'. Only one active Slab Wise bonanza per segment is allowed."
            )

    # Validation: For monetary types (non-slab), reward_amount should be provided
    if data.reward_type in ['cash', 'bonus'] and not data.reward_amount:
        raise HTTPException(
            status_code=400,
            detail="Reward amount is required for cash/bonus type bonanzas"
        )
    
    # DC-BONANZA-DATE-ONLY-001: strip any time component — bonanzas use date boundaries only,
    # always midnight (00:00:00). Prevents same-day leads being excluded by time comparison.
    _sd = data.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    _ed = data.end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    bonanza = Bonanza(
        name=data.name,
        start_date=_sd,
        end_date=_ed,
        criteria_type=data.criteria_type,
        target_requirement=data.target_requirement,
        counts_towards_regular=data.counts_towards_regular,
        consume_achievements=data.consume_achievements,
        
        # Reward details
        reward_type=data.reward_type,
        reward_amount=data.reward_amount,
        award_name=data.award_name,
        is_monetary=data.is_monetary if data.reward_type != 'slab_wise' else True,
        reward_text=data.reward_text,
        reward_file=data.reward_file,
        
        total_budget=data.total_budget,
        max_winners=data.max_winners,
        current_winners=0,
        created_by=getattr(current_user, 'emp_code', None) or str(current_user.id),
        status='Pending',

        # DC Protocol: Portal + deal-eligibility
        portal=data.portal,
        grace_days=data.grace_days,
        lead_source_id=data.lead_source_id,
        segment_id=data.segment_id,
        registered_target_bonus=data.registered_target_bonus,

        # DC_BONANZA_SLABWISE_001
        slab_extra_amount=data.slab_extra_amount,
        slab_base_reference=data.slab_base_reference,
        # DC-SOLAR-DVR-ADV-20260701-001
        advance_count_basis=data.advance_count_basis or 'DVR',

        # DC-EXTRA-COMM-001
        trigger_event=data.trigger_event if data.reward_type in ('extra_commission', 'award', 'gift') else None,
        ec_l1_amount=data.ec_l1_amount if data.reward_type in ('extra_commission', 'cash', 'bonus') else None,
        ec_l2_amount=data.ec_l2_amount if data.reward_type in ('extra_commission', 'cash', 'bonus') else None,
        ec_l3_amount=data.ec_l3_amount if data.reward_type in ('extra_commission', 'cash', 'bonus') else None,
        ec_l4_amount=data.ec_l4_amount if data.reward_type in ('extra_commission', 'cash', 'bonus') else None,
        ec_l5_amount=data.ec_l5_amount if data.reward_type in ('extra_commission', 'cash', 'bonus') else None,

        # DC-AWARD-TRIGGER-001: award/gift per-level participation config
        award_level_notes=data.award_level_notes if data.reward_type in ('award', 'gift') else None,

        # DC-EC-PER-LEVEL-TRIGGER-001: per-level trigger events (all non-slab types)
        ec_l1_trigger=data.ec_l1_trigger if data.reward_type != 'slab_wise' else None,
        ec_l2_trigger=data.ec_l2_trigger if data.reward_type != 'slab_wise' else None,
        ec_l3_trigger=data.ec_l3_trigger if data.reward_type != 'slab_wise' else None,
        ec_l4_trigger=data.ec_l4_trigger if data.reward_type != 'slab_wise' else None,
        ec_l5_trigger=data.ec_l5_trigger if data.reward_type != 'slab_wise' else None,
    )
    
    db.add(bonanza)
    db.commit()
    db.refresh(bonanza)

    # DC-EXTRA-COMM-001 / DC-AWARD-TRIGGER-001: persist category filters after bonanza is committed
    if data.reward_type in ('extra_commission', 'award', 'gift', 'cash', 'bonus') and data.category_filter_ids:
        for _cat_id in data.category_filter_ids:
            db.execute(text("""
                INSERT INTO bonanza_category_filters (bonanza_id, category_id)
                VALUES (:bid, :cid)
                ON CONFLICT (bonanza_id, category_id) DO NOTHING
            """), {'bid': bonanza.id, 'cid': _cat_id})
        db.commit()
    
    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' created successfully",
        "bonanza_id": bonanza.id,
        "reward_type": bonanza.reward_type,
        "is_monetary": bonanza.is_monetary
    }


@router.get("/list")
async def list_bonanzas(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    List all bonanzas (filtered by status)
    DC Protocol: Supports hybrid authentication for both MNR users and Staff users
    """
    # DC Protocol: Handle both User and StaffEmployee objects
    # StaffEmployee uses staff_type, User uses user_type
    user_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', 'RVZ ID')
    
    query = db.query(Bonanza).filter(Bonanza.is_deleted == False)  # Exclude soft-deleted
    
    if status:
        query = query.filter(Bonanza.status == status)
    
    bonanzas = query.order_by(Bonanza.created_at.desc()).all()
    
    return {
        "success": True,
        "bonanzas": [
            {
                "id": b.id,
                "name": b.name,
                "criteria_type": b.criteria_type,
                "target_requirement": b.target_requirement,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None,
                "status": b.status,
                "created_by": b.created_by,
                "approved_by": b.approved_by,
                
                # Reward details (supports monetary and non-monetary)
                "reward_type": b.reward_type,
                "is_monetary": b.is_monetary,
                "reward_amount": float(b.reward_amount) if b.reward_amount else None,
                "award_name": b.award_name,
                "reward_text": b.reward_text,

                # DC_BONANZA_SLABWISE_001: Slab Wise fields
                "slab_extra_amount": float(b.slab_extra_amount) if b.slab_extra_amount else None,
                "slab_base_reference": float(b.slab_base_reference) if b.slab_base_reference else None,
                "slab_total_display": float((b.slab_base_reference or 0) + (b.slab_extra_amount or 0)) if b.slab_extra_amount else None,
                "advance_count_basis": b.advance_count_basis or 'CIBIL',

                # DC-EXTRA-COMM-001: Extra commission fields
                "trigger_event":  b.trigger_event,
                "ec_l1_amount":   float(b.ec_l1_amount)  if b.ec_l1_amount  else None,
                "ec_l2_amount":   float(b.ec_l2_amount)  if b.ec_l2_amount  else None,
                "ec_l3_amount":   float(b.ec_l3_amount)  if b.ec_l3_amount  else None,
                "ec_l4_amount":   float(b.ec_l4_amount)  if b.ec_l4_amount  else None,
                "ec_l5_amount":   float(b.ec_l5_amount)  if b.ec_l5_amount  else None,
                "category_filter_ids": [
                    row[0] for row in db.execute(
                        text("SELECT category_id FROM bonanza_category_filters WHERE bonanza_id = :bid"),
                        {"bid": b.id}
                    ).fetchall()
                ] if b.reward_type in ('extra_commission', 'award', 'gift', 'cash', 'bonus') else [],

                # DC-AWARD-TRIGGER-001: award/gift trigger level config
                "award_level_notes": b.award_level_notes,

                # DC-EC-PER-LEVEL-TRIGGER-001: per-level trigger events
                "ec_l1_trigger":  b.ec_l1_trigger,
                "ec_l2_trigger":  b.ec_l2_trigger,
                "ec_l3_trigger":  b.ec_l3_trigger,
                "ec_l4_trigger":  b.ec_l4_trigger,
                "ec_l5_trigger":  b.ec_l5_trigger,

                # Max winners tracking
                "max_winners": b.max_winners or 50,
                "current_winners": b.current_winners or 0,
                
                # DC Protocol: Portal + deal-eligibility
                "portal": b.portal or 'MNR',
                "grace_days": b.grace_days if b.grace_days is not None else 15,
                "lead_source_id": b.lead_source_id,
                "segment_id": b.segment_id,

                "price_info": b.get_display_price_for_role(user_type)
            }
            for b in bonanzas
        ]
    }


def _count_first_dvr_income_for_bonanza(db: Session, partner_id: int, bonanza) -> int:
    """
    DC-BONANZA-FIRST-DVR-002 (Jul 2026): Count leads where a CONFIRMED income entry
    with income_date within the bonanza window exists, linked to a lead owned by
    this partner (associated_partner_id).

    Replaces the vgk_cash_income_entries COMMISSION-kind approach (DC-BONANZA-FIRST-DVR-001)
    which required COMMISSION ledger records that were never reliably generated for
    solar 'won' leads (only triggered on CRM 'completed' status).

    Rules:
      - income_entries.status = 'CONFIRMED' — official confirmation by accounts.
      - income_entries.income_date within bonanza window + grace days — the
        business event date (when money was received), not the confirmation date.
      - crm_leads.associated_partner_id = partner_id — lead owner perspective,
        consistent with the management tracking query.
      - COUNT(DISTINCT lead_id) prevents double-counting multi-payment leads.
    """
    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    row = db.execute(text("""
        SELECT COUNT(DISTINCT ie.lead_id)
        FROM income_entries ie
        JOIN crm_leads cl ON cl.id = ie.lead_id
        WHERE cl.associated_partner_id = :pid
          AND ie.status = 'CONFIRMED'
          AND ie.lead_id IS NOT NULL
          AND ie.income_date >= :start
          AND ie.income_date <= :end + INTERVAL '1 day' * :grace
    """), {
        'pid': partner_id,
        'start': bonanza.start_date,
        'end': bonanza.end_date,
        'grace': grace,
    }).scalar()
    return int(row or 0)


def _count_first_pmt_for_bonanza(db: Session, partner_id: int, bonanza) -> int:
    """
    DC-BONANZA-FIRST-PMT-CLAIM-001 (Jul 2026): Count qualifying leads for a single
    partner using crm_leads.first_payment_received_date (actual money received date).

    Mirrors the member-tracking else-branch query so that member tracking and the
    claim gate always show the same number.

    DC-BONANZA-SRC-REF-001: also counts leads where the partner is stored only as
    source_ref_id (type vgk/vgk_partner/partner) and associated_partner_id is NULL.
    This handles the "ground source" case where the VGK partner who brought the
    customer is stored as source reference but not synced to associated_partner_id.
    """
    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    seg   = bonanza.segment_id
    if seg and seg in _SOLAR_CAT_IDS:
        seg_clause = "AND cl.category_id = ANY(:seg_list)"
        params = {'pid': partner_id, 'start': bonanza.start_date,
                  'end': bonanza.end_date, 'grace': grace,
                  'seg_list': list(_SOLAR_CAT_IDS)}
    elif seg:
        seg_clause = "AND cl.category_id = :seg"
        params = {'pid': partner_id, 'start': bonanza.start_date,
                  'end': bonanza.end_date, 'grace': grace, 'seg': seg}
    else:
        seg_clause = ""
        params = {'pid': partner_id, 'start': bonanza.start_date,
                  'end': bonanza.end_date, 'grace': grace}
    row = db.execute(text(f"""
        SELECT COUNT(DISTINCT cl.id)
        FROM crm_leads cl
        WHERE COALESCE(
                cl.associated_partner_id,
                CASE WHEN cl.source_ref_type IN ('vgk','vgk_partner','partner')
                          AND cl.source_ref_id IS NOT NULL
                          AND cl.source_ref_id ~ '^[0-9]+$'
                     THEN cl.source_ref_id::int END
              ) = :pid
          AND cl.first_payment_received_date IS NOT NULL
          AND cl.first_payment_received_date >= CAST(:start AS DATE)
          AND cl.first_payment_received_date <= CAST(:end AS DATE) + CAST(:grace || ' days' AS INTERVAL)
          {seg_clause}
    """), params).scalar()
    return int(row or 0)


def _count_solar_advances_for_bonanza(db: Session, partner_id: int, bonanza, basis_override: str = None) -> int:
    """
    DC-BONANZA-SUBMITDATE-001 (Jun 2026): Count qualifying solar advances for a
    slab_wise bonanza.  Eligibility is determined by the LEAD's submit_date (when
    the bank file was physically submitted by the partner) — NOT the advance
    created_at (system entry date).  A file submitted in April must not qualify
    for a May–June campaign even if the advance entry was created later.

    DC-SOLAR-DVR-ADV-20260701-001: advance_count_basis on the bonanza controls
    which advance kind counts:
      'CIBIL' (default/NULL) — only kind='ADVANCE' (CIBIL-cleared).
      'DVR'                  — only kind='DVR_ADVANCE' (first-payment, gate ≥2026-07-01).
      'BOTH'                 — either kind; DISTINCT lead_id prevents double-counting.

    DC-CIBIL-DATE-OVERRIDE-001: effective date for bonanza window check is
      GREATEST(submit_date, cibil_score_updated_at::date)
    If the bank file was submitted in April but CIBIL score was entered in July,
    the lead counts toward the July bonanza window, not April.

    basis_override: when set, overrides bonanza.advance_count_basis (used by
    DC-SOLAR-AWARD-DVR-001 to force DVR counting for award/gift bonanzas).

    Rules:
      - status IN ('RELEASED','PENDING') only.  ADJUSTED / RECOVERED / DEFICIT
        are clawback/reversal statuses and must not count.
      - effective_date must fall within bonanza.start_date … bonanza.end_date + grace_days.
      - NULL submit_date (e.g. loan_rejected leads) = ineligible.
    """
    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    basis = (basis_override or getattr(bonanza, 'advance_count_basis', None) or 'CIBIL').upper()

    # DC-FIRST-PMT-001 / DC-DVR-WINDOW-FIX-001: effective date depends on basis.
    # DVR  → first_payment_received_date (actual money received, from crm_lead_transactions)
    # CIBIL→ GREATEST(submit_date, cibil_score_updated_at::date)  (CIBIL clearance date)
    # BOTH → per-row CASE: DVR rows use first_payment_received_date, CIBIL rows use cibil date
    # NOTE: first_dvr_confirmed_at is the system timestamp when the advance record was created
    # — NOT when money was received. Do NOT use it for date-window filtering.
    if basis == 'DVR':
        # DC-FIRST-PMT-001: use actual first validated payment date, not system advance timestamp
        kind_filter  = "AND a.kind = 'DVR_ADVANCE'"
        count_expr   = "COUNT(*)"
        eff_date_sql = "cl.first_payment_received_date"
        null_guard   = "cl.first_payment_received_date IS NOT NULL"
    elif basis == 'BOTH':
        kind_filter  = (
            "AND ("
            "  a.kind = 'ADVANCE' "
            "  OR (a.kind = 'DVR_ADVANCE' "
            "      AND cl.first_payment_received_date IS NOT NULL)"
            ")"
        )
        count_expr   = "COUNT(DISTINCT a.lead_id)"
        eff_date_sql = (
            "CASE WHEN a.kind = 'DVR_ADVANCE' "
            "THEN cl.first_payment_received_date "
            "ELSE GREATEST(cl.submit_date, COALESCE(cl.cibil_score_updated_at::date, cl.submit_date)) END"
        )
        null_guard   = "cl.submit_date IS NOT NULL"
    else:  # CIBIL (default)
        kind_filter  = "AND a.kind = 'ADVANCE'"
        count_expr   = "COUNT(*)"
        eff_date_sql = "GREATEST(cl.submit_date, COALESCE(cl.cibil_score_updated_at::date, cl.submit_date))"
        null_guard   = "cl.submit_date IS NOT NULL"

    row = db.execute(text(f"""
        SELECT {count_expr}
        FROM vgk_solar_cibil_advances a
        JOIN crm_leads cl ON cl.id = a.lead_id
        WHERE a.partner_id = :pid
          AND a.status IN ('RELEASED','PENDING')
          AND {null_guard}
          AND {eff_date_sql} >= CAST(:start AS DATE)
          AND {eff_date_sql} <= CAST(:end AS DATE) + CAST(:grace || ' days' AS INTERVAL)
          {kind_filter}
    """), {
        'pid': partner_id,
        'start': bonanza.start_date,
        'end': bonanza.end_date,
        'grace': grace,
    }).scalar()
    return int(row or 0)


# DC-SOLAR-AWARD-DVR-001: Solar IDs across all 4 companies (1,2,3,4)
_SOLAR_CAT_IDS = (6, 19, 36, 48)
_SOLAR_AWARD_DVR_CUTOFF = datetime(2026, 7, 1)


def _is_solar_award_dvr(db: Session, bonanza) -> bool:
    """
    DC-SOLAR-AWARD-DVR-001 (Jul 2026): Award/gift bonanzas created on or after
    2026-07-01 that target the Solar category use DVR (first-payment advance)
    counting instead of CRM-completed deal counting.

    Returns True only when ALL three conditions hold:
      1. reward_type in ('award', 'gift')
      2. bonanza.created_at >= 2026-07-01  (future awards only)
      3. at least one bonanza_category_filters row maps to a Solar category ID
    """
    if getattr(bonanza, 'reward_type', None) not in ('award', 'gift'):
        return False
    created = getattr(bonanza, 'created_at', None)
    if not created or created < _SOLAR_AWARD_DVR_CUTOFF:
        return False
    row = db.execute(text(
        "SELECT 1 FROM bonanza_category_filters"
        " WHERE bonanza_id = :bid AND category_id = ANY(:sids) LIMIT 1"
    ), {'bid': bonanza.id, 'sids': list(_SOLAR_CAT_IDS)}).scalar()
    return row is not None


def _count_vgk_completed_deals(db: Session, partner_code: str, bonanza) -> int:
    """
    DC Protocol: Count VGK completed deals for bonanza eligibility.
    Rules:
      - deal_date (won date) BETWEEN bonanza start_date AND end_date
      - deal_value_balance = 0 (payment fully cleared, within bonanza period by staff convention)
      - status = 'completed' (physical completion done)
      - close_date <= bonanza end_date + grace_days (15 days by default)
      - revenue_category_id matches segment_id if set
    """
    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    seg = bonanza.segment_id
    params = {
        "partner_code": partner_code,
        "start": bonanza.start_date,
        "end": bonanza.end_date,
        "grace": grace,
    }
    seg_clause = "AND cld.revenue_category_id = :seg_id" if seg else ""
    if seg:
        params["seg_id"] = seg
    row = db.execute(text(f"""
        SELECT COUNT(*) FROM crm_lead_deals cld
        WHERE cld.deal_source_id = :partner_code
          AND cld.deal_date >= :start
          AND cld.deal_date <= :end
          AND cld.deal_value_balance = 0
          AND cld.status = 'completed'
          AND cld.close_date IS NOT NULL
          AND cld.close_date <= :end + INTERVAL '1 day' * :grace
          {seg_clause}
    """), params).scalar()
    return int(row or 0)


def _get_vgk_member_bonanzas(partner, db: Session) -> dict:
    """
    DC Protocol: VGK OfficialPartner bonanza view.
    Returns all VGK-portal approved bonanzas with completed_deals progress.
    Claim status pulled from BonanzaProgress.partner_id.
    """
    from app.models.bonanza import BonanzaProgress
    from datetime import datetime

    partner_code = partner.partner_code or str(partner.id)

    bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False,
        Bonanza.portal == 'VGK'
    ).all()

    # Prefetch segment names
    seg_ids = [b.segment_id for b in bonanzas if b.segment_id]
    seg_map = {}
    if seg_ids:
        cats = db.execute(text("SELECT id, name FROM signup_categories WHERE id = ANY(:ids)"),
                          {"ids": seg_ids}).fetchall()
        seg_map = {r[0]: r[1] for r in cats}

    # Prefetch partner's BonanzaProgress records for all VGK bonanzas
    bonanza_ids = [b.id for b in bonanzas]
    progress_map = {}
    if bonanza_ids:
        progs = db.query(BonanzaProgress).filter(
            BonanzaProgress.partner_id == partner.id,
            BonanzaProgress.bonanza_id.in_(bonanza_ids)
        ).all()
        progress_map = {p.bonanza_id: p for p in progs}

    # DC Protocol: Determine if this partner is registered (non-activated) or activated
    partner_is_activated = bool(partner.is_active)

    result = []
    now = datetime.utcnow()
    for bonanza in bonanzas:
        # DC-BONANZA-FIRST-DVR-001 (Jul 2026): FIRST_DVR basis counts first-payment
        # COMMISSION income entries (transaction date = created_at on the entry).
        # DC-FIX-2605-BONANZA: slab_wise bonanzas count solar advances, not crm_lead_deals
        # DC-BONANZA-ADVANCE-BASIS-001: any bonanza with an explicit advance_count_basis
        # (CIBIL/DVR/BOTH) uses solar advance counting — NOT completed-deal counting.
        # Default '' (NULL basis) falls through to legacy completed-deal path.
        _bz_basis = (getattr(bonanza, 'advance_count_basis', None) or '').upper()
        if _bz_basis == 'FIRST_DVR':
            deal_count = _count_first_dvr_income_for_bonanza(db, partner.id, bonanza)
        elif _bz_basis in ('CIBIL', 'DVR', 'BOTH'):
            # DC-BONANZA-ADVANCE-BASIS-001: explicit advance_count_basis → count solar
            # advances using the configured basis (CIBIL date / DVR first-payment / both).
            deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza)
        elif _is_solar_award_dvr(db, bonanza):
            # DC-SOLAR-AWARD-DVR-001: award/gift + Solar + created ≥ 2026-07-01 → DVR stage
            deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza, basis_override='DVR')
        elif bonanza.reward_type == 'slab_wise':
            deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza)
        else:
            deal_count = _count_vgk_completed_deals(db, partner_code, bonanza)

        # DC Protocol: Two-tier target for VGK bonanzas with registered_target_bonus set
        activated_target = bonanza.target_requirement or 1
        bonus = bonanza.registered_target_bonus  # None = feature disabled
        registered_target = (activated_target + bonus) if bonus else None

        # Effective target depends on whether this partner is activated or registered
        if bonus and not partner_is_activated:
            effective_target = registered_target
        else:
            effective_target = activated_target

        achieved = deal_count >= effective_target
        is_expired = bonanza.end_date and bonanza.end_date < now
        is_upcoming = bonanza.start_date and bonanza.start_date > now

        if is_upcoming:
            status = "Upcoming"
        elif is_expired and not achieved:
            status = "Missed Opportunity"
        elif achieved:
            bp = progress_map.get(bonanza.id)
            if bp:
                status = bp.processed_status or "Achieved"
            else:
                # DC_BONANZA_AUTOCLAIM_001: auto-claim silently — no manual button needed
                try:
                    _vgk_partner_claim(partner, bonanza.id, db)
                    _bp_new = db.query(BonanzaProgress).filter(
                        BonanzaProgress.bonanza_id == bonanza.id,
                        BonanzaProgress.partner_id == partner.id
                    ).first()
                    if _bp_new:
                        progress_map[bonanza.id] = _bp_new
                    status = _bp_new.processed_status if _bp_new else "Pending"
                except HTTPException:
                    # Slots full or other hard stop — leave as achieved but unclaimed
                    status = "Achieved - Claim Now"
                except Exception:
                    status = "Achieved - Claim Now"
        else:
            status = "In Progress"

        bp = progress_map.get(bonanza.id)
        slots_remaining = max(0, bonanza.max_winners - (bonanza.current_winners or 0))

        result.append({
            "id": bonanza.id,
            "name": bonanza.name,
            "portal": "VGK",
            "criteria_type": bonanza.criteria_type,
            # Effective target for this specific member
            "target_requirement": effective_target,
            # Two-tier fields (only present when registered_target_bonus is configured)
            "activated_target": activated_target,
            "registered_target": registered_target,
            "registered_target_bonus": bonus,
            "partner_is_activated": partner_is_activated,
            "current_progress": deal_count,
            "achievement_percentage": min(100, int(deal_count / effective_target * 100)),
            "achieved": achieved,
            "is_expired": is_expired,
            "is_active": status in ["In Progress", "Achieved - Claim Now"],
            "is_upcoming": is_upcoming,
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "grace_days": bonanza.grace_days if bonanza.grace_days is not None else 15,
            "segment_id": bonanza.segment_id,
            "segment_name": seg_map.get(bonanza.segment_id) if bonanza.segment_id else None,
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "reward_text": bonanza.reward_text,
            # DC_BONANZA_SLABWISE_001
            "slab_extra_amount": float(bonanza.slab_extra_amount) if bonanza.slab_extra_amount else None,
            "slab_base_reference": float(bonanza.slab_base_reference) if bonanza.slab_base_reference else None,
            "slab_total_display": float((bonanza.slab_base_reference or 0) + (bonanza.slab_extra_amount or 0)) if bonanza.slab_extra_amount else None,
            "advance_count_basis": bonanza.advance_count_basis or 'CIBIL',
            "status": status,
            "processed_status": bp.processed_status if bp else None,
            "claimed_date": bp.achieved_date.isoformat() if bp and bp.achieved_date else None,
            "max_winners": bonanza.max_winners,
            "current_winners": bonanza.current_winners or 0,
            "slots_remaining": slots_remaining,
            "slots_full": slots_remaining == 0,
            "image_url": bonanza.image_url
        })

    result.sort(key=lambda x: (
        not x["is_active"],
        x["is_upcoming"],
        -(datetime.fromisoformat(x["end_date"]).timestamp() if x["end_date"] else 0)
    ))
    active_count = sum(1 for b in result if b["is_active"])
    return {"success": True, "bonanzas": result, "total_count": len(result), "active_count": active_count}


@router.get("/my-bonanzas")
async def get_user_bonanzas(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_vgk_partner_any)
):
    """
    Get all active bonanzas with user's current progress
    CRITICAL: Calculate progress ONLY for activations within bonanza period
    """
    from datetime import datetime
    from sqlalchemy import func
    from sqlalchemy.orm import aliased
    from app.models.placement import Placement
    from app.models.transaction import Transaction
    from app.models.staff import StaffEmployee
    
    # DC Protocol: Staff users don't participate in MNR bonanza programs
    # Staff have numeric IDs (1, 2, 3) but placement table uses string MNR IDs
    if isinstance(current_user, StaffEmployee):
        return {"success": True, "bonanzas": [], "total_count": 0, "active_count": 0}

    # ── DC Protocol: VGK OfficialPartner bonanza view (deal-based) ────────────
    from app.models.staff_accounts import OfficialPartner
    if isinstance(current_user, OfficialPartner):
        return _get_vgk_member_bonanzas(current_user, db)

    # Get all approved bonanzas in one query (MNR only — filter portal)
    bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False,
        Bonanza.portal.in_(['MNR', None])  # MNR portal only for MNR members
    ).all()
    
    # Calculate progress per bonanza (each has different date range)
    result = []
    for bonanza in bonanzas:
        current_progress = 0
        
        # Calculate based on criteria type WITH DATE RANGE
        # DC Protocol (Feb 2026): Exclude Welcome Coupon AND Star/Loyal (package_points=0) users from bonanza calculations
        # DC Protocol (Feb 2026): Handle both 'direct_referrals' and 'direct_referral' criteria types
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            DirectReferral = aliased(User)
            current_progress = db.query(func.count(DirectReferral.id)).filter(
                DirectReferral.referrer_id == current_user.id,
                DirectReferral.account_status == 'Active',
                DirectReferral.activation_date.isnot(None),
                DirectReferral.activation_date >= bonanza.start_date,
                DirectReferral.activation_date <= bonanza.end_date,
                DirectReferral.is_welcome_coupon == False,
                DirectReferral.package_points > 0
            ).scalar() or 0
            print(f"[DC-Bonanza] User {current_user.id} - Bonanza {bonanza.id} ({bonanza.criteria_type}): Progress={current_progress}, Start={bonanza.start_date}, End={bonanza.end_date}")
            
        elif bonanza.criteria_type == 'matching_points':
            # DC Protocol (Feb 2026): Count matching pairs excluding Welcome Coupon contributions
            # Use gross_amount > 0 to exclude zero-income pairs (Welcome Coupon/Star/Loyal pairs)
            matching_pairs = db.query(func.count(Transaction.id)).filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == 'Matching Referral Income',
                Transaction.created_at >= bonanza.start_date,
                Transaction.created_at <= bonanza.end_date,
                Transaction.gross_amount > 0
            ).scalar() or 0
            current_progress = matching_pairs
            
        elif bonanza.criteria_type == 'earnings_target':
            # For earnings, use total (no date range makes sense here)
            current_progress = int(current_user.earned_total or 0)
        elif bonanza.criteria_type == 'team_size':
            TeamMember = aliased(User)
            team_count = db.query(func.count(TeamMember.id)).join(
                Placement, Placement.child_id == TeamMember.id
            ).filter(
                Placement.parent_id == current_user.id,
                TeamMember.account_status == 'Active',
                TeamMember.activation_date.isnot(None),
                TeamMember.activation_date >= bonanza.start_date,
                TeamMember.activation_date <= bonanza.end_date,
                TeamMember.is_welcome_coupon != True,
                TeamMember.package_points > 0
            ).scalar() or 0
            current_progress = team_count
        else:
            current_progress = 0
        
        # DC Protocol: Calculate NET achievements if consume_achievements is enabled
        # This prevents users from reusing same achievements for multiple bonanzas
        raw_progress = current_progress
        net_progress = current_progress
        total_consumed = 0
        
        if bonanza.consume_achievements:
            # Get OTHER bonanzas (EXCLUDE current one) with same criteria type that consume achievements
            consumed_bonanzas = db.query(Bonanza).filter(
                Bonanza.criteria_type == bonanza.criteria_type,
                Bonanza.consume_achievements == True,
                Bonanza.status == 'Approved',
                Bonanza.is_deleted == False,
                Bonanza.id != bonanza.id  # CRITICAL: Exclude current bonanza to prevent self-consumption
            ).all()
            
            # DC Protocol: Sum actual achievements from approved claims (not admin-entered deduction fields)
            # Use authoritative claim data: direct_count_achieved / matching_count_achieved
            for consumed_bonanza in consumed_bonanzas:
                # Count ALL CLAIMED bonanzas (immediate deduction on claim)
                consumed_claim = db.query(DynamicBonanzaHistory).filter(
                    DynamicBonanzaHistory.user_id == current_user.id,
                    DynamicBonanzaHistory.bonanza_id == consumed_bonanza.id,
                    DynamicBonanzaHistory.claimed_at.isnot(None)  # Claimed = Deduction applies
                ).first()
                
                if consumed_claim:
                    if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
                        # Use actual achievements claimed, fallback to target requirement
                        total_consumed += consumed_claim.direct_count_achieved or consumed_bonanza.target_requirement
                    elif bonanza.criteria_type == 'matching_points':
                        # Use actual achievements claimed, fallback to target requirement
                        total_consumed += consumed_claim.matching_count_achieved or consumed_bonanza.target_requirement
            
            net_progress = max(0, raw_progress - total_consumed)
        
        # Check if achieved using NET progress (after consumption deductions)
        achieved = net_progress >= bonanza.target_requirement
        
        # DC PROTOCOL: Read status from DynamicBonanzaHistory (single source of truth)
        claimed_record = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.bonanza_id == bonanza.id,
            DynamicBonanzaHistory.user_id == current_user.id
        ).first()
        
        has_claimed = claimed_record is not None
        
        # Determine status: check if bonanza period has ended
        now = datetime.now()
        is_expired = bonanza.end_date and bonanza.end_date < now
        is_upcoming = bonanza.start_date > now  # Upcoming if start date is in future
        
        # DC PROTOCOL: Use processed_status from DynamicBonanzaHistory if claimed (single source of truth)
        if has_claimed:
            # Read status from database field (reflects delivery tracking updates)
            status = claimed_record.processed_status or "Claimed"
        elif is_expired and not achieved:
            status = "Missed Opportunity"
        elif is_expired and achieved:
            status = "Bonanza Closed"
        elif achieved:
            status = "Achieved"
        else:
            status = "In Progress"
        
        # is_active = bonanzas user can actively work on (In Progress or Achieved, not expired/claimed)
        is_active = status in ["In Progress", "Achieved"]
        
        # Calculate slots remaining
        slots_remaining = max(0, bonanza.max_winners - bonanza.current_winners)
        slots_full = bonanza.current_winners >= bonanza.max_winners
        
        result.append({
            "id": bonanza.id,
            "name": bonanza.name,
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "current_progress": net_progress,  # Show NET progress (after consumption)
            "raw_progress": raw_progress,  # Show raw achievements earned
            "consumed_progress": total_consumed,  # Show what was used for other bonanzas
            "achievement_percentage": min(100, int((net_progress / bonanza.target_requirement) * 100)) if bonanza.target_requirement > 0 else 0,
            "achieved": achieved,
            "is_expired": is_expired,
            "is_active": is_active,  # NEW: Currently active bonanza
            "is_upcoming": is_upcoming,  # NEW: Future bonanza
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "status": status,
            
            # DC Protocol: Delivery tracking fields (from claimed_record if exists)
            "processed_status": claimed_record.processed_status if has_claimed else None,
            "dispatch_date": claimed_record.dispatch_date.isoformat() if has_claimed and claimed_record.dispatch_date else None,
            "received_date": claimed_record.received_date.isoformat() if has_claimed and claimed_record.received_date else None,
            "delivery_notes": claimed_record.delivery_notes if has_claimed else None,
            "claimed_date": claimed_record.claimed_at.isoformat() if has_claimed and claimed_record.claimed_at else None,
            
            # Winners limit info
            "max_winners": bonanza.max_winners,
            "current_winners": bonanza.current_winners,
            "slots_remaining": slots_remaining,
            "slots_full": slots_full
        })
    
    # Smart sorting: Active first → Recent (by end_date desc) → Upcoming
    result.sort(key=lambda x: (
        not x['is_active'],  # Active bonanzas first (False < True)
        x['is_upcoming'],    # Then current/expired before upcoming
        -(datetime.fromisoformat(x['end_date']).timestamp() if x['end_date'] else 0)  # Then by end_date desc
    ))
    
    # Count active bonanzas for frontend
    active_count = sum(1 for b in result if b['is_active'])
    
    return {
        "success": True,
        "bonanzas": result,
        "total_count": len(result),
        "active_count": active_count  # NEW: Count of active bonanzas for smart default display
    }


@router.get("/my-reward-files")
async def get_member_reward_files(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_vgk_partner_any)
):
    """
    DC_BONANZA_REWARDFILES_001: Per-file breakdown of solar advances that qualify
    for slab_wise bonanzas for the current VGK partner. Each solar advance row
    is returned separately with its bonanza name, reward amount and achieved date.
    """
    from app.models.staff_accounts import OfficialPartner
    from app.models.staff import StaffEmployee

    if isinstance(current_user, StaffEmployee):
        return {"success": True, "files": []}
    if not isinstance(current_user, OfficialPartner):
        return {"success": True, "files": []}

    rows = db.execute(text("""
        SELECT
            a.id               AS advance_id,
            a.entry_number,
            a.status           AS advance_status,
            a.created_at,
            a.released_at,
            a.advance_amount,
            a.slab_bonus_paid,
            a.slab_bonus_amount,
            l.name             AS lead_name,
            l.id               AS lead_id,
            b.id               AS bonanza_id,
            b.name             AS bonanza_name,
            b.slab_extra_amount,
            b.start_date       AS bonanza_start,
            b.end_date         AS bonanza_end,
            b.grace_days,
            bp.processed_status,
            bp.achieved_date
        FROM vgk_solar_cibil_advances a
        LEFT JOIN crm_leads l ON l.id = a.lead_id
        JOIN bonanza b ON (
            b.reward_type = 'slab_wise'
            AND b.status  = 'Approved'
            AND b.portal  = 'VGK'
            AND l.submit_date IS NOT NULL
            AND l.submit_date >= b.start_date
            AND l.submit_date <= b.end_date + INTERVAL '1 day' * COALESCE(b.grace_days, 15)
        )
        LEFT JOIN bonanza_progress bp
               ON bp.bonanza_id = b.id
              AND bp.partner_id = a.partner_id
        WHERE a.partner_id = :pid
          AND a.status IN ('RELEASED','PENDING')
        ORDER BY b.start_date DESC, l.submit_date DESC
    """), {'pid': current_user.id}).fetchall()

    files = []
    for r in rows:
        file_date = r.released_at or r.created_at
        files.append({
            'advance_id':        r.advance_id,
            'entry_number':      r.entry_number,
            'advance_status':    r.advance_status,
            'file_date':         file_date.isoformat() if file_date else None,
            'lead_name':         r.lead_name or 'Unknown',
            'lead_id':           r.lead_id,
            'bonanza_id':        r.bonanza_id,
            'bonanza_name':      r.bonanza_name,
            'slab_extra_amount': float(r.slab_extra_amount) if r.slab_extra_amount else None,
            'bonanza_start':     r.bonanza_start.isoformat() if r.bonanza_start else None,
            'bonanza_end':       r.bonanza_end.isoformat() if r.bonanza_end else None,
            'slab_bonus_paid':   bool(r.slab_bonus_paid),
            'processed_status':  r.processed_status,
            'achieved_date':     r.achieved_date.isoformat() if r.achieved_date else None,
        })

    return {"success": True, "files": files}


@router.get("/user/{user_id}/bonanzas")
async def get_user_bonanzas_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Admin endpoint: Get any user's bonanza progress
    Admins can view any user's bonanza data
    """
    # Check if current user is admin
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get the target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Use same logic as /my-bonanzas but for target_user instead of current_user
    from datetime import datetime
    from sqlalchemy import func
    from sqlalchemy.orm import aliased
    from app.models.placement import Placement
    from app.models.transaction import Transaction
    
    # Get all approved bonanzas
    bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False  # Exclude soft-deleted
    ).all()
    
    # Calculate progress per bonanza
    result = []
    for bonanza in bonanzas:
        current_progress = 0
        
        # Calculate based on criteria type WITH DATE RANGE
        # DC Protocol (Feb 2026): Exclude Welcome Coupon users from bonanza calculations
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            DirectReferral = aliased(User)
            current_progress = db.query(func.count(DirectReferral.id)).filter(
                DirectReferral.referrer_id == target_user.id,
                DirectReferral.account_status == 'Active',
                DirectReferral.activation_date.isnot(None),
                DirectReferral.activation_date >= bonanza.start_date,
                DirectReferral.activation_date <= bonanza.end_date,
                DirectReferral.is_welcome_coupon == False,
                DirectReferral.package_points > 0
            ).scalar() or 0
            
        elif bonanza.criteria_type == 'matching_points':
            # DC Protocol (Feb 2026): Exclude zero-income pairs (Welcome Coupon/Star/Loyal)
            matching_pairs = db.query(func.count(Transaction.id)).filter(
                Transaction.user_id == target_user.id,
                Transaction.transaction_type == 'Matching Referral Income',
                Transaction.created_at >= bonanza.start_date,
                Transaction.created_at <= bonanza.end_date,
                Transaction.gross_amount > 0
            ).scalar() or 0
            current_progress = matching_pairs
            
        elif bonanza.criteria_type == 'earnings_target':
            current_progress = int(target_user.earned_total or 0)
        elif bonanza.criteria_type == 'team_size':
            TeamMember = aliased(User)
            team_count = db.query(func.count(TeamMember.id)).join(
                Placement, Placement.child_id == TeamMember.id
            ).filter(
                Placement.parent_id == target_user.id,
                TeamMember.account_status == 'Active',
                TeamMember.activation_date.isnot(None),
                TeamMember.activation_date >= bonanza.start_date,
                TeamMember.activation_date <= bonanza.end_date,
                TeamMember.is_welcome_coupon != True,
                TeamMember.package_points > 0
            ).scalar() or 0
            current_progress = team_count
        else:
            current_progress = 0
        
        # Check if achieved
        achieved = current_progress >= bonanza.target_requirement
        
        # Determine status
        now = datetime.now()
        is_expired = bonanza.end_date and bonanza.end_date < now
        
        if is_expired and not achieved:
            status = "Missed Opportunity"
        elif is_expired and achieved:
            # DC Protocol: Check DynamicBonanzaHistory instead of BonanzaProgress
            claimed = db.query(DynamicBonanzaHistory).filter(
                DynamicBonanzaHistory.bonanza_id == bonanza.id,
                DynamicBonanzaHistory.user_id == target_user.id
            ).first()
            status = "Claimed" if claimed else "Bonanza Closed"
        elif achieved:
            status = "Achieved"
        else:
            status = "In Progress"
        
        # Calculate slots remaining
        slots_remaining = max(0, bonanza.max_winners - bonanza.current_winners)
        slots_full = bonanza.current_winners >= bonanza.max_winners
        
        result.append({
            "id": bonanza.id,
            "name": bonanza.name,
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "current_progress": current_progress,
            "achievement_percentage": min(100, int((current_progress / bonanza.target_requirement) * 100)) if bonanza.target_requirement > 0 else 0,
            "achieved": achieved,
            "is_expired": is_expired,
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "status": status,
            "max_winners": bonanza.max_winners,
            "current_winners": bonanza.current_winners,
            "slots_remaining": slots_remaining,
            "slots_full": slots_full
        })
    
    return {
        "success": True,
        "user_id": user_id,
        "user_name": target_user.name,
        "bonanzas": result
    }


def _vgk_partner_claim(partner, bonanza_id: int, db: Session):
    """
    DC Protocol: VGK OfficialPartner bonanza claim.
    Validates completed_deals criteria, creates BonanzaProgress with partner_id.
    """
    from app.models.bonanza import BonanzaProgress
    from app.models.base import get_indian_time

    bonanza = db.query(Bonanza).filter(
        Bonanza.id == bonanza_id,
        Bonanza.status == 'Approved',
        Bonanza.portal == 'VGK'
    ).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="VGK bonanza not found or not approved")

    # Check slots
    if (bonanza.current_winners or 0) >= (bonanza.max_winners or 50):
        raise HTTPException(status_code=400, detail=f"All {bonanza.max_winners} slots are filled. This bonanza is full.")

    # Check not already claimed
    existing = db.query(BonanzaProgress).filter(
        BonanzaProgress.bonanza_id == bonanza_id,
        BonanzaProgress.partner_id == partner.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already claimed this bonanza")

    # Validate deal count — slab_wise bonanzas count solar advances, not crm_lead_deals
    # DC-BONANZA-FIRST-DVR-001 (Jul 2026): FIRST_DVR basis counts first-payment COMMISSION entries.
    # DC-BONANZA-ADVANCE-BASIS-001: explicit advance_count_basis (CIBIL/DVR/BOTH) → advance counting.
    # Claim gate must mirror _get_vgk_member_bonanzas routing exactly so member tracking
    # and the claim eligibility check always produce the same count.
    partner_code = partner.partner_code or str(partner.id)
    _claim_bz_basis = (getattr(bonanza, 'advance_count_basis', None) or '').upper()
    if _claim_bz_basis == 'FIRST_DVR':
        deal_count = _count_first_dvr_income_for_bonanza(db, partner.id, bonanza)
    elif _claim_bz_basis in ('CIBIL', 'DVR', 'BOTH'):
        # DC-BONANZA-ADVANCE-BASIS-001: explicit advance_count_basis → solar advance counting
        deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza)
    elif _is_solar_award_dvr(db, bonanza):
        # DC-SOLAR-AWARD-DVR-001: award/gift + Solar + created ≥ 2026-07-01 → DVR stage
        deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza, basis_override='DVR')
    elif bonanza.reward_type == 'slab_wise':
        deal_count = _count_solar_advances_for_bonanza(db, partner.id, bonanza)
    else:
        deal_count = _count_vgk_completed_deals(db, partner_code, bonanza)
    if deal_count < (bonanza.target_requirement or 1):
        raise HTTPException(
            status_code=400,
            detail=f"Target not met. You have {deal_count} qualifying deal(s), need {bonanza.target_requirement}."
        )

    now = get_indian_time()
    progress = BonanzaProgress(
        bonanza_id=bonanza_id,
        partner_id=partner.id,
        current_progress=deal_count,
        achievement_status='Achieved',
        achieved_date=now,
        processed_status='Pending',
        reward_given=False
    )
    bonanza.current_winners = (bonanza.current_winners or 0) + 1
    db.add(progress)
    db.commit()
    db.refresh(progress)
    # DC_BONANZA_SLABWISE_001 (per-file): compute total payout for slab_wise
    slab_payout = None
    if bonanza.reward_type == 'slab_wise' and bonanza.slab_extra_amount:
        slab_payout = float(bonanza.slab_extra_amount) * deal_count

    return {
        "success": True,
        "message": (
            f"✅ Bonanza '{bonanza.name}' claimed! {deal_count} solar file(s) × ₹{bonanza.slab_extra_amount:,.0f} = ₹{slab_payout:,.0f} slab bonus."
            if slab_payout is not None
            else f"✅ Bonanza '{bonanza.name}' claimed successfully! {deal_count} qualifying deal(s)."
        ),
        "claim_id": progress.id,
        "deal_count": deal_count,
        "slab_payout": slab_payout,
        "processed_status": progress.processed_status
    }


@router.post("/claim/{bonanza_id}")
async def claim_bonanza(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid_with_partner)
):
    """
    User claims a bonanza reward after achieving the target
    Creates BonanzaProgress record for tracking and processing
    
    DC Protocol Feb 2026: Requires activation + KYC + both groups activated
    """
    # ── DC Protocol: VGK OfficialPartner claim path ──────────────────────────
    from app.models.staff_accounts import OfficialPartner
    if isinstance(current_user, OfficialPartner):
        return _vgk_partner_claim(current_user, bonanza_id, db)

    # DC Protocol Feb 2026: Comprehensive eligibility check (MNR only)
    from app.core.scheduler import get_user_eligibility_status
    eligibility = get_user_eligibility_status(db, current_user)
    
    if not eligibility['is_eligible']:
        # Return specific blocking reason
        blocking_message = eligibility['blocking_reasons'][0] if eligibility['blocking_reasons'] else "You are not eligible to claim this bonanza."
        raise HTTPException(status_code=403, detail=blocking_message)
    
    from sqlalchemy import func
    from sqlalchemy.orm import aliased
    
    # Get the bonanza
    bonanza = db.query(Bonanza).filter(
        Bonanza.id == bonanza_id,
        Bonanza.status == 'Approved'
    ).first()
    
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found or not approved")
    
    # Check if bonanza period has expired
    now = datetime.utcnow()
    if bonanza.end_date and bonanza.end_date < now:
        raise HTTPException(status_code=400, detail="Bonanza period has ended. You missed the opportunity to claim this reward.")
    
    # Check max winners limit (First Come First Served)
    if bonanza.current_winners >= bonanza.max_winners:
        raise HTTPException(
            status_code=400, 
            detail=f"❌ Sorry! All {bonanza.max_winners} slots are filled. This bonanza has reached its maximum winners limit."
        )
    
    # Check if already claimed (DC Protocol: Query DynamicBonanzaHistory ONLY)
    from app.services.bonanza_service import BonanzaService
    bonanza_service = BonanzaService(db)
    
    existing_claim = bonanza_service.get_user_claim(current_user.id, bonanza_id)
    
    if existing_claim:
        raise HTTPException(status_code=400, detail="You have already claimed this bonanza")
    
    # Verify achievement
    current_progress = 0
    
    # DC Protocol (Feb 2026): Exclude Welcome Coupon users from bonanza calculations
    if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
        DirectReferral = aliased(User)
        current_progress = db.query(func.count(DirectReferral.id)).filter(
            DirectReferral.referrer_id == current_user.id,
            DirectReferral.account_status == 'Active',
            DirectReferral.activation_date.isnot(None),
            DirectReferral.activation_date >= bonanza.start_date,
            DirectReferral.activation_date <= bonanza.end_date,
            DirectReferral.is_welcome_coupon == False,
            DirectReferral.package_points > 0
        ).scalar() or 0
        
    elif bonanza.criteria_type == 'matching_points':
        # DC Protocol (Feb 2026): Exclude zero-income pairs (Welcome Coupon/Star/Loyal)
        from app.models.transaction import Transaction
        matching_pairs = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == 'Matching Referral Income',
            Transaction.created_at >= bonanza.start_date,
            Transaction.created_at <= bonanza.end_date,
            Transaction.gross_amount > 0
        ).scalar() or 0
        current_progress = matching_pairs
        
    elif bonanza.criteria_type == 'earnings_target':
        current_progress = int(current_user.earned_total or 0)
    elif bonanza.criteria_type == 'team_size':
        TeamMember = aliased(User)
        team_count = db.query(func.count(TeamMember.id)).join(
            Placement, Placement.child_id == TeamMember.id
        ).filter(
            Placement.parent_id == current_user.id,
            TeamMember.account_status == 'Active',
            TeamMember.activation_date.isnot(None),
            TeamMember.activation_date >= bonanza.start_date,
            TeamMember.activation_date <= bonanza.end_date,
            TeamMember.is_welcome_coupon != True,
            TeamMember.package_points > 0
        ).scalar() or 0
        current_progress = team_count
    
    # Check if achieved
    if current_progress < bonanza.target_requirement:
        raise HTTPException(
            status_code=400, 
            detail=f"Target not achieved. Current: {current_progress}, Required: {bonanza.target_requirement}"
        )
    
    # DC Protocol: Create ONLY DynamicBonanzaHistory record (single source of truth)
    try:
        # DC PROTOCOL FIX (Nov 11, 2025): Use actual_price from configuration, not reward_amount
        # This ensures awards show correct budgeted amounts across all RVZ pages
        budgeted_value = bonanza.actual_price if bonanza.actual_price else (bonanza.reward_amount or 0)
        
        # DC Protocol Feb 2026: ALL bonanza claims consume referrals/matching from regular awards
        deduction_direct = 0
        deduction_matching = 0
        
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            deduction_direct = bonanza.target_requirement
        elif bonanza.criteria_type == 'matching_points':
            deduction_matching = bonanza.target_requirement
        
        # ========== DC PROTOCOL: CAPTURE IMMUTABLE CONTRIBUTOR SNAPSHOTS ==========
        # Store exact contributors at claim time to prevent historical data drift
        direct_contributors_snapshot = None
        matching_contributors_snapshot = None
        
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            from sqlalchemy import and_
            snapshot_filters = [
                User.referrer_id == current_user.id,
                User.coupon_status == 'Activated',
                User.is_welcome_coupon != True,
                User.package_points > 0,
                User.activation_date.isnot(None)
            ]
            if bonanza.start_date:
                snapshot_filters.append(User.activation_date >= bonanza.start_date)
            if bonanza.end_date:
                snapshot_filters.append(User.activation_date <= bonanza.end_date)
            referrals = db.query(User).filter(and_(*snapshot_filters)).order_by(User.activation_date.asc()).all()
            
            consumed_referrals = referrals[:deduction_direct]
            direct_contributors_snapshot = [
                {
                    'user_id': ref.id,
                    'name': ref.name,
                    'package': ref.get_package_type(),
                    'points': float(ref.package_points or 0),
                    'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
                }
                for ref in consumed_referrals
            ]
        
        elif bonanza.criteria_type == 'matching_points':
            left_leg = db.query(User).filter(
                User.position.like(f'{current_user.position}L%'),
                User.coupon_status == 'Activated',
                User.is_welcome_coupon != True,
                User.package_points > 0
            ).order_by(User.activation_date.asc()).all()
            
            right_leg = db.query(User).filter(
                User.position.like(f'{current_user.position}R%'),
                User.coupon_status == 'Activated',
                User.is_welcome_coupon != True,
                User.package_points > 0
            ).order_by(User.activation_date.asc()).all()
            
            matching_contributors_snapshot = {
                'left_leg': [
                    {
                        'user_id': m.id,
                        'name': m.name,
                        'package': m.get_package_type(),
                        'points': float(m.package_points or 0)
                    }
                    for m in left_leg
                ],
                'right_leg': [
                    {
                        'user_id': m.id,
                        'name': m.name,
                        'package': m.get_package_type(),
                        'points': float(m.package_points or 0)
                    }
                    for m in right_leg
                ]
            }
        
        # Create DynamicBonanzaHistory record (DC Protocol: single source of truth)
        from app.models.bonanza import DynamicBonanzaHistory
        
        history = DynamicBonanzaHistory(
            user_id=current_user.id,
            bonanza_id=bonanza.id,
            claimed_reward_id=None,
            direct_count_achieved=current_progress if bonanza.criteria_type in ['direct_referrals', 'direct_referral'] else 0,
            matching_count_achieved=current_progress if bonanza.criteria_type == 'matching_points' else 0,
            deduction_amount_direct=deduction_direct,
            deduction_amount_matching=deduction_matching,
            deduction_applied_to_direct_awards=(bonanza.criteria_type in ['direct_referrals', 'direct_referral']),
            deduction_applied_to_matching_awards=(bonanza.criteria_type == 'matching_points'),
            # DC_BONANZA_SLABWISE_001: slab_wise pays slab_extra_amount × deal_count (per-file model)
            reward_value_claimed=(
                float(bonanza.slab_extra_amount) * current_progress
                if bonanza.reward_type == 'slab_wise' and bonanza.slab_extra_amount and current_progress
                else (float(bonanza.reward_amount) if bonanza.is_monetary and bonanza.reward_amount else 0)
            ),
            budgeted_amount=budgeted_value,  # WV Protocol: NET amount at achievement
            reward_type=bonanza.reward_type,
            award_name=bonanza.award_name,
            award_image=bonanza.reward_file,  # Store reward image path
            is_monetary=bonanza.is_monetary,
            actual_cost_incurred=0,  # Cost to be updated during procurement by Finance Admin
            claimed_at=datetime.utcnow(),
            processed_status=AwardStatus.PENDING_APPROVAL,  # DC Protocol: Standardized starting status
            rvz_approval_status='Pending RVZ Approval',  # Legacy field (for backward compatibility)
            procurement_status=None,  # Will be set after RVZ approval
            delivery_notes=(
                f"SLAB WISE (PER FILE): ₹{bonanza.slab_extra_amount} slab bonus × {current_progress} solar file(s) = ₹{float(bonanza.slab_extra_amount) * current_progress:,.0f} | Base ref: ₹{bonanza.slab_base_reference or 0}/file (Solar File Advance, display only) | Target: {bonanza.target_requirement}, Files submitted: {current_progress}"
                if bonanza.reward_type == 'slab_wise' and bonanza.slab_extra_amount
                else f"Target: {bonanza.target_requirement}, Current Progress: {current_progress}, Reward: {bonanza.award_name if not bonanza.is_monetary else f'₹{bonanza.reward_amount}'}"
            ),
            # DC PROTOCOL: Store immutable contributor snapshots
            direct_contributors_snapshot=direct_contributors_snapshot,
            matching_contributors_snapshot=matching_contributors_snapshot
        )
        
        # DC PROTOCOL: Validate snapshots are captured when deductions applied
        if deduction_direct > 0 and not direct_contributors_snapshot:
            raise ValueError("Failed to capture direct contributors snapshot - data integrity violation")
        if deduction_matching > 0 and not matching_contributors_snapshot:
            raise ValueError("Failed to capture matching contributors snapshot - data integrity violation")
        
        db.add(history)
        
        # Increment winners count (First Come First Served tracking)
        bonanza.current_winners += 1
        
        db.commit()
        db.refresh(history)
        
        # DC Protocol: Sync award statuses after bonanza claim
        # Bonanza deductions reduce effective points, so awards that no longer
        # meet their threshold must be immediately demoted (segment-specific:
        # direct deductions affect direct awards, matching deductions affect matching awards)
        if deduction_direct > 0 or deduction_matching > 0:
            try:
                from app.services.award_sync_service import sync_user_award_statuses
                sync_result = sync_user_award_statuses(db, current_user.id)
                import logging
                logging.getLogger(__name__).info(
                    f"[BONANZA-CLAIM-SYNC] Award sync after bonanza claim for {current_user.id}: "
                    f"direct_demoted={sync_result.get('direct', {}).get('demoted', 0)}, "
                    f"matching_demoted={sync_result.get('matching', {}).get('demoted', 0)}"
                )
            except Exception as sync_err:
                import logging
                logging.getLogger(__name__).warning(
                    f"[BONANZA-CLAIM-SYNC] Award sync failed for {current_user.id}: {sync_err}"
                )
        
        # Check if this was the last slot
        slots_remaining = bonanza.max_winners - bonanza.current_winners
        slots_message = f" ({slots_remaining} slots remaining)" if slots_remaining > 0 else " (Last slot filled!)"
        
        return {
            "success": True,
            "message": f"Bonanza '{bonanza.name}' claimed successfully! Pending admin approval.{slots_message}",
            "claim_id": history.id,  # DC Protocol: Return DynamicBonanzaHistory.id
            "reward": bonanza.award_name if not bonanza.is_monetary else f"₹{bonanza.reward_amount:,.0f}",
            "deduction_applied": deduction_direct + deduction_matching,
            "approval_status": "Pending",  # DC Protocol: Unified status
            "slots_remaining": slots_remaining
        }
    except Exception as e:
        db.rollback()
        # Handle unique constraint violation (duplicate claim)
        if "unique_user_bonanza_claim" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="You have already claimed this bonanza")
        # Re-raise other errors
        raise HTTPException(status_code=500, detail=f"Error claiming bonanza: {str(e)}")


@router.get("/my-claimed")
async def get_my_claimed_bonanzas(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid_with_partner)
):
    """
    Get user's claimed bonanzas history
    DC Protocol: Uses DynamicBonanzaHistory (single source of truth)
    """
    from app.models.staff import StaffEmployee
    
    # DC Protocol: Staff users don't have bonanza claims
    # Staff have numeric IDs (1, 2, 3) but bonanza tables use string MNR IDs
    if isinstance(current_user, StaffEmployee):
        return {"success": True, "claimed_bonanzas": []}
    
    # DC Protocol: Query DynamicBonanzaHistory instead of BonanzaProgress
    from app.services.bonanza_service import BonanzaService, BonanzaStatusMapper
    bonanza_service = BonanzaService(db)
    
    claimed = bonanza_service.get_user_claims(current_user.id, include_bonanza=False)
    
    result = []
    for claim in claimed:
        bonanza = db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
        
        # Extract reward info from bonanza or claim
        reward = claim.award_name if claim.award_name else "Unknown"
        if claim.is_monetary and claim.reward_value_claimed:
            reward = f"₹{claim.reward_value_claimed:,.0f}"
        
        # Map NEW status to OLD for backward compatibility
        legacy_status = BonanzaStatusMapper.processed_to_achievement(claim.processed_status)
        
        result.append({
            "id": claim.id,
            "bonanza_name": bonanza.name if bonanza else "Unknown",
            "criteria_type": bonanza.criteria_type if bonanza else None,
            "target_achieved": claim.direct_count_achieved or claim.matching_count_achieved or 0,
            "target_required": bonanza.target_requirement if bonanza else 0,
            "reward": reward,
            "is_monetary": claim.is_monetary,
            "claimed_date": claim.claimed_at.isoformat() if claim.claimed_at else None,
            "processed_status": claim.processed_status,  # NEW unified status (DC Protocol)
            "legacy_status": legacy_status,  # OLD status for UI compatibility
            "reward_given": claim.processed_status in ['Delivered - Completed', 'Delivered', 'Processed for Dispatch'],
            "reward_given_date": claim.delivered_at.isoformat() if claim.delivered_at else (claim.finance_processed_at.isoformat() if claim.finance_processed_at else None),
            # DC Protocol: Delivery tracking fields
            "dispatch_date": claim.dispatch_date.isoformat() if claim.dispatch_date else None,
            "received_date": claim.received_date.isoformat() if claim.received_date else None,
            "delivery_notes": claim.delivery_notes
        })
    
    return {
        "success": True,
        "claimed_bonanzas": result
    }


@router.get("/approvals")
async def bonanza_approvals(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Finance Admin views pending bonanza approvals
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only Finance Admin can view approvals")
    
    pending = db.query(Bonanza).filter(
        Bonanza.status == 'Pending',
        Bonanza.is_deleted == False  # Exclude soft-deleted
    ).all()
    
    return {
        "success": True,
        "pending_approvals": [
            {
                "id": b.id,
                "name": b.name,
                "criteria_type": b.criteria_type,
                "target_requirement": b.target_requirement,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None,
                "created_by": b.created_by,
                
                # Reward details
                "reward_type": b.reward_type,
                "is_monetary": b.is_monetary,
                "reward_amount": float(b.reward_amount) if b.reward_amount else None,
                "award_name": b.award_name,
                "reward_text": b.reward_text,
                
                "total_budget": float(b.total_budget) if b.total_budget else None
            }
            for b in pending
        ]
    }


@router.post("/approve/{bonanza_id}")
async def approve_bonanza(
    bonanza_id: int,
    data: BonanzaApprove,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Finance Admin approves bonanza
    DC Protocol: bonanza_id from URL path only, optional approval_comments in body
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only Finance Admin can approve bonanzas")
    
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    # DC Protocol: Update approval fields
    bonanza.status = 'Approved'
    bonanza.approved_by = _resolve_actor_id(current_user)
    bonanza.approved_date = datetime.utcnow()
    
    # DC Protocol: Store approval comments if provided
    if data.approval_comments:
        bonanza.admin_notes = data.approval_comments
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' approved successfully"
    }


@router.get("/{bonanza_id}/details")
async def bonanza_details(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get detailed bonanza information
    """
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    return {
        "success": True,
        "bonanza": {
            "id": bonanza.id,
            "name": bonanza.name,
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "counts_towards_regular": bonanza.counts_towards_regular,
            
            # Reward details (supports monetary and non-monetary)
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "reward_text": bonanza.reward_text,
            "reward_file": bonanza.reward_file,
            
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "status": bonanza.status,
            "created_by": bonanza.created_by,
            "approved_by": bonanza.approved_by,
            "approved_date": bonanza.approved_date.isoformat() if bonanza.approved_date else None,
            "total_budget": float(bonanza.total_budget) if bonanza.total_budget else None,
            "current_spending": float(bonanza.current_spending),
            "price_info": bonanza.get_display_price_for_role(getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', 'User'))
        }
    }


@router.get("/user/progress")
async def user_bonanza_progress(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get current user's bonanza progress
    DC Protocol: Uses DynamicBonanzaHistory (single source of truth)
    """
    active_bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.start_date <= datetime.utcnow(),
        Bonanza.end_date >= datetime.utcnow(),
        Bonanza.is_deleted == False  # Exclude soft-deleted
    ).all()
    
    # DC Protocol: Query DynamicBonanzaHistory instead of BonanzaProgress
    from app.services.bonanza_service import BonanzaService, BonanzaStatusMapper
    bonanza_service = BonanzaService(db)
    
    progress_list = []
    for bonanza in active_bonanzas:
        # Check if user has claimed this bonanza
        claim = bonanza_service.get_user_claim(current_user.id, bonanza.id)
        
        # Map NEW status to OLD for UI compatibility
        if claim:
            achievement_status = BonanzaStatusMapper.processed_to_achievement(claim.processed_status)
            current_progress = claim.direct_count_achieved or claim.matching_count_achieved or 0
        else:
            achievement_status = 'Not Started'
            current_progress = 0
        
        progress_list.append({
            "bonanza_id": bonanza.id,
            "bonanza_name": bonanza.name,
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "current_progress": current_progress,
            "achievement_status": achievement_status,
            "processed_status": claim.processed_status if claim else None,  # NEW: DC Protocol unified status
            
            # Reward details
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "reward_text": bonanza.reward_text,
            
            # Selection tracking (no longer supported in DC Protocol - always false for backward compatibility)
            "is_selected": False,
            "can_change_selection": False,
            
            "end_date": bonanza.end_date.isoformat(),
            "claimed": claim is not None,  # NEW: Indicates if user has claimed this bonanza
            "claim_id": claim.id if claim else None  # NEW: DC Protocol claim ID
        })
    
    return {
        "success": True,
        "user_id": current_user.id,
        "active_bonanzas": progress_list
    }


@router.get("/admin/cost-analysis")
async def bonanza_cost_analysis(
    bonanza_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Admin cost analysis for bonanzas
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    if bonanza_id:
        bonanzas = [db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()]
        if not bonanzas[0]:
            raise HTTPException(status_code=404, detail="Bonanza not found")
    else:
        bonanzas = db.query(Bonanza).filter(Bonanza.status.in_(['Approved', 'Active', 'Expired'])).all()
    
    analysis = []
    for bonanza in bonanzas:
        budget_remaining = float(bonanza.total_budget or 0) - float(bonanza.current_spending)
        budget_utilization = (float(bonanza.current_spending) / float(bonanza.total_budget) * 100) if bonanza.total_budget else 0
        
        analysis.append({
            "bonanza_id": bonanza.id,
            "bonanza_name": bonanza.name,
            "total_budget": float(bonanza.total_budget) if bonanza.total_budget else 0,
            "current_spending": float(bonanza.current_spending),
            "budget_remaining": budget_remaining,
            "budget_utilization_percent": round(budget_utilization),
            "status": bonanza.status,
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None
        })
    
    return {
        "success": True,
        "analysis": analysis
    }


@router.get("/eligible")
async def get_eligible_bonanzas(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all eligible bonanzas user can choose from
    Multiple bonanzas can run simultaneously - user chooses their preferred reward
    """
    # Get all active approved bonanzas
    active_bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.start_date <= datetime.utcnow(),
        Bonanza.end_date >= datetime.utcnow(),
        Bonanza.is_deleted == False  # Exclude soft-deleted
    ).all()
    
    # Get user's actual metrics for eligibility check
    user_direct_referrals = db.query(User).filter(User.referrer_id == current_user.id).count()
    
    # Get effective matching count (includes multiplier, NO deductions)
    matching_result = calculate_effective_matching_count(db, current_user.id)
    user_matching_points = matching_result['effective_count']
    
    eligible_bonanzas = []
    selected_bonanza_id = None
    
    for bonanza in active_bonanzas:
        # DC Protocol: Check if user has existing claim in DynamicBonanzaHistory
        progress = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.bonanza_id == bonanza.id,
            DynamicBonanzaHistory.user_id == current_user.id
        ).first()
        
        # Track selected bonanza
        if progress and progress.user_selected_bonanza_id:
            selected_bonanza_id = progress.user_selected_bonanza_id
        
        # Determine if user is eligible based on criteria
        is_eligible = False
        if bonanza.criteria_type == 'direct_referral':
            is_eligible = user_direct_referrals >= bonanza.target_requirement
        elif bonanza.criteria_type == 'matching_points':
            is_eligible = user_matching_points >= bonanza.target_requirement
        
        eligible_bonanzas.append({
            "bonanza_id": bonanza.id,
            "name": bonanza.name,
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "is_eligible": is_eligible,
            "is_selected": progress.user_selected_bonanza_id == bonanza.id if progress else False,
            "can_change_selection": not progress.selection_locked if progress else True,
            
            # Reward details
            "reward_type": bonanza.reward_type,
            "is_monetary": bonanza.is_monetary,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "award_name": bonanza.award_name,
            "reward_text": bonanza.reward_text,
            "reward_file": bonanza.reward_file,
            
            # Deduction impact
            "counts_towards_regular": bonanza.counts_towards_regular,
            "deduction_warning": f"Choosing this bonanza will deduct {bonanza.target_requirement} from your regular awards progress" if bonanza.counts_towards_regular else None,
            
            # Progress
            "current_progress": progress.current_progress if progress else 0,
            "achievement_status": progress.achievement_status if progress else 'Not Started',
            
            # Dates
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat()
        })
    
    return {
        "success": True,
        "user_id": current_user.id,
        "eligible_bonanzas": eligible_bonanzas,
        "selected_bonanza_id": selected_bonanza_id,
        "message": "You can select one bonanza to pursue. Achievement counts will be deducted from regular awards to prevent double benefits."
    }


@router.post("/select")
async def select_bonanza(
    data: BonanzaSelection,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    User selects a bonanza to pursue
    Can change selection until achievement is locked
    """
    # Verify bonanza exists and is active
    bonanza = db.query(Bonanza).filter(
        Bonanza.id == data.bonanza_id,
        Bonanza.status == 'Approved',
        Bonanza.start_date <= datetime.utcnow(),
        Bonanza.end_date >= datetime.utcnow()
    ).first()
    
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found or not active")
    
    # DC Protocol: Check if user already has a claim for this bonanza
    progress = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.bonanza_id == bonanza.id,
        DynamicBonanzaHistory.user_id == current_user.id
    ).first()
    
    if progress:
        # Check if selection is locked
        if progress.selection_locked:
            raise HTTPException(
                status_code=400,
                detail="Cannot change selection - bonanza already achieved and locked"
            )
        
        # Update selection
        progress.user_selected_bonanza_id = bonanza.id
        progress.selected_at = datetime.utcnow()
    else:
        # DC Protocol: Bonanza selection is now handled through claim workflow
        # User must claim a bonanza to track it (DynamicBonanzaHistory)
        # Legacy BonanzaProgress creation removed - endpoint deprecated
        raise HTTPException(
            status_code=400,
            detail="Bonanza selection endpoint deprecated. Please use claim workflow instead."
        )
    
    db.commit()
    db.refresh(progress)
    
    return {
        "success": True,
        "message": f"Successfully selected bonanza: {bonanza.name}",
        "bonanza_id": bonanza.id,
        "reward_type": bonanza.reward_type,
        "is_monetary": bonanza.is_monetary,
        "deduction_warning": f"Upon achievement, {bonanza.target_requirement} will be deducted from your regular awards" if bonanza.counts_towards_regular else None
    }


@router.post("/process-reward")
async def process_bonanza_reward(
    data: BonanzaProcessing,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Finance Admin processes bonanza reward
    Automatically deducts achievement counts from regular awards
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only Finance Admin can process bonanza rewards")
    
    # DC Protocol: Get claim record from DynamicBonanzaHistory
    progress = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.id == data.progress_id
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail="Bonanza claim not found")
    
    # Verify achievement status
    if progress.achievement_status != 'Achieved':
        raise HTTPException(
            status_code=400,
            detail="Cannot process - user has not achieved the bonanza target yet"
        )
    
    # Get bonanza details
    bonanza = db.query(Bonanza).filter(Bonanza.id == progress.bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    try:
        # Lock selection to prevent changes
        progress.selection_locked = True
        progress.processed_status = 'Processed'
        progress.processed_date = datetime.utcnow()
        progress.processed_by = _resolve_actor_id(current_user)
        progress.admin_notes = data.admin_notes
        progress.reward_given = True
        progress.reward_given_date = datetime.utcnow()
        
        # Create history record
        history = DynamicBonanzaHistory(
            user_id=progress.user_id,
            bonanza_id=bonanza.id,
            claimed_reward_id=progress.reward_id,
            reward_type=progress.reward_type,
            reward_value_claimed=progress.reward_amount,
            award_name=progress.award_name,
            award_image=progress.award_image,
            is_monetary=progress.is_monetary,
            claimed_at=datetime.utcnow(),
            processed_at=datetime.utcnow(),
            processed_by=_resolve_actor_id(current_user)
        )
        
        # Apply deductions from regular awards if configured
        if bonanza.counts_towards_regular:
            if bonanza.criteria_type == 'direct_referral':
                # Deduct from direct awards
                history.direct_count_achieved = progress.current_progress
                history.deduction_applied_to_direct_awards = True
                history.deduction_amount_direct = progress.current_progress
                
                # Update UserAwardProgress - deduct from effective count
                # DC PROTOCOL: Apply deductions to ALL awards, not just "In Progress"
                # Status is calculated dynamically, so don't filter by it
                award_progress_records = db.query(UserAwardProgress).filter(
                    UserAwardProgress.user_id == progress.user_id
                ).all()
                
                for award_progress in award_progress_records:
                    award_progress.bonanza_deductions_applied += progress.current_progress
                    award_progress.effective_progress_count = max(
                        0,
                        award_progress.current_referrals - award_progress.bonanza_deductions_applied
                    )
                
            elif bonanza.criteria_type == 'matching_points':
                # Deduct from matching awards
                history.matching_count_achieved = progress.current_progress
                history.deduction_applied_to_matching_awards = True
                history.deduction_amount_matching = progress.current_progress
                
                # Update UserMatchingAwardProgress - deduct from effective count
                # DC PROTOCOL: Apply deductions to ALL awards, not just "Pending"
                # Status is calculated dynamically, so don't filter by it
                matching_progress_records = db.query(UserMatchingAwardProgress).filter(
                    UserMatchingAwardProgress.user_id == progress.user_id
                ).all()
                
                for matching_progress in matching_progress_records:
                    matching_progress.bonanza_deductions_applied += progress.current_progress
                    matching_progress.effective_progress_count = max(
                        0,
                        matching_progress.current_matches - matching_progress.bonanza_deductions_applied
                    )
        
        db.add(history)
        db.commit()
        
        return {
            "success": True,
            "message": f"Bonanza reward processed successfully for user {progress.user_id}",
            "reward_type": progress.reward_type,
            "is_monetary": progress.is_monetary,
            "reward_amount": float(progress.reward_amount) if progress.reward_amount else None,
            "award_name": progress.award_name,
            "deductions_applied": {
                "direct_awards": history.deduction_amount_direct if bonanza.counts_towards_regular and bonanza.criteria_type == 'direct_referral' else 0,
                "matching_awards": history.deduction_amount_matching if bonanza.counts_towards_regular and bonanza.criteria_type == 'matching_points' else 0
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing bonanza reward: {str(e)}")


@router.get("/achievements/all")
async def get_all_achievements(
    achievement_status: Optional[str] = None,
    processed_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all bonanza achievements with filtering
    DC Protocol: Uses DynamicBonanzaHistory (single source of truth)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Admin', 'Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only admins can view all achievements")
    
    from app.services.bonanza_service import BonanzaStatusMapper
    
    # DC Protocol: Query DynamicBonanzaHistory instead of BonanzaProgress
    query = db.query(DynamicBonanzaHistory).join(
        Bonanza, DynamicBonanzaHistory.bonanza_id == Bonanza.id
    ).join(
        User, DynamicBonanzaHistory.user_id == User.id
    )
    
    # Apply filters - map OLD status to NEW if needed
    if achievement_status:
        # Map legacy achievement_status to processed_status
        new_status = BonanzaStatusMapper.achievement_to_processed(achievement_status)
        if new_status:
            query = query.filter(DynamicBonanzaHistory.processed_status == new_status)
    if processed_status:
        query = query.filter(DynamicBonanzaHistory.processed_status == processed_status)
    
    claims = query.order_by(DynamicBonanzaHistory.created_at.desc()).all()
    
    return {
        "success": True,
        "achievements": [
            {
                "id": claim.id,
                "user_id": claim.user_id,
                "bonanza_id": claim.bonanza_id,
                "bonanza_name": db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first().name if claim.bonanza_id else None,
                "current_progress": claim.direct_count_achieved or claim.matching_count_achieved or 0,
                "target_requirement": db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first().target_requirement if claim.bonanza_id else 0,
                "achievement_status": BonanzaStatusMapper.processed_to_achievement(claim.processed_status),  # Legacy field
                "processed_status": claim.processed_status,  # NEW DC Protocol status
                "achieved_at": claim.claimed_at.isoformat() if claim.claimed_at else None,
                "reward_given": claim.processed_status in ['Delivered - Completed', 'Processed for Dispatch'],
                "reward_given_date": claim.delivered_at.isoformat() if claim.delivered_at else (claim.finance_processed_at.isoformat() if claim.finance_processed_at else None),
                "reward_type": claim.reward_type,
                "reward_amount": float(claim.reward_value_claimed) if claim.reward_value_claimed else None,
                "award_name": claim.award_name,
                "is_monetary": claim.is_monetary,
                "processed_by": claim.processed_by,
                "processed_date": claim.processed_at.isoformat() if claim.processed_at else None
            }
            for claim in claims
        ]
    }


@router.post("/achievement/approve/{progress_id}")
async def approve_achievement(
    progress_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Approve a bonanza achievement
    DC Protocol: Uses DynamicBonanzaHistory (single source of truth)
    NOTE: This endpoint is DEPRECATED - use /admin/approve-claim/{claim_id} instead
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only Super Admin or Finance Admin can approve achievements")
    
    # DC Protocol: Query DynamicBonanzaHistory instead of BonanzaProgress
    claim = db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == progress_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Bonanza claim not found")
    
    if claim.processed_status not in ['Pending', 'Achieved - Pending Admin']:
        raise HTTPException(status_code=400, detail="Only pending bonanzas can be approved")
    
    # Update status to Admin Approved
    from app.models.base import get_indian_time
    claim.processed_status = 'Admin Approved'
    claim.admin_approved_by = _resolve_actor_id(current_user)
    claim.admin_approved_at = get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bonanza claim approved for user {claim.user_id}"
    }


@router.post("/achievement/reject/{progress_id}")
async def reject_achievement(
    progress_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Reject a bonanza achievement
    DC Protocol: Uses DynamicBonanzaHistory (single source of truth)
    DC PROTOCOL: Reverses bonanza deductions when claim is rejected
    NOTE: This endpoint is DEPRECATED - approval flow should use /admin/approve-claim/{claim_id} instead
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only Super Admin or Finance Admin can reject achievements")
    
    # DC Protocol: Query DynamicBonanzaHistory instead of BonanzaProgress
    claim = db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == progress_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Bonanza claim not found")
    
    # Update status to Rejected
    from app.models.base import get_indian_time
    claim.processed_status = 'Rejected'
    claim.rejection_reason = data.get('reason', 'No reason provided')
    claim.admin_approved_by = _resolve_actor_id(current_user)
    claim.admin_approved_at = get_indian_time()
    claim.super_admin_decision = 'rejected'
    
    # DC PROTOCOL: Reverse bonanza deductions for rejected claims (IDEMPOTENT + SAFE)
    user_id = claim.user_id
    deduction_direct = claim.deduction_amount_direct or 0
    deduction_matching = claim.deduction_amount_matching or 0
    
    # IDEMPOTENCY CHECK: Only reverse if flags indicate deductions were applied
    if claim.deductions_applied_direct > 0 or claim.deductions_applied_matching > 0:
        # Reverse DIRECT award deductions (iterate to avoid over-reversal)
        if deduction_direct > 0:
            from app.models.awards import UserAwardProgress
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
        claim.deductions_applied_direct = 0
        claim.deductions_applied_matching = 0
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bonanza claim rejected for user {claim.user_id}. Deductions reversed: {deduction_amount} points.",
        "reason": claim.rejection_reason
    }


@router.post("/cancel/{bonanza_id}")
async def cancel_bonanza(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Cancel bonanza (Soft Delete) - Changes status to 'Cancelled' but keeps record for audit
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Access denied - requires appropriate role"
    #     )
    
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    # Check if already cancelled
    if bonanza.status == 'Cancelled':
        raise HTTPException(status_code=400, detail="Bonanza is already cancelled")
    
    # DC Protocol: Check if any users have claimed this bonanza (query DynamicBonanzaHistory)
    from app.services.bonanza_service import BonanzaService
    bonanza_service = BonanzaService(db)
    
    claimed_count = bonanza_service.count_claimed_bonanzas(bonanza_id)
    
    if claimed_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel bonanza: {claimed_count} user(s) have already claimed this bonanza"
        )
    
    # Cancel the bonanza (soft delete)
    bonanza.status = 'Cancelled'
    bonanza.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' has been cancelled successfully",
        "bonanza_id": bonanza_id,
        "action": "cancelled"
    }


@router.post("/pause/{bonanza_id}")
async def pause_bonanza(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Pause an Approved bonanza — hides it from the public portal until reactivated.
    DC Protocol: Staff access via page-level permissions.
    """
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")

    if bonanza.status != 'Approved':
        raise HTTPException(status_code=400, detail=f"Only Approved bonanzas can be paused (current status: {bonanza.status})")

    bonanza.status = 'Paused'
    bonanza.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' has been paused. It is now hidden from partners.",
        "bonanza_id": bonanza_id,
        "action": "paused"
    }


@router.post("/activate/{bonanza_id}")
async def activate_bonanza(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Re-activate a Cancelled or Paused bonanza — restores it to Approved status.
    DC Protocol: Staff access via page-level permissions.
    """
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")

    if bonanza.status not in ('Cancelled', 'Paused'):
        raise HTTPException(status_code=400, detail=f"Only Cancelled or Paused bonanzas can be re-activated (current status: {bonanza.status})")

    bonanza.status = 'Approved'
    bonanza.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' has been re-activated and is now live.",
        "bonanza_id": bonanza_id,
        "action": "activated"
    }


@router.put("/edit/{bonanza_id}")
async def edit_bonanza(
    bonanza_id: int,
    data: BonanzaUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Staff endpoint to edit bonanza details (including extending end dates)
    Cannot edit if users have already claimed
    """
    # Staff access check
    user_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Only authorized Staff can edit bonanzas")
    
    # Get bonanza
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    # DC PROTOCOL: Allow editing but enforce data consistency
    # Update fields (only if provided)
    if data.name is not None:
        bonanza.name = data.name
    if data.start_date is not None:
        # DC-BONANZA-DATE-ONLY-001: strip time — always store midnight
        bonanza.start_date = data.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if data.end_date is not None:
        # DC-SLAB-RETRO-RESET-001: When end_date changes on a slab_wise bonanza,
        # delete the retro-backfill dc_migrations key so the corrected retro
        # (DC-SLAB-BONUS-RETRO-2605-001 v2) re-runs on next startup and credits
        # any advances whose lead.submit_date now falls within the extended window.
        if bonanza.reward_type == 'slab_wise' and bonanza.end_date != data.end_date:
            try:
                db.execute(text(
                    "DELETE FROM dc_migrations WHERE key = 'slab_bonus_retro_v2_20260711'"
                ))
                logger.info(f"[DC-SLAB-RETRO-RESET-001] Retro key deleted — bonanza {bonanza_id} end_date changed from {bonanza.end_date} to {data.end_date}")
            except Exception as _rreset_e:
                logger.warning(f"[DC-SLAB-RETRO-RESET-001] Key delete failed (non-fatal): {_rreset_e}")
        # DC-BONANZA-DATE-ONLY-001: strip time — always store midnight
        bonanza.end_date = data.end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if data.target_requirement is not None:
        bonanza.target_requirement = data.target_requirement
    if data.max_winners is not None:
        if data.max_winners < 1 or (data.max_winners > 500 and data.max_winners != 9999999):
            raise HTTPException(status_code=400, detail="Max winners must be between 1 and 500 (or unlimited)")
        # DC PROTOCOL: Cannot set max_winners lower than current claims
        if data.max_winners < bonanza.current_winners:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Cannot set max winners to {data.max_winners}. Already {bonanza.current_winners} users have claimed this bonanza. Max winners must be at least {bonanza.current_winners}."
            )
        bonanza.max_winners = data.max_winners
    if data.award_name is not None:
        bonanza.award_name = data.award_name
    if data.reward_amount is not None and bonanza.is_monetary:
        bonanza.reward_amount = data.reward_amount
    if data.counts_towards_regular is not None:
        bonanza.counts_towards_regular = data.counts_towards_regular
    if data.consume_achievements is not None:
        bonanza.consume_achievements = data.consume_achievements
    if data.portal is not None:
        bonanza.portal = data.portal
    if data.grace_days is not None:
        bonanza.grace_days = data.grace_days
    if data.lead_source_id is not None:
        bonanza.lead_source_id = data.lead_source_id
    if data.segment_id is not None:
        bonanza.segment_id = data.segment_id
    if data.registered_target_bonus is not None:
        if data.registered_target_bonus < 0:
            raise HTTPException(status_code=400, detail="Registered target bonus cannot be negative")
        bonanza.registered_target_bonus = data.registered_target_bonus
    if data.image_url is not None:
        bonanza.image_url = data.image_url if data.image_url != '' else None
    if data.reward_text is not None:
        bonanza.reward_text = data.reward_text
    # DC_BONANZA_SLABWISE_001: slab fields editable
    if data.slab_extra_amount is not None:
        bonanza.slab_extra_amount = data.slab_extra_amount
    if data.slab_base_reference is not None:
        bonanza.slab_base_reference = data.slab_base_reference
    # DC-SOLAR-DVR-ADV-20260701-001: advance count basis editable
    if data.advance_count_basis is not None:
        _valid_bases = {'CIBIL', 'DVR', 'BOTH', 'FIRST_DVR'}
        if data.advance_count_basis.upper() not in _valid_bases:
            raise HTTPException(status_code=400, detail=f"advance_count_basis must be one of {sorted(_valid_bases)}")
        bonanza.advance_count_basis = data.advance_count_basis.upper()

    # DC-EXTRA-COMM-001: update extra commission fields on edit
    if data.trigger_event is not None:
        bonanza.trigger_event = data.trigger_event or None
    if data.ec_l1_amount is not None:
        bonanza.ec_l1_amount = data.ec_l1_amount
    if data.ec_l2_amount is not None:
        bonanza.ec_l2_amount = data.ec_l2_amount
    if data.ec_l3_amount is not None:
        bonanza.ec_l3_amount = data.ec_l3_amount
    if data.ec_l4_amount is not None:
        bonanza.ec_l4_amount = data.ec_l4_amount
    if data.ec_l5_amount is not None:
        bonanza.ec_l5_amount = data.ec_l5_amount
    # DC-EC-PER-LEVEL-TRIGGER-001: update per-level trigger events on edit
    if data.ec_l1_trigger is not None:
        bonanza.ec_l1_trigger = data.ec_l1_trigger or None
    if data.ec_l2_trigger is not None:
        bonanza.ec_l2_trigger = data.ec_l2_trigger or None
    if data.ec_l3_trigger is not None:
        bonanza.ec_l3_trigger = data.ec_l3_trigger or None
    if data.ec_l4_trigger is not None:
        bonanza.ec_l4_trigger = data.ec_l4_trigger or None
    if data.ec_l5_trigger is not None:
        bonanza.ec_l5_trigger = data.ec_l5_trigger or None
    if data.category_filter_ids is not None and bonanza.reward_type in ('extra_commission', 'award', 'gift', 'cash', 'bonus'):
        db.execute(
            text("DELETE FROM bonanza_category_filters WHERE bonanza_id = :bid"),
            {"bid": bonanza.id}
        )
        for _cat_id in data.category_filter_ids:
            db.execute(
                text("INSERT INTO bonanza_category_filters (bonanza_id, category_id) "
                     "VALUES (:bid, :cid) ON CONFLICT DO NOTHING"),
                {"bid": bonanza.id, "cid": _cat_id}
            )

    # DC-AWARD-TRIGGER-001: update award_level_notes on edit
    if data.award_level_notes is not None and bonanza.reward_type in ('award', 'gift'):
        bonanza.award_level_notes = data.award_level_notes or None

    bonanza.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bonanza)

    # DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): Retroactive Evaluation
    # If triggers were updated, retroactively apply them to all leads in the bonanza period.
    if bonanza.reward_type in ('cash', 'bonus', 'slab_wise', 'extra_commission', 'award', 'gift'):
        try:
            from app.services.vgk_cash_bonus_trigger import apply_cash_bonus_trigger_if_active
            from app.models.crm import CRMLead
            from sqlalchemy import or_, func
            # Fetch leads that were active/created during the bonanza period
            _leads = db.query(CRMLead).filter(
                or_(
                    func.date(CRMLead.submit_date) >= bonanza.start_date.date(),
                    func.date(CRMLead.first_payment_date) >= bonanza.start_date.date(),
                    func.date(CRMLead.complete_date) >= bonanza.start_date.date()
                ),
                or_(
                    func.date(CRMLead.submit_date) <= bonanza.end_date.date(),
                    func.date(CRMLead.first_payment_date) <= bonanza.end_date.date(),
                    func.date(CRMLead.complete_date) <= bonanza.end_date.date()
                )
            ).all()
            for _lead in _leads:
                if getattr(_lead, 'submit_date', None):
                    apply_cash_bonus_trigger_if_active(db, _lead, 'file_submitted')
                if getattr(_lead, 'first_payment_date', None):
                    apply_cash_bonus_trigger_if_active(db, _lead, 'first_payment')
                if getattr(_lead, 'complete_date', None):
                    apply_cash_bonus_trigger_if_active(db, _lead, 'file_completed')
            db.commit()
        except Exception as e:
            logger.error(f"Retroactive bonanza evaluation failed for bonanza {bonanza.id}: {e}")
            
    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' updated successfully",
        "bonanza": {
            "id": bonanza.id,
            "name": bonanza.name,
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat(),
            "target_requirement": bonanza.target_requirement,
            "max_winners": bonanza.max_winners,
            "current_winners": bonanza.current_winners,
            "award_name": bonanza.award_name,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "image_url": bonanza.image_url
        }
    }


@router.post("/{bonanza_id}/upload-image")
async def upload_bonanza_image(
    bonanza_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-BONANZA-IMG-001: Upload a promo/banner image for a bonanza campaign."""
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")

    allowed = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    ct = file.content_type or ''
    if ct not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP or GIF images are allowed")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")

    # DC_BONANZA_IMG_COMPRESS_001: compress to WebP before storage
    data, ext = _compress_bonanza_img(data, ct)

    import uuid
    storage_path = f"bonanza_images/{bonanza_id}_{uuid.uuid4().hex[:8]}.{ext}"

    try:
        from app.services.object_storage import storage_service
        storage_service.upload_file(storage_path, data)
        public_url = f"/storage/{storage_path}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    bonanza.image_url = public_url
    db.commit()

    return {"success": True, "image_url": public_url}


@router.delete("/delete/{bonanza_id}")
async def delete_bonanza(
    bonanza_id: int,
    deletion_request: BonanzaDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    🛡️ SOFT DELETE bonanza with full audit trail
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    
    PROTECTION SYSTEM:
    - Soft delete (marks as deleted, preserves data)
    - Full audit log with timeline
    - Can be restored if needed
    
    Safety Rules:
    - Cannot delete if users have claimed/achieved the bonanza
    - Cannot delete if status is 'Completed'
    - Deletion reason is MANDATORY
    """
    # DC Protocol (Feb 2026): Staff access via page-level permissions
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    # Get bonanza
    bonanza = db.query(Bonanza).filter(
        Bonanza.id == bonanza_id,
        Bonanza.is_deleted == False  # Only show non-deleted
    ).first()
    
    if not bonanza:
        raise HTTPException(
            status_code=404,
            detail="Bonanza not found or already deleted"
        )
    
    # Safety Check 1: Cannot delete completed bonanzas
    if bonanza.status == 'Completed':
        raise HTTPException(
            status_code=400,
            detail="Cannot delete completed bonanzas. Use Cancel status instead."
        )
    
    # DC Protocol: Safety Check 2 - Check if any users have claimed this bonanza
    from app.services.bonanza_service import BonanzaService
    bonanza_service = BonanzaService(db)
    
    claimed_count = bonanza_service.count_claimed_bonanzas(bonanza_id)
    
    if claimed_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {claimed_count} user(s) have claimed this bonanza. Use Cancel status instead."
        )
    
    # SOFT DELETE - Mark as deleted (preserves data)
    bonanza.is_deleted = True
    bonanza.deleted_at = datetime.utcnow()
    bonanza.deleted_by = _resolve_actor_id(current_user)
    bonanza.deletion_reason = deletion_request.deletion_reason
    
    db.commit()
    
    # Create comprehensive audit log
    create_deletion_audit_log(
        db=db,
        user=current_user,
        entity_type="BONANZA",
        entity_id=str(bonanza_id),
        entity_name=bonanza.name,
        deletion_reason=deletion_request.deletion_reason,
        ip_address=request.client.host if request.client else None,
        additional_details={
            "criteria_type": bonanza.criteria_type,
            "target_requirement": bonanza.target_requirement,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            "status": bonanza.status,
            "current_winners": bonanza.current_winners
        }
    )
    
    return {
        "success": True,
        "message": f"✅ Bonanza '{bonanza.name}' has been soft-deleted successfully",
        "bonanza_id": bonanza_id,
        "action": "soft_deleted",
        "deleted_at": bonanza.deleted_at.isoformat(),
        "deleted_by": _resolve_actor_id(current_user),
        "audit_trail": "Complete audit log created",
        "note": "Bonanza can be restored by RVZ if needed"
    }


@router.post('/restore/{bonanza_id}')
async def restore_bonanza(
    bonanza_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    🔄 RESTORE soft-deleted bonanza
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    
    Restores a previously soft-deleted bonanza back to active state
    Full audit trail maintained
    """
    # DC Protocol (Feb 2026): Staff access via page-level permissions
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['RVZ ID', 'Super Admin', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    # Get deleted bonanza
    bonanza = db.query(Bonanza).filter(
        Bonanza.id == bonanza_id,
        Bonanza.is_deleted == True  # Only show deleted ones
    ).first()
    
    if not bonanza:
        raise HTTPException(
            status_code=404,
            detail='Bonanza not found or not deleted'
        )
    
    # Restore bonanza
    bonanza_name = bonanza.name
    bonanza.is_deleted = False
    bonanza.deleted_at = None
    bonanza.deleted_by = None
    bonanza.deletion_reason = None
    
    db.commit()
    
    # Create restore audit log
    create_restore_audit_log(
        db=db,
        user=current_user,
        entity_type='BONANZA',
        entity_id=str(bonanza_id),
        entity_name=bonanza_name,
        ip_address=request.client.host if request.client else None
    )
    
    return {
        'success': True,
        'message': f'✅ Bonanza "{bonanza_name}" has been restored successfully',
        'bonanza_id': bonanza_id,
        'action': 'restored',
        'restored_by': current_user.id,
        'audit_trail': 'Complete audit log created'
    }


@router.post("/admin/approve-claim/{claim_id}")
async def approve_bonanza_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Admin approves bonanza claim - applies deductions to award counts
    
    ADMIN APPROVAL WORKFLOW:
    1. User claims bonanza → processed_at = NULL (pending)
    2. Admin approves → processed_at = NOW(), deduction_applied_* = True
    3. Only APPROVED claims reduce award eligibility
    
    Permissions: Staff, VGK4U Supreme, Accounts
    """
    # Check permissions
    user_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only authorized Staff can approve bonanza claims"
    #     )
    
    # Get bonanza claim
    claim = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.id == claim_id
    ).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Bonanza claim not found")
    
    # Check if already approved
    if claim.processed_at is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Bonanza claim already approved by {claim.processed_by} on {claim.processed_at}"
        )
    
    # Get user and bonanza details for response
    user = db.query(User).filter(User.id == claim.user_id).first()
    bonanza = db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
    
    # Approve claim - set processed fields and apply deductions
    from app.models.base import get_indian_time
    claim.processed_at = get_indian_time()
    claim.processed_by = _resolve_actor_id(current_user)
    
    # Apply deductions based on bonanza criteria
    # CRITICAL: Only apply deductions if bonanza.counts_towards_regular is TRUE
    deduction_amount = bonanza.target_requirement
    awards_affected = []
    bonanzas_affected = []
    
    # Set deduction tracking fields only if bonanza counts towards regular awards
    if bonanza.counts_towards_regular:
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            claim.deduction_applied_to_direct_awards = True
            claim.deduction_amount_direct = deduction_amount
        elif bonanza.criteria_type == 'matching_points':
            claim.deduction_applied_to_matching_awards = True
            claim.deduction_amount_matching = deduction_amount
        elif bonanza.criteria_type == 'team_size':
            claim.deduction_applied_to_direct_awards = True
            claim.deduction_amount_direct = deduction_amount
    
    # IMMEDIATE AWARD DEDUCTION: Only if bonanza.counts_towards_regular is TRUE
    if bonanza.counts_towards_regular:
        if bonanza.criteria_type in ['direct_referrals', 'team_size']:
            # Get direct award progress records
            award_progress_records = db.query(UserAwardProgress).filter(
                UserAwardProgress.user_id == claim.user_id,
                UserAwardProgress.status.in_(['In Progress', 'Achieved', 'Pending'])
            ).all()
            
            for award_progress in award_progress_records:
                # Apply bonanza deduction (don't allow negative)
                award_progress.bonanza_deductions_applied += deduction_amount
                award_progress.effective_progress_count = max(
                    0,
                    award_progress.current_referrals - award_progress.bonanza_deductions_applied
                )
                awards_affected.append(f"Direct Award Tier {award_progress.award_tier_id}")
                
        elif bonanza.criteria_type == 'matching_points':
            # Get matching award progress records
            matching_progress_records = db.query(UserMatchingAwardProgress).filter(
                UserMatchingAwardProgress.user_id == claim.user_id,
                UserMatchingAwardProgress.status.in_(['Pending', 'Achieved', 'In Progress'])
            ).all()
            
            for matching_progress in matching_progress_records:
                # Apply bonanza deduction (don't allow negative)
                matching_progress.bonanza_deductions_applied += deduction_amount
                matching_progress.effective_progress_count = max(
                    0,
                    matching_progress.current_matches - matching_progress.bonanza_deductions_applied
                )
                awards_affected.append(f"Matching Award Tier {matching_progress.award_tier_id}")
    
    # IMMEDIATE BONANZA DEDUCTION: Only if bonanza.consume_achievements is TRUE
    # DC Protocol: Auto-reject competing claims (OPTION B - Simplified Approach)
    if bonanza.consume_achievements:
        # Get other bonanza claims (PENDING ONLY - not yet admin approved)
        # CRITICAL: Only reject genuinely pending claims, preserve already-approved ones
        other_bonanza_claims = db.query(DynamicBonanzaHistory).join(
            Bonanza, DynamicBonanzaHistory.bonanza_id == Bonanza.id
        ).filter(
            DynamicBonanzaHistory.user_id == claim.user_id,
            DynamicBonanzaHistory.bonanza_id != bonanza.id,
            DynamicBonanzaHistory.processed_status.in_(['Pending', 'Achieved - Pending Admin']),
            DynamicBonanzaHistory.admin_approved_at.is_(None),  # ✅ SAFETY GUARD: Only pending claims!
            Bonanza.criteria_type == bonanza.criteria_type
        ).all()
        
        for other_claim in other_bonanza_claims:
            # Get the bonanza details
            other_bonanza = db.query(Bonanza).filter(Bonanza.id == other_claim.bonanza_id).first()
            
            if other_bonanza:
                # AUTO-REJECT competing claim (OPTION B)
                other_claim.processed_status = 'Rejected'
                other_claim.rejection_reason = (
                    f"Achievements consumed by approved bonanza '{bonanza.name}' "
                    f"(ID: {bonanza.id}). This bonanza required {deduction_amount} "
                    f"{bonanza.criteria_type} which are no longer available for other claims."
                )
                other_claim.super_admin_decision = 'rejected'
                other_claim.super_admin_decision_by = current_user.id
                other_claim.super_admin_decision_at = get_indian_time()
                
                # Add audit note
                rejection_note = (
                    f"Auto-rejected on {get_indian_time().strftime('%Y-%m-%d %H:%M:%S')} "
                    f"due to achievements being consumed by '{bonanza.name}' approval."
                )
                if other_claim.delivery_notes:
                    other_claim.delivery_notes = f"{other_claim.delivery_notes}\n{rejection_note}"
                else:
                    other_claim.delivery_notes = rejection_note
                
                bonanzas_affected.append(f"{other_bonanza.name} (auto-rejected - achievements consumed)")
    
    db.commit()
    db.refresh(claim)
    
    return {
        "success": True,
        "message": f"✅ Bonanza claim approved successfully. Deductions applied to {len(awards_affected)} awards and {len(bonanzas_affected)} other bonanzas.",
        "claim_details": {
            "claim_id": claim.id,
            "user_id": claim.user_id,
            "user_name": user.name if user else "Unknown",
            "bonanza_name": bonanza.name if bonanza else "Unknown",
            "reward_value": float(claim.reward_value_claimed) if claim.reward_value_claimed else 0.0,
            "approved_by": _resolve_actor_id(current_user),
            "approved_at": claim.processed_at.isoformat(),
            "deductions_applied": {
                "direct_awards": claim.deduction_amount_direct if claim.deduction_applied_to_direct_awards else 0,
                "matching_awards": claim.deduction_amount_matching if claim.deduction_applied_to_matching_awards else 0
            },
            "awards_affected": awards_affected,
            "bonanzas_affected": bonanzas_affected
        }
    }


@router.get("/admin/pending-claims")
async def get_pending_bonanza_claims(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all pending bonanza claims (awaiting admin approval)
    
    Shows claims where processed_at IS NULL
    
    Permissions: Staff, VGK4U Supreme, Accounts
    """
    # Check permissions
    user_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Super Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only authorized Staff can view pending bonanza claims"
    #     )
    
    # Get all pending claims
    pending_claims = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.processed_at.is_(None)
    ).all()
    
    # Format response
    claims_list = []
    for claim in pending_claims:
        user = db.query(User).filter(User.id == claim.user_id).first()
        bonanza = db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
        
        claims_list.append({
            "claim_id": claim.id,
            "user_id": claim.user_id,
            "user_name": user.name if user else "Unknown",
            "bonanza_id": claim.bonanza_id,
            "bonanza_name": bonanza.name if bonanza else "Unknown",
            "reward_value": float(claim.reward_value_claimed) if claim.reward_value_claimed else 0.0,
            "claimed_at": claim.claimed_at.isoformat() if claim.claimed_at else None,
            "direct_count_achieved": claim.direct_count_achieved or 0,
            "matching_count_achieved": claim.matching_count_achieved or 0,
            "will_deduct_direct": bonanza.target_requirement if bonanza and bonanza.criteria_type in ['direct_referrals', 'team_size'] else 0,
            "will_deduct_matching": bonanza.target_requirement if bonanza and bonanza.criteria_type == 'matching_points' else 0
        })
    
    return {
        "success": True,
        "total_pending": len(claims_list),
        "pending_claims": claims_list
    }


class ClaimOnBehalfRequest(BaseModel):
    """Request schema for staff claiming bonanza on behalf of MNR member"""
    user_id: str
    bonanza_id: int
    staff_notes: Optional[str] = None


@router.post("/admin/claim-on-behalf")
async def claim_bonanza_on_behalf(
    data: ClaimOnBehalfRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol (Feb 2026): Staff claims bonanza on behalf of MNR member
    
    - Creates DynamicBonanzaHistory with processed_status = 'Pending Approval'
    - Applies deductions to user's direct/matching awards IMMEDIATELY
    - Same logic as user self-claim but triggered by staff
    
    Permissions: VGK4U Supreme, Accounts Department, Admin, Super Admin
    """
    from sqlalchemy import func, and_
    from sqlalchemy.orm import aliased
    from app.models.placement import Placement
    from app.models.transaction import Transaction
    
    # Permission check
    user_type = (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user_type not in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(status_code=403, detail="Access denied - requires appropriate role")
    
    # Get staff identifier for audit
    staff_id = getattr(current_user, 'emp_code', None) or str(current_user.id)
    
    # Get the target user
    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {data.user_id} not found")
    
    # DC Protocol Feb 2026: Check target user eligibility (activation + KYC + utilisation + groups)
    # DC Protocol Feb 2026: VGK4U Supreme (MR10001) can skip eligibility checks
    staff_emp_code = getattr(current_user, 'emp_code', None)
    is_skip_level_authority = (staff_emp_code == 'MR10001' and user_type in ('VGK4U Supreme', 'VGK4U', 'RVZ ID'))
    
    if not is_skip_level_authority:
        from app.core.scheduler import get_user_eligibility_status
        target_eligibility = get_user_eligibility_status(db, target_user)
        if not target_eligibility['is_eligible']:
            blocking_message = target_eligibility['blocking_reasons'][0] if target_eligibility['blocking_reasons'] else "Target user is not eligible for bonanza claims."
            raise HTTPException(status_code=403, detail=f"User {data.user_id} is not eligible: {blocking_message}")
    else:
        import logging
        logging.info(f"[DC-SKIP-LEVEL] VGK4U Supreme MR10001 bypassed eligibility check for user {data.user_id}")
    
    # Get the bonanza
    bonanza = db.query(Bonanza).filter(
        Bonanza.id == data.bonanza_id,
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False
    ).first()
    
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found or not approved")
    
    # Check if bonanza period has expired (same validation as self-claim)
    now = datetime.utcnow()
    if bonanza.end_date and bonanza.end_date < now:
        raise HTTPException(status_code=400, detail="Bonanza period has ended. Cannot claim after end date.")
    
    # Check if already claimed
    existing_claim = db.query(DynamicBonanzaHistory).filter(
        DynamicBonanzaHistory.user_id == data.user_id,
        DynamicBonanzaHistory.bonanza_id == data.bonanza_id
    ).first()
    
    if existing_claim:
        raise HTTPException(status_code=400, detail="User has already claimed this bonanza")
    
    # Check max winners limit
    if bonanza.current_winners >= bonanza.max_winners:
        raise HTTPException(status_code=400, detail=f"All {bonanza.max_winners} slots are filled")
    
    # Calculate user's current progress (same logic as self-claim)
    current_progress = 0
    
    if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
        DirectReferral = aliased(User)
        current_progress = db.query(func.count(DirectReferral.id)).filter(
            DirectReferral.referrer_id == data.user_id,
            DirectReferral.account_status == 'Active',
            DirectReferral.activation_date.isnot(None),
            DirectReferral.activation_date >= bonanza.start_date,
            DirectReferral.activation_date <= bonanza.end_date,
            DirectReferral.is_welcome_coupon == False,
            DirectReferral.package_points > 0
        ).scalar() or 0
        
    elif bonanza.criteria_type == 'matching_points':
        matching_pairs = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == data.user_id,
            Transaction.transaction_type == 'Matching Referral Income',
            Transaction.created_at >= bonanza.start_date,
            Transaction.created_at <= bonanza.end_date,
            Transaction.gross_amount > 0
        ).scalar() or 0
        current_progress = matching_pairs
        
    elif bonanza.criteria_type == 'team_size':
        TeamMember = aliased(User)
        team_count = db.query(func.count(TeamMember.id)).join(
            Placement, Placement.child_id == TeamMember.id
        ).filter(
            Placement.parent_id == data.user_id,
            TeamMember.account_status == 'Active',
            TeamMember.activation_date.isnot(None),
            TeamMember.activation_date >= bonanza.start_date,
            TeamMember.activation_date <= bonanza.end_date,
            TeamMember.is_welcome_coupon != True,
            TeamMember.package_points > 0
        ).scalar() or 0
        current_progress = team_count
    
    # Verify achievement
    if current_progress < bonanza.target_requirement:
        raise HTTPException(
            status_code=400,
            detail=f"User has not achieved target. Current: {current_progress}, Required: {bonanza.target_requirement}"
        )
    
    # DC Protocol Feb 2026: ALL bonanza claims consume referrals/matching from regular awards
    deduction_direct = 0
    deduction_matching = 0
    
    if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
        deduction_direct = bonanza.target_requirement
    elif bonanza.criteria_type == 'matching_points':
        deduction_matching = bonanza.target_requirement
    
    # Capture contributor snapshots (always capture regardless of deduction)
    direct_contributors_snapshot = None
    matching_contributors_snapshot = None
    
    if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
        snapshot_filters = [
            User.referrer_id == data.user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon != True,
            User.package_points > 0,
            User.activation_date.isnot(None)
        ]
        if bonanza.start_date:
            snapshot_filters.append(User.activation_date >= bonanza.start_date)
        if bonanza.end_date:
            snapshot_filters.append(User.activation_date <= bonanza.end_date)
        referrals = db.query(User).filter(and_(*snapshot_filters)).order_by(User.activation_date.asc()).all()
        
        consumed_referrals = referrals[:deduction_direct]
        direct_contributors_snapshot = [
            {
                'user_id': ref.id,
                'name': ref.name,
                'package': ref.get_package_type(),
                'points': float(ref.package_points or 0),
                'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
            }
            for ref in consumed_referrals
        ]
    
    elif bonanza.criteria_type == 'matching_points':
        left_leg = db.query(User).filter(
            User.position.like(f'{target_user.position}L%'),
            User.coupon_status == 'Activated',
            User.is_welcome_coupon != True,
            User.package_points > 0
        ).order_by(User.activation_date.asc()).all()
        
        right_leg = db.query(User).filter(
            User.position.like(f'{target_user.position}R%'),
            User.coupon_status == 'Activated',
            User.is_welcome_coupon != True,
            User.package_points > 0
        ).order_by(User.activation_date.asc()).all()
        
        matching_contributors_snapshot = {
            'left_leg': [{'user_id': m.id, 'name': m.name, 'package': m.get_package_type(), 'points': float(m.package_points or 0)} for m in left_leg],
            'right_leg': [{'user_id': m.id, 'name': m.name, 'package': m.get_package_type(), 'points': float(m.package_points or 0)} for m in right_leg]
        }
    
    # Calculate budgeted value
    budgeted_value = bonanza.actual_price if bonanza.actual_price else (bonanza.reward_amount or 0)
    
    try:
        # Create DynamicBonanzaHistory record
        history = DynamicBonanzaHistory(
            user_id=data.user_id,
            bonanza_id=bonanza.id,
            claimed_reward_id=None,
            direct_count_achieved=current_progress if bonanza.criteria_type in ['direct_referrals', 'direct_referral'] else 0,
            matching_count_achieved=current_progress if bonanza.criteria_type == 'matching_points' else 0,
            deduction_amount_direct=deduction_direct,
            deduction_amount_matching=deduction_matching,
            deduction_applied_to_direct_awards=(bonanza.criteria_type in ['direct_referrals', 'direct_referral']),
            deduction_applied_to_matching_awards=(bonanza.criteria_type == 'matching_points'),
            reward_value_claimed=bonanza.reward_amount if bonanza.is_monetary else 0,
            budgeted_amount=budgeted_value,
            reward_type=bonanza.reward_type,
            award_name=bonanza.award_name,
            award_image=bonanza.reward_file,
            is_monetary=bonanza.is_monetary,
            actual_cost_incurred=0,
            claimed_at=datetime.utcnow(),
            processed_status=AwardStatus.PENDING_APPROVAL,  # DC Protocol: Start at Pending Approval
            rvz_approval_status='Pending RVZ Approval',
            procurement_status=None,
            delivery_notes=f"Staff claimed on behalf. Target: {bonanza.target_requirement}, Progress: {current_progress}. {data.staff_notes or ''}",
            direct_contributors_snapshot=direct_contributors_snapshot,
            matching_contributors_snapshot=matching_contributors_snapshot
        )
        
        db.add(history)
        
        # Increment winners count
        bonanza.current_winners += 1
        
        db.commit()
        db.refresh(history)
        
        # DC Protocol: Sync award statuses after bonanza claim-on-behalf
        # Segment-specific: direct deductions affect direct awards, matching deductions affect matching awards
        if deduction_direct > 0 or deduction_matching > 0:
            try:
                from app.services.award_sync_service import sync_user_award_statuses
                sync_result = sync_user_award_statuses(db, data.user_id)
                import logging
                logging.getLogger(__name__).info(
                    f"[BONANZA-CLAIM-ON-BEHALF-SYNC] Award sync for {data.user_id} by {staff_id}: "
                    f"direct_demoted={sync_result.get('direct', {}).get('demoted', 0)}, "
                    f"matching_demoted={sync_result.get('matching', {}).get('demoted', 0)}"
                )
            except Exception as sync_err:
                import logging
                logging.getLogger(__name__).warning(
                    f"[BONANZA-CLAIM-ON-BEHALF-SYNC] Award sync failed for {data.user_id}: {sync_err}"
                )
        
        return {
            "success": True,
            "message": f"Bonanza claimed for {target_user.name} ({data.user_id}). Status: Pending Approval",
            "claim_id": history.id,
            "user_id": data.user_id,
            "user_name": target_user.name,
            "bonanza_name": bonanza.name,
            "reward": bonanza.award_name if not bonanza.is_monetary else f"₹{bonanza.reward_amount:,.0f}",
            "deduction_applied": {
                "direct": deduction_direct,
                "matching": deduction_matching
            },
            "claimed_by_staff": staff_id,
            "slots_remaining": bonanza.max_winners - bonanza.current_winners
        }
        
    except Exception as e:
        db.rollback()
        if "unique_user_bonanza_claim" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="User has already claimed this bonanza")
        raise HTTPException(status_code=500, detail=f"Error claiming bonanza: {str(e)}")


@router.get("/admin/all-eligibility")
async def get_all_user_bonanza_eligibility(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all user-wise bonanza eligibility data with claim and delivery status
    
    Permissions: Admin, Super Admin, Finance Admin, RVZ ID
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID', 'VGK4U Supreme', 'VGK4U', 'staff']:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only admins can view all bonanza eligibility data"
    #     )
    
    # Get all active bonanzas
    active_bonanzas = db.query(Bonanza).filter(
        Bonanza.status == 'Approved',
        Bonanza.is_deleted == False
    ).all()
    
    eligibility_data = []
    _elig_cache = {}
    
    for bonanza in active_bonanzas:
        # Get all users who meet the criteria
        # CRITICAL: Count ONLY achievements within bonanza date window (following existing claim logic)
        if bonanza.criteria_type in ['direct_referrals', 'direct_referral']:
            # Count direct referrals activated WITHIN bonanza period (start_date to end_date)
            # Use GREATEST with proper timestamp handling
            from datetime import datetime
            oct15_cutoff = datetime(2025, 10, 15, 0, 0, 0)
            start_filter = bonanza.start_date if bonanza.start_date > oct15_cutoff else oct15_cutoff
            
            eligible_users = db.execute(text("""
                SELECT u.id, u.name, COUNT(ref.id) as achieved_count
                FROM "user" u
                LEFT JOIN "user" ref ON ref.referrer_id = u.id 
                    AND ref.coupon_status = 'Activated'
                    AND ref.activation_date >= :start_date
                    AND ref.activation_date <= :end_date
                WHERE u.registration_date >= '2025-10-15'
                GROUP BY u.id, u.name
                HAVING COUNT(ref.id) >= :target
            """), {
                "target": bonanza.target_requirement,
                "start_date": start_filter,
                "end_date": bonanza.end_date
            }).fetchall()
            
        elif bonanza.criteria_type == 'matching_points':
            # Count matching income transactions WITHIN bonanza period
            # Must match transaction_type used in claim endpoint: 'Matching Referral Income'
            from datetime import datetime
            oct15_cutoff = datetime(2025, 10, 15, 0, 0, 0)
            start_filter = bonanza.start_date if bonanza.start_date > oct15_cutoff else oct15_cutoff
            
            eligible_users = db.execute(text("""
                SELECT u.id, u.name, COUNT(t.id) as achieved_count
                FROM "user" u
                LEFT JOIN transaction t ON t.referrer_id = u.id
                    AND t.transaction_type = 'Matching Referral Income'
                    AND t.timestamp >= :start_date
                    AND t.timestamp <= :end_date
                WHERE u.registration_date >= '2025-10-15'
                GROUP BY u.id, u.name
                HAVING COUNT(t.id) >= :target
            """), {
                "target": bonanza.target_requirement,
                "start_date": start_filter,
                "end_date": bonanza.end_date
            }).fetchall()
            
        elif bonanza.criteria_type == 'team_size':
            # Count team members activated WITHIN bonanza period
            from datetime import datetime
            oct15_cutoff = datetime(2025, 10, 15, 0, 0, 0)
            start_filter = bonanza.start_date if bonanza.start_date > oct15_cutoff else oct15_cutoff
            
            eligible_users = db.execute(text("""
                SELECT u.id, u.name, COUNT(team.id) as achieved_count
                FROM "user" u
                LEFT JOIN placement p ON p.parent_id = u.id
                LEFT JOIN "user" team ON team.id = p.child_id
                    AND team.account_status = 'Active'
                    AND team.activation_date >= :start_date
                    AND team.activation_date <= :end_date
                WHERE u.registration_date >= '2025-10-15'
                GROUP BY u.id, u.name
                HAVING COUNT(team.id) >= :target
            """), {
                "target": bonanza.target_requirement,
                "start_date": start_filter,
                "end_date": bonanza.end_date
            }).fetchall()
        elif bonanza.portal == 'VGK' or bonanza.reward_type == 'slab_wise':
            # DC_VGK_ELIG_001: VGK slab_wise bonanzas use BonanzaProgress (partner_id),
            # not the MNR user table. Build a synthetic eligible_users list from
            # all BonanzaProgress rows for this bonanza (claimed AND unclaimed qualified partners).
            from app.models.bonanza import BonanzaProgress
            progress_rows = db.query(BonanzaProgress).filter(
                BonanzaProgress.bonanza_id == bonanza.id,
                BonanzaProgress.partner_id.isnot(None)
            ).all()
            partner_ids_for_bz = list({p.partner_id for p in progress_rows})
            # Fetch partner info
            partner_info = {}
            if partner_ids_for_bz:
                rows_p = db.execute(text("""
                    SELECT id, partner_name, partner_code
                    FROM official_partners WHERE id = ANY(:ids)
                """), {"ids": partner_ids_for_bz}).fetchall()
                partner_info = {r[0]: {"name": r[1], "code": r[2]} for r in rows_p}
            # Also find partners who qualify but haven't claimed yet
            # (current_progress >= target from BonanzaProgress record)
            eligible_users = []
            eligible_user_ids = set()
            for bp in progress_rows:
                pi = partner_info.get(bp.partner_id, {})
                # Use the stored current_progress (set at claim time)
                progress_val = bp.current_progress or 0
                # Synthetic row: (partner_id_as_str, partner_name, progress)
                pid_key = f"VGK#{bp.partner_id}"
                eligible_users.append((pid_key, pi.get("name", f"Partner #{bp.partner_id}"), progress_val))
                eligible_user_ids.add(pid_key)
            # DC-BONANZA-ALL-PARTNERS-001: Include ALL registered partners (active or not)
            # Non-activated members use the same target — no is_active filter.
            all_partner_rows = db.execute(text("""
                SELECT id, partner_name, partner_code
                FROM official_partners
            """)).fetchall()
            for pr in all_partner_rows:
                pid_key = f"VGK#{pr[0]}"
                if pid_key in eligible_user_ids:
                    continue  # already in list (claimed)
                _elig_basis = (getattr(bonanza, 'advance_count_basis', None) or 'CIBIL').upper()
                if _elig_basis == 'FIRST_DVR':
                    adv_count = _count_first_dvr_income_for_bonanza(db, pr[0], bonanza)
                elif _is_solar_award_dvr(db, bonanza):
                    # DC-SOLAR-AWARD-DVR-001: award/gift + Solar + created ≥ 2026-07-01 → DVR stage
                    adv_count = _count_solar_advances_for_bonanza(db, pr[0], bonanza, basis_override='DVR')
                elif bonanza.reward_type == 'slab_wise' or _elig_basis != 'CIBIL':
                    adv_count = _count_solar_advances_for_bonanza(db, pr[0], bonanza)
                else:
                    adv_count = _count_vgk_completed_deals(db, pr[2] or str(pr[0]), bonanza)
                if adv_count >= (bonanza.target_requirement or 1):
                    eligible_users.append((pid_key, pr[1], adv_count))
                    eligible_user_ids.add(pid_key)
            # Build claim map from BonanzaProgress
            progress_by_pid = {f"VGK#{bp.partner_id}": bp for bp in progress_rows}
            for pid_key, user_name, achieved_count in eligible_users:
                bp = progress_by_pid.get(pid_key)
                deal_count = achieved_count
                if bp:
                    claim_status = bp.processed_status or 'Pending'
                    claim_id = bp.id
                    claimed_at = bp.achieved_date
                    delivery_status = 'delivered' if bp.reward_given else ('pending' if claim_status != 'Pending' else 'N/A')
                    already_claimed = True
                else:
                    claim_status = 'unclaimed'
                    claim_id = None
                    claimed_at = None
                    delivery_status = 'N/A'
                    already_claimed = False
                from datetime import datetime as _dt
                now2 = _dt.utcnow()
                is_expired2 = bonanza.end_date and bonanza.end_date < now2
                slab_payout = (float(bonanza.slab_extra_amount) * deal_count) if bonanza.slab_extra_amount and deal_count else None
                eligibility_data.append({
                    "user_id": pid_key,
                    "user_name": user_name,
                    "bonanza_id": bonanza.id,
                    "bonanza_name": bonanza.name,
                    "reward_type": bonanza.reward_type,
                    "reward_value": slab_payout if slab_payout is not None else (float(bonanza.reward_amount) if bonanza.reward_amount else 0.0),
                    "reward_amount": slab_payout if slab_payout is not None else (float(bonanza.reward_amount) if bonanza.reward_amount else 0.0),
                    "slab_extra_amount": float(bonanza.slab_extra_amount) if bonanza.slab_extra_amount else None,
                    "slab_payout": slab_payout,
                    "award_name": bonanza.award_name,
                    "is_monetary": bonanza.is_monetary,
                    "criteria_type": bonanza.criteria_type,
                    "target_requirement": bonanza.target_requirement,
                    "current_progress": deal_count,
                    "achieved_count": deal_count,
                    "raw_achieved_count": deal_count,
                    "is_eligible": deal_count >= (bonanza.target_requirement or 1),
                    "already_claimed": already_claimed,
                    "claim_status": claim_status,
                    "claim_id": claim_id,
                    "claimed_at": claimed_at.isoformat() if claimed_at else None,
                    "delivery_status": delivery_status,
                    "consume_achievements": bonanza.consume_achievements,
                    "is_expired": is_expired2,
                    "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
                    "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
                    "eligibility_criteria": None,
                    "portal": "VGK",
                })
            continue  # skip the shared MNR processing below
        else:
            continue
        
        eligible_users = list(eligible_users)
        eligible_user_ids = set(row[0] for row in eligible_users)
        existing_claims = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.bonanza_id == bonanza.id,
            DynamicBonanzaHistory.claimed_at.isnot(None)
        ).all()
        for ec in existing_claims:
            if ec.user_id not in eligible_user_ids:
                user_obj = db.query(User).filter(User.id == ec.user_id).first()
                if user_obj:
                    achieved = ec.direct_count_achieved or ec.matching_count_achieved or bonanza.target_requirement
                    eligible_users.append((ec.user_id, user_obj.name, achieved))
                    eligible_user_ids.add(ec.user_id)
        
        # For each eligible user, get their claim and delivery status
        for user_row in eligible_users:
            user_id = user_row[0]
            user_name = user_row[1]
            raw_achieved_count = user_row[2]
            
            net_achieved_count = raw_achieved_count
            total_consumed = 0
            is_direct_type = bonanza.criteria_type in ('direct_referrals', 'direct_referral')
            other_claimed = db.query(DynamicBonanzaHistory).filter(
                DynamicBonanzaHistory.user_id == user_id,
                DynamicBonanzaHistory.bonanza_id != bonanza.id,
                DynamicBonanzaHistory.claimed_at.isnot(None)
            ).all()
            for claimed_record in other_claimed:
                claimed_bonanza = db.query(Bonanza).filter(Bonanza.id == claimed_record.bonanza_id).first()
                if not claimed_bonanza:
                    continue
                claimed_is_direct = claimed_bonanza.criteria_type in ('direct_referrals', 'direct_referral')
                if is_direct_type and claimed_is_direct:
                    total_consumed += claimed_record.direct_count_achieved or claimed_bonanza.target_requirement
                elif not is_direct_type and bonanza.criteria_type == claimed_bonanza.criteria_type:
                    if bonanza.criteria_type == 'matching_points':
                        total_consumed += claimed_record.matching_count_achieved or claimed_bonanza.target_requirement
                    elif bonanza.criteria_type == 'team_size':
                        total_consumed += claimed_bonanza.target_requirement
            net_achieved_count = max(0, raw_achieved_count - total_consumed)
            
            claim = db.query(DynamicBonanzaHistory).filter(
                DynamicBonanzaHistory.user_id == user_id,
                DynamicBonanzaHistory.bonanza_id == bonanza.id
            ).first()
            
            if net_achieved_count < bonanza.target_requirement and not claim:
                continue
            
            if claim:
                claim_status = 'pending' if claim.processed_at is None else 'approved'
                claim_id = claim.id
                claimed_at = claim.claimed_at
                # Delivery status based on claim processing (delivery_status column doesn't exist yet)
                if claim.processed_at is None:
                    delivery_status = 'N/A'  # Not yet approved
                elif claim.delivery_notes and 'delivered' in claim.delivery_notes.lower():
                    delivery_status = 'delivered'
                elif claim.delivery_notes and 'shipped' in claim.delivery_notes.lower():
                    delivery_status = 'shipped'
                else:
                    delivery_status = 'pending'  # Approved but not shipped
            else:
                claim_status = 'unclaimed'
                claim_id = None
                claimed_at = None
                delivery_status = 'N/A'
            
            # Check if bonanza has expired
            now = datetime.utcnow()
            is_expired = bonanza.end_date and bonanza.end_date < now
            
            user_elig_data = None
            if user_id not in _elig_cache:
                try:
                    user_obj = db.query(User).filter(User.id == user_id).first()
                    if user_obj:
                        from app.core.scheduler import get_user_eligibility_status
                        elig = get_user_eligibility_status(db, user_obj)
                        _elig_cache[user_id] = {
                            'is_eligible': elig.get('is_eligible', False),
                            'is_activated': elig.get('is_activated', False),
                            'kyc_approved': (elig.get('kyc_status', 'pending') or 'pending').lower() == 'approved',
                            'program_utilisation_completed': elig.get('program_utilisation_completed', False),
                            'group_a_ok': elig.get('group_a_points', 0) >= 1.0,
                            'group_b_ok': elig.get('group_b_points', 0) >= 1.0,
                        }
                    else:
                        _elig_cache[user_id] = None
                except Exception:
                    _elig_cache[user_id] = None
            user_elig_data = _elig_cache.get(user_id)
            
            eligibility_data.append({
                "user_id": user_id,
                "user_name": user_name,
                "bonanza_id": bonanza.id,
                "bonanza_name": bonanza.name,
                "reward_value": float(bonanza.reward_amount) if bonanza.reward_amount else 0.0,
                "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else 0.0,
                "award_name": bonanza.award_name,
                "is_monetary": bonanza.is_monetary,
                "criteria_type": bonanza.criteria_type,
                "target_requirement": bonanza.target_requirement,
                "current_progress": net_achieved_count,
                "achieved_count": net_achieved_count,
                "raw_achieved_count": raw_achieved_count,
                "is_eligible": net_achieved_count >= bonanza.target_requirement,
                "already_claimed": claim_status != 'unclaimed',
                "claim_status": claim_status,
                "claim_id": claim_id,
                "claimed_at": claimed_at.isoformat() if claimed_at else None,
                "delivery_status": delivery_status,
                "consume_achievements": bonanza.consume_achievements,
                "is_expired": is_expired,
                "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
                "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
                "eligibility_criteria": user_elig_data
            })
    
    # Return list of active bonanzas for filter dropdown (include award_name to distinguish same-name bonanzas)
    bonanza_list = [{
        "id": b.id,
        "name": b.name,
        "award_name": b.award_name,
        "criteria_type": b.criteria_type,
        "target_requirement": b.target_requirement
    } for b in active_bonanzas]
    
    return {
        "success": True,
        "total_records": len(eligibility_data),
        "eligibility_data": eligibility_data,
        "active_bonanzas": bonanza_list
    }


@router.get("/achievement-data/campaigns")
async def get_achievement_campaigns(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee) and not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Access restricted to MNR Members and Staff only")
    from app.services.bonanza_achievement_service import BonanzaAchievementService
    service = BonanzaAchievementService(db)
    campaigns = service.get_campaign_list()
    return {"success": True, "campaigns": campaigns}


@router.get("/achievement-data")
async def get_achievement_data(
    campaign_name: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee) and not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Access restricted to MNR Members and Staff only")
    from app.services.bonanza_achievement_service import BonanzaAchievementService
    service = BonanzaAchievementService(db)
    result = service.get_achievement_data(
        campaign_name=campaign_name,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        search=search
    )
    return result


@router.get("/achievement-data/summary")
async def get_achievement_summary(
    campaign_name: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee) and not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Access restricted to MNR Members and Staff only")
    from app.services.bonanza_achievement_service import BonanzaAchievementService
    service = BonanzaAchievementService(db)
    result = service.get_campaign_summary(
        campaign_name=campaign_name,
        date_from=date_from,
        date_to=date_to
    )
    return result


@router.get("/achievement-data/contributors")
async def get_achievement_contributors(
    campaign_name: str,
    user_id: str,
    achievement_type: str = "direct",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee) and not hasattr(current_user, 'id'):
        raise HTTPException(status_code=403, detail="Access restricted to MNR Members and Staff only")
    from app.services.bonanza_achievement_service import BonanzaAchievementService
    service = BonanzaAchievementService(db)
    result = service.get_achievement_contributors(
        campaign_name=campaign_name,
        user_id=user_id,
        achievement_type=achievement_type,
        date_from=date_from,
        date_to=date_to
    )
    return result



# ── DC Protocol: Deal-Progress Endpoints ─────────────────────────────────────

@router.get("/deal-progress")
def get_deal_progress(
    portal: str = "VGK",
    bonanza_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Staff/admin view: per-ID deal count vs target for deal-based bonanzas."""
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    # Get active deal-based bonanza for the portal
    query = db.query(Bonanza).filter(
        Bonanza.criteria_type == 'completed_deals',
        Bonanza.portal == portal,
        Bonanza.status.in_(['Active', 'Approved'])
    )
    if bonanza_id:
        query = query.filter(Bonanza.id == bonanza_id)
    bonanza = query.order_by(Bonanza.start_date.desc()).first()
    if not bonanza:
        return {"success": True, "bonanza": None, "progress": [], "message": "No active deal bonanza for this portal"}

    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    seg = bonanza.segment_id
    seg_clause = "AND revenue_category_id = :seg_id" if seg else ""
    params = {"start": bonanza.start_date, "end": bonanza.end_date, "grace": grace}
    if seg:
        params["seg_id"] = seg

    # DC Protocol: deal_date (won) within period + payment cleared + completed within grace
    rows = db.execute(text(f"""
        SELECT deal_source_id, COUNT(*) as deal_count
        FROM crm_lead_deals
        WHERE deal_source_id IS NOT NULL
          AND deal_date >= :start
          AND deal_date <= :end
          AND deal_value_balance = 0
          AND status = 'completed'
          AND close_date IS NOT NULL
          AND close_date <= :end + INTERVAL '1 day' * :grace
          {seg_clause}
        GROUP BY deal_source_id
        ORDER BY deal_count DESC
    """), params).fetchall()

    target = bonanza.target_requirement or 1
    progress = [
        {
            "member_id": r[0],
            "deal_count": int(r[1]),
            "target": target,
            "pct": round(min(int(r[1]) / target * 100, 100), 1),
            "qualified": int(r[1]) >= target
        }
        for r in rows
    ]
    return {
        "success": True,
        "bonanza": {
            "id": bonanza.id,
            "name": bonanza.name,
            "portal": bonanza.portal,
            "grace_days": grace,
            "target": target,
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat()
        },
        "progress": progress
    }


@router.get("/my-deal-progress")
def get_my_deal_progress(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Member view: own deal count vs target for the active deal bonanza matching their portal."""
    from app.models.staff import StaffEmployee
    from app.models.user import User as MNRUser
    from app.models.staff_accounts import OfficialPartner

    # Determine caller ID and portal
    if isinstance(current_user, MNRUser):
        caller_id = current_user.mnr_id or str(current_user.id)
        portal = 'MNR'
    elif isinstance(current_user, OfficialPartner):
        caller_id = current_user.partner_code or str(current_user.id)
        portal = 'VGK'
    elif isinstance(current_user, StaffEmployee):
        caller_id = current_user.emp_code or str(current_user.id)
        portal = 'MNR'
    else:
        raise HTTPException(status_code=403, detail="Unknown user type")

    bonanza = db.query(Bonanza).filter(
        Bonanza.criteria_type == 'completed_deals',
        Bonanza.portal == portal,
        Bonanza.status.in_(['Active', 'Approved'])
    ).order_by(Bonanza.start_date.desc()).first()

    if not bonanza:
        return {"success": True, "bonanza": None, "deal_count": 0, "target": 0, "qualified": False}

    grace = bonanza.grace_days if bonanza.grace_days is not None else 15
    target = bonanza.target_requirement or 1
    seg = bonanza.segment_id
    seg_clause = "AND revenue_category_id = :seg_id" if seg else ""
    params = {"cid": caller_id, "start": bonanza.start_date, "end": bonanza.end_date, "grace": grace}
    if seg:
        params["seg_id"] = seg

    row = db.execute(text(f"""
        SELECT COUNT(*) FROM crm_lead_deals
        WHERE deal_source_id = :cid
          AND deal_date >= :start
          AND deal_date <= :end
          AND deal_value_balance = 0
          AND status = 'completed'
          AND close_date IS NOT NULL
          AND close_date <= :end + INTERVAL '1 day' * :grace
          {seg_clause}
    """), params).scalar()

    count = int(row or 0)
    return {
        "success": True,
        "bonanza": {
            "id": bonanza.id,
            "name": bonanza.name,
            "portal": bonanza.portal,
            "grace_days": grace,
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat()
        },
        "deal_count": count,
        "target": target,
        "pct": round(min(count / target * 100, 100), 1),
        "qualified": count >= target
    }


# ── DC Protocol: VGK Staff-Exclusive Bonanza Endpoints ───────────────────────

VGK_STATUS_CHAIN = ['Pending', 'Staff Verified', 'Procurement In Progress', 'Dispatched', 'Delivered']


@router.get("/vgk/claims")
def list_vgk_bonanza_claims(
    bonanza_id: Optional[int] = None,
    processed_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff view of all VGK bonanza claims (BonanzaProgress with partner_id).
    5-step status chain: Pending → Staff Verified → Procurement In Progress → Dispatched → Delivered
    """
    from app.models.bonanza import BonanzaProgress
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    q = db.query(BonanzaProgress).filter(BonanzaProgress.partner_id.isnot(None))
    if bonanza_id:
        q = q.filter(BonanzaProgress.bonanza_id == bonanza_id)
    if processed_status:
        q = q.filter(BonanzaProgress.processed_status == processed_status)
    claims = q.order_by(BonanzaProgress.achieved_date.desc()).all()

    # Fetch bonanza and partner info
    bonanza_ids = list({c.bonanza_id for c in claims})
    partner_ids = list({c.partner_id for c in claims if c.partner_id})
    bonanza_map = {}
    if bonanza_ids:
        bz_rows = db.query(Bonanza).filter(Bonanza.id.in_(bonanza_ids)).all()
        bonanza_map = {b.id: b for b in bz_rows}

    # Fetch partner info from official_partners
    partner_map = {}
    if partner_ids:
        rows = db.execute(text("""
            SELECT id, partner_name, partner_code, phone, email
            FROM official_partners WHERE id = ANY(:ids)
        """), {"ids": partner_ids}).fetchall()
        partner_map = {r[0]: {"id": r[0], "name": r[1], "code": r[2], "phone": r[3], "email": r[4]} for r in rows}

    result = []
    for c in claims:
        bz = bonanza_map.get(c.bonanza_id)
        pt = partner_map.get(c.partner_id)
        # DC_VGK_SLAB_CLAIM_001: slab_wise uses solar advances, not crm_lead_deals
        # DC-BONANZA-FIRST-DVR-001 (Jul 2026): FIRST_DVR basis counts first-payment COMMISSION entries.
        # DC-CIBIL-DATE-OVERRIDE-001: award bonanzas with advance_count_basis != 'CIBIL' also use advance path
        if bz and pt:
            _admin_bz_basis = (getattr(bz, 'advance_count_basis', None) or 'CIBIL').upper()
            if _admin_bz_basis == 'FIRST_DVR':
                deal_count = _count_first_dvr_income_for_bonanza(db, c.partner_id, bz)
            elif _is_solar_award_dvr(db, bz):
                # DC-SOLAR-AWARD-DVR-001: award/gift + Solar + created ≥ 2026-07-01 → DVR stage
                deal_count = _count_solar_advances_for_bonanza(db, c.partner_id, bz, basis_override='DVR')
            elif bz.reward_type == 'slab_wise' or _admin_bz_basis != 'CIBIL':
                deal_count = _count_solar_advances_for_bonanza(db, c.partner_id, bz)
            else:
                deal_count = _count_vgk_completed_deals(db, pt["code"], bz)
        else:
            deal_count = c.current_progress or 0
        # Compute slab payout: slab_extra_amount × files qualified
        slab_extra = float(bz.slab_extra_amount) if bz and bz.slab_extra_amount else None
        slab_payout = (slab_extra * deal_count) if slab_extra and deal_count else None
        result.append({
            "claim_id": c.id,
            "bonanza_id": c.bonanza_id,
            "bonanza_name": bz.name if bz else None,
            "segment_id": bz.segment_id if bz else None,
            "partner_id": c.partner_id,
            "partner_name": pt["name"] if pt else None,
            "partner_code": pt["code"] if pt else None,
            "partner_phone": pt["phone"] if pt else None,
            "partner_email": pt["email"] if pt else None,
            "deal_count": deal_count,
            "target": bz.target_requirement if bz else None,
            "achievement_status": c.achievement_status,
            "processed_status": c.processed_status,
            "claimed_date": c.achieved_date.isoformat() if c.achieved_date else None,
            "processed_date": c.processed_date.isoformat() if c.processed_date else None,
            "reward_given": c.reward_given,
            "reward_type": bz.reward_type if bz else None,
            # DC_VGK_SLAB_CLAIM_001: for slab_wise reward_amount is null; expose slab fields
            "reward_amount": float(bz.reward_amount) if bz and bz.reward_amount else None,
            "slab_extra_amount": slab_extra,
            "slab_payout": slab_payout,
            "award_name": bz.award_name if bz else None,
            "notes": c.notes,
            "admin_notes": c.admin_notes,
            # DC-AWARD-TRIGGER-001: expose auto-trigger provenance
            "auto_triggered": bool(getattr(c, 'auto_triggered', False)),
            "trigger_event_source": getattr(c, 'trigger_event_source', None),
        })

    return {
        "success": True,
        "claims": result,
        "total": len(result),
        "status_chain": VGK_STATUS_CHAIN
    }


@router.get("/vgk/pending-payments")
def list_vgk_pending_payments(
    stage: str = Query('pending', description="pending = Pending claims; released = Payment Released claims awaiting Make Payment"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC_VGK_BONANZA_PAYMENTS_001: Staff endpoint — list monetary/slab bonanza claims by stage.
    stage=pending  → Pending claims  (Release button)
    stage=released → Payment Released claims (Make Payment button)
    """
    from app.models.bonanza import BonanzaProgress
    from app.models.staff import StaffEmployee
    from app.models.staff_accounts import OfficialPartner as _OP
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    _STAGE_MAP = {'pending': 'Pending', 'released': 'Payment Released', 'paid': 'Paid'}
    if stage in _STAGE_MAP:
        _where  = "bp.processed_status = :status_val"
        _params = {'status_val': _STAGE_MAP[stage]}
    else:  # 'all' → Payment Released + Paid (for unified income table)
        _where  = "bp.processed_status IN ('Payment Released', 'Paid')"
        _params = {}

    rows = db.execute(text(f"""
        SELECT
            bp.id                AS claim_id,
            bp.partner_id,
            bp.bonanza_id,
            bp.current_progress,
            bp.processed_status,
            bp.achieved_date,
            bp.payment_mode,
            bp.payment_reference,
            bp.finance_processed_at,
            bp.reward_given_date,
            b.name               AS bonanza_name,
            b.reward_type,
            b.slab_extra_amount,
            b.reward_amount,
            b.is_monetary,
            op.partner_name,
            op.partner_code,
            op.company_id        AS partner_company_id
        FROM bonanza_progress bp
        JOIN bonanza b      ON b.id  = bp.bonanza_id
        JOIN official_partners op ON op.id = bp.partner_id
        WHERE {_where}
          AND (b.is_monetary = true OR b.reward_type = 'slab_wise')
          AND NOT (
            b.reward_type = 'slab_wise'
            AND EXISTS (
              SELECT 1 FROM vgk_solar_cibil_advances a
              WHERE a.partner_id     = bp.partner_id
                AND a.slab_bonus_paid = TRUE
            )
          )
        ORDER BY bp.achieved_date DESC NULLS LAST, bp.id DESC
    """), _params).fetchall()

    result = []
    for r in rows:
        deal_count = r.current_progress or 1
        if r.reward_type == 'slab_wise' and r.slab_extra_amount:
            amount = float(r.slab_extra_amount) * deal_count
        else:
            amount = float(r.reward_amount or 0)
        result.append({
            "claim_id":           r.claim_id,
            "partner_id":         r.partner_id,
            "partner_name":       r.partner_name,
            "partner_code":       r.partner_code,
            "bonanza_id":         r.bonanza_id,
            "bonanza_name":       r.bonanza_name,
            "reward_type":        r.reward_type,
            "is_monetary":        r.is_monetary,
            # DC-SOLAR-CO-001: slab_wise bonanzas are triggered by solar advances → MyntReal
            "is_solar":           (r.reward_type == 'slab_wise'),
            "deal_count":         deal_count,
            "slab_extra_amount":  float(r.slab_extra_amount) if r.slab_extra_amount else None,
            "reward_amount":      float(r.reward_amount) if r.reward_amount else None,
            "amount":             amount,
            "processed_status":   r.processed_status,
            "achieved_date":      r.achieved_date.isoformat() if r.achieved_date else None,
            # Payment details (populated once staff records actual payment)
            "payment_mode":       r.payment_mode,
            "payment_reference":  r.payment_reference,
            "released_at":        r.finance_processed_at.isoformat() if r.finance_processed_at and r.processed_status == 'Payment Released' else None,
            "paid_at":            r.reward_given_date.isoformat() if r.reward_given_date else (r.finance_processed_at.isoformat() if r.processed_status == 'Paid' and r.finance_processed_at else None),
        })

    return {"success": True, "total": len(result), "claims": result, "stage": stage}


class VGKClaimStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    payment_mode: Optional[str] = None       # BANK / CASH / UPI
    payment_reference: Optional[str] = None  # UTR / reference number


@router.post("/vgk/claims/{claim_id}/status")
def update_vgk_claim_status(
    claim_id: int,
    data: VGKClaimStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff advances VGK bonanza claim through 5-step status chain.
    Chain: Pending → Staff Verified → Procurement In Progress → Dispatched → Delivered
    Staff can also set status to 'Rejected'.
    """
    from app.models.bonanza import BonanzaProgress
    from app.models.staff import StaffEmployee
    from app.models.base import get_indian_time
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    claim = db.query(BonanzaProgress).filter(BonanzaProgress.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="VGK bonanza claim not found")

    new_status = data.status

    # DC_BONANZA_PAYMENT_001: monetary/slab_wise bonanzas use a 3-step chain
    # Physical:  Pending → Staff Verified → Procurement In Progress → Dispatched → Delivered
    # Monetary:  Pending → Payment Released → Paid
    #   Payment Released = staff approved, awaiting actual cash/bank transfer
    #   Paid            = staff recorded payment (UTR/bank), wallet settled
    bz = db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
    is_monetary_bonanza = bool(bz and (bz.is_monetary or bz.reward_type == 'slab_wise'))
    _active_chain = ['Pending', 'Payment Released', 'Paid'] if is_monetary_bonanza else VGK_STATUS_CHAIN

    allowed = _active_chain + ['Rejected']
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {allowed}")

    # Forward-only chain enforcement (allow Rejected from any step)
    if new_status != 'Rejected' and claim.processed_status in _active_chain:
        current_idx = _active_chain.index(claim.processed_status)
        new_idx = _active_chain.index(new_status)
        if new_idx <= current_idx:
            raise HTTPException(status_code=400, detail=f"Cannot move claim back from '{claim.processed_status}' to '{new_status}'")

    claim.processed_status = new_status
    claim.processed_date = get_indian_time()
    claim.processed_by = getattr(current_user, 'emp_code', None) or str(current_user.id)
    if data.notes:
        claim.admin_notes = data.notes

    wallet_credited = False
    if new_status == 'Paid' and is_monetary_bonanza and bz:
        # DC_BONANZA_PAYMENT_002: staff recorded actual cash/bank payment → settle wallet
        # Flow: CR gross → DR 10% admin → DR net (cash payout) → wallet = 0, earned += net
        from app.models.vgk_wallet_transaction import VGKWalletTransaction
        from app.models.staff_accounts import OfficialPartner
        from decimal import Decimal as _D
        from datetime import timedelta
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == claim.partner_id).first()
        if partner:
            deal_count = claim.current_progress or 1
            if bz.reward_type == 'slab_wise' and bz.slab_extra_amount:
                gross = _D(str(round(float(bz.slab_extra_amount) * deal_count, 2)))
            else:
                gross = _D(str(float(bz.reward_amount or 0)))
            deduction   = (gross * _D('0.10')).quantize(_D('0.01'))
            net         = gross - deduction
            wb          = _D(str(float(partner.vgk_cash_wallet or 0)))
            wa_credit   = wb + gross
            wa_deducted = wa_credit - deduction
            wa_payout   = wa_deducted - net   # = wb (back to start, typically 0)
            desc_base   = (
                f"Bonanza reward: {bz.name} — "
                f"{deal_count} file(s) × ₹{float(bz.slab_extra_amount or bz.reward_amount or 0):,.0f}"
            )
            # 1. Gross credit
            db.add(VGKWalletTransaction(
                company_id=partner.company_id, partner_id=partner.id,
                txn_type='SLAB_BONUS_CREDIT', direction='CR',
                amount=gross, wallet_before=wb, wallet_after=wa_credit,
                ref_type='bonanza_progress', ref_id=claim.id,
                description=desc_base,
                initiated_by_staff_id=getattr(current_user, 'id', None),
            ))
            # 2. 10% admin deduction (hidden from member view, baked into deduction_amount)
            db.add(VGKWalletTransaction(
                company_id=partner.company_id, partner_id=partner.id,
                txn_type='SLAB_BONUS_PAYOUT', direction='DR',
                amount=deduction, wallet_before=wa_credit, wallet_after=wa_deducted,
                ref_type='bonanza_progress', ref_id=claim.id,
                description=f"Admin charges 10% — Bonanza: {bz.name}",
                initiated_by_staff_id=getattr(current_user, 'id', None),
            ))
            # 3. Cash payout DR — wallet → 0 (physical cash/bank paid to partner)
            pay_mode = data.payment_mode or 'BANK'
            pay_ref  = data.payment_reference or ''
            db.add(VGKWalletTransaction(
                company_id=partner.company_id, partner_id=partner.id,
                txn_type='BONANZA_CASH_PAYOUT', direction='DR',
                amount=net, wallet_before=wa_deducted, wallet_after=wa_payout,
                ref_type='bonanza_progress', ref_id=claim.id,
                description=f"Bonanza cash paid — {pay_mode} UTR:{pay_ref or 'N/A'}",
                initiated_by_staff_id=getattr(current_user, 'id', None),
            ))
            partner.vgk_cash_wallet = wa_payout
            earned_before = _D(str(float(getattr(partner, 'vgk_cash_earned_total', 0) or 0)))
            partner.vgk_cash_earned_total = earned_before + net
            # Store payment details on the claim
            if data.payment_mode:      claim.payment_mode      = data.payment_mode
            if data.payment_reference: claim.payment_reference  = data.payment_reference
            claim.finance_processed_by = getattr(current_user, 'emp_code', None) or str(current_user.id)
            claim.finance_processed_at = get_indian_time()
            # Mark qualifying solar advances as slab bonus paid
            if bz.reward_type == 'slab_wise' and bz.start_date and bz.end_date:
                grace_days = bz.grace_days or 0
                end_with_grace = (bz.end_date.date() + timedelta(days=grace_days)).isoformat()
                db.execute(text("""
                    UPDATE vgk_solar_cibil_advances
                       SET slab_bonus_paid   = true,
                           slab_bonus_amount = :amt
                     WHERE partner_id        = :pid
                       AND slab_bonus_paid   = false
                       AND status IN ('RELEASED','PENDING','ADJUSTED','RECOVERED','DEFICIT')
                       AND created_at::date BETWEEN :start AND :end_grace
                """), {
                    'amt':       float(bz.slab_extra_amount),
                    'pid':       claim.partner_id,
                    'start':     bz.start_date.date().isoformat(),
                    'end_grace': end_with_grace,
                })
            wallet_credited = True

            # DC-BONANZA-POINTS-001: Credit gross points, debit net points when cash is paid
            # Rule: +1 pt per ₹1 gross credited; then -net pts ("Points Utilised for Income")
            # Net effect on points balance = +deduction (10% retained as points bonus)
            try:
                from app.models.staff_accounts import VGKPointsLedger as _VPL
                _pts_gross = _D(str(int(round(float(gross)))))
                _pts_net   = _D(str(int(round(float(net)))))
                _pts_bal   = _D(str(float(partner.vgk_points_balance or 0)))
                _pts_after_cr = _pts_bal + _pts_gross
                _pts_after_dr = _pts_after_cr - _pts_net
                _now_pts      = get_indian_time()
                _staff_id     = getattr(current_user, 'id', None)
                db.add(_VPL(
                    partner_id=partner.id,
                    points_credit=_pts_gross, points_debit=_D('0'),
                    balance_after=_pts_after_cr,
                    reason_code='BONANZA_CASH_CREDIT',
                    reference_type='bonanza_progress', reference_id=claim.id,
                    notes=f'Bonanza gross credit — {bz.name}',
                    created_at=_now_pts, created_by=_staff_id,
                ))
                db.add(_VPL(
                    partner_id=partner.id,
                    points_credit=_D('0'), points_debit=_pts_net,
                    balance_after=_pts_after_dr,
                    reason_code='INCOME_EARNED',
                    reference_type='bonanza_progress', reference_id=claim.id,
                    notes=f'Bonanza net payout utilised — {bz.name}',
                    created_at=_now_pts, created_by=_staff_id,
                ))
                partner.vgk_points_balance = _pts_after_dr
            except Exception as _pts_e:
                print(f"[DC-BONANZA-POINTS-001] ⚠️ Points ledger error: {_pts_e}", flush=True)

    if new_status in ('Delivered', 'Paid'):
        claim.reward_given = True
        claim.reward_given_date = get_indian_time()

    # DC-AWARD-TRIGGER-001: at Rejected — release trigger log rows so next trigger can re-fire
    if new_status == 'Rejected' and claim.auto_triggered:
        try:
            from app.services.vgk_award_trigger import release_trigger_log_for_claim as _release_log
            _released = _release_log(db, claim_id)
            if _released:
                print(f"[DC-AWARD-TRIGGER-001] ♻️  Released {_released} trigger log rows for rejected claim #{claim_id}", flush=True)
        except Exception as _rel_e:
            print(f"[DC-AWARD-TRIGGER-001] ⚠️ Release trigger log error: {_rel_e}", flush=True)

    # DC-AWARD-TRIGGER-001: at Delivered for non-monetary auto-triggered award/gift
    # — debit net points (gross was credited at auto-claim creation)
    if new_status == 'Delivered' and claim.auto_triggered and bz and not bz.is_monetary:
        try:
            from app.models.staff_accounts import OfficialPartner as _OP
            from decimal import Decimal as _D
            _partner_pt = db.query(_OP).filter(_OP.id == claim.partner_id).first()
            if _partner_pt and bz.total_budget:
                _pts_gross = _D(str(int(round(float(bz.total_budget)))))
                _pts_net   = (_pts_gross * _D('0.90')).quantize(_D('1'))
                _pts_bal   = _D(str(float(_partner_pt.vgk_points_balance or 0)))
                _pts_after = _pts_bal - _pts_net
                _now_d     = get_indian_time()
                _staff_d   = getattr(current_user, 'id', None)
                from app.models.staff_accounts import VGKPointsLedger as _VPL2
                db.add(_VPL2(
                    partner_id=_partner_pt.id,
                    points_credit=_D('0'), points_debit=_pts_net,
                    balance_after=_pts_after,
                    reason_code='INCOME_EARNED',
                    reference_type='bonanza_progress', reference_id=claim.id,
                    notes=f'Award delivered — net pts utilised: {bz.award_name or bz.name}',
                    created_at=_now_d, created_by=_staff_d,
                ))
                _partner_pt.vgk_points_balance = _pts_after
        except Exception as _del_pts_e:
            print(f"[DC-AWARD-TRIGGER-001] ⚠️ Delivered points debit error: {_del_pts_e}", flush=True)

    db.commit()
    return {
        "success": True,
        "claim_id": claim_id,
        "new_status": new_status,
        "wallet_credited": wallet_credited,
        "message": (
            f"Payment released and ₹{float(gross):,.0f} credited to partner wallet."
            if wallet_credited else f"Claim status updated to '{new_status}'"
        )
    }


@router.get("/vgk/public/active-bonanzas")
def list_vgk_bonanzas_public(db: Session = Depends(get_db)):
    """DC Protocol: Public endpoint — active VGK bonanzas for the /voffers page. No auth required."""
    from datetime import datetime as _dt
    now = _dt.utcnow()
    bonanzas = db.query(Bonanza).filter(
        Bonanza.portal == 'VGK',
        Bonanza.is_deleted == False,
        Bonanza.status == 'Approved',
        Bonanza.start_date <= now,
        Bonanza.end_date >= now,
    ).order_by(Bonanza.end_date.asc()).all()

    seg_ids = list({b.segment_id for b in bonanzas if b.segment_id})
    seg_map = {}
    if seg_ids:
        rows = db.execute(text("SELECT id, name FROM signup_categories WHERE id = ANY(:ids)"),
                          {"ids": seg_ids}).fetchall()
        seg_map = {r[0]: r[1] for r in rows}

    result = []
    for b in bonanzas:
        result.append({
            "id": b.id,
            "name": b.name,
            "criteria_type": b.criteria_type,
            "target_requirement": b.target_requirement,
            "start_date": b.start_date.strftime("%d %b %Y") if b.start_date else None,
            "end_date": b.end_date.strftime("%d %b %Y") if b.end_date else None,
            "end_date_iso": b.end_date.isoformat() if b.end_date else None,
            "segment_name": seg_map.get(b.segment_id, "All Channel Partners") if b.segment_id else "All Channel Partners",
            "reward_type": b.reward_type,
            "is_monetary": b.is_monetary,
            "reward_amount": float(b.reward_amount) if b.reward_amount else None,
            "award_name": b.award_name,
            "reward_text": b.reward_text,
            "max_winners": b.max_winners,
            "registered_target_bonus": b.registered_target_bonus,
            "image_url": b.image_url,
        })
    return {"success": True, "count": len(result), "bonanzas": result}


@router.get("/vgk/all-bonanzas")
def list_vgk_bonanzas_staff(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff view of all VGK bonanzas with live progress summary.
    Used by vgk_bonanza_management.html.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    bonanzas = db.query(Bonanza).filter(
        Bonanza.portal == 'VGK',
        Bonanza.is_deleted == False,
    ).order_by(Bonanza.created_at.desc()).all()

    seg_ids = list({b.segment_id for b in bonanzas if b.segment_id})
    seg_map = {}
    if seg_ids:
        rows = db.execute(text("SELECT id, name FROM signup_categories WHERE id = ANY(:ids)"),
                          {"ids": seg_ids}).fetchall()
        seg_map = {r[0]: r[1] for r in rows}

    from app.models.bonanza import BonanzaProgress
    bonanza_ids = [b.id for b in bonanzas]
    claims_count = {}
    if bonanza_ids:
        rows = db.execute(text("""
            SELECT bonanza_id, processed_status, COUNT(*) as cnt
            FROM bonanza_progress WHERE bonanza_id = ANY(:ids) AND partner_id IS NOT NULL
            GROUP BY bonanza_id, processed_status
        """), {"ids": bonanza_ids}).fetchall()
        for row in rows:
            bid = row[0]
            if bid not in claims_count:
                claims_count[bid] = {}
            claims_count[bid][row[1]] = int(row[2])

    result = []
    for b in bonanzas:
        cc = claims_count.get(b.id, {})
        result.append({
            "id": b.id,
            "name": b.name,
            "status": b.status,
            "portal": b.portal,
            "criteria_type": b.criteria_type,
            "target_requirement": b.target_requirement,
            "start_date": b.start_date.isoformat() if b.start_date else None,
            "end_date": b.end_date.isoformat() if b.end_date else None,
            "grace_days": b.grace_days if b.grace_days is not None else 15,
            "segment_id": b.segment_id,
            "segment_name": seg_map.get(b.segment_id) if b.segment_id else "All Segments",
            "reward_type": b.reward_type,
            "is_monetary": b.is_monetary,
            "reward_amount": float(b.reward_amount) if b.reward_amount else None,
            "award_name": b.award_name,
            "reward_text": b.reward_text,
            # DC_BONANZA_SLABWISE_001
            "slab_extra_amount": float(b.slab_extra_amount) if b.slab_extra_amount else None,
            "slab_base_reference": float(b.slab_base_reference) if b.slab_base_reference else None,
            "slab_total_display": float((b.slab_base_reference or 0) + (b.slab_extra_amount or 0)) if b.slab_extra_amount else None,
            "max_winners": b.max_winners,
            "current_winners": b.current_winners or 0,
            "total_budget": float(b.total_budget) if b.total_budget else None,
            "registered_target_bonus": b.registered_target_bonus,
            "image_url": b.image_url,
            "claims_summary": cc,
            "total_claims": sum(cc.values()),
            "created_by": b.created_by
        })

    return {"success": True, "bonanzas": result, "total": len(result)}


@router.get("/segments")
def list_bonanza_segments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol: Return distinct signup_categories for VGK bonanza segment picker."""
    rows = db.execute(text(
        "SELECT DISTINCT ON (name) id, name FROM signup_categories ORDER BY name, id"
    )).fetchall()
    return {"success": True, "segments": [{"id": r[0], "name": r[1]} for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# DC Protocol (Apr 2026): T007 — Bonanza Slabs CRUD
# Multiple reward tiers per bonanza campaign (Bronze/Silver/Gold style)
# ─────────────────────────────────────────────────────────────────────────────

class BonanzaSlabCreate(BaseModel):
    slab_label: str
    slab_order: Optional[int] = 1
    target_from: int
    target_to: Optional[int] = None
    reward_type: str = 'cash'
    reward_amount: Optional[float] = None
    award_name: Optional[str] = None
    is_monetary: bool = True
    max_winners: Optional[int] = None
    budget_amount: Optional[float] = None
    is_active: bool = True
    image_url: Optional[str] = None

class BonanzaSlabUpdate(BaseModel):
    slab_label: Optional[str] = None
    slab_order: Optional[int] = None
    target_from: Optional[int] = None
    target_to: Optional[int] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[float] = None
    award_name: Optional[str] = None
    is_monetary: Optional[bool] = None
    max_winners: Optional[int] = None
    budget_amount: Optional[float] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None


@router.get("/{bonanza_id}/slabs")
async def list_bonanza_slabs(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol (Apr 2026): List all slabs for a given bonanza."""
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    slabs = db.query(BonanzaSlab).filter(
        BonanzaSlab.bonanza_id == bonanza_id
    ).order_by(BonanzaSlab.slab_order.asc(), BonanzaSlab.id.asc()).all()
    return {"success": True, "slabs": [s.to_dict() for s in slabs], "bonanza_id": bonanza_id}


@router.post("/{bonanza_id}/slabs")
async def create_bonanza_slab(
    bonanza_id: int,
    payload: BonanzaSlabCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol (Apr 2026): Add a new reward slab to a bonanza campaign."""
    from app.models.base import get_indian_time
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    if payload.reward_type not in ('cash', 'bonus', 'award', 'gift'):
        raise HTTPException(status_code=400, detail="Invalid reward_type. Use: cash, bonus, award, gift")
    if payload.is_monetary and payload.reward_amount is None:
        raise HTTPException(status_code=400, detail="reward_amount required for monetary reward type")
    if not payload.is_monetary and not payload.award_name:
        raise HTTPException(status_code=400, detail="award_name required for non-monetary reward type")
    slab = BonanzaSlab(
        bonanza_id=bonanza_id,
        slab_label=payload.slab_label.strip(),
        slab_order=payload.slab_order or 1,
        target_from=payload.target_from,
        target_to=payload.target_to,
        reward_type=payload.reward_type,
        reward_amount=payload.reward_amount,
        award_name=payload.award_name,
        is_monetary=payload.is_monetary,
        max_winners=payload.max_winners,
        budget_amount=payload.budget_amount,
        is_active=payload.is_active,
        image_url=payload.image_url,
        created_at=get_indian_time(),
        updated_at=get_indian_time(),
    )
    db.add(slab)
    db.commit()
    db.refresh(slab)
    return {"success": True, "message": "Slab created", "slab": slab.to_dict()}


@router.put("/{bonanza_id}/slabs/{slab_id}")
async def update_bonanza_slab(
    bonanza_id: int,
    slab_id: int,
    payload: BonanzaSlabUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol (Apr 2026): Update a bonanza reward slab."""
    from app.models.base import get_indian_time
    slab = db.query(BonanzaSlab).filter(BonanzaSlab.id == slab_id, BonanzaSlab.bonanza_id == bonanza_id).first()
    if not slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    if payload.slab_label is not None: slab.slab_label = payload.slab_label.strip()
    if payload.slab_order is not None: slab.slab_order = payload.slab_order
    if payload.target_from is not None: slab.target_from = payload.target_from
    if payload.target_to is not None: slab.target_to = payload.target_to
    if payload.reward_type is not None: slab.reward_type = payload.reward_type
    if payload.reward_amount is not None: slab.reward_amount = payload.reward_amount
    if payload.award_name is not None: slab.award_name = payload.award_name
    if payload.is_monetary is not None: slab.is_monetary = payload.is_monetary
    if payload.max_winners is not None: slab.max_winners = payload.max_winners
    if payload.budget_amount is not None: slab.budget_amount = payload.budget_amount
    if payload.is_active is not None: slab.is_active = payload.is_active
    if payload.image_url is not None: slab.image_url = payload.image_url
    slab.updated_at = get_indian_time()
    db.commit()
    db.refresh(slab)
    return {"success": True, "message": "Slab updated", "slab": slab.to_dict()}


@router.post("/{bonanza_id}/slabs/{slab_id}/upload-image")
async def upload_slab_image(
    bonanza_id: int,
    slab_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-SLAB-IMG-001: Upload a promo image for a specific slab."""
    from app.services.object_storage import storage_service
    import uuid as _uuid
    slab = db.query(BonanzaSlab).filter(BonanzaSlab.id == slab_id, BonanzaSlab.bonanza_id == bonanza_id).first()
    if not slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    allowed = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images allowed")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB")
    # DC_BONANZA_IMG_COMPRESS_001: compress to WebP before storage
    content, ext = _compress_bonanza_img(content, file.content_type or '')
    path = f"bonanza_images/slab_{slab_id}_{_uuid.uuid4().hex[:8]}.{ext}"
    try:
        storage_service.upload_file(path, content)
        img_url = f"/storage/{path}"
        slab.image_url = img_url
        db.commit()
        return {"success": True, "image_url": img_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/{bonanza_id}/slabs/{slab_id}")
async def delete_bonanza_slab(
    bonanza_id: int,
    slab_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol (Apr 2026): Delete a bonanza reward slab."""
    slab = db.query(BonanzaSlab).filter(BonanzaSlab.id == slab_id, BonanzaSlab.bonanza_id == bonanza_id).first()
    if not slab:
        raise HTTPException(status_code=404, detail="Slab not found")
    db.delete(slab)
    db.commit()
    return {"success": True, "message": "Slab deleted"}


@router.get("/{bonanza_id}/member-slabs")
async def get_member_bonanza_slabs(
    bonanza_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_vgk_partner_any)
):
    """DC Protocol (Apr 2026): Member view — list bonanza slabs with progress context."""
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id, Bonanza.is_deleted == False).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    slabs = db.query(BonanzaSlab).filter(
        BonanzaSlab.bonanza_id == bonanza_id,
        BonanzaSlab.is_active == True
    ).order_by(BonanzaSlab.slab_order.asc(), BonanzaSlab.id.asc()).all()
    return {
        "success": True,
        "bonanza_id": bonanza_id,
        "bonanza_name": bonanza.name,
        "criteria_type": bonanza.criteria_type,
        "slabs": [s.to_dict() for s in slabs],
        "has_slabs": len(slabs) > 0
    }


# ── DC-BACKFILL-SLAB-001 ──────────────────────────────────────────────────────
# One-time admin endpoint to retroactively apply slab bonus credits for Solar
# CIBIL advances that were released while the bonanza window check used the
# current timestamp (now) instead of advance.created_at.  After F4 is deployed
# the same apply_slab_bonus_if_active function is used — it now checks the
# advance's created_at against the bonanza window, so idempotent re-runs are safe.
# Protected: staff auth required (hierarchy check inside).
# ─────────────────────────────────────────────────────────────────────────────

class SlabBonusBackfillRequest(BaseModel):
    advance_ids: List[int]
    bonanza_progress_partner_ids: Optional[List[int]] = None  # create missing claims for these partners
    bonanza_id: Optional[int] = None  # required if bonanza_progress_partner_ids provided


@router.post("/admin/backfill-slab-bonus")
def admin_backfill_slab_bonus(
    payload: SlabBonusBackfillRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """
    DC-BACKFILL-SLAB-001: Retroactively applies slab bonus for given advance IDs.
    Uses the corrected apply_slab_bonus_if_active (DC-SLAB-WINDOW-001 — checks
    advance.created_at, not now).  Idempotent: slab_bonus_paid flag prevents
    double-credit.  Staff access only; skips advances already marked paid.
    """
    from app.models.staff_accounts import OfficialPartner
    from app.services.vgk_solar_advance import apply_slab_bonus_if_active

    # Allow staff users; block VGK partner tokens
    if isinstance(current_user, OfficialPartner):
        raise HTTPException(status_code=403, detail="Staff access only")

    results = []

    # ── F1/F2: slab bonus wallet credits ─────────────────────────────────────
    for adv_id in (payload.advance_ids or []):
        try:
            row = db.execute(text(
                "SELECT id, partner_id, entry_number, status, slab_bonus_paid "
                "FROM vgk_solar_cibil_advances WHERE id = :aid"
            ), {'aid': adv_id}).fetchone()

            if not row:
                results.append({'advance_id': adv_id, 'status': 'not_found'})
                continue

            if row.slab_bonus_paid:
                results.append({'advance_id': adv_id, 'entry': row.entry_number,
                                'status': 'already_paid', 'skipped': True})
                continue

            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == row.partner_id
            ).with_for_update().first()

            if not partner:
                results.append({'advance_id': adv_id, 'status': 'partner_not_found'})
                continue

            slab_result = apply_slab_bonus_if_active(db, partner, adv_id, row.entry_number)
            db.commit()

            results.append({
                'advance_id':   adv_id,
                'entry':        row.entry_number,
                'partner':      partner.partner_code,
                'status':       'credited' if slab_result.get('slab_applied') else 'skipped',
                'reason':       slab_result.get('reason'),
                'slab_amount':  slab_result.get('slab_amount'),
                'wallet_after': slab_result.get('wallet_after'),
            })
        except Exception as exc:
            db.rollback()
            results.append({'advance_id': adv_id, 'status': 'error', 'detail': str(exc)})

    # ── F3: create missing bonanza_progress claims ────────────────────────────
    claim_results = []
    if payload.bonanza_progress_partner_ids and payload.bonanza_id:
        bonanza = db.query(Bonanza).filter(
            Bonanza.id == payload.bonanza_id,
            Bonanza.is_deleted == False
        ).first()
        if not bonanza:
            claim_results.append({'error': f'Bonanza {payload.bonanza_id} not found'})
        else:
            for pid in payload.bonanza_progress_partner_ids:
                try:
                    existing = db.execute(text(
                        "SELECT id FROM bonanza_progress WHERE bonanza_id=:bid AND partner_id=:pid LIMIT 1"
                    ), {'bid': payload.bonanza_id, 'pid': pid}).fetchone()

                    if existing:
                        claim_results.append({'partner_id': pid, 'status': 'already_exists', 'id': existing.id})
                        continue

                    partner_row = db.execute(text(
                        "SELECT id, partner_name, partner_code FROM official_partners WHERE id=:pid"
                    ), {'pid': pid}).fetchone()

                    deal_count = db.execute(text("""
                        SELECT COUNT(*) FROM vgk_solar_cibil_advances
                        WHERE partner_id = :pid
                          AND created_at BETWEEN :s AND :e
                          AND status IN ('PENDING','RELEASED')
                    """), {
                        'pid': pid,
                        's':   bonanza.start_date,
                        'e':   bonanza.end_date
                    }).scalar() or 0

                    target = bonanza.target_requirement or 1
                    achieved = deal_count >= target
                    now_ist = datetime.utcnow()

                    db.execute(text("""
                        INSERT INTO bonanza_progress
                            (bonanza_id, partner_id, current_progress, achievement_status,
                             reward_given, processed_status, created_at, updated_at)
                        VALUES
                            (:bid, :pid, :prog, :ach,
                             FALSE, 'Pending', :now, :now)
                    """), {
                        'bid':  payload.bonanza_id,
                        'pid':  pid,
                        'prog': deal_count,
                        'ach':  'Achieved' if achieved else 'In Progress',
                        'now':  now_ist,
                    })
                    db.commit()
                    claim_results.append({
                        'partner_id':   pid,
                        'partner_code': partner_row.partner_code if partner_row else None,
                        'status':       'created',
                        'progress':     deal_count,
                        'achievement':  'Achieved' if achieved else 'In Progress',
                    })
                except Exception as exc:
                    db.rollback()
                    claim_results.append({'partner_id': pid, 'status': 'error', 'detail': str(exc)})

    return {
        "success": True,
        "advance_backfill": results,
        "claim_backfill":   claim_results,
    }


# ─── DC-VGK-MEMBER-TRACKING-001: Staff member-wise bonanza progress view ─────
@router.get("/vgk/member-tracking")
def vgk_member_tracking(
    bonanza_id: Optional[int] = None,
    partner_search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """
    DC-VGK-MEMBER-TRACKING-002 (rev3): Row-wise view — bonanzas as sections.
    Bonanzas with slabs (e.g. July offer) expand to one row per tier.
    FIRST_DVR counting uses crm_leads.associated_partner_id (lead owner).

    Response shape:
      rows: [{bonanza_id, slab_id, row_key, name, tier_label, has_slabs,
              target, basis, award_name, start_date, end_date,
              members: [{partner_id,partner_name,partner_code,achieved,gap,
                         is_eligible,claim_status}],
              eligible_count, total_members}]
      total_members, eligible_count
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    q = (db.query(Bonanza)
           .filter(Bonanza.portal == 'VGK',
                   Bonanza.is_deleted == False))
    if bonanza_id:
        q = q.filter(Bonanza.id == bonanza_id)
    bonanzas = q.order_by(Bonanza.created_at.desc()).all()
    if not bonanzas:
        return {"success": True, "rows": [], "total_members": 0, "eligible_count": 0}

    # DC-BONANZA-ALL-PARTNERS-001: Include ALL registered partners regardless of activation.
    # Non-activated (is_active=false) members use the same bonanza target.
    all_partner_rows = db.execute(text("""
        SELECT id, partner_name, partner_code
        FROM official_partners
        ORDER BY partner_name
    """)).fetchall()

    if partner_search:
        ps = partner_search.strip().lower()
        all_partner_rows = [
            r for r in all_partner_rows
            if ps in (r[1] or '').lower() or ps in (r[2] or '').lower()
        ]

    partner_ids = [r[0] for r in all_partner_rows]
    partner_map = {r[0]: {"name": r[1] or '—', "code": r[2] or '—'} for r in all_partner_rows}
    if not partner_ids:
        return {"success": True, "rows": [], "total_members": 0, "eligible_count": 0}

    all_eligible_set = set()
    track_rows = []

    for bz in bonanzas:
        grace = bz.grace_days if bz.grace_days is not None else 15
        basis = (getattr(bz, 'advance_count_basis', None) or 'CIBIL').upper()

        # ── Achieved count per partner for this bonanza ───────────────────────
        if basis == 'FIRST_DVR':
            # DC-BONANZA-FIRST-DVR-002: count CONFIRMED income_entries by income_date
            # (lead owner = associated_partner_id).  Replaces COMMISSION-entry approach.
            count_rows = db.execute(text("""
                SELECT cl.associated_partner_id, COUNT(DISTINCT ie.lead_id)
                FROM income_entries ie
                JOIN crm_leads cl ON cl.id = ie.lead_id
                WHERE cl.associated_partner_id = ANY(:pids)
                  AND ie.status = 'CONFIRMED'
                  AND ie.lead_id IS NOT NULL
                  AND ie.income_date >= :start
                  AND ie.income_date <= :end + INTERVAL '1 day' * :grace
                GROUP BY cl.associated_partner_id
            """), {'pids': partner_ids, 'start': bz.start_date,
                   'end': bz.end_date, 'grace': grace}).fetchall()
        else:
            # DC-BONANZA-FIRST-PMT-001: For CIBIL/DVR/BOTH basis bonanzas on solar segment,
            # count solar leads per partner where the ACTUAL first validated payment was received
            # within the bonanza window (first_payment_received_date from crm_lead_transactions).
            # Replaces the old crm_lead_deals query which had 0 solar deals in Jul 2026.
            seg        = bz.segment_id
            # DC-BONANZA-SOLAR-MULTICOMP-001: segment_id=6 is MyntReal's Solar category.
            # Across 4 companies solar appears as category_ids 6,19,36,48 (_SOLAR_CAT_IDS).
            # When segment matches any solar id, expand filter to ALL solar category ids so
            # leads from all companies are counted. Cast start/end to DATE (bonanza stores
            # timestamps; first_payment_received_date is DATE — 00:00:00 < 14:18:00 gap
            # would silently drop same-day leads otherwise).
            if seg and seg in _SOLAR_CAT_IDS:
                seg_clause = "AND cl.category_id = ANY(:seg_list)"
                params     = {'pids': partner_ids,
                              'start': bz.start_date,
                              'end': bz.end_date,
                              'grace': grace,
                              'seg_list': list(_SOLAR_CAT_IDS)}
            elif seg:
                seg_clause = "AND cl.category_id = :seg"
                params     = {'pids': partner_ids,
                              'start': bz.start_date,
                              'end': bz.end_date,
                              'grace': grace,
                              'seg': seg}
            else:
                seg_clause = ""
                params     = {'pids': partner_ids,
                              'start': bz.start_date,
                              'end': bz.end_date,
                              'grace': grace}
            # DC-BONANZA-SRC-REF-001 (Jul 2026): ground-source partners are stored as
            # source_ref_id (type vgk/vgk_partner/partner) when associated_partner_id
            # was never backfilled.  COALESCE makes both columns equally eligible so
            # Velaga Ramnath-type partners are counted even with NULL associated_partner_id.
            count_rows = db.execute(text(f"""
                SELECT COALESCE(
                    cl.associated_partner_id,
                    CASE WHEN cl.source_ref_type IN ('vgk','vgk_partner','partner')
                              AND cl.source_ref_id IS NOT NULL
                              AND cl.source_ref_id ~ '^[0-9]+$'
                         THEN cl.source_ref_id::int END
                ) AS partner_id,
                COUNT(DISTINCT cl.id)
                FROM crm_leads cl
                WHERE COALESCE(
                    cl.associated_partner_id,
                    CASE WHEN cl.source_ref_type IN ('vgk','vgk_partner','partner')
                              AND cl.source_ref_id IS NOT NULL
                              AND cl.source_ref_id ~ '^[0-9]+$'
                         THEN cl.source_ref_id::int END
                ) = ANY(:pids)
                  AND cl.first_payment_received_date IS NOT NULL
                  AND cl.first_payment_received_date >= CAST(:start AS DATE)
                  AND cl.first_payment_received_date <= CAST(:end AS DATE) + CAST(:grace || ' days' AS INTERVAL)
                  {seg_clause}
                GROUP BY partner_id
            """), params).fetchall()

        achieved_map = {r[0]: int(r[1]) for r in count_rows}

        # Claim statuses (bonanza level — no slab-level claim tracking)
        claim_rows = db.execute(text("""
            SELECT partner_id, processed_status FROM bonanza_progress
            WHERE bonanza_id = :bid AND partner_id = ANY(:pids)
        """), {'bid': bz.id, 'pids': partner_ids}).fetchall()
        claim_map = {r[0]: r[1] for r in claim_rows}

        # ── Tiers: base + slabs ───────────────────────────────────────────────
        slab_rows = db.execute(text("""
            SELECT id, target_from, award_name FROM bonanza_slabs
            WHERE bonanza_id = :bid AND is_active = true
            ORDER BY target_from
        """), {'bid': bz.id}).fetchall()

        base_target = bz.target_requirement or 1
        tiers = [{"slab_id": None, "target": base_target,
                  "award": bz.award_name or bz.reward_text or '', "tier_num": 1}]
        for i, sl in enumerate(slab_rows, start=2):
            tiers.append({"slab_id": sl[0], "target": sl[1],
                          "award": sl[2] or '', "tier_num": i})

        has_slabs = len(tiers) > 1

        for t in tiers:
            target = t["target"]
            if has_slabs:
                tier_label = f"Tier {t['tier_num']} · {t['award']} ({target} deals)"
            else:
                tier_label = None

            members_list = []
            elig_count   = 0
            for pid in partner_ids:
                achieved = achieved_map.get(pid, 0)
                gap      = max(0, target - achieved)
                is_elig  = achieved >= target
                if is_elig:
                    elig_count += 1
                    all_eligible_set.add(pid)
                members_list.append({
                    "partner_id":   pid,
                    "partner_name": partner_map[pid]["name"],
                    "partner_code": partner_map[pid]["code"],
                    "achieved":     achieved,
                    "gap":          gap,
                    "is_eligible":  is_elig,
                    "claim_status": claim_map.get(pid),
                })
            members_list.sort(key=lambda m: (-int(m["is_eligible"]), -m["achieved"]))

            row_key = f"bz_{bz.id}" + (f"_slab_{t['slab_id']}" if t["slab_id"] else "_base")
            track_rows.append({
                "bonanza_id":    bz.id,
                "slab_id":       t["slab_id"],
                "row_key":       row_key,
                "name":          bz.name,
                "tier_label":    tier_label,
                "has_slabs":     has_slabs,
                "target":        target,
                "basis":         basis,
                "award_name":    t["award"],
                "start_date":    bz.start_date.isoformat() if bz.start_date else None,
                "end_date":      bz.end_date.isoformat()   if bz.end_date   else None,
                "members":       members_list,
                "eligible_count": elig_count,
                "total_members":  len(members_list),
            })

    return {
        "success":        True,
        "rows":           track_rows,
        "total_members":  len(partner_ids),
        "eligible_count": len(all_eligible_set),
    }


# ─── DC-VGK-ADV-CAP-001: partner-facing advance cap status ───────────────────
@router.get("/my-advance-cap")
def my_advance_cap(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_vgk_partner_any),
):
    """
    DC-VGK-ADV-CAP-001: Returns this partner's 50% advance cap status.
    cap_limit = floor(eligible_leads × 0.5)
    eligible_leads = active solar leads where partner has ANY advance row.
    paid_advances = count of advances with kind IN ('ADVANCE','BRAND_ADVANCE')
                    and income_state = 'PAID'.
    """
    from app.services.vgk_advance_cap import get_cap_status
    partner_id = current_user.id
    company_id = getattr(current_user, 'company_id', 1)
    cap = get_cap_status(db, partner_id, company_id)
    return {"success": True, "cap_status": cap}
