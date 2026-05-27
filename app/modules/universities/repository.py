from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.universities.models import University, UniversityProgram


class UniversitiesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, university_id: UUID) -> University | None:
        result = await self.db.execute(select(University).where(University.id == university_id))
        return result.scalar_one_or_none()

    async def list_universities(
        self,
        country: str | None = None,
        is_abroad: bool | None = None,
        field: str | None = None,
        min_gpa: float | None = None,
        max_tuition: int | None = None,
        degree_level: str | None = None,
        has_scholarship: bool | None = None,
        search: str | None = None,
        include_unpublished: bool = False,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[University], int]:
        stmt = select(University)

        if not include_unpublished:
            stmt = stmt.where(University.is_published == True)

        if country:
            stmt = stmt.where(University.country == country)
        elif is_abroad is True:
            stmt = stmt.where(University.country != 'Kazakhstan')
        elif is_abroad is False:
            stmt = stmt.where(University.country == 'Kazakhstan')
        if search:
            stmt = stmt.where(University.name.ilike(f"%{search}%"))

        needs_program_join = any([field, min_gpa is not None, max_tuition is not None, degree_level, has_scholarship is not None])
        if needs_program_join:
            stmt = stmt.join(UniversityProgram, UniversityProgram.university_id == University.id)

            if field:
                stmt = stmt.where(UniversityProgram.field.ilike(f"%{field}%"))
            if degree_level:
                stmt = stmt.where(UniversityProgram.degree_level == degree_level)
            if min_gpa is not None:
                stmt = stmt.where(or_(UniversityProgram.min_gpa <= min_gpa, UniversityProgram.min_gpa.is_(None)))
            if max_tuition is not None:
                stmt = stmt.where(or_(UniversityProgram.tuition_usd <= max_tuition, UniversityProgram.tuition_usd.is_(None)))
            if has_scholarship is True:
                stmt = stmt.where(
                    UniversityProgram.scholarship_info.isnot(None),
                    UniversityProgram.scholarship_info != "",
                )
            if has_scholarship is False:
                stmt = stmt.where(
                    or_(UniversityProgram.scholarship_info.is_(None), UniversityProgram.scholarship_info == "")
                )

        stmt = stmt.distinct().order_by(University.name.asc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def list_published_with_programs(
        self,
    ) -> list[tuple[University, list[UniversityProgram]]]:
        """All published universities, each paired with its active programs."""
        unis = (
            await self.db.execute(select(University).where(University.is_published == True))
        ).scalars().all()
        if not unis:
            return []
        uni_ids = [u.id for u in unis]
        progs = (
            await self.db.execute(
                select(UniversityProgram).where(
                    UniversityProgram.university_id.in_(uni_ids),
                    UniversityProgram.is_active == True,
                )
            )
        ).scalars().all()
        by_uni: dict = {}
        for p in progs:
            by_uni.setdefault(p.university_id, []).append(p)
        return [(u, by_uni.get(u.id, [])) for u in unis]

    async def create_university(self, **kwargs) -> University:
        university = University(**kwargs)
        self.db.add(university)
        await self.db.flush()
        await self.db.refresh(university)
        return university

    async def update_university(self, university: University, data: dict) -> University:
        for key, value in data.items():
            if value is not None:
                setattr(university, key, value)
        await self.db.flush()
        await self.db.refresh(university)
        return university

    async def list_programs(self, university_id: UUID, only_active: bool = True) -> list[UniversityProgram]:
        stmt = select(UniversityProgram).where(UniversityProgram.university_id == university_id)
        if only_active:
            stmt = stmt.where(UniversityProgram.is_active == True)
        result = await self.db.execute(stmt.order_by(UniversityProgram.created_at.desc()))
        return result.scalars().all()

    async def get_program(self, program_id: UUID) -> UniversityProgram | None:
        result = await self.db.execute(select(UniversityProgram).where(UniversityProgram.id == program_id))
        return result.scalar_one_or_none()

    async def create_program(self, **kwargs) -> UniversityProgram:
        program = UniversityProgram(**kwargs)
        self.db.add(program)
        await self.db.flush()
        await self.db.refresh(program)
        return program

    async def update_program(self, program: UniversityProgram, data: dict) -> UniversityProgram:
        for key, value in data.items():
            if value is not None:
                setattr(program, key, value)
        await self.db.flush()
        await self.db.refresh(program)
        return program
