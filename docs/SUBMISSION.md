# Project Submission Draft (NASA Space Apps Challenge 2026)

> Working draft for the Space Apps project page. Written with AI assistance (Claude Opus 5.5).
> Sections marked **[TEAM]** must be written or confirmed by Team Avni: the project concept and
> the "detective" experience come from the team.

## Project Name

Earth System Trend Detective **[TEAM: confirm the final name]**

## High-Level Project Summary

Earth System Trend Detective is a free web tool that turns NASA Earth observations into clear,
checkable answers to four questions: **what** is changing, **where**, **by how much**, and **is the
change statistically significant?** A user picks a region, a measurement (air temperature, snowfall,
tropospheric NO₂ or vegetation greenness) and a period. The tool builds a long time series from NASA
data, removes the seasonal cycle by using one value per year, fits a linear trend, and reports the
rate of change per decade with its 95% confidence interval and a significance test. A second,
assumption-light test (Mann-Kendall with Sen's slope) acts as a "second opinion". Results come with
plain-language explanations, so high school and college students can investigate environmental
change like data detectives. The whole app is built around an **expert detective** theme: an
investigation board shows every clue for a region with a verdict stamp ("Confirmed", "No evidence"),
and each case file walks through the question, the evidence, the verdict and a second witness.

## Link to Project Demo

**[TODO]** 30-second video (or at most 7 slides), publicly accessible, English subtitles if spoken
in Turkish.

## Link to Final Project

- Live app: https://avni-trend-detective.streamlit.app
- Source code: https://github.com/MMusab-Guldemir/NasaSpaceAppsChallenge

## Detailed Project Description

**What it does.** The user opens an **investigation board** for a region: one clue card per
measurement, each with its rate of change and a verdict stamp (Confirmed, Disputed, No evidence,
Weak clue or Open case). Opening a **case file** shows (1) the question, (2) the evidence: a chart
of annual values with the fitted trend line, its 95% confidence band and a period selector, (3) the
verdict: What / Where / How much / Significant? plus a plain-language explanation, (4) the second
witness: an independent test, and (5) case notes with caveats, monthly data, a data table, CSV
downloads and the methods.

**How it works.**
1. *Data:* monthly area averages over the region, from NASA POWER (MERRA-2 based temperature and
   snowfall), OMI tropospheric NO₂ (Giovanni area-averaged time series) and MODIS NDVI (AppEEARS).
   Data are cached as small CSV files so the app works even when the source services are busy.
2. *One value per year:* monthly values are aggregated per year (calendar-year means, water-year
   snowfall totals from October to September, growing-season NDVI means), using only complete years.
3. *Headline test:* ordinary least squares slope, 95% confidence interval and two-sided t-test. When
   consecutive years are positively correlated, the uncertainty is widened with an effective sample
   size (Santer et al., 2000), so results are not overconfident.
4. *Second opinion:* Mann-Kendall test with Sen's slope (Hamed-Rao correction when needed); the app
   says whether it agrees with the headline result.
5. *Guards:* fewer than 10 years is blocked, fewer than 20 years gets a warning, and a
   non-significant result is reported as "no significant trend detected", never as "no change".

**First findings for Colorado.**
- Annual mean air temperature rose by about +0.33 °C per decade from 1981 to 2025 (about +1.4 °C in
  total along the trend line; p < 0.001; the second opinion agrees).
- Water-year snowfall shows no significant trend from 1982 to 2026 (p = 0.66).
- Tropospheric NO₂ declined until a 2020 low and rose afterwards; the straight-line trend over
  2005-2025 is not significant (p = 0.23), while the decline is clear when the period is limited
  to 2005-2019.

**Benefits.** Students and the public can explore real NASA data, see how scientists decide whether a
change is real, and download everything to check the result themselves. Every number comes with its
uncertainty and its data source.

**What we hope to achieve.** A tool that the team itself, the judges and later anyone can use to
investigate environmental change the way a secret, expert detective would: following the evidence,
calling a second witness, and only declaring a case "Confirmed" when the statistics support it.
After Colorado, the same pipeline will be repeated for more regions. **[TEAM: confirm or reword.]**

**Tools.** Python, Streamlit, Plotly, pandas, NumPy, SciPy, statsmodels, pymannkendall, requests;
NASA POWER API, Giovanni and AppEEARS; GitHub; Streamlit Community Cloud. 31 automated tests check
the statistics, the data loaders and the app.

## Use of Super Intelligence (SI)

The project idea and all product decisions come from Team Avni, including the choice of challenge,
region, measurements and the "secret expert detective" theme. Claude Opus 5.5 (Anthropic) wrote the
code and the documentation drafts, following the team's decisions; it also proposed three layout
options for the detective theme, and the team chose the investigation-board-and-case-file layout. Claude Fable (Anthropic) reviewed
the architecture plan and the statistics code; its review comments were applied by the code author.
Every AI-assisted source file says so in its header, AI-assisted commits carry a `Co-Authored-By`
trailer, and the README has a "Use of AI" section. No AI-generated images, video or audio are used.

## NASA Data

| Measurement | Product | Access | Reference |
|---|---|---|---|
| Air temperature at 2 m | NASA POWER monthly `T2M` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based) | POWER API | Gelaro et al. (2017), doi:10.1175/JCLI-D-16-0758.1 |
| Tropospheric NO₂ | OMI `OMNO2d` v004, 30% cloud screened | Giovanni (NASA GES DISC) | OMI OMNO2d Level 3 daily product, NASA GES DISC |
| Vegetation greenness | MODIS Terra `MOD13A3` v061, monthly 1 km NDVI | AppEEARS (NASA LP DAAC) | Didan (2021), doi:10.5067/MODIS/MOD13A3.061 |

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the
NASA Earth Science/Applied Science Program.

## Space Agency Partner Data and Other References

- No Space Agency Partner data used yet.
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications,
  Version 2 (MERRA-2). *Journal of Climate*, 30, 5419-5454.
- Santer, B. D., et al. (2000). Statistical significance of trends and trend differences in
  layer-average atmospheric temperature time series. *J. Geophys. Res.*, 105, 7337-7356.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245-259.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin, London.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA*, 63, 1379-1389.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann-Kendall trend test for autocorrelated data.
  *Journal of Hydrology*, 204, 182-196.
- Hussain, M. M., & Mahmud, I. (2019). pyMannKendall: a python package for non parametric Mann Kendall
  family of trend tests. *Journal of Open Source Software*, 4(39), 1556.
- Open-source software: Streamlit, Plotly, pandas, NumPy, SciPy, statsmodels, requests (see
  `requirements.txt` for versions).

## 30-Second Demo Plan (draft)

Following the Space Apps template; the narration and visuals should be recorded by the team.

| Time | What to show | What to say (English, or Turkish with English subtitles) |
|---|---|---|
| 0:00-0:02 | Title card | Name and team name |
| 0:02-0:05 | Challenge name | Which challenge and why you chose it **[TEAM]** |
| 0:05-0:10 | App home screen | Project title and one-line tagline **[TEAM]** |
| 0:10-0:20 | Pick Colorado + air temperature, then NO₂ with the period slider | How it works, using free NASA data |
| 0:20-0:30 | Result card and chart | What it can do for students and the world **[TEAM]** |
