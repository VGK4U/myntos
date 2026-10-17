"""
FastAPI Endpoints for Games, Sessions, Progress Tracking & Rewards (DC Protocol Oct 2026)
"""
import logging
from typing import Optional, Dict, Any, Tuple
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.customer_profile import CustomerProfile
from app.models.staff_accounts import OfficialPartner
from app.models.games_and_points import CustomerPointsLedger
from app.schemas.games import (
    GameStartRequest,
    GameStartResponse,
    GameCompleteRequest,
    GameCompleteResponse,
    GameClaimRequest,
    GameClaimResponse,
    UserGameStatsResponse,
    CustomerPointsLedgerResponse,
    CustomerPointsLedgerEntry,
    QuickResumeRequest,
    QuickResumeResponse
)
from app.services.game_service import (
    start_game_session,
    complete_game_session,
    claim_reward_code,
    get_user_game_stats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["Games & Loyalty Rewards"])

JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"


def resolve_game_actor(request: Request, db: Session) -> Tuple[str, Optional[int], Optional[Any]]:
    """
    Dynamically identifies if the request originates from:
    1. Authenticated Retail Customer ('CUSTOMER', customer_id, CustomerProfile)
    2. Authenticated VGK Partner ('PARTNER', partner_id, OfficialPartner)
    3. Guest player ('GUEST', None, None)
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()

    if not token:
        # Check cookies as fallback
        token = request.cookies.get("customer_token") or request.cookies.get("staff_token") or request.cookies.get("partner_token")

    if not token:
        return "GUEST", None, None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # 1. Customer token check
        if payload.get("role") == "customer" or "customer_id" in payload:
            cid = payload.get("customer_id")
            phone = payload.get("sub")
            cust = None
            if cid:
                cust = db.query(CustomerProfile).filter_by(id=cid, is_active=True).first()
            if not cust and phone:
                cust = db.query(CustomerProfile).filter_by(mobile_number=phone, is_active=True).first()
            if cust:
                return "CUSTOMER", cust.id, cust

        # 2. VGK Partner token check
        pid = payload.get("partner_id") or payload.get("user_id") or payload.get("id")
        partner_code = payload.get("partner_code") or payload.get("emp_code")
        partner = None
        if pid:
            partner = db.query(OfficialPartner).filter_by(id=pid).first()
        if not partner and partner_code:
            partner = db.query(OfficialPartner).filter_by(partner_code=partner_code).first()
        if partner:
            return "PARTNER", partner.id, partner

    except Exception:
        # Invalid or expired token defaults to Guest
        pass

    return "GUEST", None, None


@router.post("/start", response_model=GameStartResponse)
def api_start_game(
    payload: GameStartRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Initialize a secure server-tracked game session.
    Enforces rate limits and computes remaining daily point eligibility.
    If mobile_number is provided for guest player, auto-attaches to customer profile.
    """
    account_type, account_id, _ = resolve_game_actor(request, db)

    # Seamless mobile_number association if unauthenticated
    if account_type == "GUEST" and payload.mobile_number:
        import re
        digits = re.sub(r"\D", "", payload.mobile_number or "")
        if len(digits) > 10 and (digits.startswith("91") or digits.startswith("0")):
            digits = digits[-10:]
        if len(digits) == 10:
            cust = db.query(CustomerProfile).filter_by(mobile_number=digits, is_active=True).first()
            if not cust:
                cust = CustomerProfile(
                    mobile_number=digits,
                    customer_name=f"Player {digits[-4:]}",
                    pincode="600001",
                    security_pin_hash="QUICK_ARCADE_USER",
                    loyalty_points_balance=0.00,
                    is_active=True
                )
                db.add(cust)
                db.commit()
                db.refresh(cust)
            account_type = "CUSTOMER"
            account_id = cust.id

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    res = start_game_session(
        db=db,
        game_type=payload.game_type,
        character_id=payload.character_id or "volt_fox",
        account_type=account_type,
        account_id=account_id,
        ip_address=client_ip,
        user_agent=user_agent
    )

    return GameStartResponse(
        success=True,
        session_token=res["session_token"],
        game_type=res["game_type"],
        character_id=res["character_id"],
        server_seed=res["server_seed"],
        points_eligible=res["points_eligible"],
        daily_points_earned_today=res["daily_points_earned_today"],
        daily_points_cap=res["daily_points_cap"],
        expires_in_seconds=res["expires_in_seconds"],
        reward_rules=res["reward_rules"],
        message="Session active. Good luck!"
    )


@router.post("/complete", response_model=GameCompleteResponse)
def api_complete_game(
    payload: GameCompleteRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit completed game session with anti-cheat physics verification.
    Credits authenticated account or issues single-use guest claim code.
    """
    res = complete_game_session(
        db=db,
        session_token=payload.session_token,
        score=payload.score,
        level=payload.level,
        lines_cleared=payload.lines_cleared,
        items_collected=payload.items_collected,
        distance_travelled=payload.distance_travelled,
        duration_seconds=payload.duration_seconds,
        telemetry_summary=payload.telemetry_summary
    )

    return GameCompleteResponse(
        success=True,
        score=res["score"],
        best_score=res["best_score"],
        is_new_best=res["is_new_best"],
        reward_points=res["reward_points"],
        reward_status=res["reward_status"],
        claim_code=res.get("claim_code"),
        requires_claim=res.get("requires_claim", False),
        total_balance=res.get("total_balance"),
        message=res["message"]
    )


@router.post("/claim", response_model=GameClaimResponse)
def api_claim_reward(
    payload: GameClaimRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Atomically redeem a single-use reward claim code.
    Requires authenticated session (Zero unverified mobile claim rule).
    """
    account_type, account_id, _ = resolve_game_actor(request, db)
    if account_type == "GUEST" or not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to your MyntReal customer or VGK partner account to claim rewards."
        )

    res = claim_reward_code(
        db=db,
        claim_code=payload.claim_code,
        account_type=account_type,
        account_id=account_id
    )

    return GameClaimResponse(
        success=True,
        credited_points=res["credited_points"],
        new_balance=res["new_balance"],
        account_type=res["account_type"],
        message=res["message"]
    )


@router.get("/my-stats", response_model=UserGameStatsResponse)
def api_get_my_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retrieve current user's daily cap progress, personal bests, and recent games.
    """
    account_type, account_id, _ = resolve_game_actor(request, db)
    res = get_user_game_stats(db=db, account_type=account_type, account_id=account_id)

    return UserGameStatsResponse(
        success=True,
        today_points=res["today_points"],
        daily_cap=res["daily_cap"],
        all_time_points=res["all_time_points"],
        total_games_played=res["total_games_played"],
        best_scores=res["best_scores"],
        recent_sessions=res["recent_sessions"]
    )


@router.get("/customer-ledger", response_model=CustomerPointsLedgerResponse)
def api_get_customer_points_ledger(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated points transactions for the authenticated retail customer.
    """
    account_type, account_id, cust = resolve_game_actor(request, db)
    if account_type != "CUSTOMER" or not cust:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer authentication required to view points ledger."
        )

    offset = (page - 1) * page_size
    query = db.query(CustomerPointsLedger).filter(
        CustomerPointsLedger.customer_id == cust.id
    )

    total = query.count()
    rows = query.order_by(CustomerPointsLedger.created_at.desc()).offset(offset).limit(page_size).all()

    entries = [
        CustomerPointsLedgerEntry(
            id=r.id,
            points_credit=float(r.points_credit or 0),
            points_debit=float(r.points_debit or 0),
            balance_after=float(r.balance_after or 0),
            reason_code=r.reason_code,
            reference_type=r.reference_type,
            reference_id=r.reference_id,
            notes=r.notes,
            created_at=r.created_at.isoformat() if r.created_at else None
        )
        for r in rows
    ]

    return CustomerPointsLedgerResponse(
        success=True,
        current_balance=float(cust.loyalty_points_balance or 0),
        entries=entries,
        total_entries=total,
        page=page,
        page_size=page_size
    )


@router.post("/quick-resume", response_model=QuickResumeResponse)
def api_quick_resume(
    payload: QuickResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Seamless Mobile-Number Resume & Progress Saving.
    Automatically fetches or creates customer record, issues JWT token,
    and returns high scores and loyalty points so player enters game immediately with progress.
    """
    from datetime import datetime, timedelta
    clean_phone = payload.mobile_number

    cust = db.query(CustomerProfile).filter_by(mobile_number=clean_phone, is_active=True).first()
    if not cust:
        cust = CustomerProfile(
            mobile_number=clean_phone,
            customer_name=f"Player {clean_phone[-4:]}",
            pincode="600001",
            security_pin_hash="QUICK_ARCADE_USER",
            loyalty_points_balance=0.00,
            is_active=True
        )
        db.add(cust)
        db.commit()
        db.refresh(cust)

    token_data = {
        "sub": cust.mobile_number,
        "customer_id": cust.id,
        "name": cust.customer_name,
        "role": "customer",
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    jwt_token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    stats = get_user_game_stats(db, account_type="CUSTOMER", account_id=cust.id)
    best_scores = stats.get("best_scores", {}) if isinstance(stats, dict) else (stats.best_scores if hasattr(stats, "best_scores") else {})

    return QuickResumeResponse(
        success=True,
        customer_id=cust.id,
        customer_name=cust.customer_name,
        mobile_number=cust.mobile_number,
        token=jwt_token,
        loyalty_points=float(cust.loyalty_points_balance or 0.0),
        best_scores=best_scores,
        message=f"Welcome back, {cust.customer_name}! Your game progress is active."
    )

