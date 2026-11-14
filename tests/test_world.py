"""Tests for the world board (trend/world.py).

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.
"""
import numpy as np
import pandas as pd

from trend.regions import REGIONS
from trend.variables import VARIABLES
from trend.world import (
    Cell,
    board_verdict,
    case_link,
    cell_symbol,
    opposite_trends,
    summary_counts,
    world_cells,
    world_table_html,
)


def monthly(start_year: int, years: int, yearly_step: float, noise: float = 0.0, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(f"{start_year}-01-01", periods=12 * years, freq="MS")
    trend = yearly_step * (dates.year - start_year)
    return pd.DataFrame({"date": dates, "value": 10 + trend + noise * rng.normal(size=len(dates))})


def test_board_verdict_follows_the_board_rules():
    assert board_verdict(None, "air_temperature").status == "open"
    rising = board_verdict(monthly(1981, 30, 0.05, noise=0.01), "air_temperature")
    assert rising.status == "confirmed" and rising.result.slope_per_year > 0
    assert board_verdict(monthly(2015, 5, 0.05), "air_temperature").status == "insufficient"
    dry = monthly(1981, 30, 0.0)
    dry["value"] = 0.0
    assert board_verdict(dry, "snowfall").status == "no_snow"


def test_world_cells_cover_every_region_and_measurement():
    def loader(region_key, variable_key):
        if variable_key != "air_temperature":
            return None
        step = 0.05 if region_key == "colorado" else -0.05
        return monthly(1981, 30, step, noise=0.01, seed=len(region_key))

    cells = world_cells(loader)
    assert len(cells) == len(REGIONS) * len(VARIABLES)
    assert cells[("colorado", "air_temperature")].direction == "up"
    assert cells[("colorado", "no2")].status == "open"
    found = opposite_trends(cells)
    assert found and found[0]["variable"] == "air_temperature"
    assert found[0]["up"] == ["colorado"] and "alps" in found[0]["down"]


def test_summary_counts_and_chance_range():
    cells = {
        ("a", "x"): Cell("a", "x", "confirmed", 1.0, 0.01, 1981, 2025),
        ("b", "x"): Cell("b", "x", "noevidence", 0.1, 0.5, 1981, 2025),
        ("c", "x"): Cell("c", "x", "open"),
    }
    counts = summary_counts(cells)
    assert counts["tested"] == 2 and counts["confirmed"] == 1 and counts["noevidence"] == 1
    assert 1 <= counts["low"] <= counts["high"]


def test_symbols_and_links():
    assert cell_symbol(Cell("a", "x", "confirmed", -2.0)) == "▼"
    assert cell_symbol(Cell("a", "x", "disputed", 2.0)) == "▲?"
    assert cell_symbol(Cell("a", "x", "weak", -2.0)) == "▽"
    assert cell_symbol(Cell("a", "x", "insufficient")) == ""
    assert case_link("tr", "amazon", "precipitation") == "?lang=tr&region=amazon&case=precipitation"


def test_table_html_escapes_text_and_links_tested_cells():
    cells = {("amazon", "precipitation"): Cell("amazon", "precipitation", "confirmed", -202.0, 0.001, 1981, 2025)}
    table = world_table_html(
        cells, "en",
        variable_name=lambda key: "<b>" + key,
        status_name=lambda status: status,
        unit_name=lambda key: "mm",
        rate_text=lambda key, value: f"{value:+.1f}",
    )
    assert "&lt;b&gt;precipitation" in table and "<b>precipitation" not in table
    assert "region=amazon&amp;case=precipitation" in table
    assert table.count("<a ") == 1  # only the tested cell links to a case


def test_world_board_view_renders_and_opens_a_case():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    app = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app, default_timeout=90)
    at.query_params["view"] = "world"
    at.query_params["lang"] = "tr"
    at.run()
    assert not at.exception
    assert at.session_state["view"] == "world"
    assert any("table class='world'" in m.value for m in at.markdown)
    buttons = [b for b in at.button if b.key and b.key.startswith("world_open_")]
    assert buttons, "the opposite-trends finds should offer buttons"
    target = buttons[0].key.removeprefix("world_open_")
    buttons[0].click().run()
    assert not at.exception
    assert at.session_state["view"] == "case"
    assert f"{at.session_state['region']}_{at.session_state['case']}" == target


def test_a_place_that_is_never_that_hot_gets_no_hot():
    import numpy as np
    import pandas as pd

    dates = pd.date_range("1981-01-01", periods=12 * 30, freq="MS")
    cool = pd.DataFrame({"date": dates, "value": np.zeros(len(dates))})
    assert board_verdict(cool, "hot_days").status == "no_hot"
