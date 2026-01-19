"""
FastAPI dependencies for dependency injection.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.connection import get_async_session
from src.modules.module3_orchestration import Orchestrator
from src.modules.module3_orchestration.orchestrator import get_orchestrator

# Security
security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_async_session():
        yield session


def get_orchestrator_dep() -> Orchestrator:
    """Dependency for orchestrator."""
    return get_orchestrator()


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Verify JWT token for protected endpoints.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Token payload if valid

    Raises:
        HTTPException: If token is invalid
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(
    payload: Optional[dict] = Depends(verify_token),
) -> dict:
    """
    Dependency that requires authentication.

    Args:
        payload: Token payload from verify_token

    Returns:
        Token payload

    Raises:
        HTTPException: If not authenticated
    """
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def create_access_token(data: dict) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token

    Returns:
        Encoded JWT token
    """
    from datetime import datetime, timedelta

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
