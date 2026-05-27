from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reviews.models import Review
from app.modules.users.models import User


class ReviewsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_author_adviser(self, author_id: UUID, adviser_id: UUID) -> Review | None:
        result = await self.db.execute(
            select(Review).where(Review.author_id == author_id, Review.adviser_id == adviser_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Review:
        review = Review(**kwargs)
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def update(self, review: Review, data: dict) -> Review:
        for key, value in data.items():
            setattr(review, key, value)
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def list_for_adviser(self, adviser_id: UUID) -> list[tuple[Review, str | None]]:
        """Reviews with the author's display name, newest first."""
        result = await self.db.execute(
            select(Review, User.full_name)
            .join(User, User.id == Review.author_id)
            .where(Review.adviser_id == adviser_id)
            .order_by(Review.created_at.desc())
        )
        return result.all()

    async def aggregate_for_adviser(self, adviser_id: UUID) -> tuple[float, int]:
        result = await self.db.execute(
            select(func.coalesce(func.avg(Review.rating), 0.0), func.count())
            .where(Review.adviser_id == adviser_id)
        )
        avg, count = result.one()
        return round(float(avg), 1), int(count)

    async def get_latest(self, adviser_id: UUID | None = None) -> tuple[Review, str | None] | None:
        stmt = select(Review, User.full_name).join(User, User.id == Review.author_id)
        if adviser_id is not None:
            stmt = stmt.where(Review.adviser_id == adviser_id)
        stmt = stmt.order_by(Review.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        row = result.first()
        return (row[0], row[1]) if row else None
