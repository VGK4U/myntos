"""
Canonical Phone Number Normalization & Validation Authority — MyntOS Telephony
DC Protocol: Single source of truth for telephone validation and E.164 normalization.
Used uniformly across:
  - CRM Auto-Dialer Queue Builder
  - Lead Reservation & Compliance Checks
  - WebRTC Softphone & Direct Call
  - In-App PSTN / Outbound Bridge
"""

import re
from typing import Optional, Tuple, Any
from sqlalchemy import and_, not_, func


class CanonicalPhoneValidator:
    """
    Single authoritative validation and normalization service for phone numbers.
    Guarantees deterministic normalization and rejects corrupted, non-numeric,
    or out-of-range phone numbers before they reach telecaller queues or telephony gateways.
    """

    PREFIX_REGEX = re.compile(r"^(p:|tel:|phone:|m:)\s*", re.IGNORECASE)

    @classmethod
    def validate(cls, phone: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates and normalizes phone number to standard E.164 format.

        Returns:
            (is_valid: bool, normalized_e164: Optional[str], failure_reason: Optional[str])
        """
        if phone is None:
            return False, None, "Phone number is missing or null"

        raw = str(phone).strip()
        if not raw:
            return False, None, "Phone number is empty"

        # 0. Strip common CRM / Meta Lead Ad protocol prefixes (e.g. 'p:+917780461330' -> '+917780461330')
        raw = cls.PREFIX_REGEX.sub("", raw).strip()
        if not raw:
            return False, None, "Phone number contains only protocol prefix without digits"

        # 1. Reject alphabetic / hex characters (e.g. '9194ad812bb6')
        if re.search(r"[a-zA-Z]", raw):
            return False, None, f"Invalid phone number '{raw}': contains alphabetic/hex characters"

        # 2. Reject disallowed punctuation (permitted: digits, leading +, spaces, -, (), dots)
        if re.search(r"[^\d+\s\-().]", raw):
            return False, None, f"Invalid phone number '{raw}': contains disallowed symbols"

        # 3. Extract pure digits
        has_plus = raw.startswith("+")
        digits = re.sub(r"\D", "", raw)

        # 4. Length checks (ITU-T E.164 limits: 10 to 15 digits)
        if len(digits) < 10:
            return False, None, f"Phone number '{raw}' has too few digits ({len(digits)}): expected at least 10"
        if len(digits) > 15:
            return False, None, f"Phone number '{raw}' has too many digits ({len(digits)}): maximum is 15 digits"

        # 5. Normalization rules
        # Standard 10-digit Indian number (e.g. '9849471128' -> '+919849471128')
        if len(digits) == 10:
            norm = f"+91{digits}"
        # 11-digit Indian number with leading 0 (e.g. '09849471128' -> '+919849471128')
        elif len(digits) == 11 and digits.startswith("0"):
            norm = f"+91{digits[1:]}"
        # 12-digit Indian number with country code 91 (e.g. '919849471128' -> '+919849471128')
        elif len(digits) == 12 and digits.startswith("91"):
            norm = f"+{digits}"
        # International with explicit plus prefix or 10-15 digits
        elif has_plus and 10 <= len(digits) <= 15:
            norm = f"+{digits}"
        elif 10 <= len(digits) <= 15:
            norm = f"+{digits}"
        else:
            return False, None, f"Unable to normalize phone number '{raw}'"

        # 6. Final E.164 structure validation: + followed by 10 to 15 digits
        if re.match(r"^\+[1-9]\d{9,14}$", norm):
            return True, norm, None

        return False, None, f"Phone number '{raw}' does not conform to ITU-T E.164 specification"

    @classmethod
    def normalize(cls, phone: Any) -> Optional[str]:
        """
        Returns normalized E.164 string if valid, otherwise None.
        """
        is_valid, norm, _ = cls.validate(phone)
        return norm if is_valid else None

    @classmethod
    def is_valid(cls, phone: Any) -> bool:
        """
        Fast boolean validity check.
        """
        is_valid, _, _ = cls.validate(phone)
        return is_valid

    @classmethod
    def get_sql_filter(cls, column):
        """
        Constructs deterministic SQLAlchemy filter conditions to exclude
        corrupted, empty, or non-phone records directly at the database query layer,
        handling protocol prefixes like 'p:' seamlessly.
        Reused by CRM queue builders.
        """
        clean_col = func.regexp_replace(column, r"^(p:|tel:|phone:|m:)\s*", "", "i")
        return and_(
            column.isnot(None),
            column != "",
            not_(clean_col.op("~*")("[a-zA-Z]")),
            func.length(func.regexp_replace(clean_col, r"[^\d]", "", "g")) >= 10,
            func.length(func.regexp_replace(clean_col, r"[^\d]", "", "g")) <= 15
        )
