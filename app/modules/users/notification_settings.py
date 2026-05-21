"""
Notification preferences model, schemas, and router for
GET/PUT /users/me/notification-settings
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select

from app.core.permissions import CurrentUser, get_current_user
from app.database import Base, get_db


# ── Model ────────────────────────────────────────────────────────────────────

class UserNotificationSettings(Base):
    __tablename__ = "user_notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Push / Email
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Academic
    deadline_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    roadmap_changes: Mapped[bool] = mapped_column(Boolean, default=True)
    new_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    task_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    # System
    security_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    app_updates: Mapped[bool] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotificationSettingsOut(BaseModel):
    push_enabled: bool
    email_enabled: bool
    deadline_alerts: bool
    roadmap_changes: bool
    new_messages: bool
    task_updates: bool
    security_alerts: bool
    app_updates: bool

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    push_enabled: bool | None = None
    email_enabled: bool | None = None
    deadline_alerts: bool | None = None
    roadmap_changes: bool | None = None
    new_messages: bool | None = None
    task_updates: bool | None = None
    security_alerts: bool | None = None
    app_updates: bool | None = None


class NotificationSettingsResponse(BaseModel):
    success: bool = True
    data: NotificationSettingsOut


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter()


async def _get_or_create_settings(
    user_id: uuid.UUID, db: AsyncSession
) -> UserNotificationSettings:
    result = await db.execute(
        select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserNotificationSettings(user_id=user_id)
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.get("/users/me/notification-settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationSettingsResponse:
    settings = await _get_or_create_settings(uuid.UUID(current_user.user_id), db)
    await db.commit()
    return NotificationSettingsResponse(data=NotificationSettingsOut.model_validate(settings))


@router.put("/users/me/notification-settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NotificationSettingsResponse:
    settings = await _get_or_create_settings(uuid.UUID(current_user.user_id), db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return NotificationSettingsResponse(data=NotificationSettingsOut.model_validate(settings))
