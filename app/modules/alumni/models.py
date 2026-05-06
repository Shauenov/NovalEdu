import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlumniStory(Base):
    __tablename__ = "alumni_stories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    graduation_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    university_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id"), nullable=True
    )
    university_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    program_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    scholarship_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    story_text: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gpa_at_time: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ielts_at_time: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    sat_at_time: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
