"""One span, one identity. The pipeline never mints a second.

``app.modules.vision`` builds every :class:`~app.contracts.ExtractedSpan` — it mints the
``span_id``, sets the ``source_provider`` and writes the ``region_id``. The pipeline passes
them through and changes nothing.

That is not tidiness. ``FieldFinding.evidence_span_ids`` cites spans by id, so a pipeline
that re-minted identifiers would produce two ids for one run of text: the finding would
cite one, the stored spans would carry the other, and the evidence bundle would point at a
span nobody can find. It would break silently, and only for the findings that actually cite
evidence — which today is none of them, because EXT-004 is not merged. So this is asserted
structurally rather than left to be discovered later.
"""

import ast
from pathlib import Path

import pytest

PIPELINE = Path(__file__).resolve().parents[2] / "app" / "pipeline"
FORBIDDEN_KEYWORDS = ("span_id", "source_provider", "region_id")


def _pipeline_files() -> list[Path]:
    return sorted(PIPELINE.glob("*.py"))


def test_the_sweep_reads_the_pipeline_package() -> None:
    """The scan must scan something before its findings mean anything."""
    files = _pipeline_files()
    assert len(files) >= 10, f"only {len(files)} files found under {PIPELINE}"
    assert any(path.name == "orchestrator.py" for path in files)


def test_the_pipeline_never_constructs_an_extracted_span() -> None:
    """Constructing one here would be minting a second identity for one run of text."""
    built: list[str] = []
    for path in _pipeline_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ExtractedSpan"
            ):
                built.append(f"{path.name}:{node.lineno}")
    assert built == [], (
        f"app.pipeline constructs an ExtractedSpan at {built}. Vision owns a span's "
        f"identity; a second one minted here makes evidence_span_ids cite a span that "
        f"nothing else in the record can find."
    )


def _writes_of(field: str, tree: ast.AST, where: str) -> list[str]:
    """Every place a module writes ``field``, by any of the three routes that work.

    A keyword argument catches ``ExtractedSpan(region_id=...)``. A string key in a dict
    literal catches ``span.model_copy(update={"region_id": ...})``, which is how a field
    on a frozen model is actually overwritten and which an earlier version of this test
    missed entirely. An attribute store catches ``span.region_id = ...``, which pydantic
    would reject at runtime but which should not be written in the first place.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == field:
            found.append(f"{where}:{node.lineno} (keyword)")
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value == field:
                    found.append(f"{where}:{key.lineno} (dict key)")
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Store)
            and node.attr == field
        ):
            found.append(f"{where}:{node.lineno} (attribute)")
    return found


@pytest.mark.parametrize("field", FORBIDDEN_KEYWORDS)
def test_the_pipeline_never_assigns_a_span_identity_field(field: str) -> None:
    """Nothing in this package writes a span's identity or its region, by any route.

    ``region_id`` is in the list on purpose. It is the one field that looked worth
    overwriting — vision hardcodes ``"panel"`` — and the reason not to is in
    :func:`app.pipeline.orchestrator.run_image_scan`: the OCR call is handed the whole
    frame rather than a crop of the detected panel, so stamping the panel's identity on
    those spans would assert a provenance nothing established.

    All three write routes are checked because the first version of this test checked only
    keyword arguments, and ``model_copy(update={"region_id": ...})`` — the obvious way to
    change a field on a frozen model, and the way somebody would actually do it — walked
    straight past it.
    """
    written = [
        site
        for path in _pipeline_files()
        for site in _writes_of(
            field, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), path.name
        )
    ]
    assert written == [], f"app.pipeline sets {field} at {written}; that is vision's field"


def _vision_still_has_its_own_span_type() -> bool:
    """Whether VIS-003 has landed, read off the module rather than assumed."""
    from app.contracts import ExtractedSpan
    from app.modules.vision import ocr

    return getattr(ocr, "ExtractedSpan", None) is not ExtractedSpan


@pytest.mark.skipif(
    _vision_still_has_its_own_span_type(),
    reason=(
        "VIS-003 is not merged: app.modules.vision.ocr still defines its own ExtractedSpan "
        "dataclass. This runs for real the moment that branch lands, which is when the "
        "pipeline starts depending on vision returning the contract type."
    ),
)
def test_vision_hands_the_pipeline_contract_spans() -> None:
    """After VIS-003, ``extract_panel_text`` returns contract spans and nothing adapts them.

    The pipeline stopped adapting when VIS-003 was written, so this is the assertion that
    the thing it stopped adapting is the thing it now expects. Skipped rather than left
    green while vision still returns its own dataclass — the skip reason names the branch,
    and the condition is read off the module, so it un-skips itself.
    """
    from app.contracts import ExtractedSpan
    from app.modules.vision import ocr

    assert ocr.ExtractedSpan is ExtractedSpan
    annotation = ocr.extract_panel_text.__annotations__["return"]
    assert "ExtractedSpan" in str(annotation)
