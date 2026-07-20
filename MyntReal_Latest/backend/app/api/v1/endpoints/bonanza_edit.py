"""
RVZ-Only Bonanza Edit Endpoint
Allows RVZ to update bonanza details
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.models.bonanza import Bonanza
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/bonanza", tags=["Bonanza Edit - RVZ Only"])


class BonanzaUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_requirement: Optional[int] = None
    max_winners: Optional[int] = None
    award_name: Optional[str] = None
    reward_amount: Optional[float] = None
    # DC_BONANZA_SLABWISE_001
    slab_extra_amount: Optional[float] = None
    slab_base_reference: Optional[float] = None
    # DC-SOLAR-DVR-ADV-20260701-001
    advance_count_basis: Optional[str] = None


@router.put("/edit/{bonanza_id}")
async def edit_bonanza(
    bonanza_id: int,
    data: BonanzaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RVZ-only endpoint to edit bonanza details
    Cannot edit if users have already claimed
    """
    # RVZ-only access
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
        raise HTTPException(
            status_code=403,
            detail="Only RVZ ID can edit bonanzas"
        )
    
    # Get bonanza
    bonanza = db.query(Bonanza).filter(Bonanza.id == bonanza_id).first()
    if not bonanza:
        raise HTTPException(status_code=404, detail="Bonanza not found")
    
    # DC PROTOCOL: Allow editing but enforce data consistency
    # Update fields (only if provided)
    if data.name is not None:
        bonanza.name = data.name
    
    if data.start_date is not None:
        bonanza.start_date = data.start_date
    
    if data.end_date is not None:
        bonanza.end_date = data.end_date
    
    if data.target_requirement is not None:
        bonanza.target_requirement = data.target_requirement
    
    if data.max_winners is not None:
        if data.max_winners < 1 or data.max_winners > 500:
            raise HTTPException(
                status_code=400,
                detail="Max winners must be between 1 and 500"
            )
        # DC PROTOCOL: Cannot set max_winners lower than current claims
        if data.max_winners < bonanza.current_winners:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Cannot set max winners to {data.max_winners}. Already {bonanza.current_winners} users have claimed this bonanza. Max winners must be at least {bonanza.current_winners}."
            )
        bonanza.max_winners = data.max_winners
    
    if data.award_name is not None:
        bonanza.award_name = data.award_name
    
    if data.reward_amount is not None and bonanza.is_monetary:
        bonanza.reward_amount = data.reward_amount

    # DC_BONANZA_SLABWISE_001: allow updating slab amounts directly
    if data.slab_extra_amount is not None:
        bonanza.slab_extra_amount = data.slab_extra_amount
    if data.slab_base_reference is not None:
        bonanza.slab_base_reference = data.slab_base_reference
    # DC-SOLAR-DVR-ADV-20260701-001
    if data.advance_count_basis is not None and data.advance_count_basis in ('CIBIL', 'DVR', 'BOTH'):
        bonanza.advance_count_basis = data.advance_count_basis

    bonanza.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(bonanza)
    
    return {
        "success": True,
        "message": f"Bonanza '{bonanza.name}' updated successfully",
        "bonanza": {
            "id": bonanza.id,
            "name": bonanza.name,
            "start_date": bonanza.start_date.isoformat(),
            "end_date": bonanza.end_date.isoformat(),
            "target_requirement": bonanza.target_requirement,
            "max_winners": bonanza.max_winners,
            "award_name": bonanza.award_name,
            "reward_amount": float(bonanza.reward_amount) if bonanza.reward_amount else None,
            # DC_BONANZA_SLABWISE_001
            "slab_extra_amount": float(bonanza.slab_extra_amount) if bonanza.slab_extra_amount else None,
            "slab_base_reference": float(bonanza.slab_base_reference) if bonanza.slab_base_reference else None,
            # DC-SOLAR-DVR-ADV-20260701-001
            "advance_count_basis": bonanza.advance_count_basis or 'CIBIL',
        }
    }
