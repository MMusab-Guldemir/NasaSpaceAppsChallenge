"""Tests for the "Not a straight line" note (trend/linecheck.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pytest

from trend.fetch import load_processed
from trend.linecheck import LINE_TEXT, curvature_p_value, line_check, line_text
from trend.stats import analyze_trend
from trend.world import board_verdict


def check_series(years, values):
    return line_check(years, values, analyze_trend(years, values))


def test_exponential_decay_is_curved_and_gets_the_note():
    # Shaped like NO2 in Los Angeles: a fast fall that slows down (its curve's lowest point lies
    # outside the middle of the period, so it does not "turn around").
    years = np.arange(2005, 2025)
    rng = np.random.default_rng(0)
    values = 3 + 4 * np.exp(-(years - 2005) / 8) + rng.normal(scale=0.1, size=years.size)
    result = analyze_trend(years, values)
    check = line_check(years, values, result)
    assert check.curved and check.plain_mk_p < 0.001
    assert not result.significant and result.n_effective < 6
    assert check.show


def test_noisy_straight_line_is_not_curved():
    years = np.arange(1990, 2020)
    rng = np.random.default_rng(1)
    values = 0.05 * (years - 1990) + rng.normal(scale=0.3, size=years.size)
    check = check_series(years, values)
    assert not check.curved and not check.show


def test_curvature_test_rarely_flags_straight_lines():
    years = np.arange(1990, 2020)
    flagged = 0
    for seed in range(400):
        rng = np.random.default_rng(seed)
        values = 0.05 * (years - 1990) + rng.normal(scale=0.3, size=years.size)
        flagged += curvature_p_value(years, values) < 0.05
    assert 0.02 <= flagged / 400 <= 0.09  # about 5% at alpha = 0.05


def test_exact_lines_and_curves():
    years = np.arange(1990, 2020)
    assert curvature_p_value(years, 2.0 * years + 1) == 1.0
    assert curvature_p_value(years, (years - 2000.0) ** 2) == 0.0
    assert curvature_p_value(years[:5], (years[:5] - 1990.0) ** 2) == 1.0  # fewer than 6 years


def test_los_angeles_no2_gets_the_note():
    verdict = board_verdict(load_processed("los_angeles", "no2"), "no2")
    result = verdict.result
    assert result.p_value == pytest.approx(0.258, abs=0.001)
    assert result.n_effective == pytest.approx(2.0)
    check = line_check(verdict.annual["year"], verdict.annual["value"], result)
    assert check.show and check.curved and check.plain_mk_p < 0.001


def test_istanbul_air_temperature_gets_no_note():
    verdict = board_verdict(load_processed("marmara", "air_temperature"), "air_temperature")
    check = line_check(verdict.annual["year"], verdict.annual["value"], verdict.result)
    assert verdict.result.significant and not check.show


def test_curved_series_without_a_one_way_movement_gets_no_note():
    # Los Angeles aerosols: flat for twenty years, then a late rise. Curved, but not one-way, so the
    # note's "mostly move one way" would not be true.
    verdict = board_verdict(load_processed("los_angeles", "aod"), "aod")
    check = line_check(verdict.annual["year"], verdict.annual["value"], verdict.result)
    assert check.curved and check.plain_mk_p > 0.05
    assert not verdict.result.significant and verdict.result.n_effective < 6
    assert not check.show


def test_constant_and_short_series_do_not_raise():
    years = np.arange(2000, 2020)
    check = check_series(years, np.full(years.size, 5.0))
    assert not check.curved and check.plain_mk_p == 1.0 and not check.show
    years_with_gap = np.array([2000.0, 2001.0, np.nan, 2003.0])
    values = np.array([1.0, 2.0, 3.0, np.nan])
    assert curvature_p_value(years_with_gap, values) == 1.0
    with pytest.raises(ValueError):
        curvature_p_value([2000, 2001], [1.0])


def test_note_texts():
    assert set(LINE_TEXT["tr"]) == set(LINE_TEXT["en"])
    english = line_text("en", "p < 0.001", "2")
    assert "(Mann-Kendall without the persistence correction, p < 0.001)" in english
    assert "about 2 independent years" in english
    turkish = line_text("tr", "p < 0,001", "2")
    assert "(süreklilik düzeltmesi yapılmamış Mann-Kendall, p < 0,001)" in turkish
    assert "yaklaşık 2 bağımsız yıl" in turkish
    assert line_text("de", "p = 0.002", "4") == line_text("en", "p = 0.002", "4")


def test_a_series_that_turns_around_is_left_to_the_why_box():
    # Colorado NO2 shape: falls to 2020, then climbs back. The "why is it not verified?" box explains a
    # turn, so the note (which says the values mostly move one way) steps aside.
    years = np.arange(2005, 2026)
    values = np.array([1.09, 1.10, 1.01, 0.99, 0.92, 0.93, 0.94, 1.02, 0.98, 0.89, 0.84, 0.87, 0.90,
                       0.87, 0.82, 0.73, 0.81, 0.87, 0.89, 0.95, 1.01])
    result = analyze_trend(years, values)
    assert not result.significant
    assert not line_check(years, values, result).show
