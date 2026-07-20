from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, get_indian_time
from datetime import datetime

class SuperAdminSession(Base):
    __tablename__ = 'super_admin_session'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    session_token = Column(String(255), nullable=False, unique=True)
    operation_type = Column(String(100), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    admin = relationship('User', foreign_keys=[admin_id], backref='admin_sessions')
    
    def is_valid(self):
        return self.is_verified and self.expires_at > datetime.utcnow()
    
    def __repr__(self):
        return f'<SuperAdminSession {self.admin_id} - {self.operation_type}>'
