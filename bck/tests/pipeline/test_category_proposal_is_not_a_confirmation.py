"""A proposal never reaches the officer's confirmed category, proved about the source.

``Scan.product_category`` is the officer's answer to "which Act governs this package", and
the sector dispatch routes obligations on it. ``CategoryProposal`` is a reading the
pipeline offers so that question can be asked. ``ARCHITECTURE.md`` states the separation as
a decision: a confirmed product category is a precondition of rule evaluation, not a filter
after it.

``test_orchestrator.py`` shows behaviourally that the pipeline does not *act* on a
proposal — a live ``food`` proposal leaves all thirty sector-gated findings exactly where
they were. That is a statement about the paths those tests thought to try. This is the
other half, and it is about every path including ones written later: the row is built in
one place, and that place cannot see a proposal at all.

Substring and AST checks catch the shape somebody would actually write. A determined
bypass — aliasing the import, building the name at runtime — would get through. This is a
guard rail on the path people walk, not a proof.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
ROW = "Scan"
EXPECTED_SITE = "pipeline/repository.py"
EXPECTED_FUNCTION = "new_scan"
PROPOSAL_NAMES = ("CategoryProposal", "propose_category")


def _python_files() -> list[Path]:
    return sorted(APP.rglob("*.py"))


def _construction_sites() -> list[tuple[str, str, int]]:
    """Every ``Scan(...)`` call in the application, as (file, enclosing def, line).

    A ``Call`` on a bare ``Name``, so ``class Scan(Base)`` in ``core/models.py`` is not a
    construction and ``ImageScanResult(...)`` is not this row.
    """
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
                and node.func.id == ROW
            ):
                relative = path.relative_to(APP.parent).as_posix().removeprefix("app/")
                sites.append((relative, enclosing.get(node.lineno, "<module>"), node.lineno))
    return sites


def test_the_scan_reads_a_non_zero_number_of_files() -> None:
    """The sweep must scan something before an empty result means anything.

    This project has shipped a directory scan that resolved a relative path against the
    working directory, found nothing, and passed. Checking the sweep before its findings
    is the cheapest way not to ship the sixth unfalsifiable test.
    """
    files = _python_files()
    assert len(files) > 20, f"only {len(files)} python files found under {APP}"
    assert any(path.name == "repository.py" for path in files)


def test_a_scan_row_is_constructed_in_exactly_one_place() -> None:
    """One constructor, in the repository, inside ``new_scan``.

    ``new_scan`` takes the category as an argument and the routes fill it from the request
    body or the submitted form field. A second construction site is a second way for
    something other than an officer to decide which Act governs a package.
    """
    sites = _construction_sites()
    assert sites, f"no {ROW} construction found at all — has it been renamed?"
    assert len(sites) == 1, f"{ROW} is constructed in more than one place: {sites}"

    (file, function, _line) = sites[0]
    assert file == EXPECTED_SITE, f"{ROW} is constructed in {file}, not {EXPECTED_SITE}"
    assert function == EXPECTED_FUNCTION, (
        f"{ROW} is constructed in {function}(), not {EXPECTED_FUNCTION}()"
    )


def test_the_module_that_writes_the_confirmed_category_cannot_see_a_proposal() -> None:
    """The repository does not mention proposals, so it has none to write.

    The one function that sets ``Scan.product_category`` reads it from an argument the
    request boundary supplies. Importing a proposal into this module is the single edit
    that would let a reading be stored as a confirmation, and it is the edit this refuses.
    """
    source = (APP / "pipeline" / "repository.py").read_text(encoding="utf-8")
    for name in PROPOSAL_NAMES:
        assert name not in source, (
            f"pipeline/repository.py references {name}. It is the only place "
            f"Scan.product_category is written, and a proposal is not a confirmation: an "
            f"officer decides which Act governs a package, and a regex over OCR text does "
            f"not get to decide it for them."
        )
