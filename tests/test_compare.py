"""Tests for the region ranking: how does this place compare (trend/compare.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import pickle
import string

import numpy as np
import pandas as pd
import pytest

from trend.compare import (
    COLUMNS,
    COMPARE_TEXT,
    MIN_HEIGHT,
    compare_text,
    figure_height,
    ordinal,
    ranking_figure,
    ranking_sentence,
    region_ranking,
    untested_text,
)
from trend.fetch import load_processed
from trend.regions import REGIONS
from trend.stats import to_annual
from trend.variables import VARIABLES
from trend.world import NO_HOT_DAYS, SHORT_NAMES, TESTED, board_verdict, place_name

BLUE, ORANGE, GREY, OUTLINE = "#1c5cab", "#a8501b", "#898781", "#0b0b0b"
EN, TR = SHORT_NAMES["en"], SHORT_NAMES["tr"]

# Synthetic warming in °C per year for every prepared region except Konya, whose loader returns None.
SLOPES = {
    "colorado": 0.05, "marmara": 0.03, "medina": 0.01, "beijing": -0.02, "los_angeles": -0.04,
    "cairo_nile": 0.02, "amazon": 0.04, "sahel": -0.01, "alps": 0.0, "siberia": 0.06,
}
EXPECTED_ORDER = ["siberia", "colorado", "amazon", "marmara", "cairo_nile", "medina", "alps", "sahel",
                  "beijing", "los_angeles"]


def synthetic_monthly(slope_per_year: float, years: int = 40, noise: float = 0.05, seed: int = 0) -> pd.DataFrame:
    """Monthly values from 1981 with a seasonal cycle, a steady trend and a little noise."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1981-01-01", periods=12 * years, freq="MS")
    cycle = 10 - 8 * np.cos(2 * np.pi * (dates.month - 1) / 12)
    values = cycle + slope_per_year * (dates.year - 1981) + rng.normal(0, noise, dates.size)
    return pd.DataFrame({"date": dates, "value": values})


def synthetic_loader(region_key: str, variable_key: str) -> pd.DataFrame | None:
    slope = SLOPES.get(region_key)
    if slope is None:
        return None  # no prepared file
    return synthetic_monthly(slope, seed=list(REGIONS).index(region_key))


def table_of(*rows, untested=()) -> pd.DataFrame:
    """A ranking table from (region, slope[, status]) rows, already in ranking order."""
    records = []
    for region, slope, *rest in rows:
        records.append({
            "region": region, "status": rest[0] if rest else "confirmed", "slope_per_decade": slope,
            "ci_low": slope - 0.1, "ci_high": slope + 0.1, "p_value": 0.01, "start_year": 1981, "end_year": 2025,
        })
    table = pd.DataFrame(records, columns=COLUMNS)
    table.attrs["untested"] = list(untested)
    table.attrs["variable_key"] = "air_temperature"
    return table


# The example from the task: Istanbul 4th of 11, Medina highest, the Amazon lowest.
EXAMPLE = table_of(
    ("medina", 0.63), ("alps", 0.60), ("colorado", 0.58), ("marmara", 0.55), ("beijing", 0.50),
    ("los_angeles", 0.45), ("cairo_nile", 0.40), ("siberia", 0.35), ("konya", 0.30), ("sahel", 0.20),
    ("amazon", 0.12),
)


# --- The table -----------------------------------------------------------------------------------------

def test_synthetic_regions_are_ranked_from_highest_to_lowest():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    assert list(table.columns) == COLUMNS
    assert table["region"].tolist() == EXPECTED_ORDER
    assert table["slope_per_decade"].is_monotonic_decreasing
    np.testing.assert_allclose(table["slope_per_decade"], [10 * SLOPES[r] for r in EXPECTED_ORDER], atol=0.01)
    assert table.attrs["untested"] == [("konya", "open")]  # the loader returned None
    assert table.attrs["variable_key"] == "air_temperature"
    assert set(table["status"]) <= set(TESTED)
    by_region = table.set_index("region")
    assert by_region.loc["siberia", "status"] == "confirmed"  # rising
    assert by_region.loc["los_angeles", "status"] == "confirmed"  # falling


def test_confidence_interval_columns_match_the_board_verdict():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    for row in table.itertuples(index=False):
        verdict = board_verdict(synthetic_loader(row.region, "air_temperature"), "air_temperature")
        low, high = verdict.result.ci_per_decade
        assert row.status == verdict.status
        assert row.slope_per_decade == pytest.approx(verdict.result.slope_per_decade)
        assert row.ci_low == pytest.approx(low) and row.ci_high == pytest.approx(high)
        assert row.ci_low < row.slope_per_decade < row.ci_high
        assert row.p_value == pytest.approx(verdict.result.p_value)
        assert (row.start_year, row.end_year) == (1981, 2020)


def test_regions_that_cannot_be_tested_keep_their_stamp():
    def loader(region_key, variable_key):
        if region_key == "konya":
            return None
        if region_key == "siberia":  # never a day above 30 °C
            return synthetic_monthly(0.0).assign(value=0.0)
        if region_key == "alps":  # only 5 complete years
            return synthetic_monthly(0.1, years=5)
        return synthetic_monthly(SLOPES[region_key] + 0.1, seed=list(REGIONS).index(region_key))

    table = region_ranking("hot_days", loader=loader)
    assert len(table) == 8
    assert table.attrs["untested"] == [("alps", "insufficient"), ("siberia", "no_hot"), ("konya", "open")]
    assert not set(table["region"]) & {"alps", "siberia", "konya"}
    assert untested_text("en", table, EN) == (
        "Not ranked: Alps (Not enough data); Siberia (No hot days); Konya (Open case)."
    )
    assert untested_text("tr", table, TR) == (
        "Sıralamaya girmeyenler: Alpler (Yetersiz veri); Sibirya (Sıcak gün yok); Konya (Açık dosya)."
    )
    top, bottom = table["slope_per_decade"].iloc[0], table["slope_per_decade"].iloc[-1]
    assert ranking_sentence("en", table, "siberia", EN, "days", 1) == (
        "This ranking leaves out Siberia: days above 30 °C practically never happen there. Of the 8 regions "
        f"tested over their full records, the highest rate is in Colorado ({top:+.1f} days per decade) and the "
        f"lowest in Los Angeles ({bottom:+.1f})."
    )


def test_unknown_measurement_is_a_clear_error():
    with pytest.raises(KeyError, match="Unknown variable"):
        region_ranking("sea_level", loader=synthetic_loader)


def test_attrs_survive_pickling_for_the_streamlit_cache():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    copy = pickle.loads(pickle.dumps(table))
    assert copy.attrs == table.attrs
    pd.testing.assert_frame_equal(copy, table)


# --- Real data -----------------------------------------------------------------------------------------

def _rank_phrase(rank: int, n: int) -> str:
    if rank == 1:
        return "the highest"
    if rank == n:
        return "the lowest"
    suffix = "th" if rank in (11, 12, 13) else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"the {rank}{suffix} highest"


def test_air_temperature_ranks_all_eleven_regions_like_the_board():
    table = region_ranking("air_temperature")
    assert len(table) == 11 and table.attrs["untested"] == []
    results = {r: board_verdict(load_processed(r, "air_temperature"), "air_temperature").result for r in REGIONS}
    order = sorted(REGIONS, key=lambda r: results[r].slope_per_decade, reverse=True)
    assert table["region"].tolist() == order

    rank = order.index("marmara") + 1
    rate = results["marmara"].slope_per_decade
    english = ranking_sentence("en", table, "marmara", EN, "°C", 2)
    assert english.startswith(f"Over the full records, Istanbul's rate ({rate:+.2f} °C per decade) is "
                              f"{_rank_phrase(rank, 11)} of 11 regions.")
    top, bottom = order[0], order[-1]
    if rank != 1:
        assert f"{place_name('en', top)} ({results[top].slope_per_decade:+.2f})" in english
    if rank != 11:
        assert f"{place_name('en', bottom)} ({results[bottom].slope_per_decade:+.2f})" in english

    turkish = ranking_sentence("tr", table, "marmara", TR, "°C", 2)
    assert f"İstanbul, on yılda {rate:+.2f} °C ile 11 bölge içinde ".replace(".", ",") in turkish
    assert ("en yüksek değere sahip" if rank == 1 else f"{rank}. sırada" if rank < 11 else "en düşük") in turkish
    if rank != 11:
        assert f"{place_name('tr', bottom)} ({results[bottom].slope_per_decade:+.2f})".replace(".", ",") in turkish


def test_hot_days_lists_the_never_hot_regions_as_untested():
    table = region_ranking("hot_days")
    untested = dict(table.attrs["untested"])
    assert set(table["region"]) | set(untested) == set(REGIONS)
    assert not set(table["region"]) & set(untested)
    for region_key in REGIONS:
        monthly = load_processed(region_key, "hot_days")
        if monthly is None:
            assert untested[region_key] == "open"
            continue
        annual, _ = to_annual(monthly, VARIABLES["hot_days"])
        never_hot = len(annual) > 0 and annual["value"].max() < NO_HOT_DAYS
        assert (untested.get(region_key) == "no_hot") == never_hot, region_key
        if never_hot:
            assert "30 °C" in ranking_sentence("en", table, region_key, EN, "days", 1)


def test_groundwater_rises_most_in_the_sahel_and_falls_most_in_the_amazon():
    table = region_ranking("groundwater")
    assert table["region"].iloc[0] == "sahel"
    assert table["slope_per_decade"].iloc[0] > 0  # rising
    assert "amazon" in table["region"].tail(3).tolist()
    assert table.set_index("region").loc["amazon", "slope_per_decade"] < 0
    assert (table["start_year"] >= 2003).all()  # the GRACE era
    english = ranking_sentence("en", table, "konya", EN, "mm of water", 1)
    assert english.startswith("Over the full records, Konya's rate (-")
    assert "Highest: the Sahel (+" in english
    turkish = ranking_sentence("tr", table, "konya", TR, "mm su", 1)
    assert turkish.startswith("Kayıtların tamamına bakıldığında Konya, on yılda -")
    assert "En yüksek: Sahel (+" in turkish


def test_snowfall_leaves_out_the_regions_without_snow():
    table = region_ranking("snowfall")
    no_snow = [region for region, status in table.attrs["untested"] if status == "no_snow"]
    assert {"medina", "cairo_nile"} <= set(no_snow)
    assert ranking_sentence("en", table, "medina", EN, "mm of water", 1).startswith(
        "This ranking leaves out Medina: it practically never snows there. Of the "
    )
    assert untested_text("tr", table, TR).startswith("Sıralamaya girmeyenler: Medine, Kahire")


# --- Figure --------------------------------------------------------------------------------------------

def test_figure_has_one_bar_per_region_and_outlines_the_current_one():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    figure = ranking_figure(table, "en", "marmara", EN, "°C", ".,", 2)
    assert len(figure.data) == 1
    bar = figure.data[0]
    assert bar.type == "bar" and bar.orientation == "h"
    labels = list(bar.y)
    assert len(labels) == len(table) == 10
    assert labels[0] == "Siberia" and labels[-1] == "Los Angeles"  # highest first
    assert figure.layout.yaxis.autorange == "reversed"  # so the highest is on top
    assert list(figure.layout.yaxis.categoryarray) == labels
    assert [label for label in labels if label.startswith("<b>")] == ["<b>Istanbul</b>"]
    current = labels.index("<b>Istanbul</b>")
    widths = list(bar.marker.line.width)
    assert widths[current] >= 2
    assert all(width == 0 for i, width in enumerate(widths) if i != current)
    assert bar.marker.line.color == OUTLINE
    expected = {"confirmed": BLUE, "disputed": ORANGE, "weak": ORANGE}
    assert list(bar.marker.color) == [expected.get(status, GREY) for status in table["status"]]
    np.testing.assert_allclose(np.asarray(bar.x) + np.asarray(bar.error_x.array), table["ci_high"])
    np.testing.assert_allclose(np.asarray(bar.x) - np.asarray(bar.error_x.arrayminus), table["ci_low"])
    zero = [shape for shape in figure.layout.shapes if shape.type == "line" and shape.x0 == 0]
    assert len(zero) == 1
    values = [annotation.text for annotation in figure.layout.annotations]
    assert len(values) == 10 and values[current] == "<b>+0.30</b>"
    assert values[0] == "+0.60" and values[-1] == "-0.40"
    # Each value is written past the end of its interval (right for rises, left for falls).
    for annotation, low, high in zip(figure.layout.annotations, table["ci_low"], table["ci_high"]):
        assert annotation.x > high if annotation.xanchor == "left" else annotation.x < low
    assert figure.layout.height == figure_height(10) == 24 * 10 + 60
    assert figure.layout.xaxis.title.text == "°C per decade"
    assert figure.layout.margin.l == 8 and figure.layout.margin.b == 48
    assert "95% CI" in bar.hovertext[0] and "Confirmed" in bar.hovertext[0]


def test_turkish_figure_uses_decimal_commas():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    figure = ranking_figure(table, "tr", "marmara", TR, "°C", ",.", 2)
    assert figure.layout.separators == ",."
    assert "<b>İstanbul</b>" in list(figure.data[0].y)
    values = [annotation.text for annotation in figure.layout.annotations]
    assert values and all("," in value and "." not in value for value in values)
    assert figure.layout.xaxis.title.text == "°C / 10 yıl"
    hover = figure.data[0].hovertext[0]
    assert "%95 güven aralığı" in hover and "Doğrulandı" in hover and "on yılda +0,60 °C" in hover


def test_small_and_empty_figures_keep_the_minimum_height():
    one = ranking_figure(table_of(("marmara", 0.5)), "en", "marmara", EN, "°C")
    assert one.layout.height == MIN_HEIGHT and len(one.data[0].y) == 1
    empty = ranking_figure(table_of(), "en", "marmara", EN, "°C")
    assert empty.layout.height == MIN_HEIGHT and len(empty.data[0].y) == 0
    assert figure_height(11) == 24 * 11 + 60


def test_current_region_outside_the_table_is_not_outlined():
    table = region_ranking("air_temperature", loader=synthetic_loader)
    figure = ranking_figure(table, "en", "konya", EN, "°C")
    assert not any(label.startswith("<b>") for label in figure.data[0].y)
    assert set(figure.data[0].marker.line.width) == {0}


# --- Texts ---------------------------------------------------------------------------------------------

def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_texts_have_the_same_keys_and_fields_in_both_languages():
    assert COMPARE_TEXT["en"].keys() == COMPARE_TEXT["tr"].keys()
    for key, english in COMPARE_TEXT["en"].items():
        turkish = COMPARE_TEXT["tr"][key]
        assert turkish.strip(), key
        # English puts the possessive "Istanbul's" ({owner}) where Turkish uses the plain name ({place}).
        assert {"place" if name == "owner" else name for name in _fields(english)} == _fields(turkish), key
    assert compare_text("en", "title") == "How does this place compare?"
    assert compare_text("tr", "title") == "Bu bölge diğerleriyle nasıl kıyaslanıyor?"
    assert "same test" in compare_text("en", "intro") and "full record" in compare_text("en", "intro")
    assert "aynı test" in compare_text("tr", "intro") and "kaydının tamamı" in compare_text("tr", "intro")
    for lang, words in (("en", ("Blue", "95%", "Outlined", "NO₂", "2005", "2004")),
                        ("tr", ("Mavi", "%95", "Çerçeveli", "NO₂", "2005", "2004"))):
        note = compare_text(lang, "note")
        assert all(word in note for word in words), (lang, note)
    assert compare_text("de", "title") == "How does this place compare?"  # unknown language: English


def test_ordinals():
    assert [ordinal("en", n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "101st", "111th",
    ]
    assert ordinal("tr", 4) == "4."


# --- Sentences -----------------------------------------------------------------------------------------

def test_sentence_for_a_region_in_the_middle():
    assert ranking_sentence("en", EXAMPLE, "marmara", EN, "°C", 2) == (
        "Over the full records, Istanbul's rate (+0.55 °C per decade) is the 4th highest of 11 regions. "
        "Highest: Medina (+0.63); lowest: the Amazon (+0.12). All regions: 1981–2025."
    )
    assert ranking_sentence("tr", EXAMPLE, "marmara", TR, "°C", 2) == (
        "Kayıtların tamamına bakıldığında İstanbul, on yılda +0,55 °C ile 11 bölge içinde 4. sırada. "
        "En yüksek: Medine (+0,63); en düşük: Amazon (+0,12). Tüm bölgeler: 1981–2025."
    )
    assert ranking_sentence("en", EXAMPLE, "alps", EN, "°C", 2).startswith(
        "Over the full records, the Alps' rate (+0.60 °C per decade) is the 2nd highest of 11 regions."
    )
    assert ranking_sentence("en", EXAMPLE, "colorado", EN, "°C", 2).startswith(
        "Over the full records, Colorado's rate (+0.58 °C per decade) is the 3rd highest"
    )
    assert ranking_sentence("en", EXAMPLE, "los_angeles", EN, "°C", 2).startswith(
        "Over the full records, Los Angeles' rate (+0.45 °C per decade) is the 6th highest"
    )


def test_sentence_for_the_highest_and_the_lowest():
    assert ranking_sentence("en", EXAMPLE, "medina", EN, "°C", 2) == (
        "Over the full records, Medina's rate (+0.63 °C per decade) is the highest of 11 regions. "
        "Lowest: the Amazon (+0.12). All regions: 1981–2025."
    )
    assert ranking_sentence("en", EXAMPLE, "amazon", EN, "°C", 2) == (
        "Over the full records, the Amazon's rate (+0.12 °C per decade) is the lowest of 11 regions. "
        "Highest: Medina (+0.63). All regions: 1981–2025."
    )
    assert ranking_sentence("tr", EXAMPLE, "medina", TR, "°C", 2) == (
        "Kayıtların tamamına bakıldığında Medine, on yılda +0,63 °C ile 11 bölge içinde en yüksek değere sahip. "
        "En düşük: Amazon (+0,12). Tüm bölgeler: 1981–2025."
    )
    assert ranking_sentence("tr", EXAMPLE, "amazon", TR, "°C", 2) == (
        "Kayıtların tamamına bakıldığında Amazon, on yılda +0,12 °C ile 11 bölge içinde en düşük değere sahip. "
        "En yüksek: Medine (+0,63). Tüm bölgeler: 1981–2025."
    )


def test_sentence_with_only_falling_rates_still_says_highest_and_lowest():
    falling = table_of(("medina", -0.02), ("marmara", -0.10), ("beijing", -0.31))
    unit = "10¹⁸ molecules/cm²"
    assert ranking_sentence("en", falling, "medina", EN, unit, 2) == (
        f"Over the full records, Medina's rate (-0.02 {unit} per decade) is the highest of 3 regions. "
        "Lowest: Beijing (-0.31). All regions: 1981–2025."
    )
    assert ranking_sentence("en", falling, "marmara", EN, unit, 2) == (
        f"Over the full records, Istanbul's rate (-0.10 {unit} per decade) is the 2nd highest of 3 regions. "
        "Highest: Medina (-0.02); lowest: Beijing (-0.31). All regions: 1981–2025."
    )
    assert ranking_sentence("tr", falling, "beijing", TR, unit, 2) == (
        f"Kayıtların tamamına bakıldığında Pekin, on yılda -0,31 {unit} ile 3 bölge içinde en düşük değere "
        "sahip. En yüksek: Medine (-0,02). Tüm bölgeler: 1981–2025."
    )


@pytest.mark.parametrize("status, english, turkish", [
    ("no_hot", "This ranking leaves out the Alps: days above 30 °C practically never happen there.",
     "Alpler bu sıralamada yok: orada 30 °C'yi geçen gün neredeyse hiç olmuyor."),
    ("no_snow", "This ranking leaves out the Alps: it practically never snows there.",
     "Alpler bu sıralamada yok: orada neredeyse hiç kar yağmıyor."),
    ("insufficient",
     "This ranking leaves out the Alps: the record there has too few complete years for the test.",
     "Alpler bu sıralamada yok: oradaki kayıtta test için yeterince tam yıl yok."),
    ("open", "This ranking leaves out the Alps: this measurement has not been prepared there yet.",
     "Alpler bu sıralamada yok: bu ölçüm için orada henüz hazır bir kayıt yok."),
])
def test_sentence_for_a_region_that_cannot_be_tested(status, english, turkish):
    table = table_of(("medina", 6.3), ("cairo_nile", 5.0), ("amazon", -1.2), untested=[("alps", status)])
    assert ranking_sentence("en", table, "alps", EN, "days", 1) == (
        f"{english} Of the 3 regions tested over their full records, the highest rate is in Medina (+6.3 days "
        "per decade) and the lowest in the Amazon (-1.2)."
    )
    assert ranking_sentence("tr", table, "alps", TR, "gün", 1) == (
        f"{turkish} Kayıtlarının tamamı üzerinden test edilen 3 bölge içinde en yüksek değer Medine bölgesinde "
        "(on yılda +6,3 gün), en düşük değer Amazon bölgesinde (-1,2)."
    )


def test_sentence_for_a_place_that_is_not_a_prepared_region():
    assert ranking_sentence("en", EXAMPLE, "custom", EN, "°C", 2) == (
        "Of the 11 regions tested over their full records, the highest rate is in Medina (+0.63 °C per decade) "
        "and the lowest in the Amazon (+0.12)."
    )


def test_sentence_with_fewer_than_two_tested_regions():
    one = table_of(("medina", 0.4), untested=[("marmara", "open")])
    short = (
        "Only Medina can be tested over the full record for this measurement, so there is nothing to compare "
        "yet."
    )
    assert ranking_sentence("en", one, "medina", EN, "°C", 2) == short
    assert ranking_sentence("en", one, "marmara", EN, "°C", 2) == short
    assert ranking_sentence("tr", one, "medina", TR, "°C", 2) == (
        "Bu ölçümde kaydın tamamı üzerinden yalnızca Medine test edilebiliyor; şimdilik kıyaslanacak başka "
        "bölge yok."
    )
    none = table_of(untested=[(region, "open") for region in REGIONS])
    assert ranking_sentence("en", none, "marmara", EN, "°C", 2) == (
        "No prepared region can be tested for this measurement yet, so there is no ranking."
    )
    assert ranking_sentence("tr", none, "marmara", TR, "°C", 2) == (
        "Bu ölçüm için henüz test edilebilen hazır bölge yok; sıralama yapılamıyor."
    )


def test_untested_text_is_empty_when_every_region_is_ranked():
    assert untested_text("en", EXAMPLE, EN) == ""
    table = table_of(("marmara", 1.0), untested=[("medina", "no_snow"), ("cairo_nile", "no_snow"),
                                                 ("amazon", "no_snow")])
    assert untested_text("en", table, EN) == "Not ranked: Medina, Cairo and Amazon (No snow)."
    assert untested_text("tr", table, TR) == "Sıralamaya girmeyenler: Medine, Kahire ve Amazon (Kar yok)."



def test_rank_is_shared_for_equal_shown_rates_and_an_unconfirmed_region_gets_a_caution():
    table = table_of(("medina", 0.40), ("cairo_nile", 0.33), ("siberia", 0.331), ("amazon", 0.12))
    assert "shares 2nd place among 4 regions" in ranking_sentence("en", table, "siberia", EN, "°C", 2)
    assert "2. sırayı paylaşıyor" in ranking_sentence("tr", table, "cairo_nile", TR, "°C", 2)
    table.loc[table["region"] == "amazon", "status"] = "noevidence"
    sentence = ranking_sentence("en", table, "amazon", EN, "°C", 2)
    assert "Its own trend is not Confirmed (No evidence)" in sentence
    assert "kendi trendi doğrulanmadı" in ranking_sentence("tr", table, "amazon", TR, "°C", 2)


def test_a_very_wide_interval_does_not_squeeze_the_bars():
    table = table_of(("medina", 0.40), ("cairo_nile", 0.30), ("amazon", 0.10))
    table.loc[table["region"] == "medina", ["ci_low", "ci_high"]] = (-20.0, 20.8)
    axis = ranking_figure(table, "en", "amazon", EN, "°C").layout.xaxis.range
    assert axis[1] - axis[0] < 2.0  # set by the rates (0 to 0.40), not by the -20 to +20.8 interval



def test_highest_and_lowest_name_their_stamp_when_not_confirmed():
    table = table_of(("cairo_nile", 0.31, "noevidence"), ("marmara", 0.03), ("beijing", -1.97, "noevidence"))
    sentence = ranking_sentence("en", table, "marmara", EN, "x", 2)
    assert "Highest: Cairo (+0.31, No evidence); lowest: Beijing (-1.97, No evidence)." in sentence
    assert "Kahire (+0,31, Delil yok)" in ranking_sentence("tr", table, "marmara", TR, "x", 2)
