"""Tests for strict loading of the committed YAML rule store."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from app.modules.rules import RuleLoadError, load_rules

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CORPUS_DIRECTORY = REPOSITORY_ROOT / "rules-corpus"
RULE_STORE_PATH = REPOSITORY_ROOT / "bck" / "app" / "modules" / "rules" / "data" / "rules.yaml"
EXISTING_GAZETTE = "GSR-629E__2017-06-23__amendment-rules-2017.pdf"


def _valid_rule_payload() -> dict[str, object]:
    """Return a minimal valid rule payload for loader validation tests."""
    return {
        "rule_id": "TEST-RULE",
        "clause_ref": "Test clause",
        "gazette_ref": EXISTING_GAZETTE,
        "source_text": "Synthetic source text used only by a schema test.",
        "status": "VERIFIED",
        "effective_from": "2020-01-01",
        "effective_to": None,
        "applies_to": ["test_input"],
        "conditions": {
            "kind": "declaration_required",
            "declarations": ["test_declaration"],
            "exceptions": [],
        },
        "evidence_requirement": "test_evidence",
        "severity": "POTENTIAL VIOLATION",
    }


def _write_rule_store(tmp_path: Path, rule_payload: dict[str, object]) -> Path:
    """Write a temporary YAML store containing one supplied rule payload."""
    store_path = tmp_path / "rules.yaml"
    store_path.write_text(
        yaml.safe_dump({"schema_version": 1, "rules": [rule_payload]}),
        encoding="utf-8",
    )
    return store_path


def test_missing_gazette_ref_hard_fails_loading(tmp_path: Path) -> None:
    """Removing gazette_ref must make the complete load fail."""
    payload = _valid_rule_payload()
    del payload["gazette_ref"]

    with pytest.raises(RuleLoadError, match="gazette_ref"):
        load_rules(_write_rule_store(tmp_path, payload), corpus_dir=CORPUS_DIRECTORY)


@pytest.mark.parametrize("gazette_ref", ["", "missing.pdf", "../rules-corpus/file.pdf"])
def test_invalid_gazette_ref_hard_fails_loading(
    tmp_path: Path,
    gazette_ref: str,
) -> None:
    """Empty, absent, and path-like gazette references must be rejected."""
    payload = _valid_rule_payload()
    payload["gazette_ref"] = gazette_ref

    with pytest.raises(RuleLoadError, match="gazette_ref"):
        load_rules(_write_rule_store(tmp_path, payload), corpus_dir=CORPUS_DIRECTORY)


def test_unknown_rule_field_hard_fails_loading(tmp_path: Path) -> None:
    """Adding an unknown top-level field must fail strict schema validation."""
    payload = _valid_rule_payload()
    payload["unexpected"] = "forbidden"

    with pytest.raises(RuleLoadError, match="unexpected"):
        load_rules(_write_rule_store(tmp_path, payload), corpus_dir=CORPUS_DIRECTORY)


def test_unknown_condition_field_hard_fails_loading(tmp_path: Path) -> None:
    """Adding an unknown nested condition field must fail strict validation."""
    payload = _valid_rule_payload()
    condition = deepcopy(payload["conditions"])
    assert isinstance(condition, dict)
    condition["unexpected"] = "forbidden"
    payload["conditions"] = condition

    with pytest.raises(RuleLoadError, match="unexpected"):
        load_rules(_write_rule_store(tmp_path, payload), corpus_dir=CORPUS_DIRECTORY)


def test_malformed_yaml_hard_fails_loading(tmp_path: Path) -> None:
    """Syntactically malformed YAML must fail without partial rule output."""
    store_path = tmp_path / "rules.yaml"
    store_path.write_text("rules: [unterminated", encoding="utf-8")

    with pytest.raises(RuleLoadError, match="YAML"):
        load_rules(store_path, corpus_dir=CORPUS_DIRECTORY)


def test_every_encoded_rule_has_source_text_and_existing_gazette() -> None:
    """Every shipped rule must retain source text and resolve its corpus file."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)

    assert rules
    for rule in rules:
        assert rule.source_text.strip()
        assert (CORPUS_DIRECTORY / rule.gazette_ref).is_file()


def test_rule_store_excludes_f18_and_rule_6_11() -> None:
    """RUL-001 data must not include the deferred F18 or Rule 6(11) behavior."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)

    searchable = " ".join(f"{rule.rule_id} {rule.clause_ref}" for rule in rules).lower()
    assert "f18" not in searchable
    assert "6(11)" not in searchable


def test_rule_store_contains_only_ticket_authorized_scopes() -> None:
    """The store must not grow unrelated commodity-category rules."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)
    allowed_scopes = {
        "retail_packages",
        "imported_packages",
        "electronic_products_spare_parts_and_accessories",
        "medical_device_packages",
        "ecommerce_imported_product_listings",
    }

    assert {scope for rule in rules for scope in rule.applies_to} <= allowed_scopes


EXPECTED_RULE_GAZETTE_MAPPING: dict[str, str] = {
    "R6-1-A": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-AA": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R6-1-B": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-C": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-D": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-D-GSR-722E": "GSR-722E__2023-10-06__amendment-rules-2023.pdf",
    "R6-1-DA": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R6-1-E": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-F": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-G": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R7-2-TABLE-I": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R7-3-WIDTH-RATIO": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R7-4-PDP-AREA": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R7-5-OTHER-LAW": "GSR-629E__2017-06-23__amendment-rules-2017.pdf",
    "R7-MEDICAL-DEVICE-OVERRIDE": "GSR-778E__2025-10-23__medical-devices-mdr-2017.pdf",
    "R6-1-A-EXPL-III-FOOD": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R6-1-D-COSMETICS": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R8-1-PDP-PLACEMENT": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R8-1-FREE-SPACE": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R9-1-MANNER": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R9-3-OUTER-CONTAINER": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    "R2-KA-COMBINATION-PACKAGE": "GSR-722E__2023-10-06__amendment-rules-2023.pdf",
    "R2-KB-GROUP-PACKAGE": "GSR-722E__2023-10-06__amendment-rules-2023.pdf",
    "R6-10A-GSR-128E": "GSR-128E__2026-02-13__country-of-origin-ecommerce-filter.pdf",
    "R6-10A-GSR-312E": "GSR-312E__2026-04-27__country-of-origin-second-amendment.pdf",
}


def test_explicit_rule_id_gazette_provenance_mapping() -> None:
    """Each encoded rule must map explicitly to its designated gazette corpus source."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)
    actual_mapping = {rule.rule_id: rule.gazette_ref for rule in rules}
    assert actual_mapping == EXPECTED_RULE_GAZETTE_MAPPING


def test_a_rule_citing_an_absent_corpus_file_fails_to_load(tmp_path: Path) -> None:
    """A well-formed gazette_ref naming a file nobody has is still a failed load.

    The filename passes schema validation — it is a bare PDF name — so nothing but the
    corpus check stands between a plausible-looking citation and a rule that cannot be
    traced to a document. The failure names the rule so the citation can be fixed rather
    than the check removed.
    """
    payload = _valid_rule_payload()
    payload["gazette_ref"] = "GSR-999E__2099-01-01__a-gazette-nobody-downloaded.pdf"

    with pytest.raises(RuleLoadError, match="TEST-RULE gazette_ref does not exist"):
        load_rules(_write_rule_store(tmp_path, payload), corpus_dir=CORPUS_DIRECTORY)


def test_the_shipped_store_resolves_every_citation_against_the_real_corpus() -> None:
    """The same gate, exercised against the committed store rather than a fixture."""
    for rule in load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY):
        assert (CORPUS_DIRECTORY / rule.gazette_ref).is_file()
