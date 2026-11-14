"""Tests for custom areas (rectangle validation and drawn shapes).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import pytest

from trend.area import AreaError, bbox_from_drawing, format_bbox, normalize_bbox


def test_valid_rectangle_is_kept():
    bbox, widened = normalize_bbox(27, 40, 30, 42)
    assert bbox == (27.0, 40.0, 30.0, 42.0)
    assert not widened


def test_small_rectangle_is_widened_to_two_degrees_around_its_center():
    bbox, widened = normalize_bbox(28.5, 40.8, 29.5, 41.3)
    assert widened
    assert bbox == (28.0, 40.05, 30.0, 42.05)


def test_widened_rectangle_stays_inside_the_globe():
    bbox, _ = normalize_bbox(179.5, 89.5, 180.0, 90.0)
    assert bbox[2] == 180.0 and bbox[3] == 90.0
    assert bbox[2] - bbox[0] == pytest.approx(2.0)


@pytest.mark.parametrize(
    "box, code",
    [((30, 40, 27, 42), "order"), ((20, 30, 32, 42), "too_big"), ((0, 0, 0, 95), "range")],
)
def test_bad_rectangles_are_rejected(box, code):
    with pytest.raises(AreaError) as error:
        normalize_bbox(*box)
    assert error.value.code == code


def test_bbox_from_drawn_rectangle():
    drawing = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[27.0, 40.0], [27.0, 42.0], [30.0, 42.0], [30.0, 40.0], [27.0, 40.0]]],
        },
    }
    assert bbox_from_drawing(drawing) == (27.0, 40.0, 30.0, 42.0)
    assert bbox_from_drawing(None) is None
    assert bbox_from_drawing({"geometry": {"type": "Point", "coordinates": [1, 2]}}) is None


def test_app_runs_a_custom_area_with_live_data(monkeypatch):
    """Custom mode uses live POWER data (replaced here by synthetic data, so no network)."""
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    import trend.fetch

    def fake_fetch(variable, region, start_year, end_year):
        dates = pd.date_range("1981-01-01", "2025-12-01", freq="MS")
        rng = np.random.default_rng(0)
        values = 10 + 0.03 * (dates.year - 1981) + rng.normal(0, 0.5, dates.size)
        return pd.DataFrame({"date": dates, "value": values, "n_cells": 25}), "MERRA2"

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", fake_fetch)
    app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app, default_timeout=60)
    at.session_state["area_mode"] = "custom"
    at.session_state["custom_bbox"] = (27.0, 40.0, 30.0, 42.0)
    at.run()
    assert not at.exception
    assert at.session_state["case"] in ("air_temperature", "snowfall")
    assert any("Custom area" in h.value for h in at.header)


def test_format_bbox_uses_compass_letters():
    assert format_bbox((-109.05, 37.0, -102.04, 41.0)) == "109.0°W–102.0°W, 37.0°N–41.0°N"
