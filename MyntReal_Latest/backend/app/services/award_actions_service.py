"""
DC Protocol: Award Actions Service
Calculates available actions for awards based on current status and user role

This service powers dynamic action buttons in frontend by returning
which actions are available for each award based on:
1. Current processed_status of the award
2. User's role (Finance Admin, RVZ, Admin, etc.)
3. RVZ Supreme authority override capabilities

Author: MNR Development Team
Date: Nov 11, 2025
"""

from typing import List, Dict, Any
from app.constants.award_statuses import AwardStatus, normalize_status


class AwardActionsService:
    """
    Service to calculate available actions for awards based on status and role
    
    Returns action objects with:
    - action_id: Unique identifier for the action
    - label: User-facing button text
    - type: 'primary', 'success', 'danger', 'warning'
    - requires_modal: Boolean - whether action needs input modal
    """
    
    # Action definitions
    ACTIONS = {
        'finance_approve': {
            'action_id': 'finance_approve',
            'label': 'APPROVE',
            'type': 'success',
            'requires_modal': False,
            'api_endpoint': '/api/v1/unified-awards/finance-approve'
        },
        'finance_reject': {
            'action_id': 'finance_reject',
            'label': 'REJECT',
            'type': 'danger',
            'requires_modal': True,  # Need rejection reason
            'api_endpoint': '/api/v1/unified-awards/reject'
        },
        'rvz_direct_approve': {
            'action_id': 'rvz_direct_approve',
            'label': 'RVZ DIRECT APPROVE',
            'type': 'primary',
            'requires_modal': False,
            'api_endpoint': '/api/v1/unified-awards/rvz-direct-approve'
        },
        'rvz_approve': {
            'action_id': 'rvz_approve',
            'label': 'RVZ APPROVE',
            'type': 'success',
            'requires_modal': False,
            'api_endpoint': '/api/v1/unified-awards/rvz-approve'
        },
        'rvz_reject': {
            'action_id': 'rvz_reject',
            'label': 'RVZ REJECT',
            'type': 'danger',
            'requires_modal': True,
            'api_endpoint': '/api/v1/unified-awards/reject'
        },
        'record_procurement': {
            'action_id': 'record_procurement',
            'label': 'RECORD PROCUREMENT',
            'type': 'primary',
            'requires_modal': True,  # Need cost, vendor details
            'api_endpoint': '/api/v1/unified-awards/record-procurement'
        },
        'mark_dispatched': {
            'action_id': 'mark_dispatched',
            'label': 'MARK AS DISPATCHED',
            'type': 'warning',
            'requires_modal': True,  # Need dispatch details
            'api_endpoint': '/api/v1/unified-awards/mark-dispatched'
        },
        'mark_delivered': {
            'action_id': 'mark_delivered',
            'label': 'MARK AS DELIVERED',
            'type': 'success',
            'requires_modal': True,  # Need delivery confirmation
            'api_endpoint': '/api/v1/unified-awards/mark-delivered'
        },
        'view_details': {
            'action_id': 'view_details',
            'label': 'VIEW DETAILS',
            'type': 'info',
            'requires_modal': False,
            'api_endpoint': None  # Frontend handles this
        }
    }
    
    @staticmethod
    def get_available_actions(
        processed_status: str,
        user_role: str,
        award_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate which actions are available based on status and role
        
        Args:
            processed_status: Current award status
            user_role: User's role (Finance Admin, RVZ ID, Admin, etc.)
            award_type: Optional - 'direct', 'matching', 'bonanza'
        
        Returns:
            List of action dictionaries
        """
        actions = []
        
        # DC PROTOCOL: Normalize status (convert "Pending" to "Pending Approval", etc.)
        status = normalize_status(processed_status) if processed_status else AwardStatus.PENDING_APPROVAL
        
        # ========== PENDING APPROVAL STAGE ==========
        if status == AwardStatus.PENDING_APPROVAL:
            if user_role == 'Finance Admin':
                actions.append(AwardActionsService.ACTIONS['finance_approve'])
                actions.append(AwardActionsService.ACTIONS['finance_reject'])
            
            if user_role == 'RVZ ID':
                actions.append(AwardActionsService.ACTIONS['rvz_direct_approve'])
                actions.append(AwardActionsService.ACTIONS['rvz_reject'])
        
        # ========== ADMIN APPROVED (FINANCE APPROVED) STAGE ==========
        elif status == AwardStatus.ADMIN_APPROVED:
            if user_role == 'RVZ ID':
                actions.append(AwardActionsService.ACTIONS['rvz_approve'])
                actions.append(AwardActionsService.ACTIONS['rvz_reject'])
            else:
                # Other roles can only view
                actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== PROCUREMENT PENDING (RVZ APPROVED) STAGE ==========
        elif status == AwardStatus.PROCUREMENT_PENDING:
            # Admin or Finance can record procurement
            if user_role in ['Admin', 'Finance Admin', 'RVZ ID']:
                actions.append(AwardActionsService.ACTIONS['record_procurement'])
            else:
                actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== PROCESSED FOR DISPATCH (ORDERED) STAGE ==========
        elif status == AwardStatus.PROCESSED_FOR_DISPATCH:
            # Procurement complete, can mark as dispatched (ship item)
            if user_role in ['Admin', 'Finance Admin', 'RVZ ID']:
                actions.append(AwardActionsService.ACTIONS['mark_dispatched'])
            else:
                actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== DISPATCHED (SHIPPED) STAGE ==========
        elif status == AwardStatus.DISPATCHED:
            # Item shipped, can mark as delivered (final stage)
            if user_role in ['Admin', 'Finance Admin', 'RVZ ID']:
                actions.append(AwardActionsService.ACTIONS['mark_delivered'])
            else:
                actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== DELIVERED STAGE ==========
        elif status == AwardStatus.DELIVERED:
            # Terminal state - only view
            actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== REJECTED STAGE ==========
        elif status == AwardStatus.REJECTED:
            # Rejected awards can be viewed but not re-approved automatically
            # RVZ/Finance would need to manually change status if needed
            actions.append(AwardActionsService.ACTIONS['view_details'])
        
        # ========== DEFAULT ==========
        else:
            actions.append(AwardActionsService.ACTIONS['view_details'])
        
        return actions
    
    @staticmethod
    def get_status_display_label(processed_status: str) -> str:
        """
        Get user-friendly display label for status
        
        DC Protocol: Maps DB values to user-facing labels
        - "Admin Approved" → "Finance Approved"
        - "Procurement Pending" → "RVZ Approved"
        - "Processed for Dispatch" → "Ordered"
        - "Dispatched" → "Dispatched"
        """
        mapping = {
            AwardStatus.PENDING_APPROVAL: "Pending Approval",
            AwardStatus.ADMIN_APPROVED: "Finance Approved",
            AwardStatus.PROCUREMENT_PENDING: "RVZ Approved",
            AwardStatus.PROCESSED_FOR_DISPATCH: "Ordered",
            AwardStatus.DISPATCHED: "Dispatched",
            AwardStatus.DELIVERED: "Delivered",
            AwardStatus.REJECTED: "Rejected",
            AwardStatus.RETURNED_FOR_CORRECTION: "Returned for Correction"
        }
        return mapping.get(processed_status, processed_status)
    
    @staticmethod
    def get_status_badge_color(processed_status: str) -> str:
        """
        Get Bootstrap badge color class for status
        
        Returns: 'warning', 'info', 'success', 'primary', 'danger', 'secondary'
        """
        mapping = {
            AwardStatus.PENDING_APPROVAL: "warning",  # Yellow
            AwardStatus.ADMIN_APPROVED: "secondary",  # Gray
            AwardStatus.PROCUREMENT_PENDING: "primary",  # Blue
            AwardStatus.PROCESSED_FOR_DISPATCH: "info",  # Light Blue (Ordered)
            AwardStatus.DISPATCHED: "purple",  # Purple (Shipped)
            AwardStatus.DELIVERED: "success",  # Green
            AwardStatus.REJECTED: "danger",  # Red
            AwardStatus.RETURNED_FOR_CORRECTION: "warning"  # Yellow
        }
        return mapping.get(processed_status, "secondary")
    
    @staticmethod
    def get_user_friendly_status_message(processed_status: str) -> str:
        """
        Get detailed user-facing status message for user dashboard
        
        Returns helpful explanations for each status
        """
        messages = {
            AwardStatus.PENDING_APPROVAL: "Your award claim is under review by our finance team.",
            AwardStatus.ADMIN_APPROVED: "Finance approved! Awaiting RVZ final approval.",
            AwardStatus.PROCUREMENT_PENDING: "RVZ approved! We're procuring your gift.",
            AwardStatus.PROCESSED_FOR_DISPATCH: "Your gift has been ordered! Waiting for dispatch.",
            AwardStatus.DISPATCHED: "Your award is on its way! Check tracking details below.",
            AwardStatus.DELIVERED: "Delivered successfully! Enjoy your reward! 🎉",
            AwardStatus.REJECTED: "Your claim was not approved. See rejection reason below.",
            AwardStatus.RETURNED_FOR_CORRECTION: "Please provide additional information to proceed."
        }
        return messages.get(processed_status, "Status: " + processed_status)
