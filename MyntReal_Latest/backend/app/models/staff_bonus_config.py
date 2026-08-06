from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, Numeric
from datetime import datetime
from app.models.base import Base

class StaffQuarterlyBonusConfig(Base):
    """
    Model for storing dynamic quarterly bonus targets, rates, and multipliers.
    """
    __tablename__ = "staff_quarterly_bonus_configs"

    id = Column(Integer, primary_key=True, index=True)
    period_name = Column(String(64), nullable=False, unique=True, index=True) # e.g. 'Aug-Sep 2026', 'Q4 2026'
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    min_target_files = Column(Integer, nullable=False, default=50)
    base_bonus_per_file = Column(Numeric(10, 2), nullable=False, default=150.00)
    high_performance_multiplier = Column(Numeric(5, 2), nullable=False, default=1.20) # 120%
    low_performance_multiplier = Column(Numeric(5, 2), nullable=False, default=0.50) # 50%
    kra_activity_threshold_pct = Column(Numeric(5, 2), nullable=False, default=80.00) # 80%
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
