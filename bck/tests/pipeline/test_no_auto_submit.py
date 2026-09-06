"""Nothing reaches a finalised status without an officer, proved structurally.

A behavioural test can only show that the paths *it thought to try* do not finalise a
scan. The guarantee needed here is about every path, including ones written later, so it
is asserted about the source itself: a scan is finalised exactly when a
:class:`~app.core.models.ReviewRow` exists carrying a finalising action, and there is
exactly one place in the application that constructs one.

That makes "no automated path finalises a scan" checkable rather than promised. Add a
second constructor anywhere — a background job, a re-evaluation, a convenience helper on
the submit route — and this goes red.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
CONSTRUCTOR = "ReviewRow"
EXPECTED_SITE = "pipeline/repository.py"
EXPECTED_FUNCTION = "record_review"


def _python_files() -> list[Path]:
    return sorted(APP.rglob("*.py"))


def _construction_sites() -> list[tuple[str, str, int]]:
    """Every ``ReviewRow(...)`` call in the application, as (file, enclosing def, line)."""
    sites: list[tuple[str, str, int]] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        enclosing: dict[int, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    enclosing.setdefault(line, node.name)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == CONSTRUCTOR
            ):
                relative = path.relative_to(APP.parent).as_posix().removeprefix("app/")
                sites.append((relative, enclosing.get(node.lineno, "<module>"), node.lineno))
    return sites


def test_the_scan_reads_a_non_zero_number_of_files() -> None:
    """The scan above must actually scan something.

    This project has shipped a directory scan that resolved a relative path against the
    working directory, found nothing, and passed. An empty sweep asserting an empty result
    is a green tick that means nothing, so the sweep is checked before its findings are.
    """
    files = _python_files()
    assert len(files) > 20, f"only {len(files)} python files found under {APP}"
    assert any(path.name == "repository.py" for path in files)


def test_a_review_is_constructed_in_exactly_one_place() -> None:
    """One constructor, in the repository, inside ``record_review``.

    Finalisation is the existence of a review row. A second construction site is a second
    way for something other than an officer to end a scan, whatever it is called and
    whatever it intends.
    """
    sites = _construction_sites()
    assert sites, f"no {CONSTRUCTOR} construction found at all — has it been renamed?"
    assert len(sites) == 1, f"{CONSTRUCTOR} is constructed in more than one place: {sites}"

    (file, function, _line) = sites[0]
    assert file == EXPECTED_SITE, f"{CONSTRUCTOR} is constructed in {file}, not {EXPECTED_SITE}"
    assert function == EXPECTED_FUNCTION, (
        f"{CONSTRUCTOR} is constructed in {function}(), not {EXPECTED_FUNCTION}()"
    )


def test_the_orchestrator_cannot_finalise_anything() -> None:
    """The evaluation chain does not mention reviews at all.

    Belt and braces on the count above, and it names the specific thing that must never
    happen: the pipeline that produces a verdict must not also be able to accept it.
    """
    for name in ("orchestrator.py", "findings.py", "rule_findings.py", "verdict.py"):
        source = (APP / "pipeline" / name).read_text(encoding="utf-8")
        assert CONSTRUCTOR not in source, f"{name} references {CONSTRUCTOR}"
        assert "ReviewAction" not in source, f"{name} references ReviewAction"
