"""The closed vocabularies the scan-path tables store.

The storage-side counterpart to :mod:`app.contracts.enums`. A state that crosses a module
boundary is defined in ``contracts`` and imported here, never restated — ``FieldState``,
``Verdict`` and ``DeclarationField`` all arrive that way. What lives in this file is the
vocabulary that only storage has an opinion about: how a scan arrived, how far it has got,
what basis exists for measuring it, and what an officer did to it.

Split out of :mod:`app.core.models` to keep that file inside the 300-line limit once the
review table landed. The division is vocabulary here, tables there.
"""

from enum import StrEnum


class ScanSourceType(StrEnum):
    """Which ingestion path a scan arrived by.

    Both are first-class. A listing is not an image that failed to be an image, and
    modelling it as its own source type is what keeps a marketplace adapter an adapter.
    """

    PHYSICAL_LABEL = "physical_label"
    """An image of a package captured by an officer."""

    CATALOGUE_RECORD = "catalogue_record"
    """A structured listing — see :class:`app.contracts.CatalogueRecord`."""


class ScanStatus(StrEnum):
    """Where a scan has got to. Processing state, never a compliance outcome."""

    RECEIVED = "received"
    """Accepted and stored; evaluation has not started."""

    PROCESSING = "processing"
    """Somewhere between the quality gate and verdict assembly."""

    COMPLETE = "complete"
    """Evaluation finished and a verdict was written. Says nothing about what it was."""

    FAILED = "failed"
    """Processing did not finish. Distinct from every verdict: a scan that crashed has
    no finding about the package at all."""


class CalibrationMethod(StrEnum):
    """What basis, if any, exists for a physical measurement of this scan.

    Recorded at capture because it decides whether a millimetre figure may be emitted at
    all. Typed rather than buried in :attr:`Scan.capture_metadata` for that reason — a
    value that gates a legal output is queryable and constrained, not a key in a blob.
    """

    ARTWORK = "artwork"
    """Pre-print artwork was supplied; physical sizes are known exactly."""

    REFERENCE_OBJECT = "reference_object"
    """An object of known dimensions is in frame, so a measurement carries an interval."""

    NONE = "none"
    """Neither. Measurement refuses and routes to review; it does not guess."""


class ReviewAction(StrEnum):
    """What an officer did to a verdict. The human confirmation step, as a vocabulary.

    Three of these finalise and two do not, and the difference is the whole point of the
    table: no automated path may reach a finalised state, so finalisation is the existence
    of a row carrying one of the first three actions and is never a column somewhere that
    a background job could set.
    """

    CONFIRM = "confirm"
    """The officer agrees with the recommendation and adopts it. Finalising."""

    REJECT = "reject"
    """The officer disagrees and discards the recommendation. Finalising."""

    OVERRIDE = "override"
    """The officer substitutes a different verdict, recorded alongside in
    :attr:`app.core.models.ReviewRow.overridden_verdict`. Finalising."""

    ANNOTATE = "annotate"
    """The officer records a note without deciding. Not finalising — an annotation is
    evidence about the review, not the end of it."""

    REQUEST_RECAPTURE = "request_recapture"
    """The officer wants the package photographed again. Not finalising, and not a
    finding about the package: it says the evidence was inadequate, which is the same
    thing INSUFFICIENT_EVIDENCE says about one field."""
