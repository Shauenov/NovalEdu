from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_STUDENT, DEFAULT_PAGE_SIZE
from app.modules.users.models import User
from app.modules.profile.models import StudentProfile
from app.modules.tasks.models import Task


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
        sort_by: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[tuple], int]:
        # Correlated subqueries for task counts
        tasks_total_sq = (
            select(func.count())
            .where(Task.student_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        tasks_done_sq = (
            select(func.count())
            .where(Task.student_id == User.id, Task.status == "done")
            .correlate(User)
            .scalar_subquery()
        )
        tasks_overdue_sq = (
            select(func.count())
            .where(Task.student_id == User.id, Task.status == "overdue")
            .correlate(User)
            .scalar_subquery()
        )
        tasks_in_progress_sq = (
            select(func.count())
            .where(Task.student_id == User.id, Task.status == "in_progress")
            .correlate(User)
            .scalar_subquery()
        )

        stmt = (
            select(
                User,
                StudentProfile,
                tasks_total_sq.label("tasks_total"),
                tasks_done_sq.label("tasks_done"),
                tasks_overdue_sq.label("tasks_overdue"),
                tasks_in_progress_sq.label("tasks_in_progress"),
            )
            .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
            .where(User.role == ROLE_STUDENT, User.is_active == True)
        )

        def _apply_filters(q):
            """Apply all user-provided filters to a query."""
            if group_type:
                # "D" or "F" alone → match all sub-groups (D1, D2 / F1..F4)
                if group_type in ("D", "F"):
                    q = q.where(StudentProfile.group_type.like(f"{group_type}%"))
                else:
                    q = q.where(StudentProfile.group_type == group_type)
            if course_year:
                q = q.where(StudentProfile.course_year == course_year)
            if ielts_passed is not None:
                q = q.where(StudentProfile.ielts_passed == ielts_passed)
            if sat_passed is not None:
                q = q.where(StudentProfile.sat_passed == sat_passed)
            if search:
                q = q.where(User.full_name.ilike(f"%{search}%"))
            return q

        stmt = _apply_filters(stmt)

        # Count with the same filters
        count_base = _apply_filters(
            select(func.count(User.id))
            .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
            .where(User.role == ROLE_STUDENT, User.is_active == True)
        )
        total = (await self.db.execute(count_base)).scalar_one()

        # Sorting
        if sort_by == "gpa":
            stmt = stmt.order_by(StudentProfile.gpa.desc().nulls_last())
        else:
            stmt = stmt.order_by(User.full_name.asc())

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.all(), total

    async def create_student(self, **kwargs) -> User:
        user = User(role=ROLE_STUDENT, **kwargs)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
