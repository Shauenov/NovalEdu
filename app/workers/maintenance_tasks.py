import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.modules.auth.repository import AuthRepository
from app.modules.notifications.service import NotificationsService
from app.modules.tasks.repository import TasksRepository
from app.modules.universities.models import University
from app.modules.users.repository import UsersRepository
from app.workers.celery_app import celery_app
from app.workers.email_tasks import send_email_task


async def _mark_overdue_tasks() -> int:
    async with AsyncSessionLocal() as db:
        repo = TasksRepository(db)
        count = await repo.mark_overdue_bulk()
        await db.commit()
        return count


async def _cleanup_expired_tokens() -> int:
    async with AsyncSessionLocal() as db:
        repo = AuthRepository(db)
        count = await repo.delete_expired_tokens()
        await db.commit()
        return count


async def _check_university_staleness() -> int:
    stale_before = datetime.now(tz=timezone.utc) - timedelta(days=365)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(University).where(
                or_(University.last_verified_at.is_(None), University.last_verified_at < stale_before)
            )
        )
        items = result.scalars().all()
        if not items:
            return 0

        user_repo = UsersRepository(db)
        adviser = await user_repo.get_by_email(settings.ADVISER_email)
        if not adviser:
            return 0

        examples = ", ".join([u.name for u in items[:5]])
        body = f"{len(items)} universities need review."
        if examples:
            body = f"{body} Examples: {examples}."

        notifier = NotificationsService(db)
        await notifier.create_notification(
            user_id=adviser.id,
            notification_type="university_stale",
            title="Universities need review",
            body=body,
            source_type="university",
        )
        await db.commit()

        if adviser.email:
            send_email_task.delay(
                to=adviser.email,
                subject="Universities need review",
                context={"body": body},
            )

        return len(items)


@celery_app.task
def mark_overdue_tasks() -> int:
    return asyncio.run(_mark_overdue_tasks())


@celery_app.task
def cleanup_expired_tokens() -> int:
    return asyncio.run(_cleanup_expired_tokens())


@celery_app.task
def check_university_staleness() -> int:
    return asyncio.run(_check_university_staleness())
