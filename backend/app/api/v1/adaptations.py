"""Channel Adaptations API — view and manage AI-generated content drafts.

Endpoints:
    GET  /adaptations?channel_id=&project_id=&status=draft  — list adaptations
    PATCH /adaptations/{id}                                 — approve/reject/edit
    POST /adaptations/generate                              — generate specific format on-demand
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


class GenerateRequest(BaseModel):
    """Request to generate an adaptation for a specific format on-demand."""
    material_id: str
    channel_id: str
    content_format: str = Field(..., pattern=r"^(short_post|longread|video_script|digest)$")
    language: str = "ru"


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
    """Update an adaptation (approve, reject, or edit content).

    When status changes to 'approved':
    - Creates a PublishJob record
    - Queues a Celery task to publish to the channel
    """
    from app.models.publish_job import PublishJob

    adaptation = await db.get(ChannelAdaptation, adaptation_id)
    if not adaptation or str(adaptation.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Adaptation not found")

    old_status = adaptation.status
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(adaptation, key, value)

    publish_job_id = None

    # If status changed to "approved" → trigger publish
    if data.status == "approved" and old_status != "approved":
        channel = await db.get(Channel, adaptation.channel_id)
        config = (channel.config or {}) if channel else {}

        if config.get("bot_token") and config.get("chat_id"):
            # Create PublishJob
            idempotency_key = f"{adaptation.id}:{adaptation.channel_id}:{adaptation.content_format}"

            # Check for existing job (idempotency)
            existing_job = await db.execute(
                select(PublishJob).where(PublishJob.idempotency_key == idempotency_key)
            )
            if not existing_job.scalar_one_or_none():
                job = PublishJob(
                    content_id=adaptation.id,
                    channel_id=adaptation.channel_id,
                    tenant_id=uuid.UUID(tenant_id),
                    status="queued",
                    idempotency_key=idempotency_key,
                )
                db.add(job)
                await db.flush()
                publish_job_id = str(job.id)

    await db.commit()
    await db.refresh(adaptation)

    # Queue Celery task AFTER commit (so PublishJob exists in DB)
    if publish_job_id:
        from workers.publish_tasks import publish_to_telegram
        publish_to_telegram.delay(publish_job_id)

    return {
        "id": str(adaptation.id),
        "status": adaptation.status,
        "headline": adaptation.headline,
        "body": adaptation.body,
        "content_format": adaptation.content_format,
        "publish_job_id": publish_job_id,
    }


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_adaptation(
    data: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Generate an adaptation for a specific format on-demand.

    Queues a Celery task and returns immediately (202 Accepted).
    The editor can poll /adaptations to see when it appears.
    """
    # Verify material exists and belongs to tenant
    material = await db.get(RawMaterial, uuid.UUID(data.material_id))
    if not material or str(material.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Material not found")

    # Verify channel exists and belongs to tenant
    channel = await db.get(Channel, uuid.UUID(data.channel_id))
    if not channel or str(channel.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Check if adaptation already exists
    existing = await db.execute(
        select(ChannelAdaptation).where(
            ChannelAdaptation.material_id == material.id,
            ChannelAdaptation.channel_id == channel.id,
            ChannelAdaptation.language == data.language,
            ChannelAdaptation.content_format == data.content_format,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Adaptation for this format already exists",
        )

    # Queue the Celery task
    from workers.ai_tasks import adapt_single_format

    task = adapt_single_format.delay(
        data.material_id,
        data.channel_id,
        data.content_format,
        data.language,
        tenant_id,
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "material_id": data.material_id,
        "channel_id": data.channel_id,
        "content_format": data.content_format,
        "language": data.language,
    }
