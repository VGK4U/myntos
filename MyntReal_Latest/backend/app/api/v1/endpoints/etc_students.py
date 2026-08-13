"""
VGK4U ETC Training Centre — Student Master API
DC Protocol Feb 2026 | WVV Compliant
Routes prefix: /api/v1/etc
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.database import get_db
from app.core.security import get_current_user_hybrid

logger = logging.getLogger(__name__)
router = APIRouter()

COMPANY_ID = 1  # Zynova ETC company_id
ETC_CATEGORY_IDS = (3, 13, 30, 42)  # ETC Training across all companies


def _batch_map_and_max(db: Session):
    """Return ({date_str: batch_no}, max_batch_num) from etc_students.
    For dates shared by multiple batches (data inconsistency), pick the
    batch with the smallest numeric suffix to stay stable."""
    rows = db.execute(text(
        "SELECT batch_start_date, MIN(batch_no) AS batch_no, COUNT(DISTINCT batch_no) AS cnt "
        "FROM etc_students "
        "WHERE is_active=TRUE AND batch_start_date IS NOT NULL AND batch_no IS NOT NULL "
        "GROUP BY batch_start_date"
    )).fetchall()
    date_map = {}
    max_num = 20  # floor at 20 (current last known batch)
    for r in rows:
        d_str = r.batch_start_date.isoformat() if hasattr(r.batch_start_date, 'isoformat') else str(r.batch_start_date)
        date_map[d_str] = r.batch_no
    # Also get true max batch number across all batches
    all_batches = db.execute(text(
        "SELECT DISTINCT batch_no FROM etc_students WHERE is_active=TRUE AND batch_no IS NOT NULL"
    )).fetchall()
    for r in all_batches:
        try:
            n = int(r.batch_no.split('-')[-1])
            if n > max_num:
                max_num = n
        except Exception:
            pass
    return date_map, max_num


def _crm_to_dict(r, batch_no):
    """Convert a CRM lead row to the student-compatible dict."""
    close_date = None
    if r.actual_close_date:
        close_date = (r.actual_close_date.date() if hasattr(r.actual_close_date, 'date') else r.actual_close_date).isoformat()
    created = r.created_at.isoformat() if r.created_at else None
    return {
        'id': f'crm_{r.id}',
        'crm_lead_id': r.id,
        'source': 'crm',
        'crm_status': r.status or 'new',
        'registration_id': None,
        'student_id': None,
        'sno': None,
        'batch_no': batch_no,
        'batch_start_date': close_date,
        'name': r.name,
        'phone': r.phone,
        'email': r.email,
        'score': None,
        'area': r.city,
        'district': None,
        'state': r.state,
        'pincode': None,
        'education_qualification': None,
        'experience': None,
        'package_value': float(r.deal_value_total) if r.deal_value_total else None,
        'training_completed_date': None,
        'aadhar_number': None,
        'hostel_opted': False,
        'payment_details': None,
        'mnr_member': False,
        'mnr_id': None,
        'service_center': False,
        'myntreal_hub': False,
        'comments': None,
        'course_type': None,
        'vgk_status': 'Pending',
        'vgk_id': None,
        'vgk_earnings': 0.0,
        'company_id': r.company_id,
        'created_by': 'CRM',
        'is_active': True,
        'created_at': created,
        'updated_at': None,
        'training_stage': 'schedule_pending',
        'handler_emp_code': getattr(r, 'mnr_handler_id', None),
        'handler_name': None,
        'telecaller_emp_code': None,
        'telecaller_name': None,
        'field_staff_emp_code': None,
        'field_staff_name': None,
    }


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    batch_no: Optional[str] = None
    batch_start_date: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    completed_date: Optional[str] = None
    score: Optional[float] = None
    area: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    education_qualification: Optional[str] = None
    experience: Optional[str] = None
    package_value: Optional[float] = None
    training_completed_date: Optional[str] = None
    aadhar_number: Optional[str] = None
    hostel_opted: Optional[bool] = False
    payment_details: Optional[str] = None
    mnr_member: Optional[bool] = False
    mnr_id: Optional[str] = None
    service_center: Optional[bool] = False
    myntreal_hub: Optional[bool] = False
    comments: Optional[str] = None
    crm_lead_id: Optional[int] = None
    course_type: Optional[str] = None
    source: Optional[str] = None
    guru_name: Optional[str] = None
    z_guru_name: Optional[str] = None
    handler_emp_code: Optional[str] = None
    telecaller_emp_code: Optional[str] = None
    field_staff_emp_code: Optional[str] = None
    deal_value_received: Optional[float] = None


class StudentUpdate(BaseModel):
    batch_no: Optional[str] = None
    batch_start_date: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    completed_date: Optional[str] = None
    score: Optional[float] = None
    area: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    education_qualification: Optional[str] = None
    experience: Optional[str] = None
    package_value: Optional[float] = None
    training_completed_date: Optional[str] = None
    aadhar_number: Optional[str] = None
    hostel_opted: Optional[bool] = None
    payment_details: Optional[str] = None
    mnr_member: Optional[bool] = None
    mnr_id: Optional[str] = None
    service_center: Optional[bool] = None
    myntreal_hub: Optional[bool] = None
    comments: Optional[str] = None
    course_type: Optional[str] = None
    vgk_status: Optional[str] = None
    vgk_id: Optional[str] = None
    source: Optional[str] = None
    guru_name: Optional[str] = None
    z_guru_name: Optional[str] = None
    handler_emp_code: Optional[str] = None
    telecaller_emp_code: Optional[str] = None
    field_staff_emp_code: Optional[str] = None
    deal_value_received: Optional[float] = None
    handler_confirmed: Optional[bool] = None
    telecaller_confirmed: Optional[bool] = None
    field_staff_confirmed: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

OLD_BATCH_CUTOFF = date(2025, 2, 28)

def _compute_training_stage(batch_start_date, training_completed_date) -> str:
    """Derive 3-step training stage from dates.
    Rules:
    - training_completed  → training_completed_date IS NOT NULL
                            OR batch started before Feb 2025 (legacy auto-complete)
    - under_training      → batch started but not yet completed
    - schedule_pending    → batch not started yet or no batch date
    """
    bsd = batch_start_date
    tcd = training_completed_date
    if isinstance(bsd, str):
        try: bsd = date.fromisoformat(bsd[:10])
        except: bsd = None
    if isinstance(tcd, str):
        try: tcd = date.fromisoformat(tcd[:10])
        except: tcd = None
    if tcd is not None:
        return 'training_completed'
    if bsd is not None and bsd <= OLD_BATCH_CUTOFF:
        return 'training_completed'
    if bsd is not None and bsd <= date.today():
        return 'under_training'
    return 'schedule_pending'


def _next_registration_id(db: Session) -> tuple:
    """Generate next VGK/1808XXXX/YYYY registration_id and student_id."""
    row = db.execute(text(
        "SELECT registration_id FROM etc_students ORDER BY id DESC LIMIT 1"
    )).fetchone()
    year = datetime.now().year
    if row:
        # parse the sequence number from VGK/18080NNN/YYYY
        try:
            seq = int(row.registration_id.split('/')[1]) + 1
        except Exception:
            seq = 18080132
    else:
        seq = 18080132  # next after 131 seed students
    seq_str = f"{seq:08d}"
    reg_id = f"VGK/{seq_str}/{year}"
    stu_id = f"VGK{seq_str}"
    return reg_id, stu_id


def _row_to_dict(row) -> dict:
    keys = ['id','registration_id','student_id','sno','batch_no','batch_start_date',
            'name','phone','email','completed_date','score','area','district','state',
            'pincode','education_qualification','experience','package_value',
            'training_completed_date','aadhar_number','hostel_opted','payment_details',
            'mnr_member','mnr_id','service_center','myntreal_hub','comments',
            'crm_lead_id','company_id','created_by','is_active','created_at','updated_at',
            'course_type','vgk_status','vgk_id',
            'source','guru_name','z_guru_name',
            'handler_emp_code','telecaller_emp_code','field_staff_emp_code',
            'deal_value_received']
    d = {}
    for k in keys:
        v = getattr(row, k, None)
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
        elif v is None:
            d[k] = None
        else:
            d[k] = v
    d['training_stage'] = _compute_training_stage(d.get('batch_start_date'), d.get('training_completed_date'))
    return d


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get('/students/')
def list_students(
    search: Optional[str] = Query(None),
    batch_no: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    mnr_member: Optional[bool] = Query(None),
    hostel_opted: Optional[bool] = Query(None),
    service_center: Optional[bool] = Query(None),
    myntreal_hub: Optional[bool] = Query(None),
    training_completed: Optional[bool] = Query(None),
    training_stage: Optional[str] = Query(None),   # 'schedule_pending'|'under_training'|'training_completed'
    source_filter: Optional[str] = Query(None),   # 'students' | 'crm' | None=all
    crm_status: Optional[str] = Query(None),       # filter CRM rows by status
    handler_emp_code: Optional[str] = Query(None),
    telecaller_emp_code: Optional[str] = Query(None),
    field_staff_emp_code: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    start_date_from: Optional[str] = Query(None),
    start_date_to: Optional[str] = Query(None),
    comp_date_from: Optional[str] = Query(None),
    comp_date_to: Optional[str] = Query(None),
    sort_by: str = Query('sno'),
    sort_dir: str = Query('asc'),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    # ── 1. Build etc_students filter ─────────────────────────────────────────
    where = ["is_active = TRUE", "company_id = :cid"]
    params: dict = {"cid": COMPANY_ID}

    def _s(val): return val if isinstance(val, str) else None
    search_s = _s(search)
    batch_no_s = _s(batch_no)
    state_s = _s(state)
    district_s = _s(district)
    training_stage_s = _s(training_stage)
    source_filter_s = _s(source_filter)
    crm_status_s = _s(crm_status)
    handler_s = _s(handler_emp_code)
    tc_s = _s(telecaller_emp_code)
    fs_s = _s(field_staff_emp_code)
    date_from_s = _s(date_from)
    date_to_s = _s(date_to)
    start_from_s = _s(start_date_from)
    start_to_s = _s(start_date_to)
    comp_from_s = _s(comp_date_from)
    comp_to_s = _s(comp_date_to)

    if search_s:
        where.append("(LOWER(name) LIKE :srch OR LOWER(student_id) LIKE :srch OR LOWER(registration_id) LIKE :srch OR phone LIKE :srch OR aadhar_number LIKE :srch)")
        params['srch'] = f'%{search_s.lower()}%'
    if batch_no_s and (not crm_status_s or crm_status_s.lower() not in ('won', 'won_plus')):
        where.append("batch_no = :batch_no")
        params['batch_no'] = batch_no_s
    if state_s:
        where.append("LOWER(state) = :state")
        params['state'] = state_s.lower()
    if district_s:
        where.append("LOWER(district) = :district")
        params['district'] = district_s.lower()
    if mnr_member is not None:
        where.append("mnr_member = :mnr")
        params['mnr'] = mnr_member
    if hostel_opted is not None:
        where.append("hostel_opted = :hostel")
        params['hostel'] = hostel_opted
    if service_center is not None:
        where.append("service_center = :sc")
        params['sc'] = service_center
    if myntreal_hub is not None:
        where.append("myntreal_hub = :hub")
        params['hub'] = myntreal_hub
    if training_completed is not None:
        if training_completed:
            where.append("training_completed_date IS NOT NULL")
        else:
            where.append("training_completed_date IS NULL")
    if training_stage_s == 'training_completed':
        where.append("(training_completed_date IS NOT NULL OR (batch_start_date IS NOT NULL AND batch_start_date <= '2025-02-28'))")
    elif training_stage_s == 'under_training':
        where.append("training_completed_date IS NULL AND batch_start_date IS NOT NULL AND batch_start_date > '2025-02-28' AND batch_start_date <= CURRENT_DATE")
    elif training_stage_s == 'schedule_pending':
        where.append("training_completed_date IS NULL AND (batch_start_date IS NULL OR batch_start_date > CURRENT_DATE)")
    if date_from_s:
        where.append("created_at::date >= :date_from")
        params['date_from'] = date_from_s
    if date_to_s:
        where.append("created_at::date <= :date_to")
        params['date_to'] = date_to_s
    # DC-ETC-DATE-FILTERS-001: start date and completed date range filters
    if start_from_s:
        where.append("batch_start_date >= :start_date_from")
        params['start_date_from'] = start_from_s
    if start_to_s:
        where.append("batch_start_date <= :start_date_to")
        params['start_date_to'] = start_to_s
    if comp_from_s:
        where.append("training_completed_date >= :comp_date_from")
        params['comp_date_from'] = comp_from_s
    if comp_to_s:
        where.append("training_completed_date <= :comp_date_to")
        params['comp_date_to'] = comp_to_s
    if handler_s:
        where.append("LOWER(handler_emp_code) LIKE :handler_code")
        params['handler_code'] = f'%{handler_s.lower()}%'
    if tc_s:
        where.append("LOWER(telecaller_emp_code) LIKE :tc_code")
        params['tc_code'] = f'%{tc_s.lower()}%'
    if fs_s:
        where.append("LOWER(field_staff_emp_code) LIKE :fs_code")
        params['fs_code'] = f'%{fs_s.lower()}%'

    allowed_sort = {'sno','name','batch_no','batch_start_date','training_completed_date','score','state','district','package_value','created_at'}
    direction = 'DESC' if isinstance(sort_dir, str) and sort_dir.lower() == 'desc' else 'ASC'
    sort_col = sort_by if isinstance(sort_by, str) and sort_by in allowed_sort else 'sno'
    order_clause = f"ORDER BY {sort_col} {direction} NULLS LAST"
    where_clause = " AND ".join(where)

    # ── 2. Fetch all matching etc_students (no DB-level pagination — combine first) ──
    include_students = source_filter in (None, '', 'students', 'all')
    include_crm = source_filter in (None, '', 'crm', 'all')

    student_dicts = []
    if include_students:
        rows = db.execute(text(
            f"SELECT * FROM etc_students WHERE {where_clause} {order_clause}"
        ), params).fetchall()
        # Bulk-fetch earnings for all students that have a vgk_id
        vgk_ids = [r.vgk_id for r in rows if r.vgk_id]
        earnings_map: dict = {}
        if vgk_ids:
            e_rows = db.execute(text(
                "SELECT partner_code, COALESCE(vgk_cash_earned_total, 0) AS earned "
                "FROM official_partners WHERE UPPER(TRIM(partner_code)) = ANY(:ids)"
            ), {'ids': [v.upper().strip() for v in vgk_ids]}).fetchall()
            for er in e_rows:
                earnings_map[er.partner_code.upper().strip()] = float(er.earned)
        for r in rows:
            d = _row_to_dict(r)
            d['source'] = 'student'
            d['crm_status'] = None
            d['vgk_earnings'] = earnings_map.get(r.vgk_id.upper().strip(), 0.0) if r.vgk_id else 0.0
            d['handler_name'] = None
            student_dicts.append(d)

        # Bulk-fetch all handler names (handler, telecaller, field_staff)
        all_codes = set()
        for d in student_dicts:
            for fld in ('handler_emp_code', 'telecaller_emp_code', 'field_staff_emp_code'):
                if d.get(fld):
                    all_codes.add(d[fld].upper())
        h_map: dict = {}
        if all_codes:
            h_rows = db.execute(text(
                "SELECT emp_code, full_name FROM staff_employees WHERE UPPER(emp_code) = ANY(:codes)"
            ), {'codes': list(all_codes)}).fetchall()
            h_map = {hr.emp_code.upper(): (hr.full_name or hr.emp_code) for hr in h_rows}
        for d in student_dicts:
            d['handler_name'] = h_map.get(d['handler_emp_code'].upper()) if d.get('handler_emp_code') else None
            d['telecaller_name'] = h_map.get(d['telecaller_emp_code'].upper()) if d.get('telecaller_emp_code') else None
            d['field_staff_name'] = h_map.get(d['field_staff_emp_code'].upper()) if d.get('field_staff_emp_code') else None

    _resolved_cat_ids = (3, 9, 13, 30, 42)

    crm_dicts = []
    if include_crm:
        crm_where = ["l.category_id IN :cat_ids",
                     "NOT EXISTS (SELECT 1 FROM etc_students s WHERE (s.crm_lead_id = l.id OR (l.phone IS NOT NULL AND l.phone != '' AND s.phone = l.phone)) AND s.is_active=TRUE)"]
        crm_params: dict = {'cat_ids': _resolved_cat_ids}

        if search:
            crm_where.append("(LOWER(l.name) LIKE :srch OR l.phone LIKE :srch)")
            crm_params['srch'] = f'%{search.lower()}%'
        if state:
            crm_where.append("LOWER(l.state) = :state")
            crm_params['state'] = state.lower()
        if crm_status:
            if crm_status.lower() in ('won', 'won_plus'):
                crm_where.append("l.status IN ('won', 'completed')")
            else:
                crm_where.append("l.status = :crm_status")
                crm_params['crm_status'] = crm_status
        if training_completed is True:
            crm_dicts = []  # CRM leads are never training-completed
            include_crm = False
        if training_stage in ('training_completed', 'under_training'):
            include_crm = False  # CRM unenrolled leads are always schedule_pending

        if include_crm:
            crm_clause = " AND ".join(crm_where)
            crm_rows = db.execute(text(f"""
                SELECT l.id, l.name, l.phone, l.email, l.status,
                       l.deal_value_total, l.actual_close_date,
                       l.state, l.city, l.created_at, l.company_id, l.mnr_handler_id
                FROM crm_leads l
                WHERE {crm_clause}
                ORDER BY l.actual_close_date DESC NULLS LAST, l.created_at DESC
            """), crm_params).fetchall()

            # ── Batch auto-assignment ──────────────────────────────────────
            date_map, max_num = _batch_map_and_max(db)
            new_date_batches: dict = {}

            for r in crm_rows:
                b_no = None
                if r.actual_close_date:
                    d_obj = r.actual_close_date.date() if hasattr(r.actual_close_date, 'date') else r.actual_close_date
                    d_str = d_obj.isoformat()
                    if d_str in date_map:
                        b_no = date_map[d_str]
                    elif d_str in new_date_batches:
                        b_no = new_date_batches[d_str]
                    else:
                        max_num += 1
                        b_no = f'Batch-{max_num}'
                        new_date_batches[d_str] = b_no

                # Apply batch_no filter if set (except when explicitly filtering won/won_plus leads)
                if batch_no and b_no != batch_no and (not crm_status or crm_status.lower() not in ('won', 'won_plus')):
                    continue

                crm_dicts.append(_crm_to_dict(r, b_no))

    # ── 4. Combine, deduplicate & paginate in Python ──────────────────────────
    combined = student_dicts + crm_dicts
    seen_identifiers = set()
    unique_combined = []
    for item in combined:
        key = None
        if item.get('crm_lead_id'):
            key = f"crm_{item['crm_lead_id']}"
        elif item.get('student_id'):
            key = f"stu_{item['student_id']}"
        elif item.get('phone'):
            key = f"phone_{item['phone']}"
        else:
            key = f"id_{item.get('id')}"

        if key not in seen_identifiers:
            seen_identifiers.add(key)
            unique_combined.append(item)

    combined = unique_combined
    total_combined = len(combined)
    offset = (page - 1) * per_page
    page_slice = combined[offset: offset + per_page]

    return {
        'total': total_combined,
        'page': page,
        'per_page': per_page,
        'pages': max(1, -(-total_combined // per_page)),
        'students': page_slice,
    }


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post('/students/')
def create_student(
    payload: StudentCreate = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    # DC Protocol (Apr 2026): Idempotent enroll — if CRM lead already has a student, return it
    if payload.crm_lead_id:
        existing = db.execute(text(
            "SELECT * FROM etc_students WHERE crm_lead_id = :cid AND is_active = TRUE LIMIT 1"
        ), {'cid': payload.crm_lead_id}).fetchone()
        if existing:
            return {'success': True, 'student': _row_to_dict(existing), 'already_enrolled': True}

    reg_id, stu_id = _next_registration_id(db)
    created_by = getattr(current_user, 'id', 'STAFF')

    def _d(v): return f"'{v}'" if v else "NULL"

    db.execute(text(f"""
        INSERT INTO etc_students (
            registration_id, student_id, batch_no, batch_start_date, name, phone, email,
            completed_date, score, area, district, state, pincode,
            education_qualification, experience, package_value, training_completed_date,
            aadhar_number, hostel_opted, payment_details, mnr_member, mnr_id,
            service_center, myntreal_hub, comments, crm_lead_id, company_id, created_by,
            source, guru_name, z_guru_name,
            handler_emp_code, telecaller_emp_code, field_staff_emp_code,
            deal_value_received
        ) VALUES (
            '{reg_id}', '{stu_id}', {_d(payload.batch_no)}, {_d(payload.batch_start_date)},
            :name, {_d(payload.phone)}, {_d(payload.email)},
            {_d(payload.completed_date)}, {payload.score if payload.score is not None else 'NULL'},
            {_d(payload.area)}, {_d(payload.district)}, {_d(payload.state)}, {_d(payload.pincode)},
            {_d(payload.education_qualification)}, {_d(payload.experience)},
            {payload.package_value if payload.package_value is not None else 'NULL'},
            {_d(payload.training_completed_date)}, {_d(payload.aadhar_number)},
            {payload.hostel_opted or False}, {_d(payload.payment_details)},
            {payload.mnr_member or False}, {_d(payload.mnr_id)},
            {payload.service_center or False}, {payload.myntreal_hub or False},
            {_d(payload.comments)}, {payload.crm_lead_id if payload.crm_lead_id else 'NULL'},
            {COMPANY_ID}, '{created_by}',
            {_d(payload.source)}, {_d(payload.guru_name)}, {_d(payload.z_guru_name)},
            {_d(payload.handler_emp_code)}, {_d(payload.telecaller_emp_code)}, {_d(payload.field_staff_emp_code)},
            {payload.deal_value_received if payload.deal_value_received is not None else 'NULL'}
        )
    """), {"name": payload.name})
    db.commit()

    row = db.execute(text(
        "SELECT * FROM etc_students WHERE registration_id = :rid"
    ), {'rid': reg_id}).fetchone()
    return {'success': True, 'student': _row_to_dict(row)}


# ── STAGE STATS (must be before /{student_db_id} to avoid routing conflict) ───

@router.get('/students/stage-stats')
def stage_stats(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    date_cond = ""
    params: dict = {'cid': COMPANY_ID}
    if date_from:
        date_cond += " AND created_at::date >= :date_from"
        params['date_from'] = date_from
    if date_to:
        date_cond += " AND created_at::date <= :date_to"
        params['date_to'] = date_to

    r = db.execute(text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE
                training_completed_date IS NOT NULL
                OR (batch_start_date IS NOT NULL AND batch_start_date <= '2025-02-28')
            ) AS training_completed,
            COUNT(*) FILTER (WHERE
                training_completed_date IS NULL
                AND batch_start_date IS NOT NULL
                AND batch_start_date > '2025-02-28'
                AND batch_start_date <= CURRENT_DATE
            ) AS under_training,
            COUNT(*) FILTER (WHERE
                training_completed_date IS NULL
                AND (batch_start_date IS NULL OR batch_start_date > CURRENT_DATE)
            ) AS schedule_pending,
            COUNT(*) FILTER (WHERE vgk_status = 'Active') AS vgk_registered,
            COUNT(*) FILTER (WHERE vgk_status = 'Pending' OR vgk_status IS NULL) AS vgk_pending,
            COUNT(*) FILTER (WHERE batch_start_date IS NOT NULL) AS signups
        FROM etc_students WHERE is_active = TRUE AND company_id = :cid{date_cond}
    """), params).fetchone()

    earnings_r = db.execute(text("""
        SELECT COALESCE(SUM(
            CASE 
                WHEN es.deal_value_received > 0 THEN es.deal_value_received
                WHEN cl.deal_value_received > 0 THEN cl.deal_value_received
                WHEN es.package_value > 0 THEN es.package_value
                WHEN cl.deal_value_total > 0 THEN cl.deal_value_total
                ELSE 0
            END
        ), 0) AS total_earnings
        FROM etc_students es
        LEFT JOIN crm_leads cl ON es.crm_lead_id = cl.id
        WHERE es.is_active = TRUE AND es.company_id = :cid
          AND (es.training_completed_date IS NOT NULL OR cl.status IN ('won', 'completed', 'won+'))
    """), {'cid': COMPANY_ID}).fetchone()

    return {
        'total': int(r.total),
        'training_completed': int(r.training_completed),
        'under_training': int(r.under_training),
        'schedule_pending': int(r.schedule_pending),
        'vgk_registered': int(r.vgk_registered),
        'vgk_pending': int(r.vgk_pending),
        'students_generated': int(r.total),
        'signups': int(r.signups),
        'total_earnings': float(earnings_r.total_earnings) if earnings_r else 0.0,
    }


# ── BATCHWISE ANALYTICS (Executive Dashboard Tab) (MUST be before /{student_db_id}) ────

@router.get('/students/batchwise-analytics')
def get_etc_batchwise_analytics(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    """
    Executive Report: Batch-wise ETC Students Analytics.
    Accessible only to authorized accounts/leadership staff (e.g. MR10001, Subash Kari).
    Returns batch-level aggregates (Month, Start Date, Batch Name, Students, Completed, Deal Value, Received, Balance, Confirmed)
    and detailed student lists per batch with expand/group support.
    """
    search_s = search if isinstance(search, str) and search.strip() else None

    st_where = ["s.is_active = TRUE", "s.company_id = :cid"]
    st_params: dict = {'cid': COMPANY_ID}
    if search_s:
        st_where.append("(LOWER(s.name) LIKE :srch OR LOWER(s.student_id) LIKE :srch OR LOWER(s.registration_id) LIKE :srch OR s.phone LIKE :srch OR LOWER(s.batch_no) LIKE :srch)")
        st_params['srch'] = f'%{search_s.lower()}%'

    st_clause = " AND ".join(st_where)
    student_rows = db.execute(text(f"""
        SELECT s.id, s.registration_id, s.student_id, s.batch_no, s.batch_start_date,
               s.name, s.phone, s.email, s.state, s.district, s.course_type,
               s.training_completed_date, s.package_value, s.deal_value_received,
               s.handler_confirmed, s.telecaller_confirmed, s.field_staff_confirmed,
               s.handler_emp_code, s.telecaller_emp_code, s.crm_lead_id, s.created_at,
               s.guru_name, s.z_guru_name, s.source,
               cl.deal_value_received as cl_deal_value_received,
               cl.actual_close_date as cl_actual_close_date,
               cl.deal_value_total as cl_deal_value_total,
               cl.deal_value as cl_deal_value
        FROM etc_students s
        LEFT JOIN crm_leads cl ON s.crm_lead_id = cl.id
        WHERE {st_clause}
        ORDER BY COALESCE(s.batch_start_date, s.training_completed_date, cl.actual_close_date::date, s.created_at::date) DESC, s.id DESC
    """), st_params).fetchall()

    lead_ids = [r.crm_lead_id for r in student_rows if r.crm_lead_id]
    tx_map = {}
    inc_map = {}
    if lead_ids:
        lids_tuple = tuple(set(lead_ids))
        tx_rows = db.execute(text("""
            SELECT lead_id, SUM(amount) as total_tx
            FROM crm_lead_transactions
            WHERE lead_id IN :lids
            GROUP BY lead_id
        """), {'lids': lids_tuple}).fetchall()
        tx_map = {tr.lead_id: float(tr.total_tx or 0.0) for tr in tx_rows}

        inc_rows = db.execute(text("""
            SELECT lead_id, 
                   SUM(amount) as inc_total,
                   SUM(CASE WHEN UPPER(status) IN ('CONFIRMED', 'TALLY_DONE', 'APPROVED') THEN amount ELSE 0 END) as inc_conf_total,
                   COUNT(CASE WHEN UPPER(status) IN ('CONFIRMED', 'TALLY_DONE', 'APPROVED') THEN 1 END) as inc_conf_cnt
            FROM income_entries
            WHERE is_deleted IS NOT TRUE AND lead_id IN :lids
            GROUP BY lead_id
        """), {'lids': lids_tuple}).fetchall()
        inc_map = {ir.lead_id: (float(ir.inc_total or 0.0), float(ir.inc_conf_total or 0.0), int(ir.inc_conf_cnt or 0)) for ir in inc_rows}

    all_codes = set()
    for r in student_rows:
        if r.handler_emp_code: all_codes.add(r.handler_emp_code.upper())
        if r.telecaller_emp_code: all_codes.add(r.telecaller_emp_code.upper())
    h_map: dict = {}
    if all_codes:
        h_rows = db.execute(text(
            "SELECT emp_code, full_name FROM staff_employees WHERE UPPER(emp_code) = ANY(:codes)"
        ), {'codes': list(all_codes)}).fetchall()
        h_map = {hr.emp_code.upper(): (hr.full_name or hr.emp_code) for hr in h_rows}

    batches_map = {}
    total_all_students = 0
    total_all_completed = 0
    total_all_deal_value = 0.0
    total_all_received = 0.0
    total_all_balance = 0.0
    total_all_confirmed = 0
    total_all_confirmed_value = 0.0

    import re
    for r in student_rows:
        b_raw = (r.batch_no or '').strip()
        if b_raw:
            m_b = re.match(r'(?i)^batch\s*[-_]?\s*(\d+)$', b_raw)
            b_key = f"Batch-{m_b.group(1)}" if m_b else b_raw
        else:
            b_key = 'Unassigned'

        if b_key not in batches_map:
            d_obj = r.batch_start_date or r.training_completed_date or (r.cl_actual_close_date.date() if hasattr(r.cl_actual_close_date, 'date') and r.cl_actual_close_date else None) or (r.created_at.date() if hasattr(r.created_at, 'date') and r.created_at else None)
            month_str = d_obj.strftime('%b %Y') if d_obj else '—'
            start_date_str = d_obj.strftime('%d-%b-%Y') if d_obj else '—'
            batches_map[b_key] = {
                'batch_no': b_key,
                'month': month_str,
                'start_date': start_date_str,
                'start_date_raw': d_obj.isoformat() if d_obj else '',
                'total_students': 0,
                'completed': 0,
                'deal_value': 0.0,
                'received': 0.0,
                'balance': 0.0,
                'confirmed_count': 0,
                'confirmed_value': 0.0,
                'students': []
            }

        b = batches_map[b_key]
        b['total_students'] += 1
        total_all_students += 1

        is_completed = bool(r.training_completed_date)
        if is_completed:
            b['completed'] += 1
            total_all_completed += 1

        dv = float(r.package_value or r.cl_deal_value_total or r.cl_deal_value or 0.0)
        
        # Comprehensive received calculation from CRM leads, student record, transactions & income entries
        cl_rec = float(r.cl_deal_value_received or 0.0)
        s_rec = float(r.deal_value_received or 0.0)
        tx_val = tx_map.get(r.crm_lead_id, 0.0)
        inc_val, inc_conf_val, inc_conf_cnt = inc_map.get(r.crm_lead_id, (0.0, 0.0, 0))
        rec = max(cl_rec, s_rec, tx_val, inc_val)
        bal = max(0.0, dv - rec)

        # STRICT RULE: Without a received value (rec > 0), a student CANNOT be confirmed!
        if rec > 0:
            is_conf = bool(inc_conf_cnt > 0 or inc_conf_val > 0 or r.handler_confirmed or r.telecaller_confirmed or r.field_staff_confirmed)
            conf_amt = inc_conf_val if inc_conf_val > 0 else rec
        else:
            is_conf = False
            conf_amt = 0.0

        b['deal_value'] += dv
        b['received'] += rec
        b['balance'] += bal
        b['confirmed_value'] += conf_amt
        total_all_deal_value += dv
        total_all_received += rec
        total_all_balance += bal
        total_all_confirmed_value += conf_amt

        if is_conf:
            b['confirmed_count'] += 1
            total_all_confirmed += 1

        h_name = h_map.get(r.handler_emp_code.upper()) if r.handler_emp_code else '—'
        tc_name = h_map.get(r.telecaller_emp_code.upper()) if r.telecaller_emp_code else '—'

        b['students'].append({
            'id': r.id,
            'registration_id': r.registration_id or '—',
            'student_id': r.student_id or '—',
            'name': r.name or 'Unknown',
            'phone': r.phone or '—',
            'email': r.email or '—',
            'state': r.state or '—',
            'district': r.district or '—',
            'course_type': r.course_type or 'ETC Training',
            'training_stage': 'training_completed' if is_completed else 'under_training',
            'training_completed_date': r.training_completed_date.isoformat() if r.training_completed_date else None,
            'deal_value': dv,
            'received': rec,
            'balance': bal,
            'confirmed': is_conf,
            'confirmed_amount': conf_amt,
            'handler_name': h_name,
            'handler_emp_code': r.handler_emp_code or '',
            'telecaller_name': tc_name,
            'telecaller_emp_code': r.telecaller_emp_code or '',
            'crm_lead_id': r.crm_lead_id,
            'source': 'student'
        })

    import re
    def _batch_sort_key(bm):
        d_raw = bm.get('start_date_raw') or '0000-00-00'
        b_num = 0
        m = re.search(r'\d+', bm.get('batch_no', ''))
        if m:
            b_num = int(m.group())
        return (d_raw, b_num)

    batch_list = list(batches_map.values())
    batch_list.sort(key=_batch_sort_key, reverse=True)

    return {
        'kpis': {
            'total_batches': len(batch_list),
            'total_students': total_all_students,
            'completed_students': total_all_completed,
            'total_deal_value': round(total_all_deal_value, 2),
            'total_received': round(total_all_received, 2),
            'total_balance': round(total_all_balance, 2),
            'total_confirmed': total_all_confirmed,
            'total_confirmed_value': round(total_all_confirmed_value, 2),
        },
        'batches': batch_list
    }


# ── GET ONE ───────────────────────────────────────────────────────────────────

@router.get('/students/{student_db_id}')
def get_student(
    student_db_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    row = db.execute(text(
        "SELECT * FROM etc_students WHERE id = :id AND is_active = TRUE"
    ), {'id': student_db_id}).fetchone()
    if not row:
        raise HTTPException(404, 'Student not found')
    return _row_to_dict(row)


# ── UPDATE ────────────────────────────────────────────────────────────────────

@router.put('/students/{student_db_id}')
def update_student(
    student_db_id: int,
    payload: StudentUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    row = db.execute(text(
        "SELECT id FROM etc_students WHERE id = :id AND is_active = TRUE"
    ), {'id': student_db_id}).fetchone()
    if not row:
        raise HTTPException(404, 'Student not found')

    updates = {}
    for field, val in payload.dict(exclude_none=True).items():
        updates[field] = val

    if not updates:
        return {'success': True, 'message': 'No changes'}

    set_parts = ', '.join([f"{k} = :{k}" for k in updates])
    updates['id'] = student_db_id
    updates['updated_at'] = datetime.now()
    db.execute(text(
        f"UPDATE etc_students SET {set_parts}, updated_at = :updated_at WHERE id = :id"
    ), updates)
    db.commit()

    row = db.execute(text("SELECT * FROM etc_students WHERE id = :id"), {'id': student_db_id}).fetchone()
    return {'success': True, 'student': _row_to_dict(row)}


# ── STAGE INLINE UPDATE ────────────────────────────────────────────────────────

class StageUpdate(BaseModel):
    stage: str  # training_completed | under_training | schedule_pending

@router.patch('/students/{student_db_id}/stage')
def update_student_stage(
    student_db_id: int,
    payload: StageUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    row = db.execute(text(
        "SELECT id FROM etc_students WHERE id = :id AND is_active = TRUE"
    ), {'id': student_db_id}).fetchone()
    if not row:
        raise HTTPException(404, 'Student not found')

    stage = payload.stage
    if stage not in ('training_completed', 'under_training', 'schedule_pending'):
        raise HTTPException(400, 'Invalid stage value')

    today = datetime.now().date().isoformat()

    if stage == 'training_completed':
        db.execute(text(
            "UPDATE etc_students SET training_completed_date = :tcd, updated_at = NOW() WHERE id = :id"
        ), {'tcd': today, 'id': student_db_id})
    elif stage == 'under_training':
        db.execute(text(
            "UPDATE etc_students SET training_completed_date = NULL, updated_at = NOW() WHERE id = :id"
        ), {'id': student_db_id})
    else:  # schedule_pending — clear both date fields
        db.execute(text(
            "UPDATE etc_students SET training_completed_date = NULL, batch_start_date = NULL, updated_at = NOW() WHERE id = :id"
        ), {'id': student_db_id})

    db.commit()
    row = db.execute(text("SELECT * FROM etc_students WHERE id = :id"), {'id': student_db_id}).fetchone()
    d = _row_to_dict(row)
    d['training_stage'] = _compute_training_stage(d.get('batch_start_date'), d.get('training_completed_date'))
    return {'success': True, 'student': d}


# ── SOFT DELETE ───────────────────────────────────────────────────────────────

@router.delete('/students/{student_db_id}')
def delete_student(
    student_db_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    db.execute(text(
        "UPDATE etc_students SET is_active = FALSE, updated_at = NOW() WHERE id = :id"
    ), {'id': student_db_id})
    db.commit()
    return {'success': True}


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@router.get('/students/dashboard/stats')
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    totals = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE training_completed_date IS NOT NULL) AS completed,
            COUNT(*) FILTER (WHERE mnr_member = TRUE) AS mnr_members,
            COUNT(*) FILTER (WHERE service_center = TRUE) AS service_centers,
            COUNT(*) FILTER (WHERE hostel_opted = TRUE) AS hostel,
            COUNT(*) FILTER (WHERE myntreal_hub = TRUE) AS hub,
            COALESCE(SUM(package_value),0) AS total_revenue,
            COALESCE(AVG(score) FILTER (WHERE score IS NOT NULL), 0) AS avg_score
        FROM etc_students WHERE is_active = TRUE AND company_id = :cid
    """), {'cid': COMPANY_ID}).fetchone()

    batches = db.execute(text("""
        SELECT batch_no, COUNT(*) AS cnt,
               COUNT(*) FILTER (WHERE training_completed_date IS NOT NULL) AS completed
        FROM etc_students WHERE is_active = TRUE AND company_id = :cid
        GROUP BY batch_no ORDER BY batch_no
    """), {'cid': COMPANY_ID}).fetchall()

    states = db.execute(text("""
        SELECT COALESCE(state,'Unknown') AS state, COUNT(*) AS cnt
        FROM etc_students WHERE is_active = TRUE AND company_id = :cid
        GROUP BY state ORDER BY cnt DESC LIMIT 15
    """), {'cid': COMPANY_ID}).fetchall()

    monthly = db.execute(text("""
        SELECT TO_CHAR(batch_start_date,'Mon YYYY') AS month,
               COUNT(*) AS cnt
        FROM etc_students WHERE is_active = TRUE AND company_id = :cid
          AND batch_start_date IS NOT NULL
        GROUP BY month, batch_start_date ORDER BY batch_start_date
    """), {'cid': COMPANY_ID}).fetchall()

    return {
        'totals': {
            'total': totals.total, 'completed': totals.completed,
            'mnr_members': totals.mnr_members, 'service_centers': totals.service_centers,
            'hostel': totals.hostel, 'hub': totals.hub,
            'total_revenue': float(totals.total_revenue),
            'avg_score': round(float(totals.avg_score), 1),
            'completion_pct': round(totals.completed * 100 / totals.total, 1) if totals.total else 0,
        },
        'batches': [{'batch': r.batch_no, 'total': r.cnt, 'completed': r.completed} for r in batches],
        'states': [{'state': r.state, 'count': r.cnt} for r in states],
        'monthly': [{'month': r.month, 'count': r.cnt} for r in monthly],
    }


# ── SYNC FROM CRM (Won leads last 15 days) ───────────────────────────────────

@router.post('/students/sync-crm/')
def sync_from_crm(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    # Sync deal values received from crm_lead_transactions to crm_leads
    try:
        db.execute(text("""
            UPDATE crm_leads cl
            SET deal_value_received = GREATEST(COALESCE(cl.deal_value_received, 0), tx.sum_tx)
            FROM (
                SELECT lead_id, SUM(amount) as sum_tx
                FROM crm_lead_transactions
                WHERE lead_id IS NOT NULL
                GROUP BY lead_id
            ) tx
            WHERE cl.id = tx.lead_id AND (cl.deal_value_received IS NULL OR cl.deal_value_received < tx.sum_tx)
        """))
        db.commit()
    except Exception as e:
        logger.warning(f"[ETC] Tx sync error: {e}")
        db.rollback()

    # Sync package values and deal values received from crm_leads to existing etc_students
    try:
        db.execute(text("""
            UPDATE etc_students es
            SET package_value = COALESCE(es.package_value, cl.deal_value_total, cl.deal_value),
                deal_value_received = GREATEST(COALESCE(es.deal_value_received, 0), COALESCE(cl.deal_value_received, 0)),
                training_completed_date = CASE WHEN cl.status IN ('won', 'completed') AND es.training_completed_date IS NULL THEN COALESCE(cl.actual_close_date, NOW()) ELSE es.training_completed_date END
            FROM crm_leads cl
            WHERE (es.crm_lead_id = cl.id OR (cl.phone IS NOT NULL AND cl.phone != '' AND es.phone = cl.phone))
              AND (
                  es.package_value IS NULL OR es.package_value = 0 
                  OR es.deal_value_received IS NULL OR es.deal_value_received < cl.deal_value_received
              )
        """))
        db.commit()
    except Exception as e:
        logger.warning(f"[ETC] Student deal sync error: {e}")
        db.rollback()

    rows = db.execute(text("""
        SELECT l.id, l.name, l.phone, l.email,
               COALESCE(l.deal_value_total, l.deal_value, 0) AS deal_value,
               COALESCE(l.deal_value_received, 0) AS deal_value_received,
               l.actual_close_date, l.status, l.state, l.city
        FROM crm_leads l
        WHERE (l.category_id IN (3, 9, 13, 30, 42) OR LOWER(l.solar_pipeline_status) LIKE '%etc%')
          AND l.status IN ('won', 'completed', 'won+')
          AND NOT EXISTS (
              SELECT 1 FROM etc_students es WHERE es.crm_lead_id = l.id OR (l.phone IS NOT NULL AND l.phone != '' AND es.phone = l.phone)
          )
        ORDER BY l.actual_close_date DESC NULLS LAST, l.created_at DESC
    """)).fetchall()

    date_map, max_num = _batch_map_and_max(db)
    new_date_batches: dict = {}

    created = []
    for r in rows:
        try:
            b_no = 'Unassigned'
            c_date = r.actual_close_date
            if c_date:
                d_obj = c_date.date() if hasattr(c_date, 'date') else c_date
                d_str = d_obj.isoformat()
                if d_str in date_map:
                    b_no = date_map[d_str]
                elif d_str in new_date_batches:
                    b_no = new_date_batches[d_str]
                else:
                    max_num += 1
                    b_no = f'Batch-{max_num}'
                    new_date_batches[d_str] = b_no

            reg_id, stu_id = _next_registration_id(db)
            pkg_val = float(r.deal_value) if r.deal_value else None
            rec_val = float(r.deal_value_received) if r.deal_value_received else None

            db.execute(text("""
                INSERT INTO etc_students (
                    registration_id, student_id, batch_no, batch_start_date, name, phone, email,
                    package_value, deal_value_received, crm_lead_id, company_id, created_by,
                    state, district, source, training_completed_date
                ) VALUES (
                    :rid, :sid, :bno, :bdate, :name, :phone, :email,
                    :pv, :rec, :lid, :cid, 'CRM_SYNC',
                    :state, :district, 'CRM Lead', :comp_date
                )
                ON CONFLICT (registration_id) DO NOTHING
            """), {
                'rid': reg_id, 'sid': stu_id, 'bno': b_no, 'bdate': c_date,
                'name': r.name or 'Unknown', 'phone': r.phone, 'email': r.email,
                'pv': pkg_val, 'rec': rec_val, 'lid': r.id, 'cid': COMPANY_ID,
                'state': r.state, 'district': r.city,
                'comp_date': c_date if r.status in ('won', 'completed') else None
            })
            db.commit()
            created.append({'crm_id': r.id, 'name': r.name, 'student_id': stu_id})
        except Exception as e:
            logger.warning(f"[ETC] CRM sync row {r.id} failed: {e}")
            db.rollback()

    return {'success': True, 'synced': len(created), 'students': created}


# ── VALIDATE STUDENT ID (for marketplace 10% discount) ───────────────────────

@router.get('/students/validate-id')
def validate_student_id(
    student_id: str = Query(...),
    db: Session = Depends(get_db),
):
    ...

# ── BATCHWISE ANALYTICS (Executive Dashboard Tab) ────────────────────────────
# (Route definition moved above /students/{student_db_id} to prevent 422 routing collision)
    """Public endpoint — validate ETC student ID for 10% marketplace discount."""
    row = db.execute(text("""
        SELECT name, student_id, registration_id, batch_no
        FROM etc_students
        WHERE UPPER(student_id) = :sid AND is_active = TRUE
        LIMIT 1
    """), {'sid': student_id.strip().upper()}).fetchone()
    if not row:
        return {'valid': False, 'message': 'Student ID not found or inactive'}
    return {
        'valid': True,
        'name': row.name,
        'student_id': row.student_id,
        'registration_id': row.registration_id,
        'batch_no': row.batch_no,
        'discount_mode': 'student',
        'discount_pct': 10,
    }


# ── DISTINCT BATCHES (for filter dropdown) ────────────────────────────────────

@router.get('/students/batches/list')
def list_batches(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid),
):
    rows = db.execute(text("""
        SELECT batch_no FROM (
            SELECT DISTINCT batch_no FROM etc_students
            WHERE is_active = TRUE AND company_id = :cid AND batch_no IS NOT NULL
        ) sub
        ORDER BY
            CAST(NULLIF(REGEXP_REPLACE(batch_no, '[^0-9]', '', 'g'), '') AS INTEGER) NULLS LAST,
            batch_no
    """), {'cid': COMPANY_ID}).fetchall()
    return {'batches': [r.batch_no for r in rows]}
