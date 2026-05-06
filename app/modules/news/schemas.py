from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


NewsCategory = Literal[
    "olympiad",
    "hackathon",
    "deadline",
    "summer_camp",
    "webinar",
    "internship",
    "university_news",
    "general",
]


class NewsBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=500)
    body: str = Field(..., min_length=1)
    cover_url: str | None = Field(None, max_length=500)
    category: NewsCategory
    event_date: date | None = None
    external_url: str | None = Field(None, max_length=500)
    is_published: bool = True


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=500)
    body: str | None = Field(None, min_length=1)
    cover_url: str | None = Field(None, max_length=500)
    category: NewsCategory | None = None
    event_date: date | None = None
    external_url: str | None = Field(None, max_length=500)
    is_published: bool | None = None


class NewsOut(NewsBase):
    id: UUID
    author_id: UUID
    views_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddToCalendarRequest(BaseModel):
    reminder_days_before: int | None = Field(None, ge=0, le=30)


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedNews(BaseModel):
    success: bool = True
    data: list[NewsOut]
    meta: PaginatedMeta


class NewsResponse(BaseModel):
    success: bool = True
    data: NewsOut
