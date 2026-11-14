"""How often is the detective right? A reproducible accuracy check with the app's own statistics.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Real NASA records have no answer key, so the detective is tested on simulated yearly series whose
answer is known:

* False-alarm rate: series with NO trend (red noise, AR(1) with persistence phi). The share that
  still gets the "Confirmed" stamp (headline test significant and the second witness agrees).
* Detection rate: series WITH a real trend of one standard deviation of the year-to-year noise per
  decade. The share stamped "Confirmed" in the right direction.

Usage:  python scripts/accuracy_report.py [--runs 1000]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trend.stats import analyze_trend  # noqa: E402


def red_noise(rng: np.random.Generator, phi: float, n: int) -> np.ndarray:
    """AR(1) noise with unit standard deviation (after a burn-in of 50 values)."""
    e = rng.normal(size=n + 50)
    x = np.zeros(n + 50)
    for t in range(1, n + 50):
        x[t] = phi * x[t - 1] + e[t]
    return x[50:] * np.sqrt(1 - phi**2)


def confirmed_share(n: int, phi: float, slope_per_year: float, runs: int, seed: int) -> float:
    """Percent of simulated series stamped Confirmed (in the direction of the true slope)."""
    rng = np.random.default_rng(seed)
    years = np.arange(2026 - n, 2026)
    hits = 0
    for _ in range(runs):
        values = red_noise(rng, phi, n) + slope_per_year * (years - years[0])
        result = analyze_trend(years, values)
        if result.significant and result.agrees:
            if slope_per_year == 0 or np.sign(result.slope_per_year) == np.sign(slope_per_year):
                hits += 1
    return 100 * hits / runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=1000, help="simulated series per table cell")
    args = parser.parse_args(argv)

    lengths = (10, 15, 25, 45)
    print(f"False alarms: % of trendless series stamped Confirmed ({args.runs} runs per cell)\n")
    print("| persistence | " + " | ".join(f"{n} years" for n in lengths) + " |")
    print("|---|" + "---|" * len(lengths))
    for phi in (0.0, 0.5, 0.9):
        cells = [confirmed_share(n, phi, 0.0, args.runs, seed=1000 + n + int(phi * 100)) for n in lengths]
        print(f"| {phi} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")

    lengths = (10, 15, 20, 25, 35, 45)
    print(f"\nDetection: % of series with a real trend of 1 SD per decade stamped Confirmed "
          f"({args.runs} runs per cell)\n")
    print("| persistence | " + " | ".join(f"{n} years" for n in lengths) + " |")
    print("|---|" + "---|" * len(lengths))
    for phi in (0.0, 0.5):
        cells = [confirmed_share(n, phi, 0.1, args.runs, seed=2000 + n + int(phi * 100)) for n in lengths]
        print(f"| {phi} | " + " | ".join(f"{c:.1f}" for c in cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
