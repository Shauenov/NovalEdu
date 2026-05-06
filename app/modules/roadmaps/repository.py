from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.roadmaps.models import Roadmap, RoadmapTemplateTask, StudentRoadmap


class RoadmapsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        result = await self.db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
        return result.scalar_one_or_none()

    async def list_roadmaps(
        self,
        include_unpublished: bool = False,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Roadmap], int]:
        stmt = select(Roadmap)
        if not include_unpublished:
            stmt = stmt.where(Roadmap.is_public == True)
        stmt = stmt.order_by(Roadmap.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def create_roadmap(self, **kwargs) -> Roadmap:
        roadmap = Roadmap(**kwargs)
        self.db.add(roadmap)
        await self.db.flush()
        await self.db.refresh(roadmap)
        return roadmap

    async def update_roadmap(self, roadmap: Roadmap, data: dict) -> Roadmap:
        for key, value in data.items():
            if value is not None:
                setattr(roadmap, key, value)
        await self.db.flush()
        await self.db.refresh(roadmap)
        return roadmap

    async def list_template_tasks(self, roadmap_id: UUID) -> list[RoadmapTemplateTask]:
        result = await self.db.execute(
            select(RoadmapTemplateTask)
            .where(RoadmapTemplateTask.roadmap_id == roadmap_id)
            .order_by(RoadmapTemplateTask.order_index.asc())
        )
        return result.scalars().all()

    async def get_template_task(self, task_id: UUID) -> RoadmapTemplateTask | None:
        result = await self.db.execute(select(RoadmapTemplateTask).where(RoadmapTemplateTask.id == task_id))
        return result.scalar_one_or_none()

    async def create_template_task(self, **kwargs) -> RoadmapTemplateTask:
        task = RoadmapTemplateTask(**kwargs)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def create_student_roadmap(self, **kwargs) -> StudentRoadmap:
        item = StudentRoadmap(**kwargs)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def list_student_roadmaps(self, student_id: UUID) -> list[StudentRoadmap]:
        result = await self.db.execute(
            select(StudentRoadmap)
            .where(StudentRoadmap.student_id == student_id)
            .order_by(StudentRoadmap.assigned_at.desc())
        )
        return result.scalars().all()
