"""PromptConfig model — versioned AI prompt management.

Stores system and user prompt templates with version tracking
for reproducibility and A/B testing.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class PromptConfig(Base, TenantMixin, TimestampMixin):
    """Versioned prompt configuration for AI tasks."""

    __tablename__ = "prompt_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )

    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # classify | adapt_telegram | adapt_website | adapt_video | strategy

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)

    # Prompt templates
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Contains {placeholders}

    # AI parameters
    parameters: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )  # temperature, max_tokens, etc.

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # Performance tracking
    performance_stats: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )  # avg_engagement, accuracy, etc.
