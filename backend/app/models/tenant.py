"""Tenant model — unit of data isolation.

Each tenant represents a project/business with its own sources,
channels, content, and AI configuration.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Tenant(Base, TimestampMixin):
    """Tenant — project/business unit for data isolation."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True  # Set after first user is created
    )
    plan: Mapped[str] = mapped_column(String(50), server_default="free", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provider preferences per AI capability
    ai_config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # General project settings
    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
