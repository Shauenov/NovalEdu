from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


CalendarEventType = Literal[
    "appointment",
    "task_deadline",
    "news_event",
    "university_deadline",
    "custom",
]


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    event_type: CalendarEventType
    start_time: datetime
    end_time: datetime | None = None
    all_day: bool = False
    color: str | None = Field(None, max_length=7)
    source_id: UUID | None = None
    source_type: str | None = Field(None, max_length=30)


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    event_type: CalendarEventType | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    all_day: bool | None = None
    color: str | None = Field(None, max_length=7)


class CalendarEventOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None
    event_type: CalendarEventType
    start_time: datetime
    end_time: datetime | None
    all_day: bool
    color: str
    source_id: UUID | None
    source_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarEventResponse(BaseModel):
    success: bool = True
    data: CalendarEventOut


class CalendarEventsResponse(BaseModel):
    success: bool = True
    data: list[CalendarEventOut]
