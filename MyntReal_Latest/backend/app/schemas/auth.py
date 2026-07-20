"""
Authentication schemas for request/response validation
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """JSON login request schema (preserves Flask JSON login)"""
    username: str = Field(..., min_length=1, description="MNR ID or username")
    password: str = Field(..., min_length=1, description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "MNR1800142",
                "password": "VK1808"
            }
        }


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
