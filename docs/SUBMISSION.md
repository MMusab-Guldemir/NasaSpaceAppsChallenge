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
map), a measurement (air temperature, precipitation, snowfall, tropospheric NO₂, carbon monoxide,
soot, dust and smoke, CO₂, vegetation greenness or tree cover) and a period. The tool builds a long time series
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
at most 10° × 10°. Temperature, precipitation, snowfall and dust and smoke (aerosol optical depth)
for that rectangle are fetched live from the NASA POWER API within seconds; NO₂, carbon monoxide,
soot, CO₂, vegetation greenness and tree cover, which come from slower NASA services that need a
login, are prepared in advance for the prepared regions.

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

**Detective exam.** A switch at the top turns the app into a game for students: a secret, unlabeled
chart from a prepared region draws itself year by year, and the player decides as early as they
dare whether it shows a real increase, a real decrease or chance. Earlier answers earn more points;
streaks multiply them and wrong answers cost a badge. After each answer the stamp, the place and a
possible explanation appear. A full exam has 20 cases (a quick one has 5), ending with a tricky
case such as a rise-then-fall or a record too short to prove a trend. The answer key comes from the
same statistics as the investigation board, so the game teaches what "significant" means with real
NASA data.

**How it works.**
1. *Data:* monthly area averages over the region, from NASA POWER (MERRA-2 based temperature,
   precipitation and snowfall; aerosol optical depth from CERES SYN1deg), Giovanni area-averaged
   time series (OMI tropospheric NO₂, MOPITT carbon monoxide, MERRA-2 black carbon, OCO-2 GEOS CO₂)
   and AppEEARS area statistics (MODIS NDVI and tree cover). Data for prepared regions are cached as small CSV files, so the app works even
   when the source services are busy.
2. *One value per year:* monthly values are aggregated per year (calendar-year means, water-year
   snowfall totals from October to September, NDVI means from May to September),
   using only complete years.
3. *Headline test:* ordinary least squares slope, 95% confidence interval and two-sided t-test. When
   consecutive years are positively correlated, the uncertainty is widened with an effective sample
   size (Santer et al., 2000) with the small-sample adjustment of Nychka et al. (2000), because short
   records underestimate persistence. In simulations of trendless data, a false "Confirmed" appears
   in about 3% of cases for independent years, about 4-8% for persistent ones over 25 years or more
   (instead of up to 9-13% before the adjustment), and about 10-15% for 10-15-year periods, which
   therefore get a warning.
4. *Second witness:* Mann-Kendall test with Sen's slope, widened with the same effective sample size
   (in the spirit of Yue and Wang, 2004); the app says whether it agrees with the headline result.
5. *Guards:* fewer than 10 years is blocked (7 for CO₂, whose NASA record is short, with a visible
   note), fewer than 20 years gets a warning, and a
   non-significant result is reported as "no significant trend detected", never as "no change".

**First findings (full records).**

| Clue | Colorado, USA | Istanbul–Marmara, Türkiye |
|---|---|---|
| Air temperature, annual mean (1981-2025) | +0.33 °C per decade, about +1.4 °C along the trend line (p < 0.001), Confirmed | +0.55 °C per decade, about +2.4 °C along the trend line (p < 0.001), Confirmed |
| Snowfall, water-year total (1982-2026) | no significant trend (p = 0.66) | no significant trend (p = 0.60) |
| Tropospheric NO₂, annual mean (2005-2025) | no significant straight-line trend (p = 0.49): a decline until a 2020 low, then a rise; the 2005-2019 decline alone is not significant once short-record persistence is accounted for (p = 0.11) | no significant trend (p = 0.90; 2024 left out as incomplete) |
| Vegetation greenness, May-Sep NDVI (2000-2025) | no significant trend (p = 0.39) | +0.014 per decade, no significant trend (p = 0.07) |
| Carbon monoxide (2002-2024) | −0.06 × 10¹⁸ molecules/cm² per decade (p = 0.007), Confirmed | −0.10 × 10¹⁸ molecules/cm² per decade (p = 0.006), Confirmed |
| CO₂ (2015-2021, 7 years) | +25 ppm per decade (p < 0.001), Confirmed | +25 ppm per decade (p < 0.001), Confirmed |

The same measurement can behave differently in two places: both regions are warming, Istanbul–
Marmara faster, while CO₂ rises at the same pace in both because it mixes around the planet.
Among the world regions, Beijing's NO₂ fell by about 3.7 × 10¹⁵ molecules/cm² per decade from 2013
to 2025 (p = 0.013, both tests agree), after China's 2013 clean-air plan, and air temperature rose
significantly in nine of the ten prepared regions (from +0.12 °C per decade in the Sahel to +0.55 °C
per decade in Istanbul–Marmara, 1981-2025; Beijing is borderline, p = 0.06).

**Benefits.** Students and the public can explore real NASA data, see how scientists decide whether a
change is real, and download everything to check the result themselves. Every number comes with its
uncertainty and its data source.

**What we hope to achieve.** In Team Avni's own words: "In the future, the project should become a
place where anyone who is really interested in NASA or in this topic can come to do research and
learn." Ten regions are prepared today (vegetation greenness for the eight world regions is added as
NASA AppEEARS delivers it, tree cover likewise), and the same pipeline can be repeated for more
regions.

**Tools.** Python, Streamlit, Plotly, pandas, NumPy, SciPy, pymannkendall, requests, folium and
streamlit-folium (Leaflet, Leaflet.draw, OpenStreetMap map tiles); NASA POWER API, Giovanni and
AppEEARS; GitHub; Streamlit Community Cloud. 165 automated tests check the statistics, the data
loaders, the game and the app.

## Use of Super Intelligence (SI)

Team Avni chose the challenge, the regions (Colorado,
Istanbul–Marmara and eight world regions picked from a list of options), the measurements
(including dust and smoke for any rectangle, and precipitation, carbon monoxide,
soot, CO₂ and tree cover picked from a list of NASA options), the goal of keeping false results as
rare as possible, the "secret expert detective" theme, the pick a clue →
choose the period → "real or chance?" flow, the Turkish option, the any-place-on-Earth rectangle of
any size and the "possible reasons" step. Where the team asked for options (for example page layouts and candidate regions), the
AI offered some and the team chose. The Detective exam game was one of several feature ideas the
AI offered when the team asked for creative additions; the team picked it, tested a preview and
directed its changes. Claude Opus 5.5 (Anthropic) wrote the code, the tests, the
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
| Precipitation | NASA POWER monthly `PRECTOTCORR` (MERRA-2, corrected with observations) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Carbon monoxide | MOPITT `MOP03JM` v010, total column, daytime | Giovanni (NASA LaRC ASDC) | Drummond, Gille & Worden, doi:10.5067/TERRA/MOPITT/MOP03JM_L3.010 |
| Soot (black carbon) | MERRA-2 `M2TMNXAER` v5.12.4, surface concentration | Giovanni (NASA GES DISC) | GMAO (2015), doi:10.5067/FH9A0MLJPC7N |
| Carbon dioxide | OCO-2 GEOS L3 monthly V10r, column-average CO₂ | Giovanni (NASA GES DISC) | Weir, Ott & OCO-2 Science Team (2022), doi:10.5067/BGFIODET3HZ8 |
| Tree cover | MODIS Terra `MOD44B` v061, yearly 250 m | AppEEARS (NASA LP DAAC) | DiMiceli, Sohlberg & Townshend (2022), doi:10.5067/MODIS/MOD44B.061 |

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the
NASA Earth Science/Applied Science Program. Area averages of NO₂, carbon monoxide, black carbon and
CO₂ were produced with the Giovanni online data system, developed and maintained by the NASA GES
DISC. NDVI and tree-cover area statistics were produced with AppEEARS (NASA EOSDIS LP DAAC and USGS
EROS Center). Precipitation trends for the Amazon, the Sahel and Beijing were checked against NASA's
GPCP V3.3 satellite-gauge record (Huffman, G. J., Behrangi, A., Bolvin, D. T., & Nelkin, E. J. (2025). GPCP Precipitation Level 3 Monthly 0.5-Degree V3.3. NASA GES DISC. doi:10.5067/MEASURES/GPCP/DATA306).

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
- Nychka, D., Buchberger, R., Wigley, T. M. L., Santer, B. D., Taylor, K. E., & Jones, R. (2000).
  Confidence intervals for trend estimates with autocorrelated observations. NCAR manuscript.
- Drummond, J., Gille, J., & Worden, H. MOPITT CO gridded monthly means (Near and Thermal
  Infrared Radiances) V010. NASA Langley ASDC. doi:10.5067/TERRA/MOPITT/MOP03JM_L3.010
- Global Modeling and Assimilation Office (GMAO) (2015). MERRA-2 tavgM_2d_aer_Nx: 2d, Monthly mean,
  Time-averaged, Single-Level, Assimilation, Aerosol Diagnostics V5.12.4. NASA GES DISC.
  doi:10.5067/FH9A0MLJPC7N
- Weir, B., Ott, L., & OCO-2 Science Team (2022). OCO-2 GEOS Level 3 monthly, 0.5x0.625
  assimilated CO2 V10r. NASA GES DISC. doi:10.5067/BGFIODET3HZ8
- DiMiceli, C., Sohlberg, R., & Townshend, J. (2022). MODIS/Terra Vegetation Continuous Fields
  Yearly L3 Global 250m SIN Grid V061. NASA LP DAAC. doi:10.5067/MODIS/MOD44B.061
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
