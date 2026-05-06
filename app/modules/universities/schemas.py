from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UniversityBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=300)
    country: str = Field(..., min_length=2, max_length=100)
    city: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)
    cover_image_url: str | None = Field(None, max_length=500)
    website_url: str | None = Field(None, max_length=500)
    description: str | None = None
    acceptance_rate: float | None = Field(None, ge=0.0, le=100.0)
    total_students: int | None = Field(None, ge=0)
    international_pct: float | None = Field(None, ge=0.0, le=100.0)
    qs_ranking: int | None = Field(None, ge=1)
    the_ranking: int | None = Field(None, ge=1)
    language_of_instr: str | None = Field(None, max_length=100)
    is_published: bool = True
    last_verified_at: datetime | None = None


class UniversityCreate(UniversityBase):
    pass


class UniversityUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=300)
    country: str | None = Field(None, min_length=2, max_length=100)
    city: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)
    cover_image_url: str | None = Field(None, max_length=500)
    website_url: str | None = Field(None, max_length=500)
    description: str | None = None
    acceptance_rate: float | None = Field(None, ge=0.0, le=100.0)
    total_students: int | None = Field(None, ge=0)
    international_pct: float | None = Field(None, ge=0.0, le=100.0)
    qs_ranking: int | None = Field(None, ge=1)
    the_ranking: int | None = Field(None, ge=1)
    language_of_instr: str | None = Field(None, max_length=100)
    is_published: bool | None = None
    last_verified_at: datetime | None = None


class UniversityOut(UniversityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UniversityProgramBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=300)
    degree_level: Literal["bachelor", "master", "phd", "foundation"] | None = None
    field: str | None = Field(None, max_length=100)
    min_gpa: float | None = Field(None, ge=0.0, le=4.0)
    min_ielts: float | None = Field(None, ge=0.0, le=9.0)
    min_sat: int | None = Field(None, ge=400, le=1600)
    tuition_usd: int | None = Field(None, ge=0)
    scholarship_info: str | None = None
    application_fee: int | None = Field(None, ge=0)
    intake_seasons: str | None = Field(None, max_length=100)
    deadline: date | None = None
    campus_life: str | None = None
    requirements_text: str | None = None
    apply_url: str | None = Field(None, max_length=500)
    is_active: bool = True


class UniversityProgramCreate(UniversityProgramBase):
    pass


class UniversityProgramUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=300)
    degree_level: Literal["bachelor", "master", "phd", "foundation"] | None = None
    field: str | None = Field(None, max_length=100)
    min_gpa: float | None = Field(None, ge=0.0, le=4.0)
    min_ielts: float | None = Field(None, ge=0.0, le=9.0)
    min_sat: int | None = Field(None, ge=400, le=1600)
    tuition_usd: int | None = Field(None, ge=0)
    scholarship_info: str | None = None
    application_fee: int | None = Field(None, ge=0)
    intake_seasons: str | None = Field(None, max_length=100)
    deadline: date | None = None
    campus_life: str | None = None
    requirements_text: str | None = None
    apply_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class UniversityProgramOut(UniversityProgramBase):
    id: UUID
    university_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UniversityDetail(BaseModel):
    university: UniversityOut
    programs: list[UniversityProgramOut]


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedUniversities(BaseModel):
    success: bool = True
    data: list[UniversityOut]
    meta: PaginatedMeta


class UniversityResponse(BaseModel):
    success: bool = True
    data: UniversityOut


class UniversityDetailResponse(BaseModel):
    success: bool = True
    data: UniversityDetail


class UniversityProgramResponse(BaseModel):
    success: bool = True
    data: UniversityProgramOut
