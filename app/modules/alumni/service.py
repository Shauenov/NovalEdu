from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN, ROLE_ADVISER
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.alumni.repository import AlumniRepository
from app.modules.alumni.schemas import AlumniCreate, AlumniUpdate


class AlumniService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AlumniRepository(db)

    async def list_stories(self, requester_role: str):
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_ADVISER)
        return await self.repo.list_stories(include_unpublished=include_unpublished)

    async def get_story(self, story_id: UUID, requester_role: str):
        story = await self.repo.get_by_id(story_id)
        if not story:
            raise NotFoundException("Story not found")
        if not story.is_published and requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise NotFoundException("Story not found")
        return story

    async def create_story(self, data: AlumniCreate, author_id: UUID, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can create alumni stories")
        story = await self.repo.create(author_id=author_id, **data.model_dump())
        await self.db.commit()
        return story

    async def update_story(self, story_id: UUID, data: AlumniUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can update alumni stories")
        story = await self.repo.get_by_id(story_id)
        if not story:
            raise NotFoundException("Story not found")
        updated = await self.repo.update(story, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_story(self, story_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can delete alumni stories")
        story = await self.repo.get_by_id(story_id)
        if not story:
            raise NotFoundException("Story not found")
        await self.repo.update(story, {"is_published": False})
        await self.db.commit()
