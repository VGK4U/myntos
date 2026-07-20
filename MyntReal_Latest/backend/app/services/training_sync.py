"""
DC_TRAINING_SYNC_001: Google Doc sync service for the Training Videos system.
Fetches training video list from a public Google Doc, parses "N. Title - URL" lines,
and upserts into the training_videos table.
Called at startup, every hour via APScheduler, and on admin manual trigger.
"""
import re
import logging
import requests
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)

GDOC_EXPORT_URL = (
    "https://docs.google.com/document/d/1RPYZUlO3xLNlSGwh4s4UZlg0a-wa_-sAVW2mhTLM5H8"
    "/export?format=txt"
)


def _extract_youtube_id(url: str):
    """
    Return (video_id, is_short) from any YouTube URL format.
    Handles: youtu.be/, /shorts/, watch?v=, /embed/
    Returns (None, False) on failure.
    """
    url = url.strip().rstrip(")")
    m = re.search(r'youtube\.com/shorts/([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1), True
    m = re.search(r'youtu\.be/([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1), False
    m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1), False
    m = re.search(r'youtube\.com/embed/([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1), False
    return None, False


def sync_training_videos_from_gdoc(db=None):
    """
    Fetch Google Doc, parse video list, upsert into training_videos table.
    Safe to call from any context (scheduler, startup, API handler).
    When db=None, creates and closes its own session.
    Returns dict: {added, updated, deactivated, total, error?}
    """
    from app.core.database import SessionLocal

    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        resp = requests.get(GDOC_EXPORT_URL, timeout=20)
        resp.raise_for_status()
        content = resp.text

        # Parse lines: "N. Title - URL" (handles ASCII hyphen, en-dash –, em-dash —)
        pattern = re.compile(
            r'^\s*(\d+)\.\s+(.+?)\s*[-\u2013\u2014]\s*(https?://\S+)',
            re.MULTILINE
        )
        matches = pattern.findall(content)

        if not matches:
            logger.warning("[DC_TRAINING_SYNC_001] No video entries found in Google Doc")
            return {"added": 0, "updated": 0, "deactivated": 0, "total": 0}

        now = datetime.utcnow()
        active_order_nums = set()
        added = 0
        updated = 0

        for order_str, title, url in matches:
            order_num = int(order_str.strip())
            title = title.strip()
            url = url.strip().rstrip(")")

            video_id, is_short = _extract_youtube_id(url)
            if not video_id:
                logger.warning(f"[DC_TRAINING_SYNC_001] Cannot extract video ID from: {url}")
                continue

            active_order_nums.add(order_num)

            existing = db.execute(
                text("SELECT id FROM training_videos WHERE order_num = :n"),
                {"n": order_num}
            ).fetchone()

            if existing:
                db.execute(text("""
                    UPDATE training_videos
                       SET title            = :title,
                           youtube_url      = :url,
                           youtube_video_id = :vid,
                           is_short         = :is_short,
                           is_active        = true,
                           synced_at        = :now,
                           updated_at       = :now
                     WHERE order_num = :n
                """), {"title": title, "url": url, "vid": video_id,
                       "is_short": is_short, "now": now, "n": order_num})
                updated += 1
            else:
                db.execute(text("""
                    INSERT INTO training_videos
                        (order_num, title, youtube_url, youtube_video_id,
                         is_short, is_active, synced_at, created_at, updated_at)
                    VALUES (:n, :title, :url, :vid, :is_short, true, :now, :now, :now)
                """), {"n": order_num, "title": title, "url": url, "vid": video_id,
                       "is_short": is_short, "now": now})
                added += 1

        # Deactivate rows no longer in doc — preserves completion history
        deactivated = 0
        if active_order_nums:
            nums_str = ",".join(str(n) for n in sorted(active_order_nums))
            result = db.execute(text(f"""
                UPDATE training_videos
                   SET is_active  = false,
                       updated_at = :now
                 WHERE order_num NOT IN ({nums_str})
                   AND is_active  = true
            """), {"now": now})
            deactivated = result.rowcount if hasattr(result, 'rowcount') else 0

        db.commit()
        total = added + updated
        logger.info(
            f"[DC_TRAINING_SYNC_001] ✅ Synced {total} videos "
            f"(added={added}, updated={updated}, deactivated={deactivated})"
        )
        return {"added": added, "updated": updated, "deactivated": deactivated, "total": total}

    except Exception as e:
        logger.error(f"[DC_TRAINING_SYNC_001] Sync failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {"error": str(e), "added": 0, "updated": 0, "deactivated": 0, "total": 0}
    finally:
        if own_db:
            db.close()
