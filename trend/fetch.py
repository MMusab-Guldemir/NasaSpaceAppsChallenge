"""NASA data access and the small cached CSV files the app reads.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

from trend.regions import Region
from trend.variables import Variable

POWER_MONTHLY_REGIONAL_URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Variables served by the POWER API: variable key -> (POWER parameter, value is a daily rate)
POWER_VARIABLES: dict[str, tuple[str, bool]] = {
    "air_temperature": ("T2M", False),
    "snowfall": ("PRECSNOLAND", True),
}


class DataSourceError(RuntimeError):
    """Raised when a NASA service returns an error or unexpected content."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def request_power_regional(
    parameter: str, region: Region, start_year: int, end_year: int, timeout: int = 300
) -> dict:
    """Call the POWER monthly regional API for one parameter (the API allows only one)."""
    params = {
        "parameters": parameter,
        "community": "AG",
        "latitude-min": region.south,
        "latitude-max": region.north,
        "longitude-min": region.west,
        "longitude-max": region.east,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }
    response = requests.get(POWER_MONTHLY_REGIONAL_URL, params=params, timeout=timeout)
    if response.status_code != 200:
        try:
            detail = response.json().get("messages") or response.json()
        except ValueError:
            detail = response.text[:500]
        raise DataSourceError(
            f"POWER API returned HTTP {response.status_code}: {detail}", status=response.status_code
        )
    return response.json()


def power_sources(payload: dict) -> str:
    """The data sources POWER reports in its response header (for example MERRA-2)."""
    sources = payload.get("header", {}).get("sources", [])
    if isinstance(sources, (list, tuple)):
        return ", ".join(str(s) for s in sources) or "not reported"
    return str(sources) or "not reported"


def parse_power_regional(payload: dict, parameter: str) -> pd.DataFrame:
    """Turn a POWER regional payload into a monthly area average.

    The average is weighted by the cosine of latitude, because grid cells shrink toward the poles.
    POWER's 13th "month" key (its annual value) is dropped and fill values become missing.
    A month where any grid cell is missing gets a missing value, so a partial average is never
    passed off as a full one.

    Returns a DataFrame with columns ``date`` (first day of the month), ``value`` and ``n_cells``.
    """
    fill_value = float(payload.get("header", {}).get("fill_value", -999.0))
    rows = []
    for feature in payload.get("features", []):
        lon, lat = feature["geometry"]["coordinates"][:2]
        series = feature["properties"]["parameter"][parameter]
        for key, value in series.items():
            month = int(key[4:])
            if month == 13:
                continue
            rows.append((int(key[:4]), month, float(lat), float(lon), value))
    if not rows:
        raise DataSourceError("POWER returned no grid cells for this region.")

    cells = pd.DataFrame(rows, columns=["year", "month", "lat", "lon", "value"])
    expected_cells = cells[["lat", "lon"]].drop_duplicates().shape[0]
    cells["value"] = pd.to_numeric(cells["value"], errors="coerce")
    is_fill = np.isclose(cells["value"], fill_value) | (cells["value"] <= -998)
    cells.loc[is_fill, "value"] = np.nan

    cells["weight"] = np.cos(np.radians(cells["lat"]))
    cells["weighted"] = cells["weight"] * cells["value"]
    valid = cells.dropna(subset=["value"])
    if valid.empty:
        raise DataSourceError("POWER returned only fill values for this request.")
    monthly = valid.groupby(["year", "month"], as_index=False).agg(
        weighted=("weighted", "sum"), weight=("weight", "sum"), n_cells=("value", "size")
    )
    monthly["value"] = monthly["weighted"] / monthly["weight"]
    monthly.loc[monthly["n_cells"] < expected_cells, "value"] = np.nan
    monthly["date"] = pd.to_datetime(monthly[["year", "month"]].assign(day=1))
    return monthly.loc[:, ["date", "value", "n_cells"]].sort_values("date").reset_index(drop=True)


def daily_rate_to_monthly_total(monthly: pd.DataFrame) -> pd.DataFrame:
    """Convert a monthly mean daily rate (for example mm/day) into a monthly total (mm)."""
    out = monthly.copy()
    out["value"] = out["value"] * out["date"].dt.days_in_month
    return out


def fetch_power_variable(
    variable: Variable, region: Region, start_year: int, end_year: int
) -> tuple[pd.DataFrame, str]:
    """Fetch one POWER variable for a region.

    Returns the monthly series in the cached unit and the data sources POWER reports.
    """
    if variable.key not in POWER_VARIABLES:
        raise ValueError(f"'{variable.key}' is not served by the POWER API.")
    parameter, is_daily_rate = POWER_VARIABLES[variable.key]
    try:
        payload = request_power_regional(parameter, region, start_year, end_year)
    except DataSourceError as error:
        if error.status is None or not 400 <= error.status < 500:
            raise
        # A request error can mean the newest year is not published yet; retry once without it.
        print(f"POWER rejected end year {end_year} ({error}); retrying with {end_year - 1}.")
        payload = request_power_regional(parameter, region, start_year, end_year - 1)
    monthly = parse_power_regional(payload, parameter)
    if is_daily_rate:
        monthly = daily_rate_to_monthly_total(monthly)
    return monthly, power_sources(payload)


def processed_path(region_key: str, variable_key: str) -> Path:
    """Location of the cached monthly CSV for one region and variable."""
    return PROCESSED_DIR / f"{region_key}_{variable_key}.csv"


def save_processed(monthly: pd.DataFrame, region: Region, variable: Variable, source: str) -> Path:
    """Write a monthly series to ``data/processed`` with its unit and source."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = monthly.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["unit"] = variable.unit
    out["source"] = source
    path = processed_path(region.key, variable.key)
    out.to_csv(path, index=False)
    return path


def load_processed(region_key: str, variable_key: str) -> pd.DataFrame | None:
    """Read a cached monthly series, or return None if it has not been fetched yet."""
    path = processed_path(region_key, variable_key)
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["date"])


def available_variable_keys(region_key: str) -> list[str]:
    """Variable keys that have a cached CSV for this region."""
    prefix = f"{region_key}_"
    return sorted(p.stem[len(prefix):] for p in PROCESSED_DIR.glob(f"{prefix}*.csv"))
