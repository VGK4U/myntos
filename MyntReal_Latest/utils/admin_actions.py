"""
Admin Actions Service Module
===========================

Provides centralized admin action management with permission checking,
audit logging, and consistent action execution patterns.

Author: System Generated
Date: September 18, 2025
"""

from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from flask import current_app
import uuid


class AdminActionsService:
    """
    Centralized service for handling admin actions with proper permission
    checking, audit logging, and consistent execution patterns.
    """
    
    # Role hierarchy levels for permission checking
    ROLE_LEVELS = {
        'Member': 0,
        'Finance Admin': 5,
        'Admin': 8,
        'Super Admin': 10,
        'VGK ID': 15
    }
    
    @staticmethod
    def get_user_role_level(user_type):
        """
        Get numeric role level for permission comparison.
        
        Args:
            user_type (str): User role type
            
        Returns:
            int: Role level (higher = more permissions)
        """
        return AdminActionsService.ROLE_LEVELS.get(user_type, 0)
    
    @staticmethod
    def can_perform_action(actor_user, target_user, action_type):
        """
        Check if actor can perform specific action on target user.
        
        Args:
            actor_user: User performing the action
            target_user: User being acted upon
            action_type (str): Type of action being performed
            
        Returns:
            tuple: (bool, str) - (can_perform, message)
        """
        try:
            # VGK ID has unlimited privileges - bypass all restrictions
            if actor_user.user_type == 'VGK ID':
                return True, "VGK ID has unlimited access"
            
            actor_level = AdminActionsService.get_user_role_level(actor_user.user_type)
            target_level = AdminActionsService.get_user_role_level(target_user.user_type)
            
            # Basic rule: Cannot act on users with equal or higher role level
            if target_level >= actor_level and actor_user.id != target_user.id:
                return False, f"Insufficient privileges. Cannot act on {target_user.user_type} users."
            
            # Action-specific rules
            if action_type == 'role_management':
                if actor_user.user_type not in ['Super Admin', 'VGK ID']:
                    return False, "Only Super Admin or VGK ID can change user roles"
            
            elif action_type == 'financial_action':
                if actor_user.user_type not in ['Finance Admin', 'Super Admin', 'VGK ID']:
                    return False, "Only Finance Admin, Super Admin, or VGK ID can perform financial actions"
            
            elif action_type == 'security_action':
                if actor_user.user_type not in ['Admin', 'Super Admin', 'VGK ID']:
                    return False, "Only Admin, Super Admin, or VGK ID can perform security actions"
            
            # Self-action restrictions (except for VGK ID)
            if actor_user.id == target_user.id and action_type in ['role_management', 'account_status'] and actor_user.user_type != 'VGK ID':
                return False, "Cannot perform this action on your own account"
            
            return True, "Action permitted"
            
        except Exception as e:
            return False, f"Permission check failed: {str(e)}"
    
    @staticmethod
    def log_admin_action(action_type, action_subtype, actor_user, target_user=None, 
                        action_data=None, reason=None, notes=None, ip_address=None, 
                        user_agent=None, requires_approval=False, success=True, error_message=None, **kwargs):
        """
        Log admin action with full audit trail.
        
        Args:
            action_type (str): Primary action category
            action_subtype (str): Specific action subtype
            actor_user: User performing action
            target_user: User being acted upon (optional)
            action_data (dict): Additional action details
            reason (str): Reason for the action
            notes (str): Additional notes
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            requires_approval (bool): Whether action requires approval
            success (bool): Whether action was successful (backward compatibility)
            error_message (str): Error message if failed (backward compatibility)
            **kwargs: Additional parameters for backward compatibility
            
        Returns:
            UserAction: Created action record or None if failed
        """
        try:
            # Import here to avoid circular imports
            from app import db, UserAction
            
            # Create action record
            action = UserAction(
                performed_by_id=actor_user.id if actor_user else None,
                target_user_id=target_user.id if target_user else None,
                action_type=action_type,
                action_subtype=action_subtype,
                action_data=action_data or {},
                reason=reason,
                notes=notes,
                requires_approval=requires_approval,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(action)
            db.session.commit()
            
            return action
            
        except Exception as e:
            # Don't let logging failures break the main action
            print(f"Failed to log admin action: {str(e)}")
            return None
    
    @staticmethod
    def change_account_status(actor_user, target_user, new_status, reason, notes, 
                            ip_address=None, user_agent=None):
        """
        Change user account status with validation and logging.
        
        Args:
            actor_user: User performing the action
            target_user: User whose status is being changed
            new_status (str): New account status
            reason (str): Reason for status change
            notes (str): Additional notes
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (bool, str) - (success, message)
        """
        try:
            # Import here to avoid circular imports
            from app import db
            
            # Permission check
            can_act, message = AdminActionsService.can_perform_action(
                actor_user, target_user, 'account_status'
            )
            
            if not can_act:
                return False, message
            
            # Validate status
            valid_statuses = ['Active', 'Suspended', 'Pending']
            if new_status not in valid_statuses:
                return False, f"Invalid status. Must be one of: {valid_statuses}"
            
            old_status = target_user.account_status
            target_user.account_status = new_status
            
            # Log the action
            action_details = {
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason,
                'notes': notes
            }
            
            AdminActionsService.log_admin_action(
                action_type='account_status',
                action_subtype=f'change_to_{new_status.lower()}',
                actor_user=actor_user,
                target_user=target_user,
                action_data=action_details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            
            return True, f"Account status changed from {old_status} to {new_status}"
            
        except Exception as e:
            from app import db
            db.session.rollback()
            return False, f"Failed to change account status: {str(e)}"
    
    @staticmethod
    def update_kyc_status(actor_user, target_user, new_kyc_status, reason, notes,
                         ip_address=None, user_agent=None):
        """
        Update user KYC status with validation and logging.
        
        Args:
            actor_user: User performing the action
            target_user: User whose KYC status is being updated
            new_kyc_status (str): New KYC status
            reason (str): Reason for status change
            notes (str): Additional notes
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (bool, str) - (success, message)
        """
        try:
            from app import db
            
            # Permission check
            can_act, message = AdminActionsService.can_perform_action(
                actor_user, target_user, 'kyc_action'
            )
            
            if not can_act:
                return False, message
            
            # Validate KYC status
            valid_statuses = ['Pending', 'Approved', 'Rejected', 'Under Review']
            if new_kyc_status not in valid_statuses:
                return False, f"Invalid KYC status. Must be one of: {valid_statuses}"
            
            old_kyc_status = target_user.kyc_status
            target_user.kyc_status = new_kyc_status
            
            # Log the action
            action_details = {
                'old_kyc_status': old_kyc_status,
                'new_kyc_status': new_kyc_status,
                'reason': reason,
                'notes': notes
            }
            
            AdminActionsService.log_admin_action(
                action_type='kyc_action',
                action_subtype=f'status_change_{new_kyc_status.lower().replace(" ", "_")}',
                actor_user=actor_user,
                target_user=target_user,
                action_data=action_details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            
            return True, f"KYC status updated from {old_kyc_status} to {new_kyc_status}"
            
        except Exception as e:
            from app import db
            db.session.rollback()
            return False, f"Failed to update KYC status: {str(e)}"
    
    @staticmethod
    def adjust_wallet_balance(actor_user, target_user, amount, transaction_type, reason, notes,
                            ip_address=None, user_agent=None):
        """
        Adjust user wallet balance with validation and logging.
        
        Args:
            actor_user: User performing the action
            target_user: User whose wallet is being adjusted
            amount (float): Amount to adjust (positive or negative)
            transaction_type (str): Type of transaction
            reason (str): Reason for adjustment
            notes (str): Additional notes
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (bool, str) - (success, message)
        """
        try:
            from app import db
            
            # Permission check
            can_act, message = AdminActionsService.can_perform_action(
                actor_user, target_user, 'financial_action'
            )
            
            if not can_act:
                return False, message
            
            # Validate amount
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                return False, "Invalid amount format"
            
            old_balance = target_user.wallet_balance
            new_balance = old_balance + amount
            
            # Prevent negative balances unless explicitly allowed
            if new_balance < 0:
                return False, "Adjustment would result in negative balance"
            
            target_user.wallet_balance = new_balance
            
            # Log the action
            action_details = {
                'old_balance': old_balance,
                'adjustment_amount': amount,
                'new_balance': new_balance,
                'transaction_type': transaction_type,
                'reason': reason,
                'notes': notes
            }
            
            AdminActionsService.log_admin_action(
                action_type='financial_action',
                action_subtype='wallet_adjustment',
                actor_user=actor_user,
                target_user=target_user,
                action_data=action_details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            
            return True, f"Wallet adjusted by ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}"
            
        except Exception as e:
            from app import db
            db.session.rollback()
            return False, f"Failed to adjust wallet balance: {str(e)}"
    
    @staticmethod
    def change_user_role(actor_user, target_user, new_role, reason, notes,
                        ip_address=None, user_agent=None):
        """
        Change user role with validation and logging.
        
        Args:
            actor_user: User performing the action
            target_user: User whose role is being changed
            new_role (str): New user role
            reason (str): Reason for role change
            notes (str): Additional notes
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (bool, str) - (success, message)
        """
        try:
            from app import db
            
            # Only Super Admin or VGK ID can change roles
            if actor_user.user_type not in ['Super Admin', 'VGK ID']:
                return False, "Only Super Admin or VGK ID can change user roles"
            
            # Validate role
            valid_roles = ['Member', 'Admin', 'Finance Admin', 'Super Admin', 'VGK ID']
            if new_role not in valid_roles:
                return False, f"Invalid role. Must be one of: {valid_roles}"
            
            # Prevent self-role changes (except for VGK ID)
            if actor_user.id == target_user.id and actor_user.user_type != 'VGK ID':
                return False, "Cannot change your own role"
            
            old_role = target_user.user_type
            target_user.user_type = new_role
            
            # Log the action
            action_details = {
                'old_user_type': old_role,
                'new_user_type': new_role,
                'role_elevation': AdminActionsService.get_user_role_level(new_role) > AdminActionsService.get_user_role_level(old_role),
                'reason': reason,
                'notes': notes
            }
            
            AdminActionsService.log_admin_action(
                action_type='role_management',
                action_subtype='role_change',
                actor_user=actor_user,
                target_user=target_user,
                action_data=action_details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.commit()
            
            return True, f"User role changed from {old_role} to {new_role}"
            
        except Exception as e:
            from app import db
            db.session.rollback()
            return False, f"Failed to change user role: {str(e)}"
    
    @staticmethod
    def create_bulk_operation(actor_user, operation_name, user_ids, operation_type, 
                            operation_data, ip_address=None, user_agent=None):
        """
        Create and initiate a bulk operation.
        
        Args:
            actor_user: User performing the bulk operation
            operation_name (str): Name/description of the operation
            user_ids (list): List of user IDs to act upon
            operation_type (str): Type of bulk operation
            operation_data (dict): Operation-specific data
            ip_address (str): Request IP address
            user_agent (str): Request user agent
            
        Returns:
            tuple: (bool, str|dict) - (success, message_or_operation_data)
        """
        try:
            from app import db, BulkOperation, User
            
            # Validate users exist and permissions
            existing_users = User.query.filter(User.id.in_(user_ids)).all()
            if len(existing_users) != len(user_ids):
                return False, "Some users not found"
            
            # Check permissions for all users
            unauthorized_users = []
            for user in existing_users:
                can_act, _ = AdminActionsService.can_perform_action(
                    actor_user, user, operation_type
                )
                if not can_act:
                    unauthorized_users.append(user.id)
            
            if unauthorized_users:
                return False, f"Insufficient permissions for users: {unauthorized_users}"
            
            # Create bulk operation record
            operation = BulkOperation(
                operation_id=str(uuid.uuid4()),
                actor_user_id=actor_user.id,
                operation_name=operation_name,
                operation_type=operation_type,
                total_users=len(user_ids),
                processed_users=0,
                successful_operations=0,
                failed_operations=0,
                status='In Progress',
                operation_data=operation_data,
                user_ids=user_ids,
                results=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(operation)
            db.session.commit()
            
            # Log the bulk operation initiation
            AdminActionsService.log_admin_action(
                action_type='bulk_operation',
                action_subtype='initiated',
                actor_user=actor_user,
                action_data={
                    'operation_id': operation.operation_id,
                    'operation_name': operation_name,
                    'operation_type': operation_type,
                    'total_users': len(user_ids)
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return True, {
                'operation_id': operation.operation_id,
                'status': 'initiated',
                'total_users': len(user_ids)
            }
            
        except Exception as e:
            from app import db
            db.session.rollback()
            return False, f"Failed to create bulk operation: {str(e)}"
    
    @staticmethod
    def get_bulk_operation_status(operation_id):
        """
        Get status of a bulk operation.
        
        Args:
            operation_id (str): Bulk operation ID
            
        Returns:
            dict: Operation status data
        """
        try:
            from app import BulkOperation
            
            operation = BulkOperation.query.filter_by(operation_id=operation_id).first()
            
            if not operation:
                return {'error': 'Operation not found'}
            
            return {
                'operation_id': operation.operation_id,
                'operation_name': operation.operation_name,
                'operation_type': operation.operation_type,
                'status': operation.status,
                'total_users': operation.total_users,
                'processed_users': operation.processed_users,
                'successful_operations': operation.successful_operations,
                'failed_operations': operation.failed_operations,
                'created_at': operation.created_at.isoformat(),
                'updated_at': operation.updated_at.isoformat(),
                'progress_percentage': round((operation.processed_users / operation.total_users) * 100, 2) if operation.total_users > 0 else 0
            }
            
        except Exception as e:
            return {'error': f'Failed to get operation status: {str(e)}'}
    
    @staticmethod
    def get_action_statistics(days=30):
        """
        Get admin action statistics for the specified number of days.
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            dict: Action statistics
        """
        try:
            from app import UserAction
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get total actions in period
            total_actions = UserAction.query.filter(
                UserAction.timestamp >= cutoff_date
            ).count()
            
            # Get successful vs failed actions
            successful_actions = UserAction.query.filter(
                UserAction.timestamp >= cutoff_date,
                UserAction.success == True
            ).count()
            
            failed_actions = total_actions - successful_actions
            
            # Get action breakdown by type
            from sqlalchemy import func
            action_types = UserAction.query.filter(
                UserAction.timestamp >= cutoff_date
            ).with_entities(
                UserAction.action_type,
                func.count(UserAction.id).label('count')
            ).group_by(UserAction.action_type).all()
            
            return {
                'period_days': days,
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'failed_actions': failed_actions,
                'success_rate': round((successful_actions / total_actions) * 100, 2) if total_actions > 0 else 0,
                'action_types': {action_type: count for action_type, count in action_types}
            }
            
        except Exception as e:
            return {
                'error': f'Failed to get action statistics: {str(e)}',
                'period_days': days,
                'total_actions': 0,
                'successful_actions': 0,
                'failed_actions': 0,
                'success_rate': 0,
                'action_types': {}
            }
    
    @staticmethod
    def get_recent_actions(actor_user=None, target_user=None, limit=50):
        """
        Get recent admin actions with optional filtering.
        
        Args:
            actor_user: Filter by user who performed actions
            target_user: Filter by user who was acted upon
            limit (int): Maximum number of actions to return
            
        Returns:
            list: List of recent actions
        """
        try:
            from app import UserAction
            
            query = UserAction.query
            
            if actor_user:
                query = query.filter(UserAction.actor_user_id == actor_user.id)
            
            if target_user:
                query = query.filter(UserAction.target_user_id == target_user.id)
            
            actions = query.order_by(UserAction.timestamp.desc()).limit(limit).all()
            
            return [{
                'action_id': action.action_id,
                'actor_user_id': action.actor_user_id,
                'target_user_id': action.target_user_id,
                'action_type': action.action_type,
                'action_subtype': action.action_subtype,
                'action_details': action.action_details,
                'success': action.success,
                'error_message': action.error_message,
                'timestamp': action.timestamp.isoformat() if action.timestamp else None,
                'ip_address': action.ip_address
            } for action in actions]
            
        except Exception as e:
            print(f"Failed to get recent actions: {str(e)}")
            return []