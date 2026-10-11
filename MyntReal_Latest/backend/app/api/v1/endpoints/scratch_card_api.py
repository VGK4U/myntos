"""
MyntOS Scratch Card API Endpoints
Phase 5 Implementation: Atomic claim validation, token hashing, idempotency, guest wallet balance updates, and safe display info.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.reward_scratch import RewardCampaign, ScratchCard, RewardLedger
from app.models.recharge import RechargeTransaction
from app.models.user import User
from app.models.base import get_indian_time
import hashlib

router = APIRouter()


def enforce_staff_admin_access(current_user):
    """
    Task 1: RBAC check enforcing administrative privileges for scratch card management.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    is_authorized = False
    if current_user.emp_code in ["MR10001", "MR10002", "SUPERADMIN"]:
        is_authorized = True
    elif getattr(current_user, "department", None) and current_user.department.name in ["Accounts", "Admin", "Management"]:
        is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Access denied. Requires administrative privileges.")


class ClaimScratchCardRequest(BaseModel):
    token: str
    mobile_number: Optional[str] = None


@router.get("/info/{token}")
def get_scratch_card_info(token: str, db: Session = Depends(get_db)):
    """
    Retrieve safe display information for a scratch card token without revealing the un-scratched amount.
    """
    token_hash = ScratchCard.hash_token(token)
    card = db.query(ScratchCard).filter(ScratchCard.token_hash == token_hash).first()

    if not card:
        raise HTTPException(status_code=404, detail="Invalid scratch card token.")

    now = get_indian_time()
    if card.status == "ISSUED" and card.expires_at < now:
        card.status = "EXPIRED"
        db.commit()

    # Mask mobile number for privacy (e.g. 98****3210)
    mob = card.mobile_number or ""
    masked_mobile = f"{mob[:2]}****{mob[-4:]}" if len(mob) >= 8 else mob

    response = {
        "valid": True,
        "brand": card.brand or "Zynova Mobility",
        "masked_mobile": masked_mobile,
        "status": card.status,
        "expires_at": card.expires_at.isoformat(),
        "recharge_amount": card.recharge_transaction.amount if card.recharge_transaction else 0.0,
        "is_claimed": card.status == "CLAIMED"
    }

    # Only expose revealed amount if already claimed
    if card.status == "CLAIMED":
        response["revealed_amount_rupees"] = card.allocated_amount_paise / 100.0

    return response


@router.post("/claim")
def claim_scratch_card(req: ClaimScratchCardRequest, db: Session = Depends(get_db)):
    """
    Phase 5: Atomic Claim Execution & Wallet Credit
    """
    if not req.token:
        raise HTTPException(status_code=400, detail="Token is required.")

    token_hash = ScratchCard.hash_token(req.token)

    # Begin atomic row-locking operation
    try:
        card = db.query(ScratchCard).filter(
            ScratchCard.token_hash == token_hash
        ).with_for_update().first()

        if not card:
            raise HTTPException(status_code=404, detail="Invalid scratch card token.")

        # Check if already claimed
        if card.status == "CLAIMED":
            return {
                "status": "already_claimed",
                "message": "This scratch card has already been claimed.",
                "amount_rupees": card.allocated_amount_paise / 100.0,
                "amount_paise": card.allocated_amount_paise,
                "claimed_at": card.claimed_at.isoformat() if card.claimed_at else None
            }

        now = get_indian_time()
        if card.expires_at < now:
            card.status = "EXPIRED"
            db.commit()
            raise HTTPException(status_code=400, detail="This scratch card has expired.")

        if card.status != "ISSUED":
            raise HTTPException(status_code=400, detail=f"Scratch card cannot be claimed (status: {card.status}).")

        # Campaign updates
        campaign = db.query(RewardCampaign).filter(
            RewardCampaign.id == card.campaign_id
        ).with_for_update().first()

        if campaign:
            campaign.reserved_liability_paise = max(0, campaign.reserved_liability_paise - card.allocated_amount_paise)
            campaign.settled_expenditure_paise += card.allocated_amount_paise

        # Idempotency key for reward ledger
        idempotency_key = f"SCRATCH_CLAIM_{card.id}_{card.recharge_transaction_id}"
        existing_ledger = db.query(RewardLedger).filter(RewardLedger.idempotency_key == idempotency_key).first()

        if not existing_ledger:
            # Check if customer has registered User account
            user = db.query(User).filter(User.phone_number == card.mobile_number).first()
            user_id = user.id if user else None

            # Create RewardLedger entry
            ledger = RewardLedger(
                scratch_card_id=card.id,
                mobile_number=card.mobile_number,
                user_id=user_id,
                amount_paise=card.allocated_amount_paise,
                transaction_type="SCRATCH_REWARD_CREDIT",
                idempotency_key=idempotency_key,
                created_at=now
            )
            db.add(ledger)
            db.flush()

            # Credit User wallet if registered
            if user:
                user.wallet_balance = float(user.wallet_balance or 0.0) + (card.allocated_amount_paise / 100.0)

            card.status = "CLAIMED"
            card.claimed_at = now
            card.wallet_ledger_id = ledger.id
            db.commit()

        amount_in_rs = card.allocated_amount_paise / 100.0

        return {
            "status": "success",
            "message": f"Congratulations! You won ₹{amount_in_rs:.2f}!",
            "amount_rupees": amount_in_rs,
            "amount_paise": card.allocated_amount_paise,
            "claimed_at": card.claimed_at.isoformat() if card.claimed_at else now.isoformat(),
            "mobile_number": card.mobile_number
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to claim scratch card: {str(e)}")


# ── PHASE 10: ADMINISTRATIVE CONTROLS & RECONCILIATION ────────────────────────

class ConfigureCampaignRequest(BaseModel):
    campaign_name: str
    total_budget_rupees: float # e.g. 500.0
    max_cards: int # e.g. 100
    max_ten_rupee_count: Optional[int] = 9
    min_reward_rupees: Optional[float] = 1.0
    max_standard_reward_rupees: Optional[float] = 5.0
    expiry_days: Optional[int] = 7
    is_active: Optional[bool] = True


@router.get("/admin/campaign/summary")
def get_campaign_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    Task 1: View active campaign metrics, budget liability, and expenditure.
    Enforces staff administrative RBAC.
    """
    enforce_staff_admin_access(current_user)

    from app.services.scratch_reward_service import get_or_create_active_campaign
    campaign = get_or_create_active_campaign(db)

    total_budget = campaign.total_budget_paise / 100.0
    reserved = campaign.reserved_liability_paise / 100.0
    settled = campaign.settled_expenditure_paise / 100.0
    available = (campaign.total_budget_paise - campaign.reserved_liability_paise - campaign.settled_expenditure_paise) / 100.0

    claimed_cards = db.query(ScratchCard).filter(
        ScratchCard.campaign_id == campaign.id,
        ScratchCard.status == "CLAIMED"
    ).count()

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.campaign_name,
        "is_active": campaign.is_active,
        "budget": {
            "total_budget_rupees": round(total_budget, 2),
            "reserved_liability_rupees": round(reserved, 2),
            "settled_expenditure_rupees": round(settled, 2),
            "available_budget_rupees": round(available, 2)
        },
        "cards": {
            "max_cards": campaign.max_cards,
            "issued_cards_count": campaign.issued_cards_count,
            "claimed_cards_count": claimed_cards,
            "remaining_cards": campaign.max_cards - campaign.issued_cards_count,
            "issued_ten_rupee_count": campaign.issued_ten_rupee_count,
            "max_ten_rupee_count": campaign.max_ten_rupee_count
        }
    }


@router.post("/admin/campaign")
def configure_campaign(
    req: ConfigureCampaignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    Task 1: Create or update a campaign configuration with strict input validation.
    Enforces staff administrative RBAC.
    """
    enforce_staff_admin_access(current_user)

    if req.total_budget_rupees <= 0:
        raise HTTPException(status_code=400, detail="Total budget must be greater than zero.")
    if req.max_cards <= 0:
        raise HTTPException(status_code=400, detail="Max cards must be greater than zero.")
    
    max_ten = req.max_ten_rupee_count if req.max_ten_rupee_count is not None else 9
    if max_ten < 0 or max_ten > (req.max_cards * 0.10 + 0.001):
        raise HTTPException(status_code=400, detail="Max ₹10 rewards cannot exceed 10% of total cards.")

    min_rew = req.min_reward_rupees or 1.0
    max_std = req.max_standard_reward_rupees or 5.0
    if min_rew < 1.0 or max_std < min_rew:
        raise HTTPException(status_code=400, detail="Invalid reward distribution bounds. Minimum reward must be >= ₹1.")

    campaign = db.query(RewardCampaign).filter(RewardCampaign.is_active == True).first()
    if not campaign:
        campaign = RewardCampaign()
        db.add(campaign)

    campaign.campaign_name = req.campaign_name
    campaign.total_budget_paise = int(req.total_budget_rupees * 100)
    campaign.max_cards = req.max_cards
    campaign.max_ten_rupee_count = max_ten
    campaign.min_reward_paise = int(min_rew * 100)
    campaign.max_standard_reward_paise = int(max_std * 100)
    campaign.expiry_days = req.expiry_days or 7
    campaign.is_active = req.is_active if req.is_active is not None else True

    db.commit()
    db.refresh(campaign)

    return {
        "status": "success",
        "message": f"Campaign '{campaign.campaign_name}' configured successfully.",
        "campaign_id": campaign.id
    }


@router.get("/admin/outbox")
def list_notification_outbox(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    Task 1: List notification outbox entries and delivery status.
    Enforces staff administrative RBAC.
    """
    enforce_staff_admin_access(current_user)

    from app.models.reward_scratch import NotificationOutbox
    query = db.query(NotificationOutbox)
    if status:
        query = query.filter(NotificationOutbox.status == status)

    entries = query.order_by(NotificationOutbox.created_at.desc()).limit(50).all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "destination_mobile": e.destination_mobile,
            "brand": e.brand,
            "status": e.status,
            "retry_count": e.retry_count,
            "error_message": e.error_message,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None
        } for e in entries
    ]

