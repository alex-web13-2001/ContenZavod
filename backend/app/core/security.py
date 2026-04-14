"""Security utilities — JWT creation, password hashing."""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        user_id: User UUID.
        tenant_id: Tenant UUID.
        role: User role (owner, admin, editor, viewer).
        expires_delta: Optional custom expiration.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: User UUID.
        tenant_id: Tenant UUID.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
