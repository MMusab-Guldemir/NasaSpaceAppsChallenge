"""Tests for shareable links and restoring them in the app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from streamlit.testing.v1 import AppTest

from trend.share import build_share_link, parse_period

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_build_share_link_contains_the_whole_state():
    link = build_share_link("tr", "colorado", "no2", 2005, 2019)
    query = parse_qs(urlparse(link).query)
    assert link.startswith("https://avni-trend-detective.streamlit.app/?")
    assert query == {
        "lang": ["tr"], "region": ["colorado"], "case": ["no2"], "start": ["2005"], "end": ["2019"],
    }


def test_parse_period_clamps_and_orders_years():
    assert parse_period("1990", "2010", 1981, 2025) == (1990, 2010)
    assert parse_period("1900", "2100", 1981, 2025) == (1981, 2025)
    assert parse_period("2010", "1990", 1981, 2025) == (1990, 2010)
    assert parse_period("abc", "2010", 1981, 2025) is None
    assert parse_period(None, None, 1981, 2025) is None


def test_app_restores_a_shared_case_and_period():
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["lang"] = "tr"
    at.query_params["case"] = "no2"
    at.query_params["start"] = "2005"
    at.query_params["end"] = "2019"
    at.run()
    assert not at.exception
    assert at.session_state["lang"] == "tr"
    assert at.session_state["case"] == "no2"
    assert at.slider(key="period_no2").value == (2005, 2019)
