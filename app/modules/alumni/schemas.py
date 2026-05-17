from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.constants import BUCKET_ALUMNI
from app.storage.minio_client import resolve_public_url


class AlumniCreate(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=255)
    graduation_year: int | None = Field(None, ge=1900, le=2100)
    university_id: UUID | None = None
    university_name: str | None = Field(None, max_length=300)
    program_name: str | None = Field(None, max_length=300)
    scholarship_type: str | None = Field(None, max_length=200)
    story_text: str = Field(..., min_length=1)
    photo_url: str | None = Field(None, max_length=500)
    gpa_at_time: float | None = Field(None, ge=0.0, le=4.0)
    ielts_at_time: float | None = Field(None, ge=0.0, le=9.0)
    sat_at_time: int | None = Field(None, ge=400, le=1600)
    is_published: bool = True


class AlumniUpdate(BaseModel):
    student_name: str | None = Field(None, min_length=1, max_length=255)
    graduation_year: int | None = Field(None, ge=1900, le=2100)
    university_id: UUID | None = None
    university_name: str | None = Field(None, max_length=300)
    program_name: str | None = Field(None, max_length=300)
    scholarship_type: str | None = Field(None, max_length=200)
    story_text: str | None = Field(None, min_length=1)
    photo_url: str | None = Field(None, max_length=500)
    gpa_at_time: float | None = Field(None, ge=0.0, le=4.0)
    ielts_at_time: float | None = Field(None, ge=0.0, le=9.0)
    sat_at_time: int | None = Field(None, ge=400, le=1600)
    is_published: bool | None = None


class AlumniOut(BaseModel):
    id: UUID
    author_id: UUID
    student_name: str
    graduation_year: int | None
    university_id: UUID | None
    university_name: str | None
    program_name: str | None
    scholarship_type: str | None
    story_text: str
    photo_url: str | None
    gpa_at_time: float | None
    ielts_at_time: float | None
    sat_at_time: int | None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def normalize_photo_url(self):
        self.photo_url = resolve_public_url(BUCKET_ALUMNI, self.photo_url)
        return self


class AlumniResponse(BaseModel):
    success: bool = True
    data: AlumniOut


class AlumniListResponse(BaseModel):
    success: bool = True
    data: list[AlumniOut]
