"""Channels CRUD endpoints."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_tenant_id
from app.schemas.channel import ChannelCreate, ChannelResponse, ChannelUpdate

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=dict)
async def list_channels(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    """List all channels for the current tenant, optionally filtered by project."""
    from app.services.channel_service import ChannelService

    service = ChannelService(db, tenant_id)
    items, total = await service.list(page, per_page, project_id)
    return {
        "items": [ChannelResponse.model_validate(c) for c in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.channel_service import ChannelService

    service = ChannelService(db, tenant_id)
    channel = await service.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse.model_validate(channel)


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.channel_service import ChannelService

    service = ChannelService(db, tenant_id)
    channel = await service.create(data)
    return ChannelResponse.model_validate(channel)


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: str,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.channel_service import ChannelService

    service = ChannelService(db, tenant_id)
    channel = await service.update(channel_id, data)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse.model_validate(channel)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _user: str = Depends(get_current_user_id),
):
    from app.services.channel_service import ChannelService

    service = ChannelService(db, tenant_id)
    deleted = await service.delete(channel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Channel not found")
