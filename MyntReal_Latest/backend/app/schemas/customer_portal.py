"""
Customer Portal Pydantic Schemas (DC Protocol / Oct 2026)
Defines request/response contracts for:
- Profile Setup & PIN Creation
- Customer Login (Phone + 4-digit Security PIN)
- Executive Multi-Vertical Dashboard
- Quick Redo Repeated Transactions
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import re


class CustomerProfileCreate(BaseModel):
    mobile_number: str = Field(..., description="10-digit mobile number")
    customer_name: str = Field(..., min_length=2, max_length=128, description="Customer full name")
    pincode: str = Field(..., min_length=6, max_length=10, description="Postal PIN code")
    security_pin: str = Field(..., min_length=4, max_length=4, description="4-digit Security PIN")
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    @validator("mobile_number")
    def validate_mobile(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Mobile number must be a valid 10-digit Indian number")
        return digits

    @validator("security_pin")
    def validate_pin(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) != 4:
            raise ValueError("Security PIN must be exactly 4 numeric digits")
        return digits


class CustomerLoginRequest(BaseModel):
    mobile_number: str = Field(..., description="10-digit mobile number")
    security_pin: str = Field(..., min_length=4, max_length=4, description="4-digit Security PIN")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Mobile number must be a valid 10-digit Indian number")
        return digits

    @validator("security_pin")
    def validate_pin(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) != 4:
            raise ValueError("Security PIN must be exactly 4 numeric digits")
        return digits


class ResetPinRequest(BaseModel):
    mobile_number: str
    pincode: str
    new_security_pin: str

    @validator("mobile_number")
    def validate_mobile(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Mobile number must be a valid 10-digit Indian number")
        return digits

    @validator("new_security_pin")
    def validate_pin(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) != 4:
            raise ValueError("Security PIN must be exactly 4 numeric digits")
        return digits


class CustomerProfileOut(BaseModel):
    id: int
    mobile_number: str
    customer_name: str
    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerAuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    token_type: str = "bearer"
    customer: Optional[CustomerProfileOut] = None


class QuickRedoRequest(BaseModel):
    transaction_id: int
    amount: Optional[float] = None
    custom_amount: Optional[float] = None
    service_type: Optional[str] = None
