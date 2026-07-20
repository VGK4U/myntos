"""
DC_GALLERY_001 Apr 2026 — VGK Gallery (photos & short videos)
Staff (VGK Mentor/EA) can create gallery sets and upload up to 15 photos + 4 videos per set.
Constraints: videos ≤ 3 minutes (180 sec).
Public can browse all published galleries.

Endpoints:
  Staff:
    POST   /vgk/gallery                      — Create gallery set
    GET    /vgk/gallery                      — List all gallery sets
    GET    /vgk/gallery/{id}                 — Get single gallery with files
    PATCH  /vgk/gallery/{id}                 — Update title/description/status/thumbnail_url
    DELETE /vgk/gallery/{id}                 — Soft-delete gallery
    POST   /vgk/gallery/{id}/files           — Upload files to gallery (multipart)
    DELETE /vgk/gallery/{id}/files/{file_id} — Remove a file from gallery
    PATCH  /vgk/gallery/{id}/thumbnail       — Set gallery thumbnail image

  Public:
    GET    /hub/gallery                      — List active galleries with files
"""

import hashlib, mimetypes
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.vgk_team import require_vgk_admin
from app.models.base import get_indian_time

router = APIRouter(tags=["VGK Gallery"])

ALLOWED_PHOTO_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif',
}
ALLOWED_VIDEO_TYPES = {
    'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/mpeg',
}
MAX_IMAGES  = 15
MAX_VIDEOS  = 4
MAX_FILES   = MAX_IMAGES + MAX_VIDEOS   # 19 total ceiling
MIN_FILES   = 1


# ─── Private: compress + upload helper ───────────────────────────────────────
_COMPRESSIBLE_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}

def _compress_image_to_webp(content: bytes, content_type: str) -> tuple:
    """Compress raster images to WebP ≤1920 px @ quality 85.
    GIFs and non-image types are returned unchanged.
    Returns (bytes, mime_type).
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


async def _upload_gallery_file(file: UploadFile, prefix: str = "vgk_gallery") -> tuple:
    """Upload gallery file to Replit Object Storage.
    Images (JPEG/PNG/WebP) are auto-compressed to WebP ≤1920 px @ quality 85.
    Videos are uploaded as-is.
    Returns (/storage/{key} URL, file_size_bytes).
    """
    from app.services.object_storage import storage_service
    content = await file.read()
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    content, ct = _compress_image_to_webp(content, ct)
    ext = ".webp" if ct == "image/webp" else (
        mimetypes.guess_extension(ct)
        or ("." + (file.filename or "file").rsplit(".", 1)[-1])
        or ".bin"
    )
    ts  = datetime.now().strftime("%Y%m%d%H%M%S")
    h   = hashlib.md5(content).hexdigest()[:8]
    key = f"{prefix}/{ts}_{h}{ext}"
    ok  = storage_service.upload_file(key, content)
    if not ok:
        raise HTTPException(status_code=500, detail="File upload to storage failed")
    return storage_service.get_file_url(key), len(content)  # → /storage/{key}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Create gallery set
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/vgk/gallery")
async def create_gallery(
    request: Request,
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    desc = (body.get("description") or "").strip() or None

    now = get_indian_time()
    result = db.execute(
        text("""
            INSERT INTO vgk_gallery (title, description, status, created_by_id, created_at, updated_at)
            VALUES (:title, :desc, 'active', :by, :now, :now)
            RETURNING id
        """),
        {"title": title, "desc": desc, "by": current_user.id, "now": now},
    )
    db.commit()
    gid = result.fetchone()[0]
    return {"ok": True, "id": gid, "title": title}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: List galleries
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/vgk/gallery")
async def list_galleries(
    status: Optional[str] = Query(None),
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    q = """
        SELECT g.id, g.title, g.description, g.thumbnail_url, g.status, g.created_at, g.updated_at,
               COALESCE(fc.cnt, 0) AS file_count,
               COALESCE(vc.vcnt, 0) AS video_count
        FROM vgk_gallery g
        LEFT JOIN (
            SELECT gallery_id, COUNT(*) AS cnt FROM vgk_gallery_files GROUP BY gallery_id
        ) fc ON fc.gallery_id = g.id
        LEFT JOIN (
            SELECT gallery_id, COUNT(*) AS vcnt FROM vgk_gallery_files WHERE file_type = 'video' GROUP BY gallery_id
        ) vc ON vc.gallery_id = g.id
        WHERE g.deleted_at IS NULL
    """
    params: dict = {}
    if status:
        q += " AND g.status = :status"
        params["status"] = status
    q += " ORDER BY g.created_at DESC"

    rows = db.execute(text(q), params).fetchall()
    galleries = []
    for row in rows:
        g = dict(row._mapping)
        # Prefer photos for card preview; fall back to first video if no photos
        photo_prev = db.execute(
            text("""
                SELECT file_url, file_type, thumbnail_url
                FROM vgk_gallery_files
                WHERE gallery_id = :gid AND file_type = 'photo'
                ORDER BY display_order, id LIMIT 1
            """),
            {"gid": g["id"]},
        ).fetchone()
        any_prev = photo_prev or db.execute(
            text("""
                SELECT file_url, file_type, thumbnail_url
                FROM vgk_gallery_files
                WHERE gallery_id = :gid
                ORDER BY display_order, id LIMIT 1
            """),
            {"gid": g["id"]},
        ).fetchone()
        g["preview_url"] = None
        g["preview_type"] = None
        if g.get("thumbnail_url"):
            g["preview_url"] = g["thumbnail_url"]
            g["preview_type"] = "photo"
        elif any_prev:
            g["preview_url"] = any_prev.thumbnail_url or any_prev.file_url
            g["preview_type"] = any_prev.file_type
        galleries.append(g)

    return {"ok": True, "galleries": galleries, "total": len(galleries)}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Get single gallery with files
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/vgk/gallery/{gallery_id}")
async def get_gallery(
    gallery_id: int,
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT * FROM vgk_gallery WHERE id = :id AND deleted_at IS NULL"),
        {"id": gallery_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gallery not found")
    g = dict(row._mapping)
    files = db.execute(
        text("SELECT * FROM vgk_gallery_files WHERE gallery_id = :gid ORDER BY display_order, id"),
        {"gid": gallery_id},
    ).fetchall()
    g["files"] = [dict(f._mapping) for f in files]
    return {"ok": True, "gallery": g}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Update gallery
# ──────────────────────────────────────────────────────────────────────────────

@router.patch("/vgk/gallery/{gallery_id}")
async def update_gallery(
    gallery_id: int,
    request: Request,
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id FROM vgk_gallery WHERE id = :id AND deleted_at IS NULL"),
        {"id": gallery_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gallery not found")

    body = await request.json()
    updates: dict = {}
    if body.get("title"):
        updates["title"] = body["title"].strip()
    if "description" in body:
        updates["description"] = (body["description"] or "").strip() or None
    if body.get("status") in ("active", "archived"):
        updates["status"] = body["status"]
    if "thumbnail_url" in body:
        updates["thumbnail_url"] = (body["thumbnail_url"] or "").strip() or None

    if not updates:
        return {"ok": True, "message": "Nothing to update"}

    updates["updated_at"] = get_indian_time()
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = gallery_id
    db.execute(text(f"UPDATE vgk_gallery SET {set_clause} WHERE id = :id"), updates)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Soft-delete gallery
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/vgk/gallery/{gallery_id}")
async def delete_gallery(
    gallery_id: int,
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id FROM vgk_gallery WHERE id = :id AND deleted_at IS NULL"),
        {"id": gallery_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gallery not found")

    now = get_indian_time()
    db.execute(
        text("UPDATE vgk_gallery SET deleted_at = :now, status = 'archived' WHERE id = :id"),
        {"now": now, "id": gallery_id},
    )
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Upload files to a gallery
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/vgk/gallery/{gallery_id}/files")
async def upload_gallery_files(
    gallery_id: int,
    files: List[UploadFile] = File(...),
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id FROM vgk_gallery WHERE id = :id AND deleted_at IS NULL"),
        {"id": gallery_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gallery not found")

    existing = db.execute(
        text("""
            SELECT COUNT(*) AS cnt,
                   COUNT(CASE WHEN file_type = 'video' THEN 1 END) AS vcnt,
                   COUNT(CASE WHEN file_type = 'photo' THEN 1 END) AS pcnt
            FROM vgk_gallery_files WHERE gallery_id = :gid
        """),
        {"gid": gallery_id},
    ).fetchone()
    ex_total  = existing.cnt  or 0
    ex_videos = existing.vcnt or 0
    ex_photos = existing.pcnt or 0

    if ex_total + len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Would exceed max {MAX_IMAGES} images + {MAX_VIDEOS} videos per gallery (currently {ex_total})",
        )

    new_video_count = 0
    new_photo_count = 0
    uploaded = []

    for f in files:
        ct = (f.content_type or "").lower().split(";")[0].strip()
        if ct in ALLOWED_PHOTO_TYPES:
            file_type = "photo"
        elif ct in ALLOWED_VIDEO_TYPES:
            file_type = "video"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported type '{ct}' for {f.filename}. Allowed: JPEG/PNG/WebP/GIF/MP4/WebM",
            )

        if file_type == "video":
            new_video_count += 1
            if ex_videos + new_video_count > MAX_VIDEOS:
                raise HTTPException(status_code=400, detail=f"Max {MAX_VIDEOS} videos allowed per gallery")
        else:
            new_photo_count += 1
            if ex_photos + new_photo_count > MAX_IMAGES:
                raise HTTPException(status_code=400, detail=f"Max {MAX_IMAGES} images allowed per gallery")

        try:
            file_url, file_size = await _upload_gallery_file(f)
            file_name = f.filename or "file"

            ord_row = db.execute(
                text("SELECT COALESCE(MAX(display_order), 0) + 1 AS nxt FROM vgk_gallery_files WHERE gallery_id = :gid"),
                {"gid": gallery_id},
            ).fetchone()
            nxt = ord_row.nxt if ord_row else 1

            now = get_indian_time()
            ins = db.execute(
                text("""
                    INSERT INTO vgk_gallery_files
                        (gallery_id, file_url, file_type, file_name, file_size, display_order, created_at)
                    VALUES (:gid, :url, :ftype, :fname, :fsize, :ord, :now)
                    RETURNING id
                """),
                {
                    "gid": gallery_id, "url": file_url, "ftype": file_type,
                    "fname": file_name, "fsize": file_size, "ord": nxt, "now": now,
                },
            )
            file_id = ins.fetchone()[0]
            db.commit()
            uploaded.append({"id": file_id, "file_url": file_url, "file_type": file_type, "file_name": file_name})
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Upload failed for {f.filename}: {e}")

    db.execute(
        text("UPDATE vgk_gallery SET updated_at = :now WHERE id = :id"),
        {"now": get_indian_time(), "id": gallery_id},
    )
    db.commit()
    return {"ok": True, "uploaded": uploaded, "count": len(uploaded)}


# ──────────────────────────────────────────────────────────────────────────────
# STAFF: Delete a file from gallery
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/vgk/gallery/{gallery_id}/files/{file_id}")
async def delete_gallery_file(
    gallery_id: int,
    file_id: int,
    current_user=Depends(require_vgk_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id FROM vgk_gallery_files WHERE id = :id AND gallery_id = :gid"),
        {"id": file_id, "gid": gallery_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found in this gallery")

    db.execute(text("DELETE FROM vgk_gallery_files WHERE id = :id"), {"id": file_id})
    db.execute(
        text("UPDATE vgk_gallery SET updated_at = :now WHERE id = :id"),
        {"now": get_indian_time(), "id": gallery_id},
    )
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC: List active galleries with files (no auth)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/hub/gallery")
async def hub_gallery(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT id, title, description, thumbnail_url, created_at
            FROM vgk_gallery
            WHERE status = 'active' AND deleted_at IS NULL
            ORDER BY created_at DESC
        """)
    ).fetchall()

    galleries = []
    for row in rows:
        g = dict(row._mapping)
        files = db.execute(
            text("""
                SELECT id, file_url, file_type, file_name, thumbnail_url, display_order
                FROM vgk_gallery_files
                WHERE gallery_id = :gid
                ORDER BY display_order, id
            """),
            {"gid": g["id"]},
        ).fetchall()
        g["files"] = [dict(f._mapping) for f in files]
        g["file_count"] = len(g["files"])
        if g["files"]:
            galleries.append(g)

    return {"ok": True, "galleries": galleries, "total": len(galleries)}
