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
OMNO2D_REFERENCE = (
    "Krotkov, N. A., Lamsal, L. N., et al. (2024). OMI/Aura NO2 Cloud-Screened Total and "
    "Tropospheric Column L3 Global Gridded 0.25 degree x 0.25 degree Ver 5.0, Col 004 (OMNO2d). "
    "NASA Goddard Earth Sciences Data and Information Services Center (GES DISC)."
)
GIOVANNI_ACKNOWLEDGMENT = (
    "Area averages were produced with the Giovanni online data system, developed and maintained "
    "by the NASA GES DISC."
)
MOD13A3_REFERENCE = (
    "Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. "
    "NASA EOSDIS Land Processes Distributed Active Archive Center."
)
CERES_SYN1DEG_REFERENCE = (
    "Doelling, D. R., et al. (2013). Geostationary enhanced temporal interpolation for CERES flux "
    "products. Journal of Atmospheric and Oceanic Technology, 30, 1072-1090."
)
MOPITT_REFERENCE = (
    "Drummond, J., Gille, J., & Worden, H. MOPITT CO gridded monthly means (Near and Thermal "
    "Infrared Radiances) V010. NASA Langley Atmospheric Science Data Center."
)
MERRA2_AEROSOL_REFERENCE = (
    "Global Modeling and Assimilation Office (GMAO) (2015). MERRA-2 tavgM_2d_aer_Nx: 2d, Monthly "
    "mean, Time-averaged, Single-Level, Assimilation, Aerosol Diagnostics V5.12.4. NASA GES DISC."
)
OCO2_GEOS_REFERENCE = (
    "Weir, B., Ott, L., & OCO-2 Science Team (2022). OCO-2 GEOS Level 3 monthly, 0.5x0.625 "
    "assimilated CO2 V10r. NASA GES DISC."
)
MOD44B_REFERENCE = (
    "DiMiceli, C., Sohlberg, R., & Townshend, J. (2022). MODIS/Terra Vegetation Continuous Fields "
    "Yearly L3 Global 250m SIN Grid V061. NASA EOSDIS Land Processes Distributed Active Archive "
    "Center."
)
APPEEARS_ACKNOWLEDGMENT = (
    "Area statistics were produced with AppEEARS (Application for Extracting and Exploring "
    "Analysis Ready Samples), NASA EOSDIS LP DAAC and USGS EROS Center."
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
    decimals: int = 2  # decimals shown for values and rates in this variable's unit
    min_years: int = 10  # complete years needed for a trend test (fewer only for short NASA records)


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
    "precipitation": Variable(
        key="precipitation",
        name="Precipitation (rain and snow)",
        definition="How much water falls from the sky as rain and snow, measured as a depth of water.",
        unit="mm of water per month",
        annual_label="Total precipitation per year",
        annual_unit="mm of water",
        year_axis_label="Year",
        aggregation="sum",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="NASA POWER monthly PRECTOTCORR (MERRA-2 based, corrected with observations)",
        provider="NASA Langley Research Center POWER Project",
        doi="10.1175/JCLI-D-16-0758.1",
        citation=f"{POWER_ACKNOWLEDGMENT} {MERRA2_REFERENCE}",
        caveats=(
            "Comes from the MERRA-2 reanalysis, corrected with observed precipitation where "
            "available, on a grid of about 50 km.",
            "Rain varies a lot from year to year, so a trend needs a long record to show up.",
            "The rain-gauge data used for the correction change over the decades (far fewer stations "
            "in some regions after the mid-2000s), so part of a trend can come from the data rather "
            "than the weather; NASA's GPCP satellite-gauge record is a useful second check.",
            "The newest months in NASA POWER can come from a near-real-time product and may be "
            "revised later.",
        ),
        decimals=1,
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
        doi="10.5067/AURA/OMI/DATA3407",
        citation=f"{OMNO2D_REFERENCE} {GIOVANNI_ACKNOWLEDGMENT}",
        caveats=(
            "The value is an average over the whole box, including rural areas and, near coasts, "
            "the sea, so pollution in cities is diluted.",
            "The OMI instrument has a 'row anomaly' that reduces the number of usable "
            "measurements.",
            "2020 shows a dip linked to reduced activity during the COVID-19 pandemic.",
            "The OMI instrument is aging and its Aura satellite's orbit has been drifting in recent "
            "years, so treat changes after about 2022 with extra caution.",
        ),
        min_valid_days=10,
    ),
    "co": Variable(
        key="co",
        name="Carbon monoxide (CO)",
        definition=(
            "A poisonous gas from incomplete burning: car exhaust, industry, stoves and fires."
        ),
        unit="10¹⁸ molecules/cm²",
        annual_label="Annual mean carbon monoxide column",
        annual_unit="10¹⁸ molecules/cm²",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="MOPITT MOP03JM v010, total column, daytime",
        provider="NASA Langley ASDC, via Giovanni",
        doi="10.5067/TERRA/MOPITT/MOP03JM_L3.010",
        citation=f"{MOPITT_REFERENCE} {GIOVANNI_ACKNOWLEDGMENT}",
        caveats=(
            "The value counts carbon monoxide in the whole column of air, not only at the ground.",
            "Big fire years, for example in the Amazon, can stand out; far-north regions such as "
            "Siberia have no daytime measurements in mid-winter, so no complete yearly value can be "
            "built there.",
            "MOPITT data in Giovanni currently end in December 2024.",
        ),
    ),
    "black_carbon": Variable(
        key="black_carbon",
        name="Soot (black carbon)",
        definition=(
            "Tiny black particles of soot from burning diesel, coal, wood and forests, in the air "
            "near the ground."
        ),
        unit="µg/m³",
        annual_label="Annual mean black carbon near the ground",
        annual_unit="µg/m³",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="MERRA-2 M2TMNXAER v5.12.4, black carbon surface mass concentration",
        provider="NASA GMAO and GES DISC, via Giovanni",
        doi="10.5067/FH9A0MLJPC7N",
        citation=f"{MERRA2_AEROSOL_REFERENCE} {MERRA2_REFERENCE} {GIOVANNI_ACKNOWLEDGMENT}",
        caveats=(
            "Comes from the MERRA-2 aerosol reanalysis: a model guided by satellite aerosol "
            "measurements, on a grid of about 50 km.",
            "The emission data the model uses can lag behind real changes in recent years.",
            "Wildfire smoke can make single years stand out.",
        ),
        decimals=3,
    ),
    "aod": Variable(
        key="aod",
        name="Dust and smoke (aerosols)",
        definition=(
            "How much sunlight is blocked by tiny particles in the air, such as dust, smoke and "
            "pollution haze. Higher values mean hazier air."
        ),
        unit="AOD (no unit)",
        annual_label="Annual mean aerosol optical depth",
        annual_unit="AOD",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="NASA POWER monthly AOD_55 (CERES SYN1deg)",
        provider="NASA Langley Research Center POWER Project",
        doi="10.1175/JTECH-D-12-00136.1",
        citation=f"{POWER_ACKNOWLEDGMENT} {CERES_SYN1DEG_REFERENCE}",
        caveats=(
            "Aerosol optical depth counts the particles in the whole column of air, not only the "
            "air we breathe at the ground, so it is not the same as PM2.5.",
            "It comes from an aerosol model corrected with MODIS satellite measurements (CERES "
            "SYN1deg), on a grid of about 100 km (1 degree), starting in 2001.",
            "From April 2022 the model is corrected with a different satellite instrument (VIIRS "
            "instead of MODIS), which can shift the last years a little. For a cautious check, also "
            "try the period up to 2021.",
            "There are no values over snow and ice or in the darkness of the polar winter, so such "
            "months are left out.",
            "Desert dust storms and big wildfires can make single years stand out.",
            "The newest months in NASA POWER can come from a near-real-time product and may be "
            "revised later.",
        ),
        decimals=3,
    ),
    "co2": Variable(
        key="co2",
        name="Carbon dioxide (CO₂)",
        definition=(
            "The main greenhouse gas, released mostly by burning coal, oil and gas; plants and "
            "oceans take part of it back."
        ),
        unit="ppm",
        annual_label="Annual mean CO₂ in the air column",
        annual_unit="ppm",
        year_axis_label="Year",
        aggregation="mean",
        season_months=ALL_MONTHS,
        year_starts_month=1,
        product="OCO-2 GEOS L3 monthly V10r, assimilated column-average CO₂",
        provider="NASA GES DISC, via Giovanni",
        doi="10.5067/BGFIODET3HZ8",
        citation=f"{OCO2_GEOS_REFERENCE} {GIOVANNI_ACKNOWLEDGMENT}",
        caveats=(
            "This NASA record covers only 2015 to 2021, so the app allows 7 years here instead of "
            "its usual 10; CO₂ rises so steadily that 7 years can still show it.",
            "CO₂ mixes around the whole planet within about a year, so local cuts in emissions "
            "hardly show in a regional value.",
            "It combines OCO-2 satellite measurements with the GEOS model.",
        ),
        min_years=7,
    ),
    "ndvi": Variable(
        key="ndvi",
        name="Vegetation greenness (NDVI)",
        definition=(
            "How green and dense the plants are, on a scale from -1 to 1. "
            "Higher values mean more green vegetation."
        ),
        unit="NDVI (no unit)",
        annual_label="Mean NDVI from May to September",
        annual_unit="NDVI",
        year_axis_label="Year",
        aggregation="mean",
        season_months=(5, 6, 7, 8, 9),
        year_starts_month=1,
        product="MODIS Terra MOD13A3 v061, monthly, 1 km",
        provider="NASA LP DAAC, via AppEEARS",
        doi="10.5067/MODIS/MOD13A3.061",
        citation=f"{MOD13A3_REFERENCE} {APPEEARS_ACKNOWLEDGMENT}",
        caveats=(
            "The Terra satellite's orbit has drifted since about 2020, which can slightly "
            "affect recent values.",
        ),
        decimals=3,
    ),
    "tree_cover": Variable(
        key="tree_cover",
        name="Tree cover",
        definition="The share of the land covered by tree crowns, in percent.",
        unit="% of the land",
        annual_label="Tree cover (yearly map)",
        annual_unit="% of the land",
        year_axis_label="Year",
        aggregation="mean",
        season_months=(3,),  # one yearly map, dated in March of its year
        year_starts_month=1,
        product="MODIS Terra MOD44B v061 Vegetation Continuous Fields, yearly, 250 m",
        provider="NASA LP DAAC, via AppEEARS",
        doi="10.5067/MODIS/MOD44B.061",
        citation=f"{MOD44B_REFERENCE} {APPEEARS_ACKNOWLEDGMENT}",
        caveats=(
            "A yearly map made from a whole year of MODIS images; water and missing pixels are "
            "left out.",
            "Plantations and orchards count as trees, so tree cover can grow while natural forest "
            "shrinks.",
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
