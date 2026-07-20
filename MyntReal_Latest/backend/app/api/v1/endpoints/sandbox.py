"""
Sandbox Testing Environment API Endpoints
DC Protocol Compliant - Company-wise data segregation
WVV Protocol Compliant - Full audit trail
VGK Mentor Access Only
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta
import time

from app.core.database import get_db
from app.core.config import settings
from app.models.sandbox import SandboxConfiguration, SandboxSyncLog, SandboxTestAccount, SandboxAccessLog
from app.schemas.sandbox import (
    SandboxConfigurationUpdate, SandboxConfigurationResponse,
    SandboxSyncRequest, SandboxSyncLogResponse,
    SandboxTestAccountCreate, SandboxTestAccountUpdate, SandboxTestAccountResponse,
    SandboxTestAccountPasswordChange, SandboxBulkActivation, SandboxStatusResponse
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user_hybrid
from werkzeug.security import check_password_hash
from app.core.security import SecurityManager as _SM_SBX
from pydantic import BaseModel
from jose import jwt
import os

router = APIRouter(prefix="/sandbox", tags=["Sandbox Testing"])


class SandboxLoginRequest(BaseModel):
    login_id: str
    password: str
    mode: str = "view"


@router.post("/auth/login")
async def sandbox_login(
    data: SandboxLoginRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Sandbox-specific authentication endpoint - PRODUCTION REPLICA (Dec 2025)
    DC Protocol: Authenticates against REAL production accounts for full parity
    WVV Protocol: Logs all access attempts
    
    Key change: Instead of generating sandbox-specific tokens, this now:
    1. Validates credentials against sandbox_test_accounts
    2. Looks up the REAL production account (user/staff/partner)
    3. Generates a proper production token that works with all APIs
    """
    from app.models.user import User
    from app.models.staff import StaffEmployee
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment
    from app.core.security import SecurityManager
    
    config = get_or_create_config(db)
    
    if not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sandbox is currently disabled"
        )
    
    now = datetime.now()
    if config.activation_start and now < config.activation_start:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sandbox is not yet active"
        )
    if config.activation_end and now > config.activation_end:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sandbox has expired"
        )
    
    if data.mode == "view" and not config.view_mode_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="View mode is disabled"
        )
    if data.mode == "edit" and not config.edit_mode_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit mode is disabled"
        )
    
    account = db.query(SandboxTestAccount).filter(
        SandboxTestAccount.login_id == data.login_id,
        SandboxTestAccount.is_active == True
    ).first()
    
    if not account:
        access_log = SandboxAccessLog(
            access_mode=data.mode,
            account_type="UNKNOWN",
            login_id=data.login_id,
            action_performed="LOGIN_FAILED",
            ip_address=get_client_ip(request)
        )
        db.add(access_log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your login ID and password."
        )
    
    if not check_password_hash(account.password_hash, data.password):
        access_log = SandboxAccessLog(
            access_mode=data.mode,
            account_type=account.account_type,
            login_id=data.login_id,
            action_performed="LOGIN_FAILED_BAD_PASSWORD",
            ip_address=get_client_ip(request)
        )
        db.add(access_log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials. Please check and try again."
        )
    
    account.last_login_at = datetime.now()
    account.login_count = (account.login_count or 0) + 1
    
    access_log = SandboxAccessLog(
        access_mode=data.mode,
        account_type=account.account_type,
        login_id=data.login_id,
        action_performed="LOGIN_SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('user-agent') if request else None
    )
    db.add(access_log)
    db.commit()
    
    # DC Protocol (Dec 2025): Generate REAL production tokens based on account type
    if account.account_type == "MNR":
        # MNR User: Look up real user and generate production token
        user = db.query(User).filter(User.id == data.login_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sandbox account {data.login_id} not linked to production user. Run sandbox sync."
            )
        
        token_data = {
            "sub": user.id,
            "user_type": user.user_type,
            "name": user.name,
            "email": user.email,
            "sandbox_mode": data.mode,
            "is_sandbox": True,
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        access_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "account_type": account.account_type,
            "account_role": user.user_type,
            "display_name": user.name,
            "sandbox_mode": data.mode,
            "message": f"Welcome to sandbox {data.mode} mode!"
        }
    
    elif account.account_type == "STAFF":
        # Staff: Look up real employee and generate production token
        employee = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.ilike(data.login_id)
        ).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sandbox account {data.login_id} not linked to production staff. Run sandbox sync."
            )
        
        # Get role name and code from relationship
        role_name = employee.role.role_name if employee.role else "Employee"
        role_code = employee.role.role_code if employee.role else "junior_executive"
        
        # DC Protocol: Token must match production format for staff auth endpoint validation
        # Critical fields: user_type="staff", role (role_code), sub, emp_code, email
        token_data = {
            "sub": str(employee.id),
            "emp_code": employee.emp_code,
            "email": employee.email,
            "role": role_code,
            "user_type": "staff",
            "emp_id": employee.id,
            "full_name": employee.full_name,
            "role_id": employee.role_id,
            "role_name": role_name,
            "staff_type": employee.staff_type,
            "department_id": employee.department_id,
            "base_company_id": employee.base_company_id,
            "sandbox_mode": data.mode,
            "is_sandbox": True,
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        access_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "account_type": account.account_type,
            "account_role": role_name,
            "display_name": employee.full_name,
            "sandbox_mode": data.mode,
            "emp_code": employee.emp_code,
            "staff_type": employee.staff_type,
            "message": f"Welcome to sandbox {data.mode} mode!"
        }
    
    elif account.account_type == "PARTNER":
        # Partner: Look up real partner and generate production token
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.partner_code.ilike(data.login_id)
        ).first()
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sandbox account {data.login_id} not linked to production partner. Run sandbox sync."
            )
        
        # Get partner's company segments
        company_segments = db.query(PartnerCompanySegment).filter(
            PartnerCompanySegment.partner_id == partner.id,
            PartnerCompanySegment.is_active == True
        ).all()
        
        company_ids = [cs.company_id for cs in company_segments]
        primary_company_id = None
        for cs in company_segments:
            if cs.is_primary:
                primary_company_id = cs.company_id
                break
        if not primary_company_id and company_ids:
            primary_company_id = company_ids[0]
        
        token_data = {
            "sub": str(partner.id),
            "user_type": "partner",
            "partner_code": partner.partner_code,
            "category": partner.category,
            "company_ids": company_ids,
            "primary_company_id": primary_company_id,
            "sandbox_mode": data.mode,
            "is_sandbox": True,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        access_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "account_type": account.account_type,
            "account_role": partner.category,
            "display_name": partner.partner_name,
            "sandbox_mode": data.mode,
            "partner_code": partner.partner_code,
            "message": f"Welcome to sandbox {data.mode} mode!"
        }
    
    else:
        # Fallback for unknown account types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown account type: {account.account_type}"
        )


def get_client_ip(request: Request = None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_vgk4u_access(current_user: dict):
    """Ensure only VGK4U Supreme staff can access sandbox management"""
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.get('staff_type') not in ['VGK4U', 'VGK4U Supreme']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK4U Supreme staff can access sandbox management"
        )


def get_or_create_config(db: Session) -> SandboxConfiguration:
    """Get existing config or create default - auto-enabled for sandbox testing"""
    config = db.query(SandboxConfiguration).first()
    if not config:
        config = SandboxConfiguration(
            is_enabled=True,
            view_mode_enabled=True,
            edit_mode_enabled=True,
            activation_start=datetime.now(),
            allowed_staff_types=['VGK4U', 'MANAGER', 'EMPLOYEE'],
            allowed_mnr_types=['RVZ ID', 'VGK ID', 'Admin', 'Super Admin', 'Finance Admin', 'USER'],
            allowed_partner_types=['DISTRIBUTOR', 'DEALER', 'VENDOR', 'REAL_DREAM_PARTNER']
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/status", response_model=SandboxStatusResponse)
async def get_sandbox_status(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Get current sandbox status - accessible to all staff for awareness"""
    config = get_or_create_config(db)
    
    now = datetime.now()
    is_currently_active = config.is_enabled
    
    if config.activation_start and now < config.activation_start:
        is_currently_active = False
    if config.activation_end and now > config.activation_end:
        is_currently_active = False
    
    if config.activation_hours_start is not None and config.activation_hours_end is not None:
        current_hour = now.hour
        if not (config.activation_hours_start <= current_hour <= config.activation_hours_end):
            is_currently_active = False
    
    total_accounts = db.query(SandboxTestAccount).count()
    active_accounts = db.query(SandboxTestAccount).filter(SandboxTestAccount.is_active == True).count()
    
    return SandboxStatusResponse(
        is_enabled=config.is_enabled,
        is_currently_active=is_currently_active,
        view_mode_enabled=config.view_mode_enabled,
        edit_mode_enabled=config.edit_mode_enabled,
        activation_start=config.activation_start,
        activation_end=config.activation_end,
        last_sync_at=config.last_sync_at,
        total_test_accounts=total_accounts,
        active_test_accounts=active_accounts
    )


@router.get("/configuration", response_model=SandboxConfigurationResponse)
async def get_sandbox_configuration(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Get sandbox configuration - VGK4U only"""
    require_vgk4u_access(current_user)
    config = get_or_create_config(db)
    return config


@router.put("/configuration", response_model=SandboxConfigurationResponse)
async def update_sandbox_configuration(
    data: SandboxConfigurationUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Update sandbox configuration - VGK4U only"""
    require_vgk4u_access(current_user)
    
    config = get_or_create_config(db)
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    
    config.updated_by_id = current_user.get('id')
    config.updated_by_code = current_user.get('emp_code')
    config.updated_at = datetime.now()
    
    db.commit()
    db.refresh(config)
    
    return config


@router.post("/sync", response_model=SandboxSyncLogResponse)
async def sync_sandbox_data(
    data: SandboxSyncRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """
    Synchronize sandbox data from production
    Creates testing schema and copies all tables
    VGK4U only
    """
    require_vgk4u_access(current_user)
    
    sync_log = SandboxSyncLog(
        sync_type=data.sync_type,
        status='IN_PROGRESS',
        triggered_by_id=current_user.get('id'),
        triggered_by_code=current_user.get('emp_code'),
        triggered_by_name=current_user.get('full_name'),
        started_at=datetime.now()
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    
    start_time = time.time()
    tables_synced = 0
    rows_synced = 0
    
    try:
        db.execute(text("CREATE SCHEMA IF NOT EXISTS testing"))
        db.commit()
        
        tables_result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name NOT IN ('alembic_version', 'apscheduler_jobs')
            ORDER BY table_name
        """))
        tables = [row[0] for row in tables_result.fetchall()]
        
        sync_details = {"tables": []}
        
        for table_name in tables:
            try:
                db.execute(text(f'DROP TABLE IF EXISTS testing."{table_name}" CASCADE'))
                
                db.execute(text(f'''
                    CREATE TABLE testing."{table_name}" 
                    (LIKE public."{table_name}" INCLUDING ALL)
                '''))
                
                result = db.execute(text(f'''
                    INSERT INTO testing."{table_name}" 
                    SELECT * FROM public."{table_name}"
                '''))
                
                row_count = result.rowcount if result.rowcount else 0
                rows_synced += row_count
                tables_synced += 1
                
                sync_details["tables"].append({
                    "name": table_name,
                    "rows": row_count,
                    "status": "success"
                })
                
            except Exception as table_error:
                sync_details["tables"].append({
                    "name": table_name,
                    "error": str(table_error),
                    "status": "failed"
                })
        
        db.commit()
        
        duration = int(time.time() - start_time)
        
        sync_log.status = 'COMPLETED'
        sync_log.tables_synced = tables_synced
        sync_log.rows_synced = rows_synced
        sync_log.duration_seconds = duration
        sync_log.sync_details = sync_details
        sync_log.completed_at = datetime.now()
        
        config = get_or_create_config(db)
        config.last_sync_at = datetime.now()
        config.last_sync_by_id = current_user.get('id')
        config.last_sync_by_code = current_user.get('emp_code')
        config.last_sync_by_name = current_user.get('full_name')
        config.last_sync_tables_count = tables_synced
        config.last_sync_rows_count = rows_synced
        
        db.commit()
        db.refresh(sync_log)
        
        return sync_log
        
    except Exception as e:
        sync_log.status = 'FAILED'
        sync_log.error_message = str(e)
        sync_log.completed_at = datetime.now()
        sync_log.duration_seconds = int(time.time() - start_time)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox sync failed: {str(e)}"
        )


@router.get("/sync-logs", response_model=List[SandboxSyncLogResponse])
async def get_sync_logs(
    limit: int = 20,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Get sandbox sync history - VGK4U only"""
    require_vgk4u_access(current_user)
    
    logs = db.query(SandboxSyncLog)\
        .order_by(SandboxSyncLog.started_at.desc())\
        .limit(limit)\
        .all()
    
    return logs


@router.get("/test-accounts", response_model=List[SandboxTestAccountResponse])
async def list_test_accounts(
    account_type: Optional[str] = None,
    account_role: Optional[str] = None,
    is_active: Optional[bool] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """List all test accounts - VGK4U only"""
    require_vgk4u_access(current_user)
    
    query = db.query(SandboxTestAccount)
    
    if account_type:
        query = query.filter(SandboxTestAccount.account_type == account_type)
    if account_role:
        query = query.filter(SandboxTestAccount.account_role == account_role)
    if is_active is not None:
        query = query.filter(SandboxTestAccount.is_active == is_active)
    
    return query.order_by(SandboxTestAccount.account_type, SandboxTestAccount.account_role).all()


@router.get("/test-accounts/{account_id}", response_model=SandboxTestAccountResponse)
async def get_test_account(
    account_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Get a single test account by ID - VGK4U only"""
    require_vgk4u_access(current_user)
    
    account = db.query(SandboxTestAccount).filter(SandboxTestAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Test account not found")
    
    return account


@router.post("/test-accounts", response_model=SandboxTestAccountResponse)
async def create_test_account(
    data: SandboxTestAccountCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Create a new test account - VGK4U only"""
    require_vgk4u_access(current_user)
    
    existing = db.query(SandboxTestAccount).filter(
        SandboxTestAccount.login_id == data.login_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test account with login ID '{data.login_id}' already exists"
        )
    
    account = SandboxTestAccount(
        account_type=data.account_type,
        account_role=data.account_role,
        login_id=data.login_id,
        display_name=data.display_name,
        password_hash=_SM_SBX.get_password_hash(data.password),
        is_active=data.is_active,
        activation_start=data.activation_start,
        activation_end=data.activation_end,
        created_by_id=current_user.get('id'),
        created_by_code=current_user.get('emp_code')
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return account


@router.put("/test-accounts/{account_id}", response_model=SandboxTestAccountResponse)
async def update_test_account(
    account_id: int,
    data: SandboxTestAccountUpdate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Update a test account - VGK4U only"""
    require_vgk4u_access(current_user)
    
    account = db.query(SandboxTestAccount).filter(SandboxTestAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Test account not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)
    
    return account


@router.put("/test-accounts/{account_id}/password")
async def change_test_account_password(
    account_id: int,
    data: SandboxTestAccountPasswordChange = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Change test account password - VGK4U only"""
    require_vgk4u_access(current_user)
    
    account = db.query(SandboxTestAccount).filter(SandboxTestAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Test account not found")
    
    account.password_hash = _SM_SBX.get_password_hash(data.new_password)
    account.updated_at = datetime.now()
    db.commit()
    
    return {"success": True, "message": "Password updated successfully"}


@router.post("/test-accounts/bulk-activate")
async def bulk_activate_accounts(
    data: SandboxBulkActivation = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Bulk activate/deactivate test accounts - VGK4U only"""
    require_vgk4u_access(current_user)
    
    updated_count = 0
    for account_id in data.account_ids:
        account = db.query(SandboxTestAccount).filter(SandboxTestAccount.id == account_id).first()
        if account:
            account.is_active = data.is_active
            if data.activation_start:
                account.activation_start = data.activation_start
            if data.activation_end:
                account.activation_end = data.activation_end
            account.updated_at = datetime.now()
            updated_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Updated {updated_count} accounts",
        "updated_count": updated_count
    }


@router.delete("/test-accounts/{account_id}")
async def delete_test_account(
    account_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Delete a test account - VGK4U only"""
    require_vgk4u_access(current_user)
    
    account = db.query(SandboxTestAccount).filter(SandboxTestAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Test account not found")
    
    db.delete(account)
    db.commit()
    
    return {"success": True, "message": "Test account deleted"}


@router.post("/seed-test-accounts")
async def seed_default_test_accounts(
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Seed default test accounts for all roles - VGK4U only"""
    require_vgk4u_access(current_user)
    
    default_password = "TestAccount@123"
    password_hash = _SM_SBX.get_password_hash(default_password)
    
    default_accounts = [
        {"account_type": "STAFF", "account_role": "VGK4U", "login_id": "TESTVGK001", "display_name": "Test VGK4U Supreme (VIEW ONLY)"},
        {"account_type": "STAFF", "account_role": "MANAGER", "login_id": "TESTMGR001", "display_name": "Test Manager (VIEW ONLY)"},
        {"account_type": "STAFF", "account_role": "EMPLOYEE", "login_id": "TESTEMP001", "display_name": "Test Employee (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "RVZ ID", "login_id": "MNR111000001", "display_name": "Test RVZ Admin (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "VGK ID", "login_id": "MNR111000002", "display_name": "Test VGK Admin (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "Admin", "login_id": "MNR111000003", "display_name": "Test Admin (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "Super Admin", "login_id": "MNR111000004", "display_name": "Test Super Admin (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "Finance Admin", "login_id": "MNR111000005", "display_name": "Test Finance Admin (VIEW ONLY)"},
        {"account_type": "MNR", "account_role": "USER", "login_id": "MNR111000006", "display_name": "Test Regular User (VIEW ONLY)"},
        {"account_type": "PARTNER", "account_role": "DISTRIBUTOR", "login_id": "TESTDIST001", "display_name": "Test Distributor (VIEW ONLY)"},
        {"account_type": "PARTNER", "account_role": "DEALER", "login_id": "TESTDEAL001", "display_name": "Test Dealer (VIEW ONLY)"},
        {"account_type": "PARTNER", "account_role": "VENDOR", "login_id": "TESTVEND001", "display_name": "Test Vendor (VIEW ONLY)"},
        {"account_type": "PARTNER", "account_role": "REAL_DREAM_PARTNER", "login_id": "TESTRD001", "display_name": "Test Real Dream Partner (VIEW ONLY)"},
    ]
    
    created_count = 0
    skipped_count = 0
    
    for acc_data in default_accounts:
        existing = db.query(SandboxTestAccount).filter(
            SandboxTestAccount.login_id == acc_data["login_id"]
        ).first()
        
        if existing:
            skipped_count += 1
            continue
        
        account = SandboxTestAccount(
            account_type=acc_data["account_type"],
            account_role=acc_data["account_role"],
            login_id=acc_data["login_id"],
            display_name=acc_data["display_name"],
            password_hash=password_hash,
            is_active=True,
            created_by_id=current_user.get('id'),
            created_by_code=current_user.get('emp_code')
        )
        db.add(account)
        created_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Created {created_count} test accounts, skipped {skipped_count} existing",
        "created_count": created_count,
        "skipped_count": skipped_count,
        "default_password": default_password
    }


@router.get("/access-logs")
async def get_access_logs(
    limit: int = 50,
    account_type: Optional[str] = None,
    access_mode: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user_hybrid)
):
    """Get sandbox access logs - VGK4U only"""
    require_vgk4u_access(current_user)
    
    query = db.query(SandboxAccessLog)
    
    if account_type:
        query = query.filter(SandboxAccessLog.account_type == account_type)
    if access_mode:
        query = query.filter(SandboxAccessLog.access_mode == access_mode)
    
    logs = query.order_by(SandboxAccessLog.accessed_at.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "access_mode": log.access_mode,
        "account_type": log.account_type,
        "login_id": log.login_id,
        "page_accessed": log.page_accessed,
        "action_performed": log.action_performed,
        "ip_address": log.ip_address,
        "accessed_at": log.accessed_at.isoformat() if log.accessed_at else None
    } for log in logs]
