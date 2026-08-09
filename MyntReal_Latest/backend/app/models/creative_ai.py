"""
Creative AI Data Models (Phase 2H Integration Layer)
Additive database schema for Creative Briefs, Image Generations, Quality Scores, and Asset Records.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class CreativeBriefModel(Base):
    __tablename__ = "creative_briefs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    vertical = Column(String(50), nullable=False, default="SOLAR")
    product_name = Column(String(200), nullable=False)
    target_location = Column(String(200), nullable=False)
    target_audience = Column(String(200), default="Homeowners")
    objective = Column(String(100), default="OUTCOME_LEADS")
    headline_text = Column(String(300))
    primary_text = Column(Text)
    cta_type = Column(String(50), default="LEARN_MORE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CreativeGenerationModel(Base):
    __tablename__ = "creative_generations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, default=1, index=True)
    brief_id = Column(Integer, ForeignKey("creative_briefs.id"), nullable=True)
    concept_name = Column(String(150), nullable=False)
    layout_template = Column(String(100), default="LIFESTYLE")
    aspect_ratio = Column(String(20), default="1:1")
    resolution = Column(String(50), default="1080x1080")
    provider_name = Column(String(100), default="MockProductionCreativeProvider")
    image_url_or_path = Column(Text)
    quality_score = Column(Float, default=85.0)
    decision_status = Column(String(50), default="PRODUCTION_READY")
    attempt_count = Column(Integer, default=1)
    is_brand_composited = Column(Boolean, default=True)
    is_typography_rendered = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
