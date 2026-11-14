"""Custom areas: validate a user's rectangle and read rectangles drawn on the map.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea of letting users pick any rectangle on Earth comes from
Team Avni.
"""
from __future__ import annotations

import math

from trend.regions import Region

MAX_SPAN = 40.0  # largest rectangle side in degrees; larger rectangles are fetched in pieces
MIN_SPAN = 0.01  # smallest rectangle side after rounding to 2 decimals
POWER_MIN_SPAN = 2.0  # NASA POWER regional requests need at least 2 degrees in each direction
POWER_MAX_SPAN = 10.0  # ... and at most 10 degrees
POWER_TILE = 9.9  # tile size for large rectangles, leaving room for a small overlap
TILE_OVERLAP = 0.05  # degrees added on inner tile edges, so no grid cell falls between two tiles
TOLERANCE = 1e-9  # a typed side of exactly 40 degrees is not rejected
STEP = 0.01  # coordinates are rounded to 2 decimals


class AreaError(ValueError):
    """A rectangle that cannot be used; ``code`` names the message to show."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def normalize_bbox(west: float, south: float, east: float, north: float) -> tuple[float, float, float, float]:
    """Check a rectangle and round it to 2 decimals.

    Any size from 0.01 to 40 degrees per side is allowed: a rectangle smaller than one NASA grid
    cell uses the nearest cell, a large one is fetched in pieces. Raises ``AreaError`` with code
    ``range``, ``order`` or ``too_big``.
    """
    west, south, east, north = (float(v) for v in (west, south, east, north))
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise AreaError("range")
    if west >= east or south >= north:
        raise AreaError("order")
    if east - west > MAX_SPAN + TOLERANCE or north - south > MAX_SPAN + TOLERANCE:
        raise AreaError("too_big")
    west, east = _fit_span(west, east, -180.0, 180.0, MIN_SPAN, MAX_SPAN, TOLERANCE)
    south, north = _fit_span(south, north, -90.0, 90.0, MIN_SPAN, MAX_SPAN, TOLERANCE)
    return (west, south, east, north)


def _fit_span(
    low: float, high: float, lower_limit: float, upper_limit: float, min_span: float, max_span: float,
    tolerance: float = 0.0,
) -> tuple[float, float]:
    """Round both edges to 2 decimals and keep min_span <= high - low <= max_span in plain floats.

    NASA POWER checks the plain floating-point difference of the numbers it receives, so a box
    such as 7.11 to 9.11 (difference 1.9999999999999991) is rejected. The check here uses exactly
    the rounded numbers that are sent (tolerance 0); user rectangles allow a tiny tolerance.
    """
    low, high = round(low, 2), round(high, 2)
    while high - low < min_span - tolerance:
        if round(high + STEP, 2) <= upper_limit:
            high = round(high + STEP, 2)
        else:
            low = round(low - STEP, 2)
    while high - low > max_span + tolerance:
        high = round(high - STEP, 2)
    return low, high


def _power_axis(low: float, high: float, lower_limit: float, upper_limit: float) -> list[tuple[float, float]]:
    """Pieces of one axis that NASA POWER accepts (2 to 10 degrees each) and that cover low..high."""
    span = high - low
    if span < POWER_MIN_SPAN:
        # Too narrow for POWER: ask for 2 degrees around the centre; the cells are filtered later.
        center = (low + high) / 2
        a, b = center - POWER_MIN_SPAN / 2, center + POWER_MIN_SPAN / 2
        if a < lower_limit:
            a, b = lower_limit, lower_limit + POWER_MIN_SPAN
        if b > upper_limit:
            a, b = upper_limit - POWER_MIN_SPAN, upper_limit
        return [_fit_span(a, b, lower_limit, upper_limit, POWER_MIN_SPAN, POWER_MAX_SPAN)]
    count = max(1, math.ceil(span / POWER_TILE - TOLERANCE))
    pieces = []
    for index in range(count):
        a = low + span * index / count - (TILE_OVERLAP if index > 0 else 0.0)
        b = low + span * (index + 1) / count + (TILE_OVERLAP if index < count - 1 else 0.0)
        pieces.append(
            _fit_span(max(a, lower_limit), min(b, upper_limit), lower_limit, upper_limit,
                      POWER_MIN_SPAN, POWER_MAX_SPAN)
        )
    return pieces


def power_request_boxes(bbox: tuple[float, float, float, float]) -> list[tuple[float, float, float, float]]:
    """NASA POWER request boxes (2 to 10 degrees per side, exact in floats) that cover ``bbox``."""
    west, south, east, north = bbox
    lons = _power_axis(west, east, -180.0, 180.0)
    lats = _power_axis(south, north, -90.0, 90.0)
    return [(w, s_, e, n) for (s_, n) in lats for (w, e) in lons]


def bbox_from_drawing(drawing: dict | None) -> tuple[float, float, float, float] | None:
    """Bounding box of a rectangle (GeoJSON feature) drawn on the map, or None."""
    if not drawing:
        return None
    geometry = drawing.get("geometry") or {}
    if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
        return None
    ring = geometry["coordinates"][0]
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return (round(min(lons), 2), round(min(lats), 2), round(max(lons), 2), round(max(lats), 2))


def pick_drawn_bbox(map_state: dict | None, active_bbox) -> tuple[float, float, float, float] | None:
    """The rectangle the user drew, moved or resized on the map, if it differs from the active one.

    A new rectangle arrives as ``last_active_drawing``, but an edit (move or resize, confirmed with
    Save) only refreshes ``all_drawings``; the newest entry of ``all_drawings`` is checked first
    because ``last_active_drawing`` keeps the shape from before an edit.
    """
    if not map_state:
        return None
    active = tuple(round(float(v), 2) for v in active_bbox)
    candidates = list(reversed(map_state.get("all_drawings") or []))
    candidates.append(map_state.get("last_active_drawing"))
    for drawing in candidates:
        bbox = bbox_from_drawing(drawing)
        if bbox is not None and bbox != active:
            return bbox
    return None


COMPASS = {"en": ("E", "W", "N", "S"), "tr": ("D", "B", "K", "G")}


def format_bbox(bbox: tuple[float, float, float, float], lang: str = "en") -> str:
    """Readable rectangle, for example '27.0°E–30.0°E, 40.0°N–42.0°N' (Turkish: D/B/K/G, comma)."""
    west, south, east, north = bbox
    east_letter, west_letter, north_letter, south_letter = COMPASS.get(lang, COMPASS["en"])

    def number(value: float) -> str:
        text = f"{abs(value):.1f}"
        return text.replace(".", ",") if lang == "tr" else text

    def lon(value: float) -> str:
        return f"{number(value)}°{east_letter if value >= 0 else west_letter}"

    def lat(value: float) -> str:
        return f"{number(value)}°{north_letter if value >= 0 else south_letter}"

    return f"{lon(west)}–{lon(east)}, {lat(south)}–{lat(north)}"


def custom_region(bbox: tuple[float, float, float, float], name: str) -> Region:
    west, south, east, north = bbox
    return Region(key="custom", name=name, west=west, south=south, east=east, north=north)
