from uuid import UUID

from fastapi import APIRouter, Depends, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.upload import process_and_upload_image

from app.core.constants import BUCKET_NEWS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.news.schemas import (
    NewsCreate,
    NewsUpdate,
    NewsOut,
    PaginatedNews,
    PaginatedMeta,
    AddToCalendarRequest,
    NewsResponse,
)
from app.modules.news.service import NewsService
from app.modules.calendar.schemas import CalendarEventOut, CalendarEventResponse

router = APIRouter()


@router.get("", response_model=PaginatedNews)
async def list_news(
    category: str | None = Query(None),
    upcoming: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedNews:
    service = NewsService(db)
    items, total = await service.list_news(
        requester_role=current_user.role,
        category=category,
        upcoming=upcoming,
        page=page,
        page_size=page_size,
    )
    return PaginatedNews(
        data=[NewsOut.model_validate(n) for n in items],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NewsResponse:
    service = NewsService(db)
    item = await service.get_news(news_id, current_user.role)
    return NewsResponse(data=NewsOut.model_validate(item))


@router.post("", response_model=NewsResponse, status_code=201)
async def create_news(
    body: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NewsResponse:
    service = NewsService(db)
    item = await service.create_news(body, UUID(current_user.user_id), current_user.role)
    return NewsResponse(data=NewsOut.model_validate(item))


@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: UUID,
    body: NewsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NewsResponse:
    service = NewsService(db)
    item = await service.update_news(news_id, body, current_user.role)
    return NewsResponse(data=NewsOut.model_validate(item))


@router.delete("/{news_id}", response_model=SuccessResponse)
async def delete_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = NewsService(db)
    await service.delete_news(news_id, current_user.role)
    return SuccessResponse()


@router.post("/{news_id}/cover", response_model=NewsResponse)
async def upload_news_cover(
    news_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NewsResponse:
    cover_url = await process_and_upload_image(
        file=file,
        bucket=BUCKET_NEWS,
        prefix=f"{news_id}/cover"
    )
    service = NewsService(db)
    item = await service.update_news(news_id, NewsUpdate(cover_url=cover_url), current_user.role)
    return NewsResponse(data=NewsOut.model_validate(item))


@router.post("/{news_id}/add-to-calendar", response_model=CalendarEventResponse, status_code=201)
async def add_to_calendar(
    news_id: UUID,
    body: AddToCalendarRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CalendarEventResponse:
    service = NewsService(db)
    event = await service.add_to_calendar(news_id, UUID(current_user.user_id), current_user.role)
    return CalendarEventResponse(data=CalendarEventOut.model_validate(event))
