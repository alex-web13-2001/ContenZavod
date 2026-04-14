"""Channel model — publishing destinations.

Represents a Telegram channel, YouTube account, or website
where adapted content gets published.
"""

import uuid

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Channel(Base, TenantMixin, TimestampMixin):
    """Publishing channel (Telegram, YouTube, Website)."""

    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # telegram | youtube | website

    # Encrypted configuration: bot_token, channel_id, OAuth tokens, etc.
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Posting rules: schedule windows, max posts per day, etc.
    posting_rules: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
