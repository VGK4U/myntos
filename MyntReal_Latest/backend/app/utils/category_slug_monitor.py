"""
DC Protocol: Category Slug Coverage Monitor
Created: Jan 10, 2026

Utility to monitor and validate real estate category slug coverage.
Ensures the MyntReal endpoint correctly captures all real estate categories.
"""

import logging
from typing import List, Set, Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================
# OFFICIAL CATEGORY SLUG DEFINITIONS
# ============================================================

# Real Estate category slugs that MyntReal properties tab should cover
REAL_ESTATE_SLUGS: Set[str] = {
    'real_estate',      # Legacy underscore variant
    'real-estate',      # Official hyphenated slug (DEFAULT_SIGNUP_CATEGORIES)
    'property',         # Alternative name for property listings
    'realestate',       # No separator variant
    'real_dreams',      # MyntReal Real Dreams platform specific
}

# Insurance category slugs for Zynova
INSURANCE_SLUGS: Set[str] = {
    'insurance',
    'life-insurance',
    'health-insurance',
    'general-insurance',
}

# EV category slugs
EV_SLUGS: Set[str] = {
    'ev-dealer',
    'ev-distributorship',
    'ev_dealer',
    'ev_distributorship',
}


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def get_real_estate_slugs() -> List[str]:
    """
    Returns the list of real estate slugs for filtering CRM leads.
    Used by MyntReal properties tab endpoint.
    """
    return list(REAL_ESTATE_SLUGS)


def validate_category_coverage(db: Session) -> Dict[str, Any]:
    """
    Validate real estate category slug coverage in database.
    
    Args:
        db: Database session
        
    Returns:
        Dict with validation results:
        - covered_slugs: Slugs found in database
        - missing_slugs: Expected slugs not in database
        - extra_slugs: Slugs in database not in expected list
        - is_valid: True if at least one real estate category exists
    """
    from app.models.signup_category import SignupCategory
    
    # Get all signup categories from database
    all_categories = db.query(SignupCategory).all()
    db_slugs = {c.slug for c in all_categories}
    
    # Check coverage
    covered = REAL_ESTATE_SLUGS & db_slugs
    missing = REAL_ESTATE_SLUGS - db_slugs
    
    # Find real estate related slugs that might be new variants
    extra_re_slugs = {
        s for s in db_slugs 
        if any(term in s.lower() for term in ['real', 'estate', 'property', 'dream'])
        and s not in REAL_ESTATE_SLUGS
    }
    
    return {
        'covered_slugs': list(covered),
        'missing_slugs': list(missing),
        'extra_slugs': list(extra_re_slugs),
        'is_valid': len(covered) > 0,
        'total_expected': len(REAL_ESTATE_SLUGS),
        'total_found': len(covered)
    }


def log_category_coverage(db: Session, logger=None) -> None:
    """
    Log category coverage status for monitoring.
    
    Args:
        db: Database session
        logger: Optional logger instance (uses print if None)
    """
    result = validate_category_coverage(db)
    
    log = logger.info if logger else print
    
    log(f"[DC-SLUG-MONITOR] Real Estate Category Coverage")
    log(f"  - Found: {result['total_found']}/{result['total_expected']} expected slugs")
    log(f"  - Covered: {result['covered_slugs']}")
    
    if result['missing_slugs']:
        warn = logger.warning if logger else print
        warn(f"  - Missing (may not be configured): {result['missing_slugs']}")
    
    if result['extra_slugs']:
        log(f"  - New variants found (consider adding to REAL_ESTATE_SLUGS): {result['extra_slugs']}")


def get_category_ids_by_slugs(db: Session, slugs: List[str]) -> List[int]:
    """
    Get category IDs for given slugs.
    
    Args:
        db: Database session
        slugs: List of category slugs to look up
        
    Returns:
        List of category IDs
    """
    from app.models.signup_category import SignupCategory
    
    categories = db.query(SignupCategory.id).filter(
        SignupCategory.slug.in_(slugs)
    ).all()
    
    return [c.id for c in categories]


# ============================================================
# QUICK CHECK (can be run standalone)
# ============================================================

def quick_check():
    """
    Quick check that can be called from shell.
    Usage: python -c "from app.utils.category_slug_monitor import quick_check; quick_check()"
    """
    print("=" * 50)
    print("DC Protocol: Category Slug Monitor")
    print("=" * 50)
    print(f"\nReal Estate Slugs ({len(REAL_ESTATE_SLUGS)}):")
    for slug in sorted(REAL_ESTATE_SLUGS):
        print(f"  - {slug}")
    print(f"\nInsurance Slugs ({len(INSURANCE_SLUGS)}):")
    for slug in sorted(INSURANCE_SLUGS):
        print(f"  - {slug}")
    print(f"\nEV Slugs ({len(EV_SLUGS)}):")
    for slug in sorted(EV_SLUGS):
        print(f"  - {slug}")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    quick_check()
