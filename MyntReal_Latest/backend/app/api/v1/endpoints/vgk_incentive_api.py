"""
MYNT OS — VGK Executive Incentive API Endpoints (V22 Idempotent Model)
Provides endpoints for Executive Member Overview, Multi-Segment Filters,
Lead Evaluation, Reconciled Financial Summaries, and Atomic Monthly Settlement Batches.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.services.universal_incentive_engine import (
    evaluate_file_v18_ledger,
    get_partner_current_position_v18,
    get_company_executive_summary_v18,
    process_monthly_settlement_atomic,
    seed_default_incentive_programs
)

router = APIRouter(prefix="/vgk/incentive", tags=["vgk-incentive"])


class MonthlySettlementRequest(BaseModel):
    partner_id: int
    settlement_period: str  # '2026-08'
    program_id: int = 1
    net_payable: float


@router.get("/executive-summary")
def get_executive_summary(db: Session = Depends(get_db)):
    """Returns company-wide reconciled V22 metrics for executive management dashboard."""
    seed_default_incentive_programs(db)
    summary = get_company_executive_summary_v18(db)
    return {
        "status": "success",
        "data": summary
    }


@router.get("/lead-evaluation/{lead_id}")
def evaluate_lead(lead_id: int, db: Session = Depends(get_db)):
    """Evaluates a single lead under Universal V22 rules."""
    res = evaluate_file_v18_ledger(db, lead_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return {"status": "success", "data": res}


@router.get("/partner-position/{partner_id}")
def get_partner_position(partner_id: int, db: Session = Depends(get_db)):
    """Returns a partner's L1-L4 tree count, active/activated team, and achieved rank."""
    pos = get_partner_current_position_v18(db, partner_id)
    return {"status": "success", "data": pos}


@router.post("/monthly-settlement/process")
def process_monthly_settlement(req: MonthlySettlementRequest, db: Session = Depends(get_db)):
    """
    Executes atomic, idempotent monthly settlement batch creation.
    Protected by PostgreSQL UNIQUE(partner_id, settlement_period, program_id) constraint.
    """
    try:
        settlement = process_monthly_settlement_atomic(
            db=db,
            partner_id=req.partner_id,
            settlement_period=req.settlement_period,
            program_id=req.program_id,
            net_payable=req.net_payable
        )
        return {
            "status": "success",
            "message": "Monthly settlement processed successfully with 100% DB-level atomic idempotency.",
            "data": settlement
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Settlement error: {str(e)}")
