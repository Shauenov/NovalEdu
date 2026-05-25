from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_ADVISER, ROLE_STUDENT
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.modules.calendar.repository import CalendarRepository
from app.modules.calendar.schemas import CalendarEventCreate
from app.modules.enrollments.repository import EnrollmentsRepository
from app.modules.notifications.service import NotificationsService
from app.modules.roadmaps.repository import RoadmapsRepository
from app.modules.roadmaps.schemas import RoadmapCreate, RoadmapUpdate, AssignRequest
from app.modules.tasks.repository import TasksRepository


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
        include_unpublished = requester_role in (ROLE_ADMIN, ROLE_ADVISER)
        return await self.repo.list_roadmaps(include_unpublished, page, page_size)

    async def get_roadmap_detail(self, roadmap_id: UUID, requester_role: str):
        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")
        if not roadmap.is_public and requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise NotFoundException("Roadmap not found")
        tasks = await self.repo.list_template_tasks(roadmap_id)
        return roadmap, tasks

    async def create_roadmap(self, data: RoadmapCreate, created_by: UUID, requester_role: str):
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can create roadmaps")

        roadmap = await self.repo.create_roadmap(
            title=data.title,
            description=data.description,
            target_type=data.target_type,
            is_public=data.is_public,
            university_id=data.university_id,
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
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can update roadmaps")
        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")
        # Allow explicitly clearing university_id (pass None)
        update_data = data.model_dump(exclude_unset=True)
        updated = await self.repo.update_roadmap(roadmap, update_data)
        await self.db.commit()
        return updated

    async def delete_roadmap(self, roadmap_id: UUID, requester_role: str) -> None:
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can delete roadmaps")
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
        if requester_role not in (ROLE_ADMIN, ROLE_ADVISER):
            raise ForbiddenException("Only adviser or admin can assign roadmaps")

        roadmap = await self.repo.get_by_id(roadmap_id)
        if not roadmap:
            raise NotFoundException("Roadmap not found")

        # ── 1. Pre-compute & validate EVERY deadline before any DB write, so an
        #       invalid deadline can never leave behind a half-created assignment.
        template_tasks = await self.repo.list_template_tasks(roadmap.id)
        overrides = {t.template_task_id: t.deadline for t in data.customize_tasks}
        now = datetime.now(tz=timezone.utc)
        planned: list[tuple] = []
        for tmpl in template_tasks:
            deadline = overrides.get(tmpl.id)
            if deadline is not None:
                # Custom deadline chosen by the adviser must be in the future.
                if deadline <= now:
                    raise ValidationException("Task deadline must be in the future")
            elif tmpl.days_offset is not None:
                # Auto-computed from the template; days_offset 0 means "due today".
                # Keep it strictly in the future so the task is always valid.
                deadline = now + timedelta(days=tmpl.days_offset)
                if deadline <= now:
                    deadline = now + timedelta(days=1)
            planned.append((tmpl, deadline))

        # ── 2. All DB writes happen in a SINGLE transaction. Repositories only
        #       flush; the one commit below makes the whole assignment atomic —
        #       if anything fails, nothing is persisted (no orphan roadmaps).
        tasks_repo = TasksRepository(self.db)
        calendar_repo = CalendarRepository(self.db)
        enroll_repo = EnrollmentsRepository(self.db)

        student_roadmap = await self.repo.create_student_roadmap(
            student_id=data.student_id,
            roadmap_id=roadmap.id,
            assigned_by=assigned_by,
            title=roadmap.title,
        )

        # Auto-enroll student in the linked university (if any)
        if roadmap.university_id:
            existing = await enroll_repo.get_by_student_and_university(
                data.student_id, roadmap.university_id
            )
            if not existing:
                await enroll_repo.create(
                    student_id=data.student_id,
                    university_id=roadmap.university_id,
                    status="selected",
                    progress=0,
                )

        created_tasks = []
        for tmpl, deadline in planned:
            task = await tasks_repo.create(
                student_id=data.student_id,
                created_by=assigned_by,
                title=tmpl.title,
                description=tmpl.description,
                deadline=deadline,
                student_roadmap_id=student_roadmap.id,
                is_adviser_task=True,
            )
            await tasks_repo.add_history(task.id, assigned_by, "created", new_value=tmpl.title)
            if deadline is not None:
                event = CalendarEventCreate(
                    title=task.title,
                    description=task.description,
                    event_type="task_deadline",
                    start_time=deadline,
                    end_time=None,
                    all_day=True,
                    color=None,
                    source_id=task.id,
                    source_type="task",
                )
                await calendar_repo.create(user_id=data.student_id, **event.model_dump())
            created_tasks.append(task)

        # Single commit — everything above succeeds or rolls back together.
        await self.db.commit()

        # ── 3. Best-effort side effects AFTER commit (never affect integrity). ──
        try:
            notifier = NotificationsService(self.db)
            await notifier.create_notification(
                user_id=data.student_id,
                notification_type="roadmap_assigned",
                title="New roadmap assigned",
                body=f"Roadmap '{roadmap.title}' was assigned to you ({len(created_tasks)} tasks)",
                source_id=student_roadmap.id,
                source_type="roadmap",
            )
            await self.db.commit()

            from app.modules.users.repository import UsersRepository
            from app.workers.email_tasks import send_email_task
            user_repo = UsersRepository(self.db)
            student = await user_repo.get_by_id(data.student_id)
            if student and student.email:
                send_email_task.delay(
                    to=student.email,
                    subject="New roadmap assigned",
                    template="roadmap_assigned.html",
                    context={
                        "full_name": student.full_name,
                        "roadmap_title": roadmap.title,
                        "description": roadmap.description or "",
                    },
                )
        except Exception:
            pass

        return student_roadmap

    async def list_student_roadmaps(self, student_id: UUID, requester_id: UUID, requester_role: str):
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own roadmaps")
        return await self.repo.list_student_roadmaps_with_progress(student_id)

    async def get_my_roadmaps(self, student_id: UUID) -> list[dict]:
        """Student-facing: each assigned roadmap with progress + its stages (tasks),
        ready to render the mobile 'My roadmap' screen in a single call."""
        rows = await self.repo.list_student_roadmaps_with_progress(student_id)
        tasks_repo = TasksRepository(self.db)
        out: list[dict] = []
        for sr, progress in rows:
            tasks, _ = await tasks_repo.list_for_student(
                student_id=student_id,
                student_roadmap_id=sr.id,
                page=1,
                page_size=500,
            )
            tasks = sorted(
                tasks,
                key=lambda t: (t.deadline is None, t.deadline or datetime.max.replace(tzinfo=timezone.utc)),
            )
            out.append({
                "id": sr.id,
                "roadmap_id": sr.roadmap_id,
                "title": sr.title,
                "assigned_at": sr.assigned_at,
                "is_active": sr.is_active,
                "progress": progress,
                "stages": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status,
                        "deadline": t.deadline,
                        "is_adviser_task": t.is_adviser_task,
                    }
                    for t in tasks
                ],
            })
        return out
