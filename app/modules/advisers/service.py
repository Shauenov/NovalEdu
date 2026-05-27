import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADVISER
from app.core.exceptions import NotFoundException
from app.modules.advisers.repository import AdvisersRepository
from app.modules.advisers.schemas import AdviserProfileUpdate, AdviserPublicOut
from app.modules.reviews.repository import ReviewsRepository
from app.modules.users.repository import UsersRepository


def _parse_skills(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return [str(s) for s in value] if isinstance(value, list) else []
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


class AdvisersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AdvisersRepository(db)

    async def get_public_profile(self, adviser_id: UUID) -> AdviserPublicOut:
        user = await UsersRepository(self.db).get_by_id(adviser_id)
        if not user or user.role != ROLE_ADVISER:
            raise NotFoundException("Adviser not found")

        profile = await self.repo.get_by_user_id(adviser_id)
        rating_avg, reviews_count = await ReviewsRepository(self.db).aggregate_for_adviser(adviser_id)

        return AdviserPublicOut(
            user_id=user.id,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            headline=profile.headline if profile else None,
            bio=profile.bio if profile else None,
            skills=_parse_skills(profile.skills) if profile else [],
            students_placed=profile.students_placed if profile else None,
            scholarships_won_usd=profile.scholarships_won_usd if profile else None,
            years_experience=profile.years_experience if profile else None,
            rating_avg=rating_avg,
            reviews_count=reviews_count,
        )

    async def update_my_profile(self, user_id: UUID, data: AdviserProfileUpdate) -> AdviserPublicOut:
        profile = await self.repo.get_or_create(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "skills" in update_data and isinstance(update_data["skills"], list):
            update_data["skills"] = json.dumps(update_data["skills"])
        await self.repo.update(profile, update_data)
        await self.db.commit()
        return await self.get_public_profile(user_id)
