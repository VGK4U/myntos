#!/usr/bin/env python3
"""
Safe String Utilities for VGK Migration System
Comprehensive solution to prevent 'NoneType' object has no attribute 'strip' errors

This module provides safe string handling utilities to prevent the recurring
"'NoneType' object has no attribute 'strip'" errors that were encountered
throughout the VGK migration system.

Author: VGK VM System
Date: September 27, 2025
"""

def safe_strip(value, default=''):
    """
    Safely strip whitespace from a value that might be None.
    
    Args:
        value: Any value that might be None, string, or other type
        default: Default value to return if input is None or empty (default: '')
        
    Returns:
        str: Stripped string or default value
        
    Examples:
        safe_strip(None) -> ''
        safe_strip('  hello  ') -> 'hello'
        safe_strip('') -> ''
        safe_strip(123) -> '123'
    """
    if value is None:
        return default
    return str(value).strip()

def safe_strip_upper(value, default=''):
    """
    Safely strip and convert to uppercase.
    
    Args:
        value: Any value that might be None
        default: Default value to return if input is None or empty
        
    Returns:
        str: Stripped and uppercased string or default value
    """
    return safe_strip(value, default).upper()

def safe_strip_lower(value, default=''):
    """
    Safely strip and convert to lowercase.
    
    Args:
        value: Any value that might be None
        default: Default value to return if input is None or empty
        
    Returns:
        str: Stripped and lowercased string or default value
    """
    return safe_strip(value, default).lower()

def safe_get_strip(dictionary, key, default=''):
    """
    Safely get a value from dictionary and strip it.
    
    Args:
        dictionary: Dictionary to get value from
        key: Key to look up
        default: Default value if key missing or value is None
        
    Returns:
        str: Safely stripped value
        
    Examples:
        safe_get_strip({'name': '  John  '}, 'name') -> 'John'
        safe_get_strip({'name': None}, 'name') -> ''
        safe_get_strip({}, 'name') -> ''
    """
    value = dictionary.get(key, default)
    return safe_strip(value, default)

def safe_get_strip_upper(dictionary, key, default=''):
    """
    Safely get a value from dictionary, strip it, and convert to uppercase.
    """
    return safe_get_strip(dictionary, key, default).upper()

def safe_get_strip_lower(dictionary, key, default=''):
    """
    Safely get a value from dictionary, strip it, and convert to lowercase.
    """
    return safe_get_strip(dictionary, key, default).lower()

# Legacy pattern replacement helpers
def legacy_safe_pattern(value):
    """
    Replace the legacy (value or '').strip() pattern with safe_strip().
    This function serves as a reference for the pattern we're replacing.
    
    OLD PATTERN: (user_data.get('EmailId', '') or '').strip()
    NEW PATTERN: safe_get_strip(user_data, 'EmailId')
    """
    return safe_strip(value)

class VGKSafeStringProcessor:
    """
    Centralized safe string processing for VGK migration operations.
    """
    
    @staticmethod
    def process_user_data_safely(user_data):
        """
        Process user data dictionary with safe string handling.
        
        Args:
            user_data: Dictionary containing user data from Excel/CSV
            
        Returns:
            dict: Processed user data with safe string handling
        """
        if not isinstance(user_data, dict):
            return {}
        
        # Process all string fields safely
        processed = {}
        for key, value in user_data.items():
            processed[key] = safe_strip(value)
        
        return processed
    
    @staticmethod
    def safe_validation_checks(user_data):
        """
        Perform validation checks with safe string handling.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            dict: Validation results
        """
        errors = []
        warnings = []
        
        # Safe validation examples
        member_id = safe_get_strip(user_data, 'MemberId')
        if not member_id:
            errors.append('MemberId is required')
        elif not member_id.startswith('BEV'):
            errors.append('MemberId must start with BEV')
            
        name = safe_get_strip(user_data, 'Name')
        if not name:
            errors.append('Name is required')
        elif len(name) > 100:
            errors.append('Name exceeds 100 character limit')
            
        phone_no = safe_get_strip(user_data, 'PhoneNo')
        if not phone_no:
            errors.append('PhoneNo is required')
        elif not phone_no.isdigit() or len(phone_no) != 10:
            errors.append('PhoneNo must be exactly 10 digits')
            
        sponsor_id = safe_get_strip(user_data, 'SponsorId')
        if not sponsor_id:
            errors.append('SponsorId is required')
        elif not sponsor_id.startswith('BEV'):
            errors.append('SponsorId must start with BEV')
            
        position = safe_get_strip_upper(user_data, 'Position')
        if not position:
            errors.append('Position is required')
        elif position not in ['LEFT', 'RIGHT']:
            errors.append('Position must be LEFT or RIGHT')
        
        # Optional field validations
        email = safe_get_strip(user_data, 'EmailId')
        if email:
            import re
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(email):
                warnings.append('Invalid email format')
            elif len(email) > 255:
                warnings.append('Email exceeds 255 character limit')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'sanitized_data': user_data
        }