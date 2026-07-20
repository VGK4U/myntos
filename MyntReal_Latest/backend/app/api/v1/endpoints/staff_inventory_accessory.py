"""
DC-ACC-INV-001: Battery & Charger Inventory Sheet
Tracks battery and charger stock by brand × spec × batch (IN/OUT).
category = 'battery' | 'charger'

Mirrors DC-VEH-COLOR-001 pattern exactly:
  brand  ≡ model     (e.g. LTM-SMART, ELYF, Vivek)
  spec   ≡ color     (e.g. 48V30AH, 58V 6AMPS)
  batch  ≡ batch     (purchase / opening)
  WVV Protocol: Write → Verify (cap) → Validate (commit)

IST naive datetimes. Parameterised SQL only. No company_id restriction on sheet view.
Created: 2026-06-02
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Literal
from datetime import datetime, date
import pytz
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)
router = APIRouter()
IST = pytz.timezone('Asia/Kolkata')

VALID_CATEGORIES = ('battery', 'charger')


def _ist_now() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)


def _company_id(u: StaffEmployee) -> int:
    return getattr(u, 'base_company_id', None) or getattr(u, 'company_id', 1) or 1


def _check_cat(category: str):
    if category not in VALID_CATEGORIES:
        raise HTTPException(400, f"category must be 'battery' or 'charger', got '{category}'")


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0
    sub_type: Optional[str] = Field(None, max_length=30)

class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    sub_type: Optional[str] = Field(None, max_length=30)

class SpecCreate(BaseModel):
    spec_name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0

class SpecUpdate(BaseModel):
    spec_name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class BatchCreate(BaseModel):
    batch_label: str = Field(..., min_length=1, max_length=100)
    batch_date: date
    batch_type: str = Field("purchase", pattern="^(opening|purchase|sales)$")
    purchase_qty: int = Field(0, ge=0)
    ref_no: Optional[str] = Field(None, max_length=100)

class BatchUpdate(BaseModel):
    batch_label: Optional[str] = Field(None, min_length=1, max_length=100)
    batch_date: Optional[date] = None
    purchase_qty: Optional[int] = Field(None, ge=0)
    ref_no: Optional[str] = None
    is_active: Optional[bool] = None

class InEntryUpsert(BaseModel):
    batch_id: int
    brand_id: int
    spec_id: int
    qty: int = Field(..., ge=0)
    party_type: Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name: Optional[str] = Field(None, max_length=200)
    company_tag_id: Optional[int] = None

class OutEntryUpsert(BaseModel):
    batch_id: int
    brand_id: int
    spec_id: int
    party_type: Optional[str] = Field(None, max_length=20)
    party_ref_id: Optional[int] = None
    party_name: Optional[str] = Field(None, max_length=200)
    company_tag_id: Optional[int] = None
    planned_qty: int = Field(0, ge=0)
    sold_qty: int = Field(0, ge=0)
    entry_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=200)


# ── BRANDS ────────────────────────────────────────────────────────────────────

@router.get("/{category}/brands")
def list_brands(
    category: str = Path(...),
    include_inactive: bool = Query(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    inactive_filter = "" if include_inactive else "AND b.is_active = TRUE"
    rows = db.execute(text(f"""
        SELECT b.id, b.name, b.is_active, b.sort_order, b.sub_type,
               COALESCE(
                   json_agg(
                       json_build_object(
                           'id', s.id,
                           'spec_name', s.spec_name,
                           'sort_order', s.sort_order,
                           'is_active', s.is_active
                       ) ORDER BY s.sort_order, s.spec_name
                   ) FILTER (WHERE s.id IS NOT NULL), '[]'
               ) AS specs
        FROM acc_brands b
        LEFT JOIN acc_specs s ON s.brand_id = b.id
        WHERE b.category = :cat AND b.company_id = :cid {inactive_filter}
        GROUP BY b.id
        ORDER BY b.sub_type NULLS LAST, b.sort_order, b.name
    """), {"cat": category, "cid": cid}).fetchall()
    return [{"id": r[0], "name": r[1], "is_active": r[2], "sort_order": r[3],
             "sub_type": r[4], "specs": r[5] or []}
            for r in rows]


@router.post("/{category}/brands", status_code=201)
def create_brand(
    category: str = Path(...),
    payload: BrandCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    try:
        row = db.execute(text("""
            INSERT INTO acc_brands (category, company_id, name, sort_order, sub_type, created_by, created_at, updated_at)
            VALUES (:cat, :cid, :name, :so, :st, :cb, :now, :now)
            ON CONFLICT (category, company_id, name)
            DO UPDATE SET is_active = TRUE, sort_order = EXCLUDED.sort_order,
                          sub_type = EXCLUDED.sub_type, updated_at = EXCLUDED.updated_at
            RETURNING id, name, is_active, sort_order, sub_type
        """), {"cat": category, "cid": cid, "name": payload.name.strip(),
               "so": payload.sort_order, "st": payload.sub_type,
               "cb": current_user.emp_code, "now": _ist_now()}).fetchone()
        db.commit()
        return {"id": row[0], "name": row[1], "is_active": row[2], "sort_order": row[3],
                "sub_type": row[4], "specs": []}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Could not create brand: {e}")


@router.put("/{category}/brands/{brand_id}")
def update_brand(
    category: str = Path(...),
    brand_id: int = Path(...),
    payload: BrandUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    sets, params = [], {"cat": category, "cid": cid, "bid": brand_id, "now": _ist_now()}
    if payload.name is not None:
        sets.append("name = :name"); params["name"] = payload.name.strip()
    if payload.sort_order is not None:
        sets.append("sort_order = :so"); params["so"] = payload.sort_order
    if payload.is_active is not None:
        sets.append("is_active = :ia"); params["ia"] = payload.is_active
    if payload.sub_type is not None:
        sets.append("sub_type = :st"); params["st"] = payload.sub_type
    if not sets:
        raise HTTPException(400, "Nothing to update")
    sets.append("updated_at = :now")
    try:
        db.execute(text(f"""
            UPDATE acc_brands SET {', '.join(sets)}
            WHERE id = :bid AND category = :cat AND company_id = :cid
        """), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── SPECS ─────────────────────────────────────────────────────────────────────

@router.post("/{category}/brands/{brand_id}/specs", status_code=201)
def add_spec(
    category: str = Path(...),
    brand_id: int = Path(...),
    payload: SpecCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    if not db.execute(text("""
        SELECT 1 FROM acc_brands WHERE id = :bid AND category = :cat AND company_id = :cid
    """), {"bid": brand_id, "cat": category, "cid": cid}).fetchone():
        raise HTTPException(404, "Brand not found")
    try:
        row = db.execute(text("""
            INSERT INTO acc_specs (brand_id, spec_name, sort_order)
            VALUES (:bid, :sn, :so)
            ON CONFLICT (brand_id, spec_name)
            DO UPDATE SET is_active = TRUE, sort_order = EXCLUDED.sort_order
            RETURNING id, spec_name, sort_order, is_active
        """), {"bid": brand_id, "sn": payload.spec_name.strip(), "so": payload.sort_order}).fetchone()
        db.commit()
        return {"id": row[0], "spec_name": row[1], "sort_order": row[2], "is_active": row[3]}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.put("/{category}/specs/{spec_id}")
def update_spec(
    category: str = Path(...),
    spec_id: int = Path(...),
    payload: SpecUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    sets, params = [], {"cid": cid, "sid": spec_id, "cat": category}
    if payload.spec_name is not None:
        sets.append("s.spec_name = :sn"); params["sn"] = payload.spec_name.strip()
    if payload.sort_order is not None:
        sets.append("s.sort_order = :so"); params["so"] = payload.sort_order
    if payload.is_active is not None:
        sets.append("s.is_active = :ia"); params["ia"] = payload.is_active
    if not sets:
        raise HTTPException(400, "Nothing to update")
    try:
        db.execute(text(f"""
            UPDATE acc_specs s
            SET {', '.join(sets)}
            FROM acc_brands b
            WHERE s.id = :sid AND s.brand_id = b.id AND b.category = :cat AND b.company_id = :cid
        """), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── BATCHES ───────────────────────────────────────────────────────────────────

@router.get("/{category}/batches")
def list_batches(
    category: str = Path(...),
    include_inactive: bool = Query(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    where = "" if include_inactive else "AND is_active = TRUE"
    rows = db.execute(text(f"""
        SELECT id, batch_label, batch_date, batch_type, purchase_qty, ref_no, is_active, sort_order
        FROM acc_batches
        WHERE category = :cat AND company_id = :cid {where}
        ORDER BY sort_order, batch_date, id
    """), {"cat": category, "cid": cid}).fetchall()
    return [{"id": r[0], "batch_label": r[1], "batch_date": str(r[2]),
             "batch_type": r[3], "purchase_qty": r[4], "ref_no": r[5],
             "is_active": r[6], "sort_order": r[7]} for r in rows]


@router.post("/{category}/batches", status_code=201)
def create_batch(
    category: str = Path(...),
    payload: BatchCreate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    max_so = db.execute(text(
        "SELECT COALESCE(MAX(sort_order), 0) FROM acc_batches WHERE category = :cat AND company_id = :cid"
    ), {"cat": category, "cid": cid}).scalar() or 0
    try:
        row = db.execute(text("""
            INSERT INTO acc_batches
                (category, company_id, batch_label, batch_date, batch_type, purchase_qty, ref_no,
                 sort_order, created_by, created_at, updated_at)
            VALUES (:cat, :cid, :lbl, :dt, :bt, :pq, :ref, :so, :cb, :now, :now)
            RETURNING id, batch_label, batch_date, batch_type, purchase_qty, ref_no, sort_order
        """), {
            "cat": category, "cid": cid, "lbl": payload.batch_label.strip(),
            "dt": payload.batch_date, "bt": payload.batch_type,
            "pq": payload.purchase_qty, "ref": payload.ref_no,
            "so": max_so + 1, "cb": current_user.emp_code, "now": _ist_now()
        }).fetchone()
        db.commit()
        return {"id": row[0], "batch_label": row[1], "batch_date": str(row[2]),
                "batch_type": row[3], "purchase_qty": row[4], "ref_no": row[5], "sort_order": row[6]}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.put("/{category}/batches/{batch_id}")
def update_batch(
    category: str = Path(...),
    batch_id: int = Path(...),
    payload: BatchUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    cid = _company_id(current_user)
    sets, params = [], {"cat": category, "cid": cid, "bid": batch_id, "now": _ist_now()}
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
            UPDATE acc_batches SET {', '.join(sets)}
            WHERE id = :bid AND category = :cat AND company_id = :cid
        """), params)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ── IN ENTRIES (WVV) ──────────────────────────────────────────────────────────

@router.put("/{category}/in")
def upsert_in_entry(
    category: str = Path(...),
    payload: InEntryUpsert = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    batch = db.execute(text("""
        SELECT id, purchase_qty, batch_type FROM acc_batches
        WHERE id = :bid AND category = :cat AND is_active = TRUE
    """), {"bid": payload.batch_id, "cat": category}).fetchone()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch[2] != "opening" and batch[1] > 0:
        already = db.execute(text("""
            SELECT COALESCE(SUM(qty), 0) FROM acc_in
            WHERE batch_id = :bid
              AND NOT (brand_id = :brid AND spec_id = :sid)
        """), {"bid": payload.batch_id, "brid": payload.brand_id, "sid": payload.spec_id}).scalar() or 0
        if (int(already) + payload.qty) > batch[1]:
            remaining = batch[1] - int(already)
            raise HTTPException(422,
                f"WVV cap exceeded: batch total {batch[1]}, "
                f"already allocated {int(already)}, remaining {max(0, remaining)}. "
                f"Requested {payload.qty}.")
    try:
        db.execute(text("""
            INSERT INTO acc_in
                (batch_id, brand_id, spec_id, qty,
                 party_type, party_ref_id, party_name, company_tag_id,
                 created_by, created_at, updated_at)
            VALUES (:bid, :brid, :sid, :qty, :pt, :prid, :pname, :ctag, :cb, :now, :now)
            ON CONFLICT (batch_id, brand_id, spec_id)
            DO UPDATE SET
                qty            = EXCLUDED.qty,
                party_type     = EXCLUDED.party_type,
                party_ref_id   = EXCLUDED.party_ref_id,
                party_name     = EXCLUDED.party_name,
                company_tag_id = EXCLUDED.company_tag_id,
                updated_at     = EXCLUDED.updated_at,
                created_by     = EXCLUDED.created_by
        """), {
            "bid": payload.batch_id, "brid": payload.brand_id, "sid": payload.spec_id,
            "qty": payload.qty,
            "pt": payload.party_type, "prid": payload.party_ref_id,
            "pname": payload.party_name, "ctag": payload.company_tag_id,
            "cb": current_user.emp_code, "now": _ist_now()
        })
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logger.error(f"[ACC-INV] upsert_in [{category}]: {e}")
        raise HTTPException(500, f"Could not save IN entry: {e}")


# ── OUT ENTRIES ───────────────────────────────────────────────────────────────

@router.put("/{category}/out")
def upsert_out_entry(
    category: str = Path(...),
    payload: OutEntryUpsert = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    if not db.execute(text("""
        SELECT 1 FROM acc_batches WHERE id = :bid AND category = :cat AND is_active = TRUE
    """), {"bid": payload.batch_id, "cat": category}).fetchone():
        raise HTTPException(404, "Batch not found")

    entry_date = payload.entry_date or _ist_now().date()
    now = _ist_now()
    pt   = payload.party_type or ""
    prid = payload.party_ref_id if payload.party_ref_id is not None else -1

    try:
        existing = db.execute(text("""
            SELECT id FROM acc_out
            WHERE batch_id  = :bid
              AND brand_id   = :brid
              AND spec_id    = :sid
              AND COALESCE(party_type, '')   = :pt
              AND COALESCE(party_ref_id, -1) = :prid
        """), {
            "bid": payload.batch_id, "brid": payload.brand_id, "sid": payload.spec_id,
            "pt": pt, "prid": prid
        }).fetchone()

        if existing:
            db.execute(text("""
                UPDATE acc_out
                SET planned_qty    = :pq,
                    sold_qty       = :sq,
                    party_name     = :pname,
                    company_tag_id = :ctag,
                    entry_date     = :ed,
                    notes          = :notes,
                    updated_at     = :now,
                    created_by     = :cb
                WHERE id = :oid
            """), {
                "pq": payload.planned_qty, "sq": payload.sold_qty,
                "pname": payload.party_name, "ctag": payload.company_tag_id,
                "ed": entry_date, "notes": payload.notes, "now": now,
                "cb": current_user.emp_code, "oid": existing[0]
            })
        else:
            db.execute(text("""
                INSERT INTO acc_out
                    (batch_id, brand_id, spec_id,
                     party_type, party_ref_id, party_name, company_tag_id,
                     planned_qty, sold_qty, entry_date, notes,
                     created_by, created_at, updated_at)
                VALUES
                    (:bid, :brid, :sid,
                     :pt_val, :prid_val, :pname, :ctag,
                     :pq, :sq, :ed, :notes,
                     :cb, :now, :now)
            """), {
                "bid": payload.batch_id, "brid": payload.brand_id, "sid": payload.spec_id,
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
        logger.error(f"[ACC-INV] upsert_out [{category}]: {e}")
        raise HTTPException(500, f"Could not save OUT entry: {e}")


@router.get("/{category}/out")
def list_out_entries(
    category: str = Path(...),
    batch_id: Optional[int] = Query(None),
    brand_id: Optional[int] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    filters = ["ab.category = :cat AND ab.is_active = TRUE"]
    params: dict = {"cat": category}
    if batch_id:
        filters.append("o.batch_id = :bid"); params["bid"] = batch_id
    if brand_id:
        filters.append("o.brand_id = :brid"); params["brid"] = brand_id
    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT o.id, o.batch_id, o.brand_id, o.spec_id,
               o.party_type, o.party_ref_id, o.party_name,
               o.planned_qty, o.sold_qty, o.entry_date, o.notes,
               br.name AS brand_name, s.spec_name,
               ab.batch_label, o.company_tag_id,
               ac.company_name AS company_tag_name
        FROM acc_out o
        JOIN acc_batches ab ON ab.id = o.batch_id
        JOIN acc_brands br ON br.id = o.brand_id
        JOIN acc_specs s ON s.id = o.spec_id
        LEFT JOIN associated_companies ac ON ac.id = o.company_tag_id
        WHERE {where}
        ORDER BY o.entry_date DESC, o.id DESC
    """), params).fetchall()
    return [{
        "id": r[0], "batch_id": r[1], "brand_id": r[2], "spec_id": r[3],
        "party_type": r[4], "party_ref_id": r[5], "party_name": r[6],
        "planned_qty": r[7], "sold_qty": r[8],
        "entry_date": str(r[9]) if r[9] else None, "notes": r[10],
        "brand_name": r[11], "spec_name": r[12], "batch_label": r[13],
        "company_tag_id": r[14], "company_tag_name": r[15]
    } for r in rows]


# ── SHEET ─────────────────────────────────────────────────────────────────────

@router.get("/{category}/sheet")
def get_sheet(
    category: str = Path(...),
    company_id: Optional[int] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_cat(category)
    co_filter = "AND company_id = :cid" if company_id else ""
    params_cid = {"cat": category, "cid": company_id} if company_id else {"cat": category}

    batches = db.execute(text(f"""
        SELECT id, batch_label, batch_date, batch_type, purchase_qty, ref_no, sort_order
        FROM acc_batches
        WHERE category = :cat AND is_active = TRUE {co_filter}
        ORDER BY sort_order, batch_date, id
    """), params_cid).fetchall()

    brands = db.execute(text(f"""
        SELECT b.id, b.name, b.sort_order, b.sub_type,
               COALESCE(
                   json_agg(
                       json_build_object('id', s.id, 'spec_name', s.spec_name, 'sort_order', s.sort_order)
                       ORDER BY s.sort_order, s.spec_name
                   ) FILTER (WHERE s.id IS NOT NULL), '[]'
               ) AS specs
        FROM acc_brands b
        LEFT JOIN acc_specs s ON s.brand_id = b.id AND s.is_active = TRUE
        WHERE b.category = :cat AND b.is_active = TRUE {co_filter}
        GROUP BY b.id
        ORDER BY b.sub_type NULLS LAST, b.sort_order, b.name
    """), params_cid).fetchall()

    in_rows = db.execute(text(f"""
        SELECT i.batch_id, i.brand_id, i.spec_id, i.qty, i.party_type, i.party_name
        FROM acc_in i
        JOIN acc_batches ab ON ab.id = i.batch_id
        WHERE ab.category = :cat AND ab.is_active = TRUE {co_filter}
    """), params_cid).fetchall()
    in_map = {(r[0], r[1], r[2]): {"qty": r[3], "party_type": r[4], "party_name": r[5]}
              for r in in_rows}

    out_rows = db.execute(text(f"""
        SELECT o.batch_id, o.brand_id, o.spec_id,
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
        FROM acc_out o
        JOIN acc_batches ab ON ab.id = o.batch_id
        WHERE ab.category = :cat AND ab.is_active = TRUE {co_filter}
        GROUP BY o.batch_id, o.brand_id, o.spec_id
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

    brand_list = []
    for br in brands:
        specs_raw = br[4] or []   # br[3]=sub_type, br[4]=specs
        spec_rows = []
        for s in specs_raw:
            in_by_batch, out_by_batch = {}, {}
            total_in = total_planned = total_sold = 0
            for b in batches:
                in_data = in_map.get((b[0], br[0], s["id"]), {"qty": 0})
                od = out_map.get((b[0], br[0], s["id"]), {"planned": 0, "sold": 0, "party_detail": []})
                iq = in_data["qty"]
                in_by_batch[str(b[0])] = iq
                out_by_batch[str(b[0])] = od
                total_in += iq
                total_planned += od["planned"]
                total_sold += od["sold"]
            spec_rows.append({
                "spec_id": s["id"], "spec_name": s["spec_name"],
                "in": in_by_batch, "out": out_by_batch,
                "total_in": total_in,
                "total_planned": total_planned,
                "total_sold": total_sold,
                "final_balance": total_in - total_planned - total_sold
            })
        brand_list.append({
            "brand_id": br[0], "brand_name": br[1], "sort_order": br[2],
            "sub_type": br[3],
            "specs": spec_rows
        })

    return {
        "batches": batch_list,
        "brands": brand_list,
        "out_batch_ids": out_batch_ids
    }


# ── PARTY SEARCH (shared, no category needed) ─────────────────────────────────

@router.get("/parties/search")
def search_parties(
    q: str = Query("", max_length=100),
    side: str = Query("in", pattern="^(in|out)$"),
    limit: int = Query(30, ge=1, le=80),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    q_like = f"%{q}%" if q.strip() else "%"
    per_src = max(10, limit // 3)
    results: list = []

    if side == "in":
        rows = db.execute(text("""
            SELECT id, vendor_code, vendor_name, 'VENDOR' AS pt
            FROM vendor_master WHERE is_active = TRUE
              AND (vendor_name ILIKE :q OR vendor_code ILIKE :q)
            ORDER BY vendor_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        rows = db.execute(text("""
            SELECT id, emp_code, full_name, 'STAFF' AS pt
            FROM staff_employees WHERE status = 'active'
              AND (full_name ILIKE :q OR emp_code ILIKE :q)
            ORDER BY full_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        rows = db.execute(text("""
            SELECT id, partner_code, partner_name, 'PARTNER' AS pt
            FROM official_partners WHERE is_active = TRUE
              AND (partner_name ILIKE :q OR partner_code ILIKE :q)
            ORDER BY partner_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        rows = db.execute(text("""
            SELECT id, company_code, company_name, 'COMPANY' AS pt
            FROM associated_companies
            WHERE (company_name ILIKE :q OR company_code ILIKE :q)
            ORDER BY company_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

    else:
        rows = db.execute(text("""
            SELECT id, partner_code, partner_name,
                   CASE WHEN vgk_role IS NOT NULL AND vgk_role != '' THEN 'VGK' ELSE 'PARTNER' END AS pt
            FROM official_partners WHERE is_active = TRUE
              AND (partner_name ILIKE :q OR partner_code ILIKE :q)
            ORDER BY partner_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        rows = db.execute(text("""
            SELECT id, emp_code, full_name, 'STAFF' AS pt
            FROM staff_employees WHERE status = 'active'
              AND (full_name ILIKE :q OR emp_code ILIKE :q)
            ORDER BY full_name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": r[0], "code": r[1], "name": r[2], "type": r[3]} for r in rows]

        rows = db.execute(text("""
            SELECT bev_legacy_id AS code, name, 'MNR' AS pt
            FROM "user" WHERE LOWER(user_type) IN ('member', 'user')
              AND name ILIKE :q
            ORDER BY name LIMIT :lim
        """), {"q": q_like, "lim": per_src}).fetchall()
        results += [{"id": None, "code": r[0], "name": r[1], "type": r[2]} for r in rows]

    return results[:limit]


# ── COMPANIES ─────────────────────────────────────────────────────────────────

@router.get("/companies")
def list_companies(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    rows = db.execute(text("""
        SELECT id, company_code, company_name FROM associated_companies ORDER BY id
    """)).fetchall()
    return [{"id": r[0], "code": r[1], "name": r[2]} for r in rows]
