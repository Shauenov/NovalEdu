from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADVISER
from app.core.exceptions import NotFoundException
from app.modules.reviews.repository import ReviewsRepository
from app.modules.reviews.schemas import ReviewCreate, ReviewOut
from app.modules.users.repository import UsersRepository


class ReviewsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReviewsRepository(db)

    def _serialize(self, review, author_name: str | None) -> dict:
        return {
            "id": review.id,
            "author_id": review.author_id,
            "author_name": author_name,
            "adviser_id": review.adviser_id,
            "rating": review.rating,
            "text": review.text,
            "created_at": review.created_at,
        }

    async def create_review(self, adviser_id: UUID, author_id: UUID, data: ReviewCreate) -> ReviewOut:
        adviser = await UsersRepository(self.db).get_by_id(adviser_id)
        if not adviser or adviser.role != ROLE_ADVISER:
            raise NotFoundException("Adviser not found")

        existing = await self.repo.get_by_author_adviser(author_id, adviser_id)
        if existing:
            review = await self.repo.update(existing, {"rating": data.rating, "text": data.text})
        else:
            review = await self.repo.create(
                author_id=author_id, adviser_id=adviser_id, rating=data.rating, text=data.text
            )
        await self.db.commit()
        author = await UsersRepository(self.db).get_by_id(author_id)
        return ReviewOut.model_validate(
            self._serialize(review, author.full_name if author else None)
        )

    async def list_for_adviser(self, adviser_id: UUID) -> tuple[list[ReviewOut], float, int]:
        rows = await self.repo.list_for_adviser(adviser_id)
        items = [ReviewOut.model_validate(self._serialize(r, name)) for r, name in rows]
        avg, count = await self.repo.aggregate_for_adviser(adviser_id)
        return items, avg, count

    async def latest(self, adviser_id: UUID | None = None) -> ReviewOut | None:
        row = await self.repo.get_latest(adviser_id)
        if not row:
            return None
        review, name = row
        return ReviewOut.model_validate(self._serialize(review, name))
