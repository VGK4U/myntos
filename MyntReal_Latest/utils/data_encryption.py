"""
Data Encryption Utility for Sensitive Information
Handles encryption/decryption of PAN, Aadhaar, and other sensitive data
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class DataEncryption:
    """Handle encryption/decryption of sensitive user data"""
    
    def __init__(self):
        self._key = None
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with environment-based key"""
        # Use environment variable or generate a key for development
        password = os.environ.get('ENCRYPTION_KEY', 'EV-Reference-Program-2025-Secret-Key').encode()
        salt = os.environ.get('ENCRYPTION_SALT', 'ev-ref-salt-2025').encode()
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self._fernet = Fernet(key)
    
    def encrypt_data(self, plain_text):
        """
        Encrypt sensitive data
        
        Args:
            plain_text (str): Data to encrypt
            
        Returns:
            str: Encrypted data (base64 encoded)
        """
        if not plain_text:
            return None
        
        try:
            encrypted_data = self._fernet.encrypt(plain_text.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            print(f"Encryption error: {str(e)}")
            return None
    
    def decrypt_data(self, encrypted_text):
        """
        Decrypt sensitive data
        
        Args:
            encrypted_text (str): Encrypted data (base64 encoded)
            
        Returns:
            str: Decrypted plain text
        """
        if not encrypted_text:
            return None
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            return None

# Global instance
data_encryptor = DataEncryption()

def encrypt_sensitive_data(data):
    """Convenience function to encrypt sensitive data"""
    return data_encryptor.encrypt_data(data)

def decrypt_sensitive_data(data):
    """Convenience function to decrypt sensitive data"""
    return data_encryptor.decrypt_data(data)

def mask_pan_number(pan):
    """
    Mask PAN number for display (ABCXX1234X format)
    
    Args:
        pan (str): PAN number
        
    Returns:
        str: Masked PAN number
    """
    if not pan or len(pan) != 10:
        return "XXXXX1234X"
    
    return f"{pan[:3]}XX{pan[5:9]}X"

def mask_aadhaar_number(aadhaar):
    """
    Mask Aadhaar number for display (XXXX-XXXX-1234 format)
    
    Args:
        aadhaar (str): Aadhaar number (12 digits)
        
    Returns:
        str: Masked Aadhaar number
    """
    if not aadhaar:
        return "XXXX-XXXX-1234"
    
    # Remove any existing formatting
    aadhaar_digits = ''.join(filter(str.isdigit, aadhaar))
    
    if len(aadhaar_digits) != 12:
        return "XXXX-XXXX-1234"
    
    return f"XXXX-XXXX-{aadhaar_digits[-4:]}"

def mask_mobile_number(mobile):
    """
    Mask mobile number for display (+91-XXXXX-X1234 format)
    
    Args:
        mobile (str): Mobile number
        
    Returns:
        str: Masked mobile number
    """
    if not mobile:
        return "+91-XXXXX-X1234"
    
    # Remove any existing formatting
    mobile_digits = ''.join(filter(str.isdigit, mobile))
    
    if len(mobile_digits) >= 10:
        last_4 = mobile_digits[-4:]
        return f"+91-XXXXX-X{last_4}"
    
    return "+91-XXXXX-X1234"