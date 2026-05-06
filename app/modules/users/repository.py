from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_STUDENT, DEFAULT_PAGE_SIZE
from app.modules.users.models import User
from app.modules.profile.models import StudentProfile


class UsersRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update(self, user: User, data: dict) -> User:
        for key, value in data.items():
            if value is not None:
                setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()

    async def list_students(
        self,
        group_type: str | None = None,
        course_year: int | None = None,
        ielts_passed: bool | None = None,
        sat_passed: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[User], int]:
        stmt = (
            select(User)
            .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
            .where(User.role == ROLE_STUDENT, User.is_active == True)
        )

        if group_type:
            stmt = stmt.where(StudentProfile.group_type == group_type)
        if course_year:
            stmt = stmt.where(StudentProfile.course_year == course_year)
        if ielts_passed is not None:
            stmt = stmt.where(StudentProfile.ielts_passed == ielts_passed)
        if sat_passed is not None:
            stmt = stmt.where(StudentProfile.sat_passed == sat_passed)
        if search:
            stmt = stmt.where(User.full_name.ilike(f"%{search}%"))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def create_student(self, **kwargs) -> User:
        user = User(role=ROLE_STUDENT, **kwargs)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
