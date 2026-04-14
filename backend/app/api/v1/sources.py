"""Sources CRUD endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.schemas.source import SourceCreate, SourceResponse, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=dict)
async def list_sources(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List all sources for the current tenant."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    items, total = await service.list(page, per_page)
    return {
        "items": [SourceResponse.model_validate(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Get a single source."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    source = await service.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.model_validate(source)


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Create a new source."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    source = await service.create(data)
    return SourceResponse.model_validate(source)


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: str,
    data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Update a source."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    source = await service.update(source_id, data)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Delete a source."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    deleted = await service.delete(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")


@router.post("/{source_id}/scrape", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Manually trigger scraping for a source. Returns Celery task ID."""
    from app.services.source_service import SourceService

    service = SourceService(db, tenant_id)
    source = await service.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from workers.scrape_tasks import scrape_source
    task = scrape_source.delay(source_id, tenant_id)

    return {"task_id": task.id, "status": "queued", "source": source.name}

