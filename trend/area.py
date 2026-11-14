"""Custom areas: validate a user's rectangle and read rectangles drawn on the map.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea of letting users pick any rectangle on Earth comes from
Team Avni.
"""
from __future__ import annotations

from trend.regions import Region

MIN_SPAN = 2.0  # NASA POWER regional requests need at least 2 degrees in each direction
MAX_SPAN = 10.0  # ... and at most 10 degrees
TOLERANCE = 1e-9  # typed spans of exactly 2 or 10 degrees are not widened or rejected
STEP = 0.01  # coordinates are sent to NASA POWER rounded to 2 decimals


class AreaError(ValueError):
    """A rectangle that cannot be used; ``code`` names the message to show."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def normalize_bbox(west: float, south: float, east: float, north: float) -> tuple[tuple[float, float, float, float], bool]:
    """Check a rectangle and widen it to the 2-degree minimum if needed.

    Returns ``((west, south, east, north), widened)``. Raises ``AreaError`` with code
    ``range``, ``order`` or ``too_big``.
    """
    values = [float(v) for v in (west, south, east, north)]
    west, south, east, north = values
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise AreaError("range")
    if west >= east or south >= north:
        raise AreaError("order")
    if east - west > MAX_SPAN + TOLERANCE or north - south > MAX_SPAN + TOLERANCE:
        raise AreaError("too_big")

    widened = False
    if east - west < MIN_SPAN - TOLERANCE:
        center = (west + east) / 2
        west, east = center - MIN_SPAN / 2, center + MIN_SPAN / 2
        widened = True
    if north - south < MIN_SPAN - TOLERANCE:
        center = (south + north) / 2
        south, north = center - MIN_SPAN / 2, center + MIN_SPAN / 2
        widened = True
    # Keep the widened box inside the globe.
    if west < -180:
        west, east = -180.0, -180.0 + (east - west)
    if east > 180:
        west, east = 180.0 - (east - west), 180.0
    if south < -90:
        south, north = -90.0, -90.0 + (north - south)
    if north > 90:
        south, north = 90.0 - (north - south), 90.0
    west, east = _fit_span(west, east, -180.0, 180.0)
    south, north = _fit_span(south, north, -90.0, 90.0)
    return (west, south, east, north), widened


def _fit_span(low: float, high: float, lower_limit: float, upper_limit: float) -> tuple[float, float]:
    """Round both edges to 2 decimals and keep MIN_SPAN <= high - low <= MAX_SPAN.

    NASA POWER checks the plain floating-point difference of the numbers it receives, so a box
    such as 7.11 to 9.11 (difference 1.9999999999999991) is rejected. The check here uses exactly
    the rounded numbers that are sent.
    """
    low, high = round(low, 2), round(high, 2)
    while high - low < MIN_SPAN:
        if round(high + STEP, 2) <= upper_limit:
            high = round(high + STEP, 2)
        else:
            low = round(low - STEP, 2)
    while high - low > MAX_SPAN:
        high = round(high - STEP, 2)
    return low, high


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
