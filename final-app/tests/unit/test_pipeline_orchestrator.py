"""Tests for the pipeline orchestrator with composed real stages."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.pipelines.eligibility import run_pipeline


def _eligible():
    return SimpleNamespace(
        age=40, sex="F", diagnosis="Type 2 Diabetes",
        medications=["metformin"],
        is_pregnant=False, has_liver_disease=False, in_other_trial=False,
    )


@pytest.mark.asyncio
async def test_eligible_passes_all():
    outcome = await run_pipeline(_eligible())
    assert outcome.eligible is True
    assert outcome.failed_criteria == []


@pytest.mark.asyncio
async def test_pregnant_excluded():
    s = _eligible()
    s.is_pregnant = True
    outcome = await run_pipeline(s)
    assert outcome.eligible is False
    assert "pregnancy" in outcome.failed_criteria


@pytest.mark.asyncio
async def test_multiple_failures_listed():
    s = SimpleNamespace(
        age=10, sex="F", diagnosis="Hypertension", medications=[],
        is_pregnant=True, has_liver_disease=False, in_other_trial=False,
    )
    outcome = await run_pipeline(s)
    assert outcome.eligible is False
    assert {"age", "diagnosis", "medications", "pregnancy"}.issubset(set(outcome.failed_criteria))


@pytest.mark.asyncio
async def test_on_stage_callback_invoked():
    seen: list[str] = []

    async def cb(result):
        seen.append(result.name)

    await run_pipeline(_eligible(), on_stage_complete=cb)
    assert "age" in seen and "diagnosis" in seen and "pregnancy" in seen
