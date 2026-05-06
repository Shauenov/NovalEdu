import asyncio

from celery import Task

from app.email.sender import send_email
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self: Task, to: str, subject: str, template: str | None = None, context: dict | None = None) -> None:
    """Celery task wrapper to send an email. Renders a template if provided.

    Args:
        to: recipient email
        subject: email subject
        template: template filename under `app/email/templates`
        context: template context map
    """
    try:
        asyncio.run(send_email(to=to, subject=subject, template=template, context=context))
    except Exception as exc:
        raise self.retry(exc=exc)
