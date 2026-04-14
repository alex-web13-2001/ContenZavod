"""Channel schemas — CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str = Field(..., pattern=r"^(telegram|youtube|website)$")
    config: dict = Field(default_factory=dict)
    posting_rules: dict = Field(default_factory=dict)
    is_active: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = None
    channel_type: str | None = None
    config: dict | None = None
    posting_rules: dict | None = None
    is_active: bool | None = None


class ChannelResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    channel_type: str
    config: dict
    posting_rules: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
