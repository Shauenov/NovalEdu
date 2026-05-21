from datetime import datetime
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime | None = None
    duration_min: int | None = Field(None, ge=5, le=240)

    @model_validator(mode="after")
    def validate_times(self) -> "SlotCreate":
        if not self.end_time and not self.duration_min:
            raise ValueError("Provide end_time or duration_min")
        return self


class SlotsBatchCreate(BaseModel):
    slots: list[SlotCreate]


class SlotOut(BaseModel):
    id: UUID
    adviser_id: UUID
    start_time: datetime
    end_time: datetime
    duration_min: int
    is_available: bool

    model_config = {"from_attributes": True}


class BookRequest(BaseModel):
    slot_id: UUID
    consultation_type: Literal["video", "audio", "chat"] = "video"
    notes: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class AppointmentOut(BaseModel):
    id: UUID
    slot_id: UUID | None
    student_id: UUID
    adviser_id: UUID
    status: str
    consultation_type: str
    notes: str | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime
    # Joined from users table — always present when fetched via list endpoints
    student_name: str | None = None
    student_avatar_url: str | None = None
    # Joined from availability_slots table
    slot_start_time: datetime | None = None
    slot_end_time: datetime | None = None

    model_config = {"from_attributes": True}


class SlotsResponse(BaseModel):
    success: bool = True
    data: list[SlotOut]


class AppointmentResponse(BaseModel):
    success: bool = True
    data: AppointmentOut


class AppointmentsResponse(BaseModel):
    success: bool = True
    data: list[AppointmentOut]
