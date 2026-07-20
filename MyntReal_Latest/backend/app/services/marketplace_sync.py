"""
MNR E-Com Lite — Google Sheet Sync Service
Reads data via public gviz/tq CSV export (no OAuth needed).
DC Protocol: company_id enforced on all upserted records.

SHEET COLUMN MAP (0-indexed) — verified March 2026 against live sheet (32 columns):
  0  = With us?
  1  = TALLY UPDATE
  2  = REF. NO.
  3  = S.No.
  4  = Available Company
  5  = CODE NUMBER (SKU — may be #VALUE! formula error → auto-generate)
  6  = Items (name)
  7  = Category
  8  = Images (embedded — not accessible via CSV, returns empty)
  9  = Images URL (direct URL string — active for image display)
  10 = Compatible with
  11 = Model (brand)
  12 = Color
  13 = Specification
  14 = Additional Info?
  15 = Dealer Price
  16 = Tax % (GST rate, e.g. "5%" or "18%")
  17 = Tax Amount (derived — not synced)
  18 = Price with GST (derived — not synced)
  19 = Available Quantity (stock counts — always synced)
  20 = Proc. cost
  21 = Proc. Transport
  22 = proc. Ex. Tax
  23 = Proc. Tax%
  24 = Proc. With Tax
  25 = Price at competitor
  26 = Cost
  27 = Comparison
  28 = Mark up
"""

import csv
import io
import os
import re
import logging
import urllib.request
from datetime import datetime
from typing import Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.marketplace import MarketspareItem, MarketplaceSyncLog, MarketplaceProcurementRequest, MarketplaceSegment
from app.services.marketplace_image import get_image_provider

logger = logging.getLogger(__name__)

SHEET_ID = '1zNWlACQ5MbgTROPNfAgyyDMeoSB9KjTl'
GVIZ_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid=0'


def _sheet_url_to_csv(url: str) -> str:
    """Convert a Google Sheets URL (any format) to a gviz CSV export URL."""
    if 'gviz/tq' in url:
        return url
    import re
    m = re.search(r'/spreadsheets/d/([^/]+)', url)
    if m:
        sheet_id = m.group(1)
        return f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0'
    return url

COL_MAP = {
    'company_name':     4,   # col 4  = "Available Company"
    'sku':              5,   # col 5  = "CODE NUMBER"
    'name':             6,   # col 6  = "Items"
    'category':         7,   # col 7  = "Category"
    'image':            8,   # col 8  = "Images" (embedded — inaccessible via CSV)
    'image_url':        9,   # col 9  = "Image drive URL"
    'compatible':       10,  # col 10 = "Compatible with"
    'model':            11,  # col 11 = "Model"
    'color':            12,  # col 12 = "Color"
    'spec':             13,  # col 13 = "Specification"
    'warranty_details': 14,  # col 14 = "Warranty Details"   ← sheet added this column
    'speciality':       15,  # col 15 = "Additional Info?"
    'dealer_price':     16,  # col 16 = "Dealer Price"       ← was 15, shifted +1
    'gst_pct':          17,  # col 17 = "Tax %"              ← was 16, shifted +1
    # col 18 = Tax Amount  (derived — not synced)
    # col 19 = Price with GST (derived — not synced)
    'available_qty':    20,  # col 20 = "Available Quantity" ← was 19, shifted +1
    'proc_cost':        21,  # col 21 = "Proc. cost"         ← was 20, shifted +1
    'warranty_cost':    22,  # col 22 = "Warranty Cost"      ← sheet added this column
    'proc_transport':   23,  # col 23 = "Proc. Transport"    ← was 21, shifted +2
    'proc_ex_tax':      24,  # col 24 = "proc. Ex. Tax"      ← was 22, shifted +2
    'proc_tax_pct':     25,  # col 25 = "Proc. Tax%"         ← was 23, shifted +2
    'proc_with_tax':    26,  # col 26 = "Proc. With Tax"     ← was 24, shifted +2
}

_WARRANTY_COL_MAP_INITIALIZED = False

def _discover_warranty_columns_from_header(header_row: List[str]):
    """Detect Warranty Details & Warranty Cost column indices from the sheet header row at runtime."""
    global _WARRANTY_COL_MAP_INITIALIZED
    if _WARRANTY_COL_MAP_INITIALIZED:
        return
    for idx, cell in enumerate(header_row):
        normalized = cell.strip().lower()
        if normalized in ('warranty details', 'warranty_details'):
            COL_MAP['warranty_details'] = idx
            logger.info(f'[COL_MAP] Discovered warranty_details at column {idx}')
        elif normalized in ('warranty cost', 'warranty_cost'):
            COL_MAP['warranty_cost'] = idx
            logger.info(f'[COL_MAP] Discovered warranty_cost at column {idx}')
    _WARRANTY_COL_MAP_INITIALIZED = True
    logger.info(f'[COL_MAP] warranty_details={COL_MAP["warranty_details"]}, warranty_cost={COL_MAP["warranty_cost"]}')


def _fetch_sheet_csv(url: str = None) -> str:
    """Download raw CSV from Google Sheets gviz endpoint. Uses GVIZ_URL if url not provided."""
    target = _sheet_url_to_csv(url) if url else GVIZ_URL
    req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def _clean_price(raw: str) -> float:
    """Parse price string, strip currency symbols and commas."""
    if not raw:
        return 0.0
    cleaned = re.sub(r'[^\d.]', '', raw.strip())
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _clean_int(raw: str) -> int:
    """Parse integer string (e.g. '10', '10.0'). Returns 0 if invalid."""
    if not raw or raw.strip() == '':
        return 0
    cleaned = re.sub(r'[^\d]', '', raw.strip())
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _clean_gst(raw: str) -> float | None:
    """Parse GST % string like '5%', '18%', '18.0' → float. None if missing/invalid."""
    if not raw or raw.strip() == '':
        return None
    cleaned = re.sub(r'[^\d.]', '', raw.strip())
    try:
        val = float(cleaned)
        return val if 0 < val <= 100 else None
    except ValueError:
        return None


def _is_formula_error(val: str) -> bool:
    return val.strip().startswith('#') or val.strip() == ''


def _build_sku(raw_sku: str, category: str, row_num: int) -> str:
    """
    Use sheet SKU if valid; auto-generate if formula error or empty.
    Auto format: MNR-SP-{CAT_ABBREV}-{ROW}
    """
    if raw_sku and not _is_formula_error(raw_sku):
        return raw_sku.strip().upper().replace(' ', '-')
    cat_abbrev = re.sub(r'[^A-Z]', '', category.upper())[:4] or 'SP'
    return f'MNR-SP-{cat_abbrev}-{row_num}'


def _clean_price_nullable(raw: str):
    """Parse price, return None if zero/empty (for proc fields that may be 0 meaning not set)."""
    if not raw or raw.strip() == '' or _is_formula_error(raw):
        return None
    cleaned = re.sub(r'[^\d.]', '', raw.strip())
    try:
        val = float(cleaned)
        return round(val, 2) if val > 0 else None
    except ValueError:
        return None


def _extract_fields(row: List[str]) -> dict:
    """Extract model_compat, color, specifications, speciality, company_name, image_url, proc costs."""
    def _get(idx): return row[idx].strip() if len(row) > idx else ''
    compatible   = _get(COL_MAP['compatible'])
    color        = _get(COL_MAP['color'])
    spec         = _get(COL_MAP['spec'])
    speciality   = _get(COL_MAP['speciality'])
    company_name = _get(COL_MAP['company_name'])
    image_url    = _get(COL_MAP['image_url'])
    # description = human-readable summary
    parts = []
    if compatible: parts.append(f'Compatible: {compatible}')
    if color: parts.append(f'Color: {color}')
    if spec: parts.append(spec)
    warranty_details_raw = _get(COL_MAP['warranty_details'])
    warranty_cost_raw    = _get(COL_MAP['warranty_cost'])
    return {
        'model_compat':   compatible or None,
        'color':          color or None,
        'specifications': spec or None,
        'speciality':     speciality or None,
        'company_name':   company_name or None,
        'image_url':      image_url or None,
        'description':    ' | '.join(parts) if parts else None,
        'proc_cost':      _clean_price_nullable(_get(COL_MAP['proc_cost'])),
        'proc_transport': _clean_price_nullable(_get(COL_MAP['proc_transport'])),
        'proc_ex_tax':    _clean_price_nullable(_get(COL_MAP['proc_ex_tax'])),
        'proc_tax_pct':   _clean_gst(_get(COL_MAP['proc_tax_pct'])),
        'proc_with_tax':  _clean_price_nullable(_get(COL_MAP['proc_with_tax'])),
        'warranty_details': warranty_details_raw or None,
        'warranty_cost':    _clean_price_nullable(warranty_cost_raw),
    }


def parse_sheet_rows(sheet_url: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch and parse the sheet.
    sheet_url: if provided, overrides the default GVIZ_URL.
    Returns (valid_rows, error_rows).
    """
    raw_csv = _fetch_sheet_csv(sheet_url)
    reader = csv.reader(io.StringIO(raw_csv))
    all_rows = list(reader)

    if not all_rows:
        raise ValueError('Sheet returned no data')

    _discover_warranty_columns_from_header(all_rows[0])

    image_provider = get_image_provider()
    valid = []
    errors = []

    for row_num, row in enumerate(all_rows[1:], start=2):
        try:
            if len(row) <= COL_MAP['name']:
                continue
            name = row[COL_MAP['name']].strip()
            if not name:
                continue

            category  = row[COL_MAP['category']].strip() if len(row) > COL_MAP['category'] else ''
            raw_sku   = row[COL_MAP['sku']].strip() if len(row) > COL_MAP['sku'] else ''
            sku       = _build_sku(raw_sku, category, row_num)
            brand     = row[COL_MAP['model']].strip() if len(row) > COL_MAP['model'] else ''
            price     = _clean_price(row[COL_MAP['dealer_price']] if len(row) > COL_MAP['dealer_price'] else '')
            gst_pct   = _clean_gst(row[COL_MAP['gst_pct']] if len(row) > COL_MAP['gst_pct'] else '')
            avail_qty = _clean_int(row[COL_MAP['available_qty']] if len(row) > COL_MAP['available_qty'] else '')
            fields    = _extract_fields(row)
            # Use image_url column (col 9) for image resolution — Drive URLs also expand via API
            images    = image_provider.get_images(row, COL_MAP['image_url'])

            valid.append({
                'sku':            sku,
                'name':           name,
                'category_name':  category.upper() if category else 'UNCATEGORISED',
                'dealer_price':   price,
                'gst_percent':    gst_pct,
                'available_qty':  avail_qty,
                'description':    fields['description'],
                'brand':          brand or None,
                'model_compat':   fields['model_compat'],
                'specifications': fields['specifications'],
                'color':          fields['color'],
                'speciality':     fields['speciality'],
                'company_name':   fields['company_name'],
                'image_url':      fields['image_url'],
                'image_data':     images,
                'proc_cost':      fields['proc_cost'],
                'proc_transport': fields['proc_transport'],
                'proc_ex_tax':    fields['proc_ex_tax'],
                'proc_tax_pct':   fields['proc_tax_pct'],
                'proc_with_tax':  fields['proc_with_tax'],
                'warranty_details': fields['warranty_details'],
                'warranty_cost':    fields['warranty_cost'],
            })
        except Exception as e:
            errors.append({'row': row_num, 'error': str(e)})

    return valid, errors


def _generate_proc_number_sync(db: Session, company_id: int) -> str:
    """Generate unique ZYPR-YYYYMM-NNNN procurement number (inline — avoids circular import)."""
    ym = datetime.utcnow().strftime('%Y%m')
    prefix = f'ZYPR-{ym}-'
    count_row = db.execute(text(
        "SELECT COUNT(*)+1 FROM marketplace_procurement_requests WHERE procurement_number LIKE :pfx AND company_id = :cid"
    ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
    count = int(count_row[0]) if count_row else 1
    proc_number = f'{prefix}{count:04d}'
    while db.query(MarketplaceProcurementRequest).filter_by(procurement_number=proc_number).first():
        count += 1
        proc_number = f'{prefix}{count:04d}'
    return proc_number


def _auto_raise_procurement(db: Session, company_id: int) -> int:
    """
    After sync, auto-raise ZYPR for products that:
      (a) available_qty == 0 (out of stock), OR
      (b) available_qty < min_stock_threshold (below min order level, when threshold > 0)
    that have no open (pending/ordered) procurement request.
    Returns count of new ZYPR records created.
    """
    from sqlalchemy import or_
    candidates = db.query(MarketspareItem).filter(
        MarketspareItem.company_id == company_id,
        MarketspareItem.is_active == True,
        or_(
            MarketspareItem.available_qty == 0,
            (MarketspareItem.min_stock_threshold > 0) & (MarketspareItem.available_qty < MarketspareItem.min_stock_threshold),
        )
    ).all()

    raised = 0
    for item in candidates:
        existing = db.query(MarketplaceProcurementRequest).filter(
            MarketplaceProcurementRequest.sku == item.sku,
            MarketplaceProcurementRequest.company_id == company_id,
            MarketplaceProcurementRequest.status.in_(['pending', 'ordered']),
        ).first()
        if existing:
            continue

        try:
            below_min = (
                int(item.min_stock_threshold or 0) > 0 and
                int(item.available_qty or 0) < int(item.min_stock_threshold or 0)
            )
            qty = int(item.available_qty or 0)
            threshold = int(item.min_stock_threshold or 0)
            shortfall = max(threshold - qty, 1 if qty == 0 else 0)
            # Procurement budget estimate using proc_with_tax (col 31 — base + transport + tax)
            budget_est = None
            if item.proc_with_tax and float(item.proc_with_tax) > 0:
                budget_est = round(float(item.proc_with_tax) * shortfall, 2)

            if qty == 0:
                note = f'Auto-raised: out of stock (qty=0)'
            else:
                note = f'Auto-raised: stock ({qty}) below min order level ({threshold})'
            if budget_est:
                note += f' | Proc. with Tax: ₹{item.proc_with_tax:,.2f}/unit × {shortfall} unit(s) = ₹{budget_est:,.2f} est. budget'

            proc_number = _generate_proc_number_sync(db, company_id)
            proc = MarketplaceProcurementRequest(
                procurement_number=proc_number,
                po_id=None,
                po_item_id=None,
                sku=item.sku,
                product_name=item.name,
                ordered_qty=0,
                available_qty=qty,
                shortfall_qty=shortfall,
                status='pending',
                triggered_by='auto_sync',
                procurement_notes=note,
                company_id=company_id,
            )
            db.add(proc)
            db.flush()
            # ── Store task hook: add phase for auto-sync PR ──────────────
            try:
                from app.services.store_task_service import add_pr_phase as _sync_add_pr
                _sync_add_pr(db, proc, company_id)
            except Exception as _hook_e:
                logger.warning(f'[StoreTask] marketplace_sync PR hook: {_hook_e}')
            # ─────────────────────────────────────────────────────────────
            raised += 1
        except Exception as e:
            logger.warning(f'[MARKETPLACE-SYNC] Auto-procurement failed for sku={item.sku}: {e}')

    return raised


_OBJ_STORE_KEY_PREFIX = 'marketplace/product-images'


def _sync_image_url(existing, sheet_url: str, sku: str, is_protected: bool) -> None:
    """
    DC Protocol Mar 2026: Smart image_url sync during Google Sheet import.

    Rules:
    1. Field is in override_fields (protected) → never touch it.
    2. Sheet cell is empty → keep existing URL unchanged (never wipe Object Storage URL).
    3a. Google Drive share URLs → store as-is (Drive serve-page, not raw bytes — download
        would yield HTML garbage; browser can render uc?export=view links for public files).
    3b. Other external http/https URLs → download, upload to Object Storage,
        store /api/v1/marketplace/images/{sku}.png URL.
    4. Sheet has our own /api/v1/marketplace/images/ URL already → store as-is.
    5. Any download/upload failure → keep existing URL, log warning.
    """
    if is_protected:
        return

    sheet_url = (sheet_url or '').strip()

    # Rule 2: empty sheet cell — never overwrite an existing URL
    if not sheet_url:
        return

    # Rule 4: already our own Object Storage endpoint URL — store as-is
    if sheet_url.startswith('/api/v1/marketplace/images/'):
        existing.image_url = sheet_url
        return

    if sheet_url.startswith('http://') or sheet_url.startswith('https://'):
        # Rule 3a: Google Drive URLs — convert to direct download URL and upload to Object Storage
        if 'drive.google.com' in sheet_url:
            try:
                import urllib.request as _ur
                import re as _re
                file_id = None
                m = _re.search(r'/file/d/([a-zA-Z0-9_-]+)', sheet_url)
                if not m:
                    m = _re.search(r'[?&]id=([a-zA-Z0-9_-]+)', sheet_url)
                if m:
                    file_id = m.group(1)
                if file_id:
                    direct_url = f'https://drive.google.com/uc?export=download&id={file_id}'
                    req = _ur.Request(direct_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with _ur.urlopen(req, timeout=15) as resp:
                        content = resp.read()
                    if content and len(content) > 500:
                        ext = 'png'
                        ct = resp.headers.get('Content-Type', '')
                        if 'jpeg' in ct or 'jpg' in ct:
                            ext = 'jpg'
                        elif 'webp' in ct:
                            ext = 'webp'
                        elif 'gif' in ct:
                            ext = 'gif'
                        filename = f'{sku}.{ext}'
                        from app.services.object_storage import Client as _ObjClient
                        _ObjClient().upload_from_bytes(f'{_OBJ_STORE_KEY_PREFIX}/{filename}', content)
                        existing.image_url = f'/api/v1/marketplace/images/{filename}'
                        logger.info(f'[SyncImg] Drive image uploaded to Object Storage for SKU {sku}')
                        return
                existing.image_url = sheet_url
                logger.info(f'[SyncImg] Drive URL stored as-is for SKU {sku} (no file_id extracted)')
            except Exception as e:
                logger.warning(f'[SyncImg] Drive download failed for SKU {sku}, storing URL as-is: {e}')
                existing.image_url = sheet_url
            return

        # Rule 3b: other external URL — download and upload to Object Storage
        try:
            import urllib.request as _ur
            req = _ur.Request(sheet_url, headers={'User-Agent': 'Mozilla/5.0'})
            with _ur.urlopen(req, timeout=15) as resp:
                content = resp.read()

            if not content:
                raise ValueError('Empty response from image URL')

            # Detect extension from URL or content-type
            from urllib.parse import urlparse as _up
            parsed_path = _up(sheet_url).path
            ext = parsed_path.rsplit('.', 1)[-1].lower() if '.' in parsed_path else 'png'
            if ext not in ('png', 'jpg', 'jpeg', 'webp', 'gif'):
                ext = 'png'

            filename = f'{sku}.{ext}'
            from app.services.object_storage import Client as _ObjClient
            _ObjClient().upload_from_bytes(f'{_OBJ_STORE_KEY_PREFIX}/{filename}', content)

            existing.image_url = f'/api/v1/marketplace/images/{filename}'
            logger.info(f'[SyncImg] Uploaded sheet image for SKU {sku} → Object Storage')
        except Exception as e:
            logger.warning(f'[SyncImg] Could not download/upload image for SKU {sku} ({sheet_url[:80]}): {e}')
        return

    # Any other value (relative path, etc.) — store as-is
    existing.image_url = sheet_url


def run_stock_sync(db: Session, company_id: int = 1, triggered_by: str = 'auto') -> Dict[str, Any]:
    """
    DC-STOCK-MKT-001: Sync stock_item_master → marketplace_spares.
    All active stock items are published automatically.
    - dealer_price = stock item selling_rate (pricing engine applies markup on top at runtime)
    - available_qty = sum of latest stock_ledger balance across ALL companies per item
    - image_url = first Google Drive folder_link from stock_item_images (if any)
    - source = 'stock', stock_item_id = item.id
    - Respects manually_overridden / override_fields for protected marketplace fields
    - source='direct' marketplace records are never touched
    """
    from app.models.staff_accounts import StockItemMaster, StockItemImage, StockLedger
    from decimal import Decimal

    logger.info(f'[DC-STOCK-MKT-001] Starting stock→marketplace sync, company_id={company_id}, by={triggered_by}')

    # Pre-build available_qty map: item_id → sum of latest balance across all companies
    # Using MAX(id) per (item_id, company_id) to get the latest ledger entry per company
    try:
        qty_rows = db.execute(text("""
            SELECT sl.item_id, COALESCE(SUM(sl2.balance_qty), 0) as total_qty
            FROM (
                SELECT item_id, company_id, MAX(id) as max_id
                FROM stock_ledger
                GROUP BY item_id, company_id
            ) sl
            JOIN stock_ledger sl2 ON sl2.id = sl.max_id
            GROUP BY sl.item_id
        """)).fetchall()
        qty_map = {row[0]: max(0, int(row[1])) for row in qty_rows}
    except Exception as _qe:
        logger.warning(f'[DC-STOCK-MKT-001] qty map build failed (will use 0): {_qe}')
        qty_map = {}

    # Pre-build image_url map: item_id → source_url of first folder_link
    try:
        img_rows = db.execute(text("""
            SELECT DISTINCT ON (stock_item_id) stock_item_id, source_url
            FROM stock_item_images
            WHERE source_type = 'folder_link' AND source_url IS NOT NULL
            ORDER BY stock_item_id, id ASC
        """)).fetchall()
        img_map = {row[0]: row[1] for row in img_rows}
    except Exception as _ie:
        logger.warning(f'[DC-STOCK-MKT-001] image map build failed (non-fatal): {_ie}')
        img_map = {}

    import re as _re
    def _has_real_name(name):
        """Return True only if the item name has meaningful alphanumeric content."""
        if not name:
            return False
        stripped = name.strip()
        if len(stripped) < 2:
            return False
        if not _re.search(r'[A-Za-z0-9]', stripped):
            return False
        return True

    all_items = db.query(StockItemMaster).filter(StockItemMaster.is_active == True).all()
    # Only sync items that have a real name (skip sheet placeholder rows)
    # DC-DEDUP-001: ZYSPSPA items are shadow/duplicate records — permanently excluded from sync
    items = [i for i in all_items if _has_real_name(i.item_name) and not (i.item_code or '').startswith('ZYSPSPA')]
    skipped_no_name = len(all_items) - len(items)
    if skipped_no_name:
        logger.info(f'[DC-STOCK-MKT-001] Skipped {skipped_no_name} items (no real name or ZYSPSPA excluded)')

    total = len(items)
    success_count = 0
    fail_count = 0
    fail_details = []

    for item in items:
        sp = db.begin_nested()
        try:
            # Ensure MNR (company_id=3) is always set as default company for spares
            if not item.applicable_companies:
                item.applicable_companies = [3]

            sku = item.item_code
            avail_qty = qty_map.get(item.id, 0)
            image_url = img_map.get(item.id)
            dealer_price = float(item.selling_rate or 0)
            gst_pct = float(item.default_gst_rate or 18.0)
            category = (item.item_category or 'PRODUCT').replace('_', ' ').title()

            existing = db.query(MarketspareItem).filter(
                MarketspareItem.sku == sku,
                MarketspareItem.company_id == company_id,
            ).first()

            if existing:
                # Never touch source='direct' records
                if getattr(existing, 'source', 'sheet') == 'direct':
                    success_count += 1
                    sp.commit()
                    continue

                protected = set(existing.override_fields or [])

                def _set(field, value):
                    if field not in protected:
                        setattr(existing, field, value)

                _set('name',          item.item_name)
                _set('category_name', category)
                _set('dealer_price',  dealer_price)
                _set('gst_percent',   gst_pct)
                _set('description',   item.description)
                _set('brand',         item.brand)
                _set('model_compat',  item.model_compat)
                _set('specifications', item.specification)
                _set('color',         ','.join(item.colors) if item.colors else None)
                if 'available_qty' not in protected:
                    existing.available_qty = avail_qty
                if image_url and 'image_url' not in protected:
                    existing.image_url = image_url
                existing.source        = 'stock'
                existing.stock_item_id = item.id
                existing.is_active     = True
                existing.segment_id    = existing.segment_id or 1
                existing.updated_at    = datetime.utcnow()
                # Stamp back the marketplace_sku on stock item so the badge lights up
                if not item.marketplace_sku:
                    item.marketplace_sku = sku
            else:
                new_item = MarketspareItem(
                    sku=sku,
                    name=item.item_name,
                    category_name=category,
                    dealer_price=dealer_price,
                    gst_percent=gst_pct,
                    available_qty=avail_qty,
                    description=item.description,
                    brand=item.brand,
                    model_compat=item.model_compat,
                    specifications=item.specification,
                    color=','.join(item.colors) if item.colors else None,
                    image_url=image_url,
                    image_data=[],
                    is_active=True,
                    segment_id=1,
                    source='stock',
                    stock_item_id=item.id,
                    company_id=company_id,
                )
                db.add(new_item)
                db.flush()
                # Stamp back the marketplace_sku on stock item so the badge lights up
                if not item.marketplace_sku:
                    item.marketplace_sku = sku

            sp.commit()
            success_count += 1
        except Exception as e:
            sp.rollback()
            fail_count += 1
            fail_details.append({'sku': getattr(item, 'item_code', '?'), 'error': str(e)})
            logger.error(f'[DC-STOCK-MKT-001] Failed sku={getattr(item, "item_code", "?")}: {e}')

    # Deactivate marketplace records for stock items that are now inactive
    # (source='stock' only — never touch 'sheet' or 'direct')
    # Guard: keep a record active if its stock_item_id points to an active stock item,
    # even if the marketplace SKU differs from the stock item code (happens for
    # sheet-only imports where a new item_code was generated).
    try:
        active_skus = {i.item_code for i in items}
        active_sim_ids = {i.id for i in items}
        stale = db.query(MarketspareItem).filter(
            MarketspareItem.company_id == company_id,
            MarketspareItem.source == 'stock',
            MarketspareItem.is_active == True,
        ).all()
        deactivated = 0
        for s in stale:
            if s.sku not in active_skus and s.stock_item_id not in active_sim_ids:
                s.is_active = False
                deactivated += 1
        if deactivated:
            db.flush()
    except Exception as _de:
        logger.warning(f'[DC-STOCK-MKT-001] Deactivation step failed (non-fatal): {_de}')

    # Update search vectors
    try:
        db.execute(text("""
            UPDATE marketplace_spares SET
              search_vector = to_tsvector('english',
                coalesce(name,'') || ' ' || coalesce(category_name,'') || ' ' ||
                coalesce(brand,'') || ' ' || coalesce(description,'') || ' ' || coalesce(sku,'')
              )
            WHERE company_id = :cid AND source = 'stock'
        """), {'cid': company_id})
    except Exception as _sv:
        logger.warning(f'[DC-STOCK-MKT-001] search_vector update failed (non-fatal): {_sv}')

    # Write sync log
    log_entry = MarketplaceSyncLog(
        total_records=total,
        successful_records=success_count,
        failed_records=fail_count,
        error_summary={
            'source': 'stock_items',
            'upsert_errors': fail_details,
            'triggered_by': triggered_by,
        },
        company_id=company_id,
    )
    db.add(log_entry)
    db.commit()

    result = {
        'total_records': total,
        'successful_records': success_count,
        'failed_records': fail_count,
        'triggered_by': triggered_by,
        'source': 'stock_items',
    }
    logger.info(f'[DC-STOCK-MKT-001] Complete: {result}')
    return result


def _import_sheet_products_to_stock(db: Session) -> None:
    """
    DC-STOCK-MKT-002 (one-time idempotent): Import marketplace products with no matching
    stock item into stock_item_master, then link them back (source='stock').
    Also auto-links the 289 existing matches (marketplace SKU = stock item code).
    Company ID 3 = MNR Mega Natural Resources (primary).
    Safe to call on every startup — checks before creating.
    """
    from app.models.staff_accounts import StockItemMaster
    from decimal import Decimal
    import re as _re

    MNR_COMPANY_ID = 3
    MKT_COMPANY_ID = 1  # marketplace company_id = 1

    logger.info('[DC-STOCK-MKT-002] Starting sheet→stock import & auto-link pass')

    # Step 1: Auto-link existing matches (marketplace SKU = stock item code)
    try:
        linked = db.execute(text("""
            UPDATE marketplace_spares ms
            SET source = 'stock',
                stock_item_id = sim.id,
                is_active = TRUE,
                updated_at = NOW()
            FROM stock_item_master sim
            WHERE ms.sku = sim.item_code
              AND sim.is_active = TRUE
              AND ms.source != 'direct'
              AND (ms.stock_item_id IS NULL OR ms.stock_item_id != sim.id OR ms.is_active = FALSE)
        """))
        linked_count = linked.rowcount
        db.commit()
        if linked_count:
            logger.info(f'[DC-STOCK-MKT-002] Auto-linked {linked_count} marketplace products to stock items')
    except Exception as _le:
        db.rollback()
        logger.warning(f'[DC-STOCK-MKT-002] Auto-link step failed (non-fatal): {_le}')
        linked_count = 0

    # Step 2: Import sheet-only products (no matching stock item) as new stock items.
    # Catches two states:
    #   (a) source='sheet' — never imported (first run or skipped inactive ones)
    #   (b) source='stock', is_active=FALSE — a previous import run used the wrong
    #       item_code (auto-generated instead of marketplace SKU), leaving the marketplace
    #       record deactivated. Pick them up and re-create correctly.
    try:
        sheet_only = db.execute(text("""
            SELECT ms.id, ms.sku, ms.name, ms.category_name, ms.dealer_price,
                   ms.description, ms.brand, ms.model_compat, ms.specifications,
                   ms.gst_percent, ms.color, COALESCE(ms.available_qty, 0) as available_qty
            FROM marketplace_spares ms
            WHERE (ms.source = 'sheet' OR (ms.source = 'stock' AND ms.is_active = FALSE))
              AND NOT EXISTS (
                  SELECT 1 FROM stock_item_master sim WHERE sim.item_code = ms.sku
              )
        """)).fetchall()
    except Exception as _fe:
        logger.warning(f'[DC-STOCK-MKT-002] Sheet-only query failed (non-fatal): {_fe}')
        return

    from app.models.staff_accounts import StockLedger as _StockLedger
    from datetime import date as _date

    imported = 0
    opening_created = 0
    for row in sheet_only:
        sp = db.begin_nested()
        try:
            ms_id, sku, name, cat_name, dealer_price, desc, brand, model_compat, specs, gst_pct, color, available_qty = row

            # Skip rows with no real item name (sheet placeholder rows)
            if not name or not _re.search(r'[A-Za-z0-9]', name.strip()) or len(name.strip()) < 2:
                sp.commit()
                continue

            # Map marketplace category_name back to stock item category enum
            cat_upper = (cat_name or 'PRODUCT').upper().replace(' ', '_')
            standard_cats = {'PRODUCT', 'RAW_MATERIAL', 'CONSUMABLE', 'SPARE_PART', 'ACCESSORY'}
            item_category = cat_upper if cat_upper in standard_cats else 'SPARE_PART'

            selling_rate = Decimal(str(dealer_price or 0))
            gst_rate = Decimal(str(gst_pct or 18))

            # Use the marketplace SKU as the stock item code directly —
            # these are already valid ZYSP* codes and are unique in stock_item_master
            # (guaranteed by the NOT EXISTS check above). This keeps the bidirectional
            # link clean: marketplace.sku == stock_item.item_code == marketplace.sku.
            new_code = sku

            # Check name uniqueness — append SKU suffix if needed
            existing_name = db.execute(text(
                "SELECT id FROM stock_item_master WHERE LOWER(item_name) = LOWER(:n) LIMIT 1"
            ), {'n': name}).fetchone()
            stock_name = name if not existing_name else f"{name} [{sku}]"

            new_stock_item = StockItemMaster(
                item_code=new_code,
                item_name=stock_name,
                item_category=item_category,
                applicable_companies=[MNR_COMPANY_ID],
                description=desc,
                brand=brand,
                model_compat=model_compat,
                specification=specs,
                colors=[color] if color else None,
                unit_of_measure='PCS',
                default_gst_rate=gst_rate,
                selling_rate=selling_rate,
                purchase_rate=Decimal('0.00'),
                reorder_level=0,
                is_active=True,
            )
            db.add(new_stock_item)
            db.flush()  # get new_stock_item.id

            # Link back the marketplace record and reactivate it
            mkt = db.query(MarketspareItem).filter(MarketspareItem.id == ms_id).first()
            if mkt:
                mkt.source = 'stock'
                mkt.stock_item_id = new_stock_item.id
                mkt.is_active = True
                mkt.updated_at = datetime.utcnow()

            # DC-STOCK-MKT-002a: Create OPENING stock_ledger entry from sheet qty
            # This makes the quantity from the Google Sheet visible on the Stock Items page.
            sheet_qty = int(available_qty) if available_qty and int(available_qty) > 0 else 0
            if sheet_qty > 0:
                opening_entry = _StockLedger(
                    item_id=new_stock_item.id,
                    company_id=MNR_COMPANY_ID,
                    entry_type='OPENING',
                    reference_type='OPENING',
                    reference_id=new_stock_item.id,
                    reference_number=sku,
                    transaction_date=_date.today(),
                    quantity_in=sheet_qty,
                    quantity_out=0,
                    balance_qty=sheet_qty,
                    unit_rate=selling_rate,
                    total_value=selling_rate * sheet_qty,
                    balance_value=selling_rate * sheet_qty,
                    narration=f'Opening balance from Google Sheet sync (SKU: {sku})',
                )
                db.add(opening_entry)
                opening_created += 1

            sp.commit()
            imported += 1
        except Exception as _ie:
            sp.rollback()
            logger.warning(f'[DC-STOCK-MKT-002] Failed to import sku={row[1]}: {_ie}')

    db.commit()
    logger.info(f'[DC-STOCK-MKT-002] Imported {imported} stock items, {opening_created} opening balance entries from sheet')


def run_sync(db: Session, company_id: int, triggered_by: str = 'manual', segment_id: int = None) -> Dict[str, Any]:
    """
    Full upsert sync: Google Sheet → marketplace_spares table.
    DC Protocol: all records scoped to company_id.
    Always updates available_qty (stock counts) from sheet col 23.
    Phase 3: segment_id — if provided, uses that segment's configured google_sheet_url and
             stamps all upserted rows with that segment_id + source='sheet'.
             If segment_id is None, uses default EV Spares (segment_id=1) and GVIZ_URL.
    Returns sync summary.
    """
    logger.info(f'[MARKETPLACE-SYNC] Starting sync for company_id={company_id}, segment_id={segment_id}, triggered_by={triggered_by}')

    # Resolve segment
    resolved_segment_id = segment_id or 1
    sheet_url = None
    if segment_id:
        seg = db.query(MarketplaceSegment).filter(
            MarketplaceSegment.id == segment_id,
            MarketplaceSegment.company_id == company_id,
        ).first()
        if seg is None:
            raise ValueError(f'Segment id={segment_id} not found for company_id={company_id}')
        # DC-STOCK-MKT-001: If segment is now stock-sourced, skip Sheet sync and run stock sync instead
        if getattr(seg, 'data_source', 'sheet') == 'stock':
            logger.info(f'[MARKETPLACE-SYNC] Segment {segment_id} data_source=stock — delegating to run_stock_sync')
            return run_stock_sync(db, company_id=company_id, triggered_by=triggered_by)
        if seg.google_sheet_url:
            sheet_url = seg.google_sheet_url

    valid_rows, error_rows = parse_sheet_rows(sheet_url)

    # Deduplicate by SKU — sheet may have duplicate rows; last occurrence wins.
    # This prevents UniqueViolation when two rows share a SKU and both try to INSERT.
    _seen: Dict[str, Any] = {}
    for _item in valid_rows:
        _seen[_item['sku']] = _item
    valid_rows = list(_seen.values())

    total = len(valid_rows)
    success_count = 0
    fail_count = 0
    fail_details = []

    for item in valid_rows:
        sp = db.begin_nested()
        try:
            # Unique constraint is now (sku, company_id) — look up by both.
            existing = db.query(MarketspareItem).filter(
                MarketspareItem.sku == item['sku'],
                MarketspareItem.company_id == company_id,
            ).first()

            if existing:
                # Fields that staff have manually edited are protected from sheet overwrites.
                # available_qty is ALWAYS synced from the sheet (stock count is authoritative).
                # source='direct' products are never overwritten by any sync.
                if getattr(existing, 'source', 'sheet') == 'direct':
                    # Direct-entry products: only update available_qty (sheet count may exist)
                    existing.available_qty = item.get('available_qty', 0)
                    success_count += 1
                    continue

                protected = set(existing.override_fields or [])

                def _set(field, value):
                    if field not in protected:
                        setattr(existing, field, value)

                _set('name',           item['name'])
                _set('category_name',  item['category_name'])
                _set('dealer_price',   item['dealer_price'])
                _set('gst_percent',    item.get('gst_percent'))
                _set('description',    item['description'])
                _set('brand',          item['brand'])
                _set('model_compat',   item.get('model_compat'))
                _set('specifications', item.get('specifications'))
                _set('color',          item.get('color'))
                _set('speciality',     item.get('speciality'))
                _set('company_name',   item.get('company_name'))
                _set('warranty_details', item.get('warranty_details'))
                _set('warranty_cost',    item.get('warranty_cost'))

                # DC Protocol Mar 2026: Smart image_url sync
                # Rule 1: If sheet cell is empty, never overwrite an existing Object Storage URL.
                # Rule 2: If sheet has an external http URL, download it, upload to Object Storage,
                #         and store the /api/v1/marketplace/images/ endpoint URL.
                _sync_image_url(existing, item.get('image_url'), item['sku'], 'image_url' in protected)

                _set('image_data',     item['image_data'])
                # Procurement cost fields — always synced from sheet (not user-editable)
                existing.proc_cost      = item.get('proc_cost')
                existing.proc_transport = item.get('proc_transport')
                existing.proc_ex_tax    = item.get('proc_ex_tax')
                existing.proc_tax_pct   = item.get('proc_tax_pct')
                existing.proc_with_tax  = item.get('proc_with_tax')
                # DC_STOCK_MKTLINK_001: If available_qty is in override_fields (locked by stock item bridge),
                # respect the override — do NOT overwrite from sheet.
                # Otherwise sheet remains authoritative for stock count.
                if 'available_qty' not in protected:
                    existing.available_qty = item.get('available_qty', 0)
                # Phase 3: stamp segment_id + source + is_active on every sheet-synced product
                existing.segment_id  = resolved_segment_id
                existing.source      = 'sheet'
                existing.is_active   = True   # DC Fix Mar 2026: re-activate if it was deactivated
                existing.updated_at  = datetime.utcnow()
            else:
                new_item = MarketspareItem(
                    sku=item['sku'],
                    name=item['name'],
                    category_name=item['category_name'],
                    dealer_price=item['dealer_price'],
                    gst_percent=item.get('gst_percent'),
                    available_qty=item.get('available_qty', 0),
                    description=item['description'],
                    brand=item['brand'],
                    model_compat=item.get('model_compat'),
                    specifications=item.get('specifications'),
                    color=item.get('color'),
                    speciality=item.get('speciality'),
                    company_name=item.get('company_name'),
                    image_url=item.get('image_url'),
                    image_data=item['image_data'],
                    proc_cost=item.get('proc_cost'),
                    proc_transport=item.get('proc_transport'),
                    proc_ex_tax=item.get('proc_ex_tax'),
                    proc_tax_pct=item.get('proc_tax_pct'),
                    proc_with_tax=item.get('proc_with_tax'),
                    warranty_details=item.get('warranty_details'),
                    warranty_cost=item.get('warranty_cost'),
                    is_active=True,
                    segment_id=resolved_segment_id,
                    source='sheet',
                    company_id=company_id,
                )
                db.add(new_item)
                # Flush immediately so any SKU constraint violation is caught per-row,
                # not as a bulk failure that rolls back the entire batch.
                db.flush()

            sp.commit()
            success_count += 1
        except Exception as e:
            sp.rollback()
            fail_count += 1
            fail_details.append({'sku': item.get('sku', '?'), 'error': str(e)})
            logger.error(f'[MARKETPLACE-SYNC] Failed row sku={item.get("sku")}: {e}')

    # Deactivate products no longer present in the sheet.
    # Only applies to source='sheet' products in this segment.
    # Products added via direct entry (source='direct') are never touched.
    synced_skus = {item['sku'] for item in valid_rows}
    deactivated_count = 0
    try:
        stale = db.query(MarketspareItem).filter(
            MarketspareItem.company_id == company_id,
            MarketspareItem.segment_id == resolved_segment_id,
            MarketspareItem.source == 'sheet',
            MarketspareItem.is_active == True,
        ).all()
        for item in stale:
            if item.sku not in synced_skus:
                item.is_active = False
                deactivated_count += 1
        if deactivated_count:
            db.flush()
            logger.info(f'[MARKETPLACE-SYNC] Deactivated {deactivated_count} products no longer in sheet for segment_id={resolved_segment_id}')
    except Exception as e:
        logger.warning(f'[MARKETPLACE-SYNC] Deactivation step failed: {e}')

    # Update search vectors for all items in this company
    try:
        db.execute(text("""
            UPDATE marketplace_spares SET
              search_vector = to_tsvector('english',
                coalesce(name, '') || ' ' ||
                coalesce(category_name, '') || ' ' ||
                coalesce(brand, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(sku, '')
              )
            WHERE company_id = :cid
        """), {'cid': company_id})
    except Exception as e:
        logger.warning(f'[MARKETPLACE-SYNC] search_vector update failed: {e}')

    # T007: Auto-raise procurement for zero-qty items
    # DC Fix: rollback any broken transaction state from per-row savepoint failures
    auto_proc_raised = 0
    try:
        try:
            db.rollback()
        except Exception:
            pass
        auto_proc_raised = _auto_raise_procurement(db, company_id)
        if auto_proc_raised:
            logger.info(f'[MARKETPLACE-SYNC] Auto-procurement raised for {auto_proc_raised} zero-qty items')
    except Exception as e:
        logger.warning(f'[MARKETPLACE-SYNC] Auto-procurement step failed: {e}')

    # Write sync log
    log_entry = MarketplaceSyncLog(
        total_records=total,
        successful_records=success_count,
        failed_records=fail_count,
        error_summary={
            'parse_errors': error_rows,
            'upsert_errors': fail_details,
            'auto_procurement_raised': auto_proc_raised,
            'deactivated': deactivated_count,
        },
        company_id=company_id,
    )
    db.add(log_entry)
    db.commit()

    result = {
        'total_records':          total,
        'successful_records':     success_count,
        'failed_records':         fail_count,
        'parse_errors':           len(error_rows),
        'triggered_by':           triggered_by,
        'company_id':             company_id,
        'auto_procurement_raised': auto_proc_raised,
        'upserted':               success_count,
    }
    logger.info(f'[MARKETPLACE-SYNC] Complete: {result}')
    return result
