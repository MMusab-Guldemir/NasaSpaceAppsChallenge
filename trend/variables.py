"""Variable catalog: plain-language definitions, units, data products and aggregation rules.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from dataclasses import dataclass

ALL_MONTHS = tuple(range(1, 13))

POWER_ACKNOWLEDGMENT = (
    "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project "
    "funded through the NASA Earth Science/Applied Science Program."
)
MERRA2_REFERENCE = (
    "Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and "
    "Applications, Version 2 (MERRA-2). Journal of Climate, 30, 5419-5454."
)


@dataclass(frozen=True)
class Variable:
    """Everything the app needs to know about one Earth-science variable."""

    key: str
    name: str
    definition: str
    unit: str  # unit of the cached monthly series
    annual_label: str  # what one annual value means
    annual_unit: str
    year_axis_label: str
    aggregation: str  # "mean" or "sum" of the months in season_months
    season_months: tuple[int, ...]
    year_starts_month: int  # 1 = calendar year, 10 = water year (October to September)
    product: str
    provider: str
    doi: str | None
    citation: str
    caveats: tuple[str, ...] = ()
    min_valid_days: int | None = None  # for monthly means built from daily data


VARIABLES: dict[str, Variable] = {
    "air_temperature": Variable(
        key="air_temperature",
        name="Air temperature",
        definition="How warm the air is about 2 meters (6.5 feet) above the ground.",
        unit="°C",
        annual_label="Annual mean air temperature",
        annual_unit="°C",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="NASA POWER monthly T2M (MERRA-2 based)",
        provider="NASA Langley Research Center POWER Project",
        doi="10.1175/JCLI-D-16-0758.1",
        citation=f"{POWER_ACKNOWLEDGMENT} {MERRA2_REFERENCE}",
        caveats=(
            "Comes from a reanalysis: a weather model combined with millions of observations, "
            "on a grid of about 50 km.",
            "The newest months in NASA POWER can come from a near-real-time product and may be "
            "revised later.",
        ),
    ),
    "snowfall": Variable(
        key="snowfall",
        name="Snowfall",
        definition=(
            "How much snow falls, measured as the depth of water it would make if it melted."
        ),
        unit="mm of water per month",
        annual_label="Snowfall total per water year (October to September)",
        annual_unit="mm of water",
        year_axis_label="Water year (October to September, labelled by its ending year)",
        aggregation="sum",
        season_months=ALL_MONTHS,
        year_starts_month=10,
        product="NASA POWER monthly PRECSNOLAND (MERRA-2 based)",
        provider="NASA Langley Research Center POWER Project",
        doi="10.1175/JCLI-D-16-0758.1",
        citation=f"{POWER_ACKNOWLEDGMENT} {MERRA2_REFERENCE}",
        caveats=(
            "This snowfall comes from the MERRA-2 reanalysis (a weather model guided by "
            "observations), not from direct snow measurements or snow depth.",
            "The newest months in NASA POWER can come from a near-real-time product and may be "
            "revised later.",
            "Reanalysis trends can partly reflect changes in the observing system over the decades.",
        ),
    ),
    "no2": Variable(
        key="no2",
        name="Air pollution (NO₂)",
        definition=(
            "Nitrogen dioxide in the lower atmosphere, a gas that comes mostly from vehicles, "
            "power plants and industry."
        ),
        unit="10¹⁵ molecules/cm²",
        annual_label="Annual mean tropospheric NO₂ column",
        annual_unit="10¹⁵ molecules/cm²",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="OMI OMNO2d v004, tropospheric column, 30% cloud screened",
        provider="NASA GES DISC, via Giovanni",
        doi=None,  # to be confirmed from the Giovanni download metadata
        citation="OMI NO2 Level 3 daily product (OMNO2d), NASA Goddard Earth Sciences Data and "
        "Information Services Center (GES DISC).",
        caveats=(
            "A state-wide average is dominated by rural areas, so city pollution is diluted.",
            "The OMI instrument has a 'row anomaly' that reduces the number of usable "
            "measurements.",
            "2020 shows a dip linked to reduced activity during the COVID-19 pandemic.",
        ),
        min_valid_days=10,
    ),
    "ndvi": Variable(
        key="ndvi",
        name="Vegetation greenness (NDVI)",
        definition=(
            "How green and dense the plants are, on a scale from -1 to 1. "
            "Higher values mean more green vegetation."
        ),
        unit="NDVI (no unit)",
        annual_label="Growing-season (May to September) mean NDVI",
        annual_unit="NDVI",
        year_axis_label="Year",
        aggregation="mean",
        season_months=(5, 6, 7, 8, 9),
        year_starts_month=1,
        product="MODIS Terra MOD13C2 v061, monthly, 0.05°",
        provider="NASA LP DAAC, via AppEEARS",
        doi="10.5067/MODIS/MOD13C2.061",
        citation="Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg "
        "CMG V061. NASA EOSDIS Land Processes Distributed Active Archive Center.",
        caveats=(
            "The Terra satellite's orbit has drifted since about 2020, which can slightly "
            "affect recent values.",
        ),
    ),
}


def get_variable(key: str) -> Variable:
    """Look up a variable by key, with a clear error for unknown keys."""
    try:
        return VARIABLES[key]
    except KeyError as exc:
        available = ", ".join(VARIABLES)
        raise KeyError(f"Unknown variable '{key}'. Available: {available}") from exc
