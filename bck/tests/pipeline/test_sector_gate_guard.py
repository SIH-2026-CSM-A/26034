"""Keep :func:`sector_gate.findings_for_rule` the only way a test picks a rule's findings.

The helper cannot protect a test that does not call it, so this refuses the bypass: a
direct ``rule_snapshot.rule_id == "R…"`` comparison anywhere else in this package. That is
the shape all six masked selections had, and it is the shape somebody writing the seventh
would reach for.

Membership tests are left alone — ``rule_id in SECTOR_GOVERNED_RULES`` is how the gate's
own test selects what it is about, and it cannot be masked by the gate because the gate is
the subject.

This catches the common shape rather than every conceivable one; a determined bypass
(building the literal at runtime, comparing inside a nested helper) would get through. It
is a guard rail on the path people actually walk, not a proof.
"""

import ast
from pathlib import Path

PIPELINE_TESTS = Path(__file__).resolve().parent
HELPER = "sector_gate.py"


def _test_modules() -> list[Path]:
    return sorted(p for p in PIPELINE_TESTS.glob("*.py") if p.name != HELPER)


def _finding_selections(tree: ast.AST, *, literal_only: bool) -> list[int]:
    """Lines selecting a finding by its rule: ``….rule_snapshot.rule_id == …``.

    The attribute *chain* is what distinguishes selection from assertion, and getting that
    wrong the first time flagged ``test_rule_snapshot.py``, which asserts
    ``snapshot.rule_id == "R6-1-A"`` about a snapshot it built itself. There is no gate
    anywhere near that and no finding to be masked, so requiring the comparison to reach
    through ``rule_snapshot`` keeps the guard on selections and off assertions.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        if not (isinstance(left, ast.Attribute) and left.attr == "rule_id"):
            continue
        if not (isinstance(left.value, ast.Attribute) and left.value.attr == "rule_snapshot"):
            continue
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            if not isinstance(operator, ast.Eq):
                continue
            if literal_only and not isinstance(comparator, ast.Constant):
                continue
            lines.append(node.lineno)
    return lines


def test_the_sweep_reads_the_test_package() -> None:
    """The scan must scan something before its result means anything."""
    modules = _test_modules()
    assert len(modules) >= 4, f"only {len(modules)} modules found under {PIPELINE_TESTS}"
    assert any(p.name == "test_findings.py" for p in modules)


def test_no_test_selects_a_rule_without_the_guard() -> None:
    """Every rule-id selection goes through the helper that refuses gate-settled results."""
    offenders: list[str] = []
    for path in _test_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [
            f"{path.name}:{line}" for line in _finding_selections(tree, literal_only=True)
        ]
    assert offenders == [], (
        f"these compare rule_id to a literal directly: {offenders}. Use "
        f"sector_gate.findings_for_rule instead — with no confirmed product category a "
        f"sector-gated rule is settled before its own builder runs, and a direct selection "
        f"cannot tell you that happened. Six selections in this package were wrong that way."
    )


def test_the_helper_itself_is_exempt_and_still_does_the_comparison() -> None:
    """The exemption is real: the helper is where the comparison is supposed to live.

    Without this, deleting the comparison from the helper would leave the test above
    passing over a package that no longer selects anything at all.
    """
    helper = ast.parse((PIPELINE_TESTS / HELPER).read_text(encoding="utf-8"))
    assert _finding_selections(helper, literal_only=False), (
        f"{HELPER} no longer selects findings by rule_id; the guard above is now asserting "
        f"the absence of something nothing in this package does, which would pass over a "
        f"suite that had stopped selecting rules altogether"
    )
