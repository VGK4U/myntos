from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class RechargeTransaction(Base):
    """
    Model for tracking mobile recharges via A1Topup and payments via Razorpay.
    """
    __tablename__ = "recharge_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True, index=True) # Nullable for guest checkouts
    guest_email = Column(String, nullable=True) # For guest receipts
    guest_name = Column(String, nullable=True)
    mobile_number = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    circle = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    
    # Razorpay Payment Details
    razorpay_order_id = Column(String, unique=True, index=True, nullable=True)
    razorpay_payment_id = Column(String, unique=True, index=True, nullable=True)
    razorpay_signature = Column(String, nullable=True)
    payment_status = Column(String, default="Pending") # Pending, Paid, Failed
    
    # A1Topup API Details
    api_status = Column(String, default="Pending") # Pending, Success, Failed
    api_tx_id = Column(String, nullable=True) # A1Topup transaction ID
    api_operator_id = Column(String, nullable=True) # ID from telecom operator
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    # user = relationship("User", backref="recharge_history")

class RechargePlan(Base):
    """
    Model for storing static telecom recharge plans.
    """
    __tablename__ = "recharge_plans"

    id = Column(Integer, primary_key=True, index=True)
    operator = Column(String, nullable=False, index=True) # e.g., 'Airtel', 'Jio'
    circle = Column(String, nullable=True) # e.g., 'All India'
    amount = Column(Float, nullable=False)
    validity = Column(String, nullable=False) # e.g., '28 Days'
    data_benefit = Column(String, nullable=True) # e.g., '1.5 GB/Day'
    description = Column(String, nullable=True) # Detailed text
    created_at = Column(DateTime, default=datetime.utcnow)
