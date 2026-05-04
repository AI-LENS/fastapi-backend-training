"""Pydantic schemas for the Screening resource."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Sex(str, Enum):
    M = "M"
    F = "F"


class ScreeningCreate(BaseModel):
    site_id: str = Field(..., examples=["SITE-001"])
    candidate_initials: str = Field(..., min_length=1, max_length=4)
    age: int = Field(..., ge=0, le=120)
    sex: Sex
    diagnosis: str = Field(..., examples=["Type 2 Diabetes"])
    medications: list[str] = Field(default_factory=list)
    is_pregnant: bool = False
    has_liver_disease: bool = False
    in_other_trial: bool = False


class ScreeningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_id: str
    candidate_initials: str
    age: int
    sex: Sex
    diagnosis: str
    medications: list[str]
    status: str
    eligibility_result: str | None
    failed_criteria: list[str] | None
    subject_id: str | None
    created_at: datetime
    enrolled_at: datetime | None


class ScreeningListResponse(BaseModel):
    items: list[ScreeningResponse]
    next_cursor: str | None = None
