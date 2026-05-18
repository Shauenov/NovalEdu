from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.tasks.schemas import PaginatedMeta, PaginatedTasks, TaskCreate, TaskHistoryResponse, TaskOut, TaskResponse, TaskStatsOut, TaskStatsResponse, TaskStatusUpdate, TaskUpdate
from app.modules.tasks.service import TasksService

router = APIRouter()


@router.get("/students/{student_id}/tasks", response_model=PaginatedTasks)
async def list_student_tasks(
    student_id: UUID,
    status: Optional[str] = Query(None),
    is_conductor_task: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedTasks:
    service = TasksService(db)
    tasks, total = await service.list_student_tasks(
        student_id=student_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
        status=status,
        is_conductor_task=is_conductor_task,
        page=page,
        page_size=page_size,
    )
    return PaginatedTasks(
        data=[TaskOut.model_validate(t) for t in tasks],
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/students/{student_id}/tasks/stats", response_model=TaskStatsResponse)
async def get_student_task_stats(
    student_id: UUID,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$", description="Format: YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskStatsResponse:
    service = TasksService(db)
    stats = await service.get_task_stats(
        student_id=student_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
        month=month,
    )
    return TaskStatsResponse(data=TaskStatsOut(**stats))


@router.post("/students/{student_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_conductor_task(
    student_id: UUID,
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    service = TasksService(db)
    task = await service.create_conductor_task(
        student_id=student_id,
        data=body,
        created_by=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return TaskResponse(data=task)


@router.post("/tasks/personal", response_model=TaskResponse, status_code=201)
async def create_personal_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    service = TasksService(db)
    task = await service.create_personal_task(
        data=body,
        student_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return TaskResponse(data=task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    service = TasksService(db)
    task = await service.get_task(
        task_id=task_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return TaskResponse(data=task)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    service = TasksService(db)
    task = await service.update_task(
        task_id=task_id,
        data=body,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return TaskResponse(data=task)


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def patch_task_status(
    task_id: UUID,
    body: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskResponse:
    service = TasksService(db)
    task = await service.patch_status(
        task_id=task_id,
        data=body,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return TaskResponse(data=task)


@router.get("/tasks/{task_id}/history", response_model=TaskHistoryResponse)
async def get_task_history(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TaskHistoryResponse:
    service = TasksService(db)
    return await service.get_history(
        task_id=task_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )


@router.delete("/tasks/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuccessResponse:
    service = TasksService(db)
    await service.delete_task(
        task_id=task_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
    )
    return SuccessResponse()
