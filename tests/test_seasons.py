"""Tests for removing the seasonal cycle (trend/seasons.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.fetch import load_processed
from trend.seasons import (
    SEASON_TEXT,
    anomaly_figure,
    deseasonalize,
    monthly_rate_per_decade,
    months_in_period,
    season_sentence,
    season_text,
    seasonal_swing,
)
from trend.variables import VARIABLES

AMPLITUDE = 10.0
SLOPE_PER_YEAR = 0.3


def monthly(years: int = 20, amplitude: float = AMPLITUDE, slope_per_year: float = SLOPE_PER_YEAR) -> pd.DataFrame:
    """A sine with a 12-month period on top of a linear trend."""
    dates = pd.date_range("2000-01-01", periods=12 * years, freq="MS")
    season = amplitude * np.sin(2 * np.pi * (dates.month - 1) / 12)
    trend = slope_per_year * np.arange(dates.size) / 12
    return pd.DataFrame({"date": dates, "value": 15 + season + trend})


def test_anomalies_remove_the_seasons_and_keep_the_trend():
    data = monthly()
    table = deseasonalize(data)
    assert list(table.columns) == ["date", "value", "usual", "anomaly", "smooth"]
    assert len(table) == len(data)
    per_month = table.groupby(table["date"].dt.month)["anomaly"].mean()
    assert np.allclose(per_month, 0.0, atol=1e-9)
    season = np.sin(2 * np.pi * (table["date"].dt.month - 1) / 12)
    assert abs(np.corrcoef(table["anomaly"], season)[0, 1]) < 0.01
    years = np.arange(len(table)) / 12
    assert np.polyfit(years, table["anomaly"], 1)[0] == pytest.approx(SLOPE_PER_YEAR, rel=0.02)
    smooth = table["smooth"].notna().to_numpy()
    assert smooth.all()  # min_periods=6 also covers the first and last months
    assert np.polyfit(years[smooth], table["smooth"][smooth], 1)[0] == pytest.approx(SLOPE_PER_YEAR, rel=0.02)


def test_seasonal_swing_of_a_sine_is_twice_the_amplitude():
    assert seasonal_swing(monthly(slope_per_year=0.0)) == pytest.approx(2 * AMPLITUDE, rel=1e-9)
    assert seasonal_swing(monthly(amplitude=3.0, slope_per_year=0.0)) == pytest.approx(6.0, rel=1e-9)
    januaries = pd.DataFrame({"date": pd.date_range("2000-01-01", periods=10, freq="12MS"), "value": 1.0})
    assert seasonal_swing(januaries) == 0.0  # one calendar month only, as for a yearly product
    assert seasonal_swing(januaries.iloc[0:0]) == 0.0


def test_missing_months_stay_gaps_and_do_not_raise():
    data = monthly()
    dropped = data["date"].between("2005-03-01", "2005-05-01")
    long_gap = data["date"].between("2012-01-01", "2012-08-01")  # 8 months in a row
    data = data[~dropped & ~long_gap].copy()
    data.loc[data["date"] == "2010-07-01", "value"] = np.nan
    table = deseasonalize(data).set_index("date")
    assert len(table) == 240  # every month from the first to the last is present
    for month in ("2005-03-01", "2005-04-01", "2005-05-01", "2010-07-01", "2012-04-01"):
        assert np.isnan(table.loc[month, "value"]) and np.isnan(table.loc[month, "anomaly"])
        assert np.isfinite(table.loc[month, "usual"])  # the usual value comes from the other years
    assert np.isfinite(table.loc["2005-04-01", "smooth"])  # a short gap is bridged by the 12-month window
    assert np.isnan(table.loc["2012-05-01", "smooth"])  # inside the long gap fewer than 6 months have data
    assert seasonal_swing(data) == pytest.approx(2 * AMPLITUDE, rel=0.05)


def test_real_record_with_a_missing_month():
    data = load_processed("los_angeles", "no2")
    assert data["value"].isna().sum() >= 1
    table = deseasonalize(data)
    assert len(table) == len(pd.date_range(data["date"].min(), data["date"].max(), freq="MS"))
    assert table["anomaly"].isna().sum() >= 1
    assert seasonal_swing(data) > 0


def test_unsorted_and_duplicate_rows_are_handled():
    data = monthly(years=3)
    shuffled = pd.concat([data.iloc[::-1], data.iloc[[5]].assign(value=data["value"].iloc[5] + 2)])
    table = deseasonalize(shuffled)
    assert table["date"].is_monotonic_increasing and len(table) == 36
    assert table["value"].iloc[5] == pytest.approx(data["value"].iloc[5] + 1)  # duplicates are averaged
    empty = deseasonalize(data.iloc[0:0])
    assert empty.empty and list(empty.columns) == ["date", "value", "usual", "anomaly", "smooth"]


def test_months_in_period_follows_calendar_and_water_years():
    data = pd.DataFrame({"date": pd.date_range("1999-01-01", "2003-12-01", freq="MS"), "value": 1.0})
    calendar = months_in_period(data, 2001, 2002)
    assert calendar["date"].min() == pd.Timestamp("2001-01-01")
    assert calendar["date"].max() == pd.Timestamp("2002-12-01")
    water = months_in_period(data, 2001, 2002, year_starts_month=10)
    assert water["date"].min() == pd.Timestamp("2000-10-01")
    assert water["date"].max() == pd.Timestamp("2002-09-01")
    assert len(water) == 24


def test_monthly_rate_shares_a_yearly_total_over_its_months():
    assert monthly_rate_per_decade(12.0, VARIABLES["precipitation"]) == pytest.approx(1.0)
    assert monthly_rate_per_decade(0.5, VARIABLES["air_temperature"]) == pytest.approx(0.5)


def test_sentence_compares_the_swing_with_the_trend():
    english = season_sentence("en", 20.0, 0.47, "°C", 2)
    assert "swings by 20.00 °C" in english and "+0.47 °C per decade" in english and "about 43 times" in english
    turkish = season_sentence("tr", 2.03, -0.6, "ppb", 2)
    assert "2,03 ppb oynar" in turkish and "on yılda -0,60 ppb" in turkish and "yaklaşık 3,4 kat" in turkish
    assert season_sentence("en", 4.3, 25.0, "ppm", 2) is None  # CO2 rises faster than it swings
    assert season_sentence("en", 20.0, 0.001, "°C", 2) is None  # the shown rate would be 0.00
    assert season_sentence("en", 0.0, 0.5, "°C", 2) is None
    assert season_sentence("en", float("nan"), 0.5, "°C", 2) is None


def test_texts_exist_in_both_languages():
    assert set(SEASON_TEXT["tr"]) == set(SEASON_TEXT["en"])
    assert season_text("tr", "option_removed") == "Mevsim döngüsü çıkarılmış"
    assert season_text("de", "smooth") == "12-month average"  # unknown languages fall back to English
    assert season_text("en", "y_title", unit="°C") == "Difference (°C)"


def test_figure_has_two_data_traces_and_a_zero_line():
    table = deseasonalize(monthly())
    figure = anomaly_figure(
        table, "tr", x_title="Ay", y_title="Fark (°C)", unit="°C", separators=",.", decimals=2,
    )
    assert len(figure.data) == 2
    anomaly, smooth = figure.data
    assert anomaly.name == season_text("tr", "anomaly") and smooth.name == season_text("tr", "smooth")
    assert anomaly.line.color == "#2a78d6" and smooth.line.color == "#eb6834"
    assert smooth.line.width > anomaly.line.width
    assert any(shape.y0 == 0 and shape.y1 == 0 for shape in figure.layout.shapes)
    assert figure.layout.height == 320 and figure.layout.separators == ",."
    assert figure.layout.xaxis.title.text == "Ay" and figure.layout.yaxis.title.text == "Fark (°C)"
