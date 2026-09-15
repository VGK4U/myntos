"""
Centralized CRM Phone Deduplication Service (Stage 2B Phase 2R-3D).
Authoritative, route-agnostic domain deduplication with:
- Deterministic canonical normalization (10-digit mobile, 8/9-digit landline).
- Identical Python and PostgreSQL evaluation.
- Deterministic multi-identity transaction advisory locking (lexicographically sorted SHA-256 BigInt).
- Multi-tenant and company isolation (strictly scoped to tenant_id and company_id).
- Fail-closed validation (invalid or missing tenancy immediately rejected).
- Decoupled pure domain logic (no side-effects or workflow dependencies).
"""

import re
import struct
import hashlib
import logging
from typing import Optional, List, Sequence, Tuple, Any, Dict
from dataclasses import dataclass
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.crm import CRMLead
from app.models.staff import StaffEmployee

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DuplicateCheckResult:
    is_duplicate: bool
    existing_lead_id: Optional[int] = None
    existing_lead_name: Optional[str] = None
    existing_lead_status: Optional[str] = None
    matched_field: Optional[str] = None          # 'phone' or 'alternate_phone'
    matched_identity: Optional[str] = None       # Canonical normalized 10/8/9 digit string
    company_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    owner_emp_code: Optional[str] = None
    owner_status: Optional[str] = None
    owner_active: bool = True
    lead_data: Optional[Dict[str, Any]] = None


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """
    Canonical phone normalization contract.
    - Strips all non-digit characters (including spaces, hyphens, brackets, +, and Meta 'p:').
    - If total digits >= 10: returns trailing 10 digits (digits[-10:]).
    - If total digits is 8 or 9: returns exact digits (local Indian landline without full STD).
    - If total digits < 8 or input is empty/None: returns None.
    """
    if not raw:
        return None
    digits = re.sub(r'[^0-9]', '', str(raw))
    if len(digits) >= 10:
        return digits[-10:]
    elif len(digits) >= 8:
        return digits
    return None


def acquire_phone_locks(
    db: Session,
    tenant_id: int,
    company_id: int,
    phones: Sequence[Optional[str]]
) -> List[str]:
    """
    Acquires transaction-level PostgreSQL advisory locks for all distinct normalized phone identities.
    
    To prevent lock-order deadlocks between concurrent transactions inserting or updating
    multiple phone numbers in opposite order (e.g. T1: phone A, alt B vs T2: phone B, alt A),
    all identities are lexicographically sorted prior to sequential lock acquisition.
    
    Key derivation:
      namespace = "myntos:crm_lead_phone:{tenant_id}:{company_id}:{ident}"
      lock_int  = struct.unpack('>q', hashlib.sha256(namespace.encode('utf-8')).digest()[:8])[0]
      
    PostgreSQL advisory locks (pg_advisory_xact_lock) are automatically released at transaction
    commit or rollback.
    """
    if not tenant_id or not company_id:
        raise ValueError("acquire_phone_locks requires positive tenant_id and company_id")

    normalized_set = {normalize_phone(p) for p in phones}
    normalized_set.discard(None)
    if not normalized_set:
        return []

    sorted_identities = sorted(list(normalized_set))
    for ident in sorted_identities:
        namespace_key = f"myntos:crm_lead_phone:{tenant_id}:{company_id}:{ident}"
        h = hashlib.sha256(namespace_key.encode('utf-8')).digest()
        lock_key = struct.unpack('>q', h[:8])[0]
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key})

    return sorted_identities


def find_phone_duplicate(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    with_lock: bool = True
) -> Optional[CRMLead]:
    """
    Queries for an existing CRM lead matching phone or alternate_phone against either
    database column within the specified tenant and company scope.
    
    If with_lock is True, acquires deterministic advisory locks on all incoming phone identities
    BEFORE executing the duplicate query, holding the lock for the remainder of the transaction.
    
    Returns the first matching CRMLead ORM instance ordered by id ASC, or None.
    """
    if tenant_id is None or company_id is None:
        raise ValueError("find_phone_duplicate requires explicit tenant_id and company_id")

    if with_lock:
        acquire_phone_locks(db, tenant_id, company_id, [phone, alternate_phone])

    from app.services.crm_phone_sync_service import find_candidate_leads_by_phone

    # 1. Canonical indexed lookup on crm_lead_phones
    candidates = find_candidate_leads_by_phone(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        active_only=True
    )

    if exclude_lead_id is not None:
        candidates = [c for c in candidates if c.id != exclude_lead_id]

    if candidates:
        return candidates[0]

    # 2. Defense-in-depth legacy fallback: check crm_leads for any unassociated records
    identities = {normalize_phone(p) for p in [phone, alternate_phone]}
    identities.discard(None)
    if not identities:
        return None

    sql = text("""
        SELECT c.id
        FROM crm_leads c
        WHERE (
            (CASE 
                WHEN LENGTH(REGEXP_REPLACE(c.phone, '[^0-9]', '', 'g')) >= 10 
                    THEN RIGHT(REGEXP_REPLACE(c.phone, '[^0-9]', '', 'g'), 10)
                WHEN LENGTH(REGEXP_REPLACE(c.phone, '[^0-9]', '', 'g')) >= 8 
                    THEN REGEXP_REPLACE(c.phone, '[^0-9]', '', 'g')
                ELSE NULL 
            END) IN :identities
            OR
            (CASE 
                WHEN LENGTH(REGEXP_REPLACE(c.alternate_phone, '[^0-9]', '', 'g')) >= 10 
                    THEN RIGHT(REGEXP_REPLACE(c.alternate_phone, '[^0-9]', '', 'g'), 10)
                WHEN LENGTH(REGEXP_REPLACE(c.alternate_phone, '[^0-9]', '', 'g')) >= 8 
                    THEN REGEXP_REPLACE(c.alternate_phone, '[^0-9]', '', 'g')
                ELSE NULL 
            END) IN :identities
        )
        AND c.tenant_id = :tenant_id
        AND c.company_id = :company_id
        AND (:exclude_id IS NULL OR c.id != :exclude_id)
        ORDER BY c.id ASC
        LIMIT 1
    """)

    matched_id = db.execute(sql, {
        "identities": tuple(identities),
        "tenant_id": tenant_id,
        "company_id": company_id,
        "exclude_id": exclude_lead_id
    }).scalar()

    if not matched_id:
        return None

    return db.query(CRMLead).filter(CRMLead.id == matched_id).first()


def find_duplicate_candidates(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    with_lock: bool = True
) -> List[CRMLead]:
    """
    Returns ALL candidate leads matching phone or alternate_phone within tenant and company boundaries.
    Preserves all candidate evidence without arbitrary selection (no MIN/MAX/LIMIT 1).
    """
    if tenant_id is None or company_id is None:
        raise ValueError("find_duplicate_candidates requires explicit tenant_id and company_id")

    if with_lock:
        acquire_phone_locks(db, tenant_id, company_id, [phone, alternate_phone])

    from app.services.crm_phone_sync_service import find_candidate_leads_by_phone

    candidates = find_candidate_leads_by_phone(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        active_only=True
    )

    if exclude_lead_id is not None:
        candidates = [c for c in candidates if c.id != exclude_lead_id]

    if candidates:
        return candidates

    # Legacy fallback for unassociated leads
    single = find_phone_duplicate(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        exclude_lead_id=exclude_lead_id,
        with_lock=False
    )
    return [single] if single else []



def check_phone_duplicate(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    with_lock: bool = True
) -> DuplicateCheckResult:
    """
    Evaluates duplicate status and extracts sanitized owner/lead details.
    """
    lead = find_phone_duplicate(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        exclude_lead_id=exclude_lead_id,
        with_lock=with_lock
    )
    if not lead:
        return DuplicateCheckResult(is_duplicate=False)

    # Determine matched identity and field
    norm_p = normalize_phone(phone)
    norm_a = normalize_phone(alternate_phone)
    lead_p = normalize_phone(lead.phone)
    lead_a = normalize_phone(lead.alternate_phone)

    matched_field = None
    matched_ident = None
    if norm_p and norm_p in (lead_p, lead_a):
        matched_field = "phone"
        matched_ident = norm_p
    elif norm_a and norm_a in (lead_p, lead_a):
        matched_field = "alternate_phone"
        matched_ident = norm_a
    elif hasattr(lead, 'phone_associations') and lead.phone_associations:
        assoc_norms = {a.phone_norm: a.phone_role for a in lead.phone_associations if a.is_active}
        if norm_p and norm_p in assoc_norms:
            matched_field = "phone" if assoc_norms[norm_p] == 'PRIMARY' else "alternate_phone"
            matched_ident = norm_p
        elif norm_a and norm_a in assoc_norms:
            matched_field = "alternate_phone" if assoc_norms[norm_a] == 'ALTERNATE' else "phone"
            matched_ident = norm_a

    # Resolve owner
    owner_id = None
    owner_name = None
    owner_emp_code = None
    owner_status = None
    owner_active = True

    if getattr(lead, 'primary_owner_type', None) == 'staff' and getattr(lead, 'primary_owner_id', None):
        owner = db.query(StaffEmployee).filter(StaffEmployee.id == lead.primary_owner_id).first()
        if owner:
            owner_id = owner.id
            owner_name = f"{owner.first_name or ''} {owner.last_name or ''}".strip() or owner.emp_code
            owner_emp_code = owner.emp_code
            owner_status = owner.status
            owner_active = (owner.status == 'active')
    elif getattr(lead, 'handler_type', None) == 'staff' and getattr(lead, 'handler_id', None):
        h_str = str(lead.handler_id).strip()
        owner = None
        if h_str.isdigit():
            owner = db.query(StaffEmployee).filter(StaffEmployee.id == int(h_str)).first()
        if not owner:
            owner = db.query(StaffEmployee).filter(StaffEmployee.emp_code == h_str).first()
        if owner:
            owner_id = owner.id
            owner_name = f"{owner.first_name or ''} {owner.last_name or ''}".strip() or owner.emp_code
            owner_emp_code = owner.emp_code
            owner_status = owner.status
            owner_active = (owner.status == 'active')

    return DuplicateCheckResult(
        is_duplicate=True,
        existing_lead_id=lead.id,
        existing_lead_name=lead.name or "",
        existing_lead_status=lead.status,
        matched_field=matched_field,
        matched_identity=matched_ident,
        company_id=lead.company_id,
        owner_id=owner_id,
        owner_name=owner_name,
        owner_emp_code=owner_emp_code,
        owner_status=owner_status,
        owner_active=owner_active,
        lead_data={
            "id": lead.id,
            "name": lead.name or "",
            "phone": lead.phone or "",
            "alternate_phone": lead.alternate_phone or "",
            "status": lead.status,
            "company_id": lead.company_id,
        }
    )


def assert_no_phone_duplicate(
    db: Session,
    tenant_id: int,
    company_id: int,
    phone: Optional[str],
    alternate_phone: Optional[str] = None,
    exclude_lead_id: Optional[int] = None,
    with_lock: bool = True
) -> None:
    """
    Asserts that no lead with the given phone or alternate_phone exists in the same
    tenant and company. If a duplicate exists, raises HTTPException(status_code=409).
    """
    result = check_phone_duplicate(
        db=db,
        tenant_id=tenant_id,
        company_id=company_id,
        phone=phone,
        alternate_phone=alternate_phone,
        exclude_lead_id=exclude_lead_id,
        with_lock=with_lock
    )
    if result.is_duplicate:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "duplicate_lead",
                "message": f"Mobile number already exists in Lead #{result.existing_lead_id} ({result.existing_lead_name or 'Unnamed'}).",
                "lead_id": result.existing_lead_id,
                "lead_name": result.existing_lead_name,
                "lead_status": result.existing_lead_status,
                "lead_company_id": result.company_id,
                "matched_field": result.matched_field,
                "matched_identity": result.matched_identity,
                "owner_name": result.owner_name,
                "owner_status": result.owner_status,
                "owner_active": result.owner_active,
                "lead": result.lead_data,
                "owner": {
                    "id": result.owner_id,
                    "name": result.owner_name,
                    "emp_code": result.owner_emp_code,
                    "status": result.owner_status,
                } if result.owner_id else None,
            }
        )
