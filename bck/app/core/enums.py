"""The closed vocabularies the tables in ``core`` store.

The storage-side counterpart to :mod:`app.contracts.enums`. A state that crosses a module
boundary is defined in ``contracts`` and imported here, never restated — ``FieldState``,
``Verdict`` and ``DeclarationField`` all arrive that way. What lives in this file is the
vocabulary that only storage has an opinion about: how a scan arrived, how far it has got,
what basis exists for measuring it, what an officer did to it, and — since CORE-004 — what
kind of premises a package came from, where an escalation had got to, and what one consumer
asserted about a product.

Split out of :mod:`app.core.models` to keep that file inside the 300-line limit once the
review table landed. The division is vocabulary here, tables there; the tables that store
the last three live in :mod:`app.core.market` and :mod:`app.core.complaints`.
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


class VendorType(StrEnum):
    """What kind of premises a vendor operates.

    Three, because three is what the pilot distinguishes. This says nothing about
    obligations: a kirana and a supermarket are under identical declaration rules, and
    nothing in the verdict path reads this column.
    """

    GODOWN = "godown"
    """A storage premises. Stock in bulk, not yet on a shelf."""

    SUPERMARKET = "supermarket"
    """A self-service retail premises."""

    KIRANA = "kirana"
    """A neighbourhood retail shop — the majority of the retail estate."""


class ComplaintStatus(StrEnum):
    """Where an escalation had got to **when the row carrying it was written**.

    Not a lifecycle field, despite the name. :class:`app.core.complaints.ComplaintRow` is
    append-only in shape, so each row is an event and this is the state that event
    asserts; a transition is a new row whose ``supersedes_id`` names the one it replaces.
    The word "status" is the officer's, and the discipline behind it is the model's
    docstring, not this one.
    """

    RAISED = "raised"
    """The officer has escalated the verdict to the manufacturer."""

    ACKNOWLEDGED = "acknowledged"
    """The manufacturer has confirmed receipt. Says nothing about the substance."""

    RESOLVED = "resolved"
    """The escalation is closed as answered."""

    REJECTED = "rejected"
    """The escalation is closed as not accepted. Distinct from RESOLVED: closing a
    complaint and agreeing with it are different facts, and collapsing them would lose
    which one happened."""


class ConsumerSafetyClaim(StrEnum):
    """What one member of the public asserted about one product. **Not a verdict.**

    :class:`app.contracts.Verdict` is what this system recommends about a package and is
    PASS / REVIEW / POTENTIAL_VIOLATION for the reasons stated there. This is a consumer
    reporting their own experience, stored so it can be republished as theirs. The name
    carries that boundary rather than a docstring alone, because a column name survives
    into every downstream surface a docstring cannot follow.

    It is defined here and deliberately **not** in ``contracts``: ``contracts`` holds the
    vocabularies that cross a module boundary, so keeping this out of it means nothing in
    the verdict path can import this enum and therefore nothing in the verdict path can
    branch on it.

    Its values are lowercase against ``Verdict``'s uppercase, which is free structural
    separation — in a dump, a CSV export or a log line the two vocabularies are visually
    distinct and no string comparison can match across them.
    """

    SAFE = "safe"
    """The consumer reported no problem with the product."""

    UNSAFE = "unsafe"
    """The consumer reported a problem with the product. A report, never a finding: an
    aggregate of these reads "N consumers reported this product as unsafe", never "this
    product is unsafe"."""
