"""
Hub Website Products API
DC Protocol Compliant — Apr 2026

Staff endpoints (VGK Mentor / EA):
  POST   /vgk/hub/products              — Create product
  GET    /vgk/hub/products              — List (filter by vertical/status)
  GET    /vgk/hub/products/{id}         — Single item
  PATCH  /vgk/hub/products/{id}         — Update
  DELETE /vgk/hub/products/{id}         — Soft delete
  POST   /vgk/hub/products/upload-image — Upload product image → Object Storage

Public (no auth):
  GET    /hub/products                  — Active products by vertical
"""

import os, json, hashlib, mimetypes
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.v1.endpoints.vgk_team import require_vgk_admin
from app.models.base import get_indian_time

router = APIRouter(tags=["Hub Website Products"])

VALID_VERTICALS = {"manthra", "etc", "realdreams", "hgs"}
VALID_STATUS    = {"active", "inactive"}
MAX_IMAGES      = 3

OBJECT_STORAGE_ENDPOINT = os.environ.get("OBJECT_STORAGE_ENDPOINT", "")
OBJECT_STORAGE_TOKEN    = os.environ.get("OBJECT_STORAGE_TOKEN", "")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    keys = ["id","vertical","name","short_description","full_description","notes",
            "images","video_url","product_url","specifications","display_order",
            "status","created_by_id","created_at","updated_at","variants"]
    d = dict(zip(keys, row))
    for f in ("images","specifications","variants"):
        if isinstance(d.get(f), str):
            try: d[f] = json.loads(d[f])
            except Exception: d[f] = []
        elif d.get(f) is None:
            d[f] = []
    if d["created_at"]: d["created_at"] = str(d["created_at"])
    if d["updated_at"]: d["updated_at"] = str(d["updated_at"])
    return d


async def _upload_image_to_storage(file: UploadFile) -> str:
    """Upload to Replit Object Storage and return /storage/{key} URL.
    DC_OBJSTORE_001 (May 2026): Replaced javascript_object_storage (JS shim, absent in
    production VM) with replit.object_storage Python SDK. Returns /storage/{key} served
    by the backend storage endpoint, consistent with all other upload endpoints."""
    try:
        from app.services.object_storage import Client
        content = await file.read()
        ext = mimetypes.guess_extension(file.content_type or "image/jpeg") or ".jpg"
        ts  = datetime.now().strftime("%Y%m%d%H%M%S")
        h   = hashlib.md5(content).hexdigest()[:8]
        key = f"hub_products/{ts}_{h}{ext}"
        Client().upload_from_bytes(key, content)
        return f"/storage/{key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")


# ─────────────────────────────────────────────
# STAFF ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/vgk/hub/products")
async def create_product(payload: dict, db: Session = Depends(get_db),
                         current_user=Depends(require_vgk_admin)):
    vertical = payload.get("vertical","").strip().lower()
    name     = (payload.get("name") or "").strip()
    if not vertical or vertical not in VALID_VERTICALS:
        raise HTTPException(400, detail=f"vertical must be one of: {VALID_VERTICALS}")
    if not name:
        raise HTTPException(400, detail="name is required")

    images = payload.get("images") or []
    if not isinstance(images, list): images = []
    images = images[:MAX_IMAGES]

    specs = payload.get("specifications") or []
    if not isinstance(specs, list): specs = []

    display_order = int(payload.get("display_order") or 0)
    status        = payload.get("status","active")
    if status not in VALID_STATUS: status = "active"

    row = db.execute(text("""
        INSERT INTO hub_website_products
          (vertical, name, short_description, full_description, notes,
           images, video_url, product_url, specifications, variants,
           display_order, status, created_by_id, created_at)
        VALUES
          (:vertical, :name, :short_desc, :full_desc, :notes,
           CAST(:images AS jsonb), :video_url, :product_url, CAST(:specs AS jsonb), CAST(:variants AS jsonb),
           :display_order, :status, :created_by, NOW())
        RETURNING id
    """), {
        "vertical":     vertical,
        "name":         name,
        "short_desc":   payload.get("short_description",""),
        "full_desc":    payload.get("full_description",""),
        "notes":        payload.get("notes",""),
        "images":       json.dumps(images),
        "video_url":    payload.get("video_url",""),
        "product_url":  payload.get("product_url",""),
        "specs":        json.dumps(specs),
        "variants":     json.dumps(payload.get("variants") if isinstance(payload.get("variants"), list) else []),
        "display_order": display_order,
        "status":       status,
        "created_by":   current_user.id if hasattr(current_user,"id") else None,
    })
    db.commit()
    new_id = row.fetchone()[0]
    return {"ok": True, "id": new_id, "message": "Product created"}


@router.get("/vgk/hub/products")
def list_products_staff(
    vertical: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_vgk_admin)
):
    filters = "WHERE deleted_at IS NULL"
    params  = {}
    if vertical and vertical in VALID_VERTICALS:
        filters += " AND vertical = :vertical"
        params["vertical"] = vertical
    if status and status in VALID_STATUS:
        filters += " AND status = :status"
        params["status"] = status

    rows = db.execute(text(f"""
        SELECT id, vertical, name, short_description, full_description, notes,
               images, video_url, product_url, specifications,
               display_order, status, created_by_id, created_at, updated_at, variants
        FROM hub_website_products
        {filters}
        ORDER BY vertical, display_order, id
    """), params).fetchall()

    return {"ok": True, "products": [_row_to_dict(r) for r in rows]}


@router.get("/vgk/hub/products/{product_id}")
def get_product_staff(product_id: int, db: Session = Depends(get_db),
                      current_user=Depends(require_vgk_admin)):
    row = db.execute(text("""
        SELECT id, vertical, name, short_description, full_description, notes,
               images, video_url, product_url, specifications,
               display_order, status, created_by_id, created_at, updated_at, variants
        FROM hub_website_products
        WHERE id = :id AND deleted_at IS NULL
    """), {"id": product_id}).fetchone()
    if not row:
        raise HTTPException(404, detail="Product not found")
    return {"ok": True, "product": _row_to_dict(row)}


@router.patch("/vgk/hub/products/{product_id}")
async def update_product(product_id: int, payload: dict,
                         db: Session = Depends(get_db),
                         current_user=Depends(require_vgk_admin)):
    existing = db.execute(text(
        "SELECT id FROM hub_website_products WHERE id=:id AND deleted_at IS NULL"
    ), {"id": product_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Product not found")

    sets, params = [], {"id": product_id}
    allowed_str = ["name","short_description","full_description","notes","video_url","product_url"]
    for f in allowed_str:
        if f in payload:
            sets.append(f"{f} = :{f}")
            params[f] = payload[f]

    if "vertical" in payload and payload["vertical"] in VALID_VERTICALS:
        sets.append("vertical = :vertical")
        params["vertical"] = payload["vertical"]

    if "status" in payload and payload["status"] in VALID_STATUS:
        sets.append("status = :status")
        params["status"] = payload["status"]

    if "display_order" in payload:
        sets.append("display_order = :display_order")
        params["display_order"] = int(payload["display_order"])

    if "images" in payload:
        imgs = payload["images"] if isinstance(payload["images"], list) else []
        sets.append("images = CAST(:images AS jsonb)")
        params["images"] = json.dumps(imgs[:MAX_IMAGES])

    if "specifications" in payload:
        sp = payload["specifications"] if isinstance(payload["specifications"], list) else []
        sets.append("specifications = CAST(:specifications AS jsonb)")
        params["specifications"] = json.dumps(sp)

    if "variants" in payload:
        vv = payload["variants"] if isinstance(payload["variants"], list) else []
        sets.append("variants = CAST(:variants AS jsonb)")
        params["variants"] = json.dumps(vv)

    if not sets:
        return {"ok": True, "message": "Nothing to update"}

    sets.append("updated_at = NOW()")
    db.execute(text(f"UPDATE hub_website_products SET {', '.join(sets)} WHERE id = :id"), params)
    db.commit()
    return {"ok": True, "message": "Product updated"}


@router.delete("/vgk/hub/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db),
                   current_user=Depends(require_vgk_admin)):
    r = db.execute(text(
        "UPDATE hub_website_products SET deleted_at=NOW(), status='inactive' WHERE id=:id AND deleted_at IS NULL"
    ), {"id": product_id})
    db.commit()
    if r.rowcount == 0:
        raise HTTPException(404, detail="Product not found")
    return {"ok": True, "message": "Product deleted"}


@router.post("/vgk/hub/products/upload-image")
async def upload_product_image(file: UploadFile = File(...),
                               db: Session = Depends(get_db),
                               current_user=Depends(require_vgk_admin)):
    allowed_img   = {"image/jpeg","image/png","image/webp","image/gif"}
    allowed_video = {"video/mp4","video/webm","video/quicktime","video/avi","video/mpeg"}
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in allowed_img and ct not in allowed_video:
        raise HTTPException(400, detail="Only JPEG/PNG/WebP/GIF images or MP4/WebM/MOV videos allowed")
    if ct in allowed_video:
        content = await file.read()
        if len(content) > 300 * 1024 * 1024:
            raise HTTPException(400, detail="Video file must be under 300 MB")
        await file.seek(0)
    url = await _upload_image_to_storage(file)
    return {"ok": True, "url": url, "type": "video" if ct in allowed_video else "image"}


# ─────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/hub/products")
def list_products_public(
    vertical: str = Query(..., description="manthra | etc | realdreams"),
    db: Session = Depends(get_db)
):
    if vertical not in VALID_VERTICALS:
        raise HTTPException(400, detail=f"vertical must be one of: {VALID_VERTICALS}")

    rows = db.execute(text("""
        SELECT id, vertical, name, short_description, full_description, notes,
               images, video_url, product_url, specifications,
               display_order, status, created_by_id, created_at, updated_at, variants
        FROM hub_website_products
        WHERE vertical = :vertical AND status = 'active' AND deleted_at IS NULL
        ORDER BY display_order, id
    """), {"vertical": vertical}).fetchall()

    return {"ok": True, "vertical": vertical, "products": [_row_to_dict(r) for r in rows]}
