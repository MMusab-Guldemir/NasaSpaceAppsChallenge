"""Tests for the evidence timeline and the start-year check (trend/timeline.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd

from trend.timeline import (
    earlier_significant_years,
    evidence_timeline,
    solid_since,
    start_year_check,
    timeline_figure,
    timeline_text,
    year_ranges,
)


def series(values, first=1981):
    return pd.DataFrame({"year": np.arange(first, first + len(values)), "value": np.asarray(values, dtype=float)})


def test_strong_trend_is_solid_early_and_robust_to_the_start_year():
    rng = np.random.default_rng(1)
    annual = series(0.5 * np.arange(40) + rng.normal(scale=0.5, size=40))
    timeline = evidence_timeline(annual, 10)
    assert len(timeline) == 31 and timeline["end_year"].iloc[-1] == 2020
    assert solid_since(timeline) <= 1991
    check = start_year_check(annual, 10)
    assert check["status"] == "confirmed" and check["same"] == check["n"] == 31


def test_pure_noise_is_not_solid():
    rng = np.random.default_rng(7)
    annual = series(rng.normal(size=30))
    timeline = evidence_timeline(annual, 10)
    if not timeline["significant"].iloc[-1]:
        assert solid_since(timeline) is None


def test_evidence_that_went_back_and_forth_is_reported():
    values = list(np.arange(15) * 1.0) + [14 - 1.5 * k for k in range(15)]  # up, then down again
    timeline = evidence_timeline(series(values), 10)
    assert not timeline["significant"].iloc[-1]
    assert earlier_significant_years(timeline)


def test_start_year_check_needs_three_options():
    assert start_year_check(series(np.arange(11)), 10) is None


def test_year_ranges_and_texts():
    assert year_ranges([2005, 2006, 2007, 2010]) == "2005–2007, 2010"
    assert year_ranges([]) == ""
    assert "2009" in timeline_text("tr", "solid_since", year=2009, direction="artış")


def test_figure_uses_a_log_axis_with_the_five_percent_line():
    timeline = evidence_timeline(series(np.arange(20) + np.sin(np.arange(20))), 10)
    figure = timeline_figure(timeline, "en", 1981)
    assert figure.layout.yaxis.type == "log"
    assert any(shape.y0 == 0.05 for shape in figure.layout.shapes)
