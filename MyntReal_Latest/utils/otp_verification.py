"""
OTP Verification System for Mobile Number Validation
Handles OTP generation, sending, and verification
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, Tuple

class OTPVerification:
    """Handle OTP generation and verification for mobile numbers"""
    
    @staticmethod
    def generate_otp() -> str:
        """
        Generate a 6-digit OTP
        
        Returns:
            str: 6-digit OTP
        """
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def generate_otp_expiry(minutes: int = 10) -> datetime:
        """
        Generate OTP expiry time
        
        Args:
            minutes (int): Expiry time in minutes (default: 10)
            
        Returns:
            datetime: Expiry timestamp
        """
        return datetime.utcnow() + timedelta(minutes=minutes)
    
    @staticmethod
    def is_otp_valid(otp_code: str, stored_otp: str, expiry_time: datetime) -> Dict[str, any]:
        """
        Validate OTP code and expiry
        
        Args:
            otp_code (str): User entered OTP
            stored_otp (str): Stored OTP in database
            expiry_time (datetime): OTP expiry time
            
        Returns:
            dict: Validation result
        """
        current_time = datetime.utcnow()
        
        if not otp_code or not stored_otp:
            return {'valid': False, 'error': 'OTP is required'}
        
        if otp_code.strip() != stored_otp.strip():
            return {'valid': False, 'error': 'Invalid OTP code'}
        
        if current_time > expiry_time:
            return {'valid': False, 'error': 'OTP has expired. Please request a new one'}
        
        return {'valid': True, 'error': None}
    
    @staticmethod
    def send_otp_whatsapp(mobile_number: str, otp_code: str, user_name: str = None) -> Dict[str, any]:
        """
        Send OTP via WhatsApp with VGK ID pause/resume controls
        
        Args:
            mobile_number (str): Mobile number to send OTP
            otp_code (str): OTP code to send
            user_name (str): User's name for personalization
            
        Returns:
            dict: WhatsApp sending result
        """
        try:
            from utils.whatsapp_messaging import send_otp_whatsapp
            return send_otp_whatsapp(mobile_number, otp_code, user_name)
        except ImportError:
            # Fallback to mock implementation if WhatsApp module not available
            return OTPVerification._send_mock_whatsapp_otp(mobile_number, otp_code, user_name)
    
    @staticmethod
    def _send_mock_whatsapp_otp(mobile_number: str, otp_code: str, user_name: str = None) -> Dict[str, any]:
        """
        Mock WhatsApp OTP sending for development (fallback)
        """
        greeting = f"Hello {user_name}!" if user_name else "Hello!"
        print(f"📱 MOCK WHATSAPP OTP: {otp_code} to {mobile_number}")
        print(f"🔐 *EV Reference Program*")
        print(f"{greeting}")
        print(f"Your verification code is: *{otp_code}*")
        print(f"✅ Valid for 10 minutes")
        print(f"⚠️ Do not share this code with anyone")
        
        return {
            'success': True,
            'message': f'MOCK: WhatsApp OTP sent to {mobile_number}',
            'provider': 'MOCK_WHATSAPP'
        }
    
    @staticmethod
    def send_otp_sms(mobile_number: str, otp_code: str) -> Dict[str, any]:
        """
        Send OTP via SMS (backup method for WhatsApp)
        
        Args:
            mobile_number (str): Mobile number to send OTP
            otp_code (str): OTP code to send
            
        Returns:
            dict: SMS sending result
        """
        # MOCK IMPLEMENTATION - In production, integrate with SMS service
        # like Twilio, AWS SNS, or Indian SMS providers
        
        print(f"📱 MOCK SMS: Sending OTP {otp_code} to {mobile_number}")
        print(f"📱 SMS Content: Your EV Reference Program verification code is: {otp_code}. Valid for 10 minutes. Do not share this code.")
        
        # For development/testing purposes, always return success
        return {
            'success': True,
            'message': f'OTP sent successfully to {mobile_number}',
            'provider': 'MOCK_SMS_SERVICE'
        }
    
    @staticmethod
    def update_user_mobile_verification(user_id: str, otp_code: str) -> Dict[str, any]:
        """
        Update user's mobile verification fields in database
        
        Args:
            user_id (str): User's BEV ID
            otp_code (str): Generated OTP code
            
        Returns:
            dict: Update result
        """
        try:
            from app import User, db
            
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Update OTP fields
            user.mobile_verification_code = otp_code
            user.mobile_verification_expires = OTPVerification.generate_otp_expiry()
            user.mobile_verified = False  # Reset verification status
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Mobile verification fields updated successfully',
                'expires_at': user.mobile_verification_expires
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
    
    @staticmethod
    def verify_and_confirm_mobile(user_id: str, entered_otp: str) -> Dict[str, any]:
        """
        Verify OTP and mark mobile as verified
        
        Args:
            user_id (str): User's BEV ID
            entered_otp (str): OTP entered by user
            
        Returns:
            dict: Verification result
        """
        try:
            from app import User, db
            
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            if not user.mobile_verification_code or not user.mobile_verification_expires:
                return {'success': False, 'error': 'No OTP found. Please request a new verification code'}
            
            # Validate OTP
            validation_result = OTPVerification.is_otp_valid(
                entered_otp, 
                user.mobile_verification_code, 
                user.mobile_verification_expires
            )
            
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Mark mobile as verified and clear OTP fields
            user.mobile_verified = True
            user.mobile_verification_code = None
            user.mobile_verification_expires = None
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Mobile number verified successfully',
                'mobile_verified': True
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}

def send_mobile_verification_otp(user_id: str) -> Dict[str, any]:
    """
    Complete mobile verification workflow: generate OTP, update database, send SMS
    
    Args:
        user_id (str): User's BEV ID
        
    Returns:
        dict: Complete workflow result
    """
    try:
        from app import User
        from utils.data_encryption import decrypt_sensitive_data
        
        # Get user and mobile number
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Get decrypted mobile number
        if user.mobile_number_encrypted:
            mobile_number = decrypt_sensitive_data(user.mobile_number_encrypted)
        else:
            mobile_number = user.phone_number  # Fallback to legacy field
        
        if not mobile_number:
            return {'success': False, 'error': 'No mobile number found for this user'}
        
        # Generate OTP
        otp_code = OTPVerification.generate_otp()
        
        # Update database
        db_result = OTPVerification.update_user_mobile_verification(user_id, otp_code)
        if not db_result['success']:
            return db_result
        
        # Send WhatsApp OTP (primary method)
        whatsapp_result = OTPVerification.send_otp_whatsapp(mobile_number, otp_code, user.name)
        
        return {
            'success': True,
            'message': f'Verification code sent to {mobile_number}',
            'mobile_masked': f"{mobile_number[:3]}****{mobile_number[-4:]}",
            'expires_at': db_result['expires_at'],
            'whatsapp_status': whatsapp_result
        }
        
    except Exception as e:
        return {'success': False, 'error': f'OTP workflow error: {str(e)}'}

def verify_mobile_otp(user_id: str, otp_code: str) -> Dict[str, any]:
    """
    Verify mobile OTP for user
    
    Args:
        user_id (str): User's BEV ID
        otp_code (str): OTP entered by user
        
    Returns:
        dict: Verification result
    """
    return OTPVerification.verify_and_confirm_mobile(user_id, otp_code)