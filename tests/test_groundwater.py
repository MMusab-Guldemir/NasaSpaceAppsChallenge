"""Tests for the groundwater measurement and the Konya Closed Basin region.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trend.fetch import available_variable_keys, load_processed
from trend.i18n import reasons, region_name, variable_text
from trend.regions import REGIONS
from trend.variables import VARIABLES
from trend.world import SHORT_NAMES, board_verdict

ROOT = Path(__file__).resolve().parent.parent


def test_konya_region_is_a_valid_power_box_with_names():
    west, south, east, north = REGIONS["konya"].bbox
    assert 2 <= east - west <= 10 and 2 <= north - south <= 10
    assert region_name("tr", "konya", "") == "Konya Kapalı Havzası, Türkiye"
    assert SHORT_NAMES["en"]["konya"] == SHORT_NAMES["tr"]["konya"] == "Konya"


def test_groundwater_texts_exist_in_both_languages():
    variable = VARIABLES["groundwater"]
    assert variable.aggregation == "mean" and variable.doi == "10.5067/TXBMLX370XX8"
    for lang in ("en", "tr"):
        texts = variable_text(lang, variable)
        assert texts["name"] and texts["definition"] and len(texts["caveats"]) == 3
        for direction in ("up", "down", "none"):
            assert reasons(lang, "groundwater", direction)


def test_prefetch_turns_daily_giovanni_files_into_monthly_means(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("prefetch", ROOT / "scripts" / "prefetch.py")
    prefetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prefetch)
    days = pd.date_range("2003-02-01", "2003-04-30", freq="D")
    header = "Title:,test\nFill Value (mean_GWS):, -9999\n\ntime, mean_GLDAS_CLSM025_DA1_D_2_2_GWS_tavg\n"
    rows = "\n".join(f"{d:%Y-%m-%d},{500 + i * 0.1:.1f}" for i, d in enumerate(days))
    (tmp_path / "giovanni_groundwater_testbox_2003_2003.csv").write_text(header + rows, encoding="utf-8")
    saved = {}
    monkeypatch.setattr(prefetch, "RAW_DIR", tmp_path)
    monkeypatch.setattr(prefetch, "get_region", lambda key: REGIONS["konya"])
    monkeypatch.setattr(prefetch, "save_processed", lambda monthly, region, variable, source: saved.setdefault("m", monthly) is None or tmp_path / "x.csv")
    # the region key in the file name must match the region passed in
    (tmp_path / "giovanni_groundwater_testbox_2003_2003.csv").rename(tmp_path / "giovanni_groundwater_konya_2003_2003.csv")
    prefetch.main(["--region", "konya", "--variables", "groundwater"])
    monthly = saved["m"]
    assert len(monthly) == 3 and monthly["n_days"].tolist() == [28, 31, 30]
    assert np.isclose(monthly["value"].iloc[0], np.mean([500 + i * 0.1 for i in range(28)]))


@pytest.mark.parametrize("region_key", [r for r in REGIONS if "groundwater" in available_variable_keys(r)])
def test_real_groundwater_files_start_in_2003_and_are_testable(region_key):
    monthly = load_processed(region_key, "groundwater")
    assert monthly["date"].min() >= pd.Timestamp("2003-02-01")
    assert monthly["value"].notna().mean() > 0.95
    verdict = board_verdict(monthly, "groundwater")
    assert verdict.status in ("confirmed", "disputed", "noevidence", "weak")
