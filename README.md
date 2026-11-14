# Earth System Trend Detective

**Team Avni · NASA Space Apps Challenge 2026 · Challenge: "Be An Earth System Trend Detective!"**

**Live app:** https://avni-trend-detective.streamlit.app
(If the app shows a wake-up screen, click the button and wait about a minute.)

Pick a place and a measurement from NASA Earth data, and find out **what** is changing,
**where**, **by how much**, and **whether the change is statistically significant**.

> Built during the NASA Space Apps Challenge hackathon, 14-15 November 2026.

## What it does

1. **Where?** Pick one of ten prepared regions with up to ten measurements each (Colorado,
   Istanbul–Marmara, Medina, Beijing, Los Angeles, Cairo and the Nile Delta, the Amazon, the Sahel,
   the Alps and Siberia; vegetation greenness is ready for Colorado, Istanbul–Marmara, Medina,
   Beijing, Los Angeles and Cairo and the Nile Delta, and the other regions and tree cover are added
   as NASA AppEEARS delivers them), or investigate **anywhere on Earth**: draw a rectangle on the world map,
   move or resize it with the edit tool (then click Save), or type its corners in the left panel.
   Any size from 0.01° to 40° per side works: a rectangle smaller than NASA's grid uses the nearest
   grid cell, and a large one is fetched in pieces. Temperature, precipitation, snowfall and dust and
   smoke come live from NASA POWER for any rectangle; NO₂, carbon monoxide, soot (black carbon),
   CO₂, vegetation greenness and tree cover are prepared in advance for the prepared regions. The
   cards are grouped into Climate, Air, and Carbon and green land.
2. An **investigation board** shows every clue for the area: one card per measurement with its
   rate of change and a verdict stamp (Confirmed, Disputed, No evidence, Weak clue, Open case; plus No snow, Not enough data and No data where they apply).
3. The user picks a clue, chooses the **period**, and immediately gets a large
   **"Real or chance?"** verdict with a chance meter, followed by the evidence (chart) and a
   second witness. An **EN / TR** switch (top right) shows the whole app in English or Turkish.
4. Behind the scenes, NASA monthly data become one value per year (removing the seasonal cycle).
5. The app fits a linear trend and reports:
   - the **rate of change per decade** with its 95% confidence interval,
   - whether the trend is **significant** (two-sided t-test, adjusted for year-to-year persistence
     with an effective sample size and a small-sample correction; in simulations a false
     "Confirmed" appears in about 3% of trendless cases with independent years, about 5-7% with
     moderate persistence over 15+ years, and about 9-18% for very persistent series such as soot;
     a real trend of one typical year-to-year swing per decade is confirmed about 7 times in 100
     with 10 years, 51 with 20, 81 with 25 and over 99 with 35 years; reproduce with
     `scripts/accuracy_report.py`),
   - a **second opinion** from the Mann-Kendall test with Sen's slope, adjusted for persistence in
     the same way,
   - a plain-language summary for students and the public.
6. **Possible reasons:** common explanations from research for a rise, a fall or no clear trend,
   plus local context for the prepared regions, with a clear note that the test shows *that*
   something changed, not *why*.
7. Charts, a data table, CSV downloads, share links and a "How the detective works" section make
   every result checkable.
8. **Detective exam (game):** switch from "Investigation" to "Detective exam" at the top. A secret,
   unlabeled chart draws itself year by year; the earlier the player decides "real increase",
   "real decrease" or "chance", the more points they get. Then the stamp, the place and a possible
   explanation appear. A full exam has 20 cases from all prepared regions (a quick exam has 5),
   with badges, streaks and a tricky double-points case at the end. The answers come from the same
   statistics as the investigation board. Link: `?view=exam`.

## First results (full records)

| Clue | Colorado, USA | Istanbul–Marmara, Türkiye |
|---|---|---|
| Air temperature, annual mean (1981-2025) | **+0.33 °C per decade** (p < 0.001), Confirmed | **+0.55 °C per decade** (p < 0.001), Confirmed |
| Snowfall, water-year total (1982-2026) | no significant trend (p = 0.66) | no significant trend (p = 0.60) |
| Tropospheric NO₂, annual mean (2005-2025) | no significant straight-line trend (p = 0.49); the 2005-2019 decline is not significant either once short-record persistence is accounted for (p = 0.11) | no significant trend (p = 0.90)¹ |
| Vegetation greenness, May-Sep NDVI (2000-2025) | no significant trend (p = 0.39) | +0.014 per decade, no significant trend (p = 0.07) |
| Carbon monoxide (2002-2024) | −0.06 × 10¹⁸ molecules/cm² per decade (p = 0.007), Confirmed | −0.10 × 10¹⁸ molecules/cm² per decade (p = 0.006), Confirmed |
| CO₂ (2015-2021, 7 years; 2022 is incomplete) | +25 ppm per decade (p < 0.001), Confirmed | +25 ppm per decade (p < 0.001), Confirmed |

¹ 2024 is left out because January 2024 has fewer than 10 valid OMI days.

The same measurement can behave differently in two places: both regions are warming, Istanbul–
Marmara faster, while CO₂ rises at the same pace in both because it mixes around the planet.

Highlights from the world regions (full records unless stated):
- Beijing NO₂ fell by about 3.7 × 10¹⁵ molecules/cm² per decade from 2013 to 2025 (p = 0.013, both
  tests agree), after China's 2013 clean-air plan; over 2005-2025 the rise-then-fall shape is not a
  significant straight-line trend (p = 0.23).
- NO₂ over the Alps fell by about 0.42 × 10¹⁵ molecules/cm² per decade (2005-2025, p = 0.002).
- Beijing is getting greener: May-September NDVI rose by about +0.029 per decade (2000-2025,
  p < 0.001, both tests agree).
- Air temperature rose significantly in nine of the ten prepared regions, from +0.12 °C per decade
  in the Sahel to +0.55 °C per decade in Istanbul–Marmara (1981-2025); in Beijing the rise
  (+0.23 °C per decade) is borderline (p = 0.06).

## Data

| Measurement | NASA product | Access |
|---|---|---|
| Air temperature | NASA POWER monthly `T2M` (MERRA-2 based) | POWER API |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based) | POWER API |
| Air pollution (NO₂) | OMI `OMNO2d` v004 tropospheric column (daily, averaged per month) | Giovanni area-averaged time series |
| Vegetation greenness (NDVI) | MODIS Terra `MOD13A3` v061 (monthly, 1 km) | AppEEARS area statistics |
| Dust and smoke (aerosols) | NASA POWER monthly `AOD_55` (CERES SYN1deg, about 1°) | POWER API |
| Precipitation | NASA POWER monthly `PRECTOTCORR` (MERRA-2, corrected with observations) | POWER API |
| Carbon monoxide (CO) | MOPITT `MOP03JM` v010 total column, daytime (monthly, 1°) | Giovanni area-averaged time series |
| Soot (black carbon) | MERRA-2 `M2TMNXAER` v5.12.4 black carbon surface concentration (monthly) | Giovanni area-averaged time series |
| Carbon dioxide (CO₂) | OCO-2 GEOS L3 monthly V10r column-average CO₂ (2015-2022) | Giovanni area-averaged time series |
| Tree cover | MODIS Terra `MOD44B` v061 Vegetation Continuous Fields (yearly, 250 m) | AppEEARS area statistics |

- These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded
  through the NASA Earth Science/Applied Science Program.
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications,
  Version 2 (MERRA-2). *Journal of Climate*, 30, 5419-5454. https://doi.org/10.1175/JCLI-D-16-0758.1
- Krotkov, N. A., Lamsal, L. N., Marchenko, S. V., Fisher, B. L., Bucsela, E. J., Fasnacht, Z.,
  Yang, E.-S., Qin, W., Vasilkov, A., Li, C., Joiner, J., Choi, S., & Swartz, W. H. (2024).
  OMI/Aura NO2 Cloud-Screened Total and Tropospheric Column L3 Global Gridded 0.25 degree x 0.25
  degree Ver 5.0, Col 004. NASA GES DISC. https://doi.org/10.5067/AURA/OMI/DATA3407
- Area averages of NO₂, carbon monoxide, black carbon and CO₂ were produced with the Giovanni
  online data system, developed and maintained by the NASA GES DISC.
- Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. NASA EOSDIS
  Land Processes Distributed Active Archive Center. https://doi.org/10.5067/MODIS/MOD13A3.061
- NDVI and tree-cover area statistics were produced with AppEEARS (Application for Extracting and Exploring
  Analysis Ready Samples), NASA EOSDIS LP DAAC and USGS EROS Center,
  https://appeears.earthdatacloud.nasa.gov (accessed 14 November 2026).

- Doelling, D. R., Loeb, N. G., Keyes, D. F., et al. (2013). Geostationary enhanced temporal
  interpolation for CERES flux products. *Journal of Atmospheric and Oceanic Technology*, 30,
  1072-1090. https://doi.org/10.1175/JTECH-D-12-00136.1 (CERES SYN1deg, the source of NASA POWER's
  aerosol optical depth)

- Drummond, J., Gille, J., & Worden, H. MOPITT CO gridded monthly means (Near and Thermal
  Infrared Radiances) V010. NASA Langley ASDC. https://doi.org/10.5067/TERRA/MOPITT/MOP03JM_L3.010
- Global Modeling and Assimilation Office (GMAO) (2015). MERRA-2 tavgM_2d_aer_Nx: 2d, Monthly mean,
  Time-averaged, Single-Level, Assimilation, Aerosol Diagnostics V5.12.4. NASA GES DISC.
  https://doi.org/10.5067/FH9A0MLJPC7N
- Weir, B., Ott, L., & OCO-2 Science Team (2022). OCO-2 GEOS Level 3 monthly, 0.5x0.625
  assimilated CO2 V10r. NASA GES DISC. https://doi.org/10.5067/BGFIODET3HZ8
- DiMiceli, C., Sohlberg, R., & Townshend, J. (2022). MODIS/Terra Vegetation Continuous Fields
  Yearly L3 Global 250m SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD44B.061

- Huffman, G. J., Behrangi, A., Bolvin, D. T., & Nelkin, E. J. (2025). GPCP Precipitation Level 3 Monthly 0.5-Degree V3.3. NASA GES DISC. https://doi.org/10.5067/MEASURES/GPCP/DATA306
  (used as a second check of the precipitation trends for the Amazon, the Sahel and Beijing)

Methods references:
- Santer, B. D., et al. (2000). Statistical significance of trends and trend differences in
  layer-average atmospheric temperature time series. *J. Geophys. Res.*, 105, 7337-7356.
- Nychka, D., Buchberger, R., Wigley, T. M. L., Santer, B. D., Taylor, K. E., & Jones, R. (2000).
  Confidence intervals for trend estimates with autocorrelated observations. NCAR manuscript.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245-259.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin, London.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA*, 63,
  1379-1389.
- Yue, S., & Wang, C. (2004). The Mann-Kendall test modified by effective sample size to detect
  trend in serially correlated hydrological series. *Water Resources Management*, 18, 201-218.
- Hussain, M. M., & Mahmud, I. (2019). pyMannKendall: a python package for non parametric Mann
  Kendall family of trend tests. *Journal of Open Source Software*, 4(39), 1556.

Background for the "possible reasons" step:
- IPCC (2021). Summary for Policymakers. In: *Climate Change 2021: The Physical Science Basis*.
  Cambridge University Press, 3-32. https://doi.org/10.1017/9781009157896.001
- Duncan, B. N., Lamsal, L. N., Thompson, A. M., et al. (2016). A space-based, high-resolution view
  of notable changes in urban NOx pollution around the world (2005-2014). *J. Geophys. Res.
  Atmos.*, 121, 976-996. https://doi.org/10.1002/2015JD024121
- Zheng, B., Tong, D., Li, M., et al. (2018). Trends in China's anthropogenic emissions since 2010
  as the consequence of clean air actions. *Atmos. Chem. Phys.*, 18, 14095-14111.
  https://doi.org/10.5194/acp-18-14095-2018
- Herrmann, S. M., Anyamba, A., & Tucker, C. J. (2005). Recent trends in vegetation dynamics in the
  African Sahel and their relationship to climate. *Global Environmental Change*, 15, 394-404.
  https://doi.org/10.1016/j.gloenvcha.2005.08.004
- Rantanen, M., Karpechko, A. Y., Lipponen, A., et al. (2022). The Arctic has warmed nearly four
  times faster than the globe since 1979. *Communications Earth & Environment*, 3, 168.
  https://doi.org/10.1038/s43247-022-00498-3

Third-party software and map data:
- Python libraries (see `requirements.txt`): Streamlit, Plotly, pandas, NumPy, SciPy,
  pymannkendall, requests, folium, streamlit-folium.
- Map: Leaflet and Leaflet.draw (loaded by folium); map tiles and data © OpenStreetMap
  contributors (ODbL).
- Typewriter font "Special Elite" (Astigmatic, Apache License 2.0), loaded from Google Fonts.

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
python scripts/prefetch.py --region colorado   # refresh cached data (optional)
# NO2: put the Giovanni CSV downloads in data/raw as giovanni_no2_<region>_*.csv
# NDVI: put the AppEEARS statistics CSV in data/raw as appeears_ndvi_<region>_*.csv
streamlit run app.py
python -m pytest -q
```

## Project structure

```
app.py                 Streamlit app
trend/regions.py       region catalog (ten prepared regions)
trend/variables.py     measurement catalog: definitions, units, products, citations, caveats
trend/fetch.py         NASA POWER client, Giovanni loader, cached CSV storage
trend/appeears.py      AppEEARS API client (area requests and statistics downloads)
trend/stats.py         annual aggregation, OLS trend test, Mann-Kendall, confidence band
trend/area.py          custom rectangles: validation and shapes drawn on the map
trend/charts.py        Plotly charts
trend/i18n.py          English and Turkish texts, number formatting
trend/share.py         share links
trend/game.py          Detective exam game: cases, answers, explanations and the game page
scripts/prefetch.py    fetches and caches data for a region
data/processed/        small cached monthly CSVs used by the app
tests/                 unit and app tests (168)
docs/ARCHITECTURE.md   design and methods
docs/SUBMISSION.md     draft of the Space Apps project page
```

## Use of AI

Team Avni chose the challenge, the regions (Colorado, Istanbul–Marmara and eight world regions
picked from a list of options), the measurements (including dust and smoke for any rectangle, and precipitation, carbon monoxide,
soot, CO₂ and tree cover picked from a list of NASA options), the goal of keeping false results as
rare as possible, the
"secret expert detective" theme, the pick a clue → choose the period → "real or chance?" flow, the
Turkish option, the any-place-on-Earth rectangle of any size and the "possible reasons" step. Where the team asked for options (for
example page layouts and candidate regions), the AI offered some and the team chose. The
Detective exam game was one of several feature ideas the AI offered when the team asked for
creative additions; the team picked it, tested a preview and asked for the self-drawing chart,
faster play, a "why?" explanation after each answer instead of a guessing question, and a 20-case
exam.

The code, tests, interface texts (English and Turkish) and documentation drafts were written with
AI assistance: **Claude Opus 5.5** (Anthropic) wrote them, translated the team's own Turkish answers
for the project page into English, and suggested the NASA data products and statistical methods
that implement the team's choices. **Claude Fable 5.2** (Anthropic) reviewed
the plan, the statistics and the whole project and designed the pitch deck's visuals; the review
findings were fixed with AI assistance (see the commit trailers). Every
AI-assisted source file says so in its header, and AI-assisted commits carry a `Co-Authored-By`
trailer. The pitch deck's design is AI-assisted and says so on every slide; no other AI-generated
images, video or audio are used.

## License

Apache License 2.0. See [LICENSE](LICENSE). Not affiliated with or endorsed by NASA.
