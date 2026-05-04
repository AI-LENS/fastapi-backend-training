"""Run eligibility stages and collect results (Module 14)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.pipelines.eligibility.stages import ALL_STAGES, StageResult

logger = logging.getLogger(__name__)


@dataclass
class EligibilityOutcome:
    eligible: bool
    failed_criteria: list[str]
    stage_results: list[StageResult]


async def run_pipeline(
    screening,
    *,
    on_stage_complete=None,
) -> EligibilityOutcome:
    """Run every stage. Cooperative — yields between stages so cancellation lands cleanly."""
    results: list[StageResult] = []

    for stage in ALL_STAGES:
        await asyncio.sleep(0)  # cooperative cancellation point
        result = stage(screening)
        results.append(result)
        if on_stage_complete is not None:
            await on_stage_complete(result)
        logger.debug("stage %s -> %s (%s)", result.name, result.passed, result.reason)

    failed = [r.name for r in results if not r.passed]
    return EligibilityOutcome(
        eligible=not failed,
        failed_criteria=failed,
        stage_results=results,
    )
