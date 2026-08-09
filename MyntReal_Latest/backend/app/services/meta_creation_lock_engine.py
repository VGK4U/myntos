"""
Meta Creation Lock & Idempotency Engine (Phase 2K.2 & 2L.1 Phase A)
1. Hard Creation Lock: Blocks creation of any campaign or adset other than
   Primary Campaign '120254919777680348' and Primary Ad Set '120254919777930348'.
2. Idempotency Fingerprint Engine v2: Calculates deterministic key
   SHA-256(canonical 13-parameter normalized pipe-delimited string).
   Preserves Fingerprint v1 backward compatibility.
3. Concurrency Protection: Uses PostgreSQL pg_advisory_xact_lock for deterministic
   transactional serialization across multiple FastAPI workers/processes.
"""

import hashlib
import logging
import unicodedata
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

PRIMARY_CAMPAIGN_ID = "120254919777680348"
PRIMARY_ADSET_ID = "120254919777930348"


def verify_creation_lock(target_campaign_id: str, target_adset_id: str) -> Dict[str, Any]:
    """
    Enforces hard creation lock: Only primary campaign and primary adset allowed.
    """
    if target_campaign_id != PRIMARY_CAMPAIGN_ID:
        return {
            "allowed": False,
            "status": "CREATION_LOCKED",
            "reason": f"Campaign creation locked. Target campaign {target_campaign_id} != primary campaign {PRIMARY_CAMPAIGN_ID}."
        }
    if target_adset_id != PRIMARY_ADSET_ID:
        return {
            "allowed": False,
            "status": "CREATION_LOCKED",
            "reason": f"AdSet creation locked. Target adset {target_adset_id} != primary adset {PRIMARY_ADSET_ID}."
        }
    return {"allowed": True, "status": "CREATION_PERMITTED"}


def calculate_idempotency_fingerprint(
    company_id: int,
    campaign_id: str,
    adset_id: str,
    creative_text: str,
    language: str = "en_te",
    aspect_ratio: str = "1:1"
) -> str:
    """
    Fingerprint v1 Legacy Generator (Preserved for Backward Compatibility).
    """
    raw_str = f"{company_id}:{campaign_id}:{adset_id}:{creative_text.strip()}:{language}:{aspect_ratio}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def calculate_idempotency_fingerprint_v2(
    company_id: int,
    ad_account_id: str = "act_560062103113819",
    campaign_id: str = PRIMARY_CAMPAIGN_ID,
    adset_id: str = PRIMARY_ADSET_ID,
    page_id: str = "894208310452980",
    image_hash: str = "7db4abcb49f4c4fa2d37d6bac21aeb56",
    headline: str = "",
    primary_text: str = "",
    cta: str = "LEARN_MORE",
    destination_url: str = "https://facebook.com/894208310452980",
    language: str = "en_te",
    aspect_ratio: str = "1:1",
    version: int = 2
) -> str:
    """
    Fingerprint v2 Canonical Generator.
    Normalizes inputs via NFC Unicode and builds deterministic 13-parameter pipe-delimited string.
    """
    def norm(val: Optional[str]) -> str:
        if val is None:
            return ""
        return unicodedata.normalize("NFC", str(val).strip())

    canonical_parts = [
        f"company_id:{company_id}",
        f"ad_account_id:{norm(ad_account_id)}",
        f"campaign_id:{norm(campaign_id)}",
        f"adset_id:{norm(adset_id)}",
        f"page_id:{norm(page_id)}",
        f"image_hash:{norm(image_hash)}",
        f"headline:{norm(headline)}",
        f"primary_text:{norm(primary_text)}",
        f"cta:{norm(cta)}",
        f"destination_url:{norm(destination_url)}",
        f"language:{norm(language)}",
        f"aspect_ratio:{norm(aspect_ratio)}",
        f"version:{version}"
    ]
    canonical_str = "|".join(canonical_parts)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def check_existing_ad_idempotency(
    db: Session,
    company_id: int,
    fingerprint: str
) -> Optional[Dict[str, Any]]:
    """
    Checks if an ad with the exact same fingerprint already exists in PostgreSQL database.
    Transactional Locking: Uses PostgreSQL pg_advisory_xact_lock to protect 'no existing row' race conditions.
    """
    try:
        # Acquire PostgreSQL transaction-level advisory lock on hashtext(company_id + fingerprint)
        lock_key = f"{company_id}:{fingerprint}"
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": lock_key})
    except Exception as e:
        logger.warning(f"[IDEMPOTENCY-LOCK-WARNING] Could not acquire advisory lock: {e}")

    row = db.execute(text("""
        SELECT id, ad_id, creative_id, status, name, fingerprint_version
        FROM meta_ads
        WHERE company_id = :cid AND ad_fingerprint = :fp
        LIMIT 1
    """), {"cid": company_id, "fp": fingerprint}).fetchone()

    if row:
        return {
            "status": "ALREADY_EXISTS",
            "myntos_db_id": row[0],
            "real_meta_id": row[1],
            "creative_id": row[2],
            "ad_status": row[3],
            "name": row[4],
            "fingerprint_version": row[5] or 1,
            "message": "Deterministic idempotency lock triggered. Returning existing real Meta Ad ID."
        }
    return None

