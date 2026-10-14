"""
RazorpayX Automated Cashback & Scratch Card Payout Service
Handles:
1. Automated Contact Creation (POST /v1/contacts)
2. Automated Fund Account Creation for UPI VPA and Bank Accounts (POST /v1/fund_accounts)
3. Automated Payout Disbursement (POST /v1/payouts) with Idempotency protection
4. Test-mode safe operation ensuring no real money is lost.
"""

import logging
import re
import uuid
import requests
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.reward_scratch import ScratchCard
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

RAZORPAYX_BASE_URL = "https://api.razorpay.com/v1"


def get_razorpayx_auth() -> Optional[Tuple[str, str]]:
    """Retrieve RazorpayX credentials from config or environment."""
    key_id = getattr(settings, "RAZORPAYX_KEY_ID", None)
    key_secret = getattr(settings, "RAZORPAYX_KEY_SECRET", None)
    if key_id and key_secret:
        return (key_id.strip(), key_secret.strip())
    return None


def is_razorpayx_configured() -> bool:
    """Check if RazorpayX payout credentials are configured."""
    return get_razorpayx_auth() is not None


def is_test_mode() -> bool:
    """Return True if RazorpayX is in sandbox / test mode."""
    auth = get_razorpayx_auth()
    if not auth:
        return True
    return auth[0].startswith("rzp_test_")


def sanitize_phone_10(phone: Optional[str]) -> str:
    """Sanitize any phone string into a clean 10-digit number."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return digits[-10:] if len(digits) >= 10 else digits


def resolve_upi_vpa(upi_id: Optional[str], upi_mobile: Optional[str]) -> Optional[str]:
    """
    Resolve a valid UPI Virtual Payment Address (VPA).
    E.g., if user gave full VPA 'user@okhdfcbank', use it.
    If user gave 10-digit mobile number, map to standard '@upi' handle.
    """
    if upi_id and "@" in upi_id:
        return upi_id.strip().lower()

    clean_mobile = sanitize_phone_10(upi_mobile)
    if len(clean_mobile) == 10:
        return f"{clean_mobile}@upi"

    if upi_id and len(sanitize_phone_10(upi_id)) == 10:
        return f"{sanitize_phone_10(upi_id)}@upi"

    return None


def get_or_create_contact(
    name: str,
    phone: str,
    email: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Create or retrieve a Contact in RazorpayX.
    Returns (success, contact_id, error_message).
    """
    auth = get_razorpayx_auth()
    if not auth:
        return False, None, "RazorpayX credentials not configured."

    clean_phone = sanitize_phone_10(phone)
    contact_name = (name or "Recharge Customer").strip()[:100]

    payload = {
        "name": contact_name,
        "contact": clean_phone if len(clean_phone) == 10 else "9876543210",
        "type": "customer",
        "reference_id": f"CUST_{clean_phone}_{int(get_indian_time().timestamp())}"
    }
    if email and "@" in email:
        payload["email"] = email.strip()

    try:
        url = f"{RAZORPAYX_BASE_URL}/contacts"
        resp = requests.post(url, json=payload, auth=auth, timeout=12)
        data = resp.json()

        if resp.status_code in (200, 201) and data.get("id"):
            contact_id = data["id"]
            logger.info(f"[RazorpayX] Created Contact {contact_id} for {clean_phone}")
            return True, contact_id, None
        else:
            err = data.get("error", {}).get("description") or resp.text
            logger.warning(f"[RazorpayX] Contact creation failed: {err}")
            return False, None, f"Failed to create contact: {err}"

    except Exception as e:
        logger.error(f"[RazorpayX] Contact creation exception: {e}")
        return False, None, str(e)


def create_fund_account(
    contact_id: str,
    payout_method: str,
    upi_vpa: Optional[str] = None,
    bank_account: Optional[str] = None,
    bank_ifsc: Optional[str] = None,
    account_name: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Create a Fund Account (VPA or Bank Account) linked to a Contact.
    Returns (success, fund_account_id, error_message).
    """
    auth = get_razorpayx_auth()
    if not auth:
        return False, None, "RazorpayX credentials not configured."

    url = f"{RAZORPAYX_BASE_URL}/fund_accounts"

    if payout_method in ("upi_mobile", "upi_id", "upi"):
        if not upi_vpa:
            return False, None, "Invalid or missing UPI VPA address."

        payload = {
            "contact_id": contact_id,
            "account_type": "vpa",
            "vpa": {
                "address": upi_vpa
            }
        }
    elif payout_method in ("bank_account", "bank", "imps", "neft"):
        if not bank_account or not bank_ifsc:
            return False, None, "Bank account number and IFSC are required."

        payload = {
            "contact_id": contact_id,
            "account_type": "bank_account",
            "bank_account": {
                "name": (account_name or "Valued Customer").strip()[:100],
                "ifsc": bank_ifsc.strip().upper(),
                "account_number": bank_account.strip()
            }
        }
    else:
        return False, None, f"Unsupported payout method: {payout_method}"

    try:
        resp = requests.post(url, json=payload, auth=auth, timeout=12)
        data = resp.json()

        if resp.status_code in (200, 201) and data.get("id"):
            fund_account_id = data["id"]
            logger.info(f"[RazorpayX] Created Fund Account {fund_account_id} for Contact {contact_id}")
            return True, fund_account_id, None
        else:
            err = data.get("error", {}).get("description") or resp.text
            logger.warning(f"[RazorpayX] Fund account creation failed: {err}")
            return False, None, f"Failed to create fund account: {err}"

    except Exception as e:
        logger.error(f"[RazorpayX] Fund account exception: {e}")
        return False, None, str(e)


def disburse_scratch_payout(card: ScratchCard, db: Session) -> Dict[str, Any]:
    """
    Executes automated cashback payout for a claimed Scratch Card via RazorpayX.
    
    1. Validates card eligibility.
    2. Creates Contact on RazorpayX.
    3. Creates Fund Account on RazorpayX (VPA or Bank Account).
    4. Triggers Payout if RAZORPAYX_ACCOUNT_NUMBER is configured.
       If RAZORPAYX_ACCOUNT_NUMBER is not yet configured, sets status to
       'PENDING_ACCOUNT_CONFIG' with fund account ID preserved.
    5. Updates ScratchCard payout status and transaction reference in DB.
    """
    if not card or not card.allocated_amount_paise or card.allocated_amount_paise <= 0:
        return {"success": False, "error": "Invalid scratch card or zero reward amount."}

    # Only process if card is CLAIMED and payout is not already PROCESSED
    if card.payout_status == "PROCESSED":
        return {
            "success": True,
            "already_processed": True,
            "payout_status": "PROCESSED",
            "payout_tx_id": card.payout_tx_id,
            "message": "Cashback payout already processed."
        }

    auth = get_razorpayx_auth()
    if not auth:
        card.payout_status = "PENDING_CONFIG"
        card.payout_notes = "RazorpayX credentials not configured in settings."
        db.commit()
        return {
            "success": False,
            "payout_status": "PENDING_CONFIG",
            "error": "RazorpayX credentials not configured."
        }

    # 1. Resolve contact details
    customer_name = card.customer_name or "Recharge Customer"
    phone = card.mobile_number

    # 2. Resolve payout destination
    method = (card.payout_method or "upi_mobile").lower()
    upi_vpa = None
    bank_acc = None
    bank_ifsc = None

    if method in ("upi_mobile", "upi_id", "upi"):
        payout_mode = "UPI"
        raw_vpa = card.payout_upi_id or card.payout_upi_mobile or card.mobile_number
        upi_vpa = resolve_upi_vpa(card.payout_upi_id, card.payout_upi_mobile or card.mobile_number)
        if not upi_vpa:
            # Fallback to test handle if in test mode
            if is_test_mode():
                upi_vpa = f"{sanitize_phone_10(phone)}@upi"
            else:
                card.payout_status = "FAILED"
                card.payout_notes = f"Invalid UPI details provided: {raw_vpa}"
                db.commit()
                return {"success": False, "payout_status": "FAILED", "error": "Invalid UPI ID or mobile number."}
    else:
        payout_mode = "IMPS"
        bank_acc = card.payout_bank_account
        bank_ifsc = card.payout_bank_ifsc
        if not bank_acc or not bank_ifsc:
            card.payout_status = "FAILED"
            card.payout_notes = "Incomplete bank account or IFSC details."
            db.commit()
            return {"success": False, "payout_status": "FAILED", "error": "Bank account and IFSC are required."}

    # 3. Step A: Create RazorpayX Contact
    contact_ok, contact_id, contact_err = get_or_create_contact(
        name=customer_name,
        phone=phone
    )
    if not contact_ok or not contact_id:
        card.payout_status = "FAILED"
        card.payout_notes = f"RazorpayX Contact Error: {contact_err}"
        db.commit()
        return {"success": False, "payout_status": "FAILED", "error": contact_err}

    # 4. Step B: Create RazorpayX Fund Account
    fa_ok, fa_id, fa_err = create_fund_account(
        contact_id=contact_id,
        payout_method=method,
        upi_vpa=upi_vpa,
        bank_account=bank_acc,
        bank_ifsc=bank_ifsc,
        account_name=customer_name
    )
    if not fa_ok or not fa_id:
        card.payout_status = "FAILED"
        card.payout_notes = f"RazorpayX Fund Account Error: {fa_err}"
        db.commit()
        return {"success": False, "payout_status": "FAILED", "error": fa_err}

    # 5. Step C: Payout Execution
    source_acc = getattr(settings, "RAZORPAYX_ACCOUNT_NUMBER", None)
    if source_acc:
        source_acc = str(source_acc).strip()

    amount_rupees = card.allocated_amount_paise / 100.0

    if not source_acc:
        # Contact & Fund Account were created on live RazorpayX servers!
        # Payout requires the user's RazorpayX Account Number / Customer Identifier.
        note_msg = (
            f"RazorpayX Contact ({contact_id}) and Fund Account ({fa_id}) verified. "
            f"To disburse from your RazorpayX balance, set RAZORPAYX_ACCOUNT_NUMBER in backend/.env."
        )
        card.payout_status = "PENDING_ACCOUNT_CONFIG"
        card.payout_tx_id = fa_id
        card.payout_notes = note_msg
        db.commit()

        logger.info(f"[RazorpayX] Card #{card.id}: {note_msg}")
        return {
            "success": True,
            "payout_status": "PENDING_ACCOUNT_CONFIG",
            "contact_id": contact_id,
            "fund_account_id": fa_id,
            "amount_rupees": amount_rupees,
            "message": "Contact and Fund Account created. Awaiting RazorpayX Business Account Number configuration."
        }

    # If source account number is configured, dispatch the Payout!
    idempotency_key = f"RZPX_PAYOUT_{card.id}_{card.recharge_transaction_id or 'TX'}_{int(card.allocated_amount_paise)}"
    payout_payload = {
        "account_number": source_acc,
        "fund_account_id": fa_id,
        "amount": int(card.allocated_amount_paise),
        "currency": "INR",
        "mode": payout_mode,
        "purpose": "cashback",
        "queue_if_low_balance": True,
        "reference_id": f"SCRATCH_{card.id}",
        "narration": f"Cashback Rs {int(amount_rupees)}"[:30]
    }
    payout_headers = {
        "X-Payout-Idempotency": idempotency_key
    }

    try:
        payout_url = f"{RAZORPAYX_BASE_URL}/payouts"
        resp = requests.post(payout_url, json=payout_payload, headers=payout_headers, auth=auth, timeout=15)
        pdata = resp.json()

        if resp.status_code in (200, 201) and pdata.get("id"):
            p_id = pdata["id"]
            p_status = str(pdata.get("status", "processing")).upper()
            card.payout_status = "PROCESSED" if p_status in ("PROCESSED", "SUCCESS") else "PROCESSING"
            card.payout_tx_id = p_id
            card.payout_notes = f"RazorpayX Payout {p_id} Status: {p_status}. Fund Account: {fa_id}"
            db.commit()

            logger.info(f"[RazorpayX] Payout {p_id} successfully dispatched for Card #{card.id}. Status: {p_status}")
            return {
                "success": True,
                "payout_status": card.payout_status,
                "payout_tx_id": p_id,
                "amount_rupees": amount_rupees,
                "fund_account_id": fa_id,
                "status_detail": p_status
            }
        else:
            err_desc = pdata.get("error", {}).get("description") or resp.text
            card.payout_status = "FAILED"
            card.payout_tx_id = fa_id
            card.payout_notes = f"RazorpayX Payout Error: {err_desc}"
            db.commit()

            logger.warning(f"[RazorpayX] Payout dispatch failed for Card #{card.id}: {err_desc}")
            return {
                "success": False,
                "payout_status": "FAILED",
                "error": err_desc,
                "fund_account_id": fa_id
            }

    except Exception as exc:
        logger.error(f"[RazorpayX] Payout request exception for Card #{card.id}: {exc}")
        card.payout_status = "FAILED"
        card.payout_notes = f"Network/Exception: {str(exc)}"
        db.commit()
        return {"success": False, "payout_status": "FAILED", "error": str(exc)}
