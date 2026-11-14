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
    power_request_boxes,
)


def test_valid_rectangle_is_kept():
    assert normalize_bbox(27, 40, 30, 42) == (27.0, 40.0, 30.0, 42.0)


def test_small_rectangles_are_kept_as_they_are():
    assert normalize_bbox(28.5, 40.8, 29.5, 41.3) == (28.5, 40.8, 29.5, 41.3)


def test_tiny_rectangle_gets_the_smallest_size():
    assert normalize_bbox(29.0, 41.0, 29.001, 41.001) == (29.0, 41.0, 29.01, 41.01)


def test_tiny_rectangle_at_the_edge_of_the_globe():
    west, south, east, north = normalize_bbox(179.999, 89.999, 180.0, 90.0)
    assert east <= 180 and north <= 90
    assert east - west >= 0.01 - 1e-9 and north - south >= 0.01 - 1e-9  # floats: 180 - 179.99


def test_large_rectangles_up_to_40_degrees_are_allowed():
    assert normalize_bbox(-20, 30, 20, 70) == (-20.0, 30.0, 20.0, 70.0)


@pytest.mark.parametrize(
    "box, code",
    [
        ((30, 40, 27, 42), "order"),
        ((0, 0, 45, 10), "too_big"),
        ((0, 0, 10, 41), "too_big"),
        ((0, 0, 0, 95), "range"),
    ],
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

    def fake_fetch(variable, bbox, start_year, end_year, timeout=300, **kwargs):
        assert timeout != 300  # the app uses a short timeout for live requests
        dates = pd.date_range("1981-01-01", "2025-12-01", freq="MS")
        rng = np.random.default_rng(0)
        values = 10 + 0.03 * (dates.year - 1981) + rng.normal(0, 0.5, dates.size)
        return pd.DataFrame({"date": dates, "value": values, "n_cells": 25}), "MERRA2"

    monkeypatch.setattr(trend.fetch, "fetch_power_area", fake_fetch)
    app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app, default_timeout=60)
    at.session_state["area_mode"] = "custom"
    at.session_state["custom_bbox"] = (27.0, 40.0, 30.0, 42.0)
    at.run()
    assert not at.exception
    assert at.session_state["case"] in ("air_temperature", "snowfall")
    assert any("Custom area" in h.value for h in at.header)


def test_format_bbox_uses_compass_letters():
    assert format_bbox((-109.05, 37.0, -102.04, 41.0)) == "109.05°W–102.04°W, 37°N–41°N"
    assert format_bbox((28.95, 41.0, 29.0, 41.05)) == "28.95°E–29°E, 41°N–41.05°N"


def _covers(boxes, bbox, samples=20):
    west, south, east, north = bbox
    for i in range(samples + 1):
        for j in range(samples + 1):
            lon = west + (east - west) * i / samples
            lat = south + (north - south) * j / samples
            eps = 1e-9  # sample points carry float noise
            if not any(w - eps <= lon <= e + eps and s - eps <= lat <= n + eps for w, s, e, n in boxes):
                return False
    return True


@pytest.mark.parametrize(
    "box",
    [
        (28.9, 40.95, 29.1, 41.1),
        (27, 40, 30, 42),
        (10, 7.11, 12, 9.11),  # float difference 1.9999999999999991, rejected by NASA POWER
        (10, 55.73, 12, 65.73),  # float difference 10.000000000000007, rejected by NASA POWER
        (179.0, -90.0, 180.0, -89.5),
        (20, 30, 45, 40),
        (-180, -90, -140, -50),
        (-20, 30, 20, 70),
    ],
)
def test_power_request_boxes_meet_power_limits_and_cover_the_rectangle(box):
    bbox = normalize_bbox(*box)
    boxes = power_request_boxes(bbox)
    for w, s, e, n in boxes:
        assert 2 <= e - w <= 10 and 2 <= n - s <= 10  # plain floats, as NASA POWER checks them
        assert -180 <= w < e <= 180 and -90 <= s < n <= 90
    assert _covers(boxes, bbox)


def test_random_rectangles_get_valid_power_boxes():
    rng = random.Random(7)
    for _ in range(1500):
        width, height = rng.uniform(0.01, 40), rng.uniform(0.01, 40)
        west, south = rng.uniform(-180, 180 - width), rng.uniform(-90, 90 - height)
        bbox = normalize_bbox(west, south, min(west + width, 180.0), min(south + height, 90.0))
        boxes = power_request_boxes(bbox)
        assert all(2 <= e - w <= 10 and 2 <= n - s <= 10 for w, s, e, n in boxes)
        assert _covers(boxes, bbox, samples=6)


def test_large_rectangle_is_split_into_pieces():
    assert len(power_request_boxes((20.0, 30.0, 45.0, 40.0))) == 6  # 3 x 2 pieces
    assert len(power_request_boxes((27.0, 40.0, 30.0, 42.0))) == 1


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
    assert format_bbox((-109.05, 37.0, -102.04, 41.0), "tr") == "109,05°B–102,04°B, 37°K–41°K"
