"""
Password Reset Endpoints - Forgot/Reset Password Flow
Allows users to recover their accounts via WhatsApp OTP
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
import random

from app.models.user import User
from app.core.database import get_db
from app.core.security import SecurityManager
from app.api.v1.endpoints.whatsapp import WhatsAppService

router = APIRouter(prefix="/password-reset", tags=["Password Reset"])


class ForgotPasswordRequest(BaseModel):
    user_id: str

    @validator('user_id')
    def validate_user_id(cls, v):
        v = v.strip()
        if not v.startswith('MNR') or len(v) < 10 or len(v) > 12:
            raise ValueError('Invalid MNR ID format. Please enter a valid MNR User ID (e.g., MNR182345678 or MNR1800001)')
        return v


class ResetPasswordRequest(BaseModel):
    user_id: str
    reset_code: str
    new_password: str

    @validator('user_id')
    def validate_user_id(cls, v):
        v = v.strip()
        if not v.startswith('MNR') or len(v) < 10 or len(v) > 12:
            raise ValueError('Invalid MNR ID format. Please enter a valid MNR User ID (e.g., MNR182345678 or MNR1800001)')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v


class VerifyResetCodeRequest(BaseModel):
    user_id: str
    reset_code: str


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset - Generate and send 6-digit code via WhatsApp
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    
    if user:
        # Get mobile number from phone_number field (unencrypted)
        mobile_number = user.phone_number
        
        if mobile_number:
            # Generate 6-digit OTP
            reset_code = str(random.randint(100000, 999999))
            user.reset_code = reset_code
            user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15)
            
            db.commit()
            
            # Send via WhatsApp
            try:
                whatsapp_service = WhatsAppService(db)
                result = whatsapp_service.send_otp(
                    mobile_number=mobile_number,
                    otp_code=reset_code,
                    user_name=user.name
                )
                
                if result['success']:
                    return {
                        "success": True,
                        "message": f"Password reset code sent to your WhatsApp number ending in {mobile_number[-4:]}",
                        "otp_sent": True
                    }
            except Exception as e:
                print(f"Error sending WhatsApp OTP: {str(e)}")
    
    # Generic response for security (don't reveal if user exists)
    return {
        "success": True,
        "message": "If this MNR ID is registered with a mobile number, you will receive a password reset code.",
        "otp_sent": False
    }


@router.post("/verify-reset-code")
async def verify_reset_code(
    request: VerifyResetCodeRequest,
    db: Session = Depends(get_db)
):
    """
    Verify if reset code is valid and not expired
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid MNR ID or reset code")
    
    if not user.reset_code or not user.reset_code_expires:
        raise HTTPException(status_code=400, detail="No active reset code found")
    
    if user.reset_code != request.reset_code:
        raise HTTPException(status_code=400, detail="Invalid reset code")
    
    if datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    
    return {
        "success": True,
        "message": "Reset code verified successfully",
        "valid": True
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using verified reset code
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid MNR ID or reset code")
    
    if not user.reset_code or not user.reset_code_expires:
        raise HTTPException(status_code=400, detail="No active reset code found")
    
    if user.reset_code != request.reset_code:
        raise HTTPException(status_code=400, detail="Invalid reset code")
    
    if datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    
    # Reset password
    user.password = SecurityManager.get_password_hash(request.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    
    db.commit()
    
    return {
        "success": True,
        "message": "Your password has been reset successfully. Please log in with your new password."
    }


@router.get("/check-mobile/{user_id}")
async def check_user_mobile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if user has mobile configured (without revealing the number)
    """
    if not user_id.startswith('MNR') or len(user_id) < 10:
        raise HTTPException(status_code=400, detail="Invalid MNR ID format")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return {"has_mobile": False, "message": "User not found"}
    
    has_mobile = bool(user.phone_number)
    masked_mobile = None
    
    if has_mobile and user.phone_number:
        mobile = user.phone_number
        if len(mobile) >= 4:
            masked_mobile = f"******{mobile[-4:]}"
    
    return {
        "has_mobile": has_mobile,
        "masked_mobile": masked_mobile,
        "message": "Mobile number found" if has_mobile else "No mobile number configured for this account"
    }


# ── DC-OTP-RESET-001: Universal Portal Password Reset (VGK / Staff / Dealer) ──

_PORTAL_LABELS = {
    "vgk_partner":    "VGK Partner Portal",
    "staff":          "Staff Portal",
    "dealer_partner": "Dealer Partner Portal",
    "solar_vendor":   "MyntReal SOLAR Vendor Partner Portal",
    "vendor":         "Vendor Portal",
    "influencer":     "Influencer & Promoter Portal",
}


def _resolve_portal_record(portal: str, user_id: str, db):
    """
    Returns (record_tuple, phone, table_name, display_name) for the given portal + user_id.
    record_tuple[0] = row ID, used in WHERE id=:rid on the auth table.
    """
    from sqlalchemy import text as _t
    uid = user_id.strip()
    uid_upper = uid.upper()

    if portal == "staff":
        row = db.execute(_t(
            "SELECT id, phone, full_name FROM staff_employees WHERE UPPER(emp_code)=:uid AND status='active'"
        ), {"uid": uid_upper}).fetchone()
        if not row:
            return None, None, None, None
        return row, row[1], "staff_employees", row[2]

    if portal == "vgk_partner":
        # DC-OTP-VGK-001: Match VGK login — filter by category=VGK_TEAM, no is_active gate
        # (inactive VGK members can still log in and must be able to reset their password)
        row = db.execute(_t(
            "SELECT id, phone, whatsapp_number, partner_name FROM official_partners "
            "WHERE UPPER(partner_code)=:uid AND category='VGK_TEAM'"
        ), {"uid": uid_upper}).fetchone()
        if not row:
            return None, None, None, None
        phone = row[2] or row[1]
        return row, phone, "official_partners", row[3]

    if portal == "dealer_partner":
        row = db.execute(_t(
            "SELECT id, phone, whatsapp_number, partner_name FROM official_partners "
            "WHERE UPPER(partner_code)=:uid AND is_active=true"
        ), {"uid": uid_upper}).fetchone()
        if not row:
            return None, None, None, None
        phone = row[2] or row[1]
        return row, phone, "official_partners", row[3]

    if portal == "vendor":
        # Look up vendor login by username (phone / email), get phone from vgk_vendors
        row = db.execute(_t(
            "SELECT vl.id, v.whatsapp_number, v.phone, v.vendor_name "
            "FROM vgk_vendor_logins vl "
            "JOIN vgk_vendors v ON v.id = vl.vendor_id "
            "WHERE LOWER(vl.username)=LOWER(:uid)"
        ), {"uid": uid}).fetchone()
        if not row:
            return None, None, None, None
        phone = row[1] or row[2]  # whatsapp_number or phone
        return row, phone, "vgk_vendor_logins", row[3]

    if portal == "solar_vendor":
        # Look up by vendor_code in vendor_master → resolve to official_partners for OTP storage
        row = db.execute(_t("""
            SELECT op.id, COALESCE(op.whatsapp_number, op.phone, vm.phone), vm.vendor_name
            FROM vendor_master vm
            JOIN official_partners op ON UPPER(op.partner_code) = 'SV-' || UPPER(vm.vendor_code)
            WHERE UPPER(vm.vendor_code) = :uid AND vm.is_active = true AND op.is_active = true
        """), {"uid": uid_upper}).fetchone()
        if not row:
            # Also try if official_partner not yet auto-provisioned — just check vendor_master
            vm_row = db.execute(_t(
                "SELECT phone, vendor_name FROM vendor_master WHERE UPPER(vendor_code)=:uid AND is_active=true"
            ), {"uid": uid_upper}).fetchone()
            if not vm_row:
                return None, None, None, None
            # No OTP storage table available without an official_partner record
            return None, None, None, None
        return (row[0],), row[1], "official_partners", row[2]

    if portal == "influencer":
        # Look up by email OR phone in promo_influencers, join auth table
        row = db.execute(_t(
            "SELECT pia.id, pi.phone, pi.name "
            "FROM promo_influencer_auth pia "
            "JOIN promo_influencers pi ON pi.id = pia.influencer_id "
            "WHERE LOWER(pi.email)=LOWER(:uid) OR pi.phone=:uid"
        ), {"uid": uid}).fetchone()
        if not row:
            return None, None, None, None
        return row, row[1], "promo_influencer_auth", row[2]

    return None, None, None, None


class PortalForgotRequest(BaseModel):
    user_id: str


class PortalVerifyOTPRequest(BaseModel):
    user_id: str
    otp_code: str


class PortalResetPasswordRequest(BaseModel):
    user_id: str
    otp_code: str
    new_password: str

    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


@router.post("/portal/{portal}/forgot-password")
async def portal_forgot_password(
    portal: str,
    request: PortalForgotRequest,
    db: Session = Depends(get_db),
):
    """Send WhatsApp OTP for portal password reset. Supports: vgk_partner | staff | dealer_partner | vendor | influencer"""
    if portal not in _PORTAL_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown portal. Valid portals: {', '.join(_PORTAL_LABELS)}")

    from sqlalchemy import text as _t
    record, phone, table, display_name = _resolve_portal_record(portal, request.user_id, db)

    if record and phone:
        otp = str(random.randint(100000, 999999))
        expires = datetime.utcnow() + timedelta(minutes=10)
        try:
            db.execute(_t(
                f"UPDATE {table} SET reset_code=:otp, reset_code_expires=:exp WHERE id=:rid"
            ), {"otp": otp, "exp": expires, "rid": record[0]})
            db.commit()
        except Exception as _e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Could not store OTP")

        try:
            wa = WhatsAppService(db)
            wa.send_otp(mobile_number=phone, otp_code=otp, user_name=display_name or "User")
        except Exception as _we:
            print(f"[DC-OTP] WA send error: {_we}")

        # [DC-VGK-CHANNEL-001] For VGK portal: send channel links as a follow-up free-form message
        if portal == "vgk_partner":
            try:
                from app.services.whatsapp_auto_service import send_direct_whatsapp
                _channel_msg = (
                    f"📢 *Stay Connected — Join our WhatsApp Channels:*\n"
                    f"🔷 VGK4U: https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m\n"
                    f"🌐 Myntreal: https://whatsapp.com/channel/0029VbCmSCh2kNFiA0RsHZ2r\n"
                    f"☀️ Har Ghar Solar: https://whatsapp.com/channel/0029Vb7V0ImFCCoYg891FL3D"
                )
                send_direct_whatsapp(db=db, phone=phone, message=_channel_msg, staff_id=None)
            except Exception as _ce:
                print(f"[DC-VGK-CHANNEL-001] Channel footer send error (non-blocking): {_ce}")

    return {
        "success": True,
        "message": "If your ID is registered, an OTP has been sent to your WhatsApp number.",
        "portal_label": _PORTAL_LABELS.get(portal, portal),
    }


@router.post("/portal/{portal}/verify-otp")
async def portal_verify_otp(
    portal: str,
    request: PortalVerifyOTPRequest,
    db: Session = Depends(get_db),
):
    if portal not in _PORTAL_LABELS:
        raise HTTPException(status_code=400, detail="Unknown portal")

    from sqlalchemy import text as _t
    record, _, table, _ = _resolve_portal_record(portal, request.user_id, db)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid ID or portal")

    row = db.execute(_t(
        f"SELECT reset_code, reset_code_expires FROM {table} WHERE id=:rid"
    ), {"rid": record[0]}).fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="No active OTP found. Please request a new one.")
    if row[0] != request.otp_code.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    if row[1] and datetime.utcnow() > row[1]:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    return {"success": True, "valid": True, "message": "OTP verified successfully."}


@router.post("/portal/{portal}/reset-password")
async def portal_reset_password(
    portal: str,
    request: PortalResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if portal not in _PORTAL_LABELS:
        raise HTTPException(status_code=400, detail="Unknown portal")

    from sqlalchemy import text as _t
    record, _, table, _ = _resolve_portal_record(portal, request.user_id, db)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid ID or portal")

    row = db.execute(_t(
        f"SELECT reset_code, reset_code_expires FROM {table} WHERE id=:rid"
    ), {"rid": record[0]}).fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="No active OTP found.")
    if row[0] != request.otp_code.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    if row[1] and datetime.utcnow() > row[1]:
        raise HTTPException(status_code=400, detail="OTP expired.")

    new_hash = SecurityManager.get_password_hash(request.new_password)
    try:
        db.execute(_t(
            f"UPDATE {table} SET password_hash=:ph, reset_code=NULL, reset_code_expires=NULL WHERE id=:rid"
        ), {"ph": new_hash, "rid": record[0]})
        db.commit()
    except Exception as _e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update password")

    return {
        "success": True,
        "message": f"Password reset successfully for {_PORTAL_LABELS[portal]}. Please log in with your new password.",
    }
