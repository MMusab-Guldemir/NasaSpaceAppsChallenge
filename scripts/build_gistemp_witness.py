"""Turn NASA GISTEMP v4 gridded anomalies into monthly area means for the prepared regions.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni. Usage:
  python -I gistemp_witness.py <download_dir> <app_dir>
Writes <app_dir>/data/witness/<region>_air_temperature.csv (date, value, unit, source).
"""
import gzip
import shutil
import sys
from pathlib import Path

download_dir, app_dir = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(app_dir))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

from trend.regions import REGIONS  # noqa: E402

PRODUCTS = {
    "250": ("gistemp250_GHCNv4", "NASA GISTEMP v4, 250 km smoothing (GHCN v4 land stations), GISS"),
    "1200": ("gistemp1200_GHCNv4_ERSSTv5", "NASA GISTEMP v4, 1200 km smoothing (GHCN v4 + ERSST v5), GISS"),
}


def open_product(stem):
    nc = download_dir / f"{stem}.nc"
    if not nc.exists():
        with gzip.open(download_dir / f"{stem}.nc.gz", "rb") as src, open(nc, "wb") as dst:
            shutil.copyfileobj(src, dst)
    for engine in ("h5netcdf", "scipy", None):
        try:
            return xr.open_dataset(nc, engine=engine, decode_times=True)
        except Exception:  # try the next engine
            continue
    raise RuntimeError(f"cannot open {nc}")


def region_series(ds, bbox):
    west, south, east, north = bbox
    lat, lon = ds["lat"].values, ds["lon"].values
    lat_in = (lat >= south - 1e-6) & (lat <= north + 1e-6)
    lon_in = (lon >= west - 1e-6) & (lon <= east + 1e-6)
    if not lat_in.any():
        lat_in = np.abs(lat - (south + north) / 2) == np.abs(lat - (south + north) / 2).min()
    if not lon_in.any():
        lon_in = np.abs(lon - (west + east) / 2) == np.abs(lon - (west + east) / 2).min()
    sub = ds["tempanomaly"].isel(lat=np.nonzero(lat_in)[0], lon=np.nonzero(lon_in)[0])
    sub = sub.sel(time=slice("1981-01-01", None))
    weights = np.cos(np.radians(sub["lat"])).broadcast_like(sub)
    valid = sub.notnull()
    total = (sub.fillna(0) * weights).sum(("lat", "lon"))
    wsum = (weights * valid).sum(("lat", "lon"))
    share = valid.sum(("lat", "lon")) / (sub.sizes["lat"] * sub.sizes["lon"])
    mean = (total / wsum).where(share >= 0.5)
    frame = mean.to_dataframe(name="value").reset_index()[["time", "value"]]
    frame["date"] = pd.to_datetime(frame["time"]).dt.to_period("M").dt.to_timestamp()
    return frame[["date", "value"]], int(sub.sizes["lat"] * sub.sizes["lon"])


out_dir = app_dir / "data" / "witness"
out_dir.mkdir(parents=True, exist_ok=True)
datasets = {key: open_product(stem) for key, (stem, _) in PRODUCTS.items()}
for key, region in REGIONS.items():
    chosen = None
    for product in ("250", "1200"):
        series, cells = region_series(datasets[product], region.bbox)
        core = series[(series["date"] >= "1981-01-01") & (series["date"] <= "2025-12-01")]
        missing = core["value"].isna().mean()
        if missing <= 0.10 or product == "1200":
            chosen = (product, series, cells, missing)
            break
    product, series, cells, missing = chosen
    series = series.dropna(subset=["value"])
    series["unit"] = "°C (anomaly vs 1951-1980)"
    series["source"] = f"{PRODUCTS[product][1]}; area mean of {cells} grid cell(s), cosine-latitude weighted"
    path = out_dir / f"{key}_air_temperature.csv"
    series.assign(date=series["date"].dt.strftime("%Y-%m-%d")).to_csv(path, index=False)
    print(f"{key:12s} product={product:4s} cells={cells:2d} missing_1981_2025={missing:5.1%} rows={len(series)} last={series['date'].max():%Y-%m}")
