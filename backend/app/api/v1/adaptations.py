"""Channel Adaptations API — view and manage AI-generated content drafts.

Endpoints:
    GET  /adaptations?channel_id=&project_id=&status=draft  — list adaptations
    PATCH /adaptations/{id}                                 — approve/reject/edit
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.models.channel import Channel
from app.models.channel_adaptation import ChannelAdaptation
from app.models.material import RawMaterial

router = APIRouter(prefix="/adaptations", tags=["adaptations"])


# --- Schemas ---

class AdaptationResponse(BaseModel):
    id: str
    material_id: str
    channel_id: str
    language: str
    content_format: str
    headline: str
    body: str
    priority: str
    status: str
    created_at: str
    material_title: str | None = None
    material_url: str | None = None
    channel_name: str | None = None
    channel_type: str | None = None

    model_config = {"from_attributes": True}


class AdaptationUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(draft|approved|published|rejected)$")
    headline: str | None = None
    body: str | None = None


# --- Endpoints ---

@router.get("")
async def list_adaptations(
    channel_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    adaptation_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """List adaptations with optional filters."""
    tid = uuid.UUID(tenant_id)

    query = (
        select(ChannelAdaptation)
        .where(ChannelAdaptation.tenant_id == tid)
        .order_by(ChannelAdaptation.created_at.desc())
    )

    if channel_id:
        query = query.where(ChannelAdaptation.channel_id == channel_id)

    if project_id:
        query = query.join(Channel, ChannelAdaptation.channel_id == Channel.id).where(
            Channel.project_id == project_id
        )

    if adaptation_status:
        query = query.where(ChannelAdaptation.status == adaptation_status)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    adaptations = result.scalars().all()

    # Enrich with material and channel data
    items = []
    for a in adaptations:
        material = await db.get(RawMaterial, a.material_id)
        channel = await db.get(Channel, a.channel_id)

        items.append({
            "id": str(a.id),
            "material_id": str(a.material_id),
            "channel_id": str(a.channel_id),
            "language": a.language,
            "content_format": a.content_format,
            "headline": a.headline,
            "body": a.body,
            "priority": a.priority,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "material_title": material.title if material else None,
            "material_url": material.original_url if material else None,
            "channel_name": channel.name if channel else None,
            "channel_type": channel.channel_type if channel else None,
        })

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.patch("/{adaptation_id}")
async def update_adaptation(
    adaptation_id: uuid.UUID,
    data: AdaptationUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update an adaptation (approve, reject, or edit content)."""
    adaptation = await db.get(ChannelAdaptation, adaptation_id)
    if not adaptation or str(adaptation.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Adaptation not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(adaptation, key, value)

    await db.commit()
    await db.refresh(adaptation)

    return {
        "id": str(adaptation.id),
        "status": adaptation.status,
        "headline": adaptation.headline,
        "body": adaptation.body,
        "content_format": adaptation.content_format,
    }
