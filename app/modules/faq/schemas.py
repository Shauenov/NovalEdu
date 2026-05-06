from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=100)
    order_index: int | None = Field(0, ge=0, le=32767)
    is_active: bool = True


class FAQUpdate(BaseModel):
    question: str | None = Field(None, min_length=1)
    answer: str | None = Field(None, min_length=1)
    category: str | None = Field(None, max_length=100)
    order_index: int | None = Field(None, ge=0, le=32767)
    is_active: bool | None = None


class FAQOut(BaseModel):
    id: UUID
    question: str
    answer: str
    category: str | None
    order_index: int
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReorderItem(BaseModel):
    id: UUID
    order_index: int = Field(..., ge=0, le=32767)


class ReorderRequest(BaseModel):
    items: list[ReorderItem]


class FAQResponse(BaseModel):
    success: bool = True
    data: FAQOut


class FAQListResponse(BaseModel):
    success: bool = True
    data: list[FAQOut]
