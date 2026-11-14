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


def test_load_ndvi_statistics_reads_monthly_means(tmp_path):
    from trend.appeears import load_ndvi_statistics

    path = tmp_path / "stats.csv"
    path.write_text(
        "File Name,Dataset,aid,Date,Count,Minimum,Maximum,Range,Mean,Standard Deviation\n"
        "a,_1_km_monthly_NDVI,aid0001,2000-02-01,404153.0,-0.199,0.82,\"(-0.199,0.82)\",0.18,0.11\n"
        "b,_1_km_monthly_NDVI,aid0001,2000-03-01,404161.0,-0.19,0.83,\"(-0.19,0.83)\",0.20,0.11\n",
        encoding="utf-8",
    )
    monthly = load_ndvi_statistics(path)
    assert monthly["date"].tolist() == [pd.Timestamp("2000-02-01"), pd.Timestamp("2000-03-01")]
    assert monthly["value"].tolist() == pytest.approx([0.18, 0.20])


def test_daily_rate_to_monthly_total_uses_days_in_month():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2001-02-01", "2004-02-01", "2001-01-01"]), "value": [1.0, 1.0, 2.0]}
    )
    totals = daily_rate_to_monthly_total(frame)
    assert totals["value"].tolist() == [28.0, 29.0, 62.0]


class _Answer:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def _power_payload(year):
    return {
        "header": {"fill_value": -999.0, "sources": ["MERRA2"]},
        "features": [
            {"geometry": {"coordinates": [28.0, 41.0, 0]},
             "properties": {"parameter": {"T2M": {f"{year}{m:02d}": 10.0 + m for m in range(1, 13)}}}},
        ],
    }


def _patched_get(monkeypatch, answers):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((params["end"], timeout))
        return answers[len(calls) - 1]

    monkeypatch.setattr("trend.fetch.requests.get", fake_get)
    return calls


def test_end_date_rejection_retries_once_without_the_newest_year(monkeypatch):
    from trend.fetch import fetch_power_variable
    from trend.regions import REGIONS
    from trend.variables import get_variable

    end_date = {"messages": ["Please provide a correct end date. Your end date out of range."]}
    calls = _patched_get(monkeypatch, [_Answer(422, end_date), _Answer(200, _power_payload(2025))])
    monthly, _ = fetch_power_variable(get_variable("air_temperature"), REGIONS["marmara"], 2025, 2026, timeout=(5, 20))
    assert [c[0] for c in calls] == [2026, 2025]
    assert all(c[1] == (5, 20) for c in calls)
    assert len(monthly) == 12


def test_other_request_errors_are_not_retried(monkeypatch):
    from trend.fetch import DataSourceError, fetch_power_variable
    from trend.regions import REGIONS
    from trend.variables import get_variable

    box = {"messages": ["Please provide at least a 2 degree range in latitude."]}
    calls = _patched_get(monkeypatch, [_Answer(422, box)])
    with pytest.raises(DataSourceError):
        fetch_power_variable(get_variable("air_temperature"), REGIONS["marmara"], 2025, 2026)
    assert len(calls) == 1


def test_unexpected_payload_becomes_a_data_source_error(monkeypatch):
    from trend.fetch import DataSourceError, fetch_power_variable
    from trend.regions import REGIONS
    from trend.variables import get_variable

    _patched_get(monkeypatch, [_Answer(200, {"header": {}, "features": "oops"})])
    with pytest.raises(DataSourceError):
        fetch_power_variable(get_variable("air_temperature"), REGIONS["marmara"], 2025, 2026)


@pytest.mark.parametrize("body", [["Too many requests"], "Too many requests"])
def test_error_answer_that_is_not_an_object_is_a_data_source_error(monkeypatch, body):
    from trend.fetch import DataSourceError, request_power_regional
    from trend.regions import REGIONS

    _patched_get(monkeypatch, [_Answer(429, body)])
    with pytest.raises(DataSourceError) as info:
        request_power_regional("T2M", REGIONS["marmara"], 2025, 2026)
    assert info.value.status == 429


def _retry_setup(monkeypatch, outcomes):
    import trend.fetch

    calls, pauses = [], []

    def fake(variable, region, start_year, end_year, timeout=300):
        calls.append(timeout)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", fake)
    monkeypatch.setattr(trend.fetch, "_sleep", pauses.append)
    return calls, pauses


def _retry_call():
    from trend.fetch import fetch_power_variable_retrying
    from trend.regions import REGIONS
    from trend.variables import get_variable

    return fetch_power_variable_retrying(get_variable("air_temperature"), REGIONS["marmara"], 1981, 2026, timeout=(10, 45))


def test_quick_failures_are_retried_until_an_answer_arrives(monkeypatch):
    import requests

    calls, pauses = _retry_setup(monkeypatch, [requests.ConnectionError("reset"), requests.ConnectionError("reset"), ("data", "MERRA2")])
    assert _retry_call() == ("data", "MERRA2")
    assert calls == [(10, 45)] * 3
    assert pauses == [1.5, 3.0]


@pytest.mark.parametrize("status", [429, 503])
def test_busy_server_gets_three_attempts_then_the_error(monkeypatch, status):
    from trend.fetch import DataSourceError

    busy = DataSourceError("busy", status=status)
    calls, _ = _retry_setup(monkeypatch, [busy, busy, busy])
    with pytest.raises(DataSourceError):
        _retry_call()
    assert len(calls) == 3


def test_unexpected_answer_is_retried(monkeypatch):
    from trend.fetch import UNEXPECTED_RESPONSE, DataSourceError

    calls, _ = _retry_setup(monkeypatch, [DataSourceError(UNEXPECTED_RESPONSE), ("data", "MERRA2")])
    assert _retry_call() == ("data", "MERRA2")
    assert len(calls) == 2


@pytest.mark.parametrize(
    "error",
    [
        "timeout",
        "box",
        "fill",
    ],
)
def test_timeouts_rejections_and_empty_areas_are_not_retried(monkeypatch, error):
    import requests

    from trend.fetch import DataSourceError

    exception = {
        "timeout": requests.ReadTimeout("slow"),
        "box": DataSourceError("Please provide at least a 2 degree range", status=422),
        "fill": DataSourceError("POWER returned only fill values for this request."),
    }[error]
    calls, pauses = _retry_setup(monkeypatch, [exception])
    with pytest.raises(type(exception)):
        _retry_call()
    assert len(calls) == 1 and pauses == []
