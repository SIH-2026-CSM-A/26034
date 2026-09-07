"""Request and response shapes for the scan endpoints.

DTOs, not ORM rows and not contract types. What a route accepts and returns is a decision
about the HTTP surface; what a module exchanges with another module is
:mod:`app.contracts`; what survives a restart is :mod:`app.core.models`. Keeping them
apart is what lets the API gain a field without a migration, and the schema change
without an API change.

**Every response carries the rule-set version.** Not as a courtesy: a finding is only
meaningful against the rules that produced it, and a client that renders a verdict without
knowing which published set it came from cannot tell a re-evaluation from a contradiction.
:class:`RuleSetStamped` is the base rather than a field people remember to add.

**A request may not describe the caller's own authority.** There is no officer, tier or
jurisdiction field anywhere below. Those come from a verified token, and an endpoint that
read one from a body would be scoping its queries with data chosen by the person being
scoped.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts import CatalogueRecord, FieldFinding, Verdict
from app.core import CalibrationMethod, ReviewAction, ScanSourceType, ScanStatus
from app.modules.rules import ProductCategory
from app.pipeline.capture import QualityRejection


class ScanDTO(BaseModel):
    """Base for every shape on this surface. Rejects unknown fields on the way in."""

    model_config = ConfigDict(extra="forbid")


class RuleSetStamped(ScanDTO):
    """A response that names the published rule set behind it."""

    rule_set_version: str = Field(min_length=1)


class CatalogueScanRequest(ScanDTO):
    """The listing ingestion path. A first-class input, not an adapter over the image one."""

    record: CatalogueRecord

    product_category: ProductCategory | None = None
    """The officer's confirmed product category, if they have confirmed one.

    Typed as the rules module's own vocabulary, so a category the sector dispatch does not
    recognise is refused here with a 422 rather than stored and silently failing to route
    an override. ``None`` means unconfirmed, and unconfirmed is not an error — it makes
    every obligation a sector could carve out INSUFFICIENT_EVIDENCE instead of evaluated.
    """

    institutional_or_industrial_confirmed: bool = False
    """Whether the officer has confirmed this package is supplied to an industrial or
    institutional consumer, which Rule 3(c) places outside Chapter II.

    Defaults to ``False``, which confirms nothing and changes nothing. A ``True`` makes
    every Chapter II obligation NOT_APPLICABLE — the duty does not arise — so it is an
    officer's assertion and never an inference from the listing.
    """


class ScanSummary(RuleSetStamped):
    """One scan as it appears in a list. No findings — those are on the detail route."""

    id: UUID
    source_type: ScanSourceType
    status: ScanStatus
    verdict: Verdict | None = None
    product_category: str | None = None
    officer_id: str
    created_at: datetime
    finalised: bool
    """Whether an officer has confirmed, rejected or overridden this scan's verdict.

    Derived from the existence of a review row carrying a finalising action, never stored
    as a flag: a column could be set by something other than an officer, and the point of
    this field is that nothing else can.
    """


class ScanDetail(ScanSummary):
    """One scan in full: its findings, or the capture instruction that replaced them."""

    subject_ref: str | None = None
    evaluated_at: datetime | None = None
    findings: tuple[FieldFinding, ...] = ()
    quality: QualityRejection | None = None
    """Present only where the quality gate refused the capture. A scan carrying this has
    no verdict and no findings, and that is the whole of what it says: we could not read
    the photograph, which is not a statement about the package."""


class ReviewRequest(ScanDTO):
    """An officer's action on a verdict."""

    action: ReviewAction
    note: str | None = Field(default=None, max_length=4000)
    """The officer's own words. Required for every action but CONFIRM — a rejection or an
    override nobody explained is not reviewable by the next person to read it."""

    overridden_verdict: Verdict | None = None
    """The verdict substituted, for OVERRIDE and nothing else. Still one of the three:
    an officer's substitution is a recommendation reaching a workflow, not a legal
    determination, so there is no value here the automated path could not also reach."""

    supersedes_id: UUID | None = None
    """The earlier review this one corrects. Both rows survive; nothing is edited."""

    @model_validator(mode="after")
    def _parts_agree(self) -> "ReviewRequest":
        """Reject a review whose parts contradict each other, before anything is written.

        Here rather than in the route because it is a fact about the shape of a review,
        not about HTTP: an override that names no substituted verdict has not said what
        the officer decided, and a rejection nobody explained is not reviewable by the
        next person to read it. Refusing to construct one means no such row can be built
        by any caller, including a future one that is not a route.
        """
        if self.action is ReviewAction.OVERRIDE and self.overridden_verdict is None:
            raise ValueError("an override must state the verdict it substitutes")
        if self.action is not ReviewAction.OVERRIDE and self.overridden_verdict is not None:
            raise ValueError("only an override may state a substituted verdict")
        if self.action is not ReviewAction.CONFIRM and not (self.note or "").strip():
            raise ValueError(
                f"a {self.action.value} must say why, so the next reader can follow it"
            )
        return self


class ReviewResponse(RuleSetStamped):
    """The review as recorded."""

    id: UUID
    scan_id: UUID
    verdict_id: UUID
    action: ReviewAction
    officer_id: str
    note: str | None
    overridden_verdict: Verdict | None
    supersedes_id: UUID | None
    created_at: datetime
    finalised: bool


class ScanFilters(ScanDTO):
    """The repository filters ``GET /scans`` accepts.

    Jurisdiction is deliberately absent. It is not a filter the caller chooses — it is
    applied from their verified token on every query, and a client cannot widen it.
    """

    product: str | None = None
    """Matches the common or generic name read off the package or listing."""

    manufacturer: str | None = None
    """Matches the name and address declaration."""

    status: ScanStatus | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ImageCalibration(ScanDTO):
    """What basis the officer says exists for measuring this capture.

    Stated at capture rather than inferred, because it decides whether a millimetre figure
    may be emitted at all. A claim of ``REFERENCE_OBJECT`` with no reference the
    measurement module can find still yields a refusal — this says what to look for, not
    what was found.
    """

    method: CalibrationMethod = CalibrationMethod.NONE
    reference_type: str | None = None
    artwork_dpi: float | None = Field(default=None, gt=0)
