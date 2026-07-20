"""
DC-VEH-COLOR-001: Vehicle Color-Wise Inventory Sheet — v2
Accounts → Inventory → Color Sheet

Tracks EV vehicle stock by model, color, and batch.
IN  = purchase batch (WVV cap: sum of color qtys ≤ batch.purchase_qty)
      party = vendor / staff / partner / company (purchase side)
OUT = planned + sold, party-wise
      party = official partner / staff / MNR member / VGK member (sales side)
      OUT columns only appear when at least one OUT entry exists for that batch.

WVV Protocol on all writes:
  Write → Verify (cap / integrity) → Validate (commit)

IST naive datetimes throughout. Parameterised SQL only.
No company_id restriction on sheet view — all companies visible.
company_tag_id on each IN/OUT entry for reporting purposes.
Created: 2026-06-01 | v2: 2026-06-02
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, date
import pytz
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)
router = APIRouter()
IST = pytz.timezone('Asia/Kolkata')


def _ist_now() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)


def _company_id(u: StaffEmployee) -> int:
    return getattr(u, 'base_company_id', None) or getattr(u, 'company_id', 1) or 1


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0

class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class ColorCreate(BaseModel):
    color_name: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0

class ColorUpdate(BaseModel):
    color_name: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class BatchCreate(BaseModel):
    batch_label: str = Field(..., min_length=1, max_length=100)
    batch_date: date
    batch_type: str = Field("purchase", pattern="^(opening|purchase|sales)$")
    purchase_qty: int = Field(0, ge=0)
    ref_no: Optional[str] = Field(None, max_length=100)
    party_type:   Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name:   Optional[str] = Field(None, max_length=200)

class BatchUpdate(BaseModel):
    batch_label: Optional[str] = Field(None, min_length=1, max_length=100)
    batch_date: Optional[date] = None
    purchase_qty: Optional[int] = Field(None, ge=0)
    ref_no: Optional[str] = None
    is_active: Optional[bool] = None
    # set_party=True → always write party fields (allows clearing to null)
    set_party:    bool = False
    party_type:   Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name:   Optional[str] = Field(None, max_length=200)

class InEntryUpsert(BaseModel):
    batch_id: int
    model_id: int
    color_id: int
    qty: int = Field(..., ge=0)
    # Party (purchase side)
    party_type: Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name: Optional[str] = Field(None, max_length=200)
    company_tag_id: Optional[int] = None

class OutEntryUpsert(BaseModel):
    batch_id: int
    model_id: int
    color_id: int
    # Party (sales side)
    party_type: Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name: Optional[str] = Field(None, max_length=200)
    company_tag_id: Optional[int] = None
    planned_qty: int = Field(0, ge=0)
    sold_qty: int = Field(0, ge=0)
    entry_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=200)


# ── MODELS ────────────────────────────────────────────────────────────────────

@router.get("/models")
def list_models(
    include_inactive: bool = Query(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    inactive_filter = "" if include_inactive else "AND m.is_active = TRUE"
    rows = db.execute(text(f"""
        SELECT m.id, m.name, m.is_active, m.sort_order,
               COALESCE(
                   json_agg(
                       json_build_object(
                           'id', c.id,
                           'color_name', c.color_name,
                           'sort_order', c.sort_order,
                           'is_active', c.is_active
                       ) ORDER BY c.sort_order, c.color_name
                   ) FILTER (WHERE c.id IS NOT NULL), '[]'
               ) AS colors
        FROM veh_models m
        LEFT JOIN veh_model_colors c ON c.model_id = m.id
        WHERE m.company_id = :cid {inactive_filter}
        GROUP BY m.id
        ORDER BY m.sort_order, m.name
    """), {"cid": cid}).fetchall()
    return [
        {"id": r[0], "name": r[1], "is_active": r[2], "sort_order": r[3], "colors": r[4] or []}
        for r in rows
    ]


@router.post("/models", status_code=201)
def create_model(
    payload: ModelCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    try:
        row = db.execute(text("""
            INSERT INTO veh_models (company_id, name, sort_order, created_by, created_at, updated_at)
            VALUES (:cid, :name, :so, :cb, :now, :now)
            ON CONFLICT (company_id, name)
            DO UPDATE SET is_active = TRUE, sort_order = EXCLUDED.sort_order, updated_at = EXCLUDED.updated_at
            RETURNING id, name, is_active, sort_order
        """), {"cid": cid, "name": payload.name.strip(), "so": payload.sort_order,
               "cb": current_user.emp_code, "now": _ist_now()}).fetchone()
        db.commit()
        return {"id": row[0], "name": row[1], "is_active": row[2], "sort_order": row[3], "colors": []}
    except Exception as e:
        db.rollback()
        logger.error(f"[VEH-COLOR] create_model: {e}")
        raise HTTPException(500, f"Could not create model: {e}")


@router.put("/models/{model_id}")
def update_model(
    model_id: int,
    payload: ModelUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    sets, params = [], {"cid": cid, "mid": model_id, "now": _ist_now()}
    if payload.name is not None:
        sets.append("name = :name"); params["name"] = payload.name.strip()
    if payload.sort_order is not None:
        sets.append("sort_order = :so"); params["so"] = payload.sort_order
    if payload.is_active is not None:
        sets.append("is_active = :ia"); params["ia"] = payload.is_active
    if not sets:
        raise HTTPException(400, "Nothing to update")
    sets.append("updated_at = :now")
    try:
        db.execute(text(f"UPDATE veh_models SET {', '.join(sets)} WHERE id = :mid AND company_id = :cid"), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── COLORS ────────────────────────────────────────────────────────────────────

@router.post("/models/{model_id}/colors", status_code=201)
def add_color(
    model_id: int,
    payload: ColorCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    if not db.execute(text("SELECT 1 FROM veh_models WHERE id = :mid AND company_id = :cid"),
                      {"mid": model_id, "cid": cid}).fetchone():
        raise HTTPException(404, "Model not found")
    try:
        row = db.execute(text("""
            INSERT INTO veh_model_colors (model_id, color_name, sort_order)
            VALUES (:mid, :cn, :so)
            ON CONFLICT (model_id, color_name)
            DO UPDATE SET is_active = TRUE, sort_order = EXCLUDED.sort_order
            RETURNING id, color_name, sort_order, is_active
        """), {"mid": model_id, "cn": payload.color_name.strip(), "so": payload.sort_order}).fetchone()
        db.commit()
        return {"id": row[0], "color_name": row[1], "sort_order": row[2], "is_active": row[3]}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.put("/colors/{color_id}")
def update_color(
    color_id: int,
    payload: ColorUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    sets, params = [], {"cid": cid, "coid": color_id}
    if payload.color_name is not None:
        sets.append("c.color_name = :cn"); params["cn"] = payload.color_name.strip()
    if payload.sort_order is not None:
        sets.append("c.sort_order = :so"); params["so"] = payload.sort_order
    if payload.is_active is not None:
        sets.append("c.is_active = :ia"); params["ia"] = payload.is_active
    if not sets:
        raise HTTPException(400, "Nothing to update")
    try:
        db.execute(text(f"""
            UPDATE veh_model_colors c
            SET {', '.join(sets)}
            FROM veh_models m
            WHERE c.id = :coid AND c.model_id = m.id AND m.company_id = :cid
        """), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── BATCHES ───────────────────────────────────────────────────────────────────

@router.get("/batches")
def list_batches(
    include_inactive: bool = Query(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    where = "" if include_inactive else "AND is_active = TRUE"
    rows = db.execute(text(f"""
        SELECT id, batch_label, batch_date, batch_type, purchase_qty, ref_no, is_active, sort_order,
               party_type, party_ref_id, party_name
        FROM veh_color_batches
        WHERE company_id = :cid {where}
        ORDER BY sort_order, batch_date, id
    """), {"cid": cid}).fetchall()
    return [{"id": r[0], "batch_label": r[1], "batch_date": str(r[2]),
             "batch_type": r[3], "purchase_qty": r[4], "ref_no": r[5],
             "is_active": r[6], "sort_order": r[7],
             "party_type": r[8], "party_ref_id": r[9], "party_name": r[10]} for r in rows]


@router.post("/batches", status_code=201)
def create_batch(
    payload: BatchCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    max_so = db.execute(text(
        "SELECT COALESCE(MAX(sort_order), 0) FROM veh_color_batches WHERE company_id = :cid"
    ), {"cid": cid}).scalar() or 0
    try:
        row = db.execute(text("""
            INSERT INTO veh_color_batches
                (company_id, batch_label, batch_date, batch_type, purchase_qty, ref_no,
                 party_type, party_ref_id, party_name,
                 sort_order, created_by, created_at, updated_at)
            VALUES (:cid, :lbl, :dt, :bt, :pq, :ref, :pty, :prid, :pnm, :so, :cb, :now, :now)
            RETURNING id, batch_label, batch_date, batch_type, purchase_qty, ref_no, sort_order,
                      party_type, party_ref_id, party_name
        """), {
            "cid": cid, "lbl": payload.batch_label.strip(), "dt": payload.batch_date,
            "bt": payload.batch_type, "pq": payload.purchase_qty, "ref": payload.ref_no,
            "pty": payload.party_type, "prid": payload.party_ref_id, "pnm": payload.party_name,
            "so": max_so + 1, "cb": current_user.emp_code, "now": _ist_now()
        }).fetchone()
        db.commit()
        return {"id": row[0], "batch_label": row[1], "batch_date": str(row[2]),
                "batch_type": row[3], "purchase_qty": row[4], "ref_no": row[5], "sort_order": row[6],
                "party_type": row[7], "party_ref_id": row[8], "party_name": row[9]}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.put("/batches/{batch_id}")
def update_batch(
    batch_id: int,
    payload: BatchUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    cid = _company_id(current_user)
    sets, params = [], {"cid": cid, "bid": batch_id, "now": _ist_now()}
    if payload.batch_label is not None:
        sets.append("batch_label = :lbl"); params["lbl"] = payload.batch_label.strip()
    if payload.batch_date is not None:
        sets.append("batch_date = :dt"); params["dt"] = payload.batch_date
    if payload.purchase_qty is not None:
        sets.append("purchase_qty = :pq"); params["pq"] = payload.purchase_qty
    if payload.ref_no is not None:
        sets.append("ref_no = :ref"); params["ref"] = payload.ref_no
    if payload.is_active is not None:
        sets.append("is_active = :ia"); params["ia"] = payload.is_active
    if not sets:
        raise HTTPException(400, "Nothing to update")
    sets.append("updated_at = :now")
    try:
        db.execute(text(f"""
            UPDATE veh_color_batches SET {', '.join(sets)}
            WHERE id = :bid AND company_id = :cid
        """), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── IN ENTRIES (WVV) ──────────────────────────────────────────────────────────

@router.put("/in")
def upsert_in_entry(
    payload: InEntryUpsert = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC-VEH-COLOR-001 WVV:
      Write   → accept payload
      Verify  → check SUM(color qtys) for this batch ≤ batch.purchase_qty
                 (skipped for opening batches or purchase_qty == 0)
      Validate→ commit
    No company restriction on batch lookup — any active batch is writable.
    """
    batch = db.execute(text("""
        SELECT id, purchase_qty, batch_type FROM veh_color_batches
        WHERE id = :bid AND is_active = TRUE
    """), {"bid": payload.batch_id}).fetchone()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch[2] != "opening" and batch[1] > 0:
        already_allocated = db.execute(text("""
            SELECT COALESCE(SUM(qty), 0) FROM veh_color_in
            WHERE batch_id = :bid
              AND NOT (model_id = :mid AND color_id = :coid)
        """), {"bid": payload.batch_id, "mid": payload.model_id, "coid": payload.color_id}).scalar() or 0
        if (int(already_allocated) + payload.qty) > batch[1]:
            remaining = batch[1] - int(already_allocated)
            raise HTTPException(422,
                f"WVV cap exceeded: batch total {batch[1]}, "
                f"already allocated {int(already_allocated)}, "
                f"remaining {remaining}. Requested {payload.qty}.")

    try:
        db.execute(text("""
            INSERT INTO veh_color_in
                (batch_id, model_id, color_id, qty,
                 party_type, party_ref_id, party_name, company_tag_id,
                 created_by, created_at, updated_at)
            VALUES (:bid, :mid, :coid, :qty,
                    :pt, :prid, :pname, :ctag,
                    :cb, :now, :now)
            ON CONFLICT (batch_id, model_id, color_id)
            DO UPDATE SET
                qty           = EXCLUDED.qty,
                party_type    = EXCLUDED.party_type,
                party_ref_id  = EXCLUDED.party_ref_id,
                party_name    = EXCLUDED.party_name,
                company_tag_id= EXCLUDED.company_tag_id,
                updated_at    = EXCLUDED.updated_at,
                created_by    = EXCLUDED.created_by
        """), {
            "bid": payload.batch_id, "mid": payload.model_id, "coid": payload.color_id,
            "qty": payload.qty,
            "pt": payload.party_type, "prid": payload.party_ref_id,
            "pname": payload.party_name, "ctag": payload.company_tag_id,
            "cb": current_user.emp_code, "now": _ist_now()
        })
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logger.error(f"[VEH-COLOR] upsert_in_entry: {e}")
        raise HTTPException(500, f"Could not save IN entry: {e}")


# ── OUT ENTRIES ───────────────────────────────────────────────────────────────

@router.put("/out")
def upsert_out_entry(
    payload: OutEntryUpsert = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Upsert planned/sold quantities for a batch+model+color+party combination.
    Unique key: (batch_id, model_id, color_id, COALESCE(party_type,''), COALESCE(party_ref_id,-1))
    No company restriction on batch lookup.
    Bug fix: removed :pid::int PostgreSQL cast that caused psycopg2 syntax error.
    """
    if not db.execute(text("""
        SELECT 1 FROM veh_color_batches
        WHERE id = :bid AND is_active = TRUE
    """), {"bid": payload.batch_id}).fetchone():
        raise HTTPException(404, "Batch not found")

    entry_date = payload.entry_date or _ist_now().date()
    now = _ist_now()

    pt   = payload.party_type or ""
    prid = payload.party_ref_id if payload.party_ref_id is not None else -1

    try:
        existing = db.execute(text("""
            SELECT id FROM veh_color_out
            WHERE batch_id  = :bid
              AND model_id   = :mid
              AND color_id   = :coid
              AND COALESCE(party_type, '')   = :pt
              AND COALESCE(party_ref_id, -1) = :prid
        """), {
            "bid": payload.batch_id, "mid": payload.model_id, "coid": payload.color_id,
            "pt": pt, "prid": prid
        }).fetchone()

        if existing:
            db.execute(text("""
                UPDATE veh_color_out
                SET planned_qty   = :pq,
                    sold_qty      = :sq,
                    party_name    = :pname,
                    company_tag_id= :ctag,
                    entry_date    = :ed,
                    notes         = :notes,
                    updated_at    = :now,
                    created_by    = :cb
                WHERE id = :oid
            """), {
                "pq": payload.planned_qty, "sq": payload.sold_qty,
                "pname": payload.party_name, "ctag": payload.company_tag_id,
                "ed": entry_date, "notes": payload.notes, "now": now,
                "cb": current_user.emp_code, "oid": existing[0]
            })
        else:
            db.execute(text("""
                INSERT INTO veh_color_out
                    (batch_id, model_id, color_id,
                     party_type, party_ref_id, party_name, company_tag_id,
                     planned_qty, sold_qty, entry_date, notes,
                     created_by, created_at, updated_at)
                VALUES
                    (:bid, :mid, :coid,
                     :pt_val, :prid_val, :pname, :ctag,
                     :pq, :sq, :ed, :notes,
                     :cb, :now, :now)
            """), {
                "bid": payload.batch_id, "mid": payload.model_id, "coid": payload.color_id,
                "pt_val": payload.party_type, "prid_val": payload.party_ref_id,
                "pname": payload.party_name, "ctag": payload.company_tag_id,
                "pq": payload.planned_qty, "sq": payload.sold_qty,
                "ed": entry_date, "notes": payload.notes,
                "cb": current_user.emp_code, "now": now
            })
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logger.error(f"[VEH-COLOR] upsert_out_entry: {e}")
        raise HTTPException(500, f"Could not save OUT entry: {e}")


@router.get("/out")
def list_out_entries(
    batch_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    party_type: Optional[str] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    filters = ["b.is_active = TRUE"]
    params: dict = {}
    if batch_id:
        filters.append("o.batch_id = :bid"); params["bid"] = batch_id
    if model_id:
        filters.append("o.model_id = :mid"); params["mid"] = model_id
    if party_type:
        filters.append("o.party_type = :pt"); params["pt"] = party_type
    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT o.id, o.batch_id, o.model_id, o.color_id,
               o.party_type, o.party_ref_id, o.party_name,
               o.planned_qty, o.sold_qty, o.entry_date, o.notes,
               m.name AS model_name, c.color_name,
               b.batch_label, o.company_tag_id,
               ac.company_name AS company_tag_name
        FROM veh_color_out o
        JOIN veh_color_batches b ON b.id = o.batch_id
        JOIN veh_models m ON m.id = o.model_id
        JOIN veh_model_colors c ON c.id = o.color_id
        LEFT JOIN associated_companies ac ON ac.id = o.company_tag_id
        WHERE {where}
        ORDER BY o.entry_date DESC, o.id DESC
    """), params).fetchall()
    return [{
        "id": r[0], "batch_id": r[1], "model_id": r[2], "color_id": r[3],
        "party_type": r[4], "party_ref_id": r[5], "party_name": r[6],
        "planned_qty": r[7], "sold_qty": r[8],
        "entry_date": str(r[9]) if r[9] else None, "notes": r[10],
        "model_name": r[11], "color_name": r[12], "batch_label": r[13],
        "company_tag_id": r[14], "company_tag_name": r[15]
    } for r in rows]


# ── PARTY SEARCH (typeahead) ───────────────────────────────────────────────────

@router.get("/parties/search")
def search_parties(
    q: str = Query("", max_length=100),
    side: str = Query("in", pattern="^(in|out)$"),
    limit: int = Query(30, ge=1, le=80),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Typeahead party search — no company restriction.
    side=in  → purchase-side: vendors, staff, official partners, associated companies
    side=out → sales-side: official partners, staff, MNR members, VGK members
    """
    q_like = f"%{q}%" if q.strip() else "%"
    per_src = max(10, limit // 3)
    results: list = []

    if side == "in":
        # Vendors
        rows = db.execute(text("""
            SELECT id, vendor_code, vendor_name, 'VENDOR' AS pt
            FROM vendor_master
            WHERE is_active = TRUE
              AND (vendor_name ILIKE :q OR vendor_code ILIKE :q)
            ORDER BY vendor_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        # Staff
        rows = db.execute(text("""
            SELECT id, emp_code, full_name, 'STAFF' AS pt
            FROM staff_employees
            WHERE status = 'active'
              AND (full_name ILIKE :q OR emp_code ILIKE :q)
            ORDER BY full_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        # Official Partners
        rows = db.execute(text("""
            SELECT id, partner_code, partner_name, 'PARTNER' AS pt
            FROM official_partners
            WHERE is_active = TRUE
              AND (partner_name ILIKE :q OR partner_code ILIKE :q)
            ORDER BY partner_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        # Associated Companies
        rows = db.execute(text("""
            SELECT id, company_code, company_name, 'COMPANY' AS pt
            FROM associated_companies
            WHERE (company_name ILIKE :q OR company_code ILIKE :q)
            ORDER BY company_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

    else:  # out — sales side
        # Official Partners (non-VGK or VGK alike — show all)
        rows = db.execute(text("""
            SELECT id, partner_code, partner_name,
                   CASE WHEN vgk_role IS NOT NULL AND vgk_role != '' THEN 'VGK' ELSE 'PARTNER' END AS pt
            FROM official_partners
            WHERE is_active = TRUE
              AND (partner_name ILIKE :q OR partner_code ILIKE :q)
            ORDER BY partner_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        # Staff
        rows = db.execute(text("""
            SELECT id, emp_code, full_name, 'STAFF' AS pt
            FROM staff_employees
            WHERE status = 'active'
              AND (full_name ILIKE :q OR emp_code ILIKE :q)
            ORDER BY full_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        # MNR Members (from user table)
        rows = db.execute(text("""
            SELECT bev_legacy_id AS code, name, 'MNR' AS pt
            FROM "user"
            WHERE LOWER(user_type) IN ('member', 'user')
              AND name ILIKE :q
            ORDER BY name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": None, "code": r[0], "name": r[1], "type": r[2]} for r in rows]

    return results[:limit]


# ── COMPANIES (for dropdowns) ─────────────────────────────────────────────────

@router.get("/companies")
def list_companies(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    rows = db.execute(text("""
        SELECT id, company_code, company_name
        FROM associated_companies
        ORDER BY id
    """)).fetchall()
    return [{"id": r[0], "code": r[1], "name": r[2]} for r in rows]


# ── SHEET SUMMARY ─────────────────────────────────────────────────────────────

@router.get("/sheet")
def get_sheet(
    company_id: Optional[int] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Full color sheet: models × colors × batches — IN and OUT totals.
    No company restriction by default — all companies are visible.
    Pass company_id to filter by a specific company.
    Returns out_batch_ids: batch IDs that have at least one OUT entry
    (frontend shows OUT columns only for these batches).
    """
    co_filter_batch = "AND company_id = :cid" if company_id else ""
    co_filter_model = "AND m.company_id = :cid" if company_id else ""
    params_cid = {"cid": company_id} if company_id else {}

    batches = db.execute(text(f"""
        SELECT id, batch_label, batch_date, batch_type, purchase_qty, ref_no, sort_order
        FROM veh_color_batches
        WHERE is_active = TRUE {co_filter_batch}
        ORDER BY sort_order, batch_date, id
    """), params_cid).fetchall()

    models = db.execute(text(f"""
        SELECT m.id, m.name, m.sort_order,
               COALESCE(
                   json_agg(
                       json_build_object('id', c.id, 'color_name', c.color_name, 'sort_order', c.sort_order)
                       ORDER BY c.sort_order, c.color_name
                   ) FILTER (WHERE c.id IS NOT NULL), '[]'
               ) AS colors
        FROM veh_models m
        LEFT JOIN veh_model_colors c ON c.model_id = m.id AND c.is_active = TRUE
        WHERE m.is_active = TRUE {co_filter_model}
        GROUP BY m.id
        ORDER BY m.sort_order, m.name
    """), params_cid).fetchall()

    # IN map: (batch_id, model_id, color_id) → qty
    in_rows = db.execute(text(f"""
        SELECT i.batch_id, i.model_id, i.color_id, i.qty,
               i.party_type, i.party_name
        FROM veh_color_in i
        JOIN veh_color_batches b ON b.id = i.batch_id
        WHERE b.is_active = TRUE {co_filter_batch}
    """), params_cid).fetchall()
    in_map = {(r[0], r[1], r[2]): {"qty": r[3], "party_type": r[4], "party_name": r[5]}
              for r in in_rows}

    # OUT map: (batch_id, model_id, color_id) → {planned, sold, detail[]}
    out_rows = db.execute(text(f"""
        SELECT o.batch_id, o.model_id, o.color_id,
               SUM(o.planned_qty) AS planned,
               SUM(o.sold_qty)    AS sold,
               COALESCE(
                   json_agg(json_build_object(
                       'party_type',  o.party_type,
                       'party_ref_id',o.party_ref_id,
                       'party_name',  COALESCE(o.party_name, 'General'),
                       'planned',     o.planned_qty,
                       'sold',        o.sold_qty,
                       'notes',       o.notes
                   ) ORDER BY o.id) FILTER (WHERE o.id IS NOT NULL), '[]'
               ) AS party_detail
        FROM veh_color_out o
        JOIN veh_color_batches b ON b.id = o.batch_id
        WHERE b.is_active = TRUE {co_filter_batch}
        GROUP BY o.batch_id, o.model_id, o.color_id
    """), params_cid).fetchall()
    out_map = {(r[0], r[1], r[2]): {
        "planned": int(r[3] or 0),
        "sold":    int(r[4] or 0),
        "party_detail": r[5] or []
    } for r in out_rows}

    # OUT columns = ALL active batches (so Plan/Sold cells are always available)
    out_batch_ids = [b[0] for b in batches]

    batch_list = [{"id": b[0], "batch_label": b[1], "batch_date": str(b[2]),
                   "batch_type": b[3], "purchase_qty": b[4], "ref_no": b[5],
                   "sort_order": b[6], "has_out": b[0] in set(out_batch_ids)}
                  for b in batches]

    model_list = []
    for m in models:
        colors_raw = m[3] or []
        color_rows = []
        for c in colors_raw:
            in_by_batch, out_by_batch = {}, {}
            total_in = total_planned = total_sold = 0
            for b in batches:
                in_data = in_map.get((b[0], m[0], c["id"]), {"qty": 0})
                od = out_map.get((b[0], m[0], c["id"]), {"planned": 0, "sold": 0, "party_detail": []})
                iq = in_data["qty"]
                in_by_batch[str(b[0])] = iq
                out_by_batch[str(b[0])] = od
                total_in += iq
                total_planned += od["planned"]
                total_sold += od["sold"]
            color_rows.append({
                "color_id": c["id"], "color_name": c["color_name"],
                "in": in_by_batch, "out": out_by_batch,
                "total_in": total_in,
                "total_planned": total_planned,
                "total_sold": total_sold,
                "final_balance": total_in - total_planned - total_sold
            })
        model_list.append({
            "model_id": m[0], "model_name": m[1], "sort_order": m[2],
            "colors": color_rows
        })

    return {
        "batches": batch_list,
        "models": model_list,
        "out_batch_ids": out_batch_ids
    }
