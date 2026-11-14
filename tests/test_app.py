"""Smoke tests: the board and every case file render without errors, in English and Turkish.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from trend.fetch import available_variable_keys
from trend.i18n import TEXT
from trend.regions import REGIONS

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
    at.button(key="example_beijing_no2").click().run()  # a famous case in another region
    assert not at.exception
    assert at.session_state["region"] == "beijing"
    assert at.session_state["case"] == "no2"
    assert at.slider(key="period_no2").value == (2013, 2025)


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


def test_marmara_ndvi_shows_three_decimals():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "marmara"
    at.run()
    at.button(key="open_ndvi").click().run()
    assert not at.exception
    markdown = " ".join(md.value for md in at.markdown)
    assert "+0.014" in markdown


def test_disputed_case_gets_the_borderline_headline():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "beijing"
    at.run()
    at.button(key="open_snowfall").click().run()
    assert not at.exception
    markdown = " ".join(md.value for md in at.markdown)
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


def _synthetic_fetch(variable, bbox, start_year, end_year, timeout=300, **kwargs):
    import numpy as np
    import pandas as pd

    dates = pd.date_range("1981-01-01", "2025-12-01", freq="MS")
    values = 10 + 0.03 * (dates.year - 1981) + np.random.default_rng(1).normal(0, 0.5, dates.size)
    return pd.DataFrame({"date": dates, "value": values, "n_cells": 25}), "MERRA2"


def _corner_inputs(at):
    return tuple(at.number_input(key=k).value for k in ("bbox_w", "bbox_s", "bbox_e", "bbox_n"))


def test_switching_to_custom_starts_from_the_region_on_screen(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _synthetic_fetch)
    at = run_app("en")
    at.selectbox(key="region").set_value("marmara").run()
    at.radio(key="area_mode").set_value("custom").run()
    assert not at.exception
    assert tuple(at.session_state["custom_bbox"]) == (27.0, 40.0, 30.0, 42.0)
    assert _corner_inputs(at) == (27.0, 40.0, 30.0, 42.0)


def test_region_is_kept_after_visiting_custom_mode(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _synthetic_fetch)
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

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _synthetic_fetch)
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

    calls = []

    def offline(parameter, region, start_year, end_year, timeout=300):
        calls.append(parameter)
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(trend.fetch, "request_power_regional", offline)
    monkeypatch.setattr(trend.fetch, "_sleep", lambda seconds: None)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["area_mode"] = "custom"
    at.session_state["custom_bbox"] = (101.0, 11.0, 104.0, 14.0)  # not cached by other tests
    at.run()
    assert not at.exception
    assert [error.value for error in at.error] == [TEXT["en"]["fetch_failed_all"]]
    assert at.button(key="retry_fetch") is not None
    assert not at.warning
    # Three quick attempts for the first live measurement; once NASA POWER does not answer, the
    # other measurements are not requested one by one (each could wait for a long timeout).
    assert {p: calls.count(p) for p in set(calls)} == {"T2M": 3}


@pytest.mark.parametrize("region_key", list(REGIONS))
def test_every_prepared_region_renders(region_key):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = region_key
    at.run()
    assert not at.exception


def test_desert_region_shows_no_snow_stamp():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "medina"
    at.run()
    markdown = " ".join(md.value for md in at.markdown)
    assert "stamp no_snow" in markdown


def test_possible_reasons_step_shows_reasons_and_local_context():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "beijing"
    at.run()
    at.button(key="open_no2").click().run()
    assert not at.exception
    markdown = " ".join(md.value for md in at.markdown)
    assert TEXT["en"]["step_reasons"].split("·")[-1].strip() in markdown
    assert any("2013" in info.value for info in at.info)


def test_reasons_cover_every_measurement_in_both_languages():
    from trend.i18n import REASONS, REGION_CONTEXT
    from trend.variables import VARIABLES

    for lang in ("en", "tr"):
        for key in VARIABLES:
            for direction in ("up", "down", "none"):
                assert REASONS[lang][key][direction], (lang, key, direction)
                assert len(REASONS[lang][key][direction]) == len(REASONS["en"][key][direction])
    assert {r: set(v) for r, v in REGION_CONTEXT["en"].items()} == {
        r: set(v) for r, v in REGION_CONTEXT["tr"].items()
    }
    assert set(REGION_CONTEXT["en"]) <= set(REGIONS)


def test_disputed_case_says_the_change_is_not_certain():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "beijing"
    at.run()
    at.button(key="open_snowfall").click().run()
    markdown = " ".join(md.value for md in at.markdown)
    assert "not certain" in markdown
    assert "The test shows that" not in markdown


def test_covid_reason_only_when_the_period_includes_2020():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "alps"
    at.run()
    at.button(key="open_no2").click().run()
    at.slider(key="period_no2").set_value((2005, 2019)).run()  # a significant fall before 2020
    markdown = " ".join(md.value for md in at.markdown)
    assert "economic slowdown" in markdown
    assert "COVID-19 lockdowns briefly" not in markdown
    at.slider(key="period_no2").set_value((2005, 2025)).run()  # the period includes 2020
    markdown = " ".join(md.value for md in at.markdown)
    assert "COVID-19 lockdowns briefly" in markdown


def test_co2_uses_its_short_record_with_a_note(monkeypatch):
    import numpy as np
    import pandas as pd

    import trend.fetch

    dates = pd.date_range("2015-01-01", "2022-02-01", freq="MS")
    values = 399 + 2.4 * (dates.year - 2015 + dates.month / 12) + np.random.default_rng(3).normal(0, 0.2, dates.size)
    real_loader = trend.fetch.load_processed

    def loader(region_key, variable_key):
        if variable_key == "co2":
            return pd.DataFrame({"date": dates, "value": values, "source": "synthetic"})
        return real_loader(region_key, variable_key)

    monkeypatch.setattr(trend.fetch, "load_processed", loader)
    monkeypatch.setattr(trend.fetch, "available_variable_keys", lambda region: ["air_temperature", "co2"])
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["region"] = "marmara"
    at.run()
    at.button(key="open_co2").click().run()
    assert not at.exception
    assert any("fewer than the usual 10" in info.value for info in at.info)


def test_quick_pick_a_city_sets_its_box_and_names_the_case(monkeypatch):
    import trend.fetch
    from trend.cities import city_bbox

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _synthetic_fetch)
    at = run_app("tr")
    at.radio(key="area_mode").set_value("custom").run()
    at.selectbox(key="city_pick").set_value("ankara").run()
    assert not at.exception
    assert tuple(at.session_state["custom_bbox"]) == city_bbox("ankara")
    assert _corner_inputs(at) == city_bbox("ankara")
    assert any("Ankara çevresi, Türkiye" in h.value for h in at.header)
    for key, value in zip(("bbox_w", "bbox_s", "bbox_e", "bbox_n"), (30.0, 36.0, 34.0, 39.0)):
        at.number_input(key=key).set_value(value)
    next(b for b in at.button if b.label == TEXT["tr"]["apply_coords"]).click().run()
    assert not at.exception and at.session_state["city_pick"] is None  # another box: no city shown


def _failing_fetch(variable, bbox, start_year, end_year, timeout=300, **kwargs):
    import requests

    raise requests.ConnectionError("no network")


def test_nasa_not_answering_offers_the_nearest_prepared_region(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _failing_fetch)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["lang"] = "tr"
    at.query_params["region"] = "custom"
    for key, value in zip("wsen", (32.11, 39.17, 33.61, 40.67)):  # around Ankara, a box no other test caches
        at.query_params[key] = str(value)
    at.run()
    assert not at.exception
    assert any("en yakın hazır bölge olan Konya Kapalı Havzası" in i.value for i in at.info)
    at.button(key="nearest_all").click().run()
    assert not at.exception
    assert at.session_state["area_mode"] == "prepared" and at.session_state["region"] == "konya"


def test_a_custom_area_inside_a_region_is_not_called_0_km_away(monkeypatch):
    import trend.fetch

    monkeypatch.setattr(trend.fetch, "fetch_power_area", _failing_fetch)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["lang"] = "en"
    at.query_params["region"] = "custom"
    for key, value in zip("wsen", (27.6, 40.4, 29.4, 41.6)):  # inside the Istanbul–Marmara box
        at.query_params[key] = str(value)
    at.run()
    assert not at.exception
    infos = " ".join(i.value for i in at.info)
    assert "lies in the prepared region Istanbul" in infos and "km" not in infos
