from email.message import EmailMessage
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, context: dict | None = None) -> str:
    template = _env.get_template(template_name)
    return template.render(context or {})


async def send_email(
    to: str,
    subject: str,
    template: str | None = None,
    context: dict | None = None,
    plain: str | None = None,
) -> None:
    html = None
    if template:
        html = render_template(template, context)

    if not html and context and isinstance(context, dict):
        plain = plain or context.get("body")

    message = EmailMessage()
    sender = (
        settings.email_from_address
        or settings.email_host_user
        or f"noreply@{settings.app_host.split('://')[-1]}"
    )
    message["From"] = f"{settings.email_from_name} <{sender}>"
    message["To"] = to
    message["Subject"] = subject
    if plain:
        message.set_content(plain)
    else:
        message.set_content("")
    if html:
        message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.email_host,
        port=settings.email_port,
        start_tls=settings.email_use_tls,
        username=settings.email_host_user or None,
        password=settings.email_host_password or None,
    )
