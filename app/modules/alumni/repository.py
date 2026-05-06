from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.alumni.models import AlumniStory


class AlumniRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, story_id: UUID) -> AlumniStory | None:
        result = await self.db.execute(select(AlumniStory).where(AlumniStory.id == story_id))
        return result.scalar_one_or_none()

    async def list_stories(self, include_unpublished: bool = False) -> list[AlumniStory]:
        stmt = select(AlumniStory)
        if not include_unpublished:
            stmt = stmt.where(AlumniStory.is_published == True)
        result = await self.db.execute(stmt.order_by(AlumniStory.created_at.desc()))
        return result.scalars().all()

    async def create(self, **kwargs) -> AlumniStory:
        story = AlumniStory(**kwargs)
        self.db.add(story)
        await self.db.flush()
        await self.db.refresh(story)
        return story

    async def update(self, story: AlumniStory, data: dict) -> AlumniStory:
        for key, value in data.items():
            if value is not None:
                setattr(story, key, value)
        await self.db.flush()
        await self.db.refresh(story)
        return story
