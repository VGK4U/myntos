"""
Universal History Aggregation Service
Single Source of Truth for unified communication and CRM change history across MyntOS.
Provides composite read models for:
  1. Calls & Recordings (Plivo WebRTC, Native GSM, MyOperator, AutoDialer)
  2. Messages / Chat (Inbound WhatsApp, Outbound WhatsApp/SMS)
  3. Lead Change History (Audit logs, Notes, Follow-ups, Assignments)
Pure read-only queries with zero DB side-effects.
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, case

from app.models.crm import (
    CRMLead,
    CRMLeadPhone,
    CRMLeadAuditLog,
    CRMLeadNote,
    CRMLeadFollowUp,
    CRMLeadAssignment,
)
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner
from app.models.call_tracking import CallQualityReview
from app.api.v1.endpoints.call_tracking import resolve_call_from

logger = logging.getLogger(__name__)


def normalize_phone_digits(phone: Optional[str]) -> str:
    """Extract trailing 10 digits from any phone string."""
    if not phone:
        return ""
    digits = re.sub(r"[^0-9]", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def mask_phone_number(phone: Optional[str], can_unmask: bool = True) -> str:
    """Mask phone for non-privileged staff (e.g. +91 98765 43210 -> XXXXXX3210)."""
    if not phone:
        return ""
    if can_unmask:
        return str(phone)
    raw = str(phone).strip()
    digits = re.sub(r"[^0-9]", "", raw)
    if len(digits) >= 4:
        return f"XXXXXX{digits[-4:]}"
    return "XXXXXX"


def resolve_media_attachment(
    raw_url: Optional[str] = None,
    mime_type: Optional[str] = None,
    media_name: Optional[str] = None,
    body_text: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """
    Normalizes media attachment URLs and infers media type.
    Handles numeric Meta IDs, local /storage/wa_media paths, and embedded [Media: ...] tags in text.
    Returns (final_url, media_type, mime_type, filename, cleaned_body_text).
    """
    url = str(raw_url or "").strip()
    body = str(body_text or "")

    # 1. Fallback: Search embedded [Media: <url>] if no explicit url provided
    if not url and "[Media: " in body:
        m_match = re.search(r'\[Media:\s*([^\]]+)\]', body)
        if m_match:
            url = m_match.group(1).strip()
            if not media_name:
                media_name = url.split("/")[-1].split("?")[0]

    # Clean body text from raw [Media: ...] bracket artifacts for tidy presentation
    cleaned_body = re.sub(r'\[Media:\s*[^\]]+\]', '', body).strip()

    if not url:
        return None, None, mime_type, media_name, cleaned_body

    # 2. Normalize URL
    if url.isdigit():
        final_url = f"/api/v1/whatsapp/media/{url}"
    elif url.startswith("http://") or url.startswith("https://") or url.startswith("/") or url.startswith("data:"):
        final_url = url
    else:
        final_url = f"/storage/wa_media/{url}"

    # 3. Determine media type and standard user-facing filename
    u_lower = final_url.lower().split("?")[0]
    m_lower = str(mime_type or "").lower()

    is_img = any(u_lower.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg')) or m_lower.startswith('image/')
    is_pdf = u_lower.endswith('.pdf') or 'pdf' in m_lower
    is_doc = any(u_lower.endswith(ext) for ext in ('.doc', '.docx', '.xls', '.xlsx', '.csv', '.ppt', '.pptx', '.txt')) or 'document' in m_lower or 'sheet' in m_lower or is_pdf
    is_audio = any(u_lower.endswith(ext) for ext in ('.mp3', '.ogg', '.wav', '.aac', '.m4a', '.opus')) or m_lower.startswith('audio/')
    is_video = any(u_lower.endswith(ext) for ext in ('.mp4', '.mkv', '.webm', '.3gp')) or m_lower.startswith('video/')

    if is_img:
        media_type = "image"
    elif is_doc:
        media_type = "document"
    elif is_audio:
        media_type = "audio"
    elif is_video:
        media_type = "video"
    else:
        media_type = "document"

    if not media_name or re.match(r'^\d+$', str(media_name)):
        if is_img:
            media_name = "Photo Attachment"
        elif is_pdf:
            media_name = "PDF Document"
        elif is_audio:
            media_name = "Voice Note"
        elif is_video:
            media_name = "Video Attachment"
        else:
            media_name = "Media Attachment"

    return final_url, media_type, mime_type, media_name, cleaned_body


def resolve_message_status(
    raw_status: Optional[str],
    direction: str,
    failed_at: Optional[datetime] = None,
    failure_reason: Optional[str] = None,
    error_message: Optional[str] = None,
    error_code: Optional[str] = None,
    delivered_at: Optional[datetime] = None,
    read_at: Optional[datetime] = None
) -> Tuple[str, str, str, str, Optional[str]]:
    """
    Calculates unified message delivery state (Failed, Delivered, Read, Sent, Queued, Received)
    matching WhatsApp Center conventions.
    Returns (status, status_label, status_ticks, status_color, final_failure_reason).
    """
    if direction == "inbound":
        return "received", "Received", "↙", "#10b981", None

    st = str(raw_status or "sent").lower()
    final_err = failure_reason or error_message or (f"Error {error_code}" if error_code and str(error_code).upper() not in ('0', 'NONE', 'NULL', 'SUCCESS') else None)

    is_failed = bool(
        failed_at
        or st in ('failed', 'undelivered', 'error', 'partial_failed', 'rejected')
        or final_err
    )
    is_read = bool(read_at or st in ('read', 'viewed', 'opened'))
    is_delivered = bool(delivered_at or st in ('delivered', 'received'))
    is_queued = bool(st in ('queued', 'pending', 'sending'))

    if is_failed:
        return "failed", "Failed", "❌", "#ef4444", final_err
    if is_read:
        return "read", "Read", "✓✓", "#38bdf8", None
    if is_delivered:
        return "delivered", "Delivered", "✓✓", "#94a3b8", None
    if is_queued:
        return "queued", "Queued", "⏳", "#f59e0b", None
    return "sent", "Sent", "✓", "#94a3b8", None


class UniversalHistoryService:

    @staticmethod
    def get_user_role_code(user: Any) -> str:
        """Extract uppercase role code string from StaffEmployee object or mock."""
        if not user:
            return ""
        r = getattr(user, "role", None)
        if r is not None:
            if hasattr(r, "role_code"):
                return str(r.role_code or "").upper()
            if isinstance(r, str):
                return r.upper()
        rc = getattr(user, "role_code", None)
        if rc:
            return str(rc).upper()
        return ""

    @classmethod
    def check_can_unmask_phone(cls, user: Any) -> bool:
        """Determine if requesting staff has unmasked phone view privilege."""
        if not user:
            return False
        role = cls.get_user_role_code(user)
        staff_type = str(getattr(user, "staff_type", "") or "").upper()
        admin_scope = str(getattr(user, "admin_scope", "") or "").upper()
        emp_code = str(getattr(user, "emp_code", "") or "").upper()

        if (
            "VGK" in staff_type or
            "VGK" in role or
            staff_type in ("SUPERADMIN", "ADMIN", "EA", "VGK_ADMIN", "SALES_INCHARGE", "TENANT_ADMIN", "SAAS_SEGMENT_ADMIN") or
            admin_scope in ("TENANT_ADMIN", "GLOBAL_ADMIN") or
            role in ("SUPERADMIN", "SUPER_ADMIN", "ADMIN", "EA", "MANAGEMENT", "DIRECTOR", "VGK4U", "KEY_LEADERSHIP", "LEADERSHIP_ROLE", "TENANT_ADMIN", "MANAGER") or
            emp_code in ("MN10009", "MN10003", "MN10008", "MN10010", "MR10018", "MR10001")
        ):
            return True
        caps = getattr(user, "capabilities", None) or []
        if isinstance(caps, list) and ("crm.leads.unmask_phone" in caps or "crm.admin" in caps or "admin" in caps):
            return True
        return False

    @classmethod
    def resolve_entity(
        cls,
        db: Session,
        entity_type: str,
        entity_id: int,
        current_user: StaffEmployee,
        phone: Optional[str] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate permissions and extract canonical entity details & phone numbers.
        Supports both ID-based lookup and phone/name fallback for Ground Sources and VGK Members.
        Returns:
            {
               "entity_type": "crm_lead" | "vgk_member",
               "entity_id": int,
               "name": str,
               "primary_phone": str,
               "display_phone": str,
               "phone_10digits": List[str],
               "status": str,
               "category": str,
               "company_id": Optional[int],
               "assigned_to": str
            }
        """
        can_unmask = cls.check_can_unmask_phone(current_user)

        if entity_type == "vgk_member":
            member = None
            if entity_id and int(entity_id) > 0:
                member = db.query(OfficialPartner).filter(
                    OfficialPartner.id == int(entity_id),
                    OfficialPartner.category == "VGK_TEAM"
                ).first()
                if not member:
                    member = db.query(OfficialPartner).filter(
                        OfficialPartner.id == int(entity_id)
                    ).first()

            if not member and phone:
                clean_digits = normalize_phone_digits(phone)
                if clean_digits:
                    member = db.query(OfficialPartner).filter(
                        or_(
                            OfficialPartner.phone.ilike(f"%{clean_digits}%"),
                            OfficialPartner.whatsapp_number.ilike(f"%{clean_digits}%")
                        )
                    ).order_by(
                        case((OfficialPartner.category == "VGK_TEAM", 1), else_=2)
                    ).first()

            if member:
                # Check visibility
                user_role = cls.get_user_role_code(current_user)
                user_type = str(getattr(current_user, "staff_type", "") or "").upper()
                admin_scope = str(getattr(current_user, "admin_scope", "") or "").upper()
                emp_code = str(getattr(current_user, "emp_code", "") or "").upper()
                is_vgk_admin = (
                    "VGK" in user_type or
                    "VGK" in user_role or
                    user_type in ("SUPERADMIN", "ADMIN", "EA", "VGK_ADMIN", "SALES_INCHARGE", "TENANT_ADMIN", "SAAS_SEGMENT_ADMIN") or
                    admin_scope in ("TENANT_ADMIN", "GLOBAL_ADMIN") or
                    user_role in ("SUPERADMIN", "SUPER_ADMIN", "ADMIN", "EA", "MANAGEMENT", "DIRECTOR", "VGK4U", "KEY_LEADERSHIP", "LEADERSHIP_ROLE", "TENANT_ADMIN", "MANAGER") or
                    emp_code in ("MN10009", "MN10003", "MN10008", "MN10010", "MR10018", "MR10001") or
                    getattr(current_user, "department_code", "") in ("VGK", "ADMIN", "MGMT")
                )
                if not is_vgk_admin:
                    caps = getattr(current_user, "capabilities", None) or []
                    has_view_cap = isinstance(caps, list) and ("crm.leads.view" in caps or "crm.leads.view_all" in caps or "crm.members.view" in caps)
                    if not has_view_cap and member.assigned_staff_id != current_user.id and member.registered_by_emp_code != current_user.emp_code:
                        raise PermissionError("Forbidden: You can only view history for your assigned VGK members.")

                primary_p = (member.phone or member.whatsapp_number or "").strip()
                digits = normalize_phone_digits(primary_p)
                phone_list = [digits] if digits else []

                # Check for alternate whatsapp
                alt_digits = normalize_phone_digits(member.whatsapp_number)
                if alt_digits and alt_digits not in phone_list:
                    phone_list.append(alt_digits)

                if phone:
                    p_digits = normalize_phone_digits(phone)
                    if p_digits and p_digits not in phone_list:
                        phone_list.append(p_digits)

                assigned_name = "Unassigned"
                if member.assigned_staff_id:
                    st = db.query(StaffEmployee).filter(StaffEmployee.id == member.assigned_staff_id).first()
                    if st:
                        assigned_name = getattr(st, "full_name", None) or getattr(st, "emp_code", None) or f"Staff #{getattr(st, 'id', '')}"

                p_name = member.partner_name or name or f"Partner #{member.partner_code or member.id}"
                disp_phone = mask_phone_number(primary_p or (phone_list[0] if phone_list else ""), can_unmask)

                return {
                    "entity_type": "vgk_member",
                    "entity_id": member.id,
                    "name": p_name,
                    "partner_code": member.partner_code or "",
                    "primary_phone": primary_p if can_unmask else mask_phone_number(primary_p, False),
                    "display_phone": disp_phone,
                    "phone_10digits": phone_list,
                    "status": "Active" if getattr(member, "is_active", True) else "Inactive",
                    "category": member.category or "VGK Team Partner",
                    "company_id": getattr(member, "company_id", None),
                    "assigned_to": assigned_name,
                    "is_blocked": bool(getattr(member, "is_blocked", False)),
                    "last_contact_at": member.last_contact_at.isoformat() if getattr(member, "last_contact_at", None) else None,
                }
            else:
                # If member object not in OfficialPartner, but phone or name is provided, synthesize member profile
                clean_p = normalize_phone_digits(phone or "")
                if not clean_p and not entity_id:
                    raise ValueError("VGK Member not found")

                disp_phone = mask_phone_number(clean_p, can_unmask)
                return {
                    "entity_type": "vgk_member",
                    "entity_id": int(entity_id) if entity_id else 0,
                    "name": name or (clean_p and f"Ground Source ({clean_p})") or "VGK Ground Source",
                    "partner_code": "VGK_GROUND",
                    "primary_phone": clean_p if can_unmask else mask_phone_number(clean_p, False),
                    "display_phone": disp_phone,
                    "phone_10digits": [clean_p] if clean_p else [],
                    "status": "Active",
                    "category": "VGK Member / Ground Source",
                    "company_id": None,
                    "assigned_to": "Ground Source Network",
                    "is_blocked": False,
                    "last_contact_at": None,
                }

        # Default entity_type == 'crm_lead'
        lead = db.query(CRMLead).filter(CRMLead.id == entity_id).first()
        if not lead:
            raise ValueError("CRM Lead not found")

        # RBAC Check for Lead
        user_role = cls.get_user_role_code(current_user)
        user_type = str(getattr(current_user, "staff_type", "") or "").upper()
        admin_scope = str(getattr(current_user, "admin_scope", "") or "").upper()
        emp_code = str(getattr(current_user, "emp_code", "") or "").upper()
        is_admin = (
            "VGK" in user_type or
            "VGK" in user_role or
            user_type in ("SUPERADMIN", "ADMIN", "EA", "VGK_ADMIN", "SALES_INCHARGE", "TENANT_ADMIN", "SAAS_SEGMENT_ADMIN") or
            admin_scope in ("TENANT_ADMIN", "GLOBAL_ADMIN") or
            user_role in ("SUPERADMIN", "SUPER_ADMIN", "ADMIN", "EA", "MANAGEMENT", "DIRECTOR", "VGK4U", "KEY_LEADERSHIP", "LEADERSHIP_ROLE", "TENANT_ADMIN", "MANAGER") or
            emp_code in ("MN10009", "MN10003", "MN10008", "MN10010", "MR10018", "MR10001")
        )
        if not is_admin:
            # Check company isolation safely via base_company_id or company_id
            user_comp = getattr(current_user, "base_company_id", None) or getattr(current_user, "company_id", None)
            lead_comp = getattr(lead, "company_id", None)
            if user_comp and lead_comp and user_comp != lead_comp:
                data_comps = getattr(current_user, "data_companies", None) or []
                if not (isinstance(data_comps, list) and lead_comp in data_comps):
                    raise PermissionError("Access denied: Tenant/Company mismatch.")

            # Check lead assignment association
            user_id = current_user.id
            is_assigned = (
                (getattr(lead, "handler_type", "") == "staff" and str(getattr(lead, "handler_id", "")) == str(user_id)) or
                getattr(lead, "telecaller_id", None) == user_id or
                getattr(lead, "field_staff_id", None) == user_id or
                getattr(lead, "technical_id", None) == user_id or
                getattr(lead, "associated_partner_id", None) == user_id or
                getattr(lead, "created_by_user_id", None) == user_id
            )
            caps = getattr(current_user, "capabilities", None) or []
            has_view_cap = isinstance(caps, list) and ("crm.leads.view" in caps or "crm.leads.view_all" in caps)
            if not (is_assigned or has_view_cap):
                raise PermissionError("Access denied: You do not have permission to view history for this lead.")

        # Phone resolution
        phone_list = []
        lead_p = (getattr(lead, "phone", None) or getattr(lead, "mobile_number", None) or "").strip()
        d = normalize_phone_digits(lead_p)
        if d:
            phone_list.append(d)

        alt_p = (getattr(lead, "alternate_phone", None) or "").strip()
        alt_d = normalize_phone_digits(alt_p)
        if alt_d and alt_d not in phone_list:
            phone_list.append(alt_d)

        # Query CRMLeadPhone table for any additional associated phones
        try:
            extra_phones = db.query(CRMLeadPhone.phone_norm).filter(CRMLeadPhone.lead_id == lead.id).all()
            for ep in extra_phones:
                ed = normalize_phone_digits(ep[0])
                if ed and ed not in phone_list:
                    phone_list.append(ed)
        except Exception as _pe:
            logger.warning(f"[UniversalHistory] CRMLeadPhone query warning: {_pe}")

        assigned_name = "Unassigned"
        if getattr(lead, "handler_type", None) == "staff" and lead.handler_id:
            try:
                st = db.query(StaffEmployee).filter(StaffEmployee.id == int(lead.handler_id)).first()
                if st:
                    assigned_name = getattr(st, "full_name", None) or getattr(st, "emp_code", None) or f"Staff #{st.id}"
            except Exception:
                pass
        elif getattr(lead, "telecaller_id", None):
            try:
                st = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
                if st:
                    assigned_name = getattr(st, "full_name", None) or getattr(st, "emp_code", None) or f"Staff #{st.id}"
            except Exception:
                pass

        return {
            "entity_type": "crm_lead",
            "entity_id": lead.id,
            "name": lead.name or f"Lead #{lead.id}",
            "partner_code": "",
            "primary_phone": lead_p if can_unmask else mask_phone_number(lead_p, False),
            "display_phone": mask_phone_number(lead_p, can_unmask),
            "phone_10digits": phone_list,
            "status": lead.status or "New",
            "stage": getattr(lead, "solar_pipeline_status", None) or getattr(lead, "status", None) or "",
            "category": getattr(lead, "category", None) or "",
            "company_id": lead.company_id,
            "assigned_to": assigned_name,
            "is_blocked": False,
            "last_contact_at": lead.last_contacted_at.isoformat() if getattr(lead, "last_contacted_at", None) else None,
        }

    @classmethod
    def get_calls_history(
        cls,
        db: Session,
        entity_info: Dict[str, Any],
        page: int = 1,
        limit: int = 50,
        current_user: Optional[StaffEmployee] = None
    ) -> Dict[str, Any]:
        """
        Aggregate and deduplicate calls across Plivo WebRTC, Native GSM, MyOperator, and AutoDialer.
        """
        phone_list = entity_info.get("phone_10digits") or []
        entity_id = entity_info["entity_id"]
        entity_type = entity_info["entity_type"]

        items: List[Dict[str, Any]] = []

        # 1. VoIP Call Sessions (Plivo WebRTC)
        try:
            sql_voip = """
                SELECT vcs.id, vcs.call_session_id, vcs.started_at, vcs.duration_seconds,
                       vcs.direction, vcs.status,
                       COALESCE(NULLIF(TRIM(vcs.operator_name), ''), se.full_name, NULLIF(TRIM(vcs.operator_user_ref), ''), 'Staff') AS operator_name,
                       COALESCE(vcs.operator_user_ref, se.emp_code, '') AS operator_user_ref,
                       vcs.recording_storage_key, vcs.recording_status, vcs.lead_id,
                       vcs.customer_phone, vcs.destination_number,
                       vcs.metadata_json
                FROM voip_call_sessions vcs
                LEFT JOIN staff_employees se ON (vcs.operator_id = se.id OR (vcs.operator_user_ref IS NOT NULL AND vcs.operator_user_ref = se.emp_code))
                WHERE (
                    vcs.lead_id = :lead_id
                    OR (
                        :has_phones = 1 AND (
                            RIGHT(REGEXP_REPLACE(COALESCE(vcs.customer_phone, ''), '[^0-9]', '', 'g'), 10) IN :phones
                            OR RIGHT(REGEXP_REPLACE(COALESCE(vcs.destination_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                        )
                    )
                )
                ORDER BY vcs.started_at DESC
                LIMIT 500
            """
            vcs_rows = db.execute(
                text(sql_voip),
                {
                    "lead_id": entity_id if entity_type == "crm_lead" else -1,
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in vcs_rows:
                dt = r[2]
                dur = int(r[3] or 0)
                sid = r[1]
                rec_key = r[8]
                rec_st = (r[9] or "").upper()
                has_rec = bool(rec_key or rec_st in ("AVAILABLE", "SAVED", "COMPLETED"))
                direction = (r[4] or "outbound").lower()
                c_status = (r[5] or "completed").capitalize()
                staff_name_val = r[6] or "Staff"

                meta_raw = r[13] if len(r) > 13 else None
                dialed_page = None
                if isinstance(meta_raw, dict):
                    dialed_page = meta_raw.get("dialed_page")
                elif isinstance(meta_raw, str) and meta_raw:
                    try:
                        dialed_page = json.loads(meta_raw).get("dialed_page")
                    except Exception:
                        dialed_page = None

                call_from = resolve_call_from(
                    source="softphone",
                    device_call_id=sid,
                    call_type=direction,
                    dialed_page=dialed_page,
                    matched_lead_id=r[10]
                )

                items.append({
                    "id": f"vcs_{r[0]}",
                    "raw_id": r[0],
                    "call_session_id": sid,
                    "source": "Plivo WebRTC",
                    "call_from": call_from,
                    "dialed_page": dialed_page or call_from,
                    "channel": "Web Softphone",
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "direction": direction,
                    "duration_seconds": dur,
                    "status": c_status,
                    "staff_name": staff_name_val,
                    "handled_by": staff_name_val,
                    "staff_emp_code": r[7] or "",
                    "has_recording": has_rec,
                    "recording_url": f"/api/v1/telephony/calls/{sid}/recording" if (has_rec and sid) else None,
                    "details": f"Softphone {direction} call ({dur}s)",
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] voip_call_sessions query failed: {_e}")

        # 2. Native Staff Call Logs (GSM / Mobile Call Tracking)
        try:
            sql_scl = """
                SELECT scl.id, scl.call_datetime, scl.call_type, scl.duration_seconds,
                       scl.has_recording, scl.recording_id, se.full_name, se.emp_code,
                       scl.source, scl.device_call_id, scl.matched_lead_id, scl.phone_number,
                       scl.dialed_page
                FROM staff_call_logs scl
                LEFT JOIN staff_employees se ON scl.staff_id = se.id
                WHERE (
                    scl.matched_lead_id = :lead_id
                    OR (
                        :has_phones = 1 AND
                        RIGHT(REGEXP_REPLACE(COALESCE(scl.phone_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                    )
                )
                ORDER BY scl.call_datetime DESC
                LIMIT 500
            """
            scl_rows = db.execute(
                text(sql_scl),
                {
                    "lead_id": entity_id if entity_type == "crm_lead" else -1,
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in scl_rows:
                source_tag = (r[8] or "").lower()
                dev_call_id = str(r[9] or "").lower()
                # Deduplication: suppress native mirrored softphone rows
                if source_tag in ("softphone", "webrtc") or dev_call_id.startswith("vcs_"):
                    continue

                dt = r[1]
                dur = int(r[3] or 0)
                rec_id = r[5]
                has_rec = bool(r[4] and rec_id)
                c_type = (r[2] or "OUTGOING").upper()
                direction = "inbound" if c_type == "INCOMING" else "outbound"
                status = "Answered" if dur > 0 else (c_type.capitalize() if c_type != "MISSED" else "Missed")
                scl_dialed = r[12] if len(r) > 12 else None
                call_from = resolve_call_from(
                    source=r[8] or "native",
                    device_call_id=r[9],
                    call_type=r[2],
                    dialed_page=scl_dialed,
                    matched_lead_id=r[10]
                )
                items.append({
                    "id": f"scl_{r[0]}",
                    "raw_id": r[0],
                    "call_session_id": None,
                    "source": "Native SIM",
                    "call_from": call_from,
                    "dialed_page": scl_dialed or call_from,
                    "channel": "Mobile SIM Call",
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "direction": direction,
                    "duration_seconds": dur,
                    "status": status,
                    "staff_name": r[6] or r[7] or "Staff",
                    "handled_by": r[6] or r[7] or "Staff",
                    "staff_emp_code": r[7] or "",
                    "has_recording": has_rec,
                    "recording_url": f"/api/v1/call-tracking/recordings/{rec_id}/stream" if has_rec else None,
                    "details": f"SIM {c_type.lower()} call ({dur}s)" if dur > 0 else f"SIM {c_type.lower()} call",
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] staff_call_logs query failed: {_e}")

        # 3. Central IVR / Office Trunk Calls (operator_calls)
        try:
            sql_mop = """
                SELECT oc.id, oc.caller_number, oc.called_number, oc.started_at,
                       oc.duration_seconds, oc.status, oc.recording_url,
                       oc.handled_by, oc.operator_name, oc.call_type, oc.call_id
                FROM operator_calls oc
                WHERE (
                    oc.crm_lead_id = :lead_id
                    OR (
                        :has_phones = 1 AND (
                            RIGHT(REGEXP_REPLACE(COALESCE(oc.caller_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                            OR RIGHT(REGEXP_REPLACE(COALESCE(oc.called_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                        )
                    )
                )
                ORDER BY oc.started_at DESC
                LIMIT 100
            """
            mop_rows = db.execute(
                text(sql_mop),
                {
                    "lead_id": entity_id if entity_type == "crm_lead" else -1,
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in mop_rows:
                dt = r[3]
                dur = int(r[4] or 0)
                rec_url = r[6]
                mop_staff = r[7] or r[8] or "IVR / Queue"
                call_type_raw = (r[9] or "inbound").lower()
                call_id_raw = str(r[10] or "")

                # Brand as Central IVR or Office Trunk (never display legacy MyOperator)
                if call_id_raw.startswith("plivo_") or call_id_raw.startswith("webrtc_") or call_id_raw.startswith("vcs_"):
                    src_label = "Central IVR"
                else:
                    src_label = "Office Trunk"

                if call_type_raw in ('inbound', 'incoming'):
                    call_from = "Inbound DID"
                else:
                    call_from = "Operator Calls"

                items.append({
                    "id": f"mop_{r[0]}",
                    "raw_id": r[0],
                    "call_session_id": None,
                    "source": src_label,
                    "call_from": call_from,
                    "dialed_page": call_from,
                    "channel": "Hotline Trunk",
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "direction": call_type_raw,
                    "duration_seconds": dur,
                    "status": (r[5] or "Completed").capitalize(),
                    "staff_name": mop_staff,
                    "handled_by": mop_staff,
                    "staff_emp_code": "",
                    "has_recording": bool(rec_url),
                    "recording_url": rec_url,
                    "details": f"{src_label} {call_type_raw} call ({dur}s)",
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] operator_calls query failed: {_e}")

        # 4. CRM Auto Dialer Attempts
        if entity_type == "crm_lead":
            try:
                sql_cda = """
                    SELECT cda.id, cda.session_id, cda.dialed_at, cda.duration_seconds,
                           cda.call_outcome, cda.note, cda.user_ref,
                           se.full_name
                    FROM crm_dialer_attempts cda
                    LEFT JOIN staff_employees se ON (cda.user_ref = se.emp_code OR (CASE WHEN cda.user_ref ~ '^[0-9]+$' THEN cda.user_ref::integer ELSE NULL END) = se.id)
                    WHERE cda.lead_id = :lead_id
                    ORDER BY cda.dialed_at DESC
                    LIMIT 500
                """
                cda_rows = db.execute(text(sql_cda), {"lead_id": entity_id}).fetchall()
                for r in cda_rows:
                    dt = r[2]
                    dur = int(r[3] or 0)
                    disp = r[4] or "Dial Attempt"
                    cda_staff = r[7] or r[6] or "Auto Dialer Agent"
                    items.append({
                        "id": f"cda_{r[0]}",
                        "raw_id": r[0],
                        "call_session_id": str(r[1]) if r[1] else None,
                        "source": "Auto Dialer",
                        "call_from": "Auto Dialer",
                        "dialed_page": "Auto Dialer",
                        "channel": "Campaign Dialer",
                        "timestamp": dt.isoformat() if dt else None,
                        "datetime_obj": dt,
                        "direction": "outbound",
                        "duration_seconds": dur,
                        "status": disp.capitalize(),
                        "staff_name": cda_staff,
                        "handled_by": cda_staff,
                        "staff_emp_code": r[6] or "",
                        "has_recording": False,
                        "recording_url": None,
                        "details": f"Auto dialer: {disp} ({dur}s)" if dur > 0 else f"Auto dialer: {disp}",
                    })
            except Exception as _e:
                db.rollback()
                logger.warning(f"[UniversalHistory] crm_dialer_attempts query failed: {_e}")

        # Smart Deduplication across Plivo / Native / AutoDialer:
        # If two calls have matching timestamp within 15 seconds and same duration within 5 seconds, keep the richer one (e.g. Plivo/AutoDialer with recording)
        deduped: List[Dict[str, Any]] = []
        seen_timestamps: List[Tuple[float, int, str]] = []

        # Sort reverse chronological first
        def get_ts_float(item: Dict[str, Any]) -> float:
            dto = item.get("datetime_obj")
            if dto and isinstance(dto, datetime):
                return dto.timestamp()
            return 0.0

        items.sort(key=get_ts_float, reverse=True)

        for item in items:
            ts = get_ts_float(item)
            dur = item.get("duration_seconds") or 0
            is_dup = False
            for seen_ts, seen_dur, seen_src in seen_timestamps:
                if abs(ts - seen_ts) <= 15 and abs(dur - seen_dur) <= 5:
                    # Duplicate found
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(item)
                seen_timestamps.append((ts, dur, item["source"]))

        total_count = len(deduped)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = deduped[start_idx:end_idx]

        # Enrich with Quality Review score/status
        try:
            scl_ids = [it["raw_id"] for it in paginated_items if it.get("source") == "Native SIM" and it.get("raw_id")]
            rev_map = {}
            if scl_ids:
                rev_rows = db.query(CallQualityReview.call_log_id, CallQualityReview.id, CallQualityReview.status, CallQualityReview.overall_score).filter(
                    CallQualityReview.call_log_id.in_(scl_ids)
                ).all()
                for rr in rev_rows:
                    rev_map[f"scl_{rr[0]}"] = {"review_id": rr[1], "status": rr[2], "overall_score": rr[3]}
            for it in paginated_items:
                qr = rev_map.get(f"scl_{it.get('raw_id')}")
                if qr:
                    it["quality_review_id"] = qr["review_id"]
                    it["quality_status"] = qr["status"]
                    it["quality_score"] = qr["overall_score"]
                else:
                    it["quality_review_id"] = None
                    it["quality_status"] = None
                    it["quality_score"] = None
        except Exception as _qr_e:
            pass

        # Clean non-serializable datetime_obj
        for it in paginated_items:
            it.pop("datetime_obj", None)

        return {
            "total_calls": total_count,
            "page": page,
            "limit": limit,
            "has_more": end_idx < total_count,
            "items": paginated_items,
        }

    @classmethod
    def get_messages_history(
        cls,
        db: Session,
        entity_info: Dict[str, Any],
        page: int = 1,
        limit: int = 50,
        current_user: Optional[StaffEmployee] = None
    ) -> Dict[str, Any]:
        """
        Pure read-only query for WhatsApp and SMS messages. Zero state mutation.
        Provides full delivery statuses (Failed, Delivered, Read, Sent, Queued, Received),
        rich media resolution (images, PDFs, documents, audio voice notes), and deduplication.
        """
        phone_list = entity_info.get("phone_10digits") or []
        entity_type = entity_info.get("entity_type") or "crm_lead"
        entity_id = entity_info.get("entity_id") or 0

        if not phone_list and not entity_id:
            return {"total_messages": 0, "page": page, "limit": limit, "has_more": False, "items": []}

        items: List[Dict[str, Any]] = []
        seen_wamids = set()
        seen_bodies = set()
        seen_time_body_keys = set()

        # 1. Outbound WhatsApp/SMS from message_log (Primary source for outbound dispatch + delivery statuses)
        try:
            sql_ml = """
                SELECT ml.id, ml.message_body, ml.sent_at, ml.sender_type, ml.sent_by_name,
                       ml.message_type, ml.current_status, ml.provider, ml.to_number,
                       ml.webhook_data, ml.error_code, ml.error_message, ml.failure_reason,
                       ml.delivered_at, ml.read_at, ml.failed_at, ml.message_sid,
                       ml.from_number, ml.mobile_number
                FROM message_log ml
                WHERE (
                    :has_phones = 1 AND (
                        RIGHT(REGEXP_REPLACE(COALESCE(ml.mobile_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                        OR RIGHT(REGEXP_REPLACE(COALESCE(ml.to_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                        OR RIGHT(REGEXP_REPLACE(COALESCE(ml.from_number, ''), '[^0-9]', '', 'g'), 10) IN :phones
                    )
                )
                ORDER BY ml.sent_at DESC
                LIMIT 200
            """
            ml_rows = db.execute(
                text(sql_ml),
                {
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in ml_rows:
                row_id = r[0]
                raw_body = r[1] or ""
                dt = r[2]
                sender_type = r[3] or "staff"
                sent_by_name = r[4] or "Staff"
                msg_type = r[5] or "text"
                curr_status = r[6] or "sent"
                prov = r[7] or "WhatsApp"
                to_num = r[8] or ""
                wb_data_raw = r[9]
                err_code = r[10]
                err_msg = r[11]
                fail_rsn = r[12]
                deliv_at = r[13]
                read_at = r[14]
                failed_at = r[15]
                msg_sid = str(r[16] or "")

                # Parse webhook_data for media or status metadata
                raw_media_url = None
                media_mime = None
                media_name = None
                if wb_data_raw:
                    try:
                        wb_parsed = json.loads(wb_data_raw) if isinstance(wb_data_raw, str) else wb_data_raw
                        if isinstance(wb_parsed, dict):
                            raw_media_url = wb_parsed.get("media_url")
                            media_mime = wb_parsed.get("media_mime_type")
                            media_name = wb_parsed.get("media_name")
                    except Exception:
                        pass

                final_media_url, media_type, final_mime, final_name, cleaned_text = resolve_media_attachment(
                    raw_url=raw_media_url,
                    mime_type=media_mime,
                    media_name=media_name,
                    body_text=raw_body,
                )

                st, st_label, st_ticks, st_color, final_fail_reason = resolve_message_status(
                    raw_status=curr_status,
                    direction="outbound",
                    failed_at=failed_at,
                    failure_reason=fail_rsn,
                    error_message=err_msg,
                    error_code=err_code,
                    delivered_at=deliv_at,
                    read_at=read_at,
                )

                # Channel labeling
                prov_str = (prov or "").upper()
                is_meta = ("META" in prov_str or msg_sid.startswith("wamid."))
                chan_label = "WhatsApp (Official)" if is_meta else "WhatsApp (Scanned)" if "BAIL" in prov_str else f"WhatsApp ({prov})"

                # Tracking for deduplication
                if msg_sid:
                    seen_wamids.add(msg_sid)
                if cleaned_text:
                    seen_bodies.add(cleaned_text[:120].strip())
                if dt:
                    time_bucket = int(dt.timestamp() // 20)
                    seen_time_body_keys.add((time_bucket, cleaned_text[:60].strip()))

                items.append({
                    "id": f"ml_{row_id}",
                    "raw_id": row_id,
                    "wamid": msg_sid or None,
                    "type": "message",
                    "channel": chan_label,
                    "direction": "outbound",
                    "sender_name": sent_by_name if sent_by_name not in ("Staff", "Staff / System") else "Mynt Staff",
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "status": st,
                    "status_label": st_label,
                    "status_ticks": st_ticks,
                    "status_color": st_color,
                    "failure_reason": final_fail_reason,
                    "error_message": err_msg,
                    "error_code": err_code,
                    "delivered_at": deliv_at.isoformat() if deliv_at else None,
                    "read_at": read_at.isoformat() if read_at else None,
                    "message_text": cleaned_text or raw_body,
                    "media_url": final_media_url,
                    "media_type": media_type,
                    "media_mime_type": final_mime,
                    "media_name": final_name,
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] message_log query failed: {_e}")

        # 2. Inbound WhatsApp messages from wa_inbox (and unique outbound not mirrored in message_log)
        try:
            sql_wi = """
                SELECT wi.id, wi.body_text, wi.from_name, wi.message_type, wi.received_at,
                       wi.media_url, wi.from_phone, wi.media_mime_type, wi.status, wi.wamid
                FROM wa_inbox wi
                WHERE (
                    (:lead_id > 0 AND (wi.crm_lead_id = :lead_id OR wi.lead_id = :lead_id))
                    OR (
                        :has_phones = 1 AND RIGHT(REGEXP_REPLACE(COALESCE(wi.from_phone, ''), '[^0-9]', '', 'g'), 10) IN :phones
                    )
                )
                ORDER BY wi.received_at DESC
                LIMIT 200
            """
            wi_rows = db.execute(
                text(sql_wi),
                {
                    "lead_id": entity_id if entity_type == "crm_lead" else -1,
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in wi_rows:
                row_id = r[0]
                raw_body = r[1] or ""
                from_name = r[2] or ""
                m_type = str(r[3] or "text").lower()
                dt = r[4]
                raw_media_url = r[5]
                from_phone = r[6]
                media_mime = r[7]
                raw_status = r[8]
                wamid = str(r[9] or "")

                final_media_url, media_type, final_mime, final_name, cleaned_text = resolve_media_attachment(
                    raw_url=raw_media_url,
                    mime_type=media_mime,
                    media_name=None,
                    body_text=raw_body,
                )

                is_outbound = (m_type == "outbound" or m_type.startswith("auto_"))
                time_bucket = int(dt.timestamp() // 20) if dt else 0

                # Deduplicate dual-writes against message_log
                if wamid and wamid in seen_wamids:
                    continue
                if is_outbound and (cleaned_text[:120].strip() in seen_bodies or (time_bucket, cleaned_text[:60].strip()) in seen_time_body_keys):
                    continue

                if wamid:
                    seen_wamids.add(wamid)
                if cleaned_text:
                    seen_bodies.add(cleaned_text[:120].strip())
                if dt:
                    seen_time_body_keys.add((time_bucket, cleaned_text[:60].strip()))

                direction = "outbound" if is_outbound else "inbound"
                st, st_label, st_ticks, st_color, final_fail_reason = resolve_message_status(
                    raw_status=raw_status,
                    direction=direction,
                )

                sender_name = from_name or entity_info.get("name") or "Customer"
                if is_outbound:
                    sender_name = "Mynt Staff / System"

                items.append({
                    "id": f"wi_{row_id}",
                    "raw_id": row_id,
                    "wamid": wamid or None,
                    "type": "message",
                    "channel": "WhatsApp",
                    "direction": direction,
                    "sender_name": sender_name,
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "status": st,
                    "status_label": st_label,
                    "status_ticks": st_ticks,
                    "status_color": st_color,
                    "failure_reason": final_fail_reason,
                    "error_message": None,
                    "error_code": None,
                    "delivered_at": None,
                    "read_at": None,
                    "message_text": cleaned_text or raw_body,
                    "media_url": final_media_url,
                    "media_type": media_type,
                    "media_mime_type": final_mime,
                    "media_name": final_name,
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] wa_inbox query failed: {_e}")

        # 3. WhatsApp Campaign Logs
        try:
            sql_wcl = """
                SELECT wcl.id, wcl.recipient_name, wcl.status, wcl.sent_at, wcl.campaign_id, wcl.template_id,
                       wcl.error_message, wcl.delivered_at, wcl.read_at, wcl.failed_at, wcl.wamid
                FROM whatsapp_campaign_logs wcl
                WHERE (
                    (:lead_id > 0 AND wcl.lead_id = :lead_id)
                    OR (
                        :has_phones = 1 AND RIGHT(REGEXP_REPLACE(COALESCE(wcl.phone, ''), '[^0-9]', '', 'g'), 10) IN :phones
                    )
                )
                ORDER BY wcl.sent_at DESC
                LIMIT 100
            """
            wcl_rows = db.execute(
                text(sql_wcl),
                {
                    "lead_id": entity_id if entity_type == "crm_lead" else -1,
                    "has_phones": 1 if phone_list else 0,
                    "phones": tuple(phone_list) if phone_list else ("__none__",),
                }
            ).fetchall()

            for r in wcl_rows:
                row_id = r[0]
                recip_name = r[1]
                raw_st = r[2]
                dt = r[3]
                camp_id = r[4]
                tmpl_id = r[5]
                err_msg = r[6]
                deliv_at = r[7]
                read_at = r[8]
                failed_at = r[9]
                wamid = str(r[10] or "")

                if wamid and wamid in seen_wamids:
                    continue

                st, st_label, st_ticks, st_color, final_fail_reason = resolve_message_status(
                    raw_status=raw_st,
                    direction="outbound",
                    failed_at=failed_at,
                    failure_reason=err_msg,
                    error_message=err_msg,
                    delivered_at=deliv_at,
                    read_at=read_at,
                )

                items.append({
                    "id": f"wcl_{row_id}",
                    "raw_id": row_id,
                    "wamid": wamid or None,
                    "type": "message",
                    "channel": "WhatsApp Campaign",
                    "direction": "outbound",
                    "sender_name": f"Campaign #{camp_id}" if camp_id else "Automated Campaign",
                    "timestamp": dt.isoformat() if dt else None,
                    "datetime_obj": dt,
                    "status": st,
                    "status_label": st_label,
                    "status_ticks": st_ticks,
                    "status_color": st_color,
                    "failure_reason": final_fail_reason,
                    "error_message": err_msg,
                    "error_code": None,
                    "delivered_at": deliv_at.isoformat() if deliv_at else None,
                    "read_at": read_at.isoformat() if read_at else None,
                    "message_text": f"Template: {tmpl_id}" if tmpl_id else (recip_name or "Campaign message"),
                    "media_url": None,
                    "media_type": None,
                    "media_mime_type": None,
                    "media_name": None,
                })
        except Exception as _e:
            db.rollback()
            logger.warning(f"[UniversalHistory] whatsapp_campaign_logs query failed: {_e}")

        # Sort reverse chronological by timestamp
        def get_ts_float(item: Dict[str, Any]) -> float:
            dto = item.get("datetime_obj")
            if dto and isinstance(dto, datetime):
                return dto.timestamp()
            return 0.0

        items.sort(key=get_ts_float, reverse=True)

        total_count = len(items)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = items[start_idx:end_idx]

        for it in paginated_items:
            it.pop("datetime_obj", None)

        return {
            "total_messages": total_count,
            "page": page,
            "limit": limit,
            "has_more": end_idx < total_count,
            "items": paginated_items,
        }

    @classmethod
    def get_changes_history(
        cls,
        db: Session,
        entity_info: Dict[str, Any],
        subfilter: str = "all",
        page: int = 1,
        limit: int = 50,
        current_user: Optional[StaffEmployee] = None
    ) -> Dict[str, Any]:
        """
        Unified chronological audit timeline merging:
          - Field audit edits (CRMLeadAuditLog)
          - Notes (CRMLeadNote)
          - Scheduled Follow-ups (CRMLeadFollowUp)
          - Lead Assignments (CRMLeadAssignment)
        """
        entity_id = entity_info["entity_id"]
        entity_type = entity_info["entity_type"]

        if entity_type == "vgk_member":
            # For VGK Team Member, return partner profile history and assignment
            items = [{
                "id": "vgk_info_1",
                "category": "assignment",
                "event_type": "Channel Partner Active",
                "title": f"Assigned to {entity_info.get('assigned_to', 'Unassigned')}",
                "author_name": "System / Superadmin",
                "timestamp": entity_info.get("last_contact_at"),
                "details": f"Partner Code: {entity_info.get('partner_code')}, Status: {entity_info.get('status')}",
                "old_val": None,
                "new_val": None,
            }]
            return {"total_changes": len(items), "page": page, "limit": limit, "has_more": False, "items": items}

        items: List[Dict[str, Any]] = []

        # 1. Audit Logs (Field changes)
        if subfilter in ("all", "audit", "field_changes"):
            try:
                audit_entries = (
                    db.query(CRMLeadAuditLog)
                    .filter(CRMLeadAuditLog.lead_id == entity_id)
                    .order_by(CRMLeadAuditLog.changed_at.desc())
                    .limit(100)
                    .all()
                )
                for e in audit_entries:
                    f_name = (e.field_name or "Field").replace("_", " ").title()
                    items.append({
                        "id": f"audit_{e.id}",
                        "category": "audit",
                        "event_type": "Field Changed",
                        "title": f_name,
                        "author_name": e.changed_by_name or "Staff",
                        "author_type": e.changed_by_type,
                        "timestamp": e.changed_at.isoformat() if e.changed_at else None,
                        "datetime_obj": e.changed_at,
                        "old_val": str(e.old_value) if e.old_value is not None else "",
                        "new_val": str(e.new_value) if e.new_value is not None else "",
                        "details": f"Updated {f_name}",
                    })
            except Exception as _e:
                db.rollback()
                logger.warning(f"[UniversalHistory] CRMLeadAuditLog query failed: {_e}")

        # 2. Notes
        if subfilter in ("all", "notes"):
            try:
                notes = (
                    db.query(CRMLeadNote)
                    .filter(CRMLeadNote.lead_id == entity_id)
                    .order_by(CRMLeadNote.created_at.desc())
                    .limit(100)
                    .all()
                )
                for n in notes:
                    n_type = (getattr(n, "note_type", None) or "General").title()
                    n_text = getattr(n, "note", None) or getattr(n, "note_text", None) or ""
                    auth_name = getattr(n, "author_name", None)
                    if not auth_name:
                        cid = getattr(n, "created_by_id", None)
                        ctype = getattr(n, "created_by_type", "staff") or "staff"
                        if cid and str(cid).isdigit() and ctype == "staff":
                            st = db.query(StaffEmployee).filter(StaffEmployee.id == int(cid)).first()
                            auth_name = getattr(st, "full_name", None) or getattr(st, "emp_code", None) or f"Staff #{cid}"
                        else:
                            auth_name = f"{ctype.title()} #{cid}" if cid else "Staff"

                    items.append({
                        "id": f"note_{n.id}",
                        "category": "note",
                        "event_type": f"Note: {n_type}",
                        "title": "Lead Note Added",
                        "author_name": auth_name,
                        "author_type": getattr(n, "created_by_type", "staff") or "staff",
                        "timestamp": n.created_at.isoformat() if n.created_at else None,
                        "datetime_obj": n.created_at,
                        "old_val": None,
                        "new_val": None,
                        "details": n_text,
                    })
            except Exception as _e:
                db.rollback()
                logger.warning(f"[UniversalHistory] CRMLeadNote query failed: {_e}")

        # 3. Follow-Ups
        if subfilter in ("all", "followups"):
            try:
                followups = (
                    db.query(CRMLeadFollowUp)
                    .filter(CRMLeadFollowUp.lead_id == entity_id)
                    .order_by(CRMLeadFollowUp.created_at.desc())
                    .limit(100)
                    .all()
                )
                for fu in followups:
                    dt_sched = getattr(fu, "scheduled_date", None) or getattr(fu, "scheduled_at", None)
                    sched = dt_sched.isoformat() if dt_sched else "No date"
                    status_str = (fu.status or "Scheduled").title()
                    disp = getattr(fu, "outcome", None) or getattr(fu, "disposition", None) or getattr(fu, "subject", "") or ""
                    disp_str = f" [{disp}]" if disp else ""
                    items.append({
                        "id": f"fu_{fu.id}",
                        "category": "followup",
                        "event_type": f"Follow-Up: {status_str}",
                        "title": f"Follow-Up ({status_str}{disp_str})",
                        "author_name": getattr(fu, "created_by_id", None) and f"Staff #{fu.created_by_id}" or "Assigned Staff",
                        "author_type": getattr(fu, "created_by_type", "staff") or "staff",
                        "timestamp": fu.created_at.isoformat() if fu.created_at else None,
                        "datetime_obj": fu.created_at,
                        "old_val": None,
                        "new_val": f"Scheduled for {sched}",
                        "details": fu.notes or "No notes provided",
                    })
            except Exception as _e:
                db.rollback()
                logger.warning(f"[UniversalHistory] CRMLeadFollowUp query failed: {_e}")

        # 4. Assignments
        if subfilter in ("all", "assignments"):
            try:
                assignments = (
                    db.query(CRMLeadAssignment)
                    .filter(CRMLeadAssignment.lead_id == entity_id)
                    .order_by(CRMLeadAssignment.assigned_at.desc())
                    .limit(50)
                    .all()
                )
                for a in assignments:
                    to_name = f"{a.to_handler_type or 'Staff'} #{a.to_handler_id or ''}"
                    if a.to_handler_type == "staff" and a.to_handler_id and str(a.to_handler_id).isdigit():
                        to_staff = db.query(StaffEmployee).filter(StaffEmployee.id == int(a.to_handler_id)).first()
                        if to_staff:
                            to_name = getattr(to_staff, "full_name", None) or getattr(to_staff, "emp_code", None) or f"Staff #{a.to_handler_id}"

                    by_name = f"{a.assigned_by_type or 'User'} #{a.assigned_by_id or ''}"
                    if a.assigned_by_type == "staff" and a.assigned_by_id and str(a.assigned_by_id).isdigit():
                        by_staff = db.query(StaffEmployee).filter(StaffEmployee.id == int(a.assigned_by_id)).first()
                        if by_staff:
                            by_name = getattr(by_staff, "full_name", None) or getattr(by_staff, "emp_code", None) or f"Staff #{a.assigned_by_id}"

                    items.append({
                        "id": f"asgn_{a.id}",
                        "category": "assignment",
                        "event_type": f"Assignment: {(a.to_handler_type or 'Owner').title()}",
                        "title": f"Reassigned to {to_name}",
                        "author_name": by_name,
                        "author_type": a.assigned_by_type or "admin",
                        "timestamp": a.assigned_at.isoformat() if a.assigned_at else None,
                        "datetime_obj": a.assigned_at,
                        "old_val": None,
                        "new_val": to_name,
                        "details": a.reason or f"Assigned to {to_name}",
                    })
            except Exception as _e:
                db.rollback()
                logger.warning(f"[UniversalHistory] CRMLeadAssignment query failed: {_e}")

        # 4b. Field Appointments & Supporting Staff Visits
        if subfilter in ("all", "appointments", "visits"):
            try:
                from app.models.crm_field_appointment import CRMFieldAppointment
                appts = (
                    db.query(CRMFieldAppointment)
                    .filter(CRMFieldAppointment.lead_id == entity_id)
                    .order_by(CRMFieldAppointment.created_at.desc())
                    .limit(50)
                    .all()
                )
                for ap in appts:
                    v_type_title = (ap.visit_type or "visit").replace('_', ' ').title()
                    status_title = (ap.status or "assigned").replace('_', ' ').title()
                    dt_created = ap.created_at
                    author_name = ap.creator.full_name if ap.creator else "Tele-caller"
                    assignee_name = ap.assigned_to.full_name if ap.assigned_to else "Staff"

                    detail_parts = [
                        f"Type: {v_type_title}",
                        f"Assigned To: {assignee_name}",
                        f"Status: {status_title}",
                        f"Date: {ap.appointment_date}"
                    ]
                    if ap.purpose:
                        detail_parts.append(f"Purpose: {ap.purpose}")
                    if ap.telecaller_instructions:
                        detail_parts.append(f"Instructions: {ap.telecaller_instructions}")
                    if ap.outcome_summary:
                        detail_parts.append(f"Outcome: {ap.outcome_summary}")
                    if ap.is_gps_verified:
                        detail_parts.append(f"GPS Verified ({ap.visit_latitude:.4f}, {ap.visit_longitude:.4f})")
                    if ap.photo_path:
                        detail_parts.append(f"Evidence Photo Attached")

                    items.append({
                        "id": f"appt_{ap.id}",
                        "category": "appointment",
                        "event_type": f"Appointment: {status_title}",
                        "title": f"Field Appointment ({v_type_title})",
                        "author_name": author_name,
                        "author_type": "staff",
                        "timestamp": dt_created.isoformat() if dt_created else None,
                        "datetime_obj": dt_created,
                        "old_val": None,
                        "new_val": f"{status_title} - {assignee_name}",
                        "details": " | ".join(detail_parts),
                        "photo_url": ap.photo_path or ap.compressed_photo_path,
                        "is_gps_verified": ap.is_gps_verified,
                        "appointment_code": ap.appointment_code,
                    })
            except Exception as _ae:
                db.rollback()
                logger.warning(f"[UniversalHistory] CRMFieldAppointment query failed: {_ae}")

        # 5. Calls (Included in All Changes and Calls subfilter)
        if subfilter in ("all", "calls"):

            try:
                calls_res = cls.get_calls_history(db=db, entity_info=entity_info, page=1, limit=100, current_user=current_user)
                for c in (calls_res.get("items") or []):
                    if not isinstance(c, dict) or not c.get("id"):
                        continue
                    handled_by = c.get("handled_by") or c.get("staff_name") or "Staff"
                    dur = c.get("duration_seconds") or 0
                    c_status = c.get("status") or "Completed"
                    c_dir = (c.get("direction") or "Call").capitalize()
                    c_src = c.get("source") or "Call"
                    items.append({
                        "id": f"call_evt_{c['id']}",
                        "category": "call",
                        "event_type": f"Call: {c_dir}",
                        "title": f"Phone Call ({c_src} • {c_dir})",
                        "author_name": handled_by,
                        "handled_by": handled_by,
                        "author_type": "staff",
                        "timestamp": c.get("timestamp"),
                        "datetime_obj": c.get("datetime_obj"),
                        "old_val": None,
                        "new_val": f"Handled by: {handled_by}",
                        "details": f"{c.get('details') or f'{c_dir} call'} • Status: {c_status}",
                        "duration_seconds": dur,
                        "has_recording": c.get("has_recording", False),
                        "recording_url": c.get("recording_url"),
                    })
            except Exception as _ce:
                logger.warning(f"[UniversalHistory] calls aggregation for changes failed: {_ce}")

        # Sort reverse chronological
        def get_ts_float(item: Dict[str, Any]) -> float:
            dto = item.get("datetime_obj")
            if dto and isinstance(dto, datetime):
                return dto.timestamp()
            return 0.0

        items.sort(key=get_ts_float, reverse=True)

        total_count = len(items)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = items[start_idx:end_idx]

        for it in paginated_items:
            it.pop("datetime_obj", None)

        return {
            "total_changes": total_count,
            "subfilter": subfilter,
            "page": page,
            "limit": limit,
            "has_more": end_idx < total_count,
            "items": paginated_items,
        }

    @classmethod
    def get_extensions_directory(cls, db: Session, company_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns authoritative IVR Department keypad extensions, Staff extensions directory,
        and Segment routing rules for Universal History.
        """
        departments = [
            {
                "key": "1",
                "name": "Solar Solutions",
                "segment": "solar",
                "description": "Rooftop & Commercial Solar EPC, Net Metering, PM Surya Ghar",
                "announcement_en": "Connecting your call to our Solar Solutions team. Please hold the line.",
                "announcement_te": "మా సోలార్ సొల్యూషన్స్ బృందానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "2",
                "name": "Insurance Advisory",
                "segment": "insurance",
                "description": "General, Health, Motor & Commercial Risk Advisory",
                "announcement_en": "Connecting your call to our Insurance Advisory desk. Please hold the line.",
                "announcement_te": "మా ఇన్సూరెన్స్ అడ్వైజరీ విభాగానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "3",
                "name": "Training Desk (EV Training / ETC)",
                "segment": "etc_training",
                "description": "EV Technician Training, Skill Development & Certification",
                "announcement_en": "Connecting your call to our Training desk. Please hold the line.",
                "announcement_te": "మా ట్రైనింగ్ విభాగానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "4",
                "name": "Manthra EV",
                "segment": "ev_b2b / ev_b2c / ev_spares",
                "description": "Electric Scooters, Spares, Dealerships & Fleet Mobility",
                "announcement_en": "Connecting your call to our Manthra E V team. Please hold the line.",
                "announcement_te": "మా మంత్ర ఈవీ బృందానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "5",
                "name": "VGK 4U / Real Dreams",
                "segment": "vgk_4u / real_dreams",
                "description": "Real Estate Advisory, Housing Projects & Community Services",
                "announcement_en": "Connecting your call to our V G K 4 U desk. Please hold the line.",
                "announcement_te": "మా వి జీ కే ఫర్ యు విభాగానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "6",
                "name": "Service Support",
                "segment": "service / support",
                "description": "Field Technicians, Warranty Claims, Installations & Repairs",
                "announcement_en": "Connecting your call to our Service and Support team. Please hold the line.",
                "announcement_te": "మా సర్వీస్ మరియు సపోర్ట్ బృందానికి మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "9",
                "name": "Customer Care Executives",
                "segment": "customer_care",
                "description": "Direct Customer Care & Inbound Concierge Desk",
                "announcement_en": "Connecting you to our Customer Care Executives. Please hold the line.",
                "announcement_te": "మా కస్టమర్ కేర్ ఎగ్జిక్యూటివ్‌లకు మీ కాల్‌ను కనెక్ట్ చేస్తున్నాము. దయచేసి వేచి ఉండండి."
            },
            {
                "key": "0",
                "name": "Main Menu Replay",
                "segment": "main_menu",
                "description": "Replay IVR bilingual options (Telugu / English)",
                "announcement_en": "Replaying menu options.",
                "announcement_te": "మెనూని మళ్లీ వినండి."
            }
        ]

        from app.models.staff import StaffDepartment
        from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember
        from app.models.signup_category import SignupCategory

        staff_employees = db.query(StaffEmployee).filter(
            StaffEmployee.status.in_(['active', 'ACTIVE']),
            StaffEmployee.is_deleted == False
        ).order_by(StaffEmployee.department_id, StaffEmployee.id).all()

        depts_map = {d.id: d.name for d in db.query(StaffDepartment).all()}

        active_handlers = db.query(CRMLeadHandler).filter(CRMLeadHandler.is_active == True).all()
        staff_segments = {}
        for h in active_handlers:
            cat = db.query(SignupCategory).filter(SignupCategory.id == h.category_id).first() if h.category_id else None
            cat_name = cat.name if cat else 'General'
            members = db.query(CRMLeadHandlerMember).filter(
                CRMLeadHandlerMember.handler_id == h.id,
                CRMLeadHandlerMember.is_active == True
            ).all()
            for m in members:
                staff_segments.setdefault(m.employee_id, set()).add(cat_name)

        staff_list = []
        used_exts = set()

        for s in staff_employees:
            ext = cls.get_staff_extension_number(s)
            if not ext:
                continue

            # Ensure set-based uniqueness if any future additions collide
            candidate_ext = ext
            inc = 1
            while candidate_ext in used_exts:
                next_val = int(candidate_ext) + 1
                if next_val > 99:
                    next_val = 10
                candidate_ext = f"{next_val:02d}"
                inc += 1
            used_exts.add(candidate_ext)

            emp_code = str(s.emp_code or "").strip()
            full_name = s.full_name or f"{s.first_name or ''} {s.last_name or ''}".strip() or emp_code
            dept_name = depts_map.get(s.department_id, 'General')
            segs = sorted(list(staff_segments.get(s.id, [])))

            staff_list.append({
                "id": s.id,
                "emp_code": emp_code,
                "name": full_name,
                "extension": candidate_ext,
                "department": dept_name,
                "segments": segs,
                "phone": mask_phone_number(getattr(s, "phone", "") or getattr(s, "contact_number", "") or "", can_unmask=True)
            })

        routing_rules = {
            "first_time_call": "When a first-time caller selects an IVR Department (Segment), the system resolves active CRM Lead Handlers for that segment and dials all online members simultaneously in parallel.",
            "direct_extension": "Callers entering a staff extension (e.g. 16, 36, 66) are routed directly to the employee's softphone SIP endpoint.",
            "sticky_returning_call": "Returning callers with existing CRM leads or recent VoIP call sessions bypass the menu and connect directly to their dedicated lead owner or telecaller.",
            "ivr_numbers": "+91 85858 52738 | +91 8897797667"
        }

        return {
            "departments": departments,
            "staff": staff_list,
            "routing_rules": routing_rules
        }

    @classmethod
    def get_staff_extension_number(cls, staff_emp: Any) -> Optional[str]:
        """
        Authoritative single-source-of-truth 2-digit extension derivation for staff employees.
        Guarantees unique 2-digit PBX extensions (10-99):
          - MR (Mynt Real) -> e.g. MR10016 -> 16, MR10036 -> 36
          - MN (Manthra EV) -> e.g. MN10008 -> 58, MN10016 -> 66
          - FL (Freelancer) -> e.g. FL10004 -> 44
        Excludes System Administrator (MR10001) and automated test accounts.
        """
        if not staff_emp:
            return None
        emp_code = str(getattr(staff_emp, "emp_code", "") or (staff_emp if isinstance(staff_emp, str) else "")).strip().upper()
        full_name = str(getattr(staff_emp, "full_name", "") or "").strip().upper()

        if emp_code == "MR10001" or "SYSTEM ADMINISTRATOR" in full_name:
            return None
        if emp_code.startswith(('EMP_', 'SA_', 'TEST_', 'ZYLOG_', 'AIS_', 'ZMP', 'TECO_')) or 'TEST' in full_name:
            return None

        m = re.search(r'(\d{1,4})$', emp_code)
        if not m:
            return None
        num = int(m.group(1))
        last2 = num % 100

        if emp_code.startswith('MR'):
            val = last2 if last2 >= 10 else last2 + 10
            return f"{val:02d}"
        elif emp_code.startswith('MN'):
            val = 50 + (last2 % 50)
            return f"{val:02d}"
        elif emp_code.startswith('FL'):
            val = 40 + (last2 % 10)
            return f"{val:02d}"
        val = 80 + (last2 % 20)
        return f"{val:02d}"

    @classmethod
    def resolve_staff_by_extension(cls, db: Session, extension: str) -> Optional[StaffEmployee]:
        """
        Reverse-lookup: finds active staff member corresponding to dialed extension.
        Matches 2-digit derived extension (e.g. '16', '36', '66'),
        and retains backward compatibility for legacy 3-digit dialing (e.g. '116', '136', '216').
        """
        clean_ext = str(extension or "").strip()
        if not clean_ext:
            return None

        staff_employees = db.query(StaffEmployee).filter(
            StaffEmployee.status.in_(['active', 'ACTIVE']),
            StaffEmployee.is_deleted == False
        ).all()

        # 1. Exact match with current 2-digit extension
        for s in staff_employees:
            if cls.get_staff_extension_number(s) == clean_ext:
                return s

        # 2. Backward compatibility: if 3 digits was dialed, match legacy format
        if len(clean_ext) == 3:
            legacy_2digit = clean_ext[-2:]
            for s in staff_employees:
                cur = cls.get_staff_extension_number(s)
                if cur == legacy_2digit or (clean_ext.startswith('1') and cur == legacy_2digit):
                    return s

        return None

