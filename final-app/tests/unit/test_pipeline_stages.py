"""Unit tests for the eligibility pipeline stages (Module 22)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.pipelines.eligibility.stages import (
    check_age,
    check_diagnosis,
    check_liver_disease,
    check_medications,
    check_other_trial,
    check_pregnancy,
)


def _s(**fields):
    defaults = {
        "age": 40,
        "sex": "F",
        "diagnosis": "Type 2 Diabetes",
        "medications": ["metformin"],
        "is_pregnant": False,
        "has_liver_disease": False,
        "in_other_trial": False,
    }
    return SimpleNamespace(**{**defaults, **fields})


@pytest.mark.parametrize(
    "age,passed",
    [(-1, False), (0, False), (17, False), (18, True), (40, True), (75, True), (76, False), (120, False)],
)
def test_check_age(age, passed):
    assert check_age(_s(age=age)).passed is passed


@pytest.mark.parametrize(
    "diagnosis,passed",
    [
        ("Type 2 Diabetes", True),
        ("Type 1 Diabetes", False),
        ("Hypertension", False),
    ],
)
def test_check_diagnosis(diagnosis, passed):
    assert check_diagnosis(_s(diagnosis=diagnosis)).passed is passed


@pytest.mark.parametrize("count,passed", [(0, False), (1, True), (5, True)])
def test_check_medications(count, passed):
    meds = [f"med{i}" for i in range(count)]
    assert check_medications(_s(medications=meds)).passed is passed


def test_pregnancy_excludes():
    assert check_pregnancy(_s(is_pregnant=True)).passed is False
    assert check_pregnancy(_s(is_pregnant=False)).passed is True


def test_liver_disease_excludes():
    assert check_liver_disease(_s(has_liver_disease=True)).passed is False


def test_other_trial_excludes():
    assert check_other_trial(_s(in_other_trial=True)).passed is False
