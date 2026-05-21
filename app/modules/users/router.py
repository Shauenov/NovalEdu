from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, File, UploadFile
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.upload import process_and_upload_image

from app.core.constants import BUCKET_AVATARS, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.users.schemas import (
    PaginatedStudents,
    StudentDetailResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.users.service import UsersService

router = APIRouter()


@router.get("/users/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    service = UsersService(db)
    user = await service.get_me(UUID(current_user.user_id))
    return UserResponse(data=user)


@router.put("/users/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    service = UsersService(db)
    user = await service.update_me(UUID(current_user.user_id), body)
    return UserResponse(data=user)


@router.post("/users/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    avatar_url = await process_and_upload_image(
        file=file, bucket=BUCKET_AVATARS, prefix=str(current_user.user_id)
    )
    service = UsersService(db)
    user = await service.update_me(
        UUID(current_user.user_id), UserUpdate(avatar_url=avatar_url)
    )
    return UserResponse(data=user)


@router.delete("/users/me", response_model=SuccessResponse)
async def delete_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = UsersService(db)
    await service.deactivate_me(UUID(current_user.user_id))
    return SuccessResponse()


@router.get("/students", response_model=PaginatedStudents)
async def list_students(
    group_type: Optional[str] = Query(None, pattern="^(D1|D2|D|F1|F2|F3|F4|F)$"),
    course_year: Optional[int] = Query(None, ge=2, le=3),
    ielts_passed: Optional[bool] = Query(None),
    sat_passed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    sort_by: Optional[str] = Query(None, pattern="^(gpa|full_name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedStudents:
    service = UsersService(db)
    return await service.list_students(
        requester_role=current_user.role,
        group_type=group_type,
        course_year=course_year,
        ielts_passed=ielts_passed,
        sat_passed=sat_passed,
        search=search,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/students/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> StudentDetailResponse:
    service = UsersService(db)
    data = await service.get_student(
        student_id=student_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return StudentDetailResponse(data=data)


@router.delete("/students/{student_id}", response_model=SuccessResponse)
async def delete_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = UsersService(db)
    await service.delete_student(student_id, current_user.role)
    return SuccessResponse()


class InviteStudentRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str


@router.post("/adviser/students/invite", response_model=UserResponse, status_code=201)
async def invite_student(
    body: InviteStudentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    service = UsersService(db)
    user = await service.invite_student(
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        requester_role=current_user.role,
    )
    return UserResponse(data=user)
