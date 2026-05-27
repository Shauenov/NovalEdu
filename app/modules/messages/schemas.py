from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    sender_name: str | None = None
    sender_role: str | None = None
    body: str
    image_url: str | None = None
    image_content_type: str | None = None
    image_size: int | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: UUID
    student_id: UUID
    adviser_id: UUID
    student_name: str | None = None
    student_avatar_url: str | None = None
    adviser_name: str | None = None
    adviser_avatar_url: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    unread_count: int = 0

    model_config = {"from_attributes": True}


class CreateConversationRequest(BaseModel):
    student_id: UUID


class SendMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class BroadcastRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)
    filter_group: str | None = None
    ielts_passed: bool | None = None


class MessageResponse(BaseModel):
    success: bool = True
    data: MessageOut


class MessagesResponse(BaseModel):
    success: bool = True
    data: list[MessageOut]


class ConversationResponse(BaseModel):
    success: bool = True
    data: ConversationOut


class ConversationsResponse(BaseModel):
    success: bool = True
    data: list[ConversationOut]


class BroadcastResult(BaseModel):
    sent: int
    message_ids: list[UUID] | None = None


class BroadcastResponse(BaseModel):
    success: bool = True
    data: BroadcastResult
