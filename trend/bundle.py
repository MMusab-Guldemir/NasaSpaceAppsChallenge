"""Open data: every prepared series behind the World board in one ZIP, with a sources file.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

The ZIP holds the monthly area averages the app tests (``data/processed``), the independent NASA
records used as witnesses (``data/witness``) and ``SOURCES.md``: every region box, every product
with its provider, DOI and citation, and what each witness record is. Anyone can then re-run the
trend tests outside the app, or check them with other tools.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from trend.fetch import PROCESSED_DIR, PROJECT_ROOT
from trend.regions import REGIONS
from trend.variables import VARIABLES

WITNESS_DIR = PROJECT_ROOT / "data" / "witness"

# What each witness file is (file name: <region>_<measurement>[_<source>].csv)
WITNESS_SOURCES = {
    "air_temperature": "NASA GISS Surface Temperature Analysis (GISTEMP v4): weather stations, area mean of "
                       "the 2° grid boxes.",
    "precipitation": "NASA GPCP v3.3 monthly satellite-gauge precipitation (GPCPMON_3.3), via NASA Giovanni.",
    "precipitation_imerg": "NASA GPM IMERG Final monthly precipitation (GPM_3IMERGM v07), via NASA Giovanni: "
                           "a high-resolution check, not an extra witness (it is calibrated to GPCP).",
    "aod": "MODIS Terra aerosol optical depth at 550 nm, Dark Target and Deep Blue combined (MOD08_M3 v6.1), "
           "via NASA Giovanni.",
    "snowfall": "NASA GLDAS-2.1 Noah monthly snowfall rate (GLDAS_NOAH025_M v2.1), via NASA Giovanni: a "
                "model cross-check, not a measurement.",
}

BUNDLE_TEXT = {
    "en": {
        "button": "⬇ Download every prepared series (ZIP, CSV files with sources)",
        "help": "Monthly area averages for all prepared regions and measurements, the NASA witness "
                "records, and SOURCES.md with every product, DOI and region box.",
    },
    "tr": {
        "button": "⬇ Hazır tüm serileri indir (ZIP, kaynaklarıyla CSV dosyaları)",
        "help": "Hazır tüm bölge ve ölçümler için aylık alan ortalamaları, NASA tanık kayıtları ve her "
                "ürünün, DOI'nin ve bölge kutusunun yazdığı SOURCES.md.",
    },
}


def bundle_text(lang: str, key: str) -> str:
    return BUNDLE_TEXT.get(lang, BUNDLE_TEXT["en"])[key]


def sources_markdown() -> str:
    """SOURCES.md: region boxes, measurements with product, provider, DOI and citation, witnesses."""
    lines = [
        "# Earth System Trend Detective: data bundle",
        "",
        "Team Avni, NASA Space Apps Challenge 2026. Not affiliated with or endorsed by NASA.",
        "",
        "## Files",
        "",
        "- `processed/<region>_<measurement>.csv`: monthly area averages over the region box, as tested "
        "in the app (`date`, `value`, and where known the number of valid days and the source).",
        "- `witness/<region>_<measurement>[_<source>].csv`: an independent NASA record for the same box, "
        "used as the third witness.",
        "",
        "## Regions (west, south, east, north; degrees)",
        "",
    ]
    for key, region in REGIONS.items():
        west, south, east, north = region.bbox
        lines.append(f"- `{key}`: {region.name}: {west:g}, {south:g}, {east:g}, {north:g}")
    lines += ["", "## Measurements", ""]
    for key, variable in VARIABLES.items():
        doi = f" DOI: https://doi.org/{variable.doi}" if variable.doi else ""
        lines.append(f"- `{key}`: {variable.name} ({variable.annual_unit}). {variable.product}, "
                     f"{variable.provider}.{doi}")
        lines.append(f"  Citation: {variable.citation}")
    lines += ["", "## Witness records", ""]
    for key, text in WITNESS_SOURCES.items():
        lines.append(f"- `{key}`: {text}")
    return "\n".join(lines) + "\n"


def bundle_files(processed_dir: Path = PROCESSED_DIR, witness_dir: Path = WITNESS_DIR) -> list[tuple[Path, str]]:
    """(file on disk, name inside the ZIP) for every series that goes into the bundle, sorted."""
    files = [(path, f"processed/{path.name}") for path in sorted(processed_dir.glob("*.csv"))]
    files += [(path, f"witness/{path.name}") for path in sorted(witness_dir.glob("*.csv"))]
    return files


def data_bundle(processed_dir: Path = PROCESSED_DIR, witness_dir: Path = WITNESS_DIR) -> bytes:
    """The ZIP as bytes: SOURCES.md first, then the processed and witness CSV files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("SOURCES.md", sources_markdown())
        for path, name in bundle_files(processed_dir, witness_dir):
            archive.write(path, name)
    return buffer.getvalue()
