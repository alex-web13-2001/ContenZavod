"""Channel Adaptation model.

Stores AI-generated content adapted for a specific channel × language pair.
Each adaptation contains a headline and body in the channel's format/tone,
translated to the target language.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class ChannelAdaptation(Base, TenantMixin, TimestampMixin):
    """AI-generated content draft for a channel × language pair."""

    __tablename__ = "channel_adaptations"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "channel_id", "language",
            name="uq_material_channel_lang",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # ru, en, el, etc.

    # AI-generated content
    headline: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, server_default="", nullable=False)

    # urgency: urgent = post ASAP, normal = regular schedule, filler = low priority
    priority: Mapped[str] = mapped_column(
        String(20), server_default="normal", nullable=False
    )

    # Workflow status: draft → approved → published → rejected
    status: Mapped[str] = mapped_column(
        String(20), server_default="draft", nullable=False
    )

    # Relationships
    material = relationship("RawMaterial", backref="channel_adaptations")
    channel = relationship("Channel", backref="adaptations")
