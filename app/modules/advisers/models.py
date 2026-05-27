import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdviserProfile(Base):
    """Public-facing consultant profile (bio, skills, headline stats).

    One-to-one with a `users` row whose role is `adviser`.
    """

    __tablename__ = "adviser_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)  # "Senior Admission Consultant"
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array as text
    students_placed: Mapped[int | None] = mapped_column(Integer, nullable=True)       # "450+"
    scholarships_won_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)  # "$12M"
    years_experience: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
