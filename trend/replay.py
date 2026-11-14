"""Replay the investigation: an animated chart in which the verdict changes as years are added.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The challenge notes that a trend which cannot be told from chance in a short record can become
significant as the record grows. The replay runs the investigation board's test on the first years
only, then again with one more year at a time, and animates the yearly values, the fitted line with
its 95% band and the verdict stamp. The viewer can watch the moment a case closes, or see that it is
still open. All functions are pure (no Streamlit), so the app decides where the replay is shown.
"""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from trend.charts import (
    AXIS,
    BAND_FILL,
    FONT_FAMILY,
    GRIDLINE,
    SERIES_1,
    SERIES_2,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from trend.i18n import num, p_phrase, status_text
from trend.stats import analyze_trend, trend_line_band
from trend.world import CELL_COLORS, case_status

FRAME_MS = 350  # how long each added year stays on screen while the replay plays
HEIGHT = 400
TABLE_COLUMNS = [
    "end_year", "n_years", "slope_per_decade", "ci_low", "ci_high", "p_value", "significant", "agrees",
    "status",
]

REPLAY_TEXT = {
    "en": {
        "title": "▶ Replay the investigation: watch the verdict as years are added",
        "intro": (
            "Press Play: one year is added at each step and the test is run again, as if the record "
            "had ended in that year. The stamp above the chart shows the verdict at that moment."
        ),
        "closed": (
            "With only the first {n_first} years this could not be told from chance. The case closed in "
            "{year}: since then every extra year has kept the verdict Confirmed."
        ),
        "closed_last": (
            "With only the first {n_first} years this could not be told from chance. The case closed only "
            "with the latest year, {year}, so one more year could still change the verdict."
        ),
        "always": "Confirmed from the first {n_first} years on, and every extra year has kept it so.",
        "open": (
            "Still an open case after {n_years} years: no confirmed trend yet. A longer record may change "
            "that."
        ),
        "play": "Play",
        "pause": "Pause",
        "stamp": "{start}–{end}: {stamp}, {p}",
        "points_name": "Yearly value",
        "line_name": "Trend line",
    },
    "tr": {
        "title": "▶ Soruşturmayı baştan izle: yıllar eklendikçe karar nasıl değişiyor",
        "intro": (
            "Oynat'a bas: Her adımda kayda bir yıl eklenir ve test, kayıt o yılda bitmiş gibi yeniden "
            "yapılır. Grafiğin üstündeki damga o anki kararı gösterir."
        ),
        "closed": (
            "Yalnızca ilk {n_first} yılla bu, tesadüften ayırt edilemiyordu. Dosya {year} yılında "
            "kapandı: o günden beri eklenen her yıl kararı Doğrulandı olarak korudu."
        ),
        "closed_last": (
            "Yalnızca ilk {n_first} yılla bu, tesadüften ayırt edilemiyordu. Dosya ancak son yılla, "
            "{year} yılında kapandı; bu yüzden bir yıl daha kararı yine değiştirebilir."
        ),
        "always": "İlk {n_first} yıldan itibaren doğrulanmış ve eklenen her yıl bunu korumuş.",
        "open": (
            "{n_years} yıl sonra hâlâ açık bir dosya: henüz doğrulanmış bir trend yok. Daha uzun bir "
            "kayıt bunu değiştirebilir."
        ),
        "play": "Oynat",
        "pause": "Durdur",
        "stamp": "{start}–{end}: {stamp}, {p}",
        "points_name": "Yıllık değer",
        "line_name": "Trend çizgisi",
    },
}


def replay_text(lang: str, key: str, **values) -> str:
    text = REPLAY_TEXT.get(lang, REPLAY_TEXT["en"])[key]
    return text.format(**values) if values else text


def replay_title(lang: str) -> str:
    """Title of the replay section (for example an expander label)."""
    return replay_text(lang, "title")


def _clean(annual: pd.DataFrame) -> pd.DataFrame:
    """Usable years only, sorted by year: the same cleaning as the trend test itself."""
    years = annual["year"].to_numpy(dtype=float)
    values = annual["value"].to_numpy(dtype=float)
    keep = np.isfinite(years) & np.isfinite(values)
    order = np.argsort(years[keep], kind="stable")
    return pd.DataFrame({"year": years[keep][order].astype(int), "value": values[keep][order]})


def growing_record(annual: pd.DataFrame, min_years: int) -> pd.DataFrame:
    """The board's test on the first ``min_years`` years, then again with one more year at a time.

    ``annual`` needs the columns ``year`` and ``value``. Returns one row per end index
    j = min_years..n (the record cut after its j-th year) with ``end_year``, ``n_years``,
    ``slope_per_decade``, ``ci_low`` and ``ci_high`` (the 95% interval, per decade), ``p_value``,
    ``significant``, ``agrees`` and ``status`` (the stamp of ``trend.world.case_status``). The last row
    is the verdict on the whole record. A record shorter than ``min_years`` gives an empty table.
    """
    data = _clean(annual)
    years, values = data["year"].to_numpy(), data["value"].to_numpy()
    rows = []
    for j in range(max(int(min_years), 3), len(data) + 1):
        try:
            result = analyze_trend(years[:j], values[:j], min_years=min_years)
        except ValueError:  # fewer distinct years than min_years, possible only with repeated years
            continue
        ci_low, ci_high = result.ci_per_decade
        rows.append({
            "end_year": int(years[j - 1]),
            "n_years": int(result.n_years),
            "slope_per_decade": float(result.slope_per_decade),
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "p_value": float(result.p_value),
            "significant": bool(result.significant),
            "agrees": bool(result.agrees),
            "status": case_status(result),
        })
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def replay_summary(table: pd.DataFrame) -> dict:
    """How the verdict developed while years were added (``table`` from ``growing_record``).

    Returns ``kind``, ``year``, ``n_first``, ``n_years`` and ``last_year``. ``kind`` is "open" when the
    whole record is not confirmed (``year`` is None). Otherwise ``year`` is the first end year from
    which every longer record is confirmed in the same direction, and ``kind`` is "always" when that is
    already the first record and "closed" when it came later. ``n_years`` and ``last_year`` are the
    length and the last year of the whole record, and ``n_first`` is the length of the first record.
    When that first record was itself confirmed but the verdict was lost before the case closed,
    ``n_first`` is the length of the last record that was not confirmed, so that "this could not be
    told from chance" stays true.
    """
    if table.empty:
        return {"kind": "open", "year": None, "n_first": 0, "n_years": 0, "last_year": None}
    lengths = table["n_years"].to_numpy(dtype=int)
    confirmed = (table["status"] == "confirmed").to_numpy()
    summary = {
        "kind": "open", "year": None, "n_first": int(lengths[0]), "n_years": int(lengths[-1]),
        "last_year": int(table["end_year"].iloc[-1]),
    }
    if not confirmed[-1]:
        return summary
    sign = np.sign(table["slope_per_decade"].to_numpy(dtype=float))
    kept = confirmed & (sign == sign[-1])
    first_kept = len(kept) - 1
    while first_kept > 0 and kept[first_kept - 1]:
        first_kept -= 1
    summary["year"] = int(table["end_year"].iloc[first_kept])
    summary["kind"] = "always" if first_kept == 0 else "closed"
    if summary["kind"] == "closed" and confirmed[0]:
        unconfirmed = np.flatnonzero(~confirmed[:first_kept])
        if unconfirmed.size:
            summary["n_first"] = int(lengths[unconfirmed[-1]])
    return summary


def replay_sentence(lang: str, summary: dict) -> str:
    """One sentence on how the verdict developed (``summary`` from ``replay_summary``).

    A case that closed only with the last year of the record gets its own sentence, because "since then
    every extra year has kept the verdict" would have no extra years behind it.
    """
    kind = summary.get("kind")
    if kind == "closed":
        key = "closed_last" if summary["year"] == summary.get("last_year") else "closed"
        return replay_text(lang, key, n_first=num(summary["n_first"], lang, 0), year=summary["year"])
    if kind == "always":
        return replay_text(lang, "always", n_first=num(summary["n_first"], lang, 0))
    return replay_text(lang, "open", n_years=num(summary["n_years"], lang, 0))


def _stamp(lang: str, start: int, end: int, status: str, p_value: float) -> dict:
    """The verdict stamp above the chart, coloured like the world board's cells."""
    color, background = CELL_COLORS.get(status, CELL_COLORS["noevidence"])
    text = replay_text(
        lang, "stamp", start=start, end=end, stamp=status_text(lang, status)[0], p=p_phrase(p_value, lang),
    )
    return {
        "text": f"<b>{html.escape(text, quote=False)}</b>",
        "x": 0, "xref": "paper", "xanchor": "left",
        "y": 1, "yref": "paper", "yanchor": "bottom", "yshift": 8,
        "showarrow": False, "align": "left",
        "font": {"family": FONT_FAMILY, "color": color, "size": 14},
        "bgcolor": background, "bordercolor": color, "borderwidth": 1.5, "borderpad": 5,
    }


def _traces(sub: pd.DataFrame, band: pd.DataFrame, lang: str, unit: str, decimals: int) -> list[go.Scatter]:
    """The four traces of one frame: yearly values, lower and upper band edge, fitted line."""
    hover = f"%{{y:.{decimals}f}} {unit}<extra></extra>"
    band_years = band["year"].tolist()
    return [
        go.Scatter(
            x=sub["year"].tolist(), y=sub["value"].tolist(), mode="lines+markers",
            name=replay_text(lang, "points_name"), line={"color": SERIES_1, "width": 2},
            marker={"size": 8, "color": SERIES_1, "line": {"color": SURFACE, "width": 2}},
            hovertemplate=hover, zorder=1,
        ),
        go.Scatter(
            x=band_years, y=band["low"].tolist(), mode="lines", line={"width": 0}, hoverinfo="skip",
        ),
        go.Scatter(
            x=band_years, y=band["high"].tolist(), mode="lines", line={"width": 0}, fill="tonexty",
            fillcolor=BAND_FILL, hoverinfo="skip",
        ),
        go.Scatter(
            x=band_years, y=band["fit"].tolist(), mode="lines", name=replay_text(lang, "line_name"),
            line={"color": SERIES_2, "width": 2}, hovertemplate=hover, zorder=2,
        ),
    ]


def _padded(low: float, high: float, share: float) -> list[float]:
    span = high - low
    if span <= 0:
        span = abs(high) or 1.0
    return [low - share * span, high + share * span]


def replay_figure(
    annual: pd.DataFrame,
    table: pd.DataFrame,
    lang: str,
    *,
    x_title: str,
    y_title: str,
    unit: str,
    separators: str = ".,",
    decimals: int = 2,
) -> go.Figure:
    """Animated replay with one frame per row of ``table`` (from ``growing_record`` on ``annual``).

    Every frame has the same four traces: (0) the yearly values up to the frame's end year, (1) and
    (2) the lower and upper edge of the 95% band of the trend line fitted to those years, (3) the
    fitted line; each frame also sets the verdict stamp above the chart. The axes are fixed to the
    whole record. The figure starts on the last frame, so a static render shows the final verdict;
    Play runs the replay from the first record, and the slider jumps to any end year.
    """
    if table.empty:
        raise ValueError("The replay needs at least one row from growing_record().")
    data = _clean(annual)
    start = int(data["year"].iloc[0])
    frames, stamps = [], []
    band = None
    for row in table.itertuples(index=False):
        sub = data.iloc[: int(row.n_years)]
        band = trend_line_band(sub["year"], sub["value"])
        stamp = _stamp(lang, start, int(row.end_year), str(row.status), float(row.p_value))
        stamps.append(stamp)
        frames.append(go.Frame(
            data=_traces(sub, band, lang, unit, decimals), name=str(int(row.end_year)),
            layout={"annotations": [stamp]},
        ))

    values = data["value"].to_numpy(dtype=float)
    y_range = _padded(
        min(values.min(), float(band["low"].min())), max(values.max(), float(band["high"].max())), 0.08,
    )
    first_year, last_year = float(data["year"].iloc[0]), float(data["year"].iloc[-1])
    x_pad = max(0.6, 0.02 * (last_year - first_year))
    x_range = [first_year - x_pad, last_year + x_pad]

    play = {
        "frame": {"duration": FRAME_MS, "redraw": True}, "transition": {"duration": 0},
        "fromcurrent": True, "mode": "immediate",
    }
    pause = {"frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}, "mode": "immediate"}
    jump = {"frame": {"duration": 0, "redraw": True}, "transition": {"duration": 0}, "mode": "immediate"}
    names = [frame.name for frame in frames]

    figure = go.Figure(data=frames[-1].data, frames=frames)
    figure.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT_FAMILY, "color": TEXT_SECONDARY, "size": 13},
        separators=separators,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT_PRIMARY}},
        margin={"l": 64, "r": 24, "t": 48, "b": 124},
        height=HEIGHT,
        showlegend=False,
        annotations=[stamps[-1]],
        updatemenus=[{
            "type": "buttons", "direction": "left", "showactive": False,
            "x": 0.12, "xanchor": "right", "y": 0, "yanchor": "top", "pad": {"t": 62, "r": 10},
            "bgcolor": "#ffffff", "bordercolor": AXIS, "font": {"color": TEXT_PRIMARY, "size": 12},
            "buttons": [
                {"label": replay_text(lang, "play"), "method": "animate", "args": [None, play]},
                {"label": replay_text(lang, "pause"), "method": "animate", "args": [[None], pause]},
            ],
        }],
        sliders=[{
            "active": len(names) - 1,
            "steps": [{"label": name, "method": "animate", "args": [[name], jump]} for name in names],
            "x": 0.12, "len": 0.88, "xanchor": "left", "y": 0, "yanchor": "top",
            "pad": {"t": 64, "b": 0},
            "currentvalue": {"visible": False},
            "transition": {"duration": 0},
            "font": {"color": TEXT_SECONDARY, "size": 11},
            "bgcolor": "#ffffff", "bordercolor": AXIS, "tickcolor": AXIS,
        }],
    )
    figure.update_xaxes(
        title=x_title, range=x_range, autorange=False, fixedrange=True, showgrid=False,
        linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False,
    )
    figure.update_yaxes(
        title=y_title, range=y_range, autorange=False, fixedrange=True, gridcolor=GRIDLINE,
        gridwidth=1, linecolor=AXIS, zeroline=False,
    )
    return figure
