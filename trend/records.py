"""Record check: is the last year of the period one of the highest or lowest, and a stripe per year.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The case file's last year is the newest complete year of the chosen period. When it is among the
three highest or the three lowest years of that period, one sentence says so ("2025 is the warmest
of 45 years"), in the words the time map uses. A strip of coloured stripes shows every year at once,
from the lowest (blue, or brown for water) to the highest (red, or blue-green for water), so a
change stands out before reading any number. A record year is a fact about the data, not a trend:
the trend test above stays the verdict.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

RANK_SHOWN = 3  # the last year gets a sentence when it is among the 3 highest or 3 lowest years
MIN_YEARS = 10  # fewer years than this: no record sentence (too few years to call anything a record)

# Water and greenness: more is shown blue-green, less brown; everything else: more red, less blue
WET_VARIABLES = {"precipitation", "snowfall", "ndvi", "tree_cover", "groundwater"}
WARM_SCALE = [[0.0, "#2c62a8"], [0.5, "#f4f1ea"], [1.0, "#b2302b"]]
WET_SCALE = [[0.0, "#8c5a2b"], [0.5, "#f4f1ea"], [1.0, "#1f7a8c"]]

RECORD_TEXT = {
    "en": {
        "ords": {2: "2nd", 3: "3rd"},
        "first": "📌 {year} is the {word} of {n} years ({start}–{end}).",
        "other": "📌 {year} is the {ord} {word} of {n} years ({start}–{end}).",
        "note": "A record year is not a trend by itself: the verdict above comes from all the years.",
        "stripes": "Every year as one stripe: {low} for the lowest years, {high} for the highest.",
        "colour_warm": ("blue", "red"),
        "colour_wet": ("brown", "blue-green"),
        "words": {
            "air_temperature": ("warmest", "coldest"),
            "hot_days": ("year with the most hot days", "year with the fewest hot days"),
            "precipitation": ("wettest", "driest"),
            "snowfall": ("snowiest", "least snowy"),
            "aod": ("haziest", "clearest"),
            "groundwater": ("year with the most groundwater", "year with the least groundwater"),
        },
        "generic": ("year with the highest value", "year with the lowest value"),
    },
    "tr": {
        "ords": {2: "2.", 3: "3."},
        "first": "📌 {year}, {n} yılın {word} yılı ({start}–{end}).",
        "other": "📌 {year}, {n} yılın {word} {ord} yılı ({start}–{end}).",
        "note": "Rekor bir yıl tek başına trend değildir: yukarıdaki karar bütün yıllardan çıkıyor.",
        "stripes": "Her yıl bir şerit: en düşük yıllar {low}, en yüksek yıllar {high}.",
        "colour_warm": ("mavi", "kırmızı"),
        "colour_wet": ("kahverengi", "mavi-yeşil"),
        "words": {
            "air_temperature": ("en sıcak", "en soğuk"),
            "hot_days": ("en çok sıcak gün olan", "en az sıcak gün olan"),
            "precipitation": ("en yağışlı", "en kurak"),
            "snowfall": ("en karlı", "en az karlı"),
            "aod": ("en puslu", "en açık havalı"),
            "groundwater": ("yeraltı suyunun en çok olduğu", "yeraltı suyunun en az olduğu"),
        },
        "generic": ("değerin en yüksek olduğu", "değerin en düşük olduğu"),
    },
}


def record_text(lang: str) -> dict:
    return RECORD_TEXT.get(lang, RECORD_TEXT["en"])


def last_year_rank(annual: pd.DataFrame) -> dict | None:
    """Where the last year of ``annual`` (columns year, value) ranks, or None without enough years.

    Returns year, value, n (years with a value), start, end, high (1 = highest) and low (1 = lowest).
    Equal values share the better rank, so a tie for the record still counts as the record.
    """
    table = annual.dropna(subset=["value"]).sort_values("year")
    if len(table) < MIN_YEARS:
        return None
    values = table["value"].to_numpy(dtype=float)
    last = values[-1]
    return {
        "year": int(table["year"].iloc[-1]),
        "value": float(last),
        "n": int(len(values)),
        "start": int(table["year"].iloc[0]),
        "end": int(table["year"].iloc[-1]),
        "high": int(np.sum(values > last)) + 1,
        "low": int(np.sum(values < last)) + 1,
    }


def record_sentence(lang: str, info: dict | None, variable_key: str) -> str | None:
    """'📌 2025 is the warmest of 45 years (1981–2025).' when the last year is among the top or bottom
    three; None otherwise (also when every year has the same value)."""
    if not info or info["high"] == info["low"] == 1:  # a flat record has no record year
        return None
    text = record_text(lang)
    high_word, low_word = text["words"].get(variable_key, text["generic"])
    if info["high"] <= RANK_SHOWN and info["high"] <= info["low"]:
        rank, word = info["high"], high_word
    elif info["low"] <= RANK_SHOWN:
        rank, word = info["low"], low_word
    else:
        return None
    fields = {"year": info["year"], "n": info["n"], "start": info["start"], "end": info["end"], "word": word}
    if rank == 1:
        return text["first"].format(**fields)
    return text["other"].format(ord=text["ords"][rank], **fields)


def stripes_caption(lang: str, variable_key: str) -> str:
    text = record_text(lang)
    low, high = text["colour_wet"] if variable_key in WET_VARIABLES else text["colour_warm"]
    return text["stripes"].format(low=low, high=high)


def stripes_figure(annual: pd.DataFrame, variable_key: str, unit: str, separators: str = ".,",
                   decimals: int = 2) -> go.Figure:
    """One coloured stripe per year, centred on the period's mean (no axes, about 70 px tall)."""
    table = annual.dropna(subset=["value"]).sort_values("year")
    values = table["value"].to_numpy(dtype=float)
    years = table["year"].astype(int).tolist()
    centre = float(np.mean(values)) if len(values) else 0.0
    spread = float(np.max(np.abs(values - centre))) if len(values) else 0.0
    if not math.isfinite(spread) or spread == 0:
        spread = 1.0  # a flat series: every stripe the neutral middle colour
    scale = WET_SCALE if variable_key in WET_VARIABLES else WARM_SCALE
    figure = go.Figure(
        go.Heatmap(
            z=[list(values)], x=years, y=[""], zmin=centre - spread, zmax=centre + spread,
            colorscale=scale, showscale=False, xgap=0, ygap=0,
            hovertemplate=f"%{{x}}: %{{z:.{int(decimals)}f}} {unit}<extra></extra>",
        )
    )
    figure.update_layout(
        height=70, margin={"l": 6, "r": 6, "t": 4, "b": 18}, separators=separators,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": False, "zeroline": False, "tickfont": {"size": 10}, "nticks": 8, "fixedrange": True},
        yaxis={"visible": False, "fixedrange": True},
    )
    return figure
