from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.tasks.models import Task


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
        is_conductor_task: bool | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Task], int]:
        stmt = select(Task).where(Task.student_id == student_id)
        if status:
            stmt = stmt.where(Task.status == status)
        if is_conductor_task is not None:
            stmt = stmt.where(Task.is_conductor_task == is_conductor_task)

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
