# Project Submission Draft (NASA Space Apps Challenge 2026)

> Working draft for the Space Apps project page. Written with AI assistance (Claude Opus 5.5).
> Sections marked **[TEAM]** must be written or confirmed by Team Avni: the project concept and
> the "detective" experience come from the team. Remove this note and every [TEAM] marker before
> copying the text to the project page.

## Project Name

Earth System Trend Detective **[TEAM: confirm the final name]**

## High-Level Project Summary

Earth System Trend Detective is a free web tool that turns NASA Earth observations into clear,
checkable answers to four questions: **what** is changing, **where**, **by how much**, and **is the
change statistically significant?** A user picks a region (two prepared regions, Colorado and
Istanbul–Marmara, or any rectangle on Earth drawn on a world map), a measurement (air temperature,
snowfall, tropospheric NO₂ or vegetation greenness) and a period. The tool builds a long time series
from NASA data, removes the seasonal cycle by using one value per year, fits a linear trend, and
reports the rate of change per decade with its 95% confidence interval and a significance test. A
second test of a different kind (Mann-Kendall with Sen's slope) acts as a "second witness". Results
come with plain-language explanations, so high school and college students can investigate
environmental change like data detectives. The whole app is built around an **expert detective**
theme: an investigation board shows every clue for a region with a verdict stamp ("Confirmed",
"No evidence"), and each case file walks through the question, the evidence, the verdict and the
second witness.

## Link to Project Demo

**[TODO]** 30-second video (or at most 7 slides), publicly accessible, English subtitles if spoken
in Turkish.

## Link to Final Project

- Live app: https://avni-trend-detective.streamlit.app
- Source code: https://github.com/MMusab-Guldemir/NasaSpaceAppsChallenge

## Detailed Project Description

**Any place on Earth.** Besides prepared regions, users can draw, move and resize a rectangle on a
world map, or type its corners, to investigate any area of 2° to 10° on each side. Temperature and
snowfall for that rectangle are fetched live from the NASA POWER API within seconds; air pollution
and vegetation, which come from slower NASA services, are prepared in advance for the prepared
regions.

**What it does.** The user opens an **investigation board** for a region: one clue card per
measurement, each with its rate of change and a verdict stamp (Confirmed, Disputed, No evidence,
Weak clue or Open case) and a small sparkline. After picking a clue, the user (1) chooses the
period, (2) immediately sees a large **"Real or chance?"** verdict with a chance meter that places
the p-value against the 5% line, plus how much changed per decade and in total, (3) inspects the
evidence: annual values with the fitted trend line and its 95% confidence band, (4) hears the
second witness: a second test of a different kind (rank-based, with no straight-line assumption),
and (5) reads case notes with caveats, monthly data, a data table, CSV downloads, the methods and a
share link that reopens exactly that case. An EN / TR switch in the top right shows the whole app
in English (default) or Turkish.

**How it works.**
1. *Data:* monthly area averages over the region, from NASA POWER (MERRA-2 based temperature and
   snowfall), OMI tropospheric NO₂ (Giovanni area-averaged time series) and MODIS NDVI (AppEEARS
   area statistics). Data for prepared regions are cached as small CSV files, so the app works even
   when the source services are busy.
2. *One value per year:* monthly values are aggregated per year (calendar-year means, water-year
   snowfall totals from October to September, growing-season NDVI means from May to September),
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

**Benefits.** Students and the public can explore real NASA data, see how scientists decide whether a
change is real, and download everything to check the result themselves. Every number comes with its
uncertainty and its data source.

**What we hope to achieve.** A tool that the team itself, the judges and later anyone can use to
investigate environmental change the way a secret, expert detective would: following the evidence,
calling a second witness, and only declaring a case "Confirmed" when the statistics support it.
Colorado and Istanbul–Marmara are prepared with all four measurements, and the same pipeline can be
repeated for more regions. **[TEAM: confirm or reword.]**

**Tools.** Python, Streamlit, Plotly, pandas, NumPy, SciPy, pymannkendall, requests, folium and
streamlit-folium (Leaflet, Leaflet.draw, OpenStreetMap map tiles); NASA POWER API, Giovanni and
AppEEARS; GitHub; Streamlit Community Cloud. 91 automated tests check the statistics, the data
loaders and the app.

## Use of Super Intelligence (SI)

**[TEAM: confirm this text.]** Team Avni chose the challenge, the regions (Colorado and
Istanbul–Marmara), the four measurements, the "secret expert detective" theme, the pick a clue →
choose the period → "real or chance?" flow, the Turkish option and the any-place-on-Earth
rectangle. Where the team asked for options (for example page layouts and candidate regions), the
AI offered some and the team chose. Claude Opus 5.5 (Anthropic) wrote the code, the tests, the
interface texts (English and Turkish) and the documentation drafts, and suggested the NASA data
products and statistical methods that implement the team's choices. Claude Fable 5.2 (Anthropic)
reviewed the plan, the statistics and the whole project; Claude Opus 5.5 fixed the review findings.
Every AI-assisted source file says so in its header, AI-assisted commits carry a `Co-Authored-By`
trailer, and the README has a "Use of AI" section. No AI-generated images, video or audio are used.

## NASA Data

| Measurement | Product | Access | Reference |
|---|---|---|---|
| Air temperature at 2 m | NASA POWER monthly `T2M` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Tropospheric NO₂ | OMI `OMNO2d` v004, 30% cloud screened | Giovanni (NASA GES DISC) | Krotkov et al. (2024), doi:10.5067/AURA/OMI/DATA3407 |
| Vegetation greenness | MODIS Terra `MOD13A3` v061, monthly 1 km NDVI | AppEEARS (NASA LP DAAC) | Didan (2021), doi:10.5067/MODIS/MOD13A3.061 |

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the
NASA Earth Science/Applied Science Program. Area averages of NO₂ were produced with the Giovanni
online data system, developed and maintained by the NASA GES DISC. NDVI area statistics were
produced with AppEEARS (NASA EOSDIS LP DAAC and USGS EROS Center).

## Space Agency Partner Data and Other References

- No Space Agency Partner data used.
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

## 30-Second Demo Plan (draft)

Following the Space Apps template; the narration and visuals should be recorded by the team.

| Time | What to show | What to say (English, or Turkish with English subtitles) |
|---|---|---|
| 0:00-0:02 | Title card | Name and team name |
| 0:02-0:05 | Challenge name | Which challenge and why you chose it **[TEAM]** |
| 0:05-0:10 | App home screen | Project title and one-line tagline **[TEAM]** |
| 0:10-0:20 | Pick Colorado + air temperature, then NO₂ with the period slider | How it works, using free NASA data |
| 0:20-0:30 | Result card and chart | What it can do for students and the world **[TEAM]** |
