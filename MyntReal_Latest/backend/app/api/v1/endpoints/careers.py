"""
Careers / HR Module
DC Protocol Compliant — Apr 2026
DC_CAREERS_001

Staff endpoints (HR / EA / Key Leadership / VGK Mentor):
  GET    /staff/hr/jobs              — list all jobs (filters + sort)
  POST   /staff/hr/jobs              — create job posting
  GET    /staff/hr/jobs/{id}         — single job
  PATCH  /staff/hr/jobs/{id}         — update job
  PATCH  /staff/hr/jobs/{id}/status  — pause / deactivate / activate
  GET    /staff/hr/applications      — list all applications (filters + sort)
  GET    /staff/hr/applications/{id} — single application detail
  PATCH  /staff/hr/applications/{id}/status — update candidate status + notes
  GET    /staff/hr/applications/{id}/resume  — stream resume from object storage

Public (no auth):
  GET    /public/careers/jobs        — active jobs only
  POST   /public/careers/apply       — submit application + resume upload
"""

import os, json, hashlib, mimetypes, random
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user

router = APIRouter(tags=["Careers HR"])

ALLOWED_RESUME_TYPES = {"application/pdf", "application/msword",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ALLOWED_RESUME_EXT   = {".pdf", ".doc", ".docx"}
MAX_RESUME_MB        = 5

DEPARTMENTS = ["Sales", "Technology", "Operations", "HR", "Finance",
               "Marketing", "Customer Support"]

JOB_TYPES = ["Full-Time", "Part-Time", "Contract", "Internship"]

JOB_STATUSES   = ("DRAFT", "ACTIVE", "PAUSED", "DEACTIVATED")
APP_STATUSES   = ("PENDING", "SHORTLISTED", "HOLD", "REJECTED", "FUTURE_CONSIDERATION")
SALARY_PERIODS = ("MONTHLY", "ANNUAL")


# ─────────────────────────────────────────────────────────────
# AUTH DEPENDENCY — HR / EA / VGK Mentor / Key Leadership
# ─────────────────────────────────────────────────────────────

async def require_hr_access(
    current_user=Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    st = (current_user.staff_type or "").upper()
    if "VGK" in st or st == "EA":
        return current_user
    row = db.execute(
        text("SELECT role_code FROM staff_roles WHERE id = :rid"),
        {"rid": current_user.role_id}
    ).fetchone()
    if row and row[0] in ("hr", "key_leadership", "leadership_role", "ea"):
        return current_user
    raise HTTPException(status_code=403, detail="HR section access required (HR / EA / Key Leadership / VGK Mentor)")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _job_to_dict(row) -> dict:
    keys = ["id", "title", "department", "job_type", "location",
            "exp_min", "exp_max", "description", "requirements",
            "skills", "salary_min", "salary_max", "salary_period",
            "salary_visible", "status", "base_display_count",
            "created_by_id", "created_at", "updated_at"]
    d = dict(zip(keys, row))
    for f in ("skills",):
        if isinstance(d.get(f), str):
            try: d[f] = json.loads(d[f])
            except Exception: d[f] = []
        elif d.get(f) is None:
            d[f] = []
    for f in ("created_at", "updated_at"):
        if d.get(f): d[f] = str(d[f])
    return d


def _app_to_dict(row) -> dict:
    keys = ["id", "job_id", "job_title", "full_name", "email", "phone",
            "exp_years", "current_company", "cover_letter",
            "resume_path", "status", "staff_notes",
            "applied_at", "reviewed_at", "reviewed_by_id"]
    d = dict(zip(keys, row))
    for f in ("applied_at", "reviewed_at"):
        if d.get(f): d[f] = str(d[f])
    d["has_resume"] = bool(d.get("resume_path"))
    d.pop("resume_path", None)
    return d


async def _upload_resume(file: UploadFile, app_id: int) -> str:
    """Upload resume to object storage. Returns storage path."""
    from app.services.object_storage import storage_service
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_RESUME_EXT:
        raise HTTPException(status_code=400, detail=f"Resume must be PDF or Word document (.pdf / .doc / .docx)")
    data = await file.read()
    if len(data) > MAX_RESUME_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Resume must be under {MAX_RESUME_MB} MB")
    path = f"careers/resumes/{app_id}{ext}"
    ok = storage_service.upload_file(path, data)
    if not ok:
        raise HTTPException(status_code=500, detail="Resume upload failed — please try again")
    return path


def _stable_display_count(job_id: int) -> int:
    """Returns a stable pseudo-random display count ≥ 30."""
    return 30 + ((job_id * 73 + 17) % 171)


# ─────────────────────────────────────────────────────────────
# STAFF — JOB POSTINGS
# ─────────────────────────────────────────────────────────────

@router.get("/staff/hr/jobs")
async def list_jobs(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_dir: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    allowed_sorts = {"created_at", "title", "department", "status", "updated_at"}
    if sort_by not in allowed_sorts: sort_by = "created_at"
    if sort_dir not in ("asc", "desc"): sort_dir = "desc"

    where = []
    params: dict = {}
    if status and status in JOB_STATUSES:
        where.append("status = :status"); params["status"] = status
    if department:
        where.append("department = :dept"); params["dept"] = department
    if job_type:
        where.append("job_type = :jtype"); params["jtype"] = job_type

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    count_row = db.execute(text(f"SELECT COUNT(*) FROM job_postings {where_sql}"), params).fetchone()
    total = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    params["limit"] = page_size; params["offset"] = offset
    rows = db.execute(text(f"""
        SELECT id, title, department, job_type, location,
               exp_min, exp_max, description, requirements,
               skills, salary_min, salary_max, salary_period,
               salary_visible, status, base_display_count,
               created_by_id, created_at, updated_at
        FROM job_postings
        {where_sql}
        ORDER BY {sort_by} {sort_dir}
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    jobs = [_job_to_dict(r) for r in rows]
    for j in jobs:
        app_count = db.execute(
            text("SELECT COUNT(*) FROM job_applications WHERE job_id = :jid"), {"jid": j["id"]}
        ).fetchone()
        real = app_count[0] if app_count else 0
        j["actual_applicants"] = real
        j["display_applicants"] = max(real, j.get("base_display_count") or 30)

    return {"jobs": jobs, "total": total, "page": page, "page_size": page_size}


@router.post("/staff/hr/jobs", status_code=201)
async def create_job(
    title: str = Form(...),
    department: str = Form(...),
    job_type: str = Form(...),
    location: str = Form(""),
    exp_min: int = Form(0),
    exp_max: int = Form(0),
    description: str = Form(""),
    requirements: str = Form(""),
    skills: str = Form("[]"),
    salary_min: Optional[float] = Form(None),
    salary_max: Optional[float] = Form(None),
    salary_period: str = Form("MONTHLY"),
    salary_visible: bool = Form(False),
    status: str = Form("ACTIVE"),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    if not title.strip():
        raise HTTPException(status_code=400, detail="Job title is required")
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid department")
    if job_type not in JOB_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid job type")
    if status not in JOB_STATUSES:
        status = "ACTIVE"
    if salary_period not in SALARY_PERIODS:
        salary_period = "MONTHLY"

    try: skills_json = json.loads(skills)
    except Exception: skills_json = []

    now = datetime.now(timezone.utc)
    row = db.execute(text("""
        INSERT INTO job_postings
          (title, department, job_type, location, exp_min, exp_max,
           description, requirements, skills, salary_min, salary_max,
           salary_period, salary_visible, status, created_by_id, created_at, updated_at)
        VALUES
          (:title, :dept, :jtype, :loc, :emin, :emax,
           :desc, :req, CAST(:skills AS jsonb), :smin, :smax,
           :speriod, :svis, :status, :cby, :now, :now)
        RETURNING id
    """), {
        "title": title.strip(), "dept": department, "jtype": job_type,
        "loc": location, "emin": exp_min, "emax": exp_max,
        "desc": description, "req": requirements,
        "skills": json.dumps(skills_json),
        "smin": salary_min, "smax": salary_max,
        "speriod": salary_period, "svis": salary_visible,
        "status": status, "cby": current_user.id, "now": now
    }).fetchone()
    job_id = row[0]

    # Set stable display count seeded by ID
    db.execute(text("UPDATE job_postings SET base_display_count = :cnt WHERE id = :id"),
               {"cnt": _stable_display_count(job_id), "id": job_id})
    db.commit()
    return {"id": job_id, "message": "Job posting created successfully"}


@router.get("/staff/hr/jobs/{job_id}")
async def get_job(
    job_id: int,
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    row = db.execute(text("""
        SELECT id, title, department, job_type, location,
               exp_min, exp_max, description, requirements,
               skills, salary_min, salary_max, salary_period,
               salary_visible, status, base_display_count,
               created_by_id, created_at, updated_at
        FROM job_postings WHERE id = :id
    """), {"id": job_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    j = _job_to_dict(row)
    app_count = db.execute(
        text("SELECT COUNT(*) FROM job_applications WHERE job_id = :id"), {"id": job_id}
    ).fetchone()
    j["actual_applicants"] = app_count[0] if app_count else 0
    j["display_applicants"] = max(j["actual_applicants"], j.get("base_display_count") or 30)
    return j


@router.patch("/staff/hr/jobs/{job_id}")
async def update_job(
    job_id: int,
    title: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    job_type: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    exp_min: Optional[int] = Form(None),
    exp_max: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    salary_min: Optional[float] = Form(None),
    salary_max: Optional[float] = Form(None),
    salary_period: Optional[str] = Form(None),
    salary_visible: Optional[bool] = Form(None),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    existing = db.execute(text("SELECT id FROM job_postings WHERE id = :id"), {"id": job_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")

    sets, params = [], {"id": job_id, "now": datetime.now(timezone.utc)}
    if title is not None: sets.append("title = :title"); params["title"] = title.strip()
    if department is not None and department in DEPARTMENTS:
        sets.append("department = :dept"); params["dept"] = department
    if job_type is not None and job_type in JOB_TYPES:
        sets.append("job_type = :jtype"); params["jtype"] = job_type
    if location is not None: sets.append("location = :loc"); params["loc"] = location
    if exp_min is not None: sets.append("exp_min = :emin"); params["emin"] = exp_min
    if exp_max is not None: sets.append("exp_max = :emax"); params["emax"] = exp_max
    if description is not None: sets.append("description = :desc"); params["desc"] = description
    if requirements is not None: sets.append("requirements = :req"); params["req"] = requirements
    if skills is not None:
        try: sj = json.loads(skills)
        except Exception: sj = []
        sets.append("skills = CAST(:skills AS jsonb)"); params["skills"] = json.dumps(sj)
    if salary_min is not None: sets.append("salary_min = :smin"); params["smin"] = salary_min
    if salary_max is not None: sets.append("salary_max = :smax"); params["smax"] = salary_max
    if salary_period is not None and salary_period in SALARY_PERIODS:
        sets.append("salary_period = :speriod"); params["speriod"] = salary_period
    if salary_visible is not None: sets.append("salary_visible = :svis"); params["svis"] = salary_visible

    if not sets:
        return {"message": "Nothing to update"}

    sets.append("updated_at = :now")
    db.execute(text(f"UPDATE job_postings SET {', '.join(sets)} WHERE id = :id"), params)
    db.commit()
    return {"message": "Job updated successfully"}


@router.patch("/staff/hr/jobs/{job_id}/status")
async def update_job_status(
    job_id: int,
    status: str = Form(...),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    if status not in JOB_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {JOB_STATUSES}")
    existing = db.execute(text("SELECT id FROM job_postings WHERE id = :id"), {"id": job_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")
    db.execute(text("UPDATE job_postings SET status = :s, updated_at = :now WHERE id = :id"),
               {"s": status, "now": datetime.now(timezone.utc), "id": job_id})
    db.commit()
    return {"message": f"Job status updated to {status}"}


# ─────────────────────────────────────────────────────────────
# STAFF — APPLICATIONS / CANDIDATES
# ─────────────────────────────────────────────────────────────

@router.get("/staff/hr/applications")
async def list_applications(
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    exp_min: Optional[int] = Query(None),
    exp_max: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("applied_at"),
    sort_dir: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    allowed_sorts = {"applied_at", "full_name", "exp_years", "status", "reviewed_at"}
    if sort_by not in allowed_sorts: sort_by = "applied_at"
    if sort_dir not in ("asc", "desc"): sort_dir = "desc"

    where, params = [], {}
    if job_id:
        where.append("a.job_id = :jid"); params["jid"] = job_id
    if status and status in APP_STATUSES:
        where.append("a.status = :status"); params["status"] = status
    if search:
        where.append("(a.full_name ILIKE :srch OR a.email ILIKE :srch OR a.phone ILIKE :srch)")
        params["srch"] = f"%{search}%"
    if exp_min is not None:
        where.append("a.exp_years >= :emin"); params["emin"] = exp_min
    if exp_max is not None:
        where.append("a.exp_years <= :emax"); params["emax"] = exp_max
    if date_from:
        where.append("a.applied_at >= :dfrom"); params["dfrom"] = date_from
    if date_to:
        where.append("a.applied_at <= :dto"); params["dto"] = date_to + " 23:59:59"

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    count_row = db.execute(text(f"SELECT COUNT(*) FROM job_applications a {where_sql}"), params).fetchone()
    total = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    params["limit"] = page_size; params["offset"] = offset
    rows = db.execute(text(f"""
        SELECT a.id, a.job_id, j.title as job_title,
               a.full_name, a.email, a.phone,
               a.exp_years, a.current_company, a.cover_letter,
               a.resume_path, a.status, a.staff_notes,
               a.applied_at, a.reviewed_at, a.reviewed_by_id
        FROM job_applications a
        LEFT JOIN job_postings j ON j.id = a.job_id
        {where_sql}
        ORDER BY a.{sort_by} {sort_dir}
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return {"applications": [_app_to_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/staff/hr/applications/{app_id}")
async def get_application(
    app_id: int,
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    row = db.execute(text("""
        SELECT a.id, a.job_id, j.title as job_title,
               a.full_name, a.email, a.phone,
               a.exp_years, a.current_company, a.cover_letter,
               a.resume_path, a.status, a.staff_notes,
               a.applied_at, a.reviewed_at, a.reviewed_by_id
        FROM job_applications a
        LEFT JOIN job_postings j ON j.id = a.job_id
        WHERE a.id = :id
    """), {"id": app_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return _app_to_dict(row)


@router.patch("/staff/hr/applications/{app_id}/status")
async def update_application_status(
    app_id: int,
    status: str = Form(...),
    staff_notes: Optional[str] = Form(None),
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    if status not in APP_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {APP_STATUSES}")
    existing = db.execute(text("SELECT id FROM job_applications WHERE id = :id"), {"id": app_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")

    sets = ["status = :status", "reviewed_at = :now", "reviewed_by_id = :by"]
    params = {"status": status, "now": datetime.now(timezone.utc), "by": current_user.id, "id": app_id}
    if staff_notes is not None:
        sets.append("staff_notes = :notes"); params["notes"] = staff_notes

    db.execute(text(f"UPDATE job_applications SET {', '.join(sets)} WHERE id = :id"), params)
    db.commit()
    return {"message": f"Candidate status updated to {status}"}


@router.get("/staff/hr/applications/{app_id}/resume")
async def download_resume(
    app_id: int,
    current_user=Depends(require_hr_access),
    db: Session = Depends(get_db)
):
    row = db.execute(
        text("SELECT resume_path, full_name FROM job_applications WHERE id = :id"), {"id": app_id}
    ).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Resume not found")
    resume_path, full_name = row[0], row[1]

    from app.services.object_storage import storage_service
    data = storage_service.download_file(resume_path)
    if not data:
        raise HTTPException(status_code=404, detail="Resume file not found in storage")

    ext = os.path.splitext(resume_path)[1].lower()
    mime = {"pdf": "application/pdf", ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(ext, "application/octet-stream")
    safe_name = (full_name or "candidate").replace(" ", "_")
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_resume{ext}"'}
    )


# ─────────────────────────────────────────────────────────────
# PUBLIC — CAREERS PAGE
# ─────────────────────────────────────────────────────────────

@router.get("/public/careers/jobs")
async def public_list_jobs(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, title, department, job_type, location,
               exp_min, exp_max, description, requirements,
               skills, salary_min, salary_max, salary_period,
               salary_visible, base_display_count
        FROM job_postings
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
    """)).fetchall()
    jobs = []
    for r in rows:
        keys = ["id","title","department","job_type","location",
                "exp_min","exp_max","description","requirements",
                "skills","salary_min","salary_max","salary_period",
                "salary_visible","base_display_count"]
        d = dict(zip(keys, r))
        for f in ("skills",):
            if isinstance(d.get(f), str):
                try: d[f] = json.loads(d[f])
                except Exception: d[f] = []
            elif d.get(f) is None: d[f] = []
        if not d.get("salary_visible"):
            d["salary_min"] = None; d["salary_max"] = None
        app_count = db.execute(
            text("SELECT COUNT(*) FROM job_applications WHERE job_id = :id"), {"id": d["id"]}
        ).fetchone()
        real = app_count[0] if app_count else 0
        d["display_applicants"] = max(real, d.get("base_display_count") or 30)
        d.pop("base_display_count", None)
        jobs.append(d)
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/public/careers/apply", status_code=201)
async def public_apply(
    job_id: int = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    exp_years: int = Form(0),
    current_company: Optional[str] = Form(None),
    cover_letter: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if not full_name.strip() or not email.strip() or not phone.strip():
        raise HTTPException(status_code=400, detail="Name, email and phone are required")

    job = db.execute(
        text("SELECT id, title, status FROM job_postings WHERE id = :id"), {"id": job_id}
    ).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job[2] != "ACTIVE":
        raise HTTPException(status_code=400, detail="This position is no longer accepting applications")

    dup = db.execute(
        text("SELECT id FROM job_applications WHERE job_id = :jid AND email = :em"),
        {"jid": job_id, "em": email.strip().lower()}
    ).fetchone()
    if dup:
        raise HTTPException(status_code=400, detail="You have already applied for this position")

    now = datetime.now(timezone.utc)
    row = db.execute(text("""
        INSERT INTO job_applications
          (job_id, full_name, email, phone, exp_years,
           current_company, cover_letter, status, applied_at)
        VALUES
          (:jid, :name, :email, :phone, :exp,
           :co, :cl, 'PENDING', :now)
        RETURNING id
    """), {
        "jid": job_id, "name": full_name.strip(),
        "email": email.strip().lower(), "phone": phone.strip(),
        "exp": exp_years, "co": current_company,
        "cl": cover_letter, "now": now
    }).fetchone()
    app_id = row[0]

    if resume and resume.filename:
        try:
            path = await _upload_resume(resume, app_id)
            db.execute(text("UPDATE job_applications SET resume_path = :p WHERE id = :id"),
                       {"p": path, "id": app_id})
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            pass

    db.commit()
    return {"message": "Application submitted successfully! We will get back to you soon.", "application_id": app_id}
