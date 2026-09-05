"""Evaluation package for LMPC compliance ground-truth benchmarking."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datasets.eval.harness import (
        ComplianceEvaluator,
        EvaluationReport,
        MetricScores,
    )

__all__ = ["ComplianceEvaluator", "EvaluationReport", "MetricScores"]


def __getattr__(name: str):
    if name in __all__:
        from datasets.eval import harness

        return getattr(harness, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
