from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ALMATY_TZ, DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_CONDUCTOR, ROLE_STUDENT
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.tasks.repository import TasksRepository
from app.modules.tasks.schemas import TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate


class TasksService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TasksRepository(db)

    async def create_conductor_task(
        self,
        student_id: UUID,
        data: TaskCreate,
        created_by: UUID,
        requester_role: str,
    ) -> TaskOut:
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only conductor or admin can create tasks for students")

        task = await self.repo.create(
            student_id=student_id,
            created_by=created_by,
            title=data.title,
            description=data.description,
            priority=data.priority,
            task_type=data.task_type,
            deadline=data.deadline,
            time_from=data.time_from,
            time_to=data.time_to,
            location=data.location,
            reminder_minutes=data.reminder_minutes,
            student_roadmap_id=data.student_roadmap_id,
            is_conductor_task=True,
        )
        await self.db.commit()

        # Fire notification to student (lazy import to avoid circular dep)
        try:
            from app.modules.notifications.service import NotificationsService
            notif_svc = NotificationsService(self.db)
            await notif_svc.create_notification(
                user_id=student_id,
                notification_type="new_task",
                title="New task assigned",
                body=f"Conductor assigned: {data.title}",
                source_id=task.id,
                source_type="task",
            )
            await self.db.commit()
        except Exception:
            pass  # Notification failure must not break task creation

        try:
            from app.modules.users.repository import UsersRepository
            from app.workers.email_tasks import send_email_task

            user_repo = UsersRepository(self.db)
            student = await user_repo.get_by_id(student_id)
            creator = await user_repo.get_by_id(created_by)
            if student and student.email:
                deadline_local = None
                if data.deadline:
                    deadline_local = data.deadline.astimezone(ALMATY_TZ).strftime("%Y-%m-%d")

                send_email_task.delay(
                    to=student.email,
                    subject="New task assigned",
                    template="task_assigned.html",
                    context={
                        "full_name": student.full_name,
                        "task_title": data.title,
                        "deadline": deadline_local,
                        "description": data.description or "",
                        "assigned_by": creator.full_name if creator else "Conductor",
                    },
                )
        except Exception:
            pass

        return TaskOut.model_validate(task)

    async def create_personal_task(
        self,
        data: TaskCreate,
        student_id: UUID,
        requester_role: str,
    ) -> TaskOut:
        if requester_role != ROLE_STUDENT:
            raise ForbiddenException("Only students can create personal tasks")

        task = await self.repo.create(
            student_id=student_id,
            created_by=student_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            task_type=data.task_type,
            deadline=data.deadline,
            time_from=data.time_from,
            time_to=data.time_to,
            location=data.location,
            reminder_minutes=data.reminder_minutes,
            is_conductor_task=False,
        )
        await self.db.commit()
        return TaskOut.model_validate(task)

    async def get_task(self, task_id: UUID, requester_id: UUID, requester_role: str) -> TaskOut:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role == ROLE_STUDENT and task.student_id != requester_id:
            raise ForbiddenException("Access denied")
        return TaskOut.model_validate(task)

    async def update_task(
        self, task_id: UUID, data: TaskUpdate, requester_id: UUID, requester_role: str
    ) -> TaskOut:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only conductor or admin can update tasks")

        updated = await self.repo.update(task, data.model_dump(exclude_unset=True))
        await self.db.commit()
        return TaskOut.model_validate(updated)

    async def patch_status(
        self, task_id: UUID, data: TaskStatusUpdate, requester_id: UUID, requester_role: str
    ) -> TaskOut:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role == ROLE_STUDENT and task.student_id != requester_id:
            raise ForbiddenException("Students can only update their own tasks")

        update_data = {"status": data.status}
        if data.status == "done":
            update_data["completed_at"] = datetime.now(tz=timezone.utc)

        updated = await self.repo.update(task, update_data)
        await self.db.commit()

        # Notify conductor when student marks task done
        if data.status == "done":
            try:
                from app.modules.notifications.service import NotificationsService
                notif_svc = NotificationsService(self.db)
                await notif_svc.create_notification(
                    user_id=task.created_by,
                    notification_type="new_task",
                    title="Task completed",
                    body=f"Student completed task: {task.title}",
                    source_id=task.id,
                    source_type="task",
                )
                await self.db.commit()
            except Exception:
                pass

        return TaskOut.model_validate(updated)

    async def delete_task(
        self, task_id: UUID, requester_id: UUID, requester_role: str
    ) -> None:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role not in (ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only conductor or admin can delete tasks")
        await self.repo.delete(task)
        await self.db.commit()

    async def get_task_stats(
        self,
        student_id: UUID,
        requester_id: UUID,
        requester_role: str,
        month: str | None = None,
    ) -> dict:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own stats")

        if month:
            try:
                year, mon = int(month[:4]), int(month[5:7])
            except (ValueError, IndexError):
                raise ValueError("month must be in YYYY-MM format")
            return await self.repo.stats_for_month(student_id, year, mon)

        return await self.repo.count_for_student(student_id)

    async def list_student_tasks(
        self,
        student_id: UUID,
        requester_id: UUID,
        requester_role: str,
        status: str | None = None,
        is_conductor_task: bool | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[TaskOut], int]:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own tasks")

        tasks, total = await self.repo.list_for_student(
            student_id=student_id,
            status=status,
            is_conductor_task=is_conductor_task,
            page=page,
            page_size=page_size,
        )
        return [TaskOut.model_validate(t) for t in tasks], total
