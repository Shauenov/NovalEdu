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


# ── University-centric view (Список заявок) ───────────────────────────────────

class StudentBriefForEnrollment(BaseModel):
    id: UUID
    full_name: str
    avatar_url: str | None = None
    is_active: bool = True
    # from student_profiles (nullable — profile may not exist)
    group_type: str | None = None
    course_year: int | None = None

    model_config = {"from_attributes": True}


class EnrollmentWithStudentOut(BaseModel):
    id: UUID
    student_id: UUID
    student: StudentBriefForEnrollment
    university_id: UUID
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedUniversityEnrollments(BaseModel):
    success: bool = True
    data: list[EnrollmentWithStudentOut]
    meta: PaginatedMeta
