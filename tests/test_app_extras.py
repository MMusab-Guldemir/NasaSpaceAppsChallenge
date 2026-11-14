"""App tests for the verdict strip, the jump to the case file, period resets and hidden empty cards.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from trend.fetch import available_variable_keys
from trend.regions import REGIONS

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def run(**params) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    for key, value in params.items():
        at.query_params[key] = value
    at.run()
    assert not at.exception
    return at


def strip_text(at: AppTest) -> str:
    return next((m.value for m in at.markdown if "class='strip'" in m.value), "")


def test_verdict_strip_shows_the_current_case_at_the_top():
    at = run(lang="en", region="amazon", case="precipitation")
    strip = strip_text(at)
    assert "Case on the desk" in strip and "Precipitation" in strip and "stamp confirmed" in strip
    assert "▼" in strip  # a confirmed fall


def test_first_load_does_not_jump_but_a_click_does():
    at = run(lang="en")
    assert "_jump" not in at.session_state
    card = next(b for b in at.button if b.key == "open_precipitation")
    card.click().run()
    assert not at.exception
    assert "_jump" not in at.session_state  # consumed by the scroll script on that run
    assert at.session_state["case"] == "precipitation"


def test_changing_region_resets_a_narrowed_period():
    at = run(lang="en", region="colorado", case="air_temperature", start="1990", end="2005")
    assert at.session_state["period_air_temperature"] == (1990, 2005)
    at.sidebar.selectbox[0].set_value("marmara").run()
    assert not at.exception
    first = int(at.slider[0].min)
    assert at.session_state["period_air_temperature"][0] == first


def test_measurements_without_any_prepared_file_are_hidden():
    measured = {key for region_key in REGIONS for key in available_variable_keys(region_key)}
    at = run(lang="en")
    keys = {b.key.removeprefix("open_") for b in at.button if b.key and b.key.startswith("open_")}
    assert keys <= measured
    if "tree_cover" not in measured:
        assert "tree_cover" not in keys


def test_failed_live_requests_are_not_repeated_on_every_rerun(monkeypatch):
    import requests

    import trend.fetch

    calls = []

    def offline(parameter, region, start_year, end_year, timeout=300):
        calls.append(parameter)
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(trend.fetch, "request_power_regional", offline)
    monkeypatch.setattr(trend.fetch, "_sleep", lambda seconds: None)
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["area_mode"] = "custom"
    at.session_state["custom_bbox"] = (61.0, 21.0, 64.0, 24.0)  # not cached by other tests
    at.run()
    assert not at.exception
    first = len(calls)
    assert first > 0
    at.run()  # a rerun (slider move, language switch) within a minute: no new requests
    assert len(calls) == first
    retry = next(b for b in at.button if b.key == "retry_fetch")
    retry.click().run()  # the Retry button asks again
    assert len(calls) > first
