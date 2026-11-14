"""NASA data access and the small cached CSV files the app reads.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
from __future__ import annotations

import io
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from trend.area import power_request_boxes
from trend.regions import Region
from trend.variables import Variable

LOG = logging.getLogger(__name__)

POWER_MONTHLY_REGIONAL_URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Variables served by the POWER API: variable key -> (POWER parameter, value is a daily rate)
# POWER reports exactly 0.0 (not the fill value) where CERES SYN1deg has no aerosol value, for
# example over snow and ice or in the polar winter; such cells are treated as missing.
ZERO_MEANS_MISSING = {"AOD_55"}

POWER_VARIABLES: dict[str, tuple[str, bool]] = {
    "air_temperature": ("T2M", False),
    "precipitation": ("PRECTOTCORR", True),
    "snowfall": ("PRECSNOLAND", True),
    "aod": ("AOD_55", False),
}

# Monthly measurements from Giovanni area averages: variable key -> factor to the cached unit.
GIOVANNI_MONTHLY: dict[str, float] = {
    "co": 1e-18,  # molecules/cm² -> 10^18 molecules/cm²
    "black_carbon": 1e9,  # kg/m³ -> µg/m³
    "co2": 1e6,  # mol/mol -> ppm
}


class DataSourceError(RuntimeError):
    """Raised when a NASA service returns an error or unexpected content."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


Timeout = float | tuple[float, float]


def request_power_regional(
    parameter: str, region: Region, start_year: int, end_year: int, timeout: Timeout = 300
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
            body = response.json()
            detail = (body.get("messages") if isinstance(body, dict) else None) or body
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
    Cells that never report data (for example sea cells for land-only variables such as snowfall)
    are left out. A month where any of the remaining cells is missing gets a missing value, so a
    partial average is never passed off as a full one.

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
    cells["value"] = pd.to_numeric(cells["value"], errors="coerce")
    is_fill = np.isclose(cells["value"], fill_value) | (cells["value"] <= -998)
    if parameter in ZERO_MEANS_MISSING:
        is_fill |= cells["value"] == 0
    cells.loc[is_fill, "value"] = np.nan
    expected_cells = cells.dropna(subset=["value"])[["lat", "lon"]].drop_duplicates().shape[0]

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


UNEXPECTED_RESPONSE = "POWER returned an unexpected response."
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
RETRY_PAUSES = (1.5, 3.0)  # seconds to wait before the second and the third attempt
_sleep = time.sleep  # replaced in tests


def is_transient(error: Exception) -> bool:
    """A quick failure worth another try: a dropped connection, a garbled answer or a busy server.

    Timeouts are not retried, so a NASA POWER that hangs does not keep the page waiting several
    times; neither are rejected requests or areas without data.
    """
    if isinstance(error, requests.Timeout):
        return False
    if isinstance(error, requests.RequestException):
        return True
    if isinstance(error, DataSourceError):
        return error.status in TRANSIENT_STATUS or str(error) == UNEXPECTED_RESPONSE
    return False


def _request_with_end_retry(
    parameter: str, region: Region, start_year: int, end_year: int, timeout: Timeout
) -> dict:
    """One POWER request; an "end date out of range" answer is retried once without the newest year.

    Any other error (box size, rate limit, server trouble) is reported as it is.
    """
    try:
        return request_power_regional(parameter, region, start_year, end_year, timeout)
    except DataSourceError as error:
        if not (error.status == 422 and "end date" in str(error).lower()):
            raise
        LOG.info("POWER rejected end year %s; retrying with %s.", end_year, end_year - 1)
        return request_power_regional(parameter, region, start_year, end_year - 1, timeout)


def _request_retrying(
    parameter: str, region: Region, start_year: int, end_year: int, timeout: Timeout,
    pauses: tuple[float, ...],
) -> dict:
    """``_request_with_end_retry`` with a few quick retries for transient failures."""
    for attempt, pause in enumerate((*pauses, None), start=1):
        try:
            return _request_with_end_retry(parameter, region, start_year, end_year, timeout)
        except (requests.RequestException, DataSourceError) as error:
            if pause is None or not is_transient(error):
                raise
            LOG.warning(
                "NASA POWER attempt %d failed for %s %s: %r; trying again in %.1f s.",
                attempt, parameter, region.bbox, error, pause,
            )
            _sleep(pause)
    raise AssertionError("unreachable")


EDGE_TOLERANCE = 1e-6


def _cell_center(feature: dict) -> tuple[float, float]:
    lon, lat = feature["geometry"]["coordinates"][:2]
    return round(float(lon), 6), round(float(lat), 6)


def _has_data(feature: dict, parameter: str, fill_value: float) -> bool:
    for key, value in feature["properties"]["parameter"][parameter].items():
        if int(key[4:]) == 13 or value is None:
            continue
        value = float(value)
        if np.isclose(value, fill_value) or value <= -998:
            continue
        if parameter in ZERO_MEANS_MISSING and value == 0:
            continue
        return True
    return False


def select_cells(
    features: list[dict], bbox: tuple[float, float, float, float], parameter: str, fill_value: float
) -> list[dict]:
    """Grid cells for a rectangle: those whose centres lie inside it or on its edge.

    A rectangle smaller than one grid cell may contain no centre; then the nearest cell that has
    data is used. Duplicate cells from overlapping request boxes are dropped.
    """
    west, south, east, north = bbox
    unique: dict[tuple[float, float], dict] = {}
    for feature in features:
        unique.setdefault(_cell_center(feature), feature)
    inside = [
        feature for (lon, lat), feature in unique.items()
        if west - EDGE_TOLERANCE <= lon <= east + EDGE_TOLERANCE
        and south - EDGE_TOLERANCE <= lat <= north + EDGE_TOLERANCE
    ]
    if inside:
        return inside
    center_lon, center_lat = (west + east) / 2, (south + north) / 2
    scale = math.cos(math.radians(center_lat))

    def distance(item):
        (lon, lat), _ = item
        return (lat - center_lat) ** 2 + ((lon - center_lon) * scale) ** 2

    ranked = sorted(unique.items(), key=distance)
    for _, feature in ranked:
        if _has_data(feature, parameter, fill_value):
            return [feature]
    return [ranked[0][1]] if ranked else []


def fetch_power_area(
    variable: Variable, bbox: tuple[float, float, float, float], start_year: int, end_year: int,
    timeout: Timeout = 300, pauses: tuple[float, ...] = RETRY_PAUSES, workers: int = 4,
) -> tuple[pd.DataFrame, str]:
    """Fetch one POWER variable for any rectangle the user picks (used by the app).

    NASA POWER serves 2 to 10 degrees per side, so a small rectangle is requested inside a
    2-degree box and a large one in several pieces (fetched in parallel); the area average then
    uses only the grid cells of the rectangle itself (see ``select_cells``). Quick failures are
    retried. Returns the monthly series in the cached unit and the data sources POWER reports.
    """
    if variable.key not in POWER_VARIABLES:
        raise ValueError(f"'{variable.key}' is not served by the POWER API.")
    parameter, is_daily_rate = POWER_VARIABLES[variable.key]
    boxes = power_request_boxes(bbox)
    failed = threading.Event()  # set by the first piece that fails

    def one(box):
        # A worker that frees up when a piece fails can start another piece before the caller has
        # cancelled it. That piece sends no request: the failed piece's error is raised anyway, so
        # its result would never be used.
        if failed.is_set():
            return None
        region = Region("custom", "custom", *box)
        try:
            return _request_retrying(parameter, region, start_year, end_year, timeout, pauses)
        except Exception:
            failed.set()
            raise

    if len(boxes) == 1:
        payloads = [one(boxes[0])]
    else:
        # Not a with-block: leaving one waits for every piece still running, so with NASA POWER down
        # a large rectangle would keep the page waiting for many timeout rounds after the first
        # failure. Pieces not yet started are cancelled and the error is reported at once.
        pool = ThreadPoolExecutor(max_workers=min(workers, len(boxes)))
        try:
            payloads = list(pool.map(one, boxes))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    try:
        header = payloads[0].get("header", {})
        fill_value = float(header.get("fill_value", -999.0))
        features = [feature for payload in payloads for feature in payload.get("features", [])]
        cells = select_cells(features, bbox, parameter, fill_value)
        monthly = parse_power_regional({"header": header, "features": cells}, parameter)
    except (KeyError, AttributeError, TypeError, ValueError, IndexError) as exc:
        raise DataSourceError(UNEXPECTED_RESPONSE) from exc
    if is_daily_rate:
        monthly = daily_rate_to_monthly_total(monthly)
    sources = sorted({part for payload in payloads for part in power_sources(payload).split(", ")})
    return monthly, ", ".join(sources)


def fetch_power_variable(
    variable: Variable, region: Region, start_year: int, end_year: int, timeout: Timeout = 300
) -> tuple[pd.DataFrame, str]:
    """Fetch one POWER variable for a region.

    Returns the monthly series in the cached unit and the data sources POWER reports. ``timeout``
    is passed to ``requests`` (the app uses a short one; the prefetch script keeps the default).
    """
    if variable.key not in POWER_VARIABLES:
        raise ValueError(f"'{variable.key}' is not served by the POWER API.")
    parameter, is_daily_rate = POWER_VARIABLES[variable.key]
    payload = _request_with_end_retry(parameter, region, start_year, end_year, timeout)
    try:
        monthly = parse_power_regional(payload, parameter)
    except (KeyError, AttributeError, TypeError, ValueError, IndexError) as exc:
        raise DataSourceError(UNEXPECTED_RESPONSE) from exc
    if is_daily_rate:
        monthly = daily_rate_to_monthly_total(monthly)
    return monthly, power_sources(payload)


DU_TO_MOLECULES_PER_CM2 = 2.6867e16  # 1 Dobson unit in molecules/cm²


def load_giovanni_csv(path: Path) -> pd.DataFrame:
    """Read a Giovanni area-averaged time series CSV into ``date`` and ``value`` columns.

    Giovanni puts metadata rows (title, dates, bounding box, fill value) above the data table,
    which starts with a ``time,...`` header. Fill values become missing.
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    fill_value = None
    header_index = None
    for index, line in enumerate(lines):
        lowered = line.strip().lower()
        if lowered.startswith("fill value"):
            try:
                fill_value = float(line.rsplit(",", 1)[-1])
            except ValueError:
                fill_value = None
        if lowered.startswith("time,"):
            header_index = index
            break
    if header_index is None:
        raise DataSourceError(f"{Path(path).name}: no 'time,...' data header found.")

    table = pd.read_csv(io.StringIO("\n".join(lines[header_index:])))
    table = table.iloc[:, :2]
    table.columns = ["date", "value"]
    table["date"] = pd.to_datetime(table["date"], errors="coerce", utc=True).dt.tz_localize(None)
    table["value"] = pd.to_numeric(table["value"], errors="coerce")
    if fill_value is not None:
        table.loc[np.isclose(table["value"], fill_value), "value"] = np.nan
    table.loc[table["value"] < -1e20, "value"] = np.nan
    return table.dropna(subset=["date"]).reset_index(drop=True)


def build_monthly_from_giovanni(files: list[Path], factor: float) -> pd.DataFrame:
    """Monthly series from Giovanni area-averaged CSVs of a monthly product.

    Giovanni time stamps sit in the middle of each month; they are moved to the first day, and the
    values are multiplied by ``factor`` to reach the cached unit.
    """
    frames = [load_giovanni_csv(path) for path in files]
    table = pd.concat(frames, ignore_index=True)
    table["date"] = table["date"].dt.to_period("M").dt.to_timestamp()
    monthly = table.groupby("date", as_index=False)["value"].mean()
    monthly["value"] = monthly["value"] * factor
    return monthly.sort_values("date").reset_index(drop=True)


def daily_to_monthly_mean(daily: pd.DataFrame, min_valid_days: int) -> pd.DataFrame:
    """Average daily values per month; months with too few valid days become missing."""
    frame = daily.copy()
    frame["month"] = frame["date"].dt.to_period("M")
    grouped = frame.groupby("month")["value"]
    monthly = pd.DataFrame({"value": grouped.mean(), "n_days": grouped.count()})
    monthly.loc[monthly["n_days"] < min_valid_days, "value"] = np.nan
    monthly["date"] = monthly.index.to_timestamp()
    return monthly.reset_index(drop=True).loc[:, ["date", "value", "n_days"]]


def build_no2_from_giovanni(files: list[Path], min_valid_days: int) -> pd.DataFrame:
    """Combine Giovanni OMNO2d CSV chunks into a monthly series in 10^15 molecules/cm²."""
    if not files:
        raise DataSourceError("No Giovanni NO2 CSV files found in data/raw.")
    daily = pd.concat([load_giovanni_csv(f) for f in sorted(files)], ignore_index=True)
    daily = daily.sort_values("date").drop_duplicates(subset="date", keep="first")
    valid = daily["value"].dropna()
    if not valid.empty and valid.abs().median() < 1e3:
        # Values in Dobson units: convert to molecules/cm².
        daily["value"] = daily["value"] * DU_TO_MOLECULES_PER_CM2
    daily["value"] = daily["value"] / 1e15
    return daily_to_monthly_mean(daily, min_valid_days)


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
