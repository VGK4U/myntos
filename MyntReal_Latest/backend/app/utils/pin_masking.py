"""
PIN Masking Utility
Masks PIN codes for security - shows only first 4 and last 4 digits
"""

def mask_pin(pin_code: str) -> str:
    """
    Mask PIN code to show only first 4 and last 4 digits
    
    Args:
        pin_code: Full PIN code (e.g., "607476784122314")
        
    Returns:
        Masked PIN (e.g., "6074*******2314")
    """
    if not pin_code:
        return "****"
    
    pin_str = str(pin_code)
    
    if len(pin_str) <= 8:
        # If PIN is 8 digits or less, show first 4 and mask rest
        return pin_str[:4] + "*" * (len(pin_str) - 4)
    
    # For PINs longer than 8 digits, show first 4 and last 4
    first_four = pin_str[:4]
    last_four = pin_str[-4:]
    middle_length = len(pin_str) - 8
    
    return f"{first_four}{'*' * middle_length}{last_four}"


def get_full_pin(pin_code: str, user_role: str = None) -> str:
    """
    Get full PIN code - only for authorized roles
    
    Args:
        pin_code: Full PIN code
        user_role: User's role (Admin, Super Admin, Finance Admin can see full PIN)
        
    Returns:
        Full PIN if authorized, masked PIN otherwise
    """
    authorized_roles = ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']
    
    if user_role in authorized_roles:
        return str(pin_code)
    
    return mask_pin(pin_code)
