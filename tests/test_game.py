"""Tests for the Detective exam game: fair cases, answers that match the app, and the app view.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import json
import math
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from trend.fetch import load_processed
from trend.game import (
    GAME_TEXT, MODES, RANK_THRESHOLDS, SPECIAL_CASES, VIEW_LABELS, WHY, WHY_FOR, WHY_SOURCES,
    _note_fits, build_cases, render_game_html,
)
from trend.i18n import reasons, region_context, region_name
from trend.regions import REGIONS
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(scope="module")
def cases_en():
    return build_cases("en")


@pytest.fixture(scope="module")
def cases_tr():
    return build_cases("tr")


def test_every_answer_type_and_a_big_case_exist(cases_en):
    assert {"up", "down", "chance"} <= {c["truth"] for c in cases_en}
    assert any(c["boss"] for c in cases_en)


def test_pool_is_big_enough_for_a_full_exam_without_repeating_a_place(cases_en):
    regular = [c for c in cases_en if not c["boss"]]
    distinct = {truth: {c["series"] for c in regular if c["truth"] == truth} for truth in ("up", "down", "chance")}
    need = MODES["full"]["cases"] - 1
    assert len(distinct["up"]) >= round(need * 0.35)
    assert len(distinct["down"]) >= round(need * 0.25)
    assert len(distinct["chance"]) >= need - round(need * 0.35) - round(need * 0.25)
    assert len({c["series"] for c in regular}) >= need


def test_every_prepared_region_takes_part(cases_en):
    assert {c["series"].split("-")[0] for c in cases_en} == set(REGIONS)


def test_case_ids_are_unique(cases_en):
    ids = [c["id"] for c in cases_en]
    assert len(ids) == len(set(ids))


def test_answers_match_the_app_statistics(cases_en):
    for case in cases_en:
        region, variable = case["series"].split("-")
        annual, _ = to_annual(load_processed(region, variable), VARIABLES[variable])
        sub = annual[annual["year"].between(case["years"][0], case["years"][-1])]
        result = analyze_trend(sub["year"], sub["value"])
        expected = ("up" if result.slope_per_year > 0 else "down") if result.significant else "chance"
        assert case["truth"] == expected, case["id"]
        assert result.agrees, case["id"]


def test_disputed_clues_are_left_out(cases_en):
    # Marmara's 2000-2025 greenness is significant but the second test disagrees: not a fair puzzle.
    assert "marmara-ndvi-2000-2025" not in {c["id"] for c in cases_en}


def test_places_where_it_never_snows_are_left_out(cases_en):
    snow_regions = {c["series"].split("-")[0] for c in cases_en if c["kind"] == "snowfall"}
    for region in snow_regions:
        annual, _ = to_annual(load_processed(region, "snowfall"), VARIABLES["snowfall"])
        assert annual["value"].max() >= 1.0, region
    assert not {"medina", "cairo_nile", "amazon", "sahel"} & snow_regions


def test_chart_data_is_clean(cases_en):
    for case in cases_en:
        years, values = case["years"], case["values"]
        assert len(years) == len(values) >= 10
        assert all(b > a for a, b in zip(years, years[1:]))
        assert all(math.isfinite(v) for v in values)


def test_trend_line_passes_through_the_mean(cases_en):
    for case in cases_en:
        mean_year = sum(case["years"]) / len(case["years"])
        mean_value = sum(case["values"]) / len(case["values"])
        assert case["a"] + case["b"] * mean_year == pytest.approx(mean_value, rel=1e-3, abs=1e-3)


def test_hand_written_notes_only_explain_their_own_verdict(cases_en, cases_tr):
    for case in cases_en + cases_tr:
        if not case["why_key"].startswith("catalog:"):
            assert WHY_FOR[case["why_key"]] == case["truth"], case["id"]


def test_every_hand_written_note_is_used_with_current_data(cases_en):
    used = {c["why_key"] for c in cases_en}
    assert {note for *_, note, _ in SPECIAL_CASES} <= used


def test_other_cases_use_the_apps_possible_reasons(cases_en):
    for case in cases_en:
        if case["why_key"].startswith("catalog:"):
            _, variable, direction = case["why_key"].split(":")
            region = case["series"].split("-")[0]
            assert case["why"] == reasons("en", variable, direction)[0]
            assert case["context"] == (region_context("en", region, variable) or "")
            assert case["source"] == ""


def test_a_note_never_fits_a_flipped_verdict():
    assert not _note_fits("no2_rules", "up", True)
    assert not _note_fits("temp_too_short", "chance", False)
    assert _note_fits("temp_too_short", "chance", True)
    assert not _note_fits(None, "up", True)


def test_big_cases_are_tricky_chance_cases(cases_en):
    for case in (c for c in cases_en if c["boss"]):
        assert case["truth"] == "chance", case["id"]


def test_every_case_explains_itself(cases_en, cases_tr):
    for case in cases_en + cases_tr:
        assert case["why"].strip() and case["chance"].strip() and case["rate"].strip()
        assert f"{case['years'][0]}–{case['years'][-1]}" in case["who"]


def test_region_names_follow_the_language(cases_tr):
    marmara = next(c for c in cases_tr if c["series"] == "marmara-air_temperature")
    assert region_name("tr", "marmara", REGIONS["marmara"].name) in marmara["who"]


def test_turkish_numbers_use_a_decimal_comma(cases_tr):
    rates = " ".join(c["rate"] for c in cases_tr if c["kind"] == "air_temperature")
    assert "," in rates and "0.5" not in rates


def test_temperature_uses_degrees_and_others_use_percent(cases_en):
    for case in cases_en:
        if case["kind"] == "air_temperature":
            assert "°C" in case["rate"]
        elif case["kind"] in ("snowfall", "no2", "aod", "ndvi"):
            assert "%" in case["rate"]


def test_measurements_without_a_character_get_their_own_name():
    from trend import game
    saved = game.CHARACTERS["en"].pop("aod")
    try:
        dust = [c for c in build_cases("en") if c["kind"] == "aod"]
        assert dust and all(c["who"].startswith(VARIABLES["aod"].name) for c in dust)
    finally:
        game.CHARACTERS["en"]["aod"] = saved


def test_missing_data_is_skipped_not_an_error():
    assert build_cases("en", loader=lambda region, variable: None) == []


@pytest.mark.parametrize("lang", ["en", "tr", "xx"])
def test_page_is_self_contained_and_safe(lang):
    page = render_game_html(lang)
    assert "__GAME_DATA__" not in page and "__LANG__" not in page
    data = page.split("const G=", 1)[1].split(";\nconst T=", 1)[0]
    payload = json.loads(data.replace("<\\/", "</"))
    assert payload["cases"] and set(payload["text"]) == set(GAME_TEXT["en"])
    assert page.count("</script>") == 1


def test_modes_and_ranks_make_sense():
    assert MODES["full"]["cases"] == 20 and MODES["quick"]["cases"] == 5
    assert MODES["full"]["lives"] > MODES["quick"]["lives"] >= 1
    assert list(RANK_THRESHOLDS) == sorted(RANK_THRESHOLDS) and RANK_THRESHOLDS[0] == 0


def test_texts_have_the_same_keys_in_both_languages():
    assert set(GAME_TEXT["en"]) == set(GAME_TEXT["tr"])
    assert set(WHY["en"]) == set(WHY["tr"]) == set(WHY_FOR)
    assert set(WHY_SOURCES) <= set(WHY_FOR)
    assert len(GAME_TEXT["tr"]["ranks"]) == len(RANK_THRESHOLDS)
    assert set(VIEW_LABELS["en"]) == set(VIEW_LABELS["tr"]) == {"case", "exam"}


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_exam_view_opens_in_the_app(lang):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["lang"] = lang
    at.session_state["view"] = "exam"
    at.run()
    assert not at.exception
    assert at.query_params.get("view") in ("exam", ["exam"])


def test_shared_exam_link_opens_the_exam():
    at = AppTest.from_file(APP, default_timeout=60)
    at.query_params["view"] = "exam"
    at.query_params["lang"] = "tr"
    at.run()
    assert not at.exception
    assert at.session_state["view"] == "exam"
    assert at.session_state["lang"] == "tr"
