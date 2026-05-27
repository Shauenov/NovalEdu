from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str | None = Field(None, max_length=2000)


class ReviewOut(BaseModel):
    id: UUID
    author_id: UUID
    author_name: str | None = None
    adviser_id: UUID
    rating: int
    text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewsMeta(BaseModel):
    rating_avg: float
    count: int


class ReviewResponse(BaseModel):
    success: bool = True
    data: ReviewOut | None = None


class ReviewsListResponse(BaseModel):
    success: bool = True
    data: list[ReviewOut]
    meta: ReviewsMeta
