"""Unit tests for datasets schema, evaluation metrics, and harness."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from datasets.eval.harness import (
    RULE_6_FIELDS,
    ComplianceEvaluator,
    MetricScores,
    generate_self_test_predictions,
)
from datasets.schema import (
    Category,
    ComplianceVerdict,
    DeclarationField,
    DifficultyTag,
    FieldComplianceState,
    LabelledSample,
    PDPInfo,
    PDPShape,
    ReferenceObject,
    ReferenceObjectType,
    Rule6Declarations,
    Rule7TableBand,
)


def create_minimal_declaration(
    declared: bool = True,
    text: str = "Test Text",
    state: FieldComplianceState = FieldComplianceState.PASS,
) -> DeclarationField:
    return DeclarationField(
        declared=declared,
        raw_text=text if declared else None,
        normalised_value=text if declared else None,
        expected_field_state=state,
    )


def create_dummy_sample(
    sample_id: str = "food_dummy_001",
    category: Category = Category.FOOD,
    tags: list[DifficultyTag] | None = None,
    missing_fields: list[str] | None = None,
) -> LabelledSample:
    missing_fields = missing_fields or []
    decl_dict = {}
    for f in RULE_6_FIELDS:
        if f in missing_fields:
            decl_dict[f] = create_minimal_declaration(
                declared=False,
                text="",
                state=FieldComplianceState.FAIL,
            )
        else:
            decl_dict[f] = create_minimal_declaration(
                declared=True,
                text=f"Valid {f}",
                state=FieldComplianceState.PASS,
            )

    return LabelledSample(
        sample_id=sample_id,
        sku_id=sample_id.rsplit("_", 1)[0],
        image_filename=f"{sample_id}.jpg",
        category=category,
        difficulty_tags=tags or [DifficultyTag.SMALL_PDP],
        known_issues=[],
        reference_object=ReferenceObject(
            present=False,
            object_type=ReferenceObjectType.NONE,
        ),
        pdp=PDPInfo(
            shape=PDPShape.RECTANGULAR,
            area_cm2=45.0,
            is_measurable=True,
            rule7_band=Rule7TableBand.A_LE_50,
            rule7_min_height_mm=1.0,
        ),
        declarations=Rule6Declarations(**decl_dict),
        ground_truth_verdict=ComplianceVerdict.PASS,
    )


class TestMetricScores:
    def test_zero_denominator_safe(self):
        sc = MetricScores()
        assert sc.precision == 0.0
        assert sc.recall == 0.0
        assert sc.f1_score == 0.0

    def test_precision_recall_f1_exact(self):
        sc = MetricScores(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
            true_negatives=5,
            support=10,
        )
        assert pytest.approx(sc.precision) == 0.8  # 8 / (8 + 2)
        assert pytest.approx(sc.recall) == 0.8  # 8 / (8 + 2)
        assert pytest.approx(sc.f1_score) == 0.8


class TestRule7BandCalculation:
    @pytest.mark.parametrize(
        ("area", "expected_band", "expected_height"),
        [
            (30.0, Rule7TableBand.A_LE_50, 1.0),
            (50.0, Rule7TableBand.A_LE_50, 1.0),
            (75.0, Rule7TableBand.A_50_TO_100, 1.5),
            (100.0, Rule7TableBand.A_50_TO_100, 1.5),
            (250.0, Rule7TableBand.A_100_TO_500, 2.5),
            (500.0, Rule7TableBand.A_100_TO_500, 2.5),
            (1200.0, Rule7TableBand.A_500_TO_2500, 4.0),
            (2500.0, Rule7TableBand.A_500_TO_2500, 4.0),
            (3000.0, Rule7TableBand.A_GT_2500, 6.0),
        ],
    )
    def test_pdp_area_banding(self, area, expected_band, expected_height):
        pdp = PDPInfo(shape=PDPShape.RECTANGULAR, area_cm2=area)
        band, min_h = pdp.calculate_rule7_band()
        assert band == expected_band
        assert min_h == expected_height


class TestSchemaValidation:
    def test_valid_sample_validation(self):
        sample = create_dummy_sample()
        assert sample.category == Category.FOOD
        assert sample.pdp.area_cm2 == 45.0

    def test_invalid_category_rejected(self):
        sample_dict = create_dummy_sample().model_dump()
        sample_dict["category"] = "electronics"
        with pytest.raises(ValidationError):
            LabelledSample.model_validate(sample_dict)

    def test_verdicts_restricted(self):
        # Per Standing Constraint 1: PASS / REVIEW / POTENTIAL_VIOLATION only
        sample_dict = create_dummy_sample().model_dump()
        sample_dict["ground_truth_verdict"] = "NON_COMPLIANT"
        with pytest.raises(ValidationError):
            LabelledSample.model_validate(sample_dict)


class TestComplianceEvaluator:
    def test_perfect_baseline_evaluation(self):
        s1 = create_dummy_sample(
            "food_001",
            Category.FOOD,
            tags=[DifficultyTag.SMALL_PDP],
        )
        s2 = create_dummy_sample(
            "cosmetics_001",
            Category.COSMETICS,
            tags=[DifficultyTag.CURVED],
            missing_fields=["date_of_manufacture_or_packing"],
        )
        evaluator = ComplianceEvaluator([s1, s2])
        preds = generate_self_test_predictions([s1, s2])
        report = evaluator.evaluate(preds)

        assert report.total_samples == 2
        for f in RULE_6_FIELDS:
            sc = report.overall_fields[f]
            assert sc.precision == 1.0
            assert sc.recall == 1.0
            assert sc.f1_score == 1.0

        assert "food" in report.by_category
        assert "cosmetics" in report.by_category
        assert "small_pdp" in report.by_difficulty_tag
        assert "curved" in report.by_difficulty_tag

    def test_imperfect_predictions(self):
        s1 = create_dummy_sample("food_001", Category.FOOD)
        evaluator = ComplianceEvaluator([s1])
        # Prediction where net_quantity is missed
        preds = {
            "food_001": {f: {"declared": (f != "net_quantity")} for f in RULE_6_FIELDS}
        }
        report = evaluator.evaluate(preds)
        nq_scores = report.overall_fields["net_quantity"]
        assert nq_scores.true_positives == 0
        assert nq_scores.false_negatives == 1
        assert nq_scores.recall == 0.0

    def test_load_annotations_directory(self, tmp_path: Path):
        s1 = create_dummy_sample("food_sample_001", Category.FOOD)
        file_path = tmp_path / "sample.json"
        file_path.write_text(s1.model_dump_json(), encoding="utf-8")

        evaluator = ComplianceEvaluator.load_ground_truth(tmp_path)
        assert len(evaluator.ground_truth) == 1
        assert evaluator.ground_truth[0].sample_id == "food_sample_001"
