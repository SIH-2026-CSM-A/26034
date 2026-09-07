"""Closed vocabularies shared across every module.

Every member carries a docstring stating its legal or operational meaning. These are
not stylistic labels — an officer acts on them, and an evidence export reproduces them.
Widening one of these enums changes the meaning of every stored record that used it, so
they are single-owner and changed only through a contracts pull request.
"""

from enum import StrEnum


class FieldState(StrEnum):
    """The outcome of evaluating one declaration field against one rule.

    Five states, deliberately. Four would force "we could not read it" and "it is not
    there" into the same bucket.
    """

    PASS = "PASS"
    """The declaration is present, legible, and satisfies the rule as evaluated."""

    FAIL = "FAIL"
    """The declaration was read successfully and does not satisfy the rule.

    This is a positive finding about the package: the evidence was legible and what it
    says falls short of the requirement. It is never used for evidence we could not
    obtain — see :attr:`INSUFFICIENT_EVIDENCE`.
    """

    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    """The rule cannot be resolved without human judgement.

    Evidence exists and is legible, but applying the rule to it needs a person: a
    borderline measurement, a sector carve-out whose applicability is contested, or two
    readings that disagree. Routes to an officer, never straight to an outcome.
    """

    NOT_APPLICABLE = "NOT_APPLICABLE"
    """The rule does not apply to this package.

    A statutory carve-out or exemption removes the obligation entirely — for example the
    Rule 26 exemption for packages of 10 g or 10 ml or less, the Rule 7(5) exception
    where the same information is required under another law, or the medical-devices
    routing under G.S.R. 778(E). Absence of the declaration is lawful here, so this is
    not a lesser form of PASS and not a softened FAIL.
    """

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    """The evidence needed to evaluate the rule could not be obtained.

    **This is not FAIL, and collapsing the two is a wrongful-flag liability rather than
    a style choice.** FAIL asserts something about the package: the declaration was read
    and falls short. INSUFFICIENT_EVIDENCE asserts something about the observation: the
    panel was glared, the crop was cut, the text was too small to resolve, no reference
    object was in frame. "We could not see it" and "it is not there" carry different
    legal consequences — one is a defect in the package, the other is a defect in our
    reading of it, and only the first can support enforcement.

    Anything in this state routes to human review with the reason recorded, and it never
    contributes to a POTENTIAL_VIOLATION verdict on its own.
    """


class Verdict(StrEnum):
    """The package-level recommendation assembled from the per-field findings.

    Three members. The system recommends and a human confirms, so there is no member for
    a confirmed breach — no "violation confirmed", no "non-compliant". Adding one would
    make the software issue a legal determination it has no standing to issue.
    """

    PASS = "PASS"
    """No field finding requires action. Nothing was found that warrants an officer."""

    REVIEW = "REVIEW"
    """An officer must look at this before anything else happens.

    Reached when evidence was insufficient, when a rule needed human judgement, or when
    a carve-out's applicability could not be established from the evidence available.
    """

    POTENTIAL_VIOLATION = "POTENTIAL_VIOLATION"
    """Legible evidence indicates one or more declarations fall short of the Rules.

    A recommendation for an officer to examine, not a finding of contravention. No
    enforcement step follows from this value alone; a human confirmation sits between
    this and any action taken against a manufacturer, packer or importer.
    """


class DeclarationField(StrEnum):
    """The declarations a package must bear, one member per obligation.

    Clause letters are taken from the Legal Metrology (Packaged Commodities) Rules 2011
    as consolidated in ``rules-corpus/``. One member per clause, not per role: Rule
    6(1)(a) is a single obligation covering manufacturer, packer and importer, and by
    Explanation II the marketer or brand owner as well. Which role a given declaration
    was made under is a property of the extracted value, not a separate obligation.
    """

    NAME_AND_ADDRESS = "NAME_AND_ADDRESS"
    """Rule 6(1)(a) — name and address of the manufacturer, or of the manufacturer and
    packer where they differ, or of the importer for an imported package.

    Explanation I attributes an unqualified name and address to the manufacturer.
    Explanation II makes a brand owner appearing as marketer responsible. Explanation III
    disapplies this clause for food articles, where the Food Safety and Standards Act,
    2006 governs instead.
    """

    COUNTRY_OF_ORIGIN = "COUNTRY_OF_ORIGIN"
    """Rule 6(1)(aa) — "The name of the country of origin or manufacture or assembly in
    case of imported products shall be mentioned on the package".

    This member is the declaration *on the package*, which is the obligation a scan can
    evaluate.

    Two separate provisions govern country of origin and they are not interchangeable.
    The second is **Rule 6(10A)**, inserted by G.S.R. 128(E) with effect from 1 July 2026
    and substituted by G.S.R. 312(E) with effect from 1 July 2027: "Every e-commerce
    entity offering for sale any imported product shall ... ensure that the product
    listing of such imported product contains a searchable and sortable filter specifying
    the country of origin." That is an obligation on the e-commerce entity about how a
    listing is presented, not a declaration borne by the package, and it is evaluated
    against a :class:`~app.contracts.records.CatalogueRecord` rather than against a scan.
    It has no field of its own here because it is not a declaration.

    Neither provision routes through Rule 6(1)(g). The catch-all limb is for matter
    specified elsewhere in the Rules with no express clause of its own; country of origin
    has clause (aa).
    """

    COMMON_OR_GENERIC_NAME = "COMMON_OR_GENERIC_NAME"
    """Rule 6(1)(b) — the common or generic name of the commodity, and for a package
    holding more than one product, the name and number or quantity of each."""

    NET_QUANTITY = "NET_QUANTITY"
    """Rule 6(1)(c) — net quantity in the standard unit of weight or measure, or the
    number of articles where the commodity is sold by count."""

    MANUFACTURE_DATE = "MANUFACTURE_DATE"
    """Rule 6(1)(d) — the month and year of manufacture.

    Provisos route food articles and cosmetics to other law, and exempt certified seed.
    """

    BEST_BEFORE_DATE = "BEST_BEFORE_DATE"
    """Rule 6(1)(da) — best before or use by date, month and year, where the commodity
    may become unfit for human consumption after a period of time."""

    RETAIL_SALE_PRICE = "RETAIL_SALE_PRICE"
    """Rule 6(1)(e) — the retail sale price, declared as the maximum retail price
    inclusive of all taxes in Indian currency."""

    DIMENSIONS = "DIMENSIONS"
    """Rule 6(1)(f) — dimensions of the commodity where its size is relevant, and of each
    differing piece where pieces differ."""

    OTHER_PRESCRIBED_MATTER = "OTHER_PRESCRIBED_MATTER"
    """Rule 6(1)(g) — such other matter as is specified elsewhere in the Rules.

    The catch-all limb. A rule encoded against a specific later provision addresses that
    provision by clause reference; this member exists so a finding under 6(1)(g) has a
    field to attach to.
    """

    CONSUMER_CARE = "CONSUMER_CARE"
    """Rule 6(2) — name, address, telephone number and e-mail address of the person who
    can be contacted about a consumer complaint."""

    UNIT_SALE_PRICE = "UNIT_SALE_PRICE"
    """Rule 6(11) — the unit sale price.

    A format rule: it prescribes the unit basis the price must be declared on, keyed to
    the net quantity. It states no tolerance and no rounding increment.
    """


class EvidenceProvider(StrEnum):
    """What produced a piece of evidence.

    Recorded per span and per field so an evidence bundle can state where every value
    came from. A closed set, because an unvalidated provider string reaching an export
    as three spellings of the same engine breaks the chain it exists to document.
    """

    PADDLEOCR = "PADDLEOCR"
    """Self-hosted PaddleOCR. The primary text provider and the only one guaranteed
    available offline."""

    TESSERACT = "TESSERACT"
    """Self-hosted Tesseract, character-whitelisted, used to re-read numeric declarations
    where a second independent reading is worth having."""

    CLOUD_OCR = "CLOUD_OCR"
    """A third-party hosted OCR service. An opt-in per-request escalation, disabled by
    default and bounded by a cost ceiling. Its presence on a span means the image left
    the sovereign boundary, which is why it is recorded rather than inferred."""

    ARTWORK = "ARTWORK"
    """A pre-print artwork or source file, not a photograph. Values from this provider
    are exact by construction — no calibration is involved and none is claimed."""

    CATALOGUE = "CATALOGUE"
    """A structured listing record supplied by an e-commerce catalogue, rather than read
    off an image."""

    MANUAL = "MANUAL"
    """Entered or corrected by an officer. Carries a human's judgement, so it overrides
    an automated reading and is recorded as such."""


class EvidenceAssetType(StrEnum):
    """What a stored piece of evidence *is*, for the purpose of deciding when it is destroyed.

    The counterpart to :class:`EvidenceProvider`, which records what produced a piece of
    evidence. This records what the thing is, and it is the field a retention window is
    read from — so it is inside :func:`app.modules.evidence.chain.compute_entry_hash`.
    Outside the hash an entry could be relabelled, fall under a different retention rule,
    and chain verification would still report the chain intact.

    Deliberately short. A member ships only alongside something that consumes it — a
    retention window, a purge branch, or a hash input — so this is the set the retention
    rules actually distinguish today and not a complete taxonomy of evidence. Adding a
    member later needs a hand-written ``ALTER TYPE ... ADD VALUE``, which cannot run inside
    a transaction and which ``alembic check`` does not report as drift.
    """

    PRODUCT_IMAGE = "PRODUCT_IMAGE"
    """The captured photograph of the package. Takes the default retention window, and is
    the asset a legal hold protects."""

    PERSONAL_DATA = "PERSONAL_DATA"
    """Personal identifiers and geolocation. Takes the shorter statutory window; that
    different window is the only reason this is distinct from PRODUCT_IMAGE, and the two
    kinds are one member because no rule tells them apart."""

    AUDIT_LOG = "AUDIT_LOG"
    """The chain's own entries, including purge records. Never purged: an audit trail that
    could expire cannot evidence the purges it records."""


class RuleStatus(StrEnum):
    """Whether an encoded rule has been checked against its gazette source."""

    VERIFIED = "VERIFIED"
    """The rule text and every parameter were read out of the cited gazette document and
    confirmed against it. Safe to evaluate against."""

    UNVERIFIED = "UNVERIFIED"
    """Encoded but not yet confirmed against the primary source — sourced from a
    secondary report, a compilation, or an earlier project document. Findings produced by
    an unverified rule cannot stand on their own and route to review."""


class ToleranceBasis(StrEnum):
    """How a rule's tolerance figure is to be read.

    ``Decimal("0.05")`` alone is ambiguous: five paise, or five percent. The Rules use
    both — the First Schedule states maximum permissible error as a percentage of the
    declared quantity, while a money tolerance is an absolute amount.
    """

    ABSOLUTE = "ABSOLUTE"
    """The tolerance is an amount in the field's own unit — rupees, grams, millimetres."""

    PERCENTAGE = "PERCENTAGE"
    """The tolerance is a percentage of the declared value."""


class RuleSeverity(StrEnum):
    """How a breach of this rule routes in the officer workflow.

    Operational routing, not a legal grading. No gazette grades contraventions by
    severity, so this must not be presented to an officer as a statement about how
    serious a breach is in law.
    """

    MANDATORY = "MANDATORY"
    """An express, unconditional obligation. A legible shortfall can support a
    POTENTIAL_VIOLATION verdict."""

    CONDITIONAL = "CONDITIONAL"
    """The obligation applies only where a condition holds. Where the evidence cannot
    establish whether the condition holds, the finding routes to review rather than
    resolving either way."""

    ADVISORY = "ADVISORY"
    """Guidance or good practice with no standalone obligation behind it. Never raises a
    verdict above REVIEW on its own."""


class ProductCategory(StrEnum):
    """A *confirmed* product category that a sector override may key on.

    Confirmed is the operative word. A category is an input to routing, never an
    inference this system makes: routing a package to another Act because a classifier
    guessed at its category would move a real legal obligation on a guess. A caller with
    no confirmed category passes ``None`` and the packaged rules apply unchanged.

    A member exists here because a gazette names that sector and routes an obligation
    away from these Rules for it — not because the sector is commercially interesting.
    Adding one is adding a routing target, so it comes with the provision that does the
    routing.

    The values are lowercase where every other vocabulary in this package is upper. That
    is deliberate and not to be tidied: they are the ``sector`` keys in the rule store's
    ``rules.yaml`` and the strings already written to ``scans.product_category``. Changing
    the case would stop the sector dispatch matching any rule while every type check still
    passed.

    A proposal is not a confirmation. :class:`~app.contracts.evidence.CategoryProposal`
    carries a category a reader inferred, and it is a distinct type precisely so it cannot
    be passed where this one is expected.
    """

    FOOD = "food"
    """Food articles, routed to the Food Safety and Standards Act, 2006.

    Explanation III to Rule 6(1)(a) disapplies that clause for packages containing food
    articles outright. The proviso to Rule 2(kc), inserted by G.S.R. 722(E), routes the
    multi-piece package definition itself the same way. Two separate provisions with two
    different scopes, which is why the rule store holds them as two rules rather than one
    fact about food.
    """

    COSMETICS = "cosmetics"
    """Cosmetic products, whose date declaration is routed to the Drugs and Cosmetics
    Rules, 1945.

    The third proviso to Rule 6(1)(d). It moves the month-and-year-of-manufacture
    obligation and nothing else — a cosmetic package still bears every other Rule 6
    declaration under these Rules.
    """

    MEDICAL_DEVICE = "medical_device"
    """Medical devices, routed to the Medical Devices Rules, 2017 by G.S.R. 778(E), in
    force from 24 October 2025.

    The provisos it inserts into Rule 2(h), Rule 7(2) and Rule 7(3) move the panel
    declaration, the character height and the width ratio. The Rule 33(2) it inserts
    additionally removes the power to relax, so a medical device cannot be both routed to
    the Medical Devices Rules and granted a relaxation under these ones. A carve-out, not
    a stricter path: Rule 7 Table-I stops applying rather than applying more severely.
    """
