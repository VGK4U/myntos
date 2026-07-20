"""
WhatsApp Messaging System with VGK ID Pause/Resume Controls
Handles WhatsApp OTP sending via Meta Cloud API with development/testing controls
"""

import os
import requests
from datetime import datetime
from typing import Dict, Optional


class WhatsAppMessaging:
    """Handle WhatsApp messaging with VGK ID controls using Meta Cloud API"""
    
    def __init__(self):
        self.access_token = os.environ.get("META_WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID")
        self.business_account_id = os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID")
        self.business_phone_number = "+918585852738"
        
        self._log_environment_status()
    
    def _log_environment_status(self):
        """Log environment variable status for debugging"""
        print("🔍 META WHATSAPP ENVIRONMENT DEBUG:")
        
        meta_vars = [
            "META_WHATSAPP_ACCESS_TOKEN",
            "META_WHATSAPP_PHONE_NUMBER_ID",
            "META_WHATSAPP_BUSINESS_ACCOUNT_ID",
            "META_WHATSAPP_VERIFY_TOKEN",
        ]
        for var in meta_vars:
            value = os.environ.get(var)
            if value:
                print(f"   ✅ {var}: Found ({value[:8]}...)")
            else:
                print(f"   ❌ {var}: Not found")
        
        if self.access_token and self.phone_number_id:
            print("✅ Meta Cloud API credentials ready")
        else:
            print("⚠️ Meta Cloud API credentials missing - using mock mode")
    
    def is_whatsapp_enabled(self) -> bool:
        """Check if WhatsApp messaging is enabled globally"""
        try:
            from app import AppSettings
            settings = AppSettings.query.first()
            if settings:
                return getattr(settings, 'whatsapp_enabled', True)
            return True
        except Exception:
            return True
    
    def is_whatsapp_paused_by_vgk(self) -> Dict[str, any]:
        """Check if WhatsApp is paused by VGK ID for development/testing"""
        try:
            from app import WhatsAppControl
            control = WhatsAppControl.query.first()
            if control:
                return {
                    'paused': control.is_paused,
                    'paused_by': control.paused_by_user_id,
                    'paused_at': control.paused_at,
                    'reason': control.pause_reason
                }
            return {'paused': False, 'paused_by': None, 'paused_at': None, 'reason': None}
        except Exception:
            return {'paused': False, 'paused_by': None, 'paused_at': None, 'reason': None}
    
    def send_whatsapp_otp(self, mobile_number: str, otp_code: str, user_name: str = None) -> Dict[str, any]:
        """
        Send OTP via WhatsApp using Meta Cloud API with VGK pause controls
        
        Args:
            mobile_number (str): Mobile number (+91XXXXXXXXXX format)
            otp_code (str): 6-digit OTP code
            user_name (str): User's name for personalization
            
        Returns:
            dict: Sending result with status and details
        """
        pause_status = self.is_whatsapp_paused_by_vgk()
        if pause_status['paused']:
            return {
                'success': False,
                'message': 'WhatsApp messaging is paused by VGK ID for development/testing',
                'paused_details': pause_status,
                'provider': 'WHATSAPP_PAUSED'
            }
        
        if not self.is_whatsapp_enabled():
            return {
                'success': False,
                'message': 'WhatsApp messaging is globally disabled',
                'provider': 'WHATSAPP_DISABLED'
            }
        
        if self.access_token and self.phone_number_id:
            return self._send_via_meta_api(mobile_number, otp_code, user_name)
        else:
            return self._send_mock_whatsapp(mobile_number, otp_code, "No Meta credentials")
    
    def _send_via_meta_api(self, mobile_number: str, otp_code: str, user_name: str = None) -> Dict[str, any]:
        """Send OTP via Meta Cloud API (Graph API)"""
        recipient = mobile_number.lstrip('+')
        
        greeting = f"Hello {user_name}!" if user_name else "Hello!"
        message_body = (
            f"🔐 *EV Reference Program*\n\n"
            f"{greeting}\n\n"
            f"Your verification code is: *{otp_code}*\n\n"
            f"✅ Valid for 10 minutes\n"
            f"⚠️ Do not share this code with anyone\n\n"
            f"Thank you for joining our EV community! 🚗⚡"
        )
        
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message_body}
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            wamid = data.get("messages", [{}])[0].get("id", "")
            
            self._log_message_to_database(
                message_sid=wamid,
                mobile_number=mobile_number,
                user_name=user_name,
                otp_code=None,
                message_body=None,
                from_number=self.business_phone_number,
                to_number=mobile_number,
                initial_status='sent',
                provider='META_WHATSAPP'
            )
            
            print(f"📧 MESSAGE LOGGED: {wamid} → {mobile_number}")
            
            return {
                'success': True,
                'message': f'WhatsApp OTP sent successfully to {mobile_number}',
                'message_sid': wamid,
                'provider': 'META_WHATSAPP',
                'delivery_status': 'sent'
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Meta WhatsApp sending failed: {error_msg}")
            return self._send_mock_whatsapp(mobile_number, otp_code, error_msg)
    
    def _log_message_to_database(self, message_sid: str, mobile_number: str, user_name: str,
                                 otp_code: str, message_body: str, from_number: str,
                                 to_number: str, initial_status: str, provider: str):
        """Log WhatsApp message to database for delivery tracking"""
        try:
            from app import MessageLog, db
            
            message_log = MessageLog(
                message_sid=message_sid,
                message_type='whatsapp_otp',
                mobile_number=mobile_number,
                user_name=user_name,
                otp_code=otp_code,
                message_body=message_body,
                from_number=from_number,
                to_number=to_number,
                provider=provider,
                initial_status=initial_status,
                current_status=initial_status,
                sent_at=datetime.utcnow()
            )
            
            db.session.add(message_log)
            db.session.commit()
            
            print(f"✅ MESSAGE LOGGED TO DB: {message_sid}")
            
        except Exception as e:
            print(f"❌ Failed to log message to database: {str(e)}")
    
    def _send_mock_whatsapp(self, mobile_number: str, otp_code: str, reason: str) -> Dict[str, any]:
        """Mock WhatsApp sending for development"""
        print(f"📱 MOCK WHATSAPP: Sending OTP {otp_code} to {mobile_number}")
        print(f"📱 WhatsApp Message:")
        print(f"🔐 *EV Reference Program*")
        print(f"Your verification code is: *{otp_code}*")
        print(f"✅ Valid for 10 minutes")
        print(f"⚠️ Do not share this code")
        print(f"📝 Mock Reason: {reason}")
        
        try:
            import uuid
            mock_sid = f"wamid.mock.{uuid.uuid4().hex[:32]}"
            self._log_message_to_database(
                message_sid=mock_sid,
                mobile_number=mobile_number,
                user_name='Mock User',
                otp_code=otp_code,
                message_body=f"Mock WhatsApp OTP: {otp_code}",
                from_number='mock_meta',
                to_number=mobile_number,
                initial_status='mock_sent',
                provider='MOCK_WHATSAPP'
            )
        except Exception as e:
            print(f"⚠️ Could not log mock message: {e}")
        
        return {
            'success': True,
            'message': f'MOCK: WhatsApp OTP sent to {mobile_number}',
            'provider': 'MOCK_WHATSAPP',
            'mock_reason': reason
        }


# VGK ID WhatsApp Control Functions
def pause_whatsapp_messaging(vgk_user_id: str, reason: str = "Development/Testing") -> Dict[str, any]:
    """
    Pause WhatsApp messaging (VGK ID only)
    
    Args:
        vgk_user_id (str): VGK ID user who is pausing
        reason (str): Reason for pausing
        
    Returns:
        dict: Pause result
    """
    try:
        from app import User, WhatsAppControl, db
        
        vgk_user = User.query.get(vgk_user_id)
        if not vgk_user or vgk_user.user_type != 'VGK ID':
            return {'success': False, 'error': 'Only VGK ID users can control WhatsApp messaging'}
        
        control = WhatsAppControl.query.first()
        if not control:
            control = WhatsAppControl()
            db.session.add(control)
        
        control.is_paused = True
        control.paused_by_user_id = vgk_user_id
        control.paused_at = datetime.utcnow()
        control.pause_reason = reason
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'WhatsApp messaging paused by {vgk_user.name}',
            'paused_by': vgk_user.name,
            'reason': reason
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Failed to pause WhatsApp: {str(e)}'}


def resume_whatsapp_messaging(vgk_user_id: str) -> Dict[str, any]:
    """
    Resume WhatsApp messaging (VGK ID only)
    
    Args:
        vgk_user_id (str): VGK ID user who is resuming
        
    Returns:
        dict: Resume result
    """
    try:
        from app import User, WhatsAppControl, db
        
        vgk_user = User.query.get(vgk_user_id)
        if not vgk_user or vgk_user.user_type != 'VGK ID':
            return {'success': False, 'error': 'Only VGK ID users can control WhatsApp messaging'}
        
        control = WhatsAppControl.query.first()
        if not control:
            return {'success': False, 'error': 'No WhatsApp control record found'}
        
        control.is_paused = False
        control.resumed_by_user_id = vgk_user_id
        control.resumed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'WhatsApp messaging resumed by {vgk_user.name}',
            'resumed_by': vgk_user.name
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Failed to resume WhatsApp: {str(e)}'}


def get_whatsapp_status() -> Dict[str, any]:
    """Get current WhatsApp messaging status"""
    try:
        from app import WhatsAppControl, User
        
        control = WhatsAppControl.query.first()
        if not control:
            return {
                'enabled': True,
                'paused': False,
                'status': 'Active - No controls set'
            }
        
        result = {
            'enabled': True,
            'paused': control.is_paused,
            'paused_at': control.paused_at,
            'resumed_at': control.resumed_at,
            'pause_reason': control.pause_reason
        }
        
        if control.paused_by_user_id:
            paused_by_user = User.query.get(control.paused_by_user_id)
            result['paused_by'] = paused_by_user.name if paused_by_user else 'Unknown'
        
        if control.resumed_by_user_id:
            resumed_by_user = User.query.get(control.resumed_by_user_id)
            result['resumed_by'] = resumed_by_user.name if resumed_by_user else 'Unknown'
        
        return result
        
    except Exception as e:
        return {'enabled': False, 'error': f'Status check failed: {str(e)}'}


# Global instance
whatsapp_messenger = WhatsAppMessaging()


def send_otp_whatsapp(mobile_number: str, otp_code: str, user_name: str = None) -> Dict[str, any]:
    """Convenience function to send WhatsApp OTP - matches OTP verification import"""
    return whatsapp_messenger.send_whatsapp_otp(mobile_number, otp_code, user_name)


# Additional utility functions for VGK ID controls
def pause_whatsapp_for_development(vgk_user_id: str, reason: str = "Development/Testing") -> Dict[str, any]:
    """Pause WhatsApp messaging (VGK ID only)"""
    return pause_whatsapp_messaging(vgk_user_id, reason)


def resume_whatsapp_for_development(vgk_user_id: str) -> Dict[str, any]:
    """Resume WhatsApp messaging (VGK ID only)"""
    return resume_whatsapp_messaging(vgk_user_id)


def get_whatsapp_messaging_status() -> Dict[str, any]:
    """Get current WhatsApp messaging status"""
    return get_whatsapp_status()
