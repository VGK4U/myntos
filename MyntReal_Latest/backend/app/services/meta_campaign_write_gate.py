"""
Meta Campaign Human Approval Write Gate (Phase 2A Staging Verification)
Prepares human-approval gate workflow for future Meta campaign execution:
DRAFT -> STAFF_REVIEW -> EXPLICIT_HUMAN_APPROVAL -> META_API_WRITE
Enforces strict write protection safety (META_ADS_WRITE_ENABLED = False). Zero automatic dispatches.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)


def process_human_approved_meta_campaign_publish(
    db: Session,
    company_id: int,
    staff_id: int,
    campaign_draft_payload: Dict[str, Any],
    staff_explicit_approval: bool = False
) -> Dict[str, Any]:
    """
    Human Approval Write Gate scaffold.
    Requires explicit staff_explicit_approval = True.
    Enforces META_ADS_WRITE_ENABLED flag protection.
    """
    if not staff_explicit_approval:
        logger.warning(f"[WRITE-GATE-BLOCKED] Staff ID {staff_id} did not explicitly approve campaign payload.")
        return {
            "success": False,
            "status": "REJECTED_MISSING_HUMAN_APPROVAL",
            "message": "Explicit human approval is mandatory before any Meta write attempt."
        }

    # Verify write protection feature flag
    if not getattr(settings, 'META_ADS_WRITE_ENABLED', False):
        logger.info(f"[WRITE-GATE-SAFETY] META_ADS_WRITE_ENABLED is False. Write operation safely intercepted.")
        return {
            "success": True,
            "status": "WRITE_FLAG_DISABLED_STAGING_SAFE",
            "message": "Human approval recorded successfully. Meta Graph API write execution intercepted safely because META_ADS_WRITE_ENABLED = False.",
            "approval_audit": {
                "company_id": company_id,
                "approved_by_staff_id": staff_id,
                "campaign_name": campaign_draft_payload.get("name", "Draft Campaign"),
                "write_permission_status": "DISABLED_READ_ONLY_MODE"
            }
        }

    # If write flag were enabled (Future Phase): Execute Graph API POST
    return {
        "success": False,
        "status": "UNAUTHORIZED_PHASE_2A_WRITE_NOT_ALLOWED",
        "message": "Meta write operations remain un-authorized in Phase 2A."
    }
