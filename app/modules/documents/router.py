from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE
from app.core.permissions import CurrentUser, get_current_user
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.documents.schemas import DocumentOut, DocumentResponse, DocumentUploadEnvelope, DocumentUploadResponse, DocumentsResponse
from app.modules.documents.service import DocumentsService

router = APIRouter()


@router.get("/students/{student_id}/documents", response_model=DocumentsResponse)
async def list_documents(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = DocumentsService(db)
    docs = await svc.list_documents(student_id)
    return DocumentsResponse(data=docs)


@router.get("/students/{student_id}/documents/{doc_type}", response_model=DocumentResponse)
async def get_document(
    student_id: UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = DocumentsService(db)
    doc = await svc.get_document(student_id, doc_type)
    return DocumentResponse(data=DocumentOut.model_validate(doc))


@router.post("/students/{student_id}/documents", response_model=DocumentUploadEnvelope, status_code=201)
async def upload_document(
    student_id: UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    category: Literal["personal", "education", "financial", "other"] = Form("other"),
    expires_at: Optional[datetime] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = DocumentsService(db)
    doc = await svc.upload_document(student_id, file, doc_type, category, expires_at)
    url = await svc.get_signed_url(student_id, doc_type)
    return DocumentUploadEnvelope(
        data=DocumentUploadResponse(
            id=doc.id,
            doc_type=doc.doc_type,
            category=doc.category,
            status=doc.status,
            url=url,
        )
    )


@router.delete("/students/{student_id}/documents/{doc_type}", response_model=SuccessResponse)
async def delete_document(
    student_id: UUID,
    doc_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
 ) -> SuccessResponse:
    svc = DocumentsService(db)
    await svc.delete_document(student_id, doc_type)
    return SuccessResponse()
