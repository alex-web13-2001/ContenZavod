"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.models.channel import Channel
from app.models.material import RawMaterial
from app.models.publish_job import PublishJob
from app.models.source import Source

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Get overview statistics for the dashboard."""
    import uuid

    tid = uuid.UUID(tenant_id)

    # Sources count
    sources_total = (await db.execute(
        select(func.count()).select_from(Source).where(Source.tenant_id == tid)
    )).scalar() or 0

    sources_active = (await db.execute(
        select(func.count()).select_from(Source).where(
            Source.tenant_id == tid, Source.is_active == True  # noqa: E712
        )
    )).scalar() or 0

    # Materials by status
    material_stats = (await db.execute(
        select(RawMaterial.status, func.count())
        .where(RawMaterial.tenant_id == tid)
        .group_by(RawMaterial.status)
    )).all()

    materials_by_status = {row[0]: row[1] for row in material_stats}
    materials_total = sum(materials_by_status.values())

    # Channels count
    channels_total = (await db.execute(
        select(func.count()).select_from(Channel).where(Channel.tenant_id == tid)
    )).scalar() or 0

    # Publish jobs by status
    job_stats = (await db.execute(
        select(PublishJob.status, func.count())
        .where(PublishJob.tenant_id == tid)
        .group_by(PublishJob.status)
    )).all()

    jobs_by_status = {row[0]: row[1] for row in job_stats}

    return {
        "sources": {"total": sources_total, "active": sources_active},
        "materials": {"total": materials_total, "by_status": materials_by_status},
        "channels": {"total": channels_total},
        "publish_jobs": {"by_status": jobs_by_status},
    }
