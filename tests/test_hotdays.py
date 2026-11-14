"""Tests for the hot-day counts (trend/hotdays.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest
import requests

import trend.hotdays as hd
from trend.fetch import DataSourceError, available_variable_keys, load_processed
from trend.regions import REGIONS
from trend.world import board_verdict


def feature(lon, lat, daily):
    return {"geometry": {"coordinates": [lon, lat, 0.0]}, "properties": {"parameter": {"T2M_MAX": daily}}}


def year_of(value_for_day, year=2020):
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return {d.strftime("%Y%m%d"): value_for_day(d) for d in days}


def test_counts_days_above_the_line_per_cell_then_averages_with_cos_latitude():
    hot_july = year_of(lambda d: 35.0 if d.month == 7 else 20.0)          # 31 hot days
    hot_july_aug = year_of(lambda d: 31.0 if d.month in (7, 8) else 25.0)  # 62 hot days
    payload = {"features": [feature(27.5, 40.0, hot_july), feature(28.125, 41.0, hot_july_aug)]}
    monthly = hd.monthly_hot_days([payload], (27.0, 40.0, 30.0, 42.0))
    july = monthly.loc[monthly["date"] == pd.Timestamp("2020-07-01"), "value"].item()
    august = monthly.loc[monthly["date"] == pd.Timestamp("2020-08-01"), "value"].item()
    w1, w2 = np.cos(np.deg2rad(40.0)), np.cos(np.deg2rad(41.0))
    assert july == pytest.approx(31.0)  # both cells: 31 days
    assert august == pytest.approx((0 * w1 + 31 * w2) / (w1 + w2))
    assert monthly["value"].sum() == pytest.approx((31 * w1 + 62 * w2) / (w1 + w2))
    cells = monthly.attrs["cells"]
    assert sorted(cells["days"].tolist()) == [31.0, 62.0] and set(cells["year"]) == {2020}


def test_exactly_30_degrees_is_not_a_hot_day_and_cells_outside_the_box_are_ignored():
    payload = {"features": [feature(27.5, 40.0, year_of(lambda d: 30.0)), feature(35.0, 40.0, year_of(lambda d: 40.0))]}
    monthly = hd.monthly_hot_days([payload], (27.0, 40.0, 30.0, 42.0))
    assert monthly["value"].sum() == 0.0 and set(monthly["n_cells"]) == {1}


def test_a_month_with_missing_days_is_left_out():
    daily = year_of(lambda d: 33.0)
    daily["20200715"] = -999.0
    monthly = hd.monthly_hot_days([{"features": [feature(27.5, 40.0, daily)]}], (27.0, 40.0, 30.0, 42.0))
    assert np.isnan(monthly.loc[monthly["date"] == pd.Timestamp("2020-07-01"), "value"].item())
    assert np.isnan(monthly.attrs["cells"]["days"].iloc[0])  # the year is incomplete for that cell


def test_empty_answers_raise():
    with pytest.raises(DataSourceError):
        hd.monthly_hot_days([{"features": []}], (27.0, 40.0, 30.0, 42.0))


class FakeResponse:
    def __init__(self, status, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        return self._payload


def test_request_retries_busy_answers_and_refuses_odd_ones(monkeypatch):
    answers = [FakeResponse(503), FakeResponse(200, {"features": []})]
    monkeypatch.setattr(hd.requests, "get", lambda *a, **k: answers.pop(0))
    monkeypatch.setattr(hd.time, "sleep", lambda s: None)
    assert hd.request_daily_year((27, 40, 30, 42), 2020) == {"features": []}
    monkeypatch.setattr(hd.requests, "get", lambda *a, **k: FakeResponse(422, text="too long"))
    with pytest.raises(DataSourceError):
        hd.request_daily_year((27, 40, 30, 42), 2020)
    monkeypatch.setattr(hd.requests, "get", lambda *a, **k: FakeResponse(200, ["not", "a", "dict"]))
    with pytest.raises(DataSourceError):
        hd.request_daily_year((27, 40, 30, 42), 2020, pauses=())


def test_network_errors_are_raised_after_the_retries(monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(hd.requests, "get", offline)
    monkeypatch.setattr(hd.time, "sleep", lambda s: None)
    with pytest.raises(requests.ConnectionError):
        hd.request_daily_year((27, 40, 30, 42), 2020, pauses=(0.0,))


@pytest.mark.parametrize("region_key", [r for r in REGIONS if "hot_days" in available_variable_keys(r)])
def test_real_hot_day_files_are_complete_and_testable(region_key):
    monthly = load_processed(region_key, "hot_days")
    assert monthly["value"].notna().all() and (monthly["value"] >= 0).all()
    assert monthly["value"].max() <= 31
    verdict = board_verdict(monthly, "hot_days")
    assert verdict.annual is None or len(verdict.annual) >= 40


def test_istanbul_hot_days_are_rising():
    if "hot_days" not in available_variable_keys("marmara"):
        pytest.skip("hot-day file not built")
    verdict = board_verdict(load_processed("marmara", "hot_days"), "hot_days")
    assert verdict.status == "confirmed" and verdict.result.slope_per_year > 0


def test_a_cell_repeated_by_overlapping_request_boxes_is_counted_once():
    hot_july = year_of(lambda d: 35.0 if d.month == 7 else 20.0)
    box_a = {"features": [feature(130.0, 62.0, hot_july)]}
    box_b = {"features": [feature(130.0, 62.0, hot_july)]}  # the same edge cell in the second box
    monthly = hd.monthly_hot_days([box_a, box_b], (125.0, 60.0, 135.0, 65.0))
    assert monthly.loc[monthly["date"] == pd.Timestamp("2020-07-01"), "value"].item() == 31.0
    assert monthly.attrs["cells"]["days"].tolist() == [31.0]


def test_a_month_with_days_missing_from_the_answer_is_left_out():
    daily = {k: v for k, v in year_of(lambda d: 35.0).items() if not ("20200710" <= k <= "20200720")}
    monthly = hd.monthly_hot_days([{"features": [feature(27.5, 40.0, daily)]}], (27.0, 40.0, 30.0, 42.0))
    assert np.isnan(monthly.loc[monthly["date"] == pd.Timestamp("2020-07-01"), "value"].item())
