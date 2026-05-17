from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, get_current_user, require_conductor_or_admin
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.enrollments.schemas import EnrollmentResponse, EnrollmentsResponse, EnrollmentUpdateRequest
from app.modules.enrollments.service import EnrollmentsService

router = APIRouter()


@router.post(
    "/students/{student_id}/universities/{university_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=201,
)
async def enroll_university(
    student_id: UUID,
    university_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> EnrollmentResponse:
    svc = EnrollmentsService(db)
    enrollment = await svc.enroll(
        student_id=student_id,
        university_id=university_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return EnrollmentResponse(data=enrollment)


@router.get("/students/{student_id}/enrollments", response_model=EnrollmentsResponse)
async def list_enrollments(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> EnrollmentsResponse:
    svc = EnrollmentsService(db)
    items = await svc.list_enrollments(
        student_id=student_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return EnrollmentsResponse(data=items)


@router.patch(
    "/students/{student_id}/universities/{university_id}/enroll",
    response_model=EnrollmentResponse,
)
async def update_enrollment(
    student_id: UUID,
    university_id: UUID,
    body: EnrollmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_conductor_or_admin()),
) -> EnrollmentResponse:
    svc = EnrollmentsService(db)
    enrollment = await svc.update_enrollment(
        student_id=student_id,
        university_id=university_id,
        data=body,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return EnrollmentResponse(data=enrollment)


@router.delete(
    "/students/{student_id}/universities/{university_id}/enroll",
    response_model=SuccessResponse,
)
async def delete_enrollment(
    student_id: UUID,
    university_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    svc = EnrollmentsService(db)
    await svc.delete_enrollment(
        student_id=student_id,
        university_id=university_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return SuccessResponse()
