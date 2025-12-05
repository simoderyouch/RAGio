import time
import uuid
from typing import Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from app.utils.logger import log_error, log_info
import traceback

# Lazy FastAPI imports - only needed for middleware (backend), not for exception classes (Celery)
try:
    from fastapi import Request, Response, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    FASTAPI_AVAILABLE = True
except ImportError:
    # In lightweight Celery images, FastAPI is not available
    # Create a base exception class that doesn't depend on FastAPI
    FASTAPI_AVAILABLE = False
    HTTPException = Exception  # Fallback base class
    Request = None
    Response = None
    JSONResponse = None
    RequestValidationError = None
    StarletteHTTPException = None

class CustomHTTPException(HTTPException):
    """Custom HTTP exception with additional context"""
    def __init__(self, status_code: int, detail: str, error_code: str = None, context: Dict[str, Any] = None):
        if FASTAPI_AVAILABLE:
            # FastAPI HTTPException expects status_code and detail
            super().__init__(status_code=status_code, detail=detail)
        else:
            # In lightweight images, just use Exception base class
            super().__init__(detail)
            self.status_code = status_code
        self.error_code = error_code
        self.context = context or {}

class DatabaseException(CustomHTTPException):
    """Database-related exceptions"""
    def __init__(self, detail: str, context: Dict[str, Any] = None):
        super().__init__(status_code=500, detail=detail, error_code="DB_ERROR", context=context)

class FileProcessingException(CustomHTTPException):
    """File processing exceptions"""
    def __init__(self, detail: str, context: Dict[str, Any] = None):
        super().__init__(status_code=422, detail=detail, error_code="FILE_PROCESSING_ERROR", context=context)

class AuthenticationException(CustomHTTPException):
    """Authentication exceptions"""
    def __init__(self, detail: str, context: Dict[str, Any] = None):
        super().__init__(status_code=401, detail=detail, error_code="AUTH_ERROR", context=context)

class ValidationException(CustomHTTPException):
    """Validation exceptions"""
    def __init__(self, detail: str, context: Dict[str, Any] = None):
        super().__init__(status_code=400, detail=detail, error_code="VALIDATION_ERROR", context=context)

def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    error_response = {
        "success": False,
        "error": {
            "code": error_code or "UNKNOWN_ERROR",
            "message": message,
            "status_code": status_code
        },
        "timestamp": time.time(),
        "request_id": request_id
    }
    
    if details:
        error_response["error"]["details"] = details
        
    return error_response

async def error_handler_middleware(request: Request, call_next):
    """Global error handling middleware"""
    # Only available when FastAPI is installed (backend only)
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("error_handler_middleware requires FastAPI (only available in backend)")
    
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        
        # Log successful requests
        duration = time.time() - start_time
        log_info(
            f"Request completed successfully",
            context="middleware",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            duration=duration
        )
        
        return response
        
    except CustomHTTPException as e:
        # Handle custom exceptions
        error_response = create_error_response(
            status_code=e.status_code,
            message=e.detail,
            error_code=e.error_code,
            details=e.context,
            request_id=request_id
        )
        
        log_error(
            e,
            context="custom_exception",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path),
            error_code=e.error_code,
            **e.context
        )
        
        return JSONResponse(status_code=e.status_code, content=error_response)
        
    except RequestValidationError as e:
        # Handle validation errors
        error_response = create_error_response(
            status_code=422,
            message="Validation error",
            error_code="VALIDATION_ERROR",
            details={"validation_errors": e.errors()},
            request_id=request_id
        )
        
        log_error(
            e,
            context="validation_error",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path)
        )
        
        return JSONResponse(status_code=422, content=error_response)
        
    except SQLAlchemyError as e:
        # Handle database errors
        error_response = create_error_response(
            status_code=500,
            message="Database error occurred",
            error_code="DATABASE_ERROR",
            request_id=request_id
        )
        
        log_error(
            e,
            context="database_error",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path)
        )
        
        return JSONResponse(status_code=500, content=error_response)
        
    except StarletteHTTPException as e:
        # Handle HTTP exceptions
        error_response = create_error_response(
            status_code=e.status_code,
            message=str(e.detail),
            error_code="HTTP_ERROR",
            request_id=request_id
        )
        
        log_error(
            e,
            context="http_exception",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path)
        )
        
        return JSONResponse(status_code=e.status_code, content=error_response)
        
    except Exception as e:
        # Handle unexpected errors
        error_response = create_error_response(
            status_code=500,
            message="Internal server error",
            error_code="INTERNAL_ERROR",
            request_id=request_id
        )
        
        log_error(
            e,
            context="unexpected_error",
            request_id=request_id,
            method=request.method,
            endpoint=str(request.url.path),
            traceback=traceback.format_exc()
        )
        
        return JSONResponse(status_code=500, content=error_response)

def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    # Only available when FastAPI is installed (backend only)
    if not FASTAPI_AVAILABLE:
        return 'unknown'
    return getattr(request.state, 'request_id', 'unknown')
