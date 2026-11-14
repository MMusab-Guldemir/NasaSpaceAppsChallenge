"""Smoke tests: the board and every case file render without errors, in English and Turkish.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from trend.fetch import available_variable_keys
from trend.i18n import TEXT

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def run_app(lang: str = "en") -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["lang"] = lang
    return at.run()


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_board_and_default_case_render(lang):
    at = run_app(lang)
    assert not at.exception
    assert any(TEXT[lang]["title"] == title.value for title in at.title)
    markdown = " ".join(md.value for md in at.markdown)
    assert TEXT[lang]["step_verdict"].split("·")[-1].strip() in markdown


def test_marmara_region_renders():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "marmara"
    at.run()
    assert not at.exception
    assert any("Istanbul" in h.value for h in at.header)


@pytest.mark.parametrize("variable_key", available_variable_keys("marmara"))
def test_each_marmara_case_file_opens(variable_key):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "marmara"
    at.run()
    at.button(key=f"open_{variable_key}").click().run()
    assert not at.exception
    assert at.session_state["case"] == variable_key


def test_example_case_opens_case_and_period():
    at = run_app("en")
    at.button(key="example_no2").click().run()
    assert not at.exception
    assert at.session_state["case"] == "no2"
    assert at.slider(key="period_no2").value == (2005, 2019)


@pytest.mark.parametrize("lang", ["en", "tr"])
@pytest.mark.parametrize("variable_key", available_variable_keys("colorado"))
def test_each_case_file_opens(variable_key, lang):
    at = run_app(lang)
    at.button(key=f"open_{variable_key}").click().run()
    assert not at.exception
    assert at.session_state["case"] == variable_key


def test_short_period_is_blocked_with_a_message():
    at = run_app("en")
    case = at.session_state["case"]
    at.slider(key=f"period_{case}").set_value((2015, 2020)).run()
    assert not at.exception
    assert any("at least 10 complete years" in err.value for err in at.error)


def test_turkish_numbers_use_a_decimal_comma():
    at = run_app("tr")
    markdown = " ".join(md.value for md in at.markdown)
    assert "+0,33" in markdown


def test_marmara_ndvi_shows_three_decimals_and_a_borderline_headline():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "marmara"
    at.run()
    at.button(key="open_ndvi").click().run()
    assert not at.exception
    markdown = " ".join(md.value for md in at.markdown)
    assert "+0.014" in markdown
    assert TEXT["en"]["headline_disputed"] in markdown


def test_period_is_remembered_when_coming_back_to_a_case():
    at = run_app("en")
    at.slider(key="period_air_temperature").set_value((1990, 2010)).run()
    at.button(key="open_snowfall").click().run()
    at.button(key="open_air_temperature").click().run()
    assert not at.exception
    assert at.slider(key="period_air_temperature").value == (1990, 2010)


def test_turkish_confirmed_stamp_wording():
    at = run_app("tr")
    markdown = " ".join(md.value for md in at.markdown)
    assert "Doğrulandı" in markdown
    assert "Kanıtlandı" not in markdown


def _synthetic_fetch(variable, region, start_year, end_year, timeout=300):
    import numpy as np
    import pandas as pd

    dates = pd.date_range("1981-01-01", "2025-12-01", freq="MS")
    values = 10 + 0.03 * (dates.year - 1981) + np.random.default_rng(1).normal(0, 0.5, dates.size)
    return pd.DataFrame({"date": dates, "value": values, "n_cells": 25}), "MERRA2"


def _corner_inputs(at):
    return tuple(at.number_input(key=k).value for k in ("bbox_w", "bbox_s", "bbox_e", "bbox_n"))


def test_switching_to_custom_starts_from_the_region_on_screen(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", _synthetic_fetch)
    at = run_app("en")
    at.selectbox(key="region").set_value("marmara").run()
    at.radio(key="area_mode").set_value("custom").run()
    assert not at.exception
    assert tuple(at.session_state["custom_bbox"]) == (27.0, 40.0, 30.0, 42.0)
    assert _corner_inputs(at) == (27.0, 40.0, 30.0, 42.0)


def test_region_is_kept_after_visiting_custom_mode(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", _synthetic_fetch)
    at = run_app("en")
    at.radio(key="area_mode").set_value("custom").run()  # seeded from Colorado
    at.radio(key="area_mode").set_value("prepared").run()
    at.selectbox(key="region").set_value("marmara").run()
    at.radio(key="area_mode").set_value("custom").run()  # second switch: from Marmara now
    assert tuple(at.session_state["custom_bbox"]) == (27.0, 40.0, 30.0, 42.0)
    at.radio(key="area_mode").set_value("prepared").run()
    assert not at.exception
    assert at.session_state["region"] == "marmara"
    assert any("Istanbul" in h.value for h in at.header)


def test_corner_inputs_match_a_typed_rectangle_after_a_round_trip(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", _synthetic_fetch)
    at = run_app("en")
    at.selectbox(key="region").set_value("marmara").run()
    at.radio(key="area_mode").set_value("custom").run()
    for key, value in zip(("bbox_w", "bbox_s", "bbox_e", "bbox_n"), (30.0, 36.0, 34.0, 39.0)):
        at.number_input(key=key).set_value(value)
    next(b for b in at.button if b.label == TEXT["en"]["apply_coords"]).click().run()
    assert tuple(at.session_state["custom_bbox"]) == (30.0, 36.0, 34.0, 39.0)
    at.radio(key="area_mode").set_value("prepared").run()
    at.radio(key="area_mode").set_value("custom").run()
    assert not at.exception
    assert tuple(at.session_state["custom_bbox"]) == (30.0, 36.0, 34.0, 39.0)
    assert _corner_inputs(at) == (30.0, 36.0, 34.0, 39.0)
    # An untouched "apply" keeps the same rectangle instead of jumping somewhere else.
    next(b for b in at.button if b.label == TEXT["en"]["apply_coords"]).click().run()
    assert tuple(at.session_state["custom_bbox"]) == (30.0, 36.0, 34.0, 39.0)


def test_offline_custom_area_shows_one_message_and_a_retry_button(monkeypatch):
    import requests

    import trend.fetch

    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")

    calls = []

    def offline_counted(*args, **kwargs):
        calls.append(args[0].key)
        offline()

    monkeypatch.setattr(trend.fetch, "fetch_power_variable", offline_counted)
    monkeypatch.setattr(trend.fetch, "_sleep", lambda seconds: None)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["area_mode"] = "custom"
    at.session_state["custom_bbox"] = (101.0, 11.0, 104.0, 14.0)  # not cached by other tests
    at.run()
    assert not at.exception
    assert [error.value for error in at.error] == [TEXT["en"]["fetch_failed_all"]]
    assert at.button(key="retry_fetch") is not None
    assert not at.warning
    assert calls.count("air_temperature") == 3 and calls.count("snowfall") == 3  # quick retries
