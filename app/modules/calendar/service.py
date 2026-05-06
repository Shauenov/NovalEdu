from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.calendar.repository import CalendarRepository
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate


class CalendarService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CalendarRepository(db)

    async def list_events(self, user_id: UUID, from_time=None, to_time=None, event_type=None):
        return await self.repo.list_events(user_id, from_time, to_time, event_type)

    async def create_event(self, user_id: UUID, data: CalendarEventCreate):
        event = await self.repo.create(user_id=user_id, **data.model_dump())
        await self.db.commit()
        return event

    async def update_event(self, event_id: UUID, user_id: UUID, data: CalendarEventUpdate):
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")
        if event.user_id != user_id:
            raise ForbiddenException("Access denied")
        updated = await self.repo.update(event, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_event(self, event_id: UUID, user_id: UUID) -> None:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")
        if event.user_id != user_id:
            raise ForbiddenException("Access denied")
        await self.repo.delete(event)
        await self.db.commit()
