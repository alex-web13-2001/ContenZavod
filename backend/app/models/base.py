"""Base model with common fields and TenantMixin.

All models inherit from Base. Tenant-scoped models also use TenantMixin
to automatically include tenant_id foreign key and indexing.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=datetime.utcnow,
        nullable=False,
    )


class TenantMixin:
    """Mixin that adds tenant_id for multi-tenant isolation.

    All tenant-scoped tables must include this mixin.
    PostgreSQL RLS policies use this column for row filtering.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
