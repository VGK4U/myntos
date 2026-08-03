from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel, get_indian_time
from sqlalchemy.orm import relationship

class CommunityService(BaseModel):
    """
    Community Services master configurations
    """
    __tablename__ = 'community_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(200), nullable=False)
    short_name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)  # Rich Text Editor content
    banner_images = Column(JSONB, nullable=True, default=list)  # Universal Upload images
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    applicable_verticals = Column(JSONB, nullable=True, default=list)  # e.g., ["Solar"]
    status = Column(String(20), default='ACTIVE', nullable=False)  # ACTIVE, PAUSED, DELETED
    ai_prompt = Column(String, nullable=True)  # AI Generation Prompt instructions
    settings = Column(JSONB, nullable=True, default=dict)  # Section-by-section overrides and media urls
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    registrations = relationship("CommunityRegistration", back_populates="service")


class CommunityRegistration(BaseModel):
    """
    Registrations of communities to specific community services
    """
    __tablename__ = 'community_registrations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    community_service_id = Column(Integer, ForeignKey('community_services.id', ondelete='CASCADE'), nullable=False)
    submission_date = Column(DateTime, default=get_indian_time, nullable=False)
    
    association_name = Column(String(200), nullable=True)
    primary_name = Column(String(200), nullable=False)
    primary_phone_1 = Column(String(20), nullable=False)
    primary_phone_2 = Column(String(20), nullable=True)
    
    secondary_name = Column(String(200), nullable=True)
    secondary_phone_1 = Column(String(20), nullable=True)
    secondary_phone_2 = Column(String(20), nullable=True)
    
    area = Column(String(200), nullable=False)
    pin_code = Column(String(10), nullable=False)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    
    ref1_member_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)
    ref2_member_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)
    
    referral_type = Column(String(50), default='direct', nullable=True)
    referral_code = Column(String(100), nullable=True)
    
    kyc_uploads = Column(JSONB, nullable=True, default=list)  # Aadhaar, PAN uploads
    status = Column(String(20), default='PENDING', nullable=False)  # PENDING, APPROVED, REJECTED
    user_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)  # Associated partner login credentials
    google_location = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    service = relationship("CommunityService", back_populates="registrations")
    ref1_member = relationship("OfficialPartner", foreign_keys=[ref1_member_id])
    ref2_member = relationship("OfficialPartner", foreign_keys=[ref2_member_id])
    user_partner = relationship("OfficialPartner", foreign_keys=[user_id])


class CommunityCommission(BaseModel):
    """
    Commission payouts for Community registrations linked to lead milestones
    """
    __tablename__ = 'community_commissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    community_id = Column(Integer, ForeignKey('community_registrations.id', ondelete='CASCADE'), nullable=False)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), default='RELEASED', nullable=False)  # RELEASED, PENDING, CANCELLED
    payout_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    community = relationship("CommunityRegistration")
    lead = relationship("CRMLead")
