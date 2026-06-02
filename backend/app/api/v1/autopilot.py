"""Autopilot API — manage autopilot settings and queue.

Endpoints:
  GET  /projects/{id}/autopilot/config    — get autopilot config for all channels
  PUT  /projects/{id}/autopilot/config    — update autopilot config for a channel
  GET  /projects/{id}/autopilot/queue     — get current queue with scores
  POST /projects/{id}/autopilot/approve   — approve a shadow item (shadow mode)
  POST /projects/{id}/autopilot/reject    — reject a shadow item (shadow mode)
  GET  /projects/{id}/autopilot/stats     — autopilot activity stats
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.models.autopilot_queue import AutopilotQueueItem
from app.models.channel import Channel
from app.models.channel_adaptation import ChannelAdaptation
from app.models.material import RawMaterial

router = APIRouter(prefix="/projects/{project_id}/autopilot", tags=["autopilot"])


# --- Schemas ---

class AutopilotConfigUpdate(BaseModel):
    """Request body for updating autopilot config on a channel."""
    channel_id: str
    enabled: bool | None = None
    shadow_mode: bool | None = None
    max_posts_per_day: int | None = None
    min_interval_minutes: int | None = None
    min_score_threshold: float | None = None
    cover_policy: str | None = None
    use_source_images: bool | None = None  # False → always AI-generate covers
    schedule_slots: list[str] | None = None
    strategies: list[str] | None = None
    category_limits: dict | None = None
    ttl_hours: dict | None = None
    language_settings: dict | None = None  # Per-language overrides
    format_ratios: dict | None = None  # {"flash": 0.4, "short_post": 0.4, "longread": 0.2}
    longread_max_per_day: int | None = None
    max_material_age_hours: int | None = None  # ADR-007: hard freshness cutoff


class QueueActionRequest(BaseModel):
    """Request body for approving/rejecting a queue item."""
    queue_item_id: str


class EnqueueRequest(BaseModel):
    """Request body for manual enqueue from Recommendations.

    The user explicitly chose channel + format, bypassing ratio balancing.
    Language is derived from the chosen channel's primary language.
    """
    material_id: str
    channel_id: str
    content_format: str
    language: str | None = None  # If None, uses channel's first language


# --- Endpoints ---

@router.get("/config")
async def get_autopilot_config(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get autopilot configuration for all channels in the project."""
    channels = (await session.execute(
        select(Channel).where(
            Channel.project_id == uuid.UUID(project_id),
            Channel.tenant_id == uuid.UUID(tenant_id),
            Channel.is_active == True,
        )
    )).scalars().all()

    result = []
    for ch in channels:
        config = ch.autopilot_config or {}
        result.append({
            "channel_id": str(ch.id),
            "channel_name": ch.name,
            "languages": ch.languages,
            "content_formats": ch.content_formats or ["short_post"],
            "autopilot": {
                "enabled": config.get("enabled", False),
                "shadow_mode": config.get("shadow_mode", True),
                "max_posts_per_day": config.get("max_posts_per_day", 10),
                "min_interval_minutes": config.get("min_interval_minutes", 45),
                "min_score_threshold": config.get("min_score_threshold", 7.0),
                "cover_policy": config.get("cover_policy", "short_post_optional"),
                "use_source_images": config.get("use_source_images", False),
                "schedule_slots": config.get("schedule_slots", ["morning", "lunch", "evening", "night"]),
                "strategies": config.get("strategies", ["smart_queue", "express"]),
                "category_limits": config.get("category_limits", {}),
                "ttl_hours": config.get("ttl_hours", {}),
                "language_settings": config.get("language_settings", {}),
                "format_ratios": config.get("format_ratios", {
                    "flash": 0.40, "short_post": 0.40, "longread": 0.20,
                }),
                "longread_max_per_day": config.get("longread_max_per_day", 2),
                "max_material_age_hours": config.get("max_material_age_hours", 24),
            },
        })

    return {"channels": result}


@router.put("/config")
async def update_autopilot_config(
    project_id: str,
    body: AutopilotConfigUpdate,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Update autopilot configuration for a specific channel."""
    channel = await session.get(Channel, uuid.UUID(body.channel_id))
    if not channel or str(channel.project_id) != project_id:
        raise HTTPException(404, "Channel not found in this project")
    if str(channel.tenant_id) != tenant_id:
        raise HTTPException(403, "Forbidden")

    config = {**(channel.autopilot_config or {})}

    # Update only provided fields
    updates = body.model_dump(exclude_none=True, exclude={"channel_id"})
    config.update(updates)

    channel.autopilot_config = config
    await session.commit()

    return {"status": "ok", "channel_id": body.channel_id, "config": config}


@router.get("/queue")
async def get_autopilot_queue(
    project_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get current autopilot queue items for the project."""
    pid = uuid.UUID(project_id)
    tid = uuid.UUID(tenant_id)

    query = (
        select(AutopilotQueueItem)
        .options(
            selectinload(AutopilotQueueItem.adaptation),
            selectinload(AutopilotQueueItem.channel),
        )
        .where(
            AutopilotQueueItem.project_id == pid,
            AutopilotQueueItem.tenant_id == tid,
        )
    )

    if status:
        query = query.where(AutopilotQueueItem.status == status)
    else:
        # Default: show active items (queued, shadow, approved, publishing)
        query = query.where(
            AutopilotQueueItem.status.in_(["queued", "shadow", "approved", "publishing"])
        )

    query = query.order_by(AutopilotQueueItem.final_score.desc()).limit(50)

    items = (await session.execute(query)).scalars().all()

    # Bulk-fetch source materials for material_id → freshness dates
    material_ids = {item.adaptation.material_id for item in items if item.adaptation}
    materials_map: dict = {}
    if material_ids:
        rows = (await session.execute(
            select(
                RawMaterial.id,
                RawMaterial.published_at,
                RawMaterial.scraped_at,
            ).where(RawMaterial.id.in_(material_ids))
        )).all()
        materials_map = {m_id: (pub, scr) for m_id, pub, scr in rows}

    result = []
    for item in items:
        adapt = item.adaptation
        ch = item.channel

        body_text = adapt.body if adapt else ""
        mat_published_at, mat_scraped_at = materials_map.get(
            adapt.material_id if adapt else None, (None, None)
        )
        result.append({
            "id": str(item.id),
            "channel_id": str(item.channel_id),
            "channel_name": ch.name if ch else "?",
            "adaptation_id": str(item.adaptation_id),
            "language": adapt.language if adapt else "?",
            "headline": adapt.headline if adapt else "",
            "body_preview": body_text[:200] + ("…" if len(body_text) > 200 else ""),
            "body": body_text,
            "content_format": adapt.content_format if adapt else "",
            "cover_status": adapt.cover_status if adapt else None,
            "cover_image_url": adapt.cover_image_url if adapt else None,
            "strategy": item.strategy,
            "final_score": float(item.final_score),
            "freshness_score": float(item.freshness_score),
            "status": item.status,
            "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
            "created_at": item.created_at.isoformat(),
            "material_published_at": mat_published_at.isoformat() if mat_published_at else None,
            "material_scraped_at": mat_scraped_at.isoformat() if mat_scraped_at else None,
        })

    return {"items": result, "total": len(result)}


@router.post("/enqueue")
async def enqueue_material_to_autopilot(
    project_id: str,
    body: EnqueueRequest,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Manually enqueue a material into the autopilot queue for a specific channel/format.

    Triggered from Recommendations UI when the editor wants to bypass the
    automatic ranking and force a material into the queue.
    """
    # Validate that the channel belongs to the project and tenant
    channel = await session.get(Channel, uuid.UUID(body.channel_id))
    if not channel:
        raise HTTPException(404, "Channel not found")
    if str(channel.project_id) != project_id or str(channel.tenant_id) != tenant_id:
        raise HTTPException(403, "Channel does not belong to this project/tenant")

    # Validate content_format
    allowed_formats = channel.content_formats or ["short_post"]
    if body.content_format not in allowed_formats:
        raise HTTPException(
            400,
            f"Format '{body.content_format}' not in channel.content_formats {allowed_formats}",
        )

    # Resolve language
    language = body.language or (channel.languages[0] if channel.languages else "ru")
    if language not in (channel.languages or []):
        raise HTTPException(
            400, f"Language '{language}' not in channel.languages {channel.languages}"
        )

    # Dispatch the adapt+enqueue Celery task
    from workers.ai_tasks import adapt_and_enqueue_autopilot
    task = adapt_and_enqueue_autopilot.delay(
        body.material_id, body.channel_id, body.content_format,
        language, tenant_id, project_id,
    )

    return {"status": "accepted", "task_id": task.id}


@router.post("/approve")
async def approve_queue_item(
    project_id: str,
    body: QueueActionRequest,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Approve a shadow-mode queue item for publishing."""
    item = await session.get(AutopilotQueueItem, uuid.UUID(body.queue_item_id))
    if not item or str(item.project_id) != project_id:
        raise HTTPException(404, "Queue item not found")
    if str(item.tenant_id) != tenant_id:
        raise HTTPException(403, "Forbidden")

    if item.status != "shadow":
        raise HTTPException(400, f"Item status is '{item.status}', expected 'shadow'")

    item.status = "approved"
    item.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    await session.commit()

    return {"status": "ok", "queue_item_id": body.queue_item_id, "new_status": "approved"}


@router.post("/reject")
async def reject_queue_item(
    project_id: str,
    body: QueueActionRequest,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Reject a shadow-mode queue item (feedback for calibration)."""
    item = await session.get(AutopilotQueueItem, uuid.UUID(body.queue_item_id))
    if not item or str(item.project_id) != project_id:
        raise HTTPException(404, "Queue item not found")
    if str(item.tenant_id) != tenant_id:
        raise HTTPException(403, "Forbidden")

    if item.status not in ("shadow", "queued"):
        raise HTTPException(400, f"Item status is '{item.status}', cannot reject")

    item.status = "skipped"
    item.skip_reason = "user_rejected"
    await session.commit()

    return {"status": "ok", "queue_item_id": body.queue_item_id, "new_status": "skipped"}


@router.get("/stats")
async def get_autopilot_stats(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get autopilot activity stats for today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    pid = uuid.UUID(project_id)
    tid = uuid.UUID(tenant_id)

    # Today's counts by status
    status_counts = {}
    rows = (await session.execute(
        select(
            AutopilotQueueItem.status,
            func.count(AutopilotQueueItem.id),
        )
        .where(
            AutopilotQueueItem.project_id == pid,
            AutopilotQueueItem.tenant_id == tid,
            AutopilotQueueItem.created_at >= today_start,
        )
        .group_by(AutopilotQueueItem.status)
    )).all()
    for row in rows:
        status_counts[row[0]] = row[1]

    # Next scheduled item
    next_item = (await session.execute(
        select(AutopilotQueueItem)
        .where(
            AutopilotQueueItem.project_id == pid,
            AutopilotQueueItem.tenant_id == tid,
            AutopilotQueueItem.status.in_(["queued", "approved"]),
        )
        .order_by(AutopilotQueueItem.scheduled_at.asc())
        .limit(1)
    )).scalar_one_or_none()

    # Pending shadow items
    shadow_count = (await session.execute(
        select(func.count(AutopilotQueueItem.id)).where(
            AutopilotQueueItem.project_id == pid,
            AutopilotQueueItem.tenant_id == tid,
            AutopilotQueueItem.status == "shadow",
        )
    )).scalar() or 0

    # Format counts today
    format_counts: dict[str, int] = {}
    fmt_rows = (await session.execute(
        select(
            ChannelAdaptation.content_format,
            func.count(AutopilotQueueItem.id),
        )
        .join(
            ChannelAdaptation,
            AutopilotQueueItem.adaptation_id == ChannelAdaptation.id,
        )
        .where(
            AutopilotQueueItem.project_id == pid,
            AutopilotQueueItem.tenant_id == tid,
            AutopilotQueueItem.created_at >= today_start,
            AutopilotQueueItem.status.in_(
                ["queued", "shadow", "approved", "publishing", "published"]
            ),
        )
        .group_by(ChannelAdaptation.content_format)
    )).all()
    for fmt_name, cnt in fmt_rows:
        if fmt_name:
            format_counts[fmt_name] = cnt

    return {
        "today": status_counts,
        "published_today": status_counts.get("published", 0),
        "queued": status_counts.get("queued", 0) + status_counts.get("approved", 0),
        "shadow_pending": shadow_count,
        "format_counts": format_counts,
        "next_scheduled": {
            "id": str(next_item.id),
            "scheduled_at": next_item.scheduled_at.isoformat(),
            "strategy": next_item.strategy,
            "score": float(next_item.final_score),
        } if next_item else None,
    }
