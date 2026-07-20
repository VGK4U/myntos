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

    if search:
        where.append("(LOWER(name) LIKE :srch OR LOWER(student_id) LIKE :srch OR LOWER(registration_id) LIKE :srch OR phone LIKE :srch OR aadhar_number LIKE :srch)")
        params['srch'] = f'%{search.lower()}%'
    if batch_no:
        where.append("batch_no = :batch_no")
        params['batch_no'] = batch_no
    if state:
        where.append("LOWER(state) = :state")
        params['state'] = state.lower()
    if district:
        where.append("LOWER(district) = :district")
        params['district'] = district.lower()
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
    if training_stage == 'training_completed':
        where.append("(training_completed_date IS NOT NULL OR (batch_start_date IS NOT NULL AND batch_start_date <= '2025-02-28'))")
    elif training_stage == 'under_training':
        where.append("training_completed_date IS NULL AND batch_start_date IS NOT NULL AND batch_start_date > '2025-02-28' AND batch_start_date <= CURRENT_DATE")
    elif training_stage == 'schedule_pending':
        where.append("training_completed_date IS NULL AND (batch_start_date IS NULL OR batch_start_date > CURRENT_DATE)")
    if date_from:
        where.append("created_at::date >= :date_from")
        params['date_from'] = date_from
    if date_to:
        where.append("created_at::date <= :date_to")
        params['date_to'] = date_to
    # DC-ETC-DATE-FILTERS-001: start date and completed date range filters
    if start_date_from:
        where.append("batch_start_date >= :start_date_from")
        params['start_date_from'] = start_date_from
    if start_date_to:
        where.append("batch_start_date <= :start_date_to")
        params['start_date_to'] = start_date_to
    if comp_date_from:
        where.append("training_completed_date >= :comp_date_from")
        params['comp_date_from'] = comp_date_from
    if comp_date_to:
        where.append("training_completed_date <= :comp_date_to")
        params['comp_date_to'] = comp_date_to
    if handler_emp_code:
        where.append("LOWER(handler_emp_code) LIKE :handler_code")
        params['handler_code'] = f'%{handler_emp_code.lower()}%'
    if telecaller_emp_code:
        where.append("LOWER(telecaller_emp_code) LIKE :tc_code")
        params['tc_code'] = f'%{telecaller_emp_code.lower()}%'
    if field_staff_emp_code:
        where.append("LOWER(field_staff_emp_code) LIKE :fs_code")
        params['fs_code'] = f'%{field_staff_emp_code.lower()}%'

    allowed_sort = {'sno','name','batch_no','batch_start_date','training_completed_date','score','state','district','package_value','created_at'}
    direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'
    sort_col = sort_by if sort_by in allowed_sort else 'sno'
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

    # ── 3. Fetch CRM ETC leads not yet enrolled ──────────────────────────────
    # DC-ETC-DYNCAT-001: Discover ETC category IDs dynamically from signup_categories
    # so newly created or renamed ETC Training categories are auto-included.
    # Falls back to hardcoded ETC_CATEGORY_IDS if DB returns nothing.
    _dyn_cats = db.execute(text(
        "SELECT id FROM signup_categories WHERE LOWER(name) LIKE '%etc%' OR LOWER(name) LIKE '%training%'"
    )).fetchall()
    _resolved_cat_ids = tuple(r[0] for r in _dyn_cats) or tuple(ETC_CATEGORY_IDS)

    crm_dicts = []
    if include_crm:
        crm_where = ["l.category_id IN :cat_ids",
                     "NOT EXISTS (SELECT 1 FROM etc_students s WHERE s.crm_lead_id = l.id AND s.is_active=TRUE)"]
        crm_params: dict = {'cat_ids': _resolved_cat_ids}

        if search:
            crm_where.append("(LOWER(l.name) LIKE :srch OR l.phone LIKE :srch)")
            crm_params['srch'] = f'%{search.lower()}%'
        if state:
            crm_where.append("LOWER(l.state) = :state")
            crm_params['state'] = state.lower()
        if crm_status:
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
                       l.state, l.city, l.created_at, l.company_id
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

                # Apply batch_no filter if set
                if batch_no and b_no != batch_no:
                    continue

                crm_dicts.append(_crm_to_dict(r, b_no))

    # ── 4. Combine, paginate in Python ────────────────────────────────────────
    combined = student_dicts + crm_dicts
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
        SELECT COALESCE(SUM(op.vgk_cash_earned_total), 0) AS total_earnings
        FROM etc_students es
        JOIN official_partners op ON UPPER(TRIM(op.partner_code)) = UPPER(TRIM(es.vgk_id))
        WHERE es.is_active = TRUE AND es.company_id = :cid
          AND es.vgk_id IS NOT NULL AND es.vgk_id != ''
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
    cutoff = (datetime.now() - timedelta(days=15)).date()
    rows = db.execute(text("""
        SELECT l.id, l.name, l.phone, l.email,
               COALESCE(d.deal_value_total, 0) AS deal_value,
               l.actual_close_date
        FROM crm_leads l
        LEFT JOIN crm_lead_deals d ON d.lead_id = l.id
        LEFT JOIN signup_categories sc ON sc.id = l.category_id
        WHERE l.status = 'won'
          AND l.actual_close_date >= :cutoff
          AND (
              sc.name ILIKE '%etc%' OR sc.name ILIKE '%training%'
              OR l.source ILIKE '%etc%' OR l.source ILIKE '%training%'
          )
          AND NOT EXISTS (
              SELECT 1 FROM etc_students WHERE crm_lead_id = l.id
          )
        ORDER BY l.actual_close_date DESC
    """), {'cutoff': cutoff}).fetchall()

    created = []
    for r in rows:
        try:
            reg_id, stu_id = _next_registration_id(db)
            db.execute(text("""
                INSERT INTO etc_students
                    (registration_id, student_id, name, phone, email,
                     package_value, crm_lead_id, company_id, created_by)
                VALUES
                    (:rid, :sid, :name, :phone, :email,
                     :pv, :lid, :cid, 'CRM_SYNC')
                ON CONFLICT (registration_id) DO NOTHING
            """), {
                'rid': reg_id, 'sid': stu_id,
                'name': r.name or 'Unknown',
                'phone': r.phone, 'email': r.email,
                'pv': float(r.deal_value) if r.deal_value else None,
                'lid': r.id, 'cid': COMPANY_ID,
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
