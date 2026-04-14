"""Source model — content ingestion endpoints.

Each source defines a website, RSS feed, or API to scrape for raw materials.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Source(Base, TenantMixin, TimestampMixin):
    """Source — content ingestion endpoint to scrape."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # rss | website | api | social

    # Scraper configuration: selectors, auth details, proxy, headers
    scraper_config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Cron schedule expression (e.g., "0 */2 * * *" = every 2 hours)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
