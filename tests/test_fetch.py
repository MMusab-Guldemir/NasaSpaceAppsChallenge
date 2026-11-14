"""Tests for parsing NASA POWER responses (offline, no network).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.fetch import daily_rate_to_monthly_total, parse_power_regional


def feature(lon, lat, values):
    return {
        "geometry": {"coordinates": [lon, lat, 1500.0]},
        "properties": {"parameter": {"T2M": values}},
    }


def test_parse_power_regional_weights_by_latitude_and_drops_annual_key():
    payload = {
        "header": {"fill_value": -999.0},
        "features": [
            feature(-105.0, 0.0, {"200001": 10.0, "200013": 99.0}),
            feature(-105.0, 60.0, {"200001": 20.0, "200013": 99.0}),
        ],
    }
    monthly = parse_power_regional(payload, "T2M")
    assert len(monthly) == 1  # the 13th "month" is dropped
    weights = np.cos(np.radians([0.0, 60.0]))
    expected = (10.0 * weights[0] + 20.0 * weights[1]) / weights.sum()
    assert monthly.loc[0, "value"] == pytest.approx(expected)
    assert monthly.loc[0, "date"] == pd.Timestamp("2000-01-01")


def test_month_with_partial_fill_becomes_missing():
    payload = {
        "header": {"fill_value": -999.0},
        "features": [
            feature(-105.0, 39.0, {"200001": 5.0, "200002": 6.0}),
            feature(-104.0, 39.0, {"200001": 7.0, "200002": -999.0}),
        ],
    }
    monthly = parse_power_regional(payload, "T2M").set_index("date")
    assert monthly.loc[pd.Timestamp("2000-01-01"), "value"] == pytest.approx(6.0)
    assert np.isnan(monthly.loc[pd.Timestamp("2000-02-01"), "value"])


def test_parse_power_regional_ignores_fill_values():
    payload = {
        "header": {"fill_value": -999.0},
        "features": [
            feature(-105.0, 39.0, {"200001": 5.0, "200002": -999.0}),
            feature(-104.0, 39.0, {"200001": 7.0, "200002": -999.0}),
        ],
    }
    monthly = parse_power_regional(payload, "T2M")
    assert monthly["date"].tolist() == [pd.Timestamp("2000-01-01")]
    assert monthly.loc[0, "value"] == pytest.approx(6.0)


def test_daily_rate_to_monthly_total_uses_days_in_month():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2001-02-01", "2004-02-01", "2001-01-01"]), "value": [1.0, 1.0, 2.0]}
    )
    totals = daily_rate_to_monthly_total(frame)
    assert totals["value"].tolist() == [28.0, 29.0, 62.0]
