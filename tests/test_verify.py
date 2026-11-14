"""Tests for verification: the second-dataset witness and the reasons a result is not verified.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import math

import numpy as np
import pandas as pd
import pytest

import trend.verify as vf
from trend.fetch import load_processed
from trend.regions import REGIONS
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES


def annual_series(slope, noise, years=range(1981, 2026), seed=0):
    rng = np.random.default_rng(seed)
    years = np.array(list(years))
    return pd.DataFrame({"year": years, "value": 10 + slope * (years - years[0]) + rng.normal(0, noise, len(years))})


def monthly_from_annual(annual):
    rows = [(pd.Timestamp(int(y), m, 1), v) for y, v in zip(annual["year"], annual["value"]) for m in range(1, 13)]
    return pd.DataFrame(rows, columns=["date", "value"]).assign(unit="°C (anomaly)", source="test witness")


def status_of(result):
    if result.significant:
        return "confirmed" if result.agrees else "disputed"
    return "noevidence" if result.agrees else "weak"


def real(region, variable):
    monthly = load_processed(region, variable)
    annual, _ = to_annual(monthly, VARIABLES[variable])
    result = analyze_trend(annual["year"], annual["value"], min_years=VARIABLES[variable].min_years)
    return annual, result


def compare_real(region, variable, lang="en", start=None, end=None):
    annual, result = real(region, variable)
    if start is not None:
        annual = annual[annual["year"].between(start, end)].reset_index(drop=True)
        result = analyze_trend(annual["year"], annual["value"])
    return vf.compare_witness(result, vf.load_witness(region, variable), lang, variable, result.start_year,
                              result.end_year, main_annual=annual, region_key=region)


# --- Formulas ----------------------------------------------------------------------------------

def test_years_needed_follows_weatherhead():
    expected = (3.3 * math.sqrt(12) * 0.5 / 0.02) ** (2 / 3)
    assert vf.years_needed(0.02, 0.5, 0.0) == pytest.approx(expected)
    assert vf.years_needed(0.02, 0.5, 0.5) > expected  # persistence makes detection slower
    assert vf.years_needed(0.0, 0.5, 0.0) == math.inf
    assert math.isnan(vf.years_needed(0.02, 0.0, 0.0))


def test_curvature_tells_a_turn_from_an_acceleration():
    years = np.arange(2005, 2026)
    rng = np.random.default_rng(1)
    hump_p, hump_inside = vf.curvature(years, -((years - 2015) ** 2) / 10.0 + rng.normal(0, 0.5, len(years)))
    assert hump_p < 0.01 and hump_inside
    speed_p, speed_inside = vf.curvature(years, ((years - 2000) ** 2) / 10.0 + rng.normal(0, 0.5, len(years)))
    assert speed_p < 0.01 and not speed_inside
    assert vf.curvature(years, 0.1 * years + rng.normal(0, 0.5, len(years)))[0] > 0.01


def test_detrended_correlation_ignores_a_shared_trend():
    years = np.arange(1981, 2026)
    rng = np.random.default_rng(3)
    a = pd.Series(0.05 * (years - 1981) + rng.normal(0, 0.2, len(years)), index=years)
    b = pd.Series(0.05 * (years - 1981) + rng.normal(0, 0.2, len(years)), index=years)
    assert a.corr(b) > 0.8  # raw values look alike only because both rise
    assert abs(vf.detrended_corr(a, b)) < 0.4


# --- Why not verified ------------------------------------------------------------------------------

def test_a_confirmed_result_needs_no_excuse():
    annual = annual_series(0.05, 0.3)
    result = analyze_trend(annual["year"], annual["value"])
    assert status_of(result) == "confirmed"
    assert vf.why_not_confirmed(annual, result, "confirmed", "en", "air_temperature") == []


def test_noise_wording_matches_its_rule():
    annual = annual_series(0.01, 0.6, seed=4)
    result = analyze_trend(annual["year"], annual["value"])
    lines = vf.why_not_confirmed(annual, result, status_of(result), "en", "air_temperature")
    assert any("less than twice the typical year-to-year swing" in line for line in lines)


def test_no_change_is_worded_carefully_and_dropped_when_the_witness_sees_one():
    years = np.arange(1981, 2026)
    swings = np.tile([0.5, -0.5, 0.3, -0.3, 0.0], 9)  # repeating swings, no trend at all
    annual = pd.DataFrame({"year": years, "value": 10 + swings})
    result = analyze_trend(annual["year"], annual["value"])
    lines = vf.why_not_confirmed(annual, result, status_of(result), "en", "air_temperature")
    assert vf.VERIFY_TEXT["en"]["no_change"] in lines
    assert "there is no real change" not in " ".join(lines)
    witnessed = vf.why_not_confirmed(annual, result, status_of(result), "en", "air_temperature",
                                     witness_verdict="witness_sees")
    assert vf.VERIFY_TEXT["en"]["no_change"] not in witnessed


def test_years_needed_counts_the_span_and_says_it_is_rough():
    annual = annual_series(0.012, 0.5, years=[*range(1981, 2000), *range(2003, 2026)], seed=6)
    result = analyze_trend(annual["year"], annual["value"])
    if result.significant:
        pytest.skip("random draw happened to be significant")
    lines = vf.why_not_confirmed(annual, result, status_of(result), "en", "air_temperature")
    need = [line for line in lines if "90% chance" in line]
    assert need and "spans 45 years" in need[0] and "rough estimate" in need[0]


def test_short_records_and_disputes_are_named():
    annual = annual_series(0.08, 0.3, years=range(2010, 2024), seed=5)
    result = analyze_trend(annual["year"], annual["value"])
    lines = vf.why_not_confirmed(annual, result, "disputed", "en", "air_temperature")
    assert "second test" in lines[0] and any("short (14 years)" in line for line in lines)


# --- Witness verdicts ---------------------------------------------------------------------------

def test_witness_verdicts_on_synthetic_records():
    main = annual_series(0.04, 0.3, seed=6)
    result = analyze_trend(main["year"], main["value"])
    same = vf.compare_witness(result, monthly_from_annual(annual_series(0.035, 0.3, seed=7)), "en",
                              "air_temperature", 1981, 2025, main_annual=main)
    assert same["verdict"] == "confirmed" and "second witness" in same["lines"][0]
    slower = vf.compare_witness(result, monthly_from_annual(annual_series(0.012, 0.05, seed=8)), "en",
                                "air_temperature", 1981, 2025, main_annual=main)
    assert slower["verdict"] == "confirmed_direction"
    quiet_annual = annual_series(0.0, 0.6, seed=10)
    quiet = analyze_trend(quiet_annual["year"], quiet_annual["value"])
    rescue = vf.compare_witness(quiet, monthly_from_annual(annual_series(0.05, 0.3, seed=11)), "tr",
                                "air_temperature", 1981, 2025, main_annual=quiet_annual)
    assert rescue["verdict"] == "witness_sees" and "Karşılaştırılan yıllarda" in rescue["lines"][0]


def test_a_disputed_side_cannot_make_a_case_verified():
    import dataclasses
    main = annual_series(0.04, 0.3, seed=6)
    result = analyze_trend(main["year"], main["value"])
    disputed = dataclasses.replace(result, agrees=False)
    comparison = vf.compare_witness(disputed, monthly_from_annual(annual_series(0.035, 0.3, seed=7)), "en",
                                    "air_temperature", 1981, 2025, main_annual=main)
    assert comparison["verdict"] == "confirmed_weak" and "not proven" in comparison["lines"][0]


def test_common_years_are_an_intersection_and_flips_are_named():
    main = annual_series(0.0, 0.3, years=range(1981, 2026), seed=31)
    main.loc[main["year"] >= 2000, "value"] += 0.06 * (main.loc[main["year"] >= 2000, "year"] - 2000)
    result = analyze_trend(main["year"], main["value"])
    gappy = annual_series(0.06, 0.2, years=[y for y in range(2000, 2026) if y != 2010], seed=32)
    comparison = vf.compare_witness(result, monthly_from_annual(gappy), "en", "air_temperature", 1981, 2025,
                                    main_annual=main)
    assert "same 25 years (2000–2025)" in comparison["overlap"]
    assert comparison["witness"].n_years == 25


def test_too_few_common_years_returns_nothing():
    main = annual_series(0.04, 0.3)
    result = analyze_trend(main["year"], main["value"])
    short = monthly_from_annual(annual_series(0.04, 0.3, years=range(2018, 2026)))
    assert vf.compare_witness(result, short, "en", "air_temperature", 1981, 2025, main_annual=main) is None
    assert "polar winter" in vf.no_witness_reason("en", "aod", incomplete=True)


def test_records_that_barely_match_are_flagged():
    main = annual_series(0.0, 0.3, seed=21)
    result = analyze_trend(main["year"], main["value"])
    other = monthly_from_annual(annual_series(0.0, 0.3, seed=22))
    comparison = vf.compare_witness(result, other, "en", "air_temperature", 1981, 2025, main_annual=main)
    assert comparison["corr"] < 0.3 and any("hardly match" in line for line in comparison["lines"])


# --- Data breaks ---------------------------------------------------------------------------------

def test_a_slow_drift_is_not_a_break_but_a_jump_is():
    years = np.arange(1981, 2026)
    rng = np.random.default_rng(41)
    common = rng.normal(0, 0.4, len(years))
    witness = pd.Series(10 + 0.028 * (years - 1981) + common + rng.normal(0, 0.05, len(years)), index=years)
    drift = pd.Series(10 + 0.033 * (years - 1981) + common + rng.normal(0, 0.05, len(years)), index=years)
    assert vf.data_break(drift, witness) is None
    jump = pd.Series(10 + 0.028 * (years - 1981) + common + np.where(years >= 2015, 1.0, 0.0), index=years)
    assert vf.data_break(jump, witness)["year"] == 2015


def test_alps_rain_names_a_break_without_blaming_one_record():
    comparison = compare_real("alps", "precipitation", lang="en")
    assert comparison["break"]["year"] == 2015
    line = next(line for line in comparison["lines"] if line.startswith("⚠️ Around"))
    assert "we cannot tell which" in line and "artifact" not in line
    tr = compare_real("alps", "precipitation", lang="tr")
    assert any("hangisi olduğunu bilemiyoruz" in line for line in tr["lines"])
    assert all("veri hatası" not in line for line in tr["lines"])


def test_a_break_outside_the_period_is_not_mentioned():
    comparison = compare_real("alps", "precipitation", start=1985, end=2012)
    assert comparison["break"] is None
    assert not any("⚠️ Around" in line for line in comparison["lines"])


def test_only_the_alps_rain_shows_a_break():
    flagged = {region for region in REGIONS if compare_real(region, "precipitation")["break"]}
    assert flagged == {"alps"}


# --- Real witness files ---------------------------------------------------------------------------

@pytest.mark.parametrize("region", list(REGIONS))
def test_every_region_has_a_gistemp_temperature_witness(region):
    witness = vf.load_witness(region, "air_temperature")
    assert witness is not None and {"date", "value", "unit", "source"} <= set(witness.columns)
    assert "GISTEMP" in witness["source"].iloc[0]
    annual, _ = to_annual(witness, VARIABLES["air_temperature"])
    assert annual["year"].between(1981, 2025).sum() >= 38


def test_gistemp_backs_the_app_on_warming_everywhere():
    for region in REGIONS:
        comparison = compare_real(region, "air_temperature")
        assert comparison["verdict"] in ("confirmed", "confirmed_direction", "witness_sees"), region


@pytest.mark.parametrize("region", list(REGIONS))
def test_gpcp_rain_witness_is_read_and_compared(region):
    comparison = compare_real(region, "precipitation")
    assert comparison is not None and "GPCP" in comparison["source"]
    assert comparison["overlap"] and "1983" in comparison["overlap"]  # GPCP starts two years later
    if comparison["verdict"] in ("not_seen", "witness_sees", "opposite", "confirmed_direction"):
        key = "differ_precipitation_desert" if region in vf.DESERT_REGIONS else "differ_precipitation"
        assert vf.VERIFY_TEXT["en"][key] in comparison["lines"]


def test_alps_rain_is_compared_over_exactly_the_gpcp_years():
    annual, result = real("alps", "precipitation")
    assert result.start_year == 1981 and not result.significant  # the board: no evidence (p about 0.06)
    comparison = compare_real("alps", "precipitation")
    assert "(1983–2025)" in comparison["overlap"] and "Unlike the full period" in comparison["overlap"]
    assert comparison["verdict"] == "not_seen"


@pytest.mark.parametrize("region", list(REGIONS))
def test_imerg_is_shown_as_a_high_resolution_check(region):
    assert vf.load_witness(region, "precipitation", "imerg") is not None
    line = vf.extra_check_line(region, "precipitation", "en", 1981, 2025)
    assert line and "GPM IMERG" in line and "not an extra independent one" in line


@pytest.mark.parametrize("region", list(REGIONS))
def test_modis_aerosol_witness_exists_for_every_region(region):
    witness = vf.load_witness(region, "aod")
    assert witness is not None and "MOD08" in witness["source"].iloc[0]


def test_a_witness_without_enough_common_years_is_explained_not_compared():
    witness = vf.load_witness("siberia", "aod")  # MODIS cannot see aerosol in the polar winter
    main = annual_series(0.0, 0.01, years=range(2001, 2026))
    result = analyze_trend(main["year"], main["value"])
    assert vf.compare_witness(result, witness, "en", "aod", 2001, 2025, main_annual=main) is None


@pytest.mark.parametrize("region", ["colorado", "marmara", "beijing", "los_angeles", "alps", "siberia"])
def test_gldas_snowfall_witness_exists(region):
    witness = vf.load_witness(region, "snowfall")
    assert witness is not None and "GLDAS" in witness["source"].iloc[0]


def test_too_little_snow_is_not_judged():
    comparison = compare_real("los_angeles", "snowfall")
    assert comparison["verdict"] == "too_little" and "too little snow" in comparison["lines"][0]


# --- Texts ------------------------------------------------------------------------------------------

def test_every_witness_says_how_independent_it_is_and_missing_ones_say_why():
    assert set(vf.WITNESS_KIND["en"]) == set(vf.WITNESS_KIND["tr"])
    assert set(vf.NO_WITNESS["en"]) == set(vf.NO_WITNESS["tr"])
    assert "Independent" in vf.witness_kind("en", "air_temperature")
    assert vf.witness_kind("en", "precipitation", "colorado").startswith("Partly")
    assert vf.witness_kind("tr", "precipitation", "sahel").startswith("Kısmen")
    assert "not fully independent" in vf.witness_kind("en", "aod")
    assert "OMI" in vf.no_witness_reason("tr", "no2")
    assert vf.no_witness_reason("en", "no2", custom=True) == vf.NO_WITNESS["en"]["custom"]
    for key in ("no2", "black_carbon", "co2", "tree_cover"):
        assert key in VARIABLES, key


def test_texts_have_the_same_keys_in_both_languages():
    assert set(vf.VERIFY_TEXT["en"]) == set(vf.VERIFY_TEXT["tr"])
    for key, text in vf.VERIFY_TEXT["en"].items():
        placeholders = set(pd.Series([text]).str.findall(r"\{(\w+)\}")[0])
        assert placeholders == set(pd.Series([vf.VERIFY_TEXT["tr"][key]]).str.findall(r"\{(\w+)\}")[0]), key


def test_desert_rain_disagreement_is_blamed_on_the_records():
    assert "not that the detective is wrong" in vf.VERIFY_TEXT["en"]["differ_precipitation_desert"]
    assert {"medina", "cairo_nile"} == vf.DESERT_REGIONS
