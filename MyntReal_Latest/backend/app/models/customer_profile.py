"""
Customer Profile Model (DC Protocol / Oct 2026)
Represents a retail/consumer customer account across all MyntOS & VGK4U verticals:
- Mobile & Utility Bill Payments (Recharges, Electricity, DTH, FASTag, Gas)
- Scratch Cards & Rewards Cashback
- Solar Rooftop Customers (Quotes & Installation Status)
- EV Vehicle, Battery & Charging Customers
- EVolution ETC Training Students
"""
from app.core.timezone import get_indian_time
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from app.core.database import Base


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False, index=True)
    customer_name = Column(String(128), nullable=False)
    pincode = Column(String(10), nullable=False)
    security_pin_hash = Column(String(255), nullable=False)
    email = Column(String(128), nullable=True)
    city = Column(String(64), nullable=True)
    state = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    profile_metadata = Column(Text, nullable=True)  # JSON-encoded extra preferences/saved billing accounts

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        Index("idx_customer_profile_mobile", "mobile_number"),
    )

    def __repr__(self):
        return f"<CustomerProfile id={self.id} mobile={self.mobile_number} name={self.customer_name}>"
