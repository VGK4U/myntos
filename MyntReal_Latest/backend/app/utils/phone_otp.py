"""
[DC-PHONE-OTP-001] Phone OTP Utility
Reusable OTP generation, WhatsApp delivery, and token lifecycle for pre-registration phone verification.
Purposes: 'vgk_signup', 'vgk_staff_add', 'mnr_register', 'vgk_walkin'
"""
import random
import re
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


def normalize_phone_10(phone: Optional[str]) -> str:
    """
    Standardize Indian mobile phone numbers to a clean 10-digit format.
    Strips non-digit characters, leading +91, 91 (if length 12), and leading 0 (if length 11).
    Returns a 10-digit string if valid, otherwise empty string.
    """
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone).strip())
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    elif len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else ""


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
    wa_sent = True
    wa_reason = None
    wa_err_code = None
    try:
        from app.services.whatsapp_canonical_service import WhatsAppCanonicalService
        wa_result = WhatsAppCanonicalService.send_meta_template_message(
            db=db,
            phone=phone,
            template_name="otp",
            language_code="en",
            components=[
                {"type": "body", "parameters": [{"type": "text", "text": otp_code}]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": otp_code}]}
            ],
            message_type="whatsapp_otp",
            user_name=user_name or "User",
            sent_by_name="Registration Engine"
        )
        if not wa_result.get("success"):
            wa_sent = False
            wa_reason = wa_result.get("reason")
            wa_err_code = wa_result.get("error_code")
            logger.warning(f"[DC-PHONE-OTP-001] WhatsApp OTP send issue for {phone}: {wa_reason} ({wa_err_code})")
    except Exception as e:
        wa_sent = False
        wa_reason = str(e)
        logger.error(f"[DC-PHONE-OTP-001] WhatsApp OTP send failed for {phone}: {e}")

    logger.info(f"[DC-PHONE-OTP-001] OTP generated for phone={phone} purpose={purpose} wa_sent={wa_sent}")
    if wa_sent:
        return {
            "success": True,
            "otp_sent": True,
            "message": f"OTP sent to WhatsApp on {phone[-4:].rjust(len(phone), '*')}. Valid for {OTP_EXPIRE_MINUTES} minutes."
        }
    else:
        return {
            "success": True,
            "otp_sent": False,
            "reason": wa_reason or "WhatsApp service unavailable",
            "error_code": wa_err_code,
            "message": "WhatsApp verification is currently unavailable. You may continue registration and verify your WhatsApp number later."
        }


def verify_and_mark_user_phone(phone: str, otp_code: str, purpose: str, db: Session, user_id: Optional[str] = None) -> dict:
    """
    [DC-PHONE-OTP-001] Verify OTP for existing User and set mobile_verified = True in DB.
    """
    from app.models.user import User
    # Verify OTP first
    token = verify_otp_and_issue_token(phone=phone, otp_code=otp_code, purpose=purpose, db=db)
    validate_and_consume_token(phone=phone, token=token, purpose=purpose, db=db)

    # Update User in DB
    query = db.query(User).filter(User.phone_number == phone)
    if user_id:
        query = query.filter(User.id == user_id)
    user = query.first()
    if user:
        user.mobile_verified = True
        db.commit()
        logger.info(f"[DC-PHONE-OTP-001] User {user.id} phone {phone} marked mobile_verified=True")
        return {"success": True, "message": "WhatsApp number verified successfully.", "user_id": user.id, "mobile_verified": True}
    return {"success": True, "message": "OTP verified successfully.", "mobile_verified": True}


def verify_and_mark_partner_phone(phone: str, otp_code: str, purpose: str, db: Session, partner_id: Optional[int] = None) -> dict:
    """
    [DC-PHONE-OTP-001] Verify OTP for existing OfficialPartner and set phone_verified = True in DB.
    """
    from app.models.staff_accounts import OfficialPartner
    # Verify OTP first
    token = verify_otp_and_issue_token(phone=phone, otp_code=otp_code, purpose=purpose, db=db)
    validate_and_consume_token(phone=phone, token=token, purpose=purpose, db=db)

    # Update OfficialPartner in DB
    query = db.query(OfficialPartner).filter(OfficialPartner.phone == phone)
    if partner_id:
        query = query.filter(OfficialPartner.id == partner_id)
    partner = query.first()
    if partner:
        partner.phone_verified = True
        db.commit()
        logger.info(f"[DC-PHONE-OTP-001] Partner {partner.partner_code} phone {phone} marked phone_verified=True")
        return {"success": True, "message": "WhatsApp number verified successfully.", "partner_code": partner.partner_code, "phone_verified": True}
    return {"success": True, "message": "OTP verified successfully.", "phone_verified": True}


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
