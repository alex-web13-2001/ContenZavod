"""Source schemas — CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str
    source_type: str = Field(..., pattern=r"^(rss|website|api|social)$")
    scraper_config: dict = Field(default_factory=dict)
    schedule: str | None = None
    is_active: bool = True


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    source_type: str | None = None
    scraper_config: dict | None = None
    schedule: str | None = None
    is_active: bool | None = None


class SourceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    url: str
    source_type: str
    scraper_config: dict
    schedule: str | None
    is_active: bool
    error_count: int
    last_scraped_at: datetime | None
    last_success_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
