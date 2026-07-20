"""
DC Protocol: Catalog Sharing & Hit Tracking System
Tracks MNR Business Access Programme catalog shares and page views.
Created: Feb 26, 2026
"""
from fastapi import APIRouter, Depends, Query, Request, Body, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime
import secrets
import os
import subprocess
import shutil
import logging

from app.core.database import get_db
from app.core.security import get_current_user_hybrid

router = APIRouter()
logger = logging.getLogger(__name__)

CATALOG_DOC_ID = "1M79qH4eum-qx8B7juyqQoMv0-LkTUoec"
CATALOG_PDF_PATH = os.path.join(os.path.dirname(__file__), "../../../../../frontend/public/catalog/mnr-catalog.pdf")
CATALOG_PAGES_DIR = os.path.join(os.path.dirname(__file__), "../../../../../frontend/public/catalog/pages")

CATALOG_ADMIN_ROLES = {"ea", "vgk4u"}
CATALOG_MAX_BYTES = 150 * 1024 * 1024  # 150 MB


def _require_catalog_admin(current_user):
    """DC Protocol: Verify caller is EA or VGK Supreme staff."""
    if not hasattr(current_user, "emp_code"):
        raise HTTPException(status_code=403, detail="Staff access required")
    role_code = (
        current_user.role.role_code.lower()
        if current_user.role and current_user.role.role_code
        else ""
    )
    if role_code not in CATALOG_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="MNR Catalogue management requires EA or VGK Supreme access"
        )


def _ensure_catalog_tables(db: Session):
    """DC Protocol: Auto-create catalog tables if not exist (idempotent)."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS catalog_shares (
            id          SERIAL PRIMARY KEY,
            mnr_id      VARCHAR(20),
            member_name VARCHAR(200),
            platform    VARCHAR(30)  NOT NULL DEFAULT 'unknown',
            language    VARCHAR(10)  DEFAULT 'english',
            recipient_name    VARCHAR(200),
            recipient_prefix  VARCHAR(10),
            share_ref_code    VARCHAR(60) UNIQUE,
            ip_address  VARCHAR(45),
            user_agent  TEXT,
            shared_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS catalog_hits (
            id              SERIAL PRIMARY KEY,
            share_ref_code  VARCHAR(60),
            ip_address      VARCHAR(45),
            user_agent      TEXT,
            referrer        VARCHAR(500),
            viewed_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_catalog_shares_mnr
            ON catalog_shares (mnr_id)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_catalog_hits_ref
            ON catalog_hits (share_ref_code)
    """))
    db.commit()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.client.host if request.client else "unknown")[:45]


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS  (no auth required)
# ──────────────────────────────────────────────────────────────────────────────

@router.api_route("/brochure", methods=["GET", "HEAD"], summary="Stream MNR catalog PDF — locally hosted, no Google Drive")
async def get_catalog_brochure(request: Request):
    """
    DC Protocol (Feb 2026): Serves the MNR catalog PDF directly from local storage.
    Eliminates Google Drive iframe dependency for fast, reliable, cached delivery.
    Supports HTTP range requests (browser PDF viewer seeking).
    Supports HEAD requests for link pre-flight checks and HTTP clients.
    Cache-Control: 7 days — catalog is stable; update file to refresh.
    """
    from fastapi.responses import Response as PlainResponse
    catalog_path = os.path.normpath(CATALOG_PDF_PATH)
    if not os.path.isfile(catalog_path):
        raise HTTPException(
            status_code=404,
            detail="Catalog brochure not available. Please contact admin."
        )
    _headers = {
        "Cache-Control": "public, max-age=604800, immutable",
        "Content-Disposition": "inline; filename=MNR-Business-Catalog.pdf",
        "X-DC-Source": "local-storage",
    }
    if request.method == "HEAD":
        return PlainResponse(
            headers={**_headers, "Content-Type": "application/pdf",
                     "Content-Length": str(os.path.getsize(catalog_path))},
        )
    return FileResponse(catalog_path, media_type="application/pdf", headers=_headers)


@router.post("/public/hit", summary="Record a catalog page view (public)")
async def record_catalog_hit(
    request: Request,
    ref: Optional[str] = Query(None, description="Share ref code from URL ?ref= param"),
    db: Session = Depends(get_db),
):
    """DC Protocol: Record a catalog page view. Called on every /catalog load."""
    _ensure_catalog_tables(db)
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")[:500]
    referrer = request.headers.get("Referer", "")[:500]

    db.execute(text("""
        INSERT INTO catalog_hits (share_ref_code, ip_address, user_agent, referrer, viewed_at)
        VALUES (:ref, :ip, :ua, :referrer, NOW())
    """), {
        "ref":      ref[:60] if ref else None,
        "ip":       ip,
        "ua":       ua,
        "referrer": referrer,
    })
    db.commit()
    return {"success": True}


@router.post("/share", summary="Record a catalog share event")
async def record_catalog_share(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    DC Protocol: Record a catalog share action.
    Called by the share dialog when the user taps any share button.
    Returns a unique ref_code to embed as ?ref= in the catalog URL.
    """
    _ensure_catalog_tables(db)
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")[:500]

    mnr_id = (payload.get("mnr_id") or "").strip()[:20]
    ref_code = f"{mnr_id}-{secrets.token_hex(6)}" if mnr_id else f"anon-{secrets.token_hex(8)}"

    db.execute(text("""
        INSERT INTO catalog_shares
            (mnr_id, member_name, platform, language,
             recipient_name, recipient_prefix, share_ref_code,
             ip_address, user_agent, shared_at)
        VALUES
            (:mnr_id, :member_name, :platform, :language,
             :recipient_name, :recipient_prefix, :ref_code,
             :ip, :ua, NOW())
        ON CONFLICT (share_ref_code) DO NOTHING
    """), {
        "mnr_id":           mnr_id or None,
        "member_name":      (payload.get("member_name") or "")[:200],
        "platform":         (payload.get("platform") or "unknown")[:30],
        "language":         (payload.get("language") or "english")[:10],
        "recipient_name":   (payload.get("recipient_name") or "")[:200],
        "recipient_prefix": (payload.get("recipient_prefix") or "")[:10],
        "ref_code":         ref_code,
        "ip":               ip,
        "ua":               ua,
    })
    db.commit()
    return {"success": True, "share_ref_code": ref_code}


@router.get("/public/referrer", summary="Look up who shared this catalog link (public)")
async def get_referrer_info(
    ref: str = Query(..., description="Share ref code from URL ?ref= param"),
    db: Session = Depends(get_db),
):
    """
    DC Protocol: Given a catalog ref code, return the member name + MNR ID who created that share.
    Used by the catalog page to show a 'Referred by X' banner.
    Returns found=False for anon or unknown ref codes.
    """
    _ensure_catalog_tables(db)
    try:
        row = db.execute(text("""
            SELECT mnr_id, member_name
            FROM   catalog_shares
            WHERE  share_ref_code = :ref
              AND  mnr_id IS NOT NULL
              AND  mnr_id <> ''
            LIMIT 1
        """), {"ref": ref[:60]}).fetchone()

        if not row:
            return {"success": True, "found": False}

        return {
            "success":     True,
            "found":       True,
            "mnr_id":      row.mnr_id      or "",
            "member_name": row.member_name or "",
        }
    except Exception:
        return {"success": True, "found": False}


@router.get("/public/bonanzas", summary="Get active bonanzas for share dialog (public)")
async def get_active_bonanzas_public(db: Session = Depends(get_db)):
    """DC Protocol: Return currently active bonanzas (status=approved/Approved, dates active)."""
    try:
        rows = db.execute(text("""
            SELECT id, bonanza_name, end_date,
                   COALESCE(description, '') AS reward_text
            FROM dynamic_bonanza
            WHERE LOWER(status) = 'approved'
              AND start_date <= NOW()
              AND end_date   >= NOW()
            ORDER BY end_date ASC
            LIMIT 3
        """)).fetchall()
        return {
            "success": True,
            "bonanzas": [
                {
                    "id":          r.id,
                    "name":        r.bonanza_name,
                    "end_date":    r.end_date.strftime("%d %b %Y") if r.end_date else "",
                    "reward_type": "Cash",
                    "reward_text": r.reward_text or "",
                }
                for r in rows
            ],
        }
    except Exception:
        return {"success": True, "bonanzas": []}


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATED MEMBER ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/my-stats", summary="Get current user's catalog share statistics")
async def get_my_catalog_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    DC Protocol: Personal catalog share stats for the dashboard Personal Summary card.
    Returns total_shares, total_visits (hits from own ref codes), avg_visits.
    """
    _ensure_catalog_tables(db)

    mnr_id = str(current_user.id)

    row = db.execute(text("""
        SELECT
            COUNT(cs.id)                                              AS total_shares,
            COALESCE(SUM(h.hit_count), 0)                            AS total_visits
        FROM catalog_shares cs
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS hit_count
            FROM   catalog_hits ch
            WHERE  ch.share_ref_code = cs.share_ref_code
        ) h ON TRUE
        WHERE cs.mnr_id = :mnr_id
    """), {"mnr_id": mnr_id}).fetchone()

    total_shares = int(row.total_shares or 0)
    total_visits = int(row.total_visits or 0)
    avg_visits   = round(total_visits / total_shares, 1) if total_shares > 0 else 0.0

    return {
        "success":       True,
        "total_shares":  total_shares,
        "total_visits":  total_visits,
        "avg_visits":    avg_visits,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS  (authenticated, used by /rvz/catalog-sharing page)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/shares", summary="Admin: list all catalog shares with filters")
async def admin_list_shares(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    page:       int           = Query(1,    ge=1),
    per_page:   int           = Query(50,   ge=1, le=500),
    platform:   Optional[str] = Query(None),
    language:   Optional[str] = Query(None),
    mnr_id:     Optional[str] = Query(None),
    date_from:  Optional[date] = Query(None),
    date_to:    Optional[date] = Query(None),
):
    """DC Protocol: Admin view of all catalog shares with optional filters."""
    _ensure_catalog_tables(db)

    conds  = ["1=1"]
    params: dict = {}

    if platform:
        conds.append("platform = :platform")
        params["platform"] = platform
    if language:
        conds.append("language = :language")
        params["language"] = language
    if mnr_id:
        conds.append("mnr_id ILIKE :mnr_id")
        params["mnr_id"] = f"%{mnr_id}%"
    if date_from:
        conds.append("shared_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("shared_at < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to

    where  = " AND ".join(conds)
    offset = (page - 1) * per_page

    total = db.execute(
        text(f"SELECT COUNT(*) FROM catalog_shares WHERE {where}"), params
    ).scalar()

    rows = db.execute(text(f"""
        SELECT cs.*,
               (SELECT COUNT(*) FROM catalog_hits ch
                WHERE  ch.share_ref_code = cs.share_ref_code) AS hit_count
        FROM   catalog_shares cs
        WHERE  {where}
        ORDER  BY shared_at DESC
        LIMIT  :limit OFFSET :offset
    """), {**params, "limit": per_page, "offset": offset}).fetchall()

    return {
        "success":  True,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "shares":   [dict(r._mapping) for r in rows],
    }


@router.get("/admin/hits", summary="Admin: list all catalog page hits with filters")
async def admin_list_hits(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    page:           int            = Query(1,    ge=1),
    per_page:       int            = Query(50,   ge=1, le=200),
    share_ref_code: Optional[str]  = Query(None),
    ip_address:     Optional[str]  = Query(None),
    mnr_id:         Optional[str]  = Query(None),
    has_ref:        Optional[str]  = Query(None, description="'true' for referral views, 'false' for direct"),
    date_from:      Optional[date] = Query(None),
    date_to:        Optional[date] = Query(None),
):
    """DC Protocol: Admin view of all catalog page hits with optional filters."""
    _ensure_catalog_tables(db)

    conds:  list = ["1=1"]
    params: dict = {}

    if share_ref_code:
        conds.append("ch.share_ref_code ILIKE :ref")
        params["ref"] = f"%{share_ref_code}%"
    if ip_address:
        conds.append("ch.ip_address ILIKE :ip")
        params["ip"] = f"%{ip_address}%"
    if mnr_id:
        conds.append("cs.mnr_id ILIKE :mnr_id")
        params["mnr_id"] = f"%{mnr_id}%"
    if has_ref == "true":
        conds.append("ch.share_ref_code IS NOT NULL AND ch.share_ref_code <> ''")
    elif has_ref == "false":
        conds.append("(ch.share_ref_code IS NULL OR ch.share_ref_code = '')")
    if date_from:
        conds.append("ch.viewed_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("ch.viewed_at < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to

    where  = " AND ".join(conds)
    offset = (page - 1) * per_page

    count_query = f"""
        SELECT COUNT(*) FROM catalog_hits ch
        LEFT JOIN catalog_shares cs ON cs.share_ref_code = ch.share_ref_code
        WHERE {where}
    """
    total = db.execute(text(count_query), params).scalar()

    rows = db.execute(text(f"""
        SELECT ch.*,
               cs.mnr_id,
               cs.member_name,
               cs.platform AS share_platform
        FROM   catalog_hits ch
        LEFT   JOIN catalog_shares cs ON cs.share_ref_code = ch.share_ref_code
        WHERE  {where}
        ORDER  BY ch.viewed_at DESC
        LIMIT  :limit OFFSET :offset
    """), {**params, "limit": per_page, "offset": offset}).fetchall()

    return {
        "success":  True,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "hits":     [dict(r._mapping) for r in rows],
    }


@router.get("/admin/summary", summary="Admin: overall catalog stats summary")
async def admin_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    mnr_id:    Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
):
    """DC Protocol: High-level catalog stats for admin dashboard. Supports optional MNR/date filters."""
    _ensure_catalog_tables(db)

    share_conds = ["1=1"]
    hit_conds   = ["1=1"]
    params: dict = {}

    if mnr_id:
        share_conds.append("cs.mnr_id ILIKE :mnr_id")
        params["mnr_id"] = f"%{mnr_id}%"
    if date_from:
        share_conds.append("cs.shared_at >= :date_from")
        hit_conds.append("ch.viewed_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        share_conds.append("cs.shared_at < :date_to + INTERVAL '1 day'")
        hit_conds.append("ch.viewed_at < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to

    share_where = " AND ".join(share_conds)
    hit_where   = " AND ".join(hit_conds)

    if mnr_id:
        hit_conds.append("""
            ch.share_ref_code IN (
                SELECT cs2.share_ref_code FROM catalog_shares cs2
                WHERE cs2.mnr_id ILIKE :mnr_id
            )
        """)
        hit_where = " AND ".join(hit_conds)

    r = db.execute(text(f"""
        SELECT
            (SELECT COUNT(*)               FROM catalog_shares cs WHERE {share_where})                         AS total_shares,
            (SELECT COUNT(*)               FROM catalog_hits   ch WHERE {hit_where})                           AS total_hits,
            (SELECT COUNT(DISTINCT cs.mnr_id) FROM catalog_shares cs WHERE {share_where} AND cs.mnr_id IS NOT NULL) AS unique_sharers,
            (SELECT COUNT(*)               FROM catalog_hits   ch WHERE {hit_where}
                AND ch.viewed_at  >= CURRENT_DATE)                                                             AS today_hits,
            (SELECT COUNT(*)               FROM catalog_shares cs WHERE {share_where}
                AND cs.shared_at >= CURRENT_DATE)                                                              AS today_shares,
            (SELECT COUNT(*)               FROM catalog_hits   ch
                WHERE ch.share_ref_code IS NULL OR ch.share_ref_code = '')                                     AS direct_visits,
            (SELECT COUNT(DISTINCT ch.ip_address) FROM catalog_hits ch WHERE {hit_where})                      AS unique_ips
    """), params).fetchone()

    return {
        "success":        True,
        "total_shares":   int(r.total_shares   or 0),
        "total_hits":     int(r.total_hits     or 0),
        "unique_sharers": int(r.unique_sharers or 0),
        "today_hits":     int(r.today_hits     or 0),
        "today_shares":   int(r.today_shares   or 0),
        "direct_visits":  int(r.direct_visits  or 0),
        "unique_ips":     int(r.unique_ips     or 0),
        "filtered":       bool(mnr_id or date_from or date_to),
    }


@router.get("/admin/top-sharers", summary="Admin: top 10 sharers by share count")
async def admin_top_sharers(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
    mnr_id:    Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int            = Query(10, ge=1, le=50),
):
    """DC Protocol: Server-side top sharers aggregation. Returns ranked list by shares+views."""
    _ensure_catalog_tables(db)

    conds  = ["cs.mnr_id IS NOT NULL", "cs.mnr_id <> ''"]
    params: dict = {"limit": limit}

    if mnr_id:
        conds.append("cs.mnr_id ILIKE :mnr_id")
        params["mnr_id"] = f"%{mnr_id}%"
    if date_from:
        conds.append("cs.shared_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conds.append("cs.shared_at < :date_to + INTERVAL '1 day'")
        params["date_to"] = date_to

    where = " AND ".join(conds)

    rows = db.execute(text(f"""
        SELECT
            cs.mnr_id,
            MAX(cs.member_name)          AS member_name,
            COUNT(cs.id)                 AS share_count,
            COALESCE(SUM(h.cnt), 0)      AS total_views,
            MAX(cs.shared_at)            AS last_shared_at
        FROM catalog_shares cs
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt
            FROM   catalog_hits ch
            WHERE  ch.share_ref_code = cs.share_ref_code
        ) h ON TRUE
        WHERE {where}
        GROUP BY cs.mnr_id
        ORDER BY share_count DESC, total_views DESC
        LIMIT :limit
    """), params).fetchall()

    return {
        "success": True,
        "sharers": [
            {
                "mnr_id":        r.mnr_id,
                "member_name":   r.member_name or "—",
                "share_count":   int(r.share_count  or 0),
                "total_views":   int(r.total_views  or 0),
                "avg_views":     round(int(r.total_views or 0) / int(r.share_count or 1), 1),
                "last_shared_at": r.last_shared_at.isoformat() if r.last_shared_at else None,
            }
            for r in rows
        ],
    }


@router.get("/admin/member-stats", summary="Admin: catalog stats per member (batch)")
async def admin_member_stats(
    mnr_ids: str = Query(..., description="Comma-separated MNR IDs"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    DC Protocol: Batch catalog stats for admin member tables.
    Returns shares / visits / avg_visits per MNR ID.
    Used by all-members table to populate Shares/Visits/Avg columns.
    """
    _ensure_catalog_tables(db)

    id_list = [x.strip() for x in mnr_ids.split(",") if x.strip()][:200]
    if not id_list:
        return {"success": True, "stats": {}}

    rows = db.execute(text("""
        SELECT
            cs.mnr_id,
            COUNT(cs.id)             AS total_shares,
            COALESCE(SUM(h.cnt), 0)  AS total_visits
        FROM catalog_shares cs
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt
            FROM   catalog_hits ch
            WHERE  ch.share_ref_code = cs.share_ref_code
        ) h ON TRUE
        WHERE cs.mnr_id = ANY(:ids)
        GROUP BY cs.mnr_id
    """), {"ids": id_list}).fetchall()

    stats = {}
    for r in rows:
        s = int(r.total_shares or 0)
        v = int(r.total_visits or 0)
        stats[r.mnr_id] = {
            "shares": s,
            "visits": v,
            "avg":    round(v / s, 1) if s > 0 else 0.0,
        }
    return {"success": True, "stats": stats}


# ──────────────────────────────────────────────────────────────────────────────
# CATALOG ADMIN — UPLOAD & INFO  (EA and VGK Supreme only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/catalog-info", summary="Admin: get current catalog status (EA/VGK only)")
async def catalog_admin_info(
    current_user=Depends(get_current_user_hybrid),
):
    """
    DC Protocol: Returns current catalog file info for the settings upload panel.
    Access: EA (role_code='ea') or VGK Supreme (role_code='vgk4u') staff only.
    """
    _require_catalog_admin(current_user)

    pdf_path  = os.path.normpath(CATALOG_PDF_PATH)
    pages_dir = os.path.normpath(CATALOG_PAGES_DIR)

    pdf_info: dict = {}
    if os.path.isfile(pdf_path):
        stat = os.stat(pdf_path)
        pdf_info = {
            "exists":        True,
            "size_mb":       round(stat.st_size / (1024 * 1024), 2),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y %H:%M IST"),
        }
    else:
        pdf_info = {"exists": False, "size_mb": 0, "last_modified": None}

    page_count = 0
    if os.path.isdir(pages_dir):
        page_count = len([
            f for f in os.listdir(pages_dir)
            if f.startswith("page-") and f.endswith(".jpg")
        ])

    return {
        "success":    True,
        "pdf":        pdf_info,
        "page_count": page_count,
        "max_upload_mb": 150,
    }


@router.post("/admin/catalog-upload", summary="Admin: upload new catalog PDF (EA/VGK only)")
async def catalog_admin_upload(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_hybrid),
):
    """
    DC Protocol: Replace the live MNR Catalogue with a newly uploaded PDF.
    Access: EA (role_code='ea') or VGK Supreme (role_code='vgk4u') staff only.

    WVV Protocol:
      Write  — save PDF to temp location, convert pages to temp folder
      Verify — confirm at least 1 page was generated by pdftoppm
      Validate — atomic swap: replace pages/ and mnr-catalog.pdf only on success
                 old pages are kept intact if conversion fails
    """
    _require_catalog_admin(current_user)

    # ── 1. Validate MIME type (PDF only) ──────────────────────────────────────
    ct = (file.content_type or "").lower()
    fname = (file.filename or "").lower()
    if ct not in ("application/pdf", "application/octet-stream") and not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # ── 2. Read file with size guard (150 MB max) ─────────────────────────────
    data = await file.read()
    if len(data) > CATALOG_MAX_BYTES:
        size_mb = round(len(data) / (1024 * 1024), 1)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb} MB). Maximum allowed is 150 MB."
        )
    if len(data) < 4 or data[:4] != b"%PDF":
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    # ── 3. Resolve paths (DC path traversal protection) ──────────────────────
    pdf_path  = os.path.normpath(CATALOG_PDF_PATH)
    pages_dir = os.path.normpath(CATALOG_PAGES_DIR)
    catalog_dir = os.path.dirname(pdf_path)

    # Temp locations for atomic swap
    tmp_pdf       = os.path.join(catalog_dir, "_upload_tmp.pdf")
    tmp_pages_dir = os.path.join(catalog_dir, "pages_tmp")
    old_pages_bak = os.path.join(catalog_dir, "pages_bak")

    try:
        # ── 4. Save PDF to temp location ──────────────────────────────────────
        os.makedirs(catalog_dir, exist_ok=True)
        with open(tmp_pdf, "wb") as fh:
            fh.write(data)

        # ── 5. Convert pages to temp folder (WVV — Write) ────────────────────
        if os.path.isdir(tmp_pages_dir):
            shutil.rmtree(tmp_pages_dir)
        os.makedirs(tmp_pages_dir)

        result = subprocess.run(
            ["pdftoppm", "-jpeg", "-r", "150", "-scale-to", "2000",
             tmp_pdf, os.path.join(tmp_pages_dir, "page")],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            logger.warning("pdftoppm stderr: %s", result.stderr)
            raise HTTPException(
                status_code=422,
                detail=f"PDF conversion failed. The file may be corrupted or password-protected."
            )

        # ── 6. Verify page count (WVV — Verify) ──────────────────────────────
        generated = sorted([
            f for f in os.listdir(tmp_pages_dir)
            if f.startswith("page") and f.endswith(".jpg")
        ])
        page_count = len(generated)
        if page_count == 0:
            raise HTTPException(status_code=422, detail="PDF conversion produced no pages")

        # Normalise filenames to page-01.jpg … page-14.jpg
        for i, old_name in enumerate(generated, start=1):
            new_name = f"page-{i:02d}.jpg"
            if old_name != new_name:
                os.rename(
                    os.path.join(tmp_pages_dir, old_name),
                    os.path.join(tmp_pages_dir, new_name)
                )

        # ── 7. Atomic swap (WVV — Validate) ──────────────────────────────────
        # Back up existing pages
        if os.path.isdir(pages_dir):
            if os.path.isdir(old_pages_bak):
                shutil.rmtree(old_pages_bak)
            shutil.copytree(pages_dir, old_pages_bak)

        # Replace pages directory
        if os.path.isdir(pages_dir):
            shutil.rmtree(pages_dir)
        shutil.move(tmp_pages_dir, pages_dir)

        # Replace PDF
        if os.path.isfile(pdf_path):
            os.remove(pdf_path)
        with open(pdf_path, "wb") as fh:
            fh.write(data)

        # Clean up backup on full success
        if os.path.isdir(old_pages_bak):
            shutil.rmtree(old_pages_bak)

        size_mb = round(len(data) / (1024 * 1024), 2)
        uploader = getattr(current_user, "emp_code", "unknown")
        logger.info(
            "CATALOG UPLOAD: %s uploaded new catalog PDF — %s MB, %d pages",
            uploader, size_mb, page_count
        )

        return {
            "success":     True,
            "page_count":  page_count,
            "size_mb":     size_mb,
            "updated_at":  datetime.now().strftime("%d %b %Y %H:%M IST"),
            "uploaded_by": uploader,
            "message":     f"Catalog updated successfully — {page_count} pages live",
        }

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="PDF conversion timed out (>120s). Try a smaller file.")
    except Exception as exc:
        logger.error("Catalog upload error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Catalog upload failed. Previous catalog is unchanged.")
    finally:
        # Always clean up temp files (never leave partial state)
        if os.path.isfile(tmp_pdf):
            os.remove(tmp_pdf)
        if os.path.isdir(tmp_pages_dir):
            shutil.rmtree(tmp_pages_dir)
