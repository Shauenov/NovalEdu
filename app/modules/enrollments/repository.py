from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrollments.models import Enrollment
from app.modules.users.models import User


class EnrollmentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_student_and_university(
        self, student_id: UUID, university_id: UUID
    ) -> Enrollment | None:
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.university_id == university_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_student(self, student_id: UUID) -> list[Enrollment]:
        result = await self.db.execute(
            select(Enrollment)
            .where(Enrollment.student_id == student_id)
            .order_by(Enrollment.created_at.desc())
        )
        return result.scalars().all()

    async def list_for_university(
        self,
        university_id: UUID,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """Return enrollments for a university, joined with user info."""
        base_where = [Enrollment.university_id == university_id]
        if status:
            base_where.append(Enrollment.status == status)

        # Count
        count_stmt = select(func.count(Enrollment.id)).where(*base_where)
        total: int = (await self.db.execute(count_stmt)).scalar_one()

        # Data with join
        stmt = (
            select(Enrollment, User)
            .join(User, User.id == Enrollment.student_id)
            .where(*base_where)
            .order_by(Enrollment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(stmt)).all()

        result = []
        for enrollment, user in rows:
            result.append({
                "id": enrollment.id,
                "student_id": enrollment.student_id,
                "student": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                },
                "university_id": enrollment.university_id,
                "status": enrollment.status,
                "progress": enrollment.progress,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
            })
        return result, total

    async def create(self, **kwargs) -> Enrollment:
        enrollment = Enrollment(**kwargs)
        self.db.add(enrollment)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def update(self, enrollment: Enrollment, data: dict) -> Enrollment:
        for key, value in data.items():
            setattr(enrollment, key, value)
        await self.db.flush()
        await self.db.refresh(enrollment)
        return enrollment

    async def delete(self, enrollment: Enrollment) -> None:
        await self.db.delete(enrollment)
        await self.db.flush()
