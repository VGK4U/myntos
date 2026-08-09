"""
Meta OAuth 2.0 Integration & Account 560062103113819 Connection Endpoints (Phase 2E)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.services.meta_oauth_service import (
    get_meta_oauth_login_url,
    exchange_code_for_long_lived_token,
    discover_and_connect_meta_ad_account
)

router = APIRouter(prefix="/meta/oauth", tags=["Meta OAuth 2.0 Connection"])


class CompleteConnectionRequest(BaseModel):
    user_token: str
    company_id: int = 1
    target_ad_account: str = "560062103113819"


@router.get("/login-url")
def get_oauth_login_url(
    request: Request,
    company_id: int = Query(default=1),
    app_id: Optional[str] = Query(default=None),
    redirect_uri: Optional[str] = Query(default=None),
    redirect: bool = Query(default=False)
):
    """
    Get official Meta OAuth 2.0 login URL for user authorization.
    Pass ?redirect=true or visit GET /api/v1/meta/oauth/authorize to redirect directly in browser.
    """
    if not redirect_uri:
        base = str(request.base_url).rstrip("/")
        redirect_uri = f"{base}/api/v1/meta/oauth/callback"

    info = get_meta_oauth_login_url(company_id=company_id, redirect_uri=redirect_uri, app_id=app_id)
    if redirect:
        return RedirectResponse(url=info["oauth_login_url"])
    return info


@router.get("/authorize")
def authorize_meta_direct_redirect(
    request: Request,
    company_id: int = Query(default=1),
    app_id: Optional[str] = Query(default=None)
):
    """
    Direct HTTP 307 Browser Redirect to Meta OAuth Authorization Dialog.
    """
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/api/v1/meta/oauth/callback"
    info = get_meta_oauth_login_url(company_id=company_id, redirect_uri=redirect_uri, app_id=app_id)
    return RedirectResponse(url=info["oauth_login_url"])


@router.get("/callback")
def meta_oauth_callback(
    code: str = Query(...),
    state: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Meta OAuth callback handler. Exchanges auth code for access token and discovers Ad Account 560062103113819.
    """
    from app.services.meta_oauth_service import validate_csrf_state
    if state and not validate_csrf_state(state):
        raise HTTPException(status_code=403, detail="CSRF state validation failed. Potential security risk.")

    ex_res = exchange_code_for_long_lived_token(code)
    if not ex_res.get("success"):
        raise HTTPException(status_code=400, detail=ex_res.get("error", "OAuth token exchange failed"))

    token = ex_res.get("long_lived_token")
    conn_res = discover_and_connect_meta_ad_account(db, user_token=token, company_id=1, target_ad_account="560062103113819")
    return conn_res


@router.post("/complete-connection")
def complete_meta_connection(
    data: CompleteConnectionRequest,
    db: Session = Depends(get_db)
):
    """
    Direct token submission and discovery endpoint for target Ad Account 560062103113819.
    """
    res = discover_and_connect_meta_ad_account(
        db=db,
        user_token=data.user_token,
        company_id=data.company_id,
        target_ad_account=data.target_ad_account
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Connection failed"))
    return res
