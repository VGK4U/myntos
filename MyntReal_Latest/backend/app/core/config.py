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
        "testserver",
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
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    
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
    META_ADS_WRITE_ENABLED: bool = True
    CAPI_ENABLED: bool = False
    WA_AUDIT_ENABLED: bool = True
    WA_AI_ENABLED: bool = False
    VOICE_AI_ENABLED: bool = True
    AI_ORCHESTRATOR_ENABLED: bool = False
    CAMPAIGN_AUTOMATION_ENABLED: bool = False
    STRICT_ENCRYPTED_CREDS_ONLY: bool = True
    
    # ── In-App PSTN Telephony & Call Session Engine Configuration ──
    MYNTREAL_OUTBOUND_CALLING_NUMBER: str = os.getenv("MYNTREAL_OUTBOUND_CALLING_NUMBER", "+918031728899")
    TELEPHONY_PROVIDER: str = os.getenv("TELEPHONY_PROVIDER", "plivo")
    TELEPHONY_ACCOUNT_ID: Optional[str] = os.getenv("TELEPHONY_ACCOUNT_ID")
    TELEPHONY_API_KEY: Optional[str] = os.getenv("TELEPHONY_API_KEY")
    TELEPHONY_API_SECRET: Optional[str] = os.getenv("TELEPHONY_API_SECRET")
    TELEPHONY_WEBHOOK_SECRET: Optional[str] = os.getenv("TELEPHONY_WEBHOOK_SECRET")
    TELEPHONY_APPLICATION_SID: Optional[str] = os.getenv("TELEPHONY_APPLICATION_SID")

    # ── Plivo Cloud Telephony ──
    PLIVO_AUTH_ID: Optional[str] = os.getenv("PLIVO_AUTH_ID", "MAMTLIY2U4MTKTN2E3NC")
    PLIVO_AUTH_TOKEN: Optional[str] = os.getenv("PLIVO_AUTH_TOKEN", "Nzg3MzZmZWQtNGRmNi00OWUxLTdhZjItMDQwNWYy")
    PLIVO_APP_ID: Optional[str] = os.getenv("PLIVO_APP_ID", "10583407997011554")
    PLIVO_DEFAULT_CALLER_ID: str = os.getenv("PLIVO_DEFAULT_CALLER_ID", "+918031728899")

    # ── Mobile VoIP Push Signaling (Screen-Off Calling Phase 2) ──
    ENABLE_MOBILE_VOIP_PUSH: bool = os.getenv("ENABLE_MOBILE_VOIP_PUSH", "true").lower() == "true"
    FCM_PROJECT_ID: Optional[str] = os.getenv("FCM_PROJECT_ID", "myntrealosg")
    FCM_SERVICE_ACCOUNT_JSON: Optional[str] = os.getenv(
        "FCM_SERVICE_ACCOUNT_JSON",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firebase-service-account.json"))
        if os.path.exists(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firebase-service-account.json")))
        else None
    )
    APNS_KEY_ID: Optional[str] = os.getenv("APNS_KEY_ID")
    APNS_TEAM_ID: Optional[str] = os.getenv("APNS_TEAM_ID")
    APNS_AUTH_KEY_PATH: Optional[str] = os.getenv("APNS_AUTH_KEY_PATH")
    APNS_USE_SANDBOX: bool = os.getenv("APNS_USE_SANDBOX", "true").lower() == "true"

    # ── WhatsApp API Centralized Business Contact Numbers & Signature Settings ──
    WHATSAPP_PRIMARY_BUSINESS_NUMBER: str = os.getenv("WHATSAPP_PRIMARY_BUSINESS_NUMBER", "+91 85858 52738")
    WHATSAPP_SECONDARY_BUSINESS_NUMBER: str = os.getenv("WHATSAPP_SECONDARY_BUSINESS_NUMBER", "+91 8897797667")
    WHATSAPP_BUSINESS_SIGNATURE_COMPANY: str = os.getenv("WHATSAPP_BUSINESS_SIGNATURE_COMPANY", "Mynt Real")

    # ── Ivy / IVR Telephony Business Contact Numbers ──
    IVY_PRIMARY_BUSINESS_NUMBER: str = os.getenv("IVY_PRIMARY_BUSINESS_NUMBER", "+91 85858 52738")
    IVY_SECONDARY_BUSINESS_NUMBER: str = os.getenv("IVY_SECONDARY_BUSINESS_NUMBER", "+91 80317 28899")
    IVY_BUSINESS_SIGNATURE_COMPANY: str = os.getenv("IVY_BUSINESS_SIGNATURE_COMPANY", "Mynt Real")

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        """Create database URL from environment or use PostgreSQL default"""
        # DC Protocol: Use DATABASE_URL as single source of truth (current dev database)
        # PROD_DATABASE_URL is only for production deployments
        db_url = os.getenv("DATABASE_URL") or os.getenv("PROD_DATABASE_URL")
        if db_url:
            # Fix legacy Neon SSL mode typo if present (sslmode=require. → sslmode=require)
            db_url = db_url.replace("sslmode=require.", "sslmode=require")
            # DC Protocol (ARCHITECTURAL FIX - Sep 2026): Production DB Isolation Guard
            # Detect AWS Elastic Beanstalk / Linux server environment vs local macOS dev
            is_eb = os.path.exists("/var/app") or os.path.exists("/opt/elasticbeanstalk")
            is_prod = (
                is_eb
                or os.getenv("ENVIRONMENT", "").lower() == "production"
                or os.getenv("NODE_ENV", "").lower() == "production"
            )
            if "rds.amazonaws.com" in db_url and not is_prod:
                if os.getenv("ALLOW_PROD_DB_ACCESS") != "1":
                    print("[DC-DB-GUARD] 🛡️ Blocked silent local connection to production RDS! Defaulting to local PostgreSQL (port 5433). Set ALLOW_PROD_DB_ACCESS=1 to override.", flush=True)
                    return "postgresql://postgres:postgres@localhost:5433/myntreal_dev"
            return db_url
            
        # Fallback to SQLite for development
        return "sqlite:///./mlm_app.db"
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is provided via environment"""
        secret = os.getenv("SECRET_KEY", v)
        is_eb = os.path.exists("/var/app") or os.path.exists("/opt/elasticbeanstalk")
        is_prod = (
            is_eb
            or os.getenv("ENVIRONMENT", "").lower() == "production"
            or os.getenv("NODE_ENV", "").lower() == "production"
        )
        if secret == "your-secret-key-here" or not secret:
            if is_prod:
                raise ValueError("CRITICAL: SECRET_KEY is missing or insecure in PRODUCTION. App will not start.")
            print("⚠️ WARNING: Using default secret key. Set SECRET_KEY environment variable for production!")
        return secret
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v: List[str]) -> List[str]:
        """Configure explicit allowed hosts for TrustedHostMiddleware"""
        return [
            "*",
            "testserver",
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