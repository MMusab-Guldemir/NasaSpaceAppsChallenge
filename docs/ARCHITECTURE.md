# Architecture Plan: Earth System Trend Detective (Team Avni)

> v0.2, 2026-11-14. Written with AI assistance (Claude Opus 5.5), reviewed by Claude Fable.
> The idea and all product decisions come from Team Avni.

## Goal (from the challenge statement)

A user picks an Earth-science variable and a region. The tool builds a long time series from
NASA data, plots it, and answers four questions: **what** is changing, **where**, **by how much**,
and **is the change statistically significant?** Visualization plus analysis is the full scope.

## Team decisions

- End users explore the data themselves.
- Regions: start with one US region (**Colorado**), then add more regions.
- Variables: **air temperature**, **air pollution (NO2)**, **snowfall**, **vegetation greenness (NDVI)**.

## Data sources (verified 2026-11-14)

| Variable | Product | Access | Auth | Period |
|---|---|---|---|---|
| Air temperature at 2 m | NASA POWER monthly `T2M` (MERRA-2 based), 0.5 x 0.625 deg | POWER regional API, one parameter per request | none | 1981 to present |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based, mm/day) | POWER regional API | none | 1981 to present |
| Tropospheric NO2 | OMI `OMNO2d` v004 `ColumnAmountNO2TropCloudScreened` (molecules/cm2), daily, 0.25 deg | Giovanni area-averaged time series CSV, requested in 5-year chunks | Earthdata Login | Oct 2004 to Nov 2026 |
| NDVI | MODIS Terra `MOD13A3` v061, monthly, 1 km (AppEEARS does not offer MOD13C2) | AppEEARS area request (statistics CSV) | Earthdata Login | Feb 2000 to present |

Verification notes:
- POWER regional API returns 99 grid cells over the Colorado box; requesting two parameters at once returns HTTP 422, so we request one parameter at a time.
- The POWER response has a 13th "month" key per year (the annual value). We drop it and compute annual values ourselves.
- Giovanni lists `OMNO2d_004_ColumnAmountNO2TropCloudScreened` (data through 2026-11-11). Giovanni has **no NDVI** product, so NDVI goes through AppEEARS.

Region: Colorado bounding box W -109.05, S 37.0, E -102.04, N 41.0 (the state is almost a rectangle).
Area averages: cosine-latitude-weighted mean of POWER grid cells. Giovanni and AppEEARS compute their
own area statistics; we do not claim cosine weighting for those paths.

## Data flow

1. `scripts/prefetch.py` writes `data/processed/<region>_<variable>.csv`
   (columns: `date, value, unit, source`). The files are small and committed, so the demo never
   depends on NASA servers being up.
2. Giovanni and AppEEARS downloads go to `data/raw/` (git-ignored) and are converted by loaders
   that handle metadata header rows, fill values and scale factors.
3. The app reads only `data/processed/`.

## Statistics (the core of the Validity score)

Monthly values are aggregated to one value per year, which removes the seasonal cycle and reduces
autocorrelation. A year enters the analysis only if it is complete for its aggregation:

| Variable | Annual value | Completeness rule |
|---|---|---|
| Temperature | calendar-year mean | all 12 months present |
| NO2 | calendar-year mean of monthly means | 12 months, each with at least 10 valid days |
| NDVI | growing-season mean, May to September | all 5 months present |
| Snowfall | water-year total, October to September, labelled by its ending year | all 12 months present; mm/day x days in month |

Tests on the annual series:
- **Headline:** OLS linear trend with slope, 95% confidence interval and two-sided t-test p-value.
- **Robustness check:** Mann-Kendall with Sen's slope, shown as "agrees" or "disagrees" with the headline.
  Hamed-Rao modified Mann-Kendall only when lag-1 autocorrelation of the OLS residuals is significant.
- **Rate:** per decade. **Total change:** slope x span of years, not last minus first.
- **Guards:** block analysis below 10 years, warn below 20 years, always show n and the period.
  A non-significant result is worded "no significant trend detected", never "no change".
- **Multiple testing:** one sentence in the methods explaining that many tests at alpha = 0.05 can
  produce false positives; optional Holm adjustment in any summary table.
- **Chart band:** labelled as the 95% confidence band of the fitted line, not a prediction interval.

## Variable caveats shown in the app

- Snowfall is **modelled** liquid-water-equivalent snowfall from the MERRA-2 reanalysis, not observed
  snow depth. Reanalysis trends can partly reflect changes in the observing system.
- NO2 statewide means are dominated by rural background, so city signals (Denver) are diluted.
  OMI has a row anomaly that reduces sampling. 2020 shows a COVID-related dip.
- NDVI: MODIS Terra orbit drift after about 2020. Sanity check that area means lie between -0.2 and 1.

## User interface (Streamlit)

- Region and variable pickers; each variable shows a plain-language definition, unit and caveats.
- Period selector, guarded by the length rules above.
- Chart: monthly values (light), annual values (bold), trend line with the labelled confidence band.
- Result card: What / Where / How much / Significant?
- Data source with product short name, version and DOI under every chart.
- "Methods and limitations" expander; CSV download of the series and results.
- "Detective" experience details: to be defined by the participant.

## Project structure

```
NasaSpaceAppsChallenge/
├── app.py                  # Streamlit entry point
├── trend/
│   ├── __init__.py
│   ├── regions.py          # region catalog (Colorado first)
│   ├── variables.py        # variable catalog: definition, unit, product, aggregation, caveats
│   ├── fetch.py            # POWER API client; loaders for Giovanni and AppEEARS CSVs
│   ├── stats.py            # annual aggregation, OLS + CI + t-test, Mann-Kendall, Sen's slope
│   └── charts.py           # Plotly figures
├── scripts/
│   └── prefetch.py         # fetch and cache region x variable CSVs
├── data/
│   ├── raw/                # manual downloads (git-ignored)
│   └── processed/          # small cached CSVs (committed)
├── tests/
│   └── test_stats.py
├── docs/ARCHITECTURE.md
├── requirements.txt        # app dependencies (Streamlit Cloud)
├── requirements-dev.txt    # scripts and tests
├── .env.example            # placeholder names only
└── README.md               # overview, run instructions, citations, Use of AI
```

## Testing

- `tests/test_stats.py`: known-slope synthetic series (detected, slope within tolerance), white noise
  (not significant in most seeds), completeness rules, water-year labelling, total-change formula.
- Loader tests with small fixture CSVs: header rows, fill values, scale factors.
- External cross-check: compare the Colorado temperature trend with NOAA's published statewide trend.

## Deployment

Streamlit Community Cloud from the public GitHub repository, with the Python version set and
trimmed `requirements.txt`. A skeleton is deployed early (Saturday midday). No secrets are needed.

## Scope

Cut: seasonal Mann-Kendall, live refresh, the earthaccess download path.
Extra regions use POWER variables first; NO2 and NDVI only if the manual downloads are quick to repeat.
Feature freeze: Sunday 12:00.

## Rules compliance

- English UI and README.
- AI use disclosed in the README "Use of AI" section, in file headers, in commit trailers and on the
  submission page.
- Every dataset and library cited, with DOIs where available. No NASA logos or branding.
- Apache-2.0 license (already in the repository).

## Milestones

1. Data requests first: Giovanni NO2 chunks and AppEEARS NDVI submitted by the participant.
2. Temperature end to end (POWER, statistics, chart) and a deployed skeleton: Saturday midday.
3. Snowfall (POWER): Saturday afternoon.
4. NO2 and NDVI loaders once the downloads arrive: Saturday evening.
5. First full version deployed, fallback 30-second demo recorded: Saturday night.
6. Polish, more regions, README, demo, submission: Sunday.

## Open questions for the participant

- The "detective" experience: who uses it, what they see first, what makes it different.
- Which regions come next.
