"""Earth System Trend Detective: Streamlit app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea, the "expert detective" theme, the pick-then-verdict flow
and the Turkish option come from Team Avni; the board-and-case-file layout was suggested by the AI and
approved by the team.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import html
import logging
import math
import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import folium
import requests
from folium.plugins import Draw
from streamlit_folium import st_folium

from trend.area import (
    AreaError,
    custom_region,
    format_bbox,
    normalize_bbox,
    pick_drawn_bbox,
    power_request_boxes,
)
from trend.bundle import bundle_text, data_bundle
from trend.chance import (
    DEFAULT_RUNS, chance_text, clip_phi, example_figure, intro_line, simulate, summary_lines,
)
from trend.charts import annual_trend_figure, monthly_figure, sparkline_figure
from trend.cities import (
    CITY_BY_KEY, city_bbox, city_for_bbox, city_label, city_options, city_text, near_label,
)
from trend.compare import compare_text, ranking_figure, ranking_sentence, region_ranking, untested_text
from trend.examples import EXAMPLES, example_key, example_label, examples_title
from trend.guide import (
    PLACES, TOPICS, guide_text, place_label, suggest, suggestion_key, suggestion_label, topic_label,
)
from trend.fetch import (
    POWER_VARIABLES,
    TRANSIENT_STATUS,
    DataSourceError,
    PROCESSED_DIR,
    available_variable_keys,
    fetch_power_area,
    load_processed,
    processed_path,
)
from trend.game import VIEW_LABELS, render_game_html
from trend.i18n import (
    LANGUAGES,
    METHODS,
    chance_phrase,
    ci_bounds,
    lower_first,
    method_name,
    num,
    reasons,
    region_context,
    p_phrase,
    region_name,
    status_text,
    t,
    variable_text,
)
from trend.linecheck import line_check, line_text
from trend.records import last_year_rank, record_sentence, record_text, stripes_caption, stripes_figure
from trend.regions import REGIONS, Region, nearest_region
from trend.replay import growing_record, replay_figure, replay_sentence, replay_summary, replay_text, replay_title
from trend.seasons import (
    anomaly_figure,
    deseasonalize,
    monthly_rate_per_decade,
    months_in_period,
    season_sentence,
    season_text,
    seasonal_swing,
)
from trend import seasonal
from trend.report import case_report_html, report_filename, report_text
from trend.share import build_share_link, parse_period
from trend.stats import MIN_YEARS, RECOMMENDED_YEARS, TrendResult, analyze_trend, trend_line_band
from trend.timeline import (
    earlier_significant_years,
    evidence_timeline,
    solid_since,
    start_year_check,
    timeline_figure,
    timeline_text,
    year_ranges,
)
from trend.verify import (
    compare_witness,
    extra_check_line,
    load_witness,
    no_witness_reason,
    verify_text,
    why_not_confirmed,
)
from trend.trendmap import (
    MAX_MAP_SPAN,
    add_overlay,
    cell_size,
    cell_trends,
    cell_trends_from_annual,
    fetch_cells,
    legend_html,
    map_reasons,
    map_text,
    summarize,
    why_text,
)
from trend.timelapse import (
    LAYER_KEYS,
    annual_cells,
    build_payload,
    layer_from_annual,
    load_annual_cells,
    prepared_cell_size,
    render_timelapse_html,
    time_text,
)
from trend.variables import VARIABLES
from trend.world import (
    SHORT_NAMES,
    WORLD_STYLE,
    Cell,
    board_verdict,
    case_status,
    cell_symbol,
    opposite_trends,
    place_name,
    summary_counts,
    world_cells,
    world_table_html,
    world_text,
)

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🔎", layout="wide")
LOG = logging.getLogger("trend_detective")

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
.eyebrow {
  font-family: 'Special Elite', 'Courier New', monospace; letter-spacing: 0.12em;
  text-transform: uppercase; color: #52514e; font-size: 0.85rem;
}
.step { font-weight: 700; color: #2a78d6; letter-spacing: 0.02em; margin: 0.6rem 0 0.2rem 0; }
.stamp {
  display: inline-block; font-family: 'Special Elite', 'Courier New', monospace;
  font-size: 0.95rem; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 10px; border: 2px solid currentColor; border-radius: 4px;
  transform: rotate(-3deg); margin: 4px 0 6px 0; background: rgba(255, 255, 255, 0.6);
}
.stamp.confirmed { color: #1c5cab; }
.stamp.noevidence { color: #52514e; }
.stamp.disputed, .stamp.weak { color: #a8501b; }
.stamp.open, .stamp.prepared_only, .stamp.insufficient, .stamp.no_snow, .stamp.no_hot, .stamp.no_data {
  color: #898781; border-style: dashed;
}
.clue-name { font-size: 0.78rem; letter-spacing: 0.06em; color: #52514e; min-height: 2.2em; }
.clue-value { font-size: 1.45rem; font-weight: 700; color: #0b0b0b; line-height: 1.2; }
.clue-unit { font-size: 0.82rem; color: #52514e; min-height: 2.6em; }
.hero {
  background: #ffffff; border: 1px solid #e1e0d9; border-left: 8px solid #2a78d6;
  border-radius: 10px; padding: 18px 22px 14px 22px; margin: 6px 0 10px 0;
}
.hero.chance { border-left-color: #898781; }
.hero-title { font-size: 1.55rem; font-weight: 800; color: #0b0b0b; line-height: 1.25; }
.hero-q { margin-top: 8px; color: #52514e; font-size: 0.95rem; }
.meter { margin: 30px 0 4px 0; }
.meter-track { position: relative; height: 14px; border-radius: 7px; background: #e1e0d9; }
.meter-zone { position: absolute; left: 0; top: 0; bottom: 0; background: #b7d3f6; border-radius: 7px 0 0 7px; }
.meter-threshold { position: absolute; top: -6px; bottom: -6px; width: 2px; background: #52514e; }
.meter-threshold span {
  position: absolute; top: -22px; transform: translateX(-50%); font-size: 0.72rem;
  color: #52514e; white-space: nowrap;
}
.meter-marker {
  position: absolute; top: -5px; width: 24px; height: 24px; margin-left: -12px; border-radius: 50%;
  background: #2a78d6; border: 3px solid #fcfcfb; box-shadow: 0 0 0 1px #1c5cab;
}
.hero.chance .meter-marker { background: #898781; box-shadow: 0 0 0 1px #52514e; }
.hero.disputed { border-left-color: #a8501b; }
.hero.disputed .meter-marker { background: #a8501b; box-shadow: 0 0 0 1px #7a3a14; }
.meter-labels { display: flex; justify-content: space-between; font-size: 0.8rem; color: #52514e; margin-top: 8px; }
.strip {
  background: #ffffff; border: 1px solid #e1e0d9; border-left: 6px solid #2a78d6; border-radius: 8px;
  padding: 8px 14px; margin: 2px 0 10px 0; font-size: 0.95rem; line-height: 1.9;
}
.strip .stamp { margin: 0 8px; font-size: 0.85rem; }
.strip a { white-space: nowrap; }
@keyframes slam {
  0% { transform: scale(2.2) rotate(-12deg); opacity: 0; }
  60% { transform: scale(0.94) rotate(-3deg); opacity: 1; }
  100% { transform: scale(1) rotate(-3deg); opacity: 1; }
}
.stamp.slam { animation: slam 0.45s ease-out 1; font-size: 1.1rem; }
@media (prefers-reduced-motion: reduce) { .stamp.slam { animation: none; } }
/* Phones: two clue cards per row instead of one long column */
@media (max-width: 640px) {
  div[data-testid="stHorizontalBlock"]:has(.clue-name) {
    flex-direction: row !important; flex-wrap: wrap !important; gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.clue-name) > div[data-testid="stColumn"] {
    flex: 1 1 calc(50% - 0.5rem) !important; width: calc(50% - 0.5rem) !important;
    min-width: calc(50% - 0.5rem) !important;
  }
  .clue-value { font-size: 1.15rem; }
  .clue-name { font-size: 0.72rem; }
}
</style>
"""


def file_stamp(path) -> tuple[int, int] | None:
    """When a data file last changed, and its size (None when it is missing): part of the cache keys."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


@st.cache_data(show_spinner=False)
def _load_monthly(region_key: str, variable_key: str, stamp: tuple | None) -> pd.DataFrame | None:
    return load_processed(region_key, variable_key)


def load_monthly(region_key: str, variable_key: str) -> pd.DataFrame | None:
    """A prepared monthly file, cached until the file on disk changes."""
    return _load_monthly(region_key, variable_key, file_stamp(processed_path(region_key, variable_key)))


def data_files() -> tuple:
    """Every cached data file with its change stamp. The caches below are keyed on it, so a NASA file
    that arrives or is refreshed while the app is running shows up at once, not after a restart."""
    return tuple(sorted((path.name, file_stamp(path)) for path in PROCESSED_DIR.glob("*.csv")))


@st.cache_data(show_spinner=False)
def game_page(lang: str, files: tuple) -> str:
    """The Detective exam page: every case and its answer, built from the cached data files."""
    return render_game_html(lang)


@st.cache_data(show_spinner=False)
def measured_somewhere(files: tuple) -> frozenset:
    """Measurements with a cached file in at least one prepared region (others are not shown)."""
    return frozenset(key for region_key in REGIONS for key in available_variable_keys(region_key))


@st.cache_data(show_spinner=False)
def world_board(files: tuple) -> dict:
    """Verdicts for every prepared region and measurement (full records), for the World board."""
    return world_cells(load_monthly)


@st.cache_data(show_spinner=False)
def bundle_bytes(files: tuple) -> bytes:
    """Open data: the ZIP of every prepared series with SOURCES.md (rebuilt when a data file changes)."""
    return data_bundle()


@st.cache_data(show_spinner=False)
def guide_suggestions(topic: str, place: str, files: tuple) -> list:
    """Guided start: the prepared cases for one what/where pair (recomputed when a data file changes)."""
    return suggest(topic, place, loader=load_monthly)


@st.cache_data(show_spinner=False)
def ranking_table(variable_key: str, files: tuple) -> pd.DataFrame:
    """How does this place compare: one measurement's full-record trend in every prepared region, ranked
    (recomputed when a data file changes)."""
    return region_ranking(variable_key, loader=load_monthly)


@st.cache_data(show_spinner=False, ttl=24 * 3600, max_entries=64)
def live_monthly(variable_key: str, bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Fetch a POWER variable live for any rectangle (cached for a day per rectangle).

    Any size works: ``fetch_power_area`` asks NASA POWER for 2-10 degree pieces and keeps the cells
    of the rectangle. Quick failures are retried a couple of times; a timeout is not, so a NASA
    POWER that hangs does not keep the page waiting several times.
    """
    variable = VARIABLES[variable_key]
    monthly, sources = fetch_power_area(variable, bbox, 1981, 2026, timeout=(10, 45))
    monthly = monthly.copy()
    monthly["source"] = f"{variable.product}; live NASA POWER request; POWER sources: {sources}"
    return monthly


GRID_CACHE = Path(os.environ.get("TREND_GRID_CACHE") or Path(tempfile.gettempdir()) / "trend_grid_cache")


@st.cache_data(show_spinner=False, ttl=24 * 3600, max_entries=16)
def grid_cells(variable_key: str, bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Monthly values of every NASA POWER grid cell in the area (kept on disk and for a day)."""
    cells, _ = fetch_cells(variable_key, bbox, cache_dir=GRID_CACHE, timeout=(10, 45))
    return cells


@st.cache_data(show_spinner=False, max_entries=32)
def _grid_trends(variable_key: str, bbox: tuple[float, float, float, float], start: int | None,
                 end: int | None, region_key: str | None = None) -> tuple[pd.DataFrame, int, tuple[float, float]]:
    # A prepared region reads its yearly cell values from data/processed/grid: no NASA POWER request and
    # no monthly-to-yearly step, about twice as fast; a drawn area still fetches its monthly cells.
    annual = load_annual_cells(region_key, variable_key) if region_key else None
    if annual is not None and len(annual):
        trends = cell_trends_from_annual(annual, variable_key, start, end)
        size = prepared_cell_size(annual)
    else:
        cells = grid_cells(variable_key, bbox)
        trends = cell_trends(cells, variable_key, start, end)
        size = cell_size(cells) if len(cells) else (0.5, 0.625)
    return trends, int(trends.attrs.get("no_snow_cells", 0)), size


def grid_trends(variable_key: str, bbox: tuple[float, float, float, float], start: int | None,
                end: int | None, region_key: str | None = None) -> tuple[pd.DataFrame, int, tuple[float, float]]:
    """The trend test for every grid cell, the number of cells without snow, and the cell size.

    A period that covers the whole record reuses the full-record result, so opening a case (which
    sets the period to the full record) does not test every cell a second time.
    """
    full = _grid_trends(variable_key, bbox, None, None, region_key)
    trends = full[0]
    if start is None or end is None or not len(trends):
        return full
    if start <= int(trends["start_year"].min()) and end >= int(trends["end_year"].max()):
        return full
    return _grid_trends(variable_key, bbox, start, end, region_key)


@st.cache_data(show_spinner=False, max_entries=24)
def time_layers_prepared(region_key: str, lang: str) -> list[dict]:
    """Yearly squares of every measurement prepared for a region (data/processed/grid)."""
    layers = []
    for key in LAYER_KEYS:
        annual = load_annual_cells(region_key, key)
        layer = layer_from_annual(annual, key, lang)
        if layer is not None:
            layer["cell"] = list(prepared_cell_size(annual))
            layers.append(layer)
    return layers


@st.cache_data(show_spinner=False, max_entries=16)
def time_layer_live(variable_key: str, bbox: tuple[float, float, float, float], lang: str) -> list[dict]:
    """Yearly squares of one measurement for a drawn area, from the live grid cells."""
    cells = grid_cells(variable_key, bbox)
    layer = layer_from_annual(annual_cells(cells, variable_key), variable_key, lang)
    if layer is None:
        return []
    layer["cell"] = list(cell_size(cells))
    return [layer]


def area_map(bbox: tuple[float, float, float, float], scene=None) -> folium.Map:
    """World map with the active rectangle, editable with the draw tools.

    ``scene`` is ``(trends, cell size, language, variable)`` for the crime scene layer: coloured grid
    cells with dots on real trends; the rectangle is then drawn as an outline only.
    """
    west, south, east, north = bbox
    fmap = folium.Map(
        location=[(south + north) / 2, (west + east) / 2], zoom_start=4, tiles="OpenStreetMap",
        control_scale=True,
    )
    if scene is not None:
        add_overlay(fmap, *scene)
    group = folium.FeatureGroup(name="area")
    folium.Rectangle(
        bounds=[[south, west], [north, east]], color="#2a78d6", weight=2, fill=True,
        fill_color="#2a78d6", fill_opacity=0.0 if scene is not None else 0.15,
    ).add_to(group)
    group.add_to(fmap)
    Draw(
        export=False, feature_group=group, position="topleft",
        draw_options={
            "rectangle": {"shapeOptions": {"color": "#2a78d6", "weight": 2}},
            "polyline": False, "polygon": False, "circle": False, "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": False},
    ).add_to(fmap)
    fmap.fit_bounds([[south, west], [north, east]], padding=(40, 40))
    return fmap


def set_custom_bbox(bbox: tuple[float, float, float, float]) -> None:
    st.session_state.update(
        {
            "custom_bbox": bbox, "area_mode": "custom", "area_error": None,
            "bbox_w": float(bbox[0]), "bbox_s": float(bbox[1]),
            "bbox_e": float(bbox[2]), "bbox_n": float(bbox[3]), "_custom_set": True,
        }
    )


def clear_area_error() -> None:
    st.session_state["area_error"] = None


LIVE_RETRY_SECONDS = 60  # a NASA POWER network error is not retried on reruns within this time


NEAREST_MAX_KM = 1500  # the nearest prepared region is offered only when it is this close


def offer_nearest_region(lang: str, bbox: tuple[float, float, float, float], key: str) -> None:
    """When NASA POWER does not answer for a custom area: a button to the nearest prepared region,
    which works from the files in the repository (no network needed)."""
    west, south, east, north = bbox
    region_key, km = nearest_region((south + north) / 2, (west + east) / 2)
    if km > NEAREST_MAX_KM:  # a region on another continent is no help
        return
    name = region_name(lang, region_key, REGIONS[region_key].name)
    st.info(t(lang, "nearest_offer", region=name, km=num(round(km, -1), lang, 0)))
    case = st.session_state.get("case")
    if case not in available_variable_keys(region_key):
        case = "air_temperature"
    st.button(
        t(lang, "nearest_open", region=SHORT_NAMES.get(lang, SHORT_NAMES["en"]).get(region_key, name)),
        key=key, on_click=open_world_case, args=(region_key, case),
    )


def forget_live_failures() -> None:
    """The Retry button: ask NASA POWER again for everything that failed."""
    st.session_state.pop("_live_fail", None)


def reset_periods() -> None:
    """A new place starts every case on its full record."""
    st.session_state["periods"] = {}
    for key in [k for k in st.session_state if str(k).startswith("period_")]:
        del st.session_state[key]


def on_region_change() -> None:
    clear_area_error()
    reset_periods()


def on_mode_change() -> None:
    """Entering custom mode: keep a rectangle the user made, otherwise start from the region on screen.

    The corner inputs are rewritten in both cases, because Streamlit forgets the values of inputs
    that were not on screen.
    """
    clear_area_error()
    reset_periods()
    if st.session_state.get("area_mode") != "custom":
        return
    if st.session_state.get("_custom_set"):
        set_custom_bbox(tuple(st.session_state["custom_bbox"]))
    else:
        region_key = st.session_state.get("region", next(iter(REGIONS)))
        set_custom_bbox(REGIONS[region_key].bbox)
        st.session_state["_custom_set"] = False  # seeded from a region, not made by the user


def apply_coords() -> None:
    try:
        bbox = normalize_bbox(
            st.session_state["bbox_w"], st.session_state["bbox_s"],
            st.session_state["bbox_e"], st.session_state["bbox_n"],
        )
    except AreaError as error:
        st.session_state["area_error"] = error.code
        return
    set_custom_bbox(bbox)


def pick_city() -> None:
    """Quick pick: a city (trend/cities.py) sets the rectangle to a 2° × 2° box centred on it."""
    city = CITY_BY_KEY.get(st.session_state.get("city_pick"))
    if city:
        set_custom_bbox(city_bbox(city))
        reset_periods()


def use_drawn() -> None:
    drawn = st.session_state.get("drawn_bbox")
    if not drawn:
        return
    try:
        bbox = normalize_bbox(*drawn)
    except AreaError as error:
        st.session_state["area_error"] = error.code
        return
    set_custom_bbox(bbox)


def stamp(lang: str, status: str, extra: str = "") -> str:
    classes = f"stamp {status} {extra}".strip()
    return f"<span class='{classes}' lang='{lang}'>{html.escape(status_text(lang, status)[0])}</span>"


def upper(text: str, lang: str) -> str:
    """Uppercase that keeps the Turkish dotted and dotless i correct."""
    if lang == "tr":
        text = text.replace("i", "İ").replace("ı", "I")
    return text.upper()


def chance_meter(p: float, lang: str, real: bool) -> str:
    """Marker on a log scale from p = 0.0001 (left) to p = 1 (right), with the 5% line."""
    def position(value: float) -> float:
        return (min(max(math.log10(max(value, 1e-12)), -4.0), 0.0) + 4.0) / 4.0 * 100

    threshold = position(0.05)
    return (
        "<div class='meter'><div class='meter-track'>"
        f"<div class='meter-zone' style='width:{threshold:.1f}%'></div>"
        f"<div class='meter-threshold' style='left:{threshold:.1f}%'>"
        f"<span>{html.escape(t(lang, 'meter_threshold'))}</span></div>"
        f"<div class='meter-marker' style='left:{position(p):.1f}%'></div>"
        "</div><div class='meter-labels'>"
        f"<span>{html.escape(t(lang, 'meter_left'))}</span>"
        f"<span>{html.escape(t(lang, 'meter_right'))}</span></div></div>"
    )


def axis_title(name: str, unit: str) -> str:
    """'Air temperature (°C)', but not 'Vegetation greenness (NDVI) (NDVI)'."""
    return name if unit.split(" (")[0] in name else f"{name} ({unit})"


def open_case(variable_key: str) -> None:
    st.session_state["case"] = variable_key
    st.session_state["_jump"] = True  # scroll to the case file after this click


def open_example(variable_key: str, start: int | None, end: int | None) -> None:
    st.session_state["case"] = variable_key
    st.session_state["_jump"] = True
    periods = st.session_state.setdefault("periods", {})
    if start is None:
        st.session_state.pop(f"period_{variable_key}", None)  # full record on the next run
        periods.pop(variable_key, None)
    else:
        st.session_state[f"period_{variable_key}"] = (start, end)
        periods[variable_key] = (start, end)


def open_world_case(region_key: str, variable_key: str) -> None:
    """From the World board: open this prepared region and measurement in the investigation view."""
    st.session_state["area_mode"] = "prepared"
    st.session_state["region"] = region_key
    st.session_state["case"] = variable_key
    reset_periods()  # a new place: full records
    st.session_state["view"] = "case"
    st.session_state["_jump"] = True


def open_famous_case(example) -> None:
    """Famous cases: open this prepared region, measurement and period in the investigation view."""
    open_world_case(example.region, example.case)  # prepared region, full record, investigation view
    if example.start is not None:
        open_example(example.case, example.start, example.end)  # the example's period


def show_world_board(lang: str) -> None:
    """Every prepared region and measurement at once, and the 'same clue, opposite trends' finds."""
    cells = world_board(data_files())
    names = {key: variable_text(lang, variable)["name"] for key, variable in VARIABLES.items()}
    short = SHORT_NAMES.get(lang, SHORT_NAMES["en"])
    st.markdown(WORLD_STYLE, unsafe_allow_html=True)
    st.subheader(world_text(lang, "title"))
    st.write(world_text(lang, "intro"))
    st.markdown(
        world_table_html(
            cells, lang,
            variable_name=lambda key: names[key],
            status_name=lambda status: status_text(lang, status)[0],
            unit_name=lambda key: variable_text(lang, VARIABLES[key])["annual_unit"],
            rate_text=lambda key, value: num(value, lang, VARIABLES[key].decimals, signed=True),
        ),
        unsafe_allow_html=True,
    )
    st.caption(world_text(lang, "legend"))
    counts = summary_counts(cells)
    st.write(world_text(
        lang, "counts", tested=counts["tested"], confirmed=counts["confirmed"],
        disputed=counts["disputed"], weak=counts["weak"], none=counts["noevidence"],
    ))
    st.info(world_text(lang, "chance_note", tested=counts["tested"], low=counts["low"], high=counts["high"]))

    st.markdown(f"<div class='step'>{html.escape(world_text(lang, 'opposite_title'))}</div>", unsafe_allow_html=True)
    st.caption(world_text(lang, "opposite_why"))
    found = opposite_trends(cells)
    if not found:
        st.write(world_text(lang, "opposite_none"))
    for item in found:
        joiner = " ve " if lang == "tr" else " and "
        up = joiner.join(place_name(lang, r) for r in item["up"])
        down = joiner.join(place_name(lang, r) for r in item["down"])
        st.markdown(world_text(lang, "opposite_line", variable=names[item["variable"]], up=up, down=down))
        buttons = [(r, item["variable"]) for r in item["up"][:2] + item["down"][:2]]
        for column, (region_key, variable_key) in zip(st.columns(4), buttons):
            column.button(
                world_text(lang, "open_case", region=short[region_key], variable=lower_first(names[variable_key])),
                key=f"world_open_{region_key}_{variable_key}", on_click=open_world_case,
                args=(region_key, variable_key), width="stretch",
            )

    # Open data: everything behind the board in one ZIP, so anyone can re-run the tests (trend/bundle.py)
    st.download_button(
        bundle_text(lang, "button"), bundle_bytes(data_files()), file_name="trend-detective-data.zip",
        mime="application/zip", help=bundle_text(lang, "help"), key="data_bundle_download",
    )


# --- Language, shared links and area state -------------------------------------------------------

if "_url_loaded" not in st.session_state:
    # Restore a shared link once per session: language, area, case and period.
    params = st.query_params
    requested = params.get("lang")
    st.session_state.setdefault("lang", requested if requested in LANGUAGES else "en")
    if params.get("region") in REGIONS:
        st.session_state["region"] = params.get("region")
    elif params.get("region") == "custom":
        try:
            shared_bbox = normalize_bbox(params.get("w"), params.get("s"), params.get("e"), params.get("n"))
            st.session_state["area_mode"] = "custom"
            st.session_state["custom_bbox"] = shared_bbox
            st.session_state["_custom_set"] = True
        except (AreaError, TypeError, ValueError):
            pass
    if params.get("case") in VARIABLES:
        st.session_state["case"] = params.get("case")
        st.session_state["_url_period"] = (params.get("case"), params.get("start"), params.get("end"))
        try:  # the crime scene map (Step 1) runs before Step 2 restores the period
            st.session_state["periods"] = {params.get("case"): (int(params.get("start")), int(params.get("end")))}
        except (TypeError, ValueError):
            pass
    if params.get("view") in ("exam", "world"):
        st.session_state["view"] = params.get("view")
    if params.get("map") in ("scene", "time"):
        st.session_state["map_layer"] = params.get("map")
    st.session_state["_url_loaded"] = True

default_region = next(iter(REGIONS))
st.session_state.setdefault("area_mode", "prepared")
st.session_state.setdefault("region", default_region)
# The region selectbox is only on screen in prepared mode; re-assigning its key keeps the choice
# while the user visits "Anywhere on Earth".
st.session_state["region"] = st.session_state["region"]
st.session_state.setdefault("custom_bbox", REGIONS[st.session_state["region"]].bbox)
for corner, value in zip(("bbox_w", "bbox_s", "bbox_e", "bbox_n"), st.session_state["custom_bbox"]):
    st.session_state.setdefault(corner, float(value))

st.markdown(STYLE, unsafe_allow_html=True)
head_left, head_right = st.columns([6, 1], vertical_alignment="center")
with head_right:
    st.segmented_control(
        "Language", options=list(LANGUAGES), format_func=lambda k: LANGUAGES[k], key="lang",
        label_visibility="collapsed", required=True,
    )
lang = st.session_state.get("lang") or "en"
separators = ",." if lang == "tr" else ".,"

with head_left:
    st.markdown(f"<div class='eyebrow' lang='{lang}'>{html.escape(t(lang, 'eyebrow'))}</div>", unsafe_allow_html=True)
st.title(t(lang, "title"))
st.caption(t(lang, "subtitle"))
with st.expander(t(lang, "why_title")):
    st.markdown(t(lang, "why_body"))

# --- View: the investigation or the Detective exam game (approved by Team Avni) -----------------

st.session_state.setdefault("view", "case")
view_labels = {
    "case": VIEW_LABELS[lang]["case"],
    "world": world_text(lang, "view_label"),
    "exam": VIEW_LABELS[lang]["exam"],
}
st.segmented_control(
    "View", options=list(view_labels), format_func=lambda key: view_labels[key],
    key="view", label_visibility="collapsed", required=True,
)
if st.session_state["view"] == "world":
    st.query_params.from_dict({"lang": lang, "view": "world"})
    show_world_board(lang)
    st.caption(t(lang, "footer"))
    st.stop()
if st.session_state["view"] == "exam":
    st.query_params.from_dict({"lang": lang, "view": "exam"})
    components.html(game_page(lang, data_files()), height=900, scrolling=True)
    st.caption(t(lang, "footer"))
    st.stop()

verdict_slot = st.container()  # filled with the current case's verdict once it is known

# Guided start (the challenge suggests what/where questions that lead to variables): two questions,
# then up to three prepared cases with their stamps (trend/guide.py, checked by tests/test_guide.py).
with st.expander(guide_text(lang, "title")):
    guide_topic = st.pills(
        guide_text(lang, "q_topic"), list(TOPICS), format_func=lambda key: topic_label(lang, key),
        key="guide_topic",
    )
    guide_place = st.pills(
        guide_text(lang, "q_place"), list(PLACES), format_func=lambda key: place_label(lang, key),
        key="guide_place",
    )
    if guide_topic and guide_place:
        guide_found = guide_suggestions(guide_topic, guide_place, data_files())
        if not guide_found:
            st.info(guide_text(lang, "none"))
        for suggestion in guide_found:
            text_column, button_column = st.columns([3, 1], vertical_alignment="center")
            text_column.markdown(suggestion_label(suggestion, lang))
            button_column.button(
                guide_text(lang, "open"), key=suggestion_key(suggestion), on_click=open_famous_case,
                args=(suggestion,), width="stretch",
            )
        if any(suggestion.status == "noevidence" for suggestion in guide_found):
            st.caption(guide_text(lang, "note"))

# Famous cases from around the world (the challenge asks for demonstration examples): one click
# opens a region, a measurement and a period (trend/examples.py, each checked by a test).
st.caption(examples_title(lang))
for row in range(0, len(EXAMPLES), 3):
    for column, example in zip(st.columns(3), EXAMPLES[row:row + 3]):
        column.button(
            example_label(example, lang), key=example_key(example), on_click=open_famous_case,
            args=(example,), width="stretch",
        )

# --- Left sidebar: choose the area -------------------------------------------------------------

with st.sidebar:
    st.header(t(lang, "sidebar_title"))
    st.radio(
        t(lang, "mode_label"), ["prepared", "custom"], key="area_mode", on_change=on_mode_change,
        format_func=lambda mode: t(lang, "mode_prepared" if mode == "prepared" else "mode_custom"),
    )
    if st.session_state["area_mode"] == "prepared":
        st.selectbox(
            t(lang, "region_label"), list(REGIONS), key="region", on_change=on_region_change,
            format_func=lambda key: region_name(lang, key, REGIONS[key].name),
        )
    else:
        st.caption(t(lang, "custom_help"))
        # Quick pick: a city (trend/cities.py). The list shows a city only while its box is the rectangle.
        on_city = city_for_bbox(st.session_state["custom_bbox"])
        st.session_state["city_pick"] = on_city.key if on_city else None
        st.selectbox(
            city_text(lang, "label"), city_options(lang), index=None, key="city_pick",
            format_func=lambda key: city_label(lang, key), placeholder=city_text(lang, "placeholder"),
            help=city_text(lang, "help"), on_change=pick_city,
        )
        st.markdown(f"**{t(lang, 'coords_title')}**")
        col_left, col_right = st.columns(2)
        col_left.number_input(t(lang, "west"), -180.0, 180.0, step=0.5, key="bbox_w")
        col_right.number_input(t(lang, "east"), -180.0, 180.0, step=0.5, key="bbox_e")
        col_left.number_input(t(lang, "south"), -90.0, 90.0, step=0.5, key="bbox_s")
        col_right.number_input(t(lang, "north"), -90.0, 90.0, step=0.5, key="bbox_n")
        st.button(t(lang, "apply_coords"), on_click=apply_coords, type="primary", width="stretch")
    if st.session_state.get("area_error"):
        st.error(t(lang, f"err_{st.session_state['area_error']}"))

# --- Step 1: where? (world map with a movable, resizable rectangle) -----------------------------

custom_mode = st.session_state["area_mode"] == "custom"
if custom_mode:
    active_bbox = tuple(st.session_state["custom_bbox"])
    near_city = city_for_bbox(active_bbox)  # a quick-pick box is named after its city
    region = custom_region(
        active_bbox,
        f"{near_label(lang, near_city)} ({format_bbox(active_bbox, lang)})" if near_city
        else t(lang, "custom_name", bbox=format_bbox(active_bbox, lang)),
    )
    region_key = "custom"
    region_label = region.name
else:
    near_city = None
    region_key = st.session_state["region"]
    region = REGIONS[region_key]
    region_label = region_name(lang, region_key, region.name)
    active_bbox = region.bbox

st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_where'))}</div>", unsafe_allow_html=True)
mtext = map_text(lang)
ttext = time_text(lang)
st.session_state.setdefault("map_layer", "area")
st.segmented_control(
    "Map layer", options=["area", "scene", "time"],
    format_func=lambda key: ttext["layer"] if key == "time" else mtext[f"layer_{key}"],
    key="map_layer", label_visibility="collapsed", required=True,
)
# Crime scene layer (idea chosen by Team Avni): a trend test for every grid cell of the area, for
# the clue picked below (air temperature when that clue has no NASA POWER grid).
scene = scene_summary = scene_reasons = scene_trends = None
scene_variable = scene_years = None
no_snow_cells = 0
if st.session_state["map_layer"] == "scene":
    picked = st.session_state.get("case")
    if not custom_mode and picked not in available_variable_keys(region_key):
        picked = None  # a clue left over from another place is not on screen here
    scene_variable = picked if picked in POWER_VARIABLES else "air_temperature"
    if picked and picked not in POWER_VARIABLES and picked in VARIABLES:
        st.info(mtext["fallback"].format(picked=variable_text(lang, VARIABLES[picked])["name"]))
    if max(active_bbox[2] - active_bbox[0], active_bbox[3] - active_bbox[1]) > MAX_MAP_SPAN:
        st.info(mtext["too_big"].format(max=num(MAX_MAP_SPAN, lang, 0)))
    else:
        chosen = st.session_state.get(f"period_{scene_variable}") or st.session_state.get("periods", {}).get(scene_variable)
        start_pick, end_pick = (int(chosen[0]), int(chosen[1])) if chosen else (None, None)
        scene_failures = st.session_state.setdefault("_live_fail", {})
        scene_fail_key = ("scene", scene_variable, active_bbox)
        scene_remembered = scene_failures.get(scene_fail_key)
        if scene_remembered and time.time() - scene_remembered[1] < LIVE_RETRY_SECONDS:
            st.warning(mtext["fetch_failed"])  # not asked again on every rerun (Retry clears it)
        else:
            try:
                with st.spinner(mtext["loading"]):
                    scene_trends, no_snow_cells, scene_size = grid_trends(
                        scene_variable, active_bbox, start_pick, end_pick, None if custom_mode else region_key)
            except (DataSourceError, requests.RequestException, ValueError, KeyError, TypeError, IndexError,
                    AttributeError) as error:
                LOG.warning("Crime scene map failed for %s %s: %r", scene_variable, active_bbox, error)
                scene_failures[scene_fail_key] = ("open", time.time())
                st.warning(mtext["fetch_failed"])
            else:
                scene_failures.pop(scene_fail_key, None)
                scene_trends = scene_trends.copy()
                scene_trends.attrs["no_snow_cells"] = no_snow_cells
                scene_summary = summarize(scene_trends, lang, scene_variable, active_bbox)
                scene_reasons = map_reasons(lang, scene_variable, scene_summary,
                                            None if custom_mode else region_key)
                if len(scene_trends):
                    scene = (scene_trends, scene_size, lang, scene_variable)
                    scene_years = (int(scene_trends["start_year"].min()), int(scene_trends["end_year"].max()))
if st.session_state["map_layer"] == "time":
    # Time travel map (idea chosen by Team Avni): zoom in and slide through the years.
    picked = st.session_state.get("case")
    if not custom_mode and picked not in available_variable_keys(region_key):
        picked = None
    time_layers: list[dict] = []
    if custom_mode:
        if max(active_bbox[2] - active_bbox[0], active_bbox[3] - active_bbox[1]) > MAX_MAP_SPAN:
            st.info(ttext["too_big"].format(max=num(MAX_MAP_SPAN, lang, 0)))
        else:
            live_key = picked if picked in POWER_VARIABLES else "air_temperature"
            time_failures = st.session_state.setdefault("_live_fail", {})
            time_fail_key = ("time", live_key, active_bbox)
            time_remembered = time_failures.get(time_fail_key)
            if time_remembered and time.time() - time_remembered[1] < LIVE_RETRY_SECONDS:
                st.warning(ttext["fetch_failed"])
            else:
                try:
                    with st.spinner(ttext["loading"]):
                        time_layers = time_layer_live(live_key, active_bbox, lang)
                except (DataSourceError, requests.RequestException, ValueError, KeyError, TypeError,
                        IndexError, AttributeError) as error:
                    LOG.warning("Time map failed for %s %s: %r", live_key, active_bbox, error)
                    time_failures[time_fail_key] = ("open", time.time())
                    st.warning(ttext["fetch_failed"])
                else:
                    time_failures.pop(time_fail_key, None)
            st.caption(ttext["custom_note"])
    else:
        with st.spinner(ttext["loading"]):
            time_layers = time_layers_prepared(region_key, lang)
    shown_keys = [layer["key"] for layer in time_layers]
    if picked in VARIABLES and time_layers and picked not in shown_keys:
        st.caption(ttext["fallback"].format(picked=variable_text(lang, VARIABLES[picked])["name"],
                                            shown=time_layers[0]["name"]))
    if not time_layers:
        st.caption(ttext["nothing"])
    time_payload = build_payload(time_layers, active_bbox, None if custom_mode else region_key, lang, picked,
                                 cell=(0.5, 0.625))
    components.html(render_timelapse_html(time_payload), height=720, scrolling=False)
    st.caption(ttext["honesty"])
    st.caption(ttext["gibs_ack"])
    map_state = None
else:
    st.caption(t(lang, "map_help"))
    map_state = st_folium(
        area_map(active_bbox, scene), height=460 if scene else 420, use_container_width=True,
        returned_objects=["last_active_drawing", "all_drawings"],
        key=f"area_map_{region_key}_{active_bbox}_{st.session_state['map_layer']}_{scene_variable}_{scene_years}",
    )
if scene_summary is not None and (scene_years or no_snow_cells):
    # The place's results under the map: what the cells show, where, and possible reasons.
    if scene_years:
        st.caption(mtext["showing"].format(
            variable=variable_text(lang, VARIABLES[scene_variable])["name"],
            start=scene_years[0], end=scene_years[1]))
        st.markdown(legend_html(scene_trends, lang, scene_variable), unsafe_allow_html=True)
        st.caption(mtext["dots"])
    st.subheader(("🔎 " if scene_summary["both"] else "") + scene_summary["headline"])
    for line in scene_summary["details"]:
        st.markdown(f"- {line}")
    if scene_summary.get("no_dot"):
        st.markdown(f"**{why_text(lang)['why_head']}**")
        st.markdown("\n".join(f"- {line}" for line in scene_summary["no_dot"]))
    if scene_years and scene_reasons["lines"]:
        with st.container(border=True):
            st.markdown(f"**{scene_reasons['title']}**")
            st.markdown("\n".join(f"- {line}" for line in scene_reasons["lines"]))
            if scene_reasons["context"]:
                st.markdown(f"**{mtext['context']}:** {scene_reasons['context']}")
            st.caption(scene_reasons["note"])
drawn_bbox = pick_drawn_bbox(map_state, active_bbox)
if drawn_bbox:
    try:
        normalize_bbox(*drawn_bbox)
    except AreaError as error:
        st.error(t(lang, f"err_{error.code}"))
    else:
        st.session_state["drawn_bbox"] = drawn_bbox
        st.button(
            t(lang, "use_drawn", bbox=format_bbox(drawn_bbox, lang)), on_click=use_drawn,
            type="primary", key="use_drawn",
        )
if custom_mode:
    if active_bbox[2] - active_bbox[0] < 1 or active_bbox[3] - active_bbox[1] < 1:
        st.info(t(lang, "note_small"))
    pieces = len(power_request_boxes(active_bbox))
    if pieces > 1:
        st.info(t(lang, "note_large", n=pieces))

# --- Collect the evidence: cached files for prepared regions, live NASA POWER for custom areas ---

monthly_by_key: dict[str, pd.DataFrame] = {}
unavailable_status: dict[str, str] = {}
fetch_failed = False
if custom_mode:
    no_data_messages: list[str] = []
    # Failed requests are not cached by st.cache_data. Remember them, so a slider move or a language
    # switch does not ask NASA POWER again: "no data" for the session, network errors for a minute.
    failures = st.session_state.setdefault("_live_fail", {})
    network_down = False
    with st.spinner(t(lang, "fetching")):
        for key in VARIABLES:
            if key not in POWER_VARIABLES:
                unavailable_status[key] = "prepared_only"
                continue
            if network_down:  # the server did not answer a moment ago: do not wait again
                unavailable_status[key] = "open"
                fetch_failed = True
                failures[(key, active_bbox)] = ("open", time.time())
                continue
            remembered = failures.get((key, active_bbox))
            if remembered and (remembered[0] == "no_data" or time.time() - remembered[1] < LIVE_RETRY_SECONDS):
                unavailable_status[key] = remembered[0]
                if remembered[0] == "no_data":
                    name = lower_first(variable_text(lang, VARIABLES[key])["name"])
                    no_data_messages.append(t(lang, "err_no_data", variable=name))
                else:
                    fetch_failed = True
                continue
            try:
                monthly_by_key[key] = live_monthly(key, active_bbox)
                failures.pop((key, active_bbox), None)
            except DataSourceError as error:
                unavailable_status[key] = "open"
                message = str(error).lower()
                if "fill" in message or "no grid cells" in message:
                    unavailable_status[key] = "no_data"
                    name = lower_first(variable_text(lang, VARIABLES[key])["name"])
                    no_data_messages.append(t(lang, "err_no_data", variable=name))
                else:
                    LOG.warning("Live fetch failed for %s %s: %r", key, active_bbox, error)
                    fetch_failed = True
                    status_code = getattr(error, "status", None)
                    network_down = status_code is None or status_code in TRANSIENT_STATUS
                failures[(key, active_bbox)] = (unavailable_status[key], time.time())
            except requests.RequestException as error:
                LOG.warning("Live fetch failed for %s %s: %r", key, active_bbox, error)
                unavailable_status[key] = "open"
                fetch_failed = True
                network_down = True
                failures[(key, active_bbox)] = ("open", time.time())
    for message in no_data_messages:
        st.warning(message)
    if fetch_failed and monthly_by_key:
        st.error(t(lang, "err_fetch"))
        st.button(t(lang, "retry"), key="retry_fetch_partial", on_click=forget_live_failures)
        offer_nearest_region(lang, active_bbox, "nearest_partial")
else:
    cached = set(available_variable_keys(region_key))
    for key in VARIABLES:
        if key in cached:
            monthly_by_key[key] = load_monthly(region_key, key)
        else:
            unavailable_status[key] = "open"

annual_by_key: dict[str, pd.DataFrame] = {}
incomplete_by_key: dict[str, list[int]] = {}
board_results: dict[str, TrendResult | None] = {}
for key in VARIABLES:
    if key not in monthly_by_key:
        board_results[key] = None
        continue
    verdict = board_verdict(monthly_by_key[key], key)  # the same rules as the World board
    board_results[key] = verdict.result
    if verdict.result is None:
        unavailable_status[key] = verdict.status
        continue
    annual_by_key[key], incomplete_by_key[key] = verdict.annual, verdict.incomplete

if not annual_by_key:
    if custom_mode and fetch_failed:
        st.error(t(lang, "fetch_failed_all"))
        st.button(t(lang, "retry"), key="retry_fetch", on_click=forget_live_failures)
        offer_nearest_region(lang, active_bbox, "nearest_all")
    else:
        st.warning(t(lang, "no_data_region"))
    st.stop()

available = [key for key in VARIABLES if key in annual_by_key]
if st.session_state.get("case") not in available:
    st.session_state["case"] = available[0]

# --- Step 2: what? -----------------------------------------------------------------------------

st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_what'))}</div>", unsafe_allow_html=True)
st.caption(t(lang, "step1_caption"))
BOARD_GROUPS = (
    ("group_climate", ("air_temperature", "precipitation", "snowfall", "hot_days")),
    ("group_air", ("no2", "co", "black_carbon", "aod")),
    ("group_carbon_green", ("co2", "ndvi", "groundwater", "tree_cover")),
)
board_cells = []
measured = measured_somewhere(data_files())
for group_key, group_variables in BOARD_GROUPS:
    keys = [k for k in group_variables if k in VARIABLES and k in measured]
    if not keys:
        continue
    st.markdown(
        f"<div class='eyebrow' lang='{lang}'>{html.escape(t(lang, group_key))}</div>",
        unsafe_allow_html=True,
    )
    board_cells.extend(zip(st.columns(4), keys))
listed = {k for _, ks in BOARD_GROUPS for k in ks}
extra = [k for k in VARIABLES if k not in listed and k in measured]  # measurements not in a group
if extra:
    board_cells.extend(zip(st.columns(4), extra))
for column, key in board_cells:
    variable = VARIABLES[key]
    texts = variable_text(lang, variable)
    result = board_results[key]
    status = case_status(result) if result is not None else unavailable_status.get(key, "open")
    selected = st.session_state["case"] == key
    with column.container(border=True):
        st.markdown(
            f"<div class='clue-name'>{html.escape(upper(texts['name'], lang))}</div>",
            unsafe_allow_html=True,
        )
        if result is not None:
            symbol = cell_symbol(Cell(region_key, key, status, result.slope_per_decade))
            arrow = f"{symbol} " if symbol not in ("", "–") else ""  # same marks as the World board
            rate_text = num(result.slope_per_decade, lang, variable.decimals, signed=True)
            st.markdown(
                f"<div class='clue-value'>{arrow}{rate_text}</div>"
                f"<div class='clue-unit'>{html.escape(texts['annual_unit'])} "
                f"{html.escape(t(lang, 'per_decade'))}<br>{result.start_year}–{result.end_year}</div>",
                unsafe_allow_html=True,
            )
            annual = annual_by_key[key]
            st.plotly_chart(
                sparkline_figure(annual, trend_line_band(annual["year"], annual["value"])),
                width="stretch", theme=None, key=f"spark_{key}",
                config={"staticPlot": True, "displayModeBar": False},
            )
        else:
            st.markdown(
                "<div class='clue-value'>—</div>"
                f"<div class='clue-unit'>{html.escape(status_text(lang, status)[1])}</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:64px'></div>", unsafe_allow_html=True)
        st.markdown(stamp(lang, status), unsafe_allow_html=True)
        st.button(
            t(lang, "selected") if selected else t(lang, "investigate"), key=f"open_{key}",
            on_click=open_case, args=(key,), disabled=key not in annual_by_key, width="stretch",
            type="primary" if selected else "secondary",
        )

# --- Case file -------------------------------------------------------------------------------

case_key = st.session_state["case"]
variable = VARIABLES[case_key]
texts = variable_text(lang, variable)
unit = texts["annual_unit"]
decimals = variable.decimals
subject = lower_first(texts["annual_label"])
annual_all = annual_by_key[case_key]
monthly = monthly_by_key[case_key]

st.divider()
st.markdown("<div id='case-file'></div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='eyebrow' lang='{lang}'>{html.escape(t(lang, 'case_label', region=region_label, variable=texts['name']))}</div>",
    unsafe_allow_html=True,
)
st.header(t(lang, "question", subject=subject, region=region_label))
st.write(t(lang, "question_body", name=texts["name"], definition=texts["definition"], subject=subject))
if st.session_state.pop("_jump", False):  # only after a click that opened a case
    # An instant jump (smooth scrolling stalls in background tabs); the counter makes every jump a new
    # element, so the script also runs after two clicks in a row.
    st.session_state["_jump_n"] = st.session_state.get("_jump_n", 0) + 1
    components.html(
        f"<script>/* jump {st.session_state['_jump_n']} */ try{{window.parent.document"
        ".getElementById('case-file').scrollIntoView({block:'start'})}catch(e){}</script>",
        height=0,
    )

# Step 2: choose the period
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_when'))}</div>", unsafe_allow_html=True)
first_year, last_year = int(annual_all["year"].min()), int(annual_all["year"].max())
period_key = f"period_{case_key}"
periods = st.session_state.setdefault("periods", {})
url_period = st.session_state.pop("_url_period", None)
if url_period is not None and url_period[0] == case_key:
    restored = parse_period(url_period[1], url_period[2], first_year, last_year)
    if restored is not None:
        st.session_state[period_key] = restored
saved = st.session_state.get(period_key) or periods.get(case_key)
st.session_state[period_key] = (
    parse_period(saved[0], saved[1], first_year, last_year) if saved else None
) or (first_year, last_year)
start_year, end_year = st.slider(
    t(lang, "period_label"), min_value=first_year, max_value=last_year, key=period_key,
)
periods[case_key] = (start_year, end_year)
state = {"lang": lang, "region": region_key, "case": case_key, "start": str(start_year), "end": str(end_year)}
for corner, value in zip(("w", "s", "e", "n"), active_bbox if custom_mode else ()):
    state[corner] = str(value)
if st.session_state.get("map_layer") in ("scene", "time"):
    state["map"] = st.session_state["map_layer"]
st.query_params.from_dict(state)
annual = annual_all[annual_all["year"].between(start_year, end_year)].reset_index(drop=True)
min_years = variable.min_years
if len(annual) < min_years:
    st.error(t(lang, "too_short", min=min_years, n=len(annual)))
    st.stop()
if min_years < MIN_YEARS:
    st.info(t(lang, "short_record_note", n=len(annual), usual=MIN_YEARS))

result = analyze_trend(annual["year"], annual["value"], min_years=min_years)
band = trend_line_band(annual["year"], annual["value"])
status = case_status(result)
rate = num(result.slope_per_decade, lang, decimals, signed=True)
line_note = line_check(annual["year"], annual["value"], result)  # shown under an undecided verdict
with verdict_slot:
    mark = cell_symbol(Cell(region_key, case_key, status, result.slope_per_decade))
    mark = f"{mark} " if mark not in ("", "–") else ""
    st.markdown(
        f"<div class='strip'><span class='eyebrow' lang='{lang}'>{html.escape(t(lang, 'strip_eyebrow'))}</span> · "
        f"<b>{html.escape(region_label)} · {html.escape(texts['name'])}</b> · {start_year}–{end_year}"
        f"{stamp(lang, status)}<b>{mark}{html.escape(rate)} {html.escape(unit)} "
        f"{html.escape(t(lang, 'per_decade'))}</b> · <a href='#case-file'>{html.escape(t(lang, 'strip_link'))}</a></div>",
        unsafe_allow_html=True,
    )

# Step 3: real or chance?
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_verdict'))}</div>", unsafe_allow_html=True)
if status == "disputed":
    headline, hero_class = t(lang, "headline_disputed"), "disputed"
elif result.significant:
    headline = t(lang, "headline_up" if result.slope_per_year > 0 else "headline_down")
    hero_class = "real"
else:
    headline, hero_class = t(lang, "headline_chance"), "chance"
st.markdown(
    f"<div class='hero {hero_class}'>"
    f"<div class='hero-title'>{html.escape(headline)}</div>"
    f"<div class='hero-q'>{html.escape(t(lang, 'meter_question'))} "
    f"<b>{html.escape(chance_phrase(result.p_value, lang))}</b> "
    f"({html.escape(p_phrase(result.p_value, lang))})</div>"
    f"{chance_meter(result.p_value, lang, result.significant)}</div>",
    unsafe_allow_html=True,
)
st.markdown(
    stamp(lang, status, "slam") + f"&nbsp; {html.escape(status_text(lang, status)[1])}",
    unsafe_allow_html=True,
)
tile_how, tile_total, tile_used = st.columns(3)
with tile_how.container(border=True):
    st.caption(t(lang, "how_much"))
    st.markdown(f"**{rate} {unit} {t(lang, 'per_decade')}**")
    low, high = ci_bounds(*result.ci_per_decade, lang, decimals)  # never a bare 0.00 at the edge
    st.caption(t(lang, "ci", low=low, high=high))
with tile_total.container(border=True):
    st.caption(t(lang, "total_change"))
    st.markdown(f"**{num(result.total_change, lang, decimals, signed=True)} {unit}**")
    st.caption(t(lang, "along_trend"))
with tile_used.container(border=True):
    st.caption(t(lang, "evidence_used"))
    st.markdown(f"**{t(lang, 'years_count', n=result.n_years)}**")
    st.caption(f"{result.start_year}–{result.end_year}")

if result.significant:
    st.markdown(
        t(
            lang, "verdict_sig", region=region_label, subject=subject,
            verb=t(lang, "verb_up" if result.slope_per_year > 0 else "verb_down"),
            rate=num(abs(result.slope_per_decade), lang, decimals), unit=unit,
            start=result.start_year, end=result.end_year,
            total=num(abs(result.total_change), lang, decimals),
            chance=chance_phrase(result.p_value, lang),
        )
    )
else:
    st.markdown(
        t(
            lang, "verdict_nosig", region=region_label, subject=subject, start=result.start_year,
            end=result.end_year, p=p_phrase(result.p_value, lang),
        )
    )
    # A steady change that is not a straight line can look like chance (trend/linecheck.py)
    if line_note.show:
        st.info(line_text(lang, p_phrase(line_note.plain_mk_p, lang), num(result.n_effective, lang, 0)))
if result.n_years < RECOMMENDED_YEARS:
    st.warning(t(lang, "warn_short", n=result.n_years, rec=RECOMMENDED_YEARS))
with st.expander(t(lang, "share_title")):
    st.caption(t(lang, "share_caption"))
    st.code(
        build_share_link(
            lang, region_key, case_key, start_year, end_year,
            bbox=active_bbox if custom_mode else None,
        ),
        language=None,
    )

# Step 4: the evidence
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_evidence'))}</div>", unsafe_allow_html=True)
st.plotly_chart(
    annual_trend_figure(
        annual, band,
        series_name=texts["annual_label"],
        trend_name=t(lang, "trend_name", rate=f"{rate} {unit} {t(lang, 'per_decade')}"),
        band_name=t(lang, "band_name"),
        x_title=texts["year_axis_label"],
        y_title=axis_title(texts["name"], unit),
        unit=unit,
        separators=separators,
        decimals=decimals,
    ),
    width="stretch", theme=None, config={"displaylogo": False}, key="evidence_chart",
)
dropped = [y for y in incomplete_by_key[case_key] if start_year - 1 <= y <= end_year + 1]
basis = t(lang, "based_on", n=result.n_years, start=result.start_year, end=result.end_year)
if dropped:
    basis += t(lang, "not_used", years=", ".join(str(y) for y in dropped))
if result.n_effective < 0.9 * result.n_years:
    basis += t(lang, "neff_note", n=result.n_years, n_eff=num(result.n_effective, lang, 0))
st.caption(basis)

# Every year as one stripe, and whether the last year is among the highest or lowest (trend/records.py)
st.plotly_chart(
    stripes_figure(annual, case_key, unit, separators, decimals), width="stretch", theme=None,
    config={"displaylogo": False, "displayModeBar": False}, key="stripes_chart",
)
st.caption(stripes_caption(lang, case_key, annual))
record = record_sentence(lang, last_year_rank(annual), case_key)
if record:
    st.markdown(record)
    st.caption(record_text(lang)["note"])

# How the evidence built up, and whether the verdict depends on the start year (trend/timeline.py)
timeline = evidence_timeline(annual, min_years)
if len(timeline) >= 3:
    st.markdown(f"**{timeline_text(lang, 'title')}**")
    st.caption(timeline_text(lang, "intro"))
    st.plotly_chart(
        timeline_figure(timeline, lang, result.start_year, separators),
        width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": False},
        key="timeline_chart",
    )
    since = solid_since(timeline)
    earlier = earlier_significant_years(timeline)
    if since is not None and since == int(timeline["end_year"].iloc[-1]):
        st.markdown(timeline_text(lang, "solid_last", year=since))  # nothing has confirmed it since
    elif since is not None:
        direction = timeline_text(lang, "up" if result.slope_per_year > 0 else "down")
        st.markdown(timeline_text(lang, "solid_since", year=since, direction=direction))
    elif earlier:
        st.markdown(timeline_text(lang, "flipped", years=year_ranges(earlier)))
    else:
        # "A longer record may help" would contradict the straight-line note's "try a shorter period"
        st.markdown(timeline_text(lang, "not_solid_curved" if line_note.show else "not_solid"))
    check = start_year_check(annual, min_years)
    if check:
        st.markdown(timeline_text(
            lang, "robust", n=check["n"], first=check["first"], last=check["last"], min=min_years,
            k=check["same"], status=status_text(lang, check["status"])[0],
        ))

# Replay the investigation: the verdict as years are added (trend/replay.py)
replay_table = growing_record(annual, min_years)
if len(replay_table) >= 2:
    with st.expander(replay_title(lang)):
        st.caption(replay_text(lang, "intro"))
        st.plotly_chart(
            replay_figure(
                annual, replay_table, lang,
                x_title=texts["year_axis_label"], y_title=axis_title(texts["name"], unit),
                unit=unit, separators=separators, decimals=decimals,
            ),
            width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": False},
            key="replay_chart",
        )
        st.markdown(replay_sentence(lang, replay_summary(replay_table)))

# Which season is changing? The same test for each three-month season (trend/seasonal.py)
if case_key in seasonal.SUPPORTED:
    with st.expander(seasonal.section_text(lang, "title")):
        season_table = seasonal.season_trends(monthly, case_key, start_year, end_year)
        season_latitude = region.center[0]
        st.caption(seasonal.section_text(lang, "intro"))
        st.plotly_chart(
            seasonal.season_figure(season_table, lang, season_latitude, unit, separators, decimals),
            width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": False},
            key="seasonal_chart",
        )
        st.caption(seasonal.figure_note(lang, case_key))
        st.markdown(seasonal.season_sentence(lang, season_table, case_key, season_latitude, unit))

# How does this place compare? The same measurement in every prepared region, each over its full record
# (trend/compare.py). Prepared regions only: a custom area has no ranking of its own.
if not custom_mode:
    with st.expander(compare_text(lang, "title")):
        ranking = ranking_table(case_key, data_files())
        short_names = SHORT_NAMES.get(lang, SHORT_NAMES["en"])
        st.caption(compare_text(lang, "intro"))
        if len(ranking) >= 2:
            st.plotly_chart(
                ranking_figure(ranking, lang, region_key, short_names, unit, separators, decimals),
                width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": False},
                key="ranking_chart",
            )
            st.caption(compare_text(lang, "note"))
        st.markdown(ranking_sentence(lang, ranking, region_key, short_names, unit, decimals))
        not_ranked = untested_text(lang, ranking, short_names)
        if not_ranked:
            st.caption(not_ranked)

# Step 5: the second witness
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_witness'))}</div>", unsafe_allow_html=True)
found = t(lang, {"increasing": "found_increasing", "decreasing": "found_decreasing"}.get(
    result.mk_trend, "found_none"))
st.markdown(
    t(
        lang, "witness_agrees" if result.agrees else "witness_disagrees",
        method=method_name(lang, result.mk_method), found=found, p=p_phrase(result.mk_p_value, lang),
        sen=num(result.sen_slope_per_decade, lang, decimals, signed=True), unit=unit,
    )
)
if result.end_year == last_year and result.n_years - 1 >= min_years:
    without_last = analyze_trend(annual["year"].iloc[:-1], annual["value"].iloc[:-1], min_years=min_years)
    st.caption(
        t(
            lang, "cross_exam", year=last_year,
            rate=num(without_last.slope_per_decade, lang, decimals, signed=True), unit=unit,
            p=p_phrase(without_last.p_value, lang),
            sig=t(lang, "significant" if without_last.significant else "not_significant"),
        )
    )

# Verification (asked for by Team Avni): an independent NASA dataset as a third witness, and the
# reasons why a result is not verified.
vtext = verify_text(lang)
witness_monthly = None if custom_mode else load_witness(region_key, case_key)
comparison = None
if witness_monthly is not None:
    comparison = compare_witness(result, witness_monthly, lang, case_key, result.start_year, result.end_year,
                                 main_annual=annual, region_key=region_key)
if comparison is not None:
    st.markdown(f"<div class='step'>{html.escape(comparison['title'])}</div>", unsafe_allow_html=True)
    st.caption(f"{comparison['intro']} {comparison['kind']}")
    if comparison["overlap"]:
        st.caption(comparison["overlap"])
    st.markdown(comparison["lines"][0])
    extra = extra_check_line(region_key, case_key, lang, result.start_year, result.end_year)
    st.markdown("\n".join(f"- {line}" for line in comparison["lines"][1:] + ([extra] if extra else [])))
else:
    st.caption(f"🧾 {no_witness_reason(lang, case_key, custom_mode, incomplete=witness_monthly is not None)}")
not_verified = why_not_confirmed(annual, result, status, lang, case_key,
                                 witness_verdict=comparison["verdict"] if comparison else None)
if not_verified:
    with st.container(border=True):
        st.markdown(f"**{vtext['why_title']}**")
        st.markdown("\n".join(f"- {line}" for line in not_verified))

# Step 7: possible reasons (the test shows that something changed, not why)
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_reasons'))}</div>", unsafe_allow_html=True)
direction = ("up" if result.slope_per_year > 0 else "down") if result.significant else "none"
if status == "disputed":
    intro = "reasons_intro_disputed"
elif direction != "none":
    intro = "reasons_intro_change"
else:
    intro = "reasons_intro_none"
st.markdown(t(lang, intro, subject=subject))
reason_lines = list(reasons(lang, case_key, direction))
if case_key == "no2" and direction == "down" and result.start_year <= 2020 <= result.end_year:
    reason_lines.append(t(lang, "reason_covid"))  # only when the period includes 2020
st.markdown("\n".join(f"- {line}" for line in reason_lines))
context = region_context(lang, region_key, case_key)
if context:
    st.info(f"**{t(lang, 'local_context')}:** {context}", icon="🔎")

# Case notes
st.markdown(f"<div class='step'>{html.escape(t(lang, 'case_notes'))}</div>", unsafe_allow_html=True)
if texts["caveats"]:
    with st.expander(t(lang, "keep_in_mind")):
        st.markdown("\n".join(f"- {c}" for c in texts["caveats"]))

# Monthly values with the seasonal cycle, or with it removed (trend/seasons.py)
with st.expander(season_text(lang, "title")):
    in_period = months_in_period(monthly, start_year, end_year, variable.year_starts_month)
    swing = seasonal_swing(in_period)
    season_view = "with"
    if swing > 0:  # a yearly product (one value per year) has no seasons to remove
        season_view = st.segmented_control(
            season_text(lang, "title"), options=["with", "removed"], default="with", required=True,
            format_func=lambda key: season_text(lang, "option_with" if key == "with" else "option_removed"),
            key="season_view", label_visibility="collapsed",
        )
    if season_view == "removed":
        st.caption(season_text(lang, "caption"))
        st.plotly_chart(
            anomaly_figure(
                deseasonalize(in_period), lang, x_title=t(lang, "month_axis"),
                y_title=season_text(lang, "y_title", unit=texts["unit"].split(" (")[0]),
                unit=texts["unit"], separators=separators, decimals=decimals,
            ),
            width="stretch", theme=None, config={"displaylogo": False}, key="anomaly_chart",
        )
        # A unit that can follow a number ("mm su", not "ayda mm su"; "AOD", not "AOD (birimsiz)")
        season_unit = texts["annual_unit"] if variable.aggregation == "sum" else texts["unit"].split(" (")[0]
        sentence = season_sentence(
            lang, swing, monthly_rate_per_decade(result.slope_per_decade, variable), season_unit, decimals,
        )
        if sentence:
            st.markdown(sentence)
    else:
        st.caption(t(lang, "monthly_caption"))
        st.plotly_chart(
            monthly_figure(
                in_period, x_title=t(lang, "month_axis"), y_title=axis_title(texts["name"], texts["unit"]),
                unit=texts["unit"], separators=separators, decimals=decimals,
            ),
            width="stretch", theme=None, config={"displaylogo": False}, key="monthly_chart",
        )

with st.expander(t(lang, "table_title")):
    table = annual.rename(
        columns={
            "year": texts["year_axis_label"].split(" (")[0],
            "value": f"{texts['annual_label']} ({unit})",
            "n_months": t(lang, "months_used"),
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")
    if "source" in monthly.columns:
        st.caption(t(lang, "source_recorded", source=monthly["source"].iloc[0]))
    results_row = {
        "region": t("en", "custom_name", bbox=format_bbox(active_bbox)) if custom_mode else region.name,
        "west": active_bbox[0],
        "south": active_bbox[1],
        "east": active_bbox[2],
        "north": active_bbox[3],
        "variable": variable.name,
        "unit": variable.annual_unit,
        "start_year": result.start_year,
        "end_year": result.end_year,
        "n_years": result.n_years,
        "effective_sample_size": round(result.n_effective, 1),
        "ols_slope_per_decade": result.slope_per_decade,
        "ci95_low_per_decade": result.ci_per_decade[0],
        "ci95_high_per_decade": result.ci_per_decade[1],
        "ols_p_value": result.p_value,
        "significant_at_0.05": result.significant,
        "total_change_along_trend": result.total_change,
        "robustness_test": result.mk_method,
        "robustness_trend": result.mk_trend,
        "robustness_p_value": result.mk_p_value,
        "sen_slope_per_decade": result.sen_slope_per_decade,
        "lag1_autocorrelation": result.lag1_autocorrelation,
        "verdict": status_text("en", status)[0],
    }
    file_stem = (
        "custom_" + "_".join(f"{v:g}" for v in active_bbox) if custom_mode else region_key
    ) + f"_{case_key}"
    col_a, col_b = st.columns(2)
    col_a.download_button(
        t(lang, "dl_annual"), annual.to_csv(index=False).encode("utf-8"),
        file_name=f"{file_stem}_annual.csv", mime="text/csv",
    )
    col_b.download_button(
        t(lang, "dl_results"), pd.DataFrame([results_row]).to_csv(index=False).encode("utf-8"),
        file_name=f"{file_stem}_case_results.csv", mime="text/csv",
    )

# Downloadable case report: verdict, chart, witness, reasons and sources on one printable page (trend/report.py)
report_area = "custom_" + "_".join(f"{v:g}" for v in active_bbox) if custom_mode else region_key
report_caveats = list(texts["caveats"])
if line_note.show:  # the "not a straight line" note explains a No evidence stamp on a clearly one-way chart
    report_caveats.insert(0, line_text(lang, p_phrase(line_note.plain_mk_p, lang), num(result.n_effective, lang, 0)))
st.download_button(
    report_text(lang, "button"),
    case_report_html(
        lang,
        region_label=region_label,
        variable_name=texts["name"],
        definition=texts["definition"],
        annual_label=texts["annual_label"],
        unit=unit,
        start_year=start_year,
        end_year=end_year,
        result=result,
        status=status,
        stamp_text=status_text(lang, status)[0],
        chance_text=chance_phrase(result.p_value, lang),
        p_text=p_phrase(result.p_value, lang),
        witness_text=t(
            lang, "witness_agrees" if result.agrees else "witness_disagrees",
            method=method_name(lang, result.mk_method), found=found, p=p_phrase(result.mk_p_value, lang),
            sen=num(result.sen_slope_per_decade, lang, decimals, signed=True), unit=unit,
        ),
        reasons=reason_lines + ([f"**{t(lang, 'local_context')}:** {context}"] if context else []),
        caveats=report_caveats,
        source=f"{variable.product}, {variable.provider}",
        citation=variable.citation,
        doi=variable.doi,
        share_link=build_share_link(
            lang, region_key, case_key, start_year, end_year, bbox=active_bbox if custom_mode else None,
        ),
        years=annual["year"].tolist(),
        values=annual["value"].tolist(),
        decimals=decimals,
    ).encode("utf-8"),
    file_name=report_filename(report_area, case_key, start_year, end_year),
    mime="text/html",
    help=report_text(lang, "button_help"),
    key="case_report_download",
)

# Can chance fool the detective? Pretend worlds with no trend, as long and as persistent as this record,
# tested by a naive test and by the detective (trend/chance.py). Run only on a click, kept for this case.
with st.expander(chance_text(lang, "title")):
    chance_n, chance_phi = int(result.n_years), float(result.lag1_autocorrelation)
    chance_case = (region_key, tuple(active_bbox), case_key, chance_n, round(clip_phi(chance_phi), 2))
    st.caption(intro_line(lang, DEFAULT_RUNS, chance_n, chance_phi))
    if st.button(chance_text(lang, "button", runs=DEFAULT_RUNS), key="chance_run"):
        with st.spinner(chance_text(lang, "running", runs=DEFAULT_RUNS)):
            st.session_state["chance_result"] = (chance_case, simulate(chance_n, chance_phi))
    chance_stored = st.session_state.get("chance_result")
    if chance_stored and chance_stored[0] == chance_case:  # a result made for another case is not shown
        chance_outcome = chance_stored[1]
        st.markdown("  \n".join(summary_lines(lang, chance_outcome, result.p_value)))
        if chance_outcome.get("example"):
            st.plotly_chart(
                example_figure(chance_outcome["example"], lang, separators), width="stretch", theme=None,
                config={"displaylogo": False, "displayModeBar": False}, key="chance_chart",
            )
        else:
            st.caption(chance_text(lang, "no_example"))
        st.caption(chance_text(lang, "note"))

with st.expander(t(lang, "methods_title")):
    st.markdown(METHODS[lang].format(region=region_label, min_years=MIN_YEARS))

st.divider()
doi = f" DOI: [{variable.doi}](https://doi.org/{variable.doi})." if variable.doi else ""
st.caption(f"**{t(lang, 'data_label')}:** {variable.product}, {variable.provider}. {variable.citation}{doi}")
st.caption(t(lang, "footer"))
