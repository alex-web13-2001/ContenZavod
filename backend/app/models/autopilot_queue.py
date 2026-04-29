"""AutopilotQueueItem model — smart publication queue.

Tracks materials ranked and scheduled by the autopilot for automatic
publishing. Each item represents a single adaptation queued for one channel.

Lifecycle: queued → publishing → published | skipped | expired
Shadow mode: shadow → approved → publishing → published | rejected
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class AutopilotQueueItem(Base, TenantMixin, TimestampMixin):
    """Item in the autopilot publication queue."""

    __tablename__ = "autopilot_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adaptation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_adaptations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Multi-signal scores
    final_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    freshness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), server_default="0", nullable=False
    )
    uniqueness_score: Mapped[float] = mapped_column(
        Numeric(5, 2), server_default="10", nullable=False
    )
    engagement_predict: Mapped[float] = mapped_column(
        Numeric(5, 2), server_default="5", nullable=False
    )

    # Strategy: express | smart_queue
    strategy: Mapped[str] = mapped_column(
        String(20), server_default="smart_queue", nullable=False
    )

    # When this item should be published
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lifecycle status
    # queued     — waiting for publication slot
    # shadow     — shadow mode, shown in UI for approval
    # approved   — user approved in shadow mode
    # publishing — publish task dispatched
    # published  — done
    # skipped    — failed anti-spam / dedup check at publish time
    # expired    — TTL exceeded before publication
    status: Mapped[str] = mapped_column(
        String(20), server_default="queued", nullable=False
    )

    # Why this item was skipped (if status = skipped/expired)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Reference to the PublishJob created when this item is published
    publish_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publish_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    channel = relationship("Channel")
    adaptation = relationship("ChannelAdaptation")
    project = relationship("Project")

    __table_args__ = (
        Index("idx_autopilot_tenant_status", "tenant_id", "status"),
        Index(
            "idx_autopilot_scheduled",
            "scheduled_at",
            postgresql_where="status IN ('queued', 'approved')",
        ),
        Index("idx_autopilot_channel_status", "channel_id", "status"),
        # Prevent duplicate active queue items for the same adaptation+channel
        Index(
            "uq_autopilot_active_adaptation",
            "adaptation_id", "channel_id",
            unique=True,
            postgresql_where="status IN ('queued', 'shadow', 'approved', 'publishing')",
        ),
    )
