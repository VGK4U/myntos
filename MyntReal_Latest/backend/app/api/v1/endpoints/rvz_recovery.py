"""
RVZ Data Recovery Center
View and restore all soft-deleted data across the system with timestamp-based recovery
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rvz_protection import (
    verify_rvz_access,
    verify_rvz_secondary_password,
    create_restore_audit_log
)
from app.models.user import User
from app.models.bonanza import Bonanza

router = APIRouter(prefix="/rvz/recovery", tags=["RVZ Data Recovery"])


class RestoreRequest(BaseModel):
    secondary_password: str
    entity_type: str  # 'BONANZA', 'USER', 'ALL'
    entity_id: Optional[int] = None  # For single restore
    timestamp: Optional[str] = None  # For bulk restore before this time


@router.get("/deleted-data")
async def get_all_deleted_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 RVZ ONLY - View ALL deleted data across system with timestamps
    Returns organized view of all soft-deleted records by type
    """
    verify_rvz_access(current_user, "Data Recovery Center")
    
    # Get all deleted bonanzas
    deleted_bonanzas = db.query(Bonanza).filter(
        Bonanza.is_deleted == True
    ).order_by(Bonanza.deleted_at.desc()).all()
    
    bonanzas_list = []
    for b in deleted_bonanzas:
        bonanzas_list.append({
            "id": b.id,
            "name": b.name,
            "type": "Bonanza",
            "deleted_at": b.deleted_at.isoformat() if b.deleted_at else None,
            "deleted_by": b.deleted_by,
            "deletion_reason": b.deletion_reason,
            "details": {
                "criteria_type": b.criteria_type,
                "target_requirement": b.target_requirement,
                "reward_amount": float(b.reward_amount) if b.reward_amount else None,
                "status": b.status,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None
            }
        })
    
    # TODO: Add other entity types (Users, Award Tiers, etc.) when soft delete is implemented
    
    # Get deletion audit logs
    audit_logs = db.execute(
        text("""
            SELECT 
                id,
                actor_user_id,
                action,
                entity_type,
                entity_id,
                details,
                ip_address,
                created_at,
                severity
            FROM audit_log
            WHERE action IN ('SOFT_DELETE', 'RESTORE')
            ORDER BY created_at DESC
            LIMIT 100
        """)
    ).fetchall()
    
    audit_list = []
    for log in audit_logs:
        audit_list.append({
            "id": log[0],
            "actor": log[1],
            "action": log[2],
            "entity_type": log[3],
            "entity_id": log[4],
            "details": log[5],
            "ip_address": log[6],
            "timestamp": log[7].isoformat() if log[7] else None,
            "severity": log[8]
        })
    
    return {
        "success": True,
        "summary": {
            "total_deleted_bonanzas": len(bonanzas_list),
            "total_deleted_users": 0,  # TODO: Implement when user soft delete ready
            "total_deleted_items": len(bonanzas_list)
        },
        "deleted_data": {
            "bonanzas": bonanzas_list,
            "users": [],  # TODO: Implement
            "award_tiers": []  # TODO: Implement
        },
        "audit_trail": audit_list
    }


@router.post("/restore")
async def restore_deleted_data(
    restore_req: RestoreRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔄 RVZ ONLY - Restore deleted data (single item or bulk by timestamp)
    Requires secondary password verification
    
    Options:
    - Single restore: Provide entity_type and entity_id
    - Bulk restore: Provide timestamp (restores all deletions after that time)
    """
    verify_rvz_access(current_user, "Data Restore")
    verify_rvz_secondary_password(
        current_user,
        restore_req.secondary_password,
        "Data Restore"
    )
    
    restored_items = []
    
    # SINGLE ITEM RESTORE
    if restore_req.entity_id and restore_req.entity_type:
        if restore_req.entity_type == 'BONANZA':
            bonanza = db.query(Bonanza).filter(
                Bonanza.id == restore_req.entity_id,
                Bonanza.is_deleted == True
            ).first()
            
            if not bonanza:
                raise HTTPException(
                    status_code=404,
                    detail=f"Bonanza ID {restore_req.entity_id} not found or not deleted"
                )
            
            # Restore bonanza
            bonanza_name = bonanza.name
            bonanza.is_deleted = False
            bonanza.deleted_at = None
            bonanza.deleted_by = None
            bonanza.deletion_reason = None
            
            db.commit()
            
            # Audit log
            create_restore_audit_log(
                db=db,
                user=current_user,
                entity_type='BONANZA',
                entity_id=str(bonanza.id),
                entity_name=bonanza_name,
                ip_address=request.client.host if request.client else None
            )
            
            restored_items.append({
                "type": "BONANZA",
                "id": bonanza.id,
                "name": bonanza_name
            })
        
        # TODO: Add USER, AWARD_TIER restore when implemented
        
    # BULK RESTORE BY TIMESTAMP
    elif restore_req.timestamp:
        timestamp = datetime.fromisoformat(restore_req.timestamp.replace('Z', '+00:00'))
        
        # Restore all bonanzas deleted after this timestamp
        bonanzas_to_restore = db.query(Bonanza).filter(
            Bonanza.is_deleted == True,
            Bonanza.deleted_at >= timestamp
        ).all()
        
        for bonanza in bonanzas_to_restore:
            bonanza_name = bonanza.name
            bonanza.is_deleted = False
            bonanza.deleted_at = None
            bonanza.deleted_by = None
            bonanza.deletion_reason = None
            
            create_restore_audit_log(
                db=db,
                user=current_user,
                entity_type='BONANZA',
                entity_id=str(bonanza.id),
                entity_name=bonanza_name,
                ip_address=request.client.host if request.client else None
            )
            
            restored_items.append({
                "type": "BONANZA",
                "id": bonanza.id,
                "name": bonanza_name
            })
        
        db.commit()
        
        # TODO: Add bulk restore for other entity types
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either entity_id or timestamp for restore"
        )
    
    return {
        "success": True,
        "message": f"✅ Successfully restored {len(restored_items)} item(s)",
        "restored_items": restored_items,
        "restored_by": current_user.id,
        "restored_at": datetime.utcnow().isoformat()
    }


@router.get("/deletion-timeline")
async def get_deletion_timeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📅 RVZ ONLY - Get timeline view of all deletions grouped by date
    Useful for point-in-time recovery
    """
    verify_rvz_access(current_user, "Deletion Timeline")
    
    # Get all deletions from audit log
    timeline_data = db.execute(
        text("""
            SELECT 
                DATE(created_at) as deletion_date,
                entity_type,
                COUNT(*) as count,
                array_agg(entity_id) as entity_ids,
                array_agg(details) as details_list
            FROM audit_log
            WHERE action = 'SOFT_DELETE'
            GROUP BY DATE(created_at), entity_type
            ORDER BY deletion_date DESC
        """)
    ).fetchall()
    
    timeline = []
    for row in timeline_data:
        timeline.append({
            "date": row[0].isoformat() if row[0] else None,
            "entity_type": row[1],
            "count": row[2],
            "entity_ids": row[3] if row[3] else [],
            "can_bulk_restore": True
        })
    
    return {
        "success": True,
        "timeline": timeline,
        "note": "Click any date to restore all deletions from that day"
    }
