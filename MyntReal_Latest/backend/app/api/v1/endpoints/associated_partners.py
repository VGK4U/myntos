"""
Associated Partners API — Hub public partner showcase
DC Protocol Compliant — additive only, zero negative impact.

Endpoints:
  Staff (VGK Mentor / EA):
    GET    /vgk/partners              — List all partners
    POST   /vgk/partners              — Create partner
    PATCH  /vgk/partners/{id}         — Update partner fields / toggle status
    DELETE /vgk/partners/{id}         — Soft delete
    POST   /vgk/partners/{id}/upload-logo — Upload / replace logo
    GET    /vgk/partners/{id}/gallery     — List gallery photos
    POST   /vgk/partners/{id}/gallery     — Upload gallery photo (max 5)
    DELETE /vgk/partners/{id}/gallery/{photo_id} — Delete gallery photo

  Public (no auth):
    GET    /hub/partners              — List active partners (for homepage marquee)
    GET    /hub/partners/{id}         — Single partner detail page data
    GET    /hub/partners/{id}/gallery — Partner gallery photos

Created: April 2026
"""

import os, hashlib, mimetypes
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.vgk_team import require_vgk_admin
from app.models.base import get_indian_time

router = APIRouter(tags=["Associated Partners"])


# ─── Upload helper (mirrors vgk_media._upload_media_file) ────────────────────
_COMPRESSIBLE = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}

def _compress_to_webp(content: bytes, ct: str):
    if ct not in _COMPRESSIBLE:
        return content, ct
    try:
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(content))
        img = img.convert('RGBA') if img.mode in ('RGBA', 'LA', 'PA') else img.convert('RGB') if img.mode != 'RGB' else img
        img.thumbnail((1200, 1200), Image.LANCZOS)
        out = _io.BytesIO()
        if img.mode == 'RGBA':
            img.save(out, format='WEBP', quality=85, method=4, lossless=False)
        else:
            img.save(out, format='WEBP', quality=85, method=4)
        return out.getvalue(), 'image/webp'
    except Exception:
        return content, ct

async def _upload_logo(file: UploadFile) -> str:
    from app.services.object_storage import storage_service
    content = await file.read()
    ct = (file.content_type or 'application/octet-stream').split(';')[0].strip().lower()
    content, ct = _compress_to_webp(content, ct)
    ext = '.webp' if ct == 'image/webp' else (mimetypes.guess_extension(ct) or os.path.splitext(file.filename or 'file')[1] or '.bin')
    ts  = datetime.now().strftime('%Y%m%d%H%M%S')
    h   = hashlib.md5(content).hexdigest()[:8]
    key = f'partner_logos/{ts}_{h}{ext}'
    ok  = storage_service.upload_file(key, content)
    if not ok:
        raise HTTPException(status_code=500, detail='Logo upload failed')
    return storage_service.get_file_url(key)


# ─── DB helpers ──────────────────────────────────────────────────────────────
def _row_to_dict(row) -> dict:
    return {
        'id':               row.id,
        'company_name':     row.company_name,
        'logo_url':         row.logo_url,
        'address':          row.address,
        'established_year': row.established_year,
        'notes':            row.notes,
        'status':           row.status,
        'display_order':    row.display_order,
        'created_at':       row.created_at.isoformat() if row.created_at else None,
        'updated_at':       row.updated_at.isoformat() if row.updated_at else None,
    }

def _get_partner(pid: int, db: Session):
    row = db.execute(
        text("SELECT * FROM associated_partners_hub WHERE id = :id AND status != 'deleted'"),
        {'id': pid}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Partner not found')
    return row


# ─── Staff endpoints ──────────────────────────────────────────────────────────
@router.get('/vgk/partners')
async def list_partners(db: Session = Depends(get_db), _=Depends(require_vgk_admin)):
    rows = db.execute(text(
        "SELECT * FROM associated_partners_hub WHERE status != 'deleted' ORDER BY display_order ASC, id ASC"
    )).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.post('/vgk/partners')
async def create_partner(
    company_name:     str           = Body(...),
    address:          Optional[str] = Body(None),
    established_year: Optional[str] = Body(None),
    notes:            Optional[str] = Body(None),
    display_order:    int           = Body(0),
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    result = db.execute(text("""
        INSERT INTO associated_partners_hub
               (company_name, address, established_year, notes, status, display_order, created_at, updated_at)
        VALUES (:cn, :addr, :yr, :notes, 'active', :ord, NOW(), NOW())
        RETURNING *
    """), {
        'cn': company_name.strip(),
        'addr': (address or '').strip() or None,
        'yr': (established_year or '').strip() or None,
        'notes': (notes or '').strip() or None,
        'ord': display_order,
    })
    db.commit()
    row = result.fetchone()
    return _row_to_dict(row)


@router.patch('/vgk/partners/{partner_id}')
async def update_partner(
    partner_id: int,
    company_name:     Optional[str] = Body(None),
    address:          Optional[str] = Body(None),
    established_year: Optional[str] = Body(None),
    notes:            Optional[str] = Body(None),
    status:           Optional[str] = Body(None),
    display_order:    Optional[int] = Body(None),
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    _get_partner(partner_id, db)
    updates = {}
    if company_name     is not None: updates['company_name']     = company_name.strip()
    if address          is not None: updates['address']          = address.strip() or None
    if established_year is not None: updates['established_year'] = established_year.strip() or None
    if notes            is not None: updates['notes']            = notes.strip() or None
    if status           is not None:
        if status not in ('active', 'paused', 'deleted'):
            raise HTTPException(status_code=400, detail='Invalid status')
        updates['status'] = status
    if display_order    is not None: updates['display_order']    = display_order
    if not updates:
        raise HTTPException(status_code=400, detail='No fields to update')
    set_clause = ', '.join(f"{k} = :{k}" for k in updates)
    updates['updated_at'] = datetime.now()
    updates['pid'] = partner_id
    db.execute(text(f"UPDATE associated_partners_hub SET {set_clause}, updated_at = :updated_at WHERE id = :pid"), updates)
    db.commit()
    return _row_to_dict(_get_partner(partner_id, db))


@router.delete('/vgk/partners/{partner_id}')
async def delete_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    _get_partner(partner_id, db)
    db.execute(text("UPDATE associated_partners_hub SET status='deleted', updated_at=NOW() WHERE id=:id"), {'id': partner_id})
    db.commit()
    return {'success': True}


@router.post('/vgk/partners/{partner_id}/upload-logo')
async def upload_partner_logo(
    partner_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    _get_partner(partner_id, db)
    logo_url = await _upload_logo(file)
    db.execute(text("UPDATE associated_partners_hub SET logo_url=:url, updated_at=NOW() WHERE id=:id"),
               {'url': logo_url, 'id': partner_id})
    db.commit()
    return {'success': True, 'logo_url': logo_url}


# ─── Public endpoints ─────────────────────────────────────────────────────────
@router.get('/hub/partners')
async def public_list_partners(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT * FROM associated_partners_hub WHERE status='active' ORDER BY display_order ASC, id ASC"
    )).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get('/hub/partners/{partner_id}')
async def public_get_partner(partner_id: int, db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT * FROM associated_partners_hub WHERE id=:id AND status='active'"
    ), {'id': partner_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Partner not found')
    return _row_to_dict(row)


# ─── Gallery helpers ──────────────────────────────────────────────────────────
def _gallery_row(row) -> dict:
    return {
        'id':            row.id,
        'partner_id':    row.partner_id,
        'photo_url':     row.photo_url,
        'caption':       row.caption,
        'display_order': row.display_order,
        'created_at':    row.created_at.isoformat() if row.created_at else None,
    }

async def _upload_gallery_photo(file: UploadFile) -> str:
    from app.services.object_storage import storage_service
    content = await file.read()
    ct = (file.content_type or 'application/octet-stream').split(';')[0].strip().lower()
    content, ct = _compress_to_webp(content, ct)
    ext = '.webp' if ct == 'image/webp' else (mimetypes.guess_extension(ct) or os.path.splitext(file.filename or 'file')[1] or '.bin')
    ts  = datetime.now().strftime('%Y%m%d%H%M%S')
    h   = hashlib.md5(content).hexdigest()[:8]
    key = f'partner_gallery/{ts}_{h}{ext}'
    ok  = storage_service.upload_file(key, content)
    if not ok:
        raise HTTPException(status_code=500, detail='Photo upload failed')
    return storage_service.get_file_url(key)


# ─── Gallery — Staff endpoints ────────────────────────────────────────────────
@router.get('/vgk/partners/{partner_id}/gallery')
async def list_gallery(partner_id: int, db: Session = Depends(get_db), _=Depends(require_vgk_admin)):
    _get_partner(partner_id, db)
    rows = db.execute(text(
        "SELECT * FROM partner_gallery WHERE partner_id=:pid ORDER BY display_order ASC, id ASC"
    ), {'pid': partner_id}).fetchall()
    return [_gallery_row(r) for r in rows]


@router.post('/vgk/partners/{partner_id}/gallery')
async def upload_gallery_photo(
    partner_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    _get_partner(partner_id, db)
    count = db.execute(text(
        "SELECT COUNT(*) FROM partner_gallery WHERE partner_id=:pid"
    ), {'pid': partner_id}).scalar()
    if count >= 5:
        raise HTTPException(status_code=400, detail='Maximum 5 photos per partner')
    photo_url = await _upload_gallery_photo(file)
    result = db.execute(text("""
        INSERT INTO partner_gallery (partner_id, photo_url, caption, display_order, created_at)
        VALUES (:pid, :url, :cap, :ord, NOW()) RETURNING *
    """), {'pid': partner_id, 'url': photo_url, 'cap': (caption or '').strip() or None, 'ord': int(count)})
    db.commit()
    return _gallery_row(result.fetchone())


@router.delete('/vgk/partners/{partner_id}/gallery/{photo_id}')
async def delete_gallery_photo(
    partner_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin)
):
    _get_partner(partner_id, db)
    row = db.execute(text(
        "SELECT id FROM partner_gallery WHERE id=:id AND partner_id=:pid"
    ), {'id': photo_id, 'pid': partner_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Photo not found')
    db.execute(text("DELETE FROM partner_gallery WHERE id=:id"), {'id': photo_id})
    db.commit()
    return {'success': True}


# ─── Gallery — Public endpoint ────────────────────────────────────────────────
@router.get('/hub/partners/{partner_id}/gallery')
async def public_gallery(partner_id: int, db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT id FROM associated_partners_hub WHERE id=:id AND status='active'"
    ), {'id': partner_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Partner not found')
    rows = db.execute(text(
        "SELECT * FROM partner_gallery WHERE partner_id=:pid ORDER BY display_order ASC, id ASC"
    ), {'pid': partner_id}).fetchall()
    return [_gallery_row(r) for r in rows]
