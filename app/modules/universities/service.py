from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_CONDUCTOR
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.universities.repository import UniversitiesRepository
from app.modules.universities.schemas import UniversityCreate, UniversityUpdate, UniversityProgramCreate, UniversityProgramUpdate


class UniversitiesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UniversitiesRepository(db)

    async def list_universities(
        self,
        requester_role: str,
        country: str | None = None,
        field: str | None = None,
        min_gpa: float | None = None,
        max_tuition: int | None = None,
        degree_level: str | None = None,
        has_scholarship: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_CONDUCTOR)
        return await self.repo.list_universities(
            country=country,
            field=field,
            min_gpa=min_gpa,
            max_tuition=max_tuition,
            degree_level=degree_level,
            has_scholarship=has_scholarship,
            search=search,
            include_unpublished=include_unpublished,
            page=page,
            page_size=page_size,
        )

    async def get_university_detail(self, university_id: UUID, requester_role: str):
        university = await self.repo.get_by_id(university_id)
        if not university:
            raise NotFoundException("University not found")
        if not university.is_published and requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise NotFoundException("University not found")
        programs = await self.repo.list_programs(university_id, only_active=True)
        return university, programs

    async def create_university(self, data: UniversityCreate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can create universities")
        uni = await self.repo.create_university(**data.model_dump())
        await self.db.commit()
        return uni

    async def update_university(self, university_id: UUID, data: UniversityUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can update universities")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        updated = await self.repo.update_university(uni, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_university(self, university_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can delete universities")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        await self.repo.update_university(uni, {"is_published": False})
        await self.db.commit()

    async def create_program(self, university_id: UUID, data: UniversityProgramCreate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can add programs")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        program = await self.repo.create_program(university_id=university_id, **data.model_dump())
        await self.db.commit()
        return program

    async def update_program(self, university_id: UUID, program_id: UUID, data: UniversityProgramUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can update programs")
        program = await self.repo.get_program(program_id)
        if not program or program.university_id != university_id:
            raise NotFoundException("Program not found")
        updated = await self.repo.update_program(program, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_program(self, university_id: UUID, program_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can delete programs")
        program = await self.repo.get_program(program_id)
        if not program or program.university_id != university_id:
            raise NotFoundException("Program not found")
        await self.repo.update_program(program, {"is_active": False})
        await self.db.commit()
