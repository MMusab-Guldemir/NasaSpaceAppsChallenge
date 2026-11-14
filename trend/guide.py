"""Guided start: two questions (what and where) that lead a new visitor to a prepared case.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The challenge statement suggests a short series of what/where questions that leads to variables. The
first question picks a topic (heat; water: rain, snow, groundwater; air pollution; green land;
carbon), the second a kind of place (big city, desert, rain forest, ...). ``suggest`` turns the pair
into up to three prepared cases, each with the stamp the detective gives it over its period (the World
board's rules, ``trend.world.board_verdict``), so the visitor sees the answer before opening the case
file.
"No evidence" cases are offered too: they show that not every change is a real trend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from trend.fetch import available_variable_keys, load_processed
from trend.seasons import months_in_period
from trend.variables import VARIABLES
from trend.world import SHORT_NAMES, TESTED, board_verdict

MAX_SUGGESTIONS = 3

# First question: what do you wonder about? (key -> answer text per interface language, emoji first)
TOPICS: dict[str, dict[str, str]] = {
    "heat": {"en": "🌡️ Heat", "tr": "🌡️ Sıcaklık"},
    "water": {"en": "💧 Water: rain, snow, groundwater", "tr": "💧 Su: yağmur, kar, yeraltı suyu"},
    "air": {"en": "🏭 Air pollution", "tr": "🏭 Hava kirliliği"},
    "green": {"en": "🌳 Green land", "tr": "🌳 Yeşil alanlar"},
    "carbon": {"en": "🫧 Carbon in the air", "tr": "🫧 Havadaki karbon"},
}


@dataclass(frozen=True)
class Place:
    """An answer to the second question and the prepared regions that show such a place."""

    label: dict[str, str] = field(hash=False)  # answer text per interface language, emoji first
    regions: tuple[str, ...]  # keys in trend.regions.REGIONS, in the order the guide offers them


# Second question: what kind of place?
PLACES: dict[str, Place] = {
    "city": Place({"en": "🏙️ Big city", "tr": "🏙️ Büyük şehir"}, ("marmara", "beijing", "los_angeles")),
    "desert": Place({"en": "🏜️ Desert", "tr": "🏜️ Çöl"}, ("medina", "cairo_nile")),
    "forest": Place({"en": "🌳 Rain forest", "tr": "🌳 Yağmur ormanı"}, ("amazon",)),
    "drylands": Place({"en": "🌾 Dry grassland", "tr": "🌾 Kurak bozkır"}, ("sahel", "konya")),
    "mountains": Place({"en": "🏔️ Mountains", "tr": "🏔️ Dağlar"}, ("alps", "colorado")),
    "delta": Place({"en": "🌊 River delta", "tr": "🌊 Nehir deltası"}, ("cairo_nile",)),
    "north": Place({"en": "❄️ Cold north", "tr": "❄️ Soğuk kuzey"}, ("siberia",)),
}

# The measurements a topic leads to. Each inner tuple is one slot: its alternatives in order of
# preference, of which the first with a prepared, testable record is offered for each region.
TOPIC_CASES: dict[str, tuple[tuple[str, ...], ...]] = {
    "heat": (("hot_days",), ("air_temperature",)),  # both: a place can warm without more days above 30 °C
    "water": (("precipitation",), ("groundwater",)),
    "air": (("no2", "co"),),
    "green": (("ndvi",),),
    "carbon": (("co2",),),
}
# Kinds of place where a topic leads to other measurements.
PLACE_CASES: dict[tuple[str, str], tuple[tuple[str, ...], ...]] = {
    ("water", "mountains"): (("snowfall",), ("precipitation",), ("groundwater",)),
    ("water", "north"): (("snowfall",), ("precipitation",), ("groundwater",)),
    ("air", "desert"): (("aod", "no2", "co"),),  # dust and smoke tell more than traffic gases here
    ("air", "delta"): (("aod", "no2", "co"),),
    ("green", "forest"): (("ndvi",), ("tree_cover",)),
}
# Cases with a period that has a known story: Beijing's clean-air plan started in 2013 (the same
# period as the famous case in trend/examples.py). Every other case opens on its full record.
PERIODS: dict[tuple[str, str], tuple[int, int]] = {("beijing", "no2"): (2013, 2025)}

# Clearest answers first: a confirmed trend, then the stamps where the two tests disagree.
STATUS_ORDER = {"confirmed": 0, "disputed": 1, "weak": 2, "noevidence": 3}

GUIDE_TEXT = {
    "en": {
        "title": "🧭 Not sure where to start? Answer two questions",
        "q_topic": "What are you curious about?",
        "q_place": "What kind of place?",
        "open": "Open this case",
        "none": "No prepared case for this pair yet; try another place.",
        "note": 'A "No evidence" stamp is an answer too: not every change is a real trend.',
        "label": "{place}: {case} — {verdict}",
        "label_period": "{place}: {case}, {start}–{end} — {verdict}",
        "verdict_confirmed_up": "Confirmed rise",
        "verdict_confirmed_down": "Confirmed fall",
        "verdict_disputed_up": "Disputed rise",
        "verdict_disputed_down": "Disputed fall",
        "verdict_weak_up": "Weak clue of a rise",
        "verdict_weak_down": "Weak clue of a fall",
        "verdict_noevidence": "No evidence of a trend",
        "case_air_temperature": "air temperature",
        "case_precipitation": "precipitation (rain and snow)",
        "case_snowfall": "snowfall",
        "case_hot_days": "hot days above 30 °C",
        "case_no2": "air pollution (NO₂)",
        "case_co": "carbon monoxide (CO)",
        "case_black_carbon": "soot (black carbon)",
        "case_aod": "dust and smoke (aerosols)",
        "case_co2": "carbon dioxide (CO₂)",
        "case_ndvi": "vegetation greenness (NDVI)",
        "case_tree_cover": "tree cover",
        "case_groundwater": "groundwater storage",
    },
    "tr": {
        "title": "🧭 Nereden başlayacağını bilmiyor musun? İki soruyu cevapla",
        "q_topic": "Neyi merak ediyorsun?",
        "q_place": "Nasıl bir yer?",
        "open": "Bu dosyayı aç",
        "none": "Bu seçim için henüz hazır bir dosya yok; başka bir yer dene.",
        "note": '"Delil yok" damgası da bir cevaptır: her değişim gerçek bir trend değildir.',
        "label": "{place}: {case} — {verdict}",
        "label_period": "{place}: {case}, {start}–{end} — {verdict}",
        "verdict_confirmed_up": "Doğrulanmış artış",
        "verdict_confirmed_down": "Doğrulanmış azalış",
        "verdict_disputed_up": "Tartışmalı artış",
        "verdict_disputed_down": "Tartışmalı azalış",
        "verdict_weak_up": "Artış yönünde zayıf ipucu",
        "verdict_weak_down": "Azalış yönünde zayıf ipucu",
        "verdict_noevidence": "Trende dair delil yok",
        "case_air_temperature": "hava sıcaklığı",
        "case_precipitation": "yağış (yağmur ve kar)",
        "case_snowfall": "kar yağışı",
        "case_hot_days": "30 °C üstü sıcak günler",
        "case_no2": "hava kirliliği (NO₂)",
        "case_co": "karbon monoksit (CO)",
        "case_black_carbon": "kara karbon (is)",
        "case_aod": "toz ve duman (aerosol)",
        "case_co2": "karbondioksit (CO₂)",
        "case_ndvi": "bitki yeşilliği (NDVI)",
        "case_tree_cover": "ağaç örtüsü",
        "case_groundwater": "yeraltı suyu",
    },
}


def guide_text(lang: str, key: str, **values) -> str:
    text = GUIDE_TEXT.get(lang, GUIDE_TEXT["en"])[key]
    return text.format(**values) if values else text


def topic_label(lang: str, topic: str) -> str:
    """Answer text of a topic in the first question (English if there is none)."""
    return TOPICS[topic].get(lang, TOPICS[topic]["en"])


def place_label(lang: str, place: str) -> str:
    """Answer text of a kind of place in the second question (English if there is none)."""
    return PLACES[place].label.get(lang, PLACES[place].label["en"])


@dataclass(frozen=True)
class Suggestion:
    """One prepared case the guide offers: region, measurement, period, text and stamp.

    It has the fields of ``trend.examples.Example`` that open a case (region, case, start, end), so
    the app can open it the same way as a famous case.
    """

    region: str  # key in trend.regions.REGIONS
    case: str  # key in trend.variables.VARIABLES
    start: int | None  # first year of the period; None for the full record
    end: int | None  # last year of the period; None for the full record
    label: dict[str, str] = field(hash=False)  # text per interface language, with the stamp in words
    status: str  # stamp over the period: "confirmed", "disputed", "weak" or "noevidence"


def suggestion_label(suggestion: Suggestion, lang: str) -> str:
    """Text of a suggestion in the interface language (English if there is none)."""
    return suggestion.label.get(lang, suggestion.label["en"])


def suggestion_key(suggestion: Suggestion) -> str:
    """Streamlit widget key of a suggestion's button."""
    return f"guide_{suggestion.region}_{suggestion.case}"


def topic_cases(topic: str, place: str) -> tuple[tuple[str, ...], ...]:
    """The measurement slots a topic leads to in a kind of place (see TOPIC_CASES and PLACE_CASES)."""
    if topic not in TOPICS:
        raise KeyError(f"Unknown topic '{topic}'. Available: {', '.join(TOPICS)}")
    if place not in PLACES:
        raise KeyError(f"Unknown place '{place}'. Available: {', '.join(PLACES)}")
    return PLACE_CASES.get((topic, place), TOPIC_CASES[topic])


def _labels(region_key: str, case: str, start: int | None, end: int | None, status: str,
            rising: bool) -> dict[str, str]:
    """The suggestion's text in every interface language: place, measurement, period and stamp."""
    verdict_key = "verdict_noevidence" if status == "noevidence" else (
        f"verdict_{status}_{'up' if rising else 'down'}"
    )
    labels = {}
    for lang in GUIDE_TEXT:
        values = {
            "place": SHORT_NAMES.get(lang, SHORT_NAMES["en"])[region_key],
            "case": guide_text(lang, f"case_{case}"),
            "verdict": guide_text(lang, verdict_key),
        }
        if start is None:
            labels[lang] = guide_text(lang, "label", **values)
        else:
            labels[lang] = guide_text(lang, "label_period", start=start, end=end, **values)
    return labels


def _case_suggestion(
    region_key: str, case: str, loader: Callable[[str, str], pd.DataFrame | None]
) -> Suggestion | None:
    """A suggestion for one prepared record, or None when the case file could not test it."""
    monthly = loader(region_key, case)
    verdict = board_verdict(monthly, case)
    if verdict.status not in TESTED:
        # No file, too few complete years, or a place where it never snows or is never that hot:
        # the case file does not open such a record, so the guide does not offer it.
        return None
    start, end = PERIODS.get((region_key, case), (None, None))
    if start is not None:
        in_period = board_verdict(
            months_in_period(monthly, start, end, VARIABLES[case].year_starts_month), case
        )
        if in_period.status in TESTED:
            verdict = in_period
        else:
            start, end = None, None  # the period is too short now: offer the full record instead
    rising = verdict.result.slope_per_year > 0
    return Suggestion(
        region_key, case, start, end, _labels(region_key, case, start, end, verdict.status, rising),
        verdict.status,
    )


def suggest(
    topic: str,
    place: str,
    loader: Callable[[str, str], pd.DataFrame | None] = load_processed,
    available: Callable[[str], list[str]] = available_variable_keys,
) -> list[Suggestion]:
    """Up to three prepared cases for a what/where pair, best first; empty when none fits.

    For every region of the place and every measurement slot of the topic, the first alternative
    that has a prepared file (``available``) and a record the case file can test is offered, with
    its stamp from ``board_verdict`` over the case's period (the full record, or a period with a
    known story such as Beijing's NO₂ from 2013). Order: the topic's first slot first (for example
    snowfall before precipitation in the mountains), then Confirmed before Disputed, Weak clue and
    No evidence, then the regions in the place's order. Unknown keys raise ``KeyError``.
    """
    slots = topic_cases(topic, place)
    ranked: list[tuple[tuple[int, int, int], Suggestion]] = []
    for region_index, region_key in enumerate(PLACES[place].regions):
        prepared = set(available(region_key))
        for slot_index, alternatives in enumerate(slots):
            for case in alternatives:
                if case not in prepared:
                    continue
                suggestion = _case_suggestion(region_key, case, loader)
                if suggestion is not None:
                    rank = (slot_index, STATUS_ORDER[suggestion.status], region_index)
                    ranked.append((rank, suggestion))
                    break
    ranked.sort(key=lambda item: item[0])
    found: list[Suggestion] = []
    seen: set[str] = set()
    for _, suggestion in ranked:
        if suggestion_key(suggestion) not in seen:  # one button per region and measurement
            seen.add(suggestion_key(suggestion))
            found.append(suggestion)
    return found[:MAX_SUGGESTIONS]
