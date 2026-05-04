"""Eligibility pipeline (Module 14)."""
from app.pipelines.eligibility.orchestrator import EligibilityOutcome, run_pipeline
from app.pipelines.eligibility.stages import StageResult

__all__ = ["run_pipeline", "EligibilityOutcome", "StageResult"]
