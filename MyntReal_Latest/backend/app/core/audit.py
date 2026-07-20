"""
Audit Logging System
Tracks all critical operations for security and compliance
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from app.models.user import User

logger = logging.getLogger(__name__)

class AuditLogger:
    """Centralized audit logging"""
    
    @staticmethod
    def log_action(
        db: Session,
        user: User,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log an audit event
        
        Args:
            db: Database session
            user: User performing the action
            action: Action performed (e.g., 'CREATE', 'UPDATE', 'DELETE', 'APPROVE')
            resource_type: Type of resource (e.g., 'USER', 'TRANSACTION', 'KYC')
            resource_id: ID of the resource
            details: Additional details as dict
            ip_address: User's IP address
        """
        user_id = str(getattr(user, 'id', 'SYSTEM'))
        user_type = str(getattr(user, 'user_type', 'UNKNOWN'))
        
        audit_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'user_type': user_type,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details or {},
            'ip_address': ip_address
        }
        
        # Log to structured logger (can be extended to database table)
        logger.info(f"[AUDIT] {audit_entry}")
        
        # TODO: Save to audit_log table when created
        # audit_log = AuditLog(**audit_entry)
        # db.add(audit_log)
        # db.commit()
        
        return audit_entry
    
    @staticmethod
    def log_financial_operation(
        db: Session,
        user: User,
        operation: str,
        amount: float,
        transaction_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log financial operations with special handling"""
        return AuditLogger.log_action(
            db=db,
            user=user,
            action=operation,
            resource_type='FINANCIAL',
            resource_id=transaction_id,
            details={
                **(details or {}),
                'amount': amount,
                'flagged_for_review': amount > 10000  # Flag large transactions
            }
        )
    
    @staticmethod
    def log_admin_action(
        db: Session,
        admin: User,
        action: str,
        target_user_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log admin actions on user accounts"""
        return AuditLogger.log_action(
            db=db,
            user=admin,
            action=action,
            resource_type='USER_ADMIN_ACTION',
            resource_id=target_user_id,
            details=details
        )
    
    @staticmethod
    def log_rvz_action(
        db: Session,
        action: str = None,
        action_type: str = None,
        resource_type: str = None,
        target_type: str = None,
        resource_id: Any = None,
        target_id: str = None,
        rvz_user_id: int = None,
        current_user: Any = None,
        details: Optional[Dict[str, Any]] = None,
        old_value: str = None,
        new_value: str = None,
        ip_address: Optional[str] = None
    ):
        """
        Log RVZ/Staff admin actions for audit trail
        DC Protocol: Supports multiple call signatures for backward compatibility
        """
        # Normalize parameters (handle different call signatures)
        final_action = action or action_type or "RVZ_ACTION"
        final_resource_type = resource_type or target_type or "UNKNOWN"
        final_resource_id = str(resource_id) if resource_id else (target_id or None)
        
        # Build user info
        user_id = rvz_user_id
        if current_user:
            user_id = getattr(current_user, 'id', None) or getattr(current_user, 'employee_id', None) or user_id
        
        audit_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': str(user_id) if user_id else 'SYSTEM',
            'user_type': 'RVZ',
            'action': final_action,
            'resource_type': final_resource_type,
            'resource_id': final_resource_id,
            'details': {
                **(details or {}),
                'old_value': old_value,
                'new_value': new_value
            } if old_value or new_value else (details or {}),
            'ip_address': ip_address
        }
        
        # Log to structured logger
        logger.info(f"[RVZ_AUDIT] {audit_entry}")
        
        return audit_entry

    @staticmethod
    def log_staff_page_action(
        db: Session,
        staff_user: Any,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        emp_code = getattr(staff_user, 'emp_code', None) or str(getattr(staff_user, 'id', 'UNKNOWN'))
        role_code = ''
        if hasattr(staff_user, 'role') and staff_user.role:
            role_code = getattr(staff_user.role, 'role_code', '')
        staff_type = getattr(staff_user, 'staff_type', '') or ''

        audit_entry = {
            'timestamp': datetime.utcnow(),
            'staff_id': emp_code,
            'staff_type': staff_type,
            'role_code': role_code,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details or {},
            'ip_address': ip_address,
            'access_model': 'MENU_BASED'
        }
        logger.info(f"[STAFF_PAGE_AUDIT] {audit_entry}")
        return audit_entry
