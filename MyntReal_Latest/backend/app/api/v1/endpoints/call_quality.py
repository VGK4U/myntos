"""
Call Quality Review System — DC Protocol (Mar 2026)
Handles auto-sampling of calls for quality review, review submission,
leadership dashboard, and sales day/range reports.

Sampling rule: max(5, ceil(total_day_calls_per_exec * 0.05)) per executive per day.
Visibility: Leadership/full-access sees all; others see their downline only.
"""

import math
import random
from datetime import datetime, date, timedelta
from typing import Optional
from collections import defaultdict

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.call_tracking import StaffCallLog, CallQualityReview
from app.models.crm import CRMLead
from app.models.staff import StaffEmployee, StaffRole

router = APIRouter()

INDIAN_TZ = pytz.timezone('Asia/Kolkata')
_MIN_SAMPLE = 5
_SAMPLE_PCT = 0.05

_FULL_ACCESS = {'hr', 'accounts', 'key_leadership', 'leadership_role', 'team_leader', 'manager', 'vgk4u'}


def _ist_now():
    return datetime.now(INDIAN_TZ).replace(tzinfo=None)


def _today_ist():
    return datetime.now(INDIAN_TZ).strftime('%Y-%m-%d')


def _get_role_code(db: Session, staff_id: int) -> str:
    emp = db.query(StaffEmployee).filter_by(id=staff_id).first()
    if not emp or not emp.role:
        return 'unknown'
    return emp.role.role_code or 'unknown'


def _is_full_access(role_code: str) -> bool:
    return role_code in _FULL_ACCESS


def _resolve_company_id(company_id: Optional[int], current_user) -> int:
    """Resolve company_id: use provided value, or fall back to user's base_company_id."""
    if company_id:
        return company_id
    if current_user.base_company_id:
        return current_user.base_company_id
    raise HTTPException(status_code=400, detail='company_id is required (could not be auto-resolved from your profile)')


def _resolve_company_optional(company_id: Optional[int], full_access: bool, current_user) -> Optional[int]:
    """For full_access roles: company_id is optional (None = all companies).
    For non-full_access: always require and return a resolved company_id."""
    if full_access:
        return company_id or None  # None = cross-company view
    return _resolve_company_id(company_id, current_user)


def _get_downline_ids(db: Session, manager_id: int, company_id: int) -> list:
    """Recursively get all downline staff IDs for a manager."""
    result = db.execute(text("""
        WITH RECURSIVE downline AS (
            SELECT id FROM staff_employees WHERE reporting_manager_id = :mid AND base_company_id = :cid
            UNION ALL
            SELECT e.id FROM staff_employees e
            JOIN downline d ON e.reporting_manager_id = d.id
            WHERE e.base_company_id = :cid
        )
        SELECT id FROM downline
    """), {'mid': manager_id, 'cid': company_id}).fetchall()
    return [r[0] for r in result]


def _enrich_reviews(db: Session, reviews: list) -> list:
    """Enrich review dicts with staff name, lead name, call details."""
    out = []
    for r in reviews:
        d = r.to_dict()
        # Staff name
        emp = db.query(StaffEmployee).filter_by(id=r.staff_id).first()
        d['staff_name'] = emp.full_name if emp else 'Unknown'
        d['emp_code'] = emp.emp_code if emp else None
        d['staff_role'] = emp.role.role_code if emp and emp.role else None
        # Reviewer name
        if r.reviewer_id:
            rev = db.query(StaffEmployee).filter_by(id=r.reviewer_id).first()
            d['reviewer_name'] = rev.full_name if rev else 'Unknown'
        else:
            d['reviewer_name'] = None
        # Call log details
        if r.call_log_id:
            log = db.query(StaffCallLog).filter_by(id=r.call_log_id).first()
            if log:
                d['call_phone'] = log.phone_number
                d['call_type'] = log.call_type
                d['call_datetime'] = log.call_datetime.isoformat() if log.call_datetime else None
                d['call_duration_seconds'] = log.duration_seconds
                d['call_contact_name'] = log.contact_name
            else:
                d['call_phone'] = None
                d['call_type'] = None
                d['call_datetime'] = None
                d['call_duration_seconds'] = None
                d['call_contact_name'] = None
        else:
            d['call_phone'] = d['call_type'] = d['call_datetime'] = None
            d['call_duration_seconds'] = None
            d['call_contact_name'] = None
        # Lead details
        if r.lead_id:
            lead = db.query(CRMLead).filter_by(id=r.lead_id).first()
            if lead:
                d['lead_name'] = lead.full_name
                d['lead_phone'] = lead.phone
                d['lead_status'] = lead.status
                d['lead_category_id'] = lead.category_id
            else:
                d['lead_name'] = d['lead_phone'] = d['lead_status'] = None
                d['lead_category_id'] = None
        else:
            d['lead_name'] = d['lead_phone'] = d['lead_status'] = None
            d['lead_category_id'] = None
        out.append(d)
    return out


def _score_label(score: float) -> str:
    if score is None:
        return 'N/A'
    if score >= 4.5:
        return 'Excellent'
    if score >= 3.5:
        return 'Good'
    if score >= 2.5:
        return 'Average'
    if score >= 1.5:
        return 'Below Average'
    return 'Poor'


# ── Auto Sampling ─────────────────────────────────────────────────────────────

@router.post('/call-quality/sample')
def auto_sample(
    company_id: Optional[int] = Query(None),
    sample_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    """
    Auto-sample calls for quality review for a given date.
    Creates pending review records for each executive: max(5, ceil(5% of calls)).
    Priority: 90% from connected calls, 10% from not-connected calls.
    Idempotent: skips already-sampled call logs for the date.
    """
    role_code = _get_role_code(db, current_user.id)
    full_access = _is_full_access(role_code)
    if not full_access:
        raise HTTPException(403, 'Only leadership/managers can trigger sampling.')
    effective_cid = _resolve_company_optional(company_id, full_access, current_user)

    target_date = sample_date or _today_ist()

    # Get all call logs for the date (cross-company for full_access when no cid)
    log_q = db.query(StaffCallLog).filter(StaffCallLog.call_date == target_date)
    if effective_cid:
        log_q = log_q.filter(StaffCallLog.company_id == effective_cid)
    logs = log_q.all()

    if not logs:
        return {'sampled': 0, 'message': 'No calls found for this date.'}

    # Already-sampled call_log_ids for this date
    ex_q = db.query(CallQualityReview.call_log_id).filter(
        CallQualityReview.sample_date == target_date,
        CallQualityReview.call_log_id.isnot(None),
    )
    if effective_cid:
        ex_q = ex_q.filter(CallQualityReview.company_id == effective_cid)
    existing_ids = {r.call_log_id for r in ex_q.all()}

    # Group by executive
    by_exec = defaultdict(list)
    for log in logs:
        by_exec[log.staff_id].append(log)

    _CONNECTED_TYPES = {'outgoing', 'incoming', 'OUTGOING', 'INCOMING'}

    created = 0
    for staff_id, exec_logs in by_exec.items():
        eligible = [l for l in exec_logs if l.id not in existing_ids]
        if not eligible:
            continue
        total = len(exec_logs)
        sample_n = max(_MIN_SAMPLE, math.ceil(total * _SAMPLE_PCT))
        sample_n = min(sample_n, len(eligible))

        # Split into connected (90%) vs not-connected (10%)
        connected = [l for l in eligible
                     if l.call_type in _CONNECTED_TYPES and (l.duration_seconds or 0) > 0]
        not_connected = [l for l in eligible if l not in set(connected)]

        n_conn = round(sample_n * 0.9)
        n_not  = sample_n - n_conn
        n_conn = min(n_conn, len(connected))
        n_not  = min(n_not,  len(not_connected))

        # Fill remaining slots from whichever pool has extras
        remaining = sample_n - n_conn - n_not
        if remaining > 0:
            extra = min(remaining, len(connected) - n_conn)
            n_conn += extra
            remaining -= extra
        if remaining > 0:
            n_not = min(n_not + remaining, len(not_connected))

        sampled = []
        if connected and n_conn > 0:
            sampled += random.sample(connected, n_conn)
        if not_connected and n_not > 0:
            sampled += random.sample(not_connected, n_not)

        for log in sampled:
            rev = CallQualityReview(
                company_id=log.company_id,
                staff_id=staff_id,
                call_log_id=log.id,
                lead_id=log.matched_lead_id,
                sample_date=target_date,
                sampled_by='auto',
                status='pending',
            )
            db.add(rev)
            created += 1

    db.commit()
    return {
        'sampled': created,
        'date': target_date,
        'message': f'{created} review(s) created for {target_date}.',
    }


# ── List Reviews ──────────────────────────────────────────────────────────────

@router.get('/call-quality/reviews')
def list_reviews(
    company_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    staff_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    company_id = _resolve_company_id(company_id, current_user)
    role_code = _get_role_code(db, current_user.id)
    full_access = _is_full_access(role_code)

    q = db.query(CallQualityReview).filter(CallQualityReview.company_id == company_id)

    if not full_access:
        downline = _get_downline_ids(db, current_user.id, company_id)
        if not downline:
            return {'reviews': [], 'total': 0, 'page': page, 'pages': 0}
        q = q.filter(CallQualityReview.staff_id.in_(downline))

    if staff_id:
        q = q.filter(CallQualityReview.staff_id == staff_id)
    if status:
        q = q.filter(CallQualityReview.status == status)
    if date_from:
        q = q.filter(CallQualityReview.sample_date >= date_from)
    if date_to:
        q = q.filter(CallQualityReview.sample_date <= date_to)

    total = q.count()
    reviews = q.order_by(CallQualityReview.sample_date.desc(), CallQualityReview.id.desc()) \
               .offset((page - 1) * per_page).limit(per_page).all()

    return {
        'reviews': _enrich_reviews(db, reviews),
        'total': total,
        'page': page,
        'pages': math.ceil(total / per_page) if total else 0,
    }


# ── Review Detail ─────────────────────────────────────────────────────────────

@router.get('/call-quality/reviews/{review_id}')
def get_review(
    review_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    company_id = _resolve_company_id(company_id, current_user)
    rev = db.query(CallQualityReview).filter_by(id=review_id, company_id=company_id).first()
    if not rev:
        raise HTTPException(404, 'Review not found.')

    enriched = _enrich_reviews(db, [rev])
    result = enriched[0]

    # Attach full lead notes/followups if lead exists
    if rev.lead_id:
        notes = db.execute(text("""
            SELECT n.note, n.created_at, e.full_name as author
            FROM crm_lead_notes n
            LEFT JOIN staff_employees e ON e.id = n.created_by_id
            WHERE n.lead_id = :lid
            ORDER BY n.created_at DESC LIMIT 10
        """), {'lid': rev.lead_id}).fetchall()
        result['lead_notes'] = [
            {'note': r[0], 'created_at': r[1].isoformat() if r[1] else None, 'author': r[2]}
            for r in notes
        ]

        followups = db.execute(text("""
            SELECT scheduled_date, status, notes, created_at
            FROM crm_lead_followups
            WHERE lead_id = :lid
            ORDER BY scheduled_date DESC LIMIT 5
        """), {'lid': rev.lead_id}).fetchall()
        result['lead_followups'] = [
            {'scheduled_date': str(r[0]), 'status': r[1], 'notes': r[2],
             'created_at': r[3].isoformat() if r[3] else None}
            for r in followups
        ]
    else:
        result['lead_notes'] = []
        result['lead_followups'] = []

    return result


# ── Submit Review ─────────────────────────────────────────────────────────────

@router.post('/call-quality/reviews/{review_id}/submit')
def submit_review(
    review_id: int,
    body: dict,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    company_id = _resolve_company_id(company_id, current_user)
    rev = db.query(CallQualityReview).filter_by(id=review_id, company_id=company_id).first()
    if not rev:
        raise HTTPException(404, 'Review not found.')

    scores = [
        body.get('score_script'),
        body.get('score_tone'),
        body.get('score_info_accuracy'),
        body.get('score_customer_handling'),
        body.get('score_closing'),
        body.get('score_disposition'),
    ]
    for s in scores:
        if s is not None and not (1 <= int(s) <= 5):
            raise HTTPException(400, 'All scores must be between 1 and 5.')

    rev.score_script = body.get('score_script')
    rev.score_tone = body.get('score_tone')
    rev.score_info_accuracy = body.get('score_info_accuracy')
    rev.score_customer_handling = body.get('score_customer_handling')
    rev.score_closing = body.get('score_closing')
    rev.score_disposition = body.get('score_disposition')
    rev.overall_remarks = body.get('overall_remarks', '')
    rev.reviewer_id = current_user.id
    rev.reviewed_at = _ist_now()
    rev.status = body.get('status', 'reviewed')

    filled = [s for s in scores if s is not None]
    rev.overall_score = round(sum(filled) / len(filled), 2) if filled else None

    db.commit()
    db.refresh(rev)
    return {'success': True, 'review': rev.to_dict()}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get('/call-quality/dashboard')
def dashboard(
    company_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    company_id = _resolve_company_id(company_id, current_user)
    role_code = _get_role_code(db, current_user.id)
    full_access = _is_full_access(role_code)

    today = _today_ist()
    df = date_from or (date.today() - timedelta(days=29)).strftime('%Y-%m-%d')
    dt = date_to or today

    q = db.query(CallQualityReview).filter(
        CallQualityReview.company_id == company_id,
        CallQualityReview.sample_date >= df,
        CallQualityReview.sample_date <= dt,
    )
    if not full_access:
        downline = _get_downline_ids(db, current_user.id, company_id)
        if not downline:
            q = q.filter(CallQualityReview.staff_id == -1)
        else:
            q = q.filter(CallQualityReview.staff_id.in_(downline))

    all_reviews = q.all()

    total = len(all_reviews)
    pending = sum(1 for r in all_reviews if r.status == 'pending')
    reviewed = sum(1 for r in all_reviews if r.status == 'reviewed')
    skipped = sum(1 for r in all_reviews if r.status == 'skipped')

    scored = [r for r in all_reviews if r.overall_score is not None]
    avg_score = round(sum(r.overall_score for r in scored) / len(scored), 2) if scored else None

    # Per-executive breakdown
    exec_map = defaultdict(lambda: {'total': 0, 'reviewed': 0, 'pending': 0, 'scores': []})
    for r in all_reviews:
        exec_map[r.staff_id]['total'] += 1
        exec_map[r.staff_id][r.status if r.status in ('reviewed', 'pending') else 'total'] += (0 if r.status not in ('reviewed','pending') else 0)
        if r.status == 'reviewed':
            exec_map[r.staff_id]['reviewed'] += 1
        elif r.status == 'pending':
            exec_map[r.staff_id]['pending'] += 1
        if r.overall_score is not None:
            exec_map[r.staff_id]['scores'].append(r.overall_score)

    exec_stats = []
    for staff_id, stats in exec_map.items():
        emp = db.query(StaffEmployee).filter_by(id=staff_id).first()
        avg = round(sum(stats['scores']) / len(stats['scores']), 2) if stats['scores'] else None
        exec_stats.append({
            'staff_id': staff_id,
            'staff_name': emp.full_name if emp else 'Unknown',
            'emp_code': emp.emp_code if emp else None,
            'role': emp.role.role_code if emp and emp.role else None,
            'total_sampled': stats['total'],
            'reviewed': stats['reviewed'],
            'pending': stats['pending'],
            'avg_score': avg,
            'score_label': _score_label(avg),
        })
    exec_stats.sort(key=lambda x: (x['avg_score'] or 0), reverse=True)

    # Category averages
    cat_scores = {
        'script': [r.score_script for r in all_reviews if r.score_script],
        'tone': [r.score_tone for r in all_reviews if r.score_tone],
        'info_accuracy': [r.score_info_accuracy for r in all_reviews if r.score_info_accuracy],
        'customer_handling': [r.score_customer_handling for r in all_reviews if r.score_customer_handling],
        'closing': [r.score_closing for r in all_reviews if r.score_closing],
        'disposition': [r.score_disposition for r in all_reviews if r.score_disposition],
    }
    category_averages = {k: round(sum(v)/len(v), 2) if v else None for k, v in cat_scores.items()}

    # Daily trend (last 30 days)
    trend = defaultdict(lambda: {'total': 0, 'reviewed': 0, 'avg_score': None, 'scores': []})
    for r in all_reviews:
        trend[r.sample_date]['total'] += 1
        if r.status == 'reviewed':
            trend[r.sample_date]['reviewed'] += 1
        if r.overall_score is not None:
            trend[r.sample_date]['scores'].append(r.overall_score)
    trend_list = []
    for d_str, v in sorted(trend.items()):
        trend_list.append({
            'date': d_str,
            'total': v['total'],
            'reviewed': v['reviewed'],
            'avg_score': round(sum(v['scores'])/len(v['scores']), 2) if v['scores'] else None,
        })

    return {
        'date_from': df,
        'date_to': dt,
        'summary': {
            'total_sampled': total,
            'pending': pending,
            'reviewed': reviewed,
            'skipped': skipped,
            'avg_overall_score': avg_score,
            'score_label': _score_label(avg_score),
        },
        'category_averages': category_averages,
        'exec_breakdown': exec_stats,
        'daily_trend': trend_list,
    }


# ── Sales Day Report ──────────────────────────────────────────────────────────

@router.get('/call-quality/day-report')
def day_report(
    company_id: Optional[int] = Query(None),
    report_date: Optional[str] = Query(None),
    staff_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    role_code = _get_role_code(db, current_user.id)
    full_access = _is_full_access(role_code)
    effective_cid = _resolve_company_optional(company_id, full_access, current_user)
    target_date = report_date or _today_ist()

    # Determine visible staff IDs
    if full_access:
        visible_ids = None
    else:
        visible_ids = _get_downline_ids(db, current_user.id, effective_cid)
        visible_ids.append(current_user.id)

    # Call logs for the date
    log_q = db.query(StaffCallLog).filter(StaffCallLog.call_date == target_date)
    if effective_cid:
        log_q = log_q.filter(StaffCallLog.company_id == effective_cid)
    if visible_ids is not None:
        log_q = log_q.filter(StaffCallLog.staff_id.in_(visible_ids))
    if staff_id:
        log_q = log_q.filter(StaffCallLog.staff_id == staff_id)

    logs = log_q.all()

    # Quality reviews for the date
    rev_q = db.query(CallQualityReview).filter(CallQualityReview.sample_date == target_date)
    if effective_cid:
        rev_q = rev_q.filter(CallQualityReview.company_id == effective_cid)
    if visible_ids is not None:
        rev_q = rev_q.filter(CallQualityReview.staff_id.in_(visible_ids))
    if staff_id:
        rev_q = rev_q.filter(CallQualityReview.staff_id == staff_id)

    reviews = rev_q.all()

    # Build per-executive stats
    exec_logs = defaultdict(list)
    for log in logs:
        exec_logs[log.staff_id].append(log)

    exec_reviews = defaultdict(list)
    for rev in reviews:
        exec_reviews[rev.staff_id].append(rev)

    all_staff_ids = set(exec_logs.keys()) | set(exec_reviews.keys())
    if staff_id:
        all_staff_ids = {staff_id}

    result_execs = []
    for sid in all_staff_ids:
        emp = db.query(StaffEmployee).filter_by(id=sid).first()
        e_logs = exec_logs[sid]
        e_revs = exec_reviews[sid]

        calls_total = len(e_logs)
        calls_outgoing = sum(1 for l in e_logs if l.call_type in ('outgoing', 'OUTGOING'))
        calls_incoming = sum(1 for l in e_logs if l.call_type in ('incoming', 'INCOMING'))
        calls_missed = sum(1 for l in e_logs if l.call_type in ('missed', 'MISSED'))
        total_duration = sum(l.duration_seconds for l in e_logs)
        leads_touched = len({l.matched_lead_id for l in e_logs if l.matched_lead_id})

        quality_total = len(e_revs)
        quality_pending = sum(1 for r in e_revs if r.status == 'pending')
        quality_reviewed = sum(1 for r in e_revs if r.status == 'reviewed')
        scored = [r for r in e_revs if r.overall_score is not None]
        avg_quality = round(sum(r.overall_score for r in scored) / len(scored), 2) if scored else None

        result_execs.append({
            'staff_id': sid,
            'staff_name': emp.full_name if emp else 'Unknown',
            'emp_code': emp.emp_code if emp else None,
            'role': emp.role.role_code if emp and emp.role else None,
            'calls': {
                'total': calls_total,
                'outgoing': calls_outgoing,
                'incoming': calls_incoming,
                'missed': calls_missed,
                'total_duration_seconds': total_duration,
                'avg_duration_seconds': round(total_duration / calls_total) if calls_total else 0,
            },
            'leads_touched': leads_touched,
            'quality': {
                'sampled': quality_total,
                'pending': quality_pending,
                'reviewed': quality_reviewed,
                'avg_score': avg_quality,
                'score_label': _score_label(avg_quality),
            },
        })

    result_execs.sort(key=lambda x: x['calls']['total'], reverse=True)

    # Company-wide totals
    total_calls = sum(e['calls']['total'] for e in result_execs)
    total_leads = sum(e['leads_touched'] for e in result_execs)
    q_total = sum(e['quality']['sampled'] for e in result_execs)
    q_pending = sum(e['quality']['pending'] for e in result_execs)
    q_reviewed = sum(e['quality']['reviewed'] for e in result_execs)
    all_scores = [r.overall_score for r in reviews if r.overall_score is not None]
    avg_q = round(sum(all_scores)/len(all_scores), 2) if all_scores else None

    return {
        'report_date': target_date,
        'summary': {
            'total_executives': len(result_execs),
            'total_calls': total_calls,
            'total_leads_touched': total_leads,
            'quality_sampled': q_total,
            'quality_pending': q_pending,
            'quality_reviewed': q_reviewed,
            'avg_quality_score': avg_q,
        },
        'executives': result_execs,
    }


# ── Sales Range Report ────────────────────────────────────────────────────────

@router.get('/call-quality/range-report')
def range_report(
    company_id: Optional[int] = Query(None),
    date_from: str = Query(...),
    date_to: str = Query(...),
    staff_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_user),
):
    role_code = _get_role_code(db, current_user.id)
    full_access = _is_full_access(role_code)
    effective_cid = _resolve_company_optional(company_id, full_access, current_user)

    if full_access:
        visible_ids = None
    else:
        visible_ids = _get_downline_ids(db, current_user.id, effective_cid)
        visible_ids.append(current_user.id)

    log_q = db.query(StaffCallLog).filter(
        StaffCallLog.call_date >= date_from,
        StaffCallLog.call_date <= date_to,
    )
    if effective_cid:
        log_q = log_q.filter(StaffCallLog.company_id == effective_cid)
    if visible_ids is not None:
        log_q = log_q.filter(StaffCallLog.staff_id.in_(visible_ids))
    if staff_id:
        log_q = log_q.filter(StaffCallLog.staff_id == staff_id)

    logs = log_q.all()

    rev_q = db.query(CallQualityReview).filter(
        CallQualityReview.sample_date >= date_from,
        CallQualityReview.sample_date <= date_to,
    )
    if effective_cid:
        rev_q = rev_q.filter(CallQualityReview.company_id == effective_cid)
    if visible_ids is not None:
        rev_q = rev_q.filter(CallQualityReview.staff_id.in_(visible_ids))
    if staff_id:
        rev_q = rev_q.filter(CallQualityReview.staff_id == staff_id)

    reviews = rev_q.all()

    exec_logs = defaultdict(list)
    for log in logs:
        exec_logs[log.staff_id].append(log)

    exec_reviews = defaultdict(list)
    for rev in reviews:
        exec_reviews[rev.staff_id].append(rev)

    all_staff_ids = set(exec_logs.keys()) | set(exec_reviews.keys())

    result_execs = []
    for sid in all_staff_ids:
        emp = db.query(StaffEmployee).filter_by(id=sid).first()
        e_logs = exec_logs[sid]
        e_revs = exec_reviews[sid]

        calls_total = len(e_logs)
        calls_outgoing = sum(1 for l in e_logs if l.call_type in ('outgoing', 'OUTGOING'))
        calls_incoming = sum(1 for l in e_logs if l.call_type in ('incoming', 'INCOMING'))
        calls_missed = sum(1 for l in e_logs if l.call_type in ('missed', 'MISSED'))
        total_duration = sum(l.duration_seconds for l in e_logs)
        leads_touched = len({l.matched_lead_id for l in e_logs if l.matched_lead_id})

        # Daily breakdown
        daily_logs = defaultdict(list)
        for l in e_logs:
            daily_logs[l.call_date].append(l)
        daily_revs = defaultdict(list)
        for r in e_revs:
            daily_revs[r.sample_date].append(r)
        all_dates = sorted(set(list(daily_logs.keys()) + list(daily_revs.keys())))
        daily_breakdown = []
        for d in all_dates:
            dl = daily_logs[d]
            dr = daily_revs[d]
            ds = [r.overall_score for r in dr if r.overall_score is not None]
            daily_breakdown.append({
                'date': d,
                'calls': len(dl),
                'outgoing': sum(1 for l in dl if l.call_type in ('outgoing','OUTGOING')),
                'duration': sum(l.duration_seconds for l in dl),
                'leads_touched': len({l.matched_lead_id for l in dl if l.matched_lead_id}),
                'quality_sampled': len(dr),
                'quality_reviewed': sum(1 for r in dr if r.status == 'reviewed'),
                'avg_score': round(sum(ds)/len(ds),2) if ds else None,
            })

        quality_total = len(e_revs)
        quality_reviewed = sum(1 for r in e_revs if r.status == 'reviewed')
        scored = [r for r in e_revs if r.overall_score is not None]
        avg_quality = round(sum(r.overall_score for r in scored) / len(scored), 2) if scored else None

        result_execs.append({
            'staff_id': sid,
            'staff_name': emp.full_name if emp else 'Unknown',
            'emp_code': emp.emp_code if emp else None,
            'role': emp.role.role_code if emp and emp.role else None,
            'calls': {
                'total': calls_total,
                'outgoing': calls_outgoing,
                'incoming': calls_incoming,
                'missed': calls_missed,
                'total_duration_seconds': total_duration,
                'avg_duration_seconds': round(total_duration / calls_total) if calls_total else 0,
            },
            'leads_touched': leads_touched,
            'quality': {
                'sampled': quality_total,
                'reviewed': quality_reviewed,
                'avg_score': avg_quality,
                'score_label': _score_label(avg_quality),
            },
            'daily': daily_breakdown,
        })

    result_execs.sort(key=lambda x: x['calls']['total'], reverse=True)

    # Summary
    total_calls = sum(e['calls']['total'] for e in result_execs)
    total_leads = sum(e['leads_touched'] for e in result_execs)
    q_total = sum(e['quality']['sampled'] for e in result_execs)
    q_reviewed = sum(e['quality']['reviewed'] for e in result_execs)
    all_scores = [r.overall_score for r in reviews if r.overall_score is not None]
    avg_q = round(sum(all_scores)/len(all_scores), 2) if all_scores else None

    return {
        'date_from': date_from,
        'date_to': date_to,
        'summary': {
            'total_executives': len(result_execs),
            'total_calls': total_calls,
            'total_leads_touched': total_leads,
            'quality_sampled': q_total,
            'quality_reviewed': q_reviewed,
            'avg_quality_score': avg_q,
        },
        'executives': result_execs,
    }
