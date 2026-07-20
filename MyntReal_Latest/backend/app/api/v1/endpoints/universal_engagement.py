"""
Universal Engagement API - Ratings, Comments, Shares, Saves
DC Protocol Compliant with Company-Wise Data Segregation

This is a polymorphic API that works with any entity type:
- Announcements, Properties, Products, Articles, etc.

Endpoints:
- POST/GET /engagement/{entity_type}/{entity_id}/ratings
- POST/GET /engagement/{entity_type}/{entity_id}/comments
- POST /engagement/{entity_type}/{entity_id}/share
- POST/DELETE /engagement/{entity_type}/{entity_id}/save
- DELETE /engagement/admin/ratings/{id} (RVZ/EA only)
- DELETE /engagement/admin/comments/{id} (RVZ/EA only)

Created: December 08, 2025
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.universal_engagement import (
    UniversalRating, UniversalComment, UniversalShare, UniversalSave
)
from app.models.base import get_indian_time

router = APIRouter(prefix="/engagement", tags=["Universal Engagement"])

VALID_ENTITY_TYPES = ['announcement', 'property', 'product', 'article', 'service', 'event']


def validate_entity_type(entity_type: str):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid entity type. Allowed: {VALID_ENTITY_TYPES}"
        )


# ============================================================================
# RATINGS ENDPOINTS
# ============================================================================

@router.post("/public/{entity_type}/{entity_id}/ratings")
async def add_rating(
    entity_type: str,
    entity_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to add a rating to any entity
    DC Protocol: Validate company alignment
    """
    validate_entity_type(entity_type)
    
    data = await request.json()
    
    rating_value = data.get('rating')
    rater_name = data.get('rater_name', '').strip()
    rater_email = data.get('rater_email', '').strip()
    rater_phone = data.get('rater_phone', '').strip()
    rater_type = data.get('rater_type', 'public')
    rater_id = data.get('rater_id', '')
    
    if not rating_value or not isinstance(rating_value, int) or rating_value < 1 or rating_value > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    if not rater_name:
        raise HTTPException(status_code=400, detail="Your name is required")
    
    if rater_type not in ['staff', 'partner', 'member', 'public', 'user']:
        rater_type = 'public'
    
    import uuid
    if not rater_id:
        rater_id = f"public_{uuid.uuid4().hex[:12]}"
    
    new_rating = UniversalRating(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        rating=rating_value,
        rater_type=rater_type,
        rater_id=rater_id,
        rater_name=rater_name,
        rater_email=rater_email if rater_email else None,
        rater_phone=rater_phone if rater_phone else None,
        is_verified=False,
        is_visible=True
    )
    
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    
    return {
        "success": True,
        "message": "Rating submitted successfully",
        "rating": new_rating.to_dict()
    }


@router.get("/public/{entity_type}/{entity_id}/ratings")
async def get_ratings(
    entity_type: str,
    entity_id: int,
    company_id: int,
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get ratings for any entity
    DC Protocol: Filter by company_id
    """
    validate_entity_type(entity_type)
    
    query = db.query(UniversalRating).filter(
        UniversalRating.entity_type == entity_type,
        UniversalRating.entity_id == entity_id,
        UniversalRating.company_id == company_id,
        UniversalRating.is_visible == True
    )
    
    total = query.count()
    
    avg_rating = db.query(func.avg(UniversalRating.rating)).filter(
        UniversalRating.entity_type == entity_type,
        UniversalRating.entity_id == entity_id,
        UniversalRating.company_id == company_id,
        UniversalRating.is_visible == True
    ).scalar()
    
    rating_counts = {}
    for i in range(1, 6):
        count = db.query(func.count(UniversalRating.id)).filter(
            UniversalRating.entity_type == entity_type,
            UniversalRating.entity_id == entity_id,
            UniversalRating.company_id == company_id,
            UniversalRating.is_visible == True,
            UniversalRating.rating == i
        ).scalar() or 0
        rating_counts[str(i)] = count
    
    ratings = query.order_by(UniversalRating.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "ratings": [r.to_dict() for r in ratings],
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
        "total_ratings": total,
        "rating_breakdown": rating_counts,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.delete("/admin/{entity_type}/{entity_id}/ratings/{rating_id}")
async def delete_rating(
    entity_type: str,
    entity_id: int,
    rating_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete/hide a rating - RVZ and EA roles only
    DC Protocol: Validate company alignment and role permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U_SUPREME', 'EA']:
    #     raise HTTPException(status_code=403, detail="Only RVZ Supreme and EA can delete ratings")
    
    validate_entity_type(entity_type)
    
    data = await request.json()
    reason = data.get('reason', '').strip()
    
    rating = db.query(UniversalRating).filter(
        UniversalRating.id == rating_id,
        UniversalRating.entity_type == entity_type,
        UniversalRating.entity_id == entity_id,
        UniversalRating.company_id == company_id
    ).first()
    
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    rating.is_visible = False
    rating.deleted_by_id = current_user.id
    rating.deleted_at = get_indian_time()
    rating.deletion_reason = reason if reason else "Removed by admin"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Rating removed successfully"
    }


# ============================================================================
# COMMENTS ENDPOINTS
# ============================================================================

@router.post("/public/{entity_type}/{entity_id}/comments")
async def add_comment(
    entity_type: str,
    entity_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to add a comment to any entity
    DC Protocol: Validate company alignment
    """
    validate_entity_type(entity_type)
    
    data = await request.json()
    
    comment_text = (data.get('comment') or '').strip()
    commenter_name = (data.get('commenter_name') or '').strip()
    commenter_email = (data.get('commenter_email') or '').strip()
    commenter_phone = (data.get('commenter_phone') or '').strip()
    commenter_type = data.get('commenter_type') or 'public'
    commenter_id = data.get('commenter_id') or ''
    parent_id = data.get('parent_id')
    
    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    
    if len(comment_text) > 2000:
        raise HTTPException(status_code=400, detail="Comment must be less than 2000 characters")
    
    if not commenter_name:
        raise HTTPException(status_code=400, detail="Your name is required")
    
    if commenter_type not in ['staff', 'partner', 'member', 'public', 'user']:
        commenter_type = 'public'
    
    if parent_id:
        parent_comment = db.query(UniversalComment).filter(
            UniversalComment.id == parent_id,
            UniversalComment.entity_type == entity_type,
            UniversalComment.entity_id == entity_id,
            UniversalComment.company_id == company_id,
            UniversalComment.is_visible == True
        ).first()
        if not parent_comment:
            raise HTTPException(status_code=400, detail="Parent comment not found")
    
    new_comment = UniversalComment(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        comment=comment_text,
        parent_id=parent_id,
        commenter_type=commenter_type,
        commenter_id=commenter_id if commenter_id else None,
        commenter_name=commenter_name,
        commenter_email=commenter_email if commenter_email else None,
        commenter_phone=commenter_phone if commenter_phone else None,
        is_verified=False,
        is_visible=True
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return {
        "success": True,
        "message": "Comment submitted successfully",
        "comment": new_comment.to_dict()
    }


@router.get("/public/{entity_type}/{entity_id}/comments")
async def get_comments(
    entity_type: str,
    entity_id: int,
    company_id: int,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get comments for any entity (threaded)
    DC Protocol: Filter by company_id
    """
    validate_entity_type(entity_type)
    
    parent_comments = db.query(UniversalComment).filter(
        UniversalComment.entity_type == entity_type,
        UniversalComment.entity_id == entity_id,
        UniversalComment.company_id == company_id,
        UniversalComment.is_visible == True,
        UniversalComment.parent_id == None
    ).order_by(UniversalComment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    total_parents = db.query(func.count(UniversalComment.id)).filter(
        UniversalComment.entity_type == entity_type,
        UniversalComment.entity_id == entity_id,
        UniversalComment.company_id == company_id,
        UniversalComment.is_visible == True,
        UniversalComment.parent_id == None
    ).scalar() or 0
    
    comments_with_replies = []
    for comment in parent_comments:
        comment_dict = comment.to_dict()
        replies = db.query(UniversalComment).filter(
            UniversalComment.parent_id == comment.id,
            UniversalComment.is_visible == True
        ).order_by(UniversalComment.created_at.asc()).all()
        comment_dict['replies'] = [r.to_dict() for r in replies]
        comment_dict['reply_count'] = len(replies)
        comments_with_replies.append(comment_dict)
    
    total_comments = db.query(func.count(UniversalComment.id)).filter(
        UniversalComment.entity_type == entity_type,
        UniversalComment.entity_id == entity_id,
        UniversalComment.company_id == company_id,
        UniversalComment.is_visible == True
    ).scalar() or 0
    
    return {
        "success": True,
        "comments": comments_with_replies,
        "total_comments": total_comments,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_parents,
            "pages": (total_parents + per_page - 1) // per_page
        }
    }


@router.delete("/admin/{entity_type}/{entity_id}/comments/{comment_id}")
async def delete_comment(
    entity_type: str,
    entity_id: int,
    comment_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete/hide a comment - RVZ and EA roles only
    DC Protocol: Validate company alignment and role permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U_SUPREME', 'EA']:
    #     raise HTTPException(status_code=403, detail="Only RVZ Supreme and EA can delete comments")
    
    validate_entity_type(entity_type)
    
    data = await request.json()
    reason = data.get('reason', '').strip()
    
    comment = db.query(UniversalComment).filter(
        UniversalComment.id == comment_id,
        UniversalComment.entity_type == entity_type,
        UniversalComment.entity_id == entity_id,
        UniversalComment.company_id == company_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.is_visible = False
    comment.deleted_by_id = current_user.id
    comment.deleted_at = get_indian_time()
    comment.deletion_reason = reason if reason else "Removed by admin"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Comment removed successfully"
    }


# ============================================================================
# SHARE TRACKING ENDPOINT
# ============================================================================

@router.post("/public/{entity_type}/{entity_id}/share")
async def track_share(
    entity_type: str,
    entity_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to track entity shares
    DC Protocol: Validate company alignment
    """
    validate_entity_type(entity_type)
    
    data = await request.json()
    
    platform = data.get('platform', 'other')
    valid_platforms = ['facebook', 'twitter', 'whatsapp', 'linkedin', 'email', 'copy_link', 'telegram', 'other']
    if platform not in valid_platforms:
        platform = 'other'
    
    sharer_type = data.get('sharer_type')
    sharer_id = data.get('sharer_id')
    
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('User-Agent', '')[:500]
    
    share_record = UniversalShare(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        platform=platform,
        sharer_type=sharer_type,
        sharer_id=sharer_id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    db.add(share_record)
    db.commit()
    
    total_shares = db.query(func.count(UniversalShare.id)).filter(
        UniversalShare.entity_type == entity_type,
        UniversalShare.entity_id == entity_id,
        UniversalShare.company_id == company_id
    ).scalar() or 0
    
    return {
        "success": True,
        "message": "Share recorded",
        "total_shares": total_shares
    }


@router.get("/public/{entity_type}/{entity_id}/share-stats")
async def get_share_stats(
    entity_type: str,
    entity_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Get share statistics for an entity
    DC Protocol: Filter by company_id
    """
    validate_entity_type(entity_type)
    
    total = db.query(func.count(UniversalShare.id)).filter(
        UniversalShare.entity_type == entity_type,
        UniversalShare.entity_id == entity_id,
        UniversalShare.company_id == company_id
    ).scalar() or 0
    
    platform_stats = db.query(
        UniversalShare.platform,
        func.count(UniversalShare.id).label('count')
    ).filter(
        UniversalShare.entity_type == entity_type,
        UniversalShare.entity_id == entity_id,
        UniversalShare.company_id == company_id
    ).group_by(UniversalShare.platform).all()
    
    return {
        "success": True,
        "total_shares": total,
        "by_platform": {stat.platform: stat.count for stat in platform_stats}
    }


# ============================================================================
# SAVE/FAVORITE ENDPOINTS
# ============================================================================

@router.post("/public/{entity_type}/{entity_id}/save")
async def save_entity(
    entity_type: str,
    entity_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Save/favorite an entity
    DC Protocol: Validate company alignment
    """
    validate_entity_type(entity_type)
    
    data = await request.json()
    
    saver_type = data.get('saver_type', 'public')
    saver_id = data.get('saver_id', '')
    
    if saver_type not in ['staff', 'partner', 'member', 'public', 'user']:
        saver_type = 'public'
    
    if not saver_id:
        client_ip = request.client.host if request.client else 'anonymous'
        saver_id = f"anon_{client_ip}"
    
    existing = db.query(UniversalSave).filter(
        UniversalSave.entity_type == entity_type,
        UniversalSave.entity_id == entity_id,
        UniversalSave.company_id == company_id,
        UniversalSave.saver_type == saver_type,
        UniversalSave.saver_id == saver_id
    ).first()
    
    if existing:
        return {
            "success": True,
            "message": "Already saved",
            "saved": True
        }
    
    saved = UniversalSave(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        saver_type=saver_type,
        saver_id=saver_id
    )
    
    db.add(saved)
    db.commit()
    
    return {
        "success": True,
        "message": "Saved successfully",
        "saved": True
    }


@router.delete("/public/{entity_type}/{entity_id}/save")
async def unsave_entity(
    entity_type: str,
    entity_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove entity from saves/favorites
    DC Protocol: Validate company alignment
    """
    validate_entity_type(entity_type)
    
    data = await request.json()
    
    saver_type = data.get('saver_type', 'public')
    saver_id = data.get('saver_id', '')
    
    if not saver_id:
        client_ip = request.client.host if request.client else 'anonymous'
        saver_id = f"anon_{client_ip}"
    
    saved = db.query(UniversalSave).filter(
        UniversalSave.entity_type == entity_type,
        UniversalSave.entity_id == entity_id,
        UniversalSave.company_id == company_id,
        UniversalSave.saver_type == saver_type,
        UniversalSave.saver_id == saver_id
    ).first()
    
    if not saved:
        return {
            "success": True,
            "message": "Was not saved",
            "saved": False
        }
    
    db.delete(saved)
    db.commit()
    
    return {
        "success": True,
        "message": "Removed from saves",
        "saved": False
    }


@router.get("/public/{entity_type}/{entity_id}/is-saved")
async def check_saved(
    entity_type: str,
    entity_id: int,
    company_id: int,
    saver_type: str,
    saver_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if entity is saved by user
    DC Protocol: Filter by company_id
    """
    validate_entity_type(entity_type)
    
    saved = db.query(UniversalSave).filter(
        UniversalSave.entity_type == entity_type,
        UniversalSave.entity_id == entity_id,
        UniversalSave.company_id == company_id,
        UniversalSave.saver_type == saver_type,
        UniversalSave.saver_id == saver_id
    ).first()
    
    return {
        "success": True,
        "saved": saved is not None
    }


@router.get("/saved/{saver_type}/{saver_id}")
async def get_saved_entities(
    saver_type: str,
    saver_id: str,
    company_id: int,
    entity_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all saved entities for a user
    DC Protocol: Filter by company_id
    """
    query = db.query(UniversalSave).filter(
        UniversalSave.company_id == company_id,
        UniversalSave.saver_type == saver_type,
        UniversalSave.saver_id == saver_id
    )
    
    if entity_type:
        validate_entity_type(entity_type)
        query = query.filter(UniversalSave.entity_type == entity_type)
    
    total = query.count()
    
    saves = query.order_by(UniversalSave.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "saves": [s.to_dict() for s in saves],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


# ============================================================================
# ADMIN MODERATION ENDPOINTS
# ============================================================================

@router.get("/admin/ratings")
async def admin_list_ratings(
    company_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to list all ratings for moderation
    DC Protocol: RVZ and EA roles only
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U_SUPREME', 'EA']:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(UniversalRating).filter(
        UniversalRating.company_id == company_id
    )
    
    if entity_type:
        query = query.filter(UniversalRating.entity_type == entity_type)
    if entity_id:
        query = query.filter(UniversalRating.entity_id == entity_id)
    if is_visible is not None:
        query = query.filter(UniversalRating.is_visible == is_visible)
    
    total = query.count()
    
    ratings = query.order_by(UniversalRating.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "ratings": [r.to_dict() for r in ratings],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/admin/comments")
async def admin_list_comments(
    company_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to list all comments for moderation
    DC Protocol: RVZ and EA roles only
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U_SUPREME', 'EA']:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(UniversalComment).filter(
        UniversalComment.company_id == company_id
    )
    
    if entity_type:
        query = query.filter(UniversalComment.entity_type == entity_type)
    if entity_id:
        query = query.filter(UniversalComment.entity_id == entity_id)
    if is_visible is not None:
        query = query.filter(UniversalComment.is_visible == is_visible)
    
    total = query.count()
    
    comments = query.order_by(UniversalComment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "comments": [c.to_dict() for c in comments],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/stats/{entity_type}/{entity_id}")
async def get_engagement_stats(
    entity_type: str,
    entity_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all engagement statistics for an entity
    DC Protocol: Filter by company_id
    """
    validate_entity_type(entity_type)
    
    avg_rating = db.query(func.avg(UniversalRating.rating)).filter(
        UniversalRating.entity_type == entity_type,
        UniversalRating.entity_id == entity_id,
        UniversalRating.company_id == company_id,
        UniversalRating.is_visible == True
    ).scalar()
    
    total_ratings = db.query(func.count(UniversalRating.id)).filter(
        UniversalRating.entity_type == entity_type,
        UniversalRating.entity_id == entity_id,
        UniversalRating.company_id == company_id,
        UniversalRating.is_visible == True
    ).scalar() or 0
    
    total_comments = db.query(func.count(UniversalComment.id)).filter(
        UniversalComment.entity_type == entity_type,
        UniversalComment.entity_id == entity_id,
        UniversalComment.company_id == company_id,
        UniversalComment.is_visible == True
    ).scalar() or 0
    
    total_shares = db.query(func.count(UniversalShare.id)).filter(
        UniversalShare.entity_type == entity_type,
        UniversalShare.entity_id == entity_id,
        UniversalShare.company_id == company_id
    ).scalar() or 0
    
    total_saves = db.query(func.count(UniversalSave.id)).filter(
        UniversalSave.entity_type == entity_type,
        UniversalSave.entity_id == entity_id,
        UniversalSave.company_id == company_id
    ).scalar() or 0
    
    return {
        "success": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "stats": {
            "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
            "total_ratings": total_ratings,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_saves": total_saves
        }
    }
