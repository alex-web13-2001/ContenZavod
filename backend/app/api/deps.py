"""API dependencies — shared across all routes.

Provides database sessions, authentication, and tenant context.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

settings = get_settings()
security = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Extract and validate user from JWT token.

    Returns:
        Dict with user_id, tenant_id, role.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role", "viewer")

        if user_id is None or tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user or tenant",
            )

        return {"user_id": user_id, "tenant_id": tenant_id, "role": role}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_tenant_db(
    user: Annotated[dict, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncSession:
    """Get a database session with tenant context set via RLS.

    This middleware sets the PostgreSQL session variable used by
    Row Level Security policies to filter data by tenant.

    Returns:
        AsyncSession with tenant context configured.
    """
    tenant_id = user["tenant_id"]

    # Set RLS context for this session
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )

    return db


# Type aliases for clean dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user_id)]
TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]
