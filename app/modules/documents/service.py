import io
import uuid
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import BUCKET_DOCUMENTS
from app.core.exceptions import NotFoundException
from app.storage.file_validator import validate_document
from app.storage.minio_client import upload_file, get_signed_url
from app.modules.documents.repository import DocumentsRepository


class DocumentsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DocumentsRepository(db)

    async def list_documents(self, student_id: uuid.UUID):
        docs = await self.repo.get_by_student(student_id)
        results = []
        for d in docs:
            url = get_signed_url(BUCKET_DOCUMENTS, d.object_key)
            results.append({"id": d.id, "student_id": d.student_id, "doc_type": d.doc_type, "url": url, "content_type": d.content_type, "size": d.size, "created_at": d.created_at})
        return results

    async def upload_document(self, student_id: uuid.UUID, file: UploadFile, doc_type: str):
        data = await file.read()
        # validate size and mime
        mime = validate_document(data, settings.max_document_size_bytes)

        # ensure single document per type — delete existing
        existing = await self.repo.get_by_student_and_type(student_id, doc_type)
        if existing:
            # remove from storage
            from app.storage.minio_client import delete_file

            delete_file(BUCKET_DOCUMENTS, existing.object_key)
            await self.repo.delete(existing)

        # upload
        key = f"{student_id}/{doc_type}/{uuid.uuid4().hex}"
        bio = io.BytesIO(data)
        upload_file(BUCKET_DOCUMENTS, key, bio, len(data), mime)

        doc = await self.repo.create(
            student_id=student_id,
            doc_type=doc_type,
            object_key=key,
            content_type=mime,
            size=len(data),
        )
        await self.db.commit()
        return doc

    async def get_signed_url(self, student_id: uuid.UUID, doc_type: str) -> str:
        doc = await self.repo.get_by_student_and_type(student_id, doc_type)
        if not doc:
            raise NotFoundException("Document not found")
        return get_signed_url(BUCKET_DOCUMENTS, doc.object_key)

    async def get_document(self, student_id: uuid.UUID, doc_type: str) -> dict:
        doc = await self.repo.get_by_student_and_type(student_id, doc_type)
        if not doc:
            raise NotFoundException("Document not found")
        url = get_signed_url(BUCKET_DOCUMENTS, doc.object_key)
        return {
            "id": doc.id,
            "student_id": doc.student_id,
            "doc_type": doc.doc_type,
            "url": url,
            "content_type": doc.content_type,
            "size": doc.size,
            "created_at": doc.created_at,
        }

    async def delete_document(self, student_id: uuid.UUID, doc_type: str) -> None:
        doc = await self.repo.get_by_student_and_type(student_id, doc_type)
        if not doc:
            raise NotFoundException("Document not found")
        from app.storage.minio_client import delete_file

        delete_file(BUCKET_DOCUMENTS, doc.object_key)
        await self.repo.delete(doc)
        await self.db.commit()
