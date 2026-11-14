# Earth System Trend Detective

**Team Avni · NASA Space Apps Challenge 2026 · Challenge: "Be An Earth System Trend Detective!"**

Pick a place and a measurement from NASA Earth data, and find out **what** is changing,
**where**, **by how much**, and **whether the change is statistically significant**.

> Work in progress during the hackathon (14-15 November 2026).

## What it does

1. **Where?** Pick a prepared region (Colorado, with all four measurements) or investigate
   **anywhere on Earth**: draw, move or resize a rectangle on the world map, or type its corners
   in the left sidebar. Temperature and snowfall for custom rectangles (2° to 10° wide) are fetched
   live from NASA POWER; air pollution and vegetation are prepared in advance for selected regions.
2. An **investigation board** shows every clue for the area: one card per measurement with its
   rate of change and a verdict stamp.
2. The user picks a clue, chooses the **period**, and immediately gets a large
   **"Real or chance?"** verdict with a chance meter, followed by the evidence (chart) and a
   second witness. An **EN / TR** switch (top right) shows the whole app in English or Turkish.
3. Behind the scenes, NASA monthly data become one value per year (removing the seasonal cycle).
4. The app fits a linear trend and reports:
   - the **rate of change per decade** with its 95% confidence interval,
   - whether the trend is **significant** (two-sided t-test, adjusted for year-to-year persistence),
   - a **second opinion** from the Mann-Kendall test with Sen's slope,
   - a plain-language summary for students and the public.
5. Charts, a data table, CSV downloads and a "How the detective works" section make every result checkable.

First results for Colorado:
- Annual mean air temperature rose by about **+0.33 °C per decade** (1981-2025, p < 0.001).
- Water-year snowfall shows **no significant trend** (1982-2026, p = 0.66).
- Tropospheric NO₂ fell from 2005 to a low in 2020 and rose again afterwards, so the straight-line
  trend over 2005-2025 is **not significant** (p = 0.23 after correcting for year-to-year persistence).

## Data

| Measurement | NASA product | Access |
|---|---|---|
| Air temperature | NASA POWER monthly `T2M` (MERRA-2 based) | POWER API |
| Snowfall | NASA POWER monthly `PRECSNOLAND` (MERRA-2 based) | POWER API |
| Air pollution (NO₂) | OMI `OMNO2d` v004 tropospheric column (daily, averaged per month) | Giovanni area-averaged time series |
| Vegetation greenness (NDVI) | MODIS Terra `MOD13A3` v061 (monthly, 1 km) | AppEEARS (in progress) |

- These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded
  through the NASA Earth Science/Applied Science Program.
- Gelaro, R., et al. (2017). The Modern-Era Retrospective Analysis for Research and Applications,
  Version 2 (MERRA-2). *Journal of Climate*, 30, 5419-5454. https://doi.org/10.1175/JCLI-D-16-0758.1
- Santer, B. D., et al. (2000). Statistical significance of trends and trend differences in
  layer-average atmospheric temperature time series. *J. Geophys. Res.*, 105, 7337-7356.

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
python scripts/prefetch.py --region colorado   # refresh cached data (optional)
# NO2: put the Giovanni CSV downloads in data/raw as giovanni_no2_*.csv before running prefetch
streamlit run app.py
python -m pytest -q
```

## Project structure

```
app.py                 Streamlit app
trend/regions.py       region catalog
trend/variables.py     measurement catalog: definitions, units, products, citations, caveats
trend/fetch.py         NASA POWER client and cached CSV storage
trend/stats.py         annual aggregation, OLS trend test, Mann-Kendall, confidence band
trend/charts.py        Plotly charts
scripts/prefetch.py    fetches and caches data for a region
data/processed/        small cached monthly CSVs used by the app
tests/                 unit and app smoke tests
docs/ARCHITECTURE.md   design and methods plan
```

## Use of AI

The idea and all product decisions come from Team Avni, including the "secret expert detective"
theme. The AI proposed three layout options for that theme and the team chose the board-and-case-file
layout. The code and documentation were written with AI assistance: **Claude Opus 5.5** (Anthropic) wrote the code, and **Claude Fable** (Anthropic)
reviewed the plan and the statistics code. Every AI-assisted source file says so in its header,
and AI-assisted commits carry a `Co-Authored-By` trailer. No AI-generated images, video or audio
are used.

## License

Apache License 2.0. See [LICENSE](LICENSE). Not affiliated with or endorsed by NASA.
