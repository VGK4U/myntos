"""
Google Sheets → CRM Lead Import Service
DC Protocol Mar 2026

Flow: Facebook Lead Ads → Google Sheets (FB handles this) → Myntreal CRM (we handle this)

Works with:
- Facebook-exported lead sheets (auto-column mapping)
- Google Forms response sheets
- Any sheet with name/phone/email columns

Access method: Public sheet URL (no OAuth needed — user just shares sheet as "Anyone with link can view")
"""

import logging
import re
import requests
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Column name aliases (handles Facebook's export headers + Google Form headers) ──
COL_MAP = {
    'name': ['full_name', 'name', 'full name', 'customer name', 'lead name',
             'your name', 'applicant name', 'contact name'],
    'first_name': ['first_name', 'first name'],
    'last_name':  ['last_name', 'last name', 'surname'],
    'phone': ['phone_number', 'phone', 'mobile', 'mobile number', 'contact number',
              'phone number', 'whatsapp', 'whatsapp number', 'contact', 'mob'],
    'email': ['email', 'email address', 'e-mail', 'mail'],
    'city':  ['city', 'which city', 'location', 'city name', 'your city',
              'which city are you in', 'district'],
    'state': ['state', 'state name'],
    'looking_for': ['looking_for', 'looking for', 'interest', 'requirement type',
                    'what are you looking for', 'enquiry type', 'product interest',
                    'i am looking for'],
    'budget': ['budget', 'budget range', 'your budget', 'price range'],
    'requirements': ['requirements', 'message', 'comments', 'notes', 'any message',
                     'your message', 'any specific requirements', 'additional info',
                     'remarks', 'query'],
    'electricity_bill': ['monthly electricity bill', 'electricity bill',
                         'what is your monthly electricity bill'],
    'property_type': ['type of property', 'property type'],
    'created_time': ['created_time', 'created time', 'date', 'timestamp',
                     'submission time', 'date submitted'],
    'ad_name':   ['ad_name', 'ad name'],
    'form_name': ['form_name', 'form name'],
    'campaign_name': ['campaign_name', 'campaign name'],
    'lead_id': ['id', 'lead id', 'lead_id', 'facebook lead id'],
    # DC Protocol Apr 2026: Facebook Lead form extra fields
    'investment_capacity': [
        'what_is_your_investment_capacity', 'investment capacity',
        'investment_capacity', 'what is your investment capacity',
        'investment range', 'investment plan', 'capacity',
    ],
    'planning_start': [
        'when_are_you_planning_to_start', 'when are you planning to start',
        'when_planning_to_start', 'planned start date', 'start date',
        'when do you plan to start', 'target start', 'plan to start',
    ],
    'full_time_business': [
        'are_you_planning_this_as_a_full-time_business',
        'are you planning this as a full-time business',
        'full time business', 'full_time_business',
        'full-time business', 'business type', 'full time or part time',
    ],
}

def _norm(s: str) -> str:
    return s.lower().strip().replace('?', '').replace('*', '').replace(':', '')

def map_headers(headers: List[str]) -> Dict[str, int]:
    """Returns {field_name: column_index} for all recognized columns."""
    mapping = {}
    for idx, h in enumerate(headers):
        hn = _norm(h)
        for field, aliases in COL_MAP.items():
            if hn in [_norm(a) for a in aliases]:
                if field not in mapping:
                    mapping[field] = idx
                break
    return mapping

def extract_sheet_id(url_or_id: str) -> str:
    """Extract the sheet ID from a full Google Sheets URL or return as-is."""
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url_or_id)
    return match.group(1) if match else url_or_id.strip()

def fetch_sheet_data(sheet_url_or_id: str, gid: str = '0',
                     tab_name: Optional[str] = None) -> Tuple[List[str], List[List[str]]]:
    """
    Fetch sheet data via public CSV export URL.
    Sheet must be shared as "Anyone with link can view".
    DC Protocol Mar 2026: Prefer tab_name (sheet= param) over gid= for reliability.
    The xlsx export returns sequential sheetIds that do NOT match the URL gid
    for sheets with non-sequential tab creation history.
    Returns (headers, rows).
    """
    import csv, io, urllib.parse
    sheet_id = extract_sheet_id(sheet_url_or_id)
    if tab_name:
        # Use sheet=TabName — reliable for public sheets regardless of gid value
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={urllib.parse.quote(tab_name)}"
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    try:
        resp = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code == 403:
            raise ValueError(
                "Sheet is not publicly accessible. Please share it: "
                "File → Share → Anyone with the link → Viewer"
            )
        resp.raise_for_status()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not fetch sheet: {e}")

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]

def row_to_crm_lead(row: List[str], col_map: Dict[str, int],
                    company_id: int, source_tag: str = 'Google Sheets') -> Optional[Dict[str, Any]]:
    """Convert a sheet row into a CRM lead dict."""

    def get(field: str) -> str:
        idx = col_map.get(field)
        if idx is None or idx >= len(row):
            return ''
        return row[idx].strip()

    # Build name
    name = get('name')
    if not name:
        name = f"{get('first_name')} {get('last_name')}".strip()
    if not name:
        return None  # Skip rows with no name

    phone = get('phone')
    email = get('email') or None
    city  = get('city') or None
    state = get('state') or None

    looking  = get('looking_for') or get('property_type') or get('electricity_bill') or None
    req      = get('requirements') or None
    budget   = get('budget') or None
    lead_id  = get('lead_id') or None
    ad_name  = get('ad_name') or get('form_name') or get('campaign_name') or None
    investment_capacity = get('investment_capacity') or None
    planning_start      = get('planning_start') or None
    full_time_business  = get('full_time_business') or None

    # Build description — DC Protocol Apr 2026: capture all recognised extra fields
    desc_parts = [f"Imported from {source_tag}"]
    if ad_name:              desc_parts.append(f"Form/Ad: {ad_name}")
    if looking:              desc_parts.append(f"Looking for: {looking}")
    if req:                  desc_parts.append(f"Message: {req}")
    if budget:               desc_parts.append(f"Budget: {budget}")
    if investment_capacity:  desc_parts.append(f"Investment Capacity: {investment_capacity}")
    if planning_start:       desc_parts.append(f"Planning to Start: {planning_start}")
    if full_time_business:   desc_parts.append(f"Full-Time Business: {full_time_business}")

    source_details = f"{{'source': '{source_tag}', 'lead_id': '{lead_id}', 'ad': '{ad_name}'}}"

    return {
        'company_id':           company_id,
        'name':                 name[:200],
        'phone':                phone[:20]  if phone else None,
        'email':                email[:200] if email else None,
        'city':                 city[:100]  if city  else None,
        'state':                state[:100] if state else None,
        'source':               'Online - M',
        'source_details':       source_details[:1000],
        'status':               'new',
        'priority':             'high',
        'handler_type':         'unassigned',
        'description':          '\n'.join(desc_parts)[:2000],
        'looking_for':          looking[:500]             if looking else None,
        'requirements':         req[:1000]                if req     else None,
        'investment_capacity':  investment_capacity[:100] if investment_capacity else None,
        'tags':                 'sheets_import',
        'created_by_type':      'system',
        'created_by_id':        'sheets_import',
    }

def is_duplicate(phone: Optional[str], email: Optional[str],
                 fb_lead_id: Optional[str], db) -> bool:
    """Check if this lead already exists in CRM by phone, email, or FB lead_id."""
    from sqlalchemy import text
    try:
        if fb_lead_id and fb_lead_id not in ('', 'None', 'nan'):
            row = db.execute(text(
                "SELECT id FROM crm_leads WHERE source_details LIKE :pat LIMIT 1"
            ), {'pat': f"%'lead_id': '{fb_lead_id}'%"}).fetchone()
            if row:
                return True

        if phone and len(phone) >= 8:
            clean_phone = re.sub(r'[^0-9]', '', phone)[-10:]
            # DC-DEDUP-002: Check given phone against BOTH phone and alternate_phone columns
            row = db.execute(text(
                "SELECT id FROM crm_leads WHERE "
                "regexp_replace(phone, '[^0-9]', '', 'g') LIKE :ph "
                "OR regexp_replace(alternate_phone, '[^0-9]', '', 'g') LIKE :ph LIMIT 1"
            ), {'ph': f'%{clean_phone}'}).fetchone()
            if row:
                return True
    except Exception as e:
        logger.warning(f"Duplicate check error: {e}")
    return False

def import_sheet_to_crm(sheet_url: str, db, company_id: int = 1,
                         source_tag: str = 'Google Sheets',
                         gid: str = '0',
                         tab_name: Optional[str] = None,
                         skip_duplicates: bool = True) -> Dict[str, Any]:
    """
    Fetch a single sheet tab via CSV export and import leads into CRM.
    DC Protocol Mar 2026: used as a fallback when xlsx parse is not available,
    and as the public API for single-tab imports via the CRM endpoint.
    Column detection is fully dynamic — driven by the header row.
    Returns summary dict.
    """
    try:
        headers, rows = fetch_sheet_data(sheet_url, gid=gid, tab_name=tab_name)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not headers:
        return {'success': False, 'error': 'Sheet is empty or could not be read'}

    return _import_rows_to_crm(
        headers=headers,
        rows=rows,
        db=db,
        company_id=company_id,
        source_tag=source_tag,
        skip_duplicates=skip_duplicates,
    )


def _col_letter_to_num(col_str: str) -> int:
    """Convert Excel column letters (A, B, AA, etc.) to 0-based index."""
    n = 0
    for ch in col_str:
        n = n * 26 + (ord(ch.upper()) - ord('A') + 1)
    return n - 1


def _parse_xlsx_all_sheets(sheet_id: str) -> Optional[Dict[str, Tuple[List[str], List[List[str]]]]]:
    """
    Download the Google Sheet as xlsx and parse ALL worksheets.
    DC Protocol Mar 2026: The xlsx export is the ONLY reliable way to get all
    tab data from a 'Anyone with link' shared sheet without the Sheets API.
    - sheet=TabName in the CSV URL only returns the FIRST tab (silent fallback)
    - gid= in the CSV URL uses real internal gids, not the xlsx sequential sheetIds
    - xlsx contains all data for all tabs in one download

    Returns {tab_name: (headers, data_rows)} or None on failure.
    """
    import re, io, zipfile, html as _html

    try:
        xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        r = requests.get(xlsx_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200 or r.content[:4] != b'PK\x03\x04':
            return None

        z = zipfile.ZipFile(io.BytesIO(r.content))

        # 1. Shared strings table (xlsx stores cell strings here by index)
        shared_strings: List[str] = []
        try:
            ss_xml = z.read('xl/sharedStrings.xml').decode('utf-8')
            shared_strings = [_html.unescape(s) for s in re.findall(r'<t[^>]*>(.*?)</t>', ss_xml)]
        except Exception:
            pass  # Sheet may have no strings (all numbers)

        # 2. Tab names from workbook.xml (in order)
        wb_xml = z.read('xl/workbook.xml').decode('utf-8')
        tab_names = re.findall(r'<sheet\b[^>]+\bname="([^"]+)"', wb_xml)
        if not tab_names:
            return None

        # 3. r:id → file mapping from workbook rels
        rels_xml = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')
        rid_to_file: Dict[str, str] = {}
        for rid, target in re.findall(r'<Relationship\b[^>]+\bId="([^"]+)"[^>]+\bTarget="([^"]+)"', rels_xml):
            rid_to_file[rid] = target  # e.g. rId5 → worksheets/sheet2.xml

        # 4. Per-sheet r:id from workbook.xml
        sheet_rids = re.findall(r'<sheet\b[^>]+\br:id="([^"]+)"', wb_xml)

        def _cell_value(cell_xml: str) -> str:
            is_shared = 't="s"' in cell_xml
            v_m = re.search(r'<v>(.*?)</v>', cell_xml, re.DOTALL)
            if not v_m:
                return ''
            raw = v_m.group(1)
            if is_shared:
                try:
                    idx = int(raw)
                    return shared_strings[idx] if idx < len(shared_strings) else ''
                except (ValueError, IndexError):
                    return ''
            return raw

        def _parse_worksheet(xml_content: str) -> Tuple[List[str], List[List[str]]]:
            rows_dict: Dict[int, Dict[int, str]] = {}
            for row_num_str, row_xml in re.findall(
                r'<row\b[^>]+\br="(\d+)"[^>]*>(.*?)</row>', xml_content, re.DOTALL
            ):
                row_num = int(row_num_str)
                cells: Dict[int, str] = {}
                for full_cell in re.findall(r'<c\b[^/]*?(?:/>|>.*?</c>)', row_xml, re.DOTALL):
                    ref_m = re.search(r'\br="([A-Z]+)\d+"', full_cell)
                    if ref_m:
                        col_idx = _col_letter_to_num(ref_m.group(1))
                        cells[col_idx] = _cell_value(full_cell)
                if cells:
                    rows_dict[row_num] = cells

            if not rows_dict:
                return [], []
            max_row = max(rows_dict.keys())
            max_col = max(c for row in rows_dict.values() for c in row.keys()) + 1
            all_rows = [
                [rows_dict.get(rn, {}).get(c, '') for c in range(max_col)]
                for rn in range(1, max_row + 1)
            ]
            headers = all_rows[0] if all_rows else []
            data    = all_rows[1:] if len(all_rows) > 1 else []
            return headers, data

        # 5. Parse each worksheet in tab order
        result: Dict[str, Tuple[List[str], List[List[str]]]] = {}
        for tab_name, rid in zip(tab_names, sheet_rids):
            ws_file = rid_to_file.get(rid, '')
            if not ws_file:
                result[tab_name] = ([], [])
                continue
            full_path = f'xl/{ws_file}' if not ws_file.startswith('xl/') else ws_file
            try:
                ws_xml = z.read(full_path).decode('utf-8')
                headers, data = _parse_worksheet(ws_xml)
                result[tab_name] = (headers, data)
            except Exception as e:
                logger.warning(f"[XLSX] Could not parse worksheet {tab_name!r} ({full_path}): {e}")
                result[tab_name] = ([], [])

        logger.info(f"[XLSX] ✅ Parsed {len(result)} tabs: {list(result.keys())}")
        return result

    except Exception as e:
        logger.warning(f"[XLSX] Failed to parse xlsx for {sheet_id}: {e}")
        return None


def _import_rows_to_crm(
    headers: List[str],
    rows: List[List[str]],
    db,
    company_id: int,
    source_tag: str,
    skip_duplicates: bool = True,
) -> Dict[str, Any]:
    """
    Core import logic: take pre-fetched (headers, rows), map columns dynamically,
    insert new non-duplicate leads into CRM.
    DC Protocol Mar 2026: column detection is purely header-driven (dynamic).
    """
    from app.models.crm import CRMLead

    if not headers:
        return {'success': False, 'error': 'No headers in sheet data'}

    col_map = map_headers(headers)
    if not col_map.get('name') and not (col_map.get('first_name') or col_map.get('last_name')):
        return {
            'success': False,
            'error': 'Could not find a name column. Ensure sheet has headers like "full_name", "name", or "first_name".',
            'detected_headers': headers[:20],
        }

    result: Dict[str, Any] = {
        'success':           True,
        'total_rows':        len(rows),
        'imported':          0,
        'skipped_duplicates':0,
        'skipped_empty':     0,
        'errors':            [],
        'column_mapping':    {k: headers[v] for k, v in col_map.items()},
    }

    for row in rows:
        if not any(cell.strip() for cell in row):
            result['skipped_empty'] += 1
            continue

        lead_data = row_to_crm_lead(row, col_map, company_id, source_tag)
        if not lead_data:
            result['skipped_empty'] += 1
            continue

        # DC Protocol Apr 2026: Capture ALL unmapped columns into description
        # so no form field is ever silently dropped regardless of future form changes
        _mapped_col_indices = set(col_map.values())
        _extra_parts = []
        for _ci, _hdr in enumerate(headers):
            if _ci not in _mapped_col_indices and _ci < len(row):
                _val = row[_ci].strip() if _ci < len(row) else ''
                if _val and _hdr.strip():
                    _label = _hdr.strip().replace('?', '').replace('_', ' ').replace('-', ' ').title()
                    _extra_parts.append(f"{_label}: {_val}")
        if _extra_parts:
            _existing_desc = lead_data.get('description') or ''
            _combined = (_existing_desc + '\n' + '\n'.join(_extra_parts)).strip()
            lead_data['description'] = _combined[:2000]

        if skip_duplicates:
            fb_id = row[col_map['lead_id']] if 'lead_id' in col_map and col_map['lead_id'] < len(row) else None
            if is_duplicate(lead_data.get('phone'), lead_data.get('email'), fb_id, db):
                result['skipped_duplicates'] += 1
                continue

        try:
            crm_lead = CRMLead(**lead_data)
            db.add(crm_lead)
            db.commit()
            result['imported'] += 1
        except Exception as e:
            db.rollback()
            result['errors'].append(str(e)[:200])
            if len(result['errors']) >= 10:
                break

    return result


def get_sheet_tabs(sheet_url_or_id: str) -> List[Dict]:
    """
    Discover all tabs in a Google Sheet.
    DC Protocol Mar 2026: Downloads xlsx once, parses workbook.xml for tab names,
    then reads each worksheet directly from the xlsx zip — no CSV URL gid needed.
    """
    sheet_id = extract_sheet_id(sheet_url_or_id)
    sheets = _parse_xlsx_all_sheets(sheet_id)
    if sheets:
        tabs = []
        for tab_name, (headers, data) in sheets.items():
            non_empty = [r for r in data if any(c.strip() for c in r)]
            tabs.append({
                'tab_name': tab_name,
                'title':    tab_name,
                'rows':     len(non_empty),
                'headers':  headers[:8],
            })
        return tabs

    # Fallback: gid=0 only
    logger.warning(f"[SHEET-TABS] xlsx parse failed, falling back to gid=0 for {sheet_id}")
    import csv, io
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        cr = requests.get(csv_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if cr.status_code == 200 and cr.text.strip() and not cr.text.strip().startswith('<'):
            rows = list(csv.reader(io.StringIO(cr.text)))
            return [{'tab_name': None, 'title': 'Sheet1',
                     'rows': max(0, len(rows) - 1), 'headers': rows[0][:8] if rows else []}]
    except Exception:
        pass
    return []


def sync_all_tabs(sheet_url: str, db, company_id: int = 1,
                  source_tag: str = 'Online - M',
                  skip_duplicates: bool = True) -> Dict[str, Any]:
    """
    Sync ALL tabs from a Google Sheet into CRM in a single xlsx download.
    DC Protocol Mar 2026: downloads xlsx once, parses all worksheets directly,
    maps columns dynamically from each tab's header row.
    Future tabs added to the sheet are automatically picked up on the next sync.
    """
    sheet_id = extract_sheet_id(sheet_url)
    result = {
        'success':          True,
        'sheet_id':         sheet_id,
        'tabs_synced':      0,
        'tabs_skipped':     0,
        'total_imported':   0,
        'total_duplicates': 0,
        'total_errors':     0,
        'tab_results':      [],
    }

    # Single xlsx download for all tabs
    sheets = _parse_xlsx_all_sheets(sheet_id)

    if not sheets:
        # Fallback: use CSV import for gid=0 only
        logger.warning(f"[SYNC] xlsx parse failed, using CSV fallback for {sheet_id}")
        tab_result = import_sheet_to_crm(
            sheet_url=sheet_url, db=db, company_id=company_id,
            source_tag=source_tag, skip_duplicates=skip_duplicates,
        )
        if tab_result.get('success'):
            result['tabs_synced'] = 1
            result['total_imported'] = tab_result.get('imported', 0)
            result['total_duplicates'] = tab_result.get('skipped_duplicates', 0)
            result['tab_results'] = [{'tab': 'Sheet1', **tab_result}]
        else:
            result['success'] = False
            result['tab_results'] = [{'tab': 'Sheet1', 'error': tab_result.get('error')}]
        return result

    for tab_name, (headers, data) in sheets.items():
        try:
            tab_result = _import_rows_to_crm(
                headers=headers,
                rows=data,
                db=db,
                company_id=company_id,
                source_tag=f"{source_tag} — {tab_name}",
                skip_duplicates=skip_duplicates,
            )
            if tab_result.get('success'):
                result['tabs_synced']      += 1
                result['total_imported']   += tab_result.get('imported', 0)
                result['total_duplicates'] += tab_result.get('skipped_duplicates', 0)
                result['total_errors']     += len(tab_result.get('errors', []))
                result['tab_results'].append({
                    'tab':                tab_name,
                    'imported':           tab_result.get('imported', 0),
                    'duplicates_skipped': tab_result.get('skipped_duplicates', 0),
                    'total_rows':         tab_result.get('total_rows', 0),
                    'headers_detected':   list(tab_result.get('column_mapping', {}).keys()),
                })
            else:
                result['tabs_skipped'] += 1
                result['tab_results'].append({'tab': tab_name, 'error': tab_result.get('error', 'unknown')})
        except Exception as e:
            result['tabs_skipped'] += 1
            result['tab_results'].append({'tab': tab_name, 'error': str(e)})

    return result
