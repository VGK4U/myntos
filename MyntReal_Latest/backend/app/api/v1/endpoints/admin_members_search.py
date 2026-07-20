from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime, date
import csv
import io

from app.core.database import get_db
from app.core.security import get_current_admin_user_hybrid
from app.models.user import User
from app.constants import PACKAGE_POINTS_MAP

router = APIRouter(prefix="/admin/members", tags=["Admin Members Search"])


@router.get("/search")
async def search_all_members(
    user_id: Optional[str] = Query(None, description="Search by MNR ID (partial match)"),
    name: Optional[str] = Query(None, description="Search by member name (partial match)"),
    sponsor_id: Optional[str] = Query(None, description="Filter by sponsor/referrer ID (exact match)"),
    ved_owner_id: Optional[str] = Query(None, description="Filter by Ved Owner ID (exact match)"),
    join_date_start: Optional[str] = Query(None, description="Joining date start (YYYY-MM-DD)"),
    join_date_end: Optional[str] = Query(None, description="Joining date end (YYYY-MM-DD)"),
    activation_date_start: Optional[str] = Query(None, description="Activation date start (YYYY-MM-DD)"),
    activation_date_end: Optional[str] = Query(None, description="Activation date end (YYYY-MM-DD)"),
    package: Optional[str] = Query(None, description="Filter by package (Platinum, Diamond, Blue, Loyal)"),
    account_status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    coupon_status: Optional[str] = Query(None, description="Filter by coupon status"),
    format: Optional[str] = Query("json", description="Response format (json or csv)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Results per page"),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Admin Members Search - System-wide member search with dynamic filters
    
    Access: Admin, Super Admin, Finance Admin, RVZ ID
    CSV Export: RVZ ID only
    
    This endpoint searches ALL members in the system (not just downline).
    Supports multiple filters for flexible member lookup.
    
    DC Protocol: Reads from user table (single source of truth)
    """
    try:
        # CSV export restricted to RVZ only
        if format == "csv":
            if (getattr(current_user, "staff_type", None) or getattr(current_user, "user_type", "")) != "RVZ ID":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSV export is restricted to RVZ ID role only"
                )
        # Start with base query
        query = db.query(User)
        
        # Apply filters
        if user_id and user_id.strip():
            # Partial match on user ID (case-insensitive)
            query = query.filter(User.id.ilike(f"%{user_id.strip()}%"))
        
        if name and name.strip():
            # Partial match on name (case-insensitive)
            query = query.filter(User.name.ilike(f"%{name.strip()}%"))
        
        if sponsor_id and sponsor_id.strip():
            # Exact match on sponsor/referrer ID
            query = query.filter(User.referrer_id == sponsor_id.strip())
        
        if ved_owner_id and ved_owner_id.strip():
            # Exact match on Ved Owner ID
            query = query.filter(User.ved_owner_id == ved_owner_id.strip())
        
        if package and package.strip():
            # Filter by package type using package_points
            package_upper = package.strip().upper()
            # Find the points value for this package name
            points_value = None
            for points, pkg_name in PACKAGE_POINTS_MAP.items():
                if pkg_name == package_upper:
                    points_value = points
                    break
            if points_value is not None:
                query = query.filter(User.package_points == points_value)
        
        if account_status and account_status.strip():
            # Filter by active/inactive status
            if account_status.lower() == 'active':
                query = query.filter(User.activation_date.isnot(None))
            elif account_status.lower() == 'inactive':
                query = query.filter(User.activation_date.is_(None))
        
        if coupon_status and coupon_status.strip():
            # Filter by coupon status
            query = query.filter(User.coupon_status == coupon_status.strip())
        
        # Date range filters for joining date (registration_date)
        if join_date_start:
            try:
                start_dt = datetime.fromisoformat(join_date_start)
                query = query.filter(User.registration_date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid join_date_start format: {join_date_start}"
                )
        
        if join_date_end:
            try:
                end_dt = datetime.fromisoformat(join_date_end)
                query = query.filter(User.registration_date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid join_date_end format: {join_date_end}"
                )
        
        # Date range filters for activation date
        if activation_date_start:
            try:
                start_dt = datetime.fromisoformat(activation_date_start)
                query = query.filter(User.activation_date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid activation_date_start format: {activation_date_start}"
                )
        
        if activation_date_end:
            try:
                end_dt = datetime.fromisoformat(activation_date_end)
                query = query.filter(User.activation_date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid activation_date_end format: {activation_date_end}"
                )
        
        # Get total count before pagination
        total_count = query.count()
        
        # For CSV export, get all results (no pagination)
        if format == "csv":
            members = query.order_by(User.registration_date.desc()).all()
        else:
            # Apply pagination for JSON
            offset = (page - 1) * page_size
            members = query.order_by(User.registration_date.desc()).offset(offset).limit(page_size).all()
        
        # Format response data
        members_data = []
        for member in members:
            # Get ved owner name if exists
            ved_owner_name = None
            if member.ved_owner_id:
                ved_owner = db.query(User).filter(User.id == member.ved_owner_id).first()
                if ved_owner:
                    ved_owner_name = ved_owner.name
            
            # Get package name from package_points using PACKAGE_POINTS_MAP
            package_name = PACKAGE_POINTS_MAP.get(member.package_points, "Not Activated") if member.activation_date else "Not Activated"
            
            members_data.append({
                "mnr_id": member.id,
                "name": member.name,
                "email": member.email,
                "phone": member.phone_number,
                "package": package_name,
                "status": "Active" if member.activation_date else "Inactive",
                "is_active": member.activation_date is not None,
                "join_date": member.registration_date.isoformat() if member.registration_date else None,
                "activation_date": member.activation_date.isoformat() if member.activation_date else None,
                "referrer_id": member.referrer_id,
                "ved_owner_id": member.ved_owner_id,
                "ved_owner_name": ved_owner_name,
                "coupon_status": member.coupon_status,
                "user_type": member.user_type
            })
        
        # Return CSV if requested
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write CSV headers
            writer.writerow([
                'MNR ID', 'Name', 'Email', 'Phone', 'Package', 'Status',
                'Join Date', 'Activation Date', 'Referrer ID', 'Ved Owner ID',
                'Ved Owner Name', 'Coupon Status', 'User Type'
            ])
            
            # Write data rows
            for member_data in members_data:
                writer.writerow([
                    member_data['mnr_id'],
                    member_data['name'],
                    member_data['email'] or '',
                    member_data['phone'] or '',
                    member_data['package'],
                    member_data['status'],
                    member_data['join_date'] or '',
                    member_data['activation_date'] or '',
                    member_data['referrer_id'] or '',
                    member_data['ved_owner_id'] or '',
                    member_data['ved_owner_name'] or '',
                    member_data['coupon_status'] or '',
                    member_data['user_type'] or ''
                ])
            
            # Prepare CSV response
            output.seek(0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"members_export_{timestamp}.csv"
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        # Return JSON response
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "success": True,
            "data": {
                "members": members_data,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "message": f"Found {total_count} member(s) matching filters"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search members: {str(e)}"
        )


@router.get("/autocomplete")
async def autocomplete_members(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    field: str = Query(..., description="Field to search (user_id, name, sponsor_id, ved_owner_id)"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Autocomplete Suggestions for Member Search
    
    Access: Admin, Super Admin, Finance Admin, RVZ ID
    
    Returns matching suggestions based on field type:
    - user_id: Matches MNR IDs
    - name: Matches member names
    - sponsor_id: Matches sponsor/referrer IDs
    - ved_owner_id: Matches Ved Owner IDs
    
    Returns up to 'limit' suggestions with ID and label for display.
    """
    try:
        suggestions = []
        
        if field == "user_id":
            # Search by MNR ID (partial match)
            users = db.query(User.id, User.name).filter(
                User.id.ilike(f"%{q}%")
            ).limit(limit).all()
            
            suggestions = [
                {"value": user.id, "label": f"{user.id} - {user.name}"}
                for user in users
            ]
        
        elif field == "name":
            # Search by name (partial match)
            users = db.query(User.id, User.name).filter(
                User.name.ilike(f"%{q}%")
            ).limit(limit).all()
            
            suggestions = [
                {"value": user.id, "label": f"{user.name} ({user.id})"}
                for user in users
            ]
        
        elif field == "sponsor_id":
            # Search for users who are sponsors (have referrals)
            # Get distinct referrer_ids that match the query
            referrers = db.query(User.id, User.name).filter(
                User.id.ilike(f"%{q}%")
            ).limit(limit).all()
            
            suggestions = [
                {"value": user.id, "label": f"{user.id} - {user.name}"}
                for user in referrers
            ]
        
        elif field == "ved_owner_id":
            # Search for Ved Owners
            ved_owners = db.query(User.id, User.name).filter(
                User.id.ilike(f"%{q}%")
            ).limit(limit).all()
            
            suggestions = [
                {"value": user.id, "label": f"{user.id} - {user.name}"}
                for user in ved_owners
            ]
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field: {field}. Must be one of: user_id, name, sponsor_id, ved_owner_id"
            )
        
        return {
            "success": True,
            "data": suggestions,
            "total": len(suggestions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autocomplete failed: {str(e)}"
        )
