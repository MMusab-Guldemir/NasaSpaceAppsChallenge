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
