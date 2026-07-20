"""
Standard API Response Models for FastAPI
Provides consistent response structure across all endpoints
"""

from typing import Any, Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime

class ApiResponse(BaseModel):
    """Standard API response envelope"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PaginatedResponse(BaseModel):
    """Paginated API response"""
    success: bool
    message: str
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    message: str
    errors: List[str]
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """Create a success response"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

def error_response(message: str, errors: List[str] = None, error_code: str = None) -> Dict[str, Any]:
    """Create an error response"""
    return {
        "success": False,
        "message": message,
        "errors": errors or [],
        "error_code": error_code,
        "timestamp": datetime.utcnow().isoformat()
    }

def paginated_response(message: str, data: List[Any], page: int, per_page: int, total: int) -> Dict[str, Any]:
    """Create a paginated response"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }
