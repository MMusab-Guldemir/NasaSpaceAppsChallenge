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

import pandas as pd
import streamlit as st

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
from trend.charts import annual_trend_figure, monthly_figure, sparkline_figure
from trend.fetch import (
    POWER_VARIABLES,
    DataSourceError,
    available_variable_keys,
    fetch_power_area,
    load_processed,
)
from trend.i18n import (
    LANGUAGES,
    METHODS,
    chance_phrase,
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
from trend.regions import REGIONS, Region
from trend.share import build_share_link, parse_period
from trend.stats import MIN_YEARS, RECOMMENDED_YEARS, TrendResult, analyze_trend, to_annual, trend_line_band
from trend.variables import VARIABLES

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
.stamp.open, .stamp.prepared_only, .stamp.insufficient, .stamp.no_snow, .stamp.no_data {
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
</style>
"""


@st.cache_data(show_spinner=False)
def load_monthly(region_key: str, variable_key: str) -> pd.DataFrame | None:
    return load_processed(region_key, variable_key)


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


def area_map(bbox: tuple[float, float, float, float]) -> folium.Map:
    """World map with the active rectangle, editable with the draw tools."""
    west, south, east, north = bbox
    fmap = folium.Map(
        location=[(south + north) / 2, (west + east) / 2], zoom_start=4, tiles="OpenStreetMap",
        control_scale=True,
    )
    group = folium.FeatureGroup(name="area")
    folium.Rectangle(
        bounds=[[south, west], [north, east]], color="#2a78d6", weight=2, fill=True,
        fill_color="#2a78d6", fill_opacity=0.15,
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


def on_mode_change() -> None:
    """Entering custom mode: keep a rectangle the user made, otherwise start from the region on screen.

    The corner inputs are rewritten in both cases, because Streamlit forgets the values of inputs
    that were not on screen.
    """
    clear_area_error()
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


def case_status(result: TrendResult | None) -> str:
    if result is None:
        return "open"
    if result.significant:
        return "confirmed" if result.agrees else "disputed"
    return "noevidence" if result.agrees else "weak"


def stamp(lang: str, status: str) -> str:
    return f"<span class='stamp {status}' lang='{lang}'>{html.escape(status_text(lang, status)[0])}</span>"


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


# Demonstration cases suggested by the challenge statement: one click opens a case and period.
EXAMPLE_CASES = [
    {"region": "colorado", "case": "air_temperature", "start": None, "end": None,
     "label": {"en": "🔎 Is Colorado warming?", "tr": "🔎 Colorado ısınıyor mu?"}},
    {"region": "colorado", "case": "no2", "start": 2005, "end": 2019,
     "label": {"en": "🔎 Did NO₂ fall before 2020?", "tr": "🔎 NO₂ 2020'den önce düştü mü?"}},
    {"region": "colorado", "case": "snowfall", "start": None, "end": None,
     "label": {"en": "🔎 Is snowfall changing?", "tr": "🔎 Kar yağışı değişiyor mu?"}},
]


def open_example(variable_key: str, start: int | None, end: int | None) -> None:
    st.session_state["case"] = variable_key
    periods = st.session_state.setdefault("periods", {})
    if start is None:
        st.session_state.pop(f"period_{variable_key}", None)  # full record on the next run
        periods.pop(variable_key, None)
    else:
        st.session_state[f"period_{variable_key}"] = (start, end)
        periods[variable_key] = (start, end)


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

# --- Left sidebar: choose the area -------------------------------------------------------------

with st.sidebar:
    st.header(t(lang, "sidebar_title"))
    st.radio(
        t(lang, "mode_label"), ["prepared", "custom"], key="area_mode", on_change=on_mode_change,
        format_func=lambda mode: t(lang, "mode_prepared" if mode == "prepared" else "mode_custom"),
    )
    if st.session_state["area_mode"] == "prepared":
        st.selectbox(
            t(lang, "region_label"), list(REGIONS), key="region", on_change=clear_area_error,
            format_func=lambda key: region_name(lang, key, REGIONS[key].name),
        )
    else:
        st.caption(t(lang, "custom_help"))
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
    region = custom_region(active_bbox, t(lang, "custom_name", bbox=format_bbox(active_bbox, lang)))
    region_key = "custom"
    region_label = region.name
else:
    region_key = st.session_state["region"]
    region = REGIONS[region_key]
    region_label = region_name(lang, region_key, region.name)
    active_bbox = region.bbox

st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_where'))}</div>", unsafe_allow_html=True)
st.caption(t(lang, "map_help"))
map_state = st_folium(
    area_map(active_bbox), height=420, use_container_width=True,
    returned_objects=["last_active_drawing", "all_drawings"],
    key=f"area_map_{region_key}_{active_bbox}",
)
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
    with st.spinner(t(lang, "fetching")):
        for key in VARIABLES:
            if key not in POWER_VARIABLES:
                unavailable_status[key] = "prepared_only"
                continue
            try:
                monthly_by_key[key] = live_monthly(key, active_bbox)
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
            except requests.RequestException as error:
                LOG.warning("Live fetch failed for %s %s: %r", key, active_bbox, error)
                unavailable_status[key] = "open"
                fetch_failed = True
    for message in no_data_messages:
        st.warning(message)
    if fetch_failed and monthly_by_key:
        st.error(t(lang, "err_fetch"))
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
for key, variable in VARIABLES.items():
    if key not in monthly_by_key:
        board_results[key] = None
        continue
    annual, incomplete = to_annual(monthly_by_key[key], variable)
    if key == "snowfall" and len(annual) and annual["value"].max() < 1.0:
        board_results[key] = None
        unavailable_status[key] = "no_snow"
        continue
    if len(annual) < MIN_YEARS:
        board_results[key] = None
        unavailable_status[key] = "insufficient"
        continue
    annual_by_key[key], incomplete_by_key[key] = annual, incomplete
    board_results[key] = analyze_trend(annual["year"], annual["value"])

if not annual_by_key:
    if custom_mode and fetch_failed:
        st.error(t(lang, "fetch_failed_all"))
        st.button(t(lang, "retry"), key="retry_fetch")  # any click reruns; failures are not cached
    else:
        st.warning(t(lang, "no_data_region"))
    st.stop()

available = [key for key in VARIABLES if key in annual_by_key]
if st.session_state.get("case") not in available:
    st.session_state["case"] = available[0]

# --- Step 2: what? -----------------------------------------------------------------------------

st.markdown(f"<div class='step'>{html.escape(t(lang, 'step_what'))}</div>", unsafe_allow_html=True)
examples = [
    example for example in EXAMPLE_CASES
    if example["region"] == region_key and example["case"] in annual_by_key
]
if examples:
    st.caption(t(lang, "examples_title"))
    for column, example in zip(st.columns(4), examples):
        column.button(
            example["label"][lang], key=f"example_{example['case']}", on_click=open_example,
            args=(example["case"], example["start"], example["end"]), width="stretch",
        )
st.caption(t(lang, "step1_caption"))
for column, (key, variable) in zip(st.columns(len(VARIABLES)), VARIABLES.items()):
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
            arrow = ""
            if result.significant and result.slope_per_year != 0:
                arrow = "▲ " if result.slope_per_year > 0 else "▼ "
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
st.markdown(
    f"<div class='eyebrow' lang='{lang}'>{html.escape(t(lang, 'case_label', region=region_label, variable=texts['name']))}</div>",
    unsafe_allow_html=True,
)
st.header(t(lang, "question", subject=subject, region=region_label))
st.write(t(lang, "question_body", name=texts["name"], definition=texts["definition"], subject=subject))

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
st.query_params.from_dict(state)
annual = annual_all[annual_all["year"].between(start_year, end_year)].reset_index(drop=True)
if len(annual) < MIN_YEARS:
    st.error(t(lang, "too_short", min=MIN_YEARS, n=len(annual)))
    st.stop()

result = analyze_trend(annual["year"], annual["value"])
band = trend_line_band(annual["year"], annual["value"])
status = case_status(result)
rate = num(result.slope_per_decade, lang, decimals, signed=True)

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
    stamp(lang, status) + f"&nbsp; {html.escape(status_text(lang, status)[1])}",
    unsafe_allow_html=True,
)
tile_how, tile_total, tile_used = st.columns(3)
with tile_how.container(border=True):
    st.caption(t(lang, "how_much"))
    st.markdown(f"**{rate} {unit} {t(lang, 'per_decade')}**")
    low, high = result.ci_per_decade
    st.caption(
        t(lang, "ci", low=num(low, lang, decimals, signed=True), high=num(high, lang, decimals, signed=True))
    )
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
if result.end_year == last_year and result.n_years - 1 >= MIN_YEARS:
    without_last = analyze_trend(annual["year"].iloc[:-1], annual["value"].iloc[:-1])
    st.caption(
        t(
            lang, "cross_exam", year=last_year,
            rate=num(without_last.slope_per_decade, lang, decimals, signed=True), unit=unit,
            p=p_phrase(without_last.p_value, lang),
            sig=t(lang, "significant" if without_last.significant else "not_significant"),
        )
    )

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

with st.expander(t(lang, "monthly_title")):
    st.caption(t(lang, "monthly_caption"))
    in_period = monthly[monthly["date"].dt.year.between(start_year - 1, end_year)]
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

with st.expander(t(lang, "methods_title")):
    st.markdown(METHODS[lang].format(region=region_label, min_years=MIN_YEARS))

st.divider()
doi = f" DOI: [{variable.doi}](https://doi.org/{variable.doi})." if variable.doi else ""
st.caption(f"**{t(lang, 'data_label')}:** {variable.product}, {variable.provider}. {variable.citation}{doi}")
st.caption(t(lang, "footer"))
