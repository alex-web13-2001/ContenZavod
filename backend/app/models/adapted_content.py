"""AdaptedContent model — content transformed for a specific channel.

Created by AI adapter from raw material, ready for review and publishing.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AdaptedContent(Base, TenantMixin, TimestampMixin):
    """Content adapted for a specific publishing channel."""

    __tablename__ = "adapted_contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False
    )
    ai_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_results.id", ondelete="SET NULL"), nullable=True
    )

    # Target channel type
    target_channel_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # telegram | website | youtube | shorts

    # Adapted content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Extra data: hashtags, CTA, SEO keywords, video script, etc.
    extra: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Review workflow
    status: Mapped[str] = mapped_column(
        String(50), server_default="draft", nullable=False
    )  # draft | review | approved | rejected | published

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
