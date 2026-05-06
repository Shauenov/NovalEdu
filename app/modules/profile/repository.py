from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile.models import StudentProfile


class ProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> StudentProfile | None:
        result = await self.db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, **kwargs) -> StudentProfile:
        profile = StudentProfile(user_id=user_id, **kwargs)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: StudentProfile, data: dict) -> StudentProfile:
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
