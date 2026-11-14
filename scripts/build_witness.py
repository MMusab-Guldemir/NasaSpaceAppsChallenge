"""Build the independent "witness" series in data/witness/ from Giovanni area averages in data/raw/.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

A witness is a second NASA record of the same quantity over the same prepared region, made by a
different instrument or method. It lets the detective check whether an independent record sees the
same trend. Input files are Giovanni "Time Series, Area-Averaged" CSVs over each region's exact box,
named data/raw/giovanni_<source>_<region>.csv. Output: data/witness/<region>_<variable>.csv with the
columns date (YYYY-MM-01), value, unit, source. Precipitation and snowfall become monthly totals in
mm of water; AOD stays a monthly mean.

Usage:  python scripts/build_witness.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trend.fetch import load_giovanni_csv  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "witness"


@dataclass(frozen=True)
class Source:
    variable: str
    unit: str
    to_monthly: str  # "per_day" (x days), "per_hour" (x 24 x days), "per_second" (x 86400 x days), "mean"
    valid: tuple[float, float]  # plausible monthly range after conversion
    source: str


SOURCES = {
    "gpcp": Source(
        "precipitation", "mm", "per_day", (0, 2000),
        "GPCP Version 3.3 monthly 0.5 deg satellite-gauge precipitation (GPCPMON v3.3), NASA GES DISC, "
        "area average via NASA Giovanni; doi:10.5067/MEASURES/GPCP/DATA306",
    ),
    "imerg": Source(
        "precipitation", "mm", "per_hour", (0, 2000),
        "GPM IMERG Final Run monthly 0.1 deg (GPM_3IMERGM v07), NASA GES DISC, area average via NASA "
        "Giovanni; doi:10.5067/GPM/IMERG/3B-MONTH/07",
    ),
    "gldassnow": Source(
        "snowfall", "mm", "per_second", (0, 1000),
        "GLDAS Noah land surface model monthly 0.25 deg V2.1 snowfall (GLDAS_NOAH025_M v2.1), NASA GES "
        "DISC, area average via NASA Giovanni; doi:10.5067/SXAVCZFAQLNO",
    ),
    "mod08aod": Source(
        "aod", "AOD", "mean", (0, 5),
        "MODIS Terra MOD08_M3 Collection 6.1 aerosol optical depth at 550 nm, Dark Target and Deep Blue "
        "combined, NASA LAADS DAAC, area average via NASA Giovanni; doi:10.5067/MODIS/MOD08_M3.061",
    ),
}


def convert(table: pd.DataFrame, how: str) -> pd.Series:
    days = table["date"].dt.days_in_month
    factor = {"per_day": days, "per_hour": 24 * days, "per_second": 86400 * days, "mean": 1}[how]
    return table["value"] * factor


def build(source_key: str, raw_path: Path) -> Path:
    spec = SOURCES[source_key]
    region = raw_path.stem.removeprefix(f"giovanni_{source_key}_")
    table = load_giovanni_csv(raw_path).dropna(subset=["value"])
    table["date"] = table["date"].dt.to_period("M").dt.to_timestamp()
    values = convert(table, spec.to_monthly)
    low, high = spec.valid
    if values.empty or values.min() < low or values.max() > high:
        raise ValueError(f"{raw_path.name}: values outside {low}-{high} {spec.unit} ({values.min()}, {values.max()})")
    out = pd.DataFrame({
        "date": table["date"].dt.strftime("%Y-%m-01"),
        "value": values.round(6),
        "unit": spec.unit,
        "source": spec.source,
    })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{region}_{spec.variable}.csv"
    if source_key == "imerg" and path.exists():
        path = OUT / f"{region}_{spec.variable}_imerg.csv"  # GPCP stays the main precipitation witness
    out.to_csv(path, index=False)
    print(f"{path.relative_to(ROOT)}: {len(out)} months, {out['date'].iloc[0]} to {out['date'].iloc[-1]}")
    return path


def main() -> int:
    built = 0
    for source_key in SOURCES:  # GPCP before IMERG, so GPCP owns <region>_precipitation.csv
        for raw_path in sorted(RAW.glob(f"giovanni_{source_key}_*.csv")):
            build(source_key, raw_path)
            built += 1
    print(f"{built} witness files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
