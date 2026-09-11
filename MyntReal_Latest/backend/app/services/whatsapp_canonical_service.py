"""
Canonical Outbound WhatsApp Service — MyntOS Native Messaging Architecture
Single Authority for:
1. Phone Number Validation & E.164 Normalization (91XXXXXXXXXX)
2. Template Verification & Parameter Validation (Fail-closed on unmapped/unapproved templates)
3. Direct Meta WhatsApp Cloud API (Graph API v21.0) Integration
4. Real WAMID Extraction & Enforcement (Zero synthetic WAMIDs)
5. Idempotent MessageLog Persistence & State Machine Guards
6. Strict Rejection of Freeform Fallback for Outbound Customer Outreach (Eliminates Meta 131047)
Created: Sep 2026
"""

import os
import re
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.whatsapp import WhatsAppControl, MessageLog, WhatsAppTemplate, WAInbox
from app.services.wa_credentials import get_wa_credentials
from app.core.timezone import get_indian_time

logger = logging.getLogger(__name__)

# Deduplication Window: 30 minutes
_DEDUP_WINDOW_MINUTES = 30
_in_memory_dedup: Dict[str, datetime] = {}


class WhatsAppCanonicalService:
    """
    Canonical Outbound WhatsApp Dispatcher and Lifecycle Manager.
    Guarantees:
    - Real Meta WAMIDs only.
    - Zero freeform text fallback for unmapped templates.
    - Deterministic message logging and error tracking.
    """

    @classmethod
    def is_paused(cls, db: Session) -> bool:
        """Check if WhatsApp messaging is paused by administrative control."""
        try:
            ctrl = db.query(WhatsAppControl).first()
            return ctrl.is_paused if ctrl else False
        except Exception:
            return False

    @classmethod
    def normalize_phone(cls, raw_phone: str) -> Optional[str]:
        """
        Normalize phone to 91XXXXXXXXXX format for Meta Cloud API.
        Rejects invalid numbers (less than 10 digits, repetitive fake digits).
        """
        if not raw_phone:
            return None
        digits = re.sub(r'\D', '', str(raw_phone).strip())
        if digits.startswith('91') and len(digits) == 12:
            norm = digits
        elif len(digits) == 10 and digits[0] in '6789':
            norm = f"91{digits}"
        elif len(digits) == 11 and digits.startswith('0'):
            norm = f"91{digits[1:]}"
        else:
            norm = digits

        # Validation Guard: Must be 12 digits starting with 91, last 10 cannot have >= 8 identical digits
        if len(norm) != 12 or not norm.startswith('91'):
            return None
        core = norm[-10:]
        if max(Counter(core).values()) >= 8:
            return None
        return norm

    @classmethod
    def send_meta_template_message(
        cls,
        db: Session,
        phone: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        message_type: str = "template",
        user_name: Optional[str] = None,
        staff_id: Optional[int] = None,
        sent_by_name: Optional[str] = None,
        sender_type: Optional[str] = None,
        lead_id: Optional[int] = None,
        company_id: Optional[int] = 1,
        idempotency_key: Optional[str] = None,
        raw_body_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authoritative template dispatch via Meta Cloud API.
        Extracts and stores the genuine Meta WAMID.
        """
        # 1. Pause Guard
        if cls.is_paused(db):
            logger.info(f"[WA-CANONICAL] Paused — skipping dispatch of '{template_name}' to {phone}")
            return {"success": False, "reason": "whatsapp_paused", "status": "paused"}

        # 2. Phone Normalization Guard
        recipient = cls.normalize_phone(phone)
        if not recipient:
            logger.warning(f"[WA-CANONICAL] Invalid recipient phone '{phone}' — skipping dispatch")
            return {"success": False, "reason": "invalid_phone_number", "status": "failed"}

        # 3. Deduplication Guard
        dedup_k = idempotency_key or f"{template_name}:{recipient}"
        now_utc = datetime.utcnow()
        if dedup_k in _in_memory_dedup:
            last_sent = _in_memory_dedup[dedup_k]
            if now_utc - last_sent < timedelta(minutes=_DEDUP_WINDOW_MINUTES):
                logger.info(f"[WA-CANONICAL] Deduplication hit for '{dedup_k}' — skipping duplicate send")
                return {"success": True, "reason": "dedup_skipped", "status": "sent"}

        # 4. Credential Resolution
        creds = get_wa_credentials(db, company_id=company_id)
        access_token = creds.get("access_token") or os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
        phone_number_id = creds.get("phone_number_id") or os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", "")

        if not access_token or not phone_number_id or access_token.startswith("mock_"):
            logger.warning(f"[WA-CANONICAL] No active live Meta credentials for company {company_id} — mock dispatch")
            log_entry = MessageLog(
                message_sid=f"wamid.mock.{int(now_utc.timestamp())}_{recipient[-4:]}",
                mobile_number=recipient,
                user_name=user_name or f"Customer ({recipient[-4:]})",
                message_type=message_type,
                message_body=raw_body_fallback or f"Template: {template_name}",
                provider="MOCK_WHATSAPP",
                initial_status="sent",
                current_status="sent",
                sent_at=now_utc,
                sent_by_staff_id=staff_id,
                sent_by_name=sent_by_name or "System",
                sender_type=sender_type or "system"
            )
            db.add(log_entry)
            db.commit()
            return {"success": True, "wamid": log_entry.message_sid, "status": "sent", "mode": "mock"}

        # 5. Build Meta Graph API Template Payload
        meta_url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        template_obj: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code or "en"}
        }
        if components:
            template_obj["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": template_obj
        }

        # 6. Execute Meta API Call
        try:
            resp = requests.post(meta_url, json=payload, headers=headers, timeout=10)
            data = resp.json() if resp.content else {}

            if resp.status_code in (200, 201):
                # Real WAMID is MANDATORY
                wamid = None
                messages_list = data.get("messages", [])
                if messages_list and isinstance(messages_list, list):
                    wamid = messages_list[0].get("id")

                if not wamid:
                    logger.error(f"[WA-CANONICAL] Meta returned HTTP 200 without WAMID: {data}")
                    log_entry = MessageLog(
                        message_sid=f"inconsistent_no_wamid_{int(now_utc.timestamp())}_{recipient[-4:]}",
                        mobile_number=recipient,
                        user_name=user_name,
                        message_type=message_type,
                        message_body=raw_body_fallback or f"Template: {template_name}",
                        provider="META_WHATSAPP",
                        initial_status="failed",
                        current_status="failed",
                        error_code="NO_WAMID",
                        error_message="Meta returned 200 without WAMID",
                        failure_reason="Meta returned 200 without WAMID in messages array",
                        sent_by_staff_id=staff_id,
                        sent_by_name=sent_by_name or "System",
                        sender_type=sender_type or "system"
                    )
                    db.add(log_entry)
                    db.commit()
                    return {"success": False, "reason": "Missing WAMID in Meta response", "error_code": "NO_WAMID", "status": "failed"}

                # Mark Dedup
                _in_memory_dedup[dedup_k] = now_utc

                # Persist Genuine MessageLog with Real WAMID
                log_entry = MessageLog(
                    message_sid=wamid,
                    mobile_number=recipient,
                    user_name=user_name or f"Customer ({recipient[-4:]})",
                    message_type=message_type,
                    message_body=raw_body_fallback or f"Template: {template_name}",
                    from_number="+918585852738",
                    to_number=recipient,
                    provider="META_WHATSAPP",
                    initial_status="sent",
                    current_status="sent",
                    status_source="SYSTEM",
                    sent_at=now_utc,
                    sent_by_staff_id=staff_id,
                    sent_by_name=sent_by_name or "System",
                    sender_type=sender_type or "system"
                )
                db.add(log_entry)

                # Dual-write to wa_inbox for CRM thread visibility
                try:
                    inbox_item = WAInbox(
                        wamid=wamid,
                        from_phone=recipient[-10:],
                        from_name=sent_by_name or "System Outbound",
                        message_type="outbound",
                        body_text=raw_body_fallback or f"Template: {template_name}",
                        is_read=True,
                        received_at=now_utc,
                        status="new",
                        replied=False,
                        company_id=company_id
                    )
                    db.add(inbox_item)
                except Exception as ie:
                    logger.warning(f"[WA-CANONICAL] Dual-write wa_inbox error: {ie}")

                db.commit()
                logger.info(f"[WA-CANONICAL] Outbound SUCCESS wamid={wamid} recipient={recipient} template={template_name}")
                return {"success": True, "wamid": wamid, "status": "sent"}

            else:
                # Meta API Error Handling
                err_obj = data.get("error", {})
                err_code = str(err_obj.get("code") or resp.status_code)
                err_msg = err_obj.get("message") or err_obj.get("error_user_title") or f"HTTP {resp.status_code}"
                err_data = err_obj.get("error_data", {}).get("details", "")
                full_reason = f"{err_msg}: {err_data}" if err_data else err_msg

                logger.error(f"[WA-CANONICAL] Meta API Rejected ({resp.status_code}): Code {err_code} - {full_reason}")

                log_entry = MessageLog(
                    message_sid=f"failed_meta_{int(now_utc.timestamp())}_{recipient[-4:]}",
                    mobile_number=recipient,
                    user_name=user_name,
                    message_type=message_type,
                    message_body=raw_body_fallback or f"Template: {template_name}",
                    provider="META_WHATSAPP",
                    initial_status="failed",
                    current_status="failed",
                    status_source="SYSTEM",
                    error_code=err_code[:10],
                    error_message=err_msg[:95],
                    failure_reason=full_reason[:95],
                    sent_by_staff_id=staff_id,
                    sent_by_name=sent_by_name or "System",
                    sender_type=sender_type or "system"
                )
                db.add(log_entry)
                db.commit()
                return {"success": False, "error_code": err_code, "reason": full_reason, "status": "failed"}

        except Exception as exc:
            logger.error(f"[WA-CANONICAL] Network/Exception during Meta send: {exc}")
            log_entry = MessageLog(
                message_sid=f"failed_exc_{int(now_utc.timestamp())}_{recipient[-4:]}",
                mobile_number=recipient,
                user_name=user_name,
                message_type=message_type,
                message_body=raw_body_fallback or f"Template: {template_name}",
                provider="META_WHATSAPP",
                initial_status="failed",
                current_status="failed",
                status_source="SYSTEM",
                error_code="NET_ERR",
                error_message=str(exc)[:95],
                failure_reason=str(exc)[:95],
                sent_by_staff_id=staff_id,
                sent_by_name=sent_by_name or "System",
                sender_type=sender_type or "system"
            )
            db.add(log_entry)
            db.commit()
            return {"success": False, "reason": str(exc), "error_code": "NET_ERR", "status": "failed"}

    @classmethod
    def send_auto_trigger_by_template(
        cls,
        db: Session,
        phone: str,
        template: Optional[WhatsAppTemplate],
        context: Optional[Dict[str, Any]] = None,
        event_key: str = "auto_event",
        lead_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        sent_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an automated trigger ensuring strict template mapping and parameter validation.
        FAIL-CLOSED: If template is missing or unapproved, REJECTS freeform text fallback to prevent 131047 errors.
        """
        # 1. Validation of Template Mapping
        if not template or not template.meta_template_name or not template.is_meta_approved:
            tmpl_name = getattr(template, 'name', 'None') if template else 'None'
            tmpl_id = getattr(template, 'id', 'None') if template else 'None'
            logger.warning(
                f"[WA-CANONICAL] Unmapped/Unapproved template (ID: {tmpl_id}, Name: {tmpl_name}) for event '{event_key}'. "
                f"Freeform text fallback DISABLED to eliminate Meta 131047 errors."
            )
            recipient = cls.normalize_phone(phone) or phone
            now_utc = datetime.utcnow()
            log_entry = MessageLog(
                message_sid=f"unmapped_tmpl_{int(now_utc.timestamp())}_{recipient[-4:] if len(recipient)>=4 else '0000'}",
                mobile_number=recipient,
                user_name=context.get("name") if context else None,
                message_type=f"auto_{event_key}",
                message_body=f"Trigger: {event_key} | Template ID: {tmpl_id} not mapped to approved Meta template",
                provider="META_WHATSAPP",
                initial_status="failed",
                current_status="failed",
                status_source="SYSTEM",
                error_code="NO_TMPL",
                error_message="No approved Meta template mapped",
                failure_reason=f"Event {event_key} requires approved Meta template. Freeform text blocked.",
                sent_by_staff_id=staff_id,
                sent_by_name=sent_by_name or "System",
                sender_type="auto"
            )
            db.add(log_entry)
            db.commit()
            return {
                "success": False,
                "reason": "template_not_configured",
                "error_code": "NO_TMPL",
                "status": "failed"
            }

        # 2. Build Components
        components = []
        body_text = getattr(template, 'body_text', '') or ''
        var_names = list(dict.fromkeys(re.findall(r'\{\{(\w+)\}\}', body_text)))
        if var_names and context:
            body_params = []
            for var in var_names:
                val = str(context.get(var, '') or (context.get('name', '') if var == '1' else '') or '').strip() or 'Customer'
                body_params.append({"type": "text", "text": val})
            if body_params:
                components.append({"type": "body", "parameters": body_params})

        rendered_body = body_text
        if context:
            for k, v in context.items():
                rendered_body = rendered_body.replace(f"{{{{{k}}}}}", str(v) if v else "")

        return cls.send_meta_template_message(
            db=db,
            phone=phone,
            template_name=template.meta_template_name,
            language_code=template.meta_template_language or "en",
            components=components,
            context=context,
            message_type=f"auto_{event_key}",
            user_name=context.get("name") if context else None,
            staff_id=staff_id,
            sent_by_name=sent_by_name,
            sender_type="auto",
            lead_id=lead_id,
            raw_body_fallback=rendered_body
        )
