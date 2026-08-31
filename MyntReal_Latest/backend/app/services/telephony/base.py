"""
Telephony Provider Interface & Data Contracts
Provider-agnostic abstraction for MyntReal In-App PSTN Calling & Centralized Recording
Created: Aug 2026
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from app.models.voip_enums import CallStateEnum, RecordingStatusEnum


@dataclass
class TelephonyCallResult:
    """Result of initiating an outbound PSTN call via the telephony provider"""
    success: bool
    provider_call_id: Optional[str] = None
    initial_status: CallStateEnum = CallStateEnum.DIALING
    client_token: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class TelephonyCallStatus:
    """Status query result from provider"""
    provider_call_id: str
    status: CallStateEnum
    duration_seconds: int = 0
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_status: RecordingStatusEnum = RecordingStatusEnum.NOT_STARTED
    recording_url: Optional[str] = None
    termination_reason: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class TelephonyWebhookEvent:
    """Normalized webhook event received from a telephony provider"""
    is_valid: bool
    event_type: str
    provider_call_id: str
    call_session_id: Optional[str] = None
    status: Optional[CallStateEnum] = None
    duration_seconds: Optional[int] = None
    termination_reason: Optional[str] = None
    recording_url: Optional[str] = None
    recording_status: Optional[RecordingStatusEnum] = None
    recording_bytes: Optional[bytes] = None
    recording_file_size: Optional[int] = None
    recording_duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class BaseTelephonyProvider(ABC):
    """
    Abstract Base Telephony Provider.
    Enforces clean separation between CRM business logic and external telephony vendors.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name/Identifier of this provider (e.g. 'mock', 'twilio', 'exotel', 'myoperator_sip')"""
        pass

    @abstractmethod
    def create_call(
        self,
        call_session_id: str,
        destination_phone: str,
        caller_id: str,
        operator_info: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelephonyCallResult:
        """
        Initiate an outbound PSTN call from caller_id to destination_phone.
        """
        pass

    @abstractmethod
    def get_call_status(self, provider_call_id: str) -> TelephonyCallStatus:
        """
        Query current status of a call from provider.
        """
        pass

    @abstractmethod
    def hangup_call(self, provider_call_id: str) -> bool:
        """
        Request immediate termination of an ongoing call.
        """
        pass

    @abstractmethod
    def get_recording(self, provider_call_id: str, recording_url: Optional[str] = None) -> Optional[bytes]:
        """
        Download raw audio recording bytes from provider if available.
        """
        pass

    @abstractmethod
    def handle_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str]
    ) -> TelephonyWebhookEvent:
        """
        Authenticate, parse and normalize an incoming provider webhook payload.
        """
        pass

    @abstractmethod
    def generate_client_token(
        self,
        call_session_id: str,
        operator_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate WebRTC/SIP client authentication token for the operator's app.
        """
        pass
