"""
Custom Exceptions and Error Handlers
Standardized error handling across the application
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Any, Dict

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class BusinessLogicError(AppException):
    """Business logic validation error"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)

class ResourceNotFoundError(AppException):
    """Resource not found error"""
    def __init__(self, resource: str, resource_id: str):
        message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class InsufficientFundsError(BusinessLogicError):
    """Insufficient funds for transaction"""
    def __init__(self, required: float, available: float):
        message = f"Insufficient funds. Required: ₹{required}, Available: ₹{available}"
        super().__init__(message, {'required': required, 'available': available})

class DuplicateResourceError(AppException):
    """Duplicate resource error"""
    def __init__(self, resource: str, field: str, value: str):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(message, status.HTTP_409_CONFLICT)

class UnauthorizedActionError(AppException):
    """Unauthorized action error"""
    def __init__(self, action: str):
        message = f"You are not authorized to perform: {action}"
        super().__init__(message, status.HTTP_403_FORBIDDEN)

class InvalidStateTransitionError(BusinessLogicError):
    """Invalid state transition error"""
    def __init__(self, current_state: str, target_state: str):
        message = f"Cannot transition from '{current_state}' to '{target_state}'"
        super().__init__(message, {'current': current_state, 'target': target_state})

# Error Handlers

async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "errors": [exc.message],
            "details": exc.details,
            "error_code": exc.__class__.__name__
        }
    )

async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors"""
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    req_method = getattr(request, 'method', 'WEBSOCKET')
    
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"IntegrityError caught on {req_method} {request.url.path}: {error_msg}")
    print(f"[DC-INTEGRITY-ERR] {req_method} {request.url.path} | {error_msg}", flush=True)
    
    msg_lower = error_msg.lower()
    if 'unique' in msg_lower or 'duplicate' in msg_lower:
        message = "This record already exists. Please check for duplicate entries."
    elif 'foreign key' in msg_lower or 'fk_' in msg_lower:
        message = "Referenced record does not exist or cannot be modified due to active dependencies."
    elif 'not-null' in msg_lower or 'null value' in msg_lower:
        message = "Required database field cannot be empty."
    elif 'check constraint' in msg_lower:
        message = "Invalid value violates database field constraint."
    else:
        first_line = error_msg.splitlines()[0] if error_msg else "Constraint check failed."
        message = f"Database constraint violation: {first_line}"
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "message": message,
            "errors": [message],
            "error_code": "IntegrityError"
        }
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    req_method = getattr(request, 'method', 'WEBSOCKET')
    
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    error_trace = traceback.format_exc()
    logger.error(f"SQLAlchemy Error on {req_method} {request.url.path}: {error_msg}")
    logger.error(f"Full traceback: {error_trace}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Database operation failed. Please try again.",
            "errors": ["Database operation failed."],
            "error_code": "DatabaseError"
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    import logging
    logger = logging.getLogger(__name__)
    req_method = getattr(request, 'method', 'WEBSOCKET')
    
    errors = []
    for error in exc.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        error_msg = f"{field}: {error['msg']}"
        errors.append(error_msg)
        logger.error(f"Validation Error on {req_method} {request.url.path} - {error_msg}")
    
    detailed_message = "; ".join(errors)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed. Please check your input.",
            "detail": detailed_message,  # Add detail field for frontend
            "errors": errors,
            "error_code": "ValidationError"
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    import traceback
    req_method = getattr(request, 'method', 'WEBSOCKET')
    # DC-ERR-LOG-001: single-line log first (never truncated in deployment logs)
    print(f"[DC-500] {req_method} {request.url.path} | {type(exc).__name__}: {exc}", flush=True)
    traceback.print_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred. Please contact support.",
            "errors": ["Internal server error"],
            "error_code": "UnexpectedError"
        }
    )
