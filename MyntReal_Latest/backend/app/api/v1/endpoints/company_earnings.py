"""
Company Earnings API Endpoints
DC Protocol compliant - Single source of truth for revenue and expense tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from decimal import Decimal

from app.core.database import get_db
from app.core.rbac import require_roles, require_roles_hybrid
from app.models.user import User
from app.services.company_earnings_service import CompanyEarningsService

router = APIRouter()


@router.get("/handling-charges")
async def get_handling_charges_revenue(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    user_id: Optional[str] = Query(None, description="Filter by user MNR ID"),
    collection_status: Optional[str] = Query(None, description="Filter by collection status: COLLECTED, PENDING"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    TAB 1: Get handling charges + GST revenue
    Shows company earnings from award processing handling charges
    """
    import logging
    logger = logging.getLogger(__name__)
    user_type = getattr(current_user, 'user_type', getattr(current_user, 'staff_type', 'Unknown'))
    logger.warning(f"🔍 Company Earnings API called by: {current_user.id} - Role: {user_type}")
    try:
        result = CompanyEarningsService.get_handling_charges_revenue(
            db=db,
            from_date=from_date,
            to_date=to_date,
            user_id=user_id,
            collection_status=collection_status,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching handling charges revenue: {str(e)}")


@router.get("/revenue-summary")
async def get_revenue_summary(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    TAB 2: Summary Cards - Overall revenue, payouts, expenses, profit
    """
    try:
        result = CompanyEarningsService.get_revenue_summary(
            db=db,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue summary: {str(e)}")


@router.get("/revenue-details")
async def get_revenue_details(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    TAB 2 - SUB-TAB 1: Revenue In (Package Sales + Handling Charges)
    Date-wise breakdown
    """
    try:
        result = CompanyEarningsService.get_revenue_details(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue details: {str(e)}")


@router.get("/payout-details")
async def get_payout_details(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    TAB 2 - SUB-TAB 2: Payouts (Income + TDS Payable)
    Date-wise breakdown with paid/pending status
    """
    try:
        result = CompanyEarningsService.get_payout_details(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching payout details: {str(e)}")


@router.get("/expense-details")
async def get_expense_details(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    TAB 2 - SUB-TAB 3: Expenses (Awards, Bonanza, Field Allowance, Training, Operations)
    Date-wise breakdown with paid/pending status
    """
    try:
        result = CompanyEarningsService.get_expense_details(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expense details: {str(e)}")


@router.get("/revenue-user-details")
async def get_revenue_user_details(
    transaction_date: date = Query(..., description="Transaction date"),
    source_type: str = Query(..., description="Source type: Package Sales or Company Earnings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Get user-level details for revenue transactions on a specific date and source type
    """
    try:
        result = CompanyEarningsService.get_revenue_user_details(
            db=db,
            transaction_date=transaction_date,
            source_type=source_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue user details: {str(e)}")


@router.get("/payout-user-details")
async def get_payout_user_details(
    transaction_date: date = Query(..., description="Transaction date"),
    income_type: str = Query(..., description="Income type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Get user-level details for payout transactions on a specific date and income type
    """
    try:
        result = CompanyEarningsService.get_payout_user_details(
            db=db,
            transaction_date=transaction_date,
            income_type=income_type
        )
        return result
    except Exception as e:
        import traceback
        print(f"❌ ERROR in get_payout_user_details: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching payout user details: {str(e)}")


@router.get("/expense-user-details")
async def get_expense_user_details(
    transaction_date: date = Query(..., description="Transaction date"),
    category: str = Query(..., description="Expense category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Get user-level details for expense transactions on a specific date and category
    """
    try:
        result = CompanyEarningsService.get_expense_user_details(
            db=db,
            transaction_date=transaction_date,
            category=category
        )
        return result
    except Exception as e:
        import traceback
        print(f"❌ ERROR in get_expense_user_details: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching expense user details: {str(e)}")


@router.get("/revenue-by-user")
async def get_revenue_by_user(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    User-wise revenue aggregation (User → Source → Date drill-down)
    """
    try:
        result = CompanyEarningsService.get_revenue_by_user(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue by user: {str(e)}")


@router.get("/payout-by-user")
async def get_payout_by_user(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    User-wise payout aggregation (User → Income Type → Date drill-down)
    """
    try:
        result = CompanyEarningsService.get_payout_by_user(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching payout by user: {str(e)}")


@router.get("/expense-by-user")
async def get_expense_by_user(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    User-wise expense aggregation (User → Category → Date drill-down)
    """
    try:
        result = CompanyEarningsService.get_expense_by_user(
            db=db,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expense by user: {str(e)}")


@router.get("/revenue-sources-for-user")
async def get_revenue_sources_for_user(
    user_id: str = Query(..., description="User MNR ID"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 2 drill-down: Show revenue sources for a specific user
    """
    try:
        result = CompanyEarningsService.get_revenue_sources_for_user(
            db=db,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue sources for user: {str(e)}")


@router.get("/payout-sources-for-user")
async def get_payout_sources_for_user(
    user_id: str = Query(..., description="User MNR ID"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 2 drill-down: Show payout income types for a specific user
    """
    try:
        result = CompanyEarningsService.get_payout_sources_for_user(
            db=db,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching payout sources for user: {str(e)}")


@router.get("/expense-sources-for-user")
async def get_expense_sources_for_user(
    user_id: str = Query(..., description="User MNR ID"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 2 drill-down: Show expense categories for a specific user
    """
    try:
        result = CompanyEarningsService.get_expense_sources_for_user(
            db=db,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expense sources for user: {str(e)}")


@router.get("/revenue-dates-for-user-source")
async def get_revenue_dates_for_user_source(
    user_id: str = Query(..., description="User MNR ID"),
    source: str = Query(..., description="Revenue source: Package Sales or Company Earnings"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 3 drill-down: Show dates for a specific user + source combination
    """
    try:
        result = CompanyEarningsService.get_revenue_dates_for_user_source(
            db=db,
            user_id=user_id,
            source=source,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue dates for user source: {str(e)}")


@router.get("/payout-dates-for-user-source")
async def get_payout_dates_for_user_source(
    user_id: str = Query(..., description="User MNR ID"),
    income_type: str = Query(..., description="Income type"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 3 drill-down: Show dates for a specific user + income_type combination
    """
    try:
        result = CompanyEarningsService.get_payout_dates_for_user_source(
            db=db,
            user_id=user_id,
            income_type=income_type,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching payout dates for user source: {str(e)}")


@router.get("/expense-dates-for-user-source")
async def get_expense_dates_for_user_source(
    user_id: str = Query(..., description="User MNR ID"),
    category: str = Query(..., description="Expense category"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_hybrid(["RVZ ID"]))
):
    """
    Level 3 drill-down: Show dates for a specific user + category combination
    """
    try:
        result = CompanyEarningsService.get_expense_dates_for_user_source(
            db=db,
            user_id=user_id,
            category=category,
            from_date=from_date,
            to_date=to_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expense dates for user source: {str(e)}")
