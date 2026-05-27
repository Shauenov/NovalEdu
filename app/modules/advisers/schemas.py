from uuid import UUID

from pydantic import BaseModel, Field


class AdviserProfileUpdate(BaseModel):
    headline: str | None = Field(None, max_length=200)
    bio: str | None = None
    skills: list[str] | None = None
    students_placed: int | None = Field(None, ge=0)
    scholarships_won_usd: int | None = Field(None, ge=0)
    years_experience: int | None = Field(None, ge=0, le=80)


class AdviserPublicOut(BaseModel):
    user_id: UUID
    full_name: str
    avatar_url: str | None = None
    headline: str | None = None
    bio: str | None = None
    skills: list[str] = []
    students_placed: int | None = None
    scholarships_won_usd: int | None = None
    years_experience: int | None = None
    rating_avg: float = 0.0
    reviews_count: int = 0


class AdviserResponse(BaseModel):
    success: bool = True
    data: AdviserPublicOut
