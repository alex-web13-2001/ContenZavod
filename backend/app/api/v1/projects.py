"""Projects CRUD endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List all projects for the current tenant."""
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    items, total = await service.list(page, per_page)
    return {
        "items": [ProjectListResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.create(data)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    project = await service.update(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.project_service import ProjectService

    service = ProjectService(db, tenant_id)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/recommendations")
async def list_project_recommendations(
    project_id: str,
    recommended_only: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List materials scored for this project, optionally filtered to recommended only."""
    import uuid as _uuid
    from sqlalchemy import select, func
    from app.models.project_score import MaterialProjectScore
    from app.models.material import RawMaterial

    tid = _uuid.UUID(tenant_id)
    pid = _uuid.UUID(project_id)

    query = (
        select(MaterialProjectScore)
        .where(
            MaterialProjectScore.project_id == pid,
            MaterialProjectScore.tenant_id == tid,
        )
    )

    if recommended_only:
        query = query.where(MaterialProjectScore.is_recommended == True)

    query = query.order_by(MaterialProjectScore.created_at.desc())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    scores = result.scalars().all()

    # Enrich with material data
    items = []
    for s in scores:
        material = await db.get(RawMaterial, s.material_id)
        items.append({
            "id": str(s.id),
            "material_id": str(s.material_id),
            "project_id": str(s.project_id),
            "relevance_score": s.relevance_score,
            "hype_score": s.hype_score,
            "is_recommended": s.is_recommended,
            "explanation": s.explanation,
            "created_at": s.created_at.isoformat(),
            "material_title": material.title if material else None,
            "material_url": material.original_url if material else None,
            "material_status": material.status if material else None,
        })

    return {"items": items, "total": total, "page": page, "per_page": per_page}

