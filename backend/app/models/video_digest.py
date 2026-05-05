"""Video Digest model — AI-avatar news digest videos.

Stores the script, ReVid API state, and the final video URL.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class VideoDigest(Base, TenantMixin, TimestampMixin):
    """A video digest — an AI-avatar reading a news summary."""

    __tablename__ = "video_digests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Content ──────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)

    # Source materials (list of material UUIDs)
    material_ids: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # ── ReVid state ──────────────────────────────────
    revid_pid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    revid_status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        nullable=False,
        index=True,
    )  # draft | script_generating | script_ready | rendering | ready | failed
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Config ───────────────────────────────────────
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # {avatar_url, voice_id, aspect_ratio, quality, ...}

    # ── Meta ─────────────────────────────────────────
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
