"""
[DC-PHONE-OTP-001] Phone OTP Utility
Reusable OTP generation, WhatsApp delivery, and token lifecycle for pre-registration phone verification.
Purposes: 'vgk_signup', 'vgk_staff_add', 'mnr_register', 'vgk_walkin'
"""
import random
import string
import uuid
import logging
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

OTP_EXPIRE_MINUTES = 10
TOKEN_EXPIRE_MINUTES = 15
VGK_MENTOR_BYPASS_CODE = 'MR10001'


def _get_indian_time():
    from datetime import datetime
    import pytz
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)


def generate_and_send_otp(phone: str, purpose: str, db: Session, user_name: Optional[str] = None) -> dict:
    """
    [DC-PHONE-OTP-001] Generate a 6-digit OTP, store it, send via WhatsApp.
    Invalidates any previous un-verified OTP for the same phone+purpose.
    Returns {"success": True, "message": "..."}
    """
    otp_code = ''.join(random.choices(string.digits, k=6))
    now = _get_indian_time()
    expires_at = now + timedelta(minutes=OTP_EXPIRE_MINUTES)

    # Invalidate old OTPs for this phone+purpose (mark expired)
    db.execute(sa_text(
        "UPDATE phone_otp_verifications SET expires_at = :past "
        "WHERE phone = :phone AND purpose = :purpose AND verified = FALSE AND token_used = FALSE"
    ), {"past": now - timedelta(seconds=1), "phone": phone, "purpose": purpose})

    # Insert new OTP row
    db.execute(sa_text(
        "INSERT INTO phone_otp_verifications (phone, purpose, otp_code, expires_at, created_at) "
        "VALUES (:phone, :purpose, :otp, :exp, :now)"
    ), {"phone": phone, "purpose": purpose, "otp": otp_code, "exp": expires_at, "now": now})
    db.commit()

    # Send via WhatsApp
    try:
        from app.api.v1.endpoints.whatsapp import WhatsAppService
        wa = WhatsAppService(db)
        wa_result = wa.send_otp(mobile_number=phone, otp_code=otp_code, user_name=user_name or "User")
        if not wa_result.get("success"):
            logger.warning(f"[DC-PHONE-OTP-001] WhatsApp OTP send issue for {phone}: {wa_result.get('message')}")
    except Exception as e:
        logger.error(f"[DC-PHONE-OTP-001] WhatsApp OTP send failed for {phone}: {e}")

    logger.info(f"[DC-PHONE-OTP-001] OTP sent for phone={phone} purpose={purpose}")
    return {
        "success": True,
        "message": f"OTP sent to WhatsApp on {phone[-4:].rjust(len(phone), '*')}. Valid for {OTP_EXPIRE_MINUTES} minutes."
    }


def verify_otp_and_issue_token(phone: str, otp_code: str, purpose: str, db: Session) -> str:
    """
    [DC-PHONE-OTP-001] Validate OTP and issue a single-use phone_verified_token (UUID).
    Returns the token string. Raises HTTPException on failure.
    """
    now = _get_indian_time()
    row = db.execute(sa_text(
        "SELECT id, otp_code, expires_at, verified FROM phone_otp_verifications "
        "WHERE phone = :phone AND purpose = :purpose AND verified = FALSE "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"phone": phone, "purpose": purpose}).fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="No active OTP found. Please request a new one.")

    rec_id, stored_otp, expires_at, verified = row

    if stored_otp.strip() != otp_code.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and try again.")

    if expires_at < now:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Issue token
    token = str(uuid.uuid4())
    token_expires_at = now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    db.execute(sa_text(
        "UPDATE phone_otp_verifications SET verified = TRUE, verified_at = :now, "
        "phone_verified_token = :token, token_expires_at = :texp WHERE id = :rid"
    ), {"now": now, "token": token, "texp": token_expires_at, "rid": rec_id})
    db.commit()

    logger.info(f"[DC-PHONE-OTP-001] OTP verified, token issued for phone={phone} purpose={purpose}")
    return token


def validate_and_consume_token(phone: str, token: str, purpose: str, db: Session) -> None:
    """
    [DC-PHONE-OTP-001] Validate phone_verified_token and mark it consumed.
    Raises HTTPException if token is invalid, expired, or already used.
    """
    now = _get_indian_time()
    row = db.execute(sa_text(
        "SELECT id, token_expires_at, token_used FROM phone_otp_verifications "
        "WHERE phone = :phone AND purpose = :purpose AND phone_verified_token = :token "
        "AND verified = TRUE ORDER BY verified_at DESC LIMIT 1"
    ), {"phone": phone, "purpose": purpose, "token": token}).fetchone()

    if not row:
        raise HTTPException(
            status_code=400,
            detail="Phone verification required. Please verify your phone number with OTP first."
        )

    rec_id, token_expires_at, token_used = row

    if token_used:
        raise HTTPException(status_code=400, detail="Verification token already used. Please verify your phone again.")

    if token_expires_at < now:
        raise HTTPException(status_code=400, detail="Verification token expired. Please verify your phone again.")

    # Consume token
    db.execute(sa_text(
        "UPDATE phone_otp_verifications SET token_used = TRUE WHERE id = :rid"
    ), {"rid": rec_id})
    # Note: commit is done by the calling endpoint after account creation
    logger.info(f"[DC-PHONE-OTP-001] Token consumed for phone={phone} purpose={purpose}")
