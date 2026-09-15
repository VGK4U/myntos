"""
DC Protocol: CRM Google Sheets Lead Sync API
Endpoints: configs CRUD, run sync, preview, history
"""
import csv
import io
import logging
import re
from datetime import datetime, date
from difflib import SequenceMatcher
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.crm import CRMLead, CRMLeadFollowUp
from app.models.crm_lead_sync import CRMLeadSyncConfig, CRMLeadSyncRun
from app.models.signup_category import SignupCategory
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany

logger = logging.getLogger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAPPING CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Google Sheet column order (0-indexed)
COL_SERNO    = 0
COL_DATE     = 1
COL_OWNER    = 2
COL_SOURCE   = 3
COL_REF_FROM = 4
COL_LEAD_FOR = 5
COL_TYPE     = 6
COL_NAME     = 7
COL_MOBILE   = 8
COL_PINCODE  = 9
COL_AREA     = 10
COL_STATUS   = 11
COL_LASTCALL = 12
COL_NEXTFUP  = 13
COL_COMMENTS = 14
COL_OTHER    = 15
COL_INFO_DET = 16
# B2B Meta Lead Form columns (Mar 2026) — no fixed position; detected dynamically
COL_INVESTMENT_CAPACITY = None
COL_PLANNING_TO_START   = None
COL_FULL_TIME_BUSINESS  = None

# Lead For → category_id + label
# company_id and tenant_id are dynamically resolved via _resolve_category_and_tenant()
LEAD_FOR_MAP = {
    'to_setup_solar':                  {'category_id': 6,    'label': 'Solar'},
    'to_purchase_a_electric_scooter':  {'category_id': 2,    'label': 'EV B2C'},
    'to_set_up_ev_business':           {'category_id': 1,    'label': 'EV B2B'},
    'to_get_the_training_on_ev':       {'category_id': 3,    'label': 'ETC Training'},
    'to_set_up_service_centre':        {'category_id': 1,    'label': 'EV B2B'},
    'business_hub_/_franchise':        {'category_id': 1,    'label': 'EV B2B'},
    'anything':                        {'category_id': None, 'label': 'General'},
    '':                                {'category_id': None, 'label': 'General'},
}

# Type fallback when Lead For is "Anything" or empty
TYPE_CATEGORY_MAP = {
    'solar':          {'category_id': 6,  'label': 'Solar'},
    'ev':             {'category_id': 2,  'label': 'EV B2C'},
    'ev ':            {'category_id': 2,  'label': 'EV B2C'},
    'ev+service':     {'category_id': 1,  'label': 'EV B2B'},
    'training':       {'category_id': 3,  'label': 'ETC Training'},
    'training, ev ':  {'category_id': 3,  'label': 'ETC Training'},
    'training, ev':   {'category_id': 3,  'label': 'ETC Training'},
    'business':       {'category_id': 1,  'label': 'EV B2B'},
    'service':        {'category_id': 1,  'label': 'EV B2B'},
    'service centre': {'category_id': 1,  'label': 'EV B2B'},
}

# Status mapping
STATUS_MAP = {
    'yet to contact':           'new',
    'new':                      'new',
    'not answering':            'contacted',
    'interested - transferred': 'interested',
    'interested':               'interested',
    'not interested':           'lost',
}

_category_tenant_cache: dict[int, tuple[int, int]] = {}

def _resolve_category_and_tenant(db: Session, category_id: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    """
    Resolve (company_id, tenant_id) from SignupCategory -> AssociatedCompany.
    Fails closed (returns None, None) if category_id is missing, unknown, or associated company has no tenant_id.
    """
    if not category_id:
        return None, None
    if category_id in _category_tenant_cache:
        return _category_tenant_cache[category_id]

    row = db.query(SignupCategory.company_id, AssociatedCompany.client_id)\
        .join(AssociatedCompany, AssociatedCompany.id == SignupCategory.company_id)\
        .filter(SignupCategory.id == category_id)\
        .first()

    if row and row[0] and row[1]:
        res = (row[0], row[1])
        _category_tenant_cache[category_id] = res
        return res

    return None, None

# Maps raw sheet source strings → standard CRMLeadSource names
_SOURCE_NAME_MAP = {
    'facebook':        'Online - M',
    'fb':              'Online - M',
    'facebook ads':    'Online - M',
    'fb ads':          'Online - M',
    'meta':            'Online - M',
    'instagram':       'Social Media',
    'social media':    'Social Media',
    'whatsapp':        'Social Media',
    'website':         'Website',
    'web':             'Website',
    'online':          'Website',
    'google':          'Website',
    'referral':        'Referral',
    'reference':       'Referral',
    'ref':             'Referral',
    'walk-in':         'Walk-in',
    'walkin':          'Walk-in',
    'walk in':         'Walk-in',
    'phone call':      'Phone Call',
    'call':            'Phone Call',
    'advertisement':   'Advertisement',
    'ad':              'Advertisement',
    'event':           'Event/Exhibition',
    'exhibition':      'Event/Exhibition',
    'partner':         'Partner',
    'self':            'Self Lead',
    'self lead':       'Self Lead',
    'other':           'Other',
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _map_source(raw: str) -> str:
    """Map raw Google Sheet source string to a standard CRMLeadSource name."""
    if not raw:
        return 'Google Sheets'
    mapped = _SOURCE_NAME_MAP.get(raw.strip().lower())
    return mapped if mapped else raw.strip()

def _clean_phone(raw: str) -> str:
    """Strip non-digit chars and return 10-digit mobile or empty string."""
    digits = re.sub(r'\D', '', str(raw or ''))
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    return digits[-10:] if len(digits) >= 10 else ''


def _map_lead_for(lead_for: str, type_col: str) -> dict:
    """Return {'category_id', 'label'} from Lead For (with Type fallback)."""
    lf_key = lead_for.strip().lower()
    match = LEAD_FOR_MAP.get(lf_key)
    if match and match['category_id'] is not None:
        return match

    # Fallback: use Type column
    type_key = type_col.strip().lower()
    type_match = TYPE_CATEGORY_MAP.get(type_key)
    if type_match:
        return type_match

    # Final default
    return {'category_id': None, 'label': 'General'}


def _map_status(raw: str) -> str:
    """Map raw spreadsheet status to CRM enum. Email-looking values → 'new'."""
    if not raw:
        return 'new'
    if '@' in raw:  # email misplaced in status column — treat as new
        return 'new'
    return STATUS_MAP.get(raw.strip().lower(), 'new')


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _match_owner_to_employee(owner_name: str, employees: list) -> Optional[int]:
    """Fuzzy match spreadsheet Lead Owner first-name against staff name.
    DC Protocol (F3): Uses full_name first; falls back to first_name+last_name
    when full_name is NULL/empty (e.g. Bhoolakshmi case). Threshold ≥ 0.65."""
    if not owner_name:
        return None
    first = owner_name.strip().split()[0].lower()
    best_id, best_score = None, 0.0
    for emp in employees:
        # Build candidate: prefer full_name; fall back to first_name + last_name
        raw_full = (emp.full_name or '').strip()
        if not raw_full:
            # Fallback: construct from salutation + first_name + last_name columns
            parts = [
                getattr(emp, 'first_name', '') or '',
                getattr(emp, 'last_name', '') or '',
            ]
            raw_full = ' '.join(p.strip() for p in parts if p.strip())
        full = raw_full.replace('Mr.', '').replace('Mrs.', '').replace('Ms.', '').strip().lower()
        names = full.split()
        for word in names:
            score = _similarity(first, word)
            if score > best_score:
                best_score = score
                best_id = emp.id
    return best_id if best_score >= 0.65 else None


def _csv_url(sheet_url: str) -> str:
    """Convert any Google Sheets URL to direct CSV export URL (sheet 0)."""
    m = re.search(r'/spreadsheets/d/([^/]+)', sheet_url)
    if not m:
        raise ValueError('Invalid Google Sheets URL')
    sheet_id = m.group(1)
    gid_match = re.search(r'gid=(\d+)', sheet_url)
    gid = gid_match.group(1) if gid_match else '0'
    return f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'


def _fetch_rows(sheet_url: str) -> tuple[list, list]:
    """Fetch sheet and return (header_row, data_rows). Skips rows before header."""
    csv_url = _csv_url(sheet_url)
    resp = requests.get(csv_url, timeout=30)
    resp.raise_for_status()
    reader = csv.reader(io.StringIO(resp.text))
    all_rows = list(reader)
    # Find the header row (first row where col 7 == 'Customer Name' or has >= 8 non-empty cells)
    header_idx = 0
    for i, row in enumerate(all_rows):
        non_empty = [c for c in row if c.strip()]
        if len(non_empty) >= 8 and any('name' in c.lower() or 'mobile' in c.lower() for c in row):
            header_idx = i
            break
    header = all_rows[header_idx] if all_rows else []
    data   = [r for r in all_rows[header_idx + 1:] if any(c.strip() for c in r)]
    return header, data


def _get_existing_phones(db: Session, tenant_id: Optional[int] = None, company_id: Optional[int] = None) -> set:
    """Return set of canonical normalized phone numbers in crm_leads scoped strictly to tenant and company."""
    if not tenant_id or not company_id:
        return set()
    sql = text("""
        SELECT 
            CASE 
                WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) >= 10 
                    THEN RIGHT(REGEXP_REPLACE(phone, '[^0-9]', '', 'g'), 10)
                WHEN LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) >= 8 
                    THEN REGEXP_REPLACE(phone, '[^0-9]', '', 'g')
                ELSE NULL 
            END,
            CASE 
                WHEN LENGTH(REGEXP_REPLACE(alternate_phone, '[^0-9]', '', 'g')) >= 10 
                    THEN RIGHT(REGEXP_REPLACE(alternate_phone, '[^0-9]', '', 'g'), 10)
                WHEN LENGTH(REGEXP_REPLACE(alternate_phone, '[^0-9]', '', 'g')) >= 8 
                    THEN REGEXP_REPLACE(alternate_phone, '[^0-9]', '', 'g')
                ELSE NULL 
            END
        FROM crm_leads
        WHERE tenant_id = :tenant_id AND company_id = :company_id
          AND (phone IS NOT NULL OR alternate_phone IS NOT NULL)
    """)
    rows = db.execute(sql, {"tenant_id": tenant_id, "company_id": company_id}).fetchall()
    phones = set()
    for r in rows:
        if r[0]: phones.add(r[0])
        if r[1]: phones.add(r[1])
    return phones


def _pincode_to_location(pincode: str) -> dict:
    """
    DC Protocol (Mar 2026): Lookup city/state/area from India Post API for a given pincode.
    Returns dict with keys city, state, area (all str or None).
    Silently returns empty dict on any failure — never raises.
    """
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        return {}
    try:
        resp = requests.get(
            f"https://api.postalpincode.in/pincode/{pincode}",
            timeout=5,
        )
        data = resp.json()
        if (
            isinstance(data, list)
            and data
            and data[0].get('Status') == 'Success'
            and data[0].get('PostOffice')
        ):
            po = data[0]['PostOffice'][0]
            return {
                'city':  po.get('District') or po.get('Division') or None,
                'state': po.get('State') or None,
                'area':  po.get('Name') or None,
            }
    except Exception:
        pass
    return {}


def _detect_columns(header: list) -> dict:
    """
    DC Protocol (Mar 2026): Dynamic column detection from header row.
    Maps field names → column indices by scanning header labels.
    Falls back to hardcoded constants when a field cannot be detected.
    Supports multiple Google Sheets with different column layouts.
    """
    cols = {
        'name':     COL_NAME,
        'mobile':   COL_MOBILE,
        'owner':    COL_OWNER,
        'source':   COL_SOURCE,
        'ref_from': COL_REF_FROM,
        'lead_for': COL_LEAD_FOR,
        'type':     COL_TYPE,
        'pincode':  COL_PINCODE,
        'area':     COL_AREA,
        'status':   COL_STATUS,
        'lastcall': COL_LASTCALL,
        'nextfup':  COL_NEXTFUP,
        'comments': COL_COMMENTS,
        'other':    COL_OTHER,
        'info_det': COL_INFO_DET,
        # B2B Meta Lead Form fields — default None (detected dynamically only)
        'investment_capacity': None,
        'planning_to_start':   None,
        'full_time_business':  None,
    }
    for i, raw_h in enumerate(header):
        h = raw_h.strip().lower()
        if not h:
            continue
        # Mobile / phone — check before name to avoid 'contact name' collision
        if any(k in h for k in ('mobile', 'phone', 'cell', 'contact no', 'contact number', 'whatsapp')):
            cols['mobile'] = i
        # Name
        elif any(k in h for k in ('customer name', 'client name', 'lead name', 'prospect name', 'full name',
                                   'contact name', 'applicant name')):
            cols['name'] = i
        elif h in ('name', 'names') or (h.endswith(' name') and 'owner' not in h and 'company' not in h):
            cols['name'] = i
        # Owner / executive
        elif any(k in h for k in ('owner', 'executive', 'assigned to', 'team member', 'telecaller',
                                   'emp code', 'emp id', 'staff', 'agent')):
            cols['owner'] = i
        # Source
        elif any(k in h for k in ('source', 'channel', 'medium', 'lead source')):
            cols['source'] = i
        # Ref / Reference from
        elif any(k in h for k in ('ref from', 'reference', 'referred by', 'referral', 'ref by')):
            cols['ref_from'] = i
        # Lead For / Category
        elif any(k in h for k in ('lead for', 'looking for', 'purpose', 'interested in', 'category',
                                   'product', 'requirement')):
            cols['lead_for'] = i
        # Type
        elif h in ('type', 'lead type', 'segment', 'sub type', 'sub-type'):
            cols['type'] = i
        # Pincode / ZIP
        elif any(k in h for k in ('pincode', 'pin code', 'zip', 'postal')):
            cols['pincode'] = i
        # B2B Meta Lead Form — exact custom column names (MUST be before area/city check
        # because 'city' is a substring of 'investment_capa*city*')
        elif h == 'investment_capacity':
            cols['investment_capacity'] = i
        elif h == 'planning_to_start':
            cols['planning_to_start'] = i
        elif h == 'full_time_business':
            cols['full_time_business'] = i
        # Area / Location / City
        elif any(k in h for k in ('area', 'location', 'city', 'region', 'district', 'zone', 'place',
                                   'locality', 'taluk', 'village')):
            cols['area'] = i
        # Status / Stage
        elif h in ('status', 'lead status', 'stage', 'disposition'):
            cols['status'] = i
        # Last Call / Last Contact
        elif any(k in h for k in ('last call', 'last contact', 'previous call', 'prev call',
                                   'last talked', 'last interacted')):
            cols['lastcall'] = i
        # Next Followup
        elif any(k in h for k in ('next followup', 'next follow up', 'next fup', 'follow up date',
                                   'followup date', 'callback date', 'next call')):
            cols['nextfup'] = i
        # Comments / Remarks / Notes
        elif any(k in h for k in ('comment', 'remark', 'notes', 'note', 'description', 'feedback')):
            cols['comments'] = i
        # Other details
        elif h in ('other', 'other details', 'misc', 'additional info'):
            cols['other'] = i
        # Info / Details
        elif any(k in h for k in ('info', 'details', 'additional', 'extra')):
            cols['info_det'] = i
    return cols


def _parse_date_text(raw: str) -> Optional[datetime]:
    """Best-effort parse of informal date strings like '26 Feb', '16 March', etc."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    # Try common formats
    for fmt in ('%d %b', '%d %B', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(raw, fmt)
            # For dates without year, assume current year
            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue
    return None


def _do_sync(db: Session, config: CRMLeadSyncConfig, employees: list,
             preview_only: bool = False) -> dict:
    """Core sync function. Returns summary dict.
    DC Protocol (F1): Uses PostgreSQL advisory lock to prevent concurrent syncs
    on the same config. Lock key = config.id (unique per sheet)."""
    if not preview_only:
        # Acquire advisory lock: non-blocking; raises 409 if already running
        lock_key = int(config.id) + 900000  # namespace offset to avoid collisions
        lock_result = db.execute(text('SELECT pg_try_advisory_lock(:k)'), {'k': lock_key}).scalar()
        if not lock_result:
            raise RuntimeError(f'Sync for "{config.name}" is already in progress. Please wait.')
    header_row, data_rows = _fetch_rows(config.sheet_url)
    # DC Protocol (Mar 2026): Dynamic column detection — supports multiple sheets with different layouts
    C = _detect_columns(header_row)
    from app.services.crm_dedup_service import normalize_phone
    existing_phones = _get_existing_phones(db, tenant_id=config.tenant_id, company_id=config.company_id)
    emp_lookup = {e.id: e for e in employees}

    new_leads   = []
    new_fups    = []
    duplicates  = 0
    errors      = 0
    preview     = []

    for row in data_rows:
        # Pad row to max detected column index + safety buffer
        valid_cols = [v for v in C.values() if isinstance(v, int)]
        max_col = (max(valid_cols) + 1) if valid_cols else 17
        while len(row) < max(17, max_col):
            row.append('')

        raw_phone = normalize_phone(row[C['mobile']])
        raw_name  = row[C['name']].strip()
        if not raw_name and not raw_phone:
            continue

        # Duplicate check
        if raw_phone and raw_phone in existing_phones:
            duplicates += 1
            if preview_only:
                preview.append({
                    'row_status': 'duplicate',
                    'name': raw_name,
                    'phone': raw_phone,
                    'area': row[C['area']].strip(),
                    'lead_for': row[C['lead_for']].strip(),
                    'owner': row[C['owner']].strip(),
                })
            continue

        try:
            mapping  = _map_lead_for(row[C['lead_for']], row[C['type']])
            cat_id   = mapping.get('category_id')
            company_id, tenant_id = _resolve_category_and_tenant(db, cat_id)

            if not company_id or not tenant_id:
                logger.warning(
                    "[DC_LEAD_SYNC] FAIL-CLOSED: cannot resolve company_id and tenant_id for category %s (row: %s / %s)",
                    cat_id, raw_name, raw_phone
                )
                errors += 1
                if preview_only:
                    preview.append({
                        'row_status': 'error',
                        'name': raw_name,
                        'phone': raw_phone,
                        'area': row[C['area']].strip(),
                        'lead_for': row[C['lead_for']].strip(),
                        'error': f'Cannot resolve company/tenant isolation for category {cat_id}',
                    })
                continue

            status   = _map_status(row[C['status']])
            owner_nm = row[C['owner']].strip()
            emp_id   = _match_owner_to_employee(owner_nm, employees)
            comments = row[C['comments']].strip()
            other    = row[C['other']].strip()
            info_det = row[C['info_det']].strip()
            full_desc = '\n'.join(filter(None, [comments, f'{other} {info_det}'.strip() if other or info_det else '']))
            next_fup = _parse_date_text(row[C['nextfup']])
            last_call = _parse_date_text(row[C['lastcall']])
            source_raw = row[C['source']].strip()
            ref_from   = row[C['ref_from']].strip()

            emp_name = emp_lookup[emp_id].full_name if emp_id and emp_id in emp_lookup else None

            if preview_only:
                preview.append({
                    'row_status': 'new',
                    'name': raw_name,
                    'phone': raw_phone,
                    'area': row[C['area']].strip(),
                    'lead_for': row[C['lead_for']].strip(),
                    'category_label': mapping['label'],
                    'company_id': company_id,
                    'tenant_id': tenant_id,
                    'status': status,
                    'owner': owner_nm,
                    'matched_employee': emp_name,
                    'next_followup': row[C['nextfup']].strip(),
                })
                # Still track phone to avoid showing same number twice in preview
                if raw_phone:
                    existing_phones.add(raw_phone)
                continue

            # Pincode → auto-fill city/state/area when sheet does not supply them
            raw_pincode  = row[C['pincode']].strip() if C.get('pincode') is not None else ''
            raw_area     = row[C['area']].strip()    if C.get('area')    is not None else ''
            _loc = {}
            if raw_pincode and not raw_area:
                _loc = _pincode_to_location(raw_pincode)

            # B2B Meta Lead Form custom fields (Mar 2026)
            _inv_cap  = (row[C['investment_capacity']].strip() if C.get('investment_capacity') is not None else '') or None
            _plan_str = (row[C['planning_to_start']].strip()   if C.get('planning_to_start')   is not None else '') or None
            _ft_biz   = (row[C['full_time_business']].strip()  if C.get('full_time_business')  is not None else '') or None

            lead = CRMLead(
                tenant_id           = tenant_id,
                company_id          = company_id,
                category_id         = cat_id,
                name                = raw_name or 'Unknown',
                phone               = raw_phone or None,
                area                = raw_area or _loc.get('area') or None,
                city                = _loc.get('city') or None,
                state               = _loc.get('state') or None,
                pincode             = raw_pincode or None,
                source              = _map_source(source_raw),
                source_details      = ref_from or None,
                looking_for         = row[C['lead_for']].strip() or None,
                status              = status,
                description         = full_desc or None,
                recent_comments     = comments or None,
                next_followup_date  = next_fup,
                handler_type        = 'staff' if emp_id else 'unassigned',
                handler_id          = emp_lookup[emp_id].emp_code if emp_id and emp_id in emp_lookup else None,
                telecaller_id       = emp_id,
                primary_owner_type  = 'staff' if emp_id else None,
                primary_owner_id    = emp_id,
                investment_capacity = _inv_cap,
                planning_to_start   = _plan_str,
                full_time_business  = _ft_biz,
                created_at          = datetime.utcnow(),
            )
            new_leads.append(lead)

            if raw_phone:
                existing_phones.add(raw_phone)

            # Schedule follow-up if next_fup parsed
            if next_fup:
                new_fups.append({'lead': lead, 'date': next_fup})

            # Last call note
            if last_call:
                new_fups.append({'lead': lead, 'date': last_call, 'done': True})

        except Exception as e:
            logger.warning(f'[DC_LEAD_SYNC] Row parse error: {e}')
            errors += 1
            continue

    if not preview_only and new_leads:
        from app.services.crm_dedup_service import acquire_phone_locks
        acquire_phone_locks(db, config.tenant_id, config.company_id, [l.phone for l in new_leads if l.phone])
        db.add_all(new_leads)
        db.flush()

        from app.services.crm_phone_sync_service import sync_lead_phone_identities
        for lead in new_leads:
            sync_lead_phone_identities(
                db=db,
                lead=lead,
                phone_raw=lead.phone,
                source_channel='google_sheets_sync',
                source_ref=f"sync_config_{config.id}",
                with_lock=False
            )

        # Create followups
        for fup_item in new_fups:
            lead = fup_item['lead']
            if not lead.id:
                continue
            done = fup_item.get('done', False)
            fup = CRMLeadFollowUp(
                lead_id      = lead.id,
                company_id   = lead.company_id,
                scheduled_date = fup_item['date'].date() if isinstance(fup_item['date'], datetime) else fup_item['date'],
                status       = 'completed' if done else 'scheduled',
                handler_type = lead.handler_type,
                handler_id   = lead.handler_id,
            )
            db.add(fup)

        db.commit()

        # Update config stats
        config.total_imported = (config.total_imported or 0) + len(new_leads)
        config.last_synced_at = datetime.utcnow()
        db.add(config)

        # Log run
        run = CRMLeadSyncRun(
            config_id       = config.id,
            config_name     = config.name,
            slot            = 'manual',
            triggered_by    = 'manual',
            tabs_synced     = 1,
            new_leads       = len(new_leads),
            duplicate_leads = duplicates,
            error_count     = errors,
        )
        db.add(run)
        db.commit()

    return {
        'total_imported':   len(new_leads),
        'total_skipped':    duplicates,
        'total_errors':     errors,
        'preview_rows':     preview[:200],  # cap preview at 200 rows
        'tab_results':      [{'tab': 'Sheet1', 'new': len(new_leads), 'skipped': duplicates}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _require_staff(current_user):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail='Staff access only')
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get('/lead-sync/configs')
def list_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    _require_staff(current_user)
    configs = db.query(CRMLeadSyncConfig).order_by(CRMLeadSyncConfig.id).all()
    return {'success': True, 'configs': [c.to_dict() for c in configs]}


@router.post('/lead-sync/configs')
def create_config(
    body: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    _require_staff(current_user)
    name      = (body.get('name') or '').strip()
    sheet_url = (body.get('sheet_url') or '').strip()
    if not name or not sheet_url:
        raise HTTPException(status_code=400, detail='name and sheet_url are required')
    if 'docs.google.com/spreadsheets' not in sheet_url:
        raise HTTPException(status_code=400, detail='Please provide a valid Google Sheets URL')
    cfg = CRMLeadSyncConfig(
        name       = name,
        sheet_url  = sheet_url,
        created_by = getattr(current_user, 'id', None),
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return {'success': True, 'config': cfg.to_dict()}


@router.delete('/lead-sync/configs/{config_id}')
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    _require_staff(current_user)
    cfg = db.query(CRMLeadSyncConfig).filter_by(id=config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail='Config not found')
    db.delete(cfg)
    db.commit()
    return {'success': True}


@router.put('/lead-sync/configs/{config_id}/slots')
def update_slots(
    config_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    _require_staff(current_user)
    cfg = db.query(CRMLeadSyncConfig).filter_by(id=config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail='Config not found')
    for key in ('sync_9am', 'sync_12pm', 'sync_3pm', 'sync_6pm', 'daily_sync_enabled'):
        if key in body:
            setattr(cfg, key, bool(body[key]))
    db.add(cfg)
    db.commit()
    return {'success': True}


@router.get('/lead-sync/preview/{config_id}')
def preview_sync(
    config_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """Preview what would be imported — no DB changes made."""
    _require_staff(current_user)
    cfg = db.query(CRMLeadSyncConfig).filter_by(id=config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail='Config not found')
    employees = db.query(StaffEmployee).all()
    try:
        result = _do_sync(db, cfg, employees, preview_only=True)
        return {'success': True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Preview failed: {e}')


@router.post('/lead-sync/run/{config_id}')
def run_sync(
    config_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """Execute sync for a single config — creates new leads, skips duplicates.
    DC Protocol (F1): Returns 409 if a sync for this config is already in progress."""
    _require_staff(current_user)
    cfg = db.query(CRMLeadSyncConfig).filter_by(id=config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail='Config not found')
    employees = db.query(StaffEmployee).all()
    try:
        result = _do_sync(db, cfg, employees, preview_only=False)
        return {'success': True, **result}
    except RuntimeError as e:
        # Advisory lock conflict → another sync is running
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f'[DC_LEAD_SYNC] Sync failed for config {config_id}: {e}')
        raise HTTPException(status_code=500, detail=f'Sync failed: {e}')


@router.post('/lead-sync/run-all')
def run_all_syncs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """Trigger sync for all active configs."""
    _require_staff(current_user)
    configs = db.query(CRMLeadSyncConfig).filter_by(is_active=True).all()
    if not configs:
        return {'success': True, 'message': 'No active sheets configured.'}
    employees = db.query(StaffEmployee).all()
    total_new = 0
    total_skip = 0
    errors = []
    for cfg in configs:
        try:
            r = _do_sync(db, cfg, employees, preview_only=False)
            total_new  += r['total_imported']
            total_skip += r['total_skipped']
        except Exception as e:
            errors.append({'config': cfg.name, 'error': str(e)})
    msg = f'{total_new} new leads imported, {total_skip} duplicates skipped'
    if errors:
        msg += f', {len(errors)} sheets failed'
    return {'success': True, 'message': msg, 'errors': errors}


@router.post('/lead-sync/trigger-meta')
def trigger_meta_sync(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """
    Trigger an immediate sync for all configs in lead_sync_configs (the scheduler table).
    DC Protocol: Uses sync_all_tabs() — auto-discovers every tab in the sheet including
    tabs added after the last sync. Safe to call multiple times; skips duplicates.
    """
    _require_staff(current_user)
    from app.services.sheets_leads_service import sync_all_tabs
    configs = db.execute(
        text("SELECT id, name, sheet_url, source_tag, company_id FROM lead_sync_configs WHERE is_active=TRUE")
    ).fetchall()
    if not configs:
        return {'success': True, 'message': 'No active meta-sheet configs found.', 'results': []}

    overall_imported = 0
    overall_skipped  = 0
    results = []
    for cfg_row in configs:
        cfg_id, cfg_name, sheet_url, source_tag, company_id = cfg_row
        if not company_id:
            logger.warning("[DC_LEAD_SYNC] FAIL-CLOSED: Skipping config %s (#%s) due to missing company_id", cfg_name, cfg_id)
            continue
        try:
            res = sync_all_tabs(
                sheet_url=sheet_url,
                db=db,
                company_id=company_id,
                source_tag=source_tag or 'Online - M',
            )
            imported   = res.get('total_imported', 0)
            duplicates = res.get('total_duplicates', 0)
            tabs_done  = res.get('tabs_synced', 0)
            overall_imported += imported
            overall_skipped  += duplicates
            import json as _json
            summary_json = _json.dumps({
                'total_imported': imported, 'total_skipped': duplicates,
                'tabs_synced': tabs_done, 'slot': 'manual',
                'tab_results': res.get('tab_results', [])
            })
            db.execute(text("""
                UPDATE lead_sync_configs
                SET last_synced_at=NOW(), last_sync_result=CAST(:res AS jsonb),
                    total_imported=total_imported+:n, updated_at=NOW()
                WHERE id=:id
            """), {'res': summary_json, 'n': imported, 'id': cfg_id})
            db.execute(text("""
                INSERT INTO lead_sync_history
                    (config_id, config_name, triggered_by, slot, tabs_synced, new_leads, duplicates, detail)
                VALUES (:cid, :cname, 'manual', 'manual', :tabs, :new, :dup, CAST(:det AS jsonb))
            """), {'cid': cfg_id, 'cname': cfg_name, 'tabs': tabs_done,
                   'new': imported, 'dup': duplicates, 'det': summary_json})
            db.commit()
            results.append({
                'config': cfg_name, 'tabs_synced': tabs_done,
                'imported': imported, 'duplicates_skipped': duplicates,
                'tab_results': res.get('tab_results', [])
            })
        except Exception as e:
            logger.error(f'[DC_META_SYNC] Failed for {cfg_name}: {e}')
            try: db.rollback()
            except: pass
            results.append({'config': cfg_name, 'error': str(e)})

    return {
        'success': True,
        'total_imported': overall_imported,
        'total_duplicates_skipped': overall_skipped,
        'configs_synced': len(results),
        'results': results,
    }


@router.get('/lead-sync/history')
def get_history(
    limit: int = 50,
    config_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    _require_staff(current_user)
    q = db.query(CRMLeadSyncRun).order_by(CRMLeadSyncRun.synced_at.desc())
    if config_id:
        q = q.filter(CRMLeadSyncRun.config_id == config_id)
    runs = q.limit(limit).all()
    return {'success': True, 'history': [r.to_dict() for r in runs]}


@router.post('/lead-sync/admin/cleanup-duplicates')
def cleanup_duplicate_leads(
    dry_run: bool = True,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    """
    Stage 2B Phase 2R-3B: Scoped Duplicate Lead Discovery & Safety Verification.
    
    Identifies duplicate CRM leads strictly within the authenticated tenant and authorized company scope.
    
    CRITICAL ARCHITECTURAL SAFETY CONTROLS:
    1. Authorization: Requires authoritative RequestContext with TENANT_ADMIN or PLATFORM_SUPERADMIN scope.
       All legacy role-string checks ('vgk4u', 'hr', 'ea') are completely revoked.
    2. Tenant & Company Isolation: Queries are strictly bound to CRMLead.tenant_id == ctx.tenant_id
       and CRMLead.company_id == authorized_company_id. Global partitioning is strictly forbidden.
    3. Runtime DDL Eradicated: All runtime schema and index creation statements have been permanently removed.
    4. Destructive Mutations Disarmed: Destructive merge/delete (dry_run=False) is strictly blocked
       pending approved business rules for survivor selection and 44-table child record reconciliation.
    """
    _require_staff(current_user)

    # 1. Authoritative RequestContext
    from app.core.context import AdminScope, get_current_request_context
    from app.services.auth_context_service import auth_context_service

    ctx = get_current_request_context()
    if not ctx:
        ctx = auth_context_service.build_context(db, current_user)

    # 2. Strict Administrative Scope (Tenant Admin or Platform Superadmin only)
    if not (ctx.is_platform_admin() or ctx.admin_scope == AdminScope.TENANT_ADMIN):
        logger.warning(
            f"[CLEANUP-AUTHZ-DENIED] Staff {ctx.emp_code} (AdminScope: {ctx.admin_scope}) denied duplicate cleanup admin access."
        )
        raise HTTPException(
            status_code=403,
            detail="Tenant Admin or Platform Superadmin access required for duplicate cleanup"
        )

    # 3. Authoritative Company Scope Resolution & Membership Validation
    target_company_id = company_id
    if target_company_id is None:
        if ctx.active_company_id and (ctx.is_platform_admin() or ctx.can_access_company(ctx.active_company_id)):
            target_company_id = ctx.active_company_id
        else:
            raise HTTPException(status_code=400, detail="company_id parameter is required")

    # Anti-tampering & Tenant Isolation check on company
    if not ctx.is_platform_admin():
        if not ctx.can_access_company(target_company_id):
            raise HTTPException(status_code=403, detail="Company access not authorized")

        comp = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == target_company_id,
            AssociatedCompany.client_id == ctx.tenant_id
        ).first()
        if not comp:
            raise HTTPException(status_code=403, detail="Company does not belong to authenticated tenant")
        target_tenant_id = ctx.tenant_id
    else:
        comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == target_company_id).first()
        if not comp:
            raise HTTPException(status_code=404, detail="Company not found")
        target_tenant_id = comp.client_id or 1

    # 4. Destructive Mutations Disarmed (Stop Gate 1, 2, 3, 4)
    if not dry_run:
        raise HTTPException(
            status_code=400,
            detail=(
                "Destructive duplicate cleanup is disabled. "
                "Automated deletion and child reassignment cannot proceed without approved business rules "
                "for survivor selection and multi-table child reconciliation across 44 dependent tables."
            )
        )

    # 5. Scoped Candidate Discovery (dry_run=True)
    _KEEPER_CTE = """
        SELECT
            id AS dup_id,
            tenant_id,
            company_id,
            RIGHT(REGEXP_REPLACE(phone, '[^0-9]', '', 'g'), 10) AS clean_phone,
            MIN(id) OVER (
                PARTITION BY RIGHT(REGEXP_REPLACE(phone, '[^0-9]', '', 'g'), 10)
            ) AS keeper_id
        FROM crm_leads
        WHERE tenant_id = :tenant_id
          AND company_id = :company_id
          AND phone IS NOT NULL 
          AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) >= 10
    """
    params = {'tenant_id': target_tenant_id, 'company_id': target_company_id}

    count_row = db.execute(text(f"""
        SELECT COUNT(*) FROM ({_KEEPER_CTE}) t WHERE dup_id != keeper_id
    """), params).scalar() or 0

    result = {
        'tenant_id': target_tenant_id,
        'company_id': target_company_id,
        'duplicate_leads_found': count_row,
        'dry_run': True,
    }

    if count_row == 0:
        result['message'] = 'No duplicates found within authorized company scope.'
        return {'success': True, **result}

    child_counts = {}
    for table, col in [
        ('crm_lead_followups',   'lead_id'),
        ('crm_lead_notes',       'lead_id'),
        ('crm_lead_assignments', 'lead_id'),
        ('crm_lead_deals',       'lead_id'),
        ('crm_revenue_entries',  'lead_id'),
        ('crm_lead_transactions','lead_id'),
    ]:
        n = db.execute(text(f"""
            SELECT COUNT(*) FROM {table} t
            JOIN ({_KEEPER_CTE}) d ON t.{col} = d.dup_id
            WHERE d.dup_id != d.keeper_id
        """), params).scalar() or 0
        child_counts[table] = n

    result.update({
        'child_records_to_reassign': child_counts,
        'message': 'Dry run complete within authorized scope — no changes made.',
    })
    return {'success': True, **result}
