"""
Promoter / Influencer Referral System — Data Models
DC Protocol: Additive only. Zero impact on existing tables.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.base import get_indian_time


class PromoInfluencer(Base):
    __tablename__ = "promo_influencers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    platforms = Column(String(500), nullable=True)          # comma-separated: instagram,youtube,facebook
    referral_code = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending,active,paused,inactive
    account_type = Column(String(20), nullable=False, default="unpaid")  # paid,unpaid
    is_vgk_member = Column(Boolean, default=False, nullable=False)
    vgk_member_id = Column(String(50), nullable=True)       # VGK partner_code e.g. VGK07101234
    vgk_registration_target = Column(Integer, nullable=True)  # min VGK signups to auto-activate
    notes = Column(Text, nullable=True)
    created_by_staff_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)


class PromoReferralEvent(Base):
    __tablename__ = "promo_referral_events"

    id = Column(Integer, primary_key=True, index=True)
    influencer_id = Column(Integer, ForeignKey("promo_influencers.id"), nullable=False, index=True)
    referral_code = Column(String(50), nullable=False, index=True)
    portal = Column(String(50), nullable=False)             # vgk,mnr_contact,partner,etc
    event_type = Column(String(50), nullable=False)         # registration,contact,signup
    source_ref_id = Column(String(100), nullable=True)      # e.g. VGK member code, CRM lead ID
    source_name = Column(String(200), nullable=True)
    source_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)


class PromoInfluencerAuth(Base):
    __tablename__ = "promo_influencer_auth"

    id = Column(Integer, primary_key=True, index=True)
    influencer_id = Column(Integer, ForeignKey("promo_influencers.id"), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
