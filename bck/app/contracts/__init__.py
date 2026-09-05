"""Shared vocabulary for PCCS — the types that cross a module boundary.

The bottom layer. This package imports nothing from ``app`` and depends on nothing but
Pydantic and the standard library; every other layer imports from it. That direction is
enforced by ``lint-imports`` in CI, not by convention.

Import from the package, not from its files::

    from app.contracts import DeclarationField, FieldState, VerdictRecord

The split into modules here is an internal detail. Importing through this surface means
rearranging files inside ``contracts/`` is not a change to six other people's imports.
"""

from app.contracts.base import ContractModel
from app.contracts.enums import (
    DeclarationField,
    EvidenceProvider,
    FieldState,
    RuleSeverity,
    RuleStatus,
    ToleranceBasis,
    Verdict,
)
from app.contracts.evidence import ExtractedSpan, NormalisedField, Point
from app.contracts.measurement import (
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementRefusal,
    MeasurementResult,
)
from app.contracts.records import (
    CatalogueRecord,
    FieldFinding,
    RuleParameterSnapshot,
    VerdictRecord,
)
from app.contracts.rules import RuleDefinition, RuleSetVersion

__all__ = [
    "CatalogueRecord",
    "ContractModel",
    "DeclarationField",
    "EvidenceProvider",
    "ExtractedSpan",
    "FieldFinding",
    "FieldState",
    "MeasurementCalibrated",
    "MeasurementExact",
    "MeasurementRefusal",
    "MeasurementResult",
    "NormalisedField",
    "Point",
    "RuleDefinition",
    "RuleParameterSnapshot",
    "RuleSetVersion",
    "RuleSeverity",
    "RuleStatus",
    "ToleranceBasis",
    "Verdict",
    "VerdictRecord",
]
