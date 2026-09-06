"""
Centralized Timezone Authority for MyntOS — Indian Standard Time (IST)
Authoritative Single Source of Truth for all timestamp generation, parsing, and formatting.
Timezone: Asia/Kolkata (UTC+5:30)
Created: Sep 2026
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Union
import pytz

# Timezone Singletons
IST = pytz.timezone('Asia/Kolkata')
IST_TZ = timezone(timedelta(hours=5, minutes=30))
IST_OFFSET_SECONDS = 19800  # 5 hours 30 minutes


def get_indian_time() -> datetime:
    """
    Get current time in Indian timezone (IST) as naive datetime for database storage.
    Preserves exact Postgres timestamp-without-timezone convention.
    """
    return datetime.now(IST).replace(tzinfo=None)


def get_indian_time_aware() -> datetime:
    """
    Get current time in Indian timezone (IST) as timezone-aware datetime.
    """
    return datetime.now(IST)


def get_indian_today() -> date:
    """
    Get current date in Indian timezone (IST).
    """
    return datetime.now(IST).date()


def from_epoch_to_ist(ts: Union[int, float, str, None]) -> Optional[datetime]:
    """
    Convert a unix timestamp (seconds or milliseconds) to a naive datetime in IST.
    """
    if ts is None:
        return None
    try:
        val = float(ts)
        if val <= 0:
            return None
        # Detect milliseconds (timestamps > 1e11 are in ms)
        if val > 1e11:
            val = val / 1000.0
        return datetime.fromtimestamp(val, tz=IST).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError):
        return None


def parse_to_ist(dt_val: Union[datetime, str, int, float, None]) -> Optional[datetime]:
    """
    Parse an input (ISO string, unix timestamp, or datetime) to naive IST datetime.
    """
    if dt_val is None:
        return None
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is not None:
            return dt_val.astimezone(IST).replace(tzinfo=None)
        return dt_val
    if isinstance(dt_val, (int, float)):
        return from_epoch_to_ist(dt_val)
    if isinstance(dt_val, str):
        cleaned = dt_val.strip()
        if not cleaned:
            return None
        try:
            # Handle timestamps as strings
            if cleaned.isdigit() or (cleaned.replace('.', '', 1).isdigit() and '.' in cleaned):
                return from_epoch_to_ist(float(cleaned))
            # Handle ISO formats
            if cleaned.endswith('Z') or cleaned.endswith('z'):
                dt_parsed = datetime.fromisoformat(cleaned[:-1] + '+00:00')
                return dt_parsed.astimezone(IST).replace(tzinfo=None)
            dt_parsed = datetime.fromisoformat(cleaned)
            if dt_parsed.tzinfo is not None:
                return dt_parsed.astimezone(IST).replace(tzinfo=None)
            return dt_parsed
        except Exception:
            return None
    return None


def to_ist_iso(dt_val: Optional[datetime]) -> Optional[str]:
    """
    Format a datetime into standard ISO 8601 string.
    If naive, represents naive IST string.
    """
    if not dt_val:
        return None
    if dt_val.tzinfo is None:
        return dt_val.isoformat()
    return dt_val.astimezone(IST).isoformat()


def format_indian_time(dt_val: Optional[datetime], fmt: str = "%d %b %Y, %I:%M %p IST") -> str:
    """
    Format datetime into a user-friendly IST string with AM/PM.
    """
    if not dt_val:
        return "—"
    ist_dt = parse_to_ist(dt_val)
    if not ist_dt:
        return "—"
    return ist_dt.strftime(fmt)
