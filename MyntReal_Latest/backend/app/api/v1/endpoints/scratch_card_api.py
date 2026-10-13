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
    name: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    mobile_number: Optional[str] = None
    payout_method: Optional[str] = "upi_mobile"  # upi_mobile, upi_id, bank_account
    payout_upi_mobile: Optional[str] = None
    payout_upi_id: Optional[str] = None
    payout_bank_account: Optional[str] = None
    payout_bank_ifsc: Optional[str] = None
    payout_bank_name: Optional[str] = None


@router.get("/info/{token}")
def get_scratch_card_info(token: str, db: Session = Depends(get_db)):
    """
    Retrieve display information for a scratch card token, including revealed reward amount.
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
        "brand": "Myntreal",
        "masked_mobile": masked_mobile,
        "mobile_number": mob,
        "status": card.status,
        "expires_at": card.expires_at.isoformat(),
        "recharge_amount": card.recharge_transaction.amount if card.recharge_transaction else 0.0,
        "reward_amount_rupees": card.allocated_amount_paise / 100.0,
        "is_claimed": card.status == "CLAIMED",
        "customer_name": card.customer_name or "",
        "pincode": card.pincode or "",
        "city": card.city or "",
        "state": card.state or "",
        "payout_method": getattr(card, "payout_method", None) or "",
        "payout_upi_mobile": getattr(card, "payout_upi_mobile", None) or "",
        "payout_upi_id": getattr(card, "payout_upi_id", None) or "",
        "payout_bank_account": getattr(card, "payout_bank_account", None) or "",
        "payout_bank_ifsc": getattr(card, "payout_bank_ifsc", None) or "",
        "payout_status": getattr(card, "payout_status", None) or "PENDING",
        "referral_code": card.referral_code or f"MYNT{card.id:04d}",
        "referral_link": f"https://www.vgk4u.com/recharge?ref={card.referral_code or f'MYNT{card.id:04d}'}",
        "referral_bonus_pct": 50,
        "max_referred_members": 5
    }

    if card.status == "CLAIMED":
        response["revealed_amount_rupees"] = card.allocated_amount_paise / 100.0

    return response


@router.post("/claim")
def claim_scratch_card(req: ClaimScratchCardRequest, db: Session = Depends(get_db)):
    """
    Phase 5: Atomic Claim Execution with Lead Details (Name, PIN, City, State), Wallet Credit & 50% Referral Bonus
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
            ref_code = card.referral_code or f"MYNT{card.id:04d}"
            return {
                "status": "already_claimed",
                "message": "This scratch card has already been claimed.",
                "amount_rupees": card.allocated_amount_paise / 100.0,
                "amount_paise": card.allocated_amount_paise,
                "customer_name": card.customer_name,
                "claimed_at": card.claimed_at.isoformat() if card.claimed_at else None,
                "referral_code": ref_code,
                "referral_link": f"https://www.vgk4u.com/recharge?ref={ref_code}",
                "referral_bonus_pct": 50,
                "max_referred_members": 5
            }

        now = get_indian_time()
        if card.expires_at < now:
            card.status = "EXPIRED"
            db.commit()
            raise HTTPException(status_code=400, detail="This scratch card has expired.")

        if card.status != "ISSUED":
            raise HTTPException(status_code=400, detail=f"Scratch card cannot be claimed (status: {card.status}).")

        # Save Customer Details from Claim Form
        if req.name and req.name.strip():
            card.customer_name = req.name.strip()[:100]
        if req.mobile_number and req.mobile_number.strip():
            card.mobile_number = req.mobile_number.strip()[:20]
        if req.pincode and req.pincode.strip():
            card.pincode = req.pincode.strip()[:10]
        if req.city and req.city.strip():
            card.city = req.city.strip()[:100]
        if req.state and req.state.strip():
            card.state = req.state.strip()[:100]

        # Save Payout details for disbursement (UPI Mobile, UPI ID, or Bank Account)
        if req.payout_method:
            card.payout_method = req.payout_method.strip()[:50]
        if req.payout_upi_mobile:
            card.payout_upi_mobile = req.payout_upi_mobile.strip()[:20]
        if req.payout_upi_id:
            card.payout_upi_id = req.payout_upi_id.strip()[:100]
        if req.payout_bank_account:
            card.payout_bank_account = req.payout_bank_account.strip()[:50]
        if req.payout_bank_ifsc:
            card.payout_bank_ifsc = req.payout_bank_ifsc.strip()[:20].upper()
        if req.payout_bank_name:
            card.payout_bank_name = req.payout_bank_name.strip()[:100]
        card.payout_status = "PENDING"

        if card.recharge_transaction and card.customer_name:
            card.recharge_transaction.guest_name = card.customer_name

        # Ensure card has a referral_code
        if not card.referral_code:
            card.referral_code = f"MYNT{card.id:04d}"

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

        # ── 50% Referral Bonus Processing (Up to maximum 5 members) ─────────
        if card.referred_by_card_id and not card.referral_bonus_paid:
            try:
                referrer_card = db.query(ScratchCard).filter(ScratchCard.id == card.referred_by_card_id).first()
                if referrer_card and referrer_card.id != card.id:
                    # Count how many referral bonuses this referrer has already earned
                    paid_ref_count = db.query(ScratchCard).filter(
                        ScratchCard.referred_by_card_id == referrer_card.id,
                        ScratchCard.referral_bonus_paid == True
                    ).count()

                    if paid_ref_count < 5:
                        bonus_paise = card.allocated_amount_paise // 2 # 50% of referred member's scratch reward
                        # Check referral pool budget (₹500 / 50,000 paise pool)
                        ref_budget = getattr(campaign, 'referral_budget_paise', 50000) or 50000
                        ref_spent = getattr(campaign, 'referral_expenditure_paise', 0) or 0

                        if ref_spent + bonus_paise <= ref_budget:
                            ref_idempotency = f"SCRATCH_REF_BONUS_{referrer_card.id}_{card.id}"
                            existing_ref_ledger = db.query(RewardLedger).filter(
                                RewardLedger.idempotency_key == ref_idempotency
                            ).first()

                            if not existing_ref_ledger:
                                ref_user = db.query(User).filter(User.phone_number == referrer_card.mobile_number).first()
                                ref_user_id = ref_user.id if ref_user else None

                                ref_ledger = RewardLedger(
                                    scratch_card_id=card.id,
                                    mobile_number=referrer_card.mobile_number,
                                    user_id=ref_user_id,
                                    amount_paise=bonus_paise,
                                    transaction_type="SCRATCH_REFERRAL_BONUS",
                                    idempotency_key=ref_idempotency,
                                    created_at=now
                                )
                                db.add(ref_ledger)
                                db.flush()

                                if ref_user:
                                    ref_user.wallet_balance = float(ref_user.wallet_balance or 0.0) + (bonus_paise / 100.0)

                                if campaign:
                                    campaign.referral_expenditure_paise = ref_spent + bonus_paise

                                card.referral_bonus_paid = True
                                db.commit()

                                # Dispatch referral notification to referrer
                                try:
                                    from app.services.notification_outbox_service import enqueue_scratch_referral_reward_notification
                                    enqueue_scratch_referral_reward_notification(
                                        db=db,
                                        referrer_name=referrer_card.customer_name or "Valued Partner",
                                        referrer_mobile=referrer_card.mobile_number,
                                        referred_name=card.customer_name or "Your friend",
                                        bonus_rupees=bonus_paise / 100.0,
                                        scratch_card_id=card.id
                                    )
                                except Exception as ref_notify_err:
                                    print(f"Scratch referral notify error: {ref_notify_err}")
            except Exception as ref_err:
                print(f"[SCRATCH-CLAIM] Referral processing error: {ref_err}")

        amount_in_rs = card.allocated_amount_paise / 100.0

        # Dispatch WhatsApp claim acknowledgment message
        try:
            from app.services.notification_outbox_service import enqueue_scratch_claim_ack_notification
            enqueue_scratch_claim_ack_notification(
                db=db,
                customer_name=card.customer_name or "Valued Customer",
                mobile_number=card.mobile_number,
                amount_rupees=amount_in_rs,
                scratch_card_id=card.id,
                referral_code=card.referral_code
            )
        except Exception as notify_err:
            print(f"Scratch claim ack notify error: {notify_err}")

        ref_code = card.referral_code or f"MYNT{card.id:04d}"
        return {
            "status": "success",
            "message": f"Congratulations {card.customer_name or ''}! You claimed ₹{amount_in_rs:.2f}!",
            "amount_rupees": amount_in_rs,
            "amount_paise": card.allocated_amount_paise,
            "customer_name": card.customer_name,
            "claimed_at": card.claimed_at.isoformat() if card.claimed_at else now.isoformat(),
            "mobile_number": card.mobile_number,
            "pincode": card.pincode,
            "payout_method": card.payout_method,
            "payout_upi_mobile": card.payout_upi_mobile,
            "payout_upi_id": card.payout_upi_id,
            "payout_bank_account": card.payout_bank_account,
            "payout_bank_ifsc": card.payout_bank_ifsc,
            "payout_status": card.payout_status,
            "referral_code": ref_code,
            "referral_link": f"https://www.vgk4u.com/recharge?ref={ref_code}",
            "referral_bonus_pct": 50,
            "max_referred_members": 5
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to claim scratch card: {str(e)}")


class ScratchInterestRequest(BaseModel):
    token: str
    category: str # "Solar", "EV", "Training", "Insurance"
    customer_name: Optional[str] = None
    mobile_number: Optional[str] = None


@router.post("/interest")
def register_scratch_interest(req: ScratchInterestRequest, db: Session = Depends(get_db)):
    """
    Direct endpoint for customer to express interest in ecosystem services (Solar, EV, Training, Insurance)
    from the scratch card page or quick replies. Automatically creates a CRMLead with source='Recharge'.
    """
    if not req.token:
        raise HTTPException(status_code=400, detail="Token is required.")

    token_hash = ScratchCard.hash_token(req.token)
    card = db.query(ScratchCard).filter(ScratchCard.token_hash == token_hash).first()

    phone = (card.mobile_number if card else None) or req.mobile_number
    if not phone:
        raise HTTPException(status_code=400, detail="Mobile number not associated with token.")

    clean_digits = ''.join(filter(str.isdigit, str(phone)))
    phone_10 = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits

    cat = (req.category or "").strip()
    title_map = {
        "Solar": "Suryanz Solar (Rooftop Solar & Subsidy)",
        "EV": "Electric Mobility (Clean 2W/3W EVs)",
        "Training": "EVolution Skill (EV Technical Training)",
        "Insurance": "VGK Care (Insurance Protection)"
    }
    title = title_map.get(cat, f"{cat} Services")

    from app.models.crm import CRMLead
    from datetime import timedelta

    name = (card.customer_name if card and card.customer_name else None) or req.customer_name or "Recharge Customer"
    city = card.city if card else None
    state = card.state if card else None
    pincode = card.pincode if card else None

    # Check recent lead created in the last 24h for this category
    cutoff = datetime.utcnow() - timedelta(hours=24)
    existing = db.query(CRMLead).filter(
        CRMLead.phone == phone_10,
        CRMLead.source == "Recharge",
        CRMLead.looking_for == cat,
        CRMLead.created_at >= cutoff
    ).first()

    if existing:
        return {
            "status": "success",
            "message": f"Interest in {cat} already recorded. Our team will contact you shortly!",
            "lead_id": existing.id
        }

    lead = CRMLead(
        company_id=1,
        name=name,
        phone=phone_10,
        phone_primary_whatsapp=True,
        source="Recharge",
        source_details=f"Scratch Card Web Interest: {title}",
        looking_for=cat,
        requirements=f"Customer registered interest in {title} on Scratch Card Claim page.",
        status="New",
        city=city,
        state=state,
        pincode=pincode,
        created_at=datetime.utcnow()
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "status": "success",
        "message": f"Thank you! Our {cat} specialist will connect with you on {phone_10} with exclusive discounts.",
        "lead_id": lead.id
    }


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

