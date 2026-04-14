"""Auth service — registration, login, token management."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, verify_password, hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """Register a new user with a new tenant."""
        # Check if email already exists
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Check if tenant slug exists
        existing_tenant = await self.db.execute(
            select(Tenant).where(Tenant.slug == data.tenant_slug)
        )
        if existing_tenant.scalar_one_or_none():
            raise ValueError("Tenant slug already taken")

        # Create tenant
        tenant = Tenant(
            name=data.tenant_name,
            slug=data.tenant_slug,
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create user
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role="owner",
            tenant_id=tenant.id,
        )
        self.db.add(user)
        await self.db.flush()

        # Set tenant owner
        tenant.owner_id = user.id
        await self.db.commit()
        await self.db.refresh(user)

        return TokenResponse(
            access_token=create_access_token(str(user.id), str(tenant.id)),
            refresh_token=create_refresh_token(str(user.id), str(tenant.id)),
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens."""
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is disabled")

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        return TokenResponse(
            access_token=create_access_token(str(user.id), str(user.tenant_id)),
            refresh_token=create_refresh_token(str(user.id), str(user.tenant_id)),
        )

    async def get_current_user(self, user_id: str) -> UserResponse | None:
        """Get user by ID with tenant name."""
        result = await self.db.execute(
            select(User, Tenant.name.label("tenant_name"))
            .join(Tenant, User.tenant_id == Tenant.id)
            .where(User.id == uuid.UUID(user_id))
        )
        row = result.first()
        if not row:
            return None

        user = row[0]
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=row[1],
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )
