"""'Not a straight line' note: a steady one-way change that the cautious verdict still calls chance.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The headline test fits a straight line and, when the leftovers (residuals) of neighbouring years
resemble each other, counts fewer independent years (trend/stats.py). A change that is steady but
curved, such as NO2 in Los Angeles falling fast and then slowly, leaves leftovers that rise and fall in
long waves. The persistence rule reads them as persistence, counts only a few independent years, and
the verdict says "No evidence", although the plain Mann-Kendall test, which neither corrects for
persistence nor assumes a straight line, sees a clear one-way movement. This module spots that
situation so the app can explain it. It changes no verdict.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pymannkendall as mk
from scipy import stats

from trend.stats import DEFAULT_ALPHA, TrendResult

NEFF_LIMIT = 6.0  # fewer independent years than this: the persistence rule removed most of the evidence
STRONG_MK_P = 0.01  # plain Mann-Kendall p-value of a clear one-way movement
MIN_POINTS = 6  # the curvature test needs at least this many years
EXACT_FIT = 1e-12  # leftovers this small (relative to the spread of the values) count as none at all

LINE_TEXT = {
    "en": {
        "note": (
            "The values move in one direction almost every year (plain Mann-Kendall, {p}), but not "
            "along a straight line. A straight line fits poorly, the leftover pattern looks like "
            "persistence, and our cautious rule then counts only about {n_eff} independent years. Try a "
            "shorter period where the change is closer to a line."
        ),
    },
    "tr": {
        "note": (
            "Değerler neredeyse her yıl aynı yöne gidiyor (düz Mann-Kendall, {p}), ama düz bir çizgi "
            "boyunca değil. Düz çizgi iyi oturmuyor, geriye kalan desen kalıcılık gibi görünüyor ve "
            "temkinli kuralımız yalnızca yaklaşık {n_eff} bağımsız yıl sayıyor. Değişimin çizgiye daha "
            "yakın olduğu daha kısa bir dönem dene."
        ),
    },
}


def line_text(lang: str, p_text: str, n_eff_text: str) -> str:
    """The note, with the plain Mann-Kendall p-value phrase and the number of independent years."""
    return LINE_TEXT.get(lang, LINE_TEXT["en"])["note"].format(p=p_text, n_eff=n_eff_text)


@dataclass(frozen=True)
class LineCheck:
    """Whether a "No evidence" verdict hides a steady change that is not a straight line."""

    curved: bool  # the squared-year term of a quadratic fit is significant
    plain_mk_p: float  # Mann-Kendall p-value without the persistence correction
    show: bool  # whether the app should show the note


def _finite_sorted(years, values) -> tuple[np.ndarray, np.ndarray]:
    """Usable years in time order: the same cleaning as ``analyze_trend``."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.shape != y.shape:
        raise ValueError("years and values must have the same length.")
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    order = np.argsort(x, kind="stable")
    return x[order], y[order]


def curvature_p_value(years, values) -> float:
    """Two-sided p-value of the squared-year term in an OLS fit on centred year and centred year squared.

    Uses ``numpy.linalg.lstsq`` and a t-test with n - 3 degrees of freedom. Returns 1.0 when there are
    fewer than ``MIN_POINTS`` years or fewer than 3 distinct years, or when the values are constant.
    """
    x, y = _finite_sorted(years, values)
    n = x.size
    if n < MIN_POINTS or np.ptp(y) == 0:
        return 1.0
    centred = x - x.mean()
    design = np.column_stack([np.ones(n), centred, centred * centred])
    coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if rank < 3:
        return 1.0
    residuals = y - design @ coefficients
    rss = float(residuals @ residuals)
    spread = float(np.sum((y - y.mean()) ** 2))
    if rss <= EXACT_FIT * spread:
        # No leftovers at all: curved, unless a straight line also fits exactly.
        line = np.polyfit(centred, y, 1)
        line_rss = float(np.sum((y - np.polyval(line, centred)) ** 2))
        return 1.0 if line_rss <= EXACT_FIT * spread else 0.0
    df = n - 3
    covariance = rss / df * np.linalg.inv(design.T @ design)
    t_value = coefficients[2] / math.sqrt(covariance[2, 2])
    return float(2 * stats.t.sf(abs(t_value), df=df))


def line_check(years, values, result: TrendResult, alpha: float = DEFAULT_ALPHA) -> LineCheck:
    """Decide whether to show the "Not a straight line" note next to a verdict.

    The note is shown when the headline test is not significant, the persistence rule leaves fewer than
    ``NEFF_LIMIT`` independent years, and the plain Mann-Kendall test confirms the one-way movement the
    note describes: clearly (p < ``STRONG_MK_P``), or at ``alpha`` when the series is also curved. A
    curved series without a one-way movement (a dip or a late jump) gets no note, because the note's
    first sentence would not be true for it.
    """
    x, y = _finite_sorted(years, values)
    plain_mk_p = float(mk.original_test(y).p) if y.size >= 3 else 1.0
    curved = curvature_p_value(x, y) < alpha
    one_way = plain_mk_p < STRONG_MK_P or (curved and plain_mk_p < alpha)
    show = (not result.significant) and result.n_effective < NEFF_LIMIT and one_way
    return LineCheck(curved=bool(curved), plain_mk_p=plain_mk_p, show=bool(show))
