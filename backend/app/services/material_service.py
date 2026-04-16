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
        channel_id: str | None = None,
        project_id: str | None = None,
        recommended: bool | None = None,
    ) -> tuple[list[RawMaterial], int]:
        """List materials with optional filters."""
        offset = (page - 1) * per_page

        base_filter = [RawMaterial.tenant_id == self.tenant_id]
        if status:
            base_filter.append(RawMaterial.status == status)
        if source_id:
            base_filter.append(RawMaterial.source_id == uuid.UUID(source_id))

        # Project-level filtering
        if project_id:
            from app.models.project_score import MaterialProjectScore

            join_cond = (MaterialProjectScore.material_id == RawMaterial.id) & \
                        (MaterialProjectScore.project_id == uuid.UUID(project_id))

            q = select(RawMaterial).outerjoin(MaterialProjectScore, join_cond)
            q = q.add_columns(MaterialProjectScore)
            q = q.where(*base_filter)

            if recommended is True:
                q = q.where(MaterialProjectScore.is_recommended == True)  # noqa: E712
            elif recommended is False:
                q = q.where(
                    (MaterialProjectScore.is_recommended == False) |  # noqa: E712
                    (MaterialProjectScore.id == None)  # noqa: E711
                )

            count_q = select(func.count()).select_from(q.subquery())

            q = q.order_by(
                MaterialProjectScore.is_recommended.desc().nullslast(),
                MaterialProjectScore.hype_score.desc().nullslast(),
                RawMaterial.created_at.desc()
            )

            total = (await self.db.execute(count_q)).scalar() or 0
            q = q.offset(offset).limit(per_page)
            result = await self.db.execute(q)

            rows = result.all()
            items = []
            for row in rows:
                mat = row[0]
                score = row[1]
                if score:
                    mat.project_relevance_score = score.relevance_score
                    mat.project_hype_score = score.hype_score
                    mat.is_recommended = score.is_recommended
                    mat.project_explanation = score.explanation
                items.append(mat)

            return items, total

        # Channel-level filtering (legacy/compat)
        count_q = select(func.count()).select_from(RawMaterial).where(*base_filter)
        q = select(RawMaterial).where(*base_filter)

        if channel_id:
            from app.models.channel_score import MaterialChannelScore

            join_cond = (MaterialChannelScore.material_id == RawMaterial.id) & \
                        (MaterialChannelScore.channel_id == uuid.UUID(channel_id))
            
            q = q.outerjoin(MaterialChannelScore, join_cond)
            q = q.add_columns(MaterialChannelScore)

            q = q.order_by(
                MaterialChannelScore.is_recommended.desc().nullslast(),
                MaterialChannelScore.hype_score.desc().nullslast(),
                RawMaterial.created_at.desc()
            )
        else:
            q = q.order_by(RawMaterial.created_at.desc())

        total = (await self.db.execute(count_q)).scalar() or 0

        q = q.offset(offset).limit(per_page)
        
        result = await self.db.execute(q)
        
        if channel_id:
            rows = result.all()
            items = []
            for row in rows:
                mat = row[0]
                score = row[1]
                if score:
                    # Inject into unmapped properties so schema can read them
                    mat.channel_relevance_score = score.relevance_score
                    mat.channel_hype_score = score.hype_score
                    mat.is_recommended_for_channel = score.is_recommended
                    mat.channel_explanation = score.explanation
                items.append(mat)
        else:
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
