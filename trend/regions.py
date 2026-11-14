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
    map_scope: str = "world"  # Plotly geo scope for the region map, e.g. "usa" or "world"
    us_state: str | None = None  # two-letter code to shade a US state on the map

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
        map_scope="usa",
        us_state="CO",
    ),
    "marmara": Region(
        key="marmara",
        name="Istanbul–Marmara, Türkiye",
        west=27.0,
        south=40.0,
        east=30.0,
        north=42.0,
        description=(
            "Istanbul and the Marmara region of Türkiye, including parts of the Marmara and "
            "Black Sea coasts."
        ),
    ),
    # World regions chosen by Team Avni (2026-11-14). Edges are multiples of 0.25 degrees, so the
    # spans NASA POWER checks are exact in floating point.
    "medina": Region(
        key="medina", name="Medina, Saudi Arabia", west=38.5, south=23.5, east=40.5, north=25.5,
        description="The city of Medina and the surrounding desert of the Hejaz.",
    ),
    "beijing": Region(
        key="beijing", name="Beijing, China", west=115.5, south=39.0, east=118.0, north=41.0,
        description="Beijing and part of Tianjin on the North China Plain, a large urban area.",
    ),
    "los_angeles": Region(
        key="los_angeles", name="Los Angeles, USA", west=-119.0, south=33.5, east=-117.0, north=35.5,
        description="The Los Angeles basin with nearby mountains, desert edge and coastal sea.",
    ),
    "cairo_nile": Region(
        key="cairo_nile", name="Cairo and the Nile Delta, Egypt", west=29.5, south=29.5, east=32.5,
        north=31.75,
        description="Cairo and the Nile Delta, a megacity next to a river delta and the desert.",
    ),
    "amazon": Region(
        key="amazon", name="Amazon rainforest (Rondônia), Brazil", west=-66.0, south=-13.0,
        east=-60.0, north=-8.0,
        description="Rondônia in the southern Amazon, part of the 'arc of deforestation'.",
    ),
    "sahel": Region(
        key="sahel", name="Sahel, West Africa", west=-2.0, south=12.0, east=8.0, north=16.0,
        description="The Sahel belt south of the Sahara in Burkina Faso, Mali, Niger and northern "
        "Nigeria.",
    ),
    "alps": Region(
        key="alps", name="Alps, Switzerland and Austria", west=6.0, south=45.5, east=14.0, north=48.0,
        description="The central and eastern Alps (Switzerland, Austria, northern Italy and "
        "neighbours), including the northern edge of the Po Valley.",
    ),
    "siberia": Region(
        key="siberia", name="Siberia (Yakutia), Russia", west=125.0, south=60.0, east=135.0,
        north=65.0,
        description="Central Yakutia around Yakutsk in eastern Siberia, a cold permafrost region.",
    ),
    "konya": Region(
        key="konya", name="Konya Closed Basin, Türkiye", west=31.75, south=37.0, east=34.25, north=39.0,
        description="The Konya Closed Basin in central Anatolia (Konya, Karaman, Aksaray and Lake Tuz), "
        "Türkiye's grain belt, where irrigation draws on groundwater and sinkholes have appeared.",
    ),
}


def nearest_region(latitude: float, longitude: float) -> tuple[str, float]:
    """The prepared region whose box centre is closest to a point, and the distance in km.

    Great-circle distance on a sphere of radius 6371 km. The app offers it when NASA POWER does not
    answer for a custom area: a prepared region works from the files in the repository, without the
    network.
    """
    import math

    def distance(region: Region) -> float:
        lat1, lon1, (lat2, lon2) = math.radians(latitude), math.radians(longitude), region.center
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))

    key = min(REGIONS, key=lambda name: distance(REGIONS[name]))
    return key, distance(REGIONS[key])


def get_region(key: str) -> Region:
    """Look up a region by key, with a clear error for unknown keys."""
    try:
        return REGIONS[key]
    except KeyError as exc:
        available = ", ".join(REGIONS)
        raise KeyError(f"Unknown region '{key}'. Available: {available}") from exc
