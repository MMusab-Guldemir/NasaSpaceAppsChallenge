"""App tests for the verdict strip, the jump to the case file, period resets and hidden empty cards.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import pytest
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


def test_guided_start_opens_a_suggested_case():
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["lang"] = "tr"
    at.session_state["guide_topic"] = "heat"
    at.session_state["guide_place"] = "city"
    at.run()
    assert not at.exception
    button = next(b for b in at.button if b.key == "guide_marmara_hot_days")
    button.click().run()
    assert not at.exception
    assert at.session_state["region"] == "marmara" and at.session_state["case"] == "hot_days"


@pytest.mark.parametrize("case, shown", [("air_temperature", True), ("hot_days", True), ("no2", False)])
def test_season_section_only_for_the_three_seasonal_measurements(case, shown):
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["region"] = "marmara"
    at.query_params["case"] = case
    at.run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert ("Which season is changing?" in labels) is shown


def test_case_report_download_is_a_printable_page():
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["lang"] = "tr"
    at.query_params["region"] = "konya"
    at.query_params["case"] = "hot_days"
    at.run()
    assert not at.exception
    labels = [b.proto.label for b in at.get("download_button")]
    assert any("Dosya raporunu indir" in label for label in labels)


def test_compare_section_ranks_the_prepared_regions():
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["lang"] = "tr"
    at.query_params["region"] = "konya"
    at.query_params["case"] = "groundwater"
    at.run()
    assert not at.exception
    assert "Bu bölge diğerleriyle nasıl kıyaslanıyor?" in [e.label for e in at.expander]
    assert any("11 bölge içinde" in m.value for m in at.markdown)


def test_stripes_and_record_sentence_in_the_case_file():
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["lang"] = "tr"
    at.query_params["region"] = "konya"
    at.query_params["case"] = "precipitation"
    at.run()
    assert not at.exception
    assert any(m.value.startswith("📌 2025, 45 yılın en kurak 3. yılı") for m in at.markdown)
