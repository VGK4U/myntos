"""
Core Configuration for FastAPI Backend
Preserves settings compatibility with Flask app
"""

import os
from dotenv import load_dotenv
load_dotenv()
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # App Configuration
    APP_NAME: str = "MNR Reference System API"
    VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"  # False in production, can be enabled via env var
    
    # Database Configuration (Preserve Flask database connection)
    DATABASE_URL: Optional[str] = None
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Security Configuration
    SECRET_KEY: str = "your-secret-key-here"  # Will be overridden by environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    # DC Protocol: Explicit production domains for TrustedHostMiddleware
    # Includes custom domain, Replit deployment domain, and localhost for dev
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "myntreal.com",
        "www.myntreal.com",
        "mnrteam.com",
        "www.mnrteam.com",
        "newbev.replit.app",
        "*.replit.app",
        "*.repl.co",
        "*.replit.dev"
    ]
    
    # Redis Configuration (for caching binary tree queries)
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # Email Configuration (preserve ReplitMail integration)
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    
    # MNR ID System Configuration
    # Original format: MNR1823XXXXX (MNR1823 + 5 random digits)
    # New users: 12-character format (MNR1823 + 5 digits, e.g., MNR182345678)
    # Legacy users: 10-12 character formats supported for backward compatibility
    MNR_ID_PREFIX: str = "MNR1823"  # Fixed prefix for all new MNR IDs
    MNR_ID_LENGTH: int = 12  # Standard length: MNR1823 + 5 digits = 12 chars
    MNR_ID_LEGACY_MIN_LENGTH: int = 10  # Legacy format minimum length
    
    # Income Calculation Settings (preserve exact rates)
    DAILY_CEILING_LIMIT: float = 50000.0  # ₹50,000 daily ceiling
    ADMIN_DEDUCTION_RATE: float = 8.0     # 8% admin deduction
    TDS_DEDUCTION_RATE: float = 2.0       # 2% TDS deduction
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        """Create database URL from environment or use PostgreSQL default"""
        # DC Protocol: Use DATABASE_URL as single source of truth (current dev database)
        # PROD_DATABASE_URL is only for production deployments
        db_url = os.getenv("DATABASE_URL") or os.getenv("PROD_DATABASE_URL")
        if db_url:
            # Fix legacy Neon SSL mode typo if present (sslmode=require. → sslmode=require)
            db_url = db_url.replace("sslmode=require.", "sslmode=require")
            # Strip sslmode=disable param when connecting to Neon (cloud requires SSL)
            # Harmless no-op when already on Helium (which legitimately uses sslmode=disable)
            return db_url
            
        # Fallback to SQLite for development
        return "sqlite:///./mlm_app.db"
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is provided via environment"""
        secret = os.getenv("SECRET_KEY", v)
        if secret == "your-secret-key-here":
            print("⚠️ WARNING: Using default secret key. Set SECRET_KEY environment variable for production!")
        return secret
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v: List[str]) -> List[str]:
        """Configure CORS origins based on environment"""
        # DC Protocol: Use "*" to allow all hosts - Replit's proxy handles host validation
        # Note: Starlette TrustedHostMiddleware doesn't support *.domain.com wildcards
        # Using "*" is safe because Replit's infrastructure validates incoming requests
        return ["*"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Constants for business logic (preserve exact Flask values)
class BusinessConstants:
    """Business constants that preserve exact Flask app logic"""
    
    # Income Types (preserve exact names)
    INCOME_TYPES = {
        "DIRECT_REFERRAL": "Direct Referral",
        "MATCHING_REFERRAL": "Matching Referral", 
        "VED_INCOME": "Ved Income",
        "GURU_DAKSHINA": "Guru Dakshina"
    }
    
    # User Types (preserve exact Flask types)
    USER_TYPES = {
        "USER": "User",
        "MEMBER": "Member", 
        "ADMIN": "Admin",
        "FINANCE_ADMIN": "Finance Admin",
        "SUPER_ADMIN": "Super Admin"
    }
    
    # Coupon Status (preserve exact Flask status)
    COUPON_STATUS = {
        "INACTIVE": "Inactive",
        "ACTIVE": "Active",
        "ACTIVATED": "Activated",
        "SEMI_ACTIVE": "Semi-Active"
    }
    
    # Placement Sides (preserve binary tree structure)
    PLACEMENT_SIDES = {
        "LEFT": "left",
        "RIGHT": "right"
    }
    
    # KYC Status (preserve exact Flask KYC system)
    KYC_STATUS = {
        "PENDING": "Pending",
        "SUBMITTED": "Submitted", 
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
        "SUPER_ADMIN_APPROVED": "Super Admin Approved"
    }

# Export business constants
business_constants = BusinessConstants()