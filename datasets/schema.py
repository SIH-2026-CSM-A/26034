"""Machine-readable ground-truth labelling schema for Legal Metrology compliance evaluation.

Strictly adheres to:
- Legal Metrology (Packaged Commodities) Rules, 2011 (LMPC 2011)
- G.S.R. 629(E) 2017 amendment (Rule 7 Table-I banding by PDP area)
- Standing Constraints in AGENTS.md (Verdicts are PASS / REVIEW / POTENTIAL VIOLATION)
- ARCHITECTURE.md (5 per-field states, no millimetre measurement from uncalibrated photos)
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    """Consumer commodity category under evaluation."""

    FOOD = "food"
    COSMETICS = "cosmetics"


class DifficultyTag(str, Enum):
    """Environmental and visual difficulty tags for evaluation slicing."""

    SMALL_PDP = "small_pdp"
    GLARE = "glare"
    CURVED = "curved"
    MULTISCRIPT = "multiscript"
    MISSING_MONTH_YEAR = "missing_month_year"
    FLEXIBLE_POUCH = "flexible_pouch"
    CROWDED = "crowded"
    CALIBRATED = "calibrated"
    UNCALIBRATED = "uncalibrated"
    LOW_CONTRAST = "low_contrast"
    TILTED = "tilted"
    PARTIALLY_OCCLUDED = "partially_occluded"


class ReferenceObjectType(str, Enum):
    """Known fiducial or reference object present in frame for calibration."""

    NONE = "none"
    COIN_INR_1 = "coin_inr_1"  # 21.93 mm
    COIN_INR_2 = "coin_inr_2"  # 25.00 mm
    COIN_INR_5 = "coin_inr_5"  # 25.00 mm nickel-brass / 23.0 mm stainless
    COIN_INR_10 = "coin_inr_10"  # 27.00 mm bimetallic
    CREDIT_CARD_ID1 = "credit_card_id1"  # ISO/IEC 7810 ID-1: 85.60 mm x 53.98 mm
    ARUCO_MARKER = "aruco_marker"
    RULER_SCALE = "ruler_scale"
    CHECKERBOARD = "checkerboard"


class PDPShape(str, Enum):
    """Principal Display Panel geometric classification per Rule 7(4)."""

    RECTANGULAR = "rectangular"
    CYLINDRICAL = "cylindrical"
    CIRCULAR = "circular"
    OTHER = "other"


class Rule7TableBand(str, Enum):
    """Rule 7(2) Table-I bands based on Principal Display Panel area (cm²)."""

    A_LE_50 = "A_le_50"  # Area <= 50 cm²: min 1.0 mm (1.5 mm blown/moulded)
    A_50_TO_100 = (
        "50_lt_A_le_100"  # 50 < Area <= 100 cm²: min 1.5 mm (3.0 mm blown/moulded)
    )
    A_100_TO_500 = (
        "100_lt_A_le_500"  # 100 < Area <= 500 cm²: min 2.5 mm (4.0 mm blown/moulded)
    )
    A_500_TO_2500 = (
        "500_lt_A_le_2500"  # 500 < Area <= 2500 cm²: min 4.0 mm (6.0 mm blown/moulded)
    )
    A_GT_2500 = "2500_lt_A"  # Area > 2500 cm²: min 6.0 mm (6.0 mm blown/moulded)


class ComplianceVerdict(str, Enum):
    """Overall compliance decision-support recommendation (AGENTS.md Constraint 1)."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    POTENTIAL_VIOLATION = "POTENTIAL_VIOLATION"


class FieldComplianceState(str, Enum):
    """Five-state per-field evaluation status (ARCHITECTURE.md Decision)."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ReferenceObject(BaseModel):
    """Calibration reference target details."""

    model_config = ConfigDict(extra="forbid")

    present: bool = Field(description="True if a known reference object is in frame.")
    object_type: ReferenceObjectType = Field(
        default=ReferenceObjectType.NONE,
        description="Type of calibration object.",
    )
    known_dimension_mm: float | None = Field(
        default=None,
        description="Ground-truth reference dimension in millimetres.",
    )
    confidence_interval_mm: float | None = Field(
        default=None,
        description="Stated confidence interval (e.g. ±0.15 mm).",
    )
    bbox: list[float] | None = Field(
        default=None,
        description="Normalized bounding box [xmin, ymin, xmax, ymax] in [0, 1].",
    )


class PDPInfo(BaseModel):
    """Principal Display Panel dimensional attributes and Rule 7 banding."""

    model_config = ConfigDict(extra="forbid")

    shape: PDPShape = Field(description="Geometric shape classification.")
    height_cm: float | None = Field(default=None, description="Height in cm.")
    width_cm: float | None = Field(
        default=None, description="Width in cm (rectangular)."
    )
    circumference_cm: float | None = Field(
        default=None,
        description="Circumference in cm (cylindrical).",
    )
    total_surface_area_cm2: float | None = Field(
        default=None,
        description="Total package surface area in cm² (other shapes).",
    )
    area_cm2: float | None = Field(
        default=None,
        description="Calculated PDP area in cm² per Rule 7(4).",
    )
    is_measurable: bool = Field(
        default=True,
        description="True if PDP area can be reliably computed from package dimensions.",
    )
    rule7_band: Rule7TableBand | None = Field(
        default=None,
        description="Statutory band under Rule 7 Table-I.",
    )
    rule7_min_height_mm: float | None = Field(
        default=None,
        description="Statutory minimum numeral and letter height in mm for normal print.",
    )

    def calculate_rule7_band(self) -> tuple[Rule7TableBand | None, float | None]:
        """Compute the Rule 7 Table-I band and minimum height from area."""
        if self.area_cm2 is None:
            return None, None

        a = self.area_cm2
        if a <= 50.0:
            return Rule7TableBand.A_LE_50, 1.0
        elif a <= 100.0:
            return Rule7TableBand.A_50_TO_100, 1.5
        elif a <= 500.0:
            return Rule7TableBand.A_100_TO_500, 2.5
        elif a <= 2500.0:
            return Rule7TableBand.A_500_TO_2500, 4.0
        else:
            return Rule7TableBand.A_GT_2500, 6.0


class DeclarationField(BaseModel):
    """Ground-truth annotation for an individual statutory declaration."""

    model_config = ConfigDict(extra="forbid")

    declared: bool = Field(
        description="True if declaration is present on package label."
    )
    raw_text: str | None = Field(
        default=None,
        description="Verbatim text as printed on package.",
    )
    normalised_value: Any | None = Field(
        default=None,
        description="Structured or canonical normalized value for semantic verification.",
    )
    bbox: list[float] | None = Field(
        default=None,
        description="Normalized bounding box [xmin, ymin, xmax, ymax] in [0, 1].",
    )
    polygon: list[list[float]] | None = Field(
        default=None,
        description="Optional polygon boundary points [[x1, y1], [x2, y2], ...].",
    )
    numeral_height_mm: float | None = Field(
        default=None,
        description="Measured numeral height in mm. Only emitted from calibrated image.",
    )
    letter_height_mm: float | None = Field(
        default=None,
        description="Measured letter height in mm. Only emitted from calibrated image.",
    )
    expected_field_state: FieldComplianceState = Field(
        default=FieldComplianceState.PASS,
        description="Expected compliance outcome under LMPC Rules.",
    )
    non_compliance_reason: str | None = Field(
        default=None,
        description="Legal Metrology rationale if state is FAIL or REVIEW_REQUIRED.",
    )


class Rule6Declarations(BaseModel):
    """Container for Rule 6(1) and Rule 6(11) mandatory packaging declarations."""

    model_config = ConfigDict(extra="forbid")

    # Rule 6(1)(a): Manufacturer, packer, or importer identity & complete address
    manufacturer_or_packer: DeclarationField = Field(
        description="Rule 6(1)(a) Manufacturer/Packer/Importer/Marketed By name and address."
    )
    # Rule 6(1)(b): Generic or common name of the commodity
    commodity_name: DeclarationField = Field(
        description="Rule 6(1)(b) Common or generic name of commodity."
    )
    # Rule 6(1)(c): Net quantity in standard units (weight, volume, or count)
    net_quantity: DeclarationField = Field(
        description="Rule 6(1)(c) Net quantity in standard units of weight, volume, or count."
    )
    # Rule 6(1)(d): Month and year of manufacture, packing, or import (or best before / use by)
    date_of_manufacture_or_packing: DeclarationField = Field(
        description="Rule 6(1)(d) Month and year of manufacture/pre-packing/import."
    )
    # Rule 6(1)(e): Retail sale price (MRP inclusive of all taxes)
    retail_sale_price_mrp: DeclarationField = Field(
        description="Rule 6(1)(e) Maximum Retail Price (MRP) inclusive of all taxes."
    )
    # Rule 6(11): Unit Sale Price (USP) declared on statutory basis
    unit_sale_price: DeclarationField = Field(
        description="Rule 6(11) Unit Sale Price on required statutory unit basis."
    )
    # Rule 6(1)(n): Consumer care contact details
    consumer_care_details: DeclarationField = Field(
        description="Rule 6(1)(n) Consumer care contact cell: name, address, telephone, email."
    )
    # Rule 6(1)(g) & GSR 128(E): Country of origin
    country_of_origin: DeclarationField = Field(
        description="Rule 6(1)(g) / GSR 128(E) Country of origin declaration."
    )


class LabelledSample(BaseModel):
    """Top-level ground-truth annotation record for an individual packaging sample."""

    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(
        description="Unique sample identifier (e.g. food_parle_g_001)."
    )
    sku_id: str = Field(description="SKU identifier (e.g. food_parle_g_biscuits).")
    image_filename: str = Field(description="Filename of corresponding raw image.")
    image_sha256: str | None = Field(
        default=None,
        description="Cryptographic SHA-256 hash of the raw image for BSA 63(4) evidence integrity.",
    )
    category: Category = Field(description="Commodity category (food or cosmetics).")
    difficulty_tags: list[DifficultyTag] = Field(
        default_factory=list,
        description="List of environmental, physical, or optical challenge tags.",
    )
    known_issues: list[str] = Field(
        default_factory=list,
        description="Known Legal Metrology issues in this sample (e.g. missing_month_year).",
    )
    reference_object: ReferenceObject = Field(
        description="Calibration reference target details.",
    )
    pdp: PDPInfo = Field(
        description="Principal Display Panel parameters and Rule 7 band."
    )
    declarations: Rule6Declarations = Field(
        description="Ground-truth Rule 6(1) and 6(11) declarations.",
    )
    ground_truth_verdict: ComplianceVerdict = Field(
        description="Expected overall compliance verdict (PASS / REVIEW / POTENTIAL_VIOLATION).",
    )
    notes: str | None = Field(
        default=None,
        description="Curator notes regarding capture setup or label subtleties.",
    )


def export_json_schema(output_path: Path | str) -> None:
    """Generate and write the JSON Schema definition for external tools and validators."""
    schema = LabelledSample.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "LMPC Packaging Compliance Ground-Truth Annotation Schema"
    schema["description"] = (
        "Machine-readable schema for packaging compliance ground-truth annotations under LMPC 2011."
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


if __name__ == "__main__":
    target = Path(__file__).parent / "schema.json"
    export_json_schema(target)
    print(f"Exported JSON Schema to {target}")
