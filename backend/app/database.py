"""Database engine and session management.

Provides async SQLAlchemy engine with connection pooling
and session factory for all database operations.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    pool_timeout=settings.postgres_pool_timeout,
    pool_recycle=1800,  # Reconnect every 30 minutes
    pool_pre_ping=True,  # Verify connection liveness
    echo=settings.app_debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session.

    Yields:
        AsyncSession: Database session with automatic cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
