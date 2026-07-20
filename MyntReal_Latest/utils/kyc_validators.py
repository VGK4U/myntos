"""
KYC Validation Utilities
Handles validation of PAN, Aadhaar, and Mobile numbers
"""

import re
from typing import Dict, Tuple

class KYCValidators:
    """Validation functions for KYC data"""
    
    # Validation patterns
    PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    AADHAAR_PATTERN = re.compile(r'^\d{12}$')
    MOBILE_PATTERN = re.compile(r'^(\+91[-\s]?)?[6-9]\d{9}$')
    
    @classmethod
    def validate_pan_format(cls, pan: str) -> Dict[str, any]:
        """
        Validate PAN number format (ABCDE1234F)
        
        Args:
            pan (str): PAN number to validate
            
        Returns:
            dict: Validation result with 'valid' boolean and 'error' message
        """
        if not pan:
            return {'valid': False, 'error': 'PAN number is required'}
        
        # Remove spaces and convert to uppercase
        pan_clean = pan.replace(' ', '').upper()
        
        if len(pan_clean) != 10:
            return {'valid': False, 'error': 'PAN number must be exactly 10 characters'}
        
        if not cls.PAN_PATTERN.match(pan_clean):
            return {'valid': False, 'error': 'Invalid PAN format. Expected: ABCDE1234F (5 letters + 4 digits + 1 letter)'}
        
        return {'valid': True, 'error': None, 'cleaned_value': pan_clean}
    
    @classmethod
    def validate_aadhaar_format(cls, aadhaar: str) -> Dict[str, any]:
        """
        Validate Aadhaar number format (12 digits)
        
        Args:
            aadhaar (str): Aadhaar number to validate
            
        Returns:
            dict: Validation result with 'valid' boolean and 'error' message
        """
        if not aadhaar:
            return {'valid': False, 'error': 'Aadhaar number is required'}
        
        # Remove spaces, hyphens, and other formatting
        aadhaar_clean = re.sub(r'[^\d]', '', aadhaar)
        
        if len(aadhaar_clean) != 12:
            return {'valid': False, 'error': 'Aadhaar number must be exactly 12 digits'}
        
        if not cls.AADHAAR_PATTERN.match(aadhaar_clean):
            return {'valid': False, 'error': 'Invalid Aadhaar format. Must contain only digits'}
        
        # Basic checksum validation (Verhoeff algorithm - simplified)
        if not cls._validate_aadhaar_checksum(aadhaar_clean):
            return {'valid': False, 'error': 'Invalid Aadhaar number checksum'}
        
        return {'valid': True, 'error': None, 'cleaned_value': aadhaar_clean}
    
    @classmethod
    def validate_mobile_format(cls, mobile: str) -> Dict[str, any]:
        """
        Validate Indian mobile number format
        
        Args:
            mobile (str): Mobile number to validate
            
        Returns:
            dict: Validation result with 'valid' boolean and 'error' message
        """
        if not mobile:
            return {'valid': False, 'error': 'Mobile number is required'}
        
        # Remove spaces and special characters
        mobile_clean = re.sub(r'[^\d+]', '', mobile)
        
        if not cls.MOBILE_PATTERN.match(mobile_clean):
            return {'valid': False, 'error': 'Invalid mobile format. Expected Indian mobile: +91XXXXXXXXXX or 10-digit number starting with 6-9'}
        
        # Normalize to +91 format
        if mobile_clean.startswith('+91'):
            normalized = mobile_clean
        elif mobile_clean.startswith('91') and len(mobile_clean) == 12:
            normalized = '+' + mobile_clean
        elif len(mobile_clean) == 10:
            normalized = '+91' + mobile_clean
        else:
            return {'valid': False, 'error': 'Invalid mobile number length'}
        
        return {'valid': True, 'error': None, 'cleaned_value': normalized}
    
    @classmethod
    def _validate_aadhaar_checksum(cls, aadhaar: str) -> bool:
        """
        Simplified Aadhaar checksum validation using Verhoeff algorithm
        
        Args:
            aadhaar (str): 12-digit Aadhaar number
            
        Returns:
            bool: True if checksum is valid
        """
        # Verhoeff algorithm multiplication table
        multiplication_table = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        ]
        
        # Permutation table
        permutation_table = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
        ]
        
        check = 0
        for i, digit in enumerate(reversed(aadhaar)):
            check = multiplication_table[check][permutation_table[i % 8][int(digit)]]
        
        return check == 0

def validate_unique_constraint(value: str, field_type: str, user_id: str = None) -> Dict[str, any]:
    """
    Check if value violates unique constraint using deterministic hashing
    
    Args:
        value (str): Value to check (PAN, Aadhaar, Mobile)
        field_type (str): Field type ('pan', 'aadhaar', 'mobile')
        user_id (str): Current user ID (to exclude from uniqueness check during updates)
        
    Returns:
        dict: Validation result with 'unique' boolean and 'error' message
    """
    from app import User, db
    from utils.secure_hashing import create_unique_hash
    
    if not value:
        return {'unique': True, 'error': None}
    
    # Create deterministic hash for uniqueness checking
    value_hash = create_unique_hash(value, field_type)
    
    # Map field types to database columns and display names
    field_mapping = {
        'pan': {'column': 'pan_hash', 'display': 'PAN number'},
        'aadhaar': {'column': 'aadhaar_hash', 'display': 'Aadhaar number'},
        'mobile': {'column': 'mobile_hash', 'display': 'Mobile number'}
    }
    
    if field_type not in field_mapping:
        return {'unique': False, 'error': 'Invalid field type for validation'}
    
    column_name = field_mapping[field_type]['column']
    display_name = field_mapping[field_type]['display']
    
    # Build query using hash column
    query = User.query.filter(getattr(User, column_name) == value_hash)
    
    # Exclude current user if updating
    if user_id:
        query = query.filter(User.id != user_id)
    
    existing_user = query.first()
    
    if existing_user:
        # Provide generic error message without exposing User ID (security improvement)
        return {
            'unique': False, 
            'error': f'This {display_name} is already registered with another account. Please use a different number or contact support if this is your number.'
        }
    
    return {'unique': True, 'error': None}

def comprehensive_kyc_validation(pan: str, aadhaar: str, mobile: str, user_id: str = None) -> Dict[str, any]:
    """
    Comprehensive validation for all KYC fields
    
    Args:
        pan (str): PAN number
        aadhaar (str): Aadhaar number  
        mobile (str): Mobile number
        user_id (str): Current user ID (for updates)
        
    Returns:
        dict: Complete validation result
    """
    results = {
        'valid': True,
        'errors': {},
        'cleaned_values': {}
    }
    
    # Validate PAN
    if pan:
        pan_result = KYCValidators.validate_pan_format(pan)
        if not pan_result['valid']:
            results['valid'] = False
            results['errors']['pan'] = pan_result['error']
        else:
            # Check uniqueness using corrected field type
            unique_result = validate_unique_constraint(pan_result['cleaned_value'], 'pan', user_id)
            if not unique_result['unique']:
                results['valid'] = False
                results['errors']['pan'] = unique_result['error']
            else:
                results['cleaned_values']['pan'] = pan_result['cleaned_value']
    
    # Validate Aadhaar
    if aadhaar:
        aadhaar_result = KYCValidators.validate_aadhaar_format(aadhaar)
        if not aadhaar_result['valid']:
            results['valid'] = False
            results['errors']['aadhaar'] = aadhaar_result['error']
        else:
            # Check uniqueness using corrected field type
            unique_result = validate_unique_constraint(aadhaar_result['cleaned_value'], 'aadhaar', user_id)
            if not unique_result['unique']:
                results['valid'] = False
                results['errors']['aadhaar'] = unique_result['error']
            else:
                results['cleaned_values']['aadhaar'] = aadhaar_result['cleaned_value']
    
    # Validate Mobile
    if mobile:
        mobile_result = KYCValidators.validate_mobile_format(mobile)
        if not mobile_result['valid']:
            results['valid'] = False
            results['errors']['mobile'] = mobile_result['error']
        else:
            # Check uniqueness using corrected field type
            unique_result = validate_unique_constraint(mobile_result['cleaned_value'], 'mobile', user_id)
            if not unique_result['unique']:
                results['valid'] = False
                results['errors']['mobile'] = unique_result['error']
            else:
                results['cleaned_values']['mobile'] = mobile_result['cleaned_value']
    
    return results