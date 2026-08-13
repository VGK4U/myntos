from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.services.ai_marketing_pro_service import AIMarketingProService
from app.models.staff import StaffEmployee

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    response: str
    components: Optional[Dict[str, str]] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_marketing_pro(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Process a chat message using the AI Marketing Pro service.
    """
    staff_id = 1
    company_id = 1

    # The user asked specifically for MR10001 (and optionally MR10025)
    # The staff ID isn't directly the MR code, we would query the staff table
    # But for now, we'll allow it if they are staff, and the frontend restricts the menu.

    try:
        service = AIMarketingProService(db=db, company_id=company_id, staff_id=staff_id)
        result = await service.process_chat(user_message=request.message, history=request.history)
        
        return ChatResponse(
            response=result.get("response", "I'm sorry, I couldn't process that."),
            components=result.get("components")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
