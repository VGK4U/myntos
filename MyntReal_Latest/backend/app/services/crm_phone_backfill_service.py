"""
Non-Destructive Historical Backfill Service for CRM Phone Identity (Stage 2B Phase 2R-3E-I).

Authoritative Backfill Process:
- Reads all existing crm_leads (phone & alternate_phone).
- Uses the Phase 2R-3D canonical normalization contract (re.sub, >=10 -> trailing 10, 8-9 exact, <8 -> NULL).
- Populates crm_lead_phones (Phone Association Layer) with UNIQUE(tenant_id, company_id, lead_id, phone_norm).
- Populates crm_lead_phone_provenances (Phone Provenance Layer) tracking originating fields and raw values.
- If a lead contains the same normalized phone in both phone and alternate_phone, creates ONE association and TWO provenance records.
- Preserves all 15 collision groups independently without resolving or merging.
- Preserves Lead 7635 and Lead 7636 as independent records.
- 100% non-destructive: Zero UPDATE or DELETE on crm_leads.
- Idempotent and safely restartable.
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.services.crm_dedup_service import normalize_phone

logger = logging.getLogger(__name__)


def execute_crm_phone_backfill(db: Session, batch_size: int = 500) -> Dict[str, Any]:
    """
    Executes the historical backfill from crm_leads into crm_lead_phones and crm_lead_phone_provenances.
    """
    logger.info("Starting CRM phone identity backfill...")
    
    # 1. Fetch total leads count
    total_leads = db.execute(text("SELECT count(*) FROM crm_leads")).scalar() or 0
    
    # Metrics
    stats = {
        "total_leads_scanned": total_leads,
        "leads_with_primary_phone": 0,
        "leads_with_alt_phone": 0,
        "leads_with_identical_primary_and_alt": 0,
        "leads_unnormalizable": 0,
        "associations_created": 0,
        "associations_existing": 0,
        "provenances_created": 0,
        "provenances_existing": 0,
    }
    
    # 2. Query all leads in ordered batches
    offset = 0
    while True:
        leads = db.execute(text("""
            SELECT id, tenant_id, company_id, phone, alternate_phone, source, created_at 
            FROM crm_leads 
            ORDER BY id ASC 
            LIMIT :limit OFFSET :offset
        """), {"limit": batch_size, "offset": offset}).fetchall()
        
        if not leads:
            break
            
        for lead in leads:
            lid = lead.id
            tid = lead.tenant_id
            cid = lead.company_id
            p_raw = lead.phone
            alt_raw = lead.alternate_phone
            src = lead.source or 'crm_leads_backfill'
            
            p_norm = normalize_phone(p_raw)
            alt_norm = normalize_phone(alt_raw)
            
            if not p_norm and not alt_norm:
                stats["leads_unnormalizable"] += 1
                continue
                
            if p_norm:
                stats["leads_with_primary_phone"] += 1
            if alt_norm:
                stats["leads_with_alt_phone"] += 1
                
            # Case 1: Same normalized phone in both primary and alternate
            if p_norm and alt_norm and p_norm == alt_norm:
                stats["leads_with_identical_primary_and_alt"] += 1
                assoc_id, created = _get_or_create_association(
                    db, tid, cid, lid, p_norm, role='PRIMARY', is_primary=True
                )
                if created:
                    stats["associations_created"] += 1
                else:
                    stats["associations_existing"] += 1
                    
                # Create provenance for primary field
                if _create_provenance_if_missing(db, assoc_id, tid, cid, lid, 'phone', p_raw, src):
                    stats["provenances_created"] += 1
                else:
                    stats["provenances_existing"] += 1
                    
                # Create provenance for alternate field
                if _create_provenance_if_missing(db, assoc_id, tid, cid, lid, 'alternate_phone', alt_raw, src):
                    stats["provenances_created"] += 1
                else:
                    stats["provenances_existing"] += 1
                    
            else:
                # Case 2: Distinct primary and alternate
                if p_norm:
                    assoc_id, created = _get_or_create_association(
                        db, tid, cid, lid, p_norm, role='PRIMARY', is_primary=True
                    )
                    if created:
                        stats["associations_created"] += 1
                    else:
                        stats["associations_existing"] += 1
                    if _create_provenance_if_missing(db, assoc_id, tid, cid, lid, 'phone', p_raw, src):
                        stats["provenances_created"] += 1
                    else:
                        stats["provenances_existing"] += 1
                        
                if alt_norm:
                    # Role is ALTERNATE; is_primary is False unless lead had no valid primary
                    is_prim = False if p_norm else True
                    role = 'ALTERNATE' if p_norm else 'PRIMARY'
                    assoc_id, created = _get_or_create_association(
                        db, tid, cid, lid, alt_norm, role=role, is_primary=is_prim
                    )
                    if created:
                        stats["associations_created"] += 1
                    else:
                        stats["associations_existing"] += 1
                    if _create_provenance_if_missing(db, assoc_id, tid, cid, lid, 'alternate_phone', alt_raw, src):
                        stats["provenances_created"] += 1
                    else:
                        stats["provenances_existing"] += 1
                        
        db.commit()
        offset += len(leads)
        
    logger.info("Backfill completed successfully: %s", stats)
    return stats


def _get_or_create_association(
    db: Session,
    tenant_id: int,
    company_id: int,
    lead_id: int,
    phone_norm: str,
    role: str = 'PRIMARY',
    is_primary: bool = True
) -> (int, bool):
    """
    Retrieves or inserts an association in crm_lead_phones.
    Returns (association_id, was_created).
    """
    # Attempt insert with ON CONFLICT DO NOTHING
    insert_sql = text("""
        INSERT INTO crm_lead_phones (
            tenant_id, company_id, lead_id, phone_norm, phone_role, is_primary, is_active, verification_status
        ) VALUES (
            :t, :c, :l, :p, :role, :is_prim, TRUE, 'UNVERIFIED'
        )
        ON CONFLICT (tenant_id, company_id, lead_id, phone_norm) DO NOTHING
        RETURNING id;
    """)
    row = db.execute(insert_sql, {
        "t": tenant_id, "c": company_id, "l": lead_id, 
        "p": phone_norm, "role": role, "is_prim": is_primary
    }).fetchone()
    
    if row is not None:
        return row[0], True
        
    # Already existed, query ID
    existing_id = db.execute(text("""
        SELECT id FROM crm_lead_phones 
        WHERE tenant_id = :t AND company_id = :c AND lead_id = :l AND phone_norm = :p
    """), {"t": tenant_id, "c": company_id, "l": lead_id, "p": phone_norm}).scalar()
    
    return existing_id, False


def _create_provenance_if_missing(
    db: Session,
    phone_association_id: int,
    tenant_id: int,
    company_id: int,
    lead_id: int,
    source_field: str,
    raw_value: Optional[str],
    source_channel: str
) -> bool:
    """
    Inserts a provenance row if it doesn't already exist for this association and source field.
    Returns True if created, False if already existed.
    """
    exists = db.execute(text("""
        SELECT 1 FROM crm_lead_phone_provenances 
        WHERE phone_association_id = :aid AND source_field = :sf
    """), {"aid": phone_association_id, "sf": source_field}).scalar()
    
    if exists:
        return False
        
    db.execute(text("""
        INSERT INTO crm_lead_phone_provenances (
            phone_association_id, tenant_id, company_id, lead_id, source_field, raw_value, source_channel
        ) VALUES (
            :aid, :t, :c, :l, :sf, :raw, :chan
        )
    """), {
        "aid": phone_association_id, "t": tenant_id, "c": company_id,
        "l": lead_id, "sf": source_field, "raw": raw_value, "chan": source_channel
    })
    return True
