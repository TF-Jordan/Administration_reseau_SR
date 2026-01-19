"""
Database connection and session management.
Supports both async and sync operations.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.engine import Engine

from src.config import settings
from src.utils.context import get_correlation_id

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 0.1  # 100ms

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create sync engine for Celery tasks
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


# ============================================================
# DATABASE QUERY LOGGING
# ============================================================

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    SQLAlchemy event listener - called before query execution.
    Records start time for query timing.
    """
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    SQLAlchemy event listener - called after query execution.
    Logs query with duration and detects slow queries.
    """
    # Calculate query duration
    query_start_times = conn.info.get('query_start_time', [])
    if not query_start_times:
        return

    start_time = query_start_times.pop()
    duration_seconds = time.time() - start_time
    duration_ms = duration_seconds * 1000

    # Extract query type (SELECT, INSERT, UPDATE, DELETE)
    query_type = statement.strip().split()[0].upper() if statement else "UNKNOWN"

    # Truncate long queries for logging
    query_preview = statement[:200] + "..." if len(statement) > 200 else statement

    # Determine if this is a slow query
    is_slow = duration_seconds > SLOW_QUERY_THRESHOLD

    # Log with appropriate level
    log_level = logging.WARNING if is_slow else logging.DEBUG

    logger.log(
        log_level,
        f"Query executed: {query_type} ({duration_ms:.2f}ms)",
        extra={
            "event": "database_query",
            "metric_type": "database_query",
            "query_type": query_type,
            "query_preview": query_preview,
            "duration_ms": round(duration_ms, 2),
            "duration_seconds": round(duration_seconds, 3),
            "is_slow_query": is_slow,
            "executemany": executemany,
            "correlation_id": get_correlation_id(),
        },
    )


@event.listens_for(Engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """
    SQLAlchemy event listener - called on new connection.
    Logs database connection events.
    """
    logger.debug(
        "Database connection established",
        extra={
            "event": "database_connect",
            "correlation_id": get_correlation_id(),
        },
    )


@event.listens_for(Engine, "close")
def on_close(dbapi_conn, connection_record):
    """
    SQLAlchemy event listener - called on connection close.
    Logs database connection close events.
    """
    logger.debug(
        "Database connection closed",
        extra={
            "event": "database_close",
            "correlation_id": get_correlation_id(),
        },
    )


def log_pool_status(engine):
    """
    Log current database connection pool status.

    Args:
        engine: SQLAlchemy engine instance
    """
    pool = engine.pool
    logger.info(
        "Database pool status",
        extra={
            "event": "database_pool_status",
            "metric_type": "database_pool",
            "pool_size": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow": pool.overflow(),
            "pool_timeout": pool._timeout,
            "correlation_id": get_correlation_id(),
        },
    )


# ============================================================
# SESSION MANAGEMENT
# ============================================================

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get sync database session for Celery tasks."""
    session = SyncSessionLocal()
    try:
        return session
    except Exception:
        session.rollback()
        raise


@asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close database connections."""
    await async_engine.dispose()
