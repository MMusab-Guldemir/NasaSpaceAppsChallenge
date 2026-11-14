"""Tests for the time travel map: yearly squares, differences from the normal, imagery and the page.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import trend.timelapse as tl
from trend.regions import REGIONS
from trend.stats import to_annual
from trend.variables import VARIABLES

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def monthly_cells(cells, years, value_of):
    """Monthly rows (lat, lon, date, value) for the given cells and years."""
    rows = [(lat, lon, pd.Timestamp(year, month, 1), value_of(lat, lon, year, month))
            for lat, lon in cells for year in years for month in range(1, 13)]
    return pd.DataFrame(rows, columns=["lat", "lon", "date", "value"])


def annual_frame(values_by_cell, years):
    rows = [(lat, lon, year, value) for (lat, lon), values in values_by_cell.items()
            for year, value in zip(years, values)]
    return pd.DataFrame(rows, columns=["lat", "lon", "year", "value"])


# --- Yearly values per cell ------------------------------------------------------------------------

def test_yearly_cells_follow_the_apps_own_yearly_rule():
    cells = [(40.0, 27.5), (40.5, 28.125)]
    monthly = monthly_cells(cells, range(1990, 1994), lambda lat, lon, y, m: lat / 10 + (y - 1990) + m / 100)
    monthly.loc[(monthly["lat"] == 40.0) & (monthly["date"] == pd.Timestamp(1992, 6, 1)), "value"] = np.nan
    annual = tl.annual_cells(monthly, "air_temperature")
    for lat, lon in cells:
        expected, _ = to_annual(monthly[(monthly["lat"] == lat) & (monthly["lon"] == lon)].loc[:, ["date", "value"]],
                                VARIABLES["air_temperature"])
        got = annual[(annual["lat"] == lat) & (annual["lon"] == lon)].reset_index(drop=True)
        assert got["year"].tolist() == expected["year"].tolist()
        assert np.allclose(got["value"], expected["value"])
    assert 1992 not in annual.loc[annual["lat"] == 40.0, "year"].tolist()  # an incomplete year is dropped


def test_snowfall_uses_the_season_year_and_aerosols_start_in_2001():
    monthly = monthly_cells([(46.0, 10.0)], range(1999, 2003), lambda *_: 5.0)
    snow = tl.annual_cells(monthly, "snowfall")
    assert snow["year"].tolist() == [2000, 2001, 2002]  # Oct-Sep seasons labelled by the year they end
    assert snow["value"].tolist() == [60.0, 60.0, 60.0]
    aod = tl.annual_cells(monthly, "aod")
    assert aod["year"].min() == 2001


# --- Differences from the normal -------------------------------------------------------------------

def test_differences_are_taken_from_each_cells_own_normal():
    years = list(range(1981, 2026))
    warm = [10.0] * 30 + [11.0] * 15  # normal 10, then one degree warmer
    cold = [-5.0] * 30 + [-5.5] * 15
    layer = tl.layer_from_annual(annual_frame({(40.0, 27.5): warm, (40.5, 27.5): cold}, years), "air_temperature")
    assert layer["baseline"] == [1981, 2010] and layer["years"] == years
    by_lat = {cell["lat"]: cell for cell in layer["cells"]}
    assert by_lat[40.0]["n"] == 10.0 and by_lat[40.0]["d"][-1] == 1.0 and by_lat[40.0]["d"][0] == 0.0
    assert by_lat[40.5]["n"] == -5.0 and by_lat[40.5]["d"][-1] == -0.5
    weights = np.cos(np.radians([40.0, 40.5]))
    assert layer["mean"][-1] == round(float((weights[0] * 1.0 - weights[1] * 0.5) / weights.sum()), 2)
    assert layer["scale"] == 1.0 and layer["mode"] == "diff"  # 95th percentile of |difference|, rounded up
    assert layer["ref"] == "the 1981–2010 normal" and layer["normalWord"] == "normal"


def test_rain_is_shown_in_percent_of_normal_except_in_deserts():
    years = list(range(1981, 2026))
    wet = tl.layer_from_annual(annual_frame({(14.0, 1.0): [400.0] * 30 + [600.0] * 15,
                                             (13.0, 1.0): [800.0] * 30 + [400.0] * 15}, years), "precipitation")
    assert wet["mode"] == "percent" and wet["scale"] is None
    by_lat = {cell["lat"]: cell for cell in wet["cells"]}
    assert by_lat[14.0]["d"][-1] == 50.0 and by_lat[13.0]["d"][-1] == -50.0  # +50 % and half the normal
    weights = np.cos(np.radians([14.0, 13.0]))
    expected = (weights[0] * 600 + weights[1] * 400) / (weights[0] * 400 + weights[1] * 800) * 100 - 100
    assert wet["mean"][-1] == round(float(expected))
    assert wet["ratio"] in tl.RATIO_STEPS
    desert = tl.layer_from_annual(annual_frame({(24.0, 39.0): [20.0] * 30 + [60.0] * 15}, years), "precipitation")
    assert desert["mode"] == "diff" and desert["cells"][0]["d"][-1] == 40.0  # millimetres where it hardly rains


def test_aerosols_speak_of_an_average_not_a_normal():
    years = list(range(2001, 2026))
    layer = tl.layer_from_annual(annual_frame({(40.0, 28.0): [0.2] * 10 + [0.15] * 15}, years), "aod", "tr")
    assert layer["baseline"] == [2001, 2010] and layer["ref"] == "2001–2010 ortalamasına"
    assert layer["normalWord"] == "ortalama" and layer["sourceChange"] == 2022


def test_a_cell_without_enough_baseline_years_gets_no_colour():
    years = list(range(1981, 2026))
    full = [1.0] * 45
    patchy = [np.nan] * 25 + [1.0] * 20  # only 5 baseline years
    layer = tl.layer_from_annual(annual_frame({(1.0, 1.0): full, (2.0, 1.0): patchy}, years).dropna(),
                                 "air_temperature")
    assert [cell["lat"] for cell in layer["cells"]] == [1.0]


def test_snow_free_cells_are_left_out_and_counted():
    years = list(range(1982, 2027))
    layer = tl.layer_from_annual(annual_frame({(46.0, 10.0): [100.0] * 45, (30.0, 31.0): [0.0] * 45}, years),
                                 "snowfall")
    assert layer["no_snow"] == 1 and len(layer["cells"]) == 1
    assert layer["baseline"] == [1982, 2010]  # the first season with data
    assert tl.layer_from_annual(annual_frame({(30.0, 31.0): [0.0] * 45}, years), "snowfall") is None


def test_ranks_and_round_scales():
    assert tl.year_ranks([1.0, None, 3.0, 2.0]) == [[3, 1], [None, None], [1, 3], [2, 2]]
    assert [tl.nice_ceiling(v) for v in (0.935, 1.86, 27.56, 273.9, 0.0455)] == [1.0, 2.0, 30.0, 300.0, 0.05]
    assert tl.nice_ceiling(0) == 0.0


# --- Prepared files and imagery ---------------------------------------------------------------------

@pytest.mark.parametrize("region", list(REGIONS))
def test_every_prepared_region_has_temperature_and_hot_day_squares(region):
    for key in ("air_temperature", "hot_days"):
        annual = tl.load_annual_cells(region, key)
        assert annual is not None and len(annual) > 0, (region, key)
        layer = tl.layer_from_annual(annual, key)
        assert layer is not None and layer["cells"], (region, key)
        assert all(len(cell["d"]) == len(layer["years"]) for cell in layer["cells"])


def test_hot_days_read_the_days_column_and_missing_files_give_none():
    hot = tl.load_annual_cells("marmara", "hot_days")
    assert list(hot.columns) == ["lat", "lon", "year", "value"]
    assert tl.load_annual_cells("nowhere", "air_temperature") is None


def test_imagery_has_a_tile_url_per_year_rule():
    images = {item["key"]: item for item in tl.imagery_list("beijing", "en")}
    assert images["true_colour"]["date"] == "10-15"  # Beijing's clear autumn
    for item in images.values():
        assert "{time}" in item["url"] and "{z}/{y}/{x}" in item["url"]
        assert item["url"].startswith("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/")
        assert item["first"] <= item["last"] and 3 <= item["maxNative"] <= 9


def test_the_map_opens_with_the_picked_case_when_it_has_squares():
    layers = [{"key": "air_temperature", "years": [1981, 2025]}, {"key": "aod", "years": [2001, 2025]}]
    assert tl.start_layer(layers, "aod") == "aod"
    assert tl.start_layer(layers, "no2") == "air_temperature"
    payload = tl.build_payload(layers, (27, 40, 30, 42), "marmara", "tr", "ndvi", (0.5, 0.625))
    assert payload["imageryStart"] == "ndvi" and payload["years"] == [1981, 2026]


def test_the_page_pins_leaflet_and_cannot_be_broken_by_text_in_the_data():
    annual = tl.load_annual_cells("marmara", "air_temperature")
    layer = tl.layer_from_annual(annual, "air_temperature", "tr")
    layer["name"] = "</script><script>alert(1)</script>"
    page = tl.render_timelapse_html(tl.build_payload([layer], (27, 40, 30, 42), "marmara", "tr", None, (0.5, 0.625)))
    assert "leaflet@1.9.4" in page and 'integrity="sha256-' in page
    assert "</script><script>alert(1)" not in page
    data = re.search(r'<script type="application/json" id="tl-data">(.*?)</script>', page, re.S).group(1)
    assert json.loads(data)["layers"][0]["name"] == layer["name"]


def test_texts_have_the_same_keys_in_both_languages():
    en, tr = tl.TIME_TEXT["en"], tl.TIME_TEXT["tr"]
    assert set(en) == set(tr)
    for key, text in en.items():
        if isinstance(text, str):
            assert set(re.findall(r"\{(\w+)\}", text)) == set(re.findall(r"\{(\w+)\}", tr[key])), key
    assert set(en["words"]) == set(tl.LAYER_KEYS) == set(tr["words"])
    for key in tl.LAYER_KEYS:
        assert set(en["words"][key]) == set(tr["words"][key]) == {"high1", "low1", "high", "low"}
    assert set(en["pct"]) == set(tr["pct"]) == set(tl.PERCENT_MODE)


# --- App -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["en", "tr"])
def test_app_shows_the_time_travel_layer(lang):
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["lang"] = lang
    at.session_state["map_layer"] = "time"
    at.run()
    assert not at.exception
    captions = " ".join(caption.value for caption in at.caption)
    assert tl.TIME_TEXT[lang]["honesty"] in captions
    assert at.query_params.get("map") in ("time", ["time"])
