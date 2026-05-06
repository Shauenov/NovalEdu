from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.calendar.models import CalendarEvent


class CalendarRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, event_id: UUID) -> CalendarEvent | None:
        result = await self.db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
        return result.scalar_one_or_none()

    async def list_events(
        self,
        user_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        event_type: str | None = None,
    ) -> list[CalendarEvent]:
        stmt = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        if from_time:
            stmt = stmt.where(CalendarEvent.start_time >= from_time)
        if to_time:
            stmt = stmt.where(CalendarEvent.start_time <= to_time)
        if event_type:
            stmt = stmt.where(CalendarEvent.event_type == event_type)
        result = await self.db.execute(stmt.order_by(CalendarEvent.start_time.asc()))
        return result.scalars().all()

    async def create(self, **kwargs) -> CalendarEvent:
        event = CalendarEvent(**kwargs)
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def update(self, event: CalendarEvent, data: dict) -> CalendarEvent:
        for key, value in data.items():
            if value is not None:
                setattr(event, key, value)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete(self, event: CalendarEvent) -> None:
        await self.db.delete(event)
        await self.db.flush()

    async def delete_by_source(self, user_id: UUID, source_id: UUID, source_type: str) -> int:
        result = await self.db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.source_id == source_id,
                CalendarEvent.source_type == source_type,
            )
        )
        await self.db.flush()
        return result.rowcount or 0
