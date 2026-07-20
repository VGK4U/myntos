"""
RVZ-Only Protection System
Secondary password verification + audit logging for all critical deletions
"""

from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.user import User

# RVZ ID constant
RVZ_ID = "MNR182364369"

def verify_rvz_access(user: User, operation_name: str) -> None:
    """
    Verify that the current user is RVZ ID
    Raises HTTPException if not
    
    NOTE: Temporarily accepts both 'RVZ ID' and 'RVZ ID' user_type values
    during migration period until database is fully updated
    """
    if user.id != RVZ_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: {operation_name} is exclusive to RVZ ID"
        )
    
    # Accept both RVZ ID and RVZ ID during migration period
    if user.user_type not in ['RVZ ID', 'RVZ ID']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: RVZ ID role required for {operation_name}"
        )


def verify_rvz_secondary_password(
    user: User,
    secondary_password: str,
    operation_name: str
) -> None:
    """
    Verify RVZ secondary password for dangerous operations
    Raises HTTPException if verification fails
    """
    # Ensure user is RVZ
    verify_rvz_access(user, operation_name)
    
    # Check if secondary password is set
    if not user.has_secondary_password():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RVZ secondary password not configured. Please set up secondary password first."
        )
    
    # Verify secondary password
    if not user.check_secondary_password(secondary_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secondary password incorrect"
        )


def create_deletion_audit_log(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    deletion_reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    additional_details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Create comprehensive audit log entry for RVZ deletions
    Writes to audit_log table with full timeline and details
    """
    from sqlalchemy import text
    
    details_text = f"Entity: {entity_type}\nEntity ID: {entity_id}\nEntity Name: {entity_name}"
    if deletion_reason:
        details_text += f"\nReason: {deletion_reason}"
    if additional_details:
        for key, value in additional_details.items():
            details_text += f"\n{key}: {value}"
    
    # Insert into audit_log table
    db.execute(
        text("""
            INSERT INTO audit_log (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                ip_address,
                created_at,
                severity
            ) VALUES (
                :actor_user_id,
                :action,
                :entity_type,
                :entity_id,
                :details,
                :ip_address,
                :created_at,
                :severity
            )
        """),
        {
            "actor_user_id": user.id,
            "action": "SOFT_DELETE",
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "details": details_text,
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
            "severity": "critical"  # FIXED: Changed from "HIGH" to valid value "critical"
        }
    )
    db.commit()


def create_restore_audit_log(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    ip_address: Optional[str] = None
) -> None:
    """
    Create audit log entry for RVZ restores
    """
    from sqlalchemy import text
    
    details_text = f"Entity: {entity_type}\nEntity ID: {entity_id}\nEntity Name: {entity_name}\nRestored from soft delete"
    
    db.execute(
        text("""
            INSERT INTO audit_log (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                ip_address,
                created_at,
                severity
            ) VALUES (
                :actor_user_id,
                :action,
                :entity_type,
                :entity_id,
                :details,
                :ip_address,
                :created_at,
                :severity
            )
        """),
        {
            "actor_user_id": user.id,
            "action": "RESTORE",
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "details": details_text,
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
            "severity": "warning"  # FIXED: Changed from "MEDIUM" to valid value "warning"
        }
    )
    db.commit()
