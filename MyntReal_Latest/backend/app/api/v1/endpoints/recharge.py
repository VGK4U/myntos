from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.recharge import RechargeTransaction
from pydantic import BaseModel
import razorpay
import requests

A1TOPUP_OPERATOR_MAP = {
    "Airtel": "A",
    "Jio": "RC",
    "VI": "V",
    "BSNL": "BT"
}

router = APIRouter()

# Initialize Razorpay Client
if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
else:
    razorpay_client = None


class CreateOrderRequest(BaseModel):
    amount: float # in INR
    mobile_number: str
    operator: str
    circle: str = None
    guest_email: str = None
    guest_name: str = None

@router.post("/create-order")
def create_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET) are missing in the server's .env file.")

    # 1. Create order in Razorpay (amount in paise)
    order_amount = int(req.amount * 100)
    order_currency = "INR"

    
    try:
        payment_order = razorpay_client.order.create(dict(
            amount=order_amount,
            currency=order_currency,
            payment_capture='1'
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")
        
    # 2. Save transaction to DB
    new_tx = RechargeTransaction(
        mobile_number=req.mobile_number,
        operator=req.operator,
        circle=req.circle,
        amount=req.amount,
        guest_email=req.guest_email,
        guest_name=req.guest_name,
        razorpay_order_id=payment_order['id'],
        payment_status="Pending",
        api_status="Pending"
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    
    return {
        "order_id": payment_order['id'],
        "amount": order_amount,
        "currency": order_currency,
        "key_id": settings.RAZORPAY_KEY_ID,
        "transaction_id": new_tx.id
    }

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    
@router.post("/verify-payment")
def verify_payment(req: VerifyPaymentRequest, db: Session = Depends(get_db)):
    tx = db.query(RechargeTransaction).filter(
        RechargeTransaction.razorpay_order_id == req.razorpay_order_id
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    # Verify signature
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        })
    except razorpay.errors.SignatureVerificationError:
        tx.payment_status = "Failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid payment signature")
        
    # Signature is valid
    tx.razorpay_payment_id = req.razorpay_payment_id
    tx.razorpay_signature = req.razorpay_signature
    tx.payment_status = "Paid"
    db.commit()
    
    # A1Topup Trigger (Step 3)
    if getattr(settings, "A1TOPUP_TEST_MODE", True):
        # Mock mode prevents real money deduction
        tx.api_status = "Success"
        tx.api_tx_id = f"MOCK_A1_{tx.id}"
        tx.api_operator_id = "MOCK_OP_123"
        db.commit()
    else:
        # Call Real A1Topup API
        if settings.A1TOPUP_USERNAME and settings.A1TOPUP_PASSWORD:
            a1_url = "https://business.a1topup.com/recharge/api"
            operator_code = A1TOPUP_OPERATOR_MAP.get(tx.operator, "A")
            
            params = {
                "username": settings.A1TOPUP_USERNAME,
                "pwd": settings.A1TOPUP_PASSWORD,
                "operatorcode": operator_code,
                "number": tx.mobile_number,
                "amount": int(tx.amount),
                "orderid": str(tx.id),
                "format": "json"
            }
            if tx.circle:
                params["circlecode"] = tx.circle
                
            try:
                response = requests.get(a1_url, params=params)
                data = response.json()
                if data.get("status") == "Success":
                    tx.api_status = "Success"
                    tx.api_tx_id = str(data.get("txid", ""))
                    tx.api_operator_id = str(data.get("opid", ""))
                else:
                    tx.api_status = "Failed"
                    tx.api_tx_id = str(data.get("txid", "ERROR"))
            except Exception as e:
                print(f"A1Topup API Error: {e}")
                tx.api_status = "Failed"
                
            db.commit()
        else:
            tx.api_status = "Failed"
            db.commit()
    
    return {
        "status": "success", 
        "message": "Payment verified and recharge initiated", 
        "transaction_id": tx.id,
        "recharge_status": tx.api_status
    }

from app.models.recharge import RechargePlan

@router.get("/plans")
def get_plans(operator: str = None, db: Session = Depends(get_db)):
    """
    Fetch static recharge plans for a given operator.
    """
    query = db.query(RechargePlan)
    if operator:
        # Match case-insensitively or exactly depending on frontend implementation
        # A1Topup has specific codes, but we seeded with strings like 'Airtel', 'Vodafone', 'RELIANCE - JIO', 'BSNL - TOPUP'
        # Frontend might just pass 'Airtel' etc.
        query = query.filter(RechargePlan.operator.ilike(f"%{operator}%"))
        
    plans = query.all()
    
    return [
        {
            "id": p.id,
            "operator": p.operator,
            "circle": p.circle,
            "amount": p.amount,
            "validity": p.validity,
            "data_benefit": p.data_benefit,
            "description": p.description
        } for p in plans
    ]

@router.get("/callback")
def a1topup_callback(txid: str, status: str, opid: str, db: Session = Depends(get_db)):
    """
    Webhook endpoint for A1Topup to send async status updates.
    URL Format: ?txid=ORDER_ID&status=Success/Failure&opid=OPERATOR_ID
    """
    try:
        tx = db.query(RechargeTransaction).filter(RechargeTransaction.id == int(txid)).first()
        if tx:
            tx.api_status = status
            tx.api_operator_id = opid
            db.commit()
    except Exception as e:
        print(f"Callback processing error: {e}")
        
    return {"status": "success"}
