"""Screening ORM model."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Screening(Base, TimestampMixin):
    __tablename__ = "screenings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    site_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    candidate_initials: Mapped[str] = mapped_column(String(4), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(1), nullable=False)
    diagnosis: Mapped[str] = mapped_column(String(200), nullable=False)
    medications: Mapped[list[str]] = mapped_column(JSON, default=list)

    is_pregnant: Mapped[bool] = mapped_column(Boolean, default=False)
    has_liver_disease: Mapped[bool] = mapped_column(Boolean, default=False)
    in_other_trial: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="submitted", index=True
    )
    eligibility_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    failed_criteria: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_screenings_site_status", "site_id", "status"),
    )
