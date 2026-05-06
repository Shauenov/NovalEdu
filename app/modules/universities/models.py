import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class University(Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    international_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    qs_ranking: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    the_ranking: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    language_of_instr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_universities_country", "country"),
        Index("idx_universities_published", "is_published"),
    )


class UniversityProgram(Base):
    __tablename__ = "university_programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    degree_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    min_gpa: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    min_ielts: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    min_sat: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    tuition_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scholarship_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_fee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intake_seasons: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    campus_life: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_programs_university", "university_id"),
        Index("idx_programs_field", "field"),
    )
