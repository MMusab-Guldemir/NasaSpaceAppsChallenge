"""Smoke tests: the Streamlit app renders every cached variable without errors.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from trend.fetch import available_variable_keys

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.mark.parametrize("variable_key", available_variable_keys("colorado"))
def test_app_renders_each_cached_variable(variable_key):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at.selectbox[1].select(variable_key).run()
    assert not at.exception
    assert any("per decade" in md.value for md in at.markdown)


def test_short_period_is_blocked_with_a_message():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.slider[0].set_value((2015, 2020)).run()
    assert not at.exception
    assert any("at least 10 complete years" in err.value for err in at.error)
