from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_CONDUCTOR, ROLE_STUDENT
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.modules.calendar.schemas import CalendarEventCreate
from app.modules.calendar.service import CalendarService
from app.modules.notifications.service import NotificationsService
from app.modules.roadmaps.repository import RoadmapsRepository
from app.modules.roadmaps.schemas import RoadmapCreate, RoadmapUpdate, AssignRequest
from app.modules.tasks.schemas import TaskCreate
from app.modules.tasks.service import TasksService


class RoadmapsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RoadmapsRepository(db)

    async def list_roadmaps(
        self,
        requester_role: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_CONDUCTOR)
        return await self.repo.list_roadmaps(include_unpublished, page, page_size)

    async def get_roadmap_detail(self, roadmap_id: UUID, requester_role: str):
        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")
        if not roadmap.is_public and requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise NotFoundException("Roadmap not found")
        tasks = await self.repo.list_template_tasks(roadmap_id)
        return roadmap, tasks

    async def create_roadmap(self, data: RoadmapCreate, created_by: UUID, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can create roadmaps")

        roadmap = await self.repo.create_roadmap(
            title=data.title,
            description=data.description,
            target_type=data.target_type,
            is_public=data.is_public,
            created_by=created_by,
        )

        for task in data.template_tasks:
            await self.repo.create_template_task(
                roadmap_id=roadmap.id,
                title=task.title,
                description=task.description,
                order_index=task.order_index,
                days_offset=task.days_offset,
            )

        await self.db.commit()
        return roadmap

    async def update_roadmap(self, roadmap_id: UUID, data: RoadmapUpdate, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can update roadmaps")
        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")
        updated = await self.repo.update_roadmap(roadmap, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return updated

    async def delete_roadmap(self, roadmap_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can delete roadmaps")
        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")
        await self.repo.update_roadmap(roadmap, {"is_public": False})
        await self.db.commit()

    async def assign_roadmap(
        self,
        roadmap_id: UUID,
        data: AssignRequest,
        assigned_by: UUID,
        requester_role: str,
    ):
        if requester_role not in (ROLE_ADMIN, ROLE_CONDUCTOR):
            raise ForbiddenException("Only conductor or admin can assign roadmaps")

        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")

        student_roadmap = await self.repo.create_student_roadmap(
            student_id=data.student_id,
            roadmap_id=roadmap.id,
            assigned_by=assigned_by,
            title=roadmap.title,
        )
        await self.db.commit()

        template_tasks = await self.repo.list_template_tasks(roadmap.id)
        overrides = {t.template_task_id: t.deadline for t in data.customize_tasks}
        now = datetime.now(tz=timezone.utc)

        tasks_service = TasksService(self.db)
        calendar_service = CalendarService(self.db)

        for tmpl in template_tasks:
            deadline = overrides.get(tmpl.id)
            if deadline is None and tmpl.days_offset is not None:
                deadline = now + timedelta(days=tmpl.days_offset)

            if deadline is not None and deadline <= now:
                raise ValidationException("Task deadline must be in the future")

            task_data = TaskCreate(
                title=tmpl.title,
                description=tmpl.description,
                deadline=deadline,
                student_roadmap_id=student_roadmap.id,
            )

            task = await tasks_service.create_conductor_task(
                student_id=data.student_id,
                data=task_data,
                created_by=assigned_by,
                requester_role=requester_role,
            )

            if deadline:
                await calendar_service.create_event(
                    data.student_id,
                    CalendarEventCreate(
                        title=task.title,
                        description=task.description,
                        event_type="task_deadline",
                        start_time=deadline,
                        end_time=None,
                        all_day=True,
                        color=None,
                        source_id=task.id,
                        source_type="task",
                    ),
                )

        try:
            notifier = NotificationsService(self.db)
            await notifier.create_notification(
                user_id=data.student_id,
                notification_type="roadmap_assigned",
                title="New roadmap assigned",
                body=f"Roadmap '{roadmap.title}' was assigned to you",
                source_id=student_roadmap.id,
                source_type="roadmap",
            )
            await self.db.commit()
        except Exception:
            pass

        return student_roadmap

    async def list_student_roadmaps(self, student_id: UUID, requester_id: UUID, requester_role: str):
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own roadmaps")
        return await self.repo.list_student_roadmaps(student_id)
