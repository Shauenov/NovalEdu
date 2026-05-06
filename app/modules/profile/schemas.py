from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    group_type: Literal["D", "F"]
    course_year: int
    gpa: Decimal | None = None
    ielts_passed: bool
    ielts_score: Decimal | None = None
    ielts_date: date | None = None
    sat_passed: bool
    sat_score: int | None = None
    sat_date: date | None = None
    ent_score: int | None = None
    kta_score: int | None = None
    target_country: str | None = None
    target_major: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    group_type: Literal["D", "F"] | None = None
    course_year: int | None = Field(None, ge=2, le=3)
    gpa: float | None = Field(None, ge=0.0, le=4.0)
    ielts_passed: bool | None = None
    ielts_score: float | None = Field(None, ge=0.0, le=9.0)
    ielts_date: date | None = None
    sat_passed: bool | None = None
    sat_score: int | None = Field(None, ge=400, le=1600)
    sat_date: date | None = None
    ent_score: int | None = Field(None, ge=0, le=140)
    kta_score: int | None = None
    target_country: str | None = Field(None, max_length=100)
    target_major: str | None = Field(None, max_length=200)
    notes: str | None = None


class ProfileResponse(BaseModel):
    success: bool = True
    data: ProfileOut
