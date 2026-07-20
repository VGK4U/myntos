"""
VGK Media API — Staff management + Public hub viewer + VGK Member portal
DC Protocol Compliant — additive only, zero negative impact.

Endpoints:
  Staff (VGK Mentor / EA):
    POST   /vgk/media                         — Create media item
    GET    /vgk/media                         — List all (with stats)
    GET    /vgk/media/{id}                    — Get single item
    PATCH  /vgk/media/{id}                    — Update / pause / deactivate
    DELETE /vgk/media/{id}                    — Soft delete
    POST   /vgk/media/{id}/upload-pdf         — Upload PDF for publication
    POST   /vgk/media/upload-thumbnail        — Upload thumbnail image (returns URL)
    POST   /vgk/media/ai-enhance              — AI-assist blog text

  VGK Member (partner JWT):
    GET    /vgk/media/member/items            — List active member-portal items (filter by category)
    POST   /vgk/media/member/{id}/react       — Toggle reaction (like/love/shoutout)
    POST   /vgk/media/member/{id}/click       — Record a view/click
    POST   /vgk/media/member/{id}/share       — Record a share (increments share_count)

  Public (no auth):
    GET    /hub/media/items                   — List active items by type
    POST   /hub/media/{id}/click              — Record a click
    POST   /hub/media/{id}/react              — Toggle a reaction (like/love/shoutout)
    GET    /hub/media/{id}/reactions          — Get reaction counts for an item

[DC-VGK-MEDIA-002] Added: vgk_category (promotional|training), image media type, member endpoints.
Created: April 2026
"""

import os, hashlib, json, mimetypes
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.core.database import get_db
from app.api.v1.endpoints.vgk_team import require_vgk_admin
from app.models.staff_accounts import VGKMediaItem, VGKMediaReaction, OfficialPartner
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time

router = APIRouter(tags=["VGK Media"])

# ─── Private: Object Storage upload helper ────────────────────────────────────
_COMPRESSIBLE_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}

def _compress_image_to_webp(content: bytes, content_type: str) -> tuple:
    """Compress a raster image to WebP (max 1920 px, quality 85).
    Skips GIFs and non-image types — returns (original_bytes, original_mime) unchanged.
    Returns (compressed_bytes, 'image/webp') on success.
    """
    if content_type not in _COMPRESSIBLE_IMAGE_TYPES:
        return content, content_type
    try:
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(content))
        if img.mode in ('RGBA', 'LA', 'PA'):
            img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((1920, 1920), Image.LANCZOS)
        out = _io.BytesIO()
        if img.mode == 'RGBA':
            img.save(out, format='WEBP', quality=85, method=4, lossless=False)
        else:
            img.save(out, format='WEBP', quality=85, method=4)
        return out.getvalue(), 'image/webp'
    except Exception:
        return content, content_type


async def _upload_media_file(file: UploadFile, prefix: str) -> str:
    """Upload any media file to Replit Object Storage.
    Images (JPEG/PNG/WebP) are auto-compressed to WebP ≤1920 px @ quality 85.
    Returns /storage/{key} URL served by the backend storage endpoint.
    """
    from app.services.object_storage import storage_service
    content = await file.read()
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    content, ct = _compress_image_to_webp(content, ct)
    ext = ".webp" if ct == "image/webp" else (
        mimetypes.guess_extension(ct) or
        os.path.splitext(file.filename or "file")[1] or ".bin"
    )
    ts  = datetime.now().strftime("%Y%m%d%H%M%S")
    h   = hashlib.md5(content).hexdigest()[:8]
    key = f"{prefix}/{ts}_{h}{ext}"
    ok  = storage_service.upload_file(key, content)
    if not ok:
        raise HTTPException(status_code=500, detail="File upload to storage failed")
    return storage_service.get_file_url(key)   # → /storage/{key}

OPENAI_KEY     = os.environ.get("OPENAI_API_KEY", "")
VALID_TYPES    = {'youtube', 'publication', 'blog', 'image'}
VALID_STATUS   = {'active', 'paused', 'inactive'}
VALID_REACTION = {'like', 'love', 'shoutout'}
VALID_CATEGORIES = {'promotional', 'training'}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_current_vgk_member(request: Request, db: Session = Depends(get_db)) -> OfficialPartner:
    """Inline member auth — reads partner JWT from Authorization or cookie."""
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    return get_current_vgk_member(request, db)


def _reactor_key(request: Request) -> str:
    """Derive a stable anonymous key from IP + User-Agent."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    ua = request.headers.get("user-agent", "")
    raw = f"{ip}|{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _reaction_counts(db: Session, media_id: int) -> dict:
    rows = (
        db.query(VGKMediaReaction.reaction_type, func.count(VGKMediaReaction.id))
        .filter(VGKMediaReaction.media_id == media_id)
        .group_by(VGKMediaReaction.reaction_type)
        .all()
    )
    return {r: c for r, c in rows}


def _member_reactions(db: Session, media_id: int, reactor_key: str) -> list:
    """Return list of reaction types the given reactor has already submitted."""
    rows = db.query(VGKMediaReaction.reaction_type).filter(
        VGKMediaReaction.media_id == media_id,
        VGKMediaReaction.reactor_key == reactor_key,
    ).all()
    return [r[0] for r in rows]


# ─────────────────────────────────────────────────────────────
# VGK MEMBER ENDPOINTS (partner JWT required)
# ─────────────────────────────────────────────────────────────

@router.get("/vgk/media/member/items")
def list_member_media(
    category: Optional[str] = Query(None, description="promotional | training"),
    media_type: Optional[str] = Query(None, description="youtube | publication | blog | image"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    List active VGK Member portal media items, optionally filtered by category and/or media_type.
    Requires VGK member JWT. Reactor key derived from partner_code for per-member reaction tracking.
    """
    current_member = _get_current_vgk_member(request, db)
    reactor_key = current_member.partner_code or _reactor_key(request)

    q = db.query(VGKMediaItem).filter(
        VGKMediaItem.status == 'active',
        VGKMediaItem.deleted_at == None,
        VGKMediaItem.vgk_category != None,
    )
    if category and category in VALID_CATEGORIES:
        q = q.filter(VGKMediaItem.vgk_category == category)
    if media_type and media_type in VALID_TYPES:
        q = q.filter(VGKMediaItem.media_type == media_type)
    items = q.order_by(VGKMediaItem.display_order.asc(), VGKMediaItem.published_at.desc()).all()

    out = []
    for item in items:
        d = item.to_dict()
        d['reactions'] = _reaction_counts(db, item.id)
        d['my_reactions'] = _member_reactions(db, item.id, reactor_key)
        out.append(d)

    return {"ok": True, "total": len(out), "items": out}


@router.post("/vgk/media/member/{media_id}/react")
async def member_toggle_reaction(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Toggle a reaction on a media item for a logged-in VGK member."""
    current_member = _get_current_vgk_member(request, db)
    reactor_key = current_member.partner_code or _reactor_key(request)

    try:
        body = await request.json()
    except Exception:
        body = {}
    reaction_type = (body.get('reaction_type') or '').strip().lower()
    if reaction_type not in VALID_REACTION:
        raise HTTPException(status_code=400, detail="reaction_type must be like, love, or shoutout")

    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.deleted_at == None,
        VGKMediaItem.status == 'active',
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")

    existing = db.query(VGKMediaReaction).filter(
        VGKMediaReaction.media_id == media_id,
        VGKMediaReaction.reaction_type == reaction_type,
        VGKMediaReaction.reactor_key == reactor_key,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        counts = _reaction_counts(db, media_id)
        return {"action": "removed", "reaction_type": reaction_type, "counts": counts,
                "my_reactions": _member_reactions(db, media_id, reactor_key)}
    else:
        rxn = VGKMediaReaction(
            media_id=media_id,
            reaction_type=reaction_type,
            reactor_type='partner',
            reactor_key=reactor_key,
        )
        db.add(rxn)
        db.commit()
        counts = _reaction_counts(db, media_id)
        return {"action": "added", "reaction_type": reaction_type, "counts": counts,
                "my_reactions": _member_reactions(db, media_id, reactor_key)}


@router.post("/vgk/media/member/{media_id}/click")
def member_record_click(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a view/click for a VGK member portal media item."""
    _get_current_vgk_member(request, db)
    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.status == 'active',
        VGKMediaItem.deleted_at == None,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    db.execute(text("UPDATE vgk_media_items SET click_count = click_count + 1 WHERE id = :id"), {"id": media_id})
    db.commit()
    return {"ok": True}


@router.post("/vgk/media/member/{media_id}/share")
def member_record_share(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a WhatsApp share for a VGK member portal media item."""
    _get_current_vgk_member(request, db)
    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.deleted_at == None,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    db.execute(text("UPDATE vgk_media_items SET share_count = share_count + 1 WHERE id = :id"), {"id": media_id})
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/hub/media/items")
def list_public_media(
    media_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List active media items for the public hub. Optionally filter by type."""
    q = db.query(VGKMediaItem).filter(
        VGKMediaItem.status == 'active',
        VGKMediaItem.deleted_at == None,
    )
    if media_type and media_type in VALID_TYPES:
        q = q.filter(VGKMediaItem.media_type == media_type)
    total = q.count()
    items = q.order_by(VGKMediaItem.display_order.asc(), VGKMediaItem.published_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    out = []
    for item in items:
        d = item.to_dict()
        d['reactions'] = _reaction_counts(db, item.id)
        out.append(d)

    return {"total": total, "page": page, "per_page": per_page, "items": out}


@router.get("/hub/media/{media_id}")
def get_public_media_item(media_id: int, db: Session = Depends(get_db)):
    """Fetch a single active media item by ID for public hub blog/publication permalink pages."""
    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.status == 'active',
        VGKMediaItem.deleted_at == None,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    d = item.to_dict()
    d['reactions'] = _reaction_counts(db, item.id)
    return d


@router.post("/hub/media/{media_id}/click")
def record_click(media_id: int, db: Session = Depends(get_db)):
    """Increment click count for a media item."""
    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.status == 'active',
        VGKMediaItem.deleted_at == None,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    db.execute(
        text("UPDATE vgk_media_items SET click_count = click_count + 1 WHERE id = :id"),
        {"id": media_id}
    )
    db.commit()
    return {"ok": True}


@router.post("/hub/media/{media_id}/react")
async def toggle_reaction(
    media_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Toggle a reaction on a media item. Body: {reaction_type: like|love|shoutout, reactor_key: <uuid>}"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    reaction_type = (body.get('reaction_type') or '').strip().lower()
    reactor_key = (body.get('reactor_key') or '').strip()[:256] or _reactor_key(request)

    if reaction_type not in VALID_REACTION:
        raise HTTPException(status_code=400, detail="reaction_type must be like, love, or shoutout")

    item = db.query(VGKMediaItem).filter(
        VGKMediaItem.id == media_id,
        VGKMediaItem.deleted_at == None,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")

    existing = db.query(VGKMediaReaction).filter(
        VGKMediaReaction.media_id == media_id,
        VGKMediaReaction.reaction_type == reaction_type,
        VGKMediaReaction.reactor_key == reactor_key,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        counts = _reaction_counts(db, media_id)
        return {"action": "removed", "reaction_type": reaction_type, "counts": counts}
    else:
        rxn = VGKMediaReaction(
            media_id=media_id,
            reaction_type=reaction_type,
            reactor_type='visitor',
            reactor_key=reactor_key,
        )
        db.add(rxn)
        db.commit()
        counts = _reaction_counts(db, media_id)
        return {"action": "added", "reaction_type": reaction_type, "counts": counts}


@router.get("/hub/media/{media_id}/reactions")
def get_reactions(media_id: int, db: Session = Depends(get_db)):
    """Get reaction counts for a specific media item."""
    item = db.query(VGKMediaItem).filter(VGKMediaItem.id == media_id, VGKMediaItem.deleted_at == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    return {"media_id": media_id, "counts": _reaction_counts(db, media_id)}


# ─────────────────────────────────────────────────────────────
# STAFF ENDPOINTS — VGK Admin / EA only
# ─────────────────────────────────────────────────────────────

@router.get("/vgk/media")
def list_media_staff(
    media_type: Optional[str] = Query(None),
    vgk_category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    """Staff: list all media items with counts. Filter by vgk_category for member-portal items."""
    q = db.query(VGKMediaItem).filter(VGKMediaItem.deleted_at == None)
    if media_type and media_type in VALID_TYPES:
        q = q.filter(VGKMediaItem.media_type == media_type)
    if vgk_category is not None:
        if vgk_category == '':
            q = q.filter(VGKMediaItem.vgk_category == None)
        elif vgk_category in VALID_CATEGORIES:
            q = q.filter(VGKMediaItem.vgk_category == vgk_category)
        elif vgk_category == 'any':
            q = q.filter(VGKMediaItem.vgk_category != None)
    if status and status in VALID_STATUS:
        q = q.filter(VGKMediaItem.status == status)
    total = q.count()
    items = q.order_by(VGKMediaItem.display_order.asc(), VGKMediaItem.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    out = []
    for item in items:
        d = item.to_dict()
        d['reactions'] = _reaction_counts(db, item.id)
        creator = db.query(StaffEmployee).filter(StaffEmployee.id == item.created_by_id).first() if item.created_by_id else None
        d['created_by_name'] = creator.full_name if creator else None
        out.append(d)

    return {"total": total, "page": page, "per_page": per_page, "items": out}


@router.get("/vgk/media/{media_id}")
def get_media_staff(
    media_id: int,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    item = db.query(VGKMediaItem).filter(VGKMediaItem.id == media_id, VGKMediaItem.deleted_at == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    d = item.to_dict()
    d['reactions'] = _reaction_counts(db, media_id)
    return d


@router.post("/vgk/media")
async def create_media(
    request: Request,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    """Create a new media item."""
    body = await request.json()
    media_type = (body.get('media_type') or '').strip().lower()
    if media_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"media_type must be one of {', '.join(sorted(VALID_TYPES))}")
    title = (body.get('title') or '').strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    vgk_cat = (body.get('vgk_category') or '').strip().lower() or None
    if vgk_cat and vgk_cat not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"vgk_category must be promotional or training")

    item = VGKMediaItem(
        company_id=body.get('company_id', 4),
        media_type=media_type,
        vgk_category=vgk_cat,
        title=title,
        description=body.get('description'),
        body=body.get('body'),
        url=body.get('url'),
        thumbnail_url=body.get('thumbnail_url'),
        links=body.get('links'),
        status=body.get('status', 'active'),
        display_order=body.get('display_order', 0),
        created_by_id=current_user.id,
        published_at=get_indian_time(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.patch("/vgk/media/{media_id}")
async def update_media(
    media_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    """Update a media item (title, body, status, vgk_category, links, etc.)."""
    item = db.query(VGKMediaItem).filter(VGKMediaItem.id == media_id, VGKMediaItem.deleted_at == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")

    body = await request.json()
    updatable = ['title', 'description', 'body', 'url', 'thumbnail_url', 'links', 'status', 'display_order', 'vgk_category']
    for field in updatable:
        if field in body:
            if field == 'status' and body[field] not in VALID_STATUS:
                raise HTTPException(status_code=400, detail=f"status must be one of {VALID_STATUS}")
            if field == 'vgk_category':
                val = (body[field] or '').strip().lower() or None
                if val and val not in VALID_CATEGORIES:
                    raise HTTPException(status_code=400, detail="vgk_category must be promotional or training")
                setattr(item, field, val)
            else:
                setattr(item, field, body[field])
    item.updated_at = get_indian_time()
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.delete("/vgk/media/{media_id}")
def delete_media(
    media_id: int,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete a media item."""
    item = db.query(VGKMediaItem).filter(VGKMediaItem.id == media_id, VGKMediaItem.deleted_at == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    item.deleted_at = get_indian_time()
    item.status = 'inactive'
    db.commit()
    return {"ok": True, "message": "Media item deleted"}


@router.post("/vgk/media/{media_id}/upload-pdf")
async def upload_pdf(
    media_id: int,
    file: UploadFile = File(...),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    """Upload a PDF for a publication item using the universal upload service."""
    item = db.query(VGKMediaItem).filter(VGKMediaItem.id == media_id, VGKMediaItem.deleted_at == None).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media item not found")
    if item.media_type != 'publication':
        raise HTTPException(status_code=400, detail="PDF upload only allowed for publication items")

    allowed_pdf = {'application/pdf'}
    if file.content_type not in allowed_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed here")
    try:
        pdf_url = await _upload_media_file(file, "vgk_media_pdfs")
        item.pdf_path = pdf_url
        item.pdf_name = file.filename or "publication.pdf"
        item.updated_at = get_indian_time()
        db.commit()
        return {"ok": True, "pdf_path": item.pdf_path, "pdf_name": item.pdf_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/vgk/media/upload-thumbnail")
async def upload_thumbnail(
    file: UploadFile = File(...),
    current_user: StaffEmployee = Depends(require_vgk_admin),
):
    """Upload a thumbnail image. Returns the public URL. Used before or after saving a media item."""
    allowed = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WebP or GIF images are allowed")
    try:
        url = await _upload_media_file(file, "vgk_media_thumbnails")
        return {"ok": True, "url": url, "file_name": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/vgk/media/ai-enhance")
async def ai_enhance_blog(
    request: Request,
    current_user: StaffEmployee = Depends(require_vgk_admin),
):
    """AI-enhance blog body text using GPT-4o-mini. Body: {text: str, instruction: str}"""
    if not OPENAI_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    body = await request.json()
    text_input = (body.get('text') or '').strip()
    instruction = (body.get('instruction') or 'Improve the writing quality, fix grammar, and make it engaging and professional.').strip()
    if not text_input:
        raise HTTPException(status_code=400, detail="text is required")

    # Strip HTML tags for AI processing so the model sees clean prose
    import re as _re
    plain_text = _re.sub(r'<[^>]+>', '', text_input).strip()
    if not plain_text:
        raise HTTPException(status_code=400, detail="text is required")

    import httpx
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are an expert content editor. {instruction} "
                    "Return only the improved text. Use HTML formatting: wrap paragraphs in <p> tags, "
                    "use <strong> for bold key phrases, <h2> or <h3> for section headings, "
                    "<ul>/<li> for bullet lists. No extra commentary, no code fences."
                )
            },
            {"role": "user", "content": plain_text},
        ],
        "max_tokens": 1500,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="AI service error")

    data = resp.json()
    enhanced = data['choices'][0]['message']['content'].strip()
    return {"enhanced": enhanced}


# ─────────────────────────────────────────────────────────────
# DC-VGK-VIDEO-OVERLAY-001: Video footer overlay via ffmpeg
# ─────────────────────────────────────────────────────────────

_BOLD_FONT   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_PLAIN_FONT  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_LOGO_PATH   = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../frontend/assets/logos/myntreal_logo_transparent.png")
)


def _dt_esc(text: str) -> str:
    """Escape text for ffmpeg drawtext filter value."""
    return (
        text.replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
            .replace("%",  "%%")
    )


@router.get("/vgk/media/video-overlay")
async def video_overlay_download(
    request: Request,
    video_url: str = Query(..., description="Relative /storage/... or absolute URL of the source video"),
    name:      str = Query("", description="Member name to stamp on footer"),
    mobile:    str = Query("", description="Member phone number"),
    db: Session = Depends(get_db),
):
    """
    DC-VGK-VIDEO-OVERLAY-001
    Download a VGK promo video with the branded contact footer baked in via ffmpeg.
    Requires VGK member JWT.  Streams the processed mp4 back to the browser.
    """
    import tempfile, shutil, subprocess, urllib.request as _urlreq
    from fastapi import BackgroundTasks
    from fastapi.responses import FileResponse

    # ── Auth ─────────────────────────────────────────────────────────────────
    current_member = _get_current_vgk_member(request, db)
    safe_name   = _dt_esc((name   or current_member.partner_name or "").strip()[:40])
    safe_mobile = _dt_esc((mobile or current_member.phone         or "").strip()[:15])

    # ── Resolve absolute video URL ────────────────────────────────────────────
    # For internal /storage/ or /api/ paths always use 127.0.0.1 to avoid
    # going through the external proxy (request.base_url is the proxy URL in Replit)
    if video_url.startswith("/"):
        abs_url = "http://127.0.0.1:8000" + video_url
    elif video_url.startswith("http"):
        abs_url = video_url
    else:
        raise HTTPException(status_code=400, detail="Invalid video_url")

    # ── Temp workspace ────────────────────────────────────────────────────────
    tmpdir   = tempfile.mkdtemp(prefix="vgk_vid_")
    in_path  = os.path.join(tmpdir, "input.mp4")
    out_path = os.path.join(tmpdir, "output.mp4")

    def _cleanup():
        shutil.rmtree(tmpdir, ignore_errors=True)

    try:
        # Download source video (max 150 MB)
        req = _urlreq.Request(abs_url, headers={"User-Agent": "VGK-Overlay/1.0"})
        with _urlreq.urlopen(req, timeout=60) as r, open(in_path, "wb") as f:
            read = 0
            limit = 150 * 1024 * 1024
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                read += len(chunk)
                if read > limit:
                    raise HTTPException(status_code=413, detail="Video too large (max 150 MB)")
                f.write(chunk)

        has_logo = os.path.isfile(_LOGO_PATH)
        has_bold = os.path.isfile(_BOLD_FONT)
        bf = _BOLD_FONT  if has_bold else _PLAIN_FONT
        pf = _PLAIN_FONT if os.path.isfile(_PLAIN_FONT) else bf

        # ── Build filter_complex ──────────────────────────────────────────────
        # After pad=iw:ih+150, footer occupies y=[ih-150 … ih-1] in padded output
        # ih in subsequent filters = original_ih + 150
        FOOT = 150
        boxes = (
            f"[0:v]pad=iw:ih+{FOOT}:0:0:white[pad];"
            f"[pad]drawbox=x=0:y=ih-{FOOT}:w=iw:h=5:color=1e1b4b@1:t=fill[b1];"
            f"[b1]drawbox=x=0:y=ih-{FOOT-5}:w=iw:h=3:color=d4a017@1:t=fill[b2];"
            f"[b2]drawbox=x=0:y=ih-{FOOT}:w=2:h={FOOT}:color=d4a017@1:t=fill[b3];"
            f"[b3]drawbox=x=iw-2:y=ih-{FOOT}:w=2:h={FOOT}:color=d4a017@1:t=fill[b4];"
            f"[b4]drawbox=x=0:y=ih-2:w=iw:h=2:color=d4a017@1:t=fill[b5];"
            f"[b5]drawbox=x=trunc(iw*0.60):y=ih-{FOOT-8}:w=1:h={FOOT-16}:color=d4a017@1:t=fill[div]"
        )

        # Layout (all y relative to padded ih):
        #   CONTACT label : ih-128  (ih-150+22)
        #   Name          : ih-98   (ih-150+52)
        #   Phone         : ih-54   (nameY+44   → ih-98+44)
        #   vgk4u.com     : ih-22   (near bottom)
        #   Logo top      : ih-125  (ih-150+25)
        contact_y = f"ih-{FOOT - 22}"   # → ih-128
        name_y    = f"ih-{FOOT - 52}"   # → ih-98
        phone_y   = f"ih-{FOOT - 96}"   # → ih-54  (44px below name)
        url_y     = f"ih-{FOOT - 128}"  # → ih-22
        logo_y    = FOOT - 25           # offset from footer top for overlay

        # "CONTACT : Name" on one line — label in plain font at x=22, name in bold right after
        # We approximate label width as ~13 chars * ~10px = ~130px at fontsize=22
        # (ffmpeg drawtext has no measureText; use fixed offset based on label length)
        label_px_offset = 145  # pixels for "CONTACT : " at fontsize=22
        dt_contact = (
            f"[div]drawtext=fontfile='{pf}':text='CONTACT \\:':"
            f"x=22:y={name_y}:fontsize=22:fontcolor=0x6b7280[nc]"
        )
        dt_name_node = (
            f"[nc]drawtext=fontfile='{bf}':text='{safe_name}':"
            f"x={22 + label_px_offset}:y={name_y}:fontsize=28:fontcolor=0x0f172a[n1]"
        )
        dt_nodes = f"{dt_contact};{dt_name_node}"
        prev = "n1"

        if safe_mobile:
            dt_phone = (
                f"[{prev}]drawtext=fontfile='{pf}':text='{safe_mobile}':"
                f"x=22:y={phone_y}:fontsize=22:fontcolor=0x374151[n2]"
            )
            dt_nodes += f";{dt_phone}"
            prev = "n2"

        dt_url = (
            f"[{prev}]drawtext=fontfile='{pf}':text='vgk4u.com':"
            f"x=trunc(iw*0.62)+12:y={url_y}:fontsize=20:fontcolor=0x4c1d95[ntxt]"
        )
        dt_nodes += f";{dt_url}"

        if has_logo:
            fc = (
                f"{boxes};{dt_nodes};"
                f"[1:v]scale=-2:50[logo];"
                f"[ntxt][logo]overlay=x=trunc(W*0.62)+10:y=H-{logo_y}[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-i", _LOGO_PATH,
                "-filter_complex", fc,
                "-map", "[out]", "-map", "0:a?",
                "-c:a", "copy", "-movflags", "+faststart",
                "-t", "600",
                out_path,
            ]
        else:
            dt_mnr = (
                f"[ntxt]drawtext=fontfile='{bf}':text='MyntReal':"
                f"x=trunc(iw*0.62)+12:y=ih-{FOOT - 65}:fontsize=26:fontcolor=0x0f172a[out]"
            )
            fc = f"{boxes};{dt_nodes};{dt_mnr}"
            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-filter_complex", fc,
                "-map", "[out]", "-map", "0:a?",
                "-c:a", "copy", "-movflags", "+faststart",
                "-t", "600",
                out_path,
            ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")[-1000:]
            _cleanup()
            raise HTTPException(status_code=500, detail=f"ffmpeg error: {err}")

        dl_name = "VGK4U_" + (name or "video").replace(" ", "_")[:30] + ".mp4"
        from starlette.background import BackgroundTask as _BackgroundTask
        return FileResponse(
            out_path,
            media_type="video/mp4",
            filename=dl_name,
            background=_BackgroundTask(_cleanup),
            headers={"X-VGK-Overlay": "DC-VGK-VIDEO-OVERLAY-001"},
        )

    except HTTPException:
        _cleanup()
        raise
    except subprocess.TimeoutExpired:
        _cleanup()
        raise HTTPException(status_code=504, detail="Video processing timed out")
    except Exception as e:
        _cleanup()
        raise HTTPException(status_code=500, detail=f"Overlay failed: {e}")
