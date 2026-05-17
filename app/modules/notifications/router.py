from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.notifications.schemas import NotificationOut, NotificationsResponse, UnreadCountOut, UnreadCountResponse
from app.modules.notifications.service import NotificationsService

router = APIRouter()


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    type: str | None = Query(None, description="Filter by type: admission, task, system"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationsResponse:
    service = NotificationsService(db, redis=request.app.state.redis)
    notifs, _ = await service.list_notifications(
        UUID(current_user.user_id), page, page_size, notification_type=type
    )
    return NotificationsResponse(data=notifs)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UnreadCountResponse:
    service = NotificationsService(db, redis=request.app.state.redis)
    data = await service.get_unread_count(UUID(current_user.user_id))
    return UnreadCountResponse(data=data)


@router.patch("/{notif_id}/read", response_model=SuccessResponse)
async def mark_read(
    notif_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = NotificationsService(db, redis=request.app.state.redis)
    await service.mark_read(notif_id, UUID(current_user.user_id))
    return SuccessResponse()


@router.patch("/read-all", response_model=SuccessResponse)
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = NotificationsService(db, redis=request.app.state.redis)
    await service.mark_all_read(UUID(current_user.user_id))
    return SuccessResponse()
