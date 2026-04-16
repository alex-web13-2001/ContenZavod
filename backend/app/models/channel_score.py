"""Material Channel Score model.

Represents the evaluation of a material for a specific channel,
generating hype and relevance scores based on editorial guidelines.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class MaterialChannelScore(Base, TenantMixin, TimestampMixin):
    """AI evaluation of a material for a specific channel."""

    __tablename__ = "material_channel_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    hype_score: Mapped[int] = mapped_column(Integer, nullable=False)
    is_recommended: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    material = relationship("RawMaterial", backref="channel_scores")
    channel = relationship("Channel", backref="material_scores")
