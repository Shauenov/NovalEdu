from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_CONDUCTOR, ROLE_STUDENT
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.modules.news.repository import NewsRepository
from app.modules.news.schemas import NewsCreate, NewsUpdate
from app.modules.calendar.service import CalendarService
from app.modules.calendar.schemas import CalendarEventCreate


class NewsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NewsRepository(db)

    async def list_news(
        self,
        requester_role: str,
        category: str | None = None,
        upcoming: bool | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_CONDUCTOR)
        return await self.repo.list_news(
            category=category,
            upcoming=upcoming,
            include_unpublished=include_unpublished,
            page=page,
            page_size=page_size,
        )

    async def get_news(self, news_id: UUID, requester_role: str):
        item = await self.repo.get_by_id(news_id)
        if not item:
            raise NotFoundException("News not found")
        if not item.is_published and requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise NotFoundException("News not found")

        await self.repo.increment_views(news_id)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def create_news(self, data: NewsCreate, author_id: UUID, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can create news")
        item = await self.repo.create(author_id=author_id, **data.model_dump())
        await self.db.commit()
        return item

    async def update_news(self, news_id: UUID, data: NewsUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can update news")
        item = await self.repo.get_by_id(news_id)
        if not item:
            raise NotFoundException("News not found")
        updated = await self.repo.update(item, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_news(self, news_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can delete news")
        item = await self.repo.get_by_id(news_id)
        if not item:
            raise NotFoundException("News not found")
        await self.repo.update(item, {"is_published": False})
        await self.db.commit()

    async def add_to_calendar(self, news_id: UUID, student_id: UUID, requester_role: str):
        if requester_role != ROLE_STUDENT:
            raise ForbiddenException("Only students can add news to calendar")
        item = await self.repo.get_by_id(news_id)
        if not item or not item.is_published:
            raise NotFoundException("News not found")
        if not item.event_date:
            raise ValidationException("News item has no event date")

        start = datetime.combine(item.event_date, time.min, tzinfo=timezone.utc)

        calendar = CalendarService(self.db)
        event = await calendar.create_event(
            student_id,
            CalendarEventCreate(
                title=item.title,
                description=item.body,
                event_type="news_event",
                start_time=start,
                end_time=None,
                all_day=True,
                color=None,
                source_id=item.id,
                source_type="news",
            ),
        )
        return event
