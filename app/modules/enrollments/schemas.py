from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EnrollmentOut(BaseModel):
    id: UUID
    student_id: UUID
    university_id: UUID
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentUpdateRequest(BaseModel):
    status: Literal["selected", "applying", "submitted", "accepted", "rejected"] | None = None
    progress: int | None = Field(None, ge=0, le=100)


class EnrollmentResponse(BaseModel):
    success: bool = True
    data: EnrollmentOut


class EnrollmentsResponse(BaseModel):
    success: bool = True
    data: list[EnrollmentOut]
