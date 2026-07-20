"""
Audience Switch Audit endpoint — Task #33 VGK4U Parity Phase 1

Records every time a staff user toggles the audience tab (MNR ↔ VGK4U) on a
read-only admin page. Powered by the existing StaffAuditLog table via the
log_staff_audit helper.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_rvz_user_hybrid as get_current_staff_user

router = APIRouter()


class AudienceSwitchPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: str | None = None
    from_: str | None = Field(default=None, alias='from')
    to: str | None = None
    ts: str | None = None


@router.post("/audit/audience-switch")
async def audience_switch(
    payload: AudienceSwitchPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user),
):
    """Persist audience-tab switch event into staff_audit_logs (best-effort).

    Failure path returns a generic error code only — never raw exception
    text — to avoid information disclosure (server stack/SQL leak via the
    HTTP body). Full detail is captured in server logs for ops.
    """
    import logging
    log = logging.getLogger(__name__)
    try:
        from app.models.staff import log_staff_audit
        # Note: staff_audit_log.resource_id is INTEGER. Embed the page
        # slug (a string) in new_data['page'] instead — keeps the audit
        # row schema-valid and preserves the tab/page context.
        log_staff_audit(
            db,
            employee_id=getattr(current_user, 'id', None) or 0,
            action='audience_switch',
            resource_type='admin_page',
            resource_id=None,
            old_data={"audience": payload.from_},
            new_data={"audience": payload.to,
                      "ts": payload.ts,
                      "page": payload.page or ''},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.warning("audience_switch audit failed: %s", e, exc_info=True)
        return {"ok": False, "error": "audit_failed"}
