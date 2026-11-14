"""How does this place compare? One measurement's trend in every prepared region, ranked.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

A case file tests one region. This module runs the same test on the same measurement in every prepared
region, each over its own full record and with the rules of the investigation board (``board_verdict`` in
trend/world.py), and ranks the regions by their trend per decade. ``region_ranking`` builds the table,
``ranking_figure`` draws it as horizontal bars in the colours of the season chart (trend/seasonal.py) with
the current region outlined, and ``ranking_sentence`` says in plain words where the current region stands.
Regions that cannot be tested (no data, too few complete years, no snow, no hot days) are left out of the
ranking and kept with their stamp in ``table.attrs["untested"]``; ``untested_text`` lists them.
"""
from __future__ import annotations

import math
from typing import Callable, Mapping

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from trend.charts import AXIS, FONT_FAMILY, GRIDLINE, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY
from trend.fetch import load_processed
from trend.i18n import ci_bounds, num, p_phrase, status_text
from trend.regions import REGIONS
from trend.seasonal import OTHER_COLOR, STAMP_COLORS
from trend.variables import get_variable
from trend.world import SHORT_NAMES, TESTED, board_verdict, place_name

COLUMNS = ["region", "status", "slope_per_decade", "ci_low", "ci_high", "p_value", "start_year", "end_year"]
BAR_HEIGHT = 24  # pixels per region in the chart
MIN_HEIGHT = 220
MARGIN = {"l": 8, "r": 16, "t": 12, "b": 48}  # the margins of seasonal.season_figure
OUTLINE_COLOR = TEXT_PRIMARY  # thick dark outline around the current region's bar
OUTLINE_WIDTH = 3
WHY_STATUSES = ("no_hot", "no_snow", "insufficient", "open")  # statuses with their own "why" sentence

COMPARE_TEXT = {
    "en": {
        "title": "How does this place compare?",
        "intro": (
            "Every prepared region gets the same test over its own full record, so the rates can be compared "
            "side by side."
        ),
        "note": (
            "Blue: Confirmed · orange: Disputed or Weak clue · grey: No evidence. Thin lines: 95% confidence "
            "interval; bars whose thin lines overlap may in truth be in either order, and an interval that "
            "runs off the chart is cut (hover for its ends). Outlined bar: this region. The period chosen "
            "above does not apply here: every region uses its full record, and record lengths differ "
            "between measurements (for example NO₂ from 2005, groundwater from 2004)."
        ),
        "x_title": "{unit} per decade",
        "hover": (
            "{region}<br>{rate} {unit} per decade<br>95% CI {low} to {high}<br>{stamp} ({p}) · {start}–{end}"
        ),
        "rank_top": (
            "Over the full records, {owner} rate ({rate} {unit} per decade) is the highest of {n} regions."
        ),
        "rank_bottom": (
            "Over the full records, {owner} rate ({rate} {unit} per decade) is the lowest of {n} regions."
        ),
        "rank_middle": (
            "Over the full records, {owner} rate ({rate} {unit} per decade) is the {ordinal} highest of {n} "
            "regions."
        ),
        "rank_shared": (
            "Over the full records, {owner} rate ({rate} {unit} per decade) shares {ordinal} place among {n} "
            "regions."
        ),
        "caution": "Its own trend is not Confirmed ({stamp}), so its place in this order could be chance.",
        "period_same": "All regions: {start}–{end}.",
        "period_range": "Records between {start} and {end}.",
        "extremes": "Highest: {top} ({top_rate}); lowest: {bottom} ({bottom_rate}).",
        "highest_only": "Highest: {top} ({top_rate}).",
        "lowest_only": "Lowest: {bottom} ({bottom_rate}).",
        "summary": (
            "Of the {n} regions tested over their full records, the highest rate is in {top} ({top_rate} "
            "{unit} per decade) and the lowest in {bottom} ({bottom_rate})."
        ),
        "why_no_hot": "This ranking leaves out {place}: days above 30 °C practically never happen there.",
        "why_no_snow": "This ranking leaves out {place}: it practically never snows there.",
        "why_insufficient": (
            "This ranking leaves out {place}: the record there has too few complete years for the test."
        ),
        "why_open": "This ranking leaves out {place}: this measurement has not been prepared there yet.",
        "why_other": "This ranking leaves out {place}.",
        "rank_one": (
            "Only {place} can be tested over the full record for this measurement, so there is nothing to "
            "compare yet."
        ),
        "rank_none": "No prepared region can be tested for this measurement yet, so there is no ranking.",
        "untested": "Not ranked: {regions}.",
        "and": " and ",
    },
    "tr": {
        "title": "Bu bölge diğerleriyle nasıl kıyaslanıyor?",
        "intro": (
            "Hazır bölgelerin her biri kendi kaydının tamamı üzerinden aynı testten geçer; böylece değişim "
            "hızları yan yana kıyaslanabilir."
        ),
        "note": (
            "Mavi: Doğrulandı · turuncu: Tartışmalı ya da Zayıf ipucu · gri: Delil yok. İnce çizgiler: %95 "
            "güven aralığı; ince çizgileri örtüşen çubukların gerçek sırası farklı olabilir, grafiğin dışına "
            "taşan bir aralık kesilir (uçları için üzerine gel). Çerçeveli çubuk: bu bölge. Yukarıda seçilen "
            "dönem burada kullanılmaz: her bölgede kaydın tamamı kullanılır ve kayıt uzunlukları ölçümden "
            "ölçüme değişir (örneğin NO₂ 2005'ten, yeraltı suyu 2004'ten başlar)."
        ),
        "x_title": "{unit} / 10 yıl",
        "hover": (
            "{region}<br>on yılda {rate} {unit}<br>%95 güven aralığı: {low} ile {high}<br>{stamp} ({p}) · "
            "{start}–{end}"
        ),
        "rank_top": (
            "Kayıtların tamamına bakıldığında {place}, on yılda {rate} {unit} ile {n} bölge içinde en yüksek "
            "değere sahip."
        ),
        "rank_bottom": (
            "Kayıtların tamamına bakıldığında {place}, on yılda {rate} {unit} ile {n} bölge içinde en düşük "
            "değere sahip."
        ),
        "rank_middle": (
            "Kayıtların tamamına bakıldığında {place}, on yılda {rate} {unit} ile {n} bölge içinde {ordinal} "
            "sırada."
        ),
        "rank_shared": (
            "Kayıtların tamamına bakıldığında {place}, on yılda {rate} {unit} ile {n} bölge içinde {ordinal} "
            "sırayı paylaşıyor."
        ),
        "caution": "Bu bölgenin kendi trendi doğrulanmadı ({stamp}); sıradaki yeri tesadüf olabilir.",
        "period_same": "Tüm bölgeler: {start}–{end}.",
        "period_range": "Kayıtlar {start} ile {end} arasında.",
        "extremes": "En yüksek: {top} ({top_rate}); en düşük: {bottom} ({bottom_rate}).",
        "highest_only": "En yüksek: {top} ({top_rate}).",
        "lowest_only": "En düşük: {bottom} ({bottom_rate}).",
        "summary": (
            "Kayıtlarının tamamı üzerinden test edilen {n} bölge içinde en yüksek değer {top} bölgesinde (on "
            "yılda {top_rate} {unit}), en düşük değer {bottom} bölgesinde ({bottom_rate})."
        ),
        "why_no_hot": "{place} bu sıralamada yok: orada 30 °C'yi geçen gün neredeyse hiç olmuyor.",
        "why_no_snow": "{place} bu sıralamada yok: orada neredeyse hiç kar yağmıyor.",
        "why_insufficient": "{place} bu sıralamada yok: oradaki kayıtta test için yeterince tam yıl yok.",
        "why_open": "{place} bu sıralamada yok: bu ölçüm için orada henüz hazır bir kayıt yok.",
        "why_other": "{place} bu sıralamada yok.",
        "rank_one": (
            "Bu ölçümde kaydın tamamı üzerinden yalnızca {place} test edilebiliyor; şimdilik kıyaslanacak "
            "başka bölge yok."
        ),
        "rank_none": "Bu ölçüm için henüz test edilebilen hazır bölge yok; sıralama yapılamıyor.",
        "untested": "Sıralamaya girmeyenler: {regions}.",
        "and": " ve ",
    },
}


def compare_text(lang: str, key: str, **values) -> str:
    """Text of this section in the interface language (English for an unknown language)."""
    text = COMPARE_TEXT.get(lang, COMPARE_TEXT["en"])[key]
    return text.format(**values) if values else text


def region_ranking(
    variable_key: str, loader: Callable[[str, str], pd.DataFrame | None] = load_processed
) -> pd.DataFrame:
    """The trend of one measurement in every prepared region, each over its full record, highest first.

    For each region in ``REGIONS`` the monthly series comes from ``loader(region_key, variable_key)`` and
    the trend and stamp from ``board_verdict``, the rules of the investigation board and the World board.
    Returns one row per tested region (Confirmed, Disputed, Weak clue or No evidence) with ``region``,
    ``status``, ``slope_per_decade``, ``ci_low`` and ``ci_high`` (95% interval, per decade), ``p_value``,
    ``start_year`` and ``end_year``, sorted by ``slope_per_decade`` from highest to lowest (equal rates keep
    the order of ``REGIONS``). The other regions are kept as ``(region, status)`` pairs in
    ``table.attrs["untested"]``: "open" when the loader returns None, otherwise "insufficient", "no_snow"
    or "no_hot". The measurement is kept in ``table.attrs["variable_key"]``.
    """
    get_variable(variable_key)  # a clear error for an unknown measurement
    rows, untested = [], []
    for region_key in REGIONS:
        verdict = board_verdict(loader(region_key, variable_key), variable_key)
        result = verdict.result
        if result is None or verdict.status not in TESTED:
            untested.append((region_key, verdict.status))
            continue
        low, high = result.ci_per_decade
        rows.append({
            "region": region_key, "status": verdict.status,
            "slope_per_decade": float(result.slope_per_decade), "ci_low": float(low), "ci_high": float(high),
            "p_value": float(result.p_value), "start_year": int(result.start_year),
            "end_year": int(result.end_year),
        })
    table = pd.DataFrame(rows, columns=COLUMNS).astype({
        "region": str, "status": str, "slope_per_decade": float, "ci_low": float, "ci_high": float,
        "p_value": float, "start_year": int, "end_year": int,
    })
    table = table.sort_values("slope_per_decade", ascending=False, kind="stable").reset_index(drop=True)
    table.attrs["untested"] = untested
    table.attrs["variable_key"] = variable_key
    return table


def _short(names: Mapping[str, str], region_key: str) -> str:
    """Short display name from the names the app passes, falling back to the English short name."""
    return names.get(region_key) or SHORT_NAMES["en"].get(region_key, region_key)


def _place(lang: str, region_key: str, names: Mapping[str, str]) -> str:
    """Name inside a sentence: ``place_name`` ("the Amazon", "the Sahel", "the Alps" in English)."""
    if region_key in SHORT_NAMES.get(lang, SHORT_NAMES["en"]):
        return place_name(lang, region_key)
    return _short(names, region_key)


def _owner(place: str) -> str:
    """English possessive: "Istanbul's", "the Amazon's", but "the Alps'" and "Los Angeles'"."""
    return f"{place}'" if place.endswith("s") else f"{place}'s"


def ordinal(lang: str, n: int) -> str:
    """'1st', '2nd', '3rd', '4th', '11th', '21st' in English; '4.' in Turkish."""
    if lang == "tr":
        return f"{n}."
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _join(lang: str, names: list[str]) -> str:
    """'A', 'A and B', 'A, B and C' ('ve' in Turkish)."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + compare_text(lang, "and") + names[-1]


def figure_height(n_regions: int) -> int:
    """About 24 px per bar plus the margins, never below ``MIN_HEIGHT``."""
    return max(MIN_HEIGHT, BAR_HEIGHT * n_regions + MARGIN["t"] + MARGIN["b"])


def ranking_figure(
    table: pd.DataFrame, lang: str, current_region: str, names: Mapping[str, str], unit: str,
    separators: str = ".,", decimals: int = 2,
) -> go.Figure:
    """Horizontal bars of every tested region's trend per decade, highest on top.

    Bars are blue for Confirmed, orange for Disputed or Weak clue and grey for No evidence, with the 95%
    interval as error bars and the value written past the end of each interval. The current region's bar
    gets a thick dark outline and its axis label and value are bold. A thin line marks zero. ``names`` maps
    region keys to short display names (the app passes ``SHORT_NAMES[lang]``); ``separators`` gives the
    decimal comma in Turkish.
    """
    regions = [str(region) for region in table["region"]]
    plain = [_short(names, region) for region in regions]
    current = [region == current_region for region in regions]
    labels = [f"<b>{name}</b>" if is_current else name for name, is_current in zip(plain, current)]
    slope = pd.to_numeric(table["slope_per_decade"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(table["ci_low"], errors="coerce").to_numpy(dtype=float)
    high = pd.to_numeric(table["ci_high"], errors="coerce").to_numpy(dtype=float)
    low, high = np.where(np.isfinite(low), low, slope), np.where(np.isfinite(high), high, slope)
    statuses = [str(status) for status in table["status"]]
    tested = np.isfinite(slope)

    hover = []
    rows = zip(plain, slope, low, high, statuses, table["p_value"], table["start_year"], table["end_year"])
    for name, value, lo, hi, status, p, start, end in rows:
        if not math.isfinite(value):
            hover.append("")
            continue
        hover.append(compare_text(
            lang, "hover", region=name, rate=num(value, lang, decimals, signed=True), unit=unit,
            low=ci_bounds(lo, hi, lang, decimals)[0], high=ci_bounds(lo, hi, lang, decimals)[1],
            stamp=status_text(lang, status)[0], p=p_phrase(float(p), lang), start=start, end=end,
        ))

    colors = [STAMP_COLORS.get(status, OTHER_COLOR) for status in statuses]
    fig = go.Figure(
        go.Bar(
            x=slope, y=labels, orientation="h", width=0.6,
            marker={
                "color": colors,
                "line": {"color": OUTLINE_COLOR, "width": [OUTLINE_WIDTH if c else 0 for c in current]},
            },
            error_x={
                "type": "data", "symmetric": False, "array": high - slope, "arrayminus": slope - low,
                "color": TEXT_SECONDARY, "thickness": 1.5, "width": 5,
            },
            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", showlegend=False,
        )
    )

    core = [0.0, *slope[tested]]
    core_left, core_right = min(core), max(core)
    core_span = (core_right - core_left) or 1.0
    # Intervals are shown up to 60% of the rates' spread past the extreme rates; longer ones are cut
    left = max(min([0.0, *low[tested]]), core_left - 0.6 * core_span)
    right = min(max([0.0, *high[tested]]), core_right + 0.6 * core_span)
    span = (right - left) or 1.0
    pad, room = 0.02 * span, 0.24 * span  # room for the value written past the end of each interval
    for label, value, lo, hi, is_current in zip(labels, slope, low, high, current):
        if not math.isfinite(value):
            continue
        up = value >= 0
        text = num(value, lang, decimals, signed=True)
        fig.add_annotation(
            x=(min(hi, right) + pad) if up else (max(lo, left) - pad), y=label,
            text=f"<b>{text}</b>" if is_current else text,
            xanchor="left" if up else "right", showarrow=False, font={"color": TEXT_PRIMARY, "size": 12},
        )
    fig.add_vline(x=0, line_color=TEXT_SECONDARY, line_width=1)

    negative, positive = bool((slope[tested] < 0).any()), bool((slope[tested] >= 0).any())
    x_range = [
        left - (room if negative else 0.04 * span),
        right + (room if positive or not tested.any() else 0.04 * span),
    ]
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT_FAMILY, "color": TEXT_SECONDARY, "size": 13},
        separators=separators,
        hovermode="closest",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT_PRIMARY}},
        margin=dict(MARGIN),
        height=figure_height(len(table)),
        showlegend=False,
    )
    fig.update_xaxes(
        title=compare_text(lang, "x_title", unit=unit), range=x_range, gridcolor=GRIDLINE, gridwidth=1,
        linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False,
    )
    fig.update_yaxes(
        showgrid=False, linecolor=AXIS, automargin=True, categoryorder="array", categoryarray=labels,
        autorange="reversed",
    )
    return fig


def ranking_sentence(
    lang: str, table: pd.DataFrame, current_region: str, names: Mapping[str, str], unit: str, decimals: int
) -> str:
    """One or two plain sentences: where the current region's rate stands among the tested regions.

    "Over the full records, Istanbul's rate (+0.55 °C per decade) is the 4th highest of 11 regions. Highest:
    Medina (+0.63); lowest: the Amazon (+0.12)." The first and the last region are called "the highest" and
    "the lowest", also when every rate is negative (the numbers are signed, so that stays unambiguous). A
    current region that is not in the table gets the reason from its stamp in ``table.attrs["untested"]``
    (no hot days, no snow, too few years, no prepared record) and the highest and lowest are still named.
    With fewer than two tested regions there is only a short sentence. ``unit`` is the unit of one yearly
    value, as in the case file; numbers use ``decimals`` and the decimal comma in Turkish.
    """
    regions = [str(region) for region in table["region"]]
    slopes = [float(value) for value in table["slope_per_decade"]]
    n = len(regions)
    if n == 0:
        return compare_text(lang, "rank_none")
    if n == 1:
        return compare_text(lang, "rank_one", place=_place(lang, regions[0], names))

    def rate(i: int) -> str:
        return num(slopes[i], lang, decimals, signed=True)

    statuses = [str(status) for status in table["status"]]

    def rate_stamp(i: int) -> str:
        """'+0.31, No evidence' for a highest or lowest region whose own trend is not Confirmed."""
        if statuses[i] == "confirmed":
            return rate(i)
        return f"{rate(i)}, {status_text(lang, statuses[i])[0]}"

    top, bottom = _place(lang, regions[0], names), _place(lang, regions[-1], names)
    starts, ends = list(table["start_year"]), list(table["end_year"])
    if len(set(starts)) == 1 and len(set(ends)) == 1:
        period = compare_text(lang, "period_same", start=starts[0], end=ends[0])
    else:
        period = compare_text(lang, "period_range", start=min(starts), end=max(ends))
    if current_region in regions:
        i = regions.index(current_region)
        place = _place(lang, current_region, names)
        values = {"place": place, "owner": _owner(place), "rate": rate(i), "unit": unit, "n": n}
        shown = [round(value, int(decimals)) for value in slopes]  # the rates as the reader sees them
        higher = sum(value > shown[i] for value in shown)
        lower = sum(value < shown[i] for value in shown)
        shared = shown.count(shown[i]) > 1
        if shared:
            first = compare_text(lang, "rank_shared", ordinal=ordinal(lang, higher + 1), **values)
            second = compare_text(
                lang, "extremes", top=top, top_rate=rate_stamp(0), bottom=bottom, bottom_rate=rate_stamp(n - 1)
            )
        elif higher == 0:
            first = compare_text(lang, "rank_top", **values)
            second = compare_text(lang, "lowest_only", bottom=bottom, bottom_rate=rate_stamp(n - 1))
        elif lower == 0:
            first = compare_text(lang, "rank_bottom", **values)
            second = compare_text(lang, "highest_only", top=top, top_rate=rate_stamp(0))
        else:
            first = compare_text(lang, "rank_middle", ordinal=ordinal(lang, higher + 1), **values)
            second = compare_text(
                lang, "extremes", top=top, top_rate=rate_stamp(0), bottom=bottom, bottom_rate=rate_stamp(n - 1)
            )
        status = str(table["status"].iloc[i])
        caution = "" if status == "confirmed" else " " + compare_text(
            lang, "caution", stamp=status_text(lang, status)[0])
        return f"{first}{caution} {second} {period}"

    summary = compare_text(
        lang, "summary", n=n, top=top, top_rate=rate(0), bottom=bottom, bottom_rate=rate(n - 1), unit=unit
    )
    status = dict(table.attrs.get("untested", [])).get(current_region)
    if status is None:  # not a prepared region (for example a custom area): the highest and lowest only
        return summary
    key = f"why_{status}" if status in WHY_STATUSES else "why_other"
    return f"{compare_text(lang, key, place=_place(lang, current_region, names))} {summary}"


def untested_text(lang: str, table: pd.DataFrame, names: Mapping[str, str]) -> str:
    """'Not ranked: Medina, Cairo, Amazon and Sahel (No snow).', or '' when every region is ranked."""
    groups: dict[str, list[str]] = {}
    for region_key, status in table.attrs.get("untested", []):
        groups.setdefault(status, []).append(_short(names, region_key))
    if not groups:
        return ""
    parts = [f"{_join(lang, regions)} ({status_text(lang, status)[0]})" for status, regions in groups.items()]
    return compare_text(lang, "untested", regions="; ".join(parts))
