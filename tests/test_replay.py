"""Tests for the investigation replay (trend/replay.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd
import pytest

from trend.replay import (
    REPLAY_TEXT,
    TABLE_COLUMNS,
    growing_record,
    replay_figure,
    replay_sentence,
    replay_summary,
    replay_text,
    replay_title,
)
from trend.stats import analyze_trend
from trend.world import case_status

STAMP_COLOR = {"confirmed": "#1c5cab", "disputed": "#a8501b", "weak": "#a8501b"}  # grey otherwise


def series(values, first=1981):
    return pd.DataFrame({"year": np.arange(first, first + len(values)), "value": np.asarray(values, dtype=float)})


def strong_trend(n=40):
    rng = np.random.default_rng(1)
    return series(0.5 * np.arange(n) + rng.normal(scale=0.5, size=n))


def late_trend():
    """20 years that only flip between 0 and 1 (1981-2000), then a steady rise from 2001 to 2010."""
    return series([0.0, 1.0] * 10 + [0.5 + 0.4 * k for k in range(1, 11)])


def table_of(statuses, slopes=None):
    """A hand-made growing_record table: first record 1981-1990 (10 years), then one more year per row."""
    n = len(statuses)
    return pd.DataFrame({
        "end_year": np.arange(1990, 1990 + n), "n_years": np.arange(10, 10 + n),
        "slope_per_decade": slopes if slopes is not None else [1.0] * n,
        "ci_low": [0.0] * n, "ci_high": [2.0] * n, "p_value": [0.01] * n,
        "significant": [s in ("confirmed", "disputed") for s in statuses],
        "agrees": [s in ("confirmed", "noevidence") for s in statuses],
        "status": list(statuses),
    })


def test_strong_trend_is_confirmed_and_ends_on_the_page_verdict():
    annual = strong_trend()
    table = growing_record(annual, 10)
    assert list(table.columns) == TABLE_COLUMNS
    assert len(table) == 31 and table["n_years"].tolist() == list(range(10, 41))
    assert table["end_year"].iloc[0] == 1990 and table["end_year"].iloc[-1] == 2020
    assert table["status"].iloc[-1] == "confirmed"
    summary = replay_summary(table)
    assert summary["kind"] in ("always", "closed") and summary["n_years"] == 40
    full = analyze_trend(annual["year"], annual["value"], min_years=10)  # what the case file shows
    last = table.iloc[-1]
    assert last["p_value"] == pytest.approx(full.p_value)
    assert last["slope_per_decade"] == pytest.approx(full.slope_per_decade)
    assert (last["ci_low"], last["ci_high"]) == pytest.approx(full.ci_per_decade)


def test_pure_noise_stays_an_open_case():
    rng = np.random.default_rng(7)
    table = growing_record(series(rng.normal(size=30)), 10)
    assert table["status"].iloc[-1] != "confirmed"
    assert replay_summary(table) == {"kind": "open", "year": None, "n_first": 10, "n_years": 30, "last_year": 2010}


def test_a_trend_that_appears_later_closes_the_case_in_the_right_year():
    annual = late_trend()
    table = growing_record(annual, 10)
    assert replay_summary(table) == {"kind": "closed", "year": 2004, "n_first": 10, "n_years": 30, "last_year": 2010}
    # Independent check: the test on the record cut at 2003 is not confirmed, every cut from 2004 on is.
    years, values = annual["year"].to_numpy(), annual["value"].to_numpy()
    statuses = {int(years[j - 1]): case_status(analyze_trend(years[:j], values[:j])) for j in range(10, 31)}
    assert statuses[2003] != "confirmed"
    assert all(statuses[year] == "confirmed" for year in range(2004, 2011))


def test_summary_rules_on_hand_made_tables():
    assert replay_summary(table_of(["confirmed"] * 3)) == {
        "kind": "always", "year": 1990, "n_first": 10, "n_years": 12, "last_year": 1992,
    }
    assert replay_summary(table_of(["noevidence", "weak", "confirmed", "confirmed"]))["year"] == 1992
    assert replay_summary(table_of(["confirmed", "confirmed", "disputed"]))["kind"] == "open"
    # Confirmed, lost and confirmed again: n_first is the last unconfirmed record, so the sentence stays true.
    regained = replay_summary(table_of(["confirmed", "noevidence", "noevidence", "confirmed", "confirmed"]))
    assert regained == {"kind": "closed", "year": 1993, "n_first": 12, "n_years": 14, "last_year": 1994}
    # A confirmed trend in the other direction is not the same verdict.
    flipped = replay_summary(table_of(["confirmed"] * 3, slopes=[-1.0, 1.0, 1.0]))
    assert (flipped["kind"], flipped["year"]) == ("closed", 1991)


def test_a_record_shorter_than_the_minimum_gives_an_empty_table():
    table = growing_record(series(np.arange(8.0)), 10)
    assert table.empty and list(table.columns) == TABLE_COLUMNS
    assert replay_summary(table)["kind"] == "open"
    with pytest.raises(ValueError):
        replay_figure(series(np.arange(8.0)), table, "en", x_title="Year", y_title="Value", unit="mm")


def test_unusable_years_are_dropped_and_rows_sorted():
    annual = late_trend().iloc[::-1].reset_index(drop=True)  # newest first
    annual.loc[3, "value"] = np.nan
    table = growing_record(annual, 10)
    assert table["end_year"].is_monotonic_increasing and table["n_years"].iloc[-1] == 29


def test_sentences_and_title_in_both_languages():
    assert set(REPLAY_TEXT["en"]) == set(REPLAY_TEXT["tr"])
    assert all(text.strip() for texts in REPLAY_TEXT.values() for text in texts.values())
    closed = {"kind": "closed", "year": 2004, "n_first": 10, "n_years": 30, "last_year": 2010}
    assert replay_sentence("en", closed) == (
        "With only the first 10 years this could not be told from chance. The case closed in 2004: since "
        "then every extra year has kept the verdict Confirmed."
    )
    assert replay_sentence("tr", closed) == (
        "Yalnızca ilk 10 yılla bu, tesadüften ayırt edilemiyordu. Dosya 2004 yılında kapandı: o günden "
        "beri eklenen her yıl kararı Doğrulandı olarak korudu."
    )
    always = {"kind": "always", "year": 1990, "n_first": 10, "n_years": 31, "last_year": 2020}
    assert replay_sentence("tr", always) == "İlk 10 yıldan itibaren doğrulanmış ve eklenen her yıl bunu korumuş."
    assert replay_sentence("en", always).startswith("Confirmed from the first 10 years on")
    still_open = {"kind": "open", "year": None, "n_first": 10, "n_years": 30, "last_year": 2010}
    assert replay_sentence("en", still_open).startswith("Still an open case after 30 years")
    assert replay_sentence("tr", still_open).startswith("30 yıl sonra hâlâ açık bir dosya")
    # A case that closed only with the last year has no "extra years since then" to point to.
    just_now = dict(closed, year=2010)
    for lang in ("en", "tr"):
        assert "2010" in replay_sentence(lang, just_now) and replay_sentence(lang, just_now) != replay_sentence(lang, closed)
    assert replay_title("en") == "▶ Replay the investigation: watch the verdict as years are added"
    assert replay_title("tr") == "▶ Soruşturmayı baştan izle: yıllar eklendikçe karar nasıl değişiyor"
    assert replay_text("de", "play") == "Play"  # unknown languages fall back to English


def test_figure_has_one_frame_per_record_and_starts_on_the_final_verdict():
    annual = late_trend()
    table = growing_record(annual, 10)
    figure = replay_figure(
        annual, table, "tr", x_title="Yıl", y_title="Değer (mm)", unit="mm", separators=",.", decimals=1,
    )
    assert len(figure.frames) == len(table) == 21
    assert [frame.name for frame in figure.frames] == [str(year) for year in table["end_year"]]
    assert all(len(frame.data) == 4 for frame in figure.frames)
    assert [trace.to_plotly_json() for trace in figure.data] == [
        trace.to_plotly_json() for trace in figure.frames[-1].data
    ]
    assert figure.layout.annotations[0].to_plotly_json() == figure.frames[-1].layout.annotations[0].to_plotly_json()
    first = figure.frames[0]
    assert len(first.data[0].x) == 10 and len(figure.data[0].x) == 30
    assert first.data[2].fill == "tonexty" and first.data[1].fill is None
    assert all(np.array(first.data[1].y) <= np.array(first.data[2].y))  # band low below band high
    # The stamp follows the verdict of each frame, in the board's colours.
    for frame, row in zip(figure.frames, table.itertuples()):
        stamp = frame.layout.annotations[0]
        assert f"1981–{row.end_year}" in stamp.text
        assert stamp.font.color == STAMP_COLOR.get(row.status, "#52514e")
    assert "Doğrulandı" in figure.layout.annotations[0].text and "Delil yok" in first.layout.annotations[0].text
    # Fixed axes over the whole record, Play/Pause buttons and a slider standing on the last year.
    x_low, x_high = figure.layout.xaxis.range
    y_low, y_high = figure.layout.yaxis.range
    assert x_low < 1981 and x_high > 2010
    assert y_low < annual["value"].min() and y_high > annual["value"].max()
    menu = figure.layout.updatemenus[0]
    assert [button.label for button in menu.buttons] == ["Oynat", "Durdur"]
    play = menu.buttons[0].args[1]
    assert play["frame"] == {"duration": 350, "redraw": True} and play["transition"] == {"duration": 0}
    slider = figure.layout.sliders[0]
    assert slider.active == len(table) - 1
    assert [list(step.args[0]) for step in slider.steps] == [[frame.name] for frame in figure.frames]
    assert figure.layout.separators == ",." and figure.layout.height == 400


def test_english_figure_labels():
    annual = strong_trend(15)
    figure = replay_figure(annual, growing_record(annual, 10), "en", x_title="Year", y_title="Value", unit="°C")
    assert [button.label for button in figure.layout.updatemenus[0].buttons] == ["Play", "Pause"]
    assert "Confirmed" in figure.layout.annotations[0].text and "1981–1995" in figure.layout.annotations[0].text
    assert figure.data[0].hovertemplate == "%{y:.2f} °C<extra></extra>"
