from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_student
from app.database import get_db
from app.modules.reviews.schemas import (
    ReviewCreate,
    ReviewResponse,
    ReviewsListResponse,
    ReviewsMeta,
)
from app.modules.reviews.service import ReviewsService

router = APIRouter()


@router.post("/advisers/{adviser_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    adviser_id: UUID,
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_student()),
) -> ReviewResponse:
    service = ReviewsService(db)
    review = await service.create_review(adviser_id, UUID(current_user.user_id), body)
    return ReviewResponse(data=review)


@router.get("/advisers/{adviser_id}/reviews", response_model=ReviewsListResponse)
async def list_reviews(
    adviser_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReviewsListResponse:
    service = ReviewsService(db)
    items, avg, count = await service.list_for_adviser(adviser_id)
    return ReviewsListResponse(data=items, meta=ReviewsMeta(rating_avg=avg, count=count))


@router.get("/reviews/latest", response_model=ReviewResponse)
async def latest_review(
    adviser_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReviewResponse:
    service = ReviewsService(db)
    review = await service.latest(adviser_id)
    return ReviewResponse(data=review)
