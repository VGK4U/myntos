"""
CRM Lead Contact Privacy & Server-Side Click-to-Call Service
MyntOS / VGK4U Core Architecture

Authoritative business principle:
Contact authorization = Relationship to Lead + Operational Responsibility + Authorized Business Need.
Career designation alone (Manager, GM, RM, L2, L3) MUST NOT grant raw customer phone access.

Visibility Matrix:
1. Lead Producer / Owner               -> FULL PHONE
2. Immediate Direct Sponsor            -> FULL PHONE
3. Explicitly Assigned Guru / Support  -> FULL PHONE
4. Authorized Staff                    -> FULL PHONE
5. Authorized Indirect Upline (L2+)    -> MASKED (98****3210) + CLICK-TO-CALL
6. Unauthorized Partner                -> NO ACCESS (403)
"""

import re
import os
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

from app.models.base import get_indian_time
from app.models.crm import CRMLead, CRMLeadAuditLog
from app.models.staff_accounts import OfficialPartner
from app.models.staff import StaffEmployee
from app.services.telephony.canonical_phone import CanonicalPhoneValidator
from app.services.voip_call_service import VoIPCallService

logger = logging.getLogger(__name__)


def mask_phone_canonical(phone: Optional[str]) -> str:
    """
    Returns canonically masked phone number: 98****3210 (first 2, 4 asterisks, last 4).
    If phone is missing or invalid (<6 digits), returns '—'.
    """
    if not phone:
        return "—"
    clean = re.sub(r'\D', '', str(phone).strip())
    if len(clean) < 6:
        return "—"
    c10 = clean[-10:] if len(clean) >= 10 else clean
    if len(c10) == 10:
        return f"{c10[:2]}****{c10[-4:]}"
    return f"{c10[:2]}****{c10[-2:]}"


def is_in_partner_downline(
    db: Session,
    ancestor_partner_id: int,
    descendant_partner_id: int,
    max_depth: int = 20
) -> Tuple[bool, int]:
    """
    Traverses parent_partner_id hierarchy upwards from descendant to ancestor.
    Returns (True, depth) if descendant is in ancestor's downline.
    depth=1 means ancestor is immediate direct sponsor.
    depth>=2 means ancestor is indirect upline (L2, L3, L4, etc.).
    """
    if not ancestor_partner_id or not descendant_partner_id:
        return False, 0
    if ancestor_partner_id == descendant_partner_id:
        return False, 0

    current_id = descendant_partner_id
    depth = 0
    seen = {descendant_partner_id}

    while current_id and depth < max_depth:
        depth += 1
        parent_id = db.execute(
            text("SELECT parent_partner_id FROM official_partners WHERE id = :pid"),
            {"pid": current_id}
        ).scalar()

        if not parent_id:
            break
        if parent_id == ancestor_partner_id:
            return True, depth
        if parent_id in seen:
            break
        seen.add(parent_id)
        current_id = parent_id

    return False, 0


def evaluate_lead_contact_authorization(
    lead: CRMLead,
    current_user: Any,
    db: Session
) -> Dict[str, Any]:
    """
    Authoritative evaluation of lead contact authorization.
    Decoupled from career rank/designation alone.
    Returns:
    {
        "can_view": bool,
        "has_full_contact": bool,
        "can_click_to_call": bool,
        "relationship": str,
        "display_phone": str,
        "is_masked": bool,
        "lead_id": int
    }
    """
    if not lead or not current_user:
        return {
            "can_view": False,
            "has_full_contact": False,
            "can_click_to_call": False,
            "relationship": "UNAUTHORIZED",
            "display_phone": "—",
            "is_masked": True,
            "lead_id": lead.id if lead else None
        }

    raw_phone = lead.phone or ""
    raw_alt_phone = getattr(lead, 'alternate_phone', None) or ""

    # =========================================================================
    # A. STAFF USER AUTHORIZATION
    # =========================================================================
    if isinstance(current_user, StaffEmployee) or hasattr(current_user, 'emp_code'):
        staff_id = current_user.id
        emp_code = getattr(current_user, 'emp_code', '')

        # 1. Assigned Staff (Telecaller, Field Staff, Support Staff, Tech Staff, Owner, Creator)
        is_assigned_staff = (
            lead.telecaller_id == staff_id or
            lead.field_staff_id == staff_id or
            lead.support_staff_id == staff_id or
            lead.technical_id == staff_id or
            getattr(lead, 'technical_staff1_id', None) == staff_id or
            (lead.primary_owner_type == 'staff' and lead.primary_owner_id == staff_id) or
            (lead.created_by_type == 'staff' and str(lead.created_by_id) in (emp_code, str(staff_id)))
        )
        if is_assigned_staff:
            return {
                "can_view": True,
                "has_full_contact": True,
                "can_click_to_call": True,
                "relationship": "ASSIGNED_STAFF",
                "display_phone": raw_phone or "—",
                "display_alternate_phone": raw_alt_phone or "—",
                "is_masked": False,
                "lead_id": lead.id
            }

        # 2. Administrative / Management Staff Clearance
        staff_type = (getattr(current_user, 'staff_type', '') or '').upper()
        is_admin_staff = (
            getattr(current_user, 'is_supreme', False) or
            staff_type in ('VGK4U', 'VGK4U SUPREME', 'ADMIN', 'MANAGEMENT', 'KEY LEADERSHIP') or
            emp_code in ('MR10001', 'ADMIN')
        )
        if is_admin_staff:
            return {
                "can_view": True,
                "has_full_contact": True,
                "can_click_to_call": True,
                "relationship": "AUTHORIZED_STAFF",
                "display_phone": raw_phone or "—",
                "display_alternate_phone": raw_alt_phone or "—",
                "is_masked": False,
                "lead_id": lead.id
            }

        # 3. Non-assigned Staff in same organization -> Masked + Click-to-Call
        company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None) or 1
        if lead.company_id == company_id or not lead.company_id:
            return {
                "can_view": True,
                "has_full_contact": False,
                "can_click_to_call": True,
                "relationship": "INDIRECT_STAFF",
                "display_phone": mask_phone_canonical(raw_phone),
                "display_alternate_phone": mask_phone_canonical(raw_alt_phone) if raw_alt_phone else "—",
                "is_masked": True,
                "lead_id": lead.id
            }

        return {
            "can_view": False,
            "has_full_contact": False,
            "can_click_to_call": False,
            "relationship": "UNAUTHORIZED",
            "display_phone": "—",
            "display_alternate_phone": "—",
            "is_masked": True,
            "lead_id": lead.id
        }

    # =========================================================================
    # B. OFFICIAL PARTNER / VGK MEMBER AUTHORIZATION
    # =========================================================================
    partner_id = getattr(current_user, 'id', None)
    if not partner_id:
        return {
            "can_view": False,
            "has_full_contact": False,
            "can_click_to_call": False,
            "relationship": "UNAUTHORIZED",
            "display_phone": "—",
            "display_alternate_phone": "—",
            "is_masked": True,
            "lead_id": lead.id
        }

    partner_id_str = str(partner_id)

    # 1. Lead Producer / Owner (FULL CONTACT)
    is_producer = (
        lead.associated_partner_id == partner_id or
        (lead.primary_owner_type == 'partner' and lead.primary_owner_id == partner_id) or
        (lead.created_by_type == 'partner' and str(lead.created_by_id) == partner_id_str) or
        (lead.source_ref_type in ('partner', 'vgk_partner') and str(lead.source_ref_id) == partner_id_str)
    )
    if is_producer:
        return {
            "can_view": True,
            "has_full_contact": True,
            "can_click_to_call": True,
            "relationship": "PRODUCER",
            "display_phone": raw_phone or "—",
            "display_alternate_phone": raw_alt_phone or "—",
            "is_masked": False,
            "lead_id": lead.id
        }

    # Resolve producer ID for hierarchical downline checks
    producer_id = lead.associated_partner_id
    if not producer_id and lead.created_by_type == 'partner' and str(lead.created_by_id).isdigit():
        producer_id = int(lead.created_by_id)

    # 2. Immediate Direct Sponsor (FULL CONTACT)
    is_direct_sponsor = False
    if lead.direct_team_lead_sponsor_id == partner_id and partner_id != producer_id:
        is_direct_sponsor = True
    elif producer_id:
        producer_parent_id = db.execute(
            text("SELECT parent_partner_id FROM official_partners WHERE id = :pid"),
            {"pid": producer_id}
        ).scalar()
        if producer_parent_id == partner_id and partner_id != producer_id:
            is_direct_sponsor = True

    if is_direct_sponsor:
        return {
            "can_view": True,
            "has_full_contact": True,
            "can_click_to_call": True,
            "relationship": "DIRECT_SPONSOR",
            "display_phone": raw_phone or "—",
            "display_alternate_phone": raw_alt_phone or "—",
            "is_masked": False,
            "lead_id": lead.id
        }

    # 3. Explicitly Assigned Guru / Operational Support (FULL CONTACT)
    is_explicit_support = False
    if lead.vgk_field_support_id == partner_id:
        is_explicit_support = True
    elif lead.team_senior_partner_id == partner_id and getattr(lead, 'guru_supported', False):
        is_explicit_support = True
    elif lead.team_extended_partner_id == partner_id and getattr(lead, 'z_guru_supported', False):
        is_explicit_support = True
    elif getattr(lead, 'team_core_partner_id', None) == partner_id and getattr(lead, 'core_supported', False):
        is_explicit_support = True
    else:
        confirmed_support = db.execute(text("""
            SELECT 1 FROM vgk_team_income_entries
            WHERE partner_id = :pid AND source_lead_id = :lid AND support_confirmed = true
            LIMIT 1
        """), {"pid": partner_id, "lid": lead.id}).scalar()
        if confirmed_support:
            is_explicit_support = True

    if is_explicit_support:
        return {
            "can_view": True,
            "has_full_contact": True,
            "can_click_to_call": True,
            "relationship": "ASSIGNED_SUPPORT",
            "display_phone": raw_phone or "—",
            "display_alternate_phone": raw_alt_phone or "—",
            "is_masked": False,
            "lead_id": lead.id
        }

    # 4. Authorized Indirect Upline (L2+) (MASKED + CLICK-TO-CALL)
    # Legitimate indirect relationship: producer is in this partner's downline tree
    # OR partner is tagged as an indirect team partner on the lead
    is_indirect_upline = False
    depth_val = 0

    if producer_id:
        in_downline, depth_val = is_in_partner_downline(db, ancestor_partner_id=partner_id, descendant_partner_id=producer_id)
        if in_downline and depth_val >= 2:
            is_indirect_upline = True

    if not is_indirect_upline:
        if (
            lead.team_senior_partner_id == partner_id or
            lead.team_extended_partner_id == partner_id or
            getattr(lead, 'team_core_partner_id', None) == partner_id
        ):
            is_indirect_upline = True

    if not is_indirect_upline:
        has_team_record = db.execute(text("""
            SELECT 1 FROM vgk_team_income_entries
            WHERE partner_id = :pid AND source_lead_id = :lid
            LIMIT 1
        """), {"pid": partner_id, "lid": lead.id}).scalar()
        if has_team_record:
            is_indirect_upline = True

    if is_indirect_upline:
        return {
            "can_view": True,
            "has_full_contact": False,
            "can_click_to_call": True,
            "relationship": f"INDIRECT_UPLINE_L{depth_val}" if depth_val >= 2 else "INDIRECT_UPLINE",
            "display_phone": mask_phone_canonical(raw_phone),
            "display_alternate_phone": mask_phone_canonical(raw_alt_phone) if raw_alt_phone else "—",
            "is_masked": True,
            "lead_id": lead.id
        }

    # 5. Unrelated Partner (NO ACCESS)
    return {
        "can_view": False,
        "has_full_contact": False,
        "can_click_to_call": False,
        "relationship": "UNAUTHORIZED",
        "display_phone": "—",
        "display_alternate_phone": "—",
        "is_masked": True,
        "lead_id": lead.id
    }


def acquire_lead_call_reservation(
    db: Session,
    lead_id: int,
    user_ref: str,
    portal: str = 'vgk',
    ttl_seconds: int = 60
) -> Tuple[bool, str, Optional[datetime]]:
    """
    Acquires or extends an active call reservation in crm_dialer_reservations.
    Guarantees concurrency protection: prevents two users from dialing the same lead simultaneously.
    """
    now = get_indian_time()

    # 1. Scavenge expired reservations
    try:
        db.execute(text("DELETE FROM crm_dialer_reservations WHERE expires_at <= :now"), {"now": now})
        db.flush()
    except Exception as e:
        logger.debug(f"[DC_RESERVATION] Scavenge error: {e}")

    # 2. Check existing reservation
    res_row = db.execute(text("""
        SELECT id, user_ref, expires_at
        FROM crm_dialer_reservations
        WHERE lead_id = :lid
    """), {"lid": lead_id}).fetchone()

    if res_row:
        existing_user_ref = str(res_row[1])
        existing_expires = res_row[2]
        if existing_user_ref != str(user_ref) and existing_expires > now:
            return False, "Lead is currently in an active call / reservation with another user", existing_expires

        new_expires = now + timedelta(seconds=ttl_seconds)
        db.execute(text("""
            UPDATE crm_dialer_reservations
            SET user_ref = :ref, portal = :portal, reserved_at = :now, expires_at = :expires
            WHERE lead_id = :lid
        """), {"ref": str(user_ref), "portal": portal, "now": now, "expires": new_expires, "lid": lead_id})
        db.commit()
        return True, "Reservation extended", new_expires

    # 3. New reservation
    try:
        new_expires = now + timedelta(seconds=ttl_seconds)
        db.execute(text("""
            INSERT INTO crm_dialer_reservations
                (lead_id, user_ref, portal, reserved_at, expires_at)
            VALUES
                (:lid, :ref, :portal, :now, :expires)
            ON CONFLICT (lead_id) DO UPDATE
                SET user_ref = :ref, portal = :portal, reserved_at = :now, expires_at = :expires
        """), {"lid": lead_id, "ref": str(user_ref), "portal": portal, "now": now, "expires": new_expires})
        db.commit()
        return True, "Reserved successfully", new_expires
    except Exception as e:
        db.rollback()
        logger.warning(f"[DC_RESERVATION] Acquire failed: {e}")
        return False, f"Could not acquire reservation: {e}", None


def initiate_lead_click_to_call(
    db: Session,
    lead_id: int,
    current_user: Any,
    ttl_seconds: int = 60
) -> Dict[str, Any]:
    """
    Executes secure, server-side Click-to-Call:
    1. Validates identity & evaluates dynamic relationship authorization.
    2. Verifies lead exists, is active, and callable.
    3. Acquires concurrency reservation in crm_dialer_reservations.
    4. Dispatches outbound call via existing Plivo bridge (VoIPCallService).
    5. Logs attempt in crm_dialer_attempts and voip_call_sessions.
    6. Returns call session metadata WITHOUT exposing raw customer phone to masked users.
    7. Guarantees ZERO changes to lead ownership, commissions, or points.
    """
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required")

    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    auth = evaluate_lead_contact_authorization(lead, current_user, db)
    if not auth["can_view"] or not auth["can_click_to_call"]:
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized: You do not have call permission for this lead ({auth['relationship']})"
        )

    if getattr(lead, 'status', None) in ('lost', 'dnc', 'do_not_call'):
        raise HTTPException(
            status_code=400,
            detail=f"Lead is marked as '{lead.status}' and cannot be called"
        )

    if not lead.phone:
        raise HTTPException(status_code=400, detail="Lead does not have a valid telephone number")

    user_ref = (
        getattr(current_user, 'partner_code', None) or
        getattr(current_user, 'emp_code', None) or
        str(current_user.id)
    )
    portal = 'vgk' if isinstance(current_user, OfficialPartner) or getattr(current_user, 'category', None) == 'VGK_TEAM' else 'staff'

    reserved_ok, res_msg, expires_at = acquire_lead_call_reservation(
        db=db,
        lead_id=lead.id,
        user_ref=user_ref,
        portal=portal,
        ttl_seconds=ttl_seconds
    )
    if not reserved_ok:
        raise HTTPException(status_code=409, detail=res_msg)

    now = get_indian_time()
    try:
        session = VoIPCallService.initiate_in_app_call(
            db=db,
            current_user=current_user,
            customer_phone=lead.phone,
            lead_id=lead.id,
            provider_name='plivo',
            dispatch_provider_call=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLICK-TO-CALL] Telephony bridge dispatch error: {e}")
        raise HTTPException(status_code=502, detail=f"Telephony bridge failed: {str(e)}")

    try:
        db.execute(text("""
            INSERT INTO crm_dialer_attempts (
                lead_id, user_ref, portal, call_method, dialed_at, created_at, call_outcome, note
            ) VALUES (
                :lid, :ref, :portal, 'click_to_call', :now, :now, 'initiated', :note
            )
        """), {
            "lid": lead.id,
            "ref": user_ref,
            "portal": portal,
            "now": now,
            "note": f"Click-to-call initiated by {auth['relationship']} ({user_ref})"
        })
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[CLICK-TO-CALL-LOG] Failed to log crm_dialer_attempt: {e}")

    masked_phone = mask_phone_canonical(lead.phone)
    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "provider_call_id": session.provider_call_id,
        "destination_phone": lead.phone if auth["has_full_contact"] else masked_phone,
        "customer_phone_masked": masked_phone,
        "caller_id": session.caller_id,
        "status": session.status,
        "lead_id": lead.id,
        "relationship": auth["relationship"],
        "is_masked": auth["is_masked"],
        "message": "Outbound call initiated via secure telephony bridge"
    }
