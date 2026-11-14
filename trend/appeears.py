"""Minimal AppEEARS API client: list tasks, download area statistics, submit area requests.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

Credentials come from the environment (EARTHDATA_USERNAME / EARTHDATA_PASSWORD) or from the
Earthdata Login entry in the user's netrc file. They are never printed or stored by this module.
"""
from __future__ import annotations

import netrc
import os
from pathlib import Path

import pandas as pd
import requests

from trend.regions import Region

API = "https://appeears.earthdatacloud.nasa.gov/api"
EARTHDATA_HOST = "urs.earthdata.nasa.gov"


def earthdata_credentials() -> tuple[str, str]:
    """Username and password from the environment or the netrc file (Windows uses _netrc)."""
    user, password = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if user and password:
        return user, password
    home = Path.home()
    for name in (".netrc", "_netrc"):
        path = home / name
        if path.exists():
            entry = netrc.netrc(str(path)).authenticators(EARTHDATA_HOST)
            if entry:
                return entry[0], entry[2]
    raise RuntimeError("No Earthdata Login credentials found in the environment or netrc.")


def login() -> str:
    """Return an AppEEARS bearer token."""
    response = requests.post(f"{API}/login", auth=earthdata_credentials(), timeout=60)
    response.raise_for_status()
    return response.json()["token"]


def logout(token: str) -> None:
    requests.post(f"{API}/logout", headers={"Authorization": f"Bearer {token}"}, timeout=60)


def list_tasks(token: str) -> list[dict]:
    response = requests.get(f"{API}/task", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    response.raise_for_status()
    return response.json()


def download_statistics(token: str, task_id: str, out_dir: Path, prefix: str = "") -> list[Path]:
    """Download the statistics CSV files of a finished area request.

    ``prefix`` is put in front of each file name, for example ``appeears_ndvi_marmara_``, which is
    the name pattern scripts/prefetch.py looks for.
    """
    headers = {"Authorization": f"Bearer {token}"}
    bundle = requests.get(f"{API}/bundle/{task_id}", headers=headers, timeout=60)
    bundle.raise_for_status()
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in bundle.json().get("files", []):
        name = item["file_name"]
        if not name.lower().endswith("statistics.csv"):
            continue
        response = requests.get(
            f"{API}/bundle/{task_id}/{item['file_id']}", headers=headers, timeout=300,
            allow_redirects=True,
        )
        response.raise_for_status()
        path = out_dir / f"{prefix}{Path(name).name}"
        path.write_bytes(response.content)
        saved.append(path)
    return saved


def submit_area_request(
    token: str, name: str, region: Region, product: str, layer: str, start: str, end: str
) -> str:
    """Submit an area request for a rectangular region; returns the task id.

    ``start`` and ``end`` use the AppEEARS format MM-DD-YYYY.
    """
    west, south, east, north = region.bbox
    polygon = [[[west, south], [east, south], [east, north], [west, north], [west, south]]]
    task = {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [{"startDate": start, "endDate": end}],
            "layers": [{"product": product, "layer": layer}],
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
            "geo": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "properties": {},
                              "geometry": {"type": "Polygon", "coordinates": polygon}}],
            },
        },
    }
    response = requests.post(
        f"{API}/task", json=task, headers={"Authorization": f"Bearer {token}"}, timeout=120
    )
    response.raise_for_status()
    return response.json()["task_id"]


def load_ndvi_statistics(path: Path) -> pd.DataFrame:
    """Monthly NDVI area means from an AppEEARS statistics CSV (columns ``date``, ``value``, ``n_pixels``)."""
    table = pd.read_csv(path)
    table.columns = [c.strip() for c in table.columns]
    if "Dataset" in table.columns:
        table = table[table["Dataset"].astype(str).str.contains("NDVI", case=False)]
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(table["Date"]).dt.to_period("M").dt.to_timestamp(),
            "value": pd.to_numeric(table["Mean"], errors="coerce"),
            "n_pixels": pd.to_numeric(table.get("Count"), errors="coerce"),
        }
    )
    return out.groupby("date", as_index=False).agg(value=("value", "mean"), n_pixels=("n_pixels", "sum"))
