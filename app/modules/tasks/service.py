from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ALMATY_TZ, DEFAULT_PAGE_SIZE, ROLE_ADMIN, ROLE_ADVISER, ROLE_STUDENT
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.tasks.repository import TasksRepository
from app.modules.tasks.schemas import TaskCreate, TaskHistoryOut, TaskHistoryResponse, TaskOut, TaskStatusUpdate, TaskUpdate


class TasksService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TasksRepository(db)

    async def create_adviser_task(
        self,
        student_id: UUID,
        data: TaskCreate,
        created_by: UUID,
        requester_role: str,
    ) -> TaskOut:
        if requester_role not in (ROLE_ADVISER, ROLE_ADMIN):
            raise ForbiddenException("Only ADVISER or admin can create tasks for students")

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
            is_adviser_task=True,
        )
        await self.repo.add_history(task.id, created_by, "created", new_value=data.title)
        await self.db.commit()

        # Fire notification to student (lazy import to avoid circular dep)
        try:
            from app.modules.notifications.service import NotificationsService
            notif_svc = NotificationsService(self.db)
            await notif_svc.create_notification(
                user_id=student_id,
                notification_type="new_task",
                title="New task assigned",
                body=f"Adviser assigned: {data.title}",
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
                        "assigned_by": creator.full_name if creator else "Adviser",
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
            is_adviser_task=False,
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
        if requester_role not in (ROLE_ADVISER, ROLE_ADMIN):
            raise ForbiddenException("Only ADVISER or admin can update tasks")

        changed_fields = data.model_dump(exclude_unset=True)
        updated = await self.repo.update(task, changed_fields)
        summary = ", ".join(f"{k}={v}" for k, v in changed_fields.items() if k not in ("time_from", "time_to"))
        await self.repo.add_history(task_id, requester_id, "updated", new_value=summary[:300] if summary else None)
        await self.db.commit()

        # Notify student that their task was updated
        try:
            from app.modules.notifications.service import NotificationsService
            from app.modules.users.repository import UsersRepository
            from app.workers.email_tasks import send_email_task

            notif_svc = NotificationsService(self.db)
            await notif_svc.create_notification(
                user_id=task.student_id,
                notification_type="task_updated",
                title="Task updated",
                body=f"Your task '{task.title}' was updated by your adviser",
                source_id=task.id,
                source_type="task",
            )
            await self.db.commit()

            user_repo = UsersRepository(self.db)
            student = await user_repo.get_by_id(task.student_id)
            if student and student.email:
                deadline_local = None
                if updated.deadline:
                    deadline_local = updated.deadline.astimezone(ALMATY_TZ).strftime("%Y-%m-%d")
                send_email_task.delay(
                    to=student.email,
                    subject="Task updated",
                    template="task_updated.html",
                    context={
                        "full_name": student.full_name,
                        "task_title": task.title,
                        "deadline": deadline_local,
                        "description": updated.description or "",
                    },
                )
        except Exception:
            pass

        return TaskOut.model_validate(updated)

    async def patch_status(
        self, task_id: UUID, data: TaskStatusUpdate, requester_id: UUID, requester_role: str
    ) -> TaskOut:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role == ROLE_STUDENT and task.student_id != requester_id:
            raise ForbiddenException("Students can only update their own tasks")

        old_status = task.status
        update_data = {"status": data.status}
        if data.status == "done":
            update_data["completed_at"] = datetime.now(tz=timezone.utc)

        updated = await self.repo.update(task, update_data)
        await self.repo.add_history(
            task_id, requester_id, "status_changed",
            old_value=old_status, new_value=data.status,
        )
        await self.db.commit()

        # Notify ADVISER when student marks task done
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
        if requester_role not in (ROLE_ADVISER, ROLE_ADMIN):
            raise ForbiddenException("Only ADVISER or admin can delete tasks")
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

    async def get_history(self, task_id: UUID, requester_id: UUID, requester_role: str) -> TaskHistoryResponse:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task not found")
        if requester_role == ROLE_STUDENT and task.student_id != requester_id:
            raise ForbiddenException("Access denied")
        entries = await self.repo.list_history(task_id)
        return TaskHistoryResponse(data=[TaskHistoryOut.model_validate(e) for e in entries])

    async def list_student_tasks(
        self,
        student_id: UUID,
        requester_id: UUID,
        requester_role: str,
        status: str | None = None,
        is_adviser_task: bool | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[TaskOut], int]:
        if requester_role == ROLE_STUDENT and requester_id != student_id:
            raise ForbiddenException("Students can only view their own tasks")

        tasks, total = await self.repo.list_for_student(
            student_id=student_id,
            status=status,
            is_adviser_task=is_adviser_task,
            page=page,
            page_size=page_size,
        )
        return [TaskOut.model_validate(t) for t in tasks], total
