"""
MyntOS Notification Outbox Service
Phase 7 Specification: Durable outbox queue, multi-vertical messaging templates, retries, and WhatsApp integration.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.reward_scratch import NotificationOutbox
from app.models.base import get_indian_time
from app.services.whatsapp_auto_service import send_direct_whatsapp

logger = logging.getLogger(__name__)


def build_recharge_scratch_message(
    brand: str,
    mobile_number: str,
    recharge_amount: float,
    transaction_id: int,
    scratch_card_url: str,
    verified_recharge_url: str
) -> str:
    """
    Format brand-specific multi-vertical recharge & scratch card confirmation message (Myntreal).
    """
    mob = mobile_number or ""
    masked_mobile = f"{mob[:2]}****{mob[-4:]}" if len(mob) >= 8 else mob
    brand_name = "Myntreal"

    msg = f"""🎉 *Recharge Successful!*

Thank you for recharging with *{brand_name}*.

📱 Mobile: {masked_mobile}
💰 Recharge Amount: ₹{int(recharge_amount)}
🔢 Transaction ID: TXN_{transaction_id}

🎁 *Your Scratch Card Is Ready!*

Open your secure scratch-card link to reveal your cash reward and claim it directly to your reward wallet:

👉 {scratch_card_url}

🌟 *Explore our services & verticals:*
☀️ Suryanz Solar — Rooftop solar solutions for home & commercial
⚡ Electric Mobility Solutions — High-performance smart electric scooters
🛠️ EVolution Training Centre — Technical EV 2-wheeler training
🛡️ VGK Care — Insurance & protection services
🏠 VGK Real Dreams — Premium verified real estate & properties
🌱 MNR — Applicable program benefits & Seva

📲 *Recharge again or recharge for your family & friends:*
👉 {verified_recharge_url}

*Warm Regards,*
*Team Myntreal*
🌐 www.myntreal.com"""

    return msg


def build_scratch_claim_ack_message(
    customer_name: str,
    mobile_number: str,
    amount_rupees: float,
    referral_code: Optional[str] = None,
    helpline_mobile: str = "+91 85858 52738"
) -> str:
    """
    Format personalized reward claim acknowledgment message with quick replies, referral link, and service discounts.
    """
    mob = mobile_number or ""
    masked_mobile = f"{mob[:2]}****{mob[-4:]}" if len(mob) >= 8 else mob
    name_clean = (customer_name or "").strip() or "Valued Customer"
    ref_param = f"?ref={referral_code}" if referral_code else ""
    referral_url = f"https://www.myntreal.com/recharge.html{ref_param}"

    msg = f"""🎉 *Congratulations, {name_clean}!*

Your scratch card cash reward of *₹{amount_rupees:.2f}* for your mobile recharge ({masked_mobile}) has been successfully claimed and credited! ✅

🌟 *Get Great Discounts on Our Services by Connecting with Us!*
As a valued Myntreal customer, you get special discounts across:
☀️ *Suryanz Solar* — Up to 90% power savings + ₹78,000 Govt. Subsidy
⚡ *Electric Mobility* — Smart EV 2-wheelers with festival discounts
🛠️ *EVolution Skill* — Certified EV technical courses & career training
🛡️ *VGK Care & Real Dreams* — Insurance protection & prime residential plots

💬 *Quick Reply — Tap or reply with your interest:*
1️⃣ *Interested in Solar*
2️⃣ *Interested in EV*
3️⃣ *Interested in Training*
4️⃣ *Interested in Insurance*

🎁 *Share & Earn 50% Cash Bonus!*
Share your personal link on WhatsApp Status & with friends:
👉 {referral_url}
When someone recharges via your link, *you get 50% of their scratch card reward* credited directly to your wallet (up to 5 friends)!

📞 *Helpline / WhatsApp:* {helpline_mobile}

*Warm Regards,*
*Team Myntreal*
🌐 www.myntreal.com"""

    return msg


TRUSTED_CANONICAL_DOMAINS = [
    "https://vgk4u.com",
    "https://www.vgk4u.com",
    "https://myntreal.com",
    "https://www.myntreal.com",
    "http://localhost:5000",
    "http://localhost:8000",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:8000"
]


def resolve_canonical_origin(brand: str = "Myntreal", origin_url: Optional[str] = None) -> str:
    """
    Task 4: Resolve trusted canonical origin domain preventing domain injection or token leaks.
    """
    if origin_url:
        clean_origin = origin_url.rstrip("/")
        if clean_origin in TRUSTED_CANONICAL_DOMAINS:
            return clean_origin

    return "https://www.vgk4u.com"


def enqueue_recharge_scratch_notification(
    db: Session,
    brand: str,
    mobile_number: str,
    recharge_amount: float,
    transaction_id: int,
    raw_secret_token: str,
    origin_url: Optional[str] = None
) -> NotificationOutbox:
    """
    Enqueue a notification event in the durable outbox queue.
    """
    base_url = resolve_canonical_origin(brand, origin_url)
    scratch_card_url = f"{base_url}/scratch-card.html?token={raw_secret_token}"
    verified_recharge_url = f"{base_url}/recharge"

    message_text = build_recharge_scratch_message(
        brand=brand or "Myntreal",
        mobile_number=mobile_number,
        recharge_amount=recharge_amount,
        transaction_id=transaction_id,
        scratch_card_url=scratch_card_url,
        verified_recharge_url=verified_recharge_url
    )

    payload = {
        "mobile_number": mobile_number,
        "recharge_amount": recharge_amount,
        "transaction_id": transaction_id,
        "scratch_card_url": scratch_card_url,
        "verified_recharge_url": verified_recharge_url,
        "message_text": message_text
    }

    outbox_entry = NotificationOutbox(
        event_type="RECHARGE_SCRATCH_CARD",
        destination_mobile=mobile_number,
        brand="Myntreal",
        payload_json=json.dumps(payload),
        status="PENDING",
        retry_count=0,
        created_at=get_indian_time()
    )

    db.add(outbox_entry)
    db.commit()
    db.refresh(outbox_entry)

    # Immediately attempt delivery in non-blocking try/except block
    try_process_outbox_entry(db, outbox_entry)

    return outbox_entry


def enqueue_scratch_claim_ack_notification(
    db: Session,
    customer_name: str,
    mobile_number: str,
    amount_rupees: float,
    scratch_card_id: int,
    referral_code: Optional[str] = None
) -> NotificationOutbox:
    """
    Enqueue reward claim acknowledgment message to customer via durable outbox.
    """
    message_text = build_scratch_claim_ack_message(
        customer_name=customer_name,
        mobile_number=mobile_number,
        amount_rupees=amount_rupees,
        referral_code=referral_code
    )

    payload = {
        "customer_name": customer_name,
        "mobile_number": mobile_number,
        "amount_rupees": amount_rupees,
        "scratch_card_id": scratch_card_id,
        "referral_code": referral_code,
        "message_text": message_text
    }

    outbox_entry = NotificationOutbox(
        event_type="RECHARGE_SCRATCH_CLAIM_ACK",
        destination_mobile=mobile_number,
        brand="Myntreal",
        payload_json=json.dumps(payload),
        status="PENDING",
        retry_count=0,
        created_at=get_indian_time()
    )

    db.add(outbox_entry)
    db.commit()
    db.refresh(outbox_entry)

    try_process_outbox_entry(db, outbox_entry)

    return outbox_entry


def build_scratch_referral_reward_message(
    referrer_name: str,
    referred_name: str,
    bonus_rupees: float,
    helpline_mobile: str = "+91 85858 52738"
) -> str:
    ref_name = (referrer_name or "").strip() or "Valued Partner"
    ref_friend = (referred_name or "").strip() or "Your friend"

    msg = f"""🎉 *Referral Cash Reward Earned, {ref_name}!*

Great news! {ref_friend} just claimed their Myntreal Recharge Scratch Card reward!

💰 You have received a *50% referral bonus of ₹{bonus_rupees:.2f}* directly in your Myntreal Wallet! ✅

Keep sharing your referral link to earn from up to 5 friends!

📞 *Helpline / WhatsApp:* {helpline_mobile}

*Warm Regards,*
*Team Myntreal*
🌐 www.myntreal.com"""
    return msg


def enqueue_scratch_referral_reward_notification(
    db: Session,
    referrer_name: str,
    referrer_mobile: str,
    referred_name: str,
    bonus_rupees: float,
    scratch_card_id: int
) -> NotificationOutbox:
    """
    Enqueue referral 50% bonus notification to the referrer via durable outbox.
    """
    message_text = build_scratch_referral_reward_message(
        referrer_name=referrer_name,
        referred_name=referred_name,
        bonus_rupees=bonus_rupees
    )

    payload = {
        "referrer_name": referrer_name,
        "referred_name": referred_name,
        "bonus_rupees": bonus_rupees,
        "scratch_card_id": scratch_card_id,
        "message_text": message_text
    }

    outbox_entry = NotificationOutbox(
        event_type="RECHARGE_SCRATCH_REFERRAL_BONUS",
        destination_mobile=referrer_mobile,
        brand="Myntreal",
        payload_json=json.dumps(payload),
        status="PENDING",
        retry_count=0,
        created_at=get_indian_time()
    )

    db.add(outbox_entry)
    db.commit()
    db.refresh(outbox_entry)

    try_process_outbox_entry(db, outbox_entry)

    return outbox_entry


def try_process_outbox_entry(db: Session, entry: NotificationOutbox, max_retries: int = 3) -> bool:
    """
    Process a single outbox entry with bounded retries and sanitized error reporting.
    """
    if entry.status == "SENT":
        return True

    if entry.retry_count >= max_retries:
        entry.status = "PERMANENTLY_FAILED"
        db.commit()
        return False

    try:
        payload = json.loads(entry.payload_json)
        phone = entry.destination_mobile
        message_text = payload.get("message_text", "")

        res = send_direct_whatsapp(db=db, phone=phone, message=message_text)

        entry.retry_count += 1
        entry.processed_at = get_indian_time()

        if res and res.get("status") == "success":
            entry.status = "SENT"
            entry.error_message = None
            db.commit()
            return True
        else:
            if entry.retry_count >= max_retries:
                entry.status = "PERMANENTLY_FAILED"
            else:
                entry.status = "FAILED"
            entry.error_message = str(res.get("message") if res else "WhatsApp API error")[:250]
            db.commit()
            return False

    except Exception as e:
        logger.error(f"Failed outbox delivery #{entry.id}: {e}")
        entry.retry_count += 1
        entry.processed_at = get_indian_time()
        if entry.retry_count >= max_retries:
            entry.status = "PERMANENTLY_FAILED"
        else:
            entry.status = "FAILED"
        entry.error_message = str(e)[:250]
        db.commit()
        return False


def process_pending_outbox_batch(db: Session, batch_size: int = 50, max_retries: int = 3) -> Dict[str, int]:
    """
    Task 2: Worker lifecycle processor for pending & retryable notification outbox events.
    Locks rows for atomic processing across concurrent workers.
    """
    entries = db.query(NotificationOutbox).filter(
        (NotificationOutbox.status == "PENDING") | 
        ((NotificationOutbox.status == "FAILED") & (NotificationOutbox.retry_count < max_retries))
    ).with_for_update(skip_locked=True).limit(batch_size).all()

    processed_count = 0
    success_count = 0
    failed_count = 0

    for entry in entries:
        processed_count += 1
        if try_process_outbox_entry(db, entry, max_retries=max_retries):
            success_count += 1
        else:
            failed_count += 1

    return {
        "processed": processed_count,
        "successful": success_count,
        "failed": failed_count
    }
