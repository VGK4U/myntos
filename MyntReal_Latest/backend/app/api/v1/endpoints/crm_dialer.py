"""
CRM Auto Dialer API Endpoints
DC Protocol: DC_DIALER_001
Prioritized call queue with session management, attempt logging, and analytics.
Supports Staff portal (department-based) and MNR portal (company-assignment-based).
do_not_call is a lead STATUS value — filterable and manager-changeable.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pytz
import json
import logging
import os
import re
import asyncio
import requests as _http

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.crm import CRMLead, CRMLeadFollowUp, CRMLeadNote, CRMLeadAssignment
from app.models.staff import StaffEmployee
from app.models.user import User
from app.models.call_tracking import StaffCallLog
from app.models.signup_category import SignupCategory
from app.models.operator_calls import OperatorCall
from app.utils.staff_hierarchy import get_recursive_downline, get_team_member_ids
from app.services.timesheet_auto_service import auto_upsert_timesheet_entry

logger = logging.getLogger(__name__)
router = APIRouter()

IST = pytz.timezone('Asia/Kolkata')

# ── DC_DIALER_WS: In-memory registry + single shared PG LISTEN per worker process ──
# Maps user_ref (str) -> asyncio.Queue for pushing messages to the WS handler
_dialer_ws_registry: Dict[str, asyncio.Queue] = {}

# Shared-listener state: ONE psycopg2 connection per worker process (not per socket).
# All open WS connections in this worker share it for cross-worker event fanout.
# Ensures DB connection count stays O(workers) not O(concurrent_sockets).
_dialer_pg_listener_task: Optional[asyncio.Task] = None
_dialer_pg_listener_started = False


async def _start_shared_pg_listener() -> None:
    """Start (if not already running) a single background PG LISTEN task per worker.
    Opened once on first WS connection; runs for the lifetime of the worker.
    Listens on 'dialer_events' channel; dispatches to per-user asyncio Queues.
    """
    global _dialer_pg_listener_task, _dialer_pg_listener_started
    if _dialer_pg_listener_started:
        return
    _dialer_pg_listener_started = True

    async def _listener_loop():
        import select as _select
        _conn = None
        while True:  # reconnect on transient errors
            try:
                import psycopg2 as _pg2
                from app.core.config import settings as _cfg
                loop = asyncio.get_event_loop()
                _conn = await loop.run_in_executor(
                    None,
                    lambda: _pg2.connect(str(_cfg.DATABASE_URL), connect_timeout=5)
                )
                _conn.autocommit = True
                await loop.run_in_executor(
                    None,
                    lambda: _conn.cursor().execute("LISTEN dialer_events")
                )
                logger.info("[DC_DIALER_WS] Shared PG listener started (channel=dialer_events)")

                while True:
                    def _poll():
                        _select.select([_conn], [], [], 0.1)
                        _conn.poll()
                        notifs = []
                        while _conn.notifies:
                            notifs.append(_conn.notifies.pop(0).payload)
                        return notifs

                    payloads = await loop.run_in_executor(None, _poll)
                    for raw in payloads:
                        try:
                            evt = json.loads(raw)
                            ref = evt.get("user_ref")
                            msg = evt.get("payload")
                            if ref and msg:
                                q = _dialer_ws_registry.get(ref)
                                if q is not None:
                                    try:
                                        q.put_nowait(msg)
                                    except asyncio.QueueFull:
                                        pass
                        except Exception:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as _ex:
                logger.warning("[DC_DIALER_WS] PG listener error (%s) — reconnecting in 5s", _ex)
                await asyncio.sleep(5)
            finally:
                if _conn is not None:
                    try:
                        _conn.close()
                    except Exception:
                        pass
                    _conn = None

    loop = asyncio.get_event_loop()
    _dialer_pg_listener_task = loop.create_task(_listener_loop())


async def _push_dialer_ws(user_ref: str, payload: dict) -> None:
    """DC_DIALER_WS: Same-worker fast path — enqueue payload into the in-process registry.
    Cross-worker delivery is handled by the shared PG LISTEN task (one connection per worker).
    HTTP handlers emit pg_notify('dialer_events', ...) before db.commit().
    """
    q = _dialer_ws_registry.get(user_ref)
    if q is not None:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("[DC_DIALER_WS] Queue full for user_ref=%s — dropping same-worker push", user_ref)

# DC_DIALER: Statuses that permanently disqualify a lead from the dialer queue
# NOTE: 'lost' is handled separately — lost leads re-enter after 60 days (_LOST_REENTRY_DAYS)
DIALER_EXCLUDE_STATUSES = {'won', 'completed', 'do_not_call'}
_LOST_REENTRY_DAYS = 60


def _dialer_active_filter(now: datetime):
    """DC_LOST_REENTRY: Returns a SQLAlchemy condition for dialer-eligible leads.
    - Won / completed / do_not_call: permanently excluded.
    - Lost: excluded for 60 days from lost_at, then re-enters the queue.
    """
    cutoff = now - timedelta(days=_LOST_REENTRY_DAYS)
    return and_(
        ~CRMLead.status.in_(DIALER_EXCLUDE_STATUSES),
        or_(
            CRMLead.status != 'lost',
            and_(CRMLead.lost_at.isnot(None), CRMLead.lost_at < cutoff),
        ),
    )

# DC_DIALER: Roles with full org visibility in dialer analytics
DIALER_FULL_ACCESS = {'vgk4u', 'key_leadership', 'leadership_role', 'ea', 'hr'}

# DC_MYOP_CTC: MyOperator Click-to-Call API configuration
# Public developer API (for user list and call search)
_MYOP_BASE_URL = 'https://developers.myoperator.co'
_MYOP_API_TOKEN = os.getenv('MYOPERATOR_API_TOKEN', '')
_MYOP_X_API_KEY = os.getenv('MYOPERATOR_X_API_KEY', '')
_MYOP_API_COMPANY_ID = os.getenv('MYOPERATOR_API_COMPANY_ID', '')
_MYOP_VIRTUAL_NUMBER = os.getenv('MYOPERATOR_VIRTUAL_NUMBER', '')
# OBD API (for CTC / agent bridge outbound calls)
_MYOP_OBD_URL = 'https://obd-api.myoperator.co/obd-api-v1'
_MYOP_SECRET_TOKEN = os.getenv('MYOPERATOR_WEBHOOK_SECRET', '')
_MYOP_PUBLIC_IVR_ID = os.getenv('MYOPERATOR_PUBLIC_IVR_ID', '')

# DC_MYOP_USER_CACHE: Cache of agent phone -> MyOperator user_id mappings
# Populated on first CTC call and refreshed every 30 minutes
_myop_user_cache: dict = {}
_myop_user_cache_ts: float = 0.0
_MYOP_USER_CACHE_TTL = 1800  # 30 minutes


def _get_myop_user_id(agent_phone_10: str) -> Optional[str]:
    """
    DC_MYOP_UID: Look up the MyOperator user_id for an agent by their 10-digit phone number.
    Fetches from GET /user?token=TOKEN (returns list of all agents).
    Caches result for 30 minutes to avoid repeated API calls.
    """
    import time
    global _myop_user_cache, _myop_user_cache_ts
    now = time.time()
    if now - _myop_user_cache_ts > _MYOP_USER_CACHE_TTL or not _myop_user_cache:
        try:
            resp = _http.get(
                f'{_MYOP_BASE_URL}/user',
                params={'token': _MYOP_API_TOKEN},
                timeout=10
            )
            data = resp.json()
            if data.get('status') == 'success' and data.get('data'):
                cache = {}
                for u in data['data']:
                    raw = re.sub(r'[^\d]', '', str(u.get('contact_number', '')))
                    phone10 = raw[-10:] if len(raw) > 10 else raw
                    if phone10:
                        cache[phone10] = u.get('user_id', '')
                _myop_user_cache = cache
                _myop_user_cache_ts = now
                logger.info('[DC_MYOP_UID] Refreshed user cache: %d agents', len(cache))
            else:
                logger.warning('[DC_MYOP_UID] Failed to refresh user cache: %s', data)
        except Exception as e:
            logger.error('[DC_MYOP_UID] User cache refresh failed: %s', e)
    return _myop_user_cache.get(agent_phone_10)


def _normalize_phone_for_ctc(phone: str) -> str:
    """Strip all non-digits and ensure 10-digit format for MyOperator API."""
    digits = re.sub(r'[^\d]', '', str(phone or ''))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def get_ist_now():
    return datetime.now(IST).replace(tzinfo=None)


def _is_overdue(lead) -> bool:
    if not lead.next_followup_date:
        return False
    # DC_OVERDUE_FIX: Match dashboard definition — overdue only when the scheduled date
    # is strictly before TODAY (midnight). A follow-up set for any time today is "Due Today",
    # not "Overdue". This prevents intraday false positives (e.g. nfd=9AM, call at 10AM).
    now = get_ist_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return lead.next_followup_date < today_start


def _is_due_today(lead) -> bool:
    if not lead.next_followup_date:
        return False
    now = get_ist_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return today_start <= lead.next_followup_date < today_end


def _needs_second_contact(lead) -> bool:
    """Status=contacted, last_contact_date older than 3 days."""
    if lead.status != 'contacted':
        return False
    # DC_NFD_GUARD: Skip re-escalation if telecaller deliberately scheduled a future date.
    # A lead with next_followup_date > today is intentionally deferred — not due for 2nd contact.
    if lead.next_followup_date:
        now = get_ist_now()
        today_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if lead.next_followup_date >= today_end:
            return False
    if not lead.last_contact_date:
        return True
    return (get_ist_now() - lead.last_contact_date).days >= 3


def _queue_priority(lead) -> int:
    """Lower = higher priority."""
    if _is_overdue(lead):
        return 1
    if _is_due_today(lead):
        return 2
    if lead.status == 'new':
        return 3
    if _needs_second_contact(lead):
        return 4
    return 5


def _queue_sort_key(lead) -> tuple:
    """Sort key: (priority, created_at) so ties broken by oldest-first."""
    return (_queue_priority(lead), lead.created_at or datetime.min)


def _make_category_sort_key(cat_priority_ids: List[int]):
    """
    DC_CAT_PRIORITY: Returns a sort key function that respects telecaller category preference.
    Within each urgency tier (overdue/due_today/new/second_contact/upcoming), leads whose
    category_id appears earliest in cat_priority_ids come first.
    Leads not in the priority list are sorted after all preferred-category leads in that tier.
    """
    n = len(cat_priority_ids)

    def _key(lead) -> tuple:
        tier = _queue_priority(lead)
        if cat_priority_ids and lead.category_id:
            try:
                cat_rank = cat_priority_ids.index(int(lead.category_id))
            except (ValueError, TypeError):
                cat_rank = n
        else:
            cat_rank = n
        return (tier, cat_rank, lead.created_at or datetime.min)

    return _key


def _get_staff_company_ids(staff: StaffEmployee, requested_company_id: Optional[int] = None) -> List[int]:
    """
    DC_QUEUE_COMPANY_FIX: Return the full set of company IDs a staff member can access.
    A staff member may have leads in base_company_id AND any company in data_companies.
    Previously only base_company_id was checked — this silently hid all cross-company leads.
    """
    if requested_company_id:
        return [requested_company_id]
    company_ids = []
    if staff.base_company_id:
        company_ids.append(staff.base_company_id)
    try:
        extra = staff.data_companies or []
        for cid in extra:
            if cid and cid not in company_ids:
                company_ids.append(int(cid))
    except Exception:
        pass
    return company_ids or [staff.base_company_id]


def _build_category_map(leads: List[CRMLead], db: Session) -> dict:
    """
    DC_CATEGORY_NAME_FIX: Bulk-fetch category names for a list of leads.
    Returns {category_id: category_name} dict. One query regardless of queue size.
    """
    cat_ids = {l.category_id for l in leads if l.category_id}
    if not cat_ids:
        return {}
    rows = db.query(SignupCategory.id, SignupCategory.name).filter(
        SignupCategory.id.in_(cat_ids)
    ).all()
    return {r.id: r.name for r in rows}


def _build_queue_for_staff(staff: StaffEmployee, db: Session, company_id: Optional[int] = None) -> List[dict]:
    """Build prioritized lead queue for a staff member.

    DC_TIER_QUEUE: Queue is built in two ordered tiers:
      Tier 1 — base_company_id leads (primary company, highest priority)
      Tier 2 — data_companies leads (working companies; merged, sorted by segment
                within each urgency tier via dialer_category_priority)
    Within each tier: urgency (overdue→today→new→2nd-contact) then segment preference.
    When a specific company_id is requested the tiering is bypassed — flat queue for
    that company only (preserves existing filter-by-company behaviour).
    Falls back to flat queue if base_company_id is not set.
    """
    emp_id = staff.id
    emp_code = staff.emp_code
    user_ref = str(staff.id)

    # DC_DIALER_FIX2: Exclude leads already dialed today by this user (non-skip outcomes)
    ist_today = get_ist_now().replace(hour=0, minute=0, second=0, microsecond=0)
    dialed_rows = db.execute(text("""
        SELECT DISTINCT lead_id FROM crm_dialer_attempts
        WHERE user_ref = :ref AND call_outcome != 'skip'
        AND dialed_at >= :today
    """), {"ref": user_ref, "today": ist_today}).fetchall()
    dialed_today = {r[0] for r in dialed_rows}

    # DC_NMC_FIX: Permanently exclude unassigned leads this user dismissed as "not my category"
    nmc_rows = db.execute(text("""
        SELECT DISTINCT lead_id FROM crm_dialer_attempts
        WHERE user_ref = :ref AND call_outcome = 'not_my_category'
    """), {"ref": user_ref}).fetchall()
    nmc_excluded = {r[0] for r in nmc_rows}

    # DC_CAT_PRIORITY: Category/segment preference sort function — shared across both tiers
    try:
        _cat_prio = [int(x) for x in (staff.dialer_category_priority or [])]
    except Exception:
        _cat_prio = []
    _sort_fn = _make_category_sort_key(_cat_prio) if _cat_prio else _queue_sort_key

    def _fetch_leads_for_companies(co_ids: List[int]) -> tuple:
        """
        DC_TIER_QUEUE: Fetch assigned + unassigned leads for the given company IDs,
        apply all standard exclusions (dialed today, NMC), and return sorted leads
        with their assigned-ID set.  Returns (sorted_leads_list, assigned_ids_set).
        """
        if not co_ids:
            return [], set()

        # DC_FUTURE_NFD_EXCLUDE: Compute today-end once for the future-date filter
        _now = get_ist_now()
        _today_end = _now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # Assigned leads — handler, telecaller, field_staff, or primary_owner
        # DC_PRIMARY_OWNER_FIX: includes leads assigned via primary_owner_id
        a_filter = [
            CRMLead.company_id.in_(co_ids),
            _dialer_active_filter(_now),
            or_(
                and_(CRMLead.handler_type == 'staff', CRMLead.handler_id == emp_code),
                CRMLead.telecaller_id == emp_id,
                CRMLead.field_staff_id == emp_id,
                and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == emp_id),
            ),
            # DC_FUTURE_NFD_EXCLUDE: Omit leads intentionally deferred to a future date.
            # Overdue (nfd < today) and due-today (nfd within today) are still included.
            or_(
                CRMLead.next_followup_date.is_(None),
                CRMLead.next_followup_date < _today_end,
            ),
        ]
        if dialed_today:
            a_filter.append(CRMLead.id.notin_(dialed_today))
        a_q = db.query(CRMLead).filter(*a_filter).all()
        a_ids = {l.id for l in a_q}

        # Unassigned new leads — secondary pool for this company set
        # DC_DIALER_FIX1: Exclude leads already claimed by another user
        # DC_NMC_FIX: Exclude leads this user dismissed as "not my category"
        u_exclude = a_ids | dialed_today | nmc_excluded
        u_filter = [
            CRMLead.company_id.in_(co_ids),
            CRMLead.status == 'new',
            CRMLead.handler_type == 'unassigned',
            CRMLead.telecaller_id.is_(None),
            CRMLead.field_staff_id.is_(None),
            # DC_FUTURE_NFD_EXCLUDE: Unassigned new leads with a future follow-up date
            # are excluded — a future date on an unassigned lead is unusual but guard it.
            or_(
                CRMLead.next_followup_date.is_(None),
                CRMLead.next_followup_date < _today_end,
            ),
        ]
        if u_exclude:
            u_filter.append(CRMLead.id.notin_(u_exclude))
        u_q = db.query(CRMLead).filter(*u_filter).limit(200).all()

        # DC_NEW_LEADS_FIX: merge and sort so new leads interleave by urgency tier,
        # with segment preference (dialer_category_priority) as secondary sort key
        leads = sorted(a_q + u_q, key=_sort_fn)
        return leads, a_ids

    # ── Specific company requested: bypass tiering, flat queue for that company ──
    if company_id:
        leads, assigned_ids = _fetch_leads_for_companies([company_id])
        cat_map = _build_category_map(leads, db)
        return [_lead_to_queue_item(l, 'assigned' if l.id in assigned_ids else 'unassigned', cat_map)
                for l in leads]

    # ── No specific company: build tiered queue ──
    base_id = staff.base_company_id

    # Fallback: no base company set → flat queue across all accessible companies
    if not base_id:
        all_ids = _get_staff_company_ids(staff)
        leads, assigned_ids = _fetch_leads_for_companies(all_ids)
        cat_map = _build_category_map(leads, db)
        return [_lead_to_queue_item(l, 'assigned' if l.id in assigned_ids else 'unassigned', cat_map)
                for l in leads]

    # Tier 1 — base company leads (primary, highest priority)
    tier1_leads, tier1_assigned_ids = _fetch_leads_for_companies([base_id])

    # Tier 2 — data company leads (working companies, segment-sorted within urgency tier)
    # DC_TIER_QUEUE: data_companies excludes base_company_id to prevent double-fetch
    try:
        data_ids = [int(c) for c in (staff.data_companies or []) if c and int(c) != base_id]
    except Exception:
        data_ids = []
    tier2_leads, tier2_assigned_ids = _fetch_leads_for_companies(data_ids)

    all_leads = tier1_leads + tier2_leads
    all_assigned_ids = tier1_assigned_ids | tier2_assigned_ids

    # DC_CATEGORY_NAME_FIX: Single bulk category lookup for all leads across both tiers
    cat_map = _build_category_map(all_leads, db)

    return [_lead_to_queue_item(l, 'assigned' if l.id in all_assigned_ids else 'unassigned', cat_map)
            for l in all_leads]


def _build_queue_for_mnr(user: User, db: Session) -> List[dict]:
    """Build prioritized lead queue for an MNR member."""
    user_id = user.id
    user_ref = str(user.id)

    # DC_DIALER_FIX2: Exclude leads already dialed today by this user (non-skip outcomes)
    ist_today = get_ist_now().replace(hour=0, minute=0, second=0, microsecond=0)
    dialed_rows = db.execute(text("""
        SELECT DISTINCT lead_id FROM crm_dialer_attempts
        WHERE user_ref = :ref AND call_outcome != 'skip'
        AND dialed_at >= :today
    """), {"ref": user_ref, "today": ist_today}).fetchall()
    dialed_today = {r[0] for r in dialed_rows}

    # DC_FUTURE_NFD_EXCLUDE: Compute today-end for MNR queue future-date filter
    _mnr_now = get_ist_now()
    _mnr_today_end = _mnr_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # DC_DIALER: Leads assigned to this MNR member
    assigned_filter = [
        CRMLead.mnr_handler_id == user_id,
        _dialer_active_filter(_mnr_now),
        # DC_FUTURE_NFD_EXCLUDE: Skip leads deferred to a future date
        or_(
            CRMLead.next_followup_date.is_(None),
            CRMLead.next_followup_date < _mnr_today_end,
        ),
    ]
    if dialed_today:
        assigned_filter.append(CRMLead.id.notin_(dialed_today))
    assigned_q = db.query(CRMLead).filter(*assigned_filter).all()

    # DC_NMC_FIX: Permanently exclude unassigned leads this user dismissed as "not my category"
    nmc_rows = db.execute(text("""
        SELECT DISTINCT lead_id FROM crm_dialer_attempts
        WHERE user_ref = :ref AND call_outcome = 'not_my_category'
    """), {"ref": user_ref}).fetchall()
    nmc_excluded = {r[0] for r in nmc_rows}

    # DC_DIALER: Unassigned new leads in companies linked to this member
    # DC_DIALER_FIX1: Exclude leads already claimed by another user (telecaller_id/field_staff_id set)
    # DC_NMC_FIX: Also permanently exclude any lead this user said "not my category" for
    assigned_ids = {l.id for l in assigned_q}
    company_ids = _get_mnr_company_ids(user, db)
    unassigned_leads = []
    if company_ids:
        unassigned_filter = [
            CRMLead.company_id.in_(company_ids),
            CRMLead.status == 'new',
            CRMLead.handler_type == 'unassigned',
            CRMLead.telecaller_id.is_(None),
            CRMLead.field_staff_id.is_(None),
            # DC_FUTURE_NFD_EXCLUDE: Guard unassigned leads with a future date too
            or_(
                CRMLead.next_followup_date.is_(None),
                CRMLead.next_followup_date < _mnr_today_end,
            ),
        ]
        if assigned_ids:
            unassigned_filter.append(CRMLead.id.notin_(assigned_ids))
        if dialed_today:
            unassigned_filter.append(CRMLead.id.notin_(dialed_today))
        if nmc_excluded:
            unassigned_filter.append(CRMLead.id.notin_(nmc_excluded))
        unassigned_leads = db.query(CRMLead).filter(*unassigned_filter).limit(200).all()

    # DC_NEW_LEADS_FIX: Merge assigned + unassigned into one pool and sort by priority.
    all_leads = sorted(assigned_q + unassigned_leads, key=_queue_sort_key)

    # DC_CATEGORY_NAME_FIX: Single bulk category lookup for all leads in queue
    cat_map = _build_category_map(all_leads, db)

    return [_lead_to_queue_item(l, 'assigned' if l.id in assigned_ids else 'unassigned', cat_map) for l in all_leads]


def _get_mnr_company_ids(user: User, db: Session) -> List[int]:
    """Get company IDs for an MNR user via their base company."""
    try:
        result = db.execute(
            text("SELECT id FROM associated_companies WHERE id = :cid"),
            {"cid": getattr(user, 'base_company_id', None) or getattr(user, 'company_id', None)}
        ).fetchall()
        return [r[0] for r in result]
    except Exception:
        return []


def _lead_to_queue_item(lead: CRMLead, slot_type: str, cat_map: Optional[dict] = None) -> dict:
    now = get_ist_now()
    last_contact_days = None
    if lead.last_contact_date:
        last_contact_days = (now - lead.last_contact_date).days

    priority_label = 'overdue' if _is_overdue(lead) else (
        'due_today' if _is_due_today(lead) else (
            'new' if lead.status == 'new' else (
                'second_contact' if _needs_second_contact(lead) else 'upcoming'
            )
        )
    )

    # DC_CATEGORY_NAME_FIX: Resolve human-readable category name from pre-fetched map
    category_name = None
    if lead.category_id and cat_map:
        category_name = cat_map.get(lead.category_id)

    return {
        'lead_id': lead.id,
        'name': lead.name,
        'phone': lead.phone or '',
        'alternate_phone': lead.alternate_phone or '',
        'phone_primary_whatsapp': lead.phone_primary_whatsapp,
        'phone_secondary_whatsapp': lead.phone_secondary_whatsapp,
        'status': lead.status,
        'priority': lead.priority,
        'category_id': lead.category_id,
        'category_name': category_name,
        'company_id': lead.company_id,
        'source': lead.source or '',
        'description': lead.description or '',
        'requirements': lead.requirements or '',
        'looking_for': lead.looking_for or '',
        'recent_comments': lead.recent_comments or '',
        'city': lead.city or '',
        'area': lead.area or '',
        'budget_min': lead.budget_min,
        'budget_max': lead.budget_max,
        'next_followup_date': lead.next_followup_date.isoformat() if lead.next_followup_date else None,
        'last_contact_date': lead.last_contact_date.isoformat() if lead.last_contact_date else None,
        'last_contact_days': last_contact_days,
        'queue_priority': priority_label,
        'slot_type': slot_type,
    }


def _get_session_table_row(session_id: int, db: Session):
    row = db.execute(
        text("SELECT * FROM crm_dialer_sessions WHERE id = :id"),
        {"id": session_id}
    ).fetchone()
    return row


def _row_to_session_dict(row) -> dict:
    if not row:
        return {}
    keys = row._mapping.keys()
    d = dict(zip(keys, row))
    for k in ('started_at', 'paused_at', 'last_active_at', 'closed_at'):
        if d.get(k) and isinstance(d[k], datetime):
            d[k] = d[k].isoformat()
    return d


# ──────────────────────────────────────────────────────────────────────────────
# DC_CAT_PRIORITY: DIALER PREFERENCES (category priority)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/preferences")
async def get_dialer_preferences(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_CAT_PRIORITY_GET: Return the telecaller's saved category priority order
    plus all signup categories accessible to their companies.
    category_priority: [id1, id2, ...] — ordered from highest to lowest preference.
    available_categories: [{id, name}, ...] — all categories in their company pool.
    """
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff only")
    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    company_ids = _get_staff_company_ids(staff)
    cats = (
        db.query(SignupCategory.id, SignupCategory.name)
        .filter(SignupCategory.company_id.in_(company_ids))
        .order_by(SignupCategory.name, SignupCategory.id)
        .all()
    )
    # Deduplicate by name, keeping the entry with the lowest ID.
    # Also build a mapping from every raw ID → canonical lowest ID for that name,
    # so that saved_priority entries using non-canonical IDs can be remapped.
    seen_names: dict = {}
    id_to_canonical: dict = {}
    for r in cats:
        if r.name not in seen_names:
            seen_names[r.name] = {"id": r.id, "name": r.name}
        canonical_id = seen_names[r.name]["id"]
        id_to_canonical[r.id] = canonical_id
    deduped_cats = list(seen_names.values())
    canonical_ids_set = {c["id"] for c in deduped_cats}

    try:
        raw_priority = [int(x) for x in (staff.dialer_category_priority or [])]
    except Exception:
        raw_priority = []

    # Normalize priority: remap any non-canonical IDs, remove IDs not in our set,
    # and deduplicate while preserving order.
    normalized_priority: list = []
    seen_priority: set = set()
    for pid in raw_priority:
        cid = id_to_canonical.get(pid)
        if cid is not None and cid in canonical_ids_set and cid not in seen_priority:
            normalized_priority.append(cid)
            seen_priority.add(cid)

    return {
        "success": True,
        "category_priority": normalized_priority,
        "available_categories": deduped_cats,
    }


@router.put("/dialer/preferences")
async def update_dialer_preferences(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_CAT_PRIORITY_PUT: Save the telecaller's preferred category order.
    Accepts {category_priority: [cat_id1, cat_id2, ...]} — ordered list of category IDs.
    The AutoDialer queue will surface leads from earlier categories first within
    each urgency tier (overdue > due_today > new > second_contact > upcoming).
    """
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff only")
    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    raw = body.get("category_priority", [])
    try:
        category_priority = [int(x) for x in raw]
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="category_priority must be a list of integer category IDs")

    staff.dialer_category_priority = category_priority
    db.commit()
    db.refresh(staff)

    return {"success": True, "category_priority": category_priority}


# ──────────────────────────────────────────────────────────────────────────────
# MISSED CALLBACKS (MyOperator integration)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/missed-callbacks")
async def get_missed_callbacks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_MISSED_CB: Return pending missed operator calls for the auto-dialer.
    Sorted: self-missed (handled_by matches this agent's name) first,
    then unassigned (no handled_by), then all others.
    Only returns calls from the last 7 days with missed_status='pending'.
    """
    since = datetime.utcnow() - timedelta(days=7)

    # Get staff name for matching "self" missed calls
    agent_name = ''
    if hasattr(current_user, 'emp_code'):
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if staff:
            parts = []
            if getattr(staff, 'first_name', None):
                parts.append(staff.first_name.strip())
            if getattr(staff, 'last_name', None):
                parts.append(staff.last_name.strip())
            agent_name = ' '.join(parts).lower()

    calls = db.query(OperatorCall).filter(
        OperatorCall.status == 'missed',
        OperatorCall.missed_status == 'pending',
        OperatorCall.started_at >= since,
        OperatorCall.caller_number.isnot(None),
    ).order_by(OperatorCall.started_at.desc()).limit(50).all()

    def _priority(c):
        hb = (c.handled_by or '').lower()
        if agent_name and agent_name in hb or (hb and hb in agent_name and len(hb) > 2):
            return 0  # self-missed
        if not (c.handled_by or '').strip():
            return 1  # unassigned
        return 2  # other agent's missed

    calls.sort(key=_priority)

    result = []
    for c in calls:
        prio = _priority(c)
        result.append({
            'call_id': c.call_id,
            'caller_number': c.caller_number,
            'called_number': c.called_number,
            'operator_name': c.operator_name,
            'handled_by': c.handled_by,
            'started_at': OperatorCall._fmt_dt(c.started_at),
            'duration_seconds': c.duration_seconds,
            'crm_lead_id': c.crm_lead_id,
            'missed_status': c.missed_status,
            'priority_type': 'self' if prio == 0 else ('unassigned' if prio == 1 else 'other'),
        })

    return {"success": True, "data": result, "total": len(result)}


# ──────────────────────────────────────────────────────────────────────────────
# QUEUE
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/queue")
async def get_dialer_queue(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_001: Get prioritized call queue for logged-in user.
    Staff → assigned leads first, then unassigned new.
    MNR  → assigned leads first, then company-linked unassigned.
    Excludes: won, lost, completed, do_not_call.
    """
    if hasattr(current_user, 'emp_code'):
        # Staff portal
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        queue = _build_queue_for_staff(staff, db, company_id)
    else:
        # MNR portal
        queue = _build_queue_for_mnr(current_user, db)

    return {
        "success": True,
        "total": len(queue),
        "overdue": sum(1 for i in queue if i['queue_priority'] == 'overdue'),
        "due_today": sum(1 for i in queue if i['queue_priority'] == 'due_today'),
        "new_leads": sum(1 for i in queue if i['queue_priority'] == 'new'),
        "second_contact": sum(1 for i in queue if i['queue_priority'] == 'second_contact'),
        "queue": queue
    }


# ──────────────────────────────────────────────────────────────────────────────
# LEAD DETAIL (Dialer-scoped — no assignment-ownership check)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/lead/{lead_id}/detail")
async def get_dialer_lead_detail(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_DETAIL: Return core lead fields + last 5 dialer attempts + last 3 notes.
    Scoped to the requesting user's accessible companies — no assignment-ownership check,
    since the lead is already surfaced in their dialer queue.
    Works for both assigned and unassigned leads.
    """
    is_staff = hasattr(current_user, 'emp_code')

    # Determine accessible company IDs for scope guard
    if is_staff:
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if not staff:
            raise HTTPException(status_code=403, detail="Staff record not found")
        company_ids = _get_staff_company_ids(staff)
    else:
        company_ids = _get_mnr_company_ids(current_user, db)

    # Deny-by-default: if no accessible companies resolved, block access entirely.
    # An empty company_ids list means the user's account linkage is broken/missing;
    # bypassing the check would create an IDOR vulnerability.
    if not company_ids:
        raise HTTPException(status_code=403, detail="No accessible companies for this account")

    # Fetch lead — company scope guard (no ownership check)
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.company_id not in company_ids:
        raise HTTPException(status_code=403, detail="Lead not in your accessible companies")

    # Category name
    cat_name = None
    if lead.category_id:
        cat = db.query(SignupCategory.name).filter(SignupCategory.id == lead.category_id).first()
        if cat:
            cat_name = cat[0]

    # Last 5 dialer attempts for this lead
    attempt_rows = db.execute(text("""
        SELECT call_outcome, note, dialed_at, duration_seconds, next_followup_date_set
        FROM crm_dialer_attempts
        WHERE lead_id = :lid
        ORDER BY dialed_at DESC
        LIMIT 5
    """), {"lid": lead_id}).fetchall()
    attempts = [
        {
            "outcome": r[0],
            "note": r[1] or "",
            "dialed_at": r[2].isoformat() if r[2] else None,
            "duration_seconds": r[3] or 0,
            "next_followup_date_set": r[4].isoformat() if r[4] else None,
        }
        for r in attempt_rows
    ]

    # Last 3 notes for this lead
    note_rows = db.execute(text("""
        SELECT note, created_at, created_by_type, created_by_id
        FROM crm_lead_notes
        WHERE lead_id = :lid
        ORDER BY created_at DESC
        LIMIT 3
    """), {"lid": lead_id}).fetchall()
    notes = [
        {
            "note": r[0],
            "created_at": r[1].isoformat() if r[1] else None,
            "created_by_type": r[2],
            "created_by_id": r[3],
        }
        for r in note_rows
    ]

    return {
        "success": True,
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "phone": lead.phone,
            "alternate_phone": lead.alternate_phone,
            "status": lead.status,
            "priority": lead.priority,
            "category_id": lead.category_id,
            "category_name": cat_name,
            "city": lead.city,
            "area": lead.area,
            "budget_min": lead.budget_min,
            "budget_max": lead.budget_max,
            "last_contact_date": lead.last_contact_date.isoformat() if lead.last_contact_date else None,
            "next_followup_date": lead.next_followup_date.isoformat() if lead.next_followup_date else None,
            "handler_type": lead.handler_type,
        },
        "attempts": attempts,
        "notes": notes,
    }


# ──────────────────────────────────────────────────────────────────────────────
# SESSION MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/dialer/session/start")
async def start_dialer_session(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_002: Start a new dialer session or resume existing paused one.
    Accepts queue (list of lead_ids) from client.
    """
    is_staff = hasattr(current_user, 'emp_code')
    portal = 'staff' if is_staff else 'mnr'
    user_ref = str(current_user.id)
    company_id = body.get('company_id') or (
        current_user.base_company_id if hasattr(current_user, 'base_company_id') else None
    )
    queue_lead_ids = body.get('queue_lead_ids', [])

    # Check for existing paused session
    existing = db.execute(text("""
        SELECT id FROM crm_dialer_sessions
        WHERE user_ref = :ref AND portal = :portal AND status = 'paused'
        ORDER BY last_active_at DESC LIMIT 1
    """), {"ref": user_ref, "portal": portal}).fetchone()

    if existing and body.get('resume', False):
        db.execute(text("""
            UPDATE crm_dialer_sessions
            SET status = 'active', last_active_at = :now
            WHERE id = :id
        """), {"id": existing[0], "now": get_ist_now()})
        db.commit()
        row = _get_session_table_row(existing[0], db)
        return {"success": True, "action": "resumed", "session": _row_to_session_dict(row)}

    # Close any existing active sessions for this user
    db.execute(text("""
        UPDATE crm_dialer_sessions
        SET status = 'closed', closed_at = :now
        WHERE user_ref = :ref AND portal = :portal AND status = 'active'
    """), {"ref": user_ref, "portal": portal, "now": get_ist_now()})

    queue_json = json.dumps(queue_lead_ids)
    result = db.execute(text("""
        INSERT INTO crm_dialer_sessions
            (user_ref, portal, company_id, status, queue_data, current_index, started_at, last_active_at)
        VALUES
            (:ref, :portal, :company_id, 'active', :queue, 0, :now, :now)
        RETURNING id
    """), {
        "ref": user_ref, "portal": portal, "company_id": company_id,
        "queue": queue_json, "now": get_ist_now()
    })
    session_id = result.fetchone()[0]
    db.commit()

    row = _get_session_table_row(session_id, db)
    return {"success": True, "action": "started", "session": _row_to_session_dict(row)}


@router.post("/dialer/session/pause")
async def pause_dialer_session(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """DC_DIALER_003: Pause active session — saves current_index for resume."""
    session_id = body.get('session_id')
    current_index = body.get('current_index', 0)
    queue_lead_ids = body.get('queue_lead_ids')

    updates = {"status": "paused", "now": get_ist_now(), "idx": current_index, "id": session_id}
    sql = "UPDATE crm_dialer_sessions SET status='paused', paused_at=:now, last_active_at=:now, current_index=:idx"
    if queue_lead_ids is not None:
        sql += ", queue_data=:queue"
        updates["queue"] = json.dumps(queue_lead_ids)
    sql += " WHERE id=:id"

    db.execute(text(sql), updates)
    db.commit()
    return {"success": True, "message": "Session paused"}


@router.post("/dialer/session/resume")
async def resume_dialer_session(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """DC_DIALER_004: Resume a paused session — returns saved state."""
    is_staff = hasattr(current_user, 'emp_code')
    portal = 'staff' if is_staff else 'mnr'
    user_ref = str(current_user.id)

    row = db.execute(text("""
        SELECT * FROM crm_dialer_sessions
        WHERE user_ref = :ref AND portal = :portal AND status = 'paused'
        ORDER BY last_active_at DESC LIMIT 1
    """), {"ref": user_ref, "portal": portal}).fetchone()

    if not row:
        return {"success": False, "message": "No paused session found"}

    session_dict = _row_to_session_dict(row)
    db.execute(text("""
        UPDATE crm_dialer_sessions SET status='active', last_active_at=:now WHERE id=:id
    """), {"id": session_dict['id'], "now": get_ist_now()})
    db.commit()

    queue_lead_ids = json.loads(session_dict.get('queue_data') or '[]')
    return {
        "success": True,
        "session": session_dict,
        "current_index": session_dict.get('current_index', 0),
        "queue_lead_ids": queue_lead_ids,
    }


@router.post("/dialer/session/close")
async def close_dialer_session(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """DC_DIALER_005: Close session permanently."""
    session_id = body.get('session_id')
    db.execute(text("""
        UPDATE crm_dialer_sessions
        SET status='closed', closed_at=:now, last_active_at=:now
        WHERE id=:id
    """), {"id": session_id, "now": get_ist_now()})
    db.commit()
    return {"success": True, "message": "Session closed"}


@router.get("/dialer/session/current")
async def get_current_session(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_006: Get current active/paused session + last attempt.
    Used by web browser polling every 5s to sync with mobile dialer.
    """
    is_staff = hasattr(current_user, 'emp_code')
    portal = 'staff' if is_staff else 'mnr'
    user_ref = str(current_user.id)

    row = db.execute(text("""
        SELECT * FROM crm_dialer_sessions
        WHERE user_ref = :ref AND portal = :portal AND status IN ('active','paused')
        AND last_active_at > NOW() - INTERVAL '8 hours'
        ORDER BY last_active_at DESC LIMIT 1
    """), {"ref": user_ref, "portal": portal}).fetchone()
    # DC_DIALER_P3: Sessions with last_active_at older than 8h are treated as expired (ghost sessions auto-cleared)

    if not row:
        return {"success": True, "session": None, "last_attempt": None}

    session_dict = _row_to_session_dict(row)

    # Get last attempt (for popup trigger on web)
    last_attempt = db.execute(text("""
        SELECT * FROM crm_dialer_attempts
        WHERE session_id = :sid
        ORDER BY created_at DESC LIMIT 1
    """), {"sid": session_dict['id']}).fetchone()

    last_attempt_dict = None
    if last_attempt:
        keys = last_attempt._mapping.keys()
        last_attempt_dict = dict(zip(keys, last_attempt))
        if isinstance(last_attempt_dict.get('dialed_at'), datetime):
            last_attempt_dict['dialed_at'] = last_attempt_dict['dialed_at'].isoformat()
        if isinstance(last_attempt_dict.get('created_at'), datetime):
            last_attempt_dict['created_at'] = last_attempt_dict['created_at'].isoformat()

    # DC_RESUME_FIX: Include saved queue order so client can anchor to the right lead
    queue_lead_ids = json.loads(session_dict.get('queue_data') or '[]')
    return {
        "success": True,
        "session": session_dict,
        "current_index": session_dict.get('current_index', 0),
        "queue_lead_ids": queue_lead_ids,
        "last_attempt": last_attempt_dict
    }


# ──────────────────────────────────────────────────────────────────────────────
# ATTEMPT LOGGING + LEAD UPDATE
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/dialer/attempt")
async def log_dialer_attempt(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_007: Log a dial attempt + optional outcome + lead update.
    On outcome save: updates lead status, next_followup_date, note, last_contact_date.
    do_not_call outcome sets lead.status = 'do_not_call'.
    """
    session_id = body.get('session_id')
    lead_id = body.get('lead_id')
    call_outcome = body.get('call_outcome')          # answered / no_answer / busy / callback / skip / wrong_number
    call_method = body.get('call_method', 'normal')  # 'myoperator' | 'normal'
    duration_seconds = body.get('duration_seconds', 0)
    note = body.get('note', '')
    next_followup_date = body.get('next_followup_date')   # ISO string or None
    new_status = body.get('new_status')                    # Lead status to update to
    new_priority = body.get('new_priority')
    new_source = body.get('new_source')                    # DC_SOURCE_CAT_FIX: update lead source text
    new_category_id = body.get('new_category_id')          # DC_SOURCE_CAT_FIX: update lead category
    do_not_call = body.get('do_not_call', False)
    current_index = body.get('current_index', 0)
    activity_type = body.get('activity_type')             # DC_DIALER_TIMESHEET: chip label e.g. 'Client Call'
    activity_minutes = body.get('activity_minutes')       # DC_DIALER_TIMESHEET: time spent on activity
    lead_update_minutes = body.get('lead_update_minutes') # DC_DIALER_TIMESHEET: time held for lead update

    now = get_ist_now()
    is_staff = hasattr(current_user, 'emp_code')
    portal = 'staff' if is_staff else 'mnr'
    user_ref = str(current_user.id)

    # Resolve handler info
    handler_type = 'staff' if is_staff else 'mnr'
    handler_id = str(getattr(current_user, 'emp_code', None) or current_user.id)

    # Insert attempt record
    result = db.execute(text("""
        INSERT INTO crm_dialer_attempts
            (session_id, lead_id, user_ref, portal, call_outcome, duration_seconds,
             note, next_followup_date_set, status_updated_to, dialed_at, created_at,
             call_method)
        VALUES
            (:sid, :lid, :ref, :portal, :outcome, :dur,
             :note, :nfd, :status_to, :now, :now,
             :call_method)
        RETURNING id
    """), {
        "sid": session_id, "lid": lead_id, "ref": user_ref, "portal": portal,
        "outcome": call_outcome, "dur": duration_seconds, "note": note,
        "nfd": next_followup_date, "status_to": new_status or ('do_not_call' if do_not_call else None),
        "now": now, "call_method": call_method
    })
    attempt_id = result.fetchone()[0]

    # DC_MYOP_001: Track MyOperator calls per session — unlocks Normal Call after first MyOperator attempt
    if call_method == 'myoperator' and session_id:
        db.execute(text("""
            UPDATE crm_dialer_sessions
            SET myoperator_attempts = COALESCE(myoperator_attempts, 0) + 1
            WHERE id = :id
        """), {"id": session_id})

    # DC_RESUME_FIX: Update session current_index (and optionally queue_data for skip reorders)
    queue_lead_ids_update = body.get('queue_lead_ids')  # optional — sent when queue order changes (skip)
    if session_id:
        if queue_lead_ids_update is not None:
            db.execute(text("""
                UPDATE crm_dialer_sessions
                SET current_index = :idx, queue_data = :queue, last_active_at = :now WHERE id = :id
            """), {"idx": current_index, "queue": json.dumps(queue_lead_ids_update), "now": now, "id": session_id})
        else:
            db.execute(text("""
                UPDATE crm_dialer_sessions
                SET current_index = :idx, last_active_at = :now WHERE id = :id
            """), {"idx": current_index, "now": now, "id": session_id})

    # Update lead
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if lead:
        if do_not_call or call_outcome == 'wrong_number':
            # DC Protocol (Mar 25, 2026): wrong_number outcome sets do_not_call status,
            # removing the lead from all future dialer queues (DIALER_EXCLUDE_STATUSES).
            lead.status = 'do_not_call'
        elif new_status and new_status not in ('', None):
            if lead.status != new_status:
                print(f"[DC-DIALER-STATUS] Lead {lead_id}: {lead.status!r} → {new_status!r} by user={user_ref} portal={portal}", flush=True)
            lead.status = new_status
            # DC_LOST_REENTRY: Record timestamp when lead is marked lost
            # This enables the 60-day re-entry rule in _dialer_active_filter()
            if new_status == 'lost' and not lead.lost_at:
                lead.lost_at = now
            elif new_status != 'lost':
                lead.lost_at = None  # Clear lost_at if status moves away from 'lost'
        if new_priority:
            lead.priority = new_priority
        if new_source is not None and str(new_source).strip():
            lead.source = str(new_source).strip()
        if new_category_id is not None:
            try:
                lead.category_id = int(new_category_id)
            except (ValueError, TypeError):
                pass
        if call_outcome in ('answered', 'callback') or (call_outcome and call_outcome != 'skip'):
            lead.last_contact_date = now
        if next_followup_date:
            try:
                lead.next_followup_date = datetime.fromisoformat(next_followup_date.replace('Z', ''))
            except Exception:
                pass

        # Auto-create follow-up record if next_followup_date provided
        if next_followup_date and not do_not_call:
            try:
                nfd_dt = datetime.fromisoformat(next_followup_date.replace('Z', ''))
                fu = CRMLeadFollowUp(
                    company_id=lead.company_id,
                    lead_id=lead.id,
                    followup_type='call',
                    status='scheduled',
                    scheduled_date=nfd_dt,
                    subject='Dialer follow-up',
                    notes=note or '',
                    outcome=call_outcome or '',
                    handler_type=handler_type,
                    handler_id=handler_id,
                    created_by_type=handler_type,
                    created_by_id=handler_id,
                )
                db.add(fu)
            except Exception as e:
                logger.warning(f"[DC_DIALER] Follow-up creation failed: {e}")

        # DC-DIALER-CALLNOTE-001: Always create a note for every call outcome (not just when text is provided)
        # This ensures call history always appears in the lead's comments section
        if call_outcome and call_outcome != 'skip':
            _note_body = (
                f"[Dialer] {call_outcome}: {note.strip()}"
                if note and note.strip()
                else f"[Dialer] {call_outcome}"
            )
            note_obj = CRMLeadNote(
                company_id=lead.company_id,
                lead_id=lead.id,
                note=_note_body,
                is_private=False,
                created_by_type=handler_type,
                created_by_id=handler_id,
            )
            db.add(note_obj)

        # DC_DIALER_CLIP_ASSIGN: Auto-assign unassigned lead when a followup date is set.
        # The staff member who clips a date takes ownership — lead leaves the floating pool.
        #
        # Two-layer company guard (must pass BOTH):
        #   1. Lead's company_id is within this staff member's accessible companies
        #      (base_company_id + data_companies / signed segments).
        #   2. Lead's category (if set) belongs to the same accessible company set.
        #      SignupCategory.company_id determines which company owns a category.
        #      A staff member from Company A cannot claim a lead categorised for Company B.
        _staff_company_ids = _get_staff_company_ids(current_user) if is_staff else []

        # Category-company guard
        _category_company_ok = True
        if lead.category_id:
            _cat = db.query(SignupCategory).filter(
                SignupCategory.id == lead.category_id
            ).first()
            if _cat and _cat.company_id:
                _category_company_ok = _cat.company_id in _staff_company_ids

        if (
            next_followup_date
            and not do_not_call
            and is_staff
            and lead.handler_type == 'unassigned'
            and lead.company_id in _staff_company_ids
            and _category_company_ok
        ):
            prev_handler_type = lead.handler_type
            prev_handler_id = lead.handler_id
            lead.handler_type = 'staff'
            lead.handler_id = handler_id
            lead.updated_at = now
            assignment_rec = CRMLeadAssignment(
                company_id=lead.company_id,
                lead_id=lead.id,
                from_handler_type=prev_handler_type,
                from_handler_id=prev_handler_id,
                to_handler_type='staff',
                to_handler_id=handler_id,
                reason='Dialer clip-date auto-assign',
                assigned_at=now,
                assigned_by_type='staff',
                assigned_by_id=handler_id,
            )
            db.add(assignment_rec)
            logger.info(
                f"[DC_CLIP_ASSIGN] Lead {lead.id} (company={lead.company_id}, "
                f"cat={lead.category_id}) auto-assigned to {handler_id} via dialer clip-date"
            )

    # DC_DIALER_WS: Emit pg_notify BEFORE commit so notification fires atomically.
    # Uses shared channel 'dialer_events'; user_ref is embedded in the envelope so the
    # single per-worker listener can fan out to the right per-user asyncio Queue.
    import asyncio as _asyncio
    _ws_sync_payload = {"type": "session_sync", "current_index": current_index}
    try:
        db.execute(text("SELECT pg_notify(:ch, :payload)"), {
            "ch": "dialer_events",
            "payload": json.dumps({"user_ref": user_ref, "payload": _ws_sync_payload}),
        })
    except Exception as _ne:
        logger.debug("[DC_DIALER_WS] pg_notify (session_sync) failed: %s", _ne)

    db.commit()

    # Same-worker fast path after commit
    try:
        _loop = _asyncio.get_event_loop()
        if _loop.is_running():
            _loop.create_task(_push_dialer_ws(user_ref, _ws_sync_payload))
    except Exception as _ws_err:
        logger.debug("[DC_DIALER_WS] session_sync push skipped: %s", _ws_err)

    # DC_DIALER_TIMESHEET: Auto-sync activity chip + lead update time to staff timesheet
    if is_staff and hasattr(current_user, 'id'):
        try:
            entry_date = now.date()
            lead_name = lead.name if lead else f"Lead #{lead_id}"
            if activity_type and activity_minutes and int(activity_minutes) > 0:
                auto_upsert_timesheet_entry(
                    db=db,
                    employee_id=current_user.id,
                    entry_date=entry_date,
                    time_spent_minutes=int(activity_minutes),
                    entry_type='lead',
                    auto_source='dialer',
                    comments=f"[Dialer] {activity_type} — {lead_name}",
                    created_by=current_user.id,
                )
            if lead_update_minutes and int(lead_update_minutes) > 0:
                auto_upsert_timesheet_entry(
                    db=db,
                    employee_id=current_user.id,
                    entry_date=entry_date,
                    time_spent_minutes=int(lead_update_minutes),
                    entry_type='lead',
                    auto_source='dialer_update',
                    comments=f"[Dialer] Lead update — {lead_name}",
                    created_by=current_user.id,
                )
        except Exception as ts_err:
            logger.warning(f"[DC_DIALER_TS] Timesheet sync failed for emp={current_user.id}: {ts_err}")

    return {
        "success": True,
        "attempt_id": attempt_id,
        "lead_updated": lead is not None,
        "do_not_call_set": do_not_call,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/analytics")
async def get_dialer_analytics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_008: Executive dialer analytics.
    Managers see downline data. Team members see own data only.
    Includes: sessions, dials, outcomes, leads updated, DNC counts, per-user breakdown.
    period: 'today' | 'week' | 'month' — shorthand; overrides date_from/date_to.
    """
    is_staff = hasattr(current_user, 'emp_code')
    portal = 'staff' if is_staff else 'mnr'
    now = get_ist_now()

    # Resolve period shorthand
    if period == 'week':
        date_from = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        date_to = now.isoformat()
    elif period == 'month':
        date_from = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        date_to = now.isoformat()
    elif period == 'today' or not date_from:
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        date_to = now.isoformat()

    # Default range: today
    if not date_to:
        date_to = now.isoformat()

    try:
        dt_from = datetime.fromisoformat(date_from)
        dt_to = datetime.fromisoformat(date_to)
    except Exception:
        dt_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        dt_to = now

    # Determine which user_refs to include
    # DC Protocol (Mar 25, 2026): track is_manager for frontend tab gating
    is_manager = False
    if is_staff:
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        role_code = (staff.role.role_code if staff and staff.role else '').lower()

        if role_code in DIALER_FULL_ACCESS:
            # Full org visibility
            user_refs = None  # No filter
            is_manager = True
        elif staff:
            downline_ids = get_recursive_downline(staff.id, db, StaffEmployee, include_manager=True)
            user_refs = [str(i) for i in downline_ids]
            # Manager if they have at least one person reporting to them (downline > self)
            is_manager = len(downline_ids) > 1
        else:
            user_refs = [str(current_user.id)]
    else:
        user_refs = [str(current_user.id)]

    # Build attempt query
    attempt_filter = "WHERE a.created_at BETWEEN :df AND :dt"
    params: dict = {"df": dt_from, "dt": dt_to, "portal": portal}

    if user_refs is not None:
        attempt_filter += " AND a.user_ref = ANY(:refs)"
        params["refs"] = user_refs
    if company_id:
        attempt_filter += " AND s.company_id = :company_id"
        params["company_id"] = company_id

    # Overall stats
    overall = db.execute(text(f"""
        SELECT
            COUNT(*) as total_dials,
            COUNT(CASE WHEN a.call_outcome = 'answered' THEN 1 END) as answered,
            COUNT(CASE WHEN a.call_outcome = 'no_answer' THEN 1 END) as no_answer,
            COUNT(CASE WHEN a.call_outcome = 'busy' THEN 1 END) as busy,
            COUNT(CASE WHEN a.call_outcome = 'callback' THEN 1 END) as callback,
            COUNT(CASE WHEN a.call_outcome = 'skip' THEN 1 END) as skipped,
            COUNT(CASE WHEN a.status_updated_to = 'do_not_call' THEN 1 END) as do_not_call,
            COUNT(CASE WHEN a.status_updated_to IS NOT NULL AND a.status_updated_to != '' THEN 1 END) as leads_updated,
            COALESCE(AVG(NULLIF(a.duration_seconds, 0)), 0) as avg_duration,
            COALESCE(SUM(a.duration_seconds), 0) as total_talk_seconds,
            COUNT(DISTINCT a.user_ref) as active_users,
            COUNT(DISTINCT s.id) as total_sessions
        FROM crm_dialer_attempts a
        LEFT JOIN crm_dialer_sessions s ON s.id = a.session_id
        {attempt_filter}
    """), params).fetchone()

    # Per-user breakdown
    per_user = db.execute(text(f"""
        SELECT
            a.user_ref,
            a.portal,
            COUNT(*) as total_dials,
            COUNT(CASE WHEN a.call_outcome = 'answered' THEN 1 END) as answered,
            COUNT(CASE WHEN a.call_outcome = 'no_answer' THEN 1 END) as no_answer,
            COUNT(CASE WHEN a.call_outcome = 'busy' THEN 1 END) as busy,
            COUNT(CASE WHEN a.call_outcome = 'skip' THEN 1 END) as skipped,
            COUNT(CASE WHEN a.status_updated_to = 'do_not_call' THEN 1 END) as do_not_call,
            COUNT(CASE WHEN a.status_updated_to IS NOT NULL AND a.status_updated_to != '' THEN 1 END) as leads_updated,
            COALESCE(SUM(a.duration_seconds), 0) as total_talk_seconds,
            MAX(a.created_at) as last_activity
        FROM crm_dialer_attempts a
        LEFT JOIN crm_dialer_sessions s ON s.id = a.session_id
        {attempt_filter}
        GROUP BY a.user_ref, a.portal
        ORDER BY total_dials DESC
    """), params).fetchall()

    # Enrich per-user with names
    per_user_list = []
    for row in per_user:
        d = dict(zip(row._mapping.keys(), row))
        if d['portal'] == 'staff':
            emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == d['user_ref']).first()
            if not emp:
                emp = db.query(StaffEmployee).filter(StaffEmployee.id == d['user_ref']).first()
            if emp:
                d['name'] = emp.full_name
                d['emp_code'] = emp.emp_code
                d['_staff_id'] = emp.id
                dept = emp.department
                d['department'] = dept.name if dept else None
            else:
                d['name'] = d['user_ref']
                d['_staff_id'] = None
        else:
            user = db.query(User).filter(User.id == d['user_ref']).first()
            d['name'] = user.name if user else d['user_ref']
            d['_staff_id'] = None
        if isinstance(d.get('last_activity'), datetime):
            d['last_activity'] = d['last_activity'].isoformat()
        per_user_list.append(d)

    # DC Protocol (Apr 2026): Enrich per_user with VGK Created + WA Shares
    try:
        valid_staff_ids = [u['_staff_id'] for u in per_user_list if u.get('_staff_id')]
        if valid_staff_ids:
            vgk_rows = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type='vgk_registration' "
                "AND created_at BETWEEN :df AND :dt GROUP BY staff_id"
            ), {"ids": valid_staff_ids, "df": dt_from, "dt": dt_to}).fetchall()
            wa_rows = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type='vgk_creds' "
                "AND created_at BETWEEN :df AND :dt GROUP BY staff_id"
            ), {"ids": valid_staff_ids, "df": dt_from, "dt": dt_to}).fetchall()
            vgk_map = {r[0]: int(r[1]) for r in vgk_rows}
            wa_map = {r[0]: int(r[1]) for r in wa_rows}
            for u in per_user_list:
                sid = u.get('_staff_id')
                u['vgk_created'] = vgk_map.get(sid, 0) if sid else 0
                u['wa_shares'] = wa_map.get(sid, 0) if sid else 0
        else:
            for u in per_user_list:
                u['vgk_created'] = 0
                u['wa_shares'] = 0
    except Exception:
        for u in per_user_list:
            u.setdefault('vgk_created', 0)
            u.setdefault('wa_shares', 0)
    # Clean up internal key before returning
    for u in per_user_list:
        u.pop('_staff_id', None)

    # Active sessions right now
    active_sessions_count = db.execute(text("""
        SELECT COUNT(*) FROM crm_dialer_sessions WHERE status = 'active'
    """)).scalar() or 0

    # DNC leads count
    dnc_count = db.execute(text("""
        SELECT COUNT(*) FROM crm_leads WHERE status = 'do_not_call'
    """)).scalar() or 0

    # Recent dialer attempts (last 50) with lead info
    recent_rows = db.execute(text(f"""
        SELECT a.id, a.lead_id, l.name as lead_name, l.phone as lead_phone,
               a.call_outcome, a.duration_seconds, a.status_updated_to,
               a.note, a.dialed_at, a.user_ref
        FROM crm_dialer_attempts a
        LEFT JOIN crm_leads l ON l.id = a.lead_id
        LEFT JOIN crm_dialer_sessions s ON s.id = a.session_id
        {attempt_filter}
        ORDER BY a.dialed_at DESC NULLS LAST
        LIMIT 50
    """), params).fetchall()
    recent_attempts = []
    for r in recent_rows:
        dialed_at_val = r[8]
        recent_attempts.append({
            "id": r[0],
            "lead_id": r[1],
            "lead_name": r[2] or f"Lead #{r[1]}",
            "lead_phone": r[3] or "",
            "call_outcome": r[4] or "",
            "duration_seconds": int(r[5] or 0),
            "status_updated_to": r[6] or "",
            "note": r[7] or "",
            "dialed_at": dialed_at_val.isoformat() if dialed_at_val else None,
            "user_ref": r[9] or "",
        })

    # DC_DIALER_ANALYTICS: Hourly calling pattern (IST)
    hourly_params = dict(params)
    hourly_rows = db.execute(text(f"""
        SELECT
            EXTRACT(HOUR FROM (a.dialed_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')) as hour,
            COUNT(*) as dials,
            COUNT(CASE WHEN a.call_outcome = 'answered' THEN 1 END) as answered
        FROM crm_dialer_attempts a
        LEFT JOIN crm_dialer_sessions s ON s.id = a.session_id
        {attempt_filter}
        GROUP BY 1
        ORDER BY 1
    """), hourly_params).fetchall()
    hourly_pattern = [
        {"hour": int(r[0]), "dials": int(r[1]), "answered": int(r[2])}
        for r in hourly_rows
    ]

    # DC_DIALER_ANALYTICS: Break analysis from session pause data
    break_base = "WHERE s.started_at BETWEEN :df AND :dt"
    break_params: dict = {"df": dt_from, "dt": dt_to}
    if user_refs is not None:
        break_base += " AND s.user_ref = ANY(:refs)"
        break_params["refs"] = user_refs
    if company_id:
        break_base += " AND s.company_id = :company_id"
        break_params["company_id"] = company_id

    break_rows = db.execute(text(f"""
        SELECT
            s.user_ref,
            COUNT(s.id) as session_count,
            COUNT(CASE WHEN s.paused_at IS NOT NULL THEN 1 END) as break_count,
            COALESCE(SUM(
                CASE WHEN s.paused_at IS NOT NULL
                THEN GREATEST(0, EXTRACT(EPOCH FROM (
                    COALESCE(s.last_active_at, s.closed_at, NOW()::timestamp) - s.paused_at
                )) / 60)
                ELSE 0 END
            ), 0)::int as total_break_minutes,
            COALESCE(SUM(
                EXTRACT(EPOCH FROM (
                    COALESCE(s.closed_at, s.last_active_at, NOW()::timestamp) - s.started_at
                )) / 60
            ), 0)::int as total_session_minutes
        FROM crm_dialer_sessions s
        {break_base}
        GROUP BY s.user_ref
        ORDER BY total_break_minutes DESC
    """), break_params).fetchall()

    break_list = []
    for row in break_rows:
        d = dict(zip(row._mapping.keys(), row))
        if d.get('portal') == 'staff' or True:
            emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == d['user_ref']).first()
            if not emp:
                emp = db.query(StaffEmployee).filter(StaffEmployee.id == d['user_ref']).first()
            d['name'] = emp.full_name if emp else d['user_ref']
        break_list.append(d)

    # DC_DIALER_ANALYTICS: Activity analysis from timesheet (auto_source=dialer)
    act_date_params: dict = {
        "df_date": dt_from.date() if hasattr(dt_from, 'date') else dt_from,
        "dt_date": dt_to.date() if hasattr(dt_to, 'date') else dt_to
    }
    if user_refs is not None:
        act_date_params["refs"] = user_refs

    act_filter_clause = ""
    if user_refs is not None:
        act_filter_clause = " AND te.employee_id::text = ANY(:refs)"

    activity_rows = db.execute(text(f"""
        SELECT
            CASE
                WHEN te.comments LIKE '[Dialer] %% — %%'
                THEN SPLIT_PART(SPLIT_PART(te.comments, '[Dialer] ', 2), ' — ', 1)
                WHEN te.auto_source = 'dialer_update' THEN 'Lead Update Time'
                ELSE 'Other'
            END as activity_type,
            SUM(te.duration_minutes) as total_minutes,
            COUNT(*) as entry_count
        FROM staff_timesheet_entries te
        WHERE te.auto_source IN ('dialer', 'dialer_update')
          AND te.date BETWEEN :df_date AND :dt_date
          {act_filter_clause}
        GROUP BY 1
        ORDER BY total_minutes DESC
    """), act_date_params).fetchall()

    activity_analysis = [
        {
            "activity_type": r[0] or "Other",
            "total_minutes": int(r[1] or 0),
            "entry_count": int(r[2] or 0)
        }
        for r in activity_rows
    ]

    # DC_DIALER_ANALYTICS: Session duration stats
    sess_stats = db.execute(text(f"""
        SELECT
            COALESCE(AVG(
                EXTRACT(EPOCH FROM (COALESCE(closed_at, last_active_at, NOW()::timestamp) - started_at)) / 60
            ), 0)::int as avg_session_minutes,
            COALESCE(MAX(
                EXTRACT(EPOCH FROM (COALESCE(closed_at, last_active_at, NOW()::timestamp) - started_at)) / 60
            ), 0)::int as max_session_minutes,
            COUNT(*) as total_sessions_period,
            COALESCE(SUM(
                EXTRACT(EPOCH FROM (COALESCE(closed_at, last_active_at, NOW()::timestamp) - started_at))
            ), 0)::int as total_session_seconds
        FROM crm_dialer_sessions s
        {break_base}
    """), break_params).fetchone()

    def _v(row, col, default=0):
        try:
            return getattr(row, col) or default
        except Exception:
            return default

    return {
        "success": True,
        "is_manager": is_manager,
        "period": {"from": date_from, "to": date_to},
        "overview": {
            "total_dials": _v(overall, 'total_dials'),
            "answered": _v(overall, 'answered'),
            "no_answer": _v(overall, 'no_answer'),
            "busy": _v(overall, 'busy'),
            "callback": _v(overall, 'callback'),
            "skipped": _v(overall, 'skipped'),
            "do_not_call": _v(overall, 'do_not_call'),
            "leads_updated": _v(overall, 'leads_updated'),
            "avg_duration_seconds": round(float(_v(overall, 'avg_duration', 0)), 1),
            "total_talk_seconds": int(_v(overall, 'total_talk_seconds')),
            "active_users": _v(overall, 'active_users'),
            "total_sessions": _v(overall, 'total_sessions'),
            "active_sessions_now": active_sessions_count,
            "dnc_leads_total": dnc_count,
            "total_session_seconds": int(sess_stats[3] or 0) if sess_stats else 0,
        },
        "per_user": per_user_list,
        "recent_attempts": recent_attempts,
        "hourly_pattern": hourly_pattern,
        "break_analysis": break_list,
        "activity_analysis": activity_analysis,
        "session_stats": {
            "avg_session_minutes": int(sess_stats[0] or 0) if sess_stats else 0,
            "max_session_minutes": int(sess_stats[1] or 0) if sess_stats else 0,
            "total_sessions_period": int(sess_stats[2] or 0) if sess_stats else 0,
            "total_session_seconds": int(sess_stats[3] or 0) if sess_stats else 0,
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# DO-NOT-CALL STATUS MANAGEMENT (Manager Override)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/dialer/lead/{lead_id}/dnc")
async def toggle_do_not_call(
    lead_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_009: Manager sets/clears do_not_call status on a lead.
    remove=True restores lead to previous status (or 'new' if unknown).
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    remove = body.get('remove', False)
    restore_status = body.get('restore_status', 'new')

    if remove:
        lead.status = restore_status
        action = f"restored to {restore_status}"
    else:
        lead.status = 'do_not_call'
        action = "marked do_not_call"

    db.commit()
    return {"success": True, "lead_id": lead_id, "action": action, "new_status": lead.status}


# ──────────────────────────────────────────────────────────────────────────────
# QUICK SEARCH — Override dial by name or phone
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/dialer/search")
async def dialer_search(
    q: str = Query(..., min_length=2),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_DIALER_010: Quick search leads AND contacts by name or phone for override dial.
    Leads: scoped to user's accessible CRM leads, with dialed_today flag.
    Contacts: unique entries from user's staff_call_logs (phone history).
    Leads are shown first; contacts deduplicated against lead phone numbers.
    """
    q_clean = q.strip()
    term = f"%{q_clean}%"
    ist_today = get_ist_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Leads ─────────────────────────────────────────────────────────────────
    if hasattr(current_user, 'emp_code'):
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        # DC_QUEUE_COMPANY_FIX: Search across all companies the staff member has access to
        search_company_ids = _get_staff_company_ids(staff, company_id)
        user_ref = str(staff.id)
        staff_id = staff.id
        _search_now = get_ist_now()
        leads = db.query(CRMLead).filter(
            CRMLead.company_id.in_(search_company_ids),
            _dialer_active_filter(_search_now),
            or_(
                CRMLead.name.ilike(term),
                CRMLead.phone.ilike(term),
                CRMLead.alternate_phone.ilike(term),
            )
        ).order_by(CRMLead.name).limit(12).all()
    else:
        user_ref = str(current_user.id)
        staff_id = None
        company_ids = _get_mnr_company_ids(current_user, db)
        if not company_ids:
            return {"success": True, "results": []}
        _search_now = get_ist_now()
        leads = db.query(CRMLead).filter(
            CRMLead.company_id.in_(company_ids),
            _dialer_active_filter(_search_now),
            or_(
                CRMLead.name.ilike(term),
                CRMLead.phone.ilike(term),
                CRMLead.alternate_phone.ilike(term),
            )
        ).order_by(CRMLead.name).limit(12).all()

    # Check which leads were already dialed today
    lead_ids = [l.id for l in leads]
    dialed_today: set = set()
    if lead_ids:
        dialed_rows = db.execute(text("""
            SELECT DISTINCT lead_id FROM crm_dialer_attempts
            WHERE user_ref = :ref AND call_outcome != 'skip'
            AND dialed_at >= :today AND lead_id = ANY(:ids)
        """), {"ref": user_ref, "today": ist_today, "ids": lead_ids}).fetchall()
        dialed_today = {r[0] for r in dialed_rows}

    # DC_CATEGORY_NAME_FIX: Resolve category names for search results
    search_cat_map = _build_category_map(leads, db)

    results = [
        {
            "source": "lead",
            "lead_id": l.id,
            "name": l.name or "—",
            "phone": l.phone or "",
            "alternate_phone": l.alternate_phone or "",
            "status": l.status or "new",
            "city": l.city or "",
            "area": l.area or "",
            "category_id": l.category_id,
            "category_name": search_cat_map.get(l.category_id) if l.category_id else None,
            "dialed_today": l.id in dialed_today,
        }
        for l in leads
    ]

    # ── Contacts from call log ─────────────────────────────────────────────────
    # Collect phone numbers already covered by leads to avoid duplicates
    lead_phones: set = set()
    for l in leads:
        if l.phone:
            lead_phones.add(l.phone.strip().replace(" ", ""))
        if l.alternate_phone:
            lead_phones.add(l.alternate_phone.strip().replace(" ", ""))

    if staff_id:
        contact_rows = db.execute(text("""
            SELECT DISTINCT ON (phone_number)
                phone_number, contact_name, matched_lead_id,
                MAX(call_datetime) OVER (PARTITION BY phone_number) AS last_called
            FROM staff_call_logs
            WHERE staff_id = :sid
              AND (contact_name ILIKE :term OR phone_number ILIKE :term)
              AND contact_name IS NOT NULL
              AND phone_number IS NOT NULL
            ORDER BY phone_number, call_datetime DESC
            LIMIT 10
        """), {"sid": staff_id, "term": term}).fetchall()

        for row in contact_rows:
            ph = (row[0] or "").strip().replace(" ", "")
            if ph in lead_phones:
                continue  # already shown as a lead
            results.append({
                "source": "contact",
                "lead_id": row[2],  # matched_lead_id — may be None
                "name": row[1] or ph,
                "phone": row[0] or "",
                "alternate_phone": "",
                "status": "",
                "city": "",
                "area": "",
                "dialed_today": False,
            })

    return {"success": True, "results": results}


@router.get("/dialer/recent-calls")
async def get_recent_calls(
    limit: int = Query(15, le=30),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_RECENT_001: Last N unique phone numbers from all call sources:
    - crm_dialer_attempts (CRM leads dialed via Auto Dialer)
    - staff_call_logs (INCOMING, MISSED, OUTGOING, REJECTED — native call log)
    Merged, deduped by phone, sorted by most recent. Staff only.
    """
    staff_id = None
    user_ref = None
    if hasattr(current_user, 'emp_code'):
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")
        staff_id = staff.id
        user_ref = str(staff.id)
    else:
        user_ref = str(current_user.id)

    results: list = []
    seen_phones: set = set()

    # ── Source 1: CRM dialer attempts ─────────────────────────────────────────
    if user_ref:
        dial_rows = db.execute(text("""
            SELECT DISTINCT ON (l.phone)
                a.lead_id, l.name, l.phone, l.alternate_phone, l.status,
                a.call_outcome, a.dialed_at, 0 AS duration_seconds
            FROM crm_dialer_attempts a
            JOIN crm_leads l ON a.lead_id = l.id
            WHERE a.user_ref = :ref AND a.call_outcome != 'skip'
            ORDER BY l.phone, a.dialed_at DESC
            LIMIT 30
        """), {"ref": user_ref}).fetchall()

        for r in sorted(dial_rows, key=lambda x: str(x[6] or ''), reverse=True):
            ph = (r[2] or "").strip().replace(" ", "").lstrip("+91")
            if ph and ph not in seen_phones:
                seen_phones.add(ph)
                results.append({
                    "lead_id": r[0], "name": r[1] or "Unknown",
                    "phone": r[2] or "", "status": r[4] or "",
                    "call_type": "OUTGOING", "call_outcome": r[5] or "",
                    "duration_seconds": 0,
                    "dialed_at": r[6].isoformat() if r[6] else None,
                    "source": "dialer",
                })

    # ── Source 2: Native call log (staff_call_logs) ────────────────────────────
    if staff_id:
        log_rows = db.execute(text("""
            SELECT DISTINCT ON (phone_number)
                matched_lead_id, contact_name, phone_number, call_type,
                call_datetime, duration_seconds
            FROM staff_call_logs
            WHERE staff_id = :sid
            ORDER BY phone_number, call_datetime DESC
            LIMIT 40
        """), {"sid": staff_id}).fetchall()

        for r in sorted(log_rows, key=lambda x: str(x[4] or ''), reverse=True):
            ph = (r[2] or "").strip().replace(" ", "").lstrip("+91")
            if ph and ph not in seen_phones:
                seen_phones.add(ph)
                results.append({
                    "lead_id": r[0], "name": r[1] or "",
                    "phone": r[2] or "", "status": "",
                    "call_type": r[3] or "OUTGOING", "call_outcome": "",
                    "duration_seconds": r[5] or 0,
                    "dialed_at": r[4].isoformat() if r[4] else None,
                    "source": "native",
                })

    results.sort(key=lambda x: x["dialed_at"] or "", reverse=True)
    return {"success": True, "results": results[:limit]}


@router.get("/dialer/call-history")
async def get_call_history(
    call_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_CALLHIST_001: Full paginated call history from staff_call_logs + dialer attempts.
    call_type filter: INCOMING | OUTGOING | MISSED | REJECTED | DIALER (empty = all)
    """
    staff_id = None
    user_ref = None
    if hasattr(current_user, 'emp_code'):
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")
        staff_id = staff.id
        user_ref = str(staff.id)
    else:
        user_ref = str(current_user.id)

    offset = (page - 1) * per_page
    entries: list = []

    if call_type == "DIALER":
        # Only CRM dialer attempts
        if user_ref:
            rows = db.execute(text("""
                SELECT a.lead_id, l.name, l.phone, 'OUTGOING' AS call_type,
                       a.dialed_at, 0 AS duration_seconds, a.call_outcome,
                       NULL AS contact_name
                FROM crm_dialer_attempts a
                JOIN crm_leads l ON a.lead_id = l.id
                WHERE a.user_ref = :ref AND a.call_outcome != 'skip'
                ORDER BY a.dialed_at DESC
                LIMIT :lim OFFSET :off
            """), {"ref": user_ref, "lim": per_page, "off": offset}).fetchall()
            for r in rows:
                entries.append({
                    "lead_id": r[0], "name": r[1] or "", "phone": r[2] or "",
                    "call_type": "OUTGOING", "dialed_at": r[4].isoformat() if r[4] else None,
                    "duration_seconds": 0, "call_outcome": r[6] or "",
                    "contact_name": r[1] or "", "source": "dialer",
                })
    else:
        # Native call log
        if staff_id:
            type_filter = ""
            if call_type and call_type in ("INCOMING", "MISSED", "OUTGOING", "REJECTED"):
                type_filter = "AND call_type = :ctype"
            rows = db.execute(text(f"""
                SELECT matched_lead_id, NULL AS name, phone_number, call_type,
                       call_datetime, duration_seconds, NULL AS call_outcome,
                       contact_name
                FROM staff_call_logs
                WHERE staff_id = :sid {type_filter}
                ORDER BY call_datetime DESC
                LIMIT :lim OFFSET :off
            """), {"sid": staff_id, "ctype": call_type or "", "lim": per_page, "off": offset}).fetchall()
            for r in rows:
                entries.append({
                    "lead_id": r[0], "name": r[7] or "", "phone": r[2] or "",
                    "call_type": r[3] or "OUTGOING",
                    "dialed_at": r[4].isoformat() if r[4] else None,
                    "duration_seconds": r[5] or 0, "call_outcome": "",
                    "contact_name": r[7] or "", "source": "native",
                })

    return {"success": True, "entries": entries, "page": page, "per_page": per_page}


# ── DC_ACTIVE_CALL: Mobile dial-in-progress sync ──────────────────────────────

@router.post("/dialer/call/active")
async def set_active_call(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_ACTIVE_CALL_001: Mobile sets active_lead_id when it starts dialing.
    Send lead_id=null to clear (call ended / popup opened).
    """
    lead_id = body.get("lead_id")  # None = clear
    user_ref = str(current_user.id)

    if lead_id is not None:
        db.execute(text("""
            UPDATE crm_dialer_sessions
            SET active_lead_id = :lid, call_started_at = NOW()
            WHERE user_ref = :ref AND status = 'active'
        """), {"lid": int(lead_id), "ref": user_ref})
    else:
        db.execute(text("""
            UPDATE crm_dialer_sessions
            SET active_lead_id = NULL, call_started_at = NULL
            WHERE user_ref = :ref AND status = 'active'
        """), {"ref": user_ref})

    # DC_DIALER_WS: Build ws_payload and emit pg_notify BEFORE commit so the
    # notification fires atomically with the state change (cross-worker delivery).
    import asyncio as _asyncio
    if lead_id is not None:
        lead_row = db.execute(text(
            "SELECT id, name, phone, status, city, company_id FROM crm_leads WHERE id = :lid"
        ), {"lid": int(lead_id)}).fetchone()
        if lead_row:
            ws_payload = {
                "type": "call_state",
                "active": True,
                "lead_id": lead_row[0],
                "lead_name": lead_row[1] or "—",
                "lead_phone": lead_row[2] or "",
                "lead_status": lead_row[3] or "new",
                "lead_city": lead_row[4] or "",
                "company_id": lead_row[5],
                "call_started_at": None,
            }
        else:
            ws_payload = {"type": "call_state", "active": True, "lead_id": int(lead_id)}
    else:
        ws_payload = {"type": "call_state", "active": False}

    # Emit pg_notify in-transaction so it fires on the commit below.
    # Uses shared channel 'dialer_events'; user_ref embedded in envelope for fan-out.
    try:
        db.execute(text("SELECT pg_notify(:ch, :payload)"), {
            "ch": "dialer_events",
            "payload": json.dumps({"user_ref": user_ref, "payload": ws_payload}),
        })
    except Exception as _ne:
        logger.debug("[DC_DIALER_WS] pg_notify (call_state) failed: %s", _ne)

    db.commit()

    # Same-worker fast path: enqueue directly into the in-process registry
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_push_dialer_ws(user_ref, ws_payload))
    except Exception as _ws_err:
        logger.debug("[DC_DIALER_WS] same-worker push skipped: %s", _ws_err)

    return {"success": True}


@router.get("/dialer/leads/limbo")
async def get_limbo_leads(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_LIMBO_001: Admin helper — list leads with handler_type='staff' and empty handler_id.
    These leads are invisible to all dialer queues and must be fixed.
    Returns count + lead list, optionally filtered by company_id.
    """
    is_staff = hasattr(current_user, 'emp_code')
    if not is_staff:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Only full-access roles may view limbo leads across org
    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    role_code = (staff.role.role_code if staff and staff.role else '').lower()
    if role_code not in DIALER_FULL_ACCESS:
        raise HTTPException(status_code=403, detail="Insufficient permissions — full-access role required")

    base_filter = "WHERE handler_type = 'staff' AND (handler_id IS NULL OR TRIM(handler_id) = '')"
    params: dict = {}
    if company_id:
        base_filter += " AND company_id = :company_id"
        params["company_id"] = company_id

    count_row = db.execute(text(f"SELECT COUNT(*) FROM crm_leads {base_filter}"), params).scalar()

    rows = db.execute(text(f"""
        SELECT id, name, phone, status, company_id, handler_type, handler_id, created_at
        FROM crm_leads {base_filter}
        ORDER BY created_at DESC
        LIMIT 500
    """), params).fetchall()

    leads = []
    for r in rows:
        leads.append({
            "id": r[0],
            "name": r[1],
            "phone": r[2] or "",
            "status": r[3],
            "company_id": r[4],
            "handler_type": r[5],
            "handler_id": r[6],
            "created_at": r[7].isoformat() if r[7] else None,
        })

    return {
        "success": True,
        "limbo_count": count_row or 0,
        "leads": leads,
        "note": "These leads have handler_type='staff' but no handler_id. They are invisible to all dialer queues. Fix by setting handler_type='unassigned' or assigning a valid emp_code as handler_id."
    }


@router.post("/dialer/leads/limbo/fix")
async def fix_limbo_leads(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_LIMBO_002: Admin tool — convert all limbo leads (handler_type='staff', empty handler_id)
    to handler_type='unassigned' so they appear in the secondary dialer pool.
    Accepts optional company_id to scope the fix to one company.
    """
    is_staff = hasattr(current_user, 'emp_code')
    if not is_staff:
        raise HTTPException(status_code=403, detail="Admin access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    role_code = (staff.role.role_code if staff and staff.role else '').lower()
    if role_code not in DIALER_FULL_ACCESS:
        raise HTTPException(status_code=403, detail="Insufficient permissions — full-access role required")

    company_id = body.get("company_id")
    base_filter = "WHERE handler_type = 'staff' AND (handler_id IS NULL OR TRIM(handler_id) = '')"
    params: dict = {}
    if company_id:
        base_filter += " AND company_id = :company_id"
        params["company_id"] = int(company_id)

    result = db.execute(text(f"""
        UPDATE crm_leads
        SET handler_type = 'unassigned', handler_id = NULL
        {base_filter}
        RETURNING id
    """), params)
    updated_ids = [r[0] for r in result.fetchall()]
    db.commit()

    logger.info(f"[DC_LIMBO] Admin {current_user.id} fixed {len(updated_ids)} limbo leads" +
                (f" in company {company_id}" if company_id else " across all companies"))

    return {
        "success": True,
        "fixed_count": len(updated_ids),
        "fixed_lead_ids": updated_ids,
        "message": f"{len(updated_ids)} limbo leads converted to handler_type='unassigned'."
    }


@router.post("/dialer/click-to-call")
async def initiate_click_to_call(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_MYOP_CTC: Initiate an outgoing call via MyOperator Click-to-Call API.
    MyOperator calls the agent's phone first, then bridges to the customer.
    No tel: redirect — the call is handled server-side through MyOperator's platform.
    Returns: { success, call_id } so the mobile can poll for call-end via webhook.
    """
    customer_phone = body.get('customer_phone', '')
    lead_id = body.get('lead_id')

    agent_phone_raw = getattr(current_user, 'phone', None) or ''
    if not agent_phone_raw:
        raise HTTPException(status_code=400, detail="Agent phone number not set in your staff profile. Please ask an admin to add it.")

    customer_norm = _normalize_phone_for_ctc(customer_phone)
    agent_norm = _normalize_phone_for_ctc(agent_phone_raw)

    if len(customer_norm) != 10:
        raise HTTPException(status_code=400, detail=f"Invalid customer phone number: {customer_phone}")
    if len(agent_norm) != 10:
        raise HTTPException(status_code=400, detail=f"Invalid agent phone number in profile: {agent_phone_raw}")

    if not _MYOP_X_API_KEY:
        logger.error('[DC_MYOP_CTC] MYOPERATOR_X_API_KEY not configured')
        raise HTTPException(status_code=503, detail="MyOperator API not configured on server")

    if not _MYOP_SECRET_TOKEN:
        logger.error('[DC_MYOP_CTC] MYOPERATOR_WEBHOOK_SECRET not configured')
        raise HTTPException(status_code=503, detail="MyOperator secret token not configured on server")

    if not _MYOP_PUBLIC_IVR_ID:
        logger.error('[DC_MYOP_CTC] MYOPERATOR_PUBLIC_IVR_ID not configured')
        raise HTTPException(
            status_code=503,
            detail="MyOperator Public IVR ID not configured. Please set MYOPERATOR_PUBLIC_IVR_ID in environment variables (found in MyOperator Campaign Dashboard)."
        )

    # Look up agent's MyOperator user_id by their phone number
    import uuid as uuid_mod
    myop_user_id = _get_myop_user_id(agent_norm)
    if not myop_user_id:
        logger.error('[DC_MYOP_CTC] No MyOperator user_id found for agent phone %s. Known agents: %s', agent_norm, list(_myop_user_cache.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Agent phone {agent_norm} not found in MyOperator. Ensure the agent's phone number in their staff profile matches their MyOperator account."
        )

    # E.164 format for customer number
    customer_e164 = f'+91{customer_norm}'
    reference_id = f'ctc_{lead_id or "x"}_{str(uuid_mod.uuid4())[:8]}'

    payload = {
        'company_id': _MYOP_API_COMPANY_ID,
        'secret_token': _MYOP_SECRET_TOKEN,
        'type': '1',
        'user_id': myop_user_id,
        'number': customer_e164,
        'public_ivr_id': _MYOP_PUBLIC_IVR_ID,
        'reference_id': reference_id,
    }
    headers = {
        'x-api-key': _MYOP_X_API_KEY,
        'Content-Type': 'application/json',
    }

    try:
        resp = _http.post(
            _MYOP_OBD_URL,
            json=payload,
            headers=headers,
            timeout=15
        )
        try:
            result = resp.json()
        except Exception:
            logger.error('[DC_MYOP_CTC] Non-JSON response (%s): %s', resp.status_code, resp.text[:300])
            raise HTTPException(status_code=502, detail="MyOperator returned an unexpected response")
    except HTTPException:
        raise
    except Exception as e:
        logger.error('[DC_MYOP_CTC] Request failed: %s', e)
        raise HTTPException(status_code=502, detail="Unable to reach MyOperator. Check your connection and try again.")

    # OBD API uses different status field conventions
    status_val = str(result.get('status', '')).lower()
    code_val = str(result.get('code', ''))
    if status_val == 'error' or (code_val and code_val not in ('200', '201', '202')):
        msg = result.get('details') or result.get('message') or result.get('error') or 'MyOperator API error'
        logger.warning('[DC_MYOP_CTC] API returned error: %s | user_id=%s customer=%s ref=%s', result, myop_user_id, customer_e164, reference_id)
        raise HTTPException(status_code=502, detail=f"MyOperator: {msg}")

    # Extract call/unique ID from response
    call_id = str(
        result.get('unique_id') or result.get('call_id') or
        result.get('uuid') or result.get('session_id') or reference_id
    )
    logger.info('[DC_MYOP_CTC] Call initiated: user_id=%s customer=%s call_id=%s ref=%s', myop_user_id, customer_e164, call_id, reference_id)

    return {
        'success': True,
        'call_id': call_id,
        'agent_number': agent_norm,
        'customer_number': customer_norm,
        'message': result.get('message', 'Call initiated — your phone will ring shortly'),
    }


@router.get("/dialer/click-to-call/status/{call_id}")
async def get_click_to_call_status(
    call_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_MYOP_CTC: Poll the status of a Click-to-Call initiated via MyOperator.
    Mobile polls this every 3s to detect call end (webhook updates operator_calls table).
    Status values: pending | ringing | active | answered | ended | missed
    """
    call = db.query(OperatorCall).filter(OperatorCall.call_id == call_id).first()
    if not call:
        return {
            'found': False,
            'status': 'pending',
            'duration_seconds': 0,
            'recording_url': None,
            'started_at': None,
            'ended_at': None,
        }
    return {
        'found': True,
        'status': call.status,
        'duration_seconds': call.duration_seconds or 0,
        'recording_url': call.recording_url,
        'started_at': call.started_at.isoformat() if call.started_at else None,
        'ended_at': call.ended_at.isoformat() if call.ended_at else None,
    }


@router.get("/dialer/active-call")
async def get_active_call(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_ACTIVE_CALL_002: Web polls this to detect if the employee is dialing on mobile.
    Returns lead_id + basic lead info when an active mobile call is in progress.
    Stale calls (>10 min old) are automatically cleared.
    """
    user_ref = str(current_user.id)

    # Auto-clear stale active calls (>10 min)
    db.execute(text("""
        UPDATE crm_dialer_sessions
        SET active_lead_id = NULL, call_started_at = NULL
        WHERE user_ref = :ref
          AND active_lead_id IS NOT NULL
          AND call_started_at < NOW() - INTERVAL '10 minutes'
    """), {"ref": user_ref})
    db.commit()

    row = db.execute(text("""
        SELECT s.active_lead_id, s.call_started_at
        FROM crm_dialer_sessions s
        WHERE s.user_ref = :ref
          AND s.status = 'active'
          AND s.active_lead_id IS NOT NULL
        ORDER BY s.started_at DESC
        LIMIT 1
    """), {"ref": user_ref}).fetchone()

    if not row or not row[0]:
        return {"success": True, "active": False}

    lead_id = row[0]
    call_started_at = row[1]

    # Fetch lead basics for the web banner
    lead = db.execute(text("""
        SELECT id, name, phone, alternate_phone, status, city, area, company_id
        FROM crm_leads WHERE id = :lid
    """), {"lid": lead_id}).fetchone()

    if not lead:
        return {"success": True, "active": False}

    return {
        "success": True,
        "active": True,
        "lead_id": lead[0],
        "lead_name": lead[1] or "—",
        "lead_phone": lead[2] or "",
        "lead_status": lead[4] or "new",
        "lead_city": lead[5] or "",
        "company_id": lead[7],
        "call_started_at": call_started_at.isoformat() if call_started_at else None,
    }


# ── DC_DIALER_WS_001: WebSocket endpoint for real-time dialer sync ────────────

@router.websocket("/ws/dialer/sync")
async def dialer_ws_sync(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    DC_DIALER_WS_001: Persistent WebSocket connection for the web dialer.
    Authenticated via ?token=<staff_token> query param.
    Immediately sends current active-call and session state on connect.
    Receives pushed events:
      - {type: "call_state", active: bool, ...lead info...}
      - {type: "session_sync", current_index: int}
      - {type: "ping"} / responds with {type: "pong"}
    """
    from app.core.security import SecurityManager
    from app.models.staff import StaffEmployee

    # Authenticate
    payload = SecurityManager.verify_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    subject = payload.get("sub") or payload.get("user_id") or payload.get("id")
    if not subject:
        await websocket.close(code=4001)
        return

    # Resolve staff employee
    staff = db.query(StaffEmployee).filter(StaffEmployee.id == subject).first()
    if not staff:
        await websocket.close(code=4003)
        return

    user_ref = str(staff.id)

    await websocket.accept()
    logger.info("[DC_DIALER_WS] Connected: user_ref=%s", user_ref)

    # Register connection queue
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _dialer_ws_registry[user_ref] = q

    # Send initial state: active call + session index
    try:
        # Auto-clear stale active calls (>10 min) then fetch current state
        db.execute(text("""
            UPDATE crm_dialer_sessions
            SET active_lead_id = NULL, call_started_at = NULL
            WHERE user_ref = :ref
              AND active_lead_id IS NOT NULL
              AND call_started_at < NOW() - INTERVAL '10 minutes'
        """), {"ref": user_ref})
        db.commit()

        ac_row = db.execute(text("""
            SELECT s.active_lead_id, s.call_started_at
            FROM crm_dialer_sessions s
            WHERE s.user_ref = :ref AND s.status = 'active' AND s.active_lead_id IS NOT NULL
            ORDER BY s.started_at DESC LIMIT 1
        """), {"ref": user_ref}).fetchone()

        if ac_row and ac_row[0]:
            lead_id = ac_row[0]
            call_started_at = ac_row[1]
            lead_row = db.execute(text("""
                SELECT id, name, phone, status, city, company_id FROM crm_leads WHERE id = :lid
            """), {"lid": lead_id}).fetchone()
            if lead_row:
                await websocket.send_json({
                    "type": "call_state",
                    "active": True,
                    "lead_id": lead_row[0],
                    "lead_name": lead_row[1] or "—",
                    "lead_phone": lead_row[2] or "",
                    "lead_status": lead_row[3] or "new",
                    "lead_city": lead_row[4] or "",
                    "company_id": lead_row[5],
                    "call_started_at": call_started_at.isoformat() if call_started_at else None,
                })
            else:
                await websocket.send_json({"type": "call_state", "active": False})
        else:
            await websocket.send_json({"type": "call_state", "active": False})

        sess_row = db.execute(text("""
            SELECT current_index FROM crm_dialer_sessions
            WHERE user_ref = :ref AND status = 'active'
            ORDER BY started_at DESC LIMIT 1
        """), {"ref": user_ref}).fetchone()
        if sess_row:
            await websocket.send_json({"type": "session_sync", "current_index": sess_row[0] or 0})

    except Exception as e:
        logger.warning("[DC_DIALER_WS] Init send failed for user_ref=%s: %s", user_ref, e)

    # DC_DIALER_WS_001 Main loop — two delivery paths (both are event-driven, no polling):
    #   1. Same-worker: _push_dialer_ws() enqueues into `q`; loop drains immediately.
    #   2. Cross-worker: shared PG LISTEN/NOTIFY via _start_shared_pg_listener().
    #      ONE psycopg2 connection per worker process (not per socket) LISTENs on
    #      'dialer_events'; dispatches by user_ref into the right per-user queue.
    #      This keeps DB connection count O(workers) regardless of active sockets.

    # Ensure the shared listener is running for this worker (no-op if already started)
    await _start_shared_pg_listener()

    try:
        while True:
            # Drain push-queue messages (same-worker fast path + cross-worker PG LISTEN fanout)
            try:
                msg = await asyncio.wait_for(q.get(), timeout=0.2)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                pass

            # Non-blocking receive for client ping or disconnection
            try:
                client_msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
                if isinstance(client_msg, dict) and client_msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            except (WebSocketDisconnect, Exception):
                break

    except (WebSocketDisconnect, Exception) as e:
        logger.info("[DC_DIALER_WS] Disconnected: user_ref=%s (%s)", user_ref, e)
    finally:
        if _dialer_ws_registry.get(user_ref) is q:
            del _dialer_ws_registry[user_ref]
        logger.info("[DC_DIALER_WS] Cleaned up: user_ref=%s", user_ref)
