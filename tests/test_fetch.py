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


def _grid_payload(box, parameter="T2M", value=None, fill=-999.0):
    """Synthetic POWER payload with one cell per 0.5 x 0.625 degree grid point inside the box."""
    import math

    value = value or (lambda lon, lat: 10.0 + lat / 100)
    west, south, east, north = box
    features = []
    for j in range(math.ceil(south / 0.5 - 1e-9), math.floor(north / 0.5 + 1e-9) + 1):
        for k in range(math.ceil(west / 0.625 - 1e-9), math.floor(east / 0.625 + 1e-9) + 1):
            lon, lat = k * 0.625, j * 0.5
            series = {f"2020{m:02d}": value(lon, lat) for m in range(1, 13)}
            features.append(
                {"geometry": {"coordinates": [lon, lat, 0]}, "properties": {"parameter": {parameter: series}}}
            )
    return {"header": {"fill_value": fill, "sources": ["MERRA2"]}, "features": features}


def _patch_requests(monkeypatch, behaviour):
    import trend.fetch

    calls, pauses = [], []

    def fake(parameter, region, start_year, end_year, timeout=300):
        calls.append((parameter, region.bbox, end_year, timeout))
        return behaviour(len(calls), parameter, region.bbox)

    monkeypatch.setattr(trend.fetch, "request_power_regional", fake)
    monkeypatch.setattr(trend.fetch, "_sleep", pauses.append)
    return calls, pauses


def _area(bbox, key="air_temperature"):
    from trend.fetch import fetch_power_area
    from trend.variables import get_variable

    return fetch_power_area(get_variable(key), bbox, 2020, 2020, timeout=(10, 45))


def test_small_rectangle_uses_the_nearest_grid_cell(monkeypatch):
    calls, _ = _patch_requests(monkeypatch, lambda n, p, box: _grid_payload(box, parameter=p))
    monthly, sources = _area((29.0, 41.05, 29.3, 41.2))
    assert len(calls) == 1
    west, south, east, north = calls[0][1]
    assert 2 <= east - west <= 10 and 2 <= north - south <= 10
    assert (monthly["n_cells"] == 1).all()  # no centre inside: the nearest cell (29.375, 41.0)
    assert monthly["value"].iloc[0] == pytest.approx(10.41)
    assert sources == "MERRA2"


def test_cells_inside_a_rectangle_are_used(monkeypatch):
    _patch_requests(monkeypatch, lambda n, p, box: _grid_payload(box, parameter=p))
    monthly, _ = _area((28.6, 40.9, 29.5, 41.6))  # centres 28.75/29.375 x 41.0/41.5
    assert (monthly["n_cells"] == 4).all()


def test_large_rectangle_is_fetched_in_pieces_without_double_counting(monkeypatch):
    calls, _ = _patch_requests(monkeypatch, lambda n, p, box: _grid_payload(box, parameter=p))
    bbox = (20.0, 30.0, 45.0, 40.0)
    monthly, _ = _area(bbox)
    assert len(calls) == 6
    expected = len(_grid_payload(bbox)["features"])
    assert (monthly["n_cells"] == expected).all()


def test_quick_failures_are_retried_until_an_answer_arrives(monkeypatch):
    import requests

    def behaviour(n, parameter, box):
        if n <= 2:
            raise requests.ConnectionError("reset")
        return _grid_payload(box, parameter=parameter)

    calls, pauses = _patch_requests(monkeypatch, behaviour)
    _area((27.0, 40.0, 30.0, 42.0))
    assert len(calls) == 3 and pauses == [1.5, 3.0]
    assert all(call[3] == (10, 45) for call in calls)


def test_garbled_answer_is_retried(monkeypatch):
    import requests

    def behaviour(n, parameter, box):
        if n == 1:
            raise requests.exceptions.JSONDecodeError("bad", "doc", 0)
        return _grid_payload(box, parameter=parameter)

    calls, _ = _patch_requests(monkeypatch, behaviour)
    _area((27.0, 40.0, 30.0, 42.0))
    assert len(calls) == 2


@pytest.mark.parametrize("status", [429, 503])
def test_busy_server_gets_three_attempts_then_the_error(monkeypatch, status):
    from trend.fetch import DataSourceError

    def behaviour(n, parameter, box):
        raise DataSourceError("busy", status=status)

    calls, _ = _patch_requests(monkeypatch, behaviour)
    with pytest.raises(DataSourceError):
        _area((27.0, 40.0, 30.0, 42.0))
    assert len(calls) == 3


def test_end_date_rejection_in_an_area_request_drops_the_newest_year(monkeypatch):
    from trend.fetch import DataSourceError

    def behaviour(n, parameter, box):
        if n == 1:
            raise DataSourceError("Please provide a correct end date. Your end date out of range.", status=422)
        return _grid_payload(box, parameter=parameter)

    calls, pauses = _patch_requests(monkeypatch, behaviour)
    _area((27.0, 40.0, 30.0, 42.0))
    assert [call[2] for call in calls] == [2020, 2019] and pauses == []


@pytest.mark.parametrize("error", ["timeout", "box"])
def test_timeouts_and_rejected_requests_are_not_retried(monkeypatch, error):
    import requests

    from trend.fetch import DataSourceError

    exception = {
        "timeout": requests.ReadTimeout("slow"),
        "box": DataSourceError("Please provide at least a 2 degree range", status=422),
    }[error]

    def behaviour(n, parameter, box):
        raise exception

    calls, pauses = _patch_requests(monkeypatch, behaviour)
    with pytest.raises(type(exception)):
        _area((27.0, 40.0, 30.0, 42.0))
    assert len(calls) == 1 and pauses == []


def test_area_over_the_sea_reports_no_data_without_retrying(monkeypatch):
    from trend.fetch import DataSourceError

    calls, pauses = _patch_requests(
        monkeypatch, lambda n, p, box: _grid_payload(box, parameter=p, value=lambda lon, lat: -999.0)
    )
    with pytest.raises(DataSourceError, match="fill"):
        _area((-30.0, 30.0, -27.0, 32.0), key="snowfall")
    assert len(calls) == 1 and pauses == []


def test_dust_and_smoke_is_served_by_power():
    from trend.fetch import POWER_VARIABLES

    assert POWER_VARIABLES["aod"] == ("AOD_55", False)


def test_zero_aerosol_values_count_as_missing():
    from trend.fetch import parse_power_regional

    payload = {
        "header": {"fill_value": -999.0},
        "features": [
            feature(28.0, 41.0, {"202001": 0.2, "202002": 0.0, "202003": 0.3}),
            feature(29.0, 41.0, {"202001": 0.4, "202002": 0.1, "202003": 0.0}),
        ],
    }
    for feature_ in payload["features"]:
        feature_["properties"]["parameter"] = {"AOD_55": feature_["properties"]["parameter"]["T2M"]}
    monthly = parse_power_regional(payload, "AOD_55")
    assert monthly["value"].notna().tolist() == [True, False, False]  # a zero cell makes the month missing
