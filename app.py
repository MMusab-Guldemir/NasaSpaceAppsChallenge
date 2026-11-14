"""Earth System Trend Detective: Streamlit app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea, the "expert detective" theme, the pick-then-verdict flow
and the Turkish option come from Team Avni; the board-and-case-file layout was suggested by the AI and
approved by the team.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from trend.charts import annual_trend_figure, monthly_figure, sparkline_figure
from trend.fetch import available_variable_keys, load_processed
from trend.i18n import (
    LANGUAGES,
    METHODS,
    chance_phrase,
    lower_first,
    num,
    p_phrase,
    region_name,
    status_text,
    t,
    variable_text,
)
from trend.regions import REGIONS
from trend.stats import MIN_YEARS, RECOMMENDED_YEARS, TrendResult, analyze_trend, to_annual, trend_line_band
from trend.variables import VARIABLES

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🔎", layout="wide")

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
.stamp.open { color: #898781; border-style: dashed; }
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
.meter-labels { display: flex; justify-content: space-between; font-size: 0.8rem; color: #52514e; margin-top: 8px; }
</style>
"""


@st.cache_data(show_spinner=False)
def load_monthly(region_key: str, variable_key: str) -> pd.DataFrame | None:
    return load_processed(region_key, variable_key)


def case_status(result: TrendResult | None) -> str:
    if result is None:
        return "open"
    if result.significant:
        return "confirmed" if result.agrees else "disputed"
    return "noevidence" if result.agrees else "weak"


def stamp(lang: str, status: str) -> str:
    return f"<span class='stamp {status}'>{html.escape(status_text(lang, status)[0])}</span>"


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


def open_case(variable_key: str) -> None:
    st.session_state["case"] = variable_key


# --- Language (top right) and header -------------------------------------------------------------

if "lang" not in st.session_state:
    requested = st.query_params.get("lang")
    st.session_state["lang"] = requested if requested in LANGUAGES else "en"

st.markdown(STYLE, unsafe_allow_html=True)
head_left, head_right = st.columns([6, 1], vertical_alignment="center")
with head_right:
    st.segmented_control(
        "Language", options=list(LANGUAGES), format_func=lambda k: LANGUAGES[k], key="lang",
        label_visibility="collapsed",
    )
lang = st.session_state.get("lang") or "en"
st.query_params["lang"] = lang
separators = ",." if lang == "tr" else ".,"

with head_left:
    st.markdown(f"<div class='eyebrow'>{html.escape(t(lang, 'eyebrow'))}</div>", unsafe_allow_html=True)
st.title(t(lang, "title"))
st.caption(t(lang, "subtitle"))

region_key = st.selectbox(
    t(lang, "region_label"), list(REGIONS),
    format_func=lambda key: region_name(lang, key, REGIONS[key].name), key="region",
)
region = REGIONS[region_key]
region_label = region_name(lang, region_key, region.name)
cached = set(available_variable_keys(region_key))

annual_by_key: dict[str, pd.DataFrame] = {}
incomplete_by_key: dict[str, list[int]] = {}
board_results: dict[str, TrendResult | None] = {}
for key, variable in VARIABLES.items():
    if key not in cached:
        board_results[key] = None
        continue
    annual, incomplete = to_annual(load_monthly(region_key, key), variable)
    annual_by_key[key], incomplete_by_key[key] = annual, incomplete
    board_results[key] = (
        analyze_trend(annual["year"], annual["value"]) if len(annual) >= MIN_YEARS else None
    )

if not annual_by_key:
    st.warning(t(lang, "no_data_region"))
    st.stop()

available = [key for key in VARIABLES if key in annual_by_key]
if st.session_state.get("case") not in available:
    st.session_state["case"] = available[0]

# --- Step 1: choose a clue -----------------------------------------------------------------------

st.markdown(f"<div class='step'>{html.escape(t(lang, 'step1'))}</div>", unsafe_allow_html=True)
st.caption(t(lang, "step1_caption"))
for column, (key, variable) in zip(st.columns(len(VARIABLES)), VARIABLES.items()):
    texts = variable_text(lang, variable)
    result = board_results[key]
    status = case_status(result)
    selected = st.session_state["case"] == key
    with column.container(border=True):
        st.markdown(
            f"<div class='clue-name'>{html.escape(upper(texts['name'], lang))}</div>",
            unsafe_allow_html=True,
        )
        if result is not None:
            arrow = "▲" if result.slope_per_year > 0 else "▼"
            st.markdown(
                f"<div class='clue-value'>{arrow} {num(result.slope_per_decade, lang, signed=True)}</div>"
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
                f"<div class='clue-unit'>{html.escape(t(lang, 'evidence_pending'))}<br>&nbsp;</div>",
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
subject = lower_first(texts["annual_label"])
annual_all = annual_by_key[case_key]
monthly = load_monthly(region_key, case_key)

st.divider()
st.markdown(
    f"<div class='eyebrow'>{html.escape(t(lang, 'case_label', region=region_label, variable=texts['name']))}</div>",
    unsafe_allow_html=True,
)
st.header(t(lang, "question", subject=subject, region=region_label))
st.write(t(lang, "question_body", name=texts["name"], definition=texts["definition"], subject=subject))

# Step 2: choose the period
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step2'))}</div>", unsafe_allow_html=True)
first_year, last_year = int(annual_all["year"].min()), int(annual_all["year"].max())
start_year, end_year = st.slider(
    t(lang, "period_label"), min_value=first_year, max_value=last_year,
    value=(first_year, last_year), key=f"period_{case_key}",
)
annual = annual_all[annual_all["year"].between(start_year, end_year)].reset_index(drop=True)
if len(annual) < MIN_YEARS:
    st.error(t(lang, "too_short", min=MIN_YEARS, n=len(annual)))
    st.stop()

result = analyze_trend(annual["year"], annual["value"])
band = trend_line_band(annual["year"], annual["value"])
status = case_status(result)
rate = num(result.slope_per_decade, lang, signed=True)

# Step 3: real or chance?
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step3'))}</div>", unsafe_allow_html=True)
if result.significant:
    headline = t(lang, "headline_up" if result.slope_per_year > 0 else "headline_down")
else:
    headline = t(lang, "headline_chance")
hero_class = "real" if result.significant else "chance"
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
    st.caption(t(lang, "ci", low=num(low, lang, signed=True), high=num(high, lang, signed=True)))
with tile_total.container(border=True):
    st.caption(t(lang, "total_change"))
    st.markdown(f"**{num(result.total_change, lang, signed=True)} {unit}**")
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
            rate=num(abs(result.slope_per_decade), lang), unit=unit, start=result.start_year,
            end=result.end_year, total=num(abs(result.total_change), lang),
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

# Step 4: the evidence
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step4'))}</div>", unsafe_allow_html=True)
st.plotly_chart(
    annual_trend_figure(
        annual, band,
        series_name=texts["annual_label"],
        trend_name=t(lang, "trend_name", rate=f"{rate} {unit} {t(lang, 'per_decade')}"),
        band_name=t(lang, "band_name"),
        x_title=texts["year_axis_label"],
        y_title=f"{texts['name']} ({unit})",
        unit=unit,
        separators=separators,
    ),
    width="stretch", theme=None, config={"displaylogo": False}, key="evidence_chart",
)
dropped = [y for y in incomplete_by_key[case_key] if start_year - 1 <= y <= end_year + 1]
basis = t(lang, "based_on", n=result.n_years, start=result.start_year, end=result.end_year)
if dropped:
    basis += t(lang, "not_used", years=", ".join(str(y) for y in dropped))
st.caption(basis)

# Step 5: the second witness
st.markdown(f"<div class='step'>{html.escape(t(lang, 'step5'))}</div>", unsafe_allow_html=True)
found = t(lang, {"increasing": "found_increasing", "decreasing": "found_decreasing"}.get(
    result.mk_trend, "found_none"))
st.markdown(
    t(
        lang, "witness_agrees" if result.agrees else "witness_disagrees", method=result.mk_method,
        found=found, p=p_phrase(result.mk_p_value, lang),
        sen=num(result.sen_slope_per_decade, lang, signed=True), unit=unit,
    )
)
if result.end_year == last_year and result.n_years - 1 >= MIN_YEARS:
    without_last = analyze_trend(annual["year"].iloc[:-1], annual["value"].iloc[:-1])
    st.caption(
        t(
            lang, "cross_exam", year=last_year,
            rate=num(without_last.slope_per_decade, lang, signed=True), unit=unit,
            p=p_phrase(without_last.p_value, lang),
            sig=t(lang, "significant" if without_last.significant else "not_significant"),
        )
    )

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
            in_period, x_title=t(lang, "month_axis"), y_title=f"{texts['name']} ({texts['unit']})",
            unit=texts["unit"], separators=separators,
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
        "region": region.name,
        "variable": variable.name,
        "unit": variable.annual_unit,
        "start_year": result.start_year,
        "end_year": result.end_year,
        "n_years": result.n_years,
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
    col_a, col_b = st.columns(2)
    col_a.download_button(
        t(lang, "dl_annual"), annual.to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{case_key}_annual.csv", mime="text/csv",
    )
    col_b.download_button(
        t(lang, "dl_results"), pd.DataFrame([results_row]).to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{case_key}_case_results.csv", mime="text/csv",
    )

with st.expander(t(lang, "methods_title")):
    st.markdown(METHODS[lang].format(region=region_label, min_years=MIN_YEARS))

st.divider()
doi = f" DOI: [{variable.doi}](https://doi.org/{variable.doi})." if variable.doi else ""
st.caption(f"**{t(lang, 'data_label')}:** {variable.product}, {variable.provider}. {variable.citation}{doi}")
st.caption(t(lang, "footer"))
