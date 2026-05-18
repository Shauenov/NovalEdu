from datetime import datetime, time, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    task_type: Literal["deadline", "assignment"] = "assignment"
    deadline: datetime | None = None
    time_from: time | None = None
    time_to: time | None = None
    location: str | None = Field(None, max_length=300)
    reminder_minutes: int | None = Field(None, ge=1, le=10080)
    student_roadmap_id: UUID | None = None

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v and v <= datetime.now(tz=timezone.utc):
            raise ValueError("Deadline must be in the future")
        return v


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    priority: Literal["low", "medium", "high"] | None = None
    task_type: Literal["deadline", "assignment"] | None = None
    deadline: datetime | None = None
    time_from: time | None = None
    time_to: time | None = None
    location: str | None = Field(None, max_length=300)
    reminder_minutes: int | None = Field(None, ge=1, le=10080)

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v and v <= datetime.now(tz=timezone.utc):
            raise ValueError("Deadline must be in the future")
        return v


class TaskStatusUpdate(BaseModel):
    status: Literal["todo", "in_progress", "done"]


class TaskOut(BaseModel):
    id: UUID
    student_id: UUID
    created_by: UUID
    title: str
    description: str | None
    status: str
    priority: str
    task_type: str
    deadline: datetime | None
    time_from: time | None
    time_to: time | None
    location: str | None
    reminder_minutes: int | None
    completed_at: datetime | None
    is_conductor_task: bool
    student_roadmap_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskStatsOut(BaseModel):
    total: int
    completed: int
    overdue: int
    in_progress: int
    todo: int


class TaskStatsResponse(BaseModel):
    success: bool = True
    data: TaskStatsOut


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedTasks(BaseModel):
    success: bool = True
    data: list[TaskOut]
    meta: PaginatedMeta


class TaskResponse(BaseModel):
    success: bool = True
    data: TaskOut


class TaskHistoryOut(BaseModel):
    id: UUID
    task_id: UUID
    changed_by: UUID | None
    event_type: str       # created | status_changed | updated | deleted
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskHistoryResponse(BaseModel):
    success: bool = True
    data: list[TaskHistoryOut]
