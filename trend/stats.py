"""Trend statistics: annual aggregation, the headline OLS test and a Mann-Kendall robustness check.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Method
------
1. Monthly values are aggregated to one value per year (``to_annual``). A year is kept only if it
   is complete for its aggregation rule, which removes the seasonal cycle and reduces
   autocorrelation.
2. Headline test: ordinary least squares (OLS) linear trend with the 95% confidence interval of the
   slope and a two-sided t-test of "slope = 0". When the residuals are positively autocorrelated
   (lag-1 correlation r1 > 0), the standard error and degrees of freedom use the effective sample
   size n_eff = n (1 - r1) / (1 + r1) (Santer et al., 2000, J. Geophys. Res. 105, 7337-7356),
   so persistent year-to-year swings produce less overconfident results (for short records the
   correction is only partial).
3. Robustness check: the Mann-Kendall test with Sen's slope. It follows the same persistence rule
   as the headline test: when r1 > 0, the variance of the Mann-Kendall statistic is inflated by
   n / n_eff (its z-score is scaled by sqrt(n_eff / n)), an effective-sample-size correction in the
   spirit of Yue and Wang (2004, Water Resources Management 18, 201-218). The app reports whether
   this check agrees with the headline result.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats

from trend.variables import Variable

MIN_YEARS = 10
RECOMMENDED_YEARS = 20
DEFAULT_ALPHA = 0.05
MK_PLAIN = "Mann-Kendall"
MK_ADJUSTED = "persistence-adjusted Mann-Kendall"


def to_annual(monthly: pd.DataFrame, variable: Variable) -> tuple[pd.DataFrame, list[int]]:
    """Aggregate a monthly series to one value per year, following the variable's rules.

    ``monthly`` needs the columns ``date`` and ``value``. Duplicate dates are averaged. Water years
    (``year_starts_month`` other than 1) are labelled by the calendar year in which they end.

    Returns ``(annual, incomplete)``: a DataFrame with ``year``, ``value`` and ``n_months`` for
    complete years only, and the sorted labels of the years dropped for missing months.
    """
    df = monthly.loc[:, ["date", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    df = df.groupby("date", as_index=False)["value"].mean()  # one row per month
    df["month"] = df["date"].dt.month
    df = df[df["month"].isin(variable.season_months)].copy()

    year = df["date"].dt.year
    if variable.year_starts_month != 1:
        year = year + (df["month"] >= variable.year_starts_month).astype(int)
    df["year"] = year.astype(int)

    labels_seen = set(df["year"].tolist())
    valid = df.dropna(subset=["value"])
    grouped = valid.groupby("year")["value"]
    values = grouped.sum() if variable.aggregation == "sum" else grouped.mean()
    counts = grouped.count()

    annual = pd.DataFrame(
        {
            "year": counts.index.astype(int),
            "value": values.reindex(counts.index).to_numpy(dtype=float),
            "n_months": counts.to_numpy(dtype=int),
        }
    )
    annual = annual[annual["n_months"] == len(variable.season_months)].reset_index(drop=True)
    incomplete = sorted(labels_seen - set(annual["year"].tolist()))
    return annual, incomplete


@dataclass(frozen=True)
class TrendResult:
    """Outcome of the trend analysis of one annual series."""

    n_years: int
    n_effective: float
    start_year: int
    end_year: int
    alpha: float
    slope_per_year: float
    intercept: float
    ci_low_per_year: float
    ci_high_per_year: float
    p_value: float
    significant: bool
    total_change: float
    lag1_autocorrelation: float
    autocorrelated: bool
    mk_method: str
    mk_trend: str  # "increasing", "decreasing" or "no trend"
    mk_p_value: float
    sen_slope_per_year: float
    agrees: bool
    warning: str | None

    @property
    def slope_per_decade(self) -> float:
        return self.slope_per_year * 10

    @property
    def ci_per_decade(self) -> tuple[float, float]:
        return (self.ci_low_per_year * 10, self.ci_high_per_year * 10)

    @property
    def sen_slope_per_decade(self) -> float:
        return self.sen_slope_per_year * 10

    @property
    def direction(self) -> str:
        """Direction of the fitted line: "increasing", "decreasing" or "flat"."""
        if self.slope_per_year > 0:
            return "increasing"
        if self.slope_per_year < 0:
            return "decreasing"
        return "flat"


def _clean_xy(years, values) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.shape != y.shape:
        raise ValueError("years and values must have the same length.")
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    order = np.argsort(x, kind="stable")
    return x[order], y[order]


def _lag1_autocorrelation(residuals: np.ndarray) -> float:
    centered = residuals - residuals.mean()
    denominator = float(np.sum(centered * centered))
    if denominator == 0:
        return 0.0
    return float(np.sum(centered[:-1] * centered[1:]) / denominator)


def _effective_dof(residuals: np.ndarray) -> tuple[float, float, float]:
    """Return (r1, n_eff, df) for the OLS slope, adjusting only for positive autocorrelation."""
    n = residuals.size
    r1 = _lag1_autocorrelation(residuals)
    n_eff = n * (1 - r1) / (1 + r1) if r1 > 0 else float(n)
    df = max(n_eff - 2.0, 1.0)
    return r1, float(n_eff), df


def _constant_series_result(x: np.ndarray, y: np.ndarray, alpha: float, warning: str | None):
    return TrendResult(
        n_years=int(x.size), n_effective=float(x.size), start_year=int(x[0]), end_year=int(x[-1]),
        alpha=alpha, slope_per_year=0.0, intercept=float(y[0]), ci_low_per_year=0.0,
        ci_high_per_year=0.0, p_value=1.0, significant=False, total_change=0.0,
        lag1_autocorrelation=0.0, autocorrelated=False, mk_method=MK_PLAIN,
        mk_trend="no trend", mk_p_value=1.0, sen_slope_per_year=0.0, agrees=True,
        warning=warning,
    )


def analyze_trend(years, values, alpha: float = DEFAULT_ALPHA) -> TrendResult:
    """Run the headline OLS trend test and the Mann-Kendall robustness check.

    Raises ``ValueError`` when fewer than ``MIN_YEARS`` distinct usable years are given.
    """
    x, y = _clean_xy(years, values)
    n = int(x.size)
    if np.unique(x).size < MIN_YEARS:
        raise ValueError(
            f"At least {MIN_YEARS} complete years are needed for a trend test; "
            f"this selection has {np.unique(x).size}."
        )
    warning = None
    if n < RECOMMENDED_YEARS:
        warning = (
            f"Only {n} years of data. Trend tests are less reliable with fewer than "
            f"{RECOMMENDED_YEARS} years."
        )
    if np.ptp(y) == 0:
        return _constant_series_result(x, y, alpha, warning)

    fit = stats.linregress(x, y)
    residuals = y - (fit.intercept + fit.slope * x)
    r1, n_eff, df = _effective_dof(residuals)
    # Widen the OLS standard error when positive autocorrelation reduces the information content.
    stderr = fit.stderr * np.sqrt((n - 2) / df)
    t_critical = stats.t.ppf(1 - alpha / 2, df=df)
    ci_low = fit.slope - t_critical * stderr
    ci_high = fit.slope + t_critical * stderr
    p_value = float(2 * stats.t.sf(abs(fit.slope / stderr), df=df)) if stderr > 0 else 0.0

    autocorrelated = r1 > stats.norm.ppf(1 - alpha / 2) / np.sqrt(n)
    # Second witness: the same persistence rule as the headline test, so that both tests count
    # persistent years the same way (variance inflated by n / n_eff whenever r1 > 0).
    original = mk.original_test(y, alpha=alpha)
    if r1 > 0:
        mk_z = float(original.z) * np.sqrt(n_eff / n)
        mk_p = float(2 * stats.norm.sf(abs(mk_z)))
        mk_trend = ("increasing" if mk_z > 0 else "decreasing") if mk_p < alpha else "no trend"
        mk_method = MK_ADJUSTED
    else:
        mk_p, mk_trend, mk_method = float(original.p), str(original.trend), MK_PLAIN
    # Sen's slope against the actual years, so gaps from dropped years are handled correctly.
    sen_slope = float(stats.theilslopes(y, x).slope)

    significant = bool(p_value < alpha)
    if significant:
        headline_direction = "increasing" if fit.slope > 0 else "decreasing"
        agrees = mk_trend == headline_direction
    else:
        agrees = mk_trend == "no trend"

    return TrendResult(
        n_years=n,
        n_effective=n_eff,
        start_year=int(x[0]),
        end_year=int(x[-1]),
        alpha=alpha,
        slope_per_year=float(fit.slope),
        intercept=float(fit.intercept),
        ci_low_per_year=float(ci_low),
        ci_high_per_year=float(ci_high),
        p_value=p_value,
        significant=significant,
        total_change=float(fit.slope * (x[-1] - x[0])),
        lag1_autocorrelation=r1,
        autocorrelated=bool(autocorrelated),
        mk_method=mk_method,
        mk_trend=mk_trend,
        mk_p_value=mk_p,
        sen_slope_per_year=sen_slope,
        agrees=bool(agrees),
        warning=warning,
    )


def trend_line_band(years, values, alpha: float = DEFAULT_ALPHA) -> pd.DataFrame:
    """Fitted OLS line with its confidence band (for the mean response, not a prediction interval).

    Uses the same autocorrelation adjustment as ``analyze_trend``. Returns a DataFrame with
    ``year``, ``fit``, ``low`` and ``high``, one row per input year.
    """
    x, y = _clean_xy(years, values)
    n = x.size
    if n < 3:
        raise ValueError("At least 3 points are needed for a confidence band.")
    if np.ptp(y) == 0:
        return pd.DataFrame({"year": x.astype(int), "fit": y, "low": y, "high": y})
    fit = stats.linregress(x, y)
    fitted = fit.intercept + fit.slope * x
    residuals = y - fitted
    _, _, df = _effective_dof(residuals)
    residual_sd = np.sqrt(np.sum(residuals**2) / (n - 2)) * np.sqrt((n - 2) / df)
    x_mean = x.mean()
    sxx = np.sum((x - x_mean) ** 2)
    t_critical = stats.t.ppf(1 - alpha / 2, df=df)
    half_width = t_critical * residual_sd * np.sqrt(1 / n + (x - x_mean) ** 2 / sxx)
    return pd.DataFrame(
        {"year": x.astype(int), "fit": fitted, "low": fitted - half_width, "high": fitted + half_width}
    )


def format_p_value(p: float) -> str:
    """Readable p-value: "< 0.001" for very small values, otherwise three decimals."""
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def p_text(p: float) -> str:
    """p-value phrase for sentences: "p < 0.001" or "p = 0.046"."""
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
