import asyncio
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.core.constants import (
    ALMATY_TZ,
    APPOINTMENT_STATUS_CONFIRMED,
    TASK_STATUS_DONE,
    TASK_STATUS_OVERDUE,
)
from app.database import AsyncSessionLocal
from app.modules.appointments.models import Appointment, AvailabilitySlot
from app.modules.notifications.service import NotificationsService
from app.modules.tasks.models import Task
from app.modules.users.models import User
from app.workers.celery_app import celery_app
from app.workers.email_tasks import send_email_task


async def _check_task_deadlines() -> None:
    now_utc = datetime.now(tz=timezone.utc)
    window_end = now_utc + timedelta(days=4)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task, User)
            .join(User, User.id == Task.student_id)
            .where(
                Task.deadline.isnot(None),
                Task.deadline >= now_utc,
                Task.deadline <= window_end,
                Task.status.notin_([TASK_STATUS_DONE, TASK_STATUS_OVERDUE]),
            )
        )
        rows = result.all()
        notifier = NotificationsService(db)
        today_local = datetime.now(ALMATY_TZ).date()

        for task, user in rows:
            deadline_local = task.deadline.astimezone(ALMATY_TZ)
            days_left = (deadline_local.date() - today_local).days
            if days_left not in (1, 3):
                continue

            title = "Task deadline reminder"
            body = f"Task '{task.title}' is due on {deadline_local:%Y-%m-%d}."
            await notifier.create_notification(
                user_id=user.id,
                notification_type="task_deadline",
                title=title,
                body=body,
                source_id=task.id,
                source_type="task",
            )
            if user.email:
                send_email_task.delay(
                    to=user.email,
                    subject="Task deadline reminder",
                    template="deadline_reminder.html",
                    context={
                        "full_name": user.full_name,
                        "task_title": task.title,
                        "deadline": deadline_local.strftime("%Y-%m-%d"),
                        "days_left": days_left,
                        "description": task.description or "",
                    },
                )

        await db.commit()


async def _send_appointment_reminders() -> None:
    now_local = datetime.now(ALMATY_TZ)
    window_target = now_local.replace(hour=8, minute=0, second=0, microsecond=0)
    if abs((now_local - window_target).total_seconds()) > 5 * 60:
        return
    start_local = datetime.combine(now_local.date(), time.min, tzinfo=ALMATY_TZ)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    Student = aliased(User)
    Adviser = aliased(User)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment, AvailabilitySlot, Student, Adviser)
            .join(AvailabilitySlot, AvailabilitySlot.id == Appointment.slot_id)
            .join(Student, Student.id == Appointment.student_id)
            .join(Adviser, Adviser.id == Appointment.adviser_id)
            .where(
                Appointment.status == APPOINTMENT_STATUS_CONFIRMED,
                AvailabilitySlot.start_time >= start_utc,
                AvailabilitySlot.start_time < end_utc,
            )
        )
        notifier = NotificationsService(db)

        for appt, slot, student, adviser in result.all():
            appt_time_local = slot.start_time.astimezone(ALMATY_TZ)
            body = f"Appointment at {appt_time_local:%Y-%m-%d %H:%M}."

            await notifier.create_notification(
                user_id=student.id,
                notification_type="appointment_reminder",
                title="Appointment reminder",
                body=body,
                source_id=appt.id,
                source_type="appointment",
            )
            await notifier.create_notification(
                user_id=adviser.id,
                notification_type="appointment_reminder",
                title="Appointment reminder",
                body=body,
                source_id=appt.id,
                source_type="appointment",
            )

            if student.email:
                send_email_task.delay(
                    to=student.email,
                    subject="Appointment reminder",
                    template="appointment_reminder.html",
                    context={
                        "full_name": student.full_name,
                        "appointment_time": appt_time_local.strftime("%Y-%m-%d %H:%M"),
                        "participant_name": adviser.full_name,
                    },
                )
            if adviser.email:
                send_email_task.delay(
                    to=adviser.email,
                    subject="Appointment reminder",
                    template="appointment_reminder.html",
                    context={
                        "full_name": adviser.full_name,
                        "appointment_time": appt_time_local.strftime("%Y-%m-%d %H:%M"),
                        "participant_name": student.full_name,
                    },
                )

        await db.commit()


@celery_app.task
def check_task_deadlines() -> None:
    asyncio.run(_check_task_deadlines())


@celery_app.task
def send_appointment_reminders() -> None:
    asyncio.run(_send_appointment_reminders())
