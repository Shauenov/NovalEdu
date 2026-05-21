from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ROLE_STUDENT, TASK_STATUS_DONE
from app.modules.appointments.models import Appointment
from app.modules.profile.models import StudentProfile
from app.modules.tasks.models import Task
from app.modules.users.models import User


class ReportsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview_stats(self) -> dict:
        total_students = (
            await self.db.execute(
                select(func.count()).select_from(User).where(User.role == ROLE_STUDENT, User.is_active == True)
            )
        ).scalar_one()

        by_group_rows = (
            await self.db.execute(
                select(StudentProfile.group_type, func.count())
                .join(User, User.id == StudentProfile.user_id)
                .where(User.role == ROLE_STUDENT, User.is_active == True)
                .group_by(StudentProfile.group_type)
            )
        ).all()
        by_group = {row[0]: row[1] for row in by_group_rows if row[0]}

        ielts_passed = (
            await self.db.execute(
                select(func.count())
                .select_from(StudentProfile)
                .join(User, User.id == StudentProfile.user_id)
                .where(User.role == ROLE_STUDENT, User.is_active == True, StudentProfile.ielts_passed == True)
            )
        ).scalar_one()

        sat_passed = (
            await self.db.execute(
                select(func.count())
                .select_from(StudentProfile)
                .join(User, User.id == StudentProfile.user_id)
                .where(User.role == ROLE_STUDENT, User.is_active == True, StudentProfile.sat_passed == True)
            )
        ).scalar_one()

        avg_gpa = (
            await self.db.execute(
                select(func.avg(StudentProfile.gpa))
                .join(User, User.id == StudentProfile.user_id)
                .where(User.role == ROLE_STUDENT, User.is_active == True)
            )
        ).scalar_one()
        avg_gpa_value = float(avg_gpa) if avg_gpa is not None else None

        now = datetime.now(tz=timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        next_month = datetime(now.year + (1 if now.month == 12 else 0), (now.month % 12) + 1, 1, tzinfo=timezone.utc)

        tasks_completed_this_month = (
            await self.db.execute(
                select(func.count())
                .select_from(Task)
                .where(Task.status == TASK_STATUS_DONE, Task.completed_at >= month_start, Task.completed_at < next_month)
            )
        ).scalar_one()

        appointments_this_month = (
            await self.db.execute(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.created_at >= month_start, Appointment.created_at < next_month)
            )
        ).scalar_one()

        applied_abroad = (
            await self.db.execute(
                select(func.count())
                .select_from(StudentProfile)
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    User.role == ROLE_STUDENT,
                    User.is_active == True,
                    StudentProfile.target_country.isnot(None),
                    StudentProfile.target_country != "Kazakhstan",
                )
            )
        ).scalar_one()

        total_budget_raw = (
            await self.db.execute(
                select(func.coalesce(func.sum(StudentProfile.budget_max), 0))
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    User.role == ROLE_STUDENT,
                    User.is_active == True,
                    StudentProfile.budget_max.isnot(None),
                )
            )
        ).scalar_one()
        total_budget_usd = int(total_budget_raw) if total_budget_raw else 0

        return {
            "total_students": total_students,
            "by_group": by_group,
            "ielts_passed": ielts_passed,
            "sat_passed": sat_passed,
            "avg_gpa": avg_gpa_value,
            "tasks_completed_this_month": tasks_completed_this_month,
            "appointments_this_month": appointments_this_month,
            "applied_abroad": applied_abroad,
            "total_budget_usd": total_budget_usd,
        }

    async def students_progress(self) -> list[dict]:
        task_counts = (
            select(
                Task.student_id.label("student_id"),
                func.count().label("tasks_total"),
                func.sum(case((Task.status == "done", 1), else_=0)).label("tasks_done"),
                func.sum(case((Task.status == "overdue", 1), else_=0)).label("tasks_overdue"),
            )
            .group_by(Task.student_id)
            .subquery()
        )

        result = await self.db.execute(
            select(
                User.id,
                User.full_name,
                StudentProfile.group_type,
                StudentProfile.course_year,
                StudentProfile.gpa,
                StudentProfile.ielts_passed,
                StudentProfile.sat_passed,
                task_counts.c.tasks_total,
                task_counts.c.tasks_done,
                task_counts.c.tasks_overdue,
            )
            .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
            .join(task_counts, task_counts.c.student_id == User.id, isouter=True)
            .where(User.role == ROLE_STUDENT, User.is_active == True)
            .order_by(User.full_name.asc())
        )

        rows = result.all()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row[0],
                    "full_name": row[1],
                    "group_type": row[2],
                    "course_year": row[3],
                    "gpa": float(row[4]) if row[4] is not None else None,
                    "ielts_passed": row[5] or False,
                    "sat_passed": row[6] or False,
                    "tasks_total": row[7] or 0,
                    "tasks_done": row[8] or 0,
                    "tasks_overdue": row[9] or 0,
                }
            )
        return items

    async def universities_stats(self) -> dict:
        country_rows = (
            await self.db.execute(
                select(StudentProfile.target_country, func.count())
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    User.role == ROLE_STUDENT,
                    User.is_active == True,
                    StudentProfile.target_country.isnot(None),
                )
                .group_by(StudentProfile.target_country)
            )
        ).all()
        by_country = {row[0]: row[1] for row in country_rows if row[0]}

        major_rows = (
            await self.db.execute(
                select(StudentProfile.target_major, func.count())
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    User.role == ROLE_STUDENT,
                    User.is_active == True,
                    StudentProfile.target_major.isnot(None),
                )
                .group_by(StudentProfile.target_major)
            )
        ).all()
        by_major = {row[0]: row[1] for row in major_rows if row[0]}

        return {
            "by_target_country": by_country,
            "by_target_major": by_major,
        }
