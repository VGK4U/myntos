"""
Expense Category Models - Hierarchical category system
Main Category → Sub Category structure for expense classification
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class ExpenseMainCategory(BaseModel):
    """
    Main Expense Category (e.g., Revenue, Operations, Marketing)
    Manages top-level expense classification
    """
    __tablename__ = 'expense_main_category'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_direct_expense = Column(Boolean, default=False, nullable=False)
    
    created_by_id = Column(String(50), nullable=False)
    updated_by_id = Column(String(50), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    sub_categories = relationship("ExpenseSubCategory", back_populates="main_category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ExpenseMainCategory {self.name}>'


class ExpenseSubCategory(BaseModel):
    """
    Sub Expense Category (e.g., Operational, Marketing, Infrastructure)
    Links to Main Category for hierarchical structure
    """
    __tablename__ = 'expense_sub_category'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    main_category_id = Column(Integer, ForeignKey('expense_main_category.id'), nullable=False)
    
    created_by_id = Column(String(50), nullable=False)
    updated_by_id = Column(String(50), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    main_category = relationship("ExpenseMainCategory", back_populates="sub_categories")
    
    def __repr__(self):
        return f'<ExpenseSubCategory {self.name} ({self.main_category.name})>'
