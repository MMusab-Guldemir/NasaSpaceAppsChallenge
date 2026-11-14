"""Custom areas: validate a user's rectangle and read rectangles drawn on the map.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea of letting users pick any rectangle on Earth comes from
Team Avni.
"""
from __future__ import annotations

from trend.regions import Region

MIN_SPAN = 2.0  # NASA POWER regional requests need at least 2 degrees in each direction
MAX_SPAN = 10.0  # ... and at most 10 degrees


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
    if east - west > MAX_SPAN + 1e-9 or north - south > MAX_SPAN + 1e-9:
        raise AreaError("too_big")

    widened = False
    if east - west < MIN_SPAN:
        center = (west + east) / 2
        west, east = center - MIN_SPAN / 2, center + MIN_SPAN / 2
        widened = True
    if north - south < MIN_SPAN:
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
    bbox = tuple(round(v, 2) for v in (west, south, east, north))
    return bbox, widened


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


def format_bbox(bbox: tuple[float, float, float, float]) -> str:
    """Readable rectangle, for example '27.0°E–30.0°E, 40.0°N–42.0°N'."""
    west, south, east, north = bbox

    def lon(value: float) -> str:
        return f"{abs(value):.1f}°{'E' if value >= 0 else 'W'}"

    def lat(value: float) -> str:
        return f"{abs(value):.1f}°{'N' if value >= 0 else 'S'}"

    return f"{lon(west)}–{lon(east)}, {lat(south)}–{lat(north)}"


def custom_region(bbox: tuple[float, float, float, float], name: str) -> Region:
    west, south, east, north = bbox
    return Region(key="custom", name=name, west=west, south=south, east=east, north=north)
