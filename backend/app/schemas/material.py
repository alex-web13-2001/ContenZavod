"""Material schemas — listing and detail views."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, computed_field, model_validator


class AIClassification(BaseModel):
    """Structured AI classification result."""
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] = []
    summary_ru: str | None = None
    summary_en: str | None = None
    relevance_score: int | None = None
    sentiment: str | None = None
    is_breaking: bool = False


class MaterialListResponse(BaseModel):
    id: UUID
    source_id: UUID | None
    original_url: str
    title: str
    status: str
    word_count: int | None
    scraped_at: datetime
    created_at: datetime

    # AI classification fields — extracted from metadata
    category: str | None = None
    tags: list[str] = []
    summary_ru: str | None = None
    relevance_score: int | None = None
    sentiment: str | None = None
    is_breaking: bool = False
    classified_by: str | None = None
    
    # Channel specific scores (if requested)
    channel_relevance_score: int | None = None
    channel_hype_score: int | None = None
    is_recommended_for_channel: bool | None = None
    channel_explanation: str | None = None

    # Project specific scores (if requested)
    project_relevance_score: int | None = None
    project_hype_score: int | None = None
    is_recommended: bool | None = None
    project_explanation: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_ai_fields(cls, data: Any) -> Any:
        """Pull AI classification from metadata JSONB into flat fields."""
        if hasattr(data, "__dict__"):
            # SQLAlchemy model → dict
            meta = getattr(data, "metadata_", None) or {}
            ai = meta.get("ai_classification", {}) if isinstance(meta, dict) else {}
            d = {
                "id": data.id,
                "source_id": data.source_id,
                "original_url": data.original_url,
                "title": data.title,
                "status": data.status,
                "word_count": data.word_count,
                "scraped_at": data.scraped_at,
                "created_at": data.created_at,
                "category": ai.get("category"),
                "tags": ai.get("tags", []),
                "summary_ru": ai.get("summary_ru"),
                "relevance_score": ai.get("relevance_score"),
                "sentiment": ai.get("sentiment"),
                "is_breaking": ai.get("is_breaking", False),
                "classified_by": meta.get("classified_by") if isinstance(meta, dict) else None,
                # Channel-level scores
                "channel_relevance_score": getattr(data, "channel_relevance_score", None),
                "channel_hype_score": getattr(data, "channel_hype_score", None),
                "is_recommended_for_channel": getattr(data, "is_recommended_for_channel", None),
                "channel_explanation": getattr(data, "channel_explanation", None),
                # Project-level scores
                "project_relevance_score": getattr(data, "project_relevance_score", None),
                "project_hype_score": getattr(data, "project_hype_score", None),
                "is_recommended": getattr(data, "is_recommended", None),
                "project_explanation": getattr(data, "project_explanation", None),
            }
            return d
        return data


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

    # AI classification — full detail
    ai_classification: AIClassification | None = None
    classified_at: str | None = None
    classified_by: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_ai_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            meta = getattr(data, "metadata_", None) or {}
            ai_raw = meta.get("ai_classification", {}) if isinstance(meta, dict) else {}
            d = {
                "id": data.id,
                "tenant_id": data.tenant_id,
                "source_id": data.source_id,
                "original_url": data.original_url,
                "title": data.title,
                "content_text": data.content_text,
                "status": data.status,
                "word_count": data.word_count,
                "published_at": data.published_at,
                "scraped_at": data.scraped_at,
                "created_at": data.created_at,
                "ai_classification": ai_raw if ai_raw else None,
                "classified_at": meta.get("classified_at") if isinstance(meta, dict) else None,
                "classified_by": meta.get("classified_by") if isinstance(meta, dict) else None,
            }
            return d
        return data


class MaterialStatusUpdate(BaseModel):
    status: str
