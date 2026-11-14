"""Time travel map: a zoomable map of a place with a year slider and one coloured square per grid cell.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni, NASA Space Apps Challenge 2026.
Idea from Team Avni: zoom into a place like a web map and slide through the years at the bottom.

Each square is one NASA POWER grid cell (about 0.5 x 0.625 degrees). Its colour shows how far that year
was from the cell's own normal (the 1981-2010 average; 2001-2010 for aerosols, whose record starts in
2001), on one fixed, symmetric colour scale per place and measurement, so years can be compared. One
year can be unusual by chance: whether a change is real is decided by the trend test, not by these
colours. Optional NASA GIBS satellite images of the same year give context, not evidence.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from trend.fetch import PROJECT_ROOT
from trend.i18n import variable_text
from trend.stats import to_annual
from trend.trendmap import FIRST_YEAR, NO_SNOW_MAX_MM, cell_size
from trend.variables import VARIABLES

GRID_DIR = PROJECT_ROOT / "data" / "processed" / "grid"
LAYER_KEYS = ("air_temperature", "hot_days", "precipitation", "snowfall", "aod")
DEFAULT_BASELINE = (1981, 2010)  # the climate normal used by NASA GISTEMP maps and the WMO until 2020
BASELINE = {"aod": (2001, 2010)}  # aerosols start in 2001
MIN_BASELINE_SHARE = 2 / 3  # a cell needs at least two thirds of its baseline years for a normal
SCALE_PERCENTILE = 95  # the colour scale ends here, so a few extreme cells do not wash out the map
RANK_SHOWN = 3  # a year among the 3 highest or lowest of the record gets a rank label
NICE_STEPS = (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10)  # legend ends are rounded up to one of these
# From April 2022 the app's aerosol values follow VIIRS instead of MODIS and run higher, which would
# paint every later year "hazier than 2001-2010"; the time map stops before the switch, as the witness does.
LAYER_LAST_YEAR = {"aod": 2021}
# Rain and snow are shown in percent of normal (coloured by log2 of the ratio, so half and double sit
# symmetrically), unless the place's typical normal is below this many mm a year: then percent explodes
# and the map falls back to millimetres (deserts such as Medina and the Nile delta).
PERCENT_MODE = {"precipitation": 50.0, "snowfall": 20.0}
RATIO_STEPS = (1.25, 1.5, 2.0, 3.0, 4.0, 8.0)  # the colour scale ends at one of these ratios
RATIO_CLIP = 16.0  # ratios beyond 1/16 or 16 (for example a year without snow) count as the end colour
AVERAGE_NOT_NORMAL = {"aod"}  # ten years are too short to call a "normal"
DECIMALS = {"air_temperature": 2, "hot_days": 1, "precipitation": 0, "snowfall": 1, "aod": 3}
SHOW_DECIMALS = {"air_temperature": 1, "hot_days": 0, "precipitation": 0, "snowfall": 1, "aod": 3}
LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_CSS_SRI = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
LEAFLET_JS_SRI = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="

# Negative to positive: what is good or bad depends on the measurement, so each gets intuitive colours.
PALETTES = {
    "warm": ["#2c5aa0", "#8fb3e0", "#f4f3f0", "#f0a07a", "#b8312f"],  # colder blue, warmer red
    "wet": ["#8c510a", "#d8b365", "#f4f3f0", "#5ab4ac", "#01665e"],  # drier brown, wetter teal (BrBG)
    "dust": ["#1b7837", "#a6dba0", "#f4f3f0", "#c2a5cf", "#762a83"],  # cleaner green, hazier purple
}
PALETTE_OF = {"air_temperature": "warm", "hot_days": "warm", "precipitation": "wet", "snowfall": "wet",
              "aod": "dust"}

# NASA GIBS imagery (WMTS, Web Mercator). Checked by the research workflow with real tile requests:
# monthly and yearly layers snap any date inside the period to its start; daily layers need the day.
GIBS_URL = ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{{time}}/"
            "GoogleMapsCompatible_Level{level}/{{z}}/{{y}}/{{x}}.{ext}")
IMAGERY = {
    "true_colour": {"layer": "MODIS_Terra_CorrectedReflectance_TrueColor", "level": 9, "ext": "jpg",
                    "years": (2000, 2026), "date": "07-15", "daily": True, "opacity": 1.0, "legend": None},
    "ndvi": {"layer": "MODIS_Terra_L3_NDVI_Monthly", "level": 7, "ext": "png", "years": (2000, 2026),
             "date": "08-01", "daily": False, "opacity": 0.85, "legend": "MODIS_L3_NDVI_H.svg"},
    "snow": {"layer": "MODIS_Terra_L3_Snow_Cover_Monthly_Average_Pct", "level": 6, "ext": "png",
             "years": (2000, 2026), "date": "04-01", "daily": False, "opacity": 0.7,
             "legend": "MODIS_NDSI_Snow_Cover_H.svg"},
    "night": {"layer": "VIIRS_SNPP_GapFilled_BRDF_Corrected_DayNightBand_Radiance", "level": 8, "ext": "png",
              "years": (2012, 2026), "date": "10-15", "daily": True, "opacity": 1.0, "legend": None},
    "land_cover": {"layer": "MODIS_Combined_L3_IGBP_Land_Cover_Type_Annual", "level": 8, "ext": "png",
                   "years": (2001, 2024), "date": "01-01", "daily": False, "opacity": 0.8,
                   "legend": "MODIS_IGBP_Land_Cover_Type_H.svg"},
    "co": {"layer": "MOPITT_CO_Monthly_Total_Column_Day", "level": 6, "ext": "png", "years": (2000, 2024),
           "date": "09-01", "daily": False, "opacity": 0.7, "legend": "MOPITT_CO_Total_Column_H.svg"},
}
GIBS_LEGEND_URL = "https://gibs.earthdata.nasa.gov/legends/{name}"  # official colour legends (checked: HTTP 200)
# One day a year for the daily true-colour photo, picked per place from tile checks of 2005, 2015 and
# 2023 for few clouds and no gaps between satellite passes (a single day can still be cloudy).
TRUE_COLOUR_DATE = {"colorado": "06-20", "marmara": "08-15", "medina": "07-15", "beijing": "10-15",
                    "los_angeles": "06-20", "cairo_nile": "07-15", "amazon": "08-15", "sahel": "10-15",
                    "alps": "09-05", "siberia": "06-25"}
# Cases without squares open with the satellite layer that shows them; cases with squares open without
# imagery, so the map is instant and only one colour scale is on screen (imagery is one click away).
IMAGERY_FOR_CASE = {"ndvi": "ndvi", "tree_cover": "true_colour", "co": "co"}

TIME_TEXT = {
    "en": {
        "layer": "⏳ Time travel (years)",
        "data": "Squares",
        "imagery": "Satellite image",
        "none": "None",
        "play": "Play",
        "pause": "Pause",
        "speed": "Speed",
        "slow": "Slow",
        "normal_speed": "Normal",
        "fast": "Fast",
        "opacity": "Square strength",
        "year": "Year",
        "legend_diff": "{name}: how far each square's year was from {ref}",
        "legend_pct": "{name}: each square's year in percent above or below {ref}",
        "no_data": "No data for this year",
        "tip_diff": "{d} {unit} against {ref_short} ({normal_word} {n} {unit})",
        "tip_pct": "{words} ({mm} {unit}; {normal_word} {n} {unit})",
        "area_mean": "Average of the squares this year: {value} against {ref}",
        "rank1": "{word} of {n} years (average of the squares)",
        "rank23": "{ord} {word} of {n} years (average of the squares)",
        "ords": {"2": "2nd", "3": "3rd"},
        "ref_normal": "the {b0}–{b1} normal",
        "ref_average": "the {b0}–{b1} average",
        "short_normal": "its normal",
        "short_average": "its average",
        "word_normal": "normal",
        "word_average": "average",
        "imagery_range": "{name}: available {first}–{last}",
        "no_snow": "{n} squares never get snow and are left out",
        "stripes": "Average of the squares, year by year",
        "no_leaflet": "The map library could not load. Check the internet connection and reload.",
        "credit": "Imagery: NASA GIBS/ESDIS",
        "provisional": "The newest year may still be revised by NASA",
        "aod_cut": ("Years after 2021 are left out: from April 2022 the app's aerosol data follow another "
                    "satellite (VIIRS)"),
        "tick_hint": "Tick “Squares” to see the data squares",
        "image_colours": "Colours of the satellite layer (NASA GIBS):",
        "words": {
            "air_temperature": {"high1": "Warmest", "low1": "Coldest", "high": "warmest", "low": "coldest"},
            "hot_days": {"high1": "Most hot days", "low1": "Fewest hot days", "high": "most hot days",
                         "low": "fewest hot days"},
            "precipitation": {"high1": "Wettest", "low1": "Driest", "high": "wettest", "low": "driest"},
            "snowfall": {"high1": "Snowiest", "low1": "Least snowy", "high": "snowiest", "low": "least snowy"},
            "aod": {"high1": "Haziest", "low1": "Clearest", "high": "haziest", "low": "clearest"},
        },
        "pct": {
            "precipitation": ["{p}% wetter than normal", "{p}% drier than normal"],
            "snowfall": ["{p}% more snow than normal", "{p}% less snow than normal"],
        },
        "imagery_names": {
            "true_colour": "True colour (MODIS Terra, one day)",
            "ndvi": "Vegetation greenness (MODIS NDVI, August)",
            "snow": "Snow cover (MODIS, April average)",
            "night": "Night lights (VIIRS, one night)",
            "land_cover": "Land cover (MODIS, yearly)",
            "co": "Carbon monoxide (MOPITT, September)",
        },
        "photo_day": "photo of {date}; clouds or gaps between satellite passes can show",
        "honesty": ("Colours show how far each year was from that square's own normal. One year can be "
                    "unusual by chance; whether a change is real is decided by the trend test below. "
                    "Satellite images are context, not evidence."),
        "gibs_ack": ("We acknowledge the use of imagery provided by services from NASA's Global Imagery "
                     "Browse Services (GIBS), part of NASA's Earth Science Data and Information System "
                     "(ESDIS)."),
        "custom_note": "For a drawn area the time map shows one measurement, fetched live from NASA POWER.",
        "too_big": "The time map works for areas up to {max}° per side. Draw a smaller rectangle.",
        "fetch_failed": "NASA POWER did not answer for the grid cells. Try again in a moment.",
        "loading": "Preparing every year of every square...",
        "nothing": "No yearly square data for this place yet.",
        "fallback": "{picked} has no squares on this map, so it opens with {shown}.",
    },
    "tr": {
        "layer": "⏳ Zaman yolculuğu (yıllar)",
        "data": "Kareler",
        "imagery": "Uydu görüntüsü",
        "none": "Yok",
        "play": "Oynat",
        "pause": "Durdur",
        "speed": "Hız",
        "slow": "Yavaş",
        "normal_speed": "Normal",
        "fast": "Hızlı",
        "opacity": "Kare yoğunluğu",
        "year": "Yıl",
        "legend_diff": "{name}: her karenin o yılki değerinin {ref} göre farkı",
        "legend_pct": "{name}: her karenin o yılki değerinin {ref} göre yüzde farkı",
        "no_data": "Bu yıl için veri yok",
        "tip_diff": "{ref_short} göre {d} {unit} ({normal_word} {n} {unit})",
        "tip_pct": "{words} ({mm} {unit}; {normal_word} {n} {unit})",
        "area_mean": "Bu yıl karelerin ortalaması: {ref} göre {value}",
        "rank1": "{n} yılın {word} (karelerin ortalaması)",
        "rank23": "{n} yılın {word} {ord} yılı (karelerin ortalaması)",
        "ords": {"2": "2.", "3": "3."},
        "ref_normal": "{b0}–{b1} normaline",
        "ref_average": "{b0}–{b1} ortalamasına",
        "short_normal": "normaline",
        "short_average": "ortalamasına",
        "word_normal": "normal",
        "word_average": "ortalama",
        "imagery_range": "{name}: {first}–{last} arası var",
        "no_snow": "{n} kareye hiç kar yağmıyor; gösterilmiyor",
        "stripes": "Karelerin ortalaması, yıl yıl",
        "no_leaflet": "Harita kütüphanesi yüklenemedi. İnternet bağlantısını kontrol edip sayfayı yenile.",
        "credit": "Görüntü: NASA GIBS/ESDIS",
        "provisional": "En yeni yıl NASA tarafından hâlâ düzeltilebilir",
        "aod_cut": ("2021 sonrası yıllar dışarıda bırakıldı: Nisan 2022'den itibaren uygulamanın aerosol verisi "
                    "başka bir uyduyu (VIIRS) izliyor"),
        "tick_hint": "Veri karelerini görmek için “Kareler” kutusunu işaretle",
        "image_colours": "Uydu katmanının renkleri (NASA GIBS):",
        "words": {
            "air_temperature": {"high1": "en sıcağı", "low1": "en soğuğu", "high": "en sıcak", "low": "en soğuk"},
            "hot_days": {"high1": "en çok sıcak gün olan yılı", "low1": "en az sıcak gün olan yılı",
                         "high": "en çok sıcak gün olan", "low": "en az sıcak gün olan"},
            "precipitation": {"high1": "en yağışlısı", "low1": "en kurağı", "high": "en yağışlı", "low": "en kurak"},
            "snowfall": {"high1": "en karlısı", "low1": "en az karlısı", "high": "en karlı", "low": "en az karlı"},
            "aod": {"high1": "en puslusu", "low1": "en açığı", "high": "en puslu", "low": "en açık"},
        },
        "pct": {
            "precipitation": ["normalden %{p} daha yağışlı", "normalden %{p} daha kurak"],
            "snowfall": ["normalden %{p} daha karlı", "normalden %{p} daha az karlı"],
        },
        "imagery_names": {
            "true_colour": "Gerçek renk (MODIS Terra, tek gün)",
            "ndvi": "Bitki yeşilliği (MODIS NDVI, Ağustos)",
            "snow": "Kar örtüsü (MODIS, Nisan ortalaması)",
            "night": "Gece ışıkları (VIIRS, tek gece)",
            "land_cover": "Arazi örtüsü (MODIS, yıllık)",
            "co": "Karbon monoksit (MOPITT, Eylül)",
        },
        "photo_day": "{date} tarihli görüntü; bulut ya da uydu geçişleri arasında boşluk olabilir",
        "honesty": ("Renkler her yılın o karenin kendi normalinden ne kadar saptığını gösterir. Tek bir yıl "
                    "tesadüfen sıra dışı olabilir; değişimin gerçek olup olmadığına aşağıdaki trend testi "
                    "karar verir. Uydu görüntüleri bağlam içindir, kanıt değil."),
        "gibs_ack": ("We acknowledge the use of imagery provided by services from NASA's Global Imagery "
                     "Browse Services (GIBS), part of NASA's Earth Science Data and Information System "
                     "(ESDIS)."),
        "custom_note": "Çizilen bir alanda zaman haritası tek bir ölçümü gösterir; veri NASA POWER'dan canlı gelir.",
        "too_big": "Zaman haritası kenarı en çok {max}° olan alanlarda çalışır. Daha küçük bir dikdörtgen çiz.",
        "fetch_failed": "NASA POWER ızgara kareleri için cevap vermedi. Biraz sonra tekrar dene.",
        "loading": "Her karenin her yılı hazırlanıyor...",
        "nothing": "Bu yer için henüz yıllık kare verisi yok.",
        "fallback": "{picked} bu haritada kare olarak yok; harita {shown} ile açılıyor.",
    },
}


def time_text(lang: str) -> dict:
    """The time map's words in the chosen language."""
    return TIME_TEXT.get(lang, TIME_TEXT["en"])


def grid_file(region_key: str, variable_key: str):
    """Prepared yearly values per grid cell: ``data/processed/grid/<region>_<variable>_cells.csv``."""
    return GRID_DIR / f"{region_key}_{variable_key}_cells.csv"


def load_annual_cells(region_key: str, variable_key: str) -> pd.DataFrame | None:
    """Yearly values per cell (lat, lon, year, value) from a prepared file, or None when there is none."""
    path = grid_file(region_key, variable_key)
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    column = "days" if variable_key == "hot_days" and "days" in frame.columns else "value"
    if not {"lat", "lon", "year", column} <= set(frame.columns):
        return None
    frame = frame.rename(columns={column: "value"}).loc[:, ["lat", "lon", "year", "value"]].dropna()
    frame["year"] = frame["year"].astype(int)
    return frame.reset_index(drop=True)


def annual_cells(cells: pd.DataFrame, variable_key: str) -> pd.DataFrame:
    """Yearly values per grid cell from monthly cell values, with the app's own yearly rule.

    ``cells`` has the columns ``lat, lon, date, value`` (as returned by ``trendmap.fetch_cells``). Only
    complete years are kept, snowfall uses the October-September season year, and aerosols start in
    2001, exactly as in the case file and the crime scene map.
    """
    variable = VARIABLES[variable_key]
    first = FIRST_YEAR.get(variable_key)
    frames = []
    for (lat, lon), monthly in cells.groupby(["lat", "lon"], sort=True):
        annual, _ = to_annual(monthly.loc[:, ["date", "value"]], variable)
        if first is not None:
            annual = annual[annual["year"] >= first]
        if len(annual):
            frames.append(pd.DataFrame({"lat": float(lat), "lon": float(lon),
                                        "year": annual["year"].astype(int).to_numpy(),
                                        "value": annual["value"].astype(float).to_numpy()}))
    if not frames:
        return pd.DataFrame(columns=["lat", "lon", "year", "value"])
    return pd.concat(frames, ignore_index=True)


def _clean(value: float, decimals: int):
    return None if value is None or not np.isfinite(value) else round(float(value), decimals)


def nice_ceiling(value: float) -> float:
    """The smallest 'round' number (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8 times a power of ten) at or above value."""
    if not np.isfinite(value) or value <= 0:
        return 0.0
    power = 10.0 ** math.floor(math.log10(value))
    for step in NICE_STEPS:
        if step * power >= value * (1 - 1e-9):
            return float(step * power)
    return float(10 * power)


def year_ranks(means: list) -> list:
    """Rank of each year's area average from the top (1 = highest) and from the bottom (1 = lowest)."""
    known = [(value, index) for index, value in enumerate(means) if value is not None]
    order_high = sorted(known, key=lambda item: -item[0])
    order_low = sorted(known, key=lambda item: item[0])
    high = {index: rank for rank, (_, index) in enumerate(order_high, start=1)}
    low = {index: rank for rank, (_, index) in enumerate(order_low, start=1)}
    return [[high.get(i), low.get(i)] for i in range(len(means))]


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Per-year mean over the cells that have a value, weighted by cos(latitude) like the case file."""
    mask = np.isfinite(values)
    total = np.where(mask, weights[:, None], 0.0).sum(axis=0)
    summed = np.where(mask, values * weights[:, None], 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, summed / total, np.nan)


def layer_from_annual(annual: pd.DataFrame | None, variable_key: str, lang: str = "en") -> dict | None:
    """Every cell's yearly difference from its own normal, ready for the browser (None if unusable).

    The normal is the cell's mean over the baseline years (it needs two thirds of them). Temperature, hot
    days and aerosols are shown as plain differences; rain and snow as percent of normal, coloured by
    log2 of the ratio, unless the place's median normal is too small (then millimetres). The colour scale
    is symmetric and ends at the 95th percentile of all cells and years, rounded up to a round value, so
    colours of different years compare directly; values beyond it get the end colour. The yearly average
    of the squares is weighted by cos(latitude).
    """
    if annual is None or annual.empty:
        return None
    base_start, base_end = BASELINE.get(variable_key, DEFAULT_BASELINE)
    needed = math.ceil((base_end - base_start + 1) * MIN_BASELINE_SHARE)
    table = annual.pivot_table(index=["lat", "lon"], columns="year", values="value", aggfunc="mean")
    last_year = LAYER_LAST_YEAR.get(variable_key)
    table = table.reindex(columns=[year for year in sorted(table.columns) if last_year is None or year <= last_year])
    no_snow = 0
    if variable_key == "snowfall":
        snowy = table.max(axis=1) >= NO_SNOW_MAX_MM
        no_snow = int((~snowy).sum())
        table = table[snowy]
    base_columns = [year for year in table.columns if base_start <= year <= base_end]
    if not base_columns:
        return None
    enough = table[base_columns].notna().sum(axis=1) >= needed
    table = table[enough]
    if table.empty:
        return None
    normal = table[base_columns].mean(axis=1).to_numpy(dtype=float)
    values = table.to_numpy(dtype=float)
    weights = np.cos(np.radians(table.index.get_level_values("lat").to_numpy(dtype=float)))
    decimals = DECIMALS[variable_key]
    threshold = PERCENT_MODE.get(variable_key)
    percent = threshold is not None and float(np.median(normal)) >= threshold and bool((normal > 0).all())
    if percent:
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = values / normal[:, None]
        diff = (ratio - 1.0) * 100.0
        logs = np.abs(np.log2(np.clip(ratio, 1 / RATIO_CLIP, RATIO_CLIP)))
        logs = logs[np.isfinite(logs)]
        reach = float(np.percentile(logs, SCALE_PERCENTILE)) if logs.size else 0.0
        ratio_end = next((step for step in RATIO_STEPS if math.log2(step) >= reach - 1e-9), RATIO_STEPS[-1])
        mask = np.isfinite(values)
        wet = np.where(mask, values * weights[:, None], 0.0).sum(axis=0)
        usual = np.where(mask, normal[:, None] * weights[:, None], 0.0).sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(usual > 0, (wet / usual - 1.0) * 100.0, np.nan)
        cell_decimals, scale = 0, None
    else:
        diff = values - normal[:, None]
        flat = np.abs(diff[np.isfinite(diff)])
        scale = nice_ceiling(float(np.percentile(flat, SCALE_PERCENTILE))) if flat.size else 0.0
        if not np.isfinite(scale) or scale <= 0:
            scale = 10.0 ** -decimals
        mean = _weighted_mean(diff, weights)
        cell_decimals, ratio_end = decimals, None
    texts = time_text(lang)
    base = [int(min(base_columns)), int(max(base_columns))]
    kind = "average" if variable_key in AVERAGE_NOT_NORMAL else "normal"
    variable_words = variable_text(lang, VARIABLES[variable_key]) if variable_key in VARIABLES else {}
    cells = [
        {"lat": round(float(lat), 4), "lon": round(float(lon), 4), "n": _clean(normal[k], decimals),
         "d": [_clean(value, cell_decimals) for value in diff[k]]}
        for k, (lat, lon) in enumerate(table.index)
    ]
    means = [_clean(value, cell_decimals if percent else decimals) for value in mean]
    return {
        "key": variable_key,
        "name": variable_words.get("name", variable_key),
        "unit": variable_words.get("annual_unit", ""),
        "years": [int(year) for year in table.columns],
        "cells": cells,
        "mean": means,
        "ranks": year_ranks(means),
        "mode": "percent" if percent else "diff",
        "scale": None if scale is None else round(scale, decimals + 2),
        "ratio": ratio_end,
        "baseline": base,
        "ref": texts[f"ref_{kind}"].format(b0=base[0], b1=base[1]),
        "refShort": texts[f"short_{kind}"],
        "normalWord": texts[f"word_{kind}"],
        "cut": variable_key in LAYER_LAST_YEAR,
        "decimals": SHOW_DECIMALS[variable_key],
        "no_snow": no_snow,
        "palette": PALETTES[PALETTE_OF[variable_key]],
        "words": texts["words"][variable_key],
        "pct": texts["pct"].get(variable_key),
    }


def imagery_list(region_key: str | None, lang: str) -> list[dict]:
    """The NASA GIBS imagery choices with their tile URL, native zoom, years and date rule."""
    names = time_text(lang)["imagery_names"]
    items = []
    for key, spec in IMAGERY.items():
        date = TRUE_COLOUR_DATE.get(region_key, spec["date"]) if key == "true_colour" else spec["date"]
        items.append({
            "key": key, "name": names[key], "daily": spec["daily"], "date": date,
            "url": GIBS_URL.format(layer=spec["layer"], level=spec["level"], ext=spec["ext"]),
            "maxNative": spec["level"], "first": spec["years"][0], "last": spec["years"][1],
            "opacity": spec["opacity"],
            "legend": GIBS_LEGEND_URL.format(name=spec["legend"]) if spec["legend"] else None,
        })
    return items


def start_layer(layers: list[dict], picked: str | None) -> str | None:
    """The measurement the map opens with: the picked case when it has squares, else the first one."""
    keys = [layer["key"] for layer in layers]
    if picked in keys:
        return picked
    return keys[0] if keys else None


def build_payload(layers: list[dict], bbox, region_key: str | None, lang: str, picked: str | None,
                  cell: tuple[float, float]) -> dict:
    """Everything the browser component needs, as one JSON-ready dict."""
    images = imagery_list(region_key, lang)
    first_years = [layer["years"][0] for layer in layers] + [item["first"] for item in images]
    last_years = [layer["years"][-1] for layer in layers] + [item["last"] for item in images]
    start = start_layer(layers, picked)
    start_years = next((layer["years"] for layer in layers if layer["key"] == start), [max(last_years)])
    text = {key: value for key, value in time_text(lang).items()
            if key not in ("words", "imagery_names", "honesty", "gibs_ack", "pct")}
    return {
        "lang": lang,
        "bbox": [float(v) for v in bbox],
        "cell": [float(cell[0]), float(cell[1])],
        "layers": layers,
        "start": start,
        "imagery": images,
        "imageryStart": ("none" if start == picked or picked not in IMAGERY_FOR_CASE
                         else IMAGERY_FOR_CASE[picked]),
        # A case shown only by its satellite image (NDVI, tree cover, CO) opens with the squares hidden.
        "cellsStart": not (picked in IMAGERY_FOR_CASE and picked not in [layer["key"] for layer in layers]),
        "years": [min(first_years), max(last_years)],
        "startYear": int(start_years[-1]),
        "text": text,
    }


def render_timelapse_html(payload: dict) -> str:
    """A self-contained page (Leaflet from a CDN with a pinned version) for ``components.html``."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/").replace("<!--", "<\\!--")
    return (TEMPLATE.replace("__DATA__", data)
            .replace("__LEAFLET_CSS__", LEAFLET_CSS).replace("__LEAFLET_CSS_SRI__", LEAFLET_CSS_SRI)
            .replace("__LEAFLET_JS__", LEAFLET_JS).replace("__LEAFLET_JS_SRI__", LEAFLET_JS_SRI))


def prepared_cell_size(annual: pd.DataFrame) -> tuple[float, float]:
    """The grid spacing (latitude, longitude) of a prepared file, as for the crime scene map."""
    return cell_size(annual.loc[:, ["lat", "lon"]].drop_duplicates())


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="__LEAFLET_CSS__" integrity="__LEAFLET_CSS_SRI__" crossorigin="">
<script src="__LEAFLET_JS__" integrity="__LEAFLET_JS_SRI__" crossorigin=""></script>
<style>
  :root { --ink:#1d2433; --muted:#5b6475; --line:#d9dde5; --panel:#ffffff; --soft:#f5f6f8; }
  html, body { margin:0; padding:0; background:transparent; color:var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
  #tl { border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--panel); }
  .tl-bar { display:flex; flex-wrap:wrap; gap:6px 14px; align-items:center; padding:8px 10px;
    border-bottom:1px solid var(--line); font-size:13px; background:var(--soft); }
  .tl-bar label { display:flex; align-items:center; gap:6px; white-space:nowrap; }
  .tl-bar select { font-size:13px; padding:3px 4px; max-width:240px; }
  .tl-bar input[type=range] { width:90px; }
  #tl-map { height:440px; width:100%; position:relative; }
  .tl-year { position:absolute; left:10px; top:10px; z-index:800; pointer-events:none;
    font-size:44px; font-weight:800; line-height:1; color:#fff; letter-spacing:1px;
    text-shadow:0 2px 6px rgba(0,0,0,.55), 0 0 2px rgba(0,0,0,.8); }
  .tl-info { position:absolute; left:10px; top:60px; z-index:800; pointer-events:none; max-width:70%;
    font-size:12px; color:#fff; text-shadow:0 1px 3px rgba(0,0,0,.8); line-height:1.35;
    background:rgba(29,36,51,.62); border-radius:6px; padding:3px 7px; }
  .tl-info:empty { display:none; }
  .tl-bottom { display:flex; align-items:center; gap:10px; padding:8px 10px 4px; }
  .tl-bottom button { font-size:14px; padding:6px 12px; border:1px solid var(--line); border-radius:8px;
    background:#1d2433; color:#fff; cursor:pointer; min-width:92px; }
  .tl-track { flex:1; position:relative; height:34px; }
  .tl-stripes { position:absolute; left:0; right:0; top:4px; height:14px; display:flex; border-radius:3px;
    overflow:hidden; border:1px solid var(--line); }
  .tl-stripes span { flex:1; height:100%; }
  .tl-stripes span.now { outline:2px solid #1d2433; outline-offset:-2px; }
  .tl-track input[type=range] { position:absolute; left:0; right:0; top:14px; width:100%; margin:0; height:20px;
    background:transparent; }
  .tl-ends { display:flex; justify-content:space-between; font-size:11px; color:var(--muted); padding:0 10px; }
  .tl-legend { padding:4px 10px 2px; font-size:12px; color:var(--muted); }
  .tl-scale { display:flex; align-items:center; gap:6px; margin-top:3px; }
  .tl-scale .bar { flex:1; height:10px; border-radius:3px; border:1px solid var(--line); }
  .tl-note { padding:2px 10px 8px; font-size:12px; color:var(--muted); min-height:16px; }
  .tl-imglegend { padding:0 10px 6px; font-size:12px; color:var(--muted); }
  .tl-imglegend img { display:block; max-width:100%; height:auto; max-height:56px; margin-top:2px; }
  .tl-fail { padding:30px; text-align:center; color:var(--muted); }
  .leaflet-tooltip { font-size:12px; line-height:1.35; }
  @media (max-width: 560px) {
    #tl-map { height:360px; }
    .tl-year { font-size:34px; }
    .tl-info { top:48px; max-width:85%; }
    .tl-bar select { max-width:170px; }
    .tl-bottom button { min-width:70px; padding:6px 8px; min-height:34px; }
    .tl-bar select, .tl-bottom select { font-size:15px; min-height:32px; }
    .tl-bar input[type=range] { width:110px; height:28px; }
    .tl-bar input[type=checkbox] { width:22px; height:22px; }
    .tl-track { height:44px; }
    .tl-track input[type=range] { top:14px; height:28px; }
  }
</style></head>
<body>
<div id="tl">
  <div class="tl-bar">
    <label><input type="checkbox" id="tl-cells" checked> <span id="tl-cells-label"></span>
      <select id="tl-layer" aria-label="layer"></select></label>
    <label><span id="tl-img-label"></span> <select id="tl-img" aria-label="imagery"></select></label>
    <label><span id="tl-op-label"></span> <input type="range" id="tl-op" min="0.15" max="0.9" step="0.05" value="0.55"></label>
  </div>
  <div id="tl-map"><div class="tl-year" id="tl-year"></div><div class="tl-info" id="tl-info"></div></div>
  <div class="tl-bottom">
    <button type="button" id="tl-play"></button>
    <div class="tl-track">
      <div class="tl-stripes" id="tl-stripes"></div>
      <input type="range" id="tl-slider" step="1">
    </div>
    <select id="tl-speed" aria-label="speed"></select>
  </div>
  <div class="tl-ends"><span id="tl-first"></span><span id="tl-stripes-label"></span><span id="tl-last"></span></div>
  <div class="tl-legend" id="tl-legend"></div>
  <div class="tl-imglegend" id="tl-imglegend"></div>
  <div class="tl-note" id="tl-note"></div>
</div>
<script type="application/json" id="tl-data">__DATA__</script>
<script>
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("tl-data").textContent);
  var T = D.text;
  var locale = D.lang === "tr" ? "tr-TR" : "en-US";
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) {
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  function fill(template, values) { return template.replace(/\{(\w+)\}/g, function (m, k) {
    return values[k] === undefined ? m : values[k]; }); }
  if (typeof L === "undefined") { $("tl-map").innerHTML = '<div class="tl-fail">' + esc(T.no_leaflet) + "</div>"; return; }

  var formats = {};
  function fmt(v, dec, signed) {
    if (v === null || v === undefined || !isFinite(v)) { return "–"; }
    var f = formats[dec] || (formats[dec] = new Intl.NumberFormat(locale, {minimumFractionDigits: dec, maximumFractionDigits: dec}));
    var s = f.format(v);
    if (signed && v > 0) { s = "+" + s; }
    return s;
  }
  function mix(a, b, t) {
    var x = parseInt(a.slice(1), 16), y = parseInt(b.slice(1), 16);
    var r = Math.round(((x >> 16) & 255) * (1 - t) + ((y >> 16) & 255) * t);
    var g = Math.round(((x >> 8) & 255) * (1 - t) + ((y >> 8) & 255) * t);
    var bl = Math.round((x & 255) * (1 - t) + (y & 255) * t);
    return "#" + ((1 << 24) | (r << 16) | (g << 8) | bl).toString(16).slice(1);
  }
  function position(v, layer) {
    if (layer.mode === "percent") { return v <= -100 ? -1 : Math.log(1 + v / 100) / Math.log(layer.ratio); }
    return v / layer.scale;
  }
  function pct(v) {
    if (v === null || v === undefined || !isFinite(v)) { return "–"; }
    var sign = v > 0 ? "+" : (v < 0 ? "-" : "");
    return D.lang === "tr" ? sign + "%" + fmt(Math.abs(v), 0) : sign + fmt(Math.abs(v), 0) + "%";
  }
  function show(v, layer) { return layer.mode === "percent" ? pct(v) : fmt(v, layer.decimals, true) + " " + layer.unit; }
  function colour(v, layer) {
    if (v === null || v === undefined) { return null; }
    var p = layer.palette, t = Math.max(-1, Math.min(1, position(v, layer)));
    var pos = (t + 1) / 2 * (p.length - 1), i = Math.min(p.length - 2, Math.floor(pos));
    return mix(p[i], p[i + 1], pos - i);
  }

  var b = D.bbox, bounds = L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  var map = L.map("tl-map", {zoomControl: false, minZoom: 3, maxZoom: 11});
  L.control.zoom({position: "topright"}).addTo(map);
  map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
  map.fitBounds(bounds, {padding: [8, 8]});
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {maxZoom: 19, attribution: "&copy; OpenStreetMap"}).addTo(map);
  map.createPane("imagery").style.zIndex = 250;
  L.rectangle(bounds, {color: "#1d2433", weight: 1.5, fill: false, dashArray: "5 5", interactive: false}).addTo(map);

  var BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
  var cellsGroup = L.layerGroup().addTo(map);
  var layer = null, rects = [], year = D.startYear, opacity = 0.55;
  var imgKey = D.imageryStart, imgShown = null, imgPending = null, timer = null;
  var first = D.years[0], last = D.years[1];

  function yearIndex() { return layer ? layer.years.indexOf(year) : -1; }
  function tip(c) {
    var i = yearIndex(), d = i >= 0 ? c.d[i] : null;
    if (d === null || d === undefined) { return "<b>" + year + "</b><br>" + esc(T.no_data); }
    if (layer.mode === "percent") {
      var value = c.n * (1 + d / 100), words = fill(layer.pct[d >= 0 ? 0 : 1], {p: fmt(Math.abs(d), 0)});
      return "<b>" + year + "</b><br>" + fmt(value, layer.decimals) + " " + esc(layer.unit) + "<br>" +
        esc(fill(T.tip_pct, {words: words, mm: fmt(value - c.n, layer.decimals, true), unit: layer.unit,
          normal_word: layer.normalWord, n: fmt(c.n, layer.decimals)}));
    }
    return "<b>" + year + "</b><br>" + fmt(c.n + d, layer.decimals) + " " + esc(layer.unit) + "<br>" +
      esc(fill(T.tip_diff, {d: fmt(d, layer.decimals, true), unit: layer.unit, ref_short: layer.refShort,
        normal_word: layer.normalWord, n: fmt(c.n, layer.decimals)}));
  }
  function buildCells() {
    cellsGroup.clearLayers(); rects = [];
    if (!layer) { return; }
    var size = layer.cell || D.cell, h = size[0] / 2, w = size[1] / 2;
    layer.cells.forEach(function (c) {
      var r = L.rectangle([[c.lat - h, c.lon - w], [c.lat + h, c.lon + w]],
        {weight: 0.4, color: "#ffffff", opacity: 0.5, fillOpacity: opacity});
      r.bindTooltip(function () { return tip(c); }, {sticky: true});
      r.addTo(cellsGroup); rects.push(r);
    });
  }
  function paint() {
    if (!layer) { return; }
    var i = yearIndex();
    rects.forEach(function (r, k) {
      var d = i >= 0 ? layer.cells[k].d[i] : null, col = colour(d, layer);
      if (col === null) { r.setStyle({fillOpacity: 0, opacity: 0.2}); }
      else { r.setStyle({fillColor: col, fillOpacity: opacity, opacity: 0.5}); }
    });
  }
  function cellsOn() { return !!layer && $("tl-cells").checked; }
  function range() {
    if (cellsOn()) { return [layer.years[0], layer.years[layer.years.length - 1]]; }
    var m = imagery(imgKey);
    return m ? [m.first, m.last] : [D.years[0], D.years[1]];
  }
  function applyRange() {
    var r = range(); first = r[0]; last = r[1];
    var slider = $("tl-slider"); slider.min = first; slider.max = last;
    year = Math.max(first, Math.min(last, year));
    $("tl-first").textContent = first; $("tl-last").textContent = last;
    stripes();
  }
  function stripes() {
    var box = $("tl-stripes"); box.innerHTML = "";
    for (var y = first; y <= last; y++) {
      var s = document.createElement("span"), i = layer ? layer.years.indexOf(y) : -1;
      var v = i >= 0 ? layer.mean[i] : null, col = layer ? colour(v, layer) : null;
      s.style.background = col || "transparent";
      s.title = y + (v === null || v === undefined ? "" : ": " + show(v, layer));
      s.setAttribute("data-year", y);
      box.appendChild(s);
    }
    markStripe();
  }
  function markStripe() {
    var spans = $("tl-stripes").children;
    for (var k = 0; k < spans.length; k++) { spans[k].className = (+spans[k].getAttribute("data-year") === year) ? "now" : ""; }
  }
  function legend() {
    if (!layer || !$("tl-cells").checked) { $("tl-legend").innerHTML = ""; return; }
    var p = layer.palette, grad = "linear-gradient(90deg," + p.join(",") + ")", low, high;
    if (layer.mode === "percent") { low = pct((1 / layer.ratio - 1) * 100); high = pct((layer.ratio - 1) * 100); }
    else { low = fmt(-layer.scale, layer.decimals) + " " + layer.unit; high = fmt(layer.scale, layer.decimals, true) + " " + layer.unit; }
    var title = fill(layer.mode === "percent" ? T.legend_pct : T.legend_diff, {name: layer.name, ref: layer.ref});
    $("tl-legend").innerHTML = esc(title) + '<div class="tl-scale"><span>' + esc(low) +
      '</span><span class="bar" style="background:' + grad + '"></span><span>' + esc(high) + "</span></div>";
  }
  function info() {
    var lines = [];
    if (layer && $("tl-cells").checked) {
      var i = yearIndex();
      if (i < 0 || layer.mean[i] === null || layer.mean[i] === undefined) { lines.push(esc(T.no_data)); }
      else {
        lines.push(esc(fill(T.area_mean, {value: show(layer.mean[i], layer), ref: layer.ref})));
        var rk = layer.ranks[i], n = layer.mean.filter(function (v) { return v !== null; }).length;
        var side = (rk[0] !== null && rk[0] <= 3) ? "high" : ((rk[1] !== null && rk[1] <= 3) ? "low" : null);
        if (side) {
          var rank = side === "high" ? rk[0] : rk[1];
          var text = rank === 1 ? fill(T.rank1, {word: layer.words[side + "1"], n: n})
                                : fill(T.rank23, {word: layer.words[side], n: n, ord: T.ords[String(rank)]});
          lines.push(esc(text));
        }
      }
    }
    $("tl-info").innerHTML = lines.join("<br>");
  }
  function note() {
    var parts = [], m = imagery(imgKey);
    if (m) {
      if (year < m.first || year > m.last) { parts.push(fill(T.imagery_range, {name: m.name, first: m.first, last: m.last})); }
      else if (m.daily) {
        var bits = m.date.split("-"), day = new Date(Date.UTC(year, +bits[0] - 1, +bits[1]));
        parts.push(m.name + ": " + fill(T.photo_day, {date: day.toLocaleDateString(locale, {day: "numeric", month: "long", year: "numeric", timeZone: "UTC"})}));
      }
    }
    if (layer && $("tl-cells").checked) {
      if (layer.no_snow) { parts.push(fill(T.no_snow, {n: layer.no_snow})); }
      if (layer.cut) { parts.push(T.aod_cut); }
      else if (year === layer.years[layer.years.length - 1]) { parts.push(T.provisional); }
    } else if (D.layers.length) { parts.push(T.tick_hint); }
    $("tl-note").textContent = parts.join(" · ");
  }
  function imagery(key) { for (var k = 0; k < D.imagery.length; k++) { if (D.imagery[k].key === key) { return D.imagery[k]; } } return null; }
  function imageLegend() {
    var m = imagery(imgKey), box = $("tl-imglegend");
    if (!m || !m.legend) { box.innerHTML = ""; return; }
    box.innerHTML = esc(T.image_colours) + '<img src="' + esc(m.legend) + '" alt="' + esc(m.name) + '" loading="lazy">';
  }
  function swapIn(next) {
    if (next !== imgPending) { return; }
    next.setOpacity(next._tlOpacity);
    if (imgShown && imgShown !== next) { map.removeLayer(imgShown); }
    imgShown = next; imgPending = null;
  }
  function setImagery() {
    var m = imagery(imgKey);
    if (!m || year < m.first || year > m.last) {
      if (imgPending) { map.removeLayer(imgPending); imgPending = null; }
      if (imgShown) { map.removeLayer(imgShown); imgShown = null; }
      return;
    }
    var url = m.url.replace("{time}", year + "-" + m.date);
    if (imgShown && imgShown._tlUrl === url && !imgPending) { return; }
    if (imgPending) { if (imgPending._tlUrl === url) { return; } map.removeLayer(imgPending); }
    var first_image = !imgShown;
    var next = L.tileLayer(url, {pane: "imagery", maxNativeZoom: m.maxNative, maxZoom: 11,
      opacity: first_image ? m.opacity : 0, errorTileUrl: BLANK, bounds: bounds.pad(0.6), attribution: esc(T.credit)});
    next._tlUrl = url; next._tlOpacity = m.opacity; next._tlKey = m.key;
    if (first_image) { imgShown = next; next.addTo(map); return; }  // nothing to fade from: show tiles as they come
    imgPending = next;
    next.once("load", function () { swapIn(next); });
    setTimeout(function () { if (map.hasLayer(next)) { swapIn(next); } }, 5000);
    next.addTo(map);
  }
  function update() {
    $("tl-year").textContent = year; $("tl-slider").value = year;
    paint(); markStripe(); info(); note(); setImagery();
  }
  function chooseLayer(key) {
    layer = null;
    for (var k = 0; k < D.layers.length; k++) { if (D.layers[k].key === key) { layer = D.layers[k]; } }
    buildCells(); applyRange(); paint(); legend(); update();
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } $("tl-play").textContent = "▶ " + T.play; }
  function play() {
    if (year >= last) { year = first; update(); }
    var ms = {slow: 1500, normal: 900, fast: 450}[$("tl-speed").value] || 900;
    timer = setInterval(function () { if (year >= last) { stop(); return; } year += 1; update(); }, ms);
    $("tl-play").textContent = "⏸ " + T.pause;
  }

  $("tl-cells-label").textContent = T.data;
  $("tl-img-label").textContent = T.imagery;
  $("tl-op-label").textContent = T.opacity;
  $("tl-stripes-label").textContent = T.stripes;
  var layerSelect = $("tl-layer");
  D.layers.forEach(function (l) { var o = document.createElement("option"); o.value = l.key; o.textContent = l.name; layerSelect.appendChild(o); });
  if (!D.layers.length) { $("tl-cells").checked = false; $("tl-cells").disabled = true; layerSelect.disabled = true; }
  var imgSelect = $("tl-img");
  [{key: "none", name: T.none}].concat(D.imagery).forEach(function (m) { var o = document.createElement("option"); o.value = m.key; o.textContent = m.name; imgSelect.appendChild(o); });
  imgSelect.value = imagery(imgKey) ? imgKey : "none";
  var speed = $("tl-speed");
  [["slow", T.slow], ["normal", T.normal_speed], ["fast", T.fast]].forEach(function (s) { var o = document.createElement("option"); o.value = s[0]; o.textContent = s[1]; speed.appendChild(o); });
  speed.value = "normal";
  var slider = $("tl-slider"); slider.min = first; slider.max = last; slider.setAttribute("aria-label", T.year);

  layerSelect.addEventListener("change", function () {
    if (!$("tl-cells").checked) { $("tl-cells").checked = true; cellsGroup.addTo(map); }  // a chosen measurement shows at once
    chooseLayer(layerSelect.value);
  });
  $("tl-cells").addEventListener("change", function () {
    if ($("tl-cells").checked) { cellsGroup.addTo(map); } else { map.removeLayer(cellsGroup); }
    applyRange(); legend(); update();
  });
  imgSelect.addEventListener("change", function () {
    imgKey = imgSelect.value;
    if (imgShown && (!imagery(imgKey) || imgShown._tlKey !== imgKey)) { map.removeLayer(imgShown); imgShown = null; }
    applyRange(); update(); imageLegend();
  });
  $("tl-op").addEventListener("input", function () { opacity = +$("tl-op").value; paint(); });
  slider.addEventListener("input", function () { year = +slider.value; update(); });
  $("tl-play").addEventListener("click", function () { if (timer) { stop(); } else { play(); } });
  speed.addEventListener("change", function () { if (timer) { stop(); play(); } });

  if (D.start) { layerSelect.value = D.start; }
  if (D.cellsStart === false) { $("tl-cells").checked = false; map.removeLayer(cellsGroup); }
  stop();
  imageLegend();
  chooseLayer(D.start);
})();
</script>
</body></html>
"""
