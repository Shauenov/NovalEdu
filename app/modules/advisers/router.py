from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_adviser
from app.database import get_db
from app.modules.advisers.schemas import AdviserProfileUpdate, AdviserResponse
from app.modules.advisers.service import AdvisersService

router = APIRouter()


@router.put("/advisers/me", response_model=AdviserResponse)
async def update_my_adviser_profile(
    body: AdviserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_adviser()),
) -> AdviserResponse:
    service = AdvisersService(db)
    data = await service.update_my_profile(UUID(current_user.user_id), body)
    return AdviserResponse(data=data)


@router.get("/advisers/{adviser_id}", response_model=AdviserResponse)
async def get_adviser_profile(
    adviser_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AdviserResponse:
    service = AdvisersService(db)
    data = await service.get_public_profile(adviser_id)
    return AdviserResponse(data=data)
