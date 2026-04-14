"""MediaAsset model — generated images and videos.

Stores metadata for AI-generated media (images, videos, thumbnails)
linked to adapted content pieces.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class MediaAsset(Base, TenantMixin, TimestampMixin):
    """AI-generated media asset (image, video, thumbnail)."""

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapted_contents.id", ondelete="CASCADE"),
        nullable=False,
    )

    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # image | video | thumbnail

    # Which AI provider generated this
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_job_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # For async generation jobs

    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation status
    status: Mapped[str] = mapped_column(
        String(50), server_default="pending", nullable=False
    )  # pending | generating | ready | failed

    # Storage
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Dimensions
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # For video

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
