"""Channel model — publishing destinations within a project.

Represents a Telegram channel, YouTube account, or website
where adapted content gets published. Belongs to a Project.

A channel has a single tone_of_voice but can serve multiple languages.
Each language maps to a platform-specific endpoint in the config JSON.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Channel(Base, TenantMixin, TimestampMixin):
    """Publishing channel (Telegram, YouTube, Website) within a project."""

    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Parent project
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,  # nullable for migration — existing channels won't have a project yet
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Platform type
    channel_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # telegram | youtube | website

    # Content formats: which article types this channel publishes (JSON array)
    content_formats: Mapped[list] = mapped_column(
        JSONB, server_default='["short_post"]', nullable=False
    )  # ["short_post", "longread", "video_script", "digest"]

    # Tone of voice: writing style instructions for AI
    tone_of_voice: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )

    # Languages this channel serves (JSON array: ["ru", "en"])
    languages: Mapped[list] = mapped_column(
        JSONB, server_default='["ru"]', nullable=False
    )

    # Platform config: bot_token, chat_ids per language, CMS credentials, etc.
    # Structure: {bot_token: "...", endpoints: {ru: {chat_id: "..."}, en: {chat_id: "..."}}}
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Posting rules: schedule windows, max posts per day, etc.
    posting_rules: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Editorial rules for content (technical constraints, forbidden topics, etc.)
    editorial_rules: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )

    # Formatting rules — strict text formatting instructions for AI
    # (paragraph structure, bold/emoji usage, line breaks, etc.)
    formatting_rules: Mapped[str] = mapped_column(
        Text, server_default="", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # Relationships
    project = relationship("Project", back_populates="channels")
