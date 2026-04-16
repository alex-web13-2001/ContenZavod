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
