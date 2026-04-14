"""Material service — listing and status management."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import RawMaterial


class MaterialService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id)

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        source_id: str | None = None,
    ) -> tuple[list[RawMaterial], int]:
        """List materials with optional filters."""
        offset = (page - 1) * per_page

        base_filter = [RawMaterial.tenant_id == self.tenant_id]
        if status:
            base_filter.append(RawMaterial.status == status)
        if source_id:
            base_filter.append(RawMaterial.source_id == uuid.UUID(source_id))

        count_q = select(func.count()).select_from(RawMaterial).where(*base_filter)
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(RawMaterial)
            .where(*base_filter)
            .order_by(RawMaterial.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        items = list(result.scalars().all())

        return items, total

    async def get(self, material_id: str) -> RawMaterial | None:
        """Get a single material by ID."""
        result = await self.db.execute(
            select(RawMaterial).where(
                RawMaterial.id == uuid.UUID(material_id),
                RawMaterial.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(self, material_id: str, status: str) -> RawMaterial | None:
        """Update material status."""
        material = await self.get(material_id)
        if not material:
            return None

        material.status = status
        await self.db.commit()
        await self.db.refresh(material)
        return material
