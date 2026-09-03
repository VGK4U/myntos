"""
Plivo JWT & Endpoint Provisioning Service — MyntOS Native Telephony
Manages staff-to-Plivo SIP endpoint provisioning and server-side JWT issuance for the Plivo Browser SDK.
Guarantees zero leakage of master Plivo credentials to client browsers.
Created: Sep 2026
"""

import os
import time
import secrets
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from jose import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.models.telephony_call_flow import TelephonyPlivoEndpoint
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

PLIVO_JWT_EXPIRATION_SECONDS = 3600  # 1 Hour


class PlivoJWTService:
    """
    Handles secure Plivo SIP endpoint lifecycle and browser JWT token issuance.
    """

    @classmethod
    def get_or_create_staff_endpoint(
        cls,
        db: Session,
        company_id: int,
        staff: StaffEmployee
    ) -> TelephonyPlivoEndpoint:
        """
        Retrieves existing Plivo endpoint mapping or provisions a new one for the staff employee.
        Prevents duplicate endpoint creation and guarantees company/tenant isolation.
        """
        if getattr(staff, 'status', 'active') not in ('active', 'ACTIVE'):
            raise HTTPException(status_code=403, detail="Inactive or disabled staff members cannot provision telephony endpoints")

        import re

        # 1. Check existing mapping
        endpoint = db.query(TelephonyPlivoEndpoint).filter(
            TelephonyPlivoEndpoint.company_id == company_id,
            TelephonyPlivoEndpoint.staff_id == staff.id
        ).first()

        auth_id = getattr(settings, 'PLIVO_AUTH_ID', None) or os.getenv("PLIVO_AUTH_ID")
        auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None) or os.getenv("PLIVO_AUTH_TOKEN")
        app_id = getattr(settings, 'PLIVO_APP_ID', None) or os.getenv("PLIVO_APP_ID")

        if endpoint and endpoint.plivo_endpoint_id:
            return endpoint

        # 2. Provision new endpoint username & alias
        # Plivo requires purely alphanumeric username and clean alias characters
        clean_alias = re.sub(r'[^a-zA-Z0-9_\-\+@\.]', '_', f"{staff.emp_code}_{staff.full_name}")[:30]
        base_username = f"agentc{company_id}s{staff.id}"
        raw_password = secrets.token_urlsafe(16)
        endpoint_id = None
        actual_username = base_username

        # 3. Call Plivo REST API if live credentials configured
        if auth_id and auth_token and not auth_id.startswith("mock_"):
            try:
                plivo_url = f"https://api.plivo.com/v1/Account/{auth_id}/Endpoint/"
                payload = {
                    "username": base_username,
                    "password": raw_password,
                    "alias": clean_alias
                }
                if app_id:
                    payload["app_id"] = app_id

                resp = requests.post(
                    plivo_url,
                    json=payload,
                    auth=(auth_id, auth_token),
                    timeout=8
                )
                if resp.status_code in (200, 201):
                    res_json = resp.json()
                    endpoint_id = res_json.get("endpoint_id")
                    actual_username = res_json.get("username") or base_username
                    logger.info(f"[PLIVO-ENDPOINT] Successfully provisioned remote endpoint {actual_username} (ID: {endpoint_id})")
                else:
                    logger.warning(f"[PLIVO-ENDPOINT] Plivo API endpoint creation response ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.error(f"[PLIVO-ENDPOINT-ERROR] Failed to contact Plivo API: {e}")

        # 4. Save or update mapping in database
        if endpoint:
            endpoint.plivo_endpoint_id = endpoint_id
            endpoint.plivo_username = actual_username
            endpoint.plivo_alias = clean_alias
            db.commit()
            db.refresh(endpoint)
            return endpoint

        endpoint = TelephonyPlivoEndpoint(
            company_id=company_id,
            staff_id=staff.id,
            plivo_endpoint_id=endpoint_id,
            plivo_username=actual_username,
            plivo_alias=clean_alias,
            is_registered=False
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        return endpoint

    @classmethod
    def generate_browser_token(
        cls,
        db: Session,
        company_id: int,
        staff: StaffEmployee
    ) -> Dict[str, Any]:
        """
        Generates a short-lived, cryptographically signed JWT for the Plivo Browser SDK.
        Ensures the browser only receives the JWT and never the master Plivo credentials.
        """
        # 1. Validate staff status and tenant ownership
        if getattr(staff, 'status', 'active') not in ('active', 'ACTIVE'):
            raise HTTPException(status_code=403, detail="Inactive staff members cannot acquire browser telephony tokens")

        staff_company_id = getattr(staff, 'base_company_id', None) or 1
        role_code = (getattr(staff.role, 'role_code', '') or '').lower() if getattr(staff, 'role', None) else ''
        is_super = getattr(staff, 'is_super_admin', False) or role_code in ('vgk4u', 'vgk4u_supreme', 'super_admin') or (staff.role and getattr(staff.role, 'hierarchy_level', 0) >= 90)
        
        if not is_super and staff_company_id != company_id:
            raise HTTPException(status_code=403, detail="Cross-company telephony access is strictly prohibited")

        # 2. Retrieve or provision endpoint mapping
        endpoint = cls.get_or_create_staff_endpoint(db, company_id, staff)

        auth_id = getattr(settings, 'PLIVO_AUTH_ID', None) or os.getenv("PLIVO_AUTH_ID", "mock_plivo_auth_id")
        auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None) or os.getenv("PLIVO_AUTH_TOKEN", "mock_plivo_auth_token_secret_12345")
        app_id = getattr(settings, 'PLIVO_APP_ID', None) or os.getenv("PLIVO_APP_ID", "mock_app_id")

        now = int(time.time())
        exp = now + PLIVO_JWT_EXPIRATION_SECONDS

        signed_token = None
        if auth_id and auth_token and not auth_id.startswith("mock_"):
            try:
                plivo_jwt_url = f"https://api.plivo.com/v1/Account/{auth_id}/JWT/Token/"
                jwt_payload = {
                    "iss": auth_id,
                    "sub": endpoint.plivo_username,
                    "per": {
                        "voice": {
                            "incoming_allow": True,
                            "outgoing_allow": True
                        }
                    }
                }
                if app_id:
                    jwt_payload["app"] = app_id
                
                resp = requests.post(plivo_jwt_url, json=jwt_payload, auth=(auth_id, auth_token), timeout=6)
                if resp.status_code == 200:
                    signed_token = resp.json().get("token")
                    logger.info(f"[PLIVO-JWT] Successfully acquired official JWT from Plivo API for {endpoint.plivo_username}")
                else:
                    logger.warning(f"[PLIVO-JWT] Plivo JWT API returned {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"[PLIVO-JWT-ERROR] Error calling Plivo JWT API: {e}")

        if not signed_token:
            # Compliant fallback token with official Plivo v1 header and permissions
            fallback_payload = {
                "iss": auth_id,
                "sub": endpoint.plivo_username,
                "nbf": now - 5,
                "iat": now,
                "exp": exp,
                "per": {
                    "voice": {
                        "incoming_allow": True,
                        "outgoing_allow": True
                    }
                }
            }
            if app_id:
                fallback_payload["app"] = app_id
            signed_token = jwt.encode(fallback_payload, auth_token, algorithm="HS256", headers={"typ": "JWT", "cty": "plivo;v=1"})

        return {
            "success": True,
            "token_type": "Bearer",
            "access_token": signed_token,
            "expires_in_seconds": PLIVO_JWT_EXPIRATION_SECONDS,
            "expires_at": exp,
            "endpoint": {
                "username": endpoint.plivo_username,
                "sip_uri": f"sip:{endpoint.plivo_username}@phone.plivo.com",
                "alias": endpoint.plivo_alias,
                "is_registered": endpoint.is_registered
            },
            "caller_id": getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', '+918031728899')
        }

    @classmethod
    def update_registration_status(
        cls,
        db: Session,
        company_id: int,
        staff_id: int,
        is_registered: bool
    ) -> bool:
        """Updates softphone live WebRTC registration heartbeat"""
        endpoint = db.query(TelephonyPlivoEndpoint).filter(
            TelephonyPlivoEndpoint.company_id == company_id,
            TelephonyPlivoEndpoint.staff_id == staff_id
        ).first()

        if endpoint:
            endpoint.is_registered = is_registered
            endpoint.last_registered_at = get_indian_time()
            db.commit()
            return True
        return False
