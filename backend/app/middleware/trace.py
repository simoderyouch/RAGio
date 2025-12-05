"""
Trace ID middleware for request correlation.
Generates trace_id and span_id for request tracking.
"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class TraceMiddleware(BaseHTTPMiddleware):
    """Middleware to generate trace_id and span_id for each request."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate trace_id at request start
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        
        # Continue with request
        response = await call_next(request)
        
        # Add trace headers to response
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id
        
        return response


def get_trace_id(request: Request) -> str:
    """Get trace_id from request state."""
    return getattr(request.state, "trace_id", str(uuid.uuid4()))


def get_span_id(request: Request) -> str:
    """Get span_id from request state."""
    return getattr(request.state, "span_id", str(uuid.uuid4()))

