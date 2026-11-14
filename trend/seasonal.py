"""Which season is changing? The trend test for each three-month season, next to the whole year.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The verdict uses one value per year, which hides when in the year a change happens. This module runs the
same test on four three-month seasons: December to February, March to May, June to August and September
to November. Each season becomes one value per year with ``to_annual`` (trend/stats.py): the mean of its
three months for air temperature, their sum for precipitation and hot days. The trend and its stamp come
from ``analyze_trend`` and ``case_status`` (trend/world.py), with the measurement's own ``min_years``.

December to February is labelled by the year of its January (season 2001 runs from December 2000 to
February 2001): the season's ``Variable`` gets ``year_starts_month=12``, and ``to_annual`` labels such a
year by the calendar year in which it ends. Season words (winter, summer, ...) are added only outside the
tropics and are swapped in the southern hemisphere; in the tropics the months alone are shown.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from trend.charts import AXIS, FONT_FAMILY, GRIDLINE, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY
from trend.i18n import num, status_text
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES, Variable
from trend.world import NO_HOT_DAYS, case_status

# Season key -> its three months, in the order of the table and the chart.
SEASONS: dict[str, tuple[int, int, int]] = {
    "dec_feb": (12, 1, 2),
    "mar_may": (3, 4, 5),
    "jun_aug": (6, 7, 8),
    "sep_nov": (9, 10, 11),
}
SUPPORTED = ("air_temperature", "precipitation", "hot_days")
DIRECTED = ("precipitation", "hot_days")  # sentences say "a rise of" / "a fall of" instead of a signed rate
WHOLE_YEAR = "year"  # key of the whole-year row kept in ``table.attrs["whole_year"]``

TROPIC_LATITUDE = 23.5  # season words only poleward of this latitude (degrees north or south)
NORTH_WORDS = {"dec_feb": "winter", "mar_may": "spring", "jun_aug": "summer", "sep_nov": "autumn"}
SOUTH_WORDS = {"dec_feb": "summer", "mar_may": "autumn", "jun_aug": "winter", "sep_nov": "spring"}

# Days in each season (Dec-Feb has 91 in leap years) and in a year. A hot-day season whose mean count is
# at least CEILING_SHARE of its days is "full": almost every day is already above 30 °C, so it cannot rise
# much (the summer in Medina, the spring in the Sahel).
DAYS = {"dec_feb": 90.25, "mar_may": 92.0, "jun_aug": 92.0, "sep_nov": 91.0, WHOLE_YEAR: 365.25}
CEILING_SHARE = 0.97

COLUMNS = [
    "season", "n_years", "slope_per_decade", "ci_low", "ci_high", "p_value", "status",
    "start_year", "end_year", "ceiling",
]
STAMP_COLORS = {"confirmed": "#1c5cab", "disputed": "#a8501b", "weak": "#a8501b"}
OTHER_COLOR = "#898781"  # no evidence, too few years, no hot days
FIGURE_HEIGHT = 260

SEASONAL_TEXT = {
    "en": {
        "title": "Which season is changing?",
        "intro": (
            "The same test for each three-month season. A warming that happens mostly in summer, or a "
            "change in rain and snow that happens mostly in winter, shows up here."
        ),
        "months_dec_feb": "Dec–Feb",
        "months_mar_may": "Mar–May",
        "months_jun_aug": "Jun–Aug",
        "months_sep_nov": "Sep–Nov",
        "winter": "winter",
        "spring": "spring",
        "summer": "summer",
        "autumn": "autumn",
        "named": "{months} ({word})",
        "whole_year": "Whole year",
        "whole_year_mark": "Whole year: {rate}",
        "whole_year_quarter_mark": "Whole year ÷ 4: {rate}",
        "note_mean": (
            "Blue: Confirmed · orange: Disputed or Weak clue · grey: No evidence. Thin lines: 95% confidence "
            "interval. Dashed line: the whole year."
        ),
        "note_sum": (
            "Blue: Confirmed · orange: Disputed or Weak clue · grey: No evidence. Thin lines: 95% confidence "
            "interval. Each bar is a three-month total, so the dashed line is the whole year's change "
            "divided by four: if all seasons changed alike, every bar would end there. Dec–Feb takes its "
            "December from the year before, so the four bars can add up to a different change than the "
            "whole year."
        ),
        "x_title": "{unit} per decade",
        "hover": (
            "{season}<br>{rate} {unit} per decade<br>95% CI {low} to {high}<br>{stamp} · {n} years, "
            "{start}–{end}"
        ),
        "signed": "{rate} {unit} per decade",
        "directed": "a {direction} of {rate} {unit} per decade",
        "rise": "rise",
        "fall": "fall",
        "fastest": "The fastest change is in {season}: {change}{verdict}.",
        "slowest": "The slowest is {season}: {change}.",
        "slowest_flat": "The slowest is {season}: hardly any change.",
        "slowest_ceiling": (
            "The slowest is {season}: almost every day is already above 30 °C, so there is little room to "
            "rise."
        ),
        "only": "Only {season} can be tested here: {change}{verdict}.",
        "verdict_confirmed": ", Confirmed",
        "verdict_other": ", but it is not Confirmed ({stamp})",
        "verdict_other_one": ", but it is not Confirmed ({stamp}), while {seasons} is",
        "verdict_other_many": ", but it is not Confirmed ({stamp}), while {seasons} are",
        "verdict_none": ", but no season is Confirmed",
        "and": " and ",
        "all_flat": "No season shows a noticeable change.",
        "untested": "No season can be tested here.",
    },
    "tr": {
        "title": "Hangi mevsim değişiyor?",
        "intro": (
            "Aynı test, üç aylık her mevsim için ayrı ayrı yapılır. Isınma daha çok yazın oluyorsa ya da "
            "yağıştaki değişim daha çok kışın oluyorsa, burada görünür."
        ),
        "months_dec_feb": "Ara–Şub",
        "months_mar_may": "Mar–May",
        "months_jun_aug": "Haz–Ağu",
        "months_sep_nov": "Eyl–Kas",
        "winter": "kış",
        "spring": "ilkbahar",
        "summer": "yaz",
        "autumn": "sonbahar",
        "named": "{months} ({word})",
        "whole_year": "Tüm yıl",
        "whole_year_mark": "Tüm yıl: {rate}",
        "whole_year_quarter_mark": "Tüm yıl ÷ 4: {rate}",
        "note_mean": (
            "Mavi: Doğrulandı · turuncu: Tartışmalı ya da Zayıf ipucu · gri: Delil yok. İnce çizgiler: %95 "
            "güven aralığı. Kesikli çizgi: tüm yıl."
        ),
        "note_sum": (
            "Mavi: Doğrulandı · turuncu: Tartışmalı ya da Zayıf ipucu · gri: Delil yok. İnce çizgiler: %95 "
            "güven aralığı. Her çubuk üç aylık bir toplamdır; bu yüzden kesikli çizgi tüm yılın değişiminin "
            "dörtte biridir: bütün mevsimler aynı ölçüde değişseydi, her çubuk orada biterdi. Ara–Şub aralık "
            "ayını bir önceki yıldan alır; bu yüzden dört çubuğun toplamı tüm yılın değişiminden farklı "
            "olabilir."
        ),
        "x_title": "{unit} / 10 yıl",
        "hover": (
            "{season}<br>on yılda {rate} {unit}<br>%95 güven aralığı: {low} ile {high}<br>{stamp} · {n} yıl, "
            "{start}–{end}"
        ),
        "signed": "on yılda {rate} {unit}",
        "directed": "on yılda {rate} {unit} {direction}",
        "rise": "artış",
        "fall": "azalma",
        "fastest": "En hızlı değişim {season} aylarında: {change}{verdict}.",
        "slowest": "En yavaş değişim {season} aylarında: {change}.",
        "slowest_flat": "En yavaş değişim {season} aylarında: neredeyse hiç değişim yok.",
        "slowest_ceiling": (
            "En yavaş değişim {season} aylarında: zaten neredeyse her gün 30 °C'nin üstünde, artacak yer pek "
            "kalmamış."
        ),
        "only": "Burada yalnızca {season} aylarında test yapılabiliyor: {change}{verdict}.",
        "verdict_confirmed": ", Doğrulandı",
        "verdict_other": ", ama doğrulanmadı ({stamp})",
        "verdict_other_one": ", ama doğrulanmadı ({stamp}); {seasons} ise doğrulandı",
        "verdict_other_many": ", ama doğrulanmadı ({stamp}); {seasons} ise doğrulandı",
        "verdict_none": ", ama hiçbir mevsim doğrulanmadı",
        "and": " ve ",
        "all_flat": "Hiçbir mevsimde belirgin bir değişim yok.",
        "untested": "Burada hiçbir mevsim test edilemiyor.",
    },
}


def section_text(lang: str, key: str, **values) -> str:
    """Text of this section in the interface language (English for an unknown language)."""
    text = SEASONAL_TEXT.get(lang, SEASONAL_TEXT["en"])[key]
    return text.format(**values) if values else text


def season_name(lang: str, key: str, latitude: float | None) -> str:
    """Label of a season: the months first, then the season word outside the tropics.

    North of ``TROPIC_LATITUDE`` June to August is summer ("Jun–Aug (summer)"), south of it the words are
    swapped ("Jun–Aug (winter)"), and in the tropics (or without a latitude) only the months are shown
    ("Jun–Aug"). The key ``"year"`` gives the label of the whole year.
    """
    if key == WHOLE_YEAR:
        return section_text(lang, "whole_year")
    months = section_text(lang, f"months_{key}")
    if latitude is None or not math.isfinite(latitude):
        return months
    if latitude > TROPIC_LATITUDE:
        word = NORTH_WORDS[key]
    elif latitude < -TROPIC_LATITUDE:
        word = SOUTH_WORDS[key]
    else:
        return months
    return section_text(lang, "named", months=months, word=section_text(lang, word))


def _check_supported(variable_key: str) -> None:
    if variable_key not in SUPPORTED:
        raise ValueError(f"Season trends are made for {', '.join(SUPPORTED)}, not '{variable_key}'.")


def season_variable(variable_key: str, season: str) -> Variable:
    """The measurement with its year narrowed to one season, ready for ``to_annual``.

    A season that crosses the new year (December to February) starts its year in its first month, so
    ``to_annual`` labels it by the year of its January.
    """
    months = SEASONS[season]
    starts = months[0] if months[0] > months[-1] else 1
    return dataclasses.replace(VARIABLES[variable_key], season_months=months, year_starts_month=starts)


def season_annual(
    monthly: pd.DataFrame, variable_key: str, season: str,
    start_year: int | None = None, end_year: int | None = None,
) -> pd.DataFrame:
    """One value per complete season: ``year``, ``value`` and ``n_months`` (from ``to_annual``).

    ``season`` is a key of ``SEASONS`` or ``"year"`` for the whole year. Years outside ``start_year`` to
    ``end_year`` (by label, so Dec–Feb 2001 belongs to 2001) are left out; None means no limit.
    """
    _check_supported(variable_key)
    variable = VARIABLES[variable_key] if season == WHOLE_YEAR else season_variable(variable_key, season)
    annual, _ = to_annual(monthly, variable)
    keep = pd.Series(True, index=annual.index)
    if start_year is not None:
        keep &= annual["year"] >= start_year
    if end_year is not None:
        keep &= annual["year"] <= end_year
    return annual[keep].reset_index(drop=True)


def _trend_row(annual: pd.DataFrame, variable_key: str, season: str) -> dict:
    """Trend, confidence interval, p-value and stamp of one season, with the board's rules."""
    variable = VARIABLES[variable_key]
    n_years = int(len(annual))
    row = {
        "season": season, "n_years": n_years, "slope_per_decade": math.nan, "ci_low": math.nan,
        "ci_high": math.nan, "p_value": math.nan, "status": "insufficient",
        "start_year": int(annual["year"].min()) if n_years else None,
        "end_year": int(annual["year"].max()) if n_years else None,
        "ceiling": False,
    }
    values = annual["value"]
    if variable_key == "hot_days" and n_years and values.max() < NO_HOT_DAYS:
        row["status"] = "no_hot"  # never a day above 30 °C in this season
        return row
    if n_years < variable.min_years:
        return row
    result = analyze_trend(annual["year"], values, min_years=variable.min_years)
    low, high = result.ci_per_decade
    row.update(
        slope_per_decade=float(result.slope_per_decade), ci_low=float(low), ci_high=float(high),
        p_value=float(result.p_value), status=case_status(result),
    )
    if variable_key == "hot_days":
        row["ceiling"] = bool(values.mean() >= CEILING_SHARE * DAYS[season])
    return row


def season_trends(
    monthly: pd.DataFrame, variable_key: str, start_year: int | None = None, end_year: int | None = None
) -> pd.DataFrame:
    """The trend test for each of the four seasons over the chosen years.

    ``monthly`` needs ``date`` and ``value``; ``variable_key`` must be in ``SUPPORTED``. Returns one row per
    season in the order of ``SEASONS`` with ``season`` (key), ``n_years`` (complete seasons used),
    ``slope_per_decade``, ``ci_low`` and ``ci_high`` (95% interval, per decade), ``p_value``, ``status``
    (the stamp from ``case_status``), ``start_year`` and ``end_year`` (first and last season label) and
    ``ceiling`` (hot days only: almost every day of the season is already above 30 °C).

    A season with fewer complete years than the measurement's ``min_years`` gets the status
    "insufficient", and a hot-day season that never reaches one day above 30 °C gets "no_hot"; both keep
    NaN numbers. The same test on the whole year is kept as a dict of the same fields in
    ``table.attrs["whole_year"]`` (season "year"), and the measurement in ``table.attrs["variable_key"]``,
    for the reference line of ``season_figure``.
    """
    _check_supported(variable_key)
    rows = [
        _trend_row(season_annual(monthly, variable_key, season, start_year, end_year), variable_key, season)
        for season in SEASONS
    ]
    table = pd.DataFrame(rows, columns=COLUMNS).astype(
        {
            "n_years": int, "slope_per_decade": float, "ci_low": float, "ci_high": float, "p_value": float,
            "start_year": "Int64", "end_year": "Int64", "ceiling": bool,
        }
    )
    whole = season_annual(monthly, variable_key, WHOLE_YEAR, start_year, end_year)
    table.attrs["whole_year"] = _trend_row(whole, variable_key, WHOLE_YEAR)
    table.attrs["variable_key"] = variable_key
    return table


def _is_total(variable_key: str | None) -> bool:
    """True when a season value is a sum of months (precipitation, hot days), not a mean."""
    return variable_key in VARIABLES and VARIABLES[variable_key].aggregation == "sum"


def whole_year_reference(table: pd.DataFrame) -> float | None:
    """Where the dashed whole-year line of ``season_figure`` goes, or None without a whole-year trend.

    For a mean (temperature) it is the whole year's trend per decade. For a total (precipitation, hot
    days) it is the whole year's trend divided by the four seasons: roughly the bar every season would
    reach if all of them changed alike. The season totals need not add up to the year's trend exactly,
    because Dec–Feb takes its December from the year before (and so covers slightly different years).
    """
    slope = (table.attrs.get("whole_year") or {}).get("slope_per_decade")
    if slope is None or not math.isfinite(float(slope)):
        return None
    slope = float(slope)
    return slope / len(SEASONS) if _is_total(table.attrs.get("variable_key")) else slope


def figure_note(lang: str, variable_key: str) -> str:
    """Caption for under the chart: the bar colours, the thin lines and the dashed whole-year line."""
    return section_text(lang, "note_sum" if _is_total(variable_key) else "note_mean")


def _change_text(lang: str, slope: float, variable_key: str, unit: str, decimals: int) -> str:
    """'+0.81 °C per decade' for temperature, 'a fall of 12.3 mm of water per decade' for the others."""
    if variable_key in DIRECTED:
        return section_text(
            lang, "directed", direction=section_text(lang, "rise" if slope > 0 else "fall"),
            rate=num(abs(slope), lang, decimals), unit=unit,
        )
    return section_text(lang, "signed", rate=num(slope, lang, decimals, signed=True), unit=unit)


def _join(lang: str, names: list[str]) -> str:
    """'A', 'A and B', 'A, B and C' ('ve' in Turkish)."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + section_text(lang, "and") + names[-1]


def season_sentence(
    lang: str, table: pd.DataFrame, variable_key: str, latitude: float | None, unit: str
) -> str:
    """One or two plain sentences: the season that changes fastest and the one that changes slowest.

    "Fastest" is the largest change in either direction (the largest absolute slope); the sentence says
    whether that season is Confirmed, names the Confirmed seasons when it is not, or says that no season
    is Confirmed. Precipitation and hot days say "a rise of" or "a fall of"; temperature shows the signed
    rate. Numbers use the measurement's decimals and the decimal comma in Turkish. ``unit`` is the unit of
    one yearly value, as in the case file (for example "°C").
    """
    _check_supported(variable_key)
    decimals = VARIABLES[variable_key].decimals
    slopes = pd.to_numeric(table["slope_per_decade"], errors="coerce").astype(float)
    tested = slopes[np.isfinite(slopes)]
    if tested.empty:
        return section_text(lang, "untested")
    order = tested.abs().sort_values(ascending=False, kind="stable").index
    fastest, slowest = table.loc[order[0]], table.loc[order[-1]]

    def is_flat(row: pd.Series) -> bool:
        return round(abs(float(row["slope_per_decade"])), decimals) == 0

    def name(row: pd.Series) -> str:
        return season_name(lang, row["season"], latitude)

    if is_flat(fastest):
        return section_text(lang, "all_flat")
    confirmed = [name(table.loc[i]) for i in tested.index if table.loc[i, "status"] == "confirmed"]
    stamp = status_text(lang, fastest["status"])[0]
    if fastest["status"] == "confirmed":
        verdict = section_text(lang, "verdict_confirmed")
    elif len(tested) == 1:
        verdict = section_text(lang, "verdict_other", stamp=stamp)
    elif not confirmed:
        verdict = section_text(lang, "verdict_none")
    else:  # another season is Confirmed: name it, so the sentence does not hide it
        verdict = section_text(
            lang, "verdict_other_one" if len(confirmed) == 1 else "verdict_other_many", stamp=stamp,
            seasons=_join(lang, confirmed),
        )
    change = _change_text(lang, float(fastest["slope_per_decade"]), variable_key, unit, decimals)
    if len(tested) == 1:
        return section_text(lang, "only", season=name(fastest), change=change, verdict=verdict)
    first = section_text(lang, "fastest", season=name(fastest), change=change, verdict=verdict)
    if bool(slowest.get("ceiling", False)) and round(float(slowest["slope_per_decade"]), decimals) >= 0:
        # "little room to rise" explains a flat or slow rise, never a fall
        second = section_text(lang, "slowest_ceiling", season=name(slowest))
    elif is_flat(slowest):
        second = section_text(lang, "slowest_flat", season=name(slowest))
    else:
        slow_change = _change_text(lang, float(slowest["slope_per_decade"]), variable_key, unit, decimals)
        second = section_text(lang, "slowest", season=name(slowest), change=slow_change)
    return f"{first} {second}"


def season_figure(
    table: pd.DataFrame, lang: str, latitude: float | None, unit: str, separators: str = ".,",
    decimals: int = 2,
) -> go.Figure:
    """Horizontal bars of the trend per decade of each season, with the 95% interval as error bars.

    Bars are blue for Confirmed, orange for Disputed or Weak clue and grey otherwise; the value is written
    past the end of each interval. A season without a test shows its stamp text at zero. A thin line marks
    zero and, when ``table.attrs["whole_year"]`` has a trend, a dashed line marks the whole year (divided
    by four for totals, see ``whole_year_reference``).
    """
    labels = [season_name(lang, key, latitude) for key in table["season"]]
    slope = pd.to_numeric(table["slope_per_decade"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(table["ci_low"], errors="coerce").to_numpy(dtype=float)
    high = pd.to_numeric(table["ci_high"], errors="coerce").to_numpy(dtype=float)
    statuses = [str(status) for status in table["status"]]
    tested = np.isfinite(slope)

    hover = []
    rows = table.itertuples(index=False)
    for label, row, value, lo, hi, status in zip(labels, rows, slope, low, high, statuses):
        if not math.isfinite(value):
            hover.append("")
            continue
        hover.append(section_text(
            lang, "hover", season=label, rate=num(value, lang, decimals, signed=True), unit=unit,
            low=num(lo, lang, decimals, signed=True), high=num(hi, lang, decimals, signed=True),
            stamp=status_text(lang, status)[0], n=row.n_years, start=row.start_year, end=row.end_year,
        ))

    colors = [STAMP_COLORS.get(status, OTHER_COLOR) for status in statuses]
    fig = go.Figure(
        go.Bar(
            x=slope, y=labels, orientation="h", width=0.6, marker={"color": colors, "line": {"width": 0}},
            error_x={
                "type": "data", "symmetric": False, "array": high - slope, "arrayminus": slope - low,
                "color": TEXT_SECONDARY, "thickness": 1.5, "width": 5,
            },
            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", showlegend=False,
        )
    )

    whole = whole_year_reference(table)
    edges = [0.0, *low[tested], *high[tested]] + ([whole] if whole is not None else [])
    left, right = min(edges), max(edges)
    span = (right - left) or 1.0
    pad, room = 0.02 * span, 0.24 * span  # room for the value written past the end of each interval

    for label, value, lo, hi, status in zip(labels, slope, low, high, statuses):
        if math.isfinite(value):
            up = value >= 0
            fig.add_annotation(
                x=(hi + pad) if up else (lo - pad), y=label, text=num(value, lang, decimals, signed=True),
                xanchor="left" if up else "right", showarrow=False, font={"color": TEXT_PRIMARY, "size": 12},
            )
        else:
            word, meaning = status_text(lang, status)
            fig.add_annotation(
                x=0, y=label, text=word, hovertext=meaning, xanchor="left", xshift=4, showarrow=False,
                font={"color": TEXT_SECONDARY, "size": 12},
            )

    fig.add_vline(x=0, line_color=TEXT_SECONDARY, line_width=1)
    if whole is not None:
        mark = "whole_year_quarter_mark" if _is_total(table.attrs.get("variable_key")) else "whole_year_mark"
        fig.add_vline(x=whole, line_color=TEXT_SECONDARY, line_width=1.5, line_dash="dash")
        fig.add_annotation(
            x=whole, y=1, yref="paper", yanchor="bottom", showarrow=False,
            text=section_text(lang, mark, rate=num(whole, lang, decimals, signed=True)),
            font={"color": TEXT_SECONDARY, "size": 12},
        )

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
        margin={"l": 8, "r": 16, "t": 30 if whole is not None else 12, "b": 48},
        height=FIGURE_HEIGHT,
        showlegend=False,
    )
    fig.update_xaxes(
        title=section_text(lang, "x_title", unit=unit), range=x_range, gridcolor=GRIDLINE, gridwidth=1,
        linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False,
    )
    fig.update_yaxes(
        showgrid=False, linecolor=AXIS, automargin=True, categoryorder="array", categoryarray=labels,
        autorange="reversed",
    )
    return fig
