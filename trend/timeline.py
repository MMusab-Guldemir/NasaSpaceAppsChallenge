"""Evidence timeline and start-year check: how solid is a verdict, and does it depend on the period?

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

* Evidence timeline: the same test run as if the record had ended in each year. It shows when a trend
  became significant (the challenge notes that a longer record can make a trend significant) or that
  the evidence went back and forth.
* Start-year check: the same test for every possible start year with the same end year. A verdict that
  holds for most start years cannot be the product of a cherry-picked period.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from trend.stats import analyze_trend
from trend.world import case_status

P_FLOOR = 1e-4  # smallest p-value drawn on the chart

TIMELINE_TEXT = {
    "en": {
        "title": "How the evidence built up",
        "intro": (
            "Each point is the same test, run as if the record had ended in that year. Points below the "
            "5% line were unlikely to be chance."
        ),
        "solid_since": "**Solid since {year}:** every record ending in {year} or later is Confirmed, with the same {direction}.",
        "solid_last": "**Confirmed only with the latest year, {year}:** one more year could still change the verdict.",
        "not_solid": "**Not solid yet:** the chosen period does not get the Confirmed stamp. A longer record may change that.",
        "not_solid_curved": "**Not solid yet:** the chosen period does not get the Confirmed stamp; see the note about the straight line above.",
        "flipped": (
            "**The evidence went back and forth:** records ending in {years} were Confirmed, but the "
            "chosen period is not."
        ),
        "robust": (
            "**Start-year check:** of the {n} possible start years ({first}–{last}, each keeping at least "
            "{min} years), {k} give the same verdict as the chosen period ({status})."
        ),
        "up": "rise", "down": "fall",
        "x_title": "Last year of the record", "y_title": "Chance (p-value, log scale)",
        "line": "5% line", "hover": "Record {start}–%{{x}}: p = %{{customdata}}",
    },
    "tr": {
        "title": "Delil nasıl birikti?",
        "intro": (
            "Her nokta aynı testtir; kayıt o yılda bitmiş gibi yapılır. %5 çizgisinin altındaki "
            "noktalar şansa zor bağlanır."
        ),
        "solid_since": "**{year} yılından beri sağlam:** {year} veya sonrasında biten her kayıt aynı yönde ({direction}) Doğrulandı.",
        "solid_last": "**Ancak son yılla, {year} yılında doğrulandı:** bir yıl daha kararı değiştirebilir.",
        "not_solid": "**Henüz sağlam değil:** Seçilen dönem Doğrulandı damgası almıyor. Daha uzun bir kayıt bunu değiştirebilir.",
        "not_solid_curved": "**Henüz sağlam değil:** Seçilen dönem Doğrulandı damgası almıyor; yukarıdaki düz çizgi notuna bak.",
        "flipped": (
            "**Delil gidip geldi:** son yılı {years} olan kayıtlar Doğrulandı damgası almıştı; seçilen "
            "dönem ise almıyor."
        ),
        "robust": (
            "**Başlangıç yılı kontrolü:** {first}–{last} arasındaki {n} olası başlangıç yılının (her "
            "birinde en az {min} yıl kalacak şekilde) {k} tanesi seçilen dönemle aynı kararı veriyor "
            "({status})."
        ),
        "up": "artış", "down": "azalış",
        "x_title": "Kaydın son yılı", "y_title": "Tesadüf ihtimali (p-değeri, log ölçek)",
        "line": "%5 çizgisi", "hover": "Kayıt {start}–%{{x}}: p = %{{customdata}}",
    },
}


def timeline_text(lang: str, key: str, **values) -> str:
    text = TIMELINE_TEXT.get(lang, TIMELINE_TEXT["en"])[key]
    return text.format(**values) if values else text


def evidence_timeline(annual: pd.DataFrame, min_years: int) -> pd.DataFrame:
    """The test for every end year (start fixed): end_year, p_value, significant, agrees, slope_per_decade."""
    years = annual["year"].to_numpy()
    values = annual["value"].to_numpy(dtype=float)
    rows = []
    for k in range(min_years, len(years) + 1):
        result = analyze_trend(years[:k], values[:k], min_years=min_years)
        rows.append({
            "end_year": int(years[k - 1]),
            "p_value": float(result.p_value),
            "significant": bool(result.significant),
            "agrees": bool(result.agrees),
            "slope_per_decade": float(result.slope_per_decade),
        })
    return pd.DataFrame(rows, columns=["end_year", "p_value", "significant", "agrees", "slope_per_decade"])


def _confirmed(timeline: pd.DataFrame) -> pd.Series:
    return timeline["significant"] & timeline["agrees"]


def solid_since(timeline: pd.DataFrame) -> int | None:
    """First end year from which every longer record is Confirmed in the final direction."""
    if timeline.empty or not _confirmed(timeline).iloc[-1]:
        return None
    sign = np.sign(timeline["slope_per_decade"].iloc[-1])
    ok = (_confirmed(timeline) & (np.sign(timeline["slope_per_decade"]) == sign)).to_numpy()
    i = len(ok) - 1
    while i > 0 and ok[i - 1]:
        i -= 1
    return int(timeline["end_year"].iloc[i])


def earlier_significant_years(timeline: pd.DataFrame) -> list[int]:
    """End years whose record was Confirmed, when the chosen period is not Confirmed."""
    if timeline.empty or _confirmed(timeline).iloc[-1]:
        return []
    return [int(y) for y in timeline.loc[_confirmed(timeline), "end_year"]]


def year_ranges(years: list[int]) -> str:
    """[2005, 2006, 2007, 2010] -> '2005–2007, 2010'."""
    parts: list[str] = []
    for year in sorted(years):
        if parts and year == int(parts[-1].split("–")[-1]) + 1:
            parts[-1] = f"{parts[-1].split('–')[0]}–{year}"
        else:
            parts.append(str(year))
    return ", ".join(parts)


def start_year_check(annual: pd.DataFrame, min_years: int) -> dict | None:
    """Verdict for every possible start year (same end year). None if there are fewer than 3 options."""
    years = annual["year"].to_numpy()
    values = annual["value"].to_numpy(dtype=float)
    starts = len(years) - min_years + 1
    if starts < 3:
        return None
    full = analyze_trend(years, values, min_years=min_years)
    full_status = case_status(full)
    full_sign = np.sign(full.slope_per_year)
    same = 0
    for i in range(starts):
        result = analyze_trend(years[i:], values[i:], min_years=min_years)
        status = case_status(result)
        if status == full_status and (full_status not in ("confirmed", "disputed") or np.sign(result.slope_per_year) == full_sign):
            same += 1
    return {"n": starts, "same": same, "first": int(years[0]), "last": int(years[starts - 1]), "status": full_status}


def timeline_figure(timeline: pd.DataFrame, lang: str, start_year: int, separators: str = ".,") -> go.Figure:
    """p-value by last year of the record, on a log scale, with the 5% line."""
    p = timeline["p_value"].clip(lower=P_FLOOR)
    colors = np.where(
        timeline["significant"] & timeline["agrees"], "#1c5cab",
        np.where(timeline["significant"], "#a8501b", "#898781"),
    )
    shown = [f"{value:.4f}" if value >= 0.0001 else "< 0.0001" for value in timeline["p_value"]]
    if separators.startswith(","):  # hover texts are strings, so plotly's separators do not touch them
        shown = [text.replace(".", ",") for text in shown]
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=timeline["end_year"], y=p, mode="lines+markers", customdata=shown,
        line={"color": "#c3c2bb", "width": 1.5}, marker={"color": list(colors), "size": 8},
        hovertemplate=timeline_text(lang, "hover", start=start_year) + "<extra></extra>",
        showlegend=False,
    ))
    figure.add_hline(
        y=0.05, line_dash="dash", line_color="#52514e",
        annotation_text=timeline_text(lang, "line"), annotation_position="top left",
    )
    figure.update_yaxes(type="log", range=[np.log10(P_FLOOR), 0], title=timeline_text(lang, "y_title"))
    figure.update_xaxes(title=timeline_text(lang, "x_title"), dtick=5)
    figure.update_layout(
        height=260, margin={"l": 10, "r": 10, "t": 10, "b": 10}, separators=separators,
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font={"color": "#0b0b0b"},
    )
    return figure
