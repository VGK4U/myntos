"""
DC Protocol: Unified Award Status Constants
Single source of truth for all award status values across the system
"""

from enum import Enum
from typing import Dict


class AwardStatus(str, Enum):
    """
    DC Protocol: Unified status values for all award types
    (Direct Awards, Matching Awards, Bonanza Awards)
    
    Workflow: Pending Validation → Validated → Ready for Procurement → Ordered → Dispatched → Delivered
    
    User-Facing Labels:
    - Pending Approval = "Pending Validation" (auto-validated, staff can approve)
    - Admin Approved = "Validated" (staff validation complete)
    - Procurement Pending = "Ready for Procurement" (Accounts/VGK Supreme approval)
    - Processed for Dispatch = "Ordered" (procurement completed, waiting to ship)
    - Dispatched = "Dispatched" (shipped, in transit)
    """
    PENDING_APPROVAL = "Pending Approval"
    ADMIN_APPROVED = "Admin Approved"  # DB value - Staff validation stage
    PROCUREMENT_PENDING = "Procurement Pending"  # DB value - Ready for procurement
    PROCESSED_FOR_DISPATCH = "Processed for Dispatch"  # DB value - Ordered, waiting to ship
    DISPATCHED = "Dispatched"  # DB value - Shipped, in transit
    DELIVERED = "Delivered"
    REJECTED = "Rejected"
    RETURNED_FOR_CORRECTION = "Returned for Correction"
    
    # Aliases for backward compatibility and code clarity
    VALIDATED = "Admin Approved"  # Alias for ADMIN_APPROVED (staff validated)
    READY_FOR_PROCUREMENT = "Procurement Pending"  # Alias for PROCUREMENT_PENDING
    ORDERED = "Processed for Dispatch"  # Alias for PROCESSED_FOR_DISPATCH


LEGACY_TO_DC_PROTOCOL_MAPPING: Dict[str, str] = {
    # Legacy lowercase/snake_case → DC Protocol
    'pending': AwardStatus.PENDING_APPROVAL,
    'pending_approval': AwardStatus.PENDING_APPROVAL,
    'pending_admin_review': AwardStatus.PENDING_APPROVAL,
    'pending_validation': AwardStatus.PENDING_APPROVAL,
    
    # Validated (Staff validation complete)
    'admin_approved': AwardStatus.ADMIN_APPROVED,
    'finance_approved': AwardStatus.ADMIN_APPROVED,
    'pending_super_admin': AwardStatus.ADMIN_APPROVED,
    'validated': AwardStatus.ADMIN_APPROVED,
    
    # Ready for Procurement (Accounts/VGK approved)
    'rvz_approved': AwardStatus.PROCUREMENT_PENDING,
    'procurement_pending': AwardStatus.PROCUREMENT_PENDING,
    'ready_for_procurement': AwardStatus.PROCUREMENT_PENDING,
    
    # Processed for Dispatch (Ordered)
    'pending_finance': AwardStatus.PROCESSED_FOR_DISPATCH,
    'finance_processed': AwardStatus.PROCESSED_FOR_DISPATCH,
    'processed_for_dispatch': AwardStatus.PROCESSED_FOR_DISPATCH,
    'ordered': AwardStatus.PROCESSED_FOR_DISPATCH,
    
    # Dispatched (Shipped)
    'dispatched': AwardStatus.DISPATCHED,
    'shipped': AwardStatus.DISPATCHED,
    'in_transit': AwardStatus.DISPATCHED,
    
    # Delivered
    'completed': AwardStatus.DELIVERED,
    'delivered': AwardStatus.DELIVERED,
    
    # Rejected
    'rejected': AwardStatus.REJECTED,
    'returned_for_correction': AwardStatus.RETURNED_FOR_CORRECTION,
}


def normalize_status(status: str) -> str:
    """
    Convert any status value (legacy or DC Protocol) to DC Protocol format
    
    Args:
        status: Status value (can be legacy or DC Protocol)
    
    Returns:
        DC Protocol status value
    """
    if not status:
        return AwardStatus.PENDING_APPROVAL
    
    # If already DC Protocol value, return as-is
    try:
        if status in [s.value for s in AwardStatus]:
            return status
    except:
        pass
    
    # Try to map from legacy
    status_lower = status.lower().replace(' ', '_')
    return LEGACY_TO_DC_PROTOCOL_MAPPING.get(status_lower, status)


def is_valid_dc_status(status: str) -> bool:
    """
    Check if a status value is a valid DC Protocol status
    
    Args:
        status: Status value to check
    
    Returns:
        True if valid DC Protocol status, False otherwise
    """
    return status in [s.value for s in AwardStatus]
