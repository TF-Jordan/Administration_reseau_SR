"""
Context management utilities.

Provides context variables for request tracing and correlation across
async operations, Celery tasks, and external services.
"""

import logging
from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Context variable for correlation ID
# This allows correlation ID to be propagated across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    'correlation_id',
    default=None
)

# Context variable for user ID (optional)
user_id_var: ContextVar[Optional[str]] = ContextVar(
    'user_id',
    default=None
)

# Context variable for session ID (optional)
session_id_var: ContextVar[Optional[str]] = ContextVar(
    'session_id',
    default=None
)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID in context.

    Args:
        correlation_id: Correlation ID to set
    """
    if not correlation_id:
        logger.warning("Attempted to set empty correlation_id")
        return

    correlation_id_var.set(correlation_id)
    logger.debug(f"Correlation ID set: {correlation_id}")


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID and set it in context.

    Returns:
        Generated correlation ID (UUID4)
    """
    correlation_id = str(uuid4())
    set_correlation_id(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear the correlation ID from context."""
    correlation_id_var.set(None)


def get_user_id() -> Optional[str]:
    """
    Get the current user ID from context.

    Returns:
        Current user ID or None if not set
    """
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    """
    Set the user ID in context.

    Args:
        user_id: User ID to set
    """
    user_id_var.set(user_id)


def clear_user_id() -> None:
    """Clear the user ID from context."""
    user_id_var.set(None)


def get_session_id() -> Optional[str]:
    """
    Get the current session ID from context.

    Returns:
        Current session ID or None if not set
    """
    return session_id_var.get()


def set_session_id(session_id: str) -> None:
    """
    Set the session ID in context.

    Args:
        session_id: Session ID to set
    """
    session_id_var.set(session_id)


def clear_session_id() -> None:
    """Clear the session ID from context."""
    session_id_var.set(None)


def clear_all_context() -> None:
    """Clear all context variables."""
    clear_correlation_id()
    clear_user_id()
    clear_session_id()


def get_request_context() -> dict:
    """
    Get all request context as a dictionary.

    Returns:
        Dictionary with all context variables
    """
    return {
        "correlation_id": get_correlation_id(),
        "user_id": get_user_id(),
        "session_id": get_session_id(),
    }
