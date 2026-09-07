import pytest

from app.modules.vision.ocr import _extract_numeric_value, _parse_paddle_results


def test_extract_numeric_value_graceful_fail():
    # Renamed per Abhiram instruction: this function returns empty string rather than throwing
    res = _extract_numeric_value("NO_NUMBERS_HERE_AT_ALL")
    assert res == "" or res is None


def test_parse_paddle_results_invalid_type():
    with pytest.raises(TypeError):
        _parse_paddle_results(["not_a_dict"])


def test_missing_score():
    res = {
        "dt_polys": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
        "rec_texts": ["TEST"],
    }
    with pytest.raises(KeyError):
        _parse_paddle_results(res)


def test_missing_fields():
    with pytest.raises(KeyError):
        _parse_paddle_results({"dummy": "data"})


def test_strict_zip():
    res = {
        "dt_polys": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
        "rec_texts": ["TEST1", "TEST2"],
        "rec_scores": [0.9],
    }
    with pytest.raises(ValueError):
        _parse_paddle_results(res)
