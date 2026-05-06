from datetime import datetime
from typing import List
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
    conductor_id: UUID
    start_time: datetime
    end_time: datetime
    duration_min: int
    is_available: bool

    model_config = {"from_attributes": True}


class BookRequest(BaseModel):
    slot_id: UUID
    notes: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class AppointmentOut(BaseModel):
    id: UUID
    slot_id: UUID | None
    student_id: UUID
    conductor_id: UUID
    status: str
    notes: str | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime

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
