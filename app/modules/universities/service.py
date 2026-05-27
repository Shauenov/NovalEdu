import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_ADVISER
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.profile.repository import ProfileRepository
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
        is_abroad: bool | None = None,
        field: str | None = None,
        min_gpa: float | None = None,
        max_tuition: int | None = None,
        degree_level: str | None = None,
        has_scholarship: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_ADVISER)
        return await self.repo.list_universities(
            country=country,
            is_abroad=is_abroad,
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

    async def recommend_for_student(
        self, student_id: UUID, limit: int = 10
    ) -> list[tuple[object, int]]:
        """Score published universities against the student's profile and return
        them with a match_score (0-100), highest first.

        Weights: country 30, GPA 25, IELTS 20, budget 15, SAT 10. A missing
        requirement (or no preference) counts as "no barrier" → points awarded.
        """
        profile = await ProfileRepository(self.db).get_by_user_id(student_id)
        rows = await self.repo.list_published_with_programs()

        s_gpa = float(profile.gpa) if profile and profile.gpa is not None else None
        s_ielts = float(profile.ielts_score) if profile and profile.ielts_score is not None else None
        s_sat = profile.sat_score if profile else None
        s_budget = profile.budget_max if profile else None

        countries: set[str] = set()
        if profile:
            if profile.target_country:
                countries.add(profile.target_country.strip().lower())
            if profile.target_countries:
                try:
                    for c in json.loads(profile.target_countries):
                        countries.add(str(c).strip().lower())
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

        scored: list[tuple[object, int]] = []
        for uni, programs in rows:
            if not countries:
                country_score = 30
            else:
                country_score = 30 if (uni.country or "").strip().lower() in countries else 0

            best_academic = 0
            for p in (programs or [None]):
                sc = 0
                # GPA (25)
                if p is None or p.min_gpa is None:
                    sc += 25
                elif s_gpa is not None and s_gpa >= float(p.min_gpa):
                    sc += 25
                # IELTS (20)
                if p is None or p.min_ielts is None:
                    sc += 20
                elif s_ielts is not None and s_ielts >= float(p.min_ielts):
                    sc += 20
                # Budget (15)
                if p is None or p.tuition_usd is None:
                    sc += 15
                elif s_budget is not None and p.tuition_usd <= s_budget:
                    sc += 15
                # SAT (10)
                if p is None or p.min_sat is None:
                    sc += 10
                elif s_sat is not None and s_sat >= p.min_sat:
                    sc += 10
                best_academic = max(best_academic, sc)

            scored.append((uni, min(country_score + best_academic, 100)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    async def get_university_detail(self, university_id: UUID, requester_role: str):
        university = await self.repo.get_by_id(university_id)
        if not university:
            raise NotFoundException("University not found")
        if not university.is_published and requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise NotFoundException("University not found")
        programs = await self.repo.list_programs(university_id, only_active=True)
        return university, programs

    async def create_university(self, data: UniversityCreate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can create universities")
        uni = await self.repo.create_university(**data.model_dump())
        await self.db.commit()
        return uni

    async def update_university(self, university_id: UUID, data: UniversityUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can update universities")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        updated = await self.repo.update_university(uni, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_university(self, university_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can delete universities")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        await self.repo.update_university(uni, {"is_published": False})
        await self.db.commit()

    async def create_program(self, university_id: UUID, data: UniversityProgramCreate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can add programs")
        uni = await self.repo.get_by_id(university_id)
        if not uni:
            raise NotFoundException("University not found")
        program = await self.repo.create_program(university_id=university_id, **data.model_dump())
        await self.db.commit()
        return program

    async def update_program(self, university_id: UUID, program_id: UUID, data: UniversityProgramUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can update programs")
        program = await self.repo.get_program(program_id)
        if not program or program.university_id != university_id:
            raise NotFoundException("Program not found")
        updated = await self.repo.update_program(program, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_program(self, university_id: UUID, program_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can delete programs")
        program = await self.repo.get_program(program_id)
        if not program or program.university_id != university_id:
            raise NotFoundException("Program not found")
        await self.repo.update_program(program, {"is_active": False})
        await self.db.commit()
