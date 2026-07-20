"""
Award Processing API Endpoints - Multi-Role Approval Workflow
Handles Admin → Super Admin → Finance → RVZ approval chain
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
import logging

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, get_current_user_hybrid, get_current_admin_user_hybrid
from app.core.rbac import require_admin_hybrid, require_super_admin_hybrid, require_finance_admin_hybrid, require_rvz_id_hybrid
from app.models.user import User
from app.services.award_processing_service import AwardProcessingService

router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


# ========== REQUEST/RESPONSE MODELS ==========

class AdminReviewRequest(BaseModel):
    decision: str  # 'approve' or 'return'
    notes: Optional[str] = None


class BulkApproveRequest(BaseModel):
    award_ids: List[int]
    notes: Optional[str] = None


class SuperAdminDecisionRequest(BaseModel):
    decision: str  # 'approve' or 'reject'
    notes: Optional[str] = None


class FinanceProcessRequest(BaseModel):
    actual_cost: Optional[float] = None  # If provided, enables cost variance
    cost_variance_reason: Optional[str] = None
    notes: Optional[str] = None
    handling_charges: Optional[float] = None  # Company handling charges (base amount)
    gst_amount: Optional[float] = None  # GST (18%) on handling charges (auto-calculated in frontend)
    tax_amount: Optional[float] = None  # Tax collected from winner (physical awards only)
    transport_charges: Optional[float] = None  # Transport charges collected from winner (physical awards only)
    vendor_name: Optional[str] = None  # Vendor/supplier name for expense record
    payment_mode: Optional[str] = None  # Payment method (Bank Transfer, Cash, UPI, etc.)


class TrackingUpdateRequest(BaseModel):
    dispatch_date: Optional[str] = None  # ISO format date string (bonanza only)
    received_date: Optional[str] = None  # ISO format date string (bonanza only)
    delivery_notes: Optional[str] = None  # bonanza only


class DeliveryUpdateRequest(BaseModel):
    delivered_at: Optional[str] = None  # ISO datetime string (direct/matching awards)
    delivery_proof_path: Optional[str] = None  # File path or URL (direct/matching awards)
    user_acknowledgment: Optional[bool] = None  # User confirmed receipt (direct/matching awards)


class RVZOverrideRequest(BaseModel):
    new_status: str
    reason: str


class UpdateNotesRequest(BaseModel):
    notes: str


# ========== ADMIN ENDPOINTS ==========

@router.get("/admin/awards/pending")
async def get_pending_awards_admin(
    award_type: Optional[str] = Query(None, description="Filter by award type: direct, matching, bonanza"),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    audience: Optional[str] = Query(None, regex="^(mnr|vgk4u|both)$"),
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all awards pending admin review
    Accessible by: Admin, Super Admin, Finance Admin, RVZ ID

    DC Protocol (Task #33): audience param OPTIONAL — when omitted, the
    response is identical to the pre-Task-#33 contract.

    [DC_T33_SHARED_DATA_001] VGK4U pending awards live in the SAME
    UserAwardProgress / UserMatchingAwardProgress / DynamicBonanzaHistory
    tables as MNR. The audience flag is a UI-routing hint; the underlying
    AwardProcessingService.get_pending_awards_for_admin returns the
    canonical shared dataset for every audience value.
    """
    service = AwardProcessingService(db)
    result = service.get_pending_awards_for_admin(
        award_type=award_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit
    )
    
    # Transform response to match frontend expectations
    # Frontend expects: { success: true, direct_awards: [], matching_awards: [], bonanza: [] }
    # Service returns: { awards: [...], total: N }
    awards = result.get('awards', [])
    
    # Separate by award_type
    direct_awards = [a for a in awards if a.get('award_type') == 'Direct Referral Award']
    matching_awards = [a for a in awards if a.get('award_type') == 'Matching Referral Award']
    bonanza = [a for a in awards if a.get('award_type') == 'Bonanza']
    
    return {
        'success': True,
        'direct_awards': direct_awards,
        'matching_awards': matching_awards,
        'bonanza': bonanza,
        'total': len(awards)
    }


@router.post("/admin/awards/{award_type}/{award_id}/review")
async def admin_review_award(
    award_type: str,
    award_id: int,
    request: AdminReviewRequest,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin reviews single award (approve or return)
    Accessible by: Admin, Super Admin, Finance Admin, RVZ ID
    """
    service = AwardProcessingService(db)
    result = service.admin_review_award(
        award_id=award_id,
        award_type=award_type,
        decision=request.decision,
        staff_actor_id=_resolve_actor_id(current_user),
        notes=request.notes
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/admin/awards/{award_type}/bulk-approve")
async def admin_bulk_approve(
    award_type: str,
    request: BulkApproveRequest,
    current_user: User = Depends(require_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin bulk approves multiple awards
    Accessible by: Admin, Super Admin, Finance Admin, RVZ ID
    """
    service = AwardProcessingService(db)
    result = service.admin_bulk_approve(
        award_ids=request.award_ids,
        award_type=award_type,
        staff_actor_id=_resolve_actor_id(current_user),
        notes=request.notes
    )
    return result


# ========== SUPER ADMIN ENDPOINTS ==========

@router.get("/super-admin/awards/pending")
async def get_pending_awards_super_admin(
    award_type: Optional[str] = Query(None),
    status_filter: Optional[List[str]] = Query(None, description="Filter by specific statuses (multi-select). If None/empty, returns ALL statuses (dynamic)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all awards for RVZ Supreme Authority with dynamic MULTI-STATUS filtering
    Accessible by: Super Admin, RVZ ID
    
    DYNAMIC STATUS FILTERING (DC Protocol):
    - If status_filter is None/empty list: Returns ALL awards in ANY status (future-proof)
    - If status_filter contains values: Returns awards matching ANY of those statuses (OR logic)
    
    Example: ?status_filter=Pending%20Approval&status_filter=Admin%20Approved
    Returns awards that are EITHER "Pending Approval" OR "Admin Approved"
    """
    service = AwardProcessingService(db)
    result = service.get_pending_awards_for_super_admin(
        award_type=award_type,
        status_filter=status_filter,
        skip=skip,
        limit=limit
    )
    return {'success': True, **result}


@router.get("/super-admin/awards/statuses")
async def get_dynamic_award_statuses(
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get distinct award statuses dynamically from database
    Returns unique status values across all award types for filter dropdowns
    
    DC PROTOCOL: Future-proof - automatically includes new statuses without code changes
    Accessible by: Super Admin, RVZ ID
    """
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.models.bonanza import DynamicBonanzaHistory
    
    # Query distinct statuses from each award table
    direct_statuses = db.query(UserAwardProgress.processed_status).distinct().filter(
        UserAwardProgress.processed_status.isnot(None)
    ).all()
    
    matching_statuses = db.query(UserMatchingAwardProgress.processed_status).distinct().filter(
        UserMatchingAwardProgress.processed_status.isnot(None)
    ).all()
    
    bonanza_statuses = db.query(DynamicBonanzaHistory.processed_status).distinct().filter(
        DynamicBonanzaHistory.processed_status.isnot(None)
    ).all()
    
    # Combine and deduplicate
    all_statuses = set()
    for (status,) in direct_statuses + matching_statuses + bonanza_statuses:
        if status:
            all_statuses.add(status)
    
    # Sort statuses for consistent display
    sorted_statuses = sorted(list(all_statuses))
    
    return {
        'success': True,
        'statuses': sorted_statuses,
        'total': len(sorted_statuses)
    }


@router.post("/super-admin/awards/{award_type}/{award_id}/decision")
async def super_admin_decision(
    award_type: str,
    award_id: int,
    request: SuperAdminDecisionRequest,
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Super Admin makes decision on award (approve or reject)
    Accessible by: Super Admin, RVZ ID
    """
    service = AwardProcessingService(db)
    result = service.super_admin_decision(
        award_id=award_id,
        award_type=award_type,
        decision=request.decision,
        staff_actor_id=_resolve_actor_id(current_user),
        notes=request.notes
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/super-admin/awards/{award_type}/bulk-approve")
async def super_admin_bulk_approve(
    award_type: str,
    request: BulkApproveRequest = Body(...),
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Super Admin bulk approves multiple awards
    Accessible by: Super Admin, RVZ ID
    """
    service = AwardProcessingService(db)
    result = service.super_admin_bulk_approve(
        award_ids=request.award_ids,
        award_type=award_type,
        staff_actor_id=_resolve_actor_id(current_user),
        notes=request.notes
    )
    return result


@router.post("/super-admin/awards/{award_type}/{award_id}/update-notes")
async def update_award_notes(
    award_type: str,
    award_id: int,
    request: UpdateNotesRequest,
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update award notes - RVZ Edit functionality
    Accessible by: Super Admin, RVZ ID
    DC Protocol: Updates admin_notes field in award tables
    """
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.models.bonanza import DynamicBonanzaHistory
    
    try:
        if award_type == 'direct':
            award = db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
        elif award_type == 'matching':
            award = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
        elif award_type == 'bonanza':
            award = db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid award type")
        
        if not award:
            raise HTTPException(status_code=404, detail="Award not found")
        
        # Update notes field
        if award_type in ['direct', 'matching']:
            award.admin_notes = request.notes
        else:  # bonanza
            award.delivery_notes = request.notes  # Bonanza uses delivery_notes field
        
        db.commit()
        
        return {
            "success": True,
            "message": "Award notes updated successfully",
            "data": {
                "award_id": award_id,
                "award_type": award_type,
                "notes": request.notes
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ========== FINANCE ADMIN ENDPOINTS ==========

@router.get("/finance/awards/pending")
async def get_pending_awards_finance(
    award_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all awards pending Finance processing
    Accessible by: Finance Admin, RVZ ID
    """
    service = AwardProcessingService(db)
    result = service.get_pending_awards_for_finance(
        award_type=award_type,
        skip=skip,
        limit=limit
    )
    return {'success': True, **result}


@router.post("/finance/awards/{award_type}/{award_id}/process")
async def finance_process_payment(
    award_type: str,
    award_id: int,
    request: FinanceProcessRequest,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Finance processes payment with optional cost adjustment
    Accessible by: Finance Admin, RVZ ID
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔄 Processing payment - Type: {award_type}, ID: {award_id}, User: {current_user.id}")
    logger.info(f"📦 Request data: actual_cost={request.actual_cost}, handling_charges={request.handling_charges}, gst_amount={request.gst_amount}")
    
    service = AwardProcessingService(db)
    
    # Properly handle zero values - use 'is not None' instead of truthy check
    actual_cost_decimal = Decimal(str(request.actual_cost)) if request.actual_cost is not None else None
    handling_charges_decimal = Decimal(str(request.handling_charges)) if request.handling_charges is not None else None
    gst_amount_decimal = Decimal(str(request.gst_amount)) if request.gst_amount is not None else None
    tax_amount_decimal = Decimal(str(request.tax_amount)) if request.tax_amount is not None else None
    transport_charges_decimal = Decimal(str(request.transport_charges)) if request.transport_charges is not None else None
    
    result = service.finance_process_payment(
        award_id=award_id,
        award_type=award_type,
        staff_actor_id=_resolve_actor_id(current_user),
        actual_cost=actual_cost_decimal,
        cost_variance_reason=request.cost_variance_reason,
        notes=request.notes,
        handling_charges=handling_charges_decimal,
        gst_amount=gst_amount_decimal,
        tax_amount=tax_amount_decimal,
        transport_charges=transport_charges_decimal,
        vendor_name=request.vendor_name,
        payment_mode=request.payment_mode
    )
    
    if 'error' in result:
        logger.error(f"❌ Payment processing failed: {result['error']}")
        raise HTTPException(status_code=400, detail=result['error'])
    
    logger.info(f"✅ Payment processed successfully for award {award_id}")
    return result


@router.post("/finance/bonanza/{claim_id}/tracking")
async def update_bonanza_tracking(
    claim_id: int,
    request: TrackingUpdateRequest,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ✅ DC Protocol: Update tracking details AND processed_status for bonanza claim
    
    Uses UnifiedAwardStatusManager to ensure:
    - Delivery tracking fields updated (dispatch_date, received_date, delivery_notes)
    - processed_status auto-calculated from delivery tracking
    - Changes reflected across ALL pages (Gift-Wise Status, user awards, etc.)
    - Full audit trail created
    
    Accessible by: Finance Admin, RVZ ID only
    """
    from app.services.unified_award_status_manager import UnifiedAwardStatusManager
    from datetime import datetime
    
    status_manager = UnifiedAwardStatusManager(db)
    
    dispatch_date = None
    if request.dispatch_date:
        try:
            dispatch_date = datetime.fromisoformat(request.dispatch_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dispatch_date format. Use ISO format (YYYY-MM-DD)")
    
    received_date = None
    if request.received_date:
        try:
            received_date = datetime.fromisoformat(request.received_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid received_date format. Use ISO format (YYYY-MM-DD)")
    
    try:
        result = status_manager.update_delivery_status(
            award_id=claim_id,
            award_type='bonanza',
            dispatch_date=dispatch_date,
            received_date=received_date,
            actor_id=_resolve_actor_id(current_user),
            notes=request.delivery_notes
        )
        
        logger.info(f"✅ Bonanza tracking updated via UnifiedAwardStatusManager: {result}")
        
        return {
            'success': True,
            'message': 'Tracking details and status updated successfully',
            'claim_id': claim_id,
            'dispatch_date': result.get('dispatch_date'),
            'received_date': result.get('received_date'),
            'delivery_notes': result.get('delivery_notes'),
            'old_status': result.get('old_status'),
            'new_status': result.get('new_status'),
            'delivery_status': result.get('new_status')
        }
    except ValueError as e:
        logger.error(f"❌ Validation error updating bonanza tracking: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating bonanza tracking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update tracking: {str(e)}")


@router.post("/finance/direct/{award_id}/tracking")
async def update_direct_award_tracking(
    award_id: int,
    request: TrackingUpdateRequest,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ✅ DC Protocol: Update tracking details for direct award (EXACT SAME AS BONANZA)
    
    Uses UnifiedAwardStatusManager.update_delivery_status() - IDENTICAL to bonanza endpoint
    
    Accessible by: Finance Admin, RVZ ID only
    """
    from app.services.unified_award_status_manager import UnifiedAwardStatusManager
    from datetime import datetime
    
    status_manager = UnifiedAwardStatusManager(db)
    
    dispatch_date = None
    if request.dispatch_date:
        try:
            dispatch_date = datetime.fromisoformat(request.dispatch_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dispatch_date format. Use ISO format (YYYY-MM-DD)")
    
    received_date = None
    if request.received_date:
        try:
            received_date = datetime.fromisoformat(request.received_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid received_date format. Use ISO format (YYYY-MM-DD)")
    
    try:
        result = status_manager.update_delivery_status(
            award_id=award_id,
            award_type='direct',
            dispatch_date=dispatch_date,
            received_date=received_date,
            actor_id=_resolve_actor_id(current_user),
            notes=request.delivery_notes
        )
        
        logger.info(f"✅ Direct award tracking updated via UnifiedAwardStatusManager: {result}")
        
        return {
            'success': True,
            'message': 'Tracking details and status updated successfully',
            'claim_id': award_id,
            'dispatch_date': result.get('dispatch_date'),
            'received_date': result.get('received_date'),
            'delivery_notes': result.get('delivery_notes'),
            'old_status': result.get('old_status'),
            'new_status': result.get('new_status'),
            'delivery_status': result.get('new_status')
        }
    except ValueError as e:
        logger.error(f"❌ Validation error updating direct award tracking: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating direct award tracking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update tracking: {str(e)}")


@router.post("/finance/matching/{award_id}/tracking")
async def update_matching_award_tracking(
    award_id: int,
    request: TrackingUpdateRequest,
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ✅ DC Protocol: Update tracking details for matching award (EXACT SAME AS BONANZA)
    
    Uses UnifiedAwardStatusManager.update_delivery_status() - IDENTICAL to bonanza endpoint
    
    Accessible by: Finance Admin, RVZ ID only
    """
    from app.services.unified_award_status_manager import UnifiedAwardStatusManager
    from datetime import datetime
    
    status_manager = UnifiedAwardStatusManager(db)
    
    dispatch_date = None
    if request.dispatch_date:
        try:
            dispatch_date = datetime.fromisoformat(request.dispatch_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dispatch_date format. Use ISO format (YYYY-MM-DD)")
    
    received_date = None
    if request.received_date:
        try:
            received_date = datetime.fromisoformat(request.received_date.replace('Z', '+00:00')).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid received_date format. Use ISO format (YYYY-MM-DD)")
    
    try:
        result = status_manager.update_delivery_status(
            award_id=award_id,
            award_type='matching',
            dispatch_date=dispatch_date,
            received_date=received_date,
            actor_id=_resolve_actor_id(current_user),
            notes=request.delivery_notes
        )
        
        logger.info(f"✅ Matching award tracking updated via UnifiedAwardStatusManager: {result}")
        
        return {
            'success': True,
            'message': 'Tracking details and status updated successfully',
            'claim_id': award_id,
            'dispatch_date': result.get('dispatch_date'),
            'received_date': result.get('received_date'),
            'delivery_notes': result.get('delivery_notes'),
            'old_status': result.get('old_status'),
            'new_status': result.get('new_status'),
            'delivery_status': result.get('new_status')
        }
    except ValueError as e:
        logger.error(f"❌ Validation error updating matching award tracking: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating matching award tracking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update tracking: {str(e)}")


@router.get("/finance/awards/{award_type}/{award_id}/preview")
async def finance_preview_payment(
    award_type: str,
    award_id: int,
    actual_cost: Optional[float] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Preview payment calculation before processing
    Accessible by: Finance Admin, RVZ ID
    """
    # Get award to preview
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: Use new table
    
    if award_type == 'direct':
        award = db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
    elif award_type == 'matching':
        award = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
    elif award_type == 'bonanza':
        # DC Protocol: Query DynamicBonanzaHistory (single source of truth)
        award = db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid award type")
    
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    budgeted_amount = Decimal(str(award.budgeted_amount)) if award.budgeted_amount else Decimal('0')
    actual_amount = Decimal(str(actual_cost)) if actual_cost else budgeted_amount
    
    admin_deduction = actual_amount * Decimal('0.08')
    tds_deduction = actual_amount * Decimal('0.02')
    net_amount = actual_amount - admin_deduction - tds_deduction
    cost_variance = budgeted_amount - actual_amount
    total_company_earnings = admin_deduction + tds_deduction + cost_variance
    
    return {
        'success': True,
        'budgeted_amount': float(budgeted_amount),
        'actual_cost': float(actual_amount),
        'cost_variance': float(cost_variance),
        'admin_deduction': float(admin_deduction),
        'tds_deduction': float(tds_deduction),
        'net_amount': float(net_amount),
        'total_company_earnings': float(total_company_earnings),
        'deduction_percentage': {
            'admin': 8.0,
            'tds': 2.0,
            'total': 10.0
        }
    }


# ========== RVZ ID ENDPOINTS ==========

@router.get("/rvz/awards/oversight")
async def rvz_get_all_awards(
    status: Optional[str] = Query(None),
    award_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ gets complete oversight of all awards
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    DC Protocol: Maps frontend status slugs to unified processed_status values
    """
    # DC Protocol: Map frontend filter slugs to unified status values (applies to ALL award types)
    status_mapping = {
        'pending': 'Pending Approval',
        'pending_admin_review': 'Pending Approval',  # Alias
        'admin_approved': 'Admin Approved',
        'pending_super_admin': 'Admin Approved',  # Awaiting RVZ
        'rvz_approved': 'Procurement Pending',
        'pending_finance': 'Procurement Pending',  # Awaiting finance processing
        'finance_processed': 'Processed for Dispatch',
        'completed': 'Delivered',
        'delivered': 'Delivered',
        'rejected': 'Rejected'
    }
    
    # Translate frontend slug to DC Protocol value
    mapped_status = status_mapping.get(status.lower()) if status else None
    
    service = AwardProcessingService(db)
    result = service.rvz_get_all_awards(
        status=mapped_status,  # Pass mapped DC Protocol value
        award_type=award_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit
    )
    return {'success': True, **result}


@router.post("/rvz/awards/{award_type}/{award_id}/override")
async def rvz_override_status(
    award_type: str,
    award_id: int,
    request: RVZOverrideRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ overrides any award status
    DC Protocol (Feb 2026): Staff access enabled via page-level permissions
    """
    service = AwardProcessingService(db)
    result = service.rvz_override_status(
        award_id=award_id,
        award_type=award_type,
        new_status=request.new_status,
        rvz_id=_resolve_actor_id(current_user),
        reason=request.reason
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.get("/rvz/awards/audit-trail")
async def rvz_get_audit_trail(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    actor_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete audit trail
    Accessible by: RVZ ID, Super Admin
    """
    service = AwardProcessingService(db)
    result = service.get_audit_trail(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit
    )
    return {'success': True, **result}


@router.get("/finance/awards/handling-charges-tracker")
async def get_handling_charges_tracker(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(require_finance_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get handling charges and GST tracker for awards
    Accessible by: Finance Admin, RVZ ID
    Similar to TDS tracker but for handling charges + 18% GST
    """
    from datetime import datetime, date
    from sqlalchemy import func, and_
    from app.models.transaction import CompanyEarnings
    from app.models.awards import AwardAuditLog
    
    # Parse date filters
    filters = []
    if date_from:
        try:
            date_from_parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
            filters.append(func.date(CompanyEarnings.timestamp) >= date_from_parsed)
        except:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
            filters.append(func.date(CompanyEarnings.timestamp) <= date_to_parsed)
        except:
            pass
    
    # Query CompanyEarnings for award-related handling charges
    query = db.query(CompanyEarnings).filter(
        CompanyEarnings.income_type.in_(['Direct Award', 'Matching Award', 'Bonanza Award'])
    )
    
    if filters:
        query = query.filter(and_(*filters))
    
    earnings_records = query.order_by(CompanyEarnings.timestamp.desc()).all()
    
    # Extract handling charges and GST from description field
    records = []
    total_handling_charges = Decimal('0')
    total_gst = Decimal('0')
    
    for record in earnings_records:
        # Parse description to extract handling charges and GST
        # Format: "Cash Award - Handling Charges: ₹X, GST(18%): ₹Y, Cost Variance: ₹Z"
        handling_charges = Decimal('0')
        gst_amount = Decimal('0')
        
        if record.description:
            try:
                # Extract handling charges
                if 'Handling: ₹' in record.description or 'Handling Charges: ₹' in record.description:
                    import re
                    handling_match = re.search(r'Handling.*?₹([\d.]+)', record.description)
                    if handling_match:
                        handling_charges = Decimal(handling_match.group(1))
                    
                    # Extract GST
                    gst_match = re.search(r'GST.*?₹([\d.]+)', record.description)
                    if gst_match:
                        gst_amount = Decimal(gst_match.group(1))
            except:
                pass
        
        if handling_charges > 0 or gst_amount > 0:
            total_handling_charges += handling_charges
            total_gst += gst_amount
            
            records.append({
                'id': record.id,
                'user_id': record.user_id,
                'income_type': record.income_type,
                'handling_charges': float(handling_charges),
                'gst_amount': float(gst_amount),
                'total': float(handling_charges + gst_amount),
                'date': record.timestamp.date().isoformat() if record.timestamp else None,
                'description': record.description
            })
    
    # Calculate summary statistics
    summary = {
        'total_handling_charges': float(total_handling_charges),
        'total_gst': float(total_gst),
        'grand_total': float(total_handling_charges + total_gst),
        'total_transactions': len(records)
    }
    
    return {
        'success': True,
        'records': records,
        'summary': summary,
        'date_from': date_from,
        'date_to': date_to
    }


# ========== AWARD ACHIEVEMENT BREAKDOWN ENDPOINT ==========

@router.get("/awards/breakdown/{award_type}/{award_id}")
async def get_award_achievement_breakdown(
    award_type: str,
    award_id: int,
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed breakdown of which members contributed to a specific award achievement
    Shows the calculation details - which referrals/members counted towards the award
    
    For Direct Awards: List of direct referrals with activation dates and packages
    For Matching Awards: Left leg and right leg members with points breakdown
    
    Accessible by: Super Admin, RVZ ID
    """
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier
    from app.models.placement import Placement
    from datetime import datetime
    
    try:
        if award_type == 'direct':
            # Get the award record
            award = db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
            if not award:
                raise HTTPException(status_code=404, detail="Direct award not found")
            
            # Get award tier details
            tier = db.query(DirectAwardTier).filter(DirectAwardTier.id == award.award_tier_id).first()
            
            # Get all direct referrals of this user (post Oct 21, 2025)
            from sqlalchemy import and_
            referrals = db.query(User).filter(
                and_(
                    User.referrer_id == award.user_id,
                    User.activation_date >= datetime(2025, 10, 21)
                )
            ).order_by(User.activation_date.asc()).all()
            
            # Calculate points and split into allocated vs surplus
            direct_points = 0
            all_referral_details = []
            for ref in referrals:
                # Use package_points: Platinum = 1.0, Diamond = 0.5
                points = float(ref.package_points) if ref.package_points else 0
                direct_points += points
                
                # Determine package name from points
                if points >= 1.0:
                    package_name = 'Platinum'
                elif points >= 0.5:
                    package_name = 'Diamond'
                else:
                    package_name = 'Other'
                
                all_referral_details.append({
                    'user_id': ref.id,
                    'name': ref.name,
                    'package': package_name,
                    'points': points,
                    'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
                })
            
            # INCREMENTAL ALLOCATION: Calculate previous tier requirements already consumed
            tier_requirement = tier.referral_count if tier else 0
            previous_cumulative = 0
            
            all_user_awards = db.query(UserAwardProgress).join(
                DirectAwardTier,
                UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).filter(
                UserAwardProgress.user_id == award.user_id,
                DirectAwardTier.referral_count < tier_requirement
            ).all()
            
            if all_user_awards:
                # Get highest lower tier requirement (cumulative consumed)
                lower_tier_requirements = [
                    db.query(DirectAwardTier).filter(
                        DirectAwardTier.id == a.award_tier_id
                    ).first().referral_count
                    for a in all_user_awards
                ]
                previous_cumulative = max(lower_tier_requirements) if lower_tier_requirements else 0
            
            # Incremental requirement = THIS tier's total - what was already consumed
            incremental_requirement = tier_requirement - previous_cumulative
            
            # Split members with partial point consumption support
            def split_direct_members_incremental(members, skip_points, allocate_points):
                """Incremental allocation with partial consumption for direct awards."""
                skipped = []
                allocated = []
                surplus = []
                cumulative_points = 0.0
                
                for member in members:
                    member_points = float(member['points'])
                    member_start = cumulative_points
                    member_end = cumulative_points + member_points
                    
                    # Case 1: Fully consumed by previous tiers
                    if member_end <= skip_points:
                        skipped.append(member.copy())
                        cumulative_points = member_end
                    
                    # Case 2: Spans skip boundary (partial consumption)
                    elif member_start < skip_points < member_end:
                        consumed_portion = skip_points - member_start
                        remaining_portion = member_points - consumed_portion
                        
                        if consumed_portion > 0:
                            skipped_member = member.copy()
                            skipped_member['points'] = round(consumed_portion, 2)
                            skipped_member['partial'] = True
                            skipped_member['original_points'] = member_points
                            skipped.append(skipped_member)
                        
                        already_allocated = sum(m['points'] for m in allocated)
                        budget_remaining = allocate_points - already_allocated
                        
                        if remaining_portion <= budget_remaining:
                            allocated_member = member.copy()
                            allocated_member['points'] = round(remaining_portion, 2)
                            allocated_member['partial'] = True
                            allocated_member['original_points'] = member_points
                            allocated.append(allocated_member)
                        else:
                            if budget_remaining > 0:
                                allocated_member = member.copy()
                                allocated_member['points'] = round(budget_remaining, 2)
                                allocated_member['partial'] = True
                                allocated_member['original_points'] = member_points
                                allocated.append(allocated_member)
                            
                            surplus_portion = remaining_portion - budget_remaining
                            if surplus_portion > 0:
                                surplus_member = member.copy()
                                surplus_member['points'] = round(surplus_portion, 2)
                                surplus_member['partial'] = True
                                surplus_member['original_points'] = member_points
                                surplus.append(surplus_member)
                        
                        cumulative_points = member_end
                    
                    # Case 3: Fully in allocation range
                    elif skip_points <= member_start < skip_points + allocate_points:
                        already_allocated = sum(m['points'] for m in allocated)
                        budget_remaining = allocate_points - already_allocated
                        
                        if member_points <= budget_remaining:
                            allocated.append(member.copy())
                        else:
                            if budget_remaining > 0:
                                allocated_member = member.copy()
                                allocated_member['points'] = round(budget_remaining, 2)
                                allocated_member['partial'] = True
                                allocated_member['original_points'] = member_points
                                allocated.append(allocated_member)
                            
                            surplus_portion = member_points - budget_remaining
                            if surplus_portion > 0:
                                surplus_member = member.copy()
                                surplus_member['points'] = round(surplus_portion, 2)
                                surplus_member['partial'] = True
                                surplus_member['original_points'] = member_points
                                surplus.append(surplus_member)
                        
                        cumulative_points = member_end
                    
                    # Case 4: Fully in surplus range
                    else:
                        surplus.append(member.copy())
                        cumulative_points = member_end
                
                return allocated, surplus, skipped
            
            allocated_members, surplus_members, skipped_members = split_direct_members_incremental(
                all_referral_details, previous_cumulative, incremental_requirement
            )
            
            return {
                'success': True,
                'award_type': 'direct',
                'award_id': award_id,
                'user_id': award.user_id,
                'award_name': tier.award_name if tier else 'Unknown',
                'requirement': tier_requirement,
                'incremental_requirement': incremental_requirement,
                'previous_cumulative': previous_cumulative,
                'current_achievement': direct_points,
                'total_members': len(referrals),
                'allocated_members': allocated_members,
                'surplus_members': surplus_members,
                'skipped_members': skipped_members,
                'members': all_referral_details
            }
            
        elif award_type == 'matching':
            # Get the award record
            award = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
            if not award:
                raise HTTPException(status_code=404, detail="Matching award not found")
            
            # Get award tier details
            tier = db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
            
            # Get all downline members using RECURSIVE BINARY TREE with leg preservation
            # This matches the EXACT logic used for award calculation
            from sqlalchemy import text, and_
            
            # CRITICAL: Use recursive query that preserves ROOT leg position
            # Same logic as in get_matching_pairs_with_reset_logic_sql()
            recursive_query = text("""
                WITH RECURSIVE downline AS (
                  SELECT 
                    u.id as child_id,
                    u.name,
                    u.activation_date,
                    u.coupon_status,
                    u.package_points,
                    u.referrer_id,
                    p.side as position_side,
                    1 as level
                  FROM placement p
                  INNER JOIN "user" u ON u.id = p.child_id
                  WHERE p.parent_id = :user_id
                  
                  UNION ALL
                  
                  SELECT 
                    u.id as child_id,
                    u.name,
                    u.activation_date,
                    u.coupon_status,
                    u.package_points,
                    u.referrer_id,
                    d.position_side,  -- Preserve the root leg side
                    d.level + 1
                  FROM placement p
                  INNER JOIN "user" u ON u.id = p.child_id
                  INNER JOIN downline d ON p.parent_id = d.child_id
                  WHERE d.level < 200
                )
                SELECT 
                  child_id,
                  name,
                  activation_date,
                  package_points,
                  referrer_id,
                  position_side
                FROM downline
                WHERE package_points > 0
                  AND (activation_date >= '2025-10-21' OR coupon_status IN ('Active', 'Activated'))
                ORDER BY position_side, activation_date
            """)
            
            result = db.execute(recursive_query, {"user_id": award.user_id}).fetchall()
            
            # Split into left and right legs
            left_leg = []
            right_leg = []
            
            for row in result:
                member_data = {
                    'user_id': row[0],
                    'name': row[1],
                    'activation_date': row[2],
                    'package_points': float(row[3]) if row[3] else 0,
                    'referrer_id': row[4],
                    'position_side': row[5]
                }
                
                if row[5] == 'left':
                    left_leg.append(member_data)
                elif row[5] == 'right':
                    right_leg.append(member_data)
            
            # Calculate points for each leg
            left_points = 0
            left_details = []
            for member in left_leg:
                points = member['package_points']
                left_points += points
                
                # Determine package name from points
                if points >= 1.0:
                    package_name = 'Platinum'
                elif points >= 0.5:
                    package_name = 'Diamond'
                else:
                    package_name = 'Other'
                
                # Check if this is a direct referral
                is_direct_referral = (member['referrer_id'] == award.user_id)
                
                left_details.append({
                    'user_id': member['user_id'],
                    'name': member['name'],
                    'package': package_name,
                    'points': points,
                    'activation_date': member['activation_date'].isoformat() if member['activation_date'] else None,
                    'position_side': 'LEFT',
                    'is_direct_referral': is_direct_referral,
                    'relationship': 'Direct Referral' if is_direct_referral else 'Downline Member'
                })
            
            right_points = 0
            right_details = []
            for member in right_leg:
                points = member['package_points']
                right_points += points
                
                # Determine package name from points
                if points >= 1.0:
                    package_name = 'Platinum'
                elif points >= 0.5:
                    package_name = 'Diamond'
                else:
                    package_name = 'Other'
                
                # Check if this is a direct referral
                is_direct_referral = (member['referrer_id'] == award.user_id)
                
                right_details.append({
                    'user_id': member['user_id'],
                    'name': member['name'],
                    'package': package_name,
                    'points': points,
                    'activation_date': member['activation_date'].isoformat() if member['activation_date'] else None,
                    'position_side': 'RIGHT',
                    'is_direct_referral': is_direct_referral,
                    'relationship': 'Direct Referral' if is_direct_referral else 'Downline Member'
                })
            
            # Calculate matching pairs (minimum of both legs)
            matching_pairs = min(left_points, right_points)
            tier_requirement = tier.match_count if tier else 0
            
            # INCREMENTAL ALLOCATION FIX: Calculate previous tier requirements already consumed
            # Example: Star (1) + Prime Star (3) → Star shows 1, Prime Star shows INCREMENTAL 2 (3-1)
            previous_cumulative = 0
            all_user_awards = db.query(UserMatchingAwardProgress).join(
                MatchingAwardTier,
                UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).filter(
                UserMatchingAwardProgress.user_id == award.user_id,
                MatchingAwardTier.match_count < tier_requirement
            ).all()
            
            if all_user_awards:
                # Sum the highest lower tier requirement (cumulative consumed)
                lower_tier_requirements = [
                    db.query(MatchingAwardTier).filter(
                        MatchingAwardTier.id == a.matching_award_tier_id
                    ).first().match_count
                    for a in all_user_awards
                ]
                previous_cumulative = max(lower_tier_requirements) if lower_tier_requirements else 0
            
            # Incremental requirement = THIS tier's total - what was already consumed
            incremental_requirement = tier_requirement - previous_cumulative
            
            # Progressive allocation for matching awards with PARTIAL POINT CONSUMPTION support
            # Handles Diamond (0.5 pts) and Platinum (1.0 pts) packages correctly
            # Example: If Star consumed 1.0 pts from a 1.5 pt member, Prime Star gets remaining 0.5 pts
            def split_leg_members_incremental(members, skip_points, allocate_points):
                """
                Split members into skipped, allocated, and surplus with partial consumption support.
                
                Args:
                    members: List of member dicts with 'points' field
                    skip_points: Points already consumed by lower tier awards
                    allocate_points: Points to allocate for THIS tier (incremental)
                
                Returns:
                    (allocated, surplus, skipped) - each is a list of member dicts
                    Note: Members can appear with reduced 'points' if partially consumed
                """
                skipped = []
                allocated = []
                surplus = []
                cumulative_points = 0.0
                
                for member in members:
                    member_points = float(member['points'])
                    member_start = cumulative_points
                    member_end = cumulative_points + member_points
                    
                    # Case 1: Member entirely consumed by previous tiers
                    if member_end <= skip_points:
                        skipped.append(member.copy())
                        cumulative_points = member_end
                    
                    # Case 2: Member spans skip boundary (partially consumed by previous tiers)
                    elif member_start < skip_points < member_end:
                        # Portion consumed by previous tiers
                        consumed_portion = skip_points - member_start
                        remaining_portion = member_points - consumed_portion
                        
                        # Add consumed portion to skipped
                        if consumed_portion > 0:
                            skipped_member = member.copy()
                            skipped_member['points'] = round(consumed_portion, 2)
                            skipped_member['partial'] = True
                            skipped_member['original_points'] = member_points
                            skipped.append(skipped_member)
                        
                        # Calculate how much budget is left for THIS tier
                        already_allocated = sum(m['points'] for m in allocated)
                        budget_remaining = allocate_points - already_allocated
                        
                        # Check if remaining portion fits within budget
                        if remaining_portion <= budget_remaining:
                            # Entire remaining portion allocated to THIS tier
                            allocated_member = member.copy()
                            allocated_member['points'] = round(remaining_portion, 2)
                            allocated_member['partial'] = True
                            allocated_member['original_points'] = member_points
                            allocated.append(allocated_member)
                        else:
                            # Split: some to THIS tier, rest to surplus
                            if budget_remaining > 0:
                                allocated_member = member.copy()
                                allocated_member['points'] = round(budget_remaining, 2)
                                allocated_member['partial'] = True
                                allocated_member['original_points'] = member_points
                                allocated.append(allocated_member)
                            
                            surplus_portion = remaining_portion - budget_remaining
                            if surplus_portion > 0:
                                surplus_member = member.copy()
                                surplus_member['points'] = round(surplus_portion, 2)
                                surplus_member['partial'] = True
                                surplus_member['original_points'] = member_points
                                surplus.append(surplus_member)
                        
                        cumulative_points = member_end
                    
                    # Case 3: Member entirely in allocation range for THIS tier
                    elif skip_points <= member_start < skip_points + allocate_points:
                        # Calculate how much budget is left for THIS tier
                        already_allocated = sum(m['points'] for m in allocated)
                        budget_remaining = allocate_points - already_allocated
                        
                        if member_points <= budget_remaining:
                            # Fully allocated to THIS tier
                            allocated.append(member.copy())
                        else:
                            # Partially allocated, rest is surplus
                            if budget_remaining > 0:
                                allocated_member = member.copy()
                                allocated_member['points'] = round(budget_remaining, 2)
                                allocated_member['partial'] = True
                                allocated_member['original_points'] = member_points
                                allocated.append(allocated_member)
                            
                            surplus_portion = member_points - budget_remaining
                            if surplus_portion > 0:
                                surplus_member = member.copy()
                                surplus_member['points'] = round(surplus_portion, 2)
                                surplus_member['partial'] = True
                                surplus_member['original_points'] = member_points
                                surplus.append(surplus_member)
                        
                        cumulative_points = member_end
                    
                    # Case 4: Member entirely in surplus range
                    else:
                        surplus.append(member.copy())
                        cumulative_points = member_end
                
                return allocated, surplus, skipped
            
            left_allocated, left_surplus, left_skipped = split_leg_members_incremental(
                left_details, previous_cumulative, incremental_requirement
            )
            right_allocated, right_surplus, right_skipped = split_leg_members_incremental(
                right_details, previous_cumulative, incremental_requirement
            )
            
            return {
                'success': True,
                'award_type': 'matching',
                'award_id': award_id,
                'user_id': award.user_id,
                'award_name': tier.award_name if tier else 'Unknown',
                'requirement': tier_requirement,
                'incremental_requirement': incremental_requirement,
                'previous_cumulative': previous_cumulative,
                'current_achievement': matching_pairs,
                'left_leg': {
                    'points': left_points,
                    'total_members': len(left_leg),
                    'allocated_members': left_allocated,
                    'surplus_members': left_surplus,
                    'skipped_members': left_skipped,
                    'members': left_details
                },
                'right_leg': {
                    'points': right_points,
                    'total_members': len(right_leg),
                    'allocated_members': right_allocated,
                    'surplus_members': right_surplus,
                    'skipped_members': right_skipped,
                    'members': right_details
                }
            }
        
        elif award_type == 'bonanza':
            # DC Protocol: DynamicBonanzaHistory is single source of truth (checks MNR first)
            # BonanzaProgress kept ONLY for backward compatibility with legacy read-only data
            from app.models.bonanza import BonanzaProgress, DynamicBonanza, DynamicBonanzaReward, DynamicBonanzaHistory, Bonanza
            
            # Try NEW MNR system first (DynamicBonanzaHistory - DC Protocol)
            mnr2_award = db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
            
            if mnr2_award:
                # MNR Bonanza Award - different structure
                bonanza = db.query(Bonanza).filter(Bonanza.id == mnr2_award.bonanza_id).first()
                
                # Calculate total points consumed from deductions
                points_consumed = (mnr2_award.deduction_amount_direct or 0) + (mnr2_award.deduction_amount_matching or 0)
                
                result = {
                    'success': True,
                    'award_type': 'bonanza_mnr2',
                    'award_id': award_id,
                    'user_id': mnr2_award.user_id,
                    'bonanza_name': bonanza.name if bonanza else 'Unknown',
                    'reward_name': mnr2_award.award_name if mnr2_award.reward_type == 'award' else f"₹{int(mnr2_award.reward_value_claimed):,} Cash",
                    'reward_type': mnr2_award.reward_type,
                    'reward_amount': float(mnr2_award.reward_value_claimed) if mnr2_award.reward_value_claimed else 0,
                    'claimed_date': mnr2_award.claimed_at.isoformat() if mnr2_award.claimed_at else None,
                    'processed_date': mnr2_award.processed_at.isoformat() if mnr2_award.processed_at else None,
                    'points_deducted_direct': mnr2_award.deduction_amount_direct or 0,
                    'points_deducted_matching': mnr2_award.deduction_amount_matching or 0,
                    'total_points_consumed': points_consumed,
                    'dispatch_date': mnr2_award.dispatch_date.isoformat() if mnr2_award.dispatch_date else None,
                    'received_date': mnr2_award.received_date.isoformat() if mnr2_award.received_date else None
                }
                
                # Add member contribution breakdown if deductions were applied
                if mnr2_award.deduction_amount_direct > 0:
                    # DC PROTOCOL: Read from immutable snapshot (single source of truth)
                    # NEW: Use stored contributor snapshot if available, otherwise fall back to recalculation
                    if mnr2_award.direct_contributors_snapshot:
                        # Use stored snapshot (immutable data - never changes after claim)
                        result['direct_members_consumed'] = mnr2_award.direct_contributors_snapshot
                        result['direct_achievement_count'] = mnr2_award.direct_count_achieved or 0
                    else:
                        # FALLBACK: Legacy bonanzas without snapshots - recalculate (will be backfilled)
                        # NOTE: This re-calculation is why activation date changes broke User 145's bonanza
                        from sqlalchemy import and_
                        referrals = db.query(User).filter(
                            and_(
                                User.referrer_id == mnr2_award.user_id,
                                User.coupon_status == 'Activated'
                            )
                        ).order_by(User.activation_date.asc()).all()
                        
                        consumed_referrals = referrals[:mnr2_award.deduction_amount_direct]
                        direct_members = []
                        for ref in consumed_referrals:
                            points = float(ref.package_points) if ref.package_points else 0
                            package_name = ref.get_package_type() if hasattr(ref, 'get_package_type') else ('Platinum' if points >= 1.0 else ('Diamond' if points >= 0.5 else 'Other'))
                            
                            direct_members.append({
                                'user_id': ref.id,
                                'name': ref.name,
                                'package': package_name,
                                'points': points,
                                'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
                            })
                        
                        result['direct_members_consumed'] = direct_members
                        result['direct_achievement_count'] = mnr2_award.direct_count_achieved or 0
                
                if mnr2_award.deduction_amount_matching > 0:
                    # DC PROTOCOL: Read from immutable snapshot (single source of truth)
                    # NEW: Use stored contributor snapshot if available, otherwise fall back to recalculation
                    if mnr2_award.matching_contributors_snapshot:
                        # Use stored snapshot (immutable data - never changes after claim)
                        result['matching_breakdown'] = mnr2_award.matching_contributors_snapshot
                    else:
                        # FALLBACK: Legacy bonanzas without snapshots - recalculate (will be backfilled)
                        # Get user's binary tree position
                        user = db.query(User).filter(User.id == mnr2_award.user_id).first()
                        if not user:
                            result['matching_note'] = f'{mnr2_award.deduction_amount_matching} matching pairs consumed (user not found)'
                            return result
                        
                        # Get left and right leg members (SAME LOGIC as matching awards)
                        left_leg = db.query(User).filter(
                            User.position.like(f'{user.position}L%'),
                            User.coupon_status == 'Activated'
                        ).order_by(User.activation_date.asc()).all()
                        
                        right_leg = db.query(User).filter(
                            User.position.like(f'{user.position}R%'),
                            User.coupon_status == 'Activated'
                        ).order_by(User.activation_date.asc()).all()
                        
                        # Calculate points for each leg
                        left_points = sum(float(m.package_points or 0) for m in left_leg)
                        right_points = sum(float(m.package_points or 0) for m in right_leg)
                    
                    # Build member details for each leg (SAME FORMAT as matching awards)
                    def build_leg_details(members):
                        return [{
                            'user_id': m.id,
                            'name': m.name,
                            'position': m.position,
                            'package': m.get_package_type() if hasattr(m, 'get_package_type') else ('Platinum' if (m.package_points or 0) >= 1.0 else ('Diamond' if (m.package_points or 0) >= 0.5 else 'Other')),
                            'points': float(m.package_points or 0),
                            'activation_date': m.activation_date.isoformat() if m.activation_date else None
                        } for m in members]
                    
                    left_details = build_leg_details(left_leg)
                    right_details = build_leg_details(right_leg)
                    
                    # Calculate matching pairs consumed
                    matching_pairs = min(left_points, right_points)
                    
                    # Add matching breakdown (IDENTICAL STRUCTURE to matching awards)
                    result['matching_breakdown'] = {
                        'pairs_consumed': mnr2_award.deduction_amount_matching or 0,
                        'total_pairs_available': matching_pairs,
                        'left_leg': {
                            'points': left_points,
                            'total_members': len(left_leg),
                            'members': left_details
                        },
                        'right_leg': {
                            'points': right_points,
                            'total_members': len(right_leg),
                            'members': right_details
                        }
                    }
                    result['matching_achievement_count'] = mnr2_award.matching_count_achieved or 0
                
                return result
            
            # DC Protocol: Fallback removed - DynamicBonanzaHistory is the ONLY source of truth
            # Legacy BonanzaProgress table is deprecated
            raise HTTPException(status_code=404, detail="Bonanza award not found in DynamicBonanzaHistory")
            
            # Get bonanza and reward details (old system)
            bonanza = db.query(DynamicBonanza).filter(DynamicBonanza.id == award.bonanza_id).first()
            reward = db.query(DynamicBonanzaReward).filter(DynamicBonanzaReward.id == award.reward_id).first() if award.reward_id else None
            
            result = {
                'success': True,
                'award_type': 'bonanza',
                'award_id': award_id,
                'user_id': award.user_id,
                'bonanza_name': bonanza.bonanza_name if bonanza else 'Unknown',
                'reward_name': reward.reward_name if reward else 'N/A',
                'reward_amount': float(reward.reward_value) if reward and reward.reward_value else 0,
                'has_direct_target': bonanza.has_direct_target if bonanza else False,
                'has_matching_target': bonanza.has_matching_target if bonanza else False
            }
            
            # If has direct target, show direct referrals breakdown
            if bonanza and bonanza.has_direct_target and reward and reward.direct_referral_target:
                referrals = db.query(User).filter(
                    and_(
                        User.referrer_id == award.user_id,
                        User.activation_date >= datetime(2025, 10, 21)
                    )
                ).order_by(User.activation_date.asc()).all()
                
                direct_points = 0
                all_referral_details = []
                for ref in referrals:
                    points = float(ref.package_points) if ref.package_points else 0
                    direct_points += points
                    
                    if points >= 1.0:
                        package_name = 'Platinum'
                    elif points >= 0.5:
                        package_name = 'Diamond'
                    else:
                        package_name = 'Other'
                    
                    all_referral_details.append({
                        'user_id': ref.id,
                        'name': ref.name,
                        'package': package_name,
                        'points': points,
                        'activation_date': ref.activation_date.isoformat() if ref.activation_date else None
                    })
                
                # Progressive allocation for direct target
                tier_requirement = reward.direct_referral_target
                allocated_count = 0
                allocated_members = []
                surplus_members = []
                
                for member in all_referral_details:
                    if allocated_count < tier_requirement:
                        allocated_members.append(member)
                        allocated_count += member['points']
                    else:
                        surplus_members.append(member)
                
                result['direct_target'] = {
                    'requirement': tier_requirement,
                    'current_achievement': direct_points,
                    'total_members': len(referrals),
                    'allocated_members': allocated_members,
                    'surplus_members': surplus_members
                }
            
            # If has matching target, show matching pairs breakdown
            if bonanza and bonanza.has_matching_target and reward and reward.matching_referral_target:
                # Left leg members
                left_leg = db.query(User).join(
                    Placement, Placement.child_id == User.id
                ).filter(
                    and_(
                        Placement.parent_id == award.user_id,
                        Placement.side == 'left',
                        User.activation_date >= datetime(2025, 10, 21)
                    )
                ).order_by(User.activation_date.asc()).all()
                
                # Right leg members
                right_leg = db.query(User).join(
                    Placement, Placement.child_id == User.id
                ).filter(
                    and_(
                        Placement.parent_id == award.user_id,
                        Placement.side == 'right',
                        User.activation_date >= datetime(2025, 10, 21)
                    )
                ).order_by(User.activation_date.asc()).all()
                
                # Calculate points for each leg
                left_points = 0
                left_details = []
                for member in left_leg:
                    points = float(member.package_points) if member.package_points else 0
                    left_points += points
                    
                    if points >= 1.0:
                        package_name = 'Platinum'
                    elif points >= 0.5:
                        package_name = 'Diamond'
                    else:
                        package_name = 'Other'
                    
                    left_details.append({
                        'user_id': member.id,
                        'name': member.name,
                        'package': package_name,
                        'points': points,
                        'activation_date': member.activation_date.isoformat() if member.activation_date else None
                    })
                
                right_points = 0
                right_details = []
                for member in right_leg:
                    points = float(member.package_points) if member.package_points else 0
                    right_points += points
                    
                    if points >= 1.0:
                        package_name = 'Platinum'
                    elif points >= 0.5:
                        package_name = 'Diamond'
                    else:
                        package_name = 'Other'
                    
                    right_details.append({
                        'user_id': member.id,
                        'name': member.name,
                        'package': package_name,
                        'points': points,
                        'activation_date': member.activation_date.isoformat() if member.activation_date else None
                    })
                
                # Calculate matching pairs
                matching_pairs = min(left_points, right_points)
                tier_requirement = reward.matching_referral_target
                
                # Progressive allocation for matching
                def split_leg_members(members, requirement):
                    allocated = []
                    surplus = []
                    allocated_points = 0
                    for member in members:
                        if allocated_points < requirement:
                            allocated.append(member)
                            allocated_points += member['points']
                        else:
                            surplus.append(member)
                    return allocated, surplus
                
                left_allocated, left_surplus = split_leg_members(left_details, tier_requirement)
                right_allocated, right_surplus = split_leg_members(right_details, tier_requirement)
                
                result['matching_target'] = {
                    'requirement': tier_requirement,
                    'current_achievement': matching_pairs,
                    'left_leg': {
                        'points': left_points,
                        'total_members': len(left_leg),
                        'allocated_members': left_allocated,
                        'surplus_members': left_surplus
                    },
                    'right_leg': {
                        'points': right_points,
                        'total_members': len(right_leg),
                        'allocated_members': right_allocated,
                        'surplus_members': right_surplus
                    }
                }
            
            return result
        
        else:
            raise HTTPException(status_code=400, detail="Invalid award_type. Must be 'direct', 'matching', or 'bonanza'")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in award breakdown endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching award breakdown: {str(e)}"
        )
