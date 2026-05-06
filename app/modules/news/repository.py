from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.news.models import News


class NewsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, news_id: UUID) -> News | None:
        result = await self.db.execute(select(News).where(News.id == news_id))
        return result.scalar_one_or_none()

    async def list_news(
        self,
        category: str | None = None,
        upcoming: bool | None = None,
        include_unpublished: bool = False,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[News], int]:
        stmt = select(News)

        if not include_unpublished:
            stmt = stmt.where(News.is_published == True)
        if category:
            stmt = stmt.where(News.category == category)
        if upcoming is True:
            stmt = stmt.where(News.event_date.isnot(None), News.event_date >= date.today())

        stmt = stmt.order_by(News.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def create(self, **kwargs) -> News:
        item = News(**kwargs)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update(self, item: News, data: dict) -> News:
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def increment_views(self, news_id: UUID) -> None:
        await self.db.execute(
            update(News).where(News.id == news_id).values(views_count=News.views_count + 1)
        )
