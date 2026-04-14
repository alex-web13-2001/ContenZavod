"""Source service — CRUD for content sources."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.schemas.source import SourceCreate, SourceUpdate


class SourceService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id)

    async def list(self, page: int = 1, per_page: int = 20) -> tuple[list[Source], int]:
        """List sources for the current tenant."""
        offset = (page - 1) * per_page

        # Count
        count_q = select(func.count()).select_from(Source).where(
            Source.tenant_id == self.tenant_id
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        # Items
        q = (
            select(Source)
            .where(Source.tenant_id == self.tenant_id)
            .order_by(Source.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        items = list(result.scalars().all())

        return items, total

    async def get(self, source_id: str) -> Source | None:
        """Get a single source by ID."""
        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id),
                Source.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: SourceCreate) -> Source:
        """Create a new source."""
        source = Source(
            tenant_id=self.tenant_id,
            name=data.name,
            url=data.url,
            source_type=data.source_type,
            scraper_config=data.scraper_config,
            schedule=data.schedule,
            is_active=data.is_active,
        )
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def update(self, source_id: str, data: SourceUpdate) -> Source | None:
        """Update an existing source."""
        source = await self.get(source_id)
        if not source:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(source, key, value)

        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def delete(self, source_id: str) -> bool:
        """Delete a source."""
        source = await self.get(source_id)
        if not source:
            return False

        await self.db.delete(source)
        await self.db.commit()
        return True
