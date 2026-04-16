"""Project service — CRUD for thematic content projects."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.channel import Channel
from app.models.project_score import MaterialProjectScore
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id)

    async def list(self, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        """List projects with channel count and recommendation count."""
        offset = (page - 1) * per_page

        count_q = select(func.count()).select_from(Project).where(
            Project.tenant_id == self.tenant_id
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(Project)
            .where(Project.tenant_id == self.tenant_id)
            .options(selectinload(Project.channels))
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        projects = list(result.scalars().all())

        items = []
        for p in projects:
            # Count recommendations for this project
            rec_q = select(func.count()).select_from(MaterialProjectScore).where(
                MaterialProjectScore.project_id == p.id,
                MaterialProjectScore.is_recommended == True,  # noqa: E712
            )
            rec_count = (await self.db.execute(rec_q)).scalar() or 0

            items.append({
                **{c.key: getattr(p, c.key) for c in p.__table__.columns},
                "channel_count": len(p.channels),
                "recommendation_count": rec_count,
            })

        return items, total

    async def get(self, project_id: str) -> Project | None:
        result = await self.db.execute(
            select(Project)
            .where(
                Project.id == uuid.UUID(project_id),
                Project.tenant_id == self.tenant_id,
            )
            .options(selectinload(Project.channels))
        )
        return result.scalar_one_or_none()

    async def create(self, data: ProjectCreate) -> Project:
        project = Project(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            topic_guidelines=data.topic_guidelines,
            target_audience=data.target_audience,
            is_active=data.is_active,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project_id: str, data: ProjectUpdate) -> Project | None:
        project = await self.get(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: str) -> bool:
        project = await self.get(project_id)
        if not project:
            return False

        await self.db.delete(project)
        await self.db.commit()
        return True
