"""
Universal History API Endpoints
Single API Contract for all CRM Leads, VGK Members, and Workflow pages.
Strictly read-only with complete tenant/company authorization and phone masking.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.universal_history_service import UniversalHistoryService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/entity-summary")
def get_entity_summary(
    entity_type: str = Query("crm_lead", regex="^(crm_lead|vgk_member)$"),
    entity_id: int = Query(0, ge=0),
    phone: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Fetch resolved entity profile and total counts for Calls, Messages, and Changes."""
    try:
        entity = UniversalHistoryService.resolve_entity(db, entity_type, entity_id, current_user, phone=phone, name=name)
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        db.rollback()
        logger.exception(f"[UniversalHistory] /entity-summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load entity summary: {str(e)}")

    calls = UniversalHistoryService.get_calls_history(db, entity, page=1, limit=1, current_user=current_user)
    messages = UniversalHistoryService.get_messages_history(db, entity, page=1, limit=1, current_user=current_user)
    changes = UniversalHistoryService.get_changes_history(db, entity, subfilter="all", page=1, limit=1, current_user=current_user)

    return {
        "success": True,
        "entity": entity,
        "counts": {
            "calls": calls["total_calls"],
            "messages": messages["total_messages"],
            "changes": changes["total_changes"],
        }
    }


@router.get("/calls")
def get_calls_tab(
    entity_type: str = Query("crm_lead", regex="^(crm_lead|vgk_member)$"),
    entity_id: int = Query(0, ge=0),
    phone: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Calls & Recordings tab data with deduplication and streamable recording URLs."""
    try:
        entity = UniversalHistoryService.resolve_entity(db, entity_type, entity_id, current_user, phone=phone, name=name)
        data = UniversalHistoryService.get_calls_history(db, entity, page=page, limit=limit, current_user=current_user)
        return {
            "success": True,
            "entity": entity,
            **data
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        db.rollback()
        logger.exception(f"[UniversalHistory] /calls error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load calls: {str(e)}")


@router.get("/messages")
def get_messages_tab(
    entity_type: str = Query("crm_lead", regex="^(crm_lead|vgk_member)$"),
    entity_id: int = Query(0, ge=0),
    phone: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Messages / Chat tab data. Pure read-only query with zero unread flag mutations."""
    try:
        entity = UniversalHistoryService.resolve_entity(db, entity_type, entity_id, current_user, phone=phone, name=name)
        data = UniversalHistoryService.get_messages_history(db, entity, page=page, limit=limit, current_user=current_user)
        return {
            "success": True,
            "entity": entity,
            **data
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        db.rollback()
        logger.exception(f"[UniversalHistory] /messages error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load messages: {str(e)}")


@router.get("/changes")
def get_changes_tab(
    entity_type: str = Query("crm_lead", regex="^(crm_lead|vgk_member)$"),
    entity_id: int = Query(0, ge=0),
    phone: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    subfilter: str = Query("all", regex="^(all|audit|notes|followups|assignments)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Lead Change History tab data merging field audit logs, notes, followups, and assignments."""
    try:
        entity = UniversalHistoryService.resolve_entity(db, entity_type, entity_id, current_user, phone=phone, name=name)
        data = UniversalHistoryService.get_changes_history(
            db, entity, subfilter=subfilter, page=page, limit=limit, current_user=current_user
        )
        return {
            "success": True,
            "entity": entity,
            **data
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        db.rollback()
        logger.exception(f"[UniversalHistory] /changes error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load changes: {str(e)}")


@router.get("/full")
def get_full_history(
    entity_type: str = Query("crm_lead", regex="^(crm_lead|vgk_member)$"),
    entity_id: int = Query(0, ge=0),
    phone: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    limit: int = Query(30, ge=5, le=50),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """Optimized initial load for Universal History Modal with summary + initial batch of all 3 tabs."""
    try:
        entity = UniversalHistoryService.resolve_entity(db, entity_type, entity_id, current_user, phone=phone, name=name)
        calls = UniversalHistoryService.get_calls_history(db, entity, page=1, limit=limit, current_user=current_user)
        messages = UniversalHistoryService.get_messages_history(db, entity, page=1, limit=limit, current_user=current_user)
        changes = UniversalHistoryService.get_changes_history(db, entity, subfilter="all", page=1, limit=limit, current_user=current_user)

        return {
            "success": True,
            "entity": entity,
            "calls": calls,
            "messages": messages,
            "changes": changes,
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        db.rollback()
        logger.exception(f"[UniversalHistory] /full error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load full history: {str(e)}")
