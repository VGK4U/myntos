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
    Format brand-specific multi-vertical recharge & scratch card confirmation message.
    """
    mob = mobile_number or ""
    masked_mobile = f"{mob[:2]}****{mob[-4:]}" if len(mob) >= 8 else mob
    brand_name = "Zynova Mobility" if "zynova" in brand.lower() else "MyntReal / Zynova Mobility"

    msg = f"""🎉 *Recharge Successful!*

Thank you for recharging with *{brand_name}*.

📱 Mobile: {masked_mobile}
💰 Recharge Amount: ₹{int(recharge_amount)}
🔢 Transaction ID: TXN_{transaction_id}

🎁 *Your Scratch Card Is Ready!*

Open your secure scratch-card link to reveal your cash reward and claim it directly to your reward wallet:

👉 {scratch_card_url}

🌟 *Explore our services & verticals:*
☀️ Suryanz Solar — Solar solutions for home & commercial
⚡ Zynova Electric Mobility — Electric scooters & smart mobility
🛠️ EVolution Training Centre — Technical EV 2-wheeler training
🛡️ VGK Care — Insurance & protection services
🏠 VGK Real Dreams — Premium real estate & properties
🌱 MNR — Applicable program benefits & Seva

📲 *Recharge again or recharge for your family & friends:*
👉 {verified_recharge_url}

*Terms & conditions apply. Reward eligibility and expiry are subject to campaign rules.*"""

    return msg


TRUSTED_CANONICAL_DOMAINS = [
    "https://zynovamobility.com",
    "https://www.zynovamobility.com",
    "https://myntreal.com",
    "https://www.myntreal.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]


def resolve_canonical_origin(brand: str, origin_url: Optional[str] = None) -> str:
    """
    Task 4: Resolve trusted canonical origin domain preventing domain injection or token leaks.
    """
    if origin_url:
        clean_origin = origin_url.rstrip("/")
        if clean_origin in TRUSTED_CANONICAL_DOMAINS:
            return clean_origin

    brand_clean = (brand or "").lower()
    if "myntreal" in brand_clean:
        return "https://myntreal.com"
    return "https://zynovamobility.com"


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
        brand=brand,
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
        brand=brand,
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
