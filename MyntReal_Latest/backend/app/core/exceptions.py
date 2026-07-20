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
    # Extract meaningful message from SQLAlchemy error
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    
    # DEBUG: Log full error for troubleshooting
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"IntegrityError caught: {error_msg}")
    logger.error(f"Full exception: {exc}")
    
    if 'unique constraint' in error_msg.lower() or 'duplicate' in error_msg.lower():
        message = "This record already exists. Please check for duplicates."
    elif 'foreign key' in error_msg.lower():
        message = "Referenced record does not exist or cannot be deleted due to dependencies."
    else:
        message = "Database constraint violation occurred."
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "message": message,
            "errors": [message],
            "error_code": "IntegrityError",
            "debug_error": error_msg  # Include actual error in response for debugging
        }
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    error_trace = traceback.format_exc()
    logger.error(f"SQLAlchemy Error: {error_msg}")
    logger.error(f"Full traceback: {error_trace}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Database operation failed. Please try again.",
            "errors": [error_msg],
            "error_code": "DatabaseError"
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    import logging
    logger = logging.getLogger(__name__)
    
    errors = []
    for error in exc.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        error_msg = f"{field}: {error['msg']}"
        errors.append(error_msg)
        logger.error(f"Validation Error on {request.method} {request.url.path} - {error_msg}")
    
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
    # DC-ERR-LOG-001: single-line log first (never truncated in deployment logs)
    print(f"[DC-500] {request.method} {request.url.path} | {type(exc).__name__}: {exc}", flush=True)
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
