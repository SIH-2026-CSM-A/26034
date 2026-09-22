"""A non-food, non-cosmetic packaged good is evaluated against the obligations it owes.

The worked case is a mobile phone carton. Chapter II applies to it in full — nothing in
Rule 6(1)(a), (b), (c), (d), (e) or Rules 7 to 9 is limited to a class of commodity — with
one exception the rule states itself: Rule 6(1)(da) requires a best-before date only of "a
commodity which may become unfit for human consumption after a period of time".

Every routing decision below is checked against the rule store's own ``source_text``, so
this file cannot stay green while citing a condition the rules no longer state.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.contracts import DeclarationField, FieldState, NormalisedField, ProductCategory, Verdict
from app.modules.rules import load_rules, rule_33_relaxation_applies, sector_overrides
from app.pipeline.dispositions import (
    COMMODITY_CONDITIONED_RULES,
    FACT_CONDITIONED_RULES,
    IMPORT_CONDITIONED_RULES,
    SECTOR_GOVERNED_RULES,
    Disposition,
    disposition_of,
    import_marker_in,
)
from app.pipeline.rule_findings import UNCONFIRMED_CATEGORY_REASON
from app.pipeline.verdict import assemble_verdict

from .test_findings import EVALUATION_DATE, findings_for


def declared(field: DeclarationField, value: str, **extra: object) -> tuple[NormalisedField, ...]:
    return (
        NormalisedField(
            field_type=field,
            span_refs=(f"listing:PHONE:{field.value}",),
            normalised_value=value,
            parse_confidence=1.0,
            **extra,  # type: ignore[arg-type]
        ),
    )


PHONE = {
    DeclarationField.NAME_AND_ADDRESS: declared(
        DeclarationField.NAME_AND_ADDRESS, "Acme Mobiles Pvt Ltd, Plot 12, Noida 201301"
    ),
    DeclarationField.COMMON_OR_GENERIC_NAME: declared(
        DeclarationField.COMMON_OR_GENERIC_NAME, "Mobile Phone"
    ),
    DeclarationField.NET_QUANTITY: declared(
        DeclarationField.NET_QUANTITY, "1 N", numeric_value=Decimal(1), unit="N"
    ),
    DeclarationField.MANUFACTURE_DATE: declared(DeclarationField.MANUFACTURE_DATE, "2026-08"),
    DeclarationField.RETAIL_SALE_PRICE: declared(
        DeclarationField.RETAIL_SALE_PRICE, "14999.00", numeric_value=Decimal("14999.00")
    ),
}
"""What a phone carton bears: no best-before, no dimensions, no country of origin."""


def phone(category: ProductCategory | None, declarations=PHONE, *, import_marker: bool = False):
    return findings_for(
        product_category=category,
        declared=declarations,
        source_is_listing=True,
        unreadable_reason=None,
        measurements={},
        import_marker_observed=import_marker,
    )


def by_rule(findings, rule_id: str):
    selected = [f for f in findings if f.rule_snapshot.rule_id == rule_id]
    assert selected, f"no finding for {rule_id}"
    return selected


def normalised(text: str) -> str:
    return " ".join(text.split()).casefold()


# --- the routing tables cite text that is really in the store --------------------------------


@pytest.mark.parametrize(
    ("rule_id", "phrase"),
    [(rule_id, phrase) for rule_id, (phrase, _) in COMMODITY_CONDITIONED_RULES.items()]
    + list(FACT_CONDITIONED_RULES.items())
    + list(IMPORT_CONDITIONED_RULES.items()),
)
def test_every_conditioning_phrase_is_in_the_rules_own_text(rule_id: str, phrase: str) -> None:
    rules = {rule.rule_id: rule for rule in load_rules()}
    assert rule_id in rules, f"{rule_id} is not in the rule store"
    assert normalised(phrase) in normalised(rules[rule_id].source_text)
    assert disposition_of(rules[rule_id]) is Disposition.DECLARATION


def test_the_conditioned_tables_are_not_empty_and_do_not_overlap_the_sector_gate() -> None:
    conditioned = (
        set(COMMODITY_CONDITIONED_RULES)
        | set(FACT_CONDITIONED_RULES)
        | set(IMPORT_CONDITIONED_RULES)
    )
    assert conditioned == {"R6-1-DA", "R6-1-AA", "R6-1-F"}
    # The three tables answer three different questions and no rule may be in two of them.
    assert not set(FACT_CONDITIONED_RULES) & set(IMPORT_CONDITIONED_RULES)
    assert not set(COMMODITY_CONDITIONED_RULES) & set(IMPORT_CONDITIONED_RULES)
    assert not conditioned & set(SECTOR_GOVERNED_RULES)


def test_non_consumable_is_named_by_no_sector_rule_and_routes_nothing() -> None:
    sectors = {
        rule.conditions.sector for rule in load_rules() if rule.conditions.kind == "sector_override"
    }
    assert sectors, "no sector rule was read, so an absence from them means nothing"
    assert ProductCategory.NON_CONSUMABLE not in sectors
    assert sector_overrides(ProductCategory.NON_CONSUMABLE, EVALUATION_DATE) == {}
    assert rule_33_relaxation_applies(ProductCategory.NON_CONSUMABLE, EVALUATION_DATE)


# --- the phone carton ------------------------------------------------------------------------


def test_best_before_is_not_applicable_to_a_confirmed_non_consumable() -> None:
    (finding,) = by_rule(phone(ProductCategory.NON_CONSUMABLE), "R6-1-DA")
    assert finding.state is FieldState.NOT_APPLICABLE
    assert "Rule 6(1)(da)" in finding.reason
    assert "unfit for human consumption" in finding.reason


def test_a_best_before_that_is_printed_anyway_is_still_not_applicable_never_pass() -> None:
    """The package did not satisfy the duty; it never had it."""
    bearing = PHONE | {
        DeclarationField.BEST_BEFORE_DATE: declared(DeclarationField.BEST_BEFORE_DATE, "2028-08")
    }
    (finding,) = by_rule(phone(ProductCategory.NON_CONSUMABLE, bearing), "R6-1-DA")
    assert finding.state is FieldState.NOT_APPLICABLE


def test_confirming_non_consumable_evaluates_every_sector_gated_obligation() -> None:
    unconfirmed = phone(None)
    confirmed = phone(ProductCategory.NON_CONSUMABLE)
    assert any(f.reason == UNCONFIRMED_CATEGORY_REASON for f in unconfirmed)
    assert not any(f.reason == UNCONFIRMED_CATEGORY_REASON for f in confirmed)
    # Nothing was carved out to another Act. Two obligations do not arise for this
    # package: the best-before one above, and Rule 6(1)(aa), because the phone carton
    # bears no importer declaration and so is not marked as imported.
    not_applicable = {
        f.rule_snapshot.rule_id for f in confirmed if f.state is FieldState.NOT_APPLICABLE
    }
    assert not_applicable == {"R6-1-DA", "R6-1-AA"}
    for rule_id in ("R6-1-A", "R6-1-B", "R6-1-C", "R6-1-D", "R6-1-E"):
        assert {f.state for f in by_rule(confirmed, rule_id)} == {FieldState.PASS}, rule_id


def test_the_obligations_a_phone_does_owe_still_bite() -> None:
    """NON_CONSUMABLE is not a softer path: a missing MRP is as much a shortfall as ever."""
    without_price = {k: v for k, v in PHONE.items() if k is not DeclarationField.RETAIL_SALE_PRICE}
    findings = phone(ProductCategory.NON_CONSUMABLE, without_price)
    assert {f.state for f in by_rule(findings, "R6-1-E")} == {FieldState.FAIL}
    verdict = assemble_verdict(
        subject_ref="phone",
        findings=findings,
        rule_set_version=findings[0].rule_snapshot.rule_set_version,
        evaluated_at=datetime(2026, 9, 6, tzinfo=UTC),
        field_providers={},
    )
    assert verdict.verdict is Verdict.POTENTIAL_VIOLATION


def test_an_unconfirmed_category_cannot_fail_best_before() -> None:
    (finding,) = by_rule(phone(None), "R6-1-DA")
    assert finding.state is FieldState.INSUFFICIENT_EVIDENCE
    assert "has not been confirmed" in finding.reason


@pytest.mark.parametrize(
    "category", [ProductCategory.FOOD, ProductCategory.COSMETICS, ProductCategory.MEDICAL_DEVICE]
)
def test_the_gate_softens_nothing_for_the_sectors(category: ProductCategory) -> None:
    """A food listing with no best-before is still a shortfall. Only the condition moved."""
    (finding,) = by_rule(phone(category), "R6-1-DA")
    assert finding.state is FieldState.FAIL


# --- duties conditional on a fact no category establishes -----------------------------------


@pytest.mark.parametrize("category", [None, *ProductCategory])
@pytest.mark.parametrize("rule_id", sorted(FACT_CONDITIONED_RULES))
def test_an_absent_fact_conditioned_declaration_is_review_never_fail(
    rule_id: str, category: ProductCategory | None
) -> None:
    (finding,) = by_rule(phone(category), rule_id)
    assert finding.state is FieldState.REVIEW_REQUIRED
    assert FACT_CONDITIONED_RULES[rule_id] in finding.reason


def test_a_fact_conditioned_declaration_that_is_borne_passes_as_any_other() -> None:
    bearing = PHONE | {
        DeclarationField.COUNTRY_OF_ORIGIN: declared(DeclarationField.COUNTRY_OF_ORIGIN, "IN")
    }
    (finding,) = by_rule(phone(ProductCategory.NON_CONSUMABLE, bearing), "R6-1-AA")
    assert finding.state is FieldState.PASS


# --- Rule 6(1)(aa): owed only by an imported package -----------------------------------------


@pytest.mark.parametrize("category", [None, *ProductCategory])
def test_country_of_origin_does_not_arise_on_a_package_nothing_marks_imported(
    category: ProductCategory | None,
) -> None:
    """NOT_APPLICABLE, and never INSUFFICIENT_EVIDENCE: the obligation did not exist."""
    (finding,) = by_rule(phone(category), "R6-1-AA")
    assert finding.state is FieldState.NOT_APPLICABLE
    assert "in case of imported products" in finding.reason
    assert "nothing read off this package marks it as imported" in finding.reason


def test_an_unreadable_panel_does_not_turn_a_duty_that_never_arose_into_a_reading_failure() -> None:
    """Whether the duty arises does not depend on how well the panel photographed."""
    findings = findings_for(product_category=ProductCategory.NON_CONSUMABLE)
    assert {f.state for f in by_rule(findings, "R6-1-AA")} == {FieldState.NOT_APPLICABLE}


def test_an_importer_declaration_makes_the_duty_live_and_an_absent_declaration_bite() -> None:
    """The case the rule exists for: marked imported, no country of origin, a shortfall."""
    findings = phone(ProductCategory.NON_CONSUMABLE, import_marker=True)
    (finding,) = by_rule(findings, "R6-1-AA")
    assert finding.state is FieldState.FAIL
    assert finding.state is not FieldState.NOT_APPLICABLE


def test_a_declared_country_of_origin_is_evaluated_even_with_no_marker() -> None:
    """A package that answers the obligation gets a PASS, not a shrug.

    Settling the field on the marker alone would report NOT_APPLICABLE over a declaration
    the package actually bears, and hide the PASS.
    """
    bearing = PHONE | {
        DeclarationField.COUNTRY_OF_ORIGIN: declared(DeclarationField.COUNTRY_OF_ORIGIN, "IN")
    }
    (finding,) = by_rule(phone(ProductCategory.NON_CONSUMABLE, bearing), "R6-1-AA")
    assert finding.state is FieldState.PASS


def test_made_in_india_is_not_read_as_an_import_marker() -> None:
    """The commonest line on the corpus must not invert the test."""
    assert not import_marker_in(["Made in India", "Product of India", "MADE IN INDIA"])
    assert import_marker_in(["Imported by: Acme Traders, Mumbai"])
    assert import_marker_in(["IMPORTER  :  ACME   TRADERS"])


def test_an_unreadable_photograph_is_still_insufficient_evidence_not_review() -> None:
    """The gate replaces a FAIL and nothing else: what we could not read stays unread."""
    findings = findings_for(product_category=ProductCategory.NON_CONSUMABLE)
    for rule_id in FACT_CONDITIONED_RULES:
        assert {f.state for f in by_rule(findings, rule_id)} == {FieldState.INSUFFICIENT_EVIDENCE}
