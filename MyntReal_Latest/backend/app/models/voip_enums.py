"""
VoIP Enums for MyntReal In-App PSTN Telephony & Call Session Engine
Created: Aug 2026
"""

from enum import Enum


class CallMethodEnum(str, Enum):
    """Supported dialer call methods in MyntReal"""
    IN_APP_PSTN = "in_app_pstn"
    MYOPERATOR_BRIDGE = "myoperator_bridge"
    NATIVE_SIM = "native_sim"


class CallStateEnum(str, Enum):
    """
    Authoritative server-side call state machine.
    Distinguishes distinct caller, receiver, and network termination states.
    """
    CREATED = "created"
    DIALING = "dialing"
    RINGING = "ringing"
    ANSWERED = "answered"
    CONNECTED = "connected"
    ENDED = "ended"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_states(cls):
        return {
            cls.ENDED,
            cls.BUSY,
            cls.NO_ANSWER,
            cls.REJECTED,
            cls.FAILED,
            cls.CANCELLED,
        }

    def is_terminal(self) -> bool:
        return self in self.terminal_states()


class RecordingStatusEnum(str, Enum):
    """
    Independent recording lifecycle status.
    A call can be ENDED while recording is still PROCESSING or AVAILABLE.
    """
    NOT_STARTED = "not_started"
    RECORDING = "recording"
    PROCESSING = "processing"
    AVAILABLE = "available"
    FAILED = "failed"
