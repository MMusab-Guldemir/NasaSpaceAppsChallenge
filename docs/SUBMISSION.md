# Project Submission Text (NASA Space Apps Challenge 2026)

> Text for the Space Apps project page. The ideas, decisions and the answers in "Why this challenge",
> the tagline and "What we hope to achieve" come from Team Avni (translated from Turkish); the text
> was drafted with AI assistance (Claude Opus 5.5). See "Use of Super Intelligence (SI)".

## Project Name

Earth System Trend Detective

**Tagline:** Finding out whether the changes happening in our world are chance or have a reason.

## High-Level Project Summary

Earth System Trend Detective is a free web tool that turns NASA Earth observations into clear,
checkable answers to four questions: **what** is changing, **where**, **by how much**, and **is the
change statistically significant?** A user picks a region (ten prepared regions from Colorado and
Istanbul–Marmara to Beijing, the Amazon and Siberia, or any rectangle on Earth drawn on a world
map), a measurement (air temperature, snowfall, tropospheric NO₂, dust and smoke, or vegetation
greenness) and a period. The tool builds a long time series
from NASA data, removes the seasonal cycle by using one value per year, fits a linear trend, and
reports the rate of change per decade with its 95% confidence interval and a significance test. A
second test of a different kind (Mann-Kendall with Sen's slope) acts as a "second witness". Results
come with plain-language explanations, so high school and college students can investigate
environmental change like data detectives. The whole app is built around an **expert detective**
theme: an investigation board shows every clue for a region with a verdict stamp ("Confirmed",
"No evidence"), and each case file walks through the question, the evidence, the verdict and the
second witness.

## Link to Project Demo

7-slide pitch deck (PDF, public, no login):
https://github.com/MMusab-Guldemir/NasaSpaceAppsChallenge/blob/main/docs/pitch/TrendDetective_TeamAvni_Pitch.pdf

The detective concept comes from Team Avni, who also chose the deck's story and style from
AI-proposed options. The slides' visual design is AI-assisted (Claude Fable 5.2, coordinated by
Claude Opus 5.5), and every slide carries a visible "AI-assisted design" line. All charts are drawn
from the app's own NASA data and statistics code.

## Link to Final Project

- Live app: https://avni-trend-detective.streamlit.app
- Source code: https://github.com/MMusab-Guldemir/NasaSpaceAppsChallenge

## Detailed Project Description

**Why this challenge.** In Team Avni's own words: "I chose this challenge because it is much
harder than the other topics, and it interested me more than any of the others."

**Any place on Earth.** Besides ten prepared regions, users can draw, move and resize a rectangle
on a world map, or type its corners, to investigate any area from 0.01° to 40° on each side. A
rectangle smaller than NASA's grid uses the nearest grid cell; a large one is fetched in pieces of
at most 10° × 10°. Temperature, snowfall and dust and smoke (aerosol optical depth) for that
rectangle are fetched live from the NASA POWER API within seconds; air pollution (NO₂) and
vegetation, which come from slower NASA services that need a login, are prepared in advance for
the prepared regions.

**What it does.** The user opens an **investigation board** for a region: one clue card per
measurement, each with its rate of change, a verdict stamp (Confirmed, Disputed, No evidence, Weak clue, Open case; plus No snow, Not enough data and No data where they apply) and a small sparkline. After picking a clue, the user (1) chooses the
period, (2) immediately sees a large **"Real or chance?"** verdict with a chance meter that places
the p-value against the 5% line, plus how much changed per decade and in total, (3) inspects the
evidence: annual values with the fitted trend line and its 95% confidence band, (4) hears the
second witness: a second test of a different kind (rank-based, with no straight-line assumption),
(5) reads possible reasons for the result (common explanations from research, plus local
context, with a clear note that the test shows that something changed, not why), and (6) reads
case notes with caveats, monthly data, a data table, CSV downloads, the methods and a
share link that reopens exactly that case. An EN / TR switch in the top right shows the whole app
in English (default) or Turkish.

**How it works.**
1. *Data:* monthly area averages over the region, from NASA POWER (MERRA-2 based temperature and
   snowfall; aerosol optical depth from CERES SYN1deg), OMI tropospheric NO₂ (Giovanni
   area-averaged time series) and MODIS NDVI (AppEEARS area statistics). Data for prepared regions are cached as small CSV files, so the app works even
   when the source services are busy.
2. *One value per year:* monthly values are aggregated per year (calendar-year means, water-year
   snowfall totals from October to September, NDVI means from May to September),
   using only complete years.
3. *Headline test:* ordinary least squares slope, 95% confidence interval and two-sided t-test. When
   consecutive years are positively correlated, the uncertainty is widened with an effective sample
   size (Santer et al., 2000), so results are less overconfident (for short records the correction
   is only partial).
4. *Second witness:* Mann-Kendall test with Sen's slope, widened with the same effective sample size
   (in the spirit of Yue and Wang, 2004); the app says whether it agrees with the headline result.
5. *Guards:* fewer than 10 years is blocked, fewer than 20 years gets a warning, and a
   non-significant result is reported as "no significant trend detected", never as "no change".

**First findings (full records).**

| Clue | Colorado, USA | Istanbul–Marmara, Türkiye |
|---|---|---|
| Air temperature, annual mean (1981-2025) | +0.33 °C per decade, about +1.4 °C along the trend line (p < 0.001), Confirmed | +0.55 °C per decade, about +2.4 °C along the trend line (p < 0.001), Confirmed |
| Snowfall, water-year total (1982-2026) | no significant trend (p = 0.66) | no significant trend (p = 0.60) |
| Tropospheric NO₂, annual mean (2005-2025) | no significant straight-line trend (p = 0.23): a decline until a 2020 low, then a rise; the pre-pandemic decline 2005-2019 alone is significant (p = 0.016) | no significant trend (p = 0.87; 2024 left out as incomplete) |
| Vegetation greenness, May-Sep NDVI (2000-2025) | no significant trend (p = 0.39) | +0.014 per decade (p = 0.03), but the second witness disagrees (p = 0.07), so the case is Disputed |

The same measurement can behave differently in two places: both regions are warming, Istanbul–
Marmara faster, and Colorado's NO₂ fell until 2019 while Istanbul–Marmara's shows no clear change.
Among the world regions, Beijing's NO₂ fell by about 3.7 × 10¹⁵ molecules/cm² per decade from 2013
to 2025 (p < 0.001, both tests agree), after China's 2013 clean-air plan, and air temperature rose
significantly in every prepared region (from +0.12 °C per decade in the Sahel to +0.55 °C per
decade in Istanbul–Marmara, 1981-2025).

**Benefits.** Students and the public can explore real NASA data, see how scientists decide whether a
change is real, and download everything to check the result themselves. Every number comes with its
uncertainty and its data source.

**What we hope to achieve.** In Team Avni's own words: "In the future, the project should become a
place where anyone who is really interested in NASA or in this topic can come to do research and
learn." Ten regions are prepared today (vegetation greenness for the eight world regions is added as
NASA AppEEARS delivers it), and the same pipeline can be repeated for more regions.

**Tools.** Python, Streamlit, Plotly, pandas, NumPy, SciPy, pymannkendall, requests, folium and
streamlit-folium (Leaflet, Leaflet.draw, OpenStreetMap map tiles); NASA POWER API, Giovanni and
AppEEARS; GitHub; Streamlit Community Cloud. 118 automated tests check the statistics, the data
loaders and the app.

## Use of Super Intelligence (SI)

Team Avni chose the challenge, the regions (Colorado,
Istanbul–Marmara and eight world regions picked from a list of options), the measurements
(including dust and smoke for any rectangle), the "secret expert detective" theme, the pick a clue →
choose the period → "real or chance?" flow, the Turkish option, the any-place-on-Earth rectangle of
any size and the "possible reasons" step. Where the team asked for options (for example page layouts and candidate regions), the
AI offered some and the team chose. Claude Opus 5.5 (Anthropic) wrote the code, the tests, the
interface texts (English and Turkish) and the documentation drafts, translated the team's own
Turkish answers for this page into English, and suggested the NASA data products and statistical
methods that implement the team's choices. Claude Fable 5.2 (Anthropic)
reviewed the plan, the statistics and the whole project; Claude Opus 5.5 fixed the review findings.
Every AI-assisted source file says so in its header, AI-assisted commits carry a `Co-Authored-By`
trailer, and the README has a "Use of AI" section. The pitch deck's design is AI-assisted and says
so on every slide; no other AI-generated images, video or audio are used.

## NASA Data

| Measurement | Product | Access | Reference |
|---|---|---|---|
| Air temperature at 2 m | NASA POWER monthly `T2M` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Tropospheric NO₂ | OMI `OMNO2d` v004, 30% cloud screened | Giovanni (NASA GES DISC) | Krotkov et al. (2024), doi:10.5067/AURA/OMI/DATA3407 |
| Vegetation greenness | MODIS Terra `MOD13A3` v061, monthly 1 km NDVI | AppEEARS (NASA LP DAAC) | Didan (2021), doi:10.5067/MODIS/MOD13A3.061 |
| Dust and smoke | NASA POWER monthly `AOD_55` (CERES SYN1deg, about 1°) | POWER API | Doelling et al. (2013), doi:10.1175/JTECH-D-12-00136.1 |

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the
NASA Earth Science/Applied Science Program. Area averages of NO₂ were produced with the Giovanni
online data system, developed and maintained by the NASA GES DISC. NDVI area statistics were
produced with AppEEARS (NASA EOSDIS LP DAAC and USGS EROS Center).

## Space Agency Partner Data and Other References

- No Space Agency Partner data used.
- IPCC (2021). Summary for Policymakers. In: *Climate Change 2021: The Physical Science Basis*.
  Cambridge University Press, 3-32. doi:10.1017/9781009157896.001
- Duncan, B. N., Lamsal, L. N., Thompson, A. M., et al. (2016). A space-based, high-resolution view
  of notable changes in urban NOx pollution around the world (2005-2014). *J. Geophys. Res.
  Atmos.*, 121, 976-996. doi:10.1002/2015JD024121
- Zheng, B., Tong, D., Li, M., et al. (2018). Trends in China's anthropogenic emissions since 2010
  as the consequence of clean air actions. *Atmos. Chem. Phys.*, 18, 14095-14111.
  doi:10.5194/acp-18-14095-2018
- Herrmann, S. M., Anyamba, A., & Tucker, C. J. (2005). Recent trends in vegetation dynamics in the
  African Sahel and their relationship to climate. *Global Environmental Change*, 15, 394-404.
  doi:10.1016/j.gloenvcha.2005.08.004
- Rantanen, M., Karpechko, A. Y., Lipponen, A., et al. (2022). The Arctic has warmed nearly four
  times faster than the globe since 1979. *Communications Earth & Environment*, 3, 168.
  doi:10.1038/s43247-022-00498-3
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications,
  Version 2 (MERRA-2). *Journal of Climate*, 30, 5419-5454.
- Krotkov, N. A., Lamsal, L. N., Marchenko, S. V., Fisher, B. L., Bucsela, E. J., Fasnacht, Z.,
  Yang, E.-S., Qin, W., Vasilkov, A., Li, C., Joiner, J., Choi, S., & Swartz, W. H. (2024).
  OMI/Aura NO2 Cloud-Screened Total and Tropospheric Column L3 Global Gridded 0.25 degree x 0.25
  degree Ver 5.0, Col 004. NASA GES DISC. doi:10.5067/AURA/OMI/DATA3407
- Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. NASA EOSDIS
  Land Processes Distributed Active Archive Center. doi:10.5067/MODIS/MOD13A3.061
- AppEEARS Team. Application for Extracting and Exploring Analysis Ready Samples (AppEEARS). NASA
  EOSDIS LP DAAC and USGS EROS Center. https://appeears.earthdatacloud.nasa.gov (accessed
  14 November 2026).
- Doelling, D. R., Loeb, N. G., Keyes, D. F., et al. (2013). Geostationary enhanced temporal
  interpolation for CERES flux products. *Journal of Atmospheric and Oceanic Technology*, 30,
  1072-1090. doi:10.1175/JTECH-D-12-00136.1
- Santer, B. D., et al. (2000). Statistical significance of trends and trend differences in
  layer-average atmospheric temperature time series. *J. Geophys. Res.*, 105, 7337-7356.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245-259.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin, London.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA*, 63, 1379-1389.
- Yue, S., & Wang, C. (2004). The Mann-Kendall test modified by effective sample size to detect
  trend in serially correlated hydrological series. *Water Resources Management*, 18, 201-218.
- Hussain, M. M., & Mahmud, I. (2019). pyMannKendall: a python package for non parametric Mann Kendall
  family of trend tests. *Journal of Open Source Software*, 4(39), 1556.
- Open-source software: Streamlit, Plotly, pandas, NumPy, SciPy, pymannkendall, requests, folium,
  streamlit-folium (see `requirements.txt` for versions); Leaflet and Leaflet.draw for the map.
- Map tiles and map data © OpenStreetMap contributors (Open Database License).
- "Special Elite" typewriter font by Astigmatic (Apache License 2.0), via Google Fonts.

## 30-Second Video Plan (optional; the submitted demo is the 7-slide deck)

Following the Space Apps template, in case the team also records a video.

| Time | What to show | What to say (English, or Turkish with English subtitles) |
|---|---|---|
| 0:00-0:02 | Title card | Name and team name |
| 0:02-0:05 | Challenge name | "Be An Earth System Trend Detective!": harder than the others, and the most interesting to me |
| 0:05-0:10 | App home screen | Earth System Trend Detective: finding out whether the changes in our world are chance or have a reason |
| 0:10-0:20 | Pick Colorado + air temperature, then NO₂ with the period slider | How it works, using free NASA data |
| 0:20-0:30 | Result card and chart | A place where anyone interested in NASA or this topic can research and learn |
