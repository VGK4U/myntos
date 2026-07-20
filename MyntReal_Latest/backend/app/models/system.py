"""
System configuration and checkpoint models
Tracks production start dates and system-wide reset logic
"""

from sqlalchemy import Column, String, Integer, DateTime, Text
from app.models.base import BaseModel, get_indian_time


class SystemCheckpoint(BaseModel):
    """
    System checkpoints for data reset and validation
    Prevents recalculation of awards/income before checkpoint dates
    """
    __tablename__ = 'system_checkpoints'
    
    id = Column(Integer, primary_key=True)
    checkpoint_name = Column(String(100), unique=True, nullable=False)
    checkpoint_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f'<SystemCheckpoint {self.checkpoint_name}: {self.checkpoint_date}>'
