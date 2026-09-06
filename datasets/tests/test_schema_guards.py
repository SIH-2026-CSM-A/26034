"""Guards on the ground-truth schema itself.

These exist because four fabricated annotations reached `main` and were reviewed
four times in writing without anyone loading them with `schema.py`. The corpus
that replaces them has to fail loudly at write time instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

DATASETS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATASETS_DIR))

from schema import (  # noqa: E402
    LabelledSample,
    ReferenceObject,
    ReferenceObjectType,
)


class TestReferenceObjectCoherence:
    """A calibration claim must be backed by an identified object of known size."""

    def test_present_without_object_type_is_refused(self) -> None:
        """The exact shape of the deleted food_parle_g_biscuits_001 annotation."""
        with pytest.raises(ValidationError, match="object_type is 'none'"):
            ReferenceObject.model_validate({"present": True, "object_type": "none"})

    def test_present_without_known_dimension_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="known_dimension_mm is null"):
            ReferenceObject.model_validate({"present": True, "object_type": "coin_10"})

    def test_absent_but_naming_an_object_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="object_type names an object"):
            ReferenceObject.model_validate({"present": False, "object_type": "coin_10"})

    def test_absent_but_carrying_a_dimension_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="carries a dimension or bbox"):
            ReferenceObject.model_validate(
                {
                    "present": False,
                    "object_type": "none",
                    "known_dimension_mm": 27.0,
                }
            )

    def test_a_real_calibrated_capture_is_accepted(self) -> None:
        ref = ReferenceObject.model_validate(
            {
                "present": True,
                "object_type": "coin_10",
                "known_dimension_mm": 27.0,
                "bbox": [0.05, 0.75, 0.18, 0.95],
            }
        )
        assert ref.object_type is ReferenceObjectType.COIN_10

    def test_an_honest_uncalibrated_capture_is_accepted(self) -> None:
        ref = ReferenceObject.model_validate({"present": False, "object_type": "none"})
        assert ref.known_dimension_mm is None


class TestSourcedDimensionsOnly:
    """Only reference dimensions with a source may be offered."""

    def test_unsourced_coins_are_not_offered(self) -> None:
        """The Rs 5 coin at 25.0 mm is on the Hard Nos list; Rs 1 and Rs 2 are unsourced too.

        Both spellings are named because DAT-004 moved this enum onto measurement's
        vocabulary. Someone re-adding an unsourced coin today would reach for the new
        spelling, and someone reverting an old annotation for the previous one.
        """
        offered = {member.value for member in ReferenceObjectType}
        assert offered.isdisjoint(
            {"coin_1", "coin_2", "coin_5", "coin_inr_1", "coin_inr_2", "coin_inr_5"}
        )

    def test_the_rs10_coin_remains_available(self) -> None:
        assert ReferenceObjectType.COIN_10.value == "coin_10"


class TestMeasurementCanConsumeEveryOfferedObject:
    """A member exists only alongside its REF_DIMS entry and its detector branch.

    A member without both is unreachable capability: an annotation naming it falls
    through every branch of ``detect_reference_object`` to the terminal
    MeasurementRefusal, and nothing anywhere reports that the vocabularies disagree.
    That is what DAT-004 fixed. Annotations said ``coin_inr_10`` while measurement
    dispatched on ``coin_10``, so no annotation could reach measurement at all; and
    ``aruco_marker``, ``ruler_scale`` and ``checkerboard`` were offered with no
    dimension and no branch behind any of them.

    Measurement's names are authoritative --
    ``app.pipeline.orchestrator.Calibration.reference_type`` is documented as "the
    reference object in frame, as ``app.modules.measurement`` names it". When ArUco or
    a checkerboard is genuinely built, the member is added in the same PR as its
    dimension and its branch, which is why this guard carries no exemption list.
    """

    def test_every_offered_object_is_a_ref_dims_key(self) -> None:
        """Imports app from a test outside bck/. Needs bck installed (CI-004)."""
        from app.modules.measurement.services import REF_DIMS

        offered = {m.value for m in ReferenceObjectType} - {ReferenceObjectType.NONE.value}
        assert offered <= set(REF_DIMS), (
            f"schema offers {sorted(offered - set(REF_DIMS))}, which measurement "
            "cannot calibrate from -- an annotation naming one routes to "
            "MeasurementRefusal"
        )


class TestCommittedAnnotationsLoad:
    """Every tracked annotation must load. This is what was never run."""

    def test_every_annotation_validates(self) -> None:
        files = sorted((DATASETS_DIR / "annotations").glob("*/*.json"))
        if not files:
            pytest.skip("corpus is empty pending real captures (DAT-002)")
        for path in files:
            LabelledSample.model_validate(json.loads(path.read_text()))

    def test_no_annotation_claims_a_millimetre_height(self) -> None:
        """Heights come from a calibrated measurement, never from an annotator."""
        files = sorted((DATASETS_DIR / "annotations").glob("*/*.json"))
        if not files:
            pytest.skip("corpus is empty pending real captures (DAT-002)")
        for path in files:
            sample = LabelledSample.model_validate(json.loads(path.read_text()))
            if sample.reference_object.present:
                continue
            for name, field in sample.declarations.model_dump().items():
                assert field["numeral_height_mm"] is None, (
                    f"{path.name}: {name} carries a numeral height on an "
                    "uncalibrated capture"
                )
                assert field["letter_height_mm"] is None, (
                    f"{path.name}: {name} carries a letter height on an "
                    "uncalibrated capture"
                )
