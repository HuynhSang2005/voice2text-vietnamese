"""
Database connection and session management for the Infrastructure layer.

This module provides:
- Async SQLAlchemy engine with connection pooling
- Session factory for creating database sessions
- Connection configuration optimized for async operations
- Health check utilities
"""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, text

from app.core.config import settings

logger = logging.getLogger(__name__)


# Global engine instance (created on startup)
_engine: AsyncEngine | None = None


def create_engine() -> AsyncEngine:
    """
    Create async database engine with optimized connection pooling.

    Configuration:
        - pool_size=20: Max connections in pool
        - max_overflow=10: Additional connections beyond pool_size
        - pool_pre_ping=True: Health check before using connection
        - echo=DATABASE_ECHO: Log SQL statements (dev mode)

    Returns:
        AsyncEngine: Configured SQLAlchemy async engine
    """
    connect_args = {"check_same_thread": False}  # Required for SQLite

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        connect_args=connect_args,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connection health before use
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    logger.info(
        f"Database engine created: {settings.DATABASE_URL.split('/')[-1]} "
        f"(pool_size=20, max_overflow=10)"
    )

    return engine


def get_engine() -> AsyncEngine:
    """
    Get the global engine instance.

    Raises:
        RuntimeError: If engine not initialized (call init_engine first)

    Returns:
        AsyncEngine: The global engine instance
    """
    global _engine
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


def init_engine() -> AsyncEngine:
    """
    Initialize the global engine instance.

    This should be called once during application startup.

    Returns:
        AsyncEngine: The initialized engine
    """
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


async def close_engine() -> None:
    """
    Close the global engine and dispose of connection pool.

    This should be called during application shutdown.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine closed")


async def create_db_and_tables() -> None:
    """
    Create database tables and configure SQLite settings.

    This function:
    1. Creates all tables defined in SQLModel.metadata
    2. Enables WAL mode for better concurrent writes
    3. Sets synchronous mode to NORMAL for performance

    Note: Import models before calling this to register them.
    """
    # Import models to ensure they are registered
    from app.infrastructure.database.models import TranscriptionModel, SessionModel

    engine = get_engine()

    logger.info(f"Creating tables: {list(SQLModel.metadata.tables.keys())}")

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

        # Optimize SQLite for async operations
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.execute(text("PRAGMA busy_timeout=5000;"))  # 5s timeout

    logger.info("Database initialized successfully")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides a database session.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(select(TranscriptionModel))

    Yields:
        AsyncSession: Database session with auto-commit disabled

    Note: Session is automatically closed after exiting context.
    """
    engine = get_engine()

    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for injecting database sessions.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(TranscriptionModel))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session


async def health_check() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
