"""Tests for the season trends: which season is changing (trend/seasonal.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import math
import string

import numpy as np
import pandas as pd
import pytest

from trend.fetch import load_processed
from trend.i18n import status_text
from trend.seasonal import (
    COLUMNS,
    SEASONAL_TEXT,
    SEASONS,
    SUPPORTED,
    TROPIC_LATITUDE,
    figure_note,
    season_annual,
    season_figure,
    season_name,
    season_sentence,
    season_trends,
    season_variable,
    section_text,
    whole_year_reference,
)
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES

ISTANBUL_LAT = 41.0
AMAZON_LAT = -10.5  # Rondônia, inside the tropics
CAPE_TOWN_LAT = -33.9
BLUE, ORANGE, GREY = "#1c5cab", "#a8501b", "#898781"


def synthetic_temperature(years: int = 40, warming_per_year: float = 0.08, seed: int = 3) -> pd.DataFrame:
    """Monthly temperatures with a seasonal cycle and noise, where only June to August warm."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1981-01-01", periods=12 * years, freq="MS")
    cycle = 10 - 8 * np.cos(2 * np.pi * (dates.month - 1) / 12)
    summer = np.asarray(dates.month.isin([6, 7, 8]))
    trend = np.where(summer, warming_per_year * (dates.year - 1981), 0.0)
    return pd.DataFrame({"date": dates, "value": cycle + trend + rng.normal(0, 0.5, dates.size)})


def synthetic_rain(years: int = 40, seed: int = 5) -> pd.DataFrame:
    """Monthly rain of about 60 mm, where each winter month (Dec, Jan, Feb) loses 1 mm a year."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1981-01-01", periods=12 * years, freq="MS")
    winter = np.asarray(dates.month.isin([12, 1, 2]))
    drying = np.where(winter, -1.0 * (dates.year - 1981), 0.0)
    values = np.clip(60 + drying + rng.normal(0, 5, dates.size), 0, None)
    return pd.DataFrame({"date": dates, "value": values})


def synthetic_hot_days(years: int = 40, seed: int = 7) -> pd.DataFrame:
    """Hot days per month: none in winter, every day in summer, a rising spring and a noisy autumn."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1981-01-01", periods=12 * years, freq="MS")
    month, year = np.asarray(dates.month), np.asarray(dates.year)
    values = np.zeros(dates.size)
    spring = np.isin(month, [3, 4, 5])
    values[spring] = np.clip(2 + 0.15 * (year[spring] - 1981) + rng.normal(0, 0.5, spring.sum()), 0, None)
    summer = np.isin(month, [6, 7, 8])
    values[summer] = np.asarray(dates.days_in_month)[summer]  # every summer day above 30 °C
    autumn = np.isin(month, [9, 10, 11])
    values[autumn] = np.clip(5 + rng.normal(0, 1, autumn.sum()), 0, None)
    return pd.DataFrame({"date": dates, "value": values})


def table_of(*rows) -> pd.DataFrame:
    """A season table from (season, slope, status[, ceiling]) rows, with plausible other columns."""
    records = []
    for season, slope, status, *rest in rows:
        tested = math.isfinite(slope)
        records.append({
            "season": season, "n_years": 30, "slope_per_decade": slope,
            "ci_low": slope - 0.2 if tested else math.nan, "ci_high": slope + 0.2 if tested else math.nan,
            "p_value": (0.01 if status == "confirmed" else 0.4) if tested else math.nan, "status": status,
            "start_year": 1991, "end_year": 2020, "ceiling": bool(rest[0]) if rest else False,
        })
    return pd.DataFrame(records, columns=COLUMNS)


# --- The synthetic case from the task: only June to August warm ----------------------------------------

def test_only_summer_warming_is_confirmed_and_fastest():
    table = season_trends(synthetic_temperature(), "air_temperature")
    assert list(table.columns) == COLUMNS
    assert list(table["season"]) == list(SEASONS)
    by_season = table.set_index("season")
    assert by_season.loc["jun_aug", "status"] == "confirmed"
    assert by_season.loc["jun_aug", "slope_per_decade"] == pytest.approx(0.8, abs=0.1)
    for season in ("dec_feb", "mar_may", "sep_nov"):
        assert by_season.loc[season, "status"] != "confirmed"
        assert abs(by_season.loc[season, "slope_per_decade"]) < 0.15
    assert table.loc[table["slope_per_decade"].abs().idxmax(), "season"] == "jun_aug"

    sentence = season_sentence("en", table, "air_temperature", ISTANBUL_LAT, "°C")
    assert sentence.startswith("The fastest change is in Jun–Aug (summer): +0.")
    assert "°C per decade, Confirmed." in sentence
    assert "The slowest is " in sentence
    turkish = season_sentence("tr", table, "air_temperature", ISTANBUL_LAT, "°C")
    assert turkish.startswith("En hızlı değişim Haz–Ağu (yaz) aylarında: on yılda +0,")
    assert "°C, Doğrulandı." in turkish
    assert "En yavaş değişim " in turkish


def test_whole_year_is_kept_next_to_the_seasons():
    data = synthetic_temperature()
    table = season_trends(data, "air_temperature")
    whole = table.attrs["whole_year"]
    annual, _ = to_annual(data, VARIABLES["air_temperature"])
    expected = analyze_trend(annual["year"], annual["value"])
    assert whole["season"] == "year"
    assert whole["n_years"] == len(annual)
    assert whole["slope_per_decade"] == pytest.approx(expected.slope_per_decade)
    assert whole["slope_per_decade"] == pytest.approx(0.8 * 3 / 12, abs=0.05)  # a quarter of the year warms
    assert table.attrs["variable_key"] == "air_temperature"
    assert whole_year_reference(table) == pytest.approx(whole["slope_per_decade"])  # a mean is not divided


def test_period_limits_the_years_by_their_labels():
    table = season_trends(synthetic_temperature(), "air_temperature", start_year=1991, end_year=2010)
    assert table["n_years"].tolist() == [20, 20, 20, 20]  # Dec-Feb 1991 starts in December 1990
    assert table["start_year"].tolist() == [1991] * 4
    assert table["end_year"].tolist() == [2010] * 4
    assert table.attrs["whole_year"]["n_years"] == 20


# --- Dec-Feb belongs to the year of its January ---------------------------------------------------------

def test_dec_feb_is_labelled_by_the_year_of_its_january():
    dates = pd.date_range("2000-01-01", "2002-12-01", freq="MS")
    data = pd.DataFrame({"date": dates, "value": (dates.year * 100 + dates.month).astype(float)})
    variable = season_variable("precipitation", "dec_feb")
    assert variable.season_months == (12, 1, 2) and variable.year_starts_month == 12
    assert VARIABLES["precipitation"].year_starts_month == 1  # the catalog entry is untouched

    winters = season_annual(data, "precipitation", "dec_feb")
    # January and February 2000 have no December before them, and December 2002 no January after it.
    assert winters["year"].tolist() == [2001, 2002]
    assert winters["n_months"].tolist() == [3, 3]
    assert winters["value"].iloc[0] == 200012 + 200101 + 200102  # a precipitation season is a sum
    means = season_annual(data, "air_temperature", "dec_feb")
    assert means["value"].iloc[0] == pytest.approx((200012 + 200101 + 200102) / 3)  # temperature: a mean
    assert season_annual(data, "precipitation", "dec_feb", start_year=2002)["year"].tolist() == [2002]
    summers = season_annual(data, "precipitation", "jun_aug")
    assert summers["year"].tolist() == [2000, 2001, 2002]
    assert summers["value"].iloc[0] == 200006 + 200007 + 200008


# --- Real data -------------------------------------------------------------------------------------------

def test_istanbul_temperature_runs_on_real_data():
    monthly = load_processed("marmara", "air_temperature")
    assert monthly is not None
    table = season_trends(monthly, "air_temperature")
    assert len(table) == 4
    assert list(table["season"]) == list(SEASONS)
    assert set(table["status"]) <= {"confirmed", "disputed", "noevidence", "weak"}
    assert (table["n_years"] >= VARIABLES["air_temperature"].min_years).all()
    assert table[["slope_per_decade", "ci_low", "ci_high", "p_value"]].notna().all().all()
    assert ((table["ci_low"] <= table["slope_per_decade"]) & (table["slope_per_decade"] <= table["ci_high"])).all()
    annual, _ = to_annual(monthly, VARIABLES["air_temperature"])
    expected = analyze_trend(annual["year"], annual["value"])
    assert table.attrs["whole_year"]["slope_per_decade"] == pytest.approx(expected.slope_per_decade)
    for lang, separators in (("en", ".,"), ("tr", ",.")):
        assert season_sentence(lang, table, "air_temperature", ISTANBUL_LAT, "°C")
        figure = season_figure(table, lang, ISTANBUL_LAT, "°C", separators, 2)
        assert len(figure.data) == 1 and len(figure.data[0].x) == 4


def test_istanbul_winters_have_no_hot_days():
    table = season_trends(load_processed("marmara", "hot_days"), "hot_days").set_index("season")
    assert table.loc["dec_feb", "status"] == "no_hot"
    assert math.isnan(table.loc["dec_feb", "slope_per_decade"])
    assert table.loc["dec_feb", "n_years"] >= 10  # the years are there, the hot days are not
    assert table.loc["jun_aug", "status"] in {"confirmed", "disputed", "noevidence", "weak"}


# --- Season names -----------------------------------------------------------------------------------------

def test_season_words_follow_the_hemisphere_and_stay_out_of_the_tropics():
    assert season_name("en", "jun_aug", ISTANBUL_LAT) == "Jun–Aug (summer)"
    assert season_name("en", "dec_feb", ISTANBUL_LAT) == "Dec–Feb (winter)"
    assert season_name("en", "jun_aug", CAPE_TOWN_LAT) == "Jun–Aug (winter)"  # flipped in the south
    assert season_name("en", "dec_feb", CAPE_TOWN_LAT) == "Dec–Feb (summer)"
    assert season_name("en", "mar_may", CAPE_TOWN_LAT) == "Mar–May (autumn)"
    assert season_name("en", "sep_nov", CAPE_TOWN_LAT) == "Sep–Nov (spring)"
    # The Amazon case (10.5° S) lies inside the tropics: months only, never "winter" for June there.
    assert season_name("en", "jun_aug", AMAZON_LAT) == "Jun–Aug"
    assert season_name("tr", "dec_feb", AMAZON_LAT) == "Ara–Şub"
    assert season_name("en", "jun_aug", 0) == "Jun–Aug"
    assert season_name("en", "jun_aug", None) == "Jun–Aug"
    assert season_name("en", "jun_aug", TROPIC_LATITUDE) == "Jun–Aug"
    assert season_name("en", "jun_aug", TROPIC_LATITUDE + 0.5) == "Jun–Aug (summer)"
    assert season_name("en", "jun_aug", -TROPIC_LATITUDE - 0.5) == "Jun–Aug (winter)"
    assert season_name("en", "year", ISTANBUL_LAT) == "Whole year"


def test_turkish_season_names():
    assert [season_name("tr", key, ISTANBUL_LAT) for key in SEASONS] == [
        "Ara–Şub (kış)", "Mar–May (ilkbahar)", "Haz–Ağu (yaz)", "Eyl–Kas (sonbahar)",
    ]
    assert [season_name("tr", key, CAPE_TOWN_LAT) for key in SEASONS] == [
        "Ara–Şub (yaz)", "Mar–May (sonbahar)", "Haz–Ağu (kış)", "Eyl–Kas (ilkbahar)",
    ]
    assert [season_name("tr", key, 0) for key in SEASONS] == ["Ara–Şub", "Mar–May", "Haz–Ağu", "Eyl–Kas"]


# --- Texts ------------------------------------------------------------------------------------------------

def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_texts_exist_in_both_languages_with_the_same_fields():
    assert SEASONAL_TEXT["en"].keys() == SEASONAL_TEXT["tr"].keys()
    for key, english in SEASONAL_TEXT["en"].items():
        assert SEASONAL_TEXT["tr"][key].strip(), key
        assert _fields(english) == _fields(SEASONAL_TEXT["tr"][key]), key
    assert section_text("en", "title") == "Which season is changing?"
    assert section_text("tr", "title") == "Hangi mevsim değişiyor?"
    assert section_text("en", "intro") == (
        "The same test for each three-month season. A warming that happens mostly in summer, or rain that "
        "falls mostly in winter, shows up here."
    )
    assert section_text("tr", "intro").startswith("Aynı test, üç aylık her mevsim için")
    assert section_text("de", "title") == "Which season is changing?"  # unknown language: English
    for lang in ("en", "tr"):
        assert status_text(lang, "confirmed")[0] in section_text(lang, "verdict_confirmed")


def test_figure_note_explains_the_dashed_line_for_totals_and_means():
    assert "divided by four" in figure_note("en", "precipitation")
    assert "divided by four" in figure_note("en", "hot_days")
    assert "the whole year" in figure_note("en", "air_temperature")
    assert "dörtte biri" in figure_note("tr", "precipitation")


# --- Sentences ---------------------------------------------------------------------------------------------

def test_rain_sentence_says_fall_and_uses_the_decimal_comma():
    table = season_trends(synthetic_rain(), "precipitation")
    by_season = table.set_index("season")
    assert by_season.loc["dec_feb", "status"] == "confirmed"
    assert by_season.loc["dec_feb", "slope_per_decade"] == pytest.approx(-30, abs=3)  # 3 months x -1 mm a year
    english = season_sentence("en", table, "precipitation", ISTANBUL_LAT, "mm of water")
    assert english.startswith("The fastest change is in Dec–Feb (winter): a fall of ")
    assert "mm of water per decade, Confirmed." in english
    turkish = season_sentence("tr", table, "precipitation", ISTANBUL_LAT, "mm su")
    assert turkish.startswith("En hızlı değişim Ara–Şub (kış) aylarında: on yılda ")
    assert "mm su azalma, Doğrulandı." in turkish
    rate = turkish.split("on yılda ")[1].split(" mm")[0]
    assert "," in rate and "." not in rate


def test_sentence_when_no_season_is_confirmed():
    table = table_of(("dec_feb", 0.3, "noevidence"), ("mar_may", -0.1, "weak"), ("jun_aug", 0.5, "disputed"),
                     ("sep_nov", 0.2, "noevidence"))
    english = season_sentence("en", table, "air_temperature", ISTANBUL_LAT, "°C")
    assert english == (
        "The fastest change is in Jun–Aug (summer): +0.50 °C per decade, but no season is Confirmed. "
        "The slowest is Mar–May (spring): -0.10 °C per decade."
    )
    turkish = season_sentence("tr", table, "air_temperature", ISTANBUL_LAT, "°C")
    assert turkish == (
        "En hızlı değişim Haz–Ağu (yaz) aylarında: on yılda +0,50 °C, ama hiçbir mevsim doğrulanmadı. "
        "En yavaş değişim Mar–May (ilkbahar) aylarında: on yılda -0,10 °C."
    )


def test_sentence_names_the_confirmed_season_when_the_fastest_is_not():
    table = table_of(("dec_feb", -0.9, "noevidence"), ("mar_may", 0.4, "confirmed"), ("jun_aug", 0.2, "weak"),
                     ("sep_nov", 0.3, "confirmed"))
    english = season_sentence("en", table, "precipitation", ISTANBUL_LAT, "mm of water")
    assert english.startswith(
        "The fastest change is in Dec–Feb (winter): a fall of 0.9 mm of water per decade, but it is not "
        "Confirmed (No evidence), while Mar–May (spring) and Sep–Nov (autumn) are."
    )
    assert english.endswith("The slowest is Jun–Aug (summer): a rise of 0.2 mm of water per decade.")
    turkish = season_sentence("tr", table, "precipitation", ISTANBUL_LAT, "mm su")
    assert "ama doğrulanmadı (Delil yok); Mar–May (ilkbahar) ve Eyl–Kas (sonbahar) ise doğrulandı." in turkish
    one = table_of(("dec_feb", -0.9, "disputed"), ("mar_may", 0.4, "confirmed"), ("jun_aug", 0.2, "weak"))
    assert ", but it is not Confirmed (Disputed), while Mar–May (spring) is." in season_sentence(
        "en", one, "precipitation", ISTANBUL_LAT, "mm of water"
    )


def test_fastest_and_slowest_use_the_size_of_the_change():
    # Temperature with mixed signs: -0.40 is a bigger change than +0.10, so it is not "the slowest".
    table = table_of(("dec_feb", -0.4, "confirmed"), ("mar_may", 0.1, "noevidence"), ("jun_aug", 0.3, "confirmed"),
                     ("sep_nov", 0.2, "noevidence"))
    english = season_sentence("en", table, "air_temperature", ISTANBUL_LAT, "°C")
    assert english == (
        "The fastest change is in Dec–Feb (winter): -0.40 °C per decade, Confirmed. "
        "The slowest is Mar–May (spring): +0.10 °C per decade."
    )


def test_sentence_with_one_or_no_testable_season():
    nan = math.nan
    one = table_of(("dec_feb", nan, "no_hot"), ("mar_may", nan, "no_hot"), ("jun_aug", 0.42, "noevidence"),
                   ("sep_nov", nan, "no_hot"))
    assert season_sentence("en", one, "hot_days", 62.5, "days") == (
        "Only Jun–Aug (summer) can be tested here: a rise of 0.4 days per decade, but it is not Confirmed "
        "(No evidence)."
    )
    assert season_sentence("tr", one, "hot_days", 62.5, "gün") == (
        "Burada yalnızca Haz–Ağu (yaz) aylarında test yapılabiliyor: on yılda 0,4 gün artış, ama doğrulanmadı "
        "(Delil yok)."
    )
    none = table_of(*[(key, nan, "insufficient") for key in SEASONS])
    assert season_sentence("en", none, "air_temperature", 0, "°C") == "No season can be tested here."
    assert season_sentence("tr", none, "air_temperature", 0, "°C") == "Burada hiçbir mevsim test edilemiyor."


def test_sentence_for_flat_seasons():
    flat = table_of(("dec_feb", 0.001, "noevidence"), ("mar_may", 0.0, "noevidence"),
                    ("jun_aug", -0.002, "noevidence"), ("sep_nov", 0.0, "noevidence"))
    assert season_sentence("en", flat, "air_temperature", ISTANBUL_LAT, "°C") == (
        "No season shows a noticeable change."
    )
    slow = table_of(("dec_feb", 3.0, "confirmed"), ("mar_may", 0.01, "noevidence"))
    assert season_sentence("en", slow, "precipitation", ISTANBUL_LAT, "mm of water").endswith(
        "The slowest is Mar–May (spring): hardly any change."
    )


def test_full_hot_day_season_is_explained_not_called_slow():
    table = season_trends(synthetic_hot_days(), "hot_days")
    by_season = table.set_index("season")
    assert by_season.loc["dec_feb", "status"] == "no_hot"
    assert bool(by_season.loc["jun_aug", "ceiling"]) is True
    assert by_season.loc["jun_aug", "slope_per_decade"] == 0
    assert by_season.loc["mar_may", "status"] == "confirmed"
    assert not by_season["ceiling"].drop("jun_aug").any()
    english = season_sentence("en", table, "hot_days", ISTANBUL_LAT, "days")
    assert english.startswith("The fastest change is in Mar–May (spring): a rise of ")
    assert english.endswith(
        "The slowest is Jun–Aug (summer): almost every day is already above 30 °C, so there is little room "
        "to rise."
    )
    assert "30 °C'nin üstünde" in season_sentence("tr", table, "hot_days", ISTANBUL_LAT, "gün")


# --- Too little data and unsupported measurements -------------------------------------------------------

def test_short_record_is_insufficient_with_nan_numbers():
    table = season_trends(synthetic_temperature(years=8), "air_temperature")
    assert table["status"].tolist() == ["insufficient"] * 4
    assert table["n_years"].tolist() == [7, 8, 8, 8]  # the first January and February have no December
    assert table[["slope_per_decade", "ci_low", "ci_high", "p_value"]].isna().all().all()
    assert table.attrs["whole_year"]["status"] == "insufficient"
    assert whole_year_reference(table) is None
    figure = season_figure(table, "en", ISTANBUL_LAT, "°C")
    notes = [annotation.text for annotation in figure.layout.annotations]
    assert notes.count(status_text("en", "insufficient")[0]) == 4
    assert not any(shape.line.dash == "dash" for shape in figure.layout.shapes)


@pytest.mark.parametrize("call", [
    lambda: season_trends(synthetic_temperature(), "no2"),
    lambda: season_annual(synthetic_temperature(), "snowfall", "dec_feb"),
    lambda: season_sentence("en", table_of(("dec_feb", 0.1, "noevidence")), "co2", 0, "ppm"),
])
def test_only_supported_measurements(call):
    assert SUPPORTED == ("air_temperature", "precipitation", "hot_days")
    with pytest.raises(ValueError):
        call()


# --- Figure -----------------------------------------------------------------------------------------------

def test_figure_colours_bars_by_stamp_and_marks_zero_and_the_whole_year():
    table = season_trends(synthetic_temperature(), "air_temperature")
    figure = season_figure(table, "en", ISTANBUL_LAT, "°C", ".,", 2)
    bar = figure.data[0]
    assert bar.type == "bar" and bar.orientation == "h"
    assert list(bar.y) == ["Dec–Feb (winter)", "Mar–May (spring)", "Jun–Aug (summer)", "Sep–Nov (autumn)"]
    colors = dict(zip(table["season"], bar.marker.color))
    assert colors["jun_aug"] == BLUE
    expected = {"confirmed": BLUE, "disputed": ORANGE, "weak": ORANGE}
    for season, status in zip(table["season"], table["status"]):
        assert colors[season] == expected.get(status, GREY)
    # The error bars reach the 95% interval on both sides.
    np.testing.assert_allclose(np.asarray(bar.x) + np.asarray(bar.error_x.array), table["ci_high"])
    np.testing.assert_allclose(np.asarray(bar.x) - np.asarray(bar.error_x.arrayminus), table["ci_low"])
    lines = [shape for shape in figure.layout.shapes if shape.type == "line"]
    assert any(shape.x0 == 0 and shape.line.dash is None for shape in lines)  # the zero line
    dashed = [shape for shape in lines if shape.line.dash == "dash"]
    assert len(dashed) == 1
    assert dashed[0].x0 == pytest.approx(table.attrs["whole_year"]["slope_per_decade"])
    assert any(annotation.text.startswith("Whole year: +") for annotation in figure.layout.annotations)
    assert 240 <= figure.layout.height <= 280
    assert figure.layout.yaxis.autorange == "reversed"  # Dec-Feb on top
    assert figure.layout.xaxis.title.text == "°C per decade"


def test_figure_for_totals_divides_the_whole_year_by_four_in_turkish():
    table = season_trends(synthetic_rain(), "precipitation")
    figure = season_figure(table, "tr", ISTANBUL_LAT, "mm su", ",.", 1)
    whole = table.attrs["whole_year"]["slope_per_decade"]
    assert whole_year_reference(table) == pytest.approx(whole / 4)
    dashed = [shape for shape in figure.layout.shapes if shape.line.dash == "dash"]
    assert dashed[0].x0 == pytest.approx(whole / 4)
    texts = [annotation.text for annotation in figure.layout.annotations]
    assert any(text.startswith("Tüm yıl ÷ 4: -") and "," in text for text in texts)
    assert list(figure.data[0].y)[0] == "Ara–Şub (kış)"
    assert figure.layout.separators == ",."
    assert figure.layout.xaxis.title.text == "mm su / 10 yıl"
    assert "%95 güven aralığı" in figure.data[0].hovertext[0]
