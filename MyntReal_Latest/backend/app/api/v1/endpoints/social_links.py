"""
Social Media Links API — per-entity social platform management
DC Protocol Compliant [DC-SOCIAL-001 Apr 2026] — additive only, zero negative impact.

Endpoints:
  Staff (VGK Mentor / EA):
    GET    /vgk/social-links                       — List all entries (grouped)
    PUT    /vgk/social-links/{entity}/{platform}   — Upsert URL
    PATCH  /vgk/social-links/{entity}/{platform}/toggle — Toggle active/paused
    DELETE /vgk/social-links/{entity}/{platform}   — Remove a link

  Public (no auth):
    GET    /social-links/{entity_key}              — Active links for that entity only

Created: April 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.vgk_team import require_vgk_admin

router = APIRouter(tags=["Social Links"])

VALID_PLATFORMS = {'facebook', 'instagram', 'youtube', 'linkedin', 'google'}
VALID_ENTITIES  = {'hub', 'manthra', 'hgs', 'care', 'realestate', 'etc'}

ENTITY_LABELS = {
    'hub':        'MyntReal / Hub',
    'manthra':    'Manthra EV',
    'hgs':        'Har Ghar Solar',
    'care':       'VGK Care',
    'realestate': 'VGK Real Dreams',
    'etc':        'EVolution Training Centre',
}

PLATFORM_ORDER = ['facebook', 'instagram', 'youtube', 'linkedin', 'google']


def _row_to_dict(row) -> dict:
    return {
        'id':         row.id,
        'entity_key': row.entity_key,
        'platform':   row.platform,
        'url':        row.url,
        'status':     row.status,
        'updated_at': str(row.updated_at),
    }


# ── Staff: list all (returns grouped by entity) ───────────────────────────────
@router.get('/vgk/social-links')
async def list_all_links(db: Session = Depends(get_db), _=Depends(require_vgk_admin)):
    rows = db.execute(text(
        "SELECT * FROM social_media_links ORDER BY entity_key, platform"
    )).fetchall()
    # Group by entity_key for frontend convenience
    grouped: dict = {ek: {'entity_key': ek, 'label': ENTITY_LABELS.get(ek, ek), 'links': {}} for ek in VALID_ENTITIES}
    for r in rows:
        if r.entity_key in grouped:
            grouped[r.entity_key]['links'][r.platform] = _row_to_dict(r)
    return list(grouped.values())


# ── Staff: upsert (PUT) ───────────────────────────────────────────────────────
@router.put('/vgk/social-links/{entity_key}/{platform}')
async def upsert_link(
    entity_key: str,
    platform: str,
    url: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin),
):
    if platform not in VALID_PLATFORMS:
        raise HTTPException(400, f'Invalid platform. Valid: {", ".join(sorted(VALID_PLATFORMS))}')
    if entity_key not in VALID_ENTITIES:
        raise HTTPException(400, f'Invalid entity. Valid: {", ".join(sorted(VALID_ENTITIES))}')
    url = url.strip()
    db.execute(text("""
        INSERT INTO social_media_links (entity_key, platform, url, status, updated_at)
        VALUES (:e, :p, :u, 'active', NOW())
        ON CONFLICT (entity_key, platform)
        DO UPDATE SET url = :u, status = 'active', updated_at = NOW()
    """), {'e': entity_key, 'p': platform, 'u': url})
    db.commit()
    row = db.execute(text(
        "SELECT * FROM social_media_links WHERE entity_key=:e AND platform=:p"
    ), {'e': entity_key, 'p': platform}).fetchone()
    return _row_to_dict(row)


# ── Staff: toggle active / paused ─────────────────────────────────────────────
@router.patch('/vgk/social-links/{entity_key}/{platform}/toggle')
async def toggle_link(
    entity_key: str,
    platform: str,
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin),
):
    row = db.execute(text(
        "SELECT * FROM social_media_links WHERE entity_key=:e AND platform=:p"
    ), {'e': entity_key, 'p': platform}).fetchone()
    if not row:
        raise HTTPException(404, 'Link not found')
    new_status = 'paused' if row.status == 'active' else 'active'
    db.execute(text(
        "UPDATE social_media_links SET status=:s, updated_at=NOW() WHERE entity_key=:e AND platform=:p"
    ), {'s': new_status, 'e': entity_key, 'p': platform})
    db.commit()
    row = db.execute(text(
        "SELECT * FROM social_media_links WHERE entity_key=:e AND platform=:p"
    ), {'e': entity_key, 'p': platform}).fetchone()
    return _row_to_dict(row)


# ── Staff: delete ─────────────────────────────────────────────────────────────
@router.delete('/vgk/social-links/{entity_key}/{platform}')
async def delete_link(
    entity_key: str,
    platform: str,
    db: Session = Depends(get_db),
    _=Depends(require_vgk_admin),
):
    db.execute(text(
        "DELETE FROM social_media_links WHERE entity_key=:e AND platform=:p"
    ), {'e': entity_key, 'p': platform})
    db.commit()
    return {'success': True}


# ── Public: active links for one entity ──────────────────────────────────────
@router.get('/social-links/{entity_key}')
async def public_get_links(entity_key: str, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM social_media_links
        WHERE entity_key = :e
          AND status = 'active'
          AND url IS NOT NULL
          AND url <> ''
        ORDER BY platform
    """), {'e': entity_key}).fetchall()
    return [_row_to_dict(r) for r in rows]
