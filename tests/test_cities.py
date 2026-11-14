"""Tests for the quick pick of a city (trend/cities.py): names, coordinates, boxes and sorting.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026.

No network: everything here is computed from the table in trend/cities.py.
"""
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from trend.area import normalize_bbox, power_request_boxes
from trend.cities import (
    CITIES,
    CITY_BY_KEY,
    CITY_TEXT,
    DEFAULT_HALF_SIZE,
    TURKISH_ORDER,
    City,
    city_bbox,
    city_for_bbox,
    city_label,
    city_options,
    city_text,
    near_label,
    sort_key,
)
from trend.regions import REGIONS

TURKISH_CITIES = (
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya", "gaziantep", "sanliurfa",
    "diyarbakir", "erzurum", "van", "trabzon", "samsun", "kayseri", "eskisehir", "mersin", "mugla",
    "edirne", "canakkale",
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to open a connection fails the test."""

    def refuse(*args, **kwargs):
        raise AssertionError("trend/cities.py must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_keys_are_unique_and_every_city_has_both_languages():
    keys = [city.key for city in CITIES]
    assert len(keys) == len(set(keys)) == len(CITY_BY_KEY)
    assert 55 <= len(CITIES) <= 70
    for city in CITIES:
        for lang in ("en", "tr"):
            assert city.name[lang].strip() and city.country[lang].strip()


def test_twenty_turkish_cities():
    assert all(CITY_BY_KEY[key].country == {"en": "Türkiye", "tr": "Türkiye"} for key in TURKISH_CITIES)
    assert sum(city.country["en"] == "Türkiye" for city in CITIES) == len(TURKISH_CITIES)


def test_coordinates_are_on_earth_with_two_decimals():
    for city in CITIES:
        assert -90 < city.lat < 90 and -180 < city.lon < 180
        assert round(city.lat, 2) == city.lat and round(city.lon, 2) == city.lon


@pytest.mark.parametrize(
    "key, lat, lon",
    [
        ("istanbul", 41.01, 28.98),
        ("ankara", 39.93, 32.86),
        ("new_york", 40.71, -74.01),
        ("sydney", -33.87, 151.21),
        ("reykjavik", 64.15, -21.94),
        ("buenos_aires", -34.60, -58.38),
        ("cairo", 30.04, 31.24),
        ("tokyo", 35.69, 139.69),
    ],
)
def test_known_coordinates(key, lat, lon):
    city = CITY_BY_KEY[key]
    assert city.lat == pytest.approx(lat, abs=0.15)
    assert city.lon == pytest.approx(lon, abs=0.15)


def test_hemispheres():
    """A sign slip (74 instead of -74) would put a city on the wrong side of the planet."""
    south = {"sao_paulo", "buenos_aires", "lima", "nairobi", "johannesburg", "jakarta", "sydney", "melbourne"}
    west = {"new_york", "chicago", "mexico_city", "toronto", "sao_paulo", "buenos_aires", "lima", "bogota",
            "london", "madrid", "reykjavik", "casablanca"}
    assert {city.key for city in CITIES if city.lat < 0} == south
    assert {city.key for city in CITIES if city.lon < 0} == west


def test_every_box_passes_normalize_bbox_unchanged_and_contains_its_city():
    for city in CITIES:
        box = city_bbox(city)
        assert normalize_bbox(*box) == box
        assert all(round(value, 2) == value for value in box)
        west, south, east, north = box
        assert west <= city.lon <= east and south <= city.lat <= north
        assert east - west == pytest.approx(2 * DEFAULT_HALF_SIZE)
        assert north - south == pytest.approx(2 * DEFAULT_HALF_SIZE)
        assert (west + east) / 2 == pytest.approx(city.lon) and (south + north) / 2 == pytest.approx(city.lat)


def test_a_city_box_is_one_nasa_power_request():
    assert all(len(power_request_boxes(city_bbox(city))) == 1 for city in CITIES)


def test_boxes_are_unique_and_no_prepared_region_looks_like_a_city():
    boxes = [city_bbox(city) for city in CITIES]
    assert len(set(boxes)) == len(boxes)
    # Custom mode starts from the prepared region on screen; that rectangle keeps its own name.
    assert all(city_for_bbox(region.bbox) is None for region in REGIONS.values())


@pytest.mark.parametrize("lat, lon", [(89.9, 179.9), (-89.9, -179.9), (0.0, 180.0), (90.0, -180.0), (-90.0, 0.5)])
@pytest.mark.parametrize("half_size", [0.01, 0.5, 1.0, 7.5, 20.0])
def test_boxes_at_the_date_line_and_the_poles_stay_valid(lat, lon, half_size):
    city = City("edge", {"en": "Edge"}, {"en": "Nowhere"}, lat, lon)
    box = city_bbox(city, half_size)
    assert normalize_bbox(*box) == box
    west, south, east, north = box
    assert -180 <= west < east <= 180 and -90 <= south < north <= 90
    assert west <= lon <= east and south <= lat <= north
    assert east - west == pytest.approx(2 * half_size, abs=0.011)  # slid inside, not cut
    assert north - south == pytest.approx(2 * half_size, abs=0.011)


@pytest.mark.parametrize("half_size", [0, -1, 0.001, 20.5, 90])
def test_half_size_out_of_range_is_refused(half_size):
    with pytest.raises(ValueError):
        city_bbox("istanbul", half_size)


def test_city_for_bbox_round_trips():
    for city in CITIES:
        assert city_for_bbox(city_bbox(city)) is city
        assert city_for_bbox(list(city_bbox(city))) is city  # session state may hold a list
        assert city_for_bbox(city_bbox(city, 3.0), half_size=3.0) is city


def test_city_for_bbox_needs_the_exact_box():
    istanbul = CITY_BY_KEY["istanbul"]
    west, south, east, north = city_bbox(istanbul)
    assert city_for_bbox((west, south, east + 5e-7, north)) is istanbul
    assert city_for_bbox((west, south, east + 0.01, north)) is None  # resized on the map
    assert city_for_bbox((west + 0.5, south, east + 0.5, north)) is None  # moved on the map
    assert city_for_bbox(city_bbox(istanbul, 3.0)) is None  # another size
    for bad in (None, (), (1.0, 2.0, 3.0), ("a", 2, 3, 4), 42):
        assert city_for_bbox(bad) is None


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_options_hold_every_city_once_in_alphabetical_order(lang):
    options = city_options(lang)
    assert sorted(options) == sorted(CITY_BY_KEY)
    keys = [sort_key(lang, city_label(lang, key)) for key in options]
    assert keys == sorted(keys)
    assert city_options(lang) is not city_options(lang)  # callers get their own list


def _turkish_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


def test_turkish_order_follows_the_turkish_alphabet():
    labels = [city_label("tr", key) for key in city_options("tr")]
    first_letters = [TURKISH_ORDER.index(_turkish_lower(label[0])) for label in labels]
    assert first_letters == sorted(first_letters)
    position = labels.index
    assert position("Cakarta, Endonezya") < position("Çanakkale, Türkiye") < position("Dakka, Bangladeş")
    assert position("Gaziantep, Türkiye") < position("İstanbul, Türkiye") < position("İzmir, Türkiye")
    assert position("Muğla, Türkiye") < position("Mumbai, Hindistan")  # Ğ comes before M
    assert position("Samsun, Türkiye") < position("São Paulo, Brezilya") < position("Seul, Güney Kore")
    assert position("Sidney, Avustralya") < position("Şanghay, Çin") < position("Şanlıurfa, Türkiye")
    assert position("Şikago, ABD") < position("Tahran, İran") < position("Taşkent, Özbekistan")
    assert labels[-1] == "Yeni Delhi, Hindistan"


def test_english_order_ignores_accents():
    labels = [city_label("en", key) for key in city_options("en")]
    position = labels.index
    assert labels[0] == "Adana, Türkiye"
    assert position("Cairo, Egypt") < position("Çanakkale, Türkiye") < position("Casablanca, Morocco")
    assert position("Samsun, Türkiye") < position("Şanlıurfa, Türkiye") < position("São Paulo, Brazil")
    assert position("Gaziantep, Türkiye") < position("Istanbul, Türkiye") < position("Izmir, Türkiye")
    assert position("Muğla, Türkiye") < position("Mumbai, India")


def test_english_and_turkish_texts_have_the_same_keys():
    assert set(CITY_TEXT["en"]) == set(CITY_TEXT["tr"])
    assert {"label", "placeholder", "help"} <= set(CITY_TEXT["en"])
    for texts in CITY_TEXT.values():
        assert all(text.strip() for text in texts.values())


def test_texts():
    assert city_text("en", "label") == "Quick pick: a city"
    assert city_text("tr", "label") == "Hızlı seçim: bir şehir"
    assert city_text("en", "placeholder") == "Type a city…"
    assert city_text("tr", "placeholder") == "Şehir yaz…"
    assert city_text("de", "label") == "Quick pick: a city"  # English when a language is missing
    size = f"{2 * DEFAULT_HALF_SIZE:g}° × {2 * DEFAULT_HALF_SIZE:g}°"
    assert size in city_text("en", "help") and size in city_text("tr", "help")


def test_labels_in_both_languages():
    assert city_label("en", "istanbul") == "Istanbul, Türkiye"
    assert city_label("tr", "istanbul") == "İstanbul, Türkiye"
    assert city_label("tr", CITY_BY_KEY["cairo"]) == "Kahire, Mısır"
    assert city_label("en", CITY_BY_KEY["cairo"]) == "Cairo, Egypt"
    assert city_label("tr", "moscow") == "Moskova, Rusya"
    assert city_label("tr", "new_york") == "New York, ABD"
    assert city_label("tr", "tokyo") == "Tokyo, Japonya"
    assert city_label("de", "berlin") == "Berlin, Germany"


def test_near_labels():
    assert near_label("en", "istanbul") == "Istanbul area, Türkiye"
    assert near_label("tr", "istanbul") == "İstanbul çevresi, Türkiye"
    assert near_label("tr", CITY_BY_KEY["ankara"]) == "Ankara çevresi, Türkiye"
    assert near_label("tr", "cairo") == "Kahire çevresi, Mısır"


def test_module_does_not_import_streamlit_or_network_libraries():
    code = (
        "import sys, trend.cities; "
        "print(sorted(m for m in ('streamlit', 'requests', 'urllib3', 'http.client') if m in sys.modules))"
    )
    root = Path(__file__).resolve().parent.parent
    output = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=True)
    assert output.stdout.strip() == "[]"
