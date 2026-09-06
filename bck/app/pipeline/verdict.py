"""Assemble per-field findings into the package-level verdict record.

Deterministic and pure. No clock, no I/O, no network, no model, no agent loop — the
evaluation instant is a parameter, so replaying the same findings returns the same record
byte for byte. That is not a performance choice: a verdict an officer acted on has to be
reproducible on demand, and anything that reads the world at assembly time makes it not.

The derivation is deliberately four separate passes rather than one classification:

    any FAIL                                  -> POTENTIAL_VIOLATION
    else any REVIEW_REQUIRED                  -> REVIEW
    else any INSUFFICIENT_EVIDENCE            -> REVIEW
    else                                      -> PASS

REVIEW_REQUIRED and INSUFFICIENT_EVIDENCE reach the same verdict, and they are still
tested one at a time and never grouped in a membership check. A set literal holding both
is one careless edit away from a set that also holds FAIL, and that edit would make the
system report "we could not read the label" as "the label is wrong". FAIL is a statement
about the package; INSUFFICIENT_EVIDENCE is a statement about our reading of it. Only the
first can support enforcement, so the two never share an expression here.

NOT_APPLICABLE matches no branch and falls through to PASS. A statutory carve-out means
the obligation does not exist for this package, which is not a lesser PASS and not a
softened FAIL.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from app.contracts import (
    DeclarationField,
    EvidenceProvider,
    FieldFinding,
    FieldState,
    Verdict,
    VerdictRecord,
)


def derive_verdict(findings: Sequence[FieldFinding]) -> Verdict:
    """The package-level recommendation implied by ``findings``.

    Total: every input returns a verdict, including no findings at all. Nothing was
    examined, so nothing can be asserted about the package — that routes to an officer,
    never to PASS. A system that returns PASS when it looked at nothing is worse than one
    that returns nothing.

    Recommendation only. POTENTIAL_VIOLATION says legible evidence indicates a shortfall
    an officer should examine; it is not a finding of contravention, and a human
    confirmation sits between this value and any action taken against anyone.
    """
    if not findings:
        return Verdict.REVIEW
    if any(finding.state is FieldState.FAIL for finding in findings):
        return Verdict.POTENTIAL_VIOLATION
    if any(finding.state is FieldState.REVIEW_REQUIRED for finding in findings):
        return Verdict.REVIEW
    if any(finding.state is FieldState.INSUFFICIENT_EVIDENCE for finding in findings):
        return Verdict.REVIEW
    return Verdict.PASS


def assemble_verdict(
    *,
    subject_ref: str,
    findings: Sequence[FieldFinding],
    rule_set_version: str,
    evaluated_at: datetime,
    field_providers: Mapping[DeclarationField, EvidenceProvider] | None = None,
) -> VerdictRecord:
    """Build the complete evidence record for one evaluation.

    ``evaluated_at`` is passed in rather than read from a clock. Rule applicability was
    resolved against that instant upstream, and the record has to agree with the
    evaluation that produced it rather than with whenever assembly happened to run.

    ``findings`` must be non-empty. :func:`derive_verdict` answers REVIEW for an empty
    sequence, but :class:`~app.contracts.VerdictRecord` refuses to construct without at
    least one finding — a verdict with no findings behind it has no evidence chain. Both
    are correct and they do not conflict: the derivation is total so a caller can ask what
    an empty result would mean, while the record type declines to record it. A caller
    holding no findings has a capture or evaluation failure to report, not a verdict to
    store, and the ``ValidationError`` raised here says so.
    """
    return VerdictRecord(
        subject_ref=subject_ref,
        verdict=derive_verdict(findings),
        rule_set_version=rule_set_version,
        evaluated_at=evaluated_at,
        findings=tuple(findings),
        field_providers=dict(field_providers or {}),
    )
