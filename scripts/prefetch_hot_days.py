"""Download NASA POWER daily maximum temperature for the prepared regions and build the hot-day files.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

One request per region, request box and year (POWER allows at most 366 days per daily request). Raw
answers are cached in data/raw/power_daily/ (git-ignored), so an interrupted run resumes where it
stopped. Output: data/processed/<region>_hot_days.csv with date, value, n_cells, unit, source.

Usage:  python scripts/prefetch_hot_days.py [--regions marmara beijing ...] [--start 1981] [--end 2025]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trend.area import power_request_boxes  # noqa: E402
from trend.hotdays import THRESHOLD_C, monthly_hot_days, request_daily_year  # noqa: E402
from trend.regions import REGIONS  # noqa: E402

RAW = ROOT / "data" / "raw" / "power_daily"
OUT = ROOT / "data" / "processed"
SOURCE = (
    f"NASA POWER daily T2M_MAX (MERRA-2 based); days above {THRESHOLD_C:.0f} °C counted per grid cell, "
    "cos-latitude weighted mean over the region's cells; NASA Langley Research Center POWER Project"
)


def year_payloads(region_key: str, year: int) -> list[dict]:
    payloads = []
    for index, box in enumerate(power_request_boxes(REGIONS[region_key].bbox)):
        path = RAW / f"{region_key}_{index}_{year}.json"
        if path.exists():
            payloads.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        payload = request_daily_year(box, year)
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        payloads.append(payload)
    return payloads


def build(region_key: str, start: int, end: int, workers: int = 4) -> Path:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        per_year = list(pool.map(lambda year: year_payloads(region_key, year), range(start, end + 1)))
    payloads = [payload for year in per_year for payload in year]
    monthly = monthly_hot_days(payloads, REGIONS[region_key].bbox)
    cells = monthly.attrs.get("cells")
    if cells is not None and len(cells):  # per-cell yearly counts, for the time-travel map
        grid_dir = OUT / "grid"
        grid_dir.mkdir(parents=True, exist_ok=True)
        cells.to_csv(grid_dir / f"{region_key}_hot_days_cells.csv", index=False, float_format="%.4f")
    monthly["date"] = monthly["date"].dt.strftime("%Y-%m-01")
    monthly["unit"] = "days"
    monthly["source"] = SOURCE
    path = OUT / f"{region_key}_hot_days.csv"
    monthly.to_csv(path, index=False)
    valid = monthly["value"].notna().sum()
    print(f"{region_key}: {len(monthly)} months ({valid} complete) -> {path.relative_to(ROOT)}", flush=True)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regions", nargs="*", default=list(REGIONS))
    parser.add_argument("--start", type=int, default=1981)
    parser.add_argument("--end", type=int, default=2025)
    args = parser.parse_args(argv)
    failed = []
    for region_key in args.regions:
        try:
            build(region_key, args.start, args.end)
        except Exception as error:  # keep going with the other regions; rerun resumes from the cache
            print(f"{region_key}: FAILED {error!r}", flush=True)
            failed.append(region_key)
    print("failed:", failed, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
