"""
Income Category Models — Hierarchical category system
Main Category → Sub Category for income classification (In & Out Cat.)
DC Protocol: Mirrors expense_category structure for consistency
Created: May 2026
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class IncomeMainCategory(BaseModel):
    """
    Main Income Category (e.g., Sales Revenue, Service Revenue)
    """
    __tablename__ = 'income_main_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    created_by_id = Column(String(50), nullable=False)
    updated_by_id = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sub_categories = relationship("IncomeSubCategory", back_populates="main_category", cascade="all, delete-orphan")

    def __repr__(self):
        return f'<IncomeMainCategory {self.name}>'


class IncomeSubCategory(BaseModel):
    """
    Sub Income Category (e.g., Product Sales, Consulting Fees)
    """
    __tablename__ = 'income_sub_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    main_category_id = Column(Integer, ForeignKey('income_main_category.id'), nullable=False)

    created_by_id = Column(String(50), nullable=False)
    updated_by_id = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    main_category = relationship("IncomeMainCategory", back_populates="sub_categories")

    def __repr__(self):
        return f'<IncomeSubCategory {self.name}>'
