"""Project model — thematic content projects.

A Project groups channels around a specific topic and audience.
It defines WHAT content is relevant (topic_guidelines + target_audience).
Channels within a project define HOW and WHERE to publish.
"""

import uuid

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Project(Base, TenantMixin, TimestampMixin):
    """A thematic content project (e.g., CyprusNews, TechPulse)."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, server_default="", nullable=False)

    # Topic filter for AI — what's relevant for this project
    topic_guidelines: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )

    # Target audience — who we write for
    target_audience: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )

    # Relationships
    channels = relationship("Channel", back_populates="project", cascade="all, delete-orphan")
    project_scores = relationship("MaterialProjectScore", back_populates="project", cascade="all, delete-orphan")
