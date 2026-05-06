from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.faq.models import FAQ


class FAQRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[FAQ]:
        result = await self.db.execute(
            select(FAQ).where(FAQ.is_active == True).order_by(FAQ.order_index.asc(), FAQ.created_at.asc())
        )
        return result.scalars().all()

    async def get_by_id(self, faq_id: UUID) -> FAQ | None:
        result = await self.db.execute(select(FAQ).where(FAQ.id == faq_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> FAQ:
        faq = FAQ(**kwargs)
        self.db.add(faq)
        await self.db.flush()
        await self.db.refresh(faq)
        return faq

    async def update(self, faq: FAQ, data: dict) -> FAQ:
        for key, value in data.items():
            if value is not None:
                setattr(faq, key, value)
        await self.db.flush()
        await self.db.refresh(faq)
        return faq

    async def deactivate(self, faq: FAQ) -> None:
        faq.is_active = False
        await self.db.flush()

    async def reorder(self, items: list[tuple[UUID, int]]) -> None:
        for faq_id, order_index in items:
            await self.db.execute(
                update(FAQ).where(FAQ.id == faq_id).values(order_index=order_index)
            )
