"""
Constants for MNR Electric Vehicle Reference System
NEW 4-Package System with Points-Based Structure
"""

from decimal import Decimal
from typing import Dict, Any
from datetime import date

# Import award status constants (DC Protocol)
from .award_statuses import AwardStatus, normalize_status, is_valid_dc_status, LEGACY_TO_DC_PROTOCOL_MAPPING

# PRODUCTION START DATE (Income Reset Feature)
# All income calculations from this date onwards are included
# October 1, 2025 - Production reset cutoff for clean financial data
PRODUCTION_START_DATE = date(2025, 10, 1)  # All transactions from Oct 1, 2025 onwards count

PACKAGE_SYSTEM = {
    'PLATINUM': {
        'price': 15000,
        'points': 1.0,
        'referrer_bonus': 3000,
        'referrer_bonus_max_count': 1,
        'activation': True,
        'wallet_required': False,
        'earnings_split': {
            'withdrawable': 100,
            'upgraded_wallet': 0
        },
        'ved_income': 1000,
        'matching_income_rate': 100,
        'display_name': 'Platinum Coupon',
        'emoji': '🏆'
    },
    'DIAMOND': {
        'price': 7500,
        'points': 0.5,
        'referrer_bonus': 1500,
        'referrer_bonus_max_count': 2,
        'activation': True,
        'wallet_required': True,
        'earnings_split': {
            'withdrawable': 50,
            'upgraded_wallet': 50
        },
        'ved_income': 500,
        'matching_income_rate': 50,
        'display_name': 'Diamond Coupon',
        'emoji': '💎'
    },
    'BLUE': {
        'price': 1000,
        'points': 0,
        'referrer_bonus': 0,
        'referrer_bonus_max_count': 2,
        'activation': True,
        'wallet_required': True,
        'earnings_split': {
            'withdrawable': 50,
            'upgraded_wallet': 50
        },
        'ved_income': 0,
        'matching_income_rate': 50,
        'display_name': 'Blue Coupon',
        'emoji': '🔵'
    },
    'LOYAL': {
        'price': 500,
        'points': 0,
        'referrer_bonus': 0,
        'referrer_bonus_max_count': 2,
        'activation': True,
        'wallet_required': True,
        'earnings_split': {
            'withdrawable': 50,
            'upgraded_wallet': 50
        },
        'ved_income': 0,
        'matching_income_rate': 50,
        'display_name': 'Loyal Coupon',
        'emoji': '💜'
    },
    # DC Protocol (Jan 2026): Welcome Coupon - Exception coupon for VGK Supreme/EA only
    # No payment required, generates ₹0 income for sponsors/upliners
    'WELCOME': {
        'price': 0,  # ₹0 payment
        'points': 0,  # ₹0 package = 0 matching points (excluded from matching/ved calculations)
        'referrer_bonus': 0,  # No income for sponsor when Welcome Coupon activates
        'referrer_bonus_max_count': 0,
        'activation': True,
        'wallet_required': False,
        'earnings_split': {
            'withdrawable': 100,
            'upgraded_wallet': 0
        },
        'ved_income': 0,  # No Ved income for upliners
        'matching_income_rate': 0,  # Contributes ₹0 to matching (but downline works normally)
        'display_name': 'Welcome Coupon',
        'emoji': '🎁',
        'is_exception_coupon': True,
        'receipt_downloadable': False,  # Cannot download/print receipt
        'allowed_staff_types': ['VGK4U', 'EA']  # Only VGK Supreme and EA can activate
    }
}

# COMPANY CHARGE PERCENTAGES
COMPANY_HANDLING_CHARGE_PERCENTAGE = Decimal('0.20')  # 20% handling charge
COMPANY_CEILING_CHARGE_PERCENTAGE = Decimal('0.10')   # 10% ceiling charge on matching income

# DEDUCTIONS (Applied after income calculation)
DEDUCTION_GURU_DAKSHINA = Decimal('0.02')  # 2% Guru Dakshina
DEDUCTION_ADMIN = Decimal('0.08')           # 8% Admin fee
DEDUCTION_TDS = Decimal('0.02')             # 2% TDS
TOTAL_DEDUCTION = Decimal('0.12')           # Total 12%

# COMMISSION RATES (After deductions)
COMMISSION_RATE_DIRECT = Decimal('0.88')  # 88% (100% - 12% deductions)
COMMISSION_RATE_MATCHING = Decimal('0.88')  # 88% (100% - 12% deductions)

# AWARD SYSTEM CONFIGURATION
AWARD_TIERS = {
    'direct': [
        {'name': 'Smart Watch', 'requirement': 5, 'points_consumed': 5},
        {'name': 'Tablet', 'requirement': 10, 'points_consumed': 5},
        {'name': 'TV', 'requirement': 20, 'points_consumed': 10},
        {'name': 'Bike', 'requirement': 50, 'points_consumed': 30},
        {'name': 'Scooty', 'requirement': 100, 'points_consumed': 50}
    ],
    'matching': [
        {'name': 'Smart Watch', 'requirement': 10, 'points_consumed': 10},
        {'name': 'Tablet', 'requirement': 25, 'points_consumed': 15},
        {'name': 'TV', 'requirement': 50, 'points_consumed': 25},
        {'name': 'Bike', 'requirement': 100, 'points_consumed': 50},
        {'name': 'Scooty', 'requirement': 200, 'points_consumed': 100}
    ]
}

# FIELD ALLOWANCE CONFIGURATION
FIELD_ALLOWANCE = {
    'TIER_1': {
        'name': 'Field Manager',
        'requirement': 50,  # 50 direct referrals
        'monthly_allowance': 5000
    },
    'TIER_2': {
        'name': 'Area Manager',
        'requirement': 100,  # 100 direct referrals
        'monthly_allowance': 10000
    },
    'TIER_3': {
        'name': 'Regional Manager',
        'requirement': 200,  # 200 direct referrals
        'monthly_allowance': 20000
    }
}

# BONANZA CONFIGURATION
BONANZA_REWARDS = {
    'TIER_1': {
        'name': 'Microwave',
        'requirement': 20,
        'reward_value': 8000
    },
    'TIER_2': {
        'name': 'Washing Machine',
        'requirement': 50,
        'reward_value': 15000
    },
    'TIER_3': {
        'name': 'Refrigerator',
        'requirement': 100,
        'reward_value': 25000
    },
    'TIER_4': {
        'name': 'AC',
        'requirement': 200,
        'reward_value': 40000
    },
    'TIER_5': {
        'name': 'Bike',
        'requirement': 500,
        'reward_value': 80000
    }
}

# Additional package maps from original constants
PACKAGE_POINTS_MAP = {
    1: 'PLATINUM',      # Integer 1
    1.0: 'PLATINUM',    # Float 1.0
    0.5: 'DIAMOND',
    0: 'BLUE'           # 0 points = Star (Blue) or Loyal
}

PACKAGE_PRICE_MAP = {
    15000: 'PLATINUM',
    7500: 'DIAMOND',
    1000: 'BLUE',
    500: 'LOYAL'
}

# Mapping coupon package_type (string numbers) to PACKAGE_SYSTEM
COUPON_PACKAGE_MAP = {
    '15000': 'PLATINUM',
    '7500': 'DIAMOND',
    '1000': 'BLUE',
    '500': 'LOYAL',
    'WELCOME': 'WELCOME',  # DC Protocol (Jan 2026): Welcome Coupon - Exception coupon
    '0': 'WELCOME'  # ₹0 payment Welcome Coupon
}

MATCHING_INCOME_RULES = {
    'fixed_rate_per_match': 2000.00,  # NEW: Fixed ₹2,000 per 1:1 point match
    'first_match_requirement': {
        'min_ratio': 2.0,
        'description': 'One-time prerequisite: One leg must have at least 2x the points of the other leg'
    },
    'regular_match': {
        'match_size': 1.0,
        'description': 'Every 1 point from left matches with 1 point from right'
    },
    'eligibility': {
        'min_left': 1,
        'min_right': 1,
        'min_points': 0.5
    }
}

INCOME_RATES = {
    'guru_dakshina_percentage': 2.0,
    'ved_3rd_user_position': 3,
    'tds_rate': 2.0,
    'admin_charge_rate': 8.0,
    'total_deduction_rate': 10.0
}

INCOME_LIMITS = {
    'daily_ved_matching_ceiling': 50000,
    'auto_upgrade_threshold': 15000
}

# DC Protocol (Feb 2026): Default coupon points for all activated users
# Coupon points can be used on any segment, capped at 15000 points per segment
DEFAULT_COUPON_POINTS = 30000
SEGMENT_POINTS_CAP = 15000  # Max points usable per segment (EV, Real Estate, Insurance)

# Helper functions
def get_package_config(points: float) -> Dict[str, Any]:
    """Get package configuration by points value"""
    package_type = PACKAGE_POINTS_MAP.get(points)
    if package_type:
        return PACKAGE_SYSTEM[package_type]
    return None

def get_referral_bonus(points: float, bonus_count: int = 0) -> float:
    """Calculate referral bonus based on points"""
    package_config = get_package_config(points)
    if not package_config:
        return 0.0
    max_count = package_config['referrer_bonus_max_count']
    if bonus_count >= max_count:
        return 0.0
    return float(package_config['referrer_bonus'])

def get_ved_income(points: float) -> float:
    """Get Ved income amount based on package points"""
    package_config = get_package_config(points)
    if not package_config:
        return 0.0
    return float(package_config['ved_income'])

UPGRADE_WALLET_THRESHOLD = 15000.0

def get_earnings_split(points: float, upgrade_wallet_balance: float = None) -> Dict[str, int]:
    """Get earnings split percentage for package.
    Diamond/Star/Loyal use 50/50 split until upgrade wallet reaches ₹15,000 threshold,
    then auto-switch to 100% withdrawable.
    """
    package_config = get_package_config(points)
    if not package_config:
        return {'withdrawable': 100, 'upgraded_wallet': 0}
    split = package_config['earnings_split']
    if upgrade_wallet_balance is not None and split.get('upgraded_wallet', 0) > 0:
        if upgrade_wallet_balance >= UPGRADE_WALLET_THRESHOLD:
            return {'withdrawable': 100, 'upgraded_wallet': 0}
    return split

def get_matching_income_per_point_match() -> float:
    """Get fixed matching income per 1:1 point match"""
    return MATCHING_INCOME_RULES['fixed_rate_per_match']

# KYC REQUIREMENT SETTINGS
KYC_REQUIRED_FOR_WITHDRAWAL = True
BANK_DETAILS_REQUIRED = True

# WITHDRAWAL CONFIGURATION
MINIMUM_WITHDRAWAL_AMOUNT = Decimal('100')
MAXIMUM_WITHDRAWAL_AMOUNT = Decimal('50000')
WITHDRAWAL_PROCESSING_FEE = Decimal('0')
WITHDRAWAL_APPROVAL_REQUIRED = True

__all__ = [
    'PRODUCTION_START_DATE',
    'PACKAGE_SYSTEM',
    'PACKAGE_POINTS_MAP',
    'PACKAGE_PRICE_MAP',
    'COUPON_PACKAGE_MAP',
    'MATCHING_INCOME_RULES',
    'INCOME_RATES',
    'INCOME_LIMITS',
    'COMPANY_HANDLING_CHARGE_PERCENTAGE',
    'COMPANY_CEILING_CHARGE_PERCENTAGE',
    'DEDUCTION_GURU_DAKSHINA',
    'DEDUCTION_ADMIN',
    'DEDUCTION_TDS',
    'TOTAL_DEDUCTION',
    'COMMISSION_RATE_DIRECT',
    'COMMISSION_RATE_MATCHING',
    'AWARD_TIERS',
    'FIELD_ALLOWANCE',
    'BONANZA_REWARDS',
    'KYC_REQUIRED_FOR_WITHDRAWAL',
    'BANK_DETAILS_REQUIRED',
    'MINIMUM_WITHDRAWAL_AMOUNT',
    'MAXIMUM_WITHDRAWAL_AMOUNT',
    'WITHDRAWAL_PROCESSING_FEE',
    'WITHDRAWAL_APPROVAL_REQUIRED',
    'get_package_config',
    'get_referral_bonus',
    'get_ved_income',
    'get_earnings_split',
    'get_matching_income_per_point_match',
    'AwardStatus',
    'normalize_status',
    'is_valid_dc_status',
    'LEGACY_TO_DC_PROTOCOL_MAPPING'
]
