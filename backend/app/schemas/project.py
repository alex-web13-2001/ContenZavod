"""Project schemas — CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    topic_guidelines: str = ""
    target_audience: str = ""
    is_active: bool = True


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    topic_guidelines: str | None = None
    target_audience: str | None = None
    is_active: bool | None = None


class ProjectResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str
    topic_guidelines: str
    target_audience: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(ProjectResponse):
    """Extended response with channel count for list views."""
    channel_count: int = 0
    recommendation_count: int = 0
