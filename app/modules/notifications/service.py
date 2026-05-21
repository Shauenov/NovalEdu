from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, CACHE_TTL_UNREAD_COUNT
from app.core.exceptions import NotFoundException
from app.modules.notifications.repository import NotificationsRepository
from app.modules.notifications.schemas import NotificationOut, UnreadCountOut


class NotificationsService:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.repo = NotificationsRepository(db)

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str | None = None,
        source_id: UUID | None = None,
        source_type: str | None = None,
    ) -> NotificationOut:
        """Central method called by all other services to create notifications."""
        notif = await self.repo.create(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            source_id=source_id,
            source_type=source_type,
        )
        # Invalidate unread count cache
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")

        return NotificationOut.model_validate(notif)

    async def list_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        notification_type: str | None = None,
    ) -> tuple[list[NotificationOut], int]:
        notifs, total = await self.repo.list_for_user(user_id, page, page_size, notification_type)
        return [NotificationOut.model_validate(n) for n in notifs], total

    async def mark_read(self, notif_id: UUID, user_id: UUID) -> None:
        notif = await self.repo.get_by_id(notif_id, user_id)
        if not notif:
            raise NotFoundException("Notification not found")
        await self.repo.mark_read(notif_id, user_id)
        await self.db.commit()
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.repo.mark_all_read(user_id)
        await self.db.commit()
        if self.redis:
            await self.redis.delete(f"notifications:unread:{user_id}")

    async def get_unread_count(self, user_id: UUID) -> UnreadCountOut:
        if self.redis:
            cache_key = f"notifications:unread:{user_id}"
            cached = await self.redis.get(cache_key)
            if cached is not None:
                return UnreadCountOut(count=int(cached))

        count = await self.repo.unread_count(user_id)

        if self.redis:
            await self.redis.setex(cache_key, CACHE_TTL_UNREAD_COUNT, str(count))

        return UnreadCountOut(count=count)
