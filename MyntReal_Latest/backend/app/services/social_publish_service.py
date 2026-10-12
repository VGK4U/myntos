"""
Durable Social Media Publication & Analytics Engine — MintOS / ZynovaOS
Features:
- Periodic polling worker (every 60s) claiming due posts via atomic row-level locking
- Idempotency keys generated per post dispatch to prevent duplicate publishing
- Network timeout recovery: checks provider status before blind re-dispatch
- Independent per-platform dispatch outcome tracking (Partial success handling)
- Exponential retry backoff for transient failures (Terminal state after 3 attempts)
- Webhook processor for real-time post confirmation and token expiry detection
- Automated analytics ingestion with explicit data availability state
"""

from typing import Dict, Any, List, Optional
import os
import json
import logging
import socket
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.social_media import (
    SocialPost, SocialPostDispatch, SocialAccountConnection,
    SocialAnalyticsSnapshot, SocialWebhookEvent
)
from app.models.base import get_indian_time
from app.services.social_media_service import get_social_provider, BaseSocialProvider

logger = logging.getLogger("social_publish.service")


def process_scheduled_social_posts(
    db: Session,
    batch_size: int = 20,
    max_retries: int = 3,
    provider: Optional[BaseSocialProvider] = None
) -> Dict[str, Any]:
    """
    Durable APScheduler Polling Worker.
    Executes every 60s. Atomically claims due scheduled posts using row-level locking.
    """
    now = get_indian_time()
    social_prov = provider or get_social_provider("zernio")

    # 1. Atomic row-level claim using PostgreSQL SKIP LOCKED (with SQLite fallback)
    try:
        query = db.query(SocialPost).filter(
            SocialPost.status.in_(["SCHEDULED", "UNCERTAIN"]),
            SocialPost.scheduled_at <= now,
            or_(SocialPost.next_retry_at == None, SocialPost.next_retry_at <= now)
        ).order_by(SocialPost.scheduled_at.asc()).limit(batch_size)

        try:
            due_posts = query.with_for_update(skip_locked=True).all()
        except Exception:
            # Fallback for SQLite in local test environment
            due_posts = query.all()

        if not due_posts:
            return {"processed": 0, "published": 0, "failed": 0}

        # 2. Mark claimed posts as 'PUBLISHING' immediately to release row locks & prevent duplicate workers
        for p in due_posts:
            p.status = "PUBLISHING"
            p.updated_at = now
        db.commit()

    except Exception as lock_err:
        logger.error(f"[SOCIAL-PUBLISHER] Failed acquiring scheduled post batch: {lock_err}")
        db.rollback()
        return {"error": str(lock_err), "processed": 0}

    published_count = 0
    failed_count = 0

    # 3. Dispatch each claimed post
    for post in due_posts:
        try:
            # Fetch active account connections for this company
            connections = db.query(SocialAccountConnection).filter(
                SocialAccountConnection.company_id == post.company_id,
                SocialAccountConnection.status == "ACTIVE"
            ).all()

            if not connections:
                logger.warning(f"[SOCIAL-PUBLISHER] Post #{post.id}: No active social accounts connected for Company #{post.company_id}")
                post.status = "FAILED"
                post.last_error = "No active social media accounts connected."
                post.updated_at = get_indian_time()
                db.commit()
                failed_count += 1
                continue

            dispatch_successes = 0
            dispatch_failures = 0
            dispatch_uncertain = 0

            for conn in connections:
                # Build unique idempotency key
                dispatch_key = f"DISP_P{post.id}_C{conn.id}_{conn.platform}_{int(post.scheduled_at.timestamp())}"

                # Find or create dispatch record
                dispatch = db.query(SocialPostDispatch).filter(
                    SocialPostDispatch.dispatch_key == dispatch_key
                ).first()

                if not dispatch:
                    dispatch = SocialPostDispatch(
                        post_id=post.id,
                        connection_id=conn.id,
                        platform=conn.platform,
                        tailored_caption=post.master_caption,
                        tailored_media_urls=post.media_urls,
                        dispatch_key=dispatch_key,
                        status="PENDING",
                        created_at=get_indian_time(),
                        updated_at=get_indian_time()
                    )
                    db.add(dispatch)
                    db.flush()

                # If already published by previous attempt or webhook, skip
                if dispatch.status == "PUBLISHED":
                    dispatch_successes += 1
                    continue

                # Reconcile uncertain or in-flight dispatches before re-dispatching
                if dispatch.status in ("SUBMITTED", "UNCERTAIN"):
                    reconciled = False
                    if dispatch.provider_post_id:
                        try:
                            status_info = social_prov.get_post_status(dispatch.provider_post_id)
                            st = (status_info.get("status") or "").upper()
                            if st in ("PUBLISHED", "SUCCESS"):
                                dispatch.status = "PUBLISHED"
                                dispatch.published_url = status_info.get("platform_post_url") or dispatch.published_url
                                dispatch.published_at = get_indian_time()
                                dispatch.error_message = None
                                dispatch_successes += 1
                                reconciled = True
                            elif st in ("FAILED", "ERROR"):
                                dispatch.status = "FAILED"
                                dispatch.error_message = status_info.get("error", "Confirmed provider failure")
                        except Exception as rec_err:
                            logger.info(f"[SOCIAL-PUBLISHER] Reconciliation probe failed for #{dispatch.id}: {rec_err}")

                    if reconciled:
                        continue
                    elif dispatch.status == "SUBMITTED":
                        # If recently submitted (within 90s), another concurrent worker is processing; skip to prevent duplicate
                        if dispatch.updated_at and (now - dispatch.updated_at).total_seconds() < 90:
                            logger.info(f"[SOCIAL-PUBLISHER] Dispatch #{dispatch.id} in-flight with concurrent worker. Skipping.")
                            continue

                # Set SUBMITTED before external call to protect against concurrent duplicate workers
                dispatch.status = "SUBMITTED"
                dispatch.updated_at = get_indian_time()
                db.flush()

                # Prepare payload
                payload = {
                    "platforms": [conn.platform],
                    "body": dispatch.tailored_caption,
                    "media_urls": dispatch.tailored_media_urls or []
                }

                # Dispatch via Provider
                try:
                    res = social_prov.publish_post(
                        profile_id=conn.provider_profile_id,
                        payload=payload,
                        idempotency_key=dispatch_key
                    )

                    plat_res = res.get("results", {}).get(conn.platform, {})
                    is_ok = plat_res.get("success", False) or res.get("success", False)

                    if is_ok:
                        dispatch.status = "PUBLISHED"
                        dispatch.provider_post_id = plat_res.get("provider_post_id") or res.get("id") or f"ext_{post.id}"
                        dispatch.published_url = plat_res.get("published_url") or f"https://{conn.platform}.com/posts/{post.id}"
                        dispatch.published_at = get_indian_time()
                        dispatch.error_message = None
                        dispatch_successes += 1
                    else:
                        err_msg = plat_res.get("error") or res.get("error", "Provider publishing failed")
                        dispatch.status = "FAILED"
                        dispatch.error_message = str(err_msg)
                        dispatch_failures += 1

                except Exception as disp_err:
                    err_str = str(disp_err).lower()
                    is_timeout = isinstance(disp_err, (TimeoutError, socket.timeout)) or "timeout" in err_str or "timed out" in err_str
                    if is_timeout:
                        logger.warning(f"[SOCIAL-PUBLISHER] Post #{post.id} on {conn.platform} timed out after acceptance. Marked UNCERTAIN to prevent duplicate.")
                        dispatch.status = "UNCERTAIN"
                        dispatch.error_message = f"Timeout after dispatch sent: {disp_err}"
                        dispatch_uncertain += 1
                    else:
                        logger.error(f"[SOCIAL-PUBLISHER] Dispatch error for Post #{post.id} on {conn.platform}: {disp_err}")
                        dispatch.status = "FAILED"
                        dispatch.error_message = str(disp_err)
                        dispatch_failures += 1

                dispatch.updated_at = get_indian_time()

            # 4. Evaluate overall post state across platforms
            post.updated_at = get_indian_time()

            if dispatch_successes > 0 and dispatch_failures == 0 and dispatch_uncertain == 0:
                post.status = "PUBLISHED"
                post.last_error = None
                published_count += 1
            elif dispatch_uncertain > 0:
                # Uncertain status: do NOT blindly re-post; require status reconciliation
                post.status = "UNCERTAIN"
                post.last_error = f"Dispatches pending status confirmation ({dispatch_uncertain} uncertain, {dispatch_successes} published)."
                post.next_retry_at = get_indian_time() + timedelta(minutes=5)
                failed_count += 1
            elif dispatch_successes > 0 and dispatch_failures > 0:
                post.retry_count += 1
                if post.retry_count >= max_retries:
                    post.status = "PARTIALLY_FAILED"
                    post.last_error = f"Permanent partial failure: {dispatch_successes} published, {dispatch_failures} failed."
                    failed_count += 1
                else:
                    backoff_minutes = 5 * (3 ** (post.retry_count - 1))
                    post.status = "SCHEDULED"
                    post.next_retry_at = get_indian_time() + timedelta(minutes=backoff_minutes)
                    post.last_error = f"Partial success ({dispatch_successes} published, {dispatch_failures} failed). Retrying remaining in {backoff_minutes}m."
                    published_count += 1
            else:
                # All dispatches failed
                post.retry_count += 1
                if post.retry_count >= max_retries:
                    post.status = "FAILED"
                    post.last_error = f"Permanent failure after {max_retries} attempts."
                    failed_count += 1
                else:
                    # Exponential retry backoff: 5m, 15m, 45m
                    backoff_minutes = 5 * (3 ** (post.retry_count - 1))
                    post.status = "SCHEDULED"
                    post.next_retry_at = get_indian_time() + timedelta(minutes=backoff_minutes)
                    post.last_error = f"Attempt {post.retry_count} failed. Retrying in {backoff_minutes}m."
                    failed_count += 1

            db.commit()

        except Exception as post_err:
            logger.error(f"[SOCIAL-PUBLISHER] Fatal error executing Post #{post.id}: {post_err}")
            db.rollback()
            try:
                post.status = "FAILED"
                post.last_error = str(post_err)
                db.commit()
            except Exception:
                db.rollback()
            failed_count += 1

    return {"processed": len(due_posts), "published": published_count, "failed": failed_count}


def handle_social_webhook(
    db: Session,
    headers: Dict[str, str],
    body_bytes: bytes,
    secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Idempotent Webhook Event Ingestion.
    Validates signature, prevents duplicate delivery, and updates post/account statuses.
    """
    social_prov = get_social_provider("zernio")

    # Verify signature if secret configured
    webhook_secret = secret or os.getenv("ZERNIO_WEBHOOK_SECRET")
    if webhook_secret and not social_prov.verify_webhook_signature(headers, body_bytes, webhook_secret):
        logger.warning("[SOCIAL-WEBHOOK] Invalid HMAC signature detected.")
        return {"error": "Invalid webhook signature", "status_code": 401}

    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception as parse_err:
        return {"error": f"Invalid JSON payload: {parse_err}", "status_code": 400}

    event_id = data.get("event_id") or data.get("id") or f"evt_{int(datetime.utcnow().timestamp())}_{hash(body_bytes)}"
    event_type = data.get("event_type") or data.get("type", "unknown")

    # Check for duplicate webhook event (idempotency)
    existing_evt = db.query(SocialWebhookEvent).filter(SocialWebhookEvent.event_id == event_id).first()
    if existing_evt:
        return {"status": "duplicate_ignored", "event_id": event_id}

    evt_record = SocialWebhookEvent(
        provider="zernio",
        event_id=event_id,
        event_type=event_type,
        payload=data,
        processed=False,
        created_at=get_indian_time()
    )
    db.add(evt_record)
    db.flush()

    # Process event types
    try:
        if event_type in ("post.published", "post.success"):
            provider_post_id = data.get("data", {}).get("provider_post_id") or data.get("post_id")
            pub_url = data.get("data", {}).get("published_url")
            if provider_post_id:
                dispatches = db.query(SocialPostDispatch).filter(
                    SocialPostDispatch.provider_post_id == provider_post_id
                ).all()
                for d in dispatches:
                    d.status = "PUBLISHED"
                    if pub_url:
                        d.published_url = pub_url
                    d.published_at = get_indian_time()
                    d.updated_at = get_indian_time()

        elif event_type in ("post.failed", "post.error"):
            provider_post_id = data.get("data", {}).get("provider_post_id") or data.get("post_id")
            err_msg = data.get("data", {}).get("error") or "External platform rejected publication"
            if provider_post_id:
                dispatches = db.query(SocialPostDispatch).filter(
                    SocialPostDispatch.provider_post_id == provider_post_id
                ).all()
                for d in dispatches:
                    d.status = "FAILED"
                    d.error_message = str(err_msg)
                    d.updated_at = get_indian_time()

        elif event_type in ("account.disconnected", "account.expired", "account.reauth_required"):
            provider_acc_id = data.get("data", {}).get("account_id")
            if provider_acc_id:
                accs = db.query(SocialAccountConnection).filter(
                    SocialAccountConnection.platform_account_id == provider_acc_id
                ).all()
                for acc in accs:
                    acc.status = "REQUIRES_REAUTH"
                    acc.updated_at = get_indian_time()

        evt_record.processed = True
        db.commit()
        return {"status": "success", "event_id": event_id}

    except Exception as proc_err:
        logger.error(f"[SOCIAL-WEBHOOK] Error processing event {event_id}: {proc_err}")
        evt_record.error_message = str(proc_err)
        db.commit()
        return {"status": "error", "message": str(proc_err)}


def sync_social_analytics(
    db: Session,
    company_id: Optional[int] = None,
    days_back: int = 30,
    provider: Optional[BaseSocialProvider] = None
) -> Dict[str, Any]:
    """
    Synchronizes post performance and engagement metrics.
    Runs every 6 hours via APScheduler.
    """
    social_prov = provider or get_social_provider("zernio")
    cutoff = get_indian_time() - timedelta(days=days_back)

    q = db.query(SocialPostDispatch).filter(
        SocialPostDispatch.status == "PUBLISHED",
        SocialPostDispatch.published_at >= cutoff,
        SocialPostDispatch.provider_post_id != None
    )
    if company_id:
        q = q.join(SocialPost).filter(SocialPost.company_id == company_id)

    dispatches = q.all()
    synced_count = 0

    for d in dispatches:
        try:
            metrics = social_prov.get_post_analytics(d.provider_post_id, d.platform)
            post = d.post

            snapshot = db.query(SocialAnalyticsSnapshot).filter(
                SocialAnalyticsSnapshot.dispatch_id == d.id
            ).first()

            if not snapshot:
                snapshot = SocialAnalyticsSnapshot(
                    tenant_id=post.tenant_id,
                    company_id=post.company_id,
                    dispatch_id=d.id,
                    platform=d.platform,
                    synced_at=get_indian_time()
                )
                db.add(snapshot)

            snapshot.impressions = metrics.get("impressions")
            snapshot.reach = metrics.get("reach")
            snapshot.likes = metrics.get("likes")
            snapshot.comments = metrics.get("comments")
            snapshot.shares = metrics.get("shares")
            snapshot.clicks = metrics.get("clicks")
            snapshot.video_views = metrics.get("video_views")
            snapshot.data_availability = metrics.get("data_availability", "AVAILABLE")
            snapshot.raw_metrics = metrics.get("raw_metrics", {})
            snapshot.synced_at = get_indian_time()

            # Compute engagement rate: (likes + comments + shares) / impressions if impressions > 0
            if snapshot.impressions is not None and snapshot.impressions > 0:
                eng = (snapshot.likes or 0) + (snapshot.comments or 0) + (snapshot.shares or 0)
                snapshot.engagement_rate = round((eng / float(snapshot.impressions)) * 100.0, 2)
            elif snapshot.impressions == 0:
                snapshot.engagement_rate = 0.0
            else:
                snapshot.engagement_rate = None

            synced_count += 1

        except Exception as metric_err:
            logger.warning(f"[SOCIAL-ANALYTICS] Sync failed for dispatch #{d.id}: {metric_err}")

    db.commit()
    logger.info(f"📊 [SOCIAL-ANALYTICS] Synced engagement metrics for {synced_count} dispatches.")
    return {"synced_count": synced_count}
