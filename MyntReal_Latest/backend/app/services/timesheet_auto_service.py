"""
Timesheet Auto-Entry Service (DC Protocol)
Auto-creates/updates StaffTimesheetEntry when time is logged from KRA or Day Plan.

Rules:
- auto_source='kra'      → created from KRA submission (kra_id set)
- auto_source='day_plan' → created from Day Plan EOD (task_id set)
- These entries cannot be edited or deleted by the employee
- They still go through normal manager approval flow
- start/end times are placed in the 20:00–23:59 range to stay separate from manual entries

DC Protocol (fix): All db.flush() calls inside this function use db.begin_nested()
(SAVEPOINTs) so that a collision or update failure only rolls back the inner timesheet
operation — never the caller's outer transaction (KRA submit, day plan update, etc.).
"""

from datetime import datetime, time, timedelta, date as date_type
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import logging
logger = logging.getLogger(__name__)


def _get_indian_time():
    import pytz
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)


def auto_upsert_timesheet_entry(
    db: Session,
    employee_id: int,
    entry_date,
    time_spent_minutes: int,
    entry_type: str,
    auto_source: str,
    comments: str,
    kra_id: int = None,
    task_id: int = None,
    journey_id: int = None,
    created_by: int = None,
    actual_start_time=None,   # datetime.time — use real GPS/clock times when available
    actual_end_time=None,     # datetime.time — use real GPS/clock times when available
):
    """
    Create or update a timesheet entry from KRA, Day Plan, or Journey.
    DC Protocol:
    - Upserts: if an auto entry already exists for the same source/date/entity, update it
    - auto_source entries cannot be edited/deleted by employee (enforced in endpoints)
    - KRA      entries placed in 20:xx slot (no real times available)
    - Day Plan entries placed in 21:xx slot (no real times available)
    - Journey  entries use actual GPS start/end times (actual_start_time / actual_end_time)
    - Retry up to 10 times on start_time collision
    - Uses SAVEPOINTs (begin_nested) so failures never roll back the caller's transaction
    """
    from app.models.staff_timesheet import StaffTimesheetEntry

    if time_spent_minutes < 1 or time_spent_minutes > 1440:
        logger.warning(f"[DC-AUTO-TS] Invalid time_spent={time_spent_minutes} for emp={employee_id}")
        return None

    # Build filter to find existing auto entry for this exact source entity
    filters = [
        StaffTimesheetEntry.employee_id == employee_id,
        StaffTimesheetEntry.date == entry_date,
        StaffTimesheetEntry.auto_source == auto_source,
    ]
    if kra_id is not None:
        filters.append(StaffTimesheetEntry.kra_id == kra_id)
    if task_id is not None:
        filters.append(StaffTimesheetEntry.task_id == task_id)
    if journey_id is not None:
        filters.append(StaffTimesheetEntry.journey_id == journey_id)

    existing = db.query(StaffTimesheetEntry).filter(*filters).first()

    # Determine start/end times
    if actual_start_time is not None and actual_end_time is not None:
        # Use real times (Journey)
        start_t = actual_start_time
        end_t = actual_end_time
    else:
        # Placeholder slot: KRA → 20:xx, Day Plan → 21:xx
        end_t = time(23, 59)
        end_dt = datetime.combine(entry_date, end_t)
        start_dt = end_dt - timedelta(minutes=min(time_spent_minutes, 1430))
        start_t = start_dt.time()

    if existing:
        # Keep existing start_time — changing it can cause unique constraint collisions.
        # Only update the fields that matter (duration, end time, comments).
        existing.end_time = end_t
        existing.duration_minutes = time_spent_minutes
        existing.billable_minutes = time_spent_minutes
        existing.comments = comments
        existing.updated_at = _get_indian_time()
        existing.updated_by = created_by or employee_id
        try:
            # DC-SAVEPOINT-001: Use a nested transaction so a flush failure here
            # does NOT roll back the caller's outer transaction (e.g. KRA submit).
            with db.begin_nested():
                db.flush()
            logger.info(f"[DC-AUTO-TS] Updated auto entry {existing.id} src={auto_source} emp={employee_id} mins={time_spent_minutes}")
            return existing
        except Exception as e:
            logger.warning(f"[DC-AUTO-TS] Failed to update auto entry: {e}")
            # Savepoint is rolled back automatically — outer transaction is intact.
            return None

    # New entry — retry on start_time collision using SAVEPOINTs
    for attempt in range(10):
        try:
            if actual_start_time is not None:
                # For real-time entries, offset by seconds instead of minutes to avoid collisions
                adj_start = (datetime.combine(entry_date, start_t) + timedelta(seconds=attempt)).time()
            else:
                adj_start = (datetime.combine(entry_date, start_t) + timedelta(minutes=attempt)).time()

            new_entry = StaffTimesheetEntry(
                employee_id=employee_id,
                date=entry_date,
                start_time=adj_start,
                end_time=end_t,
                duration_minutes=time_spent_minutes,
                billable_minutes=time_spent_minutes,
                break_duration_minutes=0,
                entry_type=entry_type,
                kra_id=kra_id,
                task_id=task_id,
                journey_id=journey_id,
                auto_source=auto_source,
                comments=comments,
                status='submitted',
                is_locked=False,
                created_by=created_by or employee_id,
                created_at=_get_indian_time(),
                edit_history=[],
            )
            # DC-SAVEPOINT-001: SAVEPOINT wraps each attempt so an IntegrityError
            # (start_time collision) only rolls back this attempt — not the caller's
            # outer transaction. This is the fix for the silent KRA/day-plan data-loss bug.
            with db.begin_nested():
                db.add(new_entry)
                db.flush()
            logger.info(f"[DC-AUTO-TS] Created auto entry {new_entry.id} src={auto_source} emp={employee_id} mins={time_spent_minutes} attempt={attempt}")
            return new_entry
        except IntegrityError:
            # Savepoint auto-rolled back; outer transaction untouched. Try next slot.
            logger.debug(f"[DC-AUTO-TS] start_time collision attempt {attempt} for emp={employee_id} date={entry_date}")
            continue
        except Exception as e:
            # Savepoint auto-rolled back; outer transaction untouched.
            logger.warning(f"[DC-AUTO-TS] Failed to create auto entry: {e}")
            return None

    logger.error(f"[DC-AUTO-TS] All 10 attempts failed for emp={employee_id} date={entry_date} src={auto_source}")
    return None
