from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_ADMIN, ROLE_ADVISER, ROLE_STUDENT
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.modules.enrollments.repository import EnrollmentsRepository
from app.modules.enrollments.schemas import (
    EnrollmentOut,
    EnrollmentUpdateRequest,
    EnrollmentWithStudentOut,
    PaginatedMeta,
    PaginatedUniversityEnrollments,
    StudentBriefForEnrollment,
)
from app.modules.universities.repository import UniversitiesRepository


class EnrollmentsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EnrollmentsRepository(db)

    async def enroll(
        self,
        student_id: UUID,
        university_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> EnrollmentOut:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only enroll themselves")

        uni_repo = UniversitiesRepository(self.db)
        university = await uni_repo.get_by_id(university_id)
        if not university:
            raise NotFoundException("University not found")

        existing = await self.repo.get_by_student_and_university(student_id, university_id)
        if existing:
            raise ConflictException("Already enrolled in this university")

        enrollment = await self.repo.create(
            student_id=student_id,
            university_id=university_id,
            status="selected",
            progress=0,
        )
        await self.db.commit()
        return EnrollmentOut.model_validate(enrollment)

    async def list_enrollments(
        self, student_id: UUID, requester_id: UUID, requester_role: str
    ) -> list[EnrollmentOut]:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own enrollments")
        items = await self.repo.list_for_student(student_id)
        return [EnrollmentOut.model_validate(e) for e in items]

    async def update_enrollment(
        self,
        student_id: UUID,
        university_id: UUID,
        data: EnrollmentUpdateRequest,
        requester_id: UUID,
        requester_role: str,
    ) -> EnrollmentOut:
        if requester_role not in (ROLE_ADVISER, ROLE_ADMIN):
            raise ForbiddenException("Only adviser or admin can update enrollment status")

        enrollment = await self.repo.get_by_student_and_university(student_id, university_id)
        if not enrollment:
            raise NotFoundException("Enrollment not found")

        updated = await self.repo.update(enrollment, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return EnrollmentOut.model_validate(updated)

    async def list_university_enrollments(
        self,
        university_id: UUID,
        requester_role: str,
        status: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedUniversityEnrollments:
        if requester_role not in (ROLE_ADVISER, ROLE_ADMIN):
            raise ForbiddenException("Only adviser or admin can view university enrollments")

        uni_repo = UniversitiesRepository(self.db)
        university = await uni_repo.get_by_id(university_id)
        if not university:
            raise NotFoundException("University not found")

        rows, total = await self.repo.list_for_university(
            university_id=university_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        items = [EnrollmentWithStudentOut(**row) for row in rows]
        return PaginatedUniversityEnrollments(
            data=items,
            meta=PaginatedMeta(page=page, page_size=page_size, total=total),
        )

    async def delete_enrollment(
        self,
        student_id: UUID,
        university_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> None:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only remove their own enrollments")

        enrollment = await self.repo.get_by_student_and_university(student_id, university_id)
        if not enrollment:
            raise NotFoundException("Enrollment not found")

        await self.repo.delete(enrollment)
        await self.db.commit()
