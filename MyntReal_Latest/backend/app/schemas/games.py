"""
Pydantic Schemas for Games, Anti-Cheat, and Rewards (DC Protocol Oct 2026)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import re


class GameStartRequest(BaseModel):
    game_type: str = Field(..., description="SNAKE, BLOCK_DROP, or ENDLESS_RUNNER")
    character_id: Optional[str] = Field("volt_fox", description="Character identifier for Endless Runner")
    mobile_number: Optional[str] = Field(None, description="Optional 10-digit mobile number for seamless progress saving")

    @validator("game_type")
    def validate_game_type(cls, v):
        clean = (v or "").strip().upper()
        allowed = ["SNAKE", "BLOCK_DROP", "ENDLESS_RUNNER", "BUBBLE_BLASTER", "BOUNCING_BALL", "BOUNCE_CLASSIC"]
        if clean not in allowed:
            raise ValueError(f"game_type must be one of: {', '.join(allowed)}")
        return clean


class GameStartResponse(BaseModel):
    success: bool
    session_token: str
    game_type: str
    character_id: str
    server_seed: str
    points_eligible: bool
    daily_points_earned_today: int
    daily_points_cap: int
    expires_in_seconds: int
    reward_rules: Dict[str, Any]
    message: Optional[str] = None


class GameCompleteRequest(BaseModel):
    session_token: str
    score: int = Field(..., ge=0)
    level: int = Field(1, ge=1)
    lines_cleared: int = Field(0, ge=0)
    items_collected: int = Field(0, ge=0)
    distance_travelled: int = Field(0, ge=0)
    duration_seconds: int = Field(..., ge=0)
    telemetry_summary: Optional[Dict[str, Any]] = None


class GameCompleteResponse(BaseModel):
    success: bool
    score: int
    best_score: int
    is_new_best: bool
    reward_points: int
    reward_status: str
    claim_code: Optional[str] = None
    requires_claim: bool = False
    total_balance: Optional[float] = None
    message: str


class GameClaimRequest(BaseModel):
    claim_code: str = Field(..., min_length=8, max_length=32)

    @validator("claim_code")
    def validate_code(cls, v):
        clean = (v or "").strip().upper()
        if not re.match(r"^PLAY-[A-Z0-9]{4}-\d{4}$", clean):
            raise ValueError("Invalid claim code format. Expected PLAY-XXXX-NNNN")
        return clean


class GameClaimResponse(BaseModel):
    success: bool
    credited_points: int
    new_balance: float
    account_type: str
    message: str


class GameHistoryEntry(BaseModel):
    id: int
    game_type: str
    score: int
    level: int
    lines_cleared: int
    items_collected: int
    distance_travelled: int
    duration_seconds: int
    reward_points: int
    reward_status: str
    created_at: Optional[str] = None


class UserGameStatsResponse(BaseModel):
    success: bool
    today_points: int
    daily_cap: int
    all_time_points: int
    total_games_played: int
    best_scores: Dict[str, int]
    recent_sessions: List[GameHistoryEntry]


class CustomerPointsLedgerEntry(BaseModel):
    id: int
    points_credit: float
    points_debit: float
    balance_after: float
    reason_code: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class CustomerPointsLedgerResponse(BaseModel):
    success: bool
    current_balance: float
    entries: List[CustomerPointsLedgerEntry]
    total_entries: int
    page: int
    page_size: int


class QuickResumeRequest(BaseModel):
    mobile_number: str = Field(..., description="10-digit Indian mobile number")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        digits = re.sub(r"\D", "", v or "")
        if len(digits) > 10 and (digits.startswith("91") or digits.startswith("0")):
            digits = digits[-10:]
        if len(digits) != 10:
            raise ValueError("Please provide a valid 10-digit mobile number")
        return digits


class QuickResumeResponse(BaseModel):
    success: bool
    customer_id: int
    customer_name: str
    mobile_number: str
    token: str
    loyalty_points: float
    best_scores: Dict[str, int]
    message: str

