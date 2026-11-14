# Architecture: Earth System Trend Detective (Team Avni)

> v0.3, 2026-11-14. Written with AI assistance (Claude Opus 5.5), reviewed by Claude Fable 5.2.
> Design summary written during the hackathon; README.md describes the current app.
> The idea and the product decisions come from Team Avni (see "Decisions made by the team").

## Goal (from the challenge statement)

A user picks an Earth-science variable and a region. The tool builds a long time series from
NASA data, plots it, and answers four questions: **what** is changing, **where**, **by how much**,
and **is the change statistically significant?** Visualization plus analysis is the full scope.

## Decisions made by the team

- End users explore the data themselves; the audience is the team, the judges and later the public.
- Variables: **air temperature**, **precipitation**, **snowfall**, **hot days above 30 °C** (added
  Saturday evening, from daily maximum temperature), **air pollution (NO2)**,
  **carbon monoxide**, **soot (black carbon)**, **dust and smoke (aerosols)** so that air pollution is
  available for any rectangle, **CO2**, **vegetation greenness (NDVI)** and **tree cover**.
- Regions: **Colorado**, **Istanbul–Marmara**, then eight world regions picked from options:
  Medina, Beijing, Los Angeles, Cairo and the Nile Delta, the Amazon, the Sahel, the Alps, Siberia.
- Any place on Earth: a rectangle of any size (0.01° to 40°) the user draws, moves and resizes on a
  map or types in.
- A "possible reasons" step after the verdict.
- Theme and flow: a "secret expert detective"; investigation board plus case files; pick a clue,
  choose the period, then a "real or chance?" verdict; English by default with a Turkish switch.

## Data sources (verified 2026-11-14)

| Variable | Product | Access | Auth | Period |
|---|---|---|---|---|
| Air temperature at 2 m | NASA POWER monthly `T2M` (MERRA-2 based), 0.5 x 0.625 deg | POWER regional API, one parameter per request | none | 1981 to present |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based, mm/day) | POWER regional API | none | 1981 to present |
| Tropospheric NO2 | OMI `OMNO2d` v004 `ColumnAmountNO2TropCloudScreened` (molecules/cm2), daily, 0.25 deg; doi:10.5067/AURA/OMI/DATA3407 | Giovanni area-averaged time series CSV, requested in 5-year chunks | Earthdata Login | Oct 2004 to Nov 2026 |
| NDVI | MODIS Terra `MOD13A3` v061, monthly, 1 km (AppEEARS does not offer MOD13C2) | AppEEARS area request (statistics CSV) | Earthdata Login | Feb 2000 to present |
| Dust and smoke | NASA POWER monthly `AOD_55` (CERES SYN1deg, 1 deg) | POWER regional API | none | 2001 to present |
| Precipitation | NASA POWER monthly `PRECTOTCORR` (MERRA-2, corrected with observations; mm/day x days) | POWER regional API | none | 1981 to present |
| Carbon monoxide | MOPITT `MOP03JM` v010 total column, daytime (molecules/cm2 x 1e-18) | Giovanni area-averaged time series | Earthdata Login | Mar 2000 to Dec 2024 |
| Soot (black carbon) | MERRA-2 `M2TMNXAER` v5.12.4 `BCSMASS` (kg/m3 x 1e9 = ug/m3) | Giovanni area-averaged time series | Earthdata Login | 1980 to present |
| CO2 | OCO-2 GEOS L3 monthly V10r `XCO2` (mol/mol x 1e6 = ppm); min_years = 7 | Giovanni area-averaged time series | Earthdata Login | 2015 to Feb 2022 |
| Tree cover | MODIS Terra `MOD44B` v061 `Percent_Tree_Cover`, yearly, 250 m | AppEEARS area request (statistics CSV) | Earthdata Login | 2000 to present |

Verification notes:
- POWER returns 99 grid cells over the Colorado box and 25 over the Marmara box; requesting two
  parameters at once returns HTTP 422, so we request one parameter at a time.
- POWER regional requests need 2 to 10 degrees in each direction, checked on the plain
  floating-point difference of the numbers sent; `trend/area.py` enforces this on the rounded values.
- The POWER response has a 13th "month" key per year (the annual value). We drop it and compute
  annual values ourselves. Land-only variables (snowfall) leave sea cells empty; those cells are
  excluded.
- Giovanni has **no NDVI** product, so NDVI goes through AppEEARS; open-sea pixels have no NDVI.

Regions (W, S, E, N): Colorado -109.05, 37.0, -102.04, 41.0; Istanbul–Marmara 27.0, 40.0, 30.0, 42.0;
Medina 38.5, 23.5, 40.5, 25.5; Beijing 115.5, 39.0, 118.0, 41.0; Los Angeles -119.0, 33.5, -117.0, 35.5;
Cairo and the Nile Delta 29.5, 29.5, 32.5, 31.75; Amazon (Rondônia) -66.0, -13.0, -60.0, -8.0;
Sahel -2.0, 12.0, 8.0, 16.0; Alps 6.0, 45.5, 14.0, 48.0; Siberia (Yakutia) 125.0, 60.0, 135.0, 65.0.
Area averages: cosine-latitude-weighted mean of POWER grid cells. Giovanni and AppEEARS compute their
own area statistics over the same boxes; we do not claim cosine weighting for those paths.

## Data flow

1. Prepared regions: `scripts/prefetch.py` writes `data/processed/<region>_<variable>.csv`
   (columns: `date, value, unit, source` plus a count column). The files are small and committed,
   so the prepared regions never depend on NASA servers being up.
2. Giovanni and AppEEARS downloads go to `data/raw/` (git-ignored) as
   `giovanni_no2_<region>_*.csv` and `appeears_ndvi_<region>_*.csv`, and are converted by loaders
   that handle metadata header rows, fill values and scale factors.
3. Custom rectangles: the app fetches temperature, precipitation, snowfall and dust and smoke live from the POWER
   API with a short timeout. POWER serves 2 to 10 degrees per request, so a small rectangle is
   requested inside a 2-degree box and a large one in overlapping pieces fetched in parallel; the
   average then uses the grid cells whose centres lie in the rectangle, or the nearest cell with
   data when the rectangle is smaller than one cell. The app retries quick failures (a dropped connection, a garbled answer or a busy server) up to two more times, and caches each rectangle for 24 hours. NO2 and NDVI
   are marked "Prepared regions only" there.

## Statistics (the core of the Validity score)

Monthly values are aggregated to one value per year, which removes the seasonal cycle and reduces
autocorrelation. A year enters the analysis only if it is complete for its aggregation:

| Variable | Annual value | Completeness rule |
|---|---|---|
| Temperature | calendar-year mean | all 12 months present |
| NO2 | calendar-year mean of monthly means | 12 months, each with at least 10 valid days |
| NDVI | mean of May to September (the northern growing season) | all 5 months present |
| Snowfall | water-year total, October to September, labelled by its ending year | all 12 months present; mm/day x days in month |

Tests on the annual series:
- **Headline:** OLS linear trend with slope, 95% confidence interval and two-sided t-test p-value.
  When the lag-1 autocorrelation r1 of the residuals is positive, the standard error and degrees of
  freedom use the effective sample size n_eff = n (1 - r1 - 0.68/sqrt(n)) / (1 + r1 + 0.68/sqrt(n))
  (Santer et al., 2000, with the small-sample adjustment of Nychka et al., 2000). Simulations of
  trendless AR(1) noise during the hackathon showed false "Confirmed" rates of up to 9-13% without
  the adjustment and about 3-8% with it for 25 years or more (persistence up to about 0.7); 10-15-year
  periods and very persistent series (soot) stay higher. Measured with `scripts/accuracy_report.py`
  (4000 simulated series per cell, the numbers on the pitch deck):

  | False "Confirmed", trendless data | 10 years | 15 years | 25 years | 45 years |
  |---|---|---|---|---|
  | independent years | 3.0% | 2.5% | 2.5% | 2.7% |
  | persistence 0.5 | 9.9% | 7.4% | 5.4% | 4.8% |
  | persistence 0.9 | 18.1% | 15.4% | 11.6% | 9.1% |

  | "Confirmed", real trend of 1 SD per decade | 10 y | 15 y | 20 y | 25 y | 35 y | 45 y |
  |---|---|---|---|---|---|---|
  | independent years | 6.9% | 21.0% | 51.3% | 80.9% | 99.6% | 100% |
  | persistence 0.5 | 12.4% | 17.4% | 26.7% | 41.3% | 77.6% | 95.3% |
- **Second witness:** Mann-Kendall with Sen's slope, shown as "agrees" or "disagrees" with the
  headline. It uses the same persistence rule: when r1 > 0 its z-score is scaled by sqrt(n_eff / n)
  (an effective-sample-size correction in the spirit of Yue and Wang, 2004).
- **Stamps:** Confirmed (significant, witness agrees), Disputed (significant, witness disagrees),
  No evidence (not significant), Weak clue (only the witness sees a trend), Open case (data not
  available yet or the fetch failed), No snow (it practically never snows there), Not enough data
  (fewer than 10 complete years, for example aerosols in the polar winter), No data (NASA has no
  values there, for example over open sea).
- **Rate:** per decade. **Total change:** slope x span of years, not last minus first.
- **Guards:** block analysis below 10 years (7 for CO2, with a visible note), warn below 20 years, always show n and the period.
  A non-significant result is worded "no significant trend detected", never "no change".
- **Multiple testing:** one sentence in the methods explaining that many tests at alpha = 0.05 can
  produce false positives.
- **Chart band:** labelled as the 95% confidence band of the fitted line, not a prediction interval.

## Variable caveats shown in the app

- Snowfall is **modelled** liquid-water-equivalent snowfall from the MERRA-2 reanalysis, not observed
  snow depth. Reanalysis trends can partly reflect changes in the observing system.
- NO2 is an average over the whole box (rural areas and, near coasts, the sea), so city signals are
  diluted. OMI has a row anomaly that reduces sampling; 2020 shows a COVID-related dip; the aging
  instrument and Aura's orbit drift call for extra caution after about 2022.
- NDVI: MODIS Terra orbit drift after about 2020. Sanity check that area means lie between -0.2 and 1.
- Precipitation: the MERRA-2 correction uses rain-gauge data whose station network changes over time,
  which can create steps (the Amazon box drops suddenly around 2005); local notes compare the
  Amazon, the Sahel and Beijing with NASA GPCP V3.3.
- Carbon monoxide: whole-column values; no daytime retrievals in the polar winter (Siberia).
- Soot: MERRA-2 aerosol reanalysis; very persistent from year to year.
- CO2: only 7 complete years; mixes globally, so regional values rise at almost the same pace.
- Tree cover: yearly map; plantations count as trees.

## User interface (Streamlit)

- Left panel: prepared region or custom rectangle (typed corners); world map with the rectangle,
  drawable and editable with the Leaflet.draw tools.
- Investigation board: one card per measurement with the rate per decade, a sparkline and a stamp.
- Case file: question and plain-language definition, period slider, "Real or chance?" hero with a
  chance meter (p-value on a log scale with the 5% line), rate / total change / years tiles,
  verdict sentence, share link, evidence chart with the confidence band, second witness,
  cross-examination without the newest year, possible reasons with local context, case notes (caveats, monthly data, data table, CSV
  downloads, methods), data source with DOI.
- English by default, Turkish switch (decimal comma in Turkish); share links restore language,
  region or rectangle, case and period.
- Added on Saturday evening: a "Case on the desk" verdict strip and famous cases at the top, a jump
  to the case file, the evidence timeline and start-year check, the animated replay, the seasons view,
  the "not a straight line" note, the World board view (`?view=world`), and, from the partner session,
  the crime scene map layer and the third witness.

## Project structure

```
NasaSpaceAppsChallenge/
├── app.py                  # Streamlit entry point
├── trend/
│   ├── regions.py          # region catalog
│   ├── variables.py        # variable catalog: definition, unit, product, aggregation, caveats
│   ├── fetch.py            # POWER API client; Giovanni loader; cached CSV storage
│   ├── appeears.py         # AppEEARS API client
│   ├── stats.py            # annual aggregation, OLS + CI + t-test, Mann-Kendall, Sen's slope
│   ├── area.py             # custom rectangles
│   ├── charts.py           # Plotly figures
│   ├── i18n.py             # English and Turkish texts
│   ├── share.py            # share links
│   ├── world.py            # World board: every region and measurement, opposite trends
│   ├── timeline.py         # evidence timeline and start-year check
│   ├── replay.py           # animated replay of the verdict as years are added
│   ├── seasons.py          # monthly values with the seasonal cycle removed
│   ├── linecheck.py        # "not a straight line" note
│   ├── examples.py         # famous cases (checked against the data by tests)
│   ├── hotdays.py          # hot days: daily maximum temperature counted per grid cell
│   │                       # (scripts/build_grid_cells.py writes per-cell yearly values for the time map)
│   ├── trendmap.py         # crime scene map: grid-cell trends with a Benjamini-Hochberg filter
│   ├── verify.py           # third witness and "why is it not verified?"
│   ├── timelapse.py        # time travel map: each grid cell's yearly difference from its normal
│   └── game.py             # Detective exam
├── scripts/prefetch.py     # fetch and cache region x variable CSVs
├── data/raw/               # manual downloads (git-ignored)
├── data/processed/         # small cached CSVs (committed)
├── tests/                  # test_stats, test_fetch, test_area, test_share, test_app
├── docs/                   # ARCHITECTURE.md, SUBMISSION.md
├── requirements.txt        # app dependencies (Streamlit Cloud)
└── requirements-dev.txt    # scripts and tests
```

## Testing

432 automated tests (`python -m pytest -q`), all offline:
- statistics: known-slope series, white and autocorrelated noise (false-positive rates of both
  tests), completeness rules, water-year labelling, total change, constant series;
- loaders: POWER payload parsing, fill values, land-only cells, Giovanni CSVs, retry rules;
- rectangles: validation, the 2 to 10 degree limits in plain floats, drawn and edited shapes;
- app: every case file in both languages and the prepared regions, examples, periods, custom areas with
  synthetic live data, an offline NASA POWER.

## Deployment

Streamlit Community Cloud from the public GitHub repository (Python 3.13, pinned
`requirements.txt`); every push to `main` redeploys. No secrets are needed. Error details in the
browser are limited to the error type.

## Scope

Cut: seasonal Mann-Kendall, NO2 and NDVI for custom rectangles (their NASA services need a login
and take minutes per request), the earthaccess download path.
Feature freeze: Saturday evening (team decision); after that only bug fixes and NASA data that was
still arriving.

## Rules compliance

- English UI by default (Turkish is an optional switch) and English documentation.
- AI use disclosed in the README "Use of AI" section, in file headers, in commit trailers and on the
  submission page.
- Every dataset, library, font and map source cited, with DOIs where available. No NASA logos or
  branding.
- Apache-2.0 license.
