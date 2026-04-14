"""Material schemas — listing and detail views."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MaterialResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    source_id: UUID | None
    original_url: str
    title: str
    content_text: str
    status: str
    word_count: int | None
    published_at: datetime | None
    scraped_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    id: UUID
    source_id: UUID | None
    original_url: str
    title: str
    status: str
    word_count: int | None
    scraped_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialStatusUpdate(BaseModel):
    status: str
