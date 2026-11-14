"""Tests for the record check and the year stripes (trend/records.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd

from trend.fetch import load_processed
from trend.records import (
    RECORD_TEXT,
    stripe_positions,
    last_year_rank,
    record_sentence,
    stripes_caption,
    stripes_figure,
)
from trend.stats import to_annual
from trend.variables import VARIABLES


def _annual(values, first=2001):
    return pd.DataFrame({"year": range(first, first + len(values)), "value": values})


def test_rank_from_both_ends_with_ties_sharing_the_record():
    info = last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10]))
    assert info["high"] == 1 and info["low"] == 10 and info["n"] == 11
    assert info["start"] == 2001 and info["end"] == 2011
    assert last_year_rank(_annual([1, 2, 3])) is None  # too few years


def test_sentences_in_both_languages():
    warm = last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12]))
    assert record_sentence("en", warm, "air_temperature") == "📌 2011 is the warmest of 11 years (2001–2011)."
    assert record_sentence("tr", warm, "air_temperature") == "📌 2011, 11 yılın en sıcak yılı (2001–2011)."
    dry = last_year_rank(_annual([5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 5.5]))
    assert record_sentence("en", dry, "precipitation") == "📌 2011 is the 2nd driest of 11 years (2001–2011)."
    assert record_sentence("tr", dry, "precipitation") == "📌 2011, 11 yılın en kurak 2. yılı (2001–2011)."
    assert record_sentence("en", warm, "no2") == "📌 2011 had the highest value of the 11 years (2001–2011)."
    second = last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 10]))
    assert record_sentence("en", second, "hot_days") == "📌 2011 had the 2nd most hot days of the 11 years (2001–2011)."
    assert record_sentence("tr", second, "hot_days") == (
        "📌 2011, 11 yıl içinde en çok sıcak gün görülen 2. yıl (2001–2011)."
    )
    low = last_year_rank(_annual([5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 4]))
    assert record_sentence("tr", low, "groundwater") == (
        "📌 2011, 11 yıl içinde yeraltı suyunun en az olduğu yıl (2001–2011)."
    )


def test_no_sentence_for_a_middle_year_or_a_flat_record():
    middle = last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 5.5]))
    assert record_sentence("en", middle, "air_temperature") is None
    flat = last_year_rank(_annual([4.0] * 12))
    assert record_sentence("en", flat, "air_temperature") is None
    assert record_sentence("en", None, "air_temperature") is None
    many_zero = last_year_rank(_annual([0, 0, 0, 0, 5, 6, 7, 8, 9, 10, 0]))  # snow in a few years only
    assert record_sentence("en", many_zero, "snowfall") is None
    hazy = last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12], first=2013))  # 2023: after VIIRS
    assert record_sentence("en", hazy, "aod") is None
    assert record_sentence("en", last_year_rank(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12], first=2010)), "aod")


def test_real_konya_hot_days_and_rain():
    hot, _ = to_annual(load_processed("konya", "hot_days"), VARIABLES["hot_days"])
    sentence = record_sentence("en", last_year_rank(hot), "hot_days")
    assert sentence is not None and sentence.startswith("📌 2025") and "hot days" in sentence
    rain, _ = to_annual(load_processed("konya", "precipitation"), VARIABLES["precipitation"])
    assert record_sentence("tr", last_year_rank(rain), "precipitation") == "📌 2025, 45 yılın en kurak 3. yılı (1981–2025)."


def test_stripes_figure_and_caption():
    figure = stripes_figure(_annual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), "precipitation", "mm", ",.", 1)
    heat = figure.data[0]
    assert list(heat.x) == list(range(2001, 2011)) and len(heat.z[0]) == 10
    assert heat.colorscale[0][1] == "#8c5a2b"  # water: brown for the lowest years
    assert figure.layout.separators == ",." and figure.layout.height == 70
    assert min(heat.z[0]) == -1 and max(heat.z[0]) == 1  # both ends of the colour scale are reached
    flat = stripes_figure(_annual([3.0] * 10), "air_temperature", "°C")
    assert set(flat.data[0].z[0]) == {0.0}  # a flat series: every stripe the neutral middle colour


def test_a_missing_year_stays_an_empty_slot_and_skewed_records_reach_both_colours():
    gappy = pd.DataFrame({"year": [2001, 2002, 2004, 2005], "value": [1.0, 2.0, 4.0, 5.0]})
    heat = stripes_figure(gappy, "air_temperature", "°C").data[0]
    assert list(heat.x) == [2001, 2002, 2003, 2004, 2005]
    assert heat.z[0][2] is None or np.isnan(heat.z[0][2])  # 2003 was not used: an empty slot
    assert "empty slot" in stripes_caption("en", "air_temperature", gappy)
    assert "empty slot" not in stripes_caption("en", "air_temperature", _annual([1, 2, 3]))
    skewed = stripe_positions(np.array([1.0, 1.0, 1.2, 1.1, 1.0, 9.0]))
    assert skewed.min() == -1 and skewed.max() == 1
    assert "kahverengi" in stripes_caption("tr", "precipitation") and "red" in stripes_caption("en", "air_temperature")
    for key in RECORD_TEXT["en"]:
        assert key in RECORD_TEXT["tr"]
