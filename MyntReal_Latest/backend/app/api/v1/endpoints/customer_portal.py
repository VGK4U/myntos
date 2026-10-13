"""
Universal Customer Portal Endpoints (DC Protocol / Oct 2026)
Provides multi-vertical customer access across:
1. Profile Setup & Security PIN (Phone + 4-digit PIN)
2. Customer Authentication
3. Executive Interaction Dashboard (Recharges, Utilities, Cashback, Solar, EV, Students)
4. Quick Redo Repeat Transactions
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import re

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.core.security import SecurityManager
from app.models.customer_profile import CustomerProfile
from app.schemas.customer_portal import (
    CustomerProfileCreate,
    CustomerLoginRequest,
    ResetPinRequest,
    CustomerAuthResponse,
    CustomerProfileOut,
    QuickRedoRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer", tags=["Customer Portal"])

CUSTOMER_JWT_SECRET = settings.SECRET_KEY
CUSTOMER_JWT_ALGORITHM = "HS256"
CUSTOMER_TOKEN_EXPIRE_DAYS = 90


def get_current_customer(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> CustomerProfile:
    """Dependency: Extract verified customer from Bearer JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, CUSTOMER_JWT_SECRET, algorithms=[CUSTOMER_JWT_ALGORITHM])
        role = payload.get("role")
        mobile = payload.get("sub")
        if role != "customer" or not mobile:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid customer token credentials"
            )
        customer = db.query(CustomerProfile).filter_by(mobile_number=mobile, is_active=True).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer account not found"
            )
        return customer
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again."
        )


@router.post("/create-profile", response_model=CustomerAuthResponse)
def create_customer_profile(payload: CustomerProfileCreate, db: Session = Depends(get_db)):
    """
    Post-recharge / Direct customer profile registration.
    Saves Customer Name, Postal PIN code, and 4-digit Security PIN.
    """
    clean_phone = payload.mobile_number
    hashed_pin = SecurityManager.get_password_hash(payload.security_pin)

    customer = db.query(CustomerProfile).filter_by(mobile_number=clean_phone).first()
    if customer:
        customer.customer_name = payload.customer_name
        customer.pincode = payload.pincode
        customer.security_pin_hash = hashed_pin
        if payload.email:
            customer.email = payload.email
        if payload.city:
            customer.city = payload.city
        if payload.state:
            customer.state = payload.state
        customer.updated_at = datetime.utcnow()
    else:
        customer = CustomerProfile(
            mobile_number=clean_phone,
            customer_name=payload.customer_name,
            pincode=payload.pincode,
            security_pin_hash=hashed_pin,
            email=payload.email,
            city=payload.city,
            state=payload.state,
            is_active=True
        )
        db.add(customer)

    db.commit()
    db.refresh(customer)

    # Issue Customer JWT (valid for 90 days)
    token_data = {
        "sub": customer.mobile_number,
        "customer_id": customer.id,
        "name": customer.customer_name,
        "role": "customer",
        "exp": datetime.utcnow() + timedelta(days=CUSTOMER_TOKEN_EXPIRE_DAYS)
    }
    jwt_token = jwt.encode(token_data, CUSTOMER_JWT_SECRET, algorithm=CUSTOMER_JWT_ALGORITHM)

    return CustomerAuthResponse(
        success=True,
        message="Profile created successfully. Welcome to your Executive Customer Hub!",
        token=jwt_token,
        customer=CustomerProfileOut.from_orm(customer)
    )


@router.post("/login", response_model=CustomerAuthResponse)
def customer_login(payload: CustomerLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate customer via 10-digit Mobile Number + 4-digit Security PIN.
    """
    clean_phone = payload.mobile_number
    customer = db.query(CustomerProfile).filter_by(mobile_number=clean_phone, is_active=True).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found. Please click 'Create Profile' to set up your 4-digit PIN."
        )

    if not SecurityManager.verify_password(payload.security_pin, customer.security_pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect 4-digit Security PIN. Please try again."
        )

    token_data = {
        "sub": customer.mobile_number,
        "customer_id": customer.id,
        "name": customer.customer_name,
        "role": "customer",
        "exp": datetime.utcnow() + timedelta(days=CUSTOMER_TOKEN_EXPIRE_DAYS)
    }
    jwt_token = jwt.encode(token_data, CUSTOMER_JWT_SECRET, algorithm=CUSTOMER_JWT_ALGORITHM)

    return CustomerAuthResponse(
        success=True,
        message=f"Welcome back, {customer.customer_name}!",
        token=jwt_token,
        customer=CustomerProfileOut.from_orm(customer)
    )


@router.post("/reset-pin", response_model=CustomerAuthResponse)
def reset_customer_pin(payload: ResetPinRequest, db: Session = Depends(get_db)):
    """
    Reset customer 4-digit Security PIN using registered Postal PIN code as secondary challenge.
    """
    clean_phone = payload.mobile_number
    customer = db.query(CustomerProfile).filter_by(mobile_number=clean_phone, is_active=True).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this mobile number."
        )

    clean_pincode = payload.pincode.strip()
    if customer.pincode.strip() != clean_pincode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Postal PIN code does not match registered profile records."
        )

    customer.security_pin_hash = SecurityManager.get_password_hash(payload.new_security_pin)
    customer.updated_at = datetime.utcnow()
    db.commit()

    token_data = {
        "sub": customer.mobile_number,
        "customer_id": customer.id,
        "name": customer.customer_name,
        "role": "customer",
        "exp": datetime.utcnow() + timedelta(days=CUSTOMER_TOKEN_EXPIRE_DAYS)
    }
    jwt_token = jwt.encode(token_data, CUSTOMER_JWT_SECRET, algorithm=CUSTOMER_JWT_ALGORITHM)

    return CustomerAuthResponse(
        success=True,
        message="4-digit Security PIN updated successfully!",
        token=jwt_token,
        customer=CustomerProfileOut.from_orm(customer)
    )


@router.get("/me")
def get_customer_profile_info(current_customer: CustomerProfile = Depends(get_current_customer)):
    """Return verified customer profile info."""
    return {
        "success": True,
        "customer": CustomerProfileOut.from_orm(current_customer)
    }


@router.get("/dashboard")
def get_customer_dashboard_data(
    current_customer: CustomerProfile = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Executive Multi-Vertical Dashboard Data aggregator.
    Returns:
    1. Overall executive KPI cards (Spend, Cashback, Reward Points, Service counts)
    2. Recharges Ledger (Prepaid & Postpaid)
    3. Utility Bills Ledger (Electricity, Gas, DTH, FASTag, LIC)
    4. Cashback & Scratch Cards Hub
    5. Solar Customer Hub (Quotes, Site Visits, Sanctions)
    6. EV Customer Hub (Bookings, Battery warranty, Service tickets)
    7. Students & ETC Training Hub (Course enrollments & status)
    """
    phone = current_customer.mobile_number

    # 1. Total Spend Calculation
    spend_row = db.execute(text("""
        SELECT COALESCE(SUM(amount), 0), COUNT(id)
        FROM recharge_transactions
        WHERE (mobile_number = :phone OR value2 = :phone)
          AND (payment_status = 'Success' OR payment_status ILIKE '%success%')
    """), {"phone": phone}).fetchone()
    total_spend = float(spend_row[0]) if spend_row else 0.0
    total_tx_count = int(spend_row[1]) if spend_row else 0

    # 2. Total Cashback Won & Claimed
    cashback_row = db.execute(text("""
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'claimed' THEN allocated_amount_paise ELSE 0 END), 0) / 100.0 AS claimed_amt,
            COALESCE(SUM(CASE WHEN status = 'active' THEN allocated_amount_paise ELSE 0 END), 0) / 100.0 AS pending_amt,
            COUNT(id) AS total_cards
        FROM scratch_cards
        WHERE mobile_number = :phone
    """), {"phone": phone}).fetchone()
    cashback_claimed = float(cashback_row[0]) if cashback_row else 0.0
    cashback_pending = float(cashback_row[1]) if cashback_row else 0.0
    total_scratch_cards = int(cashback_row[2]) if cashback_row else 0

    # 3. Recharges Tab (Prepaid & Postpaid)
    recharges_rows = db.execute(text("""
        SELECT id, operator, circle, amount, payment_status, api_status, created_at, mobile_number, service_type
        FROM recharge_transactions
        WHERE (mobile_number = :phone OR value2 = :phone)
          AND (service_type IN ('mobile', 'postpaid') OR service_type IS NULL)
        ORDER BY created_at DESC
        LIMIT 50
    """), {"phone": phone}).fetchall()
    recharges = [
        {
            "id": r[0],
            "operator": r[1] or "Mobile",
            "circle": r[2] or "India",
            "amount": float(r[3] or 0),
            "payment_status": r[4] or "Pending",
            "api_status": r[5] or "Pending",
            "created_at": r[6].isoformat() if r[6] else None,
            "target_number": r[7],
            "service_type": r[8] or "mobile"
        }
        for r in recharges_rows
    ]

    # 4. Utility Bills Tab (Electricity, Gas, DTH, FASTag, Insurance, Google Play)
    bills_rows = db.execute(text("""
        SELECT id, service_type, operator, circle, amount, payment_status, api_status, created_at, mobile_number, value1, value2
        FROM recharge_transactions
        WHERE (mobile_number = :phone OR value2 = :phone)
          AND service_type NOT IN ('mobile', 'postpaid')
        ORDER BY created_at DESC
        LIMIT 50
    """), {"phone": phone}).fetchall()
    utility_bills = [
        {
            "id": r[0],
            "service_type": r[1] or "utility",
            "operator": r[2] or "Board/Provider",
            "circle": r[3] or "",
            "amount": float(r[4] or 0),
            "payment_status": r[5] or "Pending",
            "api_status": r[6] or "Pending",
            "created_at": r[7].isoformat() if r[7] else None,
            "account_identifier": r[8] or r[9],
            "customer_phone": r[10] or phone
        }
        for r in bills_rows
    ]

    # 5. Cashback & Scratch Cards Gallery
    cards_rows = db.execute(text("""
        SELECT id, brand, allocated_amount_paise, status, claimed_at, created_at, referral_code, expires_at
        FROM scratch_cards
        WHERE mobile_number = :phone
        ORDER BY created_at DESC
        LIMIT 50
    """), {"phone": phone}).fetchall()
    scratch_cards_list = [
        {
            "id": r[0],
            "brand": r[1] or "MyntReal",
            "amount_rupees": float(r[2] or 0) / 100.0,
            "status": r[3] or "active",
            "claimed_at": r[4].isoformat() if r[4] else None,
            "created_at": r[5].isoformat() if r[5] else None,
            "referral_code": r[6] or f"MYNT{r[0]:04d}",
            "expires_at": r[7].isoformat() if r[7] else None,
            "claim_url": f"/scratch-card.html"
        }
        for r in cards_rows
    ]

    # 6. Solar Projects Hub
    # 6. Solar Projects Hub
    solar_rows = db.execute(text("""
        SELECT id, name, looking_for, status, solar_pipeline_status, kw_size, discom, sanction_date, created_at
        FROM crm_leads
        WHERE phone LIKE :phone_like
          AND (
              kw_size IS NOT NULL
              OR solar_pipeline_status IS NOT NULL
              OR LOWER(looking_for) LIKE '%solar%'
              OR LOWER(description) LIKE '%solar%'
              OR LOWER(requirements) LIKE '%solar%'
          )
        ORDER BY created_at DESC
        LIMIT 10
    """), {"phone_like": f"%{phone}%"}).fetchall()
    solar_projects = [
        {
            "id": r[0],
            "project_name": r[1] or "Rooftop Solar Project",
            "capacity": f"{r[5]} kW" if r[5] else "Residential Solar",
            "discom": r[6] or "Electricity Board",
            "status": r[4] or r[3] or "Assessment in Progress",
            "sanction_date": r[7].isoformat() if r[7] else None,
            "created_at": r[8].isoformat() if r[8] else None
        }
        for r in solar_rows
    ]

    # 7. EV Vehicle, Battery & Service Tickets Hub
    ev_rows = db.execute(text("""
        SELECT id, name, looking_for, status, ev_b2b_stage, description, created_at
        FROM crm_leads
        WHERE phone LIKE :phone_like
          AND (
              ev_b2b_stage IS NOT NULL
              OR LOWER(looking_for) LIKE '%ev%'
              OR LOWER(looking_for) LIKE '%manthra%'
              OR LOWER(looking_for) LIKE '%scooter%'
              OR LOWER(description) LIKE '%ev%'
              OR LOWER(description) LIKE '%battery%'
          )
        ORDER BY created_at DESC
        LIMIT 10
    """), {"phone_like": f"%{phone}%"}).fetchall()
    
    tickets_rows = db.execute(text("""
        SELECT id, ticket_id, issue_category, status, priority, created_date
        FROM service_ticket
        WHERE customer_phone LIKE :phone_like
        ORDER BY created_date DESC
        LIMIT 10
    """), {"phone_like": f"%{phone}%"}).fetchall()

    ev_hub = {
        "vehicles": [
            {
                "id": r[0],
                "model_name": r[2] or r[1] or "Manthra EV Smart Scooter",
                "status": r[4] or r[3] or "Active Booking",
                "details": r[5] or "Vehicle order verified.",
                "created_at": r[6].isoformat() if r[6] else None
            }
            for r in ev_rows
        ],
        "service_tickets": [
            {
                "id": t[0],
                "ticket_number": t[1] or f"TKT-{t[0]}",
                "title": t[2] or "Support Service Ticket",
                "status": t[3] or "Open",
                "priority": t[4] or "Normal",
                "created_at": t[5].isoformat() if t[5] else None
            }
            for t in tickets_rows
        ]
    }

    # 8. Student & EVolution ETC Training Hub
    training_rows = db.execute(text("""
        SELECT id, name, looking_for, status, description, created_at
        FROM crm_leads
        WHERE phone LIKE :phone_like
          AND (
              LOWER(looking_for) LIKE '%training%'
              OR LOWER(looking_for) LIKE '%evolution%'
              OR LOWER(looking_for) LIKE '%etc%'
              OR LOWER(description) LIKE '%training%'
              OR LOWER(requirements) LIKE '%training%'
          )
        ORDER BY created_at DESC
        LIMIT 10
    """), {"phone_like": f"%{phone}%"}).fetchall()
    training_programs = [
        {
            "id": r[0],
            "program_name": r[2] or "EVolution Technical Training (ETC Labs)",
            "batch_status": r[3] or "Enrolled",
            "details": r[4] or "Practical hands-on battery pack BMS assembly and EV technician workshop.",
            "created_at": r[5].isoformat() if r[5] else None
        }
        for r in training_rows
    ]

    return {
        "success": True,
        "profile": CustomerProfileOut.from_orm(current_customer),
        "kpi": {
            "total_spend": total_spend,
            "total_transactions": total_tx_count,
            "cashback_claimed": cashback_claimed,
            "cashback_pending": cashback_pending,
            "scratch_cards_count": total_scratch_cards,
            "referral_bonus_pct": 50,
            "active_services_count": (1 if recharges else 0) + (1 if utility_bills else 0) + (1 if solar_projects else 0) + (1 if ev_rows else 0) + (1 if training_programs else 0)
        },
        "recharges": recharges,
        "utility_bills": utility_bills,
        "scratch_cards": scratch_cards_list,
        "solar_projects": solar_projects,
        "ev_hub": ev_hub,
        "training_programs": training_programs
    }


@router.post("/quick-redo")
def prepare_quick_redo(
    payload: QuickRedoRequest,
    current_customer: CustomerProfile = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """
    Smart 'Quick Redo' repeat transaction generator.
    Fetches the historical transaction, allows amount change or proceed as-is,
    and returns pre-filled payload ready for instant Razorpay checkout.
    """
    tx = db.execute(text("""
        SELECT id, operator, circle, amount, service_type, mobile_number, value1, value2
        FROM recharge_transactions
        WHERE id = :txid
          AND (mobile_number = :phone OR value2 = :phone)
    """), {"txid": payload.transaction_id, "phone": current_customer.mobile_number}).fetchone()

    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or unauthorized"
        )

    final_amount = float(payload.amount) if (payload.amount and payload.amount > 0) else float(tx[3])

    return {
        "success": True,
        "repeat_session": {
            "original_tx_id": tx[0],
            "service_type": tx[4] or "mobile",
            "operator": tx[1] or "",
            "circle": tx[2] or "",
            "amount": final_amount,
            "target_account": tx[5],
            "value1": tx[6] or "",
            "value2": tx[7] or current_customer.mobile_number,
            "customer_name": current_customer.customer_name,
            "customer_mobile": current_customer.mobile_number,
            "customer_email": current_customer.email or f"{current_customer.mobile_number}@customer.vgk4u.com"
        }
    }
