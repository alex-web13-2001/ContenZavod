"""PublishJob model — publication task with idempotency.

Tracks every publishing attempt with status, retries, and
a unique idempotency_key to prevent duplicate publications.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class PublishJob(Base, TenantMixin, TimestampMixin):
    """Job to publish adapted content to a channel."""

    __tablename__ = "publish_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapted_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), server_default="scheduled", nullable=False
    )  # scheduled | queued | publishing | published | failed | cancelled

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Platform response
    platform_post_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # msg_id, video_id, post_slug
    platform_response: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Retries
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Idempotency key prevents duplicate publishing on retry
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    __table_args__ = (
        Index("idx_publish_jobs_tenant_status", "tenant_id", "status"),
        Index(
            "idx_publish_jobs_scheduled",
            "scheduled_at",
            postgresql_where="status = 'scheduled'",
        ),
    )
