"""RawMaterial model — scraped content before AI processing.

Materials flow through a state machine:
new → classifying → classified → adapting → adapted → published
                                                    → rejected
                                                    → archived
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class RawMaterial(Base, TenantMixin, TimestampMixin):
    """Raw material scraped from a source, before AI processing."""

    __tablename__ = "raw_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )

    # Content
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)  # Plain text
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)  # Original HTML

    # Metadata: author, publication date, tags, language, etc.
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )

    # Deduplication hash (SHA-256 of content_text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # State machine status
    status: Mapped[str] = mapped_column(
        String(50), server_default="new", nullable=False, index=True
    )

    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # When the original content was published (at the source)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("idx_materials_tenant_status", "tenant_id", "status"),
        Index("idx_materials_tenant_created", "tenant_id", "created_at"),
    )
