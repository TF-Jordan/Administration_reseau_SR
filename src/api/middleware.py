"""
Custom middleware for the API.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.context import (
    set_correlation_id,
    set_user_id,
    set_session_id,
    get_correlation_id,
    clear_all_context,
)

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses with timing.

    Logs both request start and completion with:
    - Method, path, query params
    - Client IP, user agent
    - Status code, duration
    - Correlation ID (automatically from context)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Extract additional request info
        user_agent = request.headers.get("User-Agent", "unknown")
        referer = request.headers.get("Referer")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000

        # Determine if slow request (>2s)
        is_slow = duration_seconds > 2.0

        # Log response with comprehensive info
        log_level = logging.WARNING if is_slow else logging.INFO
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration_ms:.0f}ms)",
            extra={
                "event": "request_completed",
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "duration_seconds": round(duration_seconds, 3),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": user_agent,
                "referer": referer,
                "is_slow_request": is_slow,
                "is_error": response.status_code >= 400,
                "is_server_error": response.status_code >= 500,
            },
        )

        # Add timing headers
        response.headers["X-Process-Time"] = f"{duration_seconds:.3f}"
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.0f}"

        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware for managing correlation IDs and request context.

    This middleware:
    - Extracts or generates correlation ID
    - Extracts user ID and session ID from headers
    - Sets all context variables for the request lifetime
    - Adds correlation ID to response headers
    - Cleans up context after request
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import uuid

        try:
            # Get or generate correlation ID
            correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

            # Set correlation ID in context (propagates to all logs automatically)
            set_correlation_id(correlation_id)

            # Add to request state for backwards compatibility
            request.state.correlation_id = correlation_id

            # Extract user context from headers if available
            user_id = request.headers.get("X-User-ID")
            if user_id:
                set_user_id(user_id)

            session_id = request.headers.get("X-Session-ID")
            if session_id:
                set_session_id(session_id)

            # Log request start with context
            logger.info(
                "Request started",
                extra={
                    "event": "request_start",
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        finally:
            # Clean up context after request
            clear_all_context()
