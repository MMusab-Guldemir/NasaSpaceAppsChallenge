"""Tests for custom areas (rectangle validation and drawn shapes).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import random

import pytest

from trend.area import (
    AreaError,
    bbox_from_drawing,
    format_bbox,
    normalize_bbox,
    pick_drawn_bbox,
)


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

    def fake_fetch(variable, region, start_year, end_year, timeout=300):
        assert timeout != 300  # the app uses a short timeout for live requests
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


@pytest.mark.parametrize(
    "box",
    [
        (-54.03, -8.23, -44.03, -6.24),
        (127.18, -0.01, 129.18, 0.02),
        (10, 7.11, 12, 9.11),  # float difference 1.9999999999999991, rejected by NASA POWER
        (10, 55.73, 12, 65.73),  # float difference 10.000000000000007, rejected by NASA POWER
        (179.0, -90.0, 180.0, -89.5),
    ],
)
def test_spans_sent_to_power_are_within_limits_in_plain_floats(box):
    (west, south, east, north), _ = normalize_bbox(*box)
    assert 2 <= east - west <= 10
    assert 2 <= north - south <= 10
    assert -180 <= west < east <= 180 and -90 <= south < north <= 90


def test_random_rectangles_always_fit_power_limits():
    rng = random.Random(7)
    for _ in range(20000):
        width, height = rng.uniform(0.01, 10), rng.uniform(0.01, 10)
        west = round(rng.uniform(-180, 180 - width), 2)
        south = round(rng.uniform(-90, 90 - height), 2)
        east, north = round(west + width, 2), round(south + height, 2)
        if east <= west or north <= south or east - west > 10 + 1e-9 or north - south > 10 + 1e-9:
            continue
        (w, s, e, n), _ = normalize_bbox(west, south, east, north)
        assert 2 <= e - w <= 10 and 2 <= n - s <= 10
        assert -180 <= w and e <= 180 and -90 <= s and n <= 90


def test_exactly_two_degrees_is_not_reported_as_widened():
    _, widened = normalize_bbox(10, 7.11, 12, 9.11)
    assert not widened


def rectangle(west, south, east, north):
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}}


def test_edited_rectangle_is_found_in_all_drawings():
    active = (27.0, 40.0, 30.0, 42.0)
    state = {"last_active_drawing": None, "all_drawings": [rectangle(28.0, 40.5, 31.0, 42.5)]}
    assert pick_drawn_bbox(state, active) == (28.0, 40.5, 31.0, 42.5)


def test_new_rectangle_wins_over_the_unchanged_original():
    active = (27.0, 40.0, 30.0, 42.0)
    new = rectangle(10.0, 45.0, 14.0, 48.0)
    state = {"last_active_drawing": new, "all_drawings": [rectangle(*active), new]}
    assert pick_drawn_bbox(state, active) == (10.0, 45.0, 14.0, 48.0)


def test_edit_after_draw_uses_the_edited_shape():
    active = (27.0, 40.0, 30.0, 42.0)
    before_edit = rectangle(10.0, 45.0, 14.0, 48.0)
    after_edit = rectangle(11.0, 45.0, 15.0, 48.0)
    state = {"last_active_drawing": before_edit, "all_drawings": [rectangle(*active), after_edit]}
    assert pick_drawn_bbox(state, active) == (11.0, 45.0, 15.0, 48.0)


def test_unchanged_map_gives_no_drawn_rectangle():
    active = (27.0, 40.0, 30.0, 42.0)
    assert pick_drawn_bbox({"all_drawings": [rectangle(*active)]}, active) is None
    assert pick_drawn_bbox(None, active) is None


def test_format_bbox_in_turkish_uses_turkish_letters_and_comma():
    assert format_bbox((-109.05, 37.0, -102.04, 41.0), "tr") == "109,0°B–102,0°B, 37,0°K–41,0°K"
