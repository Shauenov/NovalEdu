from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str | None
    type: str
    is_read: bool
    read_at: datetime | None
    source_id: UUID | None
    source_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    count: int


class NotificationsResponse(BaseModel):
    success: bool = True
    data: list[NotificationOut]


class UnreadCountResponse(BaseModel):
    success: bool = True
    data: UnreadCountOut
