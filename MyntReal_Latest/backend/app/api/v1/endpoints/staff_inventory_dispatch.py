"""
DC-INV-DISPATCH-001: Inventory Dispatch & Warranty Ledger API
Battery · Vehicle · Charger dispatch tracking with full CRUD, filters, and lookup endpoints.

WVV Protocol: Write → Verify → Validate (hash check on updates)
IST naive datetimes. Parameterised SQL only.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel as PydanticBase, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import hashlib, json, logging

from app.core.database import get_db
from app.models.staff_accounts import (
    InventoryBatteryDispatch,
    InventoryVehicleDispatch,
    InventoryChargerDispatch,
    VendorMaster,
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _wvv_hash(obj: dict) -> str:
    s = json.dumps({k: str(v) for k, v in sorted(obj.items()) if v is not None}, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _calc_warranty_end(dispatch_date_val, warranty_months_val) -> Optional[date]:
    if not dispatch_date_val or not warranty_months_val:
        return None
    if isinstance(dispatch_date_val, str):
        try:
            dispatch_date_val = date.fromisoformat(dispatch_date_val)
        except Exception:
            return None
    try:
        return dispatch_date_val + relativedelta(months=int(warranty_months_val))
    except Exception:
        return None


def _company_id(u) -> int:
    return getattr(u, 'base_company_id', None) or getattr(u, 'company_id', 1) or 1


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class BatteryDispatchIn(PydanticBase):
    entry_date:          Optional[date]   = None
    vendor_invoice_no:   Optional[str]   = Field(None, max_length=100)
    vendor_code:         Optional[str]   = Field(None, max_length=20)
    battery_spec:        Optional[str]   = Field(None, max_length=100)
    warranty_months:     Optional[int]   = None
    battery_serial_no:   Optional[str]   = Field(None, max_length=150)
    status:              Optional[str]   = Field(None, max_length=30)
    dispatch_date:       Optional[date]  = None
    dispatch_month:      Optional[str]   = Field(None, max_length=20)
    assigned_vehicle_no: Optional[str]   = Field(None, max_length=100)
    sales_invoice_no:    Optional[str]   = Field(None, max_length=100)
    owner_name:          Optional[str]   = Field(None, max_length=200)
    location:            Optional[str]   = Field(None, max_length=200)
    deliverable:         Optional[str]   = Field(None, max_length=200)
    comments:            Optional[str]   = None

class BatteryDispatchUpdate(BatteryDispatchIn):
    wvv_hash: str

class VehicleDispatchIn(PydanticBase):
    vehicle_no:          Optional[str]   = Field(None, max_length=50)
    vendor_invoice_no:   Optional[str]   = Field(None, max_length=100)
    vendor_code:         Optional[str]   = Field(None, max_length=20)
    vehicle_model:       Optional[str]   = Field(None, max_length=100)
    vehicle_color:       Optional[str]   = Field(None, max_length=50)
    chassis_no:          Optional[str]   = Field(None, max_length=100)
    motor_no:            Optional[str]   = Field(None, max_length=100)
    status:              Optional[str]   = Field(None, max_length=30)
    dispatch_date:       Optional[date]  = None
    dispatch_month:      Optional[str]   = Field(None, max_length=20)
    sales_invoice_no:    Optional[str]   = Field(None, max_length=100)
    customer_name:       Optional[str]   = Field(None, max_length=200)
    contact_number:      Optional[str]   = Field(None, max_length=30)
    battery_spec:        Optional[str]   = Field(None, max_length=100)
    battery_serial_no:   Optional[str]   = Field(None, max_length=150)
    charger_no:          Optional[str]   = Field(None, max_length=100)
    address:             Optional[str]   = Field(None, max_length=500)
    return_date:         Optional[date]  = None
    comments:            Optional[str]   = None

class VehicleDispatchUpdate(VehicleDispatchIn):
    wvv_hash: str

class ChargerDispatchIn(PydanticBase):
    entry_date:          Optional[date]   = None
    vendor_invoice_no:   Optional[str]   = Field(None, max_length=100)
    vendor_code:         Optional[str]   = Field(None, max_length=20)
    charger_spec:        Optional[str]   = Field(None, max_length=100)
    warranty_months:     Optional[int]   = None
    charger_no:          Optional[str]   = Field(None, max_length=150)
    status:              Optional[str]   = Field(None, max_length=30)
    dispatch_date:       Optional[date]  = None
    dispatch_month:      Optional[str]   = Field(None, max_length=20)
    assigned_vehicle_no: Optional[str]   = Field(None, max_length=100)
    sales_invoice_no:    Optional[str]   = Field(None, max_length=100)
    owner_name:          Optional[str]   = Field(None, max_length=200)
    location:            Optional[str]   = Field(None, max_length=200)
    deliverable:         Optional[str]   = Field(None, max_length=200)
    comments:            Optional[str]   = None

class ChargerDispatchUpdate(ChargerDispatchIn):
    wvv_hash: str


# ── LOOKUP ENDPOINTS ──────────────────────────────────────────────────────────

@router.get("/lookup/vendors")
def lookup_vendors(q: str = "", db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    """Return distinct vendor codes actually used in dispatch tables."""
    rows = db.execute(text("""
        SELECT DISTINCT vendor_code FROM (
            SELECT vendor_code FROM inventory_battery_dispatch WHERE vendor_code IS NOT NULL AND is_deleted=FALSE
            UNION
            SELECT vendor_code FROM inventory_vehicle_dispatch WHERE vendor_code IS NOT NULL AND is_deleted=FALSE
            UNION
            SELECT vendor_code FROM inventory_charger_dispatch WHERE vendor_code IS NOT NULL AND is_deleted=FALSE
        ) x
        WHERE vendor_code ILIKE :q
        ORDER BY vendor_code
    """), {"q": f"%{q}%" if q else "%"}).fetchall()
    codes = [r[0] for r in rows if r[0]]
    # Also include known short codes
    known = ["EA", "SK", "RD", "IN", "BC"]
    all_codes = sorted(set(codes) | set(known))
    return all_codes


@router.get("/lookup/battery-specs")
def lookup_battery_specs(db: Session = Depends(get_db),
                         current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT DISTINCT battery_spec FROM inventory_battery_dispatch
        WHERE battery_spec IS NOT NULL AND is_deleted = FALSE
        ORDER BY battery_spec
    """)).fetchall()
    # Also include common known specs
    known = ["60V 32AH LTM","60V 40AH LTM","60V 30AH LFP","52V 30AH LFP",
             "60V 45AH LFP","48V 32AH Gr","60V 30AH Gr","52V45AH","60V45AH","60V32AH",
             "60V40AH","60V30AH"]
    existing = {r[0] for r in rows}
    all_specs = sorted(existing | set(known))
    return all_specs


@router.get("/lookup/charger-specs")
def lookup_charger_specs(db: Session = Depends(get_db),
                         current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT DISTINCT charger_spec FROM inventory_charger_dispatch
        WHERE charger_spec IS NOT NULL AND is_deleted = FALSE
        ORDER BY charger_spec
    """)).fetchall()
    known = ["5A Charger","10A Charger","15A Charger","20A Charger","Smart Charger"]
    existing = {r[0] for r in rows}
    return sorted(existing | set(known))


@router.get("/lookup/vehicle-models")
def lookup_vehicle_models(db: Session = Depends(get_db),
                          current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT DISTINCT vehicle_model FROM inventory_vehicle_dispatch
        WHERE vehicle_model IS NOT NULL AND is_deleted = FALSE
        ORDER BY vehicle_model
    """)).fetchall()
    known = ["GT Pro","Power plus","Sweety Pro","M99","SL","DL"]
    existing = {r[0] for r in rows}
    return sorted(existing | set(known))


@router.get("/lookup/partners")
def lookup_partners(q: str = "", db: Session = Depends(get_db),
                    current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT id, partner_name, partner_code FROM official_partners
        WHERE is_active = TRUE
          AND (partner_name ILIKE :q OR partner_code ILIKE :q)
        ORDER BY partner_name LIMIT 50
    """), {"q": f"%{q}%"}).fetchall()
    return [{"id": r[0], "partner_name": r[1], "partner_code": r[2]} for r in rows]


@router.get("/lookup/invoice-nos")
def lookup_invoice_nos(q: str = "", db: Session = Depends(get_db),
                       current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT DISTINCT vendor_invoice_no FROM purchase_invoice_uploads
        WHERE vendor_invoice_no ILIKE :q
        ORDER BY vendor_invoice_no LIMIT 40
    """), {"q": f"%{q}%"}).fetchall()
    return [r[0] for r in rows if r[0]]


@router.get("/lookup/vehicle-nos")
def lookup_vehicle_nos(q: str = "", db: Session = Depends(get_db),
                       current_user=Depends(get_current_staff_user)):
    rows = db.execute(text("""
        SELECT DISTINCT vehicle_no FROM inventory_vehicle_dispatch
        WHERE vehicle_no IS NOT NULL AND vehicle_no ILIKE :q AND is_deleted = FALSE
        ORDER BY vehicle_no LIMIT 40
    """), {"q": f"%{q}%"}).fetchall()
    return [r[0] for r in rows]


# ── BATTERY CRUD ──────────────────────────────────────────────────────────────

@router.get("/battery")
def list_battery(
    status:         Optional[str]  = None,
    vendor_code:    Optional[str]  = None,
    battery_spec:   Optional[str]  = None,
    dispatch_month: Optional[str]  = None,
    date_from:      Optional[date] = None,
    date_to:        Optional[date] = None,
    warranty_status:Optional[str]  = None,
    search:         Optional[str]  = None,
    limit:          int = 500,
    offset:         int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    filters = ["is_deleted = FALSE"]
    params: dict = {}
    if status:
        filters.append("status = :status"); params["status"] = status
    if vendor_code:
        filters.append("vendor_code = :vendor_code"); params["vendor_code"] = vendor_code
    if battery_spec:
        filters.append("battery_spec = :battery_spec"); params["battery_spec"] = battery_spec
    if dispatch_month:
        filters.append("dispatch_month = :dispatch_month"); params["dispatch_month"] = dispatch_month
    if date_from:
        filters.append("dispatch_date >= :date_from"); params["date_from"] = date_from
    if date_to:
        filters.append("dispatch_date <= :date_to"); params["date_to"] = date_to
    if warranty_status == "active":
        filters.append("warranty_end_date >= CURRENT_DATE")
    elif warranty_status == "expired":
        filters.append("warranty_end_date < CURRENT_DATE AND warranty_end_date IS NOT NULL")
    if search:
        filters.append("""(battery_serial_no ILIKE :search OR sales_invoice_no ILIKE :search
                           OR owner_name ILIKE :search OR assigned_vehicle_no ILIKE :search
                           OR location ILIKE :search)""")
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT * FROM inventory_battery_dispatch
        WHERE {where}
        ORDER BY id ASC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": limit, "offset": offset}).mappings().fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM inventory_battery_dispatch WHERE {where}
    """), params).scalar()

    data = [dict(r) for r in rows]
    for d in data:
        for k in ("entry_date", "dispatch_date", "warranty_end_date", "created_at", "updated_at"):
            if d.get(k) and hasattr(d[k], 'isoformat'):
                d[k] = d[k].isoformat()
        d["wvv_hash"] = _wvv_hash({
            "id": d["id"], "battery_spec": d.get("battery_spec"),
            "status": d.get("status"), "dispatch_date": d.get("dispatch_date"),
        })
    return {"items": data, "total": total}


@router.post("/battery")
def create_battery(payload: BatteryDispatchIn = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    obj = InventoryBatteryDispatch(
        company_id        = _company_id(current_user),
        entry_date        = payload.entry_date,
        vendor_invoice_no = payload.vendor_invoice_no,
        vendor_code       = payload.vendor_code,
        battery_spec      = payload.battery_spec,
        warranty_months   = payload.warranty_months,
        battery_serial_no = payload.battery_serial_no,
        status            = payload.status,
        dispatch_date     = payload.dispatch_date,
        dispatch_month    = dispatch_month,
        assigned_vehicle_no = payload.assigned_vehicle_no,
        sales_invoice_no  = payload.sales_invoice_no,
        owner_name        = payload.owner_name,
        location          = payload.location,
        warranty_end_date = warranty_end,
        deliverable       = payload.deliverable,
        comments          = payload.comments,
        created_by_id     = current_user.id,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return {"ok": True, "id": obj.id, "item": obj.to_dict()}


@router.post("/battery/bulk")
def create_battery_bulk(items: List[BatteryDispatchIn] = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    """Bulk-create battery dispatch records (multi-add modal / batch hook)."""
    cid = _company_id(current_user)
    created = []
    for payload in items:
        warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
        dm = payload.dispatch_month
        if not dm and payload.dispatch_date:
            dm = payload.dispatch_date.strftime("%b'%y")
        obj = InventoryBatteryDispatch(
            company_id=cid, entry_date=payload.entry_date,
            vendor_invoice_no=payload.vendor_invoice_no, vendor_code=payload.vendor_code,
            battery_spec=payload.battery_spec, warranty_months=payload.warranty_months,
            battery_serial_no=payload.battery_serial_no, status=payload.status,
            dispatch_date=payload.dispatch_date, dispatch_month=dm,
            assigned_vehicle_no=payload.assigned_vehicle_no, sales_invoice_no=payload.sales_invoice_no,
            owner_name=payload.owner_name, location=payload.location,
            warranty_end_date=warranty_end, deliverable=payload.deliverable,
            comments=payload.comments, created_by_id=current_user.id,
        )
        db.add(obj); created.append(obj)
    db.commit()
    return {"ok": True, "created": len(created), "ids": [o.id for o in created]}


class _PatchIn(PydanticBase):
    field: str
    value: Optional[str] = None

_BAT_PATCH_FIELDS = {
    'entry_date','vendor_code','vendor_invoice_no','battery_spec','warranty_months',
    'battery_serial_no','status','dispatch_date','dispatch_month','assigned_vehicle_no',
    'sales_invoice_no','owner_name','location','warranty_end_date','deliverable','comments'
}

def _cast_val(field: str, val):
    if val is None or val == '':
        return None
    if field in ('entry_date','dispatch_date','warranty_end_date','return_date'):
        return date.fromisoformat(val)
    if field == 'warranty_months':
        return int(val)
    return str(val)

@router.patch("/battery/{item_id}")
def patch_battery_field(item_id: int, payload: _PatchIn = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    if payload.field not in _BAT_PATCH_FIELDS:
        raise HTTPException(400, f"Field '{payload.field}' not patchable")
    obj = db.query(InventoryBatteryDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj: raise HTTPException(404, "Battery dispatch record not found")
    setattr(obj, payload.field, _cast_val(payload.field, payload.value))
    if payload.field in ('dispatch_date', 'warranty_months'):
        obj.warranty_end_date = _calc_warranty_end(obj.dispatch_date, obj.warranty_months)
    obj.updated_by_id = current_user.id
    db.commit(); db.refresh(obj)
    return {"ok": True, "warranty_end_date": str(obj.warranty_end_date) if obj.warranty_end_date else None}


@router.put("/battery/{item_id}")
def update_battery(item_id: int, payload: BatteryDispatchUpdate = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryBatteryDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Battery dispatch record not found")
    expected = _wvv_hash({"id": obj.id, "battery_spec": obj.battery_spec,
                           "status": obj.status, "dispatch_date": obj.dispatch_date})
    if payload.wvv_hash != expected:
        raise HTTPException(409, "WVV hash mismatch — record may have changed. Please refresh.")

    warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    for fld, val in [
        ("entry_date", payload.entry_date), ("vendor_invoice_no", payload.vendor_invoice_no),
        ("vendor_code", payload.vendor_code), ("battery_spec", payload.battery_spec),
        ("warranty_months", payload.warranty_months), ("battery_serial_no", payload.battery_serial_no),
        ("status", payload.status), ("dispatch_date", payload.dispatch_date),
        ("dispatch_month", dispatch_month), ("assigned_vehicle_no", payload.assigned_vehicle_no),
        ("sales_invoice_no", payload.sales_invoice_no), ("owner_name", payload.owner_name),
        ("location", payload.location), ("warranty_end_date", warranty_end),
        ("deliverable", payload.deliverable), ("comments", payload.comments),
        ("updated_by_id", current_user.id),
    ]:
        setattr(obj, fld, val)
    db.commit(); db.refresh(obj)
    return {"ok": True, "item": obj.to_dict()}


@router.delete("/battery/{item_id}")
def delete_battery(item_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryBatteryDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Battery dispatch record not found")
    obj.is_deleted = True; obj.updated_by_id = current_user.id
    db.commit()
    return {"ok": True}


# ── BATTERY GET BY ID ─────────────────────────────────────────────────────────

@router.get("/battery/{item_id}")
def get_battery(item_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryBatteryDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Battery dispatch record not found")
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k in ("entry_date", "dispatch_date", "warranty_end_date", "created_at", "updated_at"):
        if d.get(k) and hasattr(d[k], 'isoformat'):
            d[k] = d[k].isoformat()
    return d


# ── VEHICLE CRUD ──────────────────────────────────────────────────────────────

@router.get("/vehicle")
def list_vehicle(
    status:         Optional[str]  = None,
    vendor_code:    Optional[str]  = None,
    vehicle_model:  Optional[str]  = None,
    dispatch_month: Optional[str]  = None,
    date_from:      Optional[date] = None,
    date_to:        Optional[date] = None,
    search:         Optional[str]  = None,
    limit:          int = 500,
    offset:         int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    filters = ["is_deleted = FALSE"]
    params: dict = {}
    if status:
        filters.append("status = :status"); params["status"] = status
    if vendor_code:
        filters.append("vendor_code = :vendor_code"); params["vendor_code"] = vendor_code
    if vehicle_model:
        filters.append("vehicle_model = :vehicle_model"); params["vehicle_model"] = vehicle_model
    if dispatch_month:
        filters.append("dispatch_month = :dispatch_month"); params["dispatch_month"] = dispatch_month
    if date_from:
        filters.append("dispatch_date >= :date_from"); params["date_from"] = date_from
    if date_to:
        filters.append("dispatch_date <= :date_to"); params["date_to"] = date_to
    if search:
        filters.append("""(vehicle_no ILIKE :search OR chassis_no ILIKE :search
                           OR motor_no ILIKE :search OR customer_name ILIKE :search
                           OR sales_invoice_no ILIKE :search OR address ILIKE :search
                           OR battery_serial_no ILIKE :search OR charger_no ILIKE :search)""")
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT * FROM inventory_vehicle_dispatch
        WHERE {where}
        ORDER BY id ASC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": limit, "offset": offset}).mappings().fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM inventory_vehicle_dispatch WHERE {where}
    """), params).scalar()

    data = [dict(r) for r in rows]
    for d in data:
        for k in ("dispatch_date", "return_date", "created_at", "updated_at"):
            if d.get(k) and hasattr(d[k], 'isoformat'):
                d[k] = d[k].isoformat()
        d["wvv_hash"] = _wvv_hash({
            "id": d["id"], "vehicle_model": d.get("vehicle_model"),
            "status": d.get("status"), "dispatch_date": d.get("dispatch_date"),
        })
    return {"items": data, "total": total}


@router.post("/vehicle")
def create_vehicle(payload: VehicleDispatchIn = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    obj = InventoryVehicleDispatch(
        company_id        = _company_id(current_user),
        vehicle_no        = payload.vehicle_no,
        vendor_invoice_no = payload.vendor_invoice_no,
        vendor_code       = payload.vendor_code,
        vehicle_model     = payload.vehicle_model,
        vehicle_color     = payload.vehicle_color,
        chassis_no        = payload.chassis_no,
        motor_no          = payload.motor_no,
        status            = payload.status,
        dispatch_date     = payload.dispatch_date,
        dispatch_month    = dispatch_month,
        sales_invoice_no  = payload.sales_invoice_no,
        customer_name     = payload.customer_name,
        contact_number    = payload.contact_number,
        battery_spec      = payload.battery_spec,
        battery_serial_no = payload.battery_serial_no,
        charger_no        = payload.charger_no,
        address           = payload.address,
        return_date       = payload.return_date,
        comments          = payload.comments,
        created_by_id     = current_user.id,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return {"ok": True, "id": obj.id, "item": obj.to_dict()}


@router.post("/vehicle/bulk")
def create_vehicle_bulk(items: List[VehicleDispatchIn] = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    """Bulk-create vehicle dispatch records."""
    cid = _company_id(current_user)
    created = []
    for payload in items:
        dm = payload.dispatch_month
        if not dm and payload.dispatch_date:
            dm = payload.dispatch_date.strftime("%b'%y")
        obj = InventoryVehicleDispatch(
            company_id=cid, vehicle_no=payload.vehicle_no,
            vendor_invoice_no=payload.vendor_invoice_no, vendor_code=payload.vendor_code,
            vehicle_model=payload.vehicle_model, vehicle_color=payload.vehicle_color,
            chassis_no=payload.chassis_no, motor_no=payload.motor_no,
            status=payload.status, dispatch_date=payload.dispatch_date, dispatch_month=dm,
            sales_invoice_no=payload.sales_invoice_no, customer_name=payload.customer_name,
            contact_number=payload.contact_number, battery_spec=payload.battery_spec,
            battery_serial_no=payload.battery_serial_no, charger_no=payload.charger_no,
            address=payload.address, return_date=payload.return_date,
            comments=payload.comments, created_by_id=current_user.id,
        )
        db.add(obj); created.append(obj)
    db.commit()
    return {"ok": True, "created": len(created), "ids": [o.id for o in created]}


_VEH_PATCH_FIELDS = {
    'vehicle_no','vendor_code','vendor_invoice_no','vehicle_model','vehicle_color',
    'chassis_no','motor_no','status','dispatch_date','dispatch_month','sales_invoice_no',
    'customer_name','contact_number','battery_spec','battery_serial_no','charger_no',
    'address','return_date','comments'
}

@router.patch("/vehicle/{item_id}")
def patch_vehicle_field(item_id: int, payload: _PatchIn = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    if payload.field not in _VEH_PATCH_FIELDS:
        raise HTTPException(400, f"Field '{payload.field}' not patchable")
    obj = db.query(InventoryVehicleDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj: raise HTTPException(404, "Vehicle dispatch record not found")
    setattr(obj, payload.field, _cast_val(payload.field, payload.value))
    obj.updated_by_id = current_user.id
    db.commit()
    return {"ok": True}


@router.put("/vehicle/{item_id}")
def update_vehicle(item_id: int, payload: VehicleDispatchUpdate = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryVehicleDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Vehicle dispatch record not found")
    expected = _wvv_hash({"id": obj.id, "vehicle_model": obj.vehicle_model,
                           "status": obj.status, "dispatch_date": obj.dispatch_date})
    if payload.wvv_hash != expected:
        raise HTTPException(409, "WVV hash mismatch — record may have changed. Please refresh.")

    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    for fld, val in [
        ("vehicle_no", payload.vehicle_no), ("vendor_invoice_no", payload.vendor_invoice_no),
        ("vendor_code", payload.vendor_code), ("vehicle_model", payload.vehicle_model),
        ("vehicle_color", payload.vehicle_color), ("chassis_no", payload.chassis_no),
        ("motor_no", payload.motor_no), ("status", payload.status),
        ("dispatch_date", payload.dispatch_date), ("dispatch_month", dispatch_month),
        ("sales_invoice_no", payload.sales_invoice_no), ("customer_name", payload.customer_name),
        ("contact_number", payload.contact_number), ("battery_spec", payload.battery_spec),
        ("battery_serial_no", payload.battery_serial_no), ("charger_no", payload.charger_no),
        ("address", payload.address), ("return_date", payload.return_date),
        ("comments", payload.comments), ("updated_by_id", current_user.id),
    ]:
        setattr(obj, fld, val)
    db.commit(); db.refresh(obj)
    return {"ok": True, "item": obj.to_dict()}


@router.delete("/vehicle/{item_id}")
def delete_vehicle(item_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryVehicleDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Vehicle dispatch record not found")
    obj.is_deleted = True; obj.updated_by_id = current_user.id
    db.commit()
    return {"ok": True}


# ── VEHICLE GET BY ID ─────────────────────────────────────────────────────────

@router.get("/vehicle/{item_id}")
def get_vehicle(item_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryVehicleDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Vehicle dispatch record not found")
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k in ("dispatch_date", "return_date", "created_at", "updated_at"):
        if d.get(k) and hasattr(d[k], 'isoformat'):
            d[k] = d[k].isoformat()
    return d


# ── CHARGER CRUD ──────────────────────────────────────────────────────────────

@router.get("/charger")
def list_charger(
    status:         Optional[str]  = None,
    vendor_code:    Optional[str]  = None,
    charger_spec:   Optional[str]  = None,
    dispatch_month: Optional[str]  = None,
    date_from:      Optional[date] = None,
    date_to:        Optional[date] = None,
    warranty_status:Optional[str]  = None,
    search:         Optional[str]  = None,
    limit:          int = 500,
    offset:         int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    filters = ["is_deleted = FALSE"]
    params: dict = {}
    if status:
        filters.append("status = :status"); params["status"] = status
    if vendor_code:
        filters.append("vendor_code = :vendor_code"); params["vendor_code"] = vendor_code
    if charger_spec:
        filters.append("charger_spec = :charger_spec"); params["charger_spec"] = charger_spec
    if dispatch_month:
        filters.append("dispatch_month = :dispatch_month"); params["dispatch_month"] = dispatch_month
    if date_from:
        filters.append("dispatch_date >= :date_from"); params["date_from"] = date_from
    if date_to:
        filters.append("dispatch_date <= :date_to"); params["date_to"] = date_to
    if warranty_status == "active":
        filters.append("warranty_end_date >= CURRENT_DATE")
    elif warranty_status == "expired":
        filters.append("warranty_end_date < CURRENT_DATE AND warranty_end_date IS NOT NULL")
    if search:
        filters.append("""(charger_no ILIKE :search OR sales_invoice_no ILIKE :search
                           OR owner_name ILIKE :search OR assigned_vehicle_no ILIKE :search
                           OR location ILIKE :search)""")
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT * FROM inventory_charger_dispatch
        WHERE {where}
        ORDER BY id ASC
        LIMIT :limit OFFSET :offset
    """), {**params, "limit": limit, "offset": offset}).mappings().fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM inventory_charger_dispatch WHERE {where}
    """), params).scalar()

    data = [dict(r) for r in rows]
    for d in data:
        for k in ("entry_date", "dispatch_date", "warranty_end_date", "created_at", "updated_at"):
            if d.get(k) and hasattr(d[k], 'isoformat'):
                d[k] = d[k].isoformat()
        d["wvv_hash"] = _wvv_hash({
            "id": d["id"], "charger_spec": d.get("charger_spec"),
            "status": d.get("status"), "dispatch_date": d.get("dispatch_date"),
        })
    return {"items": data, "total": total}


@router.post("/charger")
def create_charger(payload: ChargerDispatchIn = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    obj = InventoryChargerDispatch(
        company_id          = _company_id(current_user),
        entry_date          = payload.entry_date,
        vendor_invoice_no   = payload.vendor_invoice_no,
        vendor_code         = payload.vendor_code,
        charger_spec        = payload.charger_spec,
        warranty_months     = payload.warranty_months,
        charger_no          = payload.charger_no,
        status              = payload.status,
        dispatch_date       = payload.dispatch_date,
        dispatch_month      = dispatch_month,
        assigned_vehicle_no = payload.assigned_vehicle_no,
        sales_invoice_no    = payload.sales_invoice_no,
        owner_name          = payload.owner_name,
        location            = payload.location,
        warranty_end_date   = warranty_end,
        deliverable         = payload.deliverable,
        comments            = payload.comments,
        created_by_id       = current_user.id,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return {"ok": True, "id": obj.id, "item": obj.to_dict()}


@router.post("/charger/bulk")
def create_charger_bulk(items: List[ChargerDispatchIn] = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    """Bulk-create charger dispatch records."""
    cid = _company_id(current_user)
    created = []
    for payload in items:
        warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
        dm = payload.dispatch_month
        if not dm and payload.dispatch_date:
            dm = payload.dispatch_date.strftime("%b'%y")
        obj = InventoryChargerDispatch(
            company_id=cid, entry_date=payload.entry_date,
            vendor_invoice_no=payload.vendor_invoice_no, vendor_code=payload.vendor_code,
            charger_spec=payload.charger_spec, warranty_months=payload.warranty_months,
            charger_no=payload.charger_no, status=payload.status,
            dispatch_date=payload.dispatch_date, dispatch_month=dm,
            assigned_vehicle_no=payload.assigned_vehicle_no, sales_invoice_no=payload.sales_invoice_no,
            owner_name=payload.owner_name, location=payload.location,
            deliverable=payload.deliverable, comments=payload.comments, created_by_id=current_user.id,
        )
        db.add(obj); created.append(obj)
    db.commit()
    return {"ok": True, "created": len(created), "ids": [o.id for o in created]}


_CHG_PATCH_FIELDS = {
    'entry_date','vendor_code','vendor_invoice_no','charger_spec','warranty_months',
    'charger_no','status','dispatch_date','dispatch_month','assigned_vehicle_no',
    'sales_invoice_no','owner_name','location','warranty_end_date','deliverable','comments'
}

@router.patch("/charger/{item_id}")
def patch_charger_field(item_id: int, payload: _PatchIn = Body(...),
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_staff_user)):
    if payload.field not in _CHG_PATCH_FIELDS:
        raise HTTPException(400, f"Field '{payload.field}' not patchable")
    obj = db.query(InventoryChargerDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj: raise HTTPException(404, "Charger dispatch record not found")
    setattr(obj, payload.field, _cast_val(payload.field, payload.value))
    if payload.field in ('dispatch_date', 'warranty_months'):
        obj.warranty_end_date = _calc_warranty_end(obj.dispatch_date, obj.warranty_months)
    obj.updated_by_id = current_user.id
    db.commit(); db.refresh(obj)
    return {"ok": True, "warranty_end_date": str(obj.warranty_end_date) if obj.warranty_end_date else None}


@router.put("/charger/{item_id}")
def update_charger(item_id: int, payload: ChargerDispatchUpdate = Body(...),
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryChargerDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Charger dispatch record not found")
    expected = _wvv_hash({"id": obj.id, "charger_spec": obj.charger_spec,
                           "status": obj.status, "dispatch_date": obj.dispatch_date})
    if payload.wvv_hash != expected:
        raise HTTPException(409, "WVV hash mismatch — record may have changed. Please refresh.")

    warranty_end = _calc_warranty_end(payload.dispatch_date, payload.warranty_months)
    dispatch_month = payload.dispatch_month
    if not dispatch_month and payload.dispatch_date:
        dispatch_month = payload.dispatch_date.strftime("%b'%y")

    for fld, val in [
        ("entry_date", payload.entry_date), ("vendor_invoice_no", payload.vendor_invoice_no),
        ("vendor_code", payload.vendor_code), ("charger_spec", payload.charger_spec),
        ("warranty_months", payload.warranty_months), ("charger_no", payload.charger_no),
        ("status", payload.status), ("dispatch_date", payload.dispatch_date),
        ("dispatch_month", dispatch_month), ("assigned_vehicle_no", payload.assigned_vehicle_no),
        ("sales_invoice_no", payload.sales_invoice_no), ("owner_name", payload.owner_name),
        ("location", payload.location), ("warranty_end_date", warranty_end),
        ("deliverable", payload.deliverable), ("comments", payload.comments),
        ("updated_by_id", current_user.id),
    ]:
        setattr(obj, fld, val)
    db.commit(); db.refresh(obj)
    return {"ok": True, "item": obj.to_dict()}


@router.delete("/charger/{item_id}")
def delete_charger(item_id: int, db: Session = Depends(get_db),
                   current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryChargerDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Charger dispatch record not found")
    obj.is_deleted = True; obj.updated_by_id = current_user.id
    db.commit()
    return {"ok": True}


# ── CHARGER GET BY ID ─────────────────────────────────────────────────────────

@router.get("/charger/{item_id}")
def get_charger(item_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_staff_user)):
    obj = db.query(InventoryChargerDispatch).filter_by(id=item_id, is_deleted=False).first()
    if not obj:
        raise HTTPException(404, "Charger dispatch record not found")
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k in ("entry_date", "dispatch_date", "warranty_end_date", "created_at", "updated_at"):
        if d.get(k) and hasattr(d[k], 'isoformat'):
            d[k] = d[k].isoformat()
    return d
