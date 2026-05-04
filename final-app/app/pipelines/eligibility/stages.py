"""Eligibility-check stages — pure functions (Module 14)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class _ScreeningLike(Protocol):
    age: int
    sex: str
    diagnosis: str
    medications: list[str]
    is_pregnant: bool
    has_liver_disease: bool
    in_other_trial: bool


@dataclass(frozen=True)
class StageResult:
    name: str
    passed: bool
    reason: str = ""


Stage = Callable[[_ScreeningLike], StageResult]


def check_age(s: _ScreeningLike) -> StageResult:
    if 18 <= s.age <= 75:
        return StageResult("age", True)
    return StageResult("age", False, f"age {s.age} not in [18,75]")


def check_diagnosis(s: _ScreeningLike) -> StageResult:
    if s.diagnosis == "Type 2 Diabetes":
        return StageResult("diagnosis", True)
    return StageResult(
        "diagnosis", False, f"diagnosis must be Type 2 Diabetes (got {s.diagnosis!r})"
    )


def check_medications(s: _ScreeningLike) -> StageResult:
    if len(s.medications or []) >= 1:
        return StageResult("medications", True)
    return StageResult("medications", False, "must be on stable medication (≥1 med)")


def check_pregnancy(s: _ScreeningLike) -> StageResult:
    if not s.is_pregnant:
        return StageResult("pregnancy", True)
    return StageResult("pregnancy", False, "subjects who are pregnant are excluded")


def check_liver_disease(s: _ScreeningLike) -> StageResult:
    if not s.has_liver_disease:
        return StageResult("liver_disease", True)
    return StageResult("liver_disease", False, "history of liver disease excludes")


def check_other_trial(s: _ScreeningLike) -> StageResult:
    if not s.in_other_trial:
        return StageResult("other_trial", True)
    return StageResult("other_trial", False, "subjects in another trial are excluded")


ALL_STAGES: list[Stage] = [
    check_age,
    check_diagnosis,
    check_medications,
    check_pregnancy,
    check_liver_disease,
    check_other_trial,
]
