"""
Social Media Manager API Endpoints — MintOS / ZynovaOS
Prefix: /social
Tags: ["Social Media Manager"]

Provides:
- Company-isolated Overview & Stats
- Social Account Connection & Revocation
- Content Calendar Query & AI Generation (15 bi-daily posts)
- Post CRUD, Inline Editing & Platform Customization
- Approval & Scheduling State Machine
- Optional Selective AI Image Generation
- Normalized Engagement Analytics Dashboard
- Webhook Ingestion with HMAC Verification
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from sqlalchemy.exc import ProgrammingError, OperationalError
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
import logging

from app.core.database import get_db
from app.api.deps import get_request_context
from app.core.context import RequestContext
from app.core.authorization import (
    assert_company_access, assert_resource_tenant, assert_module_entitlement,
    is_platform_superadmin
)
from app.models.social_media import (
    SocialAccountConnection, SocialCalendarSetting, SocialPost,
    SocialPostDispatch, SocialAnalyticsSnapshot, SocialWebhookEvent
)
from app.models.base import get_indian_time
from app.services.social_media_service import get_social_provider
from app.services.social_ai_service import SocialAIService
from app.services.social_publish_service import (
    process_scheduled_social_posts, handle_social_webhook, sync_social_analytics
)

logger = logging.getLogger("social_media.api")

router = APIRouter(prefix="/social", tags=["Social Media Manager"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper Guard & Tenant Resolution
# ─────────────────────────────────────────────────────────────────────────────
def _is_missing_table_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "does not exist" in msg or "no such table" in msg or "undefinedtable" in msg


def _resolve_company_id(ctx: RequestContext, requested_company_id: Optional[int] = None) -> int:
    if isinstance(requested_company_id, int) and requested_company_id != ctx.active_company_id:
        assert_company_access(ctx, requested_company_id)
        return requested_company_id
    return ctx.active_company_id


def _enforce_social_access(ctx: RequestContext):
    """Validates user has access to Social Media Manager."""
    # Platform superadmin always has access
    if is_platform_superadmin(ctx):
        return
    # Check module entitlement if configured
    try:
        assert_module_entitlement(ctx, "SOCIAL_MEDIA_MANAGER")
    except HTTPException:
        # If not explicitly licensed but user is company admin, grant evaluation access
        if ctx.hierarchy_level < 60:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Social Media Manager module is not licensed or permitted for your role."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ConnectUrlRequest(BaseModel):
    platform: str = Field(..., description="facebook, instagram, linkedin, twitter, youtube, threads")
    redirect_uri: Optional[str] = None


class MockConnectRequest(BaseModel):
    platform: str
    account_name: Optional[str] = None
    account_username: Optional[str] = None
    account_handle: Optional[str] = None


class CalendarGenerateRequest(BaseModel):
    start_date: Optional[date] = None
    custom_instructions: Optional[str] = None


class PostCreateRequest(BaseModel):
    topic_theme: str
    master_caption: str
    scheduled_at: datetime
    master_hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    media_type: Optional[str] = "image"
    platform_captions: Optional[Dict[str, str]] = None
    call_to_action_url: Optional[str] = None
    call_to_action_text: Optional[str] = None


class PostUpdateRequest(BaseModel):
    topic_theme: Optional[str] = None
    master_caption: Optional[str] = None
    master_hashtags: Optional[List[str]] = None
    call_to_action_url: Optional[str] = None
    call_to_action_text: Optional[str] = None
    media_urls: Optional[List[str]] = None
    media_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    platform_captions: Optional[Dict[str, str]] = None # {"linkedin": "...", "twitter": "..."}


class CalendarSettingsUpdateRequest(BaseModel):
    posting_frequency_days: Optional[int] = 2
    preferred_time_ist: Optional[str] = "10:30"
    brand_voice: Optional[str] = None
    target_audience: Optional[str] = None
    content_themes: Optional[List[str]] = None
    default_hashtags: Optional[List[str]] = None
    helpline_phone: Optional[str] = None
    website_url: Optional[str] = None
    enabled_platforms: Optional[List[str]] = None
    require_admin_approval: Optional[bool] = True


# ─────────────────────────────────────────────────────────────────────────────
# 1. Accessible Companies & Tenant Filtering
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/companies")
def list_accessible_companies(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Returns list of companies accessible to current user for tenant filtering."""
    _enforce_social_access(ctx)
    companies = []
    
    try:
        from app.models.associated_company import AssociatedCompany
        if is_platform_superadmin(ctx):
            comps = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
        else:
            acc_ids = ctx.accessible_company_ids or [ctx.active_company_id]
            comps = db.query(AssociatedCompany).filter(
                AssociatedCompany.id.in_(acc_ids),
                AssociatedCompany.is_active == True
            ).all()
        for c in comps:
            companies.append({
                "id": c.id,
                "name": getattr(c, "company_name", None) or getattr(c, "name", f"Company #{c.id}"),
                "code": getattr(c, "company_code", str(c.id))
            })
    except Exception as e:
        logger.warning(f"Could not load associated companies: {e}")

    if not companies:
        known = {
            1: "Mynt Real LLP",
            2: "Zynova Mobility",
            3: "Mega Natural Resources (MNR)",
            4: "Suryanz Solar",
            88: "VGK4U Platform"
        }
        allowed = ctx.accessible_company_ids if not is_platform_superadmin(ctx) else list(known.keys())
        for cid in (allowed or [ctx.active_company_id]):
            companies.append({
                "id": cid,
                "name": known.get(cid, f"Company #{cid}"),
                "code": f"C{cid}"
            })

    return {
        "status": "success",
        "active_company_id": ctx.active_company_id,
        "companies": companies
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Overview Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/overview")
def get_social_overview(
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Aggregates high-level metrics, connection status, and upcoming posts for active company."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)

    try:
        # Accounts
        accounts = db.query(SocialAccountConnection).filter(
            SocialAccountConnection.company_id == cid
        ).all()
        active_accounts = [a for a in accounts if a.status == "ACTIVE"]

        # Posts counts
        posts_q = db.query(SocialPost).filter(SocialPost.company_id == cid)
        drafts_count = posts_q.filter(SocialPost.status == "DRAFT").count()
        pending_approval_count = posts_q.filter(SocialPost.status == "PENDING_APPROVAL").count()
        scheduled_count = posts_q.filter(SocialPost.status == "SCHEDULED").count()
        published_count = posts_q.filter(SocialPost.status.in_(["PUBLISHED", "PARTIALLY_FAILED"])).count()
        failed_count = posts_q.filter(SocialPost.status == "FAILED").count()

        # Total reach & impressions
        ana_totals = db.query(
            func.coalesce(func.sum(SocialAnalyticsSnapshot.impressions), 0).label("tot_impr"),
            func.coalesce(func.sum(SocialAnalyticsSnapshot.reach), 0).label("tot_reach"),
            func.coalesce(func.sum(SocialAnalyticsSnapshot.likes), 0).label("tot_likes"),
            func.coalesce(func.sum(SocialAnalyticsSnapshot.comments), 0).label("tot_comments")
        ).filter(SocialAnalyticsSnapshot.company_id == cid).first()

        # Upcoming 5 scheduled posts
        upcoming = posts_q.filter(
            SocialPost.status.in_(["SCHEDULED", "APPROVED", "DRAFT"])
        ).order_by(SocialPost.scheduled_at.asc()).limit(5).all()

        return {
            "status": "success",
            "company_id": cid,
            "connected_accounts_count": len(active_accounts),
            "accounts_summary": [a.to_dict() for a in accounts],
            "posts_summary": {
                "drafts": drafts_count,
                "pending_approval": pending_approval_count,
                "scheduled": scheduled_count,
                "published": published_count,
                "failed": failed_count,
                "total_planned": drafts_count + pending_approval_count + scheduled_count + published_count
            },
            "engagement_summary": {
                "total_impressions": int(ana_totals.tot_impr) if ana_totals else 0,
                "total_reach": int(ana_totals.tot_reach) if ana_totals else 0,
                "total_likes": int(ana_totals.tot_likes) if ana_totals else 0,
                "total_comments": int(ana_totals.tot_comments) if ana_totals else 0
            },
            "upcoming_posts": [p.to_dict(include_dispatches=False) for p in upcoming]
        }
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            logger.warning(f"[SOCIAL-MEDIA] Database tables not migrated yet: {exc}")
            return {
                "status": "migration_pending",
                "company_id": cid,
                "message": "Database tables have not been created yet. Run 'alembic upgrade head' to apply migration.",
                "connected_accounts_count": 0,
                "accounts_summary": [],
                "posts_summary": {"drafts": 0, "pending_approval": 0, "scheduled": 0, "published": 0, "failed": 0, "total_planned": 0},
                "engagement_summary": {"total_impressions": 0, "total_reach": 0, "total_likes": 0, "total_comments": 0},
                "upcoming_posts": []
            }
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 3. Account Connections
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/accounts")
def list_accounts(
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """List all social media accounts connected to this company."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)
    try:
        accounts = db.query(SocialAccountConnection).filter(
            SocialAccountConnection.company_id == cid
        ).order_by(SocialAccountConnection.id.asc()).all()
        return {"status": "success", "company_id": cid, "accounts": [a.to_dict() for a in accounts]}
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            return {"status": "migration_pending", "company_id": cid, "accounts": []}
        raise


@router.post("/accounts/connect-url")
def get_connect_url(
    req: ConnectUrlRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Generates hosted OAuth connection link for the company to link its social profile."""
    _enforce_social_access(ctx)
    social_prov = get_social_provider("zernio")

    setting = db.query(SocialCalendarSetting).filter(
        SocialCalendarSetting.company_id == ctx.active_company_id
    ).first()

    if not setting:
        setting = SocialCalendarSetting(
            tenant_id=ctx.tenant_id,
            company_id=ctx.active_company_id,
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        db.add(setting)
        db.flush()

    if setting.provider_profile_id:
        profile_id = setting.provider_profile_id
    else:
        prof = social_prov.create_or_get_profile(
            company_id=ctx.active_company_id,
            company_name=f"Company #{ctx.active_company_id}",
            tenant_id=ctx.tenant_id
        )
        profile_id = prof.get("profile_id") or f"prof_{ctx.active_company_id}"
        setting.provider_profile_id = profile_id
        setting.updated_at = get_indian_time()
        db.commit()

    redirect = req.redirect_uri or "/staff/configuration/social-media?connected=1"
    state = f"state_t{ctx.tenant_id}_c{ctx.active_company_id}_{int(get_indian_time().timestamp())}"

    url = social_prov.generate_connect_url(
        profile_id=profile_id,
        platform=req.platform.lower(),
        redirect_uri=redirect,
        state=state
    )

    return {
        "status": "success",
        "platform": req.platform,
        "connect_url": url,
        "profile_id": profile_id
    }


@router.post("/accounts/mock-connect")
def mock_connect_account(
    req: MockConnectRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Local Testing & Demo: Links a realistic mock social account to the active company."""
    _enforce_social_access(ctx)
    cid = ctx.active_company_id
    tid = ctx.tenant_id

    plat = req.platform.lower()
    plat_acc_id = f"mock_{plat}_{cid}_{int(get_indian_time().timestamp())}"

    icons = {
        "facebook": "https://cdn-icons-png.flaticon.com/512/124/124010.png",
        "instagram": "https://cdn-icons-png.flaticon.com/512/2111/2111463.png",
        "linkedin": "https://cdn-icons-png.flaticon.com/512/174/174857.png",
        "twitter": "https://cdn-icons-png.flaticon.com/512/3256/3256013.png"
    }

    acc_name = req.account_name or f"{plat.capitalize()} Channel"
    acc_uname = req.account_username or req.account_handle or f"@{acc_name.lower().replace(' ', '')}"

    acc = SocialAccountConnection(
        tenant_id=tid,
        company_id=cid,
        platform=plat,
        platform_account_id=plat_acc_id,
        account_name=acc_name,
        account_username=acc_uname,
        profile_image_url=icons.get(plat, "https://cdn-icons-png.flaticon.com/512/124/124010.png"),
        provider_profile_id=f"zernio_prof_t{tid}_c{cid}",
        status="ACTIVE",
        capabilities=["publish_post", "publish_video", "insights"],
        last_synced_at=get_indian_time(),
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    db.add(acc)

    setting = db.query(SocialCalendarSetting).filter(SocialCalendarSetting.company_id == cid).first()
    if not setting:
        setting = SocialCalendarSetting(
            tenant_id=tid,
            company_id=cid,
            provider_profile_id=f"zernio_prof_t{tid}_c{cid}",
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        db.add(setting)
    elif not setting.provider_profile_id:
        setting.provider_profile_id = f"zernio_prof_t{tid}_c{cid}"

    db.commit()
    db.refresh(acc)

    return {"status": "success", "platform": plat, "message": f"{acc_name} connected successfully!", "account": acc.to_dict()}


@router.delete("/accounts/{account_id}")
def disconnect_account(
    account_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Disconnects and revokes account connection (strictly tenant-isolated)."""
    _enforce_social_access(ctx)
    acc = db.query(SocialAccountConnection).filter(
        SocialAccountConnection.id == account_id,
        SocialAccountConnection.company_id == ctx.active_company_id
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Social account not found.")

    social_prov = get_social_provider("zernio")
    social_prov.disconnect_account(acc.provider_profile_id, acc.platform, acc.platform_account_id)

    db.delete(acc)
    db.commit()
    return {"status": "success", "message": f"Account {acc.account_name} disconnected."}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Calendar Settings
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/settings")
def get_calendar_settings(
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Fetch company calendar preferences."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)
    try:
        setting = db.query(SocialCalendarSetting).filter(
            SocialCalendarSetting.company_id == cid
        ).first()
        if not setting:
            setting = SocialCalendarSetting(
                tenant_id=ctx.tenant_id,
                company_id=cid,
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            db.add(setting)
            db.commit()
            db.refresh(setting)
        return {"status": "success", "company_id": cid, "settings": setting.to_dict()}
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            return {"status": "migration_pending", "company_id": cid, "settings": {}}
        raise


@router.put("/settings")
def update_calendar_settings(
    req: CalendarSettingsUpdateRequest,
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Update company calendar preferences."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)
    try:
        setting = db.query(SocialCalendarSetting).filter(
            SocialCalendarSetting.company_id == cid
        ).first()
        if not setting:
            setting = SocialCalendarSetting(tenant_id=ctx.tenant_id, company_id=cid)
            db.add(setting)

        for field, val in req.dict(exclude_unset=True).items():
            setattr(setting, field, val)

        setting.updated_at = get_indian_time()
        db.commit()
        db.refresh(setting)
        return {"status": "success", "company_id": cid, "settings": setting.to_dict()}
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=503,
                detail="Database tables have not been created yet. Run 'alembic upgrade head' to apply migration."
            )
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 4. Content Calendar & AI Generation
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/calendar")
def get_calendar_posts(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Query scheduled, draft, and published posts in date range for active company."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)

    try:
        q = db.query(SocialPost).filter(SocialPost.company_id == cid)

        month_val = month if isinstance(month, int) else None
        year_val = year if isinstance(year, int) else None
        start_date_val = start_date if isinstance(start_date, str) else None
        end_date_val = end_date if isinstance(end_date, str) else None

        if month_val and year_val:
            import calendar as py_calendar
            _, last_day = py_calendar.monthrange(year_val, month_val)
            start_dt = datetime(year_val, month_val, 1, 0, 0, 0)
            end_dt = datetime(year_val, month_val, last_day, 23, 59, 59)
            q = q.filter(SocialPost.scheduled_at >= start_dt, SocialPost.scheduled_at <= end_dt)
        else:
            if start_date_val:
                try:
                    sd = datetime.fromisoformat(start_date_val)
                    q = q.filter(SocialPost.scheduled_at >= sd)
                except Exception:
                    pass

            if end_date_val:
                try:
                    ed = datetime.fromisoformat(end_date_val)
                    q = q.filter(SocialPost.scheduled_at <= ed)
                except Exception:
                    pass

        if isinstance(status, str) and status.upper() != "ALL":
            q = q.filter(SocialPost.status == status.upper())

        posts = q.order_by(SocialPost.scheduled_at.asc()).all()
        return {"status": "success", "company_id": cid, "posts": [p.to_dict(include_dispatches=True) for p in posts]}
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            logger.warning(f"[SOCIAL-MEDIA] Database tables not migrated yet: {exc}")
            return {
                "status": "migration_pending",
                "company_id": cid,
                "message": "Database tables have not been created yet. Run 'alembic upgrade head' to apply migration.",
                "posts": []
            }
        raise


@router.post("/calendar/generate-ai")
def generate_ai_calendar(
    req: CalendarGenerateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Generates 15 bi-daily planned posts over a 30-day period in DRAFT mode."""
    _enforce_social_access(ctx)
    ai_service = SocialAIService()

    posts = ai_service.generate_monthly_calendar(
        db=db,
        company_id=ctx.active_company_id,
        tenant_id=ctx.tenant_id,
        start_date=req.start_date,
        custom_instructions=req.custom_instructions,
        staff_id=ctx.staff_id
    )

    return {
        "status": "success",
        "message": f"Successfully generated {len(posts)} draft posts across the 30-day period.",
        "posts": [p.to_dict(include_dispatches=False) for p in posts]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Post Editing, Approval & State Machine
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/posts")
def create_single_post(
    req: PostCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Creates a new ad-hoc draft social post with optional tailored platform copy."""
    _enforce_social_access(ctx)
    post = SocialPost(
        tenant_id=ctx.tenant_id,
        company_id=ctx.active_company_id,
        topic_theme=req.topic_theme,
        master_caption=req.master_caption,
        master_hashtags=req.master_hashtags or [],
        media_urls=req.media_urls or [],
        media_type=req.media_type or "image",
        scheduled_at=req.scheduled_at,
        call_to_action_url=req.call_to_action_url,
        call_to_action_text=req.call_to_action_text,
        status="DRAFT",
    )
    db.add(post)
    db.flush()

    if req.platform_captions:
        for plat, cap in req.platform_captions.items():
            if not cap:
                continue
            conn = db.query(SocialAccountConnection).filter(
                SocialAccountConnection.company_id == ctx.active_company_id,
                SocialAccountConnection.platform.in_([plat, "twitter" if plat == "x" else plat])
            ).first()
            if conn:
                disp_key = f"DISP_P{post.id}_C{conn.id}_{plat}_{int(post.scheduled_at.timestamp())}"
                disp = SocialPostDispatch(
                    post_id=post.id,
                    connection_id=conn.id,
                    platform=plat,
                    tailored_caption=cap,
                    tailored_media_urls=post.media_urls or [],
                    dispatch_key=disp_key,
                    status="PENDING",
                    created_at=get_indian_time(),
                    updated_at=get_indian_time()
                )
                db.add(disp)

    db.commit()
    db.refresh(post)
    return {"status": "success", "post": post.to_dict(include_dispatches=True)}


@router.get("/posts/{post_id}")
def get_post_detail(
    post_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Get single post details with platform dispatches."""
    _enforce_social_access(ctx)
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.company_id == ctx.active_company_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return {"status": "success", "post": post.to_dict(include_dispatches=True)}


@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    req: PostUpdateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Updates post captions, scheduled time, hashtags, and platform variations."""
    _enforce_social_access(ctx)
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.company_id == ctx.active_company_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.status in ("PUBLISHING", "PUBLISHED"):
        raise HTTPException(status_code=400, detail="Cannot edit a post that is currently publishing or already published.")

    for field, val in req.dict(exclude_unset=True).items():
        if field == "platform_captions" and val:
            for plat, cap in val.items():
                if not cap:
                    continue
                disp = db.query(SocialPostDispatch).filter(
                    SocialPostDispatch.post_id == post.id,
                    SocialPostDispatch.platform.in_([plat, "twitter" if plat == "x" else plat])
                ).first()
                if disp:
                    disp.tailored_caption = cap
                    disp.updated_at = get_indian_time()
                else:
                    conn = db.query(SocialAccountConnection).filter(
                        SocialAccountConnection.company_id == ctx.active_company_id,
                        SocialAccountConnection.platform.in_([plat, "twitter" if plat == "x" else plat])
                    ).first()
                    if conn:
                        disp_key = f"DISP_P{post.id}_C{conn.id}_{plat}_{int(post.scheduled_at.timestamp())}"
                        new_disp = SocialPostDispatch(
                            post_id=post.id,
                            connection_id=conn.id,
                            platform=plat,
                            tailored_caption=cap,
                            tailored_media_urls=post.media_urls or [],
                            dispatch_key=disp_key,
                            status="PENDING",
                            created_at=get_indian_time(),
                            updated_at=get_indian_time()
                        )
                        db.add(new_disp)
        elif hasattr(post, field) and val is not None:
            setattr(post, field, val)

    post.updated_at = get_indian_time()
    db.commit()
    db.refresh(post)
    return {"status": "success", "message": "Post updated successfully.", "post": post.to_dict(include_dispatches=True)}


@router.post("/sandbox/init-demo")
def initialize_sandbox_demo(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Initializes realistic sandbox demo: links mock accounts (FB, IG, LI, X) and generates 15 authentic bi-daily draft posts."""
    _enforce_social_access(ctx)
    cid = ctx.active_company_id
    tid = ctx.tenant_id

    platforms = [
        {"platform": "facebook", "name": "Facebook Official Page", "handle": "@official_brand"},
        {"platform": "instagram", "name": "Instagram Business", "handle": "@official_brand_ig"},
        {"platform": "linkedin", "name": "LinkedIn Corporate", "handle": "@company_hub"},
        {"platform": "x", "name": "X Official", "handle": "@brand_x"}
    ]
    icons = {
        "facebook": "https://cdn-icons-png.flaticon.com/512/124/124010.png",
        "instagram": "https://cdn-icons-png.flaticon.com/512/2111/2111463.png",
        "linkedin": "https://cdn-icons-png.flaticon.com/512/174/174857.png",
        "twitter": "https://cdn-icons-png.flaticon.com/512/3256/3256013.png",
        "x": "https://cdn-icons-png.flaticon.com/512/3256/3256013.png"
    }

    connected_count = 0
    for p in platforms:
        plat = p["platform"]
        existing = db.query(SocialAccountConnection).filter(
            SocialAccountConnection.company_id == cid,
            SocialAccountConnection.platform.in_([plat, "twitter" if plat == "x" else plat])
        ).first()
        if not existing:
            acc = SocialAccountConnection(
                tenant_id=tid,
                company_id=cid,
                platform=plat,
                platform_account_id=f"sandbox_{plat}_{cid}",
                account_name=p["name"],
                account_username=p["handle"],
                profile_image_url=icons.get(plat),
                provider_profile_id=f"zernio_prof_t{tid}_c{cid}",
                status="ACTIVE",
                capabilities=["publish_post", "publish_video", "insights"],
                last_synced_at=get_indian_time(),
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            db.add(acc)
            connected_count += 1

    posts_count = db.query(SocialPost).filter(SocialPost.company_id == cid).count()
    created_posts = []
    if posts_count == 0:
        ai_service = SocialAIService()
        created_posts = ai_service.generate_monthly_calendar(
            db=db,
            company_id=cid,
            tenant_id=tid,
            staff_id=ctx.staff_id
        )

    db.commit()
    return {
        "status": "success",
        "message": f"Sandbox initialized! Connected {connected_count} channels and ready with {len(created_posts)} posts.",
        "connected_channels": connected_count,
        "posts_generated": len(created_posts)
    }


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Deletes draft post or cancels scheduled post."""
    _enforce_social_access(ctx)
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.company_id == ctx.active_company_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    if post.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Cannot delete an already published post from dashboard.")

    db.delete(post)
    db.commit()
    return {"status": "success", "message": "Post deleted successfully."}


@router.post("/posts/{post_id}/approve")
def approve_post(
    post_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Transitions post from DRAFT/PENDING_APPROVAL to APPROVED and SCHEDULED."""
    _enforce_social_access(ctx)
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.company_id == ctx.active_company_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    post.status = "SCHEDULED"
    post.approved_by_staff_id = ctx.staff_id
    post.approved_at = get_indian_time()
    post.updated_at = get_indian_time()
    db.commit()
    db.refresh(post)

    return {"status": "success", "message": f"Post approved and scheduled for {post.scheduled_at.strftime('%d %b %Y, %I:%M %p')}.", "post": post.to_dict()}


@router.post("/posts/{post_id}/publish-now")
def publish_post_now(
    post_id: int,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Immediate publishing trigger for an approved post."""
    _enforce_social_access(ctx)
    post = db.query(SocialPost).filter(
        SocialPost.id == post_id,
        SocialPost.company_id == ctx.active_company_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    post.scheduled_at = get_indian_time()
    post.status = "SCHEDULED"
    db.commit()

    # Run dispatch processor
    res = process_scheduled_social_posts(db=db, batch_size=5)
    db.refresh(post)

    return {
        "status": "success",
        "message": f"Publication initiated. Result: {post.status}",
        "post": post.to_dict(include_dispatches=True),
        "dispatch_summary": res
    }


@router.post("/posts/{post_id}/generate-image")
def generate_post_image(
    post_id: int,
    aspect_ratio: str = Query("1:1"),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """OPTIONAL action: Generates a commercial AI image for a single post creative."""
    _enforce_social_access(ctx)
    ai_service = SocialAIService()

    try:
        res = ai_service.generate_single_post_creative(
            db=db,
            post_id=post_id,
            company_id=ctx.active_company_id,
            aspect_ratio=aspect_ratio
        )
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post("/posts/{post_id}/regenerate-caption")
def regenerate_post_caption_endpoint(
    post_id: int,
    tone: str = Query("Professional"),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Regenerates single post caption without touching the rest of the calendar."""
    _enforce_social_access(ctx)
    ai_service = SocialAIService()

    try:
        res = ai_service.regenerate_post_caption(
            db=db,
            post_id=post_id,
            company_id=ctx.active_company_id,
            tone=tone
        )
        return {"status": "success", "post": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Caption regeneration failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Analytics Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/analytics")
def get_social_analytics(
    days: int = Query(30),
    platform: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """Returns aggregated engagement metrics and top performing posts for active company."""
    _enforce_social_access(ctx)
    cid = _resolve_company_id(ctx, company_id)

    try:
        # Sync first to ensure fresh data
        try:
            sync_social_analytics(db=db, company_id=cid, days_back=days)
        except Exception as e:
            logger.warning(f"[SOCIAL-MEDIA] Analytics sync skipped: {e}")

        cutoff = get_indian_time() - timedelta(days=days)

        q = db.query(SocialAnalyticsSnapshot).filter(
            SocialAnalyticsSnapshot.company_id == cid,
            SocialAnalyticsSnapshot.synced_at >= cutoff
        )
        if platform and platform.lower() != "all":
            q = q.filter(SocialAnalyticsSnapshot.platform == platform.lower())

        snapshots = q.all()

        # Calculate platform breakdown preserving genuine 0 vs None (missing/unsupported)
        platform_breakdown = {}
        for s in snapshots:
            p = s.platform
            if p not in platform_breakdown:
                platform_breakdown[p] = {
                    "impressions": None,
                    "reach": None,
                    "likes": None,
                    "comments": None,
                    "shares": None,
                    "clicks": None,
                    "total_snapshots": 0,
                    "availability": s.data_availability
                }
            pb = platform_breakdown[p]
            pb["total_snapshots"] += 1
            if s.data_availability not in ("PENDING_PLATFORM_DATA", "UNSUPPORTED"):
                pb["availability"] = s.data_availability

            for metric in ["impressions", "reach", "likes", "comments", "shares", "clicks"]:
                val = getattr(s, metric)
                if val is not None:
                    pb[metric] = (pb[metric] or 0) + val

        # Top performing dispatches
        top_dispatches = db.query(SocialPostDispatch).join(SocialPost).filter(
            SocialPost.company_id == cid,
            SocialPostDispatch.status == "PUBLISHED"
        ).order_by(SocialPostDispatch.published_at.desc()).limit(10).all()

        return {
            "status": "success",
            "company_id": cid,
            "reporting_period_days": days,
            "total_posts_analyzed": len(snapshots),
            "platform_breakdown": platform_breakdown,
            "recent_published_posts": [
                {
                    "dispatch_id": d.id,
                    "platform": d.platform,
                    "caption": d.tailored_caption[:100] + ("..." if len(d.tailored_caption) > 100 else ""),
                    "published_url": d.published_url,
                    "published_at": d.published_at.isoformat() if d.published_at else None,
                    "metrics": d.analytics.to_dict() if d.analytics else None
                }
                for d in top_dispatches
            ]
        }
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc):
            return {
                "status": "migration_pending",
                "company_id": cid,
                "message": "Database tables have not been created yet.",
                "reporting_period_days": days,
                "total_posts_analyzed": 0,
                "platform_breakdown": {},
                "recent_published_posts": []
            }
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 7. Webhook Receiver
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/webhooks/zernio", include_in_schema=False)
async def zernio_webhook_endpoint(
    request: Request,
    db: Session = Depends(get_db)
):
    """Inbound webhook handler for real-time publishing status and account events."""
    body_bytes = await request.body()
    headers = dict(request.headers)

    res = handle_social_webhook(db=db, headers=headers, body_bytes=body_bytes)
    if "error" in res:
        code = res.get("status_code", 400)
        raise HTTPException(status_code=code, detail=res["error"])

    return res
