from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user, require_ADVISER_or_admin
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.roadmaps.schemas import (
    RoadmapCreate,
    RoadmapUpdate,
    RoadmapOut,
    RoadmapDetail,
    RoadmapTemplateTaskOut,
    AssignRequest,
    StudentRoadmapOut,
    PaginatedRoadmaps,
    PaginatedMeta,
    RoadmapDetailResponse,
    RoadmapResponse,
    StudentRoadmapResponse,
    StudentRoadmapsResponse,
)
from app.modules.roadmaps.service import RoadmapsService

router = APIRouter()


@router.get("/roadmaps", response_model=PaginatedRoadmaps)
async def list_roadmaps(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedRoadmaps:
    service = RoadmapsService(db)
    items, total = await service.list_roadmaps(current_user.role, page, page_size)
    return PaginatedRoadmaps(
        data=[RoadmapOut.model_validate(r) for r in items],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/roadmaps/{roadmap_id}", response_model=RoadmapDetailResponse)
async def get_roadmap(
    roadmap_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> RoadmapDetailResponse:
    service = RoadmapsService(db)
    roadmap, tasks = await service.get_roadmap_detail(roadmap_id, current_user.role)
    return RoadmapDetailResponse(
        data=RoadmapDetail(
            roadmap=RoadmapOut.model_validate(roadmap),
            template_tasks=[RoadmapTemplateTaskOut.model_validate(t) for t in tasks],
        ),
    )


@router.post("/roadmaps", response_model=RoadmapResponse, status_code=201)
async def create_roadmap(
    body: RoadmapCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> RoadmapResponse:
    service = RoadmapsService(db)
    roadmap = await service.create_roadmap(body, UUID(current_user.user_id), current_user.role)
    return RoadmapResponse(data=RoadmapOut.model_validate(roadmap))


@router.put("/roadmaps/{roadmap_id}", response_model=RoadmapResponse)
async def update_roadmap(
    roadmap_id: UUID,
    body: RoadmapUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> RoadmapResponse:
    service = RoadmapsService(db)
    roadmap = await service.update_roadmap(roadmap_id, body, current_user.role)
    return RoadmapResponse(data=RoadmapOut.model_validate(roadmap))


@router.delete("/roadmaps/{roadmap_id}", response_model=SuccessResponse)
async def delete_roadmap(
    roadmap_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> SuccessResponse:
    service = RoadmapsService(db)
    await service.delete_roadmap(roadmap_id, current_user.role)
    return SuccessResponse()


@router.post("/roadmaps/{roadmap_id}/assign", response_model=StudentRoadmapResponse, status_code=201)
async def assign_roadmap(
    roadmap_id: UUID,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
) -> StudentRoadmapResponse:
    service = RoadmapsService(db)
    item = await service.assign_roadmap(roadmap_id, body, UUID(current_user.user_id), current_user.role)
    return StudentRoadmapResponse(data=StudentRoadmapOut.model_validate(item))


@router.get("/students/{student_id}/roadmaps", response_model=StudentRoadmapsResponse)
async def list_student_roadmaps(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> StudentRoadmapsResponse:
    service = RoadmapsService(db)
    items = await service.list_student_roadmaps(student_id, UUID(current_user.user_id), current_user.role)
    return StudentRoadmapsResponse(data=[StudentRoadmapOut.model_validate(i) for i in items])
