"""Per-cell yearly values of the four NASA POWER measurements, for the time-travel map.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Reads the NASA POWER grid answers the app has cached (the "crime scene map" cache, by default
%TEMP%/trend_grid_cache) and never asks NASA: a region and measurement whose cache files are missing is
skipped. Every grid cell gets the app's own yearly rule (trend.stats.to_annual: complete years only,
snowfall in water years from October to September labelled by the ending year, dust and smoke from
2001). Output: data/processed/grid/<region>_<variable>_cells.csv with lat, lon, year, value.

Usage:  python scripts/build_grid_cells.py [--cache DIR] [--regions ...] [--variables ...]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trend.area import power_request_boxes  # noqa: E402
from trend.fetch import POWER_VARIABLES  # noqa: E402
from trend.regions import REGIONS  # noqa: E402
from trend.stats import to_annual  # noqa: E402
from trend.trendmap import DEFAULT_FIRST_YEAR, FIRST_YEAR, fetch_cells  # noqa: E402
from trend.variables import VARIABLES  # noqa: E402

OUT = ROOT / "data" / "processed" / "grid"
DECIMALS = {"air_temperature": 6, "precipitation": 6, "snowfall": 6, "aod": 6}  # unrounded enough that no ties are created
END_YEARS = (2026, 2025)  # the board's end year first; POWER answers for 2025 are an older cache


def cache_files(variable_key: str, bbox, end_year: int, cache_dir: Path) -> list[Path]:
    """The cache files fetch_cells would read for this rectangle (same naming as trend/trendmap.py)."""
    parameter, _ = POWER_VARIABLES[variable_key]
    start_year = FIRST_YEAR.get(variable_key, DEFAULT_FIRST_YEAR)
    return [
        cache_dir / (f"{parameter}_{start_year}_{end_year}_" + "_".join(f"{v:.2f}" for v in box) + ".json")
        for box in power_request_boxes(bbox)
    ]


def cell_years(cells: pd.DataFrame, variable_key: str) -> pd.DataFrame:
    """Yearly values per cell with the app's rule; columns lat, lon, year, value."""
    variable = VARIABLES[variable_key]
    rows = []
    for (lat, lon), group in cells.groupby(["lat", "lon"], sort=True):
        annual, _ = to_annual(group.loc[:, ["date", "value"]], variable)
        for year, value in zip(annual["year"], annual["value"]):
            rows.append((float(lat), float(lon), int(year), float(value)))
    table = pd.DataFrame(rows, columns=["lat", "lon", "year", "value"])
    table["value"] = table["value"].round(DECIMALS.get(variable_key, 3))
    return table


def build(region_key: str, variable_key: str, cache_dir: Path) -> Path | None:
    bbox = REGIONS[region_key].bbox
    for end_year in END_YEARS:
        if all(path.exists() for path in cache_files(variable_key, bbox, end_year, cache_dir)):
            break
    else:
        print(f"{region_key} {variable_key}: no cached answers, skipped", flush=True)
        return None
    cells, _ = fetch_cells(variable_key, bbox, end_year=end_year, cache_dir=cache_dir)
    table = cell_years(cells, variable_key)
    if table.duplicated(["lat", "lon", "year"]).any():
        raise RuntimeError(f"{region_key} {variable_key}: a cell-year appears twice")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{region_key}_{variable_key}_cells.csv"
    table.to_csv(path, index=False)
    n_cells = table[["lat", "lon"]].drop_duplicates().shape[0]
    years = f"{table['year'].min()}-{table['year'].max()}" if len(table) else "none"
    print(f"{region_key} {variable_key}: {n_cells} cells, years {years} (end {end_year}) -> {path.relative_to(ROOT)}",
          flush=True)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_cache = os.environ.get("TREND_GRID_CACHE") or str(Path(tempfile.gettempdir()) / "trend_grid_cache")
    parser.add_argument("--cache", default=default_cache)
    parser.add_argument("--regions", nargs="*", default=list(REGIONS))
    parser.add_argument("--variables", nargs="*", default=list(DECIMALS))
    args = parser.parse_args(argv)
    cache_dir = Path(args.cache)
    for region_key in args.regions:
        for variable_key in args.variables:
            build(region_key, variable_key, cache_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
