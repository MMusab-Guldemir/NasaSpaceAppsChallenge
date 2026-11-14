"""Fetch NASA data for a region and cache it as small CSV files in data/processed.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Usage, from the project root:
    python scripts/prefetch.py --region colorado
    python scripts/prefetch.py --region colorado --variables air_temperature no2

Air temperature and snowfall come straight from the NASA POWER API. NO2 is built from Giovanni
area-averaged CSV downloads placed in data/raw (giovanni_no2_<region>_*.csv), and NDVI from the
AppEEARS area statistics CSV (appeears_ndvi_<region>*.csv).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trend.fetch import (  # noqa: E402
    GIOVANNI_MONTHLY,
    POWER_VARIABLES,
    build_monthly_from_giovanni,
    RAW_DIR,
    build_no2_from_giovanni,
    daily_to_monthly_mean,
    fetch_power_variable,
    load_giovanni_csv,
    save_processed,
)
import pandas as pd  # noqa: E402
from trend.appeears import load_appeears_statistics, load_ndvi_statistics  # noqa: E402
from trend.regions import get_region  # noqa: E402
from trend.variables import VARIABLES, get_variable  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cache NASA monthly series for a region.")
    parser.add_argument("--region", default="colorado")
    parser.add_argument("--variables", nargs="+", default=list(VARIABLES))
    parser.add_argument("--start", type=int, default=1981)
    parser.add_argument("--end", type=int, default=2026)
    args = parser.parse_args(argv)

    region = get_region(args.region)
    for key in args.variables:
        variable = get_variable(key)
        if key in POWER_VARIABLES:
            monthly, power_sources = fetch_power_variable(variable, region, args.start, args.end)
            source = f"{variable.product}; {variable.provider}; POWER sources: {power_sources}"
        elif key == "no2":
            files = sorted(RAW_DIR.glob(f"giovanni_no2_{region.key}_*.csv"))
            if not files:
                print(f"skip no2: no giovanni_no2_{region.key}_*.csv files in data/raw")
                continue
            monthly = build_no2_from_giovanni(files, variable.min_valid_days or 1)
            names = ", ".join(f.name for f in files)
            source = f"{variable.product}; {variable.provider}; files: {names}"
        elif key == "ndvi":
            files = sorted(RAW_DIR.glob(f"appeears_ndvi_{region.key}*.csv"))
            if not files:
                print(f"skip ndvi: no appeears_ndvi_{region.key}*.csv file in data/raw")
                continue
            monthly = load_ndvi_statistics(files[0])
            valid = monthly["value"].dropna()
            if not valid.between(-0.2, 1.0).all():
                raise ValueError("NDVI area means outside -0.2..1: check scale factors.")
            source = f"{variable.product}; {variable.provider}; file: {files[0].name}"
        elif key == "groundwater":
            files = sorted(RAW_DIR.glob(f"giovanni_groundwater_{region.key}_*.csv"))
            if not files:
                print(f"skip groundwater: no giovanni_groundwater_{region.key}_*.csv files in data/raw")
                continue
            daily = pd.concat([load_giovanni_csv(f) for f in files], ignore_index=True)
            daily = daily.sort_values("date").drop_duplicates(subset="date", keep="first")
            monthly = daily_to_monthly_mean(daily, variable.min_valid_days or 25)
            source = f"{variable.product}; {variable.provider}; files: {', '.join(f.name for f in files)}"
        elif key in GIOVANNI_MONTHLY:
            files = sorted(RAW_DIR.glob(f"giovanni_{key}_{region.key}.csv"))
            if not files:
                print(f"skip {key}: no giovanni_{key}_{region.key}.csv file in data/raw")
                continue
            monthly = build_monthly_from_giovanni(files, GIOVANNI_MONTHLY[key])
            source = f"{variable.product}; {variable.provider}; file: {files[0].name}"
        elif key == "tree_cover":
            files = sorted(RAW_DIR.glob(f"appeears_treecover_{region.key}*.csv"))
            if not files:
                print(f"skip tree_cover: no appeears_treecover_{region.key}*.csv file in data/raw")
                continue
            monthly = load_appeears_statistics(files[0], "Tree_Cover")
            valid = monthly["value"].dropna()
            if not valid.between(0, 100).all():
                raise ValueError("Tree cover area means outside 0..100 %: check fill values.")
            source = f"{variable.product}; {variable.provider}; file: {files[0].name}"
        else:
            print(f"skip {key}: no loader yet")
            continue
        path = save_processed(monthly, region, variable, source)
        valid = monthly.dropna(subset=["value"])
        first, last = valid["date"].min(), valid["date"].max()
        print(
            f"{key}: {len(valid)} valid months of {len(monthly)}, {first:%Y-%m} to {last:%Y-%m} "
            f"-> {path.relative_to(path.parents[2])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
