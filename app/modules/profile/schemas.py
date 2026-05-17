import json
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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
    # Personal info
    phone: str | None = None
    gender: Literal["male", "female", "other"] | None = None
    birth_date: date | None = None
    school_name: str | None = None
    # Application settings
    degree_level: Literal["bachelor", "master", "phd"] | None = None
    target_countries: list[str] = []
    budget_max: int | None = None

    model_config = {"from_attributes": True}

    @field_validator("target_countries", mode="before")
    @classmethod
    def parse_target_countries(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return []
        return []


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
    # Personal info
    phone: str | None = Field(None, max_length=30)
    gender: Literal["male", "female", "other"] | None = None
    birth_date: date | None = None
    school_name: str | None = Field(None, max_length=300)
    # Application settings
    degree_level: Literal["bachelor", "master", "phd"] | None = None
    target_countries: list[str] | None = None
    budget_max: int | None = Field(None, ge=0)


class ProfileResponse(BaseModel):
    success: bool = True
    data: ProfileOut
