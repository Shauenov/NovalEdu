from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrollments.models import Enrollment


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
