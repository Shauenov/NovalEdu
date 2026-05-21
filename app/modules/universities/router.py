from uuid import UUID

from fastapi import APIRouter, Depends, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.upload import process_and_upload_image

from app.core.constants import BUCKET_UNIVERSITIES, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import (
    CurrentUser,
    get_current_user,
    require_ADVISER_or_admin,
)
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.universities.schemas import (
    PaginatedUniversities,
    PaginatedMeta,
    UniversityCreate,
    UniversityUpdate,
    UniversityOut,
    UniversityDetail,
    UniversityProgramCreate,
    UniversityProgramUpdate,
    UniversityProgramOut,
    UniversityDetailResponse,
    UniversityProgramResponse,
    UniversityResponse,
)
from app.modules.universities.service import UniversitiesService

router = APIRouter()


@router.get("", response_model=PaginatedUniversities)
async def list_universities(
    country: str | None = Query(None, max_length=100),
    is_abroad: bool | None = Query(None),
    field: str | None = Query(None, max_length=100),
    min_gpa: float | None = Query(None, ge=0.0, le=4.0),
    max_tuition: int | None = Query(None, ge=0),
    degree_level: str | None = Query(None),
    has_scholarship: bool | None = Query(None),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedUniversities:
    service = UniversitiesService(db)
    items, total = await service.list_universities(
        requester_role=current_user.role,
        country=country,
        is_abroad=is_abroad,
        field=field,
        min_gpa=min_gpa,
        max_tuition=max_tuition,
        degree_level=degree_level,
        has_scholarship=has_scholarship,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaginatedUniversities(
        data=[UniversityOut.model_validate(u) for u in items],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{university_id}", response_model=UniversityDetailResponse)
async def get_university(
    university_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> UniversityDetailResponse:
    service = UniversitiesService(db)
    uni, programs = await service.get_university_detail(
        university_id, current_user.role
    )
    detail = UniversityDetail(
        university=UniversityOut.model_validate(uni),
        programs=[UniversityProgramOut.model_validate(p) for p in programs],
    )
    return UniversityDetailResponse(data=detail)


@router.post("", response_model=UniversityResponse, status_code=201)
async def create_university(
    body: UniversityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityResponse:
    service = UniversitiesService(db)
    uni = await service.create_university(body, current_user.role)
    return UniversityResponse(data=UniversityOut.model_validate(uni))


@router.put("/{university_id}", response_model=UniversityResponse)
async def update_university(
    university_id: UUID,
    body: UniversityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityResponse:
    service = UniversitiesService(db)
    uni = await service.update_university(university_id, body, current_user.role)
    return UniversityResponse(data=UniversityOut.model_validate(uni))


@router.delete("/{university_id}", response_model=SuccessResponse)
async def delete_university(
    university_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> SuccessResponse:
    service = UniversitiesService(db)
    await service.delete_university(university_id, current_user.role)
    return SuccessResponse()


@router.post("/{university_id}/logo", response_model=UniversityResponse)
async def upload_university_logo(
    university_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityResponse:
    logo_url = await process_and_upload_image(
        file=file, bucket=BUCKET_UNIVERSITIES, prefix=f"{university_id}/logo"
    )
    service = UniversitiesService(db)
    uni = await service.update_university(
        university_id, UniversityUpdate(logo_url=logo_url), current_user.role
    )
    return UniversityResponse(data=UniversityOut.model_validate(uni))


@router.post("/{university_id}/cover", response_model=UniversityResponse)
async def upload_university_cover(
    university_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityResponse:
    cover_url = await process_and_upload_image(
        file=file, bucket=BUCKET_UNIVERSITIES, prefix=f"{university_id}/cover"
    )
    service = UniversitiesService(db)
    uni = await service.update_university(
        university_id, UniversityUpdate(cover_image_url=cover_url), current_user.role
    )
    return UniversityResponse(data=UniversityOut.model_validate(uni))


@router.post(
    "/{university_id}/programs",
    response_model=UniversityProgramResponse,
    status_code=201,
)
async def add_program(
    university_id: UUID,
    body: UniversityProgramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityProgramResponse:
    service = UniversitiesService(db)
    program = await service.create_program(university_id, body, current_user.role)
    return UniversityProgramResponse(data=UniversityProgramOut.model_validate(program))


@router.put(
    "/{university_id}/programs/{program_id}", response_model=UniversityProgramResponse
)
async def update_program(
    university_id: UUID,
    program_id: UUID,
    body: UniversityProgramUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> UniversityProgramResponse:
    service = UniversitiesService(db)
    program = await service.update_program(
        university_id, program_id, body, current_user.role
    )
    return UniversityProgramResponse(data=UniversityProgramOut.model_validate(program))


@router.delete("/{university_id}/programs/{program_id}", response_model=SuccessResponse)
async def delete_program(
    university_id: UUID,
    program_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> SuccessResponse:
    service = UniversitiesService(db)
    await service.delete_program(university_id, program_id, current_user.role)
    return SuccessResponse()
