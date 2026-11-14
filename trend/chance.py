"""Can chance fool the detective? Pretend worlds without a trend, tested by a naive test and by the detective.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

A button in the case file makes many simulated yearly series that have no trend at all ("pretend
worlds"). Each world has as many years as the case and the same year-to-year persistence: red noise,
AR(1) with the case's lag-1 autocorrelation as ``phi``, a burn-in of 50 values and unit standard
deviation. This is the recipe of ``scripts/accuracy_report.py``, copied here so that the app never
imports from ``scripts/``. Every world is tested twice:

* a naive test: plain ordinary least squares (``scipy.stats.linregress``), p < 0.05, with no correction
  for persistence;
* the detective: ``analyze_trend`` (trend/stats.py), fooled only by a "Confirmed" stamp (the headline
  test significant and the second witness agreeing).

In a persistent record neighbouring years resemble each other, so a run of high years looks like a trend
to the naive test far more often than 5% of the time. The detective's effective sample size and its
second witness keep its false alarms low. The page shows how often each was fooled and compares this with
the real case's p-value. The worlds are random, so a new click gives slightly different numbers; the
long-run rates, from thousands of worlds, are in the README (``scripts/accuracy_report.py``).
"""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
from scipy import stats

from trend.charts import AXIS, FONT_FAMILY, GRIDLINE, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY
from trend.i18n import num, p_phrase, status_text
from trend.stats import DEFAULT_ALPHA, MIN_YEARS, analyze_trend

DEFAULT_RUNS = 400  # pretend worlds per click: about one second for 45 years on a laptop; less chance swing
MAX_PHI = 0.95  # stronger persistence is clipped (the noise would hardly move within a record)
BURN_IN = 50  # values thrown away so that every world starts in its usual state
LAST_YEAR = 2025  # pretend years run from 2026 - n to 2025, as in scripts/accuracy_report.py
MIN_WORLD_YEARS = 3  # a straight line through fewer points has no p-value
STRONG_P = 0.01  # below this the real case is "rarely produced by chance alone"
DETECTIVE_HIGH_SHARE = 0.075  # above this the detective's own false alarms are named (5% plus sampling swing)

WORLD_COLOR = "#898781"  # grey, the "No evidence" colour of trend/seasonal.py: a pretend series
NAIVE_COLOR = "#a8501b"  # orange, the "Disputed" colour: the naive test's straight line
FIGURE_HEIGHT = 240

CHANCE_TEXT = {
    "en": {
        "title": "🎲 Can chance fool the detective?",
        "intro": (
            "We make {runs} pretend worlds with no trend at all. Each is {n} years long and as “sticky” "
            "from year to year as this record: a year resembles the one before as much as here (lag-1 "
            "autocorrelation {phi}; 0 means not at all, 1 means completely). Then we test every world "
            "twice. A fair test should be fooled in only about 1 world in 20 (5%)."
        ),
        "intro_independent": (
            "We make {runs} pretend worlds with no trend at all, each {n} years long. In this record a "
            "year hardly resembles the one before (lag-1 autocorrelation {phi}), so the pretend years are "
            "independent of each other too. Then we test every world twice. A fair test should be fooled "
            "in only about 1 world in 20 (5%)."
        ),
        "button": "Make {runs} worlds without a trend",
        "running": "Making {runs} worlds without a trend…",
        "result": (
            "A naive test (no correction for persistence) saw a trend in **{naive} of {runs}** worlds "
            "({naive_pct}%).\n"
            "The detective stamped “{stamp}” in **{detective}** ({detective_pct}%)."
        ),
        "detective_high": (
            "That is still above 5%: in a record this short and this sticky the correction cannot remove all "
            "of the persistence, but the detective is fooled far less often than the naive test."
        ),
        "compare_strong": "The real case has {p}: chance alone rarely produces evidence this strong.",
        "compare_middle": (
            "The real case has {p}: under the 5% line, but chance alone can now and then produce evidence "
            "this strong."
        ),
        "compare_chance": "The real case has {p}: it looks like what chance alone could produce.",
        "note": (
            "The worlds are random, so a new click gives slightly different numbers. The long-run rates, "
            "from thousands of worlds, are in the README (scripts/accuracy_report.py)."
        ),
        "no_example": "This time no world fooled only the naive test, so there is no example to show.",
        "figure_title": "A pretend world with no trend",
        "figure_subtitle": "Naive test: a trend · Detective: not confirmed",
        "values_name": "Pretend world",
        "line_name": "Naive straight line ({p})",
        "truth": "truth: no trend",
    },
    "tr": {
        "title": "🎲 Tesadüf dedektifi kandırabilir mi?",
        "intro": (
            "Hiç trendi olmayan {runs} hayali dünya üretiyoruz. Her biri {n} yıl uzunluğunda ve bu kayıt "
            "kadar “yapışkan”: her yıl bir öncekine buradaki kadar benziyor (gecikme-1 otokorelasyonu "
            "{phi}; 0 hiç benzemiyor, 1 tıpatıp aynı demek). Sonra her dünyayı iki kez test ediyoruz. "
            "Adil bir test, yaklaşık 20 dünyadan yalnızca 1'ine (%5) kanmalı."
        ),
        "intro_independent": (
            "Hiç trendi olmayan {runs} hayali dünya üretiyoruz, her biri {n} yıl uzunluğunda. Bu kayıtta "
            "bir yıl öncekine pek benzemiyor (gecikme-1 otokorelasyonu {phi}); bu yüzden hayali dünyalarda "
            "da her yıl öncekinden bağımsız. Sonra her dünyayı iki kez test ediyoruz. Adil bir test, "
            "yaklaşık 20 dünyadan yalnızca 1'ine (%5) kanmalı."
        ),
        "button": "Trendi olmayan {runs} dünya üret",
        "running": "Trendi olmayan {runs} dünya üretiliyor…",
        "result": (
            "Sürekliliği hesaba katmayan saf bir test, {runs} dünyanın **{naive}** tanesinde trend gördü "
            "(%{naive_pct}).\n"
            "Dedektif ise **{detective}** tanesine “{stamp}” damgası vurdu (%{detective_pct})."
        ),
        "detective_high": (
            "Bu hâlâ %5'in üstünde: bu kadar kısa ve bu kadar yapışkan bir kayıtta düzeltme sürekliliğin "
            "hepsini gideremiyor; yine de dedektif saf testten çok daha az kanıyor."
        ),
        "compare_strong": "Gerçek dosyada {p}: tesadüf tek başına bu kadar güçlü bir delili nadiren üretir.",
        "compare_middle": (
            "Gerçek dosyada {p}: %5 sınırının altında, ama tesadüf tek başına da ara sıra bu kadar güçlü bir "
            "delil üretebilir."
        ),
        "compare_chance": "Gerçek dosyada {p}: bu, tesadüfün tek başına üretebileceği bir sonuca benziyor.",
        "note": (
            "Dünyalar rastgele üretildiği için her tıklamada sayılar biraz değişir. Binlerce dünyayla "
            "hesaplanan uzun vadeli oranlar README'de (scripts/accuracy_report.py)."
        ),
        "no_example": "Bu sefer yalnızca saf testi kandıran bir dünya çıkmadı; bu yüzden gösterilecek örnek yok.",
        "figure_title": "Trendi olmayan hayali bir dünya",
        "figure_subtitle": "Saf test: trend var · Dedektif: doğrulanmadı",
        "values_name": "Hayali dünya",
        "line_name": "Saf testin düz çizgisi ({p})",
        "truth": "gerçek: trend yok",
    },
}


def chance_text(lang: str, key: str, **values) -> str:
    """Text of this section in the interface language (English for an unknown language)."""
    text = CHANCE_TEXT.get(lang, CHANCE_TEXT["en"])[key]
    return text.format(**values) if values else text


def clip_phi(phi) -> float:
    """Persistence used for the pretend worlds: ``phi`` clipped to [0, 0.95]; negative, NaN or None is 0."""
    try:
        value = float(phi)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return min(value, MAX_PHI)


def red_noise(rng: np.random.Generator, phi: float, n: int) -> np.ndarray:
    """AR(1) noise with unit standard deviation (after a burn-in of 50 values).

    The recipe of ``scripts/accuracy_report.py``; ``phi`` is clipped with ``clip_phi`` first.
    """
    phi = clip_phi(phi)
    e = rng.normal(size=n + BURN_IN)
    x = np.zeros(n + BURN_IN)
    for t in range(1, n + BURN_IN):
        x[t] = phi * x[t - 1] + e[t]
    return x[BURN_IN:] * np.sqrt(1 - phi**2)


def naive_p_value(years, values) -> float:
    """p-value of a plain least-squares line (``scipy.stats.linregress``), with no correction for persistence."""
    return float(stats.linregress(np.asarray(years, dtype=float), np.asarray(values, dtype=float)).pvalue)


def naive_significant(years, values) -> bool:
    """The naive test: does a plain least-squares line have p < 0.05?"""
    return bool(naive_p_value(years, values) < DEFAULT_ALPHA)  # a NaN p-value (flat series) is False


def simulate(n_years: int, phi: float, runs: int = DEFAULT_RUNS, seed: int | None = None) -> dict:
    """Make ``runs`` pretend worlds without a trend and count how often each test is fooled.

    Every world has ``n_years`` years (2026 - n to 2025) of red noise with persistence ``clip_phi(phi)``.
    The naive test is fooled when a plain least-squares line has p < 0.05; the detective only when
    ``analyze_trend`` stamps "Confirmed" (significant and the second witness agrees). ``analyze_trend``
    runs with its default ``min_years``, lowered to ``n_years`` for a short record (CO₂ has 7 years); it
    only decides whether the test may run, never its result.

    Returns a dict with ``runs``, ``n``, ``phi`` (the persistence used), ``naive`` and ``detective`` (how
    many worlds fooled each test), ``naive_share`` and ``detective_share`` (fractions of ``runs``) and
    ``example``: a world that fooled the naive test but not the detective, or None when there is none.
    The example is a dict with ``years``, ``values``, ``naive_p`` and ``detective_p``; of all such worlds
    it is the most convincing fake trend, preferring one whose headline test is not significant at all
    (smallest naive p-value). The same ``seed`` gives the same worlds and counts.
    """
    n = int(n_years)
    runs = int(runs)
    if n < MIN_WORLD_YEARS:
        raise ValueError(f"A pretend world needs at least {MIN_WORLD_YEARS} years; got {n}.")
    if runs < 1:
        raise ValueError(f"At least one pretend world is needed; got {runs}.")
    phi_used = clip_phi(phi)
    rng = np.random.default_rng(seed)
    years = np.arange(LAST_YEAR - n + 1, LAST_YEAR + 1)
    min_years = min(MIN_YEARS, n)

    naive = detective = 0
    example, example_rank = None, None
    for _ in range(runs):
        values = red_noise(rng, phi_used, n)
        naive_p = naive_p_value(years, values)
        naive_hit = naive_p < DEFAULT_ALPHA
        result = analyze_trend(years, values, min_years=min_years)
        detective_hit = result.significant and result.agrees
        naive += int(naive_hit)
        detective += int(detective_hit)
        if naive_hit and not detective_hit:
            rank = (result.significant, naive_p)  # not significant at all first, then the strongest fake
            if example_rank is None or rank < example_rank:
                example_rank = rank
                example = {
                    "years": years.copy(), "values": values, "naive_p": naive_p,
                    "detective_p": float(result.p_value),
                }
    return {
        "runs": runs, "n": n, "phi": phi_used, "naive": naive, "detective": detective,
        "naive_share": naive / runs, "detective_share": detective / runs, "example": example,
    }


def intro_line(lang: str, runs: int, n: int, phi) -> str:
    """The intro above the button: how many worlds, how long and how persistent.

    ``phi`` is the case's lag-1 autocorrelation. A record whose years are not alike (``clip_phi`` rounds to
    0.00) gets the "independent years" wording with its own value, so a negative value is never shown as
    "sticky".
    """
    used = clip_phi(phi)
    if round(used, 2) > 0:
        return chance_text(lang, "intro", runs=runs, n=n, phi=num(used, lang, 2))
    try:
        shown = float(phi)
    except (TypeError, ValueError):
        shown = 0.0
    shown = shown if math.isfinite(shown) else 0.0
    return chance_text(lang, "intro_independent", runs=runs, n=n, phi=num(shown, lang, 2))


def _percent(count: int, runs: int, lang: str) -> str:
    """'18.5' or '20' (one decimal only when needed), with a decimal comma in Turkish."""
    pct = 100 * count / runs if runs else 0.0
    return num(pct, lang, 0 if abs(pct - round(pct)) < 1e-9 else 1)


def compare_line(lang: str, case_p: float) -> str:
    """How the real case's p-value compares with what chance alone produces (three wordings)."""
    if case_p < STRONG_P:
        key = "compare_strong"
    elif case_p < DEFAULT_ALPHA:
        key = "compare_middle"
    else:
        key = "compare_chance"
    return chance_text(lang, key, p=p_phrase(case_p, lang))


def summary_lines(lang: str, result: dict, case_p: float | None) -> list[str]:
    """The result in sentences: the naive test's count, the detective's count, then the real case.

    ``result`` comes from ``simulate``; ``case_p`` is the case's p-value (``TrendResult.p_value``). The
    comparison line is left out when ``case_p`` is None or NaN. Markdown (bold numbers), with a decimal
    comma in Turkish.
    """
    runs = int(result["runs"])
    text = chance_text(
        lang, "result", runs=runs, naive=int(result["naive"]), detective=int(result["detective"]),
        naive_pct=_percent(int(result["naive"]), runs, lang),
        detective_pct=_percent(int(result["detective"]), runs, lang),
        stamp=status_text(lang, "confirmed")[0],
    )
    lines = text.split("\n")
    # Clearly above 5% (more than the sampling swing of a few hundred worlds): say so instead of hiding it
    if runs and int(result["detective"]) / runs > DETECTIVE_HIGH_SHARE:
        lines.append(chance_text(lang, "detective_high"))
    if case_p is not None and math.isfinite(float(case_p)):
        lines.append(compare_line(lang, float(case_p)))
    return lines


def example_figure(example: dict, lang: str, separators: str = ".,") -> go.Figure:
    """The example pretend world: its yearly values, the naive straight line and the flat truth.

    ``example`` is ``simulate(...)["example"]``. Grey line with markers for the values, an orange line for
    the naive least-squares fit (its p-value in the hover) and a dotted line at zero for the truth (no
    trend). A two-line title says what the reader sees; about 240 px high, in the style of trend/charts.py.
    """
    years = np.asarray(example["years"], dtype=int)
    values = np.asarray(example["values"], dtype=float)
    fit = stats.linregress(years.astype(float), values)
    line = fit.intercept + fit.slope * years
    naive_p = float(example.get("naive_p", fit.pvalue))
    world_name = chance_text(lang, "values_name")
    line_name = chance_text(lang, "line_name", p=p_phrase(naive_p, lang))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years, y=values, mode="lines+markers", name=world_name,
            line={"color": WORLD_COLOR, "width": 2},
            marker={"size": 7, "color": WORLD_COLOR, "line": {"color": SURFACE, "width": 1.5}},
            hovertemplate=f"{_plotly_text(world_name)}: %{{y:.2f}}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years, y=line, mode="lines", name=line_name,
            line={"color": NAIVE_COLOR, "width": 2},
            hovertemplate=f"{_plotly_text(line_name)}: %{{y:.2f}}<extra></extra>",
        )
    )
    fig.add_hline(
        y=0, line_color=TEXT_SECONDARY, line_width=1, line_dash="dot",
        annotation_text=chance_text(lang, "truth"), annotation_position="bottom right",
        annotation_font={"size": 11, "color": TEXT_SECONDARY},
    )
    title = (
        f"<b>{_plotly_text(chance_text(lang, 'figure_title'))}</b><br>"
        f"<span style='font-size:12px;color:{TEXT_SECONDARY}'>"
        f"{_plotly_text(chance_text(lang, 'figure_subtitle'))}</span>"
    )
    fig.update_layout(
        title={
            "text": title, "x": 0, "xref": "paper", "xanchor": "left", "y": 1, "yref": "container",
            "yanchor": "top", "pad": {"t": 8}, "font": {"size": 13, "color": TEXT_PRIMARY},
        },
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT_FAMILY, "color": TEXT_SECONDARY, "size": 12},
        separators=separators,
        hovermode="x unified",
        hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT_PRIMARY}},
        margin={"l": 40, "r": 16, "t": 56, "b": 32},
        height=FIGURE_HEIGHT,
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDLINE, gridwidth=1, linecolor=AXIS, zeroline=False)
    return fig


def _plotly_text(text: str) -> str:
    """Plotly reads '<' as the start of a tag, so 'p < 0.001' is written with an entity."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
