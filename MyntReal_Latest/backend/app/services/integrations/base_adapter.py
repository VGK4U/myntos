"""
Base Integration Adapter for MyntOS Central Integration Management Framework
Defines the standard contract for testing connections, validating schemas,
masking credentials, and executing provider-specific tasks.
Created: September 2026
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging
from sqlalchemy.orm import Session

from app.core.security_encryption import decrypt_credential_safe

logger = logging.getLogger(__name__)


class BaseIntegrationAdapter(ABC):
    """
    Abstract base adapter for external integration providers.
    All integration-specific network calls, auth validation, and test pings
    must inherit from this adapter.
    """

    integration_code: str = ""

    @abstractmethod
    def test_connection(self, connection, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Executes a live, non-destructive connection test against the external service.
        Returns a standardized dict:
        {
            "status": "SUCCESS" | "FAILED" | "TIMEOUT" | "AUTHENTICATION_ERROR" | "NOT_CONFIGURED",
            "message": str,
            "latency_ms": int,
            "details": dict (safe public metadata only, no secrets!)
        }
        """
        pass

    def get_decrypted_credentials(self, connection) -> Dict[str, Any]:
        """
        Safely decrypts the connection's AES-256-GCM credentials payload.
        Internal backend use only. Never expose to client/API responses.
        """
        if not connection or not connection.encrypted_credentials:
            return {}
        try:
            raw_json = decrypt_credential_safe(connection.encrypted_credentials)
            if not raw_json:
                return {}
            return json.loads(raw_json)
        except Exception as e:
            logger.error(f"[{self.integration_code}] Failed to decrypt credentials for connection {getattr(connection, 'id', None)}: {e}")
            return {}

    def mask_secret(self, val: Optional[str]) -> str:
        """Standardized credential masking for frontend safe presentation."""
        if not val:
            return ""
        s = str(val).strip()
        if len(s) <= 4:
            return "••••"
        if len(s) <= 12:
            return "••••••••" + s[-3:]
        return s[:4] + "••••••••" + s[-4:]

    def get_masked_credentials(self, connection) -> Dict[str, Any]:
        """Returns masked credential fields for frontend form pre-population."""
        creds = self.get_decrypted_credentials(connection)
        masked = {}
        for k, v in creds.items():
            if isinstance(v, str):
                masked[k] = self.mask_secret(v)
            else:
                masked[k] = "••••••••" if v else ""
        return masked
