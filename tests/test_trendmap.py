"""Tests for the crime scene map: grid cells, the many-cells correction, words, map layer and app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import trend.trendmap as tm
from trend.i18n import reasons, region_context
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES

APP = str(Path(__file__).resolve().parent.parent / "app.py")
BOX = (0.0, 0.0, 2.5, 2.0)


def payload(cells, parameter="T2M", years=range(1981, 2026), fill=-999.0):
    """A tiny fake POWER regional response: ``cells`` maps (lon, lat) to a function of (year, month)."""
    features = []
    for (lon, lat), value_of in cells.items():
        series = {}
        for year in years:
            for month in range(1, 14):
                series[f"{year}{month:02d}"] = value_of(year, month) if month < 13 else 999.0
        features.append({"geometry": {"coordinates": [lon, lat]},
                         "properties": {"parameter": {parameter: series}}})
    return {"header": {"fill_value": fill, "sources": ["MERRA2"]}, "features": features}


def synthetic_cells(rng, warming_cells, flat_cells, slope=0.05, noise=0.4, box=BOX):
    """Monthly temperatures: a seasonal cycle, noise and (for some cells) a steady warming."""
    cells = {}
    for lon, lat in warming_cells + flat_cells:
        trend = slope if (lon, lat) in warming_cells else 0.0
        shocks = {year: rng.normal(0, noise) for year in range(1981, 2026)}
        cells[(lon, lat)] = (lambda t_, s_: lambda y, m: 10 + 8 * np.sin(m / 12 * 2 * np.pi) + t_ * (y - 1981) + s_[y])(trend, shocks)
    return tm.cells_from_payloads([payload(cells)], "T2M", box)


def _trends(rows):
    df = pd.DataFrame(rows, columns=["lat", "lon", "slope_per_decade", "p_value"])
    df["fdr"] = df["p_value"] < 0.01
    df["direction"] = np.where(df["fdr"], np.where(df["slope_per_decade"] > 0, "up", "down"), "none")
    for col, val in (("significant", True), ("agrees", True), ("n_years", 45), ("start_year", 1981), ("end_year", 2025)):
        df[col] = val
    df["need_years"] = 80.0
    df["dot"] = df["fdr"]
    df["why"] = np.where(df["fdr"], "", np.where(df["p_value"] < 0.05, "fdr", "noise"))
    return df


MIXED = [(0.5, 0.625, 1.2, 0.001), (2.0, 2.5, -0.8, 0.002), (1.0, 1.25, 0.1, 0.6)]


def test_bh_fdr_matches_a_hand_computed_example():
    p = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205]
    # q * k / m with q = 0.10 and m = 8: 0.0125, 0.025, 0.0375, 0.05, 0.0625, 0.075, 0.0875, 0.1.
    # The largest k with p(k) <= q * k / m is k = 7 (0.074 <= 0.0875), so the seven smallest pass,
    # even though p(3) = 0.039 alone is above its own line: that is how Benjamini-Hochberg works.
    assert tm.bh_fdr(p, q=0.10).tolist() == [True] * 7 + [False]


def test_bh_fdr_handles_edge_cases():
    assert not tm.bh_fdr([]).any()
    assert tm.bh_fdr([0.0001] * 4).all()
    assert not tm.bh_fdr([0.5, 0.9, 0.7]).any()
    assert tm.bh_fdr([np.nan, 0.0001, 0.8]).tolist() == [False, True, False]


def test_bh_fdr_is_stricter_than_testing_each_cell_alone():
    p = np.random.default_rng(1).uniform(0, 1, 400)  # no real trend anywhere
    assert (p < 0.05).sum() > 5  # cell by cell, chance alone makes "significant" cells
    assert tm.bh_fdr(p).sum() <= 2


def test_payload_cells_drop_annual_values_fill_values_and_outside_cells():
    raw = payload({(0.625, 0.5): lambda y, m: -999.0 if (y, m) == (1990, 5) else 1.0,
                   (9.0, 9.0): lambda y, m: 1.0})
    cells = tm.cells_from_payloads([raw], "T2M", BOX)
    assert set(zip(cells["lon"], cells["lat"])) == {(0.625, 0.5)}
    assert len(cells) == 45 * 12 and cells["value"].isna().sum() == 1


def test_overlapping_boxes_keep_each_cell_once():
    raw = payload({(0.625, 0.5): lambda y, m: 1.0})
    assert len(tm.cells_from_payloads([raw, raw], "T2M", BOX)) == 45 * 12


def test_zero_aerosol_values_count_as_missing():
    raw = payload({(0.625, 0.5): lambda y, m: 0.0 if m == 1 else 0.2}, parameter="AOD_55")
    assert tm.cells_from_payloads([raw], "AOD_55", BOX)["value"].isna().sum() == 45


def test_cached_responses_are_reused(tmp_path, monkeypatch):
    calls = []

    def fake_request(parameter, region, start, end, timeout, pauses):
        calls.append(region.bbox)
        return payload({(0.625, 0.5): lambda y, m: 1.0})

    monkeypatch.setattr(tm, "_request_retrying", fake_request)
    first, _ = tm.fetch_cells("air_temperature", BOX, cache_dir=tmp_path)
    second, _ = tm.fetch_cells("air_temperature", BOX, cache_dir=tmp_path)
    assert len(calls) == 1 and first.equals(second)


def test_planted_warming_is_found_and_flat_cells_stay_quiet():
    rng = np.random.default_rng(7)
    warming = [(0.625, 0.5), (1.25, 0.5), (0.625, 1.0)]
    flat = [(1.875, 1.5), (2.5, 1.5), (1.875, 2.0)]
    by_cell = tm.cell_trends(synthetic_cells(rng, warming, flat), "air_temperature").set_index(["lon", "lat"])
    for cell in warming:
        assert by_cell.loc[cell, "direction"] == "up"
        assert by_cell.loc[cell, "slope_per_decade"] == pytest.approx(0.5, abs=0.15)
    assert (by_cell.loc[flat, "direction"] != "up").sum() >= 2


def test_cell_results_match_the_app_test():
    cells = synthetic_cells(np.random.default_rng(3), [(0.625, 0.5)], [])
    row = tm.cell_trends(cells, "air_temperature").iloc[0]
    annual, _ = to_annual(cells[["date", "value"]], VARIABLES["air_temperature"])
    result = analyze_trend(annual["year"], annual["value"])
    assert row["slope_per_decade"] == pytest.approx(result.slope_per_decade)
    assert row["p_value"] == pytest.approx(result.p_value)


def test_period_limits_and_short_records():
    cells = synthetic_cells(np.random.default_rng(5), [(0.625, 0.5)], [])
    trends = tm.cell_trends(cells, "air_temperature", 2000, 2020)
    assert (trends["start_year"] == 2000).all() and (trends["end_year"] == 2020).all()
    assert tm.cell_trends(cells, "air_temperature", 2018, 2025).empty  # fewer than 10 years


def test_cells_without_snow_are_left_out_and_explained():
    raw = payload({(0.625, 0.5): lambda y, m: 0.0, (1.25, 0.5): lambda y, m: 2.0 if m in (12, 1, 2) else 0.0},
                  parameter="PRECSNOLAND")
    trends = tm.cell_trends(tm.cells_from_payloads([raw], "PRECSNOLAND", BOX), "snowfall")
    assert set(zip(trends["lon"], trends["lat"])) == {(1.25, 0.5)}
    none = tm.cell_trends(tm.cells_from_payloads([payload({(0.625, 0.5): lambda y, m: 0.0}, parameter="PRECSNOLAND")],
                                                 "PRECSNOLAND", BOX), "snowfall")
    assert none.empty and "kar yağmıyor" in tm.summarize(none, "tr", "snowfall", BOX)["headline"]


def test_cell_size_and_compass():
    cells = pd.DataFrame({"lat": [0.5, 0.5, 1.0, 1.0], "lon": [0.625, 1.25, 0.625, 1.25]})
    assert tm.cell_size(cells) == pytest.approx((0.5, 0.625))
    box = (0.0, 0.0, 9.0, 9.0)
    assert [tm.compass(8.5, 8.5, box), tm.compass(0.5, 4.5, box), tm.compass(4.5, 4.5, box)] == ["ne", "s", "c"]


def test_summary_flags_opposite_directions_in_both_languages():
    trends = _trends(MIXED)
    en, tr = tm.summarize(trends, "en", "snowfall", BOX), tm.summarize(trends, "tr", "snowfall", BOX)
    assert en["both"] and (en["up"], en["down"], en["n"]) == (1, 1, 3)
    assert "opposite" in en["headline"] and "zıt" in tr["headline"]
    assert any("northeast" in d for d in en["details"]) and any("güneybatısında" in d for d in tr["details"])


def test_summary_uses_a_decimal_comma_in_turkish():
    tr = tm.summarize(_trends([(0.5, 0.625, 0.53, 0.001), (1.0, 1.25, 0.21, 0.004)]), "tr", "air_temperature", BOX)
    assert "+0,53" in " ".join(tr["details"]) and not tr["both"]


def test_reasons_follow_the_map():
    mixed = tm.map_reasons("tr", "snowfall", tm.summarize(_trends(MIXED), "tr", "snowfall", BOX), "colorado")
    assert mixed["lines"] == [tm.MAP_TEXT["tr"]["mixed"]["snowfall"]]
    up = tm.summarize(_trends([(0.5, 0.625, 0.5, 0.001)]), "en", "air_temperature", BOX)
    rising = tm.map_reasons("en", "air_temperature", up, "siberia")
    assert rising["lines"] == list(reasons("en", "air_temperature", "up"))
    assert rising["context"] == region_context("en", "siberia", "air_temperature")
    quiet = tm.map_reasons("en", "aod", tm.summarize(_trends([(0.5, 0.625, 0.1, 0.5)]), "en", "aod", BOX), None)
    assert quiet["lines"] == list(reasons("en", "aod", "none")) and quiet["context"] == ""


def test_colours_are_centred_on_zero():
    assert tm.slope_color(0.0, 2.0) == "#f4f3f0"
    assert tm.slope_color(2.0, 2.0) == "#b4441b" and tm.slope_color(-2.0, 2.0) == "#1c5cab"
    assert tm.slope_color(9.0, 2.0) == "#b4441b"  # clipped at the ends


def test_overlay_draws_a_square_per_cell_and_a_dot_per_real_trend():
    fmap = folium.Map()
    group = tm.add_overlay(fmap, _trends(MIXED), (0.5, 0.625), "tr", "snowfall")
    children = list(group._children.values())
    assert sum(isinstance(c, folium.Rectangle) for c in children) == 3
    assert sum(isinstance(c, folium.CircleMarker) for c in children) == 2
    assert "/ 10 yıl" in fmap.get_root().render()


def test_legend_spans_minus_to_plus_the_largest_rate():
    legend = tm.legend_html(_trends(MIXED), "en", "snowfall")
    assert "-1.20" in legend and "+1.20" in legend and "linear-gradient" in legend


def test_texts_have_the_same_keys_in_both_languages():
    assert set(tm.MAP_TEXT["en"]) == set(tm.MAP_TEXT["tr"])
    assert set(tm.MAP_TEXT["en"]["where"]) == set(tm.MAP_TEXT["tr"]["where"])
    assert set(tm.MAP_TEXT["en"]["mixed"]) == set(tm.MAP_TEXT["tr"]["mixed"])


def _fake_fetch(variable_key, bbox, cache_dir=None, timeout=300, end_year=2025):
    west, south, east, north = bbox
    rng = np.random.default_rng(11)
    lats = np.arange(south, north + 1e-9, 0.5)
    lons = np.arange(west, east + 1e-9, 0.625)
    cells = {}
    for i, lat in enumerate(lats):
        for lon in lons:
            slope = 0.06 if i < len(lats) / 2 else -0.06
            shocks = {year: rng.normal(0, 0.3) for year in range(1981, 2026)}
            cells[(float(lon), float(lat))] = (lambda s_, k_: lambda y, m: 50 + s_ * (y - 1981) + k_[y])(slope, shocks)
    return tm.cells_from_payloads([payload(cells)], "T2M", bbox), "MERRA2"


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_app_shows_the_crime_scene_layer_with_its_summary(monkeypatch, lang):
    monkeypatch.setattr(tm, "fetch_cells", _fake_fetch)
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["lang"] = lang
    at.session_state["map_layer"] = "scene"
    at.run()
    assert not at.exception
    headers = " ".join(h.value for h in at.subheader)
    assert tm.MAP_TEXT[lang]["both"].split("!")[0] in headers
    assert at.query_params.get("map") in ("scene", ["scene"])


def test_app_without_the_layer_has_no_cell_summary(monkeypatch):
    monkeypatch.setattr(tm, "fetch_cells", _fake_fetch)
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception
    assert at.session_state["map_layer"] == "area"
    assert not any("opposite" in h.value for h in at.subheader)


def test_cells_without_a_dot_say_why():
    trends = _trends([(0.5, 0.625, 1.2, 0.001), (1.0, 1.25, 0.4, 0.03), (1.5, 1.875, 0.1, 0.6), (2.0, 2.5, 0.05, 0.8)])
    lines = tm.no_dot_reasons(trends, "tr")
    assert lines[0].startswith("2 kare") and "kabaca 80 yıllık" in lines[0]
    assert any("tek başına anlamlı" in line and "4 kare" in line for line in lines)
    tips = [tm.cell_tip_reason(row, 4, "en") for row in trends.itertuples(index=False)]
    assert tips[0] == "" and "chance among 4 cells" in tips[1] and "80 years" in tips[2]


def test_real_cells_get_a_reason_and_years_needed():
    rng = np.random.default_rng(9)
    trends = tm.cell_trends(synthetic_cells(rng, [(0.625, 0.5)], [(1.875, 1.5), (2.5, 1.5)]), "air_temperature")
    flat = trends[trends["direction"] == "none"]
    assert set(flat["why"]) <= {"noise", "fdr", "short"} and (trends.loc[trends["fdr"], "why"] == "").all()
    assert (flat["need_years"] > trends.loc[trends["fdr"], "need_years"].max()).all()



def test_a_dot_needs_the_5_percent_line_and_the_second_test():
    rows = pd.DataFrame({
        "lat": [0.5] * 6, "lon": [0.625 * k for k in range(6)], "slope_per_decade": [1.0] * 6,
        "p_value": [0.001, 0.002, 0.003, 0.004, 0.07, 0.003], "agrees": [True, True, True, True, True, False],
        "n_years": [45] * 6, "need_years": [20.0] * 6,
    })
    marked = tm.mark_dots(rows)
    assert marked["fdr"].tolist()[4]  # with q = 0.10 the many-cells correction lets p = 0.07 through...
    assert not marked["dot"].tolist()[4]  # ...but it is above the app's own 5% line, so no dot
    assert marked["why"].tolist()[5] == "disputed" and not marked["dot"].tolist()[5]
    assert marked["dot"].tolist()[:4] == [True] * 4


def test_a_cell_without_any_change_is_called_flat():
    rows = pd.DataFrame({"lat": [0.5, 1.0], "lon": [0.625, 0.625], "slope_per_decade": [0.0, 0.2],
                         "p_value": [1.0, 0.5], "agrees": [True, True], "n_years": [45, 45],
                         "need_years": [float("nan"), 400.0]})
    marked = tm.mark_dots(rows)
    assert marked["why"].tolist() == ["flat", "noise"]
    lines = tm.no_dot_reasons(marked.assign(start_year=1981, end_year=2025), "en")
    assert any("no change at all" in line for line in lines) and any("too small" in line for line in lines)


def test_dot_wording_admits_some_dots_may_be_chance():
    assert "1 dot in 10 may still be chance" in tm.MAP_TEXT["en"]["dots"]
    assert "10 noktadan biri" in tm.MAP_TEXT["tr"]["dots"]
    assert "real trend" not in tm.MAP_TEXT["en"]["hover_dot"]


def test_a_broken_cache_file_is_fetched_again(tmp_path, monkeypatch):
    calls = []

    def fake_request(parameter, region, start, end, timeout, pauses):
        calls.append(region.bbox)
        return payload({(0.625, 0.5): lambda y, m: 1.0})

    monkeypatch.setattr(tm, "_request_retrying", fake_request)
    tm.fetch_cells("air_temperature", BOX, cache_dir=tmp_path)
    for cached in tmp_path.glob("*.json"):
        cached.write_text("{not json", encoding="utf-8")
    cells, _ = tm.fetch_cells("air_temperature", BOX, cache_dir=tmp_path)
    assert len(calls) == 2 and len(cells) > 0
