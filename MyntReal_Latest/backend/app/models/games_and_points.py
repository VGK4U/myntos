"""
MyntReal & VGK4U Games, Points & Rewards Models (DC Protocol Oct 2026)
Defines:
1. GameSession: Server-tracked session for Snake, Block Drop & Endless Runner with anti-cheat telemetry.
2. CustomerPointsLedger: Dedicated append-only loyalty points ledger for retail customer profiles.
3. GameRewardCode: Secure SHA-256 hashed reward claim tokens for authenticated redemption.
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Index, Text, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import hashlib
import secrets
from app.models.base import Base, BaseModel, get_indian_time


class GameSession(BaseModel):
    """
    Game session tracker enforcing single-use completion, duration-to-score physics,
    and anti-cheat validation.
    """
    __tablename__ = 'game_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    game_type = Column(String(32), nullable=False, index=True)  # 'SNAKE', 'BLOCK_DROP', 'ENDLESS_RUNNER'
    account_type = Column(String(32), default='GUEST', nullable=False, index=True)  # 'CUSTOMER', 'PARTNER', 'GUEST'

    customer_id = Column(Integer, ForeignKey('customer_profiles.id', ondelete='SET NULL'), nullable=True, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)

    status = Column(String(20), default='ACTIVE', nullable=False, index=True)  # 'ACTIVE', 'COMPLETED', 'EXPIRED', 'ABANDONED'

    score = Column(Integer, default=0, nullable=False)
    best_score = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    lines_cleared = Column(Integer, default=0, nullable=False)
    items_collected = Column(Integer, default=0, nullable=False)
    distance_travelled = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)

    reward_points = Column(Integer, default=0, nullable=False)
    reward_status = Column(String(32), default='PENDING', nullable=False)  # 'PENDING', 'ELIGIBLE', 'NOT_ELIGIBLE', 'CLAIMED', 'DISABLED'
    claim_token = Column(String(64), unique=True, nullable=True, index=True)

    character_id = Column(String(32), default='volt_fox', nullable=False)
    server_seed = Column(String(64), nullable=False)
    telemetry_summary = Column(Text, nullable=True)

    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index('idx_game_sess_cust_date', 'customer_id', 'created_at'),
        Index('idx_game_sess_part_date', 'partner_id', 'created_at'),
        Index('idx_game_sess_type_status', 'game_type', 'status'),
    )

    @staticmethod
    def generate_token() -> str:
        return f"gs_{secrets.token_hex(24)}"

    @staticmethod
    def generate_seed() -> str:
        return secrets.token_hex(16)

    def is_expired(self) -> bool:
        return get_indian_time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_token": self.session_token,
            "game_type": self.game_type,
            "account_type": self.account_type,
            "status": self.status,
            "score": self.score,
            "best_score": self.best_score,
            "level": self.level,
            "lines_cleared": self.lines_cleared,
            "items_collected": self.items_collected,
            "distance_travelled": self.distance_travelled,
            "duration_seconds": self.duration_seconds,
            "reward_points": self.reward_points,
            "reward_status": self.reward_status,
            "character_id": self.character_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class CustomerPointsLedger(BaseModel):
    """
    Dedicated, immutable append-only loyalty points ledger for retail customer profiles.
    Completely decoupled from VGK4U channel partner business commissions.
    """
    __tablename__ = 'customer_points_ledger'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customer_profiles.id', ondelete='CASCADE'), nullable=False, index=True)

    points_credit = Column(Numeric(15, 2), default=0, nullable=False)
    points_debit = Column(Numeric(15, 2), default=0, nullable=False)
    balance_after = Column(Numeric(15, 2), nullable=False)

    reason_code = Column(String(40), nullable=False)  # 'GAME_REWARD', 'WELCOME_BONUS', 'CAMPAIGN_BONUS', 'SERVICE_DISCOUNT', 'MANUAL_ADJUSTMENT'
    reference_type = Column(String(40), nullable=True)  # 'GAME_SESSION', 'RECHARGE_TX', 'SERVICE_ORDER', 'ADMIN'
    reference_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_cust_pts_ledger_cust_created', 'customer_id', 'created_at'),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "points_credit": float(self.points_credit or 0),
            "points_debit": float(self.points_debit or 0),
            "balance_after": float(self.balance_after or 0),
            "reason_code": self.reason_code,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GameRewardCode(BaseModel):
    """
    Cryptographically secure single-use claim tokens.
    Stores SHA-256 hash of human-friendly claim code (e.g. 'PLAY-9A82-MYNT').
    """
    __tablename__ = 'game_reward_codes'

    id = Column(Integer, primary_key=True, index=True)
    code_hash = Column(String(64), unique=True, nullable=False, index=True)
    game_session_id = Column(Integer, ForeignKey('game_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    points_value = Column(Integer, nullable=False)

    status = Column(String(20), default='ACTIVE', nullable=False, index=True)  # 'ACTIVE', 'CLAIMED', 'EXPIRED', 'REVOKED'
    claimed_by_account_type = Column(String(32), nullable=True)  # 'CUSTOMER' | 'PARTNER'
    claimed_by_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    claimed_at = Column(DateTime, nullable=True)

    game_session = relationship('GameSession', backref='reward_codes')

    __table_args__ = (
        Index('idx_game_reward_status_expires', 'status', 'expires_at'),
    )

    @staticmethod
    def hash_code(raw_code: str) -> str:
        clean = (raw_code or '').strip().upper()
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_human_code() -> str:
        # Format: PLAY-XXXX-NNNN (e.g., PLAY-7F9B-2048)
        chars = ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(4))
        digits = f"{secrets.randbelow(9000) + 1000}"
        return f"PLAY-{chars}-{digits}"
