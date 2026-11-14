"""Tests for parsing NASA POWER responses (offline, no network).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.fetch import (
    build_no2_from_giovanni,
    daily_rate_to_monthly_total,
    load_giovanni_csv,
    parse_power_regional,
)


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


def test_cells_that_never_report_data_are_left_out():
    # A sea cell (always fill for a land-only variable) must not blank out every month.
    payload = {
        "header": {"fill_value": -999.0},
        "features": [
            feature(29.0, 41.0, {"200001": 3.0, "200002": 4.0}),
            feature(28.0, 41.0, {"200001": -999.0, "200002": -999.0}),
        ],
    }
    monthly = parse_power_regional(payload, "T2M")
    assert monthly["value"].tolist() == [3.0, 4.0]


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


GIOVANNI_SAMPLE = """Title:,Area-Averaged Time Series
User Start Date:,2005-01-01T00:00:00Z
User End Date:,2005-02-28T23:59:59Z
Bounding Box:,"-109.05,37,-102.04,41"
Fill Value (mean_OMNO2d_004_ColumnAmountNO2TropCloudScreened):,-1.26765e+30

time,mean_OMNO2d_004_ColumnAmountNO2TropCloudScreened
{rows}
"""


def write_giovanni(tmp_path, name, rows):
    path = tmp_path / name
    path.write_text(GIOVANNI_SAMPLE.format(rows="\n".join(rows)), encoding="utf-8")
    return path


def test_load_giovanni_csv_skips_metadata_and_fill_values(tmp_path):
    path = write_giovanni(
        tmp_path, "a.csv", ["2005-01-01,1.5e+15", "2005-01-02,-1.26765e+30", "2005-01-03,2.5e+15"]
    )
    daily = load_giovanni_csv(path)
    assert len(daily) == 3
    assert daily["value"].isna().sum() == 1
    assert daily.loc[0, "date"] == pd.Timestamp("2005-01-01")


def test_build_no2_requires_enough_valid_days_per_month(tmp_path):
    january = [f"2005-01-{d:02d},2.0e+15" for d in range(1, 13)]  # 12 valid days
    february = [f"2005-02-{d:02d},4.0e+15" for d in range(1, 6)]  # only 5 valid days
    path = write_giovanni(tmp_path, "b.csv", january + february)
    monthly = build_no2_from_giovanni([path], min_valid_days=10).set_index("date")
    assert monthly.loc[pd.Timestamp("2005-01-01"), "value"] == pytest.approx(2.0)
    assert np.isnan(monthly.loc[pd.Timestamp("2005-02-01"), "value"])


def test_build_no2_merges_chunks_without_duplicate_days(tmp_path):
    first = write_giovanni(tmp_path, "c1.csv", [f"2005-01-{d:02d},1.0e+15" for d in range(1, 21)])
    second = write_giovanni(tmp_path, "c2.csv", [f"2005-01-{d:02d},1.0e+15" for d in range(15, 32)])
    monthly = build_no2_from_giovanni([first, second], min_valid_days=10)
    assert monthly.loc[0, "n_days"] == 31


def test_daily_rate_to_monthly_total_uses_days_in_month():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2001-02-01", "2004-02-01", "2001-01-01"]), "value": [1.0, 1.0, 2.0]}
    )
    totals = daily_rate_to_monthly_total(frame)
    assert totals["value"].tolist() == [28.0, 29.0, 62.0]
