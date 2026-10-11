"""
MyntOS Reward & Scratch Card Allocation Service
Phase 2 & Phase 4 Implementation: Eligibility verification, dynamic budget balancer, integer paise calculations, and cryptographically secure token generation.
"""

import hashlib
import secrets
import random
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.recharge import RechargeTransaction
from app.models.reward_scratch import RewardCampaign, ScratchCard, RewardLedger, NotificationOutbox
from app.models.base import get_indian_time


def get_or_create_active_campaign(db: Session) -> RewardCampaign:
    """
    Fetch the currently active campaign or bootstrap default 100-card ₹1,000 budget campaign (Model A).
    """
    campaign = db.query(RewardCampaign).filter(RewardCampaign.is_active == True).first()
    if not campaign:
        campaign = RewardCampaign(
            campaign_name="Myntreal Recharge Rewards",
            is_active=True,
            total_budget_paise=100000, # ₹1,000.00
            max_cards=100,
            max_ten_rupee_count=6, # Max 6 cards carrying ₹25 Jackpot (6%)
            min_reward_paise=300, # ₹3.00
            max_standard_reward_paise=1500, # ₹15.00
            expiry_days=7
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
    return campaign


def allocate_scratch_card(
    db: Session,
    recharge_tx: RechargeTransaction,
    brand: str = "Myntreal"
) -> Tuple[Optional[ScratchCard], Optional[str], bool]:
    """
    Phase 2 & Phase 4: Atomic Scratch Card Allocation Engine (Model A: ₹3 to ₹25)
    
    Returns:
        (scratch_card_obj, raw_secret_token, is_newly_issued)
    """
    # 1. Eligibility Check (Phase 2)
    # Must be Paid AND Success
    if recharge_tx.payment_status != "Paid" or recharge_tx.api_status != "Success":
        return None, None, False

    # Idempotency Check: Existing Card for this Transaction?
    existing_card = db.query(ScratchCard).filter(
        ScratchCard.recharge_transaction_id == recharge_tx.id
    ).first()
    if existing_card:
        # Card already issued for this recharge. Return existing without re-issuing or re-allocating.
        return existing_card, None, False

    # 2. Lock Active Campaign for atomic allocation (Phase 4)
    campaign = get_or_create_active_campaign(db)
    
    # Refresh/Lock campaign row
    campaign = db.query(RewardCampaign).filter(RewardCampaign.id == campaign.id).with_for_update().first()

    # Check card capacity limit
    if campaign.issued_cards_count >= campaign.max_cards:
        return None, None, False

    # Calculate available budget = total - reserved liability - settled expenditure
    available_budget = campaign.total_budget_paise - campaign.reserved_liability_paise - campaign.settled_expenditure_paise
    remaining_cards = campaign.max_cards - campaign.issued_cards_count

    # Minimum budget required to give at least min_reward_paise to all remaining cards
    required_min_for_others = (remaining_cards - 1) * campaign.min_reward_paise
    max_allocatable_for_this = available_budget - required_min_for_others

    if max_allocatable_for_this < campaign.min_reward_paise:
        # Cannot satisfy ₹3 minimum for all remaining cards within budget
        return None, None, False

    # 3. Allocation Math Rules (Tiered by Recharge Amount + Model A)
    # Tier 1: Below ₹100 recharge -> Max reward is strictly ₹5.00 (500 paise)
    is_sub_hundred = float(recharge_tx.amount or 0.0) < 100.0

    if is_sub_hundred:
        max_sub_hundred = min(500, max_allocatable_for_this)
        valid_options = [amt for amt in [300, 400, 500] if amt <= max_sub_hundred]
        if valid_options:
            reward_amount_paise = random.choice(valid_options)
        else:
            reward_amount_paise = min(campaign.min_reward_paise, 500)
    else:
        # Tier 2 & 3: ₹100 and above
        # Check if ₹25 (2500 paise) Jackpot is eligible:
        # - Max 6 out of 100 cards (6%)
        # - Less than 8% of issued cards so far
        # - Budget permits ₹25 while leaving enough for remaining cards
        can_award_jackpot = (
            campaign.issued_ten_rupee_count < 6 and
            (campaign.issued_ten_rupee_count + 1) / float(campaign.issued_cards_count + 1) <= 0.08 and
            max_allocatable_for_this >= 2500
        )

        # 10% probability roll for ₹25 jackpot if eligible
        if can_award_jackpot and random.random() < 0.10:
            reward_amount_paise = 2500 # ₹25.00
            campaign.issued_ten_rupee_count += 1
        else:
            # Standard rewards ₹3 to ₹15 (300, 500, 700, 1000, 1200, 1500 paise)
            max_standard = min(campaign.max_standard_reward_paise, max_allocatable_for_this)
            valid_options = [amt for amt in [300, 500, 700, 1000, 1200, 1500] if amt <= max_standard]
            if valid_options:
                reward_amount_paise = random.choice(valid_options)
            else:
                reward_amount_paise = campaign.min_reward_paise

    # 4. Update Campaign Liabilities
    campaign.issued_cards_count += 1
    campaign.reserved_liability_paise += reward_amount_paise

    # 5. Generate Secure Token, Hash, and Referral Code
    raw_secret_token = secrets.token_urlsafe(32)
    token_hash = ScratchCard.hash_token(raw_secret_token)
    ref_code = f"MYNT{secrets.token_hex(3).upper()}"

    # Check if this recharge was referred by another scratch card user
    referred_by_card_id = None
    ref_val = getattr(recharge_tx, "referred_by", None)
    if ref_val and str(ref_val).strip():
        ref_val_clean = str(ref_val).strip().upper()
        try:
            ref_card = db.query(ScratchCard).filter(
                ScratchCard.referral_code == ref_val_clean
            ).first()
            if not ref_card and ref_val_clean.isdigit():
                ref_card = db.query(ScratchCard).filter(ScratchCard.id == int(ref_val_clean)).first()
            if ref_card and ref_card.mobile_number != recharge_tx.mobile_number:
                referred_by_card_id = ref_card.id
        except Exception as ref_err:
            print(f"[SCRATCH-ALLOC] Referral resolve warning: {ref_err}")

    now = get_indian_time()
    expires_at = now + timedelta(days=campaign.expiry_days)

    # 6. Create ScratchCard entity
    new_card = ScratchCard(
        campaign_id=campaign.id,
        recharge_transaction_id=recharge_tx.id,
        mobile_number=recharge_tx.mobile_number,
        brand=brand or "Myntreal",
        referral_code=ref_code,
        referred_by_card_id=referred_by_card_id,
        referral_bonus_paid=False,
        token_hash=token_hash,
        allocated_amount_paise=reward_amount_paise,
        status="ISSUED",
        created_at=now,
        expires_at=expires_at
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    return new_card, raw_secret_token, True
