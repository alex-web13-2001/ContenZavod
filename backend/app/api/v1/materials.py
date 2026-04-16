"""Materials listing and management endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.schemas.material import MaterialListResponse, MaterialResponse, MaterialStatusUpdate

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=dict)
async def list_materials(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    source_id: str | None = Query(None),
    channel_id: str | None = Query(None),
    project_id: str | None = Query(None),
    recommended: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List materials with optional filters."""
    from app.services.material_service import MaterialService

    service = MaterialService(db, tenant_id)
    items, total = await service.list(
        page, per_page, status, source_id, channel_id,
        project_id=project_id, recommended=recommended,
    )
    return {
        "items": [MaterialListResponse.model_validate(m) for m in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Get a single material with full content."""
    from app.services.material_service import MaterialService

    service = MaterialService(db, tenant_id)
    material = await service.get(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return MaterialResponse.model_validate(material)


@router.patch("/{material_id}/status", response_model=MaterialResponse)
async def update_material_status(
    material_id: str,
    data: MaterialStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Update material status (e.g., new → classified → adapted → published)."""
    from app.services.material_service import MaterialService

    service = MaterialService(db, tenant_id)
    material = await service.update_status(material_id, data.status)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return MaterialResponse.model_validate(material)


@router.post("/{material_id}/classify", status_code=202)
async def classify_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Classify a single material using AI."""
    from app.services.material_service import MaterialService

    service = MaterialService(db, tenant_id)
    material = await service.get(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    from workers.ai_tasks import classify_material as classify_task
    task = classify_task.delay(material_id, tenant_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/classify-all", status_code=202)
async def classify_all_new(
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """Classify all materials with status 'new'."""
    from workers.ai_tasks import classify_new_materials
    task = classify_new_materials.delay(tenant_id)
    return {"task_id": task.id, "status": "queued"}

