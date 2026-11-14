"""Fetch NASA data for a region and cache it as small CSV files in data/processed.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Usage, from the project root:
    python scripts/prefetch.py --region colorado
    python scripts/prefetch.py --region colorado --variables air_temperature --start 1981 --end 2026
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trend.fetch import POWER_VARIABLES, fetch_power_variable, save_processed  # noqa: E402
from trend.regions import get_region  # noqa: E402
from trend.variables import get_variable  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cache NASA monthly series for a region.")
    parser.add_argument("--region", default="colorado")
    parser.add_argument("--variables", nargs="+", default=list(POWER_VARIABLES))
    parser.add_argument("--start", type=int, default=1981)
    parser.add_argument("--end", type=int, default=2026)
    args = parser.parse_args(argv)

    region = get_region(args.region)
    for key in args.variables:
        variable = get_variable(key)
        if key not in POWER_VARIABLES:
            print(f"skip {key}: not served by POWER (use the Giovanni or AppEEARS loader)")
            continue
        monthly, power_sources = fetch_power_variable(variable, region, args.start, args.end)
        source = f"{variable.product}; {variable.provider}; POWER sources: {power_sources}"
        print(f"{key}: POWER reports sources: {power_sources}")
        path = save_processed(monthly, region, variable, source)
        first, last = monthly["date"].min(), monthly["date"].max()
        print(
            f"{key}: {len(monthly)} months, {first:%Y-%m} to {last:%Y-%m}, "
            f"{int(monthly['n_cells'].median())} grid cells -> {path.relative_to(path.parents[2])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
