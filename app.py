"""Earth System Trend Detective: Streamlit app.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The idea and product decisions come from Team Avni.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from trend.charts import annual_trend_figure, monthly_figure
from trend.fetch import available_variable_keys, load_processed
from trend.regions import REGIONS
from trend.stats import (
    MIN_YEARS,
    TrendResult,
    analyze_trend,
    p_text,
    to_annual,
    trend_line_band,
)
from trend.variables import VARIABLES, Variable

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🛰️", layout="wide")


@st.cache_data(show_spinner=False)
def load_monthly(region_key: str, variable_key: str) -> pd.DataFrame | None:
    return load_processed(region_key, variable_key)


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def chance_phrase(p: float) -> str:
    return "less than 0.1% of the time" if p < 0.001 else f"only about {p * 100:.1f}% of the time"


def verdict(result: TrendResult, variable: Variable, region_name: str) -> str:
    unit = variable.annual_unit
    period = f"{result.start_year} to {result.end_year}"
    subject = lower_first(variable.annual_label)
    if result.significant:
        verb = "rose" if result.slope_per_year > 0 else "fell"
        return (
            f"In **{region_name}**, the {subject} **{verb} by about "
            f"{abs(result.slope_per_decade):.2f} {unit} per decade** from {period}, about "
            f"{abs(result.total_change):.2f} {unit} in total along the trend line. If there were no "
            f"real trend, a trend this strong would appear by chance "
            f"{chance_phrase(result.p_value)}."
        )
    return (
        f"In **{region_name}**, **no significant trend was detected** in the {subject} from {period}. "
        f"The values go up and down, but the overall direction cannot be told apart from natural "
        f"year-to-year variation ({p_text(result.p_value)})."
    )


def second_opinion(result: TrendResult, variable: Variable) -> str:
    found = {
        "increasing": "an increasing trend",
        "decreasing": "a decreasing trend",
        "no trend": "no significant trend",
    }[result.mk_trend]
    detail = (
        f"the {result.mk_method} test, which does not assume a straight line, finds {found} "
        f"({p_text(result.mk_p_value)}; Sen's slope "
        f"{result.sen_slope_per_decade:+.2f} {variable.annual_unit} per decade)."
    )
    if result.agrees:
        return f"✅ **Second opinion agrees:** {detail}"
    return f"⚠️ **Second opinion disagrees:** {detail} Treat this result with caution."


# --- Header and filters ----------------------------------------------------------------------

st.title("Earth System Trend Detective")
st.caption(
    "Pick a place and a measurement from NASA Earth data. Find out what is changing, where, "
    "by how much, and whether the change is statistically significant."
)

col_region, col_variable, col_period = st.columns([1, 1, 2])
region_key = col_region.selectbox(
    "Region", list(REGIONS), format_func=lambda key: REGIONS[key].name
)
region = REGIONS[region_key]

cached = set(available_variable_keys(region_key))
available = [key for key in VARIABLES if key in cached]
if not available:
    st.warning("No data has been prepared for this region yet.")
    st.stop()

variable_key = col_variable.selectbox(
    "Measurement", available, format_func=lambda key: VARIABLES[key].name
)
variable = VARIABLES[variable_key]

monthly = load_monthly(region_key, variable_key)
annual_all, incomplete = to_annual(monthly, variable)
first_year, last_year = int(annual_all["year"].min()), int(annual_all["year"].max())
start_year, end_year = col_period.slider(
    "Period", min_value=first_year, max_value=last_year, value=(first_year, last_year)
)

coming_soon = [VARIABLES[key].name for key in VARIABLES if key not in cached]
if coming_soon:
    st.caption("Coming soon for this region: " + ", ".join(coming_soon) + ".")

with st.expander(f"What is “{variable.name}”?"):
    st.write(variable.definition)
    st.write(f"Each point on the chart is one **{lower_first(variable.annual_label)}**.")
    if variable.caveats:
        st.markdown("**Keep in mind:**\n" + "\n".join(f"- {c}" for c in variable.caveats))

annual = annual_all[annual_all["year"].between(start_year, end_year)].reset_index(drop=True)
if len(annual) < MIN_YEARS:
    st.error(
        f"Pick a longer period: a trend test needs at least {MIN_YEARS} complete years, "
        f"and this period has {len(annual)}."
    )
    st.stop()

result = analyze_trend(annual["year"], annual["value"])
band = trend_line_band(annual["year"], annual["value"])
unit = variable.annual_unit

# --- Result card ---------------------------------------------------------------------------------

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

st.markdown(verdict(result, variable, region.name))
st.markdown(second_opinion(result, variable))

dropped = [y for y in incomplete if start_year - 1 <= y <= end_year + 1]
basis = f"Based on {result.n_years} complete years ({result.start_year} to {result.end_year})."
if dropped:
    basis += " Not used because incomplete: " + ", ".join(str(y) for y in dropped) + "."
st.caption(basis)
if result.warning:
    st.warning(result.warning)
if result.end_year == last_year and result.n_years - 1 >= MIN_YEARS:
    without_last = analyze_trend(annual["year"].iloc[:-1], annual["value"].iloc[:-1])
    st.caption(
        f"Sensitivity check: leaving out the newest year ({last_year}), whose data can still be "
        f"revised, gives {without_last.slope_per_decade:+.2f} {unit} per decade "
        f"({p_text(without_last.p_value)}, "
        f"{'significant' if without_last.significant else 'not significant'})."
    )

trend_label = f"{result.slope_per_decade:+.2f} {unit} per decade"
st.markdown(f"#### {variable.annual_label}, {result.start_year} to {result.end_year}")
st.plotly_chart(
    annual_trend_figure(annual, band, variable, trend_label),
    width="stretch",
    theme=None,
    config={"displaylogo": False},
)

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
    }
    col_a, col_b = st.columns(2)
    col_a.download_button(
        "Download the annual series (CSV)",
        annual.to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{variable_key}_annual.csv",
        mime="text/csv",
    )
    col_b.download_button(
        "Download the test results (CSV)",
        pd.DataFrame([results_row]).to_csv(index=False).encode("utf-8"),
        file_name=f"{region_key}_{variable_key}_trend_results.csv",
        mime="text/csv",
    )

with st.expander("Methods and limitations"):
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
- **Second opinion:** the Mann-Kendall test checks for a steady rise or fall without assuming a
  straight line; Sen's slope is a robust estimate of the rate. If the residuals of the straight
  line are correlated from one year to the next, the Hamed-Rao corrected version is used.
- **Total change** is the slope multiplied by the number of years, not the last value minus the first.
- **Confidence band:** the shaded band is the 95% confidence band of the fitted line, not a range
  for individual years.
- **Short periods:** at least {MIN_YEARS} years are required; fewer than 20 years gives a warning.
- **Many tests:** if you test many measurements, regions and periods, about 1 in 20 tests can look
  significant by chance alone.
- **No significant trend detected** does not mean "no change"; a longer record may reveal one.
"""
    )

st.markdown("---")
doi = f" DOI: [{variable.doi}](https://doi.org/{variable.doi})." if variable.doi else ""
st.caption(f"**Data:** {variable.product}, {variable.provider}. {variable.citation}{doi}")
st.caption(
    "Team Avni · NASA Space Apps Challenge 2026 · Built with AI assistance (Claude by Anthropic); "
    "see the README for details. Not affiliated with or endorsed by NASA."
)
