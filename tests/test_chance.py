"""Tests for "Can chance fool the detective?": pretend worlds without a trend (trend/chance.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import importlib.util
import re
import string
import time
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from trend.chance import (
    CHANCE_TEXT,
    DEFAULT_RUNS,
    MAX_PHI,
    chance_text,
    clip_phi,
    compare_line,
    example_figure,
    intro_line,
    naive_p_value,
    naive_significant,
    red_noise,
    simulate,
    summary_lines,
)
from trend.i18n import p_phrase
from trend.stats import analyze_trend

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("accuracy_report", ROOT / "scripts" / "accuracy_report.py")
accuracy_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accuracy_report)

# A finished simulation with round numbers, for the sentences
SAMPLE = {
    "runs": 200, "n": 45, "phi": 0.43, "naive": 37, "detective": 9, "naive_share": 0.185,
    "detective_share": 0.045, "example": None,
}


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


# --- The pretend worlds ----------------------------------------------------------------------------


@pytest.mark.parametrize("phi", [0.0, 0.5, 0.9])
def test_red_noise_is_the_recipe_of_the_accuracy_report(phi):
    ours = red_noise(np.random.default_rng(5), phi, 30)
    theirs = accuracy_report.red_noise(np.random.default_rng(5), phi, 30)
    np.testing.assert_array_equal(ours, theirs)


def test_red_noise_has_unit_sd_and_the_asked_persistence():
    x = red_noise(np.random.default_rng(1), 0.6, 20000)
    assert x.std() == pytest.approx(1.0, abs=0.05)
    assert np.corrcoef(x[:-1], x[1:])[0, 1] == pytest.approx(0.6, abs=0.03)


@pytest.mark.parametrize(
    "phi, expected",
    [(0.4, 0.4), (0.0, 0.0), (0.95, 0.95), (1.7, MAX_PHI), (-0.3, 0.0), (float("nan"), 0.0), (None, 0.0)],
)
def test_phi_is_clipped_to_zero_and_095(phi, expected):
    assert clip_phi(phi) == expected


def test_red_noise_clips_phi_too():
    def noise(phi):
        return red_noise(np.random.default_rng(3), phi, 40)

    assert np.isfinite(noise(1.7)).all()
    np.testing.assert_array_equal(noise(1.7), noise(MAX_PHI))
    np.testing.assert_array_equal(noise(-0.5), noise(0.0))
    np.testing.assert_array_equal(noise(float("nan")), noise(0.0))


def test_simulate_uses_the_clipped_phi_and_accepts_negative_or_nan():
    assert simulate(20, 1.7, runs=5, seed=1)["phi"] == MAX_PHI
    independent = simulate(20, 0.0, runs=5, seed=1)
    for phi in (-0.4, float("nan")):
        result = simulate(20, phi, runs=5, seed=1)
        assert result["phi"] == 0.0
        assert (result["naive"], result["detective"]) == (independent["naive"], independent["detective"])


def test_the_same_seed_gives_the_same_worlds():
    first = simulate(25, 0.5, runs=60, seed=7)
    second = simulate(25, 0.5, runs=60, seed=7)
    for key in ("runs", "n", "phi", "naive", "detective", "naive_share", "detective_share"):
        assert first[key] == second[key]
    assert first["example"] is not None
    np.testing.assert_array_equal(first["example"]["values"], second["example"]["values"])


def test_persistence_fools_the_naive_test_far_more_often_than_the_detective():
    result = simulate(25, 0.6, runs=400, seed=2026)
    assert (result["runs"], result["n"], result["phi"]) == (400, 25, 0.6)
    assert result["naive_share"] == result["naive"] / 400
    assert result["detective_share"] == result["detective"] / 400
    assert result["naive_share"] > result["detective_share"] + 0.03
    assert result["detective_share"] < 0.15


def test_independent_years_fool_both_tests_about_one_time_in_twenty():
    result = simulate(30, 0.0, runs=400, seed=11)
    assert 0.01 <= result["naive_share"] <= 0.10
    assert result["detective_share"] <= 0.08
    assert result["detective"] <= result["naive"]  # a Confirmed stamp needs the stricter test to pass


def test_the_example_fooled_the_naive_test_but_not_the_detective():
    example = simulate(25, 0.6, runs=200, seed=7)["example"]
    assert example is not None
    np.testing.assert_array_equal(example["years"], np.arange(2001, 2026))  # 2026 - n to 2025
    assert naive_significant(example["years"], example["values"])
    assert example["naive_p"] == pytest.approx(naive_p_value(example["years"], example["values"]))
    detective = analyze_trend(example["years"], example["values"])
    assert not (detective.significant and detective.agrees)
    assert example["detective_p"] == pytest.approx(detective.p_value)


def test_no_example_when_no_world_fooled_only_the_naive_test():
    result = simulate(25, 0.0, runs=1, seed=0)
    assert result["naive"] == 0
    assert result["example"] is None


def test_a_short_record_such_as_co2_can_be_simulated():
    result = simulate(7, 0.3, runs=20, seed=1)  # fewer years than analyze_trend's default minimum of 10
    assert result["n"] == 7
    assert 0 <= result["detective"] <= result["naive"] <= 20


def test_impossible_worlds_are_refused():
    with pytest.raises(ValueError):
        simulate(2, 0.3)
    with pytest.raises(ValueError):
        simulate(20, 0.3, runs=0)


def test_naive_test_on_a_flat_series_is_not_significant():
    assert naive_significant(np.arange(2000, 2020), np.ones(20)) is False


def test_four_hundred_worlds_of_45_years_are_quick():
    start = time.perf_counter()
    result = simulate(45, 0.5, seed=3)
    elapsed = time.perf_counter() - start
    assert result["runs"] == DEFAULT_RUNS == 400
    assert elapsed < 5.0  # about 1 s on a laptop; generous for CI


# --- The chart -------------------------------------------------------------------------------------


def test_example_figure_shows_the_world_and_the_naive_line():
    example = simulate(25, 0.6, runs=200, seed=7)["example"]
    fig = example_figure(example, "en")
    world, line = fig.data
    assert world.name == "Pretend world"
    assert line.name == f"Naive straight line ({p_phrase(example['naive_p'], 'en')})"
    assert (world.mode, line.mode) == ("lines+markers", "lines")
    assert (world.line.color, line.line.color) == ("#898781", "#a8501b")
    np.testing.assert_array_equal(world.x, example["years"])
    np.testing.assert_allclose(world.y, example["values"])
    np.testing.assert_allclose(np.diff(line.y, 2), 0, atol=1e-9)  # a straight line
    slope = (line.y[-1] - line.y[0]) / (line.x[-1] - line.x[0])
    assert slope == pytest.approx(stats.linregress(example["years"], example["values"]).slope)
    assert [shape.y0 for shape in fig.layout.shapes] == [0]  # the truth: flat at zero
    assert fig.layout.height == 240
    assert "A pretend world with no trend" in fig.layout.title.text
    assert "Detective: not confirmed" in fig.layout.title.text


def test_turkish_figure_uses_a_decimal_comma_and_escapes_less_than():
    years = np.arange(2001, 2026)
    values = 0.1 * (years - 2001) + np.sin(years)
    fig = example_figure({"years": years, "values": values, "naive_p": 0.0123}, "tr", separators=",.")
    assert fig.layout.separators == ",."
    assert fig.data[1].name == "Saf testin düz çizgisi (p = 0,012)"
    assert "Trendi olmayan hayali bir dünya" in fig.layout.title.text
    tiny = example_figure({"years": years, "values": values, "naive_p": 0.0001}, "en")
    assert tiny.data[1].name == "Naive straight line (p < 0.001)"
    assert "p &lt; 0.001" in tiny.data[1].hovertemplate
    assert tiny.data[1].hovertemplate.endswith("<extra></extra>")


# --- The texts -------------------------------------------------------------------------------------


def test_english_and_turkish_have_the_same_texts_and_placeholders():
    assert set(CHANCE_TEXT["en"]) == set(CHANCE_TEXT["tr"])
    for key, text in CHANCE_TEXT["en"].items():
        assert placeholders(text) == placeholders(CHANCE_TEXT["tr"][key]), key
    assert chance_text("en", "title") == "🎲 Can chance fool the detective?"
    assert chance_text("tr", "title") == "🎲 Tesadüf dedektifi kandırabilir mi?"
    assert chance_text("en", "button", runs=200) == "Make 200 worlds without a trend"
    assert chance_text("tr", "button", runs=200) == "Trendi olmayan 200 dünya üret"
    assert chance_text("de", "title") == chance_text("en", "title")  # unknown language: English


def test_summary_lines_in_english():
    assert summary_lines("en", SAMPLE, 0.0004) == [
        "A naive test (no correction for persistence) saw a trend in **37 of 200** worlds (18.5%).",
        "The detective stamped “Confirmed” in **9** (4.5%).",
        "The real case has p < 0.001: chance alone rarely produces evidence this strong.",
    ]


def test_summary_lines_in_turkish_use_decimal_commas():
    lines = summary_lines("tr", SAMPLE, 0.0234)
    text = " ".join(lines)
    assert len(lines) == 3
    assert "(%18,5)" in text and "(%4,5)" in text and "p = 0,023" in text
    assert "“Doğrulandı”" in text
    assert not re.search(r"\d\.\d", text)


def test_whole_percentages_have_no_decimals():
    lines = summary_lines("en", dict(SAMPLE, naive=40, detective=10), None)
    assert "(20%)" in lines[0] and "(5%)" in lines[1]


@pytest.mark.parametrize(
    "p, key",
    [
        (0.0004, "compare_strong"), (0.0099, "compare_strong"), (0.01, "compare_middle"),
        (0.03, "compare_middle"), (0.05, "compare_chance"), (0.4, "compare_chance"),
    ],
)
def test_the_real_case_is_compared_in_three_wordings(p, key):
    for lang in ("en", "tr"):
        assert compare_line(lang, p) == chance_text(lang, key, p=p_phrase(p, lang))


def test_no_comparison_without_a_case_p_value():
    assert len(summary_lines("en", SAMPLE, None)) == 2
    assert len(summary_lines("tr", SAMPLE, float("nan"))) == 2


def test_intro_shows_the_persistence_used():
    english = intro_line("en", 200, 45, 0.432)
    assert "200 pretend worlds" in english and "45 years" in english
    assert "“sticky”" in english and "lag-1 autocorrelation 0.43" in english
    assert "gecikme-1 otokorelasyonu 0,43" in intro_line("tr", 200, 45, 0.432)
    assert "lag-1 autocorrelation 0.95" in intro_line("en", 200, 30, 0.99)  # clipped


def test_intro_for_years_that_are_not_alike():
    english = intro_line("en", 200, 7, -0.2)
    assert "independent" in english and "-0.20" in english and "sticky" not in english
    assert "bağımsız" in intro_line("tr", 200, 7, -0.2) and "-0,20" in intro_line("tr", 200, 7, -0.2)
    assert "0,00" in intro_line("tr", 200, 20, float("nan"))
