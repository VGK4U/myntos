"""
Authoritative CRM Phone Domain Orchestrator & Synchronization Service (Stage 2B Phase 2R-3E).

Responsibilities:
1. Transactional synchronization between:
     - crm_leads.phone (legacy compatibility)
     - crm_leads.alternate_phone (legacy compatibility)
     - crm_lead_phones (authoritative association layer, Model-B+ uniqueness)
     - crm_lead_phone_provenances (non-destructive provenance tracking)
2. Preserves strict multi-tenant and company isolation: (tenant_id, company_id, lead_id).
3. Enforces deterministic advisory locking across all candidate identities.
4. Symmetric lifecycle handling for primary and alternate phones:
     - Creation
     - Update / Swap
     - Removal
     - Stale association deactivation (is_active=False)
     - Previously deactivated association reactivation
5. Non-destructive provenance logging (appends observations with source_field, raw_value, source_channel, source_ref, captured_at).
6. Atomicity: Operates strictly within caller's transaction; no premature commits.
"""

import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Sequence, Tuple
from sqlalchemy import text, or_
from sqlalchemy.orm import Session

from app.models.crm import CRMLead, CRMLeadPhone, CRMLeadPhoneProvenance
from app.services.crm_dedup_service import normalize_phone, acquire_phone_locks

logger = logging.getLogger(__name__)


def sync_lead_phone_identities(
    db: Session,
    lead: CRMLead,
    phone_raw: Optional[str] = None,
    alternate_phone_raw: Optional[str] = None,
    source_channel: str = 'manual',
    source_ref: Optional[str] = None,
    with_lock: bool = True
) -> Dict[str, Any]:
    """
    Authoritative phone synchronization function.
    Must be called within an active transaction whenever a CRMLead is created or its phone/alternate_phone is updated.
    
    Guarantees:
    - If lead.id is not yet assigned, flushes the session to acquire lead.id within the active transaction.
    - Locks both primary and alternate phone identities using deterministic lexicographical advisory locks.
    - Synchronizes crm_lead_phones and crm_lead_phone_provenances.
    - Does NOT commit the session; leaves final commit/rollback to the caller.
    """
    if lead is None:
        raise ValueError("sync_lead_phone_identities requires a valid CRMLead instance")

    # Ensure lead has an ID within the current transaction
    if getattr(lead, 'id', None) is None:
        db.flush()

    lead_id = lead.id
    tenant_id = lead.tenant_id
    company_id = lead.company_id

    if not tenant_id or not company_id:
        raise ValueError(f"sync_lead_phone_identities requires positive tenant_id and company_id (lead_id={lead_id})")

    # If raw strings not provided, fall back to lead attributes
    if phone_raw is None and hasattr(lead, 'phone'):
        phone_raw = lead.phone
    if alternate_phone_raw is None and hasattr(lead, 'alternate_phone'):
        alternate_phone_raw = lead.alternate_phone

    # Canonical normalization
    p_norm = normalize_phone(phone_raw)
    alt_norm = normalize_phone(alternate_phone_raw)

    # Acquire deterministic advisory locks covering both identities
    if with_lock:
        lock_identities = [p for p in (p_norm, alt_norm) if p]
        if lock_identities:
            acquire_phone_locks(db, tenant_id, company_id, lock_identities)

    # Fetch existing phone associations for this lead
    existing_assocs = db.query(CRMLeadPhone).filter(
        CRMLeadPhone.tenant_id == tenant_id,
        CRMLeadPhone.company_id == company_id,
        CRMLeadPhone.lead_id == lead_id
    ).all()
    existing_by_norm: Dict[str, CRMLeadPhone] = {a.phone_norm: a for a in existing_assocs}

    now_utc = datetime.utcnow()
    primary_assoc: Optional[CRMLeadPhone] = None
    alternate_assoc: Optional[CRMLeadPhone] = None

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Primary Phone Synchronization
    # ─────────────────────────────────────────────────────────────────────────
    if p_norm:
        if p_norm in existing_by_norm:
            assoc = existing_by_norm[p_norm]
            assoc.is_primary = True
            assoc.is_active = True
            assoc.phone_role = 'PRIMARY'
            assoc.updated_at = now_utc
            primary_assoc = assoc
        else:
            assoc = CRMLeadPhone(
                tenant_id=tenant_id,
                company_id=company_id,
                lead_id=lead_id,
                phone_norm=p_norm,
                phone_role='PRIMARY',
                is_primary=True,
                is_active=True,
                verification_status='UNVERIFIED',
                created_at=now_utc,
                updated_at=now_utc
            )
            db.add(assoc)
            db.flush()
            existing_by_norm[p_norm] = assoc
            primary_assoc = assoc

        # Append non-destructive provenance observation for primary phone
        prov_primary = CRMLeadPhoneProvenance(
            phone_association_id=primary_assoc.id,
            tenant_id=tenant_id,
            company_id=company_id,
            lead_id=lead_id,
            source_field='phone',
            raw_value=str(phone_raw)[:100] if phone_raw else None,
            source_channel=source_channel,
            source_ref=str(source_ref) if source_ref else None,
            captured_at=now_utc
        )
        db.add(prov_primary)

        # Demote/deactivate any previous primary association on this lead
        for norm, old_assoc in existing_by_norm.items():
            if norm != p_norm:
                if old_assoc.is_primary:
                    old_assoc.is_primary = False
                    old_assoc.updated_at = now_utc
                # If this old association is not the current alternate phone, deactivate it
                if norm != alt_norm:
                    if old_assoc.is_active:
                        old_assoc.is_active = False
                        old_assoc.updated_at = now_utc
    else:
        # Primary phone is absent / cleared
        for norm, old_assoc in existing_by_norm.items():
            if norm != alt_norm:
                old_assoc.is_primary = False
                old_assoc.is_active = False
                old_assoc.updated_at = now_utc

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Alternate Phone Synchronization
    # ─────────────────────────────────────────────────────────────────────────
    if alt_norm:
        if alt_norm == p_norm:
            # Identical primary and alternate: ONE association, TWO provenances
            if primary_assoc:
                prov_alt = CRMLeadPhoneProvenance(
                    phone_association_id=primary_assoc.id,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    lead_id=lead_id,
                    source_field='alternate_phone',
                    raw_value=str(alternate_phone_raw)[:100] if alternate_phone_raw else None,
                    source_channel=source_channel,
                    source_ref=str(source_ref) if source_ref else None,
                    captured_at=now_utc
                )
                db.add(prov_alt)
        else:
            # Distinct alternate phone
            if alt_norm in existing_by_norm:
                assoc = existing_by_norm[alt_norm]
                assoc.phone_role = 'ALTERNATE'
                # If lead had no valid primary phone, alternate acts as primary communication line
                assoc.is_primary = (p_norm is None)
                assoc.is_active = True
                assoc.updated_at = now_utc
                alternate_assoc = assoc
            else:
                assoc = CRMLeadPhone(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    lead_id=lead_id,
                    phone_norm=alt_norm,
                    phone_role='ALTERNATE',
                    is_primary=(p_norm is None),
                    is_active=True,
                    verification_status='UNVERIFIED',
                    created_at=now_utc,
                    updated_at=now_utc
                )
                db.add(assoc)
                db.flush()
                existing_by_norm[alt_norm] = assoc
                alternate_assoc = assoc

            # Append non-destructive provenance observation for alternate phone
            prov_alt = CRMLeadPhoneProvenance(
                phone_association_id=alternate_assoc.id,
                tenant_id=tenant_id,
                company_id=company_id,
                lead_id=lead_id,
                source_field='alternate_phone',
                raw_value=str(alternate_phone_raw)[:100] if alternate_phone_raw else None,
                source_channel=source_channel,
                source_ref=str(source_ref) if source_ref else None,
                captured_at=now_utc
            )
            db.add(prov_alt)
    else:
        # Alternate phone is absent / cleared
        for norm, old_assoc in existing_by_norm.items():
            if norm != p_norm:
                old_assoc.is_active = False
                old_assoc.is_primary = False
                old_assoc.updated_at = now_utc

    db.flush()

    return {
        "lead_id": lead_id,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "phone_norm": p_norm,
        "alternate_phone_norm": alt_norm,
        "primary_association_id": primary_assoc.id if primary_assoc else None,
        "alternate_association_id": alternate_assoc.id if alternate_assoc else None,
    }


def find_candidate_associations_by_phone(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    active_only: bool = True
) -> List[CRMLeadPhone]:
    """
    Canonical phone candidate-read primitive (Stage 2B Phase 2R-3E-II Batch 1).
    Fast indexed lookup for candidate phone associations matching given phone identities.
    Queries crm_lead_phones via idx_crm_lead_phones_lookup(tenant_id, company_id, phone_norm).
    Returns all matching CRMLeadPhone instances within tenant and company boundaries.
    Preserves lead_id, phone_norm, phone_role, is_primary, and is_active.
    Phone is treated as candidate evidence, not lead identity.
    Does NOT arbitrarily select one candidate (no MIN/MAX/LIMIT 1).
    """
    if not tenant_id or not company_id:
        return []

    identities = {normalize_phone(p) for p in (phone, alternate_phone) if p}
    identities.discard(None)
    if not identities:
        return []

    q = db.query(CRMLeadPhone).filter(
        CRMLeadPhone.tenant_id == tenant_id,
        CRMLeadPhone.company_id == company_id,
        CRMLeadPhone.phone_norm.in_(identities)
    )

    if active_only:
        q = q.filter(CRMLeadPhone.is_active == True)

    return q.order_by(CRMLeadPhone.lead_id.asc(), CRMLeadPhone.id.asc()).all()


def find_candidate_leads_by_phone(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    active_only: bool = True
) -> List[CRMLead]:
    """
    Fast indexed lookup for candidate leads associated with given phone identities.
    Queries crm_lead_phones via idx_crm_lead_phones_lookup and loads matching crm_leads.
    Returns list of distinct CRMLead instances within tenant and company boundaries.
    Preserves all matching candidates without arbitrary selection (no MIN/MAX/LIMIT 1).
    """
    assocs = find_candidate_associations_by_phone(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        active_only=active_only
    )
    if not assocs:
        return []

    lead_ids = [a.lead_id for a in assocs]
    leads = db.query(CRMLead).filter(
        CRMLead.tenant_id == tenant_id,
        CRMLead.company_id == company_id,
        CRMLead.id.in_(lead_ids)
    ).all()

    lead_map = {l.id: l for l in leads}
    seen = set()
    result = []
    for lid in lead_ids:
        if lid not in seen and lid in lead_map:
            seen.add(lid)
            result.append(lead_map[lid])
    return result


# Canonical alias
find_leads_by_phone = find_candidate_leads_by_phone


def find_candidate_lead_ids_for_search(
    db: Session,
    tenant_id: Optional[int],
    company_ids: Optional[Sequence[int]],
    search_term: Optional[str],
    active_only: bool = True
) -> List[int]:
    """
    Search-oriented canonical candidate lookup primitive (Stage 2B Phase 2R-3E-II Batch 2).
    Discovers candidate lead IDs whose active phone associations match the search term.
    
    Behavior:
    - Extracts digits from search_term.
    - If clean digits >= 10: normalizes to trailing 10 digits and queries canonical phone associations
      via idx_crm_lead_phones_lookup(tenant_id, company_id, phone_norm).
    - If 4 <= clean digits < 10: performs partial substring matching on active crm_lead_phones.phone_norm.
    - If clean digits < 4 or empty: returns [] (avoids noise/unnecessary queries on non-phone searches).
    - Respects tenant_id and company_ids boundaries strictly.
    - Preserves all candidate leads without arbitrary winner selection (no MIN/MAX/LIMIT 1).
    """
    if not search_term or not isinstance(search_term, str):
        return []

    clean_digits = re.sub(r'\D', '', search_term.strip())
    if len(clean_digits) < 4:
        return []

    if company_ids is not None and len(company_ids) == 0:
        return []

    norm = normalize_phone(clean_digits) if len(clean_digits) >= 10 else None

    q = db.query(CRMLeadPhone.lead_id)
    if tenant_id is not None:
        q = q.filter(CRMLeadPhone.tenant_id == tenant_id)
    if company_ids is not None:
        q = q.filter(CRMLeadPhone.company_id.in_(company_ids))
    if active_only:
        q = q.filter(CRMLeadPhone.is_active == True)

    if norm:
        q = q.filter(CRMLeadPhone.phone_norm == norm)
    else:
        q = q.filter(CRMLeadPhone.phone_norm.like(f"%{clean_digits}%"))

    return [r[0] for r in q.distinct().all()]



def catchup_sync_unassociated_leads(
    db: Session,
    specific_lead_ids: Optional[Sequence[int]] = None
) -> Dict[str, Any]:
    """
    Controlled, idempotent catch-up synchronization for leads missing from crm_lead_phones.
    Specifically designed for post-backfill inbound leads (e.g. Leads 11272 & 11273).
    
    Leaves existing crm_leads data 100% untouched.
    """
    if specific_lead_ids:
        query = db.query(CRMLead).filter(CRMLead.id.in_(specific_lead_ids)).order_by(CRMLead.id.asc())
    else:
        # Scan for leads with normalizable phones that have 0 phone associations
        subquery = db.query(CRMLeadPhone.lead_id).subquery()
        query = db.query(CRMLead).filter(
            ~CRMLead.id.in_(subquery)
        ).order_by(CRMLead.id.asc())

    leads = query.all()
    synced_leads = []
    skipped_leads = []

    for lead in leads:
        p_norm = normalize_phone(lead.phone)
        alt_norm = normalize_phone(lead.alternate_phone)
        if not p_norm and not alt_norm:
            skipped_leads.append(lead.id)
            continue

        res = sync_lead_phone_identities(
            db=db,
            lead=lead,
            phone_raw=lead.phone,
            alternate_phone_raw=lead.alternate_phone,
            source_channel=lead.source or 'catchup_sync',
            source_ref=lead.source_details,
            with_lock=True
        )
        synced_leads.append(res)

    db.flush()
    return {
        "scanned_count": len(leads),
        "synced_count": len(synced_leads),
        "skipped_count": len(skipped_leads),
        "synced_lead_ids": [s["lead_id"] for s in synced_leads],
    }
