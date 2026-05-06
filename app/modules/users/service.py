from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_CONDUCTOR
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import hash_password
from app.modules.profile.repository import ProfileRepository
from app.modules.users.repository import UsersRepository
from app.modules.users.schemas import (
    PaginatedMeta,
    PaginatedStudents,
    StudentListItem,
    UserOut,
    UserUpdate,
)


class UsersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UsersRepository(db)
        self.profile_repo = ProfileRepository(db)

    async def get_me(self, user_id: UUID) -> UserOut:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return UserOut.model_validate(user)

    async def update_me(self, user_id: UUID, data: UserUpdate) -> UserOut:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        updated = await self.repo.update(user, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return UserOut.model_validate(updated)

    async def get_student(
        self, student_id: UUID, requester_id: UUID, requester_role: str
    ) -> dict:
        # Self-access OR conductor/admin
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN) and requester_id != student_id:
            raise ForbiddenException("Access denied")

        user = await self.repo.get_by_id(student_id)
        if not user:
            raise NotFoundException("Student not found")

        profile = await self.profile_repo.get_by_user_id(student_id)

        return {
            "user": UserOut.model_validate(user).model_dump(),
            "profile": profile.__dict__ if profile else None,
        }

    async def list_students(
        self,
        requester_role: str,
        group_type: str | None = None,
        course_year: int | None = None,
        ielts_passed: bool | None = None,
        sat_passed: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedStudents:
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only conductor or admin can list students")

        users, total = await self.repo.list_students(
            group_type=group_type,
            course_year=course_year,
            ielts_passed=ielts_passed,
            sat_passed=sat_passed,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = [StudentListItem.model_validate(u) for u in users]
        return PaginatedStudents(
            data=items,
            meta=PaginatedMeta(page=page, page_size=page_size, total=total),
        )

    async def delete_student(self, student_id: UUID, requester_role: str) -> None:
        if requester_role != ROLE_ADMIN:
            raise ForbiddenException("Only admin can delete student accounts")
        user = await self.repo.get_by_id(student_id)
        if not user:
            raise NotFoundException("Student not found")
        await self.repo.delete(user)
        await self.db.commit()

    async def invite_student(
        self,
        email: str,
        full_name: str,
        password: str,
        requester_role: str,
    ) -> UserOut:
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only conductor or admin can invite students")
        existing = await self.repo.get_by_email(email)
        if existing:
            from app.core.exceptions import ConflictException, ErrorCode
            raise ConflictException(message="Email already registered")
        user = await self.repo.create_student(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
        )
        await self.db.commit()
        return UserOut.model_validate(user)
