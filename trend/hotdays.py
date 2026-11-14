"""Hot days: how many days a year are hotter than 30 °C, from NASA POWER daily maximum temperature.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

NASA POWER serves daily values for a region at most 366 days per request, so a 45-year record takes one
request per year. Every grid cell counts its own days above the threshold in each month; the region's
value is the cos(latitude)-weighted mean of those counts, that is the number of hot days a typical spot
in the region gets. Counting first and averaging second keeps hot days that averaging the temperatures of
hot and cool cells (sea, mountains) first would hide.
"""
from __future__ import annotations

import calendar
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import requests

from trend.fetch import DataSourceError, select_cells

PARAMETER = "T2M_MAX"
THRESHOLD_C = 30.0
DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"
FILL_VALUE = -999.0


def request_daily_year(bbox: tuple[float, float, float, float], year: int, timeout: float = 120,
                       pauses: tuple[float, ...] = (3.0, 8.0, 20.0)) -> dict:
    """One year of daily T2M_MAX for a 2-10 degree box (west, south, east, north), with retries."""
    west, south, east, north = bbox
    params = {
        "parameters": PARAMETER, "community": "AG",
        "latitude-min": south, "latitude-max": north, "longitude-min": west, "longitude-max": east,
        "start": f"{year}0101", "end": f"{year}1231", "format": "JSON",
    }
    for attempt, pause in enumerate((*pauses, None), start=1):
        try:
            response = requests.get(DAILY_URL, params=params, timeout=timeout)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("features"), list):
                    return payload
                raise DataSourceError("NASA POWER sent an unexpected answer.")
            if response.status_code not in (429, 500, 502, 503, 504):
                raise DataSourceError(f"NASA POWER daily API: HTTP {response.status_code}: {response.text[:200]}",
                                      status=response.status_code)
        except (requests.RequestException, ValueError) as error:
            if pause is None:
                raise
            last = error  # noqa: F841 (kept for debugging)
        if pause is None:
            raise DataSourceError(f"NASA POWER daily API kept failing for {bbox} {year}.")
        time.sleep(pause)
    raise DataSourceError(f"NASA POWER daily API kept failing for {bbox} {year}.")


def _days_in(month: str) -> int:
    """Days in a calendar month given as 'YYYY-MM-01'."""
    return calendar.monthrange(int(month[:4]), int(month[5:7]))[1]


def monthly_hot_days(payloads: list[dict], bbox: tuple[float, float, float, float],
                     threshold: float = THRESHOLD_C) -> pd.DataFrame:
    """Monthly number of days above ``threshold`` (°C), averaged over the grid cells of ``bbox``.

    ``payloads`` are daily POWER regional answers (any number of years and request boxes). A cell's
    month counts only when all its days have values; a month where any selected cell is incomplete is
    left out, like the monthly POWER variables. Returns columns date (first of the month), value and
    n_cells.
    """
    features = [feature for payload in payloads for feature in payload.get("features", [])]
    if not features:
        raise DataSourceError("NASA POWER returned no grid cells for this area.")
    cells = select_cells(features, bbox, PARAMETER, FILL_VALUE)
    if not cells:
        raise DataSourceError("No grid cells with data in this area.")
    keep = {(round(float(c["geometry"]["coordinates"][0]), 6), round(float(c["geometry"]["coordinates"][1]), 6))
            for c in cells}

    # (cell, month) -> [hot days, valid days, days in the record]
    counts: dict[tuple[tuple[float, float], str], list[int]] = defaultdict(lambda: [0, 0, 0])
    latitudes: dict[tuple[float, float], float] = {}
    seen: set[tuple[tuple[float, float], str]] = set()  # overlapping request boxes repeat edge cells
    for feature in features:
        lon, lat = feature["geometry"]["coordinates"][:2]
        cell = (round(float(lon), 6), round(float(lat), 6))
        if cell not in keep:
            continue
        latitudes[cell] = float(lat)
        for day, value in feature["properties"]["parameter"][PARAMETER].items():
            if (cell, day) in seen:
                continue
            seen.add((cell, day))
            month = f"{day[:4]}-{day[4:6]}-01"
            entry = counts[(cell, month)]
            entry[2] += 1
            if value is None:
                continue
            value = float(value)
            if np.isclose(value, FILL_VALUE) or value <= -998:
                continue
            entry[1] += 1
            entry[0] += int(value > threshold)

    months = sorted({month for _, month in counts})
    cell_list = sorted(latitudes)
    weights = np.cos(np.deg2rad([latitudes[c] for c in cell_list]))
    rows = []
    for month in months:
        values = []
        for cell in cell_list:
            hot, valid, _ = counts.get((cell, month), [0, 0, 0])
            values.append(hot if valid == _days_in(month) else np.nan)
        values = np.asarray(values, dtype=float)
        value = float(np.average(values, weights=weights)) if not np.isnan(values).any() else np.nan
        rows.append({"date": pd.Timestamp(month), "value": value, "n_cells": len(cell_list)})
    table = pd.DataFrame(rows, columns=["date", "value", "n_cells"])
    cells_table = []
    for cell in cell_list:
        for year in sorted({month[:4] for month in months}):
            year_months = [m for m in months if m.startswith(year)]
            entries = [counts.get((cell, m), [0, 0, 0]) for m in year_months]
            complete = len(year_months) == 12 and all(
                entry[1] == _days_in(m) for m, entry in zip(year_months, entries)
            )
            cells_table.append({
                "lat": latitudes[cell], "lon": cell[0], "year": int(year),
                "days": float(sum(hot for hot, _, _ in entries)) if complete else np.nan,
            })
    table.attrs["cells"] = pd.DataFrame(cells_table, columns=["lat", "lon", "year", "days"])
    return table
