"""Smoke tests: the board and every case file render without errors.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from trend.fetch import available_variable_keys

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_board_and_default_case_render():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("Investigation board" in h.value for h in at.subheader)
    assert any("per decade" in md.value for md in at.markdown)


@pytest.mark.parametrize("variable_key", available_variable_keys("colorado"))
def test_each_case_file_opens(variable_key):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button(key=f"open_{variable_key}").click().run()
    assert not at.exception
    assert at.session_state["case"] == variable_key
    assert any("The verdict" in md.value for md in at.markdown)


def test_short_period_is_blocked_with_a_message():
    at = AppTest.from_file(APP, default_timeout=60).run()
    case = at.session_state["case"]
    at.slider(key=f"period_{case}").set_value((2015, 2020)).run()
    assert not at.exception
    assert any("at least 10 complete years" in err.value for err in at.error)
