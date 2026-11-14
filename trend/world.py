"""World board: every prepared region and measurement on one board of verdicts.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The challenge stresses that one variable can trend one way in one region and the opposite way in
another. This module runs the detective on every prepared region and measurement with the same rules
as the investigation board, finds measurements whose confirmed trends point in opposite directions
in different regions, and draws the board as an HTML table.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode

import pandas as pd

from trend.fetch import load_processed
from trend.regions import REGIONS
from trend.stats import TrendResult, analyze_trend, to_annual
from trend.variables import VARIABLES

NO_SNOW_MM = 1.0  # a snowfall record whose yearly totals all stay below this means "it never snows here"
NO_HOT_DAYS = 1.0  # fewer hot days than this in every year means "it is never that hot here"
# Share of trendless cases that still get a "Confirmed" stamp (scripts/accuracy_report.py): about 3%
# with independent years; with persistent years about 5-7% over 15 years or more and about 10% for the
# short records (7-10 years) and strongly persistent ones on this board.
FALSE_ALARM_LOW, FALSE_ALARM_HIGH = 0.03, 0.10

SHORT_NAMES = {
    "en": {
        "colorado": "Colorado", "marmara": "Istanbul", "medina": "Medina", "beijing": "Beijing",
        "los_angeles": "Los Angeles", "cairo_nile": "Cairo", "amazon": "Amazon", "sahel": "Sahel",
        "alps": "Alps", "siberia": "Siberia",
    },
    "tr": {
        "colorado": "Colorado", "marmara": "İstanbul", "medina": "Medine", "beijing": "Pekin",
        "los_angeles": "Los Angeles", "cairo_nile": "Kahire", "amazon": "Amazon", "sahel": "Sahel",
        "alps": "Alpler", "siberia": "Sibirya",
    },
}

# Names inside English sentences ("falls in the Amazon"); Turkish and table headers use SHORT_NAMES.
SENTENCE_NAMES_EN = {"amazon": "the Amazon", "sahel": "the Sahel", "alps": "the Alps"}


def place_name(lang: str, region_key: str) -> str:
    if lang == "en" and region_key in SENTENCE_NAMES_EN:
        return SENTENCE_NAMES_EN[region_key]
    return SHORT_NAMES.get(lang, SHORT_NAMES["en"])[region_key]


WORLD_TEXT = {
    "en": {
        "view_label": "🌍 World board",
        "title": "World board: every region, every clue",
        "intro": (
            "The detective ran every prepared region and every measurement with the same rules as the "
            "investigation board, over each record's full length. ▲ and ▼ mark confirmed rises and falls "
            "(both tests agree); click any cell to open its case file."
        ),
        "opposite_title": "Same clue, opposite trends",
        "opposite_line": "**{variable}** rises in {up} but falls in {down}.",
        "opposite_none": "No measurement has confirmed trends in opposite directions yet.",
        "opposite_why": (
            "The challenge's key point: the same Earth variable can move in opposite directions in "
            "different places, because local causes (rain belts, laws, fires, farming) differ."
        ),
        "open_case": "Open {region}: {variable}",
        "counts": (
            "{tested} cases tested: {confirmed} confirmed, {disputed} disputed, {weak} weak clues, "
            "{none} without evidence."
        ),
        "chance_note": (
            "Keep in mind: even if nothing were changing anywhere, about {low}-{high} of {tested} tests "
            "would get a Confirmed stamp by chance. A verdict is stronger when a second record, a nearby "
            "region or a known cause points the same way."
        ),
        "legend": (
            "▲ ▼ confirmed rise / fall · ▲? ▼? disputed (only the headline test) · △ ▽ weak clue (only "
            "the second witness) · – no evidence · blank: no data, too few years or no snow"
        ),
        "corner": "Measurement",
        "cell_title": "{region} · {variable}: {status}",
        "cell_rate": "{rate} {unit} per decade, {start}–{end}",
    },
    "tr": {
        "view_label": "🌍 Dünya panosu",
        "title": "Dünya panosu: her bölge, her ipucu",
        "intro": (
            "Dedektif, hazır bölgelerin hepsini ve ölçümlerin hepsini soruşturma panosundaki kurallarla, "
            "her kaydın tamamı üzerinden inceledi. ▲ ve ▼ doğrulanmış artış ve azalışları gösterir (iki "
            "test de aynı fikirde); dosyasını açmak için bir hücreye tıkla."
        ),
        "opposite_title": "Aynı ipucu, zıt trendler",
        "opposite_line": "**{variable}** {up} bölgesinde artıyor, {down} bölgesinde azalıyor.",
        "opposite_none": "Henüz zıt yönde doğrulanmış trendi olan bir ölçüm yok.",
        "opposite_why": (
            "Yarışmanın ana fikri: Aynı yer sistemi değişkeni farklı yerlerde zıt yönlere gidebilir, "
            "çünkü yerel nedenler (yağmur kuşakları, yasalar, yangınlar, tarım) farklıdır."
        ),
        "open_case": "Aç: {region} – {variable}",
        "counts": (
            "{tested} dosya incelendi: {confirmed} doğrulandı, {disputed} tartışmalı, {weak} zayıf ipucu, "
            "{none} delilsiz."
        ),
        "chance_note": (
            "Unutma: Hiçbir yerde hiçbir şey değişmiyor olsaydı bile {tested} testin yaklaşık {low}-{high} "
            "tanesi şans eseri Doğrulandı damgası alırdı. İkinci bir kayıt, yakın bir bölge ya da bilinen "
            "bir neden aynı yönü gösteriyorsa karar daha güçlüdür."
        ),
        "legend": (
            "▲ ▼ doğrulanmış artış / azalış · ▲? ▼? tartışmalı (sadece ana test) · △ ▽ zayıf ipucu "
            "(sadece ikinci tanık) · – delil yok · boş: veri yok, yıl az ya da kar yağmıyor"
        ),
        "corner": "Ölçüm",
        "cell_title": "{region} · {variable}: {status}",
        "cell_rate": "{rate} {unit} / 10 yıl, {start}–{end}",
    },
}


def world_text(lang: str, key: str, **values) -> str:
    text = WORLD_TEXT.get(lang, WORLD_TEXT["en"])[key]
    return text.format(**values) if values else text


def case_status(result: TrendResult | None) -> str:
    """The verdict stamp of a clue card."""
    if result is None:
        return "open"
    if result.significant:
        return "confirmed" if result.agrees else "disputed"
    return "noevidence" if result.agrees else "weak"


@dataclass(frozen=True)
class Verdict:
    """One clue card: the complete years, the dropped years, the trend and the stamp."""

    annual: pd.DataFrame | None
    incomplete: list[int]
    result: TrendResult | None
    status: str


def board_verdict(monthly: pd.DataFrame | None, variable_key: str) -> Verdict:
    """Yearly series, trend and stamp for one measurement, with the investigation board's rules."""
    if monthly is None:
        return Verdict(None, [], None, "open")
    variable = VARIABLES[variable_key]
    annual, incomplete = to_annual(monthly, variable)
    if variable_key == "snowfall" and len(annual) and annual["value"].max() < NO_SNOW_MM:
        return Verdict(None, incomplete, None, "no_snow")
    if variable_key == "hot_days" and len(annual) and annual["value"].max() < NO_HOT_DAYS:
        return Verdict(None, incomplete, None, "no_hot")
    if len(annual) < variable.min_years:
        return Verdict(None, incomplete, None, "insufficient")
    result = analyze_trend(annual["year"], annual["value"], min_years=variable.min_years)
    return Verdict(annual, incomplete, result, case_status(result))


@dataclass(frozen=True)
class Cell:
    region: str
    variable: str
    status: str
    slope_per_decade: float | None = None
    p_value: float | None = None
    start_year: int | None = None
    end_year: int | None = None

    @property
    def direction(self) -> str | None:
        if not self.slope_per_decade:
            return None
        return "up" if self.slope_per_decade > 0 else "down"


def world_cells(loader: Callable[[str, str], pd.DataFrame | None] = load_processed) -> dict[tuple[str, str], Cell]:
    """Run the detective on every prepared region and measurement (full records)."""
    cells: dict[tuple[str, str], Cell] = {}
    for region_key in REGIONS:
        for variable_key in VARIABLES:
            verdict = board_verdict(loader(region_key, variable_key), variable_key)
            result = verdict.result
            if result is None:
                cells[(region_key, variable_key)] = Cell(region_key, variable_key, verdict.status)
            else:
                cells[(region_key, variable_key)] = Cell(
                    region_key, variable_key, verdict.status, float(result.slope_per_decade),
                    float(result.p_value), int(result.start_year), int(result.end_year),
                )
    return cells


TESTED = ("confirmed", "disputed", "noevidence", "weak")


def summary_counts(cells: dict[tuple[str, str], Cell]) -> dict[str, int]:
    counts = {status: 0 for status in TESTED}
    for cell in cells.values():
        if cell.status in counts:
            counts[cell.status] += 1
    counts["tested"] = sum(counts[status] for status in TESTED)
    counts["low"] = max(1, round(counts["tested"] * FALSE_ALARM_LOW)) if counts["tested"] else 0
    counts["high"] = max(counts["low"], round(counts["tested"] * FALSE_ALARM_HIGH))
    return counts


def opposite_trends(cells: dict[tuple[str, str], Cell]) -> list[dict]:
    """Measurements confirmed rising in some regions and confirmed falling in others."""
    found = []
    for variable_key in VARIABLES:
        confirmed = [c for c in cells.values() if c.variable == variable_key and c.status == "confirmed"]
        up = [c.region for c in confirmed if c.direction == "up"]
        down = [c.region for c in confirmed if c.direction == "down"]
        if up and down:
            found.append({"variable": variable_key, "up": up, "down": down})
    return found


def cell_symbol(cell: Cell) -> str:
    if cell.status == "confirmed":
        return "▲" if cell.direction == "up" else "▼"
    if cell.status == "disputed":
        return "▲?" if cell.direction == "up" else "▼?"
    if cell.status == "weak":
        return "△" if cell.direction == "up" else "▽"
    if cell.status == "noevidence":
        return "–"
    return ""


CELL_COLORS = {
    "confirmed": ("#1c5cab", "#e3eefc"),
    "disputed": ("#a8501b", "#fbeee3"),
    "weak": ("#a8501b", "#fdf6f0"),
    "noevidence": ("#52514e", "#f3f2ee"),
}


def case_link(lang: str, region_key: str, variable_key: str) -> str:
    """Relative link that reopens the app on this region and case (full record)."""
    return "?" + urlencode({"lang": lang, "region": region_key, "case": variable_key})


def world_table_html(
    cells: dict[tuple[str, str], Cell],
    lang: str,
    variable_name: Callable[[str], str],
    status_name: Callable[[str], str],
    unit_name: Callable[[str], str],
    rate_text: Callable[[str, float], str],
) -> str:
    """The board as a scrollable HTML table: rows are measurements, columns are regions."""
    regions = list(REGIONS)
    head = "".join(
        f"<th scope='col'>{html.escape(SHORT_NAMES.get(lang, SHORT_NAMES['en'])[r])}</th>" for r in regions
    )
    rows = []
    for variable_key in VARIABLES:
        if all(cells.get((r, variable_key), Cell(r, variable_key, "open")).status == "open" for r in regions):
            continue  # no prepared region has this measurement yet
        tds = []
        for region_key in regions:
            cell = cells.get((region_key, variable_key), Cell(region_key, variable_key, "open"))
            symbol = cell_symbol(cell)
            color, background = CELL_COLORS.get(cell.status, ("#898781", "#ffffff"))
            title = world_text(
                lang, "cell_title", region=SHORT_NAMES.get(lang, SHORT_NAMES["en"])[region_key],
                variable=variable_name(variable_key), status=status_name(cell.status),
            )
            if cell.slope_per_decade is not None:
                title += " · " + world_text(
                    lang, "cell_rate", rate=rate_text(variable_key, cell.slope_per_decade),
                    unit=unit_name(variable_key), start=cell.start_year, end=cell.end_year,
                )
            content = html.escape(symbol) if symbol else "&nbsp;"
            if cell.status in TESTED:
                content = (
                    f"<a href='{html.escape(case_link(lang, region_key, variable_key))}' target='_self' "
                    f"style='color:{color};text-decoration:none;display:block'>{content}</a>"
                )
            tds.append(
                f"<td title='{html.escape(title)}' style='color:{color};background:{background}'>{content}</td>"
            )
        rows.append(f"<tr><th scope='row'>{html.escape(variable_name(variable_key))}</th>{''.join(tds)}</tr>")
    return (
        "<div class='world-wrap'><table class='world'>"
        f"<thead><tr><th scope='col'>{html.escape(world_text(lang, 'corner'))}</th>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


WORLD_STYLE = """
<style>
.world-wrap { overflow-x: auto; margin: 6px 0 8px 0; }
table.world { border-collapse: collapse; font-size: 0.86rem; min-width: 720px; }
table.world th, table.world td { border: 1px solid #e1e0d9; padding: 6px 8px; text-align: center; }
table.world thead th { background: #fcfcfb; font-weight: 700; color: #0b0b0b; white-space: nowrap; }
table.world tbody th { text-align: left; font-weight: 600; color: #0b0b0b; white-space: nowrap; background: #fcfcfb; }
table.world td { font-size: 1.15rem; font-weight: 700; min-width: 48px; }
</style>
"""
