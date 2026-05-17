from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    student_id: UUID
    doc_type: str
    category: Literal["personal", "education", "financial", "other"]
    status: Literal["active", "pending", "expired", "needs_update"]
    expires_at: datetime | None
    url: str
    content_type: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    id: UUID
    doc_type: str
    category: str
    status: str
    url: str


class DocumentsResponse(BaseModel):
    success: bool = True
    data: list[DocumentOut]


class DocumentUploadEnvelope(BaseModel):
    success: bool = True
    data: DocumentUploadResponse


class DocumentResponse(BaseModel):
    success: bool = True
    data: DocumentOut
