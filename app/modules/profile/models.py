import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    group_type: Mapped[str] = mapped_column(String(2), nullable=False)        # D1 | D2 | F1 | F2 | F3 | F4
    course_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)    # 2 | 3
    gpa: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ielts_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    ielts_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    ielts_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sat_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    sat_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    sat_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ent_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    kta_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    target_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_major: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Personal info (Личная информация screen)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)   # male | female | other
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Application settings (Настройки поступления screen)
    degree_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # bachelor | master | phd
    target_countries: Mapped[str | None] = mapped_column(Text, nullable=True)    # JSON array as text
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intake_semester: Mapped[str | None] = mapped_column(String(20), nullable=True)  # fall_2024 | spring_2025
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
