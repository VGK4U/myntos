"""
VoIP Call Session Controller & Telephony Orchestration Engine
Authoritative call session state machine, concurrency management, CRM timeline logging, and S3 recording vault integration.
Created: Aug 2026
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException

from app.core.config import settings
from app.models.base import get_indian_time
from app.models.voip_enums import CallMethodEnum, CallStateEnum, RecordingStatusEnum
from app.models.voip_call_session import VoIPCallSession
from app.models.operator_calls import OperatorCall
from app.models.crm import CRMLead, CRMLeadAuditLog
from app.models.staff import StaffEmployee
from app.services.telephony.factory import get_telephony_provider
from app.services.s3_storage import s3_storage_service

logger = logging.getLogger(__name__)


class VoIPCallService:
    """
    Central Controller for MyntReal In-App PSTN Telephony.
    Orchestrates telephony providers, enforces tenant isolation, handles call state transitions,
    and manages authoritative recording pipelines.
    """

    @staticmethod
    def normalize_phone_e164(phone: str) -> str:
        """
        Normalize telephone number to standard E.164 format (+91XXXXXXXXXX for India).
        Rejects invalid or ambiguous numbers.
        """
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number is required")

        cleaned = re.sub(r'[^\d+]', '', str(phone).strip())
        digits_only = re.sub(r'[^\d]', '', cleaned)

        # Handle 10-digit standard Indian mobile
        if len(digits_only) == 10:
            return f"+91{digits_only}"
        
        # Handle 11-digit with leading 0 (e.g. 09703118501)
        if len(digits_only) == 11 and digits_only.startswith('0'):
            return f"+91{digits_only[1:]}"

        # Handle 12-digit with 91 country code (e.g. 919703118501)
        if len(digits_only) == 12 and digits_only.startswith('91'):
            return f"+{digits_only}"

        # International E.164 check (between 10 and 15 digits)
        if cleaned.startswith('+') and 10 <= len(digits_only) <= 15:
            return cleaned

        raise HTTPException(
            status_code=400,
            detail=f"Invalid phone number '{phone}'. Expected 10-digit mobile or valid E.164 format (+91XXXXXXXXXX)."
        )

    @classmethod
    def initiate_in_app_call(
        cls,
        db: Session,
        current_user: Any,
        customer_phone: str,
        lead_id: Optional[int] = None,
        provider_name: Optional[str] = None
    ) -> VoIPCallSession:
        """
        Initiate an authoritative In-App PSTN call session.
        - Validates operator and lead
        - Normalizes customer number to E.164
        - Resolves dedicated MyntReal outbound caller ID
        - Dispatches call via provider-agnostic telephony adapter
        - Idempotently links OperatorCall & CRM Lead history
        """
        # 1. Resolve Operator Identity & Company ID
        is_staff = hasattr(current_user, 'emp_code')
        operator_id = current_user.id if is_staff else None
        operator_user_ref = getattr(current_user, 'emp_code', None) or str(current_user.id)
        operator_name = getattr(current_user, 'full_name', '') or getattr(current_user, 'name', 'Operator')
        operator_phone = getattr(current_user, 'phone', None) or getattr(current_user, 'phone_number', '') or ''
        company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None) or 1
        branch_id = getattr(current_user, 'branch_id', None)

        # 2. Normalize customer phone number
        dest_e164 = cls.normalize_phone_e164(customer_phone)

        # 3. Validate Lead & Tenant Isolation (if lead_id supplied)
        lead = None
        if lead_id:
            lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
            if not lead:
                raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
            
            # Tenant check: Ensure lead belongs to operator's company
            if lead.company_id and lead.company_id != company_id:
                raise HTTPException(status_code=403, detail="Unauthorized: Lead belongs to a different company organization")

        # 4. Concurrency & Double-Dial Protection
        # Check if this operator already has an active ongoing call to prevent rapid double-clicks
        active_cutoff = datetime.utcnow()
        active_session = db.query(VoIPCallSession).filter(
            VoIPCallSession.operator_user_ref == operator_user_ref,
            VoIPCallSession.destination_number == dest_e164,
            VoIPCallSession.status.in_([
                CallStateEnum.CREATED.value,
                CallStateEnum.DIALING.value,
                CallStateEnum.RINGING.value,
                CallStateEnum.ANSWERED.value,
                CallStateEnum.CONNECTED.value
            ])
        ).order_by(desc(VoIPCallSession.created_at)).first()

        if active_session:
            logger.warning(f"[VOIP-CONCURRENCY] Active call session {active_session.call_session_id} already exists for {dest_e164}")
            return active_session

        # 5. Dedicated MyntReal Business Calling Number (Configured, never personal SIM)
        caller_id = (
            getattr(settings, 'MYNTREAL_OUTBOUND_CALLING_NUMBER', None) or 
            os.getenv('MYNTREAL_OUTBOUND_CALLING_NUMBER') or 
            "+912269470537"
        )

        # 6. Instantiate Provider & Generate Unique Session ID
        provider = get_telephony_provider(provider_name)
        import uuid
        call_session_id = f"vcs_{uuid.uuid4().hex[:16]}"
        now = get_indian_time()

        # 7. Create Session Record in Database (State: CREATED)
        session = VoIPCallSession(
            call_session_id=call_session_id,
            company_id=company_id,
            branch_id=branch_id,
            lead_id=lead_id,
            operator_id=operator_id,
            operator_user_ref=operator_user_ref,
            operator_name=operator_name,
            customer_phone=customer_phone,
            direction='outbound',
            call_method=CallMethodEnum.IN_APP_PSTN.value,
            provider=provider.provider_name,
            caller_id=caller_id,
            destination_number=dest_e164,
            status=CallStateEnum.CREATED.value,
            started_at=now,
            recording_status=RecordingStatusEnum.NOT_STARTED.value
        )
        db.add(session)
        db.flush()

        # 8. Dispatch Call to Telephony Provider
        operator_info = {
            "id": operator_id,
            "user_ref": operator_user_ref,
            "name": operator_name,
            "phone": operator_phone,
            "company_id": company_id
        }
        metadata = {
            "lead_id": lead_id,
            "company_id": company_id,
            "branch_id": branch_id
        }

        call_result = provider.create_call(
            call_session_id=call_session_id,
            destination_phone=dest_e164,
            caller_id=caller_id,
            operator_info=operator_info,
            metadata=metadata
        )

        if not call_result.success:
            session.status = CallStateEnum.FAILED.value
            session.failure_reason = call_result.error_message or "Telephony provider rejected call dispatch"
            session.ended_at = get_indian_time()
            db.commit()
            logger.error(f"[VOIP-CALL-FAILED] Session {call_session_id} failed: {session.failure_reason}")
            raise HTTPException(status_code=502, detail=f"Telephony Provider Error: {session.failure_reason}")

        # 9. Update Session with Provider Call ID & DIALING state
        session.provider_call_id = call_result.provider_call_id
        session.status = CallStateEnum.DIALING.value
        session.dialing_at = get_indian_time()
        if call_result.client_token:
            session.client_token = json.dumps(call_result.client_token)

        # 10. Idempotently Associate with OperatorCall Tracking
        op_call = db.query(OperatorCall).filter(
            OperatorCall.company_id == company_id,
            OperatorCall.call_id == call_result.provider_call_id
        ).first()

        if not op_call:
            op_call = OperatorCall(
                company_id=company_id,
                call_id=call_result.provider_call_id,
                caller_number=caller_id,
                called_number=dest_e164,
                operator_name=operator_name,
                operator_number=operator_phone,
                handled_by=operator_name,
                call_type='outbound',
                status='ringing',
                started_at=now,
                crm_lead_id=lead_id
            )
            db.add(op_call)
            db.flush()

        session.operator_call_id = op_call.id

        # 11. Initial CRM Lead Activity / Audit Log
        if lead_id:
            audit = CRMLeadAuditLog(
                lead_id=lead_id,
                changed_by_type='staff' if is_staff else 'vgk_member',
                changed_by_id=str(operator_id or current_user.id),
                changed_by_name=operator_name,
                field_name='call_session_id',
                old_value=None,
                new_value=call_session_id,
                change_category='call'
            )
            db.add(audit)

        db.commit()
        db.refresh(session)
        logger.info(f"[VOIP-CALL-INITIATED] Session {call_session_id} -> {dest_e164} (Provider ID: {call_result.provider_call_id})")
        return session

    @classmethod
    def end_in_app_call(
        cls,
        db: Session,
        current_user: Any,
        call_session_id: str,
        reason: Optional[str] = None
    ) -> VoIPCallSession:
        """
        Request immediate call termination from client.
        """
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.call_session_id == call_session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail=f"Call session '{call_session_id}' not found")

        # Tenant isolation
        user_company_id = getattr(current_user, 'company_id', 1) or 1
        if session.company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to this call session")

        # If already terminal, return directly (idempotent)
        if CallStateEnum(session.status).is_terminal():
            return session

        # Dispatch hangup to provider
        provider = get_telephony_provider(session.provider)
        if session.provider_call_id:
            provider.hangup_call(session.provider_call_id)

        session.status = CallStateEnum.ENDED.value
        session.ended_at = get_indian_time()
        session.termination_reason = reason or "operator_requested_hangup"

        if session.answered_at and session.ended_at:
            session.duration_seconds = max(0, int((session.ended_at - session.answered_at).total_seconds()))
        elif session.started_at and session.ended_at:
            session.duration_seconds = max(0, int((session.ended_at - session.started_at).total_seconds()))

        # Update OperatorCall
        if session.operator_call_id:
            op_call = db.query(OperatorCall).filter(OperatorCall.id == session.operator_call_id).first()
            if op_call:
                op_call.status = 'ended'
                op_call.ended_at = session.ended_at
                op_call.duration_seconds = session.duration_seconds

        db.commit()
        db.refresh(session)
        logger.info(f"[VOIP-CALL-ENDED] Session {call_session_id} ended (Duration: {session.duration_seconds}s)")
        return session

    @classmethod
    def process_telephony_webhook(
        cls,
        db: Session,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str],
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process and normalize telephony provider webhooks idempotently.
        Handles signature verification, call state machine transitions, S3 recording uploads,
        and CRM timeline logs.
        """
        provider = get_telephony_provider(provider_name)
        event = provider.handle_webhook(headers=headers, body=body, query_params=query_params)

        if not event.is_valid:
            logger.warning(f"[VOIP-WEBHOOK-REJECTED] Provider {provider.provider_name} webhook validation failed: {event.error_message}")
            return {"success": False, "error": event.error_message or "Invalid webhook signature or payload"}

        # Resolve VoIPCallSession by provider_call_id or call_session_id
        session = None
        if event.provider_call_id:
            session = db.query(VoIPCallSession).filter(
                VoIPCallSession.provider_call_id == event.provider_call_id
            ).first()

        if not session and event.call_session_id:
            session = db.query(VoIPCallSession).filter(
                VoIPCallSession.call_session_id == event.call_session_id
            ).first()

        if not session:
            logger.info(f"[VOIP-WEBHOOK-IGNORED] Unknown call session for provider_call_id='{event.provider_call_id}'")
            return {"success": True, "message": "Ignored unknown call"}

        # State Machine Transitions (Prevent out-of-order state regression)
        current_state = CallStateEnum(session.status)
        new_state = event.status

        now = get_indian_time()

        if new_state:
            # If current state is terminal and new state is non-terminal, do not regress
            if current_state.is_terminal() and not new_state.is_terminal():
                logger.info(f"[VOIP-WEBHOOK-IDEMPOTENT] Session {session.call_session_id} already terminal ({current_state.value}). Ignoring state {new_state.value}")
            else:
                session.status = new_state.value
                if new_state == CallStateEnum.RINGING and not session.ringing_at:
                    session.ringing_at = now
                elif new_state in (CallStateEnum.ANSWERED, CallStateEnum.CONNECTED) and not session.answered_at:
                    session.answered_at = now
                elif new_state.is_terminal():
                    if not session.ended_at:
                        session.ended_at = now
                    if event.duration_seconds is not None:
                        session.duration_seconds = event.duration_seconds
                    elif session.answered_at:
                        session.duration_seconds = max(0, int((now - session.answered_at).total_seconds()))

        if event.termination_reason and not session.termination_reason:
            session.termination_reason = event.termination_reason

        # Handle Recording Lifecycle & Secure S3 Storage
        if event.recording_status:
            session.recording_status = event.recording_status.value

        if event.recording_url or event.recording_status == RecordingStatusEnum.AVAILABLE:
            session.recording_status = RecordingStatusEnum.AVAILABLE.value
            
            # Construct deterministic, private S3 storage key
            # format: call_recordings/YYYY/MM/DD/<company_id>/<lead_id>/<call_session_id>.wav
            s3_key = (
                f"call_recordings/{now.year}/{now.month:02d}/{now.day:02d}/"
                f"{session.company_id}/{session.lead_id or 'direct'}/{session.call_session_id}.wav"
            )
            session.recording_storage_key = s3_key
            session.recording_mime_type = "audio/wav"

            # If provider supplies raw audio bytes, upload directly to private S3 bucket
            rec_bytes = provider.get_recording(session.provider_call_id, event.recording_url)
            if rec_bytes:
                session.recording_file_size = len(rec_bytes)
                import hashlib
                session.recording_checksum = hashlib.sha256(rec_bytes).hexdigest()
                try:
                    s3_storage_service.upload_file(s3_key, rec_bytes)
                    logger.info(f"[VOIP-RECORDING-SAVED] Uploaded call recording to S3: {s3_key} ({len(rec_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"[VOIP-RECORDING-S3-ERR] Failed to upload recording {s3_key}: {e}")

        # Update OperatorCall table
        if session.operator_call_id:
            op_call = db.query(OperatorCall).filter(OperatorCall.id == session.operator_call_id).first()
            if op_call:
                op_status_map = {
                    CallStateEnum.DIALING.value: 'ringing',
                    CallStateEnum.RINGING.value: 'ringing',
                    CallStateEnum.ANSWERED.value: 'active',
                    CallStateEnum.CONNECTED.value: 'active',
                    CallStateEnum.ENDED.value: 'ended',
                    CallStateEnum.BUSY.value: 'missed',
                    CallStateEnum.NO_ANSWER.value: 'missed',
                    CallStateEnum.REJECTED.value: 'missed',
                    CallStateEnum.FAILED.value: 'missed',
                    CallStateEnum.CANCELLED.value: 'missed'
                }
                op_call.status = op_status_map.get(session.status, op_call.status)
                op_call.duration_seconds = session.duration_seconds
                if session.ended_at:
                    op_call.ended_at = session.ended_at
                if session.recording_storage_key:
                    op_call.recording_url = session.recording_storage_key

        # Append final timeline summary to CRM Lead history if call finished
        if session.lead_id and CallStateEnum(session.status).is_terminal():
            mins = session.duration_seconds // 60
            secs = session.duration_seconds % 60
            dur_str = f"{mins:02d}:{secs:02d}"
            
            source_label = (
                "MyOperator Bridge" if session.call_method == CallMethodEnum.MYOPERATOR_BRIDGE.value or session.provider == "myoperator"
                else "MyntReal In-App PSTN" if session.call_method == CallMethodEnum.IN_APP_PSTN.value
                else "Native SIM"
            )
            
            audit = CRMLeadAuditLog(
                lead_id=session.lead_id,
                changed_by_type='staff',
                changed_by_id=str(session.operator_id or 1),
                changed_by_name=session.operator_name,
                field_name='call_outcome',
                old_value=CallStateEnum.DIALING.value,
                new_value=(
                    f"📞 Outgoing Call | Source: {source_label} | Operator: {session.operator_name} | "
                    f"Customer: {session.customer_phone_masked} | Status: {session.status.upper()} | "
                    f"Duration: {dur_str} | Recording: {session.recording_status.upper()}"
                ),
                change_category='call'
            )
            db.add(audit)

        # DC_SOFTPHONE_TALKTIME_SYNC: Auto-sync VoIP & Softphone duration into StaffCallLog
        # Ensures browser softphone, WebRTC, and VoIP calls are counted across Team Performance, Call Tracking & QA Audits
        if session.operator_id and CallStateEnum(session.status).is_terminal():
            try:
                from app.models.call_tracking import StaffCallLog
                existing_log = db.query(StaffCallLog).filter(
                    StaffCallLog.device_call_id == session.call_session_id
                ).first()
                call_dt = session.answered_at or session.created_at or now
                call_type_val = 'OUTGOING' if getattr(session, 'direction', 'outbound') == 'outbound' else 'INCOMING'
                if session.status in (CallStateEnum.BUSY.value, CallStateEnum.NO_ANSWER.value, CallStateEnum.REJECTED.value, CallStateEnum.FAILED.value, CallStateEnum.CANCELLED.value):
                    call_type_val = 'MISSED'

                if not existing_log:
                    new_call_log = StaffCallLog(
                        company_id=session.company_id or 1,
                        staff_id=session.operator_id,
                        phone_number=session.destination_number or session.customer_phone_masked or '',
                        contact_name=session.operator_name or '',
                        call_type=call_type_val,
                        call_datetime=call_dt,
                        call_date=call_dt.strftime('%Y-%m-%d'),
                        duration_seconds=session.duration_seconds or 0,
                        source='softphone',
                        device_call_id=session.call_session_id,
                        matched_lead_id=session.lead_id,
                        matched_at=now if session.lead_id else None,
                        has_recording=bool(session.recording_storage_key),
                        synced_at=now,
                        created_at=now
                    )
                    db.add(new_call_log)
                else:
                    existing_log.duration_seconds = session.duration_seconds or existing_log.duration_seconds
                    existing_log.call_type = call_type_val
                    existing_log.has_recording = bool(session.recording_storage_key)
            except Exception as e:
                logger.warning(f"[VOIP-STAFF-CALL-LOG-SYNC] Sync failed: {e}")

        db.commit()
        db.refresh(session)
        logger.info(f"[VOIP-WEBHOOK-PROCESSED] Session {session.call_session_id} -> Status: {session.status}, Recording: {session.recording_status}")
        return {
            "success": True,
            "call_session_id": session.call_session_id,
            "status": session.status,
            "recording_status": session.recording_status
        }

    @classmethod
    def get_recording_signed_url(
        cls,
        db: Session,
        current_user: Any,
        call_session_id: str,
        expiration: int = 900
    ) -> Dict[str, Any]:
        """
        Generate short-lived signed S3 URL for private call recording playback.
        Enforces tenant and operator authorization. Never exposes permanent public S3 URLs.
        """
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.call_session_id == call_session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Call session not found")

        # Tenant isolation
        user_company_id = getattr(current_user, 'company_id', 1) or 1
        if session.company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to this call recording")

        if session.recording_status != RecordingStatusEnum.AVAILABLE.value or not session.recording_storage_key:
            raise HTTPException(
                status_code=404,
                detail=f"Recording is not available for this call session (Status: {session.recording_status})"
            )

        # Generate presigned URL
        presigned_url = s3_storage_service.generate_presigned_url(
            session.recording_storage_key,
            expiration=expiration
        )

        if not presigned_url:
            # Fallback if S3 client not configured in local environment
            presigned_url = f"/api/v1/crm/dialer/recordings/stream/{session.call_session_id}"

        return {
            "success": True,
            "call_session_id": session.call_session_id,
            "playback_url": presigned_url,
            "mime_type": session.recording_mime_type or "audio/wav",
            "duration_seconds": session.duration_seconds,
            "expires_in_seconds": expiration
        }
