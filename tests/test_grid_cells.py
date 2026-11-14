"""Tests for the per-cell yearly files of the time-travel map (scripts/build_grid_cells.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import importlib.util
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trend.regions import REGIONS
from trend.stats import to_annual
from trend.variables import VARIABLES

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_grid_cells", ROOT / "scripts" / "build_grid_cells.py")
bgc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bgc)
GRID = ROOT / "data" / "processed" / "grid"
CACHE = Path(os.environ.get("TREND_GRID_CACHE") or Path(tempfile.gettempdir()) / "trend_grid_cache")


def monthly_cells(values_by_cell, start="1981-01-01", months=24):
    dates = pd.date_range(start, periods=months, freq="MS")
    rows = []
    for (lat, lon), values in values_by_cell.items():
        rows += [(lat, lon, d, v) for d, v in zip(dates, values)]
    return pd.DataFrame(rows, columns=["lat", "lon", "date", "value"])


def test_cell_years_uses_the_apps_yearly_rule():
    cells = monthly_cells({(40.0, 27.5): [10.0] * 12 + [12.0] * 12, (40.5, 27.5): [1.0] * 12 + [np.nan] + [2.0] * 11})
    table = bgc.cell_years(cells, "air_temperature")
    first = table[(table["lat"] == 40.0)]
    assert first["year"].tolist() == [1981, 1982] and first["value"].tolist() == [10.0, 12.0]
    second = table[(table["lat"] == 40.5)]
    assert second["year"].tolist() == [1981]  # 1982 misses January, so it is not a complete year


def test_snowfall_uses_water_years_labelled_by_the_ending_year():
    cells = monthly_cells({(46.0, 10.0): [1.0] * 36}, start="1980-10-01", months=36)
    table = bgc.cell_years(cells, "snowfall")
    assert table["year"].tolist() == [1981, 1982, 1983] and set(table["value"]) == {12.0}


@pytest.mark.parametrize("path", sorted(GRID.glob("*_cells.csv")) if GRID.exists() else [], ids=lambda p: p.name)
def test_every_cell_year_appears_once(path):
    table = pd.read_csv(path)
    assert not table.duplicated(["lat", "lon", "year"]).any()


@pytest.mark.parametrize("region_key", ["siberia", "sahel"])  # rectangles fetched as two boxes
def test_cells_lie_inside_the_region_and_are_not_doubled(region_key):
    path = GRID / f"{region_key}_air_temperature_cells.csv"
    if not path.exists():
        pytest.skip("grid file not built")
    table = pd.read_csv(path)
    west, south, east, north = REGIONS[region_key].bbox
    assert table["lon"].between(west - 1e-6, east + 1e-6).all() and table["lat"].between(south - 1e-6, north + 1e-6).all()
    per_cell = table.groupby(["lat", "lon"]).size()
    assert per_cell.max() == 45  # 1981-2025, once each


def test_a_cell_matches_to_annual_on_the_cached_answers():
    path = GRID / "marmara_air_temperature_cells.csv"
    files = bgc.cache_files("air_temperature", REGIONS["marmara"].bbox, 2026, CACHE)
    if not path.exists() or not all(f.exists() for f in files):
        pytest.skip("grid cache or file not available")
    cells, _ = bgc.fetch_cells("air_temperature", REGIONS["marmara"].bbox, end_year=2026, cache_dir=CACHE)
    lat, lon = cells.iloc[0][["lat", "lon"]]
    one = cells[(cells["lat"] == lat) & (cells["lon"] == lon)]
    annual, _ = to_annual(one.loc[:, ["date", "value"]], VARIABLES["air_temperature"])
    built = pd.read_csv(path)
    built = built[(built["lat"] == lat) & (built["lon"] == lon)]
    assert built["year"].tolist() == annual["year"].tolist()
    assert np.allclose(built["value"], annual["value"].round(6))
