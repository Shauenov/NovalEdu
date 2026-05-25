from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.tasks.models import Task, TaskHistory


class TasksRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, task_id: UUID) -> Task | None:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update(self, task: Task, data: dict) -> Task:
        for key, value in data.items():
            setattr(task, key, value)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.flush()

    async def list_for_student(
        self,
        student_id: UUID,
        status: str | None = None,
        is_adviser_task: bool | None = None,
        student_roadmap_id: UUID | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Task], int]:
        stmt = select(Task).where(Task.student_id == student_id)
        if status:
            stmt = stmt.where(Task.status == status)
        if is_adviser_task is not None:
            stmt = stmt.where(Task.is_adviser_task == is_adviser_task)
        if student_roadmap_id is not None:
            stmt = stmt.where(Task.student_roadmap_id == student_roadmap_id)

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def mark_overdue_bulk(self) -> int:
        now = datetime.now(tz=timezone.utc)
        result = await self.db.execute(
            update(Task)
            .where(Task.status.notin_(["done", "overdue"]), Task.deadline < now, Task.deadline.isnot(None))
            .values(status="overdue")
        )
        return result.rowcount

    async def count_for_student(self, student_id: UUID) -> dict:
        result = await self.db.execute(
            select(Task.status, func.count()).where(Task.student_id == student_id).group_by(Task.status)
        )
        counts = dict(result.all())
        return {
            "total": sum(counts.values()),
            "done": counts.get("done", 0),
            "overdue": counts.get("overdue", 0),
        }

    # ── History ───────────────────────────────────────────────

    async def add_history(
        self,
        task_id: UUID,
        changed_by: UUID | None,
        event_type: str,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> TaskHistory:
        entry = TaskHistory(
            task_id=task_id,
            changed_by=changed_by,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_history(self, task_id: UUID) -> list[TaskHistory]:
        result = await self.db.execute(
            select(TaskHistory)
            .where(TaskHistory.task_id == task_id)
            .order_by(TaskHistory.created_at.asc())
        )
        return list(result.scalars().all())

    # ── Stats ─────────────────────────────────────────────────

    async def stats_for_month(self, student_id: UUID, year: int, month: int) -> dict:
        from sqlalchemy import extract
        stmt = select(Task.status, func.count()).where(
            Task.student_id == student_id,
            extract("year", Task.created_at) == year,
            extract("month", Task.created_at) == month,
        ).group_by(Task.status)
        result = await self.db.execute(stmt)
        counts = dict(result.all())
        total = sum(counts.values())
        completed = counts.get("done", 0)
        overdue = counts.get("overdue", 0)
        return {
            "total": total,
            "completed": completed,
            "overdue": overdue,
            "in_progress": counts.get("in_progress", 0),
            "todo": counts.get("todo", 0),
        }
