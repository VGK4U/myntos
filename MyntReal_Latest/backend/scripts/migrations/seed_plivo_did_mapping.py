"""
Data Migration Script: Seed Plivo Primary Inbound DID Mapping
Maps +918031728899 to Company ID 1 (Plivo Provider).
Idempotent and non-destructive.
Created: Sep 2026
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.database import SessionLocal
from app.models.operator_calls import TelephonyDIDMapping
from app.services.telephony.flow_interpreter import CallFlowInterpreter


def seed_plivo_did():
    db = SessionLocal()
    target_did = "+918031728899"
    target_company_id = 1
    target_provider = "plivo"

    try:
        mapping = db.query(TelephonyDIDMapping).filter(
            TelephonyDIDMapping.did_number == target_did
        ).first()

        if mapping:
            print(f"[SEED-DID] Existing mapping found (ID={mapping.id}). Updating to target parameters...")
            mapping.company_id = target_company_id
            mapping.provider = target_provider
            mapping.is_active = True
        else:
            print(f"[SEED-DID] Creating new TelephonyDIDMapping for {target_did}...")
            mapping = TelephonyDIDMapping(
                did_number=target_did,
                company_id=target_company_id,
                provider=target_provider,
                is_active=True
            )
            db.add(mapping)

        db.commit()
        db.refresh(mapping)

        print(f"✅ TelephonyDIDMapping saved successfully:")
        print(f"   ID: {mapping.id}")
        print(f"   DID Number: {mapping.did_number}")
        print(f"   Company ID: {mapping.company_id}")
        print(f"   Provider: {mapping.provider}")
        print(f"   Is Active: {mapping.is_active}")
        print(f"   Created At: {mapping.created_at}")

        # Verification step
        resolved_cid = CallFlowInterpreter._resolve_company_from_did(db, target_did)
        print(f"\n[VERIFICATION] _resolve_company_from_did('{target_did}') -> {resolved_cid}")
        assert resolved_cid == target_company_id, f"Resolution mismatch: expected {target_company_id}, got {resolved_cid}"
        print("✅ Resolution verified successfully.")

        return mapping.to_dict()

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding Plivo DID mapping: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_plivo_did()
