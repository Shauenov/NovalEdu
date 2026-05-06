from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.modules.notifications.models import Notification


class NotificationsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Notification:
        notif = Notification(**kwargs)
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def get_by_id(self, notif_id: UUID, user_id: UUID) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notif_id, Notification.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(
            Notification.created_at.desc()
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def mark_read(self, notif_id: UUID, user_id: UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notif_id, Notification.user_id == user_id)
            .values(is_read=True, read_at=datetime.now(tz=timezone.utc))
        )

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.now(tz=timezone.utc))
        )

    async def unread_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                Notification.user_id == user_id, Notification.is_read == False
            )
        )
        return result.scalar_one()
