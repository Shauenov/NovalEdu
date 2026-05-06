from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RoadmapTemplateTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    order_index: int = Field(..., ge=0, le=32767)
    days_offset: int | None = None


class RoadmapTemplateTaskOut(BaseModel):
    id: UUID
    roadmap_id: UUID
    title: str
    description: str | None
    order_index: int
    days_offset: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=300)
    description: str | None = None
    target_type: str | None = Field(None, max_length=50)
    is_public: bool = True
    template_tasks: list[RoadmapTemplateTaskCreate] = []


class RoadmapUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=300)
    description: str | None = None
    target_type: str | None = Field(None, max_length=50)
    is_public: bool | None = None


class RoadmapOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    target_type: str | None
    is_public: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoadmapDetail(BaseModel):
    roadmap: RoadmapOut
    template_tasks: list[RoadmapTemplateTaskOut]


class TemplateTaskOverride(BaseModel):
    template_task_id: UUID
    deadline: datetime


class AssignRequest(BaseModel):
    student_id: UUID
    customize_tasks: list[TemplateTaskOverride] = []


class StudentRoadmapOut(BaseModel):
    id: UUID
    student_id: UUID
    roadmap_id: UUID | None
    assigned_by: UUID
    title: str
    assigned_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedRoadmaps(BaseModel):
    success: bool = True
    data: list[RoadmapOut]
    meta: PaginatedMeta


class RoadmapResponse(BaseModel):
    success: bool = True
    data: RoadmapOut


class RoadmapDetailResponse(BaseModel):
    success: bool = True
    data: RoadmapDetail


class StudentRoadmapResponse(BaseModel):
    success: bool = True
    data: StudentRoadmapOut


class StudentRoadmapsResponse(BaseModel):
    success: bool = True
    data: list[StudentRoadmapOut]
