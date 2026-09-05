"""Offline evaluation harness for packaging compliance ground-truth benchmarking.

Evaluates predicted Rule 6(1) and Rule 6(11) declarations against ground-truth annotations,
computing precision, recall, and F1 scores sliced by:
- Mandatory declaration field
- Product category (food vs cosmetics)
- Environmental & optical difficulty tags (small_pdp, glare, curved, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from datasets.schema import (
    Category,
    DifficultyTag,
    LabelledSample,
)

RULE_6_FIELDS = [
    "manufacturer_or_packer",
    "commodity_name",
    "net_quantity",
    "date_of_manufacture_or_packing",
    "retail_sale_price_mrp",
    "unit_sale_price",
    "consumer_care_details",
    "country_of_origin",
]


@dataclass
class MetricScores:
    """Precision, recall, and F1 count and score breakdown."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    support: int = 0  # Number of samples where field is declared in GT

    @property
    def precision(self) -> float:
        total_positive_preds = self.true_positives + self.false_positives
        if total_positive_preds == 0:
            return 0.0
        return self.true_positives / total_positive_preds

    @property
    def recall(self) -> float:
        total_actual_positives = self.true_positives + self.false_negatives
        if total_actual_positives == 0:
            return 0.0
        return self.true_positives / total_actual_positives

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2.0 * (p * r) / (p + r)

    def record_outcome(
        self,
        *,
        is_tp: bool,
        is_fp: bool,
        is_fn: bool,
        is_tn: bool,
        gt_declared: bool,
    ) -> None:
        """Tally classification outcome counts."""
        if gt_declared:
            self.support += 1
        if is_tp:
            self.true_positives += 1
        elif is_fp:
            self.false_positives += 1
        elif is_fn:
            self.false_negatives += 1
        elif is_tn:
            self.true_negatives += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "support": self.support,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
        }


@dataclass
class EvaluationReport:
    """Consolidated evaluation summary report."""

    total_samples: int = 0
    overall_fields: dict[str, MetricScores] = field(default_factory=dict)
    by_category: dict[str, dict[str, MetricScores]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    by_difficulty_tag: dict[str, dict[str, MetricScores]] = field(
        default_factory=lambda: defaultdict(dict)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "overall_fields": {k: v.to_dict() for k, v in self.overall_fields.items()},
            "by_category": {
                cat: {f: m.to_dict() for f, m in fields.items()}
                for cat, fields in self.by_category.items()
            },
            "by_difficulty_tag": {
                tag: {f: m.to_dict() for f, m in fields.items()}
                for tag, fields in self.by_difficulty_tag.items()
            },
        }


class ComplianceEvaluator:
    """Core evaluation engine that benchmarks predicted declarations against ground truth."""

    def __init__(self, ground_truth: list[LabelledSample]) -> None:
        self.ground_truth = ground_truth
        self.gt_by_id = {sample.sample_id: sample for sample in ground_truth}

    @classmethod
    def load_ground_truth(cls, annotations_path: Path | str) -> ComplianceEvaluator:
        """Load ground truth annotations from a single JSON file or directory of JSON files."""
        path = Path(annotations_path)
        samples: list[LabelledSample] = []

        if path.is_file():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        samples.append(LabelledSample.model_validate(item))
                elif isinstance(data, dict):
                    samples.append(LabelledSample.model_validate(data))
        elif path.is_dir():
            json_files = sorted(path.rglob("*.json"))
            # Exclude schema.json if located inside annotations directory
            for jf in json_files:
                if jf.name == "schema.json":
                    continue
                try:
                    with open(jf, encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                samples.append(LabelledSample.model_validate(item))
                        elif (
                            isinstance(data, dict)
                            and "sample_id" in data
                            and "declarations" in data
                        ):
                            samples.append(LabelledSample.model_validate(data))
                except (json.JSONDecodeError, ValidationError) as err:
                    print(f"Warning: Skipping file {jf}: {err}", file=sys.stderr)
        else:
            raise FileNotFoundError(f"Annotations path not found: {annotations_path}")

        return cls(samples)

    def evaluate(self, predictions: dict[str, dict[str, Any]]) -> EvaluationReport:
        """Evaluate predictions dictionary against ground truth.

        predictions schema:
        {
            "<sample_id>": {
                "<field_name>": {
                    "declared": bool,
                    "raw_text": Optional[str],
                    "normalised_value": Optional[Any]
                }
            }
        }
        """
        report = EvaluationReport(total_samples=len(self.ground_truth))

        # Initialize metric score containers
        overall_scores: dict[str, MetricScores] = {
            field_name: MetricScores() for field_name in RULE_6_FIELDS
        }
        category_scores: dict[str, dict[str, MetricScores]] = {
            cat.value: {field_name: MetricScores() for field_name in RULE_6_FIELDS}
            for cat in Category
        }
        difficulty_scores: dict[str, dict[str, MetricScores]] = defaultdict(
            lambda: {field_name: MetricScores() for field_name in RULE_6_FIELDS}
        )

        for sample in self.ground_truth:
            sample_preds = predictions.get(sample.sample_id, {})
            cat_key = sample.category.value

            for field_name in RULE_6_FIELDS:
                gt_field = getattr(sample.declarations, field_name)
                gt_declared = gt_field.declared

                pred_field = sample_preds.get(field_name, {})
                pred_declared = bool(pred_field.get("declared", False))

                # Tally counts
                is_tp = gt_declared and pred_declared
                is_fp = (not gt_declared) and pred_declared
                is_fn = gt_declared and (not pred_declared)
                is_tn = (not gt_declared) and (not pred_declared)

                # Update overall
                overall_scores[field_name].record_outcome(
                    is_tp=is_tp,
                    is_fp=is_fp,
                    is_fn=is_fn,
                    is_tn=is_tn,
                    gt_declared=gt_declared,
                )

                # Update category
                category_scores[cat_key][field_name].record_outcome(
                    is_tp=is_tp,
                    is_fp=is_fp,
                    is_fn=is_fn,
                    is_tn=is_tn,
                    gt_declared=gt_declared,
                )

                # Update difficulty tags
                for tag in sample.difficulty_tags:
                    tag_str = tag.value if isinstance(tag, DifficultyTag) else str(tag)
                    difficulty_scores[tag_str][field_name].record_outcome(
                        is_tp=is_tp,
                        is_fp=is_fp,
                        is_fn=is_fn,
                        is_tn=is_tn,
                        gt_declared=gt_declared,
                    )

        report.overall_fields = overall_scores
        report.by_category = category_scores
        report.by_difficulty_tag = dict(difficulty_scores)
        return report

    def render_console_table(self, report: EvaluationReport) -> None:
        """Print clean ASCII summary tables of evaluation metrics to stdout."""
        print("\n" + "=" * 94)
        print(
            f"LMPC COMPLIANCE EVALUATION REPORT (Total Samples: {report.total_samples})"
        )
        print("=" * 94)

        def print_field_table(title: str, scores: dict[str, MetricScores]) -> None:
            print(f"\n--- {title} ---")
            print("-" * 94)
            header = f"{'Field Name':<34} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Supp':<4}"
            print(header)
            print("-" * 94)

            total_tp = 0
            total_fp = 0
            total_fn = 0
            total_supp = 0
            f1_sum = 0.0

            for f_name in RULE_6_FIELDS:
                sc = scores.get(f_name, MetricScores())
                total_tp += sc.true_positives
                total_fp += sc.false_positives
                total_fn += sc.false_negatives
                total_supp += sc.support
                f1_sum += sc.f1_score

                line = (
                    f"{f_name:<34} | "
                    f"{sc.precision:<10.4f} | "
                    f"{sc.recall:<10.4f} | "
                    f"{sc.f1_score:<10.4f} | "
                    f"{sc.true_positives:<4} | "
                    f"{sc.false_positives:<4} | "
                    f"{sc.false_negatives:<4} | "
                    f"{sc.support:<4}"
                )
                print(line)

            print("-" * 94)
            macro_f1 = f1_sum / len(RULE_6_FIELDS) if RULE_6_FIELDS else 0.0
            micro_prec = (
                total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
            )
            micro_rec = (
                total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
            )
            micro_f1 = (
                2 * micro_prec * micro_rec / (micro_prec + micro_rec)
                if (micro_prec + micro_rec) > 0
                else 0.0
            )

            summary_line = (
                f"{'MICRO AVERAGE / TOTALS':<34} | "
                f"{micro_prec:<10.4f} | "
                f"{micro_rec:<10.4f} | "
                f"{micro_f1:<10.4f} | "
                f"{total_tp:<4} | "
                f"{total_fp:<4} | "
                f"{total_fn:<4} | "
                f"{total_supp:<4}"
            )
            print(summary_line)
            print(f"Macro Average F1: {macro_f1:.4f}")

        # Overall
        print_field_table(
            "Overall Performance across Rule 6(1) Fields", report.overall_fields
        )

        # By Category
        for cat, scores in report.by_category.items():
            print_field_table(f"Category Slice: {cat.upper()}", scores)

        # By Difficulty Tag
        if report.by_difficulty_tag:
            print("\n--- Performance Sliced by Difficulty Tag (Macro F1) ---")
            print("-" * 65)
            print(
                f"{'Difficulty Tag':<30} | {'Macro F1':<12} | {'Evaluated Fields':<12}"
            )
            print("-" * 65)
            for tag, scores in sorted(report.by_difficulty_tag.items()):
                f1_vals = [sc.f1_score for sc in scores.values() if sc.support > 0]
                avg_f1 = sum(f1_vals) / len(f1_vals) if f1_vals else 0.0
                print(f"{tag:<30} | {avg_f1:<12.4f} | {len(f1_vals):<12}")
            print("-" * 65)


def generate_self_test_predictions(
    ground_truth: list[LabelledSample],
) -> dict[str, dict[str, Any]]:
    """Generate perfect baseline predictions from ground-truth annotations for self-testing."""
    preds: dict[str, dict[str, Any]] = {}
    for sample in ground_truth:
        sample_dict: dict[str, Any] = {}
        for f_name in RULE_6_FIELDS:
            gt_field = getattr(sample.declarations, f_name)
            sample_dict[f_name] = {
                "declared": gt_field.declared,
                "raw_text": gt_field.raw_text,
                "normalised_value": gt_field.normalised_value,
            }
        preds[sample.sample_id] = sample_dict
    return preds


def main() -> int:
    """CLI entry point for evaluation harness."""
    parser = argparse.ArgumentParser(
        description="LMPC Packaging Compliance Evaluation Harness",
    )
    parser.add_argument(
        "--annotations",
        "-a",
        type=str,
        default=str(Path(__file__).parent.parent / "annotations"),
        help="Path to ground truth annotations directory or JSON file.",
    )
    parser.add_argument(
        "--predictions",
        "-p",
        type=str,
        default=None,
        help="Path to predictions JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Path to export evaluation report JSON.",
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Run self-test using ground truth as oracle predictions.",
    )

    args = parser.parse_args()

    annotations_path = Path(args.annotations)
    if not annotations_path.exists():
        print(
            f"Error: Annotations path '{annotations_path}' does not exist.",
            file=sys.stderr,
        )
        return 1

    evaluator = ComplianceEvaluator.load_ground_truth(annotations_path)
    if not evaluator.ground_truth:
        print(
            f"Error: No valid annotations found in '{annotations_path}'.",
            file=sys.stderr,
        )
        return 1

    if args.test_run:
        print("Executing self-test evaluation with ground-truth oracle baseline...")
        predictions = generate_self_test_predictions(evaluator.ground_truth)
    elif args.predictions:
        pred_path = Path(args.predictions)
        if not pred_path.exists():
            print(
                f"Error: Predictions file '{pred_path}' does not exist.",
                file=sys.stderr,
            )
            return 1
        with open(pred_path, encoding="utf-8") as f:
            predictions = json.load(f)
    else:
        print(
            "Error: Must specify --predictions <path> or --test-run flag.",
            file=sys.stderr,
        )
        parser.print_help()
        return 1

    report = evaluator.evaluate(predictions)
    evaluator.render_console_table(report)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nExported evaluation report to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
