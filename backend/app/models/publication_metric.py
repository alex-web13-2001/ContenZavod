"""PublicationMetric model — analytics data points.

Stores periodic snapshots of engagement metrics for published content
(views, likes, comments, CTR, watch time, etc.).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class PublicationMetric(Base, TenantMixin):
    """Engagement metric snapshot for a published piece of content."""

    __tablename__ = "publication_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    publish_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publish_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # views | likes | comments | shares | ctr | watch_time_avg | forwards

    value: Mapped[float] = mapped_column(Numeric, nullable=False)

    # At which interval this snapshot was taken
    snapshot_period: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 1h | 6h | 24h | 48h | 7d | 30d

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_metrics_pub_period", "publish_job_id", "snapshot_period"),
        Index("idx_metrics_tenant_collected", "tenant_id", "collected_at"),
    )
