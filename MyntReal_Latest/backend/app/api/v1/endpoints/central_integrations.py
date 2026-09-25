"""
Central Integration Management API Endpoints — MyntOS
Strictly guarded for MR10001 and MR10016 only.
Provides:
- Dynamic Category & Definition metadata
- Dynamic Client list (Internal & External)
- Master Integration Matrix
- Connection CRUD with AES-256-GCM encryption & masking
- Connection Testing via Provider Adapters
- Audit Logging
Created: September 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
import logging
from datetime import datetime

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.platform_b2b import PlatformClient
from app.models.integration_framework import (
    IntegrationCategory, IntegrationDefinition, IntegrationConnection, IntegrationAuditLog
)
from app.core.security_encryption import encrypt_credential, decrypt_credential_safe
from app.services.integrations.registry import (
    get_master_matrix_data, mask_connection_credentials, seed_default_registry
)
from app.services.integrations.adapters import get_adapter_for_integration
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Central Integration Management"])


# ─────────────────────────────────────────────────────────────────────────────
# RBAC Dependency: ONLY MR10001 and MR10016
# ─────────────────────────────────────────────────────────────────────────────
def require_central_integrations_admin(
    current_user: StaffEmployee = Depends(get_current_staff_user)
) -> StaffEmployee:
    """
    Enforces strict access control:
    ONLY MR10001 (VGK Supreme Administrator) and MR10016 (Yaswanth) are permitted.
    All other users, staff types, or roles receive HTTP 403 Forbidden.
    """
    code = (getattr(current_user, 'emp_code', '') or '').strip().upper()
    if code not in ('MR10001', 'MR10016'):
        logger.warning(f"[INTEGRATIONS-ACCESS-DENIED] Unauthorized attempt by staff {current_user.id} ({code})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Central Integration Management is strictly restricted to MR10001 and Yaswanth (MR10016)."
        )
    return current_user


def _log_audit(db: Session, actor_emp: str, action: str, integration_code: str,
               tenant_id: Optional[int] = None, connection_id: Optional[int] = None,
               details: Optional[Dict] = None, ip: Optional[str] = None):
    try:
        log = IntegrationAuditLog(
            tenant_id=tenant_id,
            integration_code=integration_code,
            connection_id=connection_id,
            action=action,
            actor_emp_code=actor_emp,
            actor_ip=ip,
            details=details or {},
            created_at=get_indian_time()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"[INTEGRATION-AUDIT-ERROR] Failed writing audit log: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ConnectionCreateRequest(BaseModel):
    tenant_id: Optional[int] = None
    integration_code: str
    connection_name: str
    scope: str = "tenant" # "platform" or "tenant"
    auth_type: str = "api_key"
    credentials: Dict[str, Any] = {}
    public_configuration: Dict[str, Any] = {}
    provider_account_id: Optional[str] = None
    is_default: bool = False


class ConnectionUpdateRequest(BaseModel):
    connection_name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None # Partial or full update; masked strings ignored
    public_configuration: Optional[Dict[str, Any]] = None
    provider_account_id: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Metadata: Categories & Definitions
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/categories", summary="List all integration categories")
def get_categories(
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    cats = db.query(IntegrationCategory).filter_by(is_active=True).order_by(IntegrationCategory.display_order.asc()).all()
    return {"success": True, "categories": [c.to_dict() for c in cats]}


@router.get("/definitions", summary="List all integration provider definitions")
def get_definitions(
    category_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    q = db.query(IntegrationDefinition).filter_by(is_active=True)
    if category_code:
        q = q.filter(IntegrationDefinition.category_code == category_code)
    defs = q.order_by(IntegrationDefinition.display_order.asc()).all()
    return {"success": True, "definitions": [d.to_dict() for d in defs]}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Clients List (Internal vs External)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/clients", summary="List clients for tenant selector dropdown")
def get_clients_for_selector(
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    clients = db.query(PlatformClient).order_by(
        PlatformClient.is_internal.desc(),
        PlatformClient.client_name.asc()
    ).all()

    internal = []
    external = []
    for c in clients:
        item = {
            "id": c.id,
            "client_code": c.client_code,
            "client_name": c.client_name,
            "is_internal": c.is_internal,
            "status": c.status,
            "contact_email": c.contact_email
        }
        if c.is_internal:
            internal.append(item)
        else:
            external.append(item)

    return {
        "success": True,
        "internal_clients": internal,
        "external_clients": external,
        "all_clients": internal + external,
        "total_clients": len(clients)
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Master Integrations Matrix
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/matrix", summary="Compute dynamic Master Integrations Matrix")
def get_master_matrix(
    tenant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    matrix_data = get_master_matrix_data(db, tenant_id=tenant_id)
    return {"success": True, "data": matrix_data}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Connections Management
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/connections", summary="List connections for a tenant or provider")
def get_connections(
    tenant_id: Optional[int] = Query(None),
    integration_code: Optional[str] = Query(None),
    include_platform: bool = Query(True),
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    q = db.query(IntegrationConnection)
    if tenant_id is not None:
        if include_platform:
            q = q.filter((IntegrationConnection.tenant_id == tenant_id) | (IntegrationConnection.tenant_id == 1) | (IntegrationConnection.scope == 'platform'))
        else:
            q = q.filter(IntegrationConnection.tenant_id == tenant_id)
    if integration_code:
        q = q.filter(IntegrationConnection.integration_code == integration_code)

    conns = q.order_by(IntegrationConnection.is_default.desc(), IntegrationConnection.id.asc()).all()
    return {"success": True, "connections": [c.to_dict(include_masked_creds=True) for c in conns]}


@router.post("/connections", summary="Create a new integration connection")
def create_connection(
    payload: ConnectionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    idef = db.query(IntegrationDefinition).filter_by(integration_code=payload.integration_code).first()
    if not idef:
        raise HTTPException(status_code=404, detail=f"Integration definition '{payload.integration_code}' not found.")

    target_tenant_id = payload.tenant_id if payload.scope == "tenant" else 1

    # If is_default is True, reset other connections of the same tenant & integration
    if payload.is_default:
        db.query(IntegrationConnection).filter(
            IntegrationConnection.tenant_id == target_tenant_id,
            IntegrationConnection.integration_code == payload.integration_code
        ).update({"is_default": False})

    # Encrypt raw credentials with AES-256-GCM
    enc_creds = ""
    if payload.credentials:
        enc_creds = encrypt_credential(json.dumps(payload.credentials))

    conn = IntegrationConnection(
        tenant_id=target_tenant_id,
        integration_code=payload.integration_code,
        connection_name=payload.connection_name,
        scope=payload.scope,
        auth_type=payload.auth_type or idef.auth_type,
        encrypted_credentials=enc_creds,
        public_configuration=payload.public_configuration or {},
        provider_account_id=payload.provider_account_id,
        status="ACTIVE",
        is_active=True,
        is_default=payload.is_default,
        created_by=admin.emp_code
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    client_ip = request.client.host if request.client else None
    _log_audit(db, admin.emp_code, "connection_created", payload.integration_code, target_tenant_id, conn.id, {"name": conn.connection_name}, client_ip)

    return {"success": True, "message": "Connection created successfully.", "connection": conn.to_dict(include_masked_creds=True)}


@router.put("/connections/{conn_id}", summary="Update an integration connection")
def update_connection(
    conn_id: int,
    payload: ConnectionUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    conn = db.query(IntegrationConnection).filter_by(id=conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    if payload.connection_name is not None:
        conn.connection_name = payload.connection_name
    if payload.public_configuration is not None:
        conn.public_configuration = payload.public_configuration
    if payload.provider_account_id is not None:
        conn.provider_account_id = payload.provider_account_id
    if payload.is_active is not None:
        conn.is_active = payload.is_active
    if payload.is_default is not None:
        if payload.is_default:
            db.query(IntegrationConnection).filter(
                IntegrationConnection.tenant_id == conn.tenant_id,
                IntegrationConnection.integration_code == conn.integration_code
            ).update({"is_default": False})
        conn.is_default = payload.is_default

    # Merge secret credentials: ignore masked bullets ("••••") and preserve existing secrets!
    if payload.credentials is not None:
        adapter = get_adapter_for_integration(conn.integration_code)
        existing_creds = adapter.get_decrypted_credentials(conn)
        updated_creds = dict(existing_creds)

        for k, v in payload.credentials.items():
            s_val = str(v).strip()
            # If the user submitted masked bullets, DO NOT overwrite existing secret
            if "••••" in s_val or s_val == "":
                continue
            updated_creds[k] = v

        conn.encrypted_credentials = encrypt_credential(json.dumps(updated_creds))

    conn.updated_by = admin.emp_code
    conn.updated_at = get_indian_time()
    db.commit()
    db.refresh(conn)

    client_ip = request.client.host if request.client else None
    _log_audit(db, admin.emp_code, "credentials_updated", conn.integration_code, conn.tenant_id, conn.id, {"name": conn.connection_name}, client_ip)

    return {"success": True, "message": "Connection updated successfully.", "connection": conn.to_dict(include_masked_creds=True)}


@router.delete("/connections/{conn_id}", summary="Delete an integration connection")
def delete_connection(
    conn_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    conn = db.query(IntegrationConnection).filter_by(id=conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    t_id = conn.tenant_id
    i_code = conn.integration_code
    conn_name = conn.connection_name

    db.delete(conn)
    db.commit()

    client_ip = request.client.host if request.client else None
    _log_audit(db, admin.emp_code, "connection_deleted", i_code, t_id, conn_id, {"deleted_name": conn_name}, client_ip)

    return {"success": True, "message": f"Connection '{conn_name}' deleted successfully."}


@router.post("/connections/{conn_id}/test", summary="Execute connection test")
def test_connection_endpoint(
    conn_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    conn = db.query(IntegrationConnection).filter_by(id=conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    adapter = get_adapter_for_integration(conn.integration_code)
    test_res = adapter.test_connection(conn, db)

    # Persist test result
    conn.last_tested_at = get_indian_time()
    conn.last_test_result = test_res
    if test_res.get("status") in ("SUCCESS", "ACTIVE"):
        conn.status = "ACTIVE"
    elif test_res.get("status") in ("AUTHENTICATION_ERROR", "FAILED", "ERROR"):
        conn.status = "ERROR"
    db.commit()

    client_ip = request.client.host if request.client else None
    _log_audit(db, admin.emp_code, "connection_tested", conn.integration_code, conn.tenant_id, conn.id, {"result_status": test_res.get("status")}, client_ip)

    return {"success": True, "test_result": test_res, "connection_status": conn.status}


@router.post("/connections/{conn_id}/default", summary="Set connection as default")
def set_default_connection(
    conn_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    conn = db.query(IntegrationConnection).filter_by(id=conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    db.query(IntegrationConnection).filter(
        IntegrationConnection.tenant_id == conn.tenant_id,
        IntegrationConnection.integration_code == conn.integration_code
    ).update({"is_default": False})

    conn.is_default = True
    db.commit()

    client_ip = request.client.host if request.client else None
    _log_audit(db, admin.emp_code, "default_changed", conn.integration_code, conn.tenant_id, conn.id, {}, client_ip)

    return {"success": True, "message": f"Connection '{conn.connection_name}' is now default."}


@router.patch("/connections/{conn_id}/toggle", summary="Toggle active/inactive state")
@router.post("/connections/{conn_id}/toggle", summary="Toggle active/inactive state")
@router.post("/connections/{conn_id}/toggle-status", summary="Toggle active/inactive state")
def toggle_connection_status(
    conn_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    conn = db.query(IntegrationConnection).filter_by(id=conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    conn.is_active = not conn.is_active
    conn.status = "ACTIVE" if conn.is_active else "INACTIVE"
    db.commit()

    client_ip = request.client.host if request.client else None
    action = "connection_activated" if conn.is_active else "connection_deactivated"
    _log_audit(db, admin.emp_code, action, conn.integration_code, conn.tenant_id, conn.id, {"is_active": conn.is_active}, client_ip)

    return {"success": True, "is_active": conn.is_active, "status": conn.status}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Audit Trail & Registry Reseed Trigger
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/audit-logs", summary="Get integration management audit history")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    logs = db.query(IntegrationAuditLog).order_by(desc(IntegrationAuditLog.id)).limit(limit).all()
    log_dicts = [l.to_dict() for l in logs]
    return {"success": True, "audit_logs": log_dicts, "logs": log_dicts}


@router.post("/reseed", summary="Reseed integration definitions & categories")
def reseed_registry_endpoint(
    db: Session = Depends(get_db),
    admin: StaffEmployee = Depends(require_central_integrations_admin)
):
    res = seed_default_registry(db)
    return {"success": True, "message": "Registry reseeded successfully.", "details": res}
