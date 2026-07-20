"""
Centralized System Constants & Configuration
Single source of truth for all common values used throughout the system
"""

from decimal import Decimal

# ========== FINANCIAL DEDUCTIONS ==========
# Standard deductions applied to all income types

ADMIN_DEDUCTION_RATE = Decimal('0.08')  # 8% Admin deduction
TDS_DEDUCTION_RATE = Decimal('0.02')     # 2% TDS deduction
TOTAL_DEDUCTION_RATE = ADMIN_DEDUCTION_RATE + TDS_DEDUCTION_RATE  # 10% total
NET_PAYOUT_RATE = Decimal('1') - TOTAL_DEDUCTION_RATE             # 90% net to member

# For display/API responses
ADMIN_DEDUCTION_PERCENT = 8.0
TDS_DEDUCTION_PERCENT = 2.0
TOTAL_DEDUCTION_PERCENT = 10.0

# ========== GURU DAKSHINA ==========
# Percentage paid to referrer from user's income

GURU_DAKSHINA_RATE = Decimal('0.02')  # 2% paid to referrer
GURU_DAKSHINA_PERCENT = 2.0

# ========== DAILY INCOME CEILING ==========
# Maximum daily income limit per user

DAILY_INCOME_CEILING = Decimal('50000.00')  # ₹50,000 daily limit
DAILY_INCOME_CEILING_DISPLAY = 50000.0

# ========== PACKAGE POINTS ==========
# Income multipliers based on package tier

PACKAGE_POINTS = {
    'Star': Decimal('0.25'),      # 25% income
    'Loyal': Decimal('0.50'),     # 50% income
    'Diamond': Decimal('0.75'),   # 75% income
    'Platinum': Decimal('1.00')   # 100% income
}

# ========== WALLET SPLIT RATIOS ==========
# How income is split between earning and withdrawable wallets based on package

WALLET_SPLIT = {
    'Platinum': {
        'withdrawable': Decimal('1.00'),  # 100% withdrawable
        'earning': Decimal('0.00')         # 0% earning
    },
    'Diamond': {
        'withdrawable': Decimal('0.50'),  # 50% withdrawable
        'earning': Decimal('0.50')         # 50% earning
    },
    'default': {  # Star, Loyal, and others
        'withdrawable': Decimal('0.50'),  # 50% withdrawable
        'earning': Decimal('0.50')         # 50% earning
    }
}

# ========== REFERRAL INCOME RATES ==========
# Percentage of package value paid as referral income

DIRECT_REFERRAL_RATE = {
    'Star': Decimal('500.00'),      # ₹500 per Star referral
    'Loyal': Decimal('1000.00'),    # ₹1,000 per Loyal referral
    'Diamond': Decimal('1500.00'),  # ₹1,500 per Diamond referral
    'Platinum': Decimal('2000.00')  # ₹2,000 per Platinum referral
}

MATCHING_REFERRAL_RATE = {
    'Star': Decimal('250.00'),      # ₹250 per Star matching pair
    'Loyal': Decimal('500.00'),     # ₹500 per Loyal matching pair
    'Diamond': Decimal('750.00'),   # ₹750 per Diamond matching pair
    'Platinum': Decimal('1000.00')  # ₹1,000 per Platinum matching pair
}

# ========== VED INCOME RATES ==========
# Income paid to Ved members when downline activates

VED_INCOME_RATES = {
    'Platinum': Decimal('1000.00'),  # ₹1,000 for Platinum activation
    'Loyal': Decimal('500.00'),      # ₹500 for Loyal/Diamond activation
    'default': Decimal('0.00')       # No Ved income for Star
}

# ========== MINIMUM WITHDRAWAL ==========
# Minimum balance required to request withdrawal

MINIMUM_WITHDRAWAL_AMOUNT = Decimal('1000.00')  # ₹1,000 minimum
MINIMUM_WITHDRAWAL_DISPLAY = 1000.0

# ========== AUTO-WITHDRAWAL ELIGIBILITY ==========
# Criteria for automatic withdrawal generation

AUTO_WITHDRAWAL_MIN_BALANCE = Decimal('5000.00')  # ₹5,000 minimum balance
AUTO_WITHDRAWAL_REQUIRES_KYC = False  # TEMPORARY: KYC check disabled (November 2, 2025)
AUTO_WITHDRAWAL_REQUIRES_BANK = True  # Must have verified bank details

# ========== MNR ID CONFIGURATION ==========
# User ID format and generation

MNR_ID_PREFIX = 'MNR'
MNR_ID_LENGTH = 12  # Total length including prefix (MNR + 9 digits)
MNR_ID_RANDOM_LENGTH = 9  # Number of random digits

# ========== PACKAGE PRICES ==========
# Official package prices (for reference)

PACKAGE_PRICES = {
    'Star': Decimal('2000.00'),
    'Loyal': Decimal('4000.00'),
    'Diamond': Decimal('6000.00'),
    'Platinum': Decimal('8000.00')
}

# ========== SESSION CONFIGURATION ==========
# Session timeout and security settings

SESSION_TIMEOUT_HOURS = 24  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS

# ========== SECONDARY PASSWORD (2FA) ==========
# RVZ/Super Admin secondary verification

SECONDARY_PASSWORD_TIMEOUT_MINUTES = 15  # 15 minutes validity
SECONDARY_PASSWORD_MAX_ATTEMPTS = 3  # Max failed attempts before lockout

# ========== PAGINATION DEFAULTS ==========
# Default values for paginated API responses

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
DEFAULT_SKIP = 0

# ========== FILE UPLOAD LIMITS ==========
# Maximum file sizes for uploads

MAX_BILL_UPLOAD_SIZE_MB = 5  # 5 MB for bills/receipts
MAX_KYC_DOCUMENT_SIZE_MB = 2  # 2 MB for KYC documents
MAX_PROFILE_IMAGE_SIZE_MB = 1  # 1 MB for profile pictures

ALLOWED_BILL_FORMATS = ['pdf', 'jpg', 'jpeg', 'png']
ALLOWED_KYC_FORMATS = ['pdf', 'jpg', 'jpeg', 'png']
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png']

# ========== AWARD PROCESSING ==========
# Settings for award approval workflow

AWARD_BULK_PROCESS_LIMIT = 100  # Max awards in single bulk operation
AWARD_COST_VARIANCE_THRESHOLD = Decimal('0.20')  # 20% variance warning threshold

# ========== HELPER FUNCTIONS ==========

def calculate_deductions(gross_amount: Decimal) -> dict:
    """
    Calculate standard deductions from gross amount
    Returns: dict with admin_deduction, tds_deduction, net_amount
    """
    admin_deduction = gross_amount * ADMIN_DEDUCTION_RATE
    tds_deduction = gross_amount * TDS_DEDUCTION_RATE
    net_amount = gross_amount - admin_deduction - tds_deduction
    
    return {
        'gross_amount': gross_amount,
        'admin_deduction': admin_deduction,
        'tds_deduction': tds_deduction,
        'total_deduction': admin_deduction + tds_deduction,
        'net_amount': net_amount
    }

def get_package_wallet_split(package_name: str) -> dict:
    """
    Get wallet split ratios for a package
    Returns: dict with withdrawable and earning percentages
    """
    if package_name == 'Platinum':
        return WALLET_SPLIT['Platinum']
    else:
        return WALLET_SPLIT['default']

def get_ved_income_amount(package_points: Decimal) -> Decimal:
    """
    Get Ved income amount based on package points
    """
    if package_points == Decimal('1.0'):  # Platinum
        return VED_INCOME_RATES['Platinum']
    elif package_points in [Decimal('0.5'), Decimal('0.75')]:  # Loyal/Diamond
        return VED_INCOME_RATES['Loyal']
    else:
        return VED_INCOME_RATES['default']

def format_deduction_display() -> dict:
    """
    Get deduction percentages for display/API responses
    """
    return {
        'admin': ADMIN_DEDUCTION_PERCENT,
        'tds': TDS_DEDUCTION_PERCENT,
        'total': TOTAL_DEDUCTION_PERCENT
    }
