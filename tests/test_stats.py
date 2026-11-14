"""Tests for trend statistics.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.stats import (
    MIN_YEARS,
    analyze_trend,
    format_p_value,
    to_annual,
    trend_line_band,
)
from trend.variables import get_variable


def monthly_frame(start: str, periods: int, values) -> pd.DataFrame:
    dates = pd.date_range(start, periods=periods, freq="MS")
    return pd.DataFrame({"date": dates, "value": np.asarray(values, dtype=float)})


# --- to_annual -------------------------------------------------------------------------------

def test_calendar_mean_keeps_only_complete_years():
    temp = get_variable("air_temperature")
    frame = monthly_frame("2000-01-01", 36, np.arange(36))
    frame.loc[frame["date"] == "2001-06-01", "value"] = np.nan  # 2001 is incomplete
    annual, incomplete = to_annual(frame, temp)
    assert annual["year"].tolist() == [2000, 2002]
    assert incomplete == [2001]
    assert annual.loc[0, "value"] == pytest.approx(np.mean(np.arange(12)))


def test_water_year_is_labelled_by_ending_year_and_summed():
    snow = get_variable("snowfall")
    # October 2000 to September 2001 is water year 2001.
    frame = monthly_frame("2000-10-01", 12, np.ones(12) * 10.0)
    annual, incomplete = to_annual(frame, snow)
    assert annual["year"].tolist() == [2001]
    assert annual.loc[0, "value"] == pytest.approx(120.0)
    assert incomplete == []


def test_partial_water_year_is_dropped():
    snow = get_variable("snowfall")
    # Jan to Dec 2001 covers the end of water year 2001 and the start of water year 2002.
    frame = monthly_frame("2001-01-01", 12, np.ones(12))
    annual, incomplete = to_annual(frame, snow)
    assert annual.empty
    assert incomplete == [2001, 2002]


def test_multi_year_water_years_with_trailing_autumn_months():
    snow = get_variable("snowfall")
    # Oct 2000 to Dec 2003: water years 2001, 2002 and 2003 are complete; 2004 has only Oct-Dec.
    frame = monthly_frame("2000-10-01", 39, np.arange(39, dtype=float))
    annual, incomplete = to_annual(frame, snow)
    assert annual["year"].tolist() == [2001, 2002, 2003]
    assert annual.loc[0, "value"] == pytest.approx(sum(range(12)))
    assert incomplete == [2004]


def test_duplicate_month_does_not_hide_a_missing_month():
    temp = get_variable("air_temperature")
    frame = monthly_frame("2000-01-01", 12, np.ones(12))
    frame = frame[frame["date"] != "2000-05-01"]  # May is missing
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)  # January twice
    annual, incomplete = to_annual(frame, temp)
    assert annual.empty
    assert incomplete == [2000]


def test_growing_season_uses_may_to_september_only():
    ndvi = get_variable("ndvi")
    values = np.zeros(12)
    values[4:9] = 0.5  # May to September
    frame = monthly_frame("2005-01-01", 12, values)
    annual, _ = to_annual(frame, ndvi)
    assert annual.loc[0, "value"] == pytest.approx(0.5)
    assert annual.loc[0, "n_months"] == 5


# --- analyze_trend ---------------------------------------------------------------------------

def test_known_trend_is_detected():
    rng = np.random.default_rng(42)
    years = np.arange(1981, 2021)
    values = 0.03 * (years - years[0]) + rng.normal(0, 0.2, years.size)
    result = analyze_trend(years, values)
    assert result.significant
    assert result.slope_per_year == pytest.approx(0.03, abs=0.01)
    assert result.ci_low_per_year < 0.03 < result.ci_high_per_year
    assert result.mk_trend == "increasing"
    assert result.agrees
    assert result.direction == "increasing"


def test_false_positive_rate_on_white_noise_is_near_alpha():
    rng = np.random.default_rng(7)
    years = np.arange(1990, 2020)
    hits = sum(analyze_trend(years, rng.normal(0, 1, years.size)).significant for _ in range(300))
    assert 0.01 < hits / 300 < 0.11


def test_short_series_is_blocked():
    years = np.arange(2000, 2000 + MIN_YEARS - 1)
    with pytest.raises(ValueError):
        analyze_trend(years, np.arange(years.size, dtype=float))


def test_series_under_twenty_years_gets_a_warning():
    years = np.arange(2000, 2015)
    result = analyze_trend(years, np.arange(years.size, dtype=float) + np.sin(years))
    assert result.warning is not None


def test_total_change_is_slope_times_span():
    rng = np.random.default_rng(1)
    years = np.arange(1981, 2026)
    values = -0.5 * (years - 1981) + rng.normal(0, 3, years.size)
    result = analyze_trend(years, values)
    assert result.total_change == pytest.approx(result.slope_per_year * (2025 - 1981))


def test_gaps_in_years_are_handled_by_sen_slope():
    years = np.array([2000, 2001, 2002, 2005, 2006, 2007, 2008, 2010, 2011, 2012, 2013, 2014])
    values = 2.0 * years
    result = analyze_trend(years, values)
    assert result.sen_slope_per_year == pytest.approx(2.0)


def ar1_series(rng, phi: float, n: int) -> np.ndarray:
    noise = rng.normal(0, 1, n + 50)
    out = np.zeros_like(noise)
    for i in range(1, noise.size):
        out[i] = phi * out[i - 1] + noise[i]
    return out[50:]


def test_positive_autocorrelation_does_not_inflate_false_positives():
    rng = np.random.default_rng(21)
    years = np.arange(1981, 2026)
    hits = sum(analyze_trend(years, ar1_series(rng, 0.5, years.size)).significant for _ in range(300))
    # Without the effective-sample-size correction this is about 25%.
    assert hits / 300 < 0.13


def test_positive_autocorrelation_switches_to_hamed_rao():
    rng = np.random.default_rng(5)
    years = np.arange(1981, 2026)
    methods = {analyze_trend(years, ar1_series(rng, 0.7, years.size)).mk_method for _ in range(20)}
    assert any(m.startswith("Hamed-Rao") for m in methods)


def test_negative_autocorrelation_keeps_the_original_test():
    rng = np.random.default_rng(9)
    years = np.arange(1981, 2026)
    for _ in range(20):
        result = analyze_trend(years, ar1_series(rng, -0.6, years.size))
        assert result.mk_method == "Mann-Kendall"
        assert result.n_effective == result.n_years


def test_constant_series_reports_no_trend():
    years = np.arange(1990, 2010)
    result = analyze_trend(years, np.full(years.size, 3.0))
    assert result.p_value == 1.0
    assert not result.significant
    assert result.mk_trend == "no trend"
    assert format_p_value(result.p_value) == "1.000"


def test_unsorted_input_gives_the_same_result():
    rng = np.random.default_rng(13)
    years = np.arange(1990, 2020)
    values = 0.05 * years + rng.normal(0, 1, years.size)
    order = rng.permutation(years.size)
    a = analyze_trend(years, values)
    b = analyze_trend(years[order], values[order])
    assert a.slope_per_year == pytest.approx(b.slope_per_year)
    assert a.p_value == pytest.approx(b.p_value)


def test_robustness_check_always_returns_a_finite_p_value():
    rng = np.random.default_rng(11)
    years = np.arange(1990, 2020)
    for _ in range(300):
        result = analyze_trend(years, rng.normal(0, 1, years.size))
        assert np.isfinite(result.mk_p_value)


def test_confidence_band_contains_the_fitted_line():
    rng = np.random.default_rng(3)
    years = np.arange(1990, 2020)
    band = trend_line_band(years, 0.1 * years + rng.normal(0, 1, years.size))
    assert (band["low"] <= band["fit"]).all() and (band["fit"] <= band["high"]).all()
    widths = band["high"] - band["low"]
    assert widths.iloc[len(widths) // 2] < widths.iloc[0]  # narrowest near the middle


def test_format_p_value():
    assert format_p_value(0.0001) == "< 0.001"
    assert format_p_value(0.04567) == "0.046"
