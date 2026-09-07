"""Guard the import-linter configuration itself.

`lint-imports` only checks the contracts it is given. A module added to
`app/modules/` without a matching entry in the independence contract would import
freely and CI would stay green. These tests close that gap: the contracts in
pyproject.toml must describe exactly what is on disk.
"""

import tomllib
from pathlib import Path

BCK = Path(__file__).resolve().parents[1]
PYPROJECT = BCK / "pyproject.toml"
MODULES_DIR = BCK / "app" / "modules"

EXPECTED_LAYERS = [
    "app.main",
    "app.pipeline",
    "app.modules",
    "app.core",
    "app.contracts",
]
"""The layer order, top first.

``app.main`` is in the contract rather than left outside it because a layers contract only
constrains the layers it names. Without this entry nothing would stop a module importing
the FastAPI application, which would make the composition circular and would do it
silently.
"""


def _import_linter_config() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)["tool"]["importlinter"]


def _contract(contract_type: str) -> dict:
    matches = [c for c in _import_linter_config()["contracts"] if c["type"] == contract_type]
    assert len(matches) == 1, f"expected exactly one {contract_type!r} contract, got {len(matches)}"
    return matches[0]


def _packages_on_disk() -> set[str]:
    return {
        path.name
        for path in MODULES_DIR.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }


def test_root_package_is_app() -> None:
    assert _import_linter_config()["root_package"] == "app"


def test_layers_contract_orders_every_layer() -> None:
    assert _contract("layers")["layers"] == EXPECTED_LAYERS


def test_independence_contract_covers_every_module_on_disk() -> None:
    declared = {name.rsplit(".", 1)[-1] for name in _contract("independence")["modules"]}
    assert declared == _packages_on_disk(), (
        "app/modules/ and the independence contract in pyproject.toml disagree. "
        "A new module must be added to the contract, or it has no enforced boundary."
    )


def test_independence_contract_lists_the_seven_modules() -> None:
    assert _contract("independence")["modules"] == [
        "app.modules.analytics",
        "app.modules.vision",
        "app.modules.extraction",
        "app.modules.measurement",
        "app.modules.rules",
        "app.modules.tamper",
        "app.modules.evidence",
    ]
