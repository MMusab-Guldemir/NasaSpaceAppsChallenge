"""Tests for the guided start (trend/guide.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from dataclasses import fields

import numpy as np
import pandas as pd
import pytest

from trend.examples import Example
from trend.fetch import available_variable_keys, load_processed, processed_path
from trend.guide import (
    GUIDE_TEXT,
    MAX_SUGGESTIONS,
    PERIODS,
    PLACE_CASES,
    PLACES,
    TOPIC_CASES,
    TOPICS,
    Suggestion,
    guide_text,
    place_label,
    suggest,
    suggestion_key,
    suggestion_label,
    topic_cases,
    topic_label,
)
from trend.regions import REGIONS
from trend.variables import VARIABLES
from trend.world import TESTED, board_verdict

PAIRS = [(topic, place) for topic in TOPICS for place in PLACES]


def _verdict_phrases(lang: str, status: str) -> list[str]:
    if status == "noevidence":
        return [guide_text(lang, "verdict_noevidence")]
    return [guide_text(lang, f"verdict_{status}_{direction}") for direction in ("up", "down")]


@pytest.mark.parametrize(("topic", "place"), PAIRS, ids=[f"{topic}-{place}" for topic, place in PAIRS])
def test_every_pair_offers_only_prepared_testable_cases(topic, place):
    found = suggest(topic, place)  # the real prepared files
    assert isinstance(found, list) and len(found) <= MAX_SUGGESTIONS
    keys = [suggestion_key(suggestion) for suggestion in found]
    assert len(set(keys)) == len(keys)  # unique widget keys within a result
    for suggestion in found:
        assert suggestion.region in PLACES[place].regions
        assert suggestion.case in available_variable_keys(suggestion.region)
        assert processed_path(suggestion.region, suggestion.case).exists()
        assert suggestion.status in TESTED
        for lang in ("en", "tr"):
            label = suggestion_label(suggestion, lang)
            assert label.strip()
            assert any(label.endswith(" — " + phrase) for phrase in _verdict_phrases(lang, suggestion.status))
        assert suggestion.label["en"] != suggestion.label["tr"]
        if suggestion.start is None:  # full record: the same stamp as on the World board
            monthly = load_processed(suggestion.region, suggestion.case)
            assert board_verdict(monthly, suggestion.case).status == suggestion.status


def test_heat_in_a_big_city_starts_with_istanbul_hot_days():
    first = suggest("heat", "city")[0]
    assert (first.region, first.case, first.start, first.end) == ("marmara", "hot_days", None, None)
    assert first.status == "confirmed"
    assert first.label == {
        "en": "Istanbul: hot days above 30 °C — Confirmed rise",
        "tr": "İstanbul: 30 °C üstü sıcak günler — Doğrulanmış artış",
    }
    assert suggestion_key(first) == "guide_marmara_hot_days"


def test_air_in_a_big_city_offers_beijing_no2_since_2013():
    beijing = [s for s in suggest("air", "city") if (s.region, s.case) == ("beijing", "no2")]
    assert len(beijing) == 1
    case = beijing[0]
    assert (case.start, case.end) == (2013, 2025) == PERIODS[("beijing", "no2")]
    assert case.status == "confirmed"  # the same answer as the famous case in trend/examples.py
    assert case.label["en"] == "Beijing: air pollution (NO₂), 2013–2025 — Confirmed fall"
    assert case.label["tr"] == "Pekin: hava kirliliği (NO₂), 2013–2025 — Doğrulanmış azalış"


def test_texts_exist_in_both_languages():
    assert GUIDE_TEXT["en"].keys() == GUIDE_TEXT["tr"].keys()
    expected = {
        "title": (
            "🧭 Not sure where to start? Answer two questions",
            "🧭 Nereden başlayacağını bilmiyor musun? İki soruyu cevapla",
        ),
        "q_topic": ("What are you curious about?", "Neyi merak ediyorsun?"),
        "q_place": ("What kind of place?", "Nasıl bir yer?"),
        "open": ("Open this case", "Bu dosyayı aç"),
    }
    for key, (english, turkish) in expected.items():
        assert guide_text("en", key) == english and guide_text("tr", key) == turkish
    assert guide_text("en", "none") == "No prepared case for this pair yet; try another place."
    for key in GUIDE_TEXT["en"]:
        if not key.startswith("label"):
            assert guide_text("tr", key).strip() and guide_text("tr", key) != guide_text("en", key), key
    assert guide_text("de", "open") == "Open this case"  # unknown language: English
    for key in VARIABLES:  # every measurement has a name, in case the rules change
        assert guide_text("en", f"case_{key}") and guide_text("tr", f"case_{key}")
    for status in ("confirmed", "disputed", "weak"):
        for direction in ("up", "down"):
            assert guide_text("tr", f"verdict_{status}_{direction}")


def test_answers_start_with_the_same_emoji_in_both_languages():
    for key in TOPICS:
        english, turkish = topic_label("en", key), topic_label("tr", key)
        assert english != turkish and english.split()[0] == turkish.split()[0]
        assert not english.split()[0].isalpha()  # emoji first
    for key, place in PLACES.items():
        english, turkish = place_label("en", key), place_label("tr", key)
        assert english != turkish and english.split()[0] == turkish.split()[0]
        assert not english.split()[0].isalpha()
        assert place.regions and all(region in REGIONS for region in place.regions)
    assert topic_label("de", "heat") == "🌡️ Heat" and place_label("de", "city") == "🏙️ Big city"


def test_rules_name_known_measurements_and_unknown_answers_fail_clearly():
    assert set(TOPIC_CASES) == set(TOPICS)
    assert all(topic in TOPICS and place in PLACES for topic, place in PLACE_CASES)
    for topic, place in PAIRS:
        slots = topic_cases(topic, place)
        assert slots and all(case in VARIABLES for slot in slots for case in slot)
    assert topic_cases("water", "mountains")[0] == ("snowfall",)
    assert topic_cases("air", "delta")[0][0] == "aod"
    with pytest.raises(KeyError):
        suggest("noise", "city")
    with pytest.raises(KeyError):
        suggest("heat", "moon")


def test_suggestion_text_key_and_the_fields_that_open_a_case():
    suggestion = Suggestion("alps", "snowfall", None, None, {"en": "A", "tr": "B"}, "noevidence")
    assert suggestion_label(suggestion, "tr") == "B" and suggestion_label(suggestion, "de") == "A"
    assert suggestion_key(suggestion) == "guide_alps_snowfall"
    assert isinstance(hash(suggestion), int)  # frozen and hashable despite the label dict
    # The app opens a suggestion like a famous case: the same region, case, start and end fields.
    opening = {"region", "case", "start", "end"}
    assert opening <= {f.name for f in fields(Suggestion)} and opening <= {f.name for f in fields(Example)}


# --- The rules on made-up records ----------------------------------------------------------------


def _monthly(start_year: int = 1981, years: int = 30, step: float = 0.05, base: float = 10.0,
             noise: float = 0.01, seed: int = 0) -> pd.DataFrame:
    """Monthly values with a steady yearly change and a little noise."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(f"{start_year}-01-01", periods=12 * years, freq="MS")
    values = base + step * (dates.year - start_year) + noise * rng.normal(size=len(dates))
    return pd.DataFrame({"date": dates, "value": values})


def _flat(start_year: int = 1981, years: int = 30) -> pd.DataFrame:
    return _monthly(start_year, years, step=0.0, noise=0.0)  # constant: always No evidence


def _never(start_year: int = 1981, years: int = 30) -> pd.DataFrame:
    return _monthly(start_year, years, step=0.0, base=0.0, noise=0.0)  # never snows, never that hot


def _world(records: dict):
    """A loader and a file list for made-up prepared records {(region, case): monthly}."""
    def loader(region_key, variable_key):
        return records.get((region_key, variable_key))

    def available(region_key):
        return sorted(case for region, case in records if region == region_key)

    return loader, available


def test_heat_falls_back_to_air_temperature_where_it_is_never_that_hot():
    loader, available = _world({("siberia", "hot_days"): _never(), ("siberia", "air_temperature"): _monthly()})
    found = suggest("heat", "north", loader, available)
    assert [(s.region, s.case) for s in found] == [("siberia", "air_temperature")]
    assert found[0].label == {
        "en": "Siberia: air temperature — Confirmed rise",
        "tr": "Sibirya: hava sıcaklığı — Doğrulanmış artış",
    }
    loader, available = _world({("siberia", "hot_days"): _monthly(), ("siberia", "air_temperature"): _monthly()})
    # both: a place can warm without getting more days above 30 °C
    assert [s.case for s in suggest("heat", "north", loader, available)] == ["hot_days", "air_temperature"]


def test_mountains_put_snowfall_before_precipitation_and_skip_snowless_places():
    loader, available = _world({
        ("alps", "snowfall"): _flat(),
        ("colorado", "snowfall"): _monthly(),
        ("alps", "precipitation"): _monthly(),
        ("colorado", "precipitation"): _monthly(step=-0.05),
    })
    found = suggest("water", "mountains", loader, available)
    assert [(s.region, s.case) for s in found] == [
        ("colorado", "snowfall"),  # a confirmed trend before no evidence
        ("alps", "snowfall"),
        ("alps", "precipitation"),  # the fourth case does not fit: at most three
    ]
    loader, available = _world({("siberia", "snowfall"): _never(), ("siberia", "precipitation"): _monthly()})
    assert [s.case for s in suggest("water", "north", loader, available)] == ["precipitation"]
    loader, available = _world({("marmara", "snowfall"): _monthly(), ("marmara", "precipitation"): _flat()})
    assert [s.case for s in suggest("water", "city", loader, available)] == ["precipitation"]


def test_air_uses_aerosols_in_deserts_and_carbon_monoxide_when_no2_is_missing():
    loader, available = _world({
        ("medina", "no2"): _monthly(2005, 21),
        ("medina", "aod"): _monthly(2001, 25, step=-0.05),
        ("cairo_nile", "co"): _monthly(2002, 23),
    })
    found = suggest("air", "desert", loader, available)
    assert [(s.region, s.case) for s in found] == [("medina", "aod"), ("cairo_nile", "co")]
    assert found[0].label["en"] == "Medina: dust and smoke (aerosols) — Confirmed fall"
    loader, available = _world({
        ("marmara", "no2"): _monthly(2020, 5),  # 5 years: too short to test
        ("marmara", "co"): _monthly(2002, 23),
        ("los_angeles", "no2"): _flat(2005, 21),
        ("los_angeles", "co"): _monthly(2002, 23),
    })
    found = suggest("air", "city", loader, available)
    assert [(s.region, s.case) for s in found] == [("marmara", "co"), ("los_angeles", "no2")]


def test_beijing_no2_is_judged_over_its_clean_air_years():
    dates = pd.date_range("2005-01-01", "2025-12-01", freq="MS")
    year = dates.year
    values = np.where(year <= 2012, 10 + 0.5 * (year - 2005), 13.5 - 0.5 * (year - 2012))  # up, then down
    noise = 0.01 * np.random.default_rng(3).normal(size=len(dates))
    no2 = pd.DataFrame({"date": dates, "value": values + noise})
    loader, available = _world({("beijing", "no2"): no2})
    found = suggest("air", "city", loader, available)
    assert [(s.start, s.end, s.status) for s in found] == [(2013, 2025, "confirmed")]
    assert found[0].label["en"] == "Beijing: air pollution (NO₂), 2013–2025 — Confirmed fall"
    assert found[0].label["tr"] == "Pekin: hava kirliliği (NO₂), 2013–2025 — Doğrulanmış azalış"
    # A record that ends in 2016 leaves only 4 years after 2013: the full record is offered instead.
    loader, available = _world({("beijing", "no2"): no2[no2["date"].dt.year <= 2016]})
    found = suggest("air", "city", loader, available)
    assert [(s.start, s.end) for s in found] == [(None, None)] and "2013" not in found[0].label["en"]


def test_rain_forest_adds_tree_cover_only_when_its_file_exists():
    records = {("amazon", "ndvi"): _monthly(2000, 26, step=-0.05)}
    loader, available = _world(records)
    assert [s.case for s in suggest("green", "forest", loader, available)] == ["ndvi"]
    records[("amazon", "tree_cover")] = _monthly(2000, 25, step=-0.05)
    loader, available = _world(records)
    assert [s.case for s in suggest("green", "forest", loader, available)] == ["ndvi", "tree_cover"]
    # A record the loader knows but without a prepared file is not offered.
    assert [s.case for s in suggest("green", "forest", loader, lambda region: ["ndvi"])] == ["ndvi"]


def test_records_too_short_to_test_are_never_offered():
    loader, available = _world({("amazon", "co2"): _monthly(2019, 3)})  # 3 years, 7 needed
    assert suggest("carbon", "forest", loader, available) == []


def test_confirmed_cases_come_first_and_every_stamp_is_in_words():
    loader, available = _world({
        ("marmara", "hot_days"): _flat(),
        ("beijing", "hot_days"): _monthly(),
        ("los_angeles", "hot_days"): _monthly(step=-0.05),
    })
    found = suggest("heat", "city", loader, available)
    assert [s.region for s in found] == ["beijing", "los_angeles", "marmara"]
    assert [s.status for s in found] == ["confirmed", "confirmed", "noevidence"]
    assert [s.label["en"].split(" — ")[1] for s in found] == [
        "Confirmed rise", "Confirmed fall", "No evidence of a trend",
    ]
    assert [s.label["tr"].split(" — ")[1] for s in found] == [
        "Doğrulanmış artış", "Doğrulanmış azalış", "Trende dair delil yok",
    ]
