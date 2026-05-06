from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    deadline: datetime | None = None
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
    deadline: datetime | None = None

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
    deadline: datetime | None
    completed_at: datetime | None
    is_conductor_task: bool
    student_roadmap_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
