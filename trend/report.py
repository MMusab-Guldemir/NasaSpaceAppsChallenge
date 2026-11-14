"""Downloadable case report: the verdict of one case on a single printable HTML page.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The case file in the app spreads its findings over several steps. This module puts them on one page
that a student, a teacher or a judge can keep: the stamp, the verdict in one sentence, a small chart of
the yearly values with the trend line, the second witness, a short "how to read this" box, the possible
reasons, the caveats, the data source and the share link. The page is self-contained (inline CSS, an
inline SVG chart drawn here, no scripts and no external files), so it opens offline and prints or saves
as PDF from any browser.

Every text that comes in is escaped with ``html.escape``. Some app texts are written in Markdown, so
``**bold**`` becomes <b>bold</b> after escaping; nothing else is interpreted. Numbers use
``trend.i18n.num`` (a decimal comma in Turkish).
"""
from __future__ import annotations

import html
import math
import re
from typing import Iterable, Sequence
from urllib.parse import quote

from trend.charts import AXIS, GRIDLINE, SERIES_1, SERIES_2, SURFACE
from trend.i18n import ci_bounds, method_name, num, p_phrase, status_text
from trend.stats import RECOMMENDED_YEARS, TrendResult

REPORT_TEXT = {
    "en": {
        "button": "⬇ Download the case report (HTML, printable)",
        "button_help": (
            "Puts the verdict, the chart, the possible reasons and the sources on one page. Open it in a "
            "browser to print it or save it as PDF."
        ),
        "eyebrow": "Earth System Trend Detective · Case report",
        "title": "Case report: {variable} in {region}",
        "period": "Period investigated: {start}–{end}",
        "print_hint": (
            "To keep a PDF copy, use your browser's Print command (Ctrl+P, or ⌘P on a Mac) and choose "
            "“Save as PDF”."
        ),
        "verdict_title": "Verdict",
        "headline_up": "Unlikely to be chance: a significant upward trend",
        "headline_down": "Unlikely to be chance: a significant downward trend",
        "headline_disputed": "Borderline: the two tests disagree",
        "headline_chance": "Could be chance: no clear trend",
        "verdict_up": (
            "The {subject} **rose by about {rate} {unit} per decade** from {start} to {end} ({level}% CI "
            "{low} to {high}), about {total} {unit} in total along the trend line ({p})."
        ),
        "verdict_down": (
            "The {subject} **fell by about {rate} {unit} per decade** from {start} to {end} ({level}% CI "
            "{low} to {high}), about {total} {unit} in total along the trend line ({p})."
        ),
        "verdict_none": (
            "**No significant trend** in the {subject} from {start} to {end}: the trend line changes by "
            "{rate} {unit} per decade ({level}% CI {low} to {high}), {total} {unit} in total ({p}), which "
            "cannot be told apart from natural year-to-year swings."
        ),
        "chance": "If there were no real trend, a trend this strong would appear by chance {chance}.",
        "tile_rate": "How much",
        "tile_total": "Total change",
        "tile_years": "Evidence used",
        "per_decade": "{rate} {unit} per decade",
        "ci": "{level}% CI {low} to {high}",
        "along_trend": "along the trend line",
        "years_count": "{n} complete years",
        "evidence_title": "The evidence: yearly values and trend line",
        "what": "What is measured? {definition}",
        "points": "Each point is one year: {label}; unit: {unit}.",
        "chart_title": "{label}, {start}–{end}, with the trend line",
        "legend_values": "Yearly values",
        "legend_trend": "Trend line ({rate} {unit} per decade)",
        "based_on": "Based on {n} complete years ({start} to {end}).",
        "neff": (
            "Neighbouring years resemble each other, so these {n} years carry about as much information "
            "as {n_eff} independent years."
        ),
        "short": "Only {n} years of data. Trend tests are less reliable with fewer than {rec} years.",
        "no_values": "No yearly values to draw.",
        "witness_title": "The second witness",
        "witness_agrees": "Agrees",
        "witness_disagrees": "Disagrees",
        "witness_auto": (
            "The {method} test, which does not assume a straight line, finds {found} ({p}; Sen's slope "
            "{sen} {unit} per decade)."
        ),
        "found_increasing": "an increasing trend",
        "found_decreasing": "a decreasing trend",
        "found_none": "no significant trend",
        "howto_title": "How to read this report",
        "howto_p": (
            "The **p-value** is the chance of seeing a trend at least this strong if there were really no "
            "trend. When p\u00a0<\u00a0{alpha}, we call the trend significant: unlikely to be chance."
        ),
        "howto_ci": (
            "The **{level}% confidence interval (CI)** is the range of rates per decade that are "
            "compatible with the data; when it does not include zero, the direction of the change is clear."
        ),
        "howto_total": (
            "**Total change** is the change along the trend line from the first to the last year, not the "
            "last value minus the first."
        ),
        "howto_witness": (
            "The **second witness**, the Mann-Kendall test, checks for a steady rise or fall without "
            "assuming a straight line. When both tests agree on a significant trend, the stamp says "
            "“{confirmed}”."
        ),
        "howto_why": (
            "**The test shows that something changed, not why.** Finding the cause needs other evidence."
        ),
        "howto_none": "No significant trend does not mean no change: a longer record may reveal one.",
        "reasons_title": "Possible reasons",
        "reasons_note": (
            "Explanations scientists often point to. The trend test alone cannot prove any of them."
        ),
        "caveats_title": "Keep in mind",
        "source_title": "Data source",
        "doi": "DOI",
        "share_title": "Open this case in the app",
        "share_note": (
            "This link opens exactly this case, period and language in the Earth System Trend Detective."
        ),
        "footer": (
            "Team Avni · NASA Space Apps Challenge 2026 · made with the Earth System Trend Detective; "
            "built with AI assistance (Claude by Anthropic)"
        ),
        "disclaimer": "Not affiliated with or endorsed by NASA.",
    },
    "tr": {
        "button": "⬇ Dosya raporunu indir (HTML, yazdırılabilir)",
        "button_help": (
            "Hükmü, grafiği, olası nedenleri ve kaynakları tek sayfada toplar. Tarayıcıda açıp "
            "yazdırabilir ya da PDF olarak kaydedebilirsin."
        ),
        "eyebrow": "Dünya Sistemi Trend Dedektifi · Dosya raporu",
        "title": "Dosya raporu: {region} – {variable}",
        "period": "İncelenen dönem: {start}–{end}",
        "print_hint": (
            "PDF olarak saklamak için tarayıcının Yazdır komutunu kullan (Ctrl+P, Mac'te ⌘P) ve "
            "“PDF olarak kaydet”i seç."
        ),
        "verdict_title": "Hüküm",
        "headline_up": "Tesadüf olması zor: anlamlı bir artış trendi",
        "headline_down": "Tesadüf olması zor: anlamlı bir azalış trendi",
        "headline_disputed": "Sınırda: iki test aynı fikirde değil",
        "headline_chance": "Tesadüf olabilir: belirgin bir trend yok",
        "verdict_up": (
            "{label}, {start}–{end} arasında **on yılda yaklaşık {rate} {unit} arttı** (%{level} güven "
            "aralığı: {low} ile {high}); trend çizgisi boyunca toplam artış yaklaşık {total} {unit} ({p})."
        ),
        "verdict_down": (
            "{label}, {start}–{end} arasında **on yılda yaklaşık {rate} {unit} azaldı** (%{level} güven "
            "aralığı: {low} ile {high}); trend çizgisi boyunca toplam azalış yaklaşık {total} {unit} ({p})."
        ),
        "verdict_none": (
            "{label} için {start}–{end} arasında **anlamlı bir trend yok**: trend çizgisi on yılda {rate} "
            "{unit} değişiyor (%{level} güven aralığı: {low} ile {high}), toplamda {total} {unit} ({p}); "
            "bu, doğal yıldan yıla dalgalanmadan ayırt edilemiyor."
        ),
        "chance": (
            "Gerçek bir trend olmasaydı, bu kadar güçlü bir trendin tesadüfen ortaya çıkma ihtimali "
            "{chance} olurdu."
        ),
        "tile_rate": "Ne kadar",
        "tile_total": "Toplam değişim",
        "tile_years": "Kullanılan delil",
        "per_decade": "{rate} {unit} / 10 yıl",
        "ci": "%{level} güven aralığı: {low} ile {high}",
        "along_trend": "trend çizgisi boyunca",
        "years_count": "{n} tam yıl",
        "evidence_title": "Delil: yıllık değerler ve trend çizgisi",
        "what": "Ne ölçülüyor? {definition}",
        "points": "Her nokta bir yıl: {label}; birim: {unit}.",
        "chart_title": "{label}, {start}–{end}, trend çizgisiyle",
        "legend_values": "Yıllık değerler",
        "legend_trend": "Trend çizgisi ({rate} {unit} / 10 yıl)",
        "based_on": "{n} tam yıla dayanıyor ({start}–{end}).",
        "neff": (
            "Komşu yıllar birbirine benzediği için bu {n} yıl, yaklaşık {n_eff} bağımsız yıl kadar bilgi "
            "taşıyor."
        ),
        "short": "Sadece {n} yıllık veri var. {rec} yıldan kısa dönemlerde trend testleri daha az güvenilir.",
        "no_values": "Çizilecek yıllık değer yok.",
        "witness_title": "İkinci tanık",
        "witness_agrees": "Doğruluyor",
        "witness_disagrees": "Doğrulamıyor",
        "witness_auto": (
            "Düz bir çizgi varsaymayan {method} testinin sonucu: {found} ({p}; Sen eğimi on yılda {sen} "
            "{unit})."
        ),
        "found_increasing": "artan trend",
        "found_decreasing": "azalan trend",
        "found_none": "anlamlı trend yok",
        "howto_title": "Bu rapor nasıl okunur?",
        "howto_p": (
            "**p-değeri**, gerçekte hiç trend yokken en az bu kadar güçlü bir trend görme ihtimalidir. "
            "p\u00a0<\u00a0{alpha} olduğunda trendi anlamlı, yani tesadüf olması zor kabul ederiz."
        ),
        "howto_ci": (
            "**%{level} güven aralığı**, verilerle uyumlu on yıllık değişim hızlarının aralığıdır; aralık "
            "sıfırı içermiyorsa değişimin yönü bellidir."
        ),
        "howto_total": (
            "**Toplam değişim**, trend çizgisi boyunca ilk yıldan son yıla olan değişimdir; son değer eksi "
            "ilk değer değildir."
        ),
        "howto_witness": (
            "**İkinci tanık** olan Mann-Kendall testi, düz bir çizgi varsaymadan istikrarlı bir artış ya da "
            "azalış olup olmadığına bakar. İki test de anlamlı bir trend üzerinde aynı fikirdeyse damgada "
            "“{confirmed}” yazar."
        ),
        "howto_why": (
            "**Test bir şeyin değiştiğini gösterir, nedenini göstermez.** Nedeni bulmak için başka delil "
            "gerekir."
        ),
        "howto_none": (
            "Anlamlı trend bulunmaması değişim olmadığı anlamına gelmez; daha uzun bir kayıt bir trendi "
            "ortaya çıkarabilir."
        ),
        "reasons_title": "Olası nedenler",
        "reasons_note": (
            "Bilim insanlarının sık gösterdiği açıklamalar. Trend testi bunların hiçbirini tek başına "
            "kanıtlayamaz."
        ),
        "caveats_title": "Dikkat edilecekler",
        "source_title": "Veri kaynağı",
        "doi": "DOI",
        "share_title": "Bu dosyayı uygulamada aç",
        "share_note": (
            "Bu link, Dünya Sistemi Trend Dedektifi'nde tam olarak bu dosyayı, dönemi ve dili açar."
        ),
        "footer": (
            "Avni Takımı · NASA Space Apps Challenge 2026 · Dünya Sistemi Trend Dedektifi ile hazırlandı; "
            "yapay zekâ (Anthropic'in Claude'u) yardımıyla geliştirildi"
        ),
        "disclaimer": "NASA ile bağlantılı değildir ve NASA tarafından onaylanmamıştır.",
    },
}


def report_text(lang: str, key: str, **values) -> str:
    """A text of the case report in the chosen language (English for an unknown language)."""
    text = REPORT_TEXT.get(lang, REPORT_TEXT["en"])[key]
    return text.format(**values) if values else text


STAMP_CLASSES = ("confirmed", "disputed", "noevidence", "weak")  # any other status gets a dashed grey stamp
CHART_WIDTH, CHART_HEIGHT = 600, 250
PLOT_LEFT, PLOT_RIGHT, PLOT_TOP, PLOT_BOTTOM = 62, 578, 30, 214  # the plot area inside the SVG
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _esc(text) -> str:
    return html.escape(str(text), quote=True)


def _rich(text) -> str:
    """Escape a text, then turn the app's Markdown **bold** into <b>bold</b>."""
    return _BOLD.sub(r"<b>\1</b>", _esc(text))


def _nowrap(text: str) -> str:
    """Keep a short phrase such as "p < 0.001" on one line (non-breaking spaces)."""
    return str(text).replace(" ", "\u00a0")


def _lower_first(text: str) -> str:
    """First letter in lower case for use inside an English sentence; acronyms (NDVI, CO₂) stay."""
    if len(text) > 1 and text[1].isupper():
        return text
    return text[:1].lower() + text[1:]


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def report_filename(region_key: str, variable_key: str, start_year: int, end_year: int) -> str:
    """File name of the report, e.g. "trend-detective_marmara_hot_days_1981-2025.html" (never a space)."""
    region = _UNSAFE_NAME.sub("-", str(region_key)) or "area"
    variable = _UNSAFE_NAME.sub("-", str(variable_key)) or "case"
    return f"trend-detective_{region}_{variable}_{int(start_year)}-{int(end_year)}.html"


# --- The chart ------------------------------------------------------------------------------------


def _nice_step(span: float, target: int = 5) -> float:
    """A round tick step (1, 2, 2.5 or 5 times a power of ten) giving about ``target`` intervals."""
    raw = span / target
    power = 10.0 ** math.floor(math.log10(raw))
    for factor in (1.0, 2.0, 2.5, 5.0):
        if raw <= factor * power * (1 + 1e-9):
            return factor * power
    return 10.0 * power


def _step_decimals(step: float) -> int:
    """The fewest decimals that show every tick of this step exactly (0.25 gives 2, 5 gives 0)."""
    for decimals in range(7):
        if abs(round(step, decimals) - step) <= step * 1e-6:
            return decimals
    return 6


def _year_ticks(first: float, last: float) -> list[int]:
    """Round years for the x-axis: at most about ten labels."""
    span = last - first
    step = next((s for s in (1, 2, 5, 10, 20, 25, 50, 100) if span / s <= 10), 100 * math.ceil(span / 1000))
    return list(range(int(math.ceil(first / step) * step), int(math.floor(last)) + 1, step))


def report_chart_svg(
    lang: str,
    years: Iterable,
    values: Iterable,
    slope_per_year: float,
    *,
    unit: str,
    decimals: int = 2,
    title: str = "",
) -> str:
    """Inline SVG line chart of the yearly values with the fitted trend line (no libraries, no script).

    The trend line has the given slope and passes through the mean year and the mean value of the drawn
    points, where an OLS line always passes (the intercept implied by the data). Points with a missing
    year or value are left out. Raises ``ValueError`` when ``years`` and ``values`` differ in length;
    returns a short note instead of a chart when no point is left.
    """
    years, values = list(years), list(values)
    if len(years) != len(values):
        raise ValueError("years and values must have the same length.")
    points = sorted((float(x), float(y)) for x, y in zip(years, values) if _finite(x) and _finite(y))
    if not points:
        return f"<p class='caption'>{_esc(report_text(lang, 'no_values'))}</p>"

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    x_mean, y_mean = sum(xs) / len(xs), sum(ys) / len(ys)
    trend = None
    if _finite(slope_per_year) and xs[-1] > xs[0]:
        slope = float(slope_per_year)
        trend = [(x, y_mean + slope * (x - x_mean)) for x in (xs[0], xs[-1])]

    x_low, x_high = (xs[0], xs[-1]) if xs[-1] > xs[0] else (xs[0] - 1.0, xs[0] + 1.0)
    reach = ys + ([y for _, y in trend] if trend else [])
    y_low, y_high = min(reach), max(reach)
    if y_high - y_low <= 1e-9 * max(1.0, abs(y_high)):  # constant values: give them some room
        pad = abs(y_high) * 0.05 or 1.0
        y_low, y_high = y_low - pad, y_high + pad
    step = _nice_step(y_high - y_low)
    axis_low = math.floor(y_low / step) * step
    axis_high = math.ceil(y_high / step) * step
    ticks = [axis_low + i * step for i in range(int(round((axis_high - axis_low) / step)) + 1)]
    tick_decimals = _step_decimals(step)

    def px(x: float) -> float:
        return PLOT_LEFT + (x - x_low) / (x_high - x_low) * (PLOT_RIGHT - PLOT_LEFT)

    def py(y: float) -> float:
        return PLOT_BOTTOM - (y - axis_low) / (axis_high - axis_low) * (PLOT_BOTTOM - PLOT_TOP)

    label = title or report_text(lang, "legend_values")
    parts = [
        f"<svg class='chart-svg' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {CHART_WIDTH} {CHART_HEIGHT}' "
        f"role='img' aria-label='{_esc(label)}'>",
        f"<title>{_esc(label)}</title>",
        f"<rect x='0' y='0' width='{CHART_WIDTH}' height='{CHART_HEIGHT}' fill='{SURFACE}'/>",
        f"<text x='10' y='18' text-anchor='start'>{_esc(unit)}</text>",
    ]
    for tick in ticks:
        y = py(tick)
        parts.append(
            f"<line x1='{PLOT_LEFT}' y1='{y:.1f}' x2='{PLOT_RIGHT}' y2='{y:.1f}' stroke='{GRIDLINE}' "
            "stroke-width='1'/>"
        )
        parts.append(
            f"<text x='{PLOT_LEFT - 8}' y='{y + 4:.1f}' text-anchor='end'>{_esc(num(tick, lang, tick_decimals))}</text>"
        )
    parts.append(
        f"<line x1='{PLOT_LEFT}' y1='{PLOT_BOTTOM}' x2='{PLOT_RIGHT}' y2='{PLOT_BOTTOM}' stroke='{AXIS}' "
        "stroke-width='1'/>"
    )
    for year in _year_ticks(x_low, x_high):
        x = px(year)
        parts.append(
            f"<line x1='{x:.1f}' y1='{PLOT_BOTTOM}' x2='{x:.1f}' y2='{PLOT_BOTTOM + 5}' stroke='{AXIS}' "
            "stroke-width='1'/>"
        )
        parts.append(f"<text x='{x:.1f}' y='{PLOT_BOTTOM + 21}' text-anchor='middle'>{year}</text>")
    coordinates = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in points)
    parts.append(
        f"<polyline class='values' points='{coordinates}' fill='none' stroke='{SERIES_1}' stroke-width='2' "
        "stroke-linejoin='round' stroke-linecap='round'/>"
    )
    for x, y in points:
        parts.append(
            f"<circle cx='{px(x):.1f}' cy='{py(y):.1f}' r='3.5' fill='{SERIES_1}' stroke='{SURFACE}' "
            f"stroke-width='1.5'><title>{int(round(x))}: {_esc(num(y, lang, decimals))} {_esc(unit)}</title></circle>"
        )
    if trend:
        (x1, y1), (x2, y2) = trend
        parts.append(
            f"<line class='trend' x1='{px(x1):.1f}' y1='{py(y1):.1f}' x2='{px(x2):.1f}' y2='{py(y2):.1f}' "
            f"stroke='{SERIES_2}' stroke-width='2.5' stroke-linecap='round'/>"
        )
    parts.append("</svg>")
    return "".join(parts)


# --- The page -------------------------------------------------------------------------------------

REPORT_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; background: #f3f2ee; color: #0b0b0b;
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page {
  max-width: 820px; margin: 24px auto; padding: 32px 40px; background: #fcfcfb;
  border: 1px solid #e1e0d9; border-radius: 10px;
}
.eyebrow {
  font-family: "Special Elite", "Courier New", Courier, monospace; letter-spacing: 0.12em;
  text-transform: uppercase; color: #52514e; font-size: 0.8rem; font-weight: 400; margin: 0;
}
h1 { font-size: 1.75rem; line-height: 1.25; margin: 6px 0; }
h2 { font-size: 1.05rem; color: #2a78d6; margin: 0 0 6px 0; }
p { margin: 0 0 6px 0; }
.meta, .chance, .meaning { color: #52514e; }
.meaning { font-size: 0.9rem; }
.hint {
  font-size: 0.85rem; color: #52514e; border: 1px dashed #c3c2b7; border-radius: 6px;
  padding: 6px 10px; margin-top: 10px;
}
section { margin-top: 22px; break-inside: avoid; }
.verdict {
  background: #ffffff; border: 1px solid #e1e0d9; border-left: 8px solid #2a78d6;
  border-radius: 10px; padding: 14px 20px;
}
.verdict.disputed, .verdict.weak { border-left-color: #a8501b; }
.verdict.noevidence, .verdict.other { border-left-color: #898781; }
.stamp {
  display: inline-block; font-family: "Special Elite", "Courier New", Courier, monospace;
  font-size: 1.05rem; letter-spacing: 0.08em; text-transform: uppercase; padding: 2px 10px;
  border: 2px solid currentColor; border-radius: 4px; transform: rotate(-3deg);
  margin: 8px 8px 4px 0; color: #1c5cab; background: rgba(255, 255, 255, 0.6);
}
.stamp.disputed, .stamp.weak { color: #a8501b; }
.stamp.noevidence { color: #52514e; }
.stamp.other { color: #898781; border-style: dashed; }
.headline { font-size: 1.3rem; font-weight: 800; line-height: 1.3; margin: 8px 0 6px 0; }
.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.tile { background: #ffffff; border: 1px solid #e1e0d9; border-radius: 8px; padding: 10px 14px; }
.tile .label { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: #52514e; }
.tile .value { font-size: 1.15rem; font-weight: 700; margin: 2px 0; }
.tile .sub { font-size: 0.82rem; color: #52514e; }
.chart-svg {
  display: block; width: 100%; height: auto; margin: 8px 0 4px 0;
  border: 1px solid #e1e0d9; border-radius: 8px;
}
.chart-svg text { font: 13px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; fill: #52514e; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 18px; font-size: 0.85rem; color: #52514e; margin: 4px 0 6px 0; }
.key { display: inline-block; width: 22px; border-top: 3px solid; vertical-align: middle; margin-right: 6px; }
.caption, .note, .citation { font-size: 0.86rem; color: #52514e; }
.warn {
  background: #fbeee3; border: 1px solid #f0d4bd; color: #7a3a14; border-radius: 6px;
  padding: 6px 10px; font-size: 0.9rem;
}
.badge {
  display: inline-block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; border-radius: 999px; padding: 1px 9px; margin-right: 6px; vertical-align: 1px;
}
.badge.agrees { background: #e3eefc; color: #1c5cab; }
.badge.disagrees { background: #fbeee3; color: #a8501b; }
.howto { background: #ffffff; border: 1px solid #e1e0d9; border-radius: 10px; padding: 14px 20px; }
ul { margin: 4px 0 0 0; padding-left: 20px; }
li { margin: 3px 0; }
a { color: #1c5cab; overflow-wrap: anywhere; }
footer { margin-top: 28px; padding-top: 10px; border-top: 1px solid #e1e0d9; font-size: 0.8rem; color: #52514e; }
footer p { margin: 0 0 2px 0; }
@media (max-width: 640px) {
  .page { margin: 0; border: 0; border-radius: 0; padding: 20px 16px; }
  .tiles { grid-template-columns: 1fr; }
  h1 { font-size: 1.4rem; }
}
@page { size: A4; margin: 14mm; }
@media print {
  body { background: #ffffff; font-size: 10pt; line-height: 1.45; }
  .page { max-width: none; margin: 0; padding: 0; border: 0; background: #ffffff; }
  .noprint { display: none; }
  section { margin-top: 14px; }
  .chart-svg { width: 86%; margin: 6px auto 4px auto; }
  .howto { padding: 10px 16px; }
  h1 { font-size: 1.5rem; }
  li { margin: 1px 0; }
  footer { margin-top: 16px; }
  a { color: inherit; text-decoration: none; }
}
"""


def _tile(label: str, value: str, sub: str) -> str:
    return (
        f"<div class='tile'><div class='label'>{_esc(label)}</div><div class='value'>{_esc(value)}</div>"
        f"<div class='sub'>{_esc(sub)}</div></div>"
    )


def _bullets(items: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{_rich(item)}</li>" for item in items) + "</ul>"


def _status_meaning(lang: str, status: str) -> str:
    try:
        return status_text(lang, status)[1]
    except KeyError:
        return ""


def case_report_html(
    lang: str,
    *,
    region_label: str,
    variable_name: str,
    definition: str,
    annual_label: str,
    unit: str,
    start_year: int,
    end_year: int,
    result: TrendResult,
    status: str,
    stamp_text: str,
    chance_text: str,
    p_text: str,
    witness_text: str | None,
    reasons: Sequence[str],
    caveats: Sequence[str],
    source: str,
    citation: str,
    doi: str | None,
    share_link: str,
    years: Sequence[int],
    values: Sequence[float],
    decimals: int,
) -> str:
    """A complete, self-contained, printable HTML page for one case, in English or Turkish.

    ``status`` is the stamp key (``trend.world.case_status``) and ``stamp_text`` its word in the chosen
    language; ``chance_text`` and ``p_text`` are the app's phrases for ``result.p_value``
    (``trend.i18n.chance_phrase`` and ``p_phrase``). ``witness_text`` is the app's second-witness
    sentence; with None the page builds one from ``result``. ``years`` and ``values`` are the yearly
    series that ``result`` was computed from. Every text is escaped; Markdown ``**bold**`` is kept.
    """
    lang = "tr" if lang == "tr" else "en"
    decimals = int(decimals)

    def say(key: str, **fields) -> str:
        return report_text(lang, key, **fields)

    def signed(value: float) -> str:
        return num(value, lang, decimals, signed=True)

    title = say("title", variable=variable_name, region=region_label)
    level = num((1 - result.alpha) * 100, lang, 0)
    low, high = ci_bounds(*result.ci_per_decade, lang, decimals)  # never a bare 0.00 at the edge
    rate = signed(result.slope_per_decade)
    rising = result.slope_per_year > 0
    stamp_class = status if status in STAMP_CLASSES else "other"

    if status == "disputed":
        headline = say("headline_disputed")
    elif result.significant:
        headline = say("headline_up" if rising else "headline_down")
    else:
        headline = say("headline_chance")
    common = {
        "subject": _lower_first(annual_label), "label": annual_label, "unit": unit,
        "start": result.start_year, "end": result.end_year, "level": level,
        "low": low, "high": high, "p": _nowrap(p_text),
    }
    if result.significant:
        verdict = say(
            "verdict_up" if rising else "verdict_down", rate=num(abs(result.slope_per_decade), lang, decimals),
            total=num(abs(result.total_change), lang, decimals), **common,
        )
    else:
        verdict = say("verdict_none", rate=rate, total=signed(result.total_change), **common)
    meaning = _status_meaning(lang, status)

    tiles = (
        _tile(say("tile_rate"), say("per_decade", rate=rate, unit=unit),
              say("ci", level=level, low=low, high=high))
        + _tile(say("tile_total"), f"{signed(result.total_change)} {unit}", say("along_trend"))
        + _tile(say("tile_years"), say("years_count", n=result.n_years), f"{result.start_year}–{result.end_year}")
    )

    chart = report_chart_svg(
        lang, years, values, result.slope_per_year, unit=unit, decimals=decimals,
        title=say("chart_title", label=annual_label, start=result.start_year, end=result.end_year),
    )
    basis = say("based_on", n=result.n_years, start=result.start_year, end=result.end_year)
    if result.n_effective < 0.9 * result.n_years:
        basis += " " + say("neff", n=result.n_years, n_eff=num(result.n_effective, lang, 0))
    warning = ""
    if result.n_years < RECOMMENDED_YEARS:
        warning = f"<p class='warn'>{_esc(say('short', n=result.n_years, rec=RECOMMENDED_YEARS))}</p>"

    if witness_text:
        witness = _rich(witness_text)  # the app's sentence already says whether the witness agrees
    else:
        found = say({"increasing": "found_increasing", "decreasing": "found_decreasing"}.get(
            result.mk_trend, "found_none"))
        badge_class = "agrees" if result.agrees else "disagrees"
        witness = f"<span class='badge {badge_class}'>{_esc(say('witness_' + badge_class))}</span>" + _rich(say(
            "witness_auto", method=method_name(lang, result.mk_method), found=found,
            p=_nowrap(p_phrase(result.mk_p_value, lang)), sen=signed(result.sen_slope_per_decade), unit=unit,
        ))

    howto = [
        say("howto_p", alpha=num(result.alpha, lang, 2)),
        say("howto_ci", level=level),
        say("howto_total"),
        say("howto_witness", confirmed=status_text(lang, "confirmed")[0]),
        say("howto_why"),
        say("howto_none"),
    ]
    reasons_html = ""
    if reasons:
        reasons_html = (
            f"<section class='reasons'><h2>{_esc(say('reasons_title'))}</h2>"
            f"<p class='note'>{_esc(say('reasons_note'))}</p>{_bullets(reasons)}</section>"
        )
    caveats_html = ""
    if caveats:
        caveats_html = f"<section class='caveats'><h2>{_esc(say('caveats_title'))}</h2>{_bullets(caveats)}</section>"

    source_html = f"<p>{_rich(source)}</p>"
    if citation:
        source_html += f"<p class='citation'>{_rich(citation)}</p>"
    if doi:
        href = "https://doi.org/" + quote(str(doi), safe="/:;()")
        source_html += f"<p>{_esc(say('doi'))}: <a href='{_esc(href)}'>{_esc(doi)}</a></p>"
    share_html = ""
    if share_link:
        link = _esc(share_link)
        if str(share_link).startswith(("https://", "http://")):
            link = f"<a href='{link}'>{link}</a>"  # anything else (e.g. "javascript:") stays plain text
        share_html = (
            f"<section class='share'><h2>{_esc(say('share_title'))}</h2><p>{link}</p>"
            f"<p class='note'>{_esc(say('share_note'))}</p></section>"
        )

    return f"""<!doctype html>
<html lang='{lang}'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{_esc(title)}</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<main class='page'>
<header>
<p class='eyebrow'>{_esc(say('eyebrow'))}</p>
<h1>{_esc(title)}</h1>
<p class='meta'>{_esc(say('period', start=start_year, end=end_year))}</p>
<p class='hint noprint'>{_esc(say('print_hint'))}</p>
</header>
<section class='verdict {stamp_class}'>
<h2 class='eyebrow'>{_esc(say('verdict_title'))}</h2>
<p><span class='stamp {stamp_class}'>{_esc(stamp_text)}</span> <span class='meaning'>{_esc(meaning)}</span></p>
<p class='headline'>{_esc(headline)}</p>
<p class='sentence'>{_rich(verdict)}</p>
<p class='chance'>{_esc(say('chance', chance=chance_text))}</p>
</section>
<section class='tiles'>{tiles}</section>
<section class='evidence'>
<h2>{_esc(say('evidence_title'))}</h2>
<p>{_esc(say('what', definition=definition))}</p>
<p class='caption'>{_esc(say('points', label=annual_label, unit=unit))}</p>
{chart}
<div class='legend'><span><span class='key' style='border-color:{SERIES_1}'></span>{_esc(say('legend_values'))}</span>
<span><span class='key' style='border-color:{SERIES_2}'></span>{_esc(say('legend_trend', rate=rate, unit=unit))}</span></div>
<p class='caption'>{_esc(basis)}</p>
{warning}
</section>
<section class='witness'>
<h2>{_esc(say('witness_title'))}</h2>
<p>{witness}</p>
</section>
<section class='howto'>
<h2>{_esc(say('howto_title'))}</h2>
{_bullets(howto)}
</section>
{reasons_html}
{caveats_html}
<section class='source'>
<h2>{_esc(say('source_title'))}</h2>
{source_html}
</section>
{share_html}
<footer>
<p>{_esc(say('footer'))}</p>
<p>{_esc(say('disclaimer'))}</p>
</footer>
</main>
</body>
</html>
"""
