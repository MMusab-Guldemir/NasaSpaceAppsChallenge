"""Quick pick: a city. About 60 cities that set the custom rectangle to a box around them.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

In the "Anywhere on Earth" mode, the sidebar has a searchable list of cities. Picking one sets the
custom rectangle to a 2° × 2° box centred on the city (``city_bbox``), and the app runs its usual
live NASA POWER analysis for that box. A 2° side is also the smallest box a NASA POWER regional
request accepts, so a city box needs one request per measurement. ``city_for_bbox`` finds the city
again from the rectangle, so titles can say "Around Istanbul" instead of only the coordinates.

Twenty Turkish cities come first in the table (the local jury is in Istanbul), then forty from every
continent. Coordinates are city centres to 2 decimals (about 1 km), written from general knowledge
and spot-checked against public gazetteers (Wikipedia, GeoNames-based sites, the OpenStreetMap
wiki). For large cities the sources differ by a few hundredths of a degree, which does not matter
for a box 2° wide.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from trend.area import MAX_SPAN, STEP, normalize_bbox

DEFAULT_HALF_SIZE = 1.0  # degrees from the city to each side of its box: a 2° × 2° box
MATCH_TOLERANCE = 1e-6  # degrees; a rectangle within this of a city box is that city's box


@dataclass(frozen=True)
class City:
    """A city of the quick pick list: key, names per interface language and the centre point."""

    key: str
    name: dict[str, str] = field(hash=False)  # city name per interface language
    country: dict[str, str] = field(hash=False)  # country name per interface language
    lat: float  # degrees north, 2 decimals
    lon: float  # degrees east, 2 decimals


COUNTRIES: dict[str, dict[str, str]] = {
    "tr": {"en": "Türkiye", "tr": "Türkiye"},
    "us": {"en": "USA", "tr": "ABD"},
    "mx": {"en": "Mexico", "tr": "Meksika"},
    "ca": {"en": "Canada", "tr": "Kanada"},
    "br": {"en": "Brazil", "tr": "Brezilya"},
    "ar": {"en": "Argentina", "tr": "Arjantin"},
    "pe": {"en": "Peru", "tr": "Peru"},
    "co": {"en": "Colombia", "tr": "Kolombiya"},
    "gb": {"en": "UK", "tr": "Birleşik Krallık"},
    "fr": {"en": "France", "tr": "Fransa"},
    "de": {"en": "Germany", "tr": "Almanya"},
    "es": {"en": "Spain", "tr": "İspanya"},
    "it": {"en": "Italy", "tr": "İtalya"},
    "gr": {"en": "Greece", "tr": "Yunanistan"},
    "ru": {"en": "Russia", "tr": "Rusya"},
    "ua": {"en": "Ukraine", "tr": "Ukrayna"},
    "eg": {"en": "Egypt", "tr": "Mısır"},
    "ng": {"en": "Nigeria", "tr": "Nijerya"},
    "ke": {"en": "Kenya", "tr": "Kenya"},
    "et": {"en": "Ethiopia", "tr": "Etiyopya"},
    "za": {"en": "South Africa", "tr": "Güney Afrika"},
    "ma": {"en": "Morocco", "tr": "Fas"},
    "sa": {"en": "Saudi Arabia", "tr": "Suudi Arabistan"},
    "ae": {"en": "UAE", "tr": "BAE"},
    "ir": {"en": "Iran", "tr": "İran"},
    "az": {"en": "Azerbaijan", "tr": "Azerbaycan"},
    "uz": {"en": "Uzbekistan", "tr": "Özbekistan"},
    "pk": {"en": "Pakistan", "tr": "Pakistan"},
    "in": {"en": "India", "tr": "Hindistan"},
    "bd": {"en": "Bangladesh", "tr": "Bangladeş"},
    "th": {"en": "Thailand", "tr": "Tayland"},
    "id": {"en": "Indonesia", "tr": "Endonezya"},
    "ph": {"en": "Philippines", "tr": "Filipinler"},
    "cn": {"en": "China", "tr": "Çin"},
    "jp": {"en": "Japan", "tr": "Japonya"},
    "kr": {"en": "South Korea", "tr": "Güney Kore"},
    "au": {"en": "Australia", "tr": "Avustralya"},
    "is": {"en": "Iceland", "tr": "İzlanda"},
}


def _city(key: str, name_en: str, name_tr: str, country: str, lat: float, lon: float) -> City:
    return City(key, {"en": name_en, "tr": name_tr}, dict(COUNTRIES[country]), lat, lon)


CITIES: tuple[City, ...] = (
    # Türkiye
    _city("istanbul", "Istanbul", "İstanbul", "tr", 41.01, 28.98),
    _city("ankara", "Ankara", "Ankara", "tr", 39.93, 32.86),
    _city("izmir", "Izmir", "İzmir", "tr", 38.42, 27.13),
    _city("bursa", "Bursa", "Bursa", "tr", 40.20, 29.06),
    _city("antalya", "Antalya", "Antalya", "tr", 36.89, 30.70),
    _city("adana", "Adana", "Adana", "tr", 37.00, 35.32),
    _city("konya", "Konya", "Konya", "tr", 37.87, 32.48),
    _city("gaziantep", "Gaziantep", "Gaziantep", "tr", 37.06, 37.38),
    _city("sanliurfa", "Şanlıurfa", "Şanlıurfa", "tr", 37.16, 38.79),
    _city("diyarbakir", "Diyarbakır", "Diyarbakır", "tr", 37.91, 40.23),
    _city("erzurum", "Erzurum", "Erzurum", "tr", 39.90, 41.27),
    _city("van", "Van", "Van", "tr", 38.49, 43.38),
    _city("trabzon", "Trabzon", "Trabzon", "tr", 41.00, 39.73),
    _city("samsun", "Samsun", "Samsun", "tr", 41.28, 36.33),
    _city("kayseri", "Kayseri", "Kayseri", "tr", 38.73, 35.49),
    _city("eskisehir", "Eskişehir", "Eskişehir", "tr", 39.78, 30.52),
    _city("mersin", "Mersin", "Mersin", "tr", 36.80, 34.63),
    _city("mugla", "Muğla", "Muğla", "tr", 37.22, 28.37),
    _city("edirne", "Edirne", "Edirne", "tr", 41.68, 26.56),
    _city("canakkale", "Çanakkale", "Çanakkale", "tr", 40.15, 26.41),
    # The Americas
    _city("new_york", "New York", "New York", "us", 40.71, -74.01),
    _city("chicago", "Chicago", "Şikago", "us", 41.88, -87.63),
    _city("mexico_city", "Mexico City", "Meksiko", "mx", 19.43, -99.13),
    _city("toronto", "Toronto", "Toronto", "ca", 43.65, -79.38),
    _city("sao_paulo", "São Paulo", "São Paulo", "br", -23.55, -46.63),
    _city("buenos_aires", "Buenos Aires", "Buenos Aires", "ar", -34.60, -58.38),
    _city("lima", "Lima", "Lima", "pe", -12.05, -77.04),
    _city("bogota", "Bogotá", "Bogota", "co", 4.71, -74.07),
    # Europe
    _city("london", "London", "Londra", "gb", 51.51, -0.13),
    _city("paris", "Paris", "Paris", "fr", 48.86, 2.35),
    _city("berlin", "Berlin", "Berlin", "de", 52.52, 13.40),
    _city("madrid", "Madrid", "Madrid", "es", 40.42, -3.70),
    _city("rome", "Rome", "Roma", "it", 41.89, 12.48),
    _city("athens", "Athens", "Atina", "gr", 37.98, 23.73),
    _city("moscow", "Moscow", "Moskova", "ru", 55.76, 37.62),
    _city("kyiv", "Kyiv", "Kiev", "ua", 50.45, 30.52),
    _city("reykjavik", "Reykjavik", "Reykjavik", "is", 64.15, -21.94),
    # Africa
    _city("cairo", "Cairo", "Kahire", "eg", 30.04, 31.24),
    _city("lagos", "Lagos", "Lagos", "ng", 6.45, 3.39),
    _city("nairobi", "Nairobi", "Nairobi", "ke", -1.29, 36.82),
    _city("addis_ababa", "Addis Ababa", "Addis Ababa", "et", 9.03, 38.74),
    _city("johannesburg", "Johannesburg", "Johannesburg", "za", -26.20, 28.05),
    _city("casablanca", "Casablanca", "Kazablanka", "ma", 33.57, -7.59),
    # Asia and Oceania
    _city("riyadh", "Riyadh", "Riyad", "sa", 24.69, 46.72),
    _city("dubai", "Dubai", "Dubai", "ae", 25.26, 55.30),
    _city("tehran", "Tehran", "Tahran", "ir", 35.69, 51.39),
    _city("baku", "Baku", "Bakü", "az", 40.39, 49.88),
    _city("tashkent", "Tashkent", "Taşkent", "uz", 41.30, 69.24),
    _city("karachi", "Karachi", "Karaçi", "pk", 24.86, 67.01),
    _city("new_delhi", "New Delhi", "Yeni Delhi", "in", 28.61, 77.21),
    _city("mumbai", "Mumbai", "Mumbai", "in", 19.08, 72.88),
    _city("dhaka", "Dhaka", "Dakka", "bd", 23.71, 90.41),
    _city("bangkok", "Bangkok", "Bangkok", "th", 13.75, 100.50),
    _city("jakarta", "Jakarta", "Cakarta", "id", -6.21, 106.85),
    _city("manila", "Manila", "Manila", "ph", 14.60, 120.98),
    _city("shanghai", "Shanghai", "Şanghay", "cn", 31.23, 121.47),
    _city("tokyo", "Tokyo", "Tokyo", "jp", 35.69, 139.69),
    _city("seoul", "Seoul", "Seul", "kr", 37.57, 126.98),
    _city("sydney", "Sydney", "Sidney", "au", -33.87, 151.21),
    _city("melbourne", "Melbourne", "Melbourne", "au", -37.81, 144.96),
)

CITY_BY_KEY: dict[str, City] = {city.key: city for city in CITIES}

CITY_TEXT = {
    "en": {
        "label": "Quick pick: a city",
        "placeholder": "Type a city…",
        "help": (
            "Sets the rectangle to a 2° × 2° box (about 200 km across) centred on the city. You can "
            "still move or resize it on the map, or change the corners below."
        ),
        "near": "{city} area, {country}",
    },
    "tr": {
        "label": "Hızlı seçim: bir şehir",
        "placeholder": "Şehir yaz…",
        "help": (
            "Dikdörtgeni, şehri ortalayan 2° × 2°'lik bir kutuya ayarlar (yaklaşık 200 km). Kutuyu "
            "haritada yine taşıyabilir, boyutunu değiştirebilir ya da aşağıdaki köşe değerlerini "
            "düzenleyebilirsin."
        ),
        "near": "{city} çevresi, {country}",
    },
}


def city_text(lang: str, key: str, **values) -> str:
    """A text of the quick pick in the interface language (English if there is none)."""
    text = CITY_TEXT.get(lang, CITY_TEXT["en"])[key]
    return text.format(**values) if values else text


def _as_city(city: City | str) -> City:
    """A City from a City or its key (Streamlit hands the key to ``format_func``)."""
    return city if isinstance(city, City) else CITY_BY_KEY[city]


def city_name(lang: str, city: City | str) -> str:
    """The city's name in the interface language (English if there is none)."""
    city = _as_city(city)
    return city.name.get(lang, city.name["en"])


def country_name(lang: str, city: City | str) -> str:
    """The city's country in the interface language (English if there is none)."""
    city = _as_city(city)
    return city.country.get(lang, city.country["en"])


def city_label(lang: str, city: City | str) -> str:
    """The list entry of a city, for example 'Istanbul, Türkiye' or 'Kahire, Mısır'."""
    return f"{city_name(lang, city)}, {country_name(lang, city)}"


def near_label(lang: str, city: City | str) -> str:
    """The area name for titles: 'Around Istanbul, Türkiye' or 'İstanbul çevresi, Türkiye'."""
    return city_text(lang, "near", city=city_name(lang, city), country=country_name(lang, city))


# Turkish alphabetical order, with the Latin letters Turkish does not use (q, w, x) in their usual place.
TURKISH_ORDER = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_TURKISH_RANK = {letter: rank for rank, letter in enumerate(TURKISH_ORDER)}


def _strip_marks(text: str) -> str:
    """Letters without accents: 'São' -> 'Sao', 'Bogotá' -> 'Bogota'."""
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))


def sort_key(lang: str, text: str) -> tuple:
    """Alphabetical sort key of a label in the interface language.

    Turkish: the Turkish alphabet (C < Ç < D, G < Ğ < H, I < İ, O < Ö < P, S < Ş < T, U < Ü < V),
    with the dotted and dotless capital I lowered the Turkish way; other accents are ignored
    (São Paulo sorts as Sao Paulo). Other languages: case and accents are ignored (Şanlıurfa sorts as
    Sanliurfa). Spaces and punctuation come before letters, so 'Van, Türkiye' precedes 'Vancouver'.
    """
    text = unicodedata.normalize("NFC", text)
    if lang != "tr":
        return (_strip_marks(text.replace("ı", "i").casefold()),)
    lowered = text.replace("I", "ı").replace("İ", "i").lower()
    key = []
    for ch in lowered:
        if ch not in _TURKISH_RANK:
            ch = _strip_marks(ch) or ch
        rank = _TURKISH_RANK.get(ch)
        key.append((1, rank) if rank is not None else (0, ord(ch)))
    return tuple(key)


@lru_cache(maxsize=None)
def _sorted_keys(lang: str) -> tuple[str, ...]:
    return tuple(
        sorted(CITY_BY_KEY, key=lambda key: (sort_key(lang, city_label(lang, key)), city_label(lang, key)))
    )


def city_options(lang: str) -> list[str]:
    """City keys in alphabetical order of their list entries in the interface language."""
    return list(_sorted_keys(lang))


def _slide_inside(low: float, high: float, lower_limit: float, upper_limit: float) -> tuple[float, float]:
    """Move an interval inside the limits without changing its length (it is never longer)."""
    if low < lower_limit:
        low, high = lower_limit, high + (lower_limit - low)
    if high > upper_limit:
        low, high = low - (high - upper_limit), upper_limit
    return low, high


def city_bbox(city: City | str, half_size: float = DEFAULT_HALF_SIZE) -> tuple[float, float, float, float]:
    """The city's box (west, south, east, north): ``half_size`` degrees from the centre to each side.

    Rounded to 2 decimals by ``normalize_bbox``, so the box passes it unchanged. Near the date line
    or a pole the box slides inside the map and keeps its size; it always contains the city.
    ``half_size`` must be between 0.01 and 20 degrees (the largest rectangle is 40° × 40°).
    """
    city = _as_city(city)
    if not STEP <= half_size <= MAX_SPAN / 2:
        raise ValueError(f"half_size must be between {STEP} and {MAX_SPAN / 2} degrees, not {half_size}")
    west, east = _slide_inside(city.lon - half_size, city.lon + half_size, -180.0, 180.0)
    south, north = _slide_inside(city.lat - half_size, city.lat + half_size, -90.0, 90.0)
    return normalize_bbox(west, south, east, north)


def city_for_bbox(bbox, half_size: float = DEFAULT_HALF_SIZE) -> City | None:
    """The city whose box is this rectangle (within 1e-6 degrees), or None.

    The app uses it to name a custom area after its city in titles; a rectangle the user moved or
    resized is no longer a city box, so it keeps its coordinates-only name.
    """
    try:
        values = tuple(float(value) for value in bbox)
    except (TypeError, ValueError):
        return None
    if len(values) != 4:
        return None
    for city in CITIES:
        if all(abs(a - b) <= MATCH_TOLERANCE for a, b in zip(city_bbox(city, half_size), values)):
            return city
    return None
