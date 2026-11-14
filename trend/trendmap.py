"""Crime scene map: where exactly is it changing? A trend for every NASA POWER grid cell of an area.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The map was one of the feature options the AI offered; Team Avni
chose it and asked to build it into the "Where?" map with a switch (dots on or off), followed by
the place's results and the possible reasons.

Every grid cell gets its own annual series and the same trend test as the investigation board.
When many cells are tested at once, a few would look "significant" by chance alone, so a cell gets
a dot only if it stays significant under the Benjamini-Hochberg false discovery rate at q = 0.10,
the setting recommended for maps of neighbouring, correlated grid cells (Wilks, 2016, BAMS 97,
2263-2273).
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

import folium
import numpy as np
import pandas as pd

from trend.area import power_request_boxes
from trend.fetch import (
    POWER_VARIABLES,
    RETRY_PAUSES,
    UNEXPECTED_RESPONSE,
    ZERO_MEANS_MISSING,
    DataSourceError,
    _request_retrying,
    power_sources,
)
from trend.i18n import chance_phrase, num, reasons, region_context, t, variable_text
from trend.regions import REGIONS, Region
from trend.stats import MIN_YEARS, RECOMMENDED_YEARS, analyze_trend, to_annual
from trend.variables import VARIABLES
from trend.verify import MAX_YEARS, residual_swing, years_needed

FDR_Q = 0.10
NO_SNOW_MAX_MM = 1.0  # same rule as the app: a cell where snowfall never reaches 1 mm has no snow
FIRST_YEAR = {"aod": 2001}  # CERES SYN1deg aerosols start in 2001; the MERRA-2 values in 1981
DEFAULT_FIRST_YEAR = 1981
LAST_YEAR = 2026  # like the board; POWER's "end date out of range" answer is retried one year earlier
YEARLY_DECIMALS = 6  # yearly cell values are compared at this precision (as stored in data/processed/grid)
MAX_MAP_SPAN = 10.0  # degrees; a larger rectangle has too many cells for a readable map
EDGE = 1e-6

# Decrease (blue) -> no change (pale) -> increase (orange): the app's two series colours.
DIVERGING = [
    (0.0, "#1c5cab"), (0.25, "#7fb0e8"), (0.5, "#f4f3f0"), (0.75, "#f4a582"), (1.0, "#b4441b"),
]

MAP_TEXT = {
    "en": {
        "layer_area": "📍 Pick the area", "layer_scene": "🔎 Crime scene map (dots)",
        "showing": "The map shows: {variable}, {start}–{end}",
        "fallback": "{picked} has no NASA grid, so the map shows air temperature. Pick temperature, "
                    "precipitation, snowfall or dust and smoke below to map them.",
        "loading": "Testing every grid cell...",
        "too_big": "The crime scene map works for areas up to {max}° per side. Draw a smaller "
                   "rectangle to see the dots.",
        "fetch_failed": "NASA POWER did not answer for the grid cells. Try again in a moment.",
        "intro": "Every square is one NASA grid cell (about 50 km) with its own trend test.",
        "both": "Two opposite directions in the same area! Significant increase in {up} grid cell(s), "
                "significant decrease in {down}.",
        "up_only": "Significant increase in {up} of {n} grid cells.",
        "down_only": "Significant decrease in {down} of {n} grid cells.",
        "none": "None of the {n} grid cell(s) keeps a significant trend after the correction for testing "
                "many cells.",
        "fastest_up": "Fastest increase among the cells with a dot {where}: {rate}.",
        "fastest_down": "Fastest decrease among the cells with a dot {where}: {rate}.",
        "spread": "Over all cells, with or without a dot, the rate goes from {low} to {high}.",
        "no_cells": "Not enough grid-cell data for this measurement here.",
        "no_snow": "It practically never snows here, so there is nothing to map.",
        "legend_low": "decrease", "legend_high": "increase",
        "dots": "Dot = a trend that holds up: significant in the app's test, backed by the second "
                "(rank-based) test, and still significant after correcting for testing many cells at once "
                "(Benjamini-Hochberg false discovery rate, q = 0.10; Wilks, 2016). About 1 dot in 10 may "
                "still be chance. Hover over a square for its numbers.",
        "hover_dot": "Dot: holds up after the correction",
        "hover_nodot": "No dot: could be chance",
        "chance": "Chance alone: {phrase}",
        "why_title": "Why? (possible explanations)",
        "why_note": "The map shows where something changed, not why; these are common explanations "
                    "from research.",
        "context": "Local context",
        "mixed": {
            "snowfall": "Opposite directions are common for snow: warming turns snow into rain in "
                        "lower, milder places, while in high mountains that are still cold enough, "
                        "warmer air carries more moisture and can bring more snow.",
            "precipitation": "Rain is local: slopes facing the wind get more and the land behind "
                             "the mountains less, and shifting storm tracks can make one part wetter "
                             "and another drier.",
            "air_temperature": "Warming is not equally fast everywhere: irrigation, cities, melting "
                               "snow cover or the sea nearby create local differences.",
            "aod": "Dust and smoke depend on local sources: fires or dust storms can grow in one part "
                   "while clean-air rules cut haze in another.",
            "generic": "Local differences in land, height and nearby sources can push neighbouring "
                       "places in opposite directions.",
        },
        "where": {"n": "in the north", "s": "in the south", "e": "in the east", "w": "in the west",
                  "ne": "in the northeast", "nw": "in the northwest", "se": "in the southeast",
                  "sw": "in the southwest", "c": "in the middle"},
    },
    "tr": {
        "layer_area": "📍 Bölge seç", "layer_scene": "🔎 Olay yeri haritası (noktalar)",
        "showing": "Haritada: {variable}, {start}–{end}",
        "fallback": "{picked} için NASA ızgara verisi yok; harita hava sıcaklığını gösteriyor. "
                    "Sıcaklık, yağış, kar ya da toz ve dumanı haritada görmek için aşağıdan seç.",
        "loading": "Her ızgara karesi test ediliyor...",
        "too_big": "Olay yeri haritası her kenarı en fazla {max}° olan alanlarda çalışıyor. Noktaları "
                   "görmek için daha küçük bir dikdörtgen çiz.",
        "fetch_failed": "NASA POWER ızgara kareleri için cevap vermedi. Biraz sonra tekrar dene.",
        "intro": "Her kare NASA'nın bir ızgara karesi (yaklaşık 50 km); her birinin trendi ayrı test "
                 "edildi.",
        "both": "Aynı bölgede iki zıt yön! {up} karede anlamlı artış, {down} karede anlamlı azalış "
                "var.",
        "up_only": "{n} karenin {up} tanesinde anlamlı artış var.",
        "down_only": "{n} karenin {down} tanesinde anlamlı azalış var.",
        "none": "{n} karenin hiçbirinde, çoklu test düzeltmesinden sonra anlamlı bir trend kalmıyor.",
        "fastest_up": "Noktalı kareler arasında en hızlı artış bölgenin {where}: {rate}.",
        "fastest_down": "Noktalı kareler arasında en hızlı azalış bölgenin {where}: {rate}.",
        "spread": "Noktalı noktasız bütün karelerde hız {low} ile {high} arasında değişiyor.",
        "no_cells": "Bu ölçüm için burada yeterli ızgara verisi yok.",
        "no_snow": "Burada neredeyse hiç kar yağmıyor; haritada gösterilecek bir şey yok.",
        "legend_low": "azalış", "legend_high": "artış",
        "dots": "Nokta = geçerliliğini koruyan trend: uygulamanın testinde anlamlı, ikinci (sıralamaya "
                "dayalı) test de aynı fikirde ve çok sayıda kare birlikte test edildiği için yapılan "
                "düzeltmeden sonra da anlamlı (Benjamini-Hochberg yanlış keşif oranı, q = 0,10; Wilks, "
                "2016). Yaklaşık 10 noktadan biri yine de tesadüf olabilir. Rakamlar için farenle bir "
                "karenin üstüne gel.",
        "hover_dot": "Nokta: düzeltmeden sonra da geçerli",
        "hover_nodot": "Nokta yok: tesadüf olabilir",
        "chance": "Tesadüf ihtimali: {phrase}",
        "why_title": "Neden? (olası açıklamalar)",
        "why_note": "Harita bir şeyin nerede değiştiğini gösterir, nedenini değil; bunlar bilimde sık "
                    "anılan açıklamalar.",
        "context": "Yerel bilgi",
        "mixed": {
            "snowfall": "Kar için zıt yönler sık görülür: ısınma alçak ve ılık yerlerde karı yağmura "
                        "çevirirken, hâlâ yeterince soğuk olan yüksek dağlarda ılık havanın taşıdığı "
                        "fazla nem daha çok kar getirebilir.",
            "precipitation": "Yağış yereldir: rüzgâr alan yamaçlar daha çok, dağların arkası daha az "
                             "yağış alır; kayan fırtına yolları bir kısmı ıslatıp bir kısmı "
                             "kurutabilir.",
            "air_temperature": "Isınma her yerde aynı hızda olmaz: sulama, şehirler, eriyen kar "
                               "örtüsü ya da yakındaki deniz yerel farklar yaratır.",
            "aod": "Toz ve duman yerel kaynaklara bağlıdır: bir yerde yangınlar ya da toz fırtınaları "
                   "artarken başka bir yerde temiz hava kuralları pusu azaltabilir.",
            "generic": "Arazi, yükseklik ve yakındaki kaynaklardaki farklar komşu yerleri zıt yönlere "
                       "itebilir.",
        },
        "where": {"n": "kuzeyinde", "s": "güneyinde", "e": "doğusunda", "w": "batısında",
                  "ne": "kuzeydoğusunda", "nw": "kuzeybatısında", "se": "güneydoğusunda",
                  "sw": "güneybatısında", "c": "ortasında"},
    },
}

TREND_COLUMNS = ["lat", "lon", "slope_per_decade", "p_value", "significant", "agrees", "n_years",
                 "start_year", "end_year", "need_years", "fdr", "dot", "direction", "why"]

# Why a cell has no dot ("" for cells with a dot): "fdr" significant alone but not after the
# many-cells correction, "disputed" the second test disagrees, "short" record, "flat" no change at
# all, "noise" the change is small next to the year-to-year swings.
WHY_TEXT = {
    "en": {
        "why_head": "Why do some cells have no dot?",
        "why_noise": "{n} cell(s): the change is small next to the year-to-year swings (a typical one would "
                     "need roughly {need} years of records)",
        "why_noise_centuries": "{n} cell(s): the change is too small to tell apart from the year-to-year "
                               "swings",
        "why_fdr": "{n} cell(s): significant on their own, but with {total} cells tested at once a result "
                   "this strong can also be chance",
        "why_disputed": "{n} cell(s): significant, but the second (rank-based) test disagrees",
        "why_short": "{n} cell(s): the record is short (under {rec} years)",
        "why_flat": "{n} cell(s): no change at all",
        "tip_noise": "No dot: the change is small next to the swings; roughly {need} years needed",
        "tip_noise_centuries": "No dot: the change is too small to tell apart from the swings",
        "tip_fdr": "No dot: significant alone, but could be chance among {total} cells",
        "tip_disputed": "No dot: the second test disagrees",
        "tip_short": "No dot: short record",
        "tip_flat": "No dot: no change",
    },
    "tr": {
        "why_head": "Neden bazı karelerde nokta yok?",
        "why_noise": "{n} kare: değişim yıllık oynamanın yanında küçük kalıyor (tipik bir kare için kabaca "
                     "{need} yıllık kayıt gerekir)",
        "why_noise_centuries": "{n} kare: değişim yıllık oynamalardan ayırt edilemeyecek kadar küçük",
        "why_fdr": "{n} kare: tek başına anlamlı, ama {total} kare birlikte test edildiğinde bu kadar güçlü "
                   "bir sonuç tesadüfen de çıkabiliyor",
        "why_disputed": "{n} kare: anlamlı, ama ikinci (sıralamaya dayalı) test aynı fikirde değil",
        "why_short": "{n} kare: kayıt kısa ({rec} yıldan az)",
        "why_flat": "{n} kare: hiç değişim yok",
        "tip_noise": "Nokta yok: değişim oynamanın yanında küçük; kabaca {need} yıl gerekir",
        "tip_noise_centuries": "Nokta yok: değişim oynamalardan ayırt edilemeyecek kadar küçük",
        "tip_fdr": "Nokta yok: tek başına anlamlı ama {total} kare içinde tesadüf olabilir",
        "tip_disputed": "Nokta yok: ikinci test aynı fikirde değil",
        "tip_short": "Nokta yok: kayıt kısa",
        "tip_flat": "Nokta yok: değişim yok",
    },
}


def why_text(lang: str) -> dict:
    return WHY_TEXT.get(lang, WHY_TEXT["en"])


def map_text(lang: str) -> dict:
    return MAP_TEXT.get(lang, MAP_TEXT["en"])


# --- Data ------------------------------------------------------------------------------------------

def cells_from_payloads(payloads: list[dict], parameter: str,
                        bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Monthly values of every grid cell whose centre lies inside ``bbox`` (or on its edge).

    Returns columns ``lat, lon, date, value``. POWER's 13th "month" (its annual value) is dropped,
    fill values become missing, and a cell repeated by overlapping request boxes is kept once.
    """
    west, south, east, north = bbox
    header = (payloads[0].get("header", {}) if payloads else {}) or {}
    fill_value = float(header.get("fill_value", -999.0))
    rows, seen = [], set()
    for payload in payloads:
        for feature in payload.get("features", []):
            lon, lat = (round(float(v), 6) for v in feature["geometry"]["coordinates"][:2])
            inside = west - EDGE <= lon <= east + EDGE and south - EDGE <= lat <= north + EDGE
            if not inside or (lat, lon) in seen:
                continue
            seen.add((lat, lon))
            for key, value in feature["properties"]["parameter"][parameter].items():
                month = int(key[4:])
                if month == 13:
                    continue
                rows.append((lat, lon, int(key[:4]), month, value))
    if not rows:
        return pd.DataFrame(columns=["lat", "lon", "date", "value"])
    cells = pd.DataFrame(rows, columns=["lat", "lon", "year", "month", "value"])
    cells["value"] = pd.to_numeric(cells["value"], errors="coerce")
    missing = np.isclose(cells["value"], fill_value) | (cells["value"] <= -998)
    if parameter in ZERO_MEANS_MISSING:
        missing |= cells["value"] == 0
    cells.loc[missing, "value"] = np.nan
    cells["date"] = pd.to_datetime(cells[["year", "month"]].assign(day=1))
    return cells.loc[:, ["lat", "lon", "date", "value"]].sort_values(["lat", "lon", "date"]).reset_index(drop=True)


def _usable(payload) -> bool:
    """A NASA POWER regional answer that has a list of grid cells (features)."""
    return isinstance(payload, dict) and isinstance(payload.get("features"), list)


def fetch_cells(variable_key: str, bbox: tuple[float, float, float, float], end_year: int = LAST_YEAR,
                cache_dir: Path | None = None, timeout=300) -> tuple[pd.DataFrame, str]:
    """Monthly values per grid cell from NASA POWER for any rectangle.

    Responses can be kept in ``cache_dir``, so NASA is asked only once per box. Returns the cells in
    the app's cached unit (daily rates become monthly totals) and the data sources POWER reports.
    """
    if variable_key not in POWER_VARIABLES:
        raise ValueError(f"'{variable_key}' has no NASA POWER grid.")
    parameter, is_daily_rate = POWER_VARIABLES[variable_key]
    start_year = FIRST_YEAR.get(variable_key, DEFAULT_FIRST_YEAR)
    payloads = []
    for box in power_request_boxes(bbox):
        path = None
        if cache_dir is not None:
            name = f"{parameter}_{start_year}_{end_year}_" + "_".join(f"{v:.2f}" for v in box) + ".json"
            path = Path(cache_dir) / name
        if path is not None and path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                cached = None
            if _usable(cached):
                payloads.append(cached)
                continue
            try:
                path.unlink(missing_ok=True)  # a broken cache file is fetched again
            except OSError:
                pass
        payload = _request_retrying(parameter, Region("custom", "custom", *box), start_year, end_year,
                                    timeout, RETRY_PAUSES)
        if not _usable(payload):
            raise DataSourceError(UNEXPECTED_RESPONSE)
        # Only a response that really has cells for this box is kept on disk.
        if path is not None and not cells_from_payloads([payload], parameter, box).empty:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload), encoding="utf-8")
            except OSError:
                pass  # a read-only disk only means NASA is asked again next time
        payloads.append(payload)
    cells = cells_from_payloads(payloads, parameter, bbox)
    if is_daily_rate and not cells.empty:
        cells["value"] = cells["value"] * cells["date"].dt.days_in_month
    sources = sorted({part for payload in payloads for part in power_sources(payload).split(", ")})
    return cells, ", ".join(sources)


# --- Statistics ------------------------------------------------------------------------------------

def bh_fdr(p_values, q: float = FDR_Q) -> np.ndarray:
    """Benjamini-Hochberg: which tests stay significant when the false discovery rate is q."""
    p = np.asarray(p_values, dtype=float)
    keep = np.zeros(p.shape, dtype=bool)
    valid = np.isfinite(p)
    m = int(valid.sum())
    if m == 0:
        return keep
    ranked = np.sort(p[valid])
    passing = np.nonzero(ranked <= q * np.arange(1, m + 1) / m)[0]
    if passing.size:
        keep[valid] = p[valid] <= ranked[passing[-1]]
    return keep


def mark_dots(trends: pd.DataFrame) -> pd.DataFrame:
    """Add the many-cells correction, the dots, the direction and the no-dot reason to cell results.

    A dot needs all three: Benjamini-Hochberg at q = 0.10, the app's own 5% line and the second
    (rank-based) test agreeing, so a dot never sits on a cell the board would call disputed.
    """
    trends = trends.copy()
    trends["fdr"] = bh_fdr(trends["p_value"])
    trends["dot"] = trends["fdr"] & (trends["p_value"] < 0.05) & trends["agrees"].astype(bool)
    trends["direction"] = np.where(trends["dot"], np.where(trends["slope_per_decade"] > 0, "up", "down"), "none")
    significant_alone = trends["p_value"] < 0.05
    trends["why"] = np.select(
        [trends["dot"], significant_alone & ~trends["fdr"], significant_alone & ~trends["agrees"].astype(bool),
         trends["n_years"] < RECOMMENDED_YEARS, trends["need_years"].isna()],
        ["", "fdr", "disputed", "short", "flat"], default="noise",
    )
    return trends


def _trends_from_yearly(yearly, variable_key: str, start_year: int | None,
                        end_year: int | None) -> pd.DataFrame:
    """The trend test for each (lat, lon, yearly values) item, plus the FDR dots and the snow-free count."""
    records, no_snow = [], 0
    for lat, lon, annual in yearly:
        # Six decimals, as in the prepared files: float noise from monthly sums (0.17 * 31) must not
        # decide whether two years tie in the rank test.
        annual = annual.assign(value=annual["value"].round(YEARLY_DECIMALS))
        if start_year is not None:
            annual = annual[annual["year"] >= start_year]
        if end_year is not None:
            annual = annual[annual["year"] <= end_year]
        if variable_key == "snowfall" and len(annual) and annual["value"].max() < NO_SNOW_MAX_MM:
            no_snow += 1
            continue
        if len(annual) < MIN_YEARS:
            continue
        result = analyze_trend(annual["year"], annual["value"])
        if not math.isfinite(result.p_value):
            continue
        swing = residual_swing(annual["year"], annual["value"])
        records.append(
            {
                "lat": float(lat), "lon": float(lon),
                "slope_per_decade": float(result.slope_per_decade), "p_value": float(result.p_value),
                "significant": bool(result.significant), "agrees": bool(result.agrees),
                "n_years": int(result.n_years), "start_year": int(result.start_year),
                "end_year": int(result.end_year),
                "need_years": float(years_needed(result.slope_per_year, swing, result.lag1_autocorrelation)),
            }
        )
    trends = pd.DataFrame(records)
    if trends.empty:
        trends = pd.DataFrame(columns=TREND_COLUMNS)
    else:
        trends = mark_dots(trends).loc[:, TREND_COLUMNS]
    trends.attrs["no_snow_cells"] = no_snow
    return trends


def cell_trends(cells: pd.DataFrame, variable_key: str, start_year: int | None = None,
                end_year: int | None = None) -> pd.DataFrame:
    """The app's trend test for every cell with enough complete years, plus the FDR dots.

    ``cells`` are monthly values per cell (``fetch_cells``); each cell is turned into complete years
    with the app's own yearly rule first.
    """
    variable = VARIABLES[variable_key]

    def yearly():
        for (lat, lon), monthly in cells.groupby(["lat", "lon"], sort=True):
            annual, _ = to_annual(monthly.loc[:, ["date", "value"]], variable)
            yield lat, lon, annual

    return _trends_from_yearly(yearly(), variable_key, start_year, end_year)


def cell_trends_from_annual(annual: pd.DataFrame, variable_key: str, start_year: int | None = None,
                            end_year: int | None = None) -> pd.DataFrame:
    """The same test from yearly values per cell (``lat, lon, year, value``), such as the prepared files.

    The prepared files in data/processed/grid were built with the same yearly rule, so this skips the
    slow monthly-to-yearly step for the prepared regions and needs no request to NASA POWER.
    """
    def yearly():
        for (lat, lon), group in annual.groupby(["lat", "lon"], sort=True):
            yield lat, lon, group.loc[:, ["year", "value"]].sort_values("year").reset_index(drop=True)

    return _trends_from_yearly(yearly(), variable_key, start_year, end_year)


def cell_size(cells: pd.DataFrame) -> tuple[float, float]:
    """Grid spacing (latitude, longitude) in degrees, read from the cell centres."""
    def spacing(values, default):
        unique = np.unique(np.round(np.asarray(values, dtype=float), 6))
        steps = np.diff(unique)
        steps = steps[steps > 1e-6]
        return float(steps.min()) if steps.size else default
    return spacing(cells["lat"], 0.5), spacing(cells["lon"], 0.625)


# --- Words -----------------------------------------------------------------------------------------

def compass(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> str:
    """Where a cell lies in the area: n, s, e, w, ne, nw, se, sw or c (middle)."""
    west, south, east, north = bbox
    dy = (lat - (south + north) / 2) / max((north - south) / 2, 1e-9)
    dx = (lon - (west + east) / 2) / max((east - west) / 2, 1e-9)
    ns = "n" if dy > 1 / 3 else "s" if dy < -1 / 3 else ""
    ew = "e" if dx > 1 / 3 else "w" if dx < -1 / 3 else ""
    return (ns + ew) or "c"


def rate_text(value: float, lang: str, variable_key: str) -> str:
    variable = VARIABLES[variable_key]
    texts = variable_text(lang, variable)
    decimals = getattr(variable, "decimals", 2)
    return f"{num(value, lang, decimals, signed=True)} {texts['annual_unit']} {t(lang, 'per_decade')}"


def summarize(trends: pd.DataFrame, lang: str, variable_key: str,
              bbox: tuple[float, float, float, float]) -> dict:
    """Headline and details in words: how many cells changed, in which direction, and where."""
    text = map_text(lang)
    if trends.empty:
        headline = text["no_snow"] if trends.attrs.get("no_snow_cells") else text["no_cells"]
        return {"headline": headline, "details": [], "n": 0, "up": 0, "down": 0, "both": False}
    n = len(trends)
    up = int((trends["direction"] == "up").sum())
    down = int((trends["direction"] == "down").sum())
    if up and down:
        headline = text["both"].format(up=up, down=down)
    elif up:
        headline = text["up_only"].format(up=up, n=n)
    elif down:
        headline = text["down_only"].format(down=down, n=n)
    else:
        headline = text["none"].format(n=n)
    details = []
    if up:
        top = trends[trends["direction"] == "up"].sort_values("slope_per_decade").iloc[-1]
        where = text["where"][compass(top["lat"], top["lon"], bbox)]
        details.append(text["fastest_up"].format(where=where, rate=rate_text(top["slope_per_decade"], lang, variable_key)))
    if down:
        low = trends[trends["direction"] == "down"].sort_values("slope_per_decade").iloc[0]
        where = text["where"][compass(low["lat"], low["lon"], bbox)]
        details.append(text["fastest_down"].format(where=where, rate=rate_text(low["slope_per_decade"], lang, variable_key)))
    if n > 1:
        details.append(text["spread"].format(
            low=rate_text(trends["slope_per_decade"].min(), lang, variable_key),
            high=rate_text(trends["slope_per_decade"].max(), lang, variable_key),
        ))
    return {"headline": headline, "details": details, "n": n, "up": up, "down": down,
            "both": bool(up and down), "no_dot": no_dot_reasons(trends, lang)}


def no_dot_reasons(trends: pd.DataFrame, lang: str) -> list[str]:
    """Why the cells without a dot are not verified, as counted lines (most common reason first)."""
    words = why_text(lang)
    if trends.empty or "why" not in trends.columns:
        return []
    total = len(trends)
    lines = []
    for reason, group in sorted(trends[trends["why"] != ""].groupby("why"), key=lambda item: -len(item[1])):
        if reason == "noise":
            # Infinite needs count as "very long" in the median instead of being dropped.
            needs = group["need_years"].dropna().replace(np.inf, 1e9)
            typical = float(np.median(needs)) if len(needs) else math.inf
            if typical > MAX_YEARS:
                lines.append(words["why_noise_centuries"].format(n=len(group)))
            else:
                lines.append(words["why_noise"].format(n=len(group), need=math.ceil(typical)))
        elif reason == "fdr":
            lines.append(words["why_fdr"].format(n=len(group), total=total))
        elif reason == "disputed":
            lines.append(words["why_disputed"].format(n=len(group)))
        elif reason == "flat":
            lines.append(words["why_flat"].format(n=len(group)))
        else:
            lines.append(words["why_short"].format(n=len(group), rec=RECOMMENDED_YEARS))
    return lines


def cell_tip_reason(row, total: int, lang: str) -> str:
    """One short line for a cell's tooltip: why it has no dot."""
    words = why_text(lang)
    if row.why == "fdr":
        return words["tip_fdr"].format(total=total)
    if row.why == "disputed":
        return words["tip_disputed"]
    if row.why == "short":
        return words["tip_short"]
    if row.why == "flat":
        return words["tip_flat"]
    if row.why == "noise":
        need = row.need_years
        if not math.isfinite(need) or need > MAX_YEARS:
            return words["tip_noise_centuries"]
        return words["tip_noise"].format(need=math.ceil(need))
    return ""


def map_reasons(lang: str, variable_key: str, summary: dict, region_key: str | None) -> dict:
    """Possible explanations for what the map shows: the app's reasons catalog, a note for opposite
    directions, and the region's local context when it is a prepared region."""
    text = map_text(lang)
    if summary.get("both"):
        lines = [text["mixed"].get(variable_key, text["mixed"]["generic"])]
    else:
        direction = "up" if summary.get("up") else "down" if summary.get("down") else "none"
        lines = list(reasons(lang, variable_key, direction))
    context = region_context(lang, region_key, variable_key) if region_key in REGIONS else None
    return {"title": text["why_title"], "lines": lines, "context": context or "", "note": text["why_note"]}


# --- Map -------------------------------------------------------------------------------------------

def _mix(color_a: str, color_b: str, share: float) -> str:
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * share):02x}" for x, y in zip(a, b))


def slope_color(value: float, zmax: float) -> str:
    """Colour of a rate of change on the diverging scale centred at zero (-zmax blue, +zmax orange)."""
    position = 0.5 if zmax <= 0 else 0.5 + 0.5 * max(-1.0, min(1.0, value / zmax))
    for (x0, c0), (x1, c1) in zip(DIVERGING, DIVERGING[1:]):
        if position <= x1:
            return _mix(c0, c1, (position - x0) / (x1 - x0))
    return DIVERGING[-1][1]


def scale_max(trends: pd.DataFrame) -> float:
    zmax = float(trends["slope_per_decade"].abs().max()) if len(trends) else 0.0
    return zmax if zmax > 0 else 1.0


def add_overlay(fmap: folium.Map, trends: pd.DataFrame, size: tuple[float, float], lang: str,
                variable_key: str) -> folium.FeatureGroup:
    """Coloured grid cells and dots on the cells that stay significant, as a non-editable layer."""
    text = map_text(lang)
    zmax = scale_max(trends)
    dlat, dlon = size[0] / 2, size[1] / 2
    group = folium.FeatureGroup(name="crime scene", control=False)
    total = len(trends)
    for row in trends.itertuples(index=False):
        status = text["hover_dot"] if row.dot else (cell_tip_reason(row, total, lang) or text["hover_nodot"])
        tip = (
            f"<b>{html.escape(rate_text(row.slope_per_decade, lang, variable_key))}</b><br>"
            f"{html.escape(text['chance'].format(phrase=chance_phrase(row.p_value, lang)))}<br>"
            f"{html.escape(status)}<br>{row.start_year}–{row.end_year}"
        )
        folium.Rectangle(
            bounds=[[row.lat - dlat, row.lon - dlon], [row.lat + dlat, row.lon + dlon]],
            color="#ffffff", weight=0.6, fill=True, fill_color=slope_color(row.slope_per_decade, zmax),
            fill_opacity=0.72, tooltip=folium.Tooltip(tip, sticky=True),
        ).add_to(group)
        if row.dot:
            folium.CircleMarker(
                location=[row.lat, row.lon], radius=3, weight=0, fill=True, fill_color="#0b0b0b",
                fill_opacity=0.95,
            ).add_to(group)
    group.add_to(fmap)
    return group


def legend_html(trends: pd.DataFrame, lang: str, variable_key: str) -> str:
    """A small colour bar from the fastest decrease to the fastest increase, with the dot key."""
    text = map_text(lang)
    zmax = scale_max(trends)
    stops = ", ".join(f"{color} {round(pos * 100)}%" for pos, color in DIVERGING)
    low, high = rate_text(-zmax, lang, variable_key), rate_text(zmax, lang, variable_key)
    return (
        "<div style='max-width:520px;margin:4px 0 2px 0'>"
        f"<div style='height:12px;border-radius:6px;background:linear-gradient(90deg, {stops})'></div>"
        "<div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#52514e'>"
        f"<span>{html.escape(low)} · {html.escape(text['legend_low'])}</span><span>0</span>"
        f"<span>{html.escape(text['legend_high'])} · {html.escape(high)}</span></div></div>"
    )
