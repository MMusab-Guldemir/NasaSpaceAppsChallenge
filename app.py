"""Earth System Trend Detective: Streamlit app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea, the "expert detective" theme and all product decisions come
from Team Avni; the board-and-case-file layout was suggested by the AI and approved by the team.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from trend.charts import annual_trend_figure, monthly_figure
from trend.fetch import available_variable_keys, load_processed
from trend.regions import REGIONS, Region
from trend.stats import (
    MIN_YEARS,
    TrendResult,
    analyze_trend,
    p_text,
    to_annual,
    trend_line_band,
)
from trend.variables import VARIABLES, Variable

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🔎", layout="wide")

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
.case-label {
  font-family: 'Special Elite', 'Courier New', monospace;
  letter-spacing: 0.12em; text-transform: uppercase; color: #52514e; font-size: 0.85rem;
}
.stamp {
  display: inline-block; font-family: 'Special Elite', 'Courier New', monospace;
  font-size: 0.95rem; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 10px; border: 2px solid currentColor; border-radius: 4px;
  transform: rotate(-3deg); margin: 6px 0 8px 0; background: rgba(255, 255, 255, 0.6);
}
.stamp.confirmed { color: #1c5cab; }
.stamp.noevidence { color: #52514e; }
.stamp.disputed, .stamp.weak { color: #a8501b; }
.stamp.open { color: #898781; border-style: dashed; }
.clue-value { font-size: 1.35rem; font-weight: 700; color: #0b0b0b; }
</style>
"""

STATUS_TEXT = {
    "confirmed": ("Confirmed", "A real trend: both tests agree."),
    "disputed": ("Disputed", "The headline test sees a trend, the second witness does not."),
    "noevidence": ("No evidence", "No significant trend detected."),
    "weak": ("Weak clue", "Only the second witness sees a trend."),
    "open": ("Open case", "Evidence still being collected."),
}


@st.cache_data(show_spinner=False)
def load_monthly(region_key: str, variable_key: str) -> pd.DataFrame | None:
    return load_processed(region_key, variable_key)


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def chance_phrase(p: float) -> str:
    return "less than 0.1% of the time" if p < 0.001 else f"only about {p * 100:.1f}% of the time"


def case_status(result: TrendResult | None) -> str:
    if result is None:
        return "open"
    if result.significant:
        return "confirmed" if result.agrees else "disputed"
    return "noevidence" if result.agrees else "weak"


def stamp(status: str) -> str:
    return f"<span class='stamp {status}'>{STATUS_TEXT[status][0]}</span>"


def verdict_sentence(result: TrendResult, variable: Variable, region: Region) -> str:
    unit = variable.annual_unit
    period = f"{result.start_year} to {result.end_year}"
    subject = lower_first(variable.annual_label)
    if result.significant:
        verb = "rose" if result.slope_per_year > 0 else "fell"
        return (
            f"In **{region.name}**, the {subject} **{verb} by about "
            f"{abs(result.slope_per_decade):.2f} {unit} per decade** from {period}, about "
            f"{abs(result.total_change):.2f} {unit} in total along the trend line. If there were no "
            f"real trend, a trend this strong would appear by chance {chance_phrase(result.p_value)}."
        )
    return (
        f"In **{region.name}**, **no significant trend was detected** in the {subject} from {period}. "
        f"The values go up and down, but the overall direction cannot be told apart from natural "
        f"year-to-year variation ({p_text(result.p_value)})."
    )


def second_witness(result: TrendResult, variable: Variable) -> str:
    found = {
        "increasing": "an increasing trend",
        "decreasing": "a decreasing trend",
        "no trend": "no significant trend",
    }[result.mk_trend]
    detail = (
        f"the {result.mk_method} test, which does not assume a straight line, finds {found} "
        f"({p_text(result.mk_p_value)}; Sen's slope {result.sen_slope_per_decade:+.2f} "
        f"{variable.annual_unit} per decade)."
    )
    if result.agrees:
        return f"✅ **The second witness agrees:** {detail}"
    return f"⚠️ **The second witness disagrees:** {detail} Treat this verdict with caution."


def open_case(variable_key: str) -> None:
    st.session_state["case"] = variable_key


st.markdown(STYLE, unsafe_allow_html=True)

# --- Header ----------------------------------------------------------------------------------

st.markdown("<div class='case-label'>NASA Earth data · Statistical investigation</div>",
            unsafe_allow_html=True)
st.title("Earth System Trend Detective")
st.caption(
    "Every place leaves clues in NASA's satellite records. Open a case file to find out what is "
    "changing, by how much, and whether the change is real or just chance."
)

region_key = st.selectbox(
    "Region under investigation", list(REGIONS), format_func=lambda key: REGIONS[key].name,
    key="region",
)
region = REGIONS[region_key]
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
    board_results[key] = analyze_trend(annual["year"], annual["value"]) if len(annual) >= MIN_YEARS else None

if not annual_by_key:
    st.warning("No evidence has been collected for this region yet.")
    st.stop()

available = [key for key in VARIABLES if key in annual_by_key]
if st.session_state.get("case") not in available:
    st.session_state["case"] = available[0]

# --- Investigation board ---------------------------------------------------------------------

st.subheader(f"Investigation board · {region.name}")
st.caption("Four clues from NASA Earth data, each over its full record. Open a case file for the evidence.")
for column, (key, variable) in zip(st.columns(len(VARIABLES)), VARIABLES.items()):
    result = board_results[key]
    status = case_status(result)
    with column.container(border=True):
        st.caption(variable.name.upper())
        if result is not None:
            arrow = "▲" if result.slope_per_year > 0 else "▼"
            st.markdown(
                f"<div class='clue-value'>{arrow} {result.slope_per_decade:+.2f}</div>"
                f"<div>{variable.annual_unit} per decade · {result.start_year}–{result.end_year}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div class='clue-value'>—</div><div>Evidence pending</div>",
                        unsafe_allow_html=True)
        st.markdown(stamp(status), unsafe_allow_html=True)
        st.button(
            "Open case file", key=f"open_{key}", on_click=open_case, args=(key,),
            disabled=key not in annual_by_key, width="stretch",
            type="primary" if st.session_state["case"] == key else "secondary",
        )

# --- Case file -------------------------------------------------------------------------------

case_key = st.session_state["case"]
variable = VARIABLES[case_key]
annual_all = annual_by_key[case_key]
monthly = load_monthly(region_key, case_key)
unit = variable.annual_unit

st.divider()
st.markdown(f"<div class='case-label'>Case file · {region.name} · {variable.name}</div>",
            unsafe_allow_html=True)
st.header(f"Is the {lower_first(variable.annual_label)} in {region.name} changing?")

st.markdown("##### 1 · The question")
st.write(
    f"**{variable.name}:** {variable.definition} Each piece of evidence below is one "
    f"{lower_first(variable.annual_label)}."
)

st.markdown("##### 2 · The evidence")
first_year, last_year = int(annual_all["year"].min()), int(annual_all["year"].max())
start_year, end_year = st.slider(
    "Period under investigation", min_value=first_year, max_value=last_year,
    value=(first_year, last_year), key=f"period_{case_key}",
)
annual = annual_all[annual_all["year"].between(start_year, end_year)].reset_index(drop=True)
if len(annual) < MIN_YEARS:
    st.error(
        f"Not enough evidence: a trend test needs at least {MIN_YEARS} complete years, "
        f"and this period has {len(annual)}. Pick a longer period."
    )
    st.stop()

result = analyze_trend(annual["year"], annual["value"])
band = trend_line_band(annual["year"], annual["value"])
trend_label = f"{result.slope_per_decade:+.2f} {unit} per decade"
st.plotly_chart(
    annual_trend_figure(annual, band, variable, trend_label),
    width="stretch", theme=None, config={"displaylogo": False},
)
incomplete = incomplete_by_key[case_key]
dropped = [y for y in incomplete if start_year - 1 <= y <= end_year + 1]
basis = f"Based on {result.n_years} complete years ({result.start_year} to {result.end_year})."
if dropped:
    basis += " Not used because incomplete: " + ", ".join(str(y) for y in dropped) + "."
st.caption(basis)

st.markdown("##### 3 · The verdict")
status = case_status(result)
st.markdown(stamp(status) + f"&nbsp; {STATUS_TEXT[status][1]}", unsafe_allow_html=True)
tile_what, tile_where, tile_how, tile_sig = st.columns(4)
with tile_what.container(border=True):
    st.caption("WHAT")
    st.markdown(f"**{variable.name}**")
with tile_where.container(border=True):
    st.caption("WHERE")
    st.markdown(f"**{region.name}**")
with tile_how.container(border=True):
    st.caption("HOW MUCH")
    st.markdown(f"**{result.slope_per_decade:+.2f} {unit} per decade**")
    low, high = result.ci_per_decade
    st.caption(f"95% CI {low:+.2f} to {high:+.2f}")
with tile_sig.container(border=True):
    st.caption("SIGNIFICANT?")
    if result.significant:
        st.markdown(f"**Yes** ({p_text(result.p_value)})")
    else:
        st.markdown(f"**No significant trend detected** ({p_text(result.p_value)})")
st.markdown(verdict_sentence(result, variable, region))
if result.warning:
    st.warning(result.warning)

st.markdown("##### 4 · The second witness")
st.markdown(second_witness(result, variable))
if result.end_year == last_year and result.n_years - 1 >= MIN_YEARS:
    without_last = analyze_trend(annual["year"].iloc[:-1], annual["value"].iloc[:-1])
    st.caption(
        f"Cross-examination: leaving out the newest year ({last_year}), whose data can still be "
        f"revised, gives {without_last.slope_per_decade:+.2f} {unit} per decade "
        f"({p_text(without_last.p_value)}, "
        f"{'significant' if without_last.significant else 'not significant'})."
    )

st.markdown("##### 5 · Case notes")
if variable.caveats:
    with st.expander("Keep in mind"):
        st.markdown("\n".join(f"- {c}" for c in variable.caveats))

with st.expander("Monthly values (with the seasonal cycle)"):
    st.caption("Monthly values still include the seasonal cycle, so they swing up and down every year.")
    in_period = monthly[monthly["date"].dt.year.between(start_year - 1, end_year)]
    st.plotly_chart(
        monthly_figure(in_period, variable), width="stretch", theme=None,
        config={"displaylogo": False},
    )

with st.expander("Data table and downloads"):
    table = annual.rename(
        columns={
            "year": variable.year_axis_label.split(" (")[0],
            "value": f"{variable.annual_label} ({unit})",
            "n_months": "Months used",
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")
    if "source" in monthly.columns:
        st.caption(f"Source recorded when the data was fetched: {monthly['source'].iloc[0]}")
    results_row = {
        "region": region.name,
        "variable": variable.name,
        "unit": unit,
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
        "verdict": STATUS_TEXT[status][0],
    }
    col_a, col_b = st.columns(2)
    col_a.download_button(
        "Download the annual series (CSV)",
        annual.to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{case_key}_annual.csv",
        mime="text/csv",
    )
    col_b.download_button(
        "Download the case results (CSV)",
        pd.DataFrame([results_row]).to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{case_key}_case_results.csv",
        mime="text/csv",
    )

with st.expander("How the detective works (methods and limitations)"):
    st.markdown(
        f"""
- **Area average:** the value for {region.name} is the average of all data grid cells whose
  centres lie inside or on the edge of the region's box, weighted by the cosine of latitude.
  Cells centred on the edge reach about a quarter of a degree beyond the box.
- **One value per year:** monthly values are combined into one value per year, which removes the
  seasonal cycle. A year is used only if all of its months are available.
- **Headline test:** a straight line is fitted with ordinary least squares (OLS). We report its
  slope, the 95% confidence interval of the slope and the p-value of a two-sided t-test.
  The **p-value** is the chance of seeing a trend at least this strong if there were really no trend.
  We call a trend significant when p < 0.05.
- **Year-to-year persistence:** when a year's departure from the trend line tends to be followed by
  a similar departure (positive autocorrelation), the uncertainty is widened using an effective
  sample size (Santer et al., 2000), so the result is not overconfident.
- **Second witness:** the Mann-Kendall test checks for a steady rise or fall without assuming a
  straight line; Sen's slope is a robust estimate of the rate. If the residuals of the straight
  line are correlated from one year to the next, the Hamed-Rao corrected version is used.
- **Stamps:** *Confirmed* = significant and the second witness agrees; *Disputed* = significant
  but the second witness disagrees; *No evidence* = no significant trend; *Weak clue* = only the
  second witness sees a trend.
- **Total change** is the slope multiplied by the number of years, not the last value minus the first.
- **Confidence band:** the shaded band is the 95% confidence band of the fitted line, not a range
  for individual years.
- **Short periods:** at least {MIN_YEARS} years are required; fewer than 20 years gives a warning.
- **Many tests:** if you test many measurements, regions and periods, about 1 in 20 tests can look
  significant by chance alone.
- **No significant trend detected** does not mean "no change"; a longer record may reveal one.
"""
    )

st.divider()
doi = f" DOI: [{variable.doi}](https://doi.org/{variable.doi})." if variable.doi else ""
st.caption(f"**Data:** {variable.product}, {variable.provider}. {variable.citation}{doi}")
st.caption(
    "Team Avni · NASA Space Apps Challenge 2026 · Built with AI assistance (Claude by Anthropic); "
    "see the README for details. Not affiliated with or endorsed by NASA."
)
