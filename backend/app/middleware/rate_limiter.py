"""
Rate limiting middleware using slowapi.
Protects endpoints from abuse and DoS attacks.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import os


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URL", "memory://"),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
)

RATE_LIMITS = {
    "auth": "5/minute",      
    "upload": "10/minute",   
    "api": "60/minute",      
    "chat": "30/minute"      
}


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:


    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail),
            "retry_after": exc.detail.split("Retry after ")[1] if "Retry after" in exc.detail else None
        },
        headers={"Retry-After": str(60)}  
    )
