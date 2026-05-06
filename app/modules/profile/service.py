from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.constants import ROLE_STUDENT
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.schemas import ProfileOut, ProfileUpdate


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProfileRepository(db)

    async def get_profile(self, user_id: UUID) -> ProfileOut:
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundException(f"Profile for user {user_id} not found")
        return ProfileOut.model_validate(profile)

    async def update_profile(
        self,
        target_user_id: UUID,
        data: ProfileUpdate,
        requester_id: UUID,
        requester_role: str,
    ) -> ProfileOut:
        # Students can only update their own profile
        if requester_role == ROLE_STUDENT and requester_id != target_user_id:
            raise ForbiddenException("Students can only update their own profile")

        profile = await self.repo.get_by_user_id(target_user_id)
        if not profile:
            raise NotFoundException(f"Profile for user {target_user_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        updated = await self.repo.update(profile, update_data)
        await self.db.commit()
        return ProfileOut.model_validate(updated)
