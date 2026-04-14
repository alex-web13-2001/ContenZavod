"""Database engine and session management.

Provides:
- Async SQLAlchemy engine with connection pooling (for FastAPI)
- Sync SQLAlchemy engine (for Celery workers)
"""

from collections.abc import AsyncGenerator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# ── Async Engine (FastAPI) ────────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    pool_timeout=settings.postgres_pool_timeout,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.app_debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Sync Engine (Celery Workers) ─────────────────────────────

_sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

sync_engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=3,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
)


@contextmanager
def get_sync_session():
    """Context manager providing a sync database session for Celery tasks."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

