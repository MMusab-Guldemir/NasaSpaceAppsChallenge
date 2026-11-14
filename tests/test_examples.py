"""Tests for the famous cases (trend/examples.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.examples import (
    EXAMPLES,
    EXPECTED_ANSWERS,
    Example,
    check_example,
    example_key,
    example_label,
    examples_title,
)
from trend.fetch import processed_path
from trend.regions import REGIONS
from trend.variables import VARIABLES


def test_every_example_has_its_prepared_file():
    for example in EXAMPLES:
        assert example.region in REGIONS and example.case in VARIABLES
        assert processed_path(example.region, example.case).exists(), example_key(example)


@pytest.mark.parametrize("example", EXAMPLES, ids=example_key)
def test_each_question_matches_the_real_data(example):
    assert check_example(example) == example.expect


def test_keys_are_unique_and_labels_exist_in_both_languages():
    keys = [example_key(example) for example in EXAMPLES]
    assert len(set(keys)) == len(keys) == 6
    for example in EXAMPLES:
        assert example.expect in EXPECTED_ANSWERS
        assert example.label["en"].strip() and example.label["tr"].strip()
        assert example.label["en"] != example.label["tr"]
        assert example_label(example, "tr") == example.label["tr"]
        assert example_label(example, "de") == example.label["en"]  # unknown language: English
    assert examples_title("en") and examples_title("tr") and examples_title("en") != examples_title("tr")


def _synthetic(region_key, variable_key):
    """Flat until 2000, then rising, for "colorado"; falling all along for "amazon"."""
    dates = pd.date_range("1981-01-01", "2020-12-01", freq="MS")
    noise = 0.05 * np.random.default_rng(1).normal(size=len(dates))
    if region_key == "colorado":
        change = np.where(dates.year > 2000, 0.1 * (dates.year - 2000), 0.0)
    else:
        change = -0.05 * (dates.year - 1981)
    return pd.DataFrame({"date": dates, "value": 10 + change + noise})


def _example(region, start=None, end=None):
    return Example(region, "air_temperature", start, end, {"en": "?", "tr": "?"}, "none")


def test_check_example_uses_the_period_and_the_confirmed_stamp():
    assert check_example(_example("colorado", 1981, 2000), _synthetic) == "none"  # the flat years
    assert check_example(_example("colorado", 2001, 2020), _synthetic) == "up"  # the rising years
    assert check_example(_example("amazon"), _synthetic) == "down"  # full record


def test_check_example_reports_missing_data_and_too_short_periods():
    with pytest.raises(ValueError):
        check_example(_example("colorado"), lambda region_key, variable_key: None)
    with pytest.raises(ValueError):
        check_example(_example("colorado", 2015, 2020), _synthetic)  # 6 years, 10 needed
