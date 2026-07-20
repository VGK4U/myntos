"""
Secure Hashing Utilities for Uniqueness Validation
Uses deterministic HMAC-SHA256 for uniqueness checking while maintaining encryption for privacy
"""

import hashlib
import hmac
import os
from typing import Optional

class SecureHasher:
    """Handle deterministic hashing for uniqueness validation"""
    
    def __init__(self):
        self._hmac_key = self._get_hmac_key()
    
    def _get_hmac_key(self) -> bytes:
        """Get HMAC key for deterministic hashing"""
        # Use environment variable or generate secure key for development
        hmac_key = os.environ.get('HMAC_SECRET_KEY', 'EV-Reference-HMAC-Key-2025-Unique-Validation')
        return hmac_key.encode('utf-8')
    
    def create_deterministic_hash(self, value: str, field_type: str) -> str:
        """
        Create deterministic hash for uniqueness validation
        
        Args:
            value (str): Value to hash (PAN, Aadhaar, Mobile)
            field_type (str): Type of field ('pan', 'aadhaar', 'mobile')
            
        Returns:
            str: Deterministic HMAC-SHA256 hash (hex encoded)
        """
        if not value:
            return ""
        
        # Add field type to prevent collision between different field types
        message = f"{field_type}:{value}".encode('utf-8')
        
        # Create deterministic HMAC-SHA256 hash
        hash_digest = hmac.new(self._hmac_key, message, hashlib.sha256).hexdigest()
        
        return hash_digest
    
    def create_pan_hash(self, pan: str) -> str:
        """Create deterministic hash for PAN number"""
        return self.create_deterministic_hash(pan, 'pan')
    
    def create_aadhaar_hash(self, aadhaar: str) -> str:
        """Create deterministic hash for Aadhaar number"""  
        return self.create_deterministic_hash(aadhaar, 'aadhaar')
    
    def create_mobile_hash(self, mobile: str) -> str:
        """Create deterministic hash for Mobile number"""
        return self.create_deterministic_hash(mobile, 'mobile')
    
    def hash_otp_code(self, otp: str, user_id: str) -> str:
        """
        Create hash for OTP storage (security improvement)
        
        Args:
            otp (str): OTP code
            user_id (str): User's BEV ID (for additional entropy)
            
        Returns:
            str: Hashed OTP
        """
        if not otp:
            return ""
        
        message = f"otp:{user_id}:{otp}".encode('utf-8')
        return hmac.new(self._hmac_key, message, hashlib.sha256).hexdigest()
    
    def verify_otp_hash(self, entered_otp: str, user_id: str, stored_hash: str) -> bool:
        """
        Verify OTP against stored hash
        
        Args:
            entered_otp (str): OTP entered by user
            user_id (str): User's BEV ID
            stored_hash (str): Stored OTP hash
            
        Returns:
            bool: True if OTP matches
        """
        if not all([entered_otp, user_id, stored_hash]):
            return False
        
        calculated_hash = self.hash_otp_code(entered_otp, user_id)
        return hmac.compare_digest(calculated_hash, stored_hash)

# Global instance
secure_hasher = SecureHasher()

def create_unique_hash(value: str, field_type: str) -> str:
    """Convenience function to create deterministic hash for uniqueness"""
    return secure_hasher.create_deterministic_hash(value, field_type)

def create_pan_hash(pan: str) -> str:
    """Create deterministic hash for PAN uniqueness validation"""
    return secure_hasher.create_pan_hash(pan)

def create_aadhaar_hash(aadhaar: str) -> str:
    """Create deterministic hash for Aadhaar uniqueness validation"""
    return secure_hasher.create_aadhaar_hash(aadhaar)

def create_mobile_hash(mobile: str) -> str:
    """Create deterministic hash for Mobile uniqueness validation"""
    return secure_hasher.create_mobile_hash(mobile)

def hash_otp_code(otp: str, user_id: str) -> str:
    """Create secure hash for OTP storage"""
    return secure_hasher.hash_otp_code(otp, user_id)

def verify_otp_hash(entered_otp: str, user_id: str, stored_hash: str) -> bool:
    """Verify OTP against stored hash"""
    return secure_hasher.verify_otp_hash(entered_otp, user_id, stored_hash)