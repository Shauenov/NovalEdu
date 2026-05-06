import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base

# Import all models so Alembic can detect them. Import failures are logged
# and ignored to allow running migrations while some optional modules
# are not yet implemented during development.
import importlib
import logging

logger = logging.getLogger("alembic.env")

_MODULES = [
    "app.modules.users.models",
    "app.modules.auth.models",
    "app.modules.profile.models",
    "app.modules.documents.models",
    "app.modules.universities.models",
    "app.modules.news.models",
    "app.modules.tasks.models",
    "app.modules.roadmaps.models",
    "app.modules.appointments.models",
    "app.modules.messages.models",
    "app.modules.calendar.models",
    "app.modules.notifications.models",
    "app.modules.faq.models",
    "app.modules.alumni.models",
]

for _m in _MODULES:
    try:
        importlib.import_module(_m)
    except Exception as exc:  # pragma: no cover - defensive for dev environments
        logger.debug("Alembic import: could not import %s: %s", _m, exc)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
