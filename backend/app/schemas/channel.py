"""Channel schemas — CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    project_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: str = Field(..., pattern=r"^(telegram|youtube|website)$")
    content_format: str = Field(default="short_post", pattern=r"^(short_post|longread|video_script|digest)$")
    tone_of_voice: str = ""
    languages: list[str] = Field(default_factory=lambda: ["ru"])
    config: dict = Field(default_factory=dict)
    posting_rules: dict = Field(default_factory=dict)
    editorial_rules: str = ""
    is_active: bool = True


class ChannelUpdate(BaseModel):
    project_id: UUID | None = None
    name: str | None = None
    channel_type: str | None = None
    content_format: str | None = None
    tone_of_voice: str | None = None
    languages: list[str] | None = None
    config: dict | None = None
    posting_rules: dict | None = None
    editorial_rules: str | None = None
    is_active: bool | None = None


class ChannelResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID | None = None
    name: str
    channel_type: str
    content_format: str
    tone_of_voice: str
    languages: list[str]
    config: dict
    posting_rules: dict
    editorial_rules: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
