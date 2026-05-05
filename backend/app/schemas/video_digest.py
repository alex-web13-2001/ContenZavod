"""Pydantic schemas for the Video Digest feature."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────

class DigestCreate(BaseModel):
    """Create a new video digest."""
    title: str = Field(..., min_length=1, max_length=500)
    project_id: uuid.UUID
    material_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=10)
    language: str = "ru"


class DigestScriptUpdate(BaseModel):
    """Manually update/edit the script."""
    script_text: str = Field(..., min_length=10)


class ProvidedMediaItem(BaseModel):
    """A user-provided media item for ReVid scene matching."""
    url: str
    title: str = ""
    type: str = "image"  # "image" or "video"


class DigestGenerateRequest(BaseModel):
    """Request to generate video from the script.
    
    render_config contains all ReVid settings from the frontend:
    avatarUrl, voiceId, voiceSpeed, voiceLanguage, mediaType, mediaDensity,
    mediaImageModel, videoModel, bRollType, placeAvatarInContext,
    avatarImageModel, removeBackground, captionsEnabled, captionsPreset,
    captionsPosition, musicEnabled, aspectRatio, disableAudio,
    providedMedia[{url, title, type}]
    """
    render_config: dict | None = None  # Full settings from frontend
    # Legacy fields (backward compat)
    avatar_url: str | None = None
    voice_id: str | None = None
    aspect_ratio: str | None = None
    quality: str | None = None


# ── Response Schemas ─────────────────────────────────

class DigestResponse(BaseModel):
    """Full digest detail."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    script_text: str | None = None
    language: str
    material_ids: list[uuid.UUID]
    revid_pid: str | None = None
    revid_status: str
    video_url: str | None = None
    thumbnail_url: str | None = None
    config: dict = {}
    duration_seconds: int | None = None
    credits_used: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DigestListItem(BaseModel):
    """Compact digest for list views."""
    id: uuid.UUID
    title: str
    language: str
    revid_status: str
    video_url: str | None = None
    duration_seconds: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DigestListResponse(BaseModel):
    """Paginated list of digests."""
    items: list[DigestListItem]
    total: int


class DigestStatusResponse(BaseModel):
    """Real-time status for polling."""
    id: uuid.UUID
    revid_status: str
    revid_pid: str | None = None
    video_url: str | None = None
    error_message: str | None = None
    progress: int | None = None
