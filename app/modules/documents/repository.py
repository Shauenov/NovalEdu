from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import StudentDocument


class DocumentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> StudentDocument:
        doc = StudentDocument(**kwargs)
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_by_student(self, student_id: UUID) -> list[StudentDocument]:
        result = await self.db.execute(select(StudentDocument).where(StudentDocument.student_id == student_id))
        return result.scalars().all()

    async def get_by_student_and_type(self, student_id: UUID, doc_type: str) -> StudentDocument | None:
        result = await self.db.execute(
            select(StudentDocument).where(StudentDocument.student_id == student_id, StudentDocument.doc_type == doc_type)
        )
        return result.scalar_one_or_none()

    async def delete(self, doc: StudentDocument) -> None:
        await self.db.delete(doc)
        await self.db.flush()

    async def delete_by_student_and_type(self, student_id: UUID, doc_type: str) -> int:
        result = await self.db.execute(delete(StudentDocument).where(StudentDocument.student_id == student_id, StudentDocument.doc_type == doc_type))
        return result.rowcount
