"""Channel service — CRUD for publication channels."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.schemas.channel import ChannelCreate, ChannelUpdate


class ChannelService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id)

    async def list(self, page: int = 1, per_page: int = 20) -> tuple[list[Channel], int]:
        """List channels for the current tenant."""
        offset = (page - 1) * per_page

        count_q = select(func.count()).select_from(Channel).where(
            Channel.tenant_id == self.tenant_id
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(Channel)
            .where(Channel.tenant_id == self.tenant_id)
            .order_by(Channel.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(q)
        items = list(result.scalars().all())

        return items, total

    async def get(self, channel_id: str) -> Channel | None:
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == uuid.UUID(channel_id),
                Channel.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: ChannelCreate) -> Channel:
        channel = Channel(
            tenant_id=self.tenant_id,
            name=data.name,
            channel_type=data.channel_type,
            config=data.config,
            posting_rules=data.posting_rules,
            is_active=data.is_active,
        )
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def update(self, channel_id: str, data: ChannelUpdate) -> Channel | None:
        channel = await self.get(channel_id)
        if not channel:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(channel, key, value)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def delete(self, channel_id: str) -> bool:
        channel = await self.get(channel_id)
        if not channel:
            return False

        await self.db.delete(channel)
        await self.db.commit()
        return True
