"""Tests for the downloadable case report (trend/report.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import dataclasses
import html
import math
import re
from html.parser import HTMLParser

import numpy as np
import pytest

from trend.fetch import load_processed
from trend.i18n import chance_phrase, num, p_phrase, reasons, region_name, status_text, variable_text
from trend.regions import REGIONS
from trend.report import REPORT_TEXT, case_report_html, report_chart_svg, report_filename, report_text
from trend.share import build_share_link
from trend.stats import analyze_trend
from trend.variables import VARIABLES
from trend.world import board_verdict, case_status

YEARS = list(range(1981, 2026))
NAMES = {
    "en": ("Istanbul–Marmara, Türkiye", "Air temperature", "Annual mean air temperature"),
    "tr": ("İstanbul–Marmara, Türkiye", "Hava sıcaklığı", "Yıllık ortalama hava sıcaklığı"),
}


def rising_values():
    rng = np.random.default_rng(7)
    noise = rng.normal(scale=0.25, size=len(YEARS))
    return [float(v) for v in 14.0 + 0.045 * (np.array(YEARS) - 1981) + noise]


def flat_values():
    rng = np.random.default_rng(3)
    return [float(v) for v in 14.0 + rng.normal(scale=0.4, size=len(YEARS))]


def build(lang="en", values=None, result=None, **overrides):
    """A report for a made-up Istanbul temperature series, with the app's own phrases."""
    values = rising_values() if values is None else values
    result = analyze_trend(YEARS, values) if result is None else result
    status = case_status(result)
    region, variable, label = NAMES[lang]
    fields = dict(
        region_label=region,
        variable_name=variable,
        definition="How warm the air is about 2 meters above the ground.",
        annual_label=label,
        unit="°C",
        start_year=YEARS[0],
        end_year=YEARS[-1],
        result=result,
        status=status,
        stamp_text=status_text(lang, status)[0],
        chance_text=chance_phrase(result.p_value, lang),
        p_text=p_phrase(result.p_value, lang),
        witness_text=None,
        reasons=["Greenhouse gases trap heat."],
        caveats=["Comes from a reanalysis."],
        source="NASA POWER monthly T2M (MERRA-2 based), NASA Langley Research Center POWER Project",
        citation="Gelaro, R., et al. (2017). MERRA-2. Journal of Climate, 30, 5419-5454.",
        doi="10.1175/JCLI-D-16-0758.1",
        share_link=build_share_link(lang, "marmara", "air_temperature", YEARS[0], YEARS[-1]),
        years=YEARS,
        values=values,
        decimals=2,
    )
    fields.update(overrides)
    return case_report_html(lang, **fields), fields


class TagChecker(HTMLParser):
    """Records end tags that do not close the most recent open tag."""

    VOID = {"meta", "link", "br", "hr", "img", "input"}

    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass  # <line ... /> and other self-closing SVG elements

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(tag)


def svg_points(svg):
    match = re.search(r"<polyline[^>]*points='([^']+)'", svg)
    return [tuple(float(v) for v in pair.split(",")) for pair in match.group(1).split()]


def trend_line(svg):
    match = re.search(r"<line class='trend' x1='([^']+)' y1='([^']+)' x2='([^']+)' y2='([^']+)'", svg)
    return tuple(float(v) for v in match.groups())


def test_english_report_has_the_region_stamp_rate_link_and_chart():
    page, fields = build("en")
    result = fields["result"]
    assert fields["status"] == "confirmed"
    assert page.startswith("<!doctype html>") and "<html lang='en'>" in page
    assert "<title>Case report: Air temperature in Istanbul–Marmara, Türkiye</title>" in page
    assert "<h1>Case report: Air temperature in Istanbul–Marmara, Türkiye</h1>" in page
    assert "<span class='stamp confirmed'>Confirmed</span>" in page
    assert "A significant trend: both tests agree." in page
    assert "Unlikely to be chance: a significant upward trend" in page
    rate = num(result.slope_per_decade, "en", 2, signed=True)
    assert rate == "+0.46" and f"{rate} °C per decade" in page
    low, high = (num(v, "en", 2, signed=True) for v in result.ci_per_decade)
    total = num(abs(result.total_change), "en", 2)
    assert (
        f"The annual mean air temperature <b>rose by about 0.46 °C per decade</b> from 1981 to 2025 "
        f"(95% CI {low} to {high}), about {total} °C in total along the trend line (p\u00a0&lt;\u00a00.001)."
    ) in page  # the p phrase never breaks across lines
    assert "a trend this strong would appear by chance less than 0.1% of the time." in page
    assert "Each point is one year: Annual mean air temperature; unit: °C." in page
    assert f"<a href='{html.escape(fields['share_link'])}'>" in page
    assert re.search(r"<svg[^>]*>.*<polyline[^>]*points='[^']+'.*</svg>", page, re.S)
    assert "<script" not in page.lower()


def test_turkish_report_is_in_turkish_with_decimal_commas():
    page, fields = build("tr")
    result = fields["result"]
    assert "<html lang='tr'>" in page
    assert "<h1>Dosya raporu: İstanbul–Marmara, Türkiye – Hava sıcaklığı</h1>" in page
    assert "<span class='stamp confirmed'>Doğrulandı</span>" in page
    rate = num(result.slope_per_decade, "tr", 2, signed=True)
    assert rate == "+0,46" and f"{rate} °C / 10 yıl" in page
    low, high = (num(v, "tr", 2, signed=True) for v in result.ci_per_decade)
    assert (
        f"Yıllık ortalama hava sıcaklığı, 1981–2025 arasında <b>on yılda yaklaşık 0,46 °C arttı</b> "
        f"(%95 güven aralığı: {low} ile {high})"
    ) in page
    assert "p\u00a0&lt;\u00a00,001" in page and "%0,1&#x27;den az olurdu." in page
    assert "p\u00a0&lt;\u00a00,05 olduğunda" in page
    assert "İkinci tanık" in page and ">Doğruluyor<" in page and "Sen eğimi on yılda" in page
    assert "nedenini göstermez" in page and "Avni Takımı" in page
    for english in ("The second witness", "Keep in mind", "How to read", "Case report", "per decade"):
        assert english not in page


def test_every_text_is_escaped():
    attack = "<script>alert(1)</script>"
    page, _ = build(
        "en", region_label=attack, variable_name=attack, definition=attack, annual_label=attack,
        unit="<i>u</i>", stamp_text=attack, chance_text=attack, p_text=attack, witness_text=attack,
        reasons=["Use <b>bold</b> with care", attack], caveats=[attack], source=attack, citation=attack,
        doi="10.1/<x>'\"",
    )
    assert "<script" not in page.lower()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "&lt;b&gt;bold&lt;/b&gt;" in page and "<b>bold</b>" not in page
    assert "<i>u</i>" not in page and "&lt;i&gt;u&lt;/i&gt;" in page
    assert "<x>" not in page


def test_markdown_bold_from_the_app_texts_becomes_bold_after_escaping():
    witness = "✅ **The second witness agrees:** the Mann-Kendall test finds <more>."
    page, _ = build("en", witness_text=witness, reasons=["**Local context:** a <b>law</b> of 2013."])
    assert "✅ <b>The second witness agrees:</b> the Mann-Kendall test finds &lt;more&gt;." in page
    assert "<li><b>Local context:</b> a &lt;b&gt;law&lt;/b&gt; of 2013.</li>" in page


def test_share_link_is_a_link_only_when_it_is_a_web_address():
    page, _ = build("en", share_link="javascript:alert(1)")
    assert "href='javascript" not in page and "<p>javascript:alert(1)</p>" in page
    page, _ = build("en", share_link="")
    assert "Open this case in the app" not in page


def test_page_is_self_contained_and_well_formed():
    for lang in ("en", "tr"):
        page, _ = build(lang)
        for marker in ("<script", " src=", "<link", "@import", "url(", "<iframe"):
            assert marker not in page.lower()
        checker = TagChecker()
        checker.feed(page)
        checker.close()
        assert checker.stack == [] and checker.errors == []


def test_no_trend_verdict():
    page, fields = build("en", values=flat_values())
    result = fields["result"]
    assert fields["status"] == "noevidence" and not result.significant
    assert "Could be chance: no clear trend" in page and "<span class='stamp noevidence'>No evidence</span>" in page
    rate = num(result.slope_per_decade, "en", 2, signed=True)
    assert f"<b>No significant trend</b> in the annual mean air temperature from 1981 to 2025: " \
           f"the trend line changes by {rate} °C per decade" in page
    page, _ = build("tr", values=flat_values())
    assert "Yıllık ortalama hava sıcaklığı için 1981–2025 arasında <b>anlamlı bir trend yok</b>" in page


def test_disputed_verdict_and_a_disagreeing_witness():
    disputed = dataclasses.replace(
        analyze_trend(YEARS, rising_values()), agrees=False, mk_trend="no trend", mk_p_value=0.2
    )
    page, fields = build("en", result=disputed)
    assert fields["status"] == "disputed"
    assert "Borderline: the two tests disagree" in page and "class='verdict disputed'" in page
    assert "<span class='badge disagrees'>Disagrees</span>" in page
    assert "finds no significant trend (p\u00a0=\u00a00.200;" in page


def test_a_witness_sentence_from_the_app_replaces_the_built_one_without_a_badge():
    page, _ = build("en", witness_text="⚠️ **The second witness disagrees:** the test finds nothing.")
    assert "⚠️ <b>The second witness disagrees:</b> the test finds nothing." in page
    assert "class='badge" not in page and "Sen&#x27;s slope" not in page


def test_unknown_status_gets_a_neutral_stamp_and_no_meaning():
    page, _ = build("en", status="open\"><b>x", stamp_text="Open case")
    assert "<span class='stamp other'>Open case</span>" in page and "class='verdict other'" in page
    assert "<b>x" not in page and "open&quot;" not in page and 'open"' not in page


def test_short_and_persistent_records_get_their_notes():
    years, values = YEARS[:12], rising_values()[:12]
    result = analyze_trend(years, values)
    page, _ = build("en", result=result, years=years, values=values, start_year=1981, end_year=1992)
    assert "Only 12 years of data. Trend tests are less reliable with fewer than 20 years." in page
    persistent = dataclasses.replace(result, n_effective=4.2)
    page, _ = build("tr", result=persistent, years=years, values=values)
    assert "bu 12 yıl, yaklaşık 4 bağımsız yıl kadar bilgi taşıyor" in page


def test_chart_draws_every_year_and_the_ols_line():
    values = rising_values()
    result = analyze_trend(YEARS, values)
    svg = report_chart_svg("en", YEARS, values, result.slope_per_year, unit="°C", decimals=2, title="t")
    points = svg_points(svg)
    assert len(points) == len(YEARS)
    assert all(0 <= x <= 600 and 0 <= y <= 250 for x, y in points)
    x1, y1, x2, y2 = trend_line(svg)
    assert y2 < y1  # a rising trend climbs up the page
    # The drawing is a linear map of the data, so the OLS line of the drawn points is the drawn line.
    xs, ys = np.array([p[0] for p in points]), np.array([p[1] for p in points])
    pixel_slope, pixel_intercept = np.polyfit(xs, ys, 1)
    assert (y2 - y1) / (x2 - x1) == pytest.approx(pixel_slope, rel=0.01)
    assert y1 == pytest.approx(pixel_intercept + pixel_slope * x1, abs=0.3)
    distance = abs((y2 - y1) * xs.mean() - (x2 - x1) * ys.mean() + x2 * y1 - y2 * x1) / math.hypot(x2 - x1, y2 - y1)
    assert distance < 0.3  # through the mean year and mean value
    assert "<title>1981: " in svg and "°C</title></circle>" in svg


def test_chart_handles_gaps_constant_values_single_points_and_bad_input():
    svg = report_chart_svg("en", [2000, 2001, 2002, 2003], [1.0, float("nan"), 2.0, None], 0.5, unit="x")
    assert len(svg_points(svg)) == 2
    svg = report_chart_svg("en", list(range(2000, 2012)), [5.0] * 12, 0.0, unit="x")
    x1, y1, x2, y2 = trend_line(svg)
    assert y1 == y2 and len({y for _, y in svg_points(svg)}) == 1
    svg = report_chart_svg("en", [2000], [3.0], 0.0, unit="x")
    assert len(svg_points(svg)) == 1 and "class='trend'" not in svg
    note = report_chart_svg("tr", [], [], 0.0, unit="x")
    assert "<svg" not in note and "Çizilecek yıllık değer yok." in note
    with pytest.raises(ValueError):
        report_chart_svg("en", [2000, 2001], [1.0], 0.0, unit="x")


def test_turkish_chart_labels_use_a_decimal_comma():
    values = [0.1 + 0.002 * i for i in range(len(YEARS))]
    svg = report_chart_svg("tr", YEARS, values, 0.002, unit="AOD", decimals=3)
    labels = re.findall(r"text-anchor='end'>([^<]+)<", svg)
    assert len(labels) >= 3 and all("," in label and "." not in label for label in labels)
    assert "1990" in svg and "2020" in svg  # round years on the x-axis


def test_filename_has_no_spaces():
    assert report_filename("marmara", "hot_days", 1981, 2025) == "trend-detective_marmara_hot_days_1981-2025.html"
    assert (
        report_filename("custom_-109.05_37_-102.04_41", "aod", 2001, 2025)
        == "trend-detective_custom_-109.05_37_-102.04_41_aod_2001-2025.html"
    )
    for name in (report_filename("custom area 27.5", "air temperature", 1981, 2025),
                 report_filename("../a b/c", "x\ty", 2000, 2010)):
        assert " " not in name and "/" not in name and "\t" not in name and name.endswith(".html")


def test_report_texts():
    assert report_text("en", "button") == "⬇ Download the case report (HTML, printable)"
    assert report_text("tr", "button") == "⬇ Dosya raporunu indir (HTML, yazdırılabilir)"
    assert report_text("de", "button") == report_text("en", "button")
    assert set(REPORT_TEXT["tr"]) == set(REPORT_TEXT["en"])
    assert report_text("en", "footer") == (
        "Team Avni · NASA Space Apps Challenge 2026 · made with the Earth System Trend Detective; "
        "built with AI assistance (Claude by Anthropic)"
    )
    page, _ = build("en")
    assert report_text("en", "footer") in page and "Not affiliated with or endorsed by NASA." in page


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_report_from_the_istanbul_hot_days_file(lang):
    verdict = board_verdict(load_processed("marmara", "hot_days"), "hot_days")
    result, status, variable = verdict.result, verdict.status, VARIABLES["hot_days"]
    texts = variable_text(lang, variable)
    direction = ("up" if result.slope_per_year > 0 else "down") if result.significant else "none"
    page = case_report_html(
        lang,
        region_label=region_name(lang, "marmara", REGIONS["marmara"].name),
        variable_name=texts["name"], definition=texts["definition"], annual_label=texts["annual_label"],
        unit=texts["annual_unit"], start_year=result.start_year, end_year=result.end_year, result=result,
        status=status, stamp_text=status_text(lang, status)[0], chance_text=chance_phrase(result.p_value, lang),
        p_text=p_phrase(result.p_value, lang), witness_text=None, reasons=reasons(lang, "hot_days", direction),
        caveats=texts["caveats"], source=f"{variable.product}, {variable.provider}", citation=variable.citation,
        doi=variable.doi,
        share_link=build_share_link(lang, "marmara", "hot_days", result.start_year, result.end_year),
        years=verdict.annual["year"].tolist(), values=verdict.annual["value"].tolist(),
        decimals=variable.decimals,
    )
    assert status == "confirmed" and len(svg_points(page)) == result.n_years
    assert "<a href='https://doi.org/10.1175/JCLI-D-16-0758.1'>" in page
    assert html.escape(texts["caveats"][0]) in page and html.escape(texts["definition"]) in page
    assert num(result.slope_per_decade, lang, variable.decimals, signed=True) in page
    assert len(page) < 60_000


def test_interval_never_shows_a_bare_zero_next_to_a_significant_trend():
    """Alps carbon monoxide: the 95% interval ends at -0.0026, which must not print as 0.00."""
    from trend.i18n import ci_bounds

    assert ci_bounds(-0.1213, -0.0026, "en", 2) == ("-0.121", "-0.003")
    assert ci_bounds(-0.1213, -0.0026, "tr", 2) == ("-0,121", "-0,003")
    assert ci_bounds(0.004, 0.635, "en", 2) == ("+0.004", "+0.635")
    assert ci_bounds(0.12, 0.55, "en", 2) == ("+0.12", "+0.55")  # nothing near zero: unchanged
    assert ci_bounds(0.0, 0.0, "en", 2) == ("0.00", "0.00")
