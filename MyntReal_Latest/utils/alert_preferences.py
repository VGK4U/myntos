"""
Alert preferences utility module
Provides functions to check if specific alerts should be sent based on VGK ID alert management settings
"""

from typing import Optional
from flask import current_app

def should_send_alert(alert_type: str, user_id: Optional[int] = None) -> bool:
    """
    Check if a specific alert type should be sent
    CRITICAL: Defaults to False on exceptions for security (fail-safe behavior)
    
    Args:
        alert_type: Type of alert (e.g., 'mail_alerts', 'whatsapp_alerts', 'system_alerts')
        user_id: Optional user ID for user-specific preferences (future enhancement)
        
    Returns:
        True if alert should be sent, False otherwise (FAIL-SAFE: False on error)
    """
    try:
        # Import models locally to avoid circular imports
        from app import AlertPreferences, WhatsAppControl, SystemControl
        
        # CRITICAL: Check SystemControl for global maintenance/pause first
        system_control = SystemControl.query.first()
        if system_control and system_control.is_maintenance_mode:
            # System is in maintenance mode - no alerts should be sent
            return False
        
        # Check global override (highest priority after maintenance)
        global_override = AlertPreferences.query.filter_by(alert_type='global_override').first()
        if global_override and not global_override.enabled:
            # Global override is paused - no alerts should be sent
            return False
            
        # Then check specific alert type
        alert_pref = AlertPreferences.query.filter_by(alert_type=alert_type).first()
        if alert_pref and not alert_pref.enabled:
            # This specific alert type is disabled
            return False
            
        # For WhatsApp, also check the WhatsAppControl
        if alert_type == 'whatsapp_alerts':
            whatsapp_control = WhatsAppControl.query.first()
            if whatsapp_control and whatsapp_control.is_paused:
                return False
                
        # Default to True if no preference found and no override (backwards compatibility)
        return True
        
    except Exception as e:
        # CRITICAL SECURITY FIX: Default to False (fail-safe) on exceptions
        # This prevents unintended alert leakage when system is meant to be paused
        if current_app:
            current_app.logger.error(f"ALERT SECURITY: Failed to check alert preferences for {alert_type}, BLOCKING for safety: {str(e)}")
        return False

def should_send_email_alert() -> bool:
    """Check if email alerts should be sent"""
    return should_send_alert('mail_alerts')

def should_send_whatsapp_alert() -> bool:
    """Check if WhatsApp alerts should be sent"""
    return should_send_alert('whatsapp_alerts')

def should_send_system_alert() -> bool:
    """Check if system alerts should be sent"""
    return should_send_alert('system_alerts')

def should_send_popup_alert() -> bool:
    """Check if popup/notification alerts should be sent"""
    return should_send_alert('popup_notifications')

def should_send_bulk_operation_alert() -> bool:
    """Check if bulk operation alerts should be sent"""
    return should_send_alert('bulk_operations')

def should_send_kyc_alert() -> bool:
    """Check if KYC change alerts should be sent"""
    return should_send_alert('kyc_changes')

def should_send_wallet_alert() -> bool:
    """Check if wallet alerts should be sent"""
    return should_send_alert('wallet_alerts')

def should_send_security_alert() -> bool:
    """Check if security alerts should be sent"""
    return should_send_alert('security_alerts')

def should_send_config_alert() -> bool:
    """Check if configuration alerts should be sent"""
    return should_send_alert('config_changes')

def is_whatsapp_paused() -> bool:
    """
    Check if WhatsApp messaging is globally paused
    CRITICAL: Defaults to True (paused) on exceptions for security (fail-safe behavior)
    """
    try:
        # Import models locally to avoid circular imports
        from app import WhatsAppControl, SystemControl
        
        # Check system maintenance first
        system_control = SystemControl.query.first()
        if system_control and system_control.is_maintenance_mode:
            return True
        
        # Check both alert preferences and WhatsApp control
        if not should_send_whatsapp_alert():
            return True
            
        whatsapp_control = WhatsAppControl.query.first()
        if whatsapp_control and whatsapp_control.is_paused:
            return True
            
        return False
        
    except Exception as e:
        # CRITICAL SECURITY FIX: Default to True (paused) on exceptions
        # This prevents unintended WhatsApp messages when system is meant to be paused
        if current_app:
            current_app.logger.error(f"WHATSAPP SECURITY: Failed to check pause status, PAUSING for safety: {str(e)}")
        return True

def get_alert_status(alert_type: str) -> dict:
    """
    Get detailed status information for a specific alert type
    
    Returns:
        Dict with status information including enabled state, last_updated, etc.
    """
    try:
        # Import models locally to avoid circular imports
        from app import AlertPreferences
        
        alert_pref = AlertPreferences.query.filter_by(alert_type=alert_type).first()
        if not alert_pref:
            return {
                'alert_type': alert_type,
                'enabled': True,  # Default enabled if not configured
                'configured': False,
                'last_updated': None
            }
            
        return {
            'alert_type': alert_type,
            'enabled': alert_pref.enabled,
            'configured': True,
            'last_updated': alert_pref.updated_at,
            'created_at': alert_pref.created_at
        }
        
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error getting alert status for {alert_type}: {str(e)}")
        return {
            'alert_type': alert_type,
            'enabled': True,
            'configured': False,
            'error': str(e)
        }

def get_all_alert_statuses() -> dict:
    """
    Get status for all configured alert types
    
    Returns:
        Dict with all alert statuses
    """
    alert_types = [
        'mail_alerts', 'whatsapp_alerts', 'popup_notifications', 'system_alerts',
        'bulk_operations', 'kyc_changes', 'wallet_alerts', 'security_alerts',
        'config_changes', 'global_override'
    ]
    
    statuses = {}
    for alert_type in alert_types:
        statuses[alert_type] = get_alert_status(alert_type)
        
    return statuses