"""Record check: is the last year of the period one of the highest or lowest, and a stripe per year.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. Reviewed by Claude Fable; its findings are applied.

The case file's last year is the newest complete year of the chosen period. When it is among the
three highest or the three lowest years of that period, one sentence says so ("2025 is the warmest
of 45 years"). A strip of coloured stripes shows every year at once, from the lowest (blue, or brown
for water) to the highest (red, or blue-green for water), so a change stands out before reading any
number; a year that was not used stays an empty slot. A record year is a fact about the data, not a
trend: the trend test above stays the verdict.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

RANK_SHOWN = 3  # the last year gets a sentence when it is among the 3 highest or 3 lowest years
MIN_YEARS = 10  # fewer years than this: no record sentence (too few years to call anything a record)
# The app's aerosol data follow another satellite (VIIRS) from April 2022, which reads differently:
# a later year is never ranked against the earlier ones (the time map leaves those years out too).
RECORD_LAST_YEAR = {"aod": 2021}

# Water and greenness: more is shown blue-green, less brown; everything else: more red, less blue
WET_VARIABLES = {"precipitation", "snowfall", "ndvi", "tree_cover", "groundwater"}
WARM_SCALE = [[0.0, "#2c62a8"], [0.5, "#f4f1ea"], [1.0, "#b2302b"]]
WET_SCALE = [[0.0, "#8c5a2b"], [0.5, "#f4f1ea"], [1.0, "#1f7a8c"]]

# One sentence pair per measurement: (highest, lowest) x (rank 1, rank 2 or 3)
RECORD_TEXT = {
    "en": {
        "ords": {2: "2nd", 3: "3rd"},
        "sentences": {
            "air_temperature": (("📌 {year} is the warmest of {n} years ({start}–{end}).",
                                 "📌 {year} is the {ord} warmest of {n} years ({start}–{end})."),
                                ("📌 {year} is the coldest of {n} years ({start}–{end}).",
                                 "📌 {year} is the {ord} coldest of {n} years ({start}–{end}).")),
            "hot_days": (("📌 {year} had the most hot days of the {n} years ({start}–{end}).",
                          "📌 {year} had the {ord} most hot days of the {n} years ({start}–{end})."),
                         ("📌 {year} had the fewest hot days of the {n} years ({start}–{end}).",
                          "📌 {year} had the {ord} fewest hot days of the {n} years ({start}–{end}).")),
            "precipitation": (("📌 {year} is the wettest of {n} years ({start}–{end}).",
                               "📌 {year} is the {ord} wettest of {n} years ({start}–{end})."),
                              ("📌 {year} is the driest of {n} years ({start}–{end}).",
                               "📌 {year} is the {ord} driest of {n} years ({start}–{end}).")),
            "snowfall": (("📌 {year} is the snowiest of {n} years ({start}–{end}).",
                          "📌 {year} is the {ord} snowiest of {n} years ({start}–{end})."),
                         ("📌 {year} is the least snowy of {n} years ({start}–{end}).",
                          "📌 {year} is the {ord} least snowy of {n} years ({start}–{end}).")),
            "aod": (("📌 {year} is the haziest of {n} years ({start}–{end}).",
                     "📌 {year} is the {ord} haziest of {n} years ({start}–{end})."),
                    ("📌 {year} is the clearest of {n} years ({start}–{end}).",
                     "📌 {year} is the {ord} clearest of {n} years ({start}–{end}).")),
            "groundwater": (("📌 {year} had the most groundwater of the {n} years ({start}–{end}).",
                             "📌 {year} had the {ord} most groundwater of the {n} years ({start}–{end})."),
                            ("📌 {year} had the least groundwater of the {n} years ({start}–{end}).",
                             "📌 {year} had the {ord} least groundwater of the {n} years ({start}–{end}).")),
        },
        "generic": (("📌 {year} had the highest value of the {n} years ({start}–{end}).",
                     "📌 {year} had the {ord} highest value of the {n} years ({start}–{end})."),
                    ("📌 {year} had the lowest value of the {n} years ({start}–{end}).",
                     "📌 {year} had the {ord} lowest value of the {n} years ({start}–{end}).")),
        "note": "A record year is not a trend by itself: the verdict above comes from all the years.",
        "stripes": "Every year as one stripe: {low} for the lowest years, {high} for the highest.",
        "gap": " An empty slot is a year that was not used.",
        "colour_warm": ("blue", "red"),
        "colour_wet": ("brown", "blue-green"),
    },
    "tr": {
        "ords": {2: "2.", 3: "3."},
        "sentences": {
            "air_temperature": (("📌 {year}, {n} yılın en sıcak yılı ({start}–{end}).",
                                 "📌 {year}, {n} yılın en sıcak {ord} yılı ({start}–{end})."),
                                ("📌 {year}, {n} yılın en soğuk yılı ({start}–{end}).",
                                 "📌 {year}, {n} yılın en soğuk {ord} yılı ({start}–{end}).")),
            "hot_days": (("📌 {year}, {n} yıl içinde en çok sıcak gün görülen yıl ({start}–{end}).",
                          "📌 {year}, {n} yıl içinde en çok sıcak gün görülen {ord} yıl ({start}–{end})."),
                         ("📌 {year}, {n} yıl içinde en az sıcak gün görülen yıl ({start}–{end}).",
                          "📌 {year}, {n} yıl içinde en az sıcak gün görülen {ord} yıl ({start}–{end}).")),
            "precipitation": (("📌 {year}, {n} yılın en yağışlı yılı ({start}–{end}).",
                               "📌 {year}, {n} yılın en yağışlı {ord} yılı ({start}–{end})."),
                              ("📌 {year}, {n} yılın en kurak yılı ({start}–{end}).",
                               "📌 {year}, {n} yılın en kurak {ord} yılı ({start}–{end}).")),
            "snowfall": (("📌 {year}, {n} yılın en karlı yılı ({start}–{end}).",
                          "📌 {year}, {n} yılın en karlı {ord} yılı ({start}–{end})."),
                         ("📌 {year}, {n} yılın en az kar yağan yılı ({start}–{end}).",
                          "📌 {year}, {n} yılın en az kar yağan {ord} yılı ({start}–{end}).")),
            "aod": (("📌 {year}, {n} yılın en puslu yılı ({start}–{end}).",
                     "📌 {year}, {n} yılın en puslu {ord} yılı ({start}–{end})."),
                    ("📌 {year}, {n} yılın havası en açık yılı ({start}–{end}).",
                     "📌 {year}, {n} yılın havası en açık {ord} yılı ({start}–{end}).")),
            "groundwater": (("📌 {year}, {n} yıl içinde yeraltı suyunun en çok olduğu yıl ({start}–{end}).",
                             "📌 {year}, {n} yıl içinde yeraltı suyunun en çok olduğu {ord} yıl ({start}–{end})."),
                            ("📌 {year}, {n} yıl içinde yeraltı suyunun en az olduğu yıl ({start}–{end}).",
                             "📌 {year}, {n} yıl içinde yeraltı suyunun en az olduğu {ord} yıl ({start}–{end}).")),
        },
        "generic": (("📌 {year}, {n} yıl içinde değerin en yüksek olduğu yıl ({start}–{end}).",
                     "📌 {year}, {n} yıl içinde değerin en yüksek olduğu {ord} yıl ({start}–{end})."),
                    ("📌 {year}, {n} yıl içinde değerin en düşük olduğu yıl ({start}–{end}).",
                     "📌 {year}, {n} yıl içinde değerin en düşük olduğu {ord} yıl ({start}–{end}).")),
        "note": "Rekor bir yıl tek başına trend değildir: yukarıdaki karar bütün yıllardan çıkıyor.",
        "stripes": "Her yıl bir şerit: en düşük yıllar {low}, en yüksek yıllar {high}.",
        "gap": " Boş kalan yer, kullanılmayan bir yıl.",
        "colour_warm": ("mavi", "kırmızı"),
        "colour_wet": ("kahverengi", "mavi-yeşil"),
    },
}


def record_text(lang: str) -> dict:
    return RECORD_TEXT.get(lang, RECORD_TEXT["en"])


def last_year_rank(annual: pd.DataFrame) -> dict | None:
    """Where the last year of ``annual`` (columns year, value) ranks, or None without enough years.

    Returns year, value, n (years with a value), start, end, high (1 = highest), low (1 = lowest)
    and ties (how many other years have exactly the same value). Equal values share the better rank.
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
        "ties": int(np.sum(values == last)) - 1,
    }


def record_sentence(lang: str, info: dict | None, variable_key: str) -> str | None:
    """'📌 2025 is the warmest of 45 years (1981–2025).' when the last year is among the top or bottom
    three; None otherwise: a middle year, a flat record, a value shared by several other years, or a
    year after a change of satellite (RECORD_LAST_YEAR)."""
    if not info or info["high"] == info["low"] == 1:  # a flat record has no record year
        return None
    if info.get("ties", 0) >= RANK_SHOWN:  # e.g. no snow in many years: not a record of its own
        return None
    if info["year"] > RECORD_LAST_YEAR.get(variable_key, info["year"]):
        return None
    if info["high"] <= RANK_SHOWN and info["high"] <= info["low"]:
        side, rank = 0, info["high"]
    elif info["low"] <= RANK_SHOWN:
        side, rank = 1, info["low"]
    else:
        return None
    text = record_text(lang)
    pair = text["sentences"].get(variable_key, text["generic"])[side]
    fields = {"year": info["year"], "n": info["n"], "start": info["start"], "end": info["end"]}
    if rank == 1:
        return pair[0].format(**fields)
    return pair[1].format(ord=text["ords"][rank], **fields)


def stripes_caption(lang: str, variable_key: str, annual: pd.DataFrame | None = None) -> str:
    """What the colours mean; with ``annual``, also that an empty slot is a year that was not used."""
    text = record_text(lang)
    low, high = text["colour_wet"] if variable_key in WET_VARIABLES else text["colour_warm"]
    caption = text["stripes"].format(low=low, high=high)
    if annual is not None:
        years = annual.dropna(subset=["value"])["year"].astype(int)
        if len(years) and len(years) < years.max() - years.min() + 1:
            caption += text["gap"]
    return caption


def stripe_positions(values: np.ndarray) -> np.ndarray:
    """Colour position of each value in [-1, 1]: the mean is 0, the lowest year -1 and the highest +1.

    Each side is scaled on its own, so a skewed record (one very wet year among many dry ones) still
    shows its lowest years in the low colour. NaN stays NaN (an empty slot).
    """
    known = values[np.isfinite(values)]
    if not len(known):
        return np.full_like(values, np.nan, dtype=float)
    centre = float(np.mean(known))
    below = centre - float(np.min(known))
    above = float(np.max(known)) - centre
    positions = np.full_like(values, np.nan, dtype=float)
    for index, value in enumerate(values):
        if not math.isfinite(value):
            continue
        if value >= centre:
            positions[index] = (value - centre) / above if above > 0 else 0.0
        else:
            positions[index] = (value - centre) / below if below > 0 else 0.0
    return positions


def stripes_figure(annual: pd.DataFrame, variable_key: str, unit: str, separators: str = ".,",
                   decimals: int = 2) -> go.Figure:
    """One coloured stripe per year of the period's range, centred on its mean (no axes, about 70 px
    tall); a year without a value stays an empty slot instead of being covered by its neighbours."""
    table = annual.dropna(subset=["value"]).sort_values("year")
    if len(table):
        years = list(range(int(table["year"].min()), int(table["year"].max()) + 1))
        values = table.set_index("year")["value"].astype(float).reindex(years).to_numpy()
    else:
        years, values = [], np.array([], dtype=float)
    positions = stripe_positions(values)
    scale = WET_SCALE if variable_key in WET_VARIABLES else WARM_SCALE
    figure = go.Figure(
        go.Heatmap(
            z=[positions.tolist()], x=years, y=[""], zmin=-1, zmax=1, customdata=[values.tolist()],
            colorscale=scale, showscale=False, xgap=0, ygap=0, hoverongaps=False,
            hovertemplate=f"%{{x}}: %{{customdata:.{int(decimals)}f}} {unit}<extra></extra>",
        )
    )
    figure.update_layout(
        height=70, margin={"l": 6, "r": 6, "t": 4, "b": 18}, separators=separators,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": False, "zeroline": False, "tickfont": {"size": 10}, "nticks": 8, "fixedrange": True},
        yaxis={"visible": False, "fixedrange": True},
    )
    return figure
