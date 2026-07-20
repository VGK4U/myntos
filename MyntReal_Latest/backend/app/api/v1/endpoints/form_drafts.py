import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.form_draft import FormDraft

router = APIRouter()

_DRAFT_TTL_DAYS = 7


class DraftUpsert(BaseModel):
    draft_data: Optional[str] = None
    page_url: Optional[str] = None


def _get_draft_user(request: Request):
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip() if auth else None
    if not token:
        token = request.query_params.get('_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get('sub') or payload.get('user_id') or payload.get('id')
        user_type = str(payload.get('user_type', 'staff'))
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return str(sub), user_type
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.put("/drafts/{form_key}")
async def upsert_draft(
    form_key: str,
    body: DraftUpsert,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id, user_type = _get_draft_user(request)
    expires = datetime.datetime.now() + datetime.timedelta(days=_DRAFT_TTL_DAYS)
    draft = db.query(FormDraft).filter(
        FormDraft.user_id == user_id,
        FormDraft.user_type == user_type,
        FormDraft.form_key == form_key,
    ).first()
    if draft:
        draft.draft_data = body.draft_data
        draft.page_url = body.page_url
        draft.updated_at = datetime.datetime.now()
        draft.expires_at = expires
    else:
        draft = FormDraft(
            user_id=user_id,
            user_type=user_type,
            form_key=form_key,
            draft_data=body.draft_data,
            page_url=body.page_url,
            expires_at=expires,
        )
        db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"success": True, "draft": draft.to_dict()}


@router.get("/drafts/{form_key}")
async def get_draft(
    form_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id, user_type = _get_draft_user(request)
    draft = db.query(FormDraft).filter(
        FormDraft.user_id == user_id,
        FormDraft.user_type == user_type,
        FormDraft.form_key == form_key,
        FormDraft.expires_at > datetime.datetime.now(),
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="No draft found")
    return draft.to_dict()


@router.delete("/drafts/{form_key}")
async def delete_draft(
    form_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id, user_type = _get_draft_user(request)
    db.query(FormDraft).filter(
        FormDraft.user_id == user_id,
        FormDraft.user_type == user_type,
        FormDraft.form_key == form_key,
    ).delete()
    db.commit()
    return {"success": True}


@router.get("/drafts")
async def list_drafts(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id, user_type = _get_draft_user(request)
    drafts = (
        db.query(FormDraft)
        .filter(
            FormDraft.user_id == user_id,
            FormDraft.user_type == user_type,
            FormDraft.expires_at > datetime.datetime.now(),
        )
        .order_by(FormDraft.updated_at.desc())
        .all()
    )
    return [d.to_dict() for d in drafts]
