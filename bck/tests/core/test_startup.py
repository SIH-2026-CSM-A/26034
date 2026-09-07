"""The application refuses to start without the models it cannot run a scan without.

The check exists because the alternative is worse in a specific way. ``extract_panel_text``
raises ``FileNotFoundError`` and ``detect_pdp`` raises ``RuntimeError`` when their weights
are absent, and
without a startup gate that surfaces as a 500 on the first scan an officer submits — in
front of whoever is watching, on a machine that had been "working" all morning. Weights
are gitignored and pre-cached, so the case this guards is a fresh clone.

Never a fallback. A stage that cannot run must stop the application starting; substituting
a different stage would produce a verdict by a path nobody chose.
"""

from pathlib import Path

import pytest

from app.core.config import Settings, get_settings

WEIGHT_SETTINGS = (
    "ocr_det_model_dir",
    "ocr_rec_model_dir",
    "tesseract_tessdata_dir",
)
"""Every model path a scan needs, in the order :meth:`Settings.missing_model_paths`
reports them.

``pdp_weights_path`` is deliberately NOT here. CORE-005 removed it: there is no
PDP-trained detector, and pointing it at stock COCO weights is worse than leaving it unset,
because ``detect_pdp`` returns a box from whatever the detector hands back and that area
feeds the Rule 7 Table-I band lookup. Unset, VIS-008's heuristic supplies a region of a
distinct type, so a heuristic panel can never be mistaken for a model detection.
``tesseract_tessdata_dir`` is last because VIS-003 made ``extract_mrp_quantity``
raise ``FileNotFoundError`` without it. The chain does not call that function yet — the
constrained re-read needs a bound MRP crop and binding is EXT-004 — but it is checked at
startup all the same: the whole point of the gate is that the failure lands at boot rather
than the first time an officer scans a price."""


@pytest.fixture
def weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Three model paths that exist, so the check has something to pass against."""
    for name in WEIGHT_SETTINGS:
        path = tmp_path / name
        path.mkdir()
        monkeypatch.setenv(name.upper(), str(path))
    get_settings.cache_clear()
    return tmp_path


def test_missing_model_paths_names_every_unset_setting() -> None:
    """The message a deployment needs is which variable to set, not which file is absent."""
    settings = Settings(_env_file=None, jwt_secret="k" * 40)
    assert settings.missing_model_paths() == WEIGHT_SETTINGS


def test_a_path_that_does_not_exist_counts_as_missing(tmp_path: Path) -> None:
    """Set is not the same as present. A stale path from a previous checkout is missing."""
    settings = Settings(
        _env_file=None,
        jwt_secret="k" * 40,
        ocr_det_model_dir=tmp_path / "gone",
        ocr_rec_model_dir=tmp_path,
        tesseract_tessdata_dir=tmp_path,
    )
    assert settings.missing_model_paths() == ("ocr_det_model_dir",)


def test_an_absent_pdp_weights_path_does_not_block_startup(tmp_path: Path) -> None:
    """CORE-005. This is the behaviour change, pinned.

    The backend never booted on this project because pdp_weights_path was required and no
    PDP-trained detector exists. It is now optional; a missing one is not a missing model
    path, and detection degrades to VIS-008's heuristic rather than refusing to start."""
    settings = Settings(
        _env_file=None,
        jwt_secret="k" * 40,
        pdp_weights_path=tmp_path / "does-not-exist.pt",
        ocr_det_model_dir=tmp_path,
        ocr_rec_model_dir=tmp_path,
        tesseract_tessdata_dir=tmp_path,
    )
    assert settings.missing_model_paths() == ()


async def test_the_application_refuses_to_start_without_its_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup raises, naming the settings, and the app never serves a request."""
    from app.main import create_app, lifespan

    for name in WEIGHT_SETTINGS:
        monkeypatch.delenv(name.upper(), raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError) as raised:
        async with lifespan(create_app()):
            pytest.fail("the application started with no model weights")

    for name in WEIGHT_SETTINGS:
        assert name in str(raised.value)
    assert ".env.example" in str(raised.value)


async def test_the_application_starts_when_the_weights_are_there(weights: Path) -> None:
    """The counterpart: a check that refused everything would pass the test above."""
    from app.main import create_app, lifespan

    async with lifespan(create_app()):
        pass
