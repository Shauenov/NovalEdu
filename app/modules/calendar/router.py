from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventOut, CalendarEventResponse, CalendarEventUpdate, CalendarEventsResponse
from app.modules.calendar.service import CalendarService

router = APIRouter()


@router.get("", response_model=CalendarEventsResponse)
async def list_events(
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CalendarEventsResponse:
    service = CalendarService(db)
    items = await service.list_events(UUID(current_user.user_id), from_time, to_time, event_type)
    return CalendarEventsResponse(data=[CalendarEventOut.model_validate(i) for i in items])


@router.post("", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    body: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CalendarEventResponse:
    service = CalendarService(db)
    event = await service.create_event(UUID(current_user.user_id), body)
    return CalendarEventResponse(data=CalendarEventOut.model_validate(event))


@router.put("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: UUID,
    body: CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CalendarEventResponse:
    service = CalendarService(db)
    event = await service.update_event(event_id, UUID(current_user.user_id), body)
    return CalendarEventResponse(data=CalendarEventOut.model_validate(event))


@router.delete("/{event_id}", response_model=SuccessResponse)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = CalendarService(db)
    await service.delete_event(event_id, UUID(current_user.user_id))
    return SuccessResponse()
