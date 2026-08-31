from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class IncentiveProgram(Base):
    __tablename__ = "incentive_programs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1)
    segment_code = Column(String(30), nullable=False, index=True)  # 'SOLAR', 'EV', 'PROJECTS'
    program_code = Column(String(50), nullable=False, unique=True, index=True)  # 'SOLAR_V2_2026', 'EV_V2_2026'
    program_name = Column(String(200), nullable=False)
    max_pool_pct = Column(Numeric(5, 2), nullable=False, default=0.0)  # e.g. 8.50
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rate_configs = relationship("PositionRateConfig", back_populates="program", cascade="all, delete-orphan")


class PositionRateConfig(Base):
    __tablename__ = "position_rate_configs"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("incentive_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    position_name = Column(String(40), nullable=False)  # 'Channel Partner', 'Manager', 'Zonal Manager', 'Regional Manager', 'Director'
    stars = Column(Integer, nullable=False, default=1)
    required_active_team = Column(Integer, nullable=False, default=0)
    required_qualifying_files = Column(Integer, nullable=False, default=0)
    commission_pct = Column(Numeric(5, 2), nullable=False, default=0.0)  # e.g. 5.00, 6.50, 7.50, 8.25, 8.50
    base_income_amount = Column(Numeric(12, 2), nullable=True)  # e.g. 10000, 13000, 15000, 16500, 17000
    created_at = Column(DateTime, default=datetime.utcnow)

    program = relationship("IncentiveProgram", back_populates="rate_configs")


class MonthlySettlementBatch(Base):
    __tablename__ = "monthly_settlement_batches"
    __table_args__ = (
        UniqueConstraint('partner_id', 'settlement_period', 'program_id', name='uq_monthly_settlement_partner_period'),
    )

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("official_partners.id", ondelete="RESTRICT"), nullable=False, index=True)
    settlement_period = Column(String(7), nullable=False, index=True)  # e.g. '2026-08'
    program_id = Column(Integer, ForeignKey("incentive_programs.id", ondelete="RESTRICT"), nullable=False, index=True)
    net_payable = Column(Numeric(12, 2), nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default='PROCESSED')  # 'PROCESSED', 'CONFIRMED', 'PAID'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
