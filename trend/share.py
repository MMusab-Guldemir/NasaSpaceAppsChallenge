"""Shareable links: the URL keeps the language, region, case and period.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from __future__ import annotations

from urllib.parse import urlencode

APP_URL = "https://avni-trend-detective.streamlit.app"


def build_share_link(
    lang: str,
    region: str,
    case: str,
    start: int,
    end: int,
    base: str = APP_URL,
    bbox: tuple[float, float, float, float] | None = None,
) -> str:
    """Link that reopens exactly this case, period and language (and custom rectangle)."""
    params: dict[str, object] = {"lang": lang, "region": region, "case": case, "start": start, "end": end}
    if bbox is not None:
        params.update({"w": bbox[0], "s": bbox[1], "e": bbox[2], "n": bbox[3]})
    return f"{base}/?{urlencode(params)}"


def parse_period(start_text, end_text, first: int, last: int) -> tuple[int, int] | None:
    """Turn URL text into a valid (start, end) inside the available years, or None if unusable."""
    try:
        start, end = int(start_text), int(end_text)
    except (TypeError, ValueError):
        return None
    start = max(first, min(start, last))
    end = max(first, min(end, last))
    if start > end:
        start, end = end, start
    return start, end
