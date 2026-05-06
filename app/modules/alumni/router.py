from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_conductor_or_admin
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.alumni.schemas import AlumniCreate, AlumniListResponse, AlumniOut, AlumniResponse, AlumniUpdate
from app.modules.alumni.service import AlumniService

router = APIRouter()


@router.get("/alumni", response_model=AlumniListResponse)
async def list_alumni(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AlumniListResponse:
    service = AlumniService(db)
    items = await service.list_stories(current_user.role)
    return AlumniListResponse(data=[AlumniOut.model_validate(i) for i in items])


@router.get("/alumni/{story_id}", response_model=AlumniResponse)
async def get_alumni(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AlumniResponse:
    service = AlumniService(db)
    item = await service.get_story(story_id, current_user.role)
    return AlumniResponse(data=AlumniOut.model_validate(item))


@router.post("/alumni", response_model=AlumniResponse, status_code=201)
async def create_alumni(
    body: AlumniCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> AlumniResponse:
    service = AlumniService(db)
    item = await service.create_story(body, UUID(current_user.user_id), current_user.role)
    return AlumniResponse(data=AlumniOut.model_validate(item))


@router.put("/alumni/{story_id}", response_model=AlumniResponse)
async def update_alumni(
    story_id: UUID,
    body: AlumniUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> AlumniResponse:
    service = AlumniService(db)
    item = await service.update_story(story_id, body, current_user.role)
    return AlumniResponse(data=AlumniOut.model_validate(item))


@router.delete("/alumni/{story_id}", response_model=SuccessResponse)
async def delete_alumni(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> SuccessResponse:
    service = AlumniService(db)
    await service.delete_story(story_id, current_user.role)
    return SuccessResponse()
