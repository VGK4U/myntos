"""
Hub Website Asset Manager API
DC Protocol Compliant — Apr 2026

Staff-only endpoints (VGK Mentor / EA / high-level admin):
  GET    /vgk/hub/assets              — List all assets (auto-scan placements + cloud sync)
  POST   /vgk/hub/assets/upload       — Upload + auto-optimize + dual-write (disk + cloud)
  DELETE /vgk/hub/assets/{fname}      — Delete custom asset (system slot files blocked)
  GET    /vgk/hub/assets/scan/{fname} — Re-scan placements for a single file

Storage strategy:
  1. Every upload writes to local disk (immediately served via /hub/Assets/)
  2. Every upload also writes to Object Storage key=hub_assets/{filename}
  3. A manifest JSON (hub_assets_manifest.json) is kept in Object Storage listing
     all uploaded files with their obj_url.
  4. On first GET /vgk/hub/assets call after a fresh container start, if any manifest
     files are missing from local disk they are re-downloaded from Object Storage,
     so production deployments are always complete.
  DC_HUB_ADMIN_001 (May 2026): Broadened access — VGK/EA staff AND any staff with
     hierarchy_level >= 85 or role_code in {SUPER_ADMIN,CEO,CTO,CFO,FOUNDER,MARKETING}.
"""

import os, io, re, json, time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from PIL import Image

from app.api.v1.endpoints.vgk_team import require_vgk_admin
from app.api.v1.endpoints.staff_auth import get_current_staff_user

# DC_HUB_ADMIN_001: Broader access guard — VGK/EA staff OR high-level admin roles
_HUB_ADMIN_ROLES = {"SUPER_ADMIN", "CEO", "CTO", "CFO", "FOUNDER", "MARKETING", "DIRECTOR"}

def _require_hub_admin(current_user=Depends(get_current_staff_user)):
    """Allow VGK/EA staff types OR hierarchy_level >= 85 OR specific admin roles."""
    st = (current_user.staff_type or "").upper()
    if "VGK" in st or st == "EA":
        return current_user
    try:
        hl = current_user.role.hierarchy_level if current_user.role else 0
        rc = (current_user.role.role_code or "").upper() if current_user.role else ""
        if hl >= 85 or rc in _HUB_ADMIN_ROLES:
            return current_user
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Website Asset Manager: VGK/EA staff or admin role required")

# ─── Lightweight DB KV helper (no ORM — raw psycopg2) ────────────────────────
def _kv_get(key: str) -> str:
    """Read a value from hub_kv table. Returns '' on any error."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur  = conn.cursor()
        cur.execute("SELECT value FROM hub_kv WHERE key = %s", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""

def _kv_set(key: str, value: str) -> None:
    """Upsert a value into hub_kv table. Creates table if missing."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hub_kv (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        cur.execute("""
            INSERT INTO hub_kv (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, value))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WA] hub_kv write failed: {e}")

router = APIRouter(tags=["Hub Website Assets"])

# ─── Paths ──────────────────────────────────────────────────────────────────
_HERE      = os.path.dirname(os.path.abspath(__file__))
HUB_DIR    = os.path.normpath(os.path.join(_HERE, '..', '..', '..', '..', '..', 'frontend', 'public', 'hub'))
ASSETS_DIR = os.path.join(HUB_DIR, 'Assets')
LANDING_PATH = os.path.normpath(os.path.join(HUB_DIR, '..', 'landing.html'))

# ─── Object Storage helpers ──────────────────────────────────────────────────
_OBJ_PREFIX      = "hub_assets"
_MANIFEST_KEY    = f"{_OBJ_PREFIX}/_manifest.json"
_LOCAL_MANIFEST  = os.path.join(ASSETS_DIR, ".wa_manifest.json")
_MANIFEST_URL_FILE = os.path.join(ASSETS_DIR, ".manifest_url")  # persists the cloud manifest URL
_synced_this_run = False   # only sync once per process start

def _obj_upload(key: str, data: bytes, content_type: str = "image/png") -> str:
    """Upload bytes to Object Storage. Returns /storage/{key} URL or '' on failure.
    DC_OBJSTORE_001 (May 2026): Replaced javascript_object_storage (JS integration shim,
    unavailable in production VM) with replit.object_storage Python SDK which is always
    present. Returns /storage/{key} URL served by the backend storage endpoint."""
    try:
        from app.services.object_storage import Client
        Client().upload_from_bytes(key, data)
        return f"/storage/{key}"
    except Exception as e:
        print(f"[WA] Object Storage upload failed for {key}: {e}")
        return ""

def _load_manifest() -> dict:
    """Load the local manifest cache. Returns {} on missing/error."""
    try:
        if os.path.isfile(_LOCAL_MANIFEST):
            with open(_LOCAL_MANIFEST, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_manifest(manifest: dict) -> None:
    """Persist manifest locally, push copy to Object Storage, and save the public URL
    both to the filesystem and to hub_kv DB table so a fresh production container
    can always bootstrap the manifest without requiring a committed file."""
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
        with open(_LOCAL_MANIFEST, "w") as f:
            json.dump(manifest, f, indent=2)
        url = _obj_upload(_MANIFEST_KEY, json.dumps(manifest, indent=2).encode(), "application/json")
        if url:
            with open(_MANIFEST_URL_FILE, "w") as f:
                f.write(url)
            _kv_set("hub_manifest_url", url)
            print(f"[WA] manifest URL saved to file+DB: {url[:60]}...")
    except Exception as e:
        print(f"[WA] manifest save error: {e}")

def _mime_for(fname: str) -> str:
    """Return MIME type based on file extension."""
    ext = os.path.splitext(fname)[1].lower()
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
        ".avif": "image/avif",
    }.get(ext, "application/octet-stream")


def _sync_from_cloud() -> None:
    """
    On first list call per process: read the manifest and re-download any files
    that are in the manifest but missing from the local Assets directory.
    Phase 2 (backfill): any local file with an empty obj_url gets uploaded to
    Object Storage so future fresh containers can restore it automatically.
    Bootstrap priority (fresh deployment):
      1. Local .wa_manifest.json cache
      2. .manifest_url file (URL written after each upload)
      3. hub_kv DB table  (written alongside file — survives deploys)
    This ensures a fresh production container picks up all previously
    uploaded assets automatically without manual staff intervention.
    """
    global _synced_this_run
    if _synced_this_run:
        return
    _synced_this_run = True

    manifest = _load_manifest()

    # Bootstrap from cloud if local manifest is absent
    # DC_OBJSTORE_001 (May 2026): Try Object Storage SDK first (works at container startup
    # before the backend HTTP server is listening).  Fall back to httpx for legacy http:// URLs.
    if not manifest:
        # Priority 1: direct SDK read of manifest from Object Storage
        try:
            from app.services.object_storage import Client as _ObjClient
            data = _ObjClient().download_as_bytes(_MANIFEST_KEY)
            if data:
                manifest = json.loads(data)
                os.makedirs(ASSETS_DIR, exist_ok=True)
                with open(_LOCAL_MANIFEST, "w") as f:
                    json.dump(manifest, f, indent=2)
                print(f"[WA] manifest bootstrapped from Object Storage SDK: {len(manifest)} entries")
        except Exception as _e:
            print(f"[WA] SDK manifest bootstrap failed (trying URL fallback): {_e}")

    if not manifest:
        # Priority 2: legacy http:// URL stored in file / DB (backward compat)
        import httpx as _httpx
        murl = ""
        try:
            if os.path.isfile(_MANIFEST_URL_FILE):
                with open(_MANIFEST_URL_FILE) as f:
                    murl = f.read().strip()
        except Exception:
            pass
        if not murl:
            murl = _kv_get("hub_manifest_url")
        if murl and murl.startswith("http"):
            try:
                r = _httpx.get(murl, timeout=15, follow_redirects=True)
                if r.status_code == 200:
                    manifest = r.json()
                    os.makedirs(ASSETS_DIR, exist_ok=True)
                    with open(_LOCAL_MANIFEST, "w") as f:
                        json.dump(manifest, f, indent=2)
                    print(f"[WA] manifest bootstrapped from legacy URL: {len(manifest)} entries")
            except Exception as e:
                print(f"[WA] cloud manifest bootstrap failed: {e}")

    if not manifest:
        print("[WA] no manifest available — cloud sync skipped")
        return

    os.makedirs(ASSETS_DIR, exist_ok=True)

    # ── Phase 1: Download cloud files missing from local disk ─────────────────
    synced = 0
    skipped = 0
    failed = 0
    for fname, entry in manifest.items():
        fpath = os.path.join(ASSETS_DIR, fname)
        if os.path.isfile(fpath):
            skipped += 1
            continue
        url = entry.get("obj_url", "")
        if not url:
            continue
        try:
            # DC_OBJSTORE_001 (May 2026): /storage/{key} URLs use SDK download.
            # Legacy http:// URLs use httpx (backward compat for old javascript_object_storage entries).
            file_bytes = None
            if url.startswith("/storage/"):
                obj_key = url[len("/storage/"):]
                from app.services.object_storage import Client as _ObjClient
                file_bytes = _ObjClient().download_as_bytes(obj_key)
            elif url.startswith("http"):
                import httpx as _httpx
                r = _httpx.get(url, timeout=15, follow_redirects=True)
                if r.status_code == 200:
                    file_bytes = r.content
            if file_bytes:
                with open(fpath, "wb") as f:
                    f.write(file_bytes)
                os.chmod(fpath, 0o644)
                synced += 1
                print(f"[WA] synced from cloud: {fname}", flush=True)
            else:
                failed += 1
                print(f"[WA] ⚠️ cloud sync empty response for {fname} (url={url})", flush=True)
        except Exception as e:
            failed += 1
            print(f"[WA] ❌ cloud sync failed for {fname}: {type(e).__name__}: {e}", flush=True)
    print(f"[WA] phase-1 summary: {synced} restored, {skipped} already present, {failed} failed", flush=True)
    if synced:
        print(f"[WA] ✅ phase-1 cloud sync complete — {synced} files restored", flush=True)

    # ── Phase 2: Upload local files that have no cloud backup ─────────────────
    # Covers git-committed assets that were never uploaded to Object Storage.
    # Handles both: manifest entries with empty obj_url, AND files on disk that
    # are not in the manifest at all (common for git-committed initial assets).
    # Once uploaded, obj_url is persisted so this runs only once per file.
    _IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
    manifest_changed = False
    uploaded = 0

    # Build full candidate list: manifest files + disk files not in manifest
    candidates: dict = {}
    for fname, entry in manifest.items():
        if not entry.get("obj_url"):
            candidates[fname] = entry
    try:
        for fname in os.listdir(ASSETS_DIR):
            if fname.startswith("."):
                continue
            if os.path.splitext(fname)[1].lower() not in _IMG_EXTS:
                continue
            if fname not in manifest:
                candidates[fname] = {}     # disk-only file, not in manifest yet
    except Exception:
        pass

    for fname, entry in candidates.items():
        fpath = os.path.join(ASSETS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "rb") as fh:
                data = fh.read()
            obj_key = f"{_OBJ_PREFIX}/{fname}"
            url = _obj_upload(obj_key, data, _mime_for(fname))
            if url:
                if fname not in manifest:
                    manifest[fname] = {"obj_key": obj_key, "obj_url": url,
                                       "preset": "partner", "slot": None,
                                       "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                       "size_kb": round(len(data) / 1024, 1)}
                else:
                    manifest[fname]["obj_url"] = url
                    manifest[fname]["obj_key"] = obj_key
                manifest_changed = True
                uploaded += 1
                print(f"[WA] backfilled to cloud: {fname}")
        except Exception as e:
            print(f"[WA] cloud backfill failed for {fname}: {e}")
    if uploaded:
        print(f"[WA] ✅ phase-2 backfill complete — {uploaded} files uploaded to Object Storage")
    if manifest_changed:
        _save_manifest(manifest)

# ─── Asset type presets ─────────────────────────────────────────────────────
PRESETS = {
    "logo-h":      {"label": "Logo (Horizontal)",      "w": 400,  "h": 120,  "alpha": True,  "fmt": "PNG",  "q": 90},
    "logo-v":      {"label": "Logo (Vertical/Square)", "w": 240,  "h": 240,  "alpha": True,  "fmt": "PNG",  "q": 90},
    "brand-card":  {"label": "Brand Card Logo",        "w": 220,  "h": 110,  "alpha": True,  "fmt": "PNG",  "q": 90},
    "hero-bg":     {"label": "Hero Background",        "w": 1280, "h": 720,  "alpha": False, "fmt": "WEBP", "q": 72},
    "banner":      {"label": "Banner / Hero Image",    "w": 1280, "h": 500,  "alpha": False, "fmt": "WEBP", "q": 74},
    "product":     {"label": "Product Image",          "w": 800,  "h": 600,  "alpha": False, "fmt": "WEBP", "q": 78},
    "certificate": {"label": "Certificate / Document", "w": 1200, "h": 900,  "alpha": False, "fmt": "WEBP", "q": 88},
    "partner":     {"label": "Partner / Finance Logo", "w": 300,  "h": 120,  "alpha": True,  "fmt": "PNG",  "q": 90},
    "other":       {"label": "Other",                  "w": 1200, "h": 1200, "alpha": True,  "fmt": "PNG",  "q": 85},
}

# ─── System Slots ───────────────────────────────────────────────────────────
SYSTEM_SLOTS = {
    "header-logo":       {"label": "Header Logo (Light BG)",      "filename": "Myntreal.logo.png",   "preset": "logo-h"},
    "footer-logo":       {"label": "Footer Logo (Dark BG)",       "filename": "MyntWhite.png",       "preset": "logo-h"},
    "hub-hero-bg":       {"label": "Hub Hero Background",         "filename": "hero-bg.webp",        "preset": "hero-bg"},
    "iso-certificate":   {"label": "ISO Certificate",             "filename": "ISO-Certificate.png", "preset": "certificate"},
    "manthra-hero":      {"label": "Manthra EV Hero Image",       "filename": "Manthra_1.webp",      "preset": "banner"},
    "manthra-ev-logo":   {"label": "Manthra EV Logo",             "filename": "ManthraEV-logo.webp", "preset": "logo-h"},
    "hgs-logo":          {"label": "Har Ghar Solar Logo",         "filename": "hgs-logo.png",        "preset": "logo-h"},
    "vgk-care-logo":     {"label": "VGK Care Logo",               "filename": "Care.png",            "preset": "logo-h"},
    "realestate-logo":   {"label": "VGK Real Dreams Logo",        "filename": "realdreams.webp",     "preset": "logo-h"},
    "etc-logo":          {"label": "EVolution Training Logo",     "filename": "ETC.webp",            "preset": "logo-h"},
    "manthra-dealer":    {"label": "Manthra Dealer Hero",         "filename": "Manthra-D.png",       "preset": "banner"},
    "zynova-logo":       {"label": "Zynova Mobility Logo",        "filename": "zynova-mobility-logo.png", "preset": "brand-card"},
    "vgk4u-logo":        {"label": "VGK4U Logo",                  "filename": "vgk4u-logo.png",      "preset": "brand-card"},
    "mnr-logo":          {"label": "MNR Logo",                    "filename": "mnr-logo.png",        "preset": "brand-card"},
}

# ─── Category rules ─────────────────────────────────────────────────────────
_LOGO_SLOTS   = {"header-logo","footer-logo","manthra-ev-logo","hgs-logo","vgk-care-logo","realestate-logo","etc-logo"}
_BANNER_SLOTS = {"hub-hero-bg","manthra-hero","manthra-dealer"}
_BRAND_SLOTS  = {"zynova-logo","vgk4u-logo","mnr-logo"}
_DOC_SLOTS    = {"iso-certificate"}

# ─── Pages to scan for placements ───────────────────────────────────────────
PAGE_MAP = {
    "index.html":      ("Home",                    "/hub"),
    "about.html":      ("About",                   "/hub/about"),
    "about.css":       ("About (CSS)",             "/hub/about"),
    "manthra.html":    ("Manthra EV",              "/hub/manthra"),
    "manthra.css":     ("Manthra EV (CSS)",        "/hub/manthra"),
    "hgs.html":        ("Har Ghar Solar",          "/hub/hgs"),
    "care.html":       ("VGK Care",                "/hub/care"),
    "realestate.html": ("VGK Real Dreams",         "/hub/realestate"),
    "etc.html":        ("EVolution Training",      "/hub/etc"),
    "media.html":      ("Media",                   "/hub/media"),
    "contact.html":    ("Contact",                 "/hub/contact"),
    "style.css":       ("Shared Styles",           None),
}


def _scan_placements(filename: str) -> list:
    """Scan hub HTML/CSS + landing.html for uses of filename."""
    results = []
    search_name  = os.path.basename(filename)
    search_enc   = search_name.replace(' ', '%20')

    for rel, (label, url) in PAGE_MAP.items():
        fpath = os.path.normpath(os.path.join(HUB_DIR, rel))
        if not os.path.isfile(fpath):
            continue
        try:
            content = open(fpath, encoding='utf-8', errors='ignore').read()
            if search_name in content or (search_enc != search_name and search_enc in content):
                results.append({"file": rel, "page": label, "url": url})
        except Exception:
            pass

    if os.path.isfile(LANDING_PATH):
        try:
            content = open(LANDING_PATH, encoding='utf-8', errors='ignore').read()
            if search_name in content or (search_enc != search_name and search_enc in content):
                results.append({"file": "landing.html", "page": "Landing / Portal", "url": "/landing"})
        except Exception:
            pass

    return results


def _optimize_image(content: bytes, preset_key: str, force_fmt: str = None) -> tuple:
    """Resize + compress. Returns (bytes, ext, final_w, final_h, orig_w, orig_h).
    force_fmt: 'PNG' | 'JPG' | 'WEBP' — overrides preset format when provided.
    """
    p = dict(PRESETS.get(preset_key, PRESETS["other"]))

    # Apply caller-requested format override
    if force_fmt:
        norm = force_fmt.upper()
        if norm in ('JPG', 'JPEG'):
            p["fmt"]   = "JPEG"
            p["alpha"] = False
        elif norm == 'WEBP':
            p["fmt"]   = "WEBP"
            p["alpha"] = False
        elif norm == 'PNG':
            p["fmt"]   = "PNG"
            p["alpha"] = True

    img = Image.open(io.BytesIO(content))
    orig_w, orig_h = img.size

    if p["alpha"] and img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGBA')
    elif not p["alpha"] and img.mode != 'RGB':
        img = img.convert('RGB')
    elif img.mode not in ('RGBA', 'RGB', 'L', 'LA'):
        img = img.convert('RGBA' if p["alpha"] else 'RGB')

    img.thumbnail((p["w"], p["h"]), Image.LANCZOS)
    final_w, final_h = img.size

    out = io.BytesIO()
    if p["fmt"] == "WEBP":
        save_img = img.convert('RGB') if img.mode == 'RGBA' else img
        save_img.save(out, format='WEBP', quality=p.get("q", 82), method=6)
        ext = '.webp'
    elif p["fmt"] == "JPEG":
        img.convert('RGB').save(out, format='JPEG', quality=p.get("q", 85), optimize=True)
        ext = '.jpg'
    else:
        if img.mode == 'RGBA':
            img.save(out, format='PNG', optimize=True)
        else:
            img.convert('RGB').save(out, format='PNG', optimize=True)
        ext = '.png'

    return out.getvalue(), ext, final_w, final_h, orig_w, orig_h


def _file_info(filename: str) -> dict:
    """Get metadata for a file in ASSETS_DIR."""
    fpath = os.path.join(ASSETS_DIR, filename)
    if not os.path.isfile(fpath):
        return {}
    stat = os.stat(fpath)
    size_kb = round(stat.st_size / 1024, 1)
    w, h = None, None
    try:
        img = Image.open(fpath)
        w, h = img.size
        img.close()
    except Exception:
        pass
    url_name = filename.replace(' ', '%20')
    return {
        "filename":  filename,
        "url":       f"/hub/Assets/{url_name}?v={int(stat.st_mtime)}",
        "size_kb":   size_kb,
        "width":     w,
        "height":    h,
        "ext":       os.path.splitext(filename)[1].lower(),
        "modified":  datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _build_asset_list() -> list:
    """Scan ASSETS_DIR and return full asset list with slot + placements info."""
    file_to_slot = {v["filename"]: k for k, v in SYSTEM_SLOTS.items()}

    try:
        entries = sorted(os.listdir(ASSETS_DIR))
    except Exception:
        return []

    assets = []
    for fname in entries:
        fpath = os.path.join(ASSETS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.avif'}:
            continue

        info = _file_info(fname)
        if not info:
            continue

        slot = file_to_slot.get(fname)
        info["slot"]        = slot
        info["slot_label"]  = SYSTEM_SLOTS[slot]["label"] if slot else None
        info["is_system"]   = slot is not None
        info["placements"]  = _scan_placements(fname)
        info["placement_count"] = len(info["placements"])

        if slot in _LOGO_SLOTS:
            info["category"] = "logo"
        elif slot in _BANNER_SLOTS:
            info["category"] = "banner"
        elif slot in _BRAND_SLOTS:
            info["category"] = "brand"
        elif slot in _DOC_SLOTS:
            info["category"] = "document"
        else:
            ext_low = info["ext"]
            if fname.lower().endswith(('.png','.webp','.jpg','.jpeg')) and info["placement_count"] == 0:
                info["category"] = "unused"
            else:
                info["category"] = "other"

        assets.append(info)

    return assets


# ─── LIST ────────────────────────────────────────────────────────────────────

@router.get("/vgk/hub/assets")
async def list_assets(current_user=Depends(_require_hub_admin)):
    _sync_from_cloud()   # no-op after first call per process
    assets = _build_asset_list()
    # DC_ASSETS_SELF_HEAL_001 (May 2026): If ASSETS_DIR is empty but the manifest has
    # entries, the startup sync may have been skipped in the production container.
    # Reset the flag and re-sync once to self-heal without requiring a redeploy.
    if not assets and _load_manifest():
        global _synced_this_run
        _synced_this_run = False
        print("[WA] ⚠️ list_assets: ASSETS_DIR empty but manifest found — forcing re-sync", flush=True)
        _sync_from_cloud()
        assets = _build_asset_list()
    total_kb = sum(a.get("size_kb", 0) for a in assets)
    system   = [a for a in assets if a["is_system"]]
    custom   = [a for a in assets if not a["is_system"]]
    used     = [a for a in assets if a["placement_count"] > 0]
    unused   = [a for a in assets if a["placement_count"] == 0 and not a["is_system"]]
    return {
        "assets": assets,
        "stats": {
            "total":         len(assets),
            "system_slots":  len(system),
            "custom":        len(custom),
            "in_use":        len(used),
            "unused":        len(unused),
            "total_size_mb": round(total_kb / 1024, 2),
        },
        "presets":      PRESETS,
        "system_slots": SYSTEM_SLOTS,
    }


# ─── UPLOAD + OPTIMIZE ───────────────────────────────────────────────────────

@router.post("/vgk/hub/assets/upload")
async def upload_asset(
    file: UploadFile            = File(...),
    preset: str                 = Form("other"),
    custom_name: Optional[str]  = Form(None),
    slot: Optional[str]         = Form(None),
    original_filename: Optional[str] = Form(None),
    force_format: Optional[str] = Form(None),
    current_user=Depends(_require_hub_admin),
):
    if preset not in PRESETS:
        raise HTTPException(400, f"Unknown preset '{preset}'. Valid: {list(PRESETS.keys())}")
    if slot and slot not in SYSTEM_SLOTS:
        raise HTTPException(400, f"Unknown slot '{slot}'")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    # Determine output filename and preset
    if slot:
        # Replacing a system slot → keep the original filename
        out_base = os.path.splitext(SYSTEM_SLOTS[slot]["filename"])[0]
        active_preset = SYSTEM_SLOTS[slot]["preset"]
    elif custom_name:
        safe = re.sub(r'[^\w\-. ]', '', custom_name).strip() or (file.filename or "upload")
        out_base = os.path.splitext(safe)[0]
        active_preset = preset
    else:
        out_base = os.path.splitext(file.filename or "upload")[0]
        active_preset = preset

    # Normalize force_format: only apply on custom files (slots manage their own format)
    effective_force_fmt = None
    if not slot and force_format and force_format.lower() in ('png', 'jpg', 'jpeg', 'webp'):
        effective_force_fmt = force_format.lower()

    # Optimize
    try:
        optimized, out_ext, final_w, final_h, orig_w, orig_h = _optimize_image(
            content, active_preset, force_fmt=effective_force_fmt
        )
    except Exception as e:
        raise HTTPException(422, f"Image optimization failed: {e}")

    final_filename = out_base + out_ext
    out_path = os.path.join(ASSETS_DIR, final_filename)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1. Write to local disk (immediate serving via /hub/Assets/)
    with open(out_path, 'wb') as f:
        f.write(optimized)
    os.chmod(out_path, 0o644)

    # 2. Write to Object Storage (cross-deployment persistence)
    ext_lower = out_ext.lstrip(".").lower()
    mime_map  = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                 "webp": "image/webp", "gif": "image/gif"}
    mime      = mime_map.get(ext_lower, "image/png")
    obj_key   = f"{_OBJ_PREFIX}/{final_filename}"
    obj_url   = _obj_upload(obj_key, optimized, mime)

    # 3. Update manifest + delete original if this is a replace with a different filename
    manifest = _load_manifest()
    manifest[final_filename] = {
        "obj_url":     obj_url,
        "obj_key":     obj_key,
        "preset":      active_preset,
        "slot":        slot,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_kb":     round(len(optimized) / 1024, 1),
    }
    # Remove the original file when replacing a custom asset that has a different resulting name
    orig_deleted = False
    if original_filename and original_filename != final_filename:
        orig_path = os.path.normpath(os.path.join(ASSETS_DIR, original_filename))
        if orig_path.startswith(os.path.normpath(ASSETS_DIR)) and os.path.isfile(orig_path):
            os.remove(orig_path)
            orig_deleted = True
            print(f"[WA] replace: deleted original '{original_filename}' → new '{final_filename}'")
        manifest.pop(original_filename, None)
    _save_manifest(manifest)

    orig_kb = round(len(content) / 1024, 1)
    new_kb  = round(len(optimized) / 1024, 1)

    _out_path  = os.path.join(ASSETS_DIR, final_filename)
    _url_mtime = int(os.stat(_out_path).st_mtime) if os.path.isfile(_out_path) else int(datetime.now(timezone.utc).timestamp())
    return {
        "ok":               True,
        "filename":         final_filename,
        "url":              f"/hub/Assets/{final_filename.replace(' ', '%20')}?v={_url_mtime}",
        "obj_url":          obj_url,
        "cloud_synced":     bool(obj_url),
        "preset":           active_preset,
        "slot":             slot,
        "original":         {"w": orig_w, "h": orig_h, "kb": orig_kb},
        "optimized":        {"w": final_w, "h": final_h, "kb": new_kb},
        "reduction_pct":    round((1 - new_kb / orig_kb) * 100, 1) if orig_kb > 0 else 0,
        "placements":       _scan_placements(final_filename),
        "replaced":         bool(original_filename),
        "original_deleted": orig_deleted,
    }


# ─── DELETE ──────────────────────────────────────────────────────────────────

@router.delete("/vgk/hub/assets/{filename:path}")
async def delete_asset(filename: str, current_user=Depends(_require_hub_admin)):
    slot_files = {v["filename"] for v in SYSTEM_SLOTS.values()}
    if filename in slot_files:
        raise HTTPException(403, f"'{filename}' is a system slot file. Upload a replacement instead of deleting.")

    fpath = os.path.normpath(os.path.join(ASSETS_DIR, filename))
    if not fpath.startswith(os.path.normpath(ASSETS_DIR)):
        raise HTTPException(400, "Invalid path")
    if not os.path.isfile(fpath):
        raise HTTPException(404, f"File '{filename}' not found")

    os.remove(fpath)

    # Remove from manifest (so fresh-container sync won't re-download deleted file)
    manifest = _load_manifest()
    if filename in manifest:
        manifest.pop(filename)
        _save_manifest(manifest)

    return {"ok": True, "deleted": filename}


# ─── SCAN SINGLE FILE ────────────────────────────────────────────────────────

@router.get("/vgk/hub/assets/scan/{filename:path}")
async def scan_file_placements(filename: str, current_user=Depends(_require_hub_admin)):
    return {"filename": filename, "placements": _scan_placements(filename)}
