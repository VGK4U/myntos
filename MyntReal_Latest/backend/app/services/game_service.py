"""
Game Service: Session Lifecycle, Anti-Cheat Verification & Rewards Engine (DC Protocol Oct 2026)
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from fastapi import HTTPException, status

from app.models.base import get_indian_time
from app.models.games_and_points import GameSession, CustomerPointsLedger, GameRewardCode
from app.models.customer_profile import CustomerProfile
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger

logger = logging.getLogger(__name__)

# Business Safety Constraint: Point issuance is disabled by default until explicitly enabled by business approval
POINTS_ISSUANCE_ACTIVE = os.getenv("GAMES_POINTS_ISSUANCE_ACTIVE", "0") == "1"

DAILY_POINTS_CAP = 50
SESSION_EXPIRY_MINUTES = 30
CODE_EXPIRY_HOURS = 24

# Reward calculation matrices (Points earned per milestone)
GAME_REWARD_RULES = {
    "SNAKE": {
        "points_per_milestone": 10,
        "milestone_interval": 10,  # 10 food = 10 pts, 20 food = 20 pts
        "max_points_per_session": 20,
        "min_seconds_per_food": 0.35,  # Anti-cheat: cannot eat faster than 350ms per food
    },
    "BLOCK_DROP": {
        "points_per_milestone": 10,
        "milestone_interval": 4,   # 4 lines = 10 pts, 8 lines = 20 pts
        "max_points_per_session": 20,
        "min_seconds_per_line": 1.5,  # Anti-cheat: cannot clear lines faster than 1.5s per line
    },
    "ENDLESS_RUNNER": {
        "points_per_milestone": 10,
        "milestone_interval": 250, # 250m distance = 10 pts, 500m = 20 pts
        "max_points_per_session": 20,
        "min_seconds_per_100m": 0.7, # Anti-cheat: cannot sprint faster than 0.7s per 100m
    }
}


def get_today_earned_points(db: Session, account_type: str, account_id: int) -> int:
    """Calculate total points earned by this account across all games today."""
    if not account_id or account_type == "GUEST":
        return 0

    try:
        today_start = get_indian_time().replace(hour=0, minute=0, second=0, microsecond=0)

        query = db.query(func.coalesce(func.sum(GameSession.reward_points), 0)).filter(
            GameSession.status == "COMPLETED",
            GameSession.created_at >= today_start
        )

        if account_type == "CUSTOMER":
            query = query.filter(GameSession.customer_id == account_id)
        elif account_type == "PARTNER":
            query = query.filter(GameSession.partner_id == account_id)
        else:
            return 0

        return int(query.scalar() or 0)
    except Exception as e:
        logger.warning(f"Could not query today earned points: {e}")
        db.rollback()
        return 0



def start_game_session(
    db: Session,
    game_type: str,
    character_id: str = "volt_fox",
    account_type: str = "GUEST",
    account_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """Initialize a verified game session."""
    now = get_indian_time()
    expires_at = now + timedelta(minutes=SESSION_EXPIRY_MINUTES)

    # Check rate limit (max 15 starts in the last hour per user/IP)
    one_hour_ago = now - timedelta(hours=1)
    rate_query = db.query(func.count(GameSession.id)).filter(
        GameSession.created_at >= one_hour_ago
    )
    if account_id and account_type == "CUSTOMER":
        rate_query = rate_query.filter(GameSession.customer_id == account_id)
    elif account_id and account_type == "PARTNER":
        rate_query = rate_query.filter(GameSession.partner_id == account_id)
    elif ip_address:
        rate_query = rate_query.filter(GameSession.ip_address == ip_address)

    recent_count = 0
    try:
        recent_count = rate_query.scalar() or 0
    except Exception:
        db.rollback()

    if recent_count >= 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session creation rate limit reached. Please take a break and try again in an hour."
        )

    # Check daily points cap
    today_points = get_today_earned_points(db, account_type, account_id) if account_id else 0
    points_eligible = (today_points < DAILY_POINTS_CAP)

    session_token = GameSession.generate_token()
    server_seed = GameSession.generate_seed()

    customer_id = account_id if account_type == "CUSTOMER" else None
    partner_id = account_id if account_type == "PARTNER" else None

    session = GameSession(
        session_token=session_token,
        game_type=game_type,
        account_type=account_type,
        customer_id=customer_id,
        partner_id=partner_id,
        status="ACTIVE",
        character_id=character_id or "volt_fox",
        server_seed=server_seed,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now,
        updated_at=now,
        expires_at=expires_at
    )
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    except Exception as e:
        logger.warning(f"Could not persist game session: {e}")
        db.rollback()

    return {
        "session_token": session_token,
        "game_type": game_type,
        "character_id": character_id,
        "server_seed": server_seed,
        "points_eligible": points_eligible,
        "daily_points_earned_today": today_points,
        "daily_points_cap": DAILY_POINTS_CAP,
        "expires_in_seconds": SESSION_EXPIRY_MINUTES * 60,
        "reward_rules": GAME_REWARD_RULES.get(game_type, {})
    }


def validate_anti_cheat_physics(
    game_type: str,
    score: int,
    level: int,
    lines_cleared: int,
    items_collected: int,
    distance_travelled: int,
    duration_seconds: int
) -> bool:
    """Validate that reported gameplay events are physically possible within the elapsed duration."""
    # Allow 1 second grace window for network lag
    dur = max(duration_seconds, 1)

    rules = GAME_REWARD_RULES.get(game_type, {})
    if game_type == "SNAKE":
        min_time = items_collected * rules.get("min_seconds_per_food", 0.35)
        if dur < min_time:
            logger.warning(f"[ANTI-CHEAT] Snake velocity anomaly: {items_collected} food in {dur}s (min: {min_time}s)")
            return False

    elif game_type == "BLOCK_DROP":
        min_time = lines_cleared * rules.get("min_seconds_per_line", 1.5)
        if dur < min_time:
            logger.warning(f"[ANTI-CHEAT] Block Drop speed anomaly: {lines_cleared} lines in {dur}s (min: {min_time}s)")
            return False

    elif game_type == "ENDLESS_RUNNER":
        min_time = (distance_travelled / 100.0) * rules.get("min_seconds_per_100m", 0.7)
        if dur < min_time:
            logger.warning(f"[ANTI-CHEAT] Runner speed anomaly: {distance_travelled}m in {dur}s (min: {min_time}s)")
            return False

    return True


def calculate_reward_points(
    game_type: str,
    score: int,
    lines_cleared: int,
    items_collected: int,
    distance_travelled: int
) -> int:
    """Calculate reward points according to approved milestone rules."""
    rules = GAME_REWARD_RULES.get(game_type, {})
    max_pts = rules.get("max_points_per_session", 20)
    pts_per_step = rules.get("points_per_milestone", 10)
    interval = rules.get("milestone_interval", 10)

    if game_type == "SNAKE":
        milestones = items_collected // interval
        return min(milestones * pts_per_step, max_pts)
    elif game_type == "BLOCK_DROP":
        milestones = lines_cleared // interval
        return min(milestones * pts_per_step, max_pts)
    elif game_type == "ENDLESS_RUNNER":
        milestones = distance_travelled // interval
        return min(milestones * pts_per_step, max_pts)
    return 0


def complete_game_session(
    db: Session,
    session_token: str,
    score: int,
    level: int,
    lines_cleared: int,
    items_collected: int,
    distance_travelled: int,
    duration_seconds: int,
    telemetry_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate, record, and resolve game session completion."""
    now = get_indian_time()

    # Atomically lock session row
    session = db.query(GameSession).filter(
        GameSession.session_token == session_token
    ).with_for_update().first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game session not found.")

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game session already finalized with status: {session.status}"
        )

    if session.is_expired():
        session.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game session has expired.")

    # Anti-cheat physics check
    is_valid = validate_anti_cheat_physics(
        session.game_type, score, level, lines_cleared, items_collected, distance_travelled, duration_seconds
    )
    if not is_valid:
        session.status = "ABANDONED"
        session.reward_status = "NOT_ELIGIBLE"
        session.duration_seconds = duration_seconds
        session.score = score
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session flagged by anti-cheat timing validation. Score rejected."
        )

    # Determine previous best score for this account & game type
    best_score = score
    is_new_best = True
    best_query = db.query(func.max(GameSession.score)).filter(
        GameSession.game_type == session.game_type,
        GameSession.status == "COMPLETED"
    )
    if session.account_type == "CUSTOMER" and session.customer_id:
        best_query = best_query.filter(GameSession.customer_id == session.customer_id)
        prev_max = best_query.scalar() or 0
        is_new_best = score > prev_max
        best_score = max(score, prev_max)
    elif session.account_type == "PARTNER" and session.partner_id:
        best_query = best_query.filter(GameSession.partner_id == session.partner_id)
        prev_max = best_query.scalar() or 0
        is_new_best = score > prev_max
        best_score = max(score, prev_max)

    # Calculate points
    raw_reward = calculate_reward_points(
        session.game_type, score, lines_cleared, items_collected, distance_travelled
    )

    # Apply daily cap
    today_earned = 0
    if session.account_type in ["CUSTOMER", "PARTNER"]:
        acc_id = session.customer_id or session.partner_id
        today_earned = get_today_earned_points(db, session.account_type, acc_id)

    remaining_cap = max(0, DAILY_POINTS_CAP - today_earned)
    eligible_points = min(raw_reward, remaining_cap)

    # Finalize session fields
    session.score = score
    session.best_score = best_score
    session.level = level
    session.lines_cleared = lines_cleared
    session.items_collected = items_collected
    session.distance_travelled = distance_travelled
    session.duration_seconds = duration_seconds
    session.status = "COMPLETED"
    session.updated_at = now

    claim_code = None
    requires_claim = False
    total_balance = None
    reward_status_val = "NOT_ELIGIBLE"

    if eligible_points > 0:
        if not POINTS_ISSUANCE_ACTIVE:
            # Reward infrastructure verified, but actual points issuance kept disabled per business rule
            session.reward_points = eligible_points
            session.reward_status = "DISABLED"
            reward_status_val = "DISABLED"
            message = f"Superb! Score {score} recorded. (Promotional point issuance is currently in preview mode)"
        else:
            # Point issuance is active
            session.reward_points = eligible_points
            reward_status_val = "ELIGIBLE"

            if session.account_type == "CUSTOMER" and session.customer_id:
                # Credit customer points ledger directly
                cust = db.query(CustomerProfile).filter_by(id=session.customer_id).with_for_update().first()
                if cust:
                    curr_bal = float(cust.loyalty_points_balance or 0)
                    new_bal = curr_bal + eligible_points
                    cust.loyalty_points_balance = new_bal

                    ledger = CustomerPointsLedger(
                        customer_id=cust.id,
                        points_credit=eligible_points,
                        points_debit=0,
                        balance_after=new_bal,
                        reason_code="GAME_REWARD",
                        reference_type="GAME_SESSION",
                        reference_id=session.id,
                        notes=f"{session.game_type} Game Reward (Score: {score})",
                        created_at=now
                    )
                    db.add(ledger)
                    session.reward_status = "CLAIMED"
                    reward_status_val = "CLAIMED"
                    total_balance = new_bal
                    message = f"Awesome! {eligible_points} loyalty points credited to your MyntReal account."

            elif session.account_type == "PARTNER" and session.partner_id:
                # Credit partner points ledger directly (using CAMPAIGN_BONUS to honor existing check constraints)
                partner = db.query(OfficialPartner).filter_by(id=session.partner_id).with_for_update().first()
                if partner:
                    curr_bal = float(partner.vgk_points_balance or 0)
                    new_bal = curr_bal + eligible_points
                    partner.vgk_points_balance = new_bal

                    ledger = VGKPointsLedger(
                        partner_id=partner.id,
                        points_credit=eligible_points,
                        points_debit=0,
                        balance_after=new_bal,
                        reason_code="CAMPAIGN_BONUS",
                        reference_type="GAME_SESSION",
                        reference_id=session.id,
                        notes=f"{session.game_type} Arcade Reward (Score: {score})",
                        created_at=now
                    )
                    db.add(ledger)
                    session.reward_status = "CLAIMED"
                    reward_status_val = "CLAIMED"
                    total_balance = new_bal
                    message = f"Congratulations! {eligible_points} promotional points added to your VGK balance."

            else:
                # Guest player: Generate secure claim code
                human_code = GameRewardCode.generate_human_code()
                code_hash = GameRewardCode.hash_code(human_code)
                code_obj = GameRewardCode(
                    code_hash=code_hash,
                    game_session_id=session.id,
                    points_value=eligible_points,
                    status="ACTIVE",
                    created_at=now,
                    expires_at=now + timedelta(hours=CODE_EXPIRY_HOURS)
                )
                db.add(code_obj)
                session.claim_token = code_hash
                session.reward_status = "ELIGIBLE"
                claim_code = human_code
                requires_claim = True
                message = f"Great game! You won {eligible_points} points. Sign in to claim your reward code."
    else:
        session.reward_points = 0
        session.reward_status = "NOT_ELIGIBLE"
        message = f"Game complete! Final score: {score}."

    db.commit()

    return {
        "success": True,
        "score": score,
        "best_score": best_score,
        "is_new_best": is_new_best,
        "reward_points": eligible_points,
        "reward_status": reward_status_val,
        "claim_code": claim_code,
        "requires_claim": requires_claim,
        "total_balance": total_balance,
        "message": message
    }


def claim_reward_code(
    db: Session,
    claim_code: str,
    account_type: str,
    account_id: int
) -> Dict[str, Any]:
    """
    Atomically redeem single-use claim code.
    Requires authenticated session (Zero unverified mobile claim rule).
    """
    if not claim_code or not account_id or account_type not in ["CUSTOMER", "PARTNER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid authentication is required to claim reward codes."
        )

    code_hash = GameRewardCode.hash_code(claim_code)
    now = get_indian_time()

    code_obj = db.query(GameRewardCode).filter(
        GameRewardCode.code_hash == code_hash
    ).with_for_update().first()

    if not code_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired claim code.")

    if code_obj.status == "CLAIMED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This claim code has already been redeemed.")

    if code_obj.status != "ACTIVE" or code_obj.expires_at < now:
        code_obj.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This claim code has expired.")

    # Check daily cap for the claiming user
    today_earned = get_today_earned_points(db, account_type, account_id)
    pts_to_credit = code_obj.points_value
    if today_earned + pts_to_credit > DAILY_POINTS_CAP:
        allowed = max(0, DAILY_POINTS_CAP - today_earned)
        if allowed <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily points limit ({DAILY_POINTS_CAP} pts) reached for today. Try claiming tomorrow."
            )
        pts_to_credit = allowed

    new_balance = 0.0

    if account_type == "CUSTOMER":
        cust = db.query(CustomerProfile).filter_by(id=account_id).with_for_update().first()
        if not cust:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer account not found.")

        curr_bal = float(cust.loyalty_points_balance or 0)
        new_balance = curr_bal + pts_to_credit
        cust.loyalty_points_balance = new_balance

        ledger = CustomerPointsLedger(
            customer_id=cust.id,
            points_credit=pts_to_credit,
            points_debit=0,
            balance_after=new_balance,
            reason_code="GAME_REWARD",
            reference_type="CLAIM_CODE",
            reference_id=code_obj.id,
            notes=f"Redeemed Game Code {claim_code}",
            created_at=now
        )
        db.add(ledger)

    elif account_type == "PARTNER":
        partner = db.query(OfficialPartner).filter_by(id=account_id).with_for_update().first()
        if not partner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner account not found.")

        curr_bal = float(partner.vgk_points_balance or 0)
        new_balance = curr_bal + pts_to_credit
        partner.vgk_points_balance = new_balance

        ledger = VGKPointsLedger(
            partner_id=partner.id,
            points_credit=pts_to_credit,
            points_debit=0,
            balance_after=new_balance,
            reason_code="CAMPAIGN_BONUS",
            reference_type="CLAIM_CODE",
            reference_id=code_obj.id,
            notes=f"Redeemed Arcade Code {claim_code}",
            created_at=now
        )
        db.add(ledger)

    code_obj.status = "CLAIMED"
    code_obj.claimed_by_account_type = account_type
    code_obj.claimed_by_id = account_id
    code_obj.claimed_at = now

    # Also update linked session
    if code_obj.game_session:
        code_obj.game_session.reward_status = "CLAIMED"

    db.commit()

    return {
        "success": True,
        "credited_points": pts_to_credit,
        "new_balance": new_balance,
        "account_type": account_type,
        "message": f"Success! {pts_to_credit} points added to your balance."
    }


def get_user_game_stats(
    db: Session,
    account_type: str,
    account_id: int
) -> Dict[str, Any]:
    """Retrieve personal bests, points earned, and recent session history."""
    if not account_id:
        return {
            "today_points": 0,
            "daily_cap": DAILY_POINTS_CAP,
            "all_time_points": 0,
            "total_games_played": 0,
            "best_scores": {"SNAKE": 0, "BLOCK_DROP": 0, "ENDLESS_RUNNER": 0},
            "recent_sessions": []
        }

    today_points = get_today_earned_points(db, account_type, account_id)

    try:
        # Base query for this user
        base_q = db.query(GameSession).filter(GameSession.status == "COMPLETED")
        if account_type == "CUSTOMER":
            base_q = base_q.filter(GameSession.customer_id == account_id)
        elif account_type == "PARTNER":
            base_q = base_q.filter(GameSession.partner_id == account_id)

        total_games = base_q.count()
        all_time_points = db.query(func.coalesce(func.sum(GameSession.reward_points), 0)).filter(
            GameSession.status == "COMPLETED",
            (GameSession.customer_id == account_id) if account_type == "CUSTOMER" else (GameSession.partner_id == account_id)
        ).scalar() or 0

        best_scores = {"SNAKE": 0, "BLOCK_DROP": 0, "ENDLESS_RUNNER": 0}
        for gtype in best_scores.keys():
            mx = base_q.filter(GameSession.game_type == gtype).with_entities(func.max(GameSession.score)).scalar()
            best_scores[gtype] = int(mx or 0)

        recent_rows = base_q.order_by(GameSession.created_at.desc()).limit(10).all()
        recent_sessions = [
            {
                "id": r.id,
                "game_type": r.game_type,
                "score": r.score,
                "level": r.level,
                "lines_cleared": r.lines_cleared,
                "items_collected": r.items_collected,
                "distance_travelled": r.distance_travelled,
                "duration_seconds": r.duration_seconds,
                "reward_points": r.reward_points,
                "reward_status": r.reward_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_rows
        ]

        return {
            "today_points": today_points,
            "daily_cap": DAILY_POINTS_CAP,
            "all_time_points": int(all_time_points),
            "total_games_played": total_games,
            "best_scores": best_scores,
            "recent_sessions": recent_sessions
        }
    except Exception as e:
        logger.warning(f"Could not load stats from DB: {e}")
        db.rollback()
        return {
            "today_points": 0,
            "daily_cap": DAILY_POINTS_CAP,
            "all_time_points": 0,
            "total_games_played": 0,
            "best_scores": {"SNAKE": 0, "BLOCK_DROP": 0, "ENDLESS_RUNNER": 0},
            "recent_sessions": []
        }
