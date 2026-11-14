"""Region catalog for the Earth System Trend Detective.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """A rectangular study area in geographic coordinates (degrees)."""

    key: str
    name: str
    west: float
    south: float
    east: float
    north: float
    description: str = ""

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Return the box as (west, south, east, north)."""
        return (self.west, self.south, self.east, self.north)

    @property
    def center(self) -> tuple[float, float]:
        """Return the box center as (latitude, longitude)."""
        return ((self.south + self.north) / 2, (self.west + self.east) / 2)


REGIONS: dict[str, Region] = {
    "colorado": Region(
        key="colorado",
        name="Colorado, USA",
        west=-109.05,
        south=37.0,
        east=-102.04,
        north=41.0,
        description=(
            "The state of Colorado. Its borders are almost a rectangle, "
            "so this box closely matches the state."
        ),
    ),
}


def get_region(key: str) -> Region:
    """Look up a region by key, with a clear error for unknown keys."""
    try:
        return REGIONS[key]
    except KeyError as exc:
        available = ", ".join(REGIONS)
        raise KeyError(f"Unknown region '{key}'. Available: {available}") from exc
