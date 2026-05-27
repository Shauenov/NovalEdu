from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advisers.models import AdviserProfile


class AdvisersRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> AdviserProfile | None:
        result = await self.db.execute(
            select(AdviserProfile).where(AdviserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: UUID) -> AdviserProfile:
        profile = await self.get_by_user_id(user_id)
        if profile:
            return profile
        profile = AdviserProfile(user_id=user_id)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: AdviserProfile, data: dict) -> AdviserProfile:
        for key, value in data.items():
            setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
