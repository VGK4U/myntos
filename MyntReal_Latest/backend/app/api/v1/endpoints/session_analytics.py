"""
DC Protocol Mar 2026: Portal Login Session Analytics
Tracks login sessions for Staff (from audit log), MNR Members, and Business Partners.
New table: portal_session_log for MNR + Partner.
Staff data sourced from existing staff_audit_log.
Access: EA or VGK Mentor (role_code in {"ea", "vgk4u"}).
Zero negative impact — purely additive reads + appended inserts.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date
import logging

from app.core.database import get_db
from app.core.security import get_current_user_hybrid

router = APIRouter()
logger = logging.getLogger(__name__)

SESSION_ADMIN_ROLES = {"ea", "vgk4u"}


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _require_session_admin(current_user):
    """DC Protocol: Verify caller is EA or VGK Mentor."""
    if not hasattr(current_user, "emp_code"):
        raise HTTPException(status_code=403, detail="Staff access required")
    role_code = (
        current_user.role.role_code.lower()
        if current_user.role and current_user.role.role_code
        else ""
    )
    if role_code not in SESSION_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Session analytics requires EA or VGK Mentor access"
        )


def _ensure_session_log_table(db: Session):
    """DC Protocol: Auto-create portal_session_log (idempotent IF NOT EXISTS)."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS portal_session_log (
            id                      SERIAL PRIMARY KEY,
            user_type               VARCHAR(20)  NOT NULL,
            user_id                 VARCHAR(100) NOT NULL,
            user_identifier         VARCHAR(100) NOT NULL,
            display_name            VARCHAR(200),
            login_at                TIMESTAMP    NOT NULL DEFAULT NOW(),
            logout_at               TIMESTAMP,
            session_duration_minutes INTEGER,
            token_expiry_minutes    INTEGER      NOT NULL DEFAULT 30,
            ip_address              VARCHAR(64),
            user_agent              TEXT,
            ended_by                VARCHAR(20)
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_psl_type_login
            ON portal_session_log (user_type, login_at DESC)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_psl_user_id
            ON portal_session_log (user_id, login_at DESC)
    """))
    db.commit()


def insert_session_log(db: Session, user_type: str, user_id: str,
                       user_identifier: str, display_name: str,
                       ip_address: Optional[str], user_agent: Optional[str],
                       token_expiry_minutes: int = 30):
    """
    DC Protocol: Insert a login session record.
    Called from auth endpoints at login time.
    Wrapped in try/except — failure MUST NOT block login.
    """
    try:
        _ensure_session_log_table(db)
        db.execute(text("""
            INSERT INTO portal_session_log
                (user_type, user_id, user_identifier, display_name,
                 login_at, token_expiry_minutes, ip_address, user_agent)
            VALUES
                (:user_type, :user_id, :user_identifier, :display_name,
                 NOW(), :expiry, :ip, :ua)
        """), {
            "user_type":   user_type,
            "user_id":     str(user_id),
            "user_identifier": str(user_identifier),
            "display_name": display_name or "",
            "expiry":      token_expiry_minutes,
            "ip":          ip_address,
            "ua":          user_agent,
        })
        db.commit()
    except Exception as e:
        logger.warning(f"[SESSION_LOG] Insert failed ({user_type}/{user_identifier}): {e}")
        try:
            db.rollback()
        except Exception:
            pass


def close_session_log(db: Session, user_type: str, user_id: str):
    """
    DC Protocol: Close the most recent open session for this user on logout.
    Wrapped in try/except — failure MUST NOT block logout.
    """
    try:
        _ensure_session_log_table(db)
        db.execute(text("""
            UPDATE portal_session_log
               SET logout_at               = NOW(),
                   session_duration_minutes = GREATEST(
                       1,
                       FLOOR(EXTRACT(EPOCH FROM (NOW() - login_at)) / 60)::INTEGER
                   ),
                   ended_by               = 'logout'
             WHERE id = (
                 SELECT id
                   FROM portal_session_log
                  WHERE user_type = :user_type
                    AND user_id   = :user_id
                    AND logout_at IS NULL
                  ORDER BY login_at DESC
                  LIMIT 1
             )
        """), {"user_type": user_type, "user_id": str(user_id)})
        db.commit()
    except Exception as e:
        logger.warning(f"[SESSION_LOG] Close failed ({user_type}/{user_id}): {e}")
        try:
            db.rollback()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# STAFF LOGIN ANALYTICS  (sourced from staff_audit_log)
# ─────────────────────────────────────────────────────────────────────────────

def _staff_where(date_from, date_to, emp_code, params):
    """Build staff_audit_log WHERE conditions."""
    conds = ["sal.action = 'LOGIN_SUCCESS'"]
    if date_from:
        conds.append("sal.timestamp >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("sal.timestamp < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to
    if emp_code:
        conds.append("(se.emp_code ILIKE :emp_code OR se.full_name ILIKE :emp_code)")
        params["emp_code"] = f"%{emp_code}%"
    return " AND ".join(conds)


@router.get("/session-analytics/staff/summary")
async def staff_login_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    emp_code:  Optional[str]  = Query(None),
):
    """DC Protocol: Staff login session summary — 6 executive stat cards."""
    _require_session_admin(current_user)
    params: dict = {}
    where = _staff_where(date_from, date_to, emp_code, params)

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE {where}
    """), params).scalar() or 0

    unique = db.execute(text(f"""
        SELECT COUNT(DISTINCT sal.employee_id) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE {where}
    """), params).scalar() or 0

    today_p = dict(params)
    today_where = _staff_where(None, None, emp_code, today_p)
    today_p_clean = {k: v for k, v in today_p.items() if k != "date_from" and k != "date_to"}
    today = db.execute(text(f"""
        SELECT COUNT(*) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE {today_where}
          AND sal.timestamp >= CURRENT_DATE
    """), today_p_clean).scalar() or 0

    month_p = dict(today_p_clean)
    this_month = db.execute(text(f"""
        SELECT COUNT(*) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE {today_where}
          AND sal.timestamp >= DATE_TRUNC('month', NOW())
    """), month_p).scalar() or 0

    avg_row = db.execute(text(f"""
        SELECT ROUND(AVG(dur))::BIGINT AS avg_dur
        FROM (
            SELECT FLOOR(EXTRACT(EPOCH FROM (
                (SELECT MIN(sal2.timestamp)
                   FROM staff_audit_log sal2
                  WHERE sal2.employee_id = sal.employee_id
                    AND sal2.action = 'LOGOUT'
                    AND sal2.timestamp > sal.timestamp)
                - sal.timestamp
            )) / 60)::INTEGER AS dur
            FROM staff_audit_log sal
            JOIN staff_employees se ON se.id = sal.employee_id
            WHERE {where}
        ) sub
        WHERE dur IS NOT NULL AND dur >= 0 AND dur <= 1440
    """), params).fetchone()
    avg_duration = int(avg_row.avg_dur) if avg_row and avg_row.avg_dur else 0

    _date_to_cond = "AND sal.timestamp < :date_to + INTERVAL '1 day'" if date_to else ""
    failed = db.execute(text(f"""
        SELECT COUNT(*) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE sal.action IN ('LOGIN_FAILED', 'ACCOUNT_LOCKED')
          {'AND se.emp_code ILIKE :emp_code' if emp_code else ''}
          {'AND sal.timestamp >= :date_from' if date_from else ''}
          {_date_to_cond}
    """), {k: v for k, v in params.items()}).scalar() or 0

    return {
        "success": True,
        "total_logins":    int(total),
        "unique_users":    int(unique),
        "today_logins":    int(today),
        "this_month":      int(this_month),
        "avg_duration_min": avg_duration,
        "failed_logins":   int(failed),
    }


@router.get("/session-analytics/staff/sessions")
async def staff_login_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    page:      int            = Query(1,  ge=1),
    per_page:  int            = Query(50, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    emp_code:  Optional[str]  = Query(None),
):
    """DC Protocol: Paginated staff login session list with duration."""
    _require_session_admin(current_user)
    params: dict = {}
    where  = _staff_where(date_from, date_to, emp_code, params)
    offset = (page - 1) * per_page

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM staff_audit_log sal
        JOIN staff_employees se ON se.id = sal.employee_id
        WHERE {where}
    """), params).scalar() or 0

    rows = db.execute(text(f"""
        SELECT
            sal.id,
            sal.timestamp                        AS login_at,
            sal.ip_address,
            se.emp_code,
            se.full_name,
            sd.name                              AS department_name,
            sr.role_name,
            logout_sub.logout_at,
            CASE
                WHEN logout_sub.logout_at IS NOT NULL
                THEN FLOOR(EXTRACT(EPOCH FROM (logout_sub.logout_at - sal.timestamp))/60)::INTEGER
                ELSE NULL
            END                                  AS session_duration_minutes,
            CASE
                WHEN logout_sub.logout_at IS NOT NULL THEN 'logout'
                ELSE 'timeout'
            END                                  AS ended_by
        FROM staff_audit_log sal
        JOIN staff_employees  se ON se.id = sal.employee_id
        LEFT JOIN staff_departments sd ON sd.id = se.department_id
        LEFT JOIN staff_roles       sr ON sr.id = se.role_id
        LEFT JOIN LATERAL (
            SELECT MIN(sal2.timestamp) AS logout_at
            FROM   staff_audit_log sal2
            WHERE  sal2.employee_id = sal.employee_id
              AND  sal2.action      = 'LOGOUT'
              AND  sal2.timestamp   > sal.timestamp
        ) logout_sub ON TRUE
        WHERE {where}
        ORDER BY sal.timestamp DESC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": per_page, "offset": offset}).fetchall()

    return {
        "success":  True,
        "total":    int(total),
        "page":     page,
        "per_page": per_page,
        "sessions": [dict(r._mapping) for r in rows],
    }


@router.get("/session-analytics/staff/top-users")
async def staff_top_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(10, ge=1, le=50),
):
    """DC Protocol: Top staff by total session time and login frequency."""
    _require_session_admin(current_user)
    params: dict = {"limit": limit}
    extra = ""
    if date_from:
        extra += " AND sal.timestamp >= :date_from"
        params["date_from"] = date_from
    if date_to:
        extra += " AND sal.timestamp < :date_to + INTERVAL '1 day'"
        params["date_to"] = date_to

    rows = db.execute(text(f"""
        SELECT
            se.emp_code,
            se.full_name,
            sr.role_name,
            sd.name                               AS department_name,
            COUNT(sal.id)                         AS total_logins,
            COALESCE(SUM(dur_sub.dur_min), 0)     AS total_minutes,
            MAX(sal.timestamp)                    AS last_login
        FROM staff_audit_log sal
        JOIN staff_employees  se ON se.id = sal.employee_id
        LEFT JOIN staff_departments sd ON sd.id = se.department_id
        LEFT JOIN staff_roles       sr ON sr.id = se.role_id
        LEFT JOIN LATERAL (
            SELECT FLOOR(EXTRACT(EPOCH FROM (
                (SELECT MIN(sal2.timestamp)
                   FROM staff_audit_log sal2
                  WHERE sal2.employee_id = sal.employee_id
                    AND sal2.action = 'LOGOUT'
                    AND sal2.timestamp > sal.timestamp)
                - sal.timestamp
            )) / 60)::INTEGER AS dur_min
        ) dur_sub ON TRUE
        WHERE sal.action = 'LOGIN_SUCCESS' {extra}
        GROUP BY se.emp_code, se.full_name, sr.role_name, sd.name
        ORDER BY total_logins DESC, total_minutes DESC
        LIMIT :limit
    """), params).fetchall()

    return {
        "success": True,
        "users":   [dict(r._mapping) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPER: portal_session_log queries (MNR + Partner)
# ─────────────────────────────────────────────────────────────────────────────

def _psl_where(user_type, date_from, date_to, search, has_type, params):
    conds = ["user_type = :user_type"]
    params["user_type"] = user_type
    if date_from:
        conds.append("login_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("login_at < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to
    if search:
        conds.append("(user_identifier ILIKE :search OR display_name ILIKE :search)")
        params["search"] = f"%{search}%"
    if has_type == "logout":
        conds.append("ended_by = 'logout'")
    elif has_type == "timeout":
        conds.append("(ended_by IS NULL OR ended_by = 'timeout')")
    return " AND ".join(conds)


def _psl_summary(db, user_type, date_from, date_to, search):
    _ensure_session_log_table(db)
    params: dict = {}
    where = _psl_where(user_type, date_from, date_to, search, None, params)

    total    = db.execute(text(f"SELECT COUNT(*) FROM portal_session_log WHERE {where}"), params).scalar() or 0
    unique   = db.execute(text(f"SELECT COUNT(DISTINCT user_id) FROM portal_session_log WHERE {where}"), params).scalar() or 0

    td_p = dict(params)
    today_conds = [f"user_type = '{user_type}'"]
    if search:
        today_conds.append("(user_identifier ILIKE :search OR display_name ILIKE :search)")
        td_p["search"] = f"%{search}%"
    today_conds.append("login_at >= CURRENT_DATE")
    today = db.execute(text(f"SELECT COUNT(*) FROM portal_session_log WHERE {' AND '.join(today_conds)}"), td_p).scalar() or 0

    mo_p = dict(td_p)
    mo_p_conds = [f"user_type = '{user_type}'"]
    if search:
        mo_p_conds.append("(user_identifier ILIKE :search OR display_name ILIKE :search)")
    mo_p_conds.append("login_at >= DATE_TRUNC('month', NOW())")
    this_month = db.execute(text(f"SELECT COUNT(*) FROM portal_session_log WHERE {' AND '.join(mo_p_conds)}"), mo_p).scalar() or 0

    avg_row = db.execute(text(f"""
        SELECT ROUND(AVG(session_duration_minutes))::BIGINT AS avg_dur
        FROM portal_session_log
        WHERE {where}
          AND session_duration_minutes IS NOT NULL
          AND session_duration_minutes >= 0
          AND session_duration_minutes <= 1440
    """), params).fetchone()
    avg_duration = int(avg_row.avg_dur) if avg_row and avg_row.avg_dur else 0

    clean_params: dict = {}
    if search:
        clean_params["search"] = f"%{search}%"
    clean_where = f"user_type = '{user_type}' AND ended_by = 'logout'"
    if search:
        clean_where += " AND (user_identifier ILIKE :search OR display_name ILIKE :search)"
    clean_sessions = db.execute(text(f"SELECT COUNT(*) FROM portal_session_log WHERE {clean_where}"), clean_params).scalar() or 0

    return {
        "success":          True,
        "total_logins":     int(total),
        "unique_users":     int(unique),
        "today_logins":     int(today),
        "this_month":       int(this_month),
        "avg_duration_min": avg_duration,
        "clean_sessions":   int(clean_sessions),
    }


def _psl_sessions(db, user_type, page, per_page, date_from, date_to, search, has_type):
    _ensure_session_log_table(db)
    params: dict = {}
    where  = _psl_where(user_type, date_from, date_to, search, has_type, params)
    offset = (page - 1) * per_page

    total = db.execute(text(f"SELECT COUNT(*) FROM portal_session_log WHERE {where}"), params).scalar() or 0
    rows  = db.execute(text(f"""
        SELECT *,
               CASE
                   WHEN session_duration_minutes IS NULL AND logout_at IS NULL
                   THEN token_expiry_minutes
                   ELSE session_duration_minutes
               END AS effective_duration_minutes
        FROM portal_session_log
        WHERE {where}
        ORDER BY login_at DESC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": per_page, "offset": offset}).fetchall()

    return {
        "success":  True,
        "total":    int(total),
        "page":     page,
        "per_page": per_page,
        "sessions": [dict(r._mapping) for r in rows],
    }


def _psl_top_users(db, user_type, date_from, date_to, limit):
    _ensure_session_log_table(db)
    params: dict = {"user_type": user_type, "limit": limit}
    extra = ""
    if date_from:
        extra += " AND login_at >= :date_from"
        params["date_from"] = date_from
    if date_to:
        extra += " AND login_at < :date_to + INTERVAL '1 day'"
        params["date_to"] = date_to

    rows = db.execute(text(f"""
        SELECT
            user_identifier,
            display_name,
            COUNT(*)                                 AS total_logins,
            COALESCE(SUM(session_duration_minutes),0) AS total_minutes,
            ROUND(AVG(session_duration_minutes))::INTEGER AS avg_minutes,
            MAX(login_at)                            AS last_login
        FROM portal_session_log
        WHERE user_type = :user_type {extra}
        GROUP BY user_identifier, display_name
        ORDER BY total_logins DESC, total_minutes DESC
        LIMIT :limit
    """), params).fetchall()

    return {"success": True, "users": [dict(r._mapping) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# MNR LOGIN ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/session-analytics/mnr/summary")
async def mnr_login_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    search:    Optional[str]  = Query(None),
):
    _require_session_admin(current_user)
    return _psl_summary(db, "mnr", date_from, date_to, search)


@router.get("/session-analytics/mnr/sessions")
async def mnr_login_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    page:      int            = Query(1,  ge=1),
    per_page:  int            = Query(50, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    search:    Optional[str]  = Query(None),
    has_type:  Optional[str]  = Query(None),
):
    _require_session_admin(current_user)
    return _psl_sessions(db, "mnr", page, per_page, date_from, date_to, search, has_type)


@router.get("/session-analytics/mnr/top-users")
async def mnr_top_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(10, ge=1, le=50),
):
    _require_session_admin(current_user)
    return _psl_top_users(db, "mnr", date_from, date_to, limit)


# ─────────────────────────────────────────────────────────────────────────────
# PARTNER LOGIN ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/session-analytics/partner/summary")
async def partner_login_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    search:    Optional[str]  = Query(None),
):
    _require_session_admin(current_user)
    return _psl_summary(db, "partner", date_from, date_to, search)


@router.get("/session-analytics/partner/sessions")
async def partner_login_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    page:      int            = Query(1,  ge=1),
    per_page:  int            = Query(50, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    search:    Optional[str]  = Query(None),
    has_type:  Optional[str]  = Query(None),
):
    _require_session_admin(current_user)
    return _psl_sessions(db, "partner", page, per_page, date_from, date_to, search, has_type)


@router.get("/session-analytics/partner/top-users")
async def partner_top_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(10, ge=1, le=50),
):
    _require_session_admin(current_user)
    return _psl_top_users(db, "partner", date_from, date_to, limit)


# ── TOP MARKETPLACE PRODUCTS (basket/PO data) ─────────────────────────────────
@router.get("/session-analytics/marketplace/top-products")
async def marketplace_top_products(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(10, ge=1, le=50),
):
    _require_session_admin(current_user)

    params: dict = {}
    where_parts = []

    if date_from:
        where_parts.append("mpo.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        _dt_end = "mpo.created_at < :date_to + INTERVAL '1 day'"
        where_parts.append(_dt_end)
        params["date_to"] = date_to

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    rows = db.execute(text(f"""
        SELECT
            poi.sku,
            poi.product_name,
            poi.category_name,
            poi.brand,
            SUM(poi.ordered_qty)          AS total_qty_ordered,
            COUNT(DISTINCT poi.po_id)     AS total_orders,
            COUNT(DISTINCT COALESCE(mpo.mnr_id, mpo.partner_code)) AS unique_buyers,
            MAX(mpo.created_at)           AS last_ordered
        FROM marketplace_po_items poi
        JOIN marketplace_purchase_orders mpo ON mpo.id = poi.po_id
        {where_sql}
        GROUP BY poi.sku, poi.product_name, poi.category_name, poi.brand
        ORDER BY total_qty_ordered DESC, total_orders DESC
        LIMIT :limit
    """), {**params, "limit": limit}).fetchall()

    products = []
    for i, r in enumerate(rows, 1):
        products.append({
            "rank":             i,
            "sku":              r.sku,
            "product_name":     r.product_name,
            "category_name":    r.category_name or "—",
            "brand":            r.brand or "—",
            "total_qty_ordered": int(r.total_qty_ordered or 0),
            "total_orders":     int(r.total_orders or 0),
            "unique_buyers":    int(r.unique_buyers or 0),
            "last_ordered":     r.last_ordered.isoformat() if r.last_ordered else None,
        })

    return {"success": True, "products": products}
