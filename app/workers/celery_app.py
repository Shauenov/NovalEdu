from celery import Celery
from celery.schedules import crontab
from app.config import settings


def make_celery() -> Celery:
    app = Celery(
        "app.workers",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "app.workers.email_tasks",
            "app.workers.reminder_tasks",
            "app.workers.maintenance_tasks",
        ],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Almaty",
        enable_utc=False,
        task_track_started=True,
        worker_send_task_events=True,
        beat_schedule={
            "task-deadline-reminders": {
                "task": "app.workers.reminder_tasks.check_task_deadlines",
                "schedule": crontab(hour=8, minute=0),
            },
            "appointment-reminders": {
                "task": "app.workers.reminder_tasks.send_appointment_reminders",
                "schedule": crontab(minute=0),
            },
            "mark-overdue-tasks": {
                "task": "app.workers.maintenance_tasks.mark_overdue_tasks",
                "schedule": crontab(hour=0, minute=15),
            },
            "cleanup-expired-tokens": {
                "task": "app.workers.maintenance_tasks.cleanup_expired_tokens",
                "schedule": crontab(hour=0, minute=30),
            },
            "check-university-staleness": {
                "task": "app.workers.maintenance_tasks.check_university_staleness",
                "schedule": crontab(day_of_week="mon", hour=9, minute=0),
            },
        },
    )

    return app


celery_app = make_celery()
