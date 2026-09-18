"""Rule 6(11) is evaluated on both scan paths, from the net quantity and nothing else.

A format rule: the basis after "per" must be the one the net quantity calls for. No figure
is divided by anything, because the gazette states no tolerance and none may be invented.
"""

from app.contracts import DeclarationField, FieldState
from app.modules.rules import ProductCategory

from .test_geometry_wiring import Label, finding_for, scan
from .test_orchestrator import NOW, listing, run_catalogue_scan

RULE = "R6-11-UNIT-SALE-PRICE"


def catalogue(**fields):
    return run_catalogue_scan(
        listing(NET_QUANTITY="500 g", RETAIL_SALE_PRICE="Rs. 45.00", **fields),
        product_category=ProductCategory.FOOD,
        evaluated_at=NOW,
        subject_ref="scan-usp",
    )


def usp(record):
    return next(
        f
        for f in record.findings
        if f.rule_snapshot.rule_id == RULE and f.field is DeclarationField.UNIT_SALE_PRICE
    )


def test_a_listing_priced_per_gram_below_a_kilogram_passes() -> None:
    found = usp(catalogue(UNIT_SALE_PRICE="Rs. 9.00 per g"))
    assert found.state is FieldState.PASS
    assert found.expected_value == "per g"
    assert found.evidence_span_ids == ("listing:B0TEST:UNIT_SALE_PRICE",)


def test_a_listing_priced_per_kilogram_below_a_kilogram_is_a_potential_violation() -> None:
    found = usp(catalogue(UNIT_SALE_PRICE="Rs. 9000 per kg"))
    assert found.state is FieldState.FAIL
    assert "prescribes per 'g'" in found.reason


def test_at_exactly_one_kilogram_the_basis_is_the_kilogram() -> None:
    record = run_catalogue_scan(
        listing(NET_QUANTITY="1000 g", UNIT_SALE_PRICE="Rs. 90 per kg"),
        product_category=ProductCategory.FOOD,
        evaluated_at=NOW,
        subject_ref="scan-usp",
    )
    assert usp(record).state is FieldState.PASS


def test_a_listing_with_no_unit_sale_price_has_nothing_for_the_rule_to_apply_to() -> None:
    found = usp(catalogue())
    assert found.state is FieldState.NOT_APPLICABLE
    assert found.state is not FieldState.FAIL


def test_a_basis_the_rule_does_not_name_goes_to_an_officer() -> None:
    found = usp(catalogue(UNIT_SALE_PRICE="Rs. 2 per 100 g"))
    assert found.state is FieldState.REVIEW_REQUIRED


def test_no_figure_is_ever_compared_against_the_price() -> None:
    """Rs. 1 per g on a 500 g pack at Rs. 45 is arithmetically absurd and still PASSES.

    That is the point: Rule 6(11) is about the basis, and any check of the figure would be
    a tolerance the gazette does not state.
    """
    assert usp(catalogue(UNIT_SALE_PRICE="Rs. 1 per g")).state is FieldState.PASS


def test_the_image_path_reads_the_basis_off_the_label() -> None:
    label = Label().write("Net Quantity: 100 g", (250, 250), span_id="s-quantity")
    label.write("Unit Sale Price: Rs. 0.45 per g", (250, 420), span_id="s-usp")
    found = finding_for(scan(label), RULE, DeclarationField.UNIT_SALE_PRICE)
    assert found.state is FieldState.PASS
    assert found.evidence_span_ids == ("s-usp",)

    wrong = Label().write("Net Quantity: 100 g", (250, 250), span_id="s-quantity")
    wrong.write("Unit Sale Price: Rs. 450 per kg", (250, 420), span_id="s-usp")
    assert finding_for(scan(wrong), RULE, DeclarationField.UNIT_SALE_PRICE).state is FieldState.FAIL


def test_an_unread_label_leaves_the_rule_insufficient_not_failed() -> None:
    label = Label().write("Net Quantity: 100 g", (250, 250), span_id="s-quantity")
    found = finding_for(scan(label), RULE, DeclarationField.UNIT_SALE_PRICE)
    assert found.state is FieldState.INSUFFICIENT_EVIDENCE
