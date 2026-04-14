"""Health check endpoint — used by Docker and monitoring."""

from fastapi import APIRouter
from sqlalchemy import text

from app.database import AsyncSessionLocal

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check that the API and database are operational.

    Returns:
        Status of all critical components.
    """
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            db_ok = result.scalar() == 1
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "components": {
            "api": "ok",
            "database": "ok" if db_ok else "error",
        },
    }
