"""
Compliance API endpoints for TDS, GST, and Handling Charges tracking
Access: Finance Admin and RVZ only
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.services.compliance_service import ComplianceService
from app.models.transaction import CompanyEarnings
from app.models.user import User

router = APIRouter()


# Request/Response Models
class BulkUpdateRequest(BaseModel):
    """Request model for bulk status updates"""
    record_ids: List[int] = Field(..., description="List of compliance record IDs to update")


class ExportColumnsRequest(BaseModel):
    """Request model for CSV export with column selection"""
    record_type: str = Field(..., description="Type of compliance records: TDS, GST, HANDLING_CHARGE")
    columns: List[str] = Field(..., description="List of columns to include in export")
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    filters: Optional[dict] = None


@router.get("/tds")
async def get_tds_records(
    from_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tally_status: Optional[str] = Query(None, description="Filter by Tally status: UPDATED, NOT_UPDATED"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status: PAID, PENDING"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum gross amount"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum gross amount"),
    sort_by: str = Query("transaction_date", description="Sort by: transaction_date, amount, user_name"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Get TDS compliance records with filters
    User-wise TDS tracking for tax compliance
    """
    try:
        result = ComplianceService.get_tds_records(
            db=db,
            from_date=from_date,
            to_date=to_date,
            user_id=user_id,
            tally_status=tally_status,
            payment_status=payment_status,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TDS records: {str(e)}")


@router.get("/gst")
async def get_gst_records(
    from_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    award_type: Optional[str] = Query(None, description="Filter by award type: Direct Award, Matching Award, Bonanza"),
    tally_status: Optional[str] = Query(None, description="Filter by Tally status: UPDATED, NOT_UPDATED"),
    collection_status: Optional[str] = Query(None, description="Filter by collection status: COLLECTED, PENDING"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum handling charges amount"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum handling charges amount"),
    sort_by: str = Query("transaction_date", description="Sort by: transaction_date, amount, gst_amount"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Get GST compliance records with filters
    Invoice-wise GST tracking for tax compliance
    """
    try:
        result = ComplianceService.get_gst_records(
            db=db,
            from_date=from_date,
            to_date=to_date,
            user_id=user_id,
            award_type=award_type,
            tally_status=tally_status,
            collection_status=collection_status,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching GST records: {str(e)}")


@router.get("/handling-charges")
async def get_handling_charges_records(
    from_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    award_type: Optional[str] = Query(None, description="Filter by award type"),
    tally_status: Optional[str] = Query(None, description="Filter by Tally status"),
    collection_status: Optional[str] = Query(None, description="Filter by collection status"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Get Handling Charges compliance records with filters
    Record-wise handling charges tracking
    """
    try:
        # Use same service as GST but with HANDLING_CHARGE type
        result = ComplianceService.get_gst_records(
            db=db,
            from_date=from_date,
            to_date=to_date,
            user_id=user_id,
            award_type=award_type,
            tally_status=tally_status,
            collection_status=collection_status,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching handling charges records: {str(e)}")


@router.put("/{record_id}/tally-status")
async def update_tally_status(
    record_id: int,
    status: str = Query(..., description="Tally status: UPDATED, PENDING"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Update Tally status for a single compliance record
    """
    try:
        # Validate status
        if status not in ['UPDATED', 'PENDING']:
            raise HTTPException(status_code=400, detail=f"Invalid Tally status: {status}. Must be UPDATED or PENDING")
        
        success = ComplianceService.update_tally_status(
            db=db,
            record_id=record_id,
            updated_by=current_user.id,
            status=status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Compliance record not found")
        
        return {
            "success": True,
            "message": f"Tally status updated to {status}",
            "record_id": record_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating Tally status: {str(e)}")


@router.put("/{record_id}/collection-status")
async def update_collection_status(
    record_id: int,
    status: str = Query(..., description="Collection status: COLLECTED, PENDING"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Update collection status for a single GST/Handling Charge record
    """
    try:
        # Validate status
        if status not in ['COLLECTED', 'PENDING']:
            raise HTTPException(status_code=400, detail=f"Invalid collection status: {status}. Must be COLLECTED or PENDING")
        
        success = ComplianceService.update_collection_status(
            db=db,
            record_id=record_id,
            updated_by=current_user.id,
            status=status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Compliance record not found or invalid type (TDS records cannot have collection status)")
        
        return {
            "success": True,
            "message": f"Collection status updated to {status}",
            "record_id": record_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating collection status: {str(e)}")


@router.put("/{record_id}/payment-status")
async def update_payment_status(
    record_id: int,
    status: str = Query(..., description="Payment status: PAID, PENDING"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Update payment status for a single TDS record
    """
    try:
        # Validate status
        if status not in ['PAID', 'PENDING']:
            raise HTTPException(status_code=400, detail=f"Invalid payment status: {status}. Must be PAID or PENDING")
        
        success = ComplianceService.update_payment_status(
            db=db,
            record_id=record_id,
            updated_by=current_user.id,
            status=status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Compliance record not found or invalid type (GST records cannot have payment status)")
        
        return {
            "success": True,
            "message": f"Payment status updated to {status}",
            "record_id": record_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating payment status: {str(e)}")


@router.post("/bulk-tally-update")
async def bulk_update_tally_status(
    request: BulkUpdateRequest,
    status: str = Query(..., description="Tally status: UPDATED, NOT_UPDATED"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Bulk update Tally status for multiple compliance records
    """
    try:
        # Validate status
        try:
            tally_status = TallyStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid Tally status: {status}")
        
        result = ComplianceService.bulk_update_tally_status(
            db=db,
            record_ids=request.record_ids,
            updated_by=current_user['id'],
            status=tally_status
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk Tally update: {str(e)}")


@router.post("/bulk-collection-update")
async def bulk_update_collection_status(
    request: BulkUpdateRequest,
    status: str = Query(..., description="Collection status: COLLECTED, PENDING"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Bulk update collection status for multiple GST/Handling Charge records
    """
    try:
        # Validate status
        try:
            collection_status = CollectionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid collection status: {status}")
        
        result = ComplianceService.bulk_update_collection_status(
            db=db,
            record_ids=request.record_ids,
            updated_by=current_user['id'],
            status=collection_status
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk collection update: {str(e)}")


@router.post("/export")
async def export_compliance_data(
    request: ExportColumnsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["Finance Admin", "RVZ Admin"]))
):
    """
    Export compliance data to CSV with selected columns
    Returns CSV data as string
    """
    try:
        # Get data based on record type
        if request.record_type == "TDS":
            result = ComplianceService.get_tds_records(
                db=db,
                from_date=request.from_date,
                to_date=request.to_date,
                user_id=request.filters.get('user_id') if request.filters else None,
                tally_status=request.filters.get('tally_status') if request.filters else None,
                payment_status=request.filters.get('payment_status') if request.filters else None,
                page=1,
                limit=10000  # Large limit for export
            )
        elif request.record_type == "GST":
            result = ComplianceService.get_gst_records(
                db=db,
                from_date=request.from_date,
                to_date=request.to_date,
                user_id=request.filters.get('user_id') if request.filters else None,
                award_type=request.filters.get('award_type') if request.filters else None,
                tally_status=request.filters.get('tally_status') if request.filters else None,
                collection_status=request.filters.get('collection_status') if request.filters else None,
                page=1,
                limit=10000
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid record type: {request.record_type}")
        
        # Build CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=request.columns)
        writer.writeheader()
        
        for record in result['records']:
            # Filter only requested columns
            filtered_record = {col: record.get(col, '') for col in request.columns}
            writer.writerow(filtered_record)
        
        csv_data = output.getvalue()
        output.close()
        
        return {
            "success": True,
            "csv_data": csv_data,
            "total_records": len(result['records']),
            "columns": request.columns
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting compliance data: {str(e)}")


@router.get("/company-earnings")
async def get_company_earnings(
    from_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    income_type: Optional[str] = Query(None, description="Filter by income type"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum amount"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles(["RVZ Admin"]))
):
    """
    Get Company Earnings records (RVZ only)
    DC Protocol: Direct query from company_earnings source table
    Shows all company revenue from awards, handling charges, and excess income
    """
    try:
        from sqlalchemy import func, desc
        
        # Build query - DC Protocol: Pull directly from source table
        query = db.query(
            CompanyEarnings,
            User.id.label('username'),  # DC Protocol: User has no username field, use id (MNR ID)
            User.name.label('full_name')
        ).join(
            User, CompanyEarnings.user_id == User.id
        )
        
        # Apply filters
        if from_date:
            query = query.filter(func.date(CompanyEarnings.timestamp) >= from_date)
        if to_date:
            query = query.filter(func.date(CompanyEarnings.timestamp) <= to_date)
        if user_id:
            query = query.filter(CompanyEarnings.user_id == user_id)
        if income_type:
            query = query.filter(CompanyEarnings.income_type == income_type)
        if min_amount:
            query = query.filter(CompanyEarnings.net_company_earnings >= min_amount)
        if max_amount:
            query = query.filter(CompanyEarnings.net_company_earnings <= max_amount)
        
        # Count total
        total_count = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        results = query.order_by(desc(CompanyEarnings.timestamp)).offset(offset).limit(limit).all()
        
        # Format response
        records = []
        for earning, username, full_name in results:
            # Parse description to extract details (handling charges, GST, etc.)
            description_parts = {}
            if earning.description:
                # Example: "Handling charges: ₹500, GST: ₹90, Total: ₹590"
                for part in earning.description.split(','):
                    if ':' in part:
                        key, value = part.split(':', 1)
                        description_parts[key.strip()] = value.strip()
            
            records.append({
                "id": earning.id,
                "user_id": earning.user_id,
                "username": username,
                "full_name": full_name,
                "original_amount": float(earning.original_amount or 0),
                "excess_amount": float(earning.excess_amount or 0),
                "admin_deduction": float(earning.admin_deduction or 0),
                "tds_deduction": float(earning.tds_deduction or 0),
                "net_company_earnings": float(earning.net_company_earnings or 0),
                "paid_amount": float(earning.paid_amount or 0),
                "income_type": earning.income_type,
                "ceiling_date": earning.ceiling_date.isoformat() if earning.ceiling_date else None,
                "timestamp": earning.timestamp.isoformat() if earning.timestamp else None,
                "description": earning.description,
                "description_details": description_parts
            })
        
        # Summary statistics - DC Protocol: Calculate from source
        summary_query = db.query(
            func.count(CompanyEarnings.id).label('total_records'),
            func.sum(CompanyEarnings.net_company_earnings).label('total_earnings'),
            func.sum(CompanyEarnings.original_amount).label('total_original'),
            func.sum(CompanyEarnings.excess_amount).label('total_excess'),
            func.sum(CompanyEarnings.admin_deduction).label('total_admin'),
            func.sum(CompanyEarnings.tds_deduction).label('total_tds')
        )
        
        if from_date:
            summary_query = summary_query.filter(func.date(CompanyEarnings.timestamp) >= from_date)
        if to_date:
            summary_query = summary_query.filter(func.date(CompanyEarnings.timestamp) <= to_date)
        
        summary = summary_query.first()
        
        return {
            "success": True,
            "records": records,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit
            },
            "summary": {
                "total_records": summary.total_records or 0,
                "total_net_earnings": float(summary.total_earnings or 0),
                "total_original_amount": float(summary.total_original or 0),
                "total_excess_amount": float(summary.total_excess or 0),
                "total_admin_deduction": float(summary.total_admin or 0),
                "total_tds_deduction": float(summary.total_tds or 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching company earnings: {str(e)}")
