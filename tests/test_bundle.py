"""Tests for the open-data ZIP (trend/bundle.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import io
import zipfile

import pandas as pd

from trend.bundle import BUNDLE_TEXT, WITNESS_SOURCES, bundle_files, bundle_text, data_bundle, sources_markdown
from trend.fetch import PROCESSED_DIR
from trend.regions import REGIONS
from trend.variables import VARIABLES


def test_sources_name_every_region_measurement_and_doi():
    text = sources_markdown()
    for key, region in REGIONS.items():
        assert f"`{key}`: {region.name}" in text
    for key, variable in VARIABLES.items():
        assert f"`{key}`: {variable.name}" in text
        if variable.doi:
            assert f"https://doi.org/{variable.doi}" in text
    assert "Not affiliated with or endorsed by NASA" in text


def test_every_witness_file_kind_is_described():
    kinds = set()
    for path, _ in bundle_files():
        if path.parent.name == "witness":
            stem = path.stem
            region = next(r for r in sorted(REGIONS, key=len, reverse=True) if stem.startswith(r + "_"))
            kinds.add(stem.removeprefix(region + "_"))
    assert kinds and kinds <= set(WITNESS_SOURCES)


def test_zip_holds_sources_and_every_prepared_series_unchanged():
    archive = zipfile.ZipFile(io.BytesIO(data_bundle()))
    names = archive.namelist()
    assert names[0] == "SOURCES.md"
    processed = sorted(PROCESSED_DIR.glob("*.csv"))
    assert {f"processed/{p.name}" for p in processed} <= set(names)
    assert not any(name.startswith("processed/grid") for name in names)  # the map cells stay out
    sample = processed[0]
    assert archive.read(f"processed/{sample.name}") == sample.read_bytes()
    table = pd.read_csv(io.BytesIO(archive.read("processed/konya_groundwater.csv")))
    assert {"date", "value"} <= set(table.columns)


def test_small_folders_and_texts(tmp_path):
    processed, witness = tmp_path / "p", tmp_path / "w"
    processed.mkdir()
    witness.mkdir()
    (processed / "x_air_temperature.csv").write_text("date,value\n2000-01-01,1\n", encoding="utf-8")
    archive = zipfile.ZipFile(io.BytesIO(data_bundle(processed, witness)))
    assert archive.namelist() == ["SOURCES.md", "processed/x_air_temperature.csv"]
    assert set(BUNDLE_TEXT["en"]) == set(BUNDLE_TEXT["tr"])
    assert bundle_text("tr", "button").startswith("⬇ Hazır") and bundle_text("de", "button") == bundle_text("en", "button")
