from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_any_authenticated
from app.database import get_db
from app.modules.profile.schemas import ProfileOut, ProfileResponse, ProfileUpdate
from app.modules.profile.service import ProfileService

router = APIRouter()


@router.get("/students/{student_id}/profile", response_model=ProfileResponse)
async def get_student_profile(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_authenticated()),
) -> ProfileResponse:
    service = ProfileService(db)
    profile = await service.get_profile(student_id)
    return ProfileResponse(data=profile)


@router.put("/students/{student_id}/profile", response_model=ProfileResponse)
async def update_student_profile(
    student_id: UUID,
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_authenticated()),
) -> ProfileResponse:
    service = ProfileService(db)
    profile = await service.update_profile(
        target_user_id=student_id,
        data=body,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return ProfileResponse(data=profile)
