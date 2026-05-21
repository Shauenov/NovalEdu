from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN, ROLE_ADVISER
from app.core.exceptions import ForbiddenException
from app.modules.reports.repository import ReportsRepository


class ReportsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReportsRepository(db)

    async def overview(self, requester_role: str) -> dict:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can access reports")
        return await self.repo.overview_stats()

    async def students(self, requester_role: str) -> list[dict]:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can access reports")
        return await self.repo.students_progress()

    async def universities(self, requester_role: str) -> dict:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only ADVISER or admin can access reports")
        return await self.repo.universities_stats()
