"""Material Project Score model.

Evaluation of a material for a specific Project.
This replaces the old MaterialChannelScore — scoring now happens
at the project level, not channel level.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class MaterialProjectScore(Base, TenantMixin, TimestampMixin):
    """AI evaluation of a material for a specific project."""

    __tablename__ = "material_project_scores"
    __table_args__ = (
        UniqueConstraint("material_id", "project_id", name="uq_material_project"),
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
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-10
    hype_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-10
    is_recommended: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    material = relationship("RawMaterial", backref="project_scores")
    project = relationship("Project", back_populates="project_scores")
