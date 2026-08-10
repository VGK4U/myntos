"""
Core Configuration for FastAPI Backend
Preserves settings compatibility with Flask app
"""

import os
from dotenv import load_dotenv
load_dotenv()
from typing import List, Optional, Any
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
        "vgk4u.com",
        "www.vgk4u.com",
        "*.vgk4u.com",
        "myntreal.com",
        "www.myntreal.com",
        "mnrteam.com",
        "www.mnrteam.com",
        "*.elasticbeanstalk.com",
        "newbev.replit.app",
        "*.replit.app",
        "*.repl.co",
        "*.replit.dev"
    ]
    
    # Redis Configuration (for caching binary tree queries)
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # Razorpay Configuration
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # A1Topup Configuration
    A1TOPUP_USERNAME: Optional[str] = None
    A1TOPUP_PASSWORD: Optional[str] = None
    A1TOPUP_TEST_MODE: bool = True
    
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

    # ── Release 1A & Phase 2D Feature Flags ──
    META_SYNC_ENABLED: bool = True
    META_ADS_READ_ENABLED: bool = True
    META_ADS_WRITE_ENABLED: bool = False
    CAPI_ENABLED: bool = False
    WA_AUDIT_ENABLED: bool = True
    WA_AI_ENABLED: bool = False
    VOICE_AI_ENABLED: bool = False
    AI_ORCHESTRATOR_ENABLED: bool = False
    CAMPAIGN_AUTOMATION_ENABLED: bool = False
    STRICT_ENCRYPTED_CREDS_ONLY: bool = True
    
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
        """Configure explicit allowed hosts for TrustedHostMiddleware"""
        return [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "vgk4u.com",
            "www.vgk4u.com",
            "*.vgk4u.com",
            "myntreal.com",
            "www.myntreal.com",
            "*.myntreal.com",
            "mnrteam.com",
            "www.mnrteam.com",
            "*.mnrteam.com",
            "*.elasticbeanstalk.com",
            "newbev.replit.app",
            "*.replit.app",
            "*.repl.co",
            "*.replit.dev"
        ]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Centralized Approved Public Domains List
APPROVED_PUBLIC_DOMAINS = {
    "myntreal.com",
    "www.myntreal.com",
    "mnrteam.com",
    "www.mnrteam.com",
    "vgk4u.com",
    "www.vgk4u.com"
}
DEFAULT_PUBLIC_DOMAIN = "https://www.vgk4u.com"

def get_safe_base_url(request: Optional[Any] = None) -> str:
    """
    Safely resolves the public base URL using an explicit approved-domain allowlist.
    Prevents Host Header Poisoning by validating against APPROVED_PUBLIC_DOMAINS.
    Defaults to DEFAULT_PUBLIC_DOMAIN (https://www.vgk4u.com) if request is missing or Host is untrusted.
    """
    if not request:
        return DEFAULT_PUBLIC_DOMAIN
    try:
        raw_host = request.headers.get("host", "").split(":")[0].strip().lower()
        if raw_host in APPROVED_PUBLIC_DOMAINS:
            scheme = request.headers.get("x-forwarded-proto", getattr(getattr(request, "url", None), "scheme", "https")).split(",")[0].strip()
            return f"{scheme}://{raw_host}"
    except Exception:
        pass
    return DEFAULT_PUBLIC_DOMAIN


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