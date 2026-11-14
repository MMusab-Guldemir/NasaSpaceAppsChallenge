"""Fetch NASA data for a region and cache it as small CSV files in data/processed.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Usage, from the project root:
    python scripts/prefetch.py --region colorado
    python scripts/prefetch.py --region colorado --variables air_temperature no2

Air temperature and snowfall come straight from the NASA POWER API. NO2 is built from Giovanni
area-averaged CSV downloads placed in data/raw (giovanni_no2_*.csv).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trend.fetch import (  # noqa: E402
    POWER_VARIABLES,
    RAW_DIR,
    build_no2_from_giovanni,
    fetch_power_variable,
    save_processed,
)
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
            files = sorted(RAW_DIR.glob(f"giovanni_no2_*.csv"))
            if not files:
                print("skip no2: no giovanni_no2_*.csv files in data/raw")
                continue
            monthly = build_no2_from_giovanni(files, variable.min_valid_days or 1)
            names = ", ".join(f.name for f in files)
            source = f"{variable.product}; {variable.provider}; files: {names}"
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
