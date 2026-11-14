"""Famous cases from around the world: one click opens a prepared region, a measurement and a period.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Each example asks a question that the data answer: a confirmed fall, a confirmed rise, or no confirmed
trend (a record that is too short). ``check_example`` runs the case file's test over the example's
period, so the tests can make sure every question still matches the data after the files are
refreshed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from trend.fetch import load_processed
from trend.stats import analyze_trend, to_annual
from trend.variables import VARIABLES
from trend.world import case_status

EXPECTED_ANSWERS = ("up", "down", "none")


@dataclass(frozen=True)
class Example:
    """One famous case: a prepared region, a measurement, a period and the answer the data give."""

    region: str  # key in trend.regions.REGIONS
    case: str  # key in trend.variables.VARIABLES
    start: int | None  # first year of the period; None for the full record
    end: int | None  # last year of the period; None for the full record
    label: dict[str, str] = field(hash=False)  # button text per interface language
    expect: str  # "up" or "down" (a confirmed trend) or "none" (no confirmed trend)


EXAMPLES: tuple[Example, ...] = (
    Example(
        "amazon", "precipitation", None, None,
        {"en": "🌳 Rain forest: is the Amazon drying?", "tr": "🌳 Yağmur ormanı: Amazon kuruyor mu?"},
        "down",
    ),
    Example(
        "beijing", "precipitation", None, None,
        {"en": "🏙️ The opposite: is Beijing getting wetter?", "tr": "🏙️ Tam tersi: Pekin daha mı yağışlı?"},
        "up",
    ),
    Example(
        "beijing", "no2", 2013, 2025,
        {
            "en": "🏙️ Big-city air: did Beijing get cleaner after 2013?",
            "tr": "🏙️ Büyük şehir havası: Pekin 2013 sonrası temizlendi mi?",
        },
        "down",
    ),
    Example(
        "marmara", "hot_days", None, None,
        {"en": "🏠 Home: are days above 30 °C becoming common in Istanbul?",
         "tr": "🏠 Evimiz: İstanbul'da 30 °C'yi geçen günler artıyor mu?"},
        "up",
    ),
    Example(
        "cairo_nile", "aod", None, None,
        {
            "en": "🌊 River delta: is the air over Cairo clearing?",
            "tr": "🌊 Nehir deltası: Kahire'nin havası temizleniyor mu?",
        },
        "down",
    ),
    Example(
        "colorado", "air_temperature", 1981, 2000,
        {
            "en": "⏳ Too short a record: was Colorado warming by 2000?",
            "tr": "⏳ Kısa kayıt: Colorado 2000'e kadar ısınıyor muydu?",
        },
        "none",
    ),
)

EXAMPLES_TEXT = {
    "en": {"title": "Famous cases from around the world: open one with a single click"},
    "tr": {"title": "Dünyadan ünlü dosyalar: tek tıkla aç"},
}


def examples_text(lang: str, key: str, **values) -> str:
    text = EXAMPLES_TEXT.get(lang, EXAMPLES_TEXT["en"])[key]
    return text.format(**values) if values else text


def examples_title(lang: str) -> str:
    """Caption above the famous-case buttons."""
    return examples_text(lang, "title")


def example_label(example: Example, lang: str) -> str:
    """Button text of an example in the interface language (English if there is none)."""
    return example.label.get(lang, example.label["en"])


def example_key(example: Example) -> str:
    """Streamlit widget key of an example's button."""
    return f"example_{example.region}_{example.case}"


def check_example(
    example: Example, loader: Callable[[str, str], pd.DataFrame | None] = load_processed
) -> str:
    """The answer the data give to an example: "up", "down" or "none".

    The case file's test over the example's period (the full record when ``start`` is None): yearly
    values from ``to_annual``, then ``analyze_trend`` with the measurement's ``min_years``. "up" or
    "down" only for a Confirmed stamp (significant, and the second witness agrees), otherwise "none".
    Raises ``ValueError`` when the data file is missing or the period has too few complete years.
    """
    monthly = loader(example.region, example.case)
    if monthly is None:
        raise ValueError(f"No prepared data for {example.region} / {example.case}.")
    variable = VARIABLES[example.case]
    annual, _ = to_annual(monthly, variable)
    if example.start is not None:
        annual = annual[annual["year"] >= example.start]
    if example.end is not None:
        annual = annual[annual["year"] <= example.end]
    result = analyze_trend(annual["year"], annual["value"], min_years=variable.min_years)
    if case_status(result) != "confirmed":
        return "none"
    return "up" if result.slope_per_year > 0 else "down"
