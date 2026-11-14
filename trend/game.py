"""Detective exam: a short game built on the app's own data and statistics.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. The game was offered by the AI as an option; Team Avni approved it,
asked for the more playful version (self-drawing chart, badges, streaks), asked to explain why each
trend rises, falls or is chance, and asked for a 20-case exam.

A secret, unlabeled annual series draws itself year by year. The player decides, as early as they
dare, whether it shows a real increase, a real decrease or just chance. The answer key comes from
the same statistics as the investigation board (``trend.stats.analyze_trend``), so the game never
disagrees with the rest of the app. After each answer, a "Why?" note gives a possible explanation:
a hand-written note for a few teaching cases, otherwise the app's own "Possible reasons" catalog.
"""
from __future__ import annotations

import json

import pandas as pd

from trend.fetch import load_processed
from trend.i18n import (
    chance_phrase, num, reasons, region_context, region_name, status_text, t, variable_text,
)
from trend.regions import REGIONS
from trend.stats import MIN_YEARS, analyze_trend, to_annual
from trend.variables import VARIABLES

NO_SNOW_MAX_MM = 1.0  # same rule as the app: a snowfall series that never reaches 1 mm is "No snow"

# Every prepared region and measurement enters the game with its full record. These extra cases
# add windows and hand-written notes: (region, variable, window, note, big case). Window: None =
# full record, ("first", n) or ("last", n) years, or (start_year, end_year).
SPECIAL_CASES: tuple[tuple, ...] = (
    ("marmara", "air_temperature", None, "temp_marmara", False),
    ("colorado", "air_temperature", ("last", 20), "temp_recent", False),
    ("marmara", "air_temperature", ("last", 20), "temp_recent", False),
    ("alps", "air_temperature", ("last", 20), "temp_recent", False),
    ("beijing", "no2", (2013, 2025), "beijing_no2_plan", False),
    ("beijing", "aod", (2013, 2025), "beijing_aod_plan", False),
    ("marmara", "ndvi", (2000, 2019), "ndvi_greening", False),
    # Big cases: the last case of every game, worth double. Tricky on purpose.
    ("colorado", "no2", None, "no2_vshape", True),
    ("beijing", "no2", None, "beijing_no2_humped", True),
    ("colorado", "air_temperature", ("first", 20), "temp_too_short", True),
    ("marmara", "air_temperature", ("first", 20), "temp_too_short", True),
    ("alps", "air_temperature", ("first", 20), "temp_too_short", True),
    ("siberia", "air_temperature", ("first", 20), "temp_too_short", True),
)

MODES = {"full": {"cases": 20, "lives": 5}, "quick": {"cases": 5, "lives": 3}}

# Labels of the switch at the top of the app: the investigation or the Detective exam.
VIEW_LABELS = {
    "en": {"case": "🔎 Investigation", "exam": "🕵️ Detective exam"},
    "tr": {"case": "🔎 Soruşturma", "exam": "🕵️ Dedektif sınavı"},
}
# Score needed for each rank in a five-case game; the game scales them by its number of cases.
RANK_THRESHOLDS = (0, 200, 450, 750, 1100)

# The verdict each hand-written note was written for. A note never explains another verdict.
WHY_FOR = {
    "temp_marmara": "up", "temp_recent": "up", "ndvi_greening": "up",
    "no2_rules": "down", "beijing_no2_plan": "down", "beijing_aod_plan": "down",
    "no2_vshape": "chance", "beijing_no2_humped": "chance", "temp_too_short": "chance",
}

WHY_SOURCES = {
    "temp_marmara": "IPCC (2021), AR6 WG I; MedECC (2020), MAR1",
    "temp_recent": "IPCC (2021), AR6 WG I",
    "no2_rules": "Krotkov et al. (2016), Atmos. Chem. Phys. 16, 4605-4629",
    "beijing_no2_plan": "Zheng et al. (2018), Atmos. Chem. Phys. 18, 14095-14111",
    "beijing_aod_plan": "Zheng et al. (2018), Atmos. Chem. Phys. 18, 14095-14111",
    "ndvi_greening": "Zhu et al. (2016), Nature Climate Change 6, 791-795",
}

WHY = {
    "en": {
        "temp_marmara": "The main cause is greenhouse gases such as CO₂, released by burning coal, oil "
                        "and gas: they trap heat like a blanket. On top of that, the Mediterranean basin "
                        "warms faster than the global average, which fits Marmara warming faster than "
                        "Colorado.",
        "temp_recent": "Greenhouse gases keep rising, and so does the warming. The last ten years were "
                       "among the warmest ever measured worldwide, so even a short 20-year window shows "
                       "a clear rise.",
        "temp_too_short": "Warming had already started, but the weather swings a lot from year to year. "
                          "Twenty years of evidence can't separate the warming from those swings; the "
                          "same place's full record gets the Confirmed stamp. Sometimes all a trend needs is a "
                          "longer record.",
        "no2_rules": "US emission rules for cars and power plants cut NO₂: cleaner engines, filters and "
                     "a shift from coal to gas. The OMI instrument on NASA's Aura satellite saw this decline across much of the "
                     "US.",
        "no2_vshape": "NO₂ drifted down until 2019 (cleaner cars are a likely reason), COVID lockdowns made 2020 the lowest "
                      "point, and it rose again afterwards, probably as traffic and industry came back. "
                      "A straight line can't fit something that falls and then rises. The OMI instrument "
                      "is also aging, so recent years need extra caution.",
        "beijing_no2_plan": "China started a national clean-air plan in 2013: less coal, and stricter "
                            "rules for power plants, factories and vehicles. Satellites saw NO₂ fall "
                            "after it.",
        "beijing_no2_humped": "NO₂ over Beijing rose until about 2011 and fell after China's 2013 "
                              "clean-air plan. A straight line can't fit a rise followed by a fall, so the "
                              "whole period looks like chance. Look at 2013 to 2025 alone and the fall is "
                              "Confirmed.",
        "beijing_aod_plan": "China's 2013 clean-air plan also targeted soot and dust (PM2.5): less coal "
                            "burning and cleaner factories. The satellite sees less haze since then.",
        "ndvi_greening": "Plants are getting greener in many parts of the world. The main reasons: "
                         "extra CO₂ speeds up plant growth, warming lengthens the growing season, and "
                         "tree planting and farming change the land. This data alone can't tell which "
                         "one dominates in Marmara.",
    },
    "tr": {
        "temp_marmara": "Ana sebep, kömür, petrol ve doğal gaz yakılınca açığa çıkan CO₂ gibi sera gazları: "
                        "ısıyı bir battaniye gibi tutuyorlar. Üstelik Akdeniz havzası dünya "
                        "ortalamasından daha hızlı ısınıyor; Marmara'nın Colorado'dan hızlı ısınması "
                        "buna uyuyor.",
        "temp_recent": "Sera gazları artmaya devam ediyor, ısınma da. Son on yıl, dünya genelinde "
                       "ölçülen en sıcak yıllar arasında; bu yüzden 20 yıllık kısa bir dönemde bile "
                       "artış belirgin.",
        "temp_too_short": "Isınma o yıllarda da başlamıştı, ama hava her yıl kendi başına çok oynar. 20 "
                          "yıllık delil ısınmayı bu oynamaların arasından ayırmaya yetmiyor; aynı yerin "
                          "tüm kaydında trend doğrulanıyor. Bazen bir trendin tek eksiği daha uzun bir "
                          "kayıttır.",
        "no2_rules": "ABD'de araçlar ve elektrik santralleri için konan emisyon kuralları NO₂'yi "
                     "azalttı: daha temiz motorlar, filtreler ve kömürden doğal gaza geçiş. NASA'nın Aura "
                     "uydusundaki OMI aleti bu düşüşü ABD'nin birçok yerinde gördü.",
        "no2_vshape": "NO₂ 2019'a kadar yavaşça düştü (temiz araçlar olası bir neden), 2020'de COVID kapanmalarıyla "
                      "en dibe indi, sonra muhtemelen trafik ve sanayi geri dönünce tekrar yükseldi. "
                      "Önce düşüp sonra yükselen bir şeye düz çizgi uymaz. Ayrıca OMI aleti yaşlandığı "
                      "için son yıllara temkinli bakmak gerekiyor.",
        "beijing_no2_plan": "Çin 2013'te ulusal bir temiz hava planı başlattı: daha az kömür, santraller, "
                            "fabrikalar ve araçlar için daha sıkı kurallar. Uydular bundan sonra NO₂'nin "
                            "düştüğünü gördü.",
        "beijing_no2_humped": "Pekin üzerindeki NO₂ 2011 civarına kadar arttı, Çin'in 2013 temiz hava "
                              "planından sonra düştü. Önce artıp sonra düşen bir şeye düz çizgi uymaz; bu "
                              "yüzden tüm dönem tesadüf gibi görünüyor. 2013–2025'e ayrı bakınca düşüş "
                              "doğrulanıyor.",
        "beijing_aod_plan": "Çin'in 2013 temiz hava planı is ve tozu da (PM2,5) hedefledi: daha az kömür "
                            "yakımı ve daha temiz fabrikalar. Uydu o zamandan beri daha az pus görüyor.",
        "ndvi_greening": "Dünyanın birçok yerinde bitkiler yeşilleniyor. Başlıca sebepler: havadaki "
                         "fazla CO₂'nin bitki büyümesini hızlandırması, ısınmayla uzayan büyüme mevsimi, "
                         "ağaçlandırma ve tarımdaki değişiklikler. Marmara'da hangisinin baskın olduğunu "
                         "bu veri tek başına söylemez.",
    },
}

CHARACTERS = {
    "en": {"air_temperature": "Mr. Heat", "snowfall": "Ms. Snow", "no2": "Mr. Exhaust",
           "aod": "Ms. Dust", "ndvi": "Auntie Green", "precipitation": "Ms. Rain",
           "hot_days": "Mr. Scorcher", "co": "Mr. Smoke", "black_carbon": "Mr. Soot",
           "co2": "Grandpa Carbon", "tree_cover": "Sister Forest", "groundwater": "Grandpa Well"},
    "tr": {"air_temperature": "Bay Sıcaklık", "snowfall": "Kar Hanım", "no2": "Egzoz Bey",
           "aod": "Toz Hanım", "ndvi": "Yeşil Teyze", "precipitation": "Yağmur Hanım",
           "hot_days": "Kavurucu Bey", "co": "Duman Bey", "black_carbon": "Kurum Bey",
           "co2": "Karbon Dede", "tree_cover": "Orman Abla", "groundwater": "Kuyu Dede"},
}

GAME_TEXT = {
    "en": {
        "title": "Detective exam",
        "intro_1": "A secret chart draws itself, year by year. The earlier you decide, the more points "
                   "you get.",
        "intro_2": "Correct answers in a row build a streak; a wrong answer costs a badge. The last case "
                   "is worth double.",
        "full": "Full exam: {n} cases", "quick": "Quick exam: {n} cases",
        "up": "Real increase", "down": "Real decrease", "chance": "Chance",
        "case": "Case {i} of {n}", "boss": "big case, double points", "file": "Secret file #{i}",
        "points_left": "Points left: {p}", "score": "{s} points", "lives": "{n} badges left",
        "correct": "Correct! +{p} points", "streak": "{m}x streak",
        "wrong": "Wrong. The answer was: {a}. You lost a badge.",
        "chance_line": "Chance of a fluke: {phrase}",
        "why": "Why? (a possible explanation)", "context": "Local context: {s}",
        "source": "Source: {s}",
        "next": "Next case", "result": "See your rank", "no_badges": "No badges left. See your rank",
        "over": "Exam over", "rank": "Your rank", "final": "{s} points · {c} cases solved · {b}",
        "badges_ok": "badges left", "badges_lost": "no badges left",
        "mute": "Mute", "unmute": "Unmute", "chart": "Secret chart drawing itself",
        "ranks": ["Rookie", "Trainee", "Detective", "Inspector", "Chief inspector"],
    },
    "tr": {
        "title": "Dedektif sınavı",
        "intro_1": "Gizli bir grafik yıl yıl kendi kendine çizilir. Ne kadar erken karar verirsen o "
                   "kadar çok puan alırsın.",
        "intro_2": "Üst üste doğru tahmin seri bonusu getirir, yanlış tahmin bir rozet götürür. Son dava "
                   "çift puan.",
        "full": "Tam sınav: {n} dava", "quick": "Hızlı sınav: {n} dava",
        "up": "Gerçek artış", "down": "Gerçek azalış", "chance": "Tesadüf",
        "case": "Dava {i} / {n}", "boss": "büyük dava, çift puan", "file": "Gizli dosya #{i}",
        "points_left": "Kalan puan: {p}", "score": "{s} puan", "lives": "{n} rozet kaldı",
        "correct": "Doğru! +{p} puan", "streak": "{m}x seri",
        "wrong": "Yanlış. Doğru cevap: {a}. Bir rozet gitti.",
        "chance_line": "Tesadüf ihtimali: {phrase}",
        "why": "Neden? (olası açıklama)", "context": "Yerel bilgi: {s}",
        "source": "Kaynak: {s}",
        "next": "Sonraki dava", "result": "Rütbeni gör", "no_badges": "Rozetin kalmadı. Rütbeni gör",
        "over": "Sınav bitti", "rank": "Rütben", "final": "{s} puan · {c} dava çözüldü · {b}",
        "badges_ok": "rozetin kaldı", "badges_lost": "rozetin kalmadı",
        "mute": "Sesi kapat", "unmute": "Sesi aç", "chart": "Kendi kendine çizilen gizli grafik",
        "ranks": ["Çaylak", "Stajyer", "Dedektif", "Komiser", "Başmüfettiş"],
    },
}


def _window(annual: pd.DataFrame, window) -> pd.DataFrame:
    if window is None:
        return annual
    years = annual["year"]
    if window[0] == "first":
        return annual[years <= years.min() + window[1] - 1]
    if window[0] == "last":
        return annual[years >= years.max() - window[1] + 1]
    start, end = window
    return annual[years.between(start, end)]


def _note_fits(note: str | None, truth: str, full_record_significant: bool) -> bool:
    """A hand-written note is shown only for the verdict it was written for."""
    if not note or WHY_FOR.get(note) != truth:
        return False
    return full_record_significant if note == "temp_too_short" else True


ABSOLUTE_RATE = {"air_temperature", "groundwater"}  # never shown as a percentage of the starting value


def _rate_text(lang: str, variable_key: str, result, intercept: float) -> str:
    texts = variable_text(lang, VARIABLES[variable_key])
    start_value = intercept + result.slope_per_year * result.start_year
    pct = abs(result.total_change / start_value * 100) if start_value > 0 else None
    # A percentage of a near-zero starting value (for example desert rain) is meaningless, so very
    # large percentages fall back to the change per decade. Temperature has no true zero, and the
    # groundwater value is a model's absolute storage (its caveat says only changes are meaningful),
    # so both always use the change per decade.
    if variable_key in ABSOLUTE_RATE or pct is None or pct > 300:
        decimals = VARIABLES[variable_key].decimals
        text = f"{num(result.slope_per_decade, lang, decimals, signed=True)} {texts['annual_unit']} {t(lang, 'per_decade')}"
    else:
        rising = result.slope_per_year > 0
        if lang == "tr":
            text = f"Trend çizgisine göre %{num(pct, lang, 0)} {'artış' if rising else 'düşüş'}"
        else:
            text = f"{num(pct, lang, 0)}% {'increase' if rising else 'decrease'} along the trend line"
    if not result.significant:
        text += " (anlamlı değil)" if lang == "tr" else " (not significant)"
    return text


def _case_plan() -> list[tuple]:
    """Full records of every prepared region and measurement, plus the special cases."""
    special_full = {(region, variable) for region, variable, window, _, _ in SPECIAL_CASES if window is None}
    plan = [
        (region, variable, None, None, False)
        for region in REGIONS for variable in VARIABLES
        if (region, variable) not in special_full
    ]
    return plan + list(SPECIAL_CASES)


def build_cases(lang: str, loader=load_processed) -> list[dict]:
    """All playable cases with their answers and localized texts (the game picks some per round)."""
    lang = lang if lang in GAME_TEXT else "en"
    cases: list[dict] = []
    annual_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
    for region_key, variable_key, window, note, boss in _case_plan():
        if region_key not in REGIONS or variable_key not in VARIABLES:
            continue
        key = (region_key, variable_key)
        if key not in annual_cache:
            monthly = loader(region_key, variable_key)
            annual_cache[key] = None if monthly is None else to_annual(monthly, VARIABLES[variable_key])[0]
        annual = annual_cache[key]
        if annual is None or len(annual) < MIN_YEARS:
            continue
        if variable_key == "snowfall" and annual["value"].max() < NO_SNOW_MAX_MM:
            continue  # it practically never snows here
        sub = _window(annual, window).sort_values("year").reset_index(drop=True)
        if len(sub) < MIN_YEARS:
            continue
        result = analyze_trend(sub["year"], sub["value"])
        if not result.agrees:
            continue  # a disputed or weak clue is not a fair puzzle
        truth = ("up" if result.slope_per_year > 0 else "down") if result.significant else "chance"
        full = analyze_trend(annual["year"], annual["value"])
        if _note_fits(note, truth, full.significant):
            why, context, source = WHY[lang][note], "", WHY_SOURCES.get(note, "")
            why_key = note
        else:
            direction = "none" if truth == "chance" else truth
            options = reasons(lang, variable_key, direction)
            why = options[0] if options else ""
            context = region_context(lang, region_key, variable_key) or ""
            source, why_key = "", f"catalog:{variable_key}:{direction}"
        years = sub["year"].astype(float)
        values = sub["value"].astype(float)
        intercept = float(values.mean() - result.slope_per_year * years.mean())
        stamp_status = "confirmed" if result.significant else "noevidence"
        cases.append(
            {
                "id": f"{region_key}-{variable_key}-{result.start_year}-{result.end_year}",
                "series": f"{region_key}-{variable_key}",
                "kind": variable_key,
                "boss": bool(boss),
                "truth": truth,
                "years": [int(y) for y in years],
                "values": [round(float(v), 4) for v in values],
                "a": intercept,
                "b": float(result.slope_per_year),
                "stamp": status_text(lang, stamp_status)[0],
                "stamp_class": stamp_status,
                "chance": chance_phrase(result.p_value, lang),
                "who": (f"{CHARACTERS[lang].get(variable_key) or variable_text(lang, VARIABLES[variable_key])['name']} · "
                        f"{region_name(lang, region_key, REGIONS[region_key].name)} · "
                        f"{result.start_year}–{result.end_year}"),
                "rate": _rate_text(lang, variable_key, result, intercept),
                "why_key": why_key,
                "why": why,
                "context": context,
                "source": source,
            }
        )
    return cases


def game_payload(lang: str, loader=load_processed) -> dict:
    lang = lang if lang in GAME_TEXT else "en"
    return {
        "lang": lang,
        "text": GAME_TEXT[lang],
        "modes": MODES,
        "thresholds": list(RANK_THRESHOLDS),
        "cases": build_cases(lang, loader),
    }


def render_game_html(lang: str, loader=load_processed) -> str:
    """A self-contained HTML page with the game, for ``streamlit.components.v1.html``."""
    payload = json.dumps(game_payload(lang, loader), ensure_ascii=False).replace("</", "<\\/")
    return GAME_HTML.replace("__LANG__", lang if lang in GAME_TEXT else "en").replace("__GAME_DATA__", payload)


GAME_HTML = r"""<!doctype html>
<html lang="__LANG__"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&display=swap" rel="stylesheet">
<style>
:root{--accent:#2a78d6;--accent-dark:#1c5cab;--text:#0b0b0b;--muted:#52514e;--faint:#898781;--border:#e1e0d9;--card:#f4f3f0;--ok:#1e7a3c;--ok-bg:#e3f2e7;--bad:#b3261e}
*{box-sizing:border-box}
body{margin:0;padding:4px 2px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--text);background:transparent;font-size:15px}
button{font:inherit;font-size:15px;padding:8px 14px;border:1px solid #c9c7bd;border-radius:8px;background:#fff;color:var(--text);cursor:pointer}
button:hover{border-color:var(--accent);color:var(--accent-dark)}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button.primary:hover{background:var(--accent-dark);color:#fff}
button.right{border-color:var(--ok);color:var(--ok);border-width:2px}
button.wrong{border-color:var(--bad);color:var(--bad);border-width:2px}
.hud{display:flex;align-items:center;gap:12px;font-size:14px;color:var(--muted);margin-bottom:8px;flex-wrap:wrap}
.eyebrow{font-family:'Special Elite','Courier New',monospace;letter-spacing:.1em;text-transform:uppercase}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
.bar{background:var(--border);border-radius:3px;margin:6px 0 8px}
.bar>div{height:7px;border-radius:3px;background:var(--accent);transition:width .1s linear}
.row{display:flex;gap:8px;flex-wrap:wrap}
.stamp{display:inline-block;font-family:'Special Elite','Courier New',monospace;text-transform:uppercase;letter-spacing:.08em;border:3px solid currentColor;border-radius:6px;padding:4px 14px;font-size:20px;background:rgba(255,255,255,.7);animation:slam .35s ease-out both}
.stamp.confirmed{color:var(--accent-dark)}.stamp.noevidence{color:var(--muted)}
.pop{animation:pop .25s ease-out both}
.streak{display:inline-block;background:var(--ok-bg);color:var(--ok);padding:2px 9px;border-radius:8px;font-weight:600}
.badge{font-size:17px;transition:opacity .3s}.badge.lost{opacity:.2;filter:grayscale(1)}
.why{margin-top:12px;background:#fff;border:1px solid var(--border);border-left:5px solid var(--accent);border-radius:0;padding:10px 14px}
p{margin:0}
@keyframes slam{0%{transform:scale(2.6) rotate(-14deg);opacity:0}60%{transform:scale(.92) rotate(-4deg);opacity:1}100%{transform:scale(1) rotate(-4deg);opacity:1}}
@keyframes pop{0%{transform:scale(.6);opacity:0}100%{transform:scale(1);opacity:1}}
@media (prefers-reduced-motion:reduce){.stamp,.pop{animation:none}}
</style></head><body>
<div class="hud">
  <span id="lives"></span><span id="round" style="flex:1;font-weight:600;letter-spacing:.02em"></span>
  <span id="combo"></span><span id="score" style="font-weight:600;color:var(--text)"></span>
  <button type="button" id="mute" style="padding:4px 10px">🔊</button>
</div>
<div class="card">
  <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--muted)"><span id="file" class="eyebrow"></span><span id="pts"></span></div>
  <div class="bar"><div id="bar" style="width:100%"></div></div>
  <svg id="chart" viewBox="0 0 640 210" width="100%" role="img"></svg>
</div>
<div id="start" style="margin-top:14px">
  <p id="intro1" style="margin-bottom:4px"></p>
  <p id="intro2" style="margin-bottom:12px;color:var(--muted)"></p>
  <div class="row"><button type="button" id="go-full" class="primary"></button><button type="button" id="go-quick"></button></div>
</div>
<div id="answers" class="row" style="margin-top:14px;display:none">
  <button type="button" data-a="up"></button><button type="button" data-a="down"></button><button type="button" data-a="chance"></button>
</div>
<div id="reveal" role="status" aria-live="polite" style="margin-top:14px"></div>
<script>
const G=__GAME_DATA__;
const T=G.text,$=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const ICON={up:"▲ ",down:"▼ ",chance:"🎲 "};
const fmt=(s,v)=>s.replace(/\{(\w+)\}/g,(m,k)=>k in v?v[k]:m);
let game=[],mode="full",i=0,score=0,lives=3,maxLives=3,streak=0,solved=0,shown=0,timer=null,phase="idle",muted=false,ac=null;
const svg=$("chart"),rev=$("reveal"),ans=$("answers"),btns=[...ans.querySelectorAll("button")];
const modeLabel=m=>fmt(T[m],{n:G.modes[m].cases});
btns.forEach(b=>b.textContent=ICON[b.dataset.a]+T[b.dataset.a]);
$("intro1").textContent=T.intro_1;$("intro2").textContent=T.intro_2;
$("go-full").textContent="▶ "+modeLabel("full");$("go-quick").textContent=modeLabel("quick");
svg.setAttribute("aria-label",T.chart);$("mute").setAttribute("aria-label",T.mute);
function tone(f,d,type,vol,when){if(muted)return;try{ac=ac||new(window.AudioContext||window.webkitAudioContext)();const o=ac.createOscillator(),g=ac.createGain(),t=ac.currentTime+(when||0);o.type=type||"sine";o.frequency.setValueAtTime(f,t);g.gain.setValueAtTime(vol||0.07,t);g.gain.exponentialRampToValueAtTime(0.0001,t+d);o.connect(g);g.connect(ac.destination);o.start(t);o.stop(t+d+0.02);}catch(e){}}
const sfx={tick:()=>tone(1400,0.025,"sine",0.012),ok:()=>{tone(660,0.12,"triangle",0.08);tone(990,0.2,"triangle",0.08,0.11);},bad:()=>tone(130,0.4,"sawtooth",0.05),stamp:()=>tone(80,0.14,"square",0.07),win:()=>[523,659,784,1047].forEach((f,k)=>tone(f,0.22,"triangle",0.07,k*0.13))};
function shuffle(a){for(let k=a.length-1;k>0;k--){const j=Math.floor(Math.random()*(k+1));[a[k],a[j]]=[a[j],a[k]];}return a;}
function pickGame(n){
  const reg=shuffle(G.cases.filter(c=>!c.boss)),boss=shuffle(G.cases.filter(c=>c.boss));
  const k=Math.max(0,n-1),want={up:Math.round(k*0.35),down:Math.round(k*0.25)};want.chance=k-want.up-want.down;
  const used=new Set(),out=[];
  const take=f=>{const j=reg.findIndex(c=>f(c)&&!used.has(c.series));if(j<0)return false;const c=reg.splice(j,1)[0];used.add(c.series);out.push(c);return true;};
  ["up","down","chance"].forEach(t=>{for(let m=0;m<want[t];m++)if(!take(c=>c.truth===t))break;});
  while(out.length<k&&take(()=>true));
  while(out.length<k&&reg.length)out.push(reg.shift());
  const g=shuffle(out);
  if(boss.length)g.push(boss[0]);else if(g.length)g.push(Object.assign({},g.pop(),{boss:true}));
  return g;
}
function el(n,a){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);return e;}
function pts(){const n=game[i].values.length;return Math.max(10,Math.round(100-90*(shown-3)/Math.max(1,n-3)));}
function hud(){
  let s="";for(let k=0;k<maxLives;k++)s+='<span class="badge'+(k<lives?"":" lost")+'">🛡️</span>';
  $("lives").innerHTML=s;$("lives").setAttribute("aria-label",fmt(T.lives,{n:lives}));
  $("score").textContent=fmt(T.score,{s:score});
  $("combo").innerHTML=streak>=2?'<span class="streak pop">'+fmt(T.streak,{m:Math.min(streak,3)})+"</span>":"";
}
function draw(full){
  svg.innerHTML="";const x0=20,x1=620,y0=12,y1=176;
  svg.appendChild(el("line",{x1:x0,y1:y1+12,x2:x1,y2:y1+12,stroke:"#c3c2b7","stroke-width":1}));
  if(phase==="idle"){const q=el("text",{x:320,y:112,"text-anchor":"middle",fill:"#b4b2a9","font-size":64,"font-family":"Special Elite, Courier New, monospace"});q.textContent="?";svg.appendChild(q);return;}
  const c=game[i],n=c.values.length,m=full?n:shown,vis=c.values.slice(0,m),src=full?c.values:vis;
  const mn=Math.min(...src),mx=Math.max(...src),sp=Math.max(mx-mn,Math.abs(mx)*0.02+1e-6),lo=mn-sp*0.25,hi=mx+sp*0.25;
  const ya=c.years[0],yb=c.years[n-1],X=y=>x0+(x1-x0)*(y-ya)/Math.max(1,yb-ya),Y=v=>y1-(y1-y0)*(v-lo)/(hi-lo);
  svg.appendChild(el("polyline",{points:vis.map((v,k)=>X(c.years[k]).toFixed(1)+","+Y(v).toFixed(1)).join(" "),fill:"none",stroke:"#52514e","stroke-width":1.6}));
  vis.forEach((v,k)=>{const head=!full&&k===m-1;svg.appendChild(el("circle",{cx:X(c.years[k]).toFixed(1),cy:Y(v).toFixed(1),r:head?5.5:3,fill:head?"#2a78d6":"#52514e"}));});
  if(full)svg.appendChild(el("line",{x1:X(ya),y1:Y(c.a+c.b*ya).toFixed(1),x2:X(yb),y2:Y(c.a+c.b*yb).toFixed(1),stroke:"#eb6834","stroke-width":3}));
  const t1=el("text",{x:x0,y:206,fill:"#52514e","font-size":12});t1.textContent=ya;
  const t2=el("text",{x:x1,y:206,"text-anchor":"end",fill:"#52514e","font-size":12});t2.textContent=c.years[m-1];
  svg.appendChild(t1);svg.appendChild(t2);
}
function upd(){const p=pts()*(game[i].boss?2:1);$("bar").style.width=pts()+"%";$("pts").textContent=fmt(T.points_left,{p:p});}
function beginCase(){
  const c=game[i];phase="reveal";shown=Math.min(3,c.values.length);rev.innerHTML="";
  btns.forEach(b=>b.classList.remove("right","wrong"));ans.style.display="flex";
  $("round").textContent=fmt(T.case,{i:i+1,n:game.length})+(c.boss?" · "+T.boss:"");
  $("file").textContent=fmt(T.file,{i:i+1});
  draw(false);upd();
  const step=Math.min(180,Math.max(55,Math.round(3000/c.values.length)));
  timer=setInterval(()=>{if(shown<c.values.length){shown++;draw(false);upd();if(shown%2===0)sfx.tick();}if(shown>=c.values.length){clearInterval(timer);timer=null;}},step);
}
function line(text,css){const p=document.createElement("p");p.style.cssText=css||"";p.textContent=text;return p;}
btns.forEach(b=>b.addEventListener("click",()=>{
  if(phase!=="reveal")return;phase="decided";if(timer){clearInterval(timer);timer=null;}
  const c=game[i],ok=b.dataset.a===c.truth,base=pts();
  shown=c.values.length;draw(true);sfx.stamp();
  let gained=0,mult=1;
  if(ok){streak++;solved++;mult=Math.min(streak,3);gained=base*mult*(c.boss?2:1);score+=gained;setTimeout(sfx.ok,180);}
  else{streak=0;lives--;setTimeout(sfx.bad,180);}
  b.classList.add(ok?"right":"wrong");hud();
  const head=document.createElement("div");head.style.cssText="display:flex;align-items:center;gap:14px;flex-wrap:wrap";
  const st=document.createElement("span");st.className="stamp "+c.stamp_class;st.textContent=c.stamp;
  const res=document.createElement("span");res.className="pop";res.style.cssText="font-size:16px;font-weight:600;color:"+(ok?"var(--ok)":"var(--bad)");
  res.textContent=ok?fmt(T.correct,{p:gained})+(mult>1?" · "+fmt(T.streak,{m:mult}):""):fmt(T.wrong,{a:T[c.truth]});
  head.appendChild(st);head.appendChild(res);rev.appendChild(head);
  rev.appendChild(line(c.who,"margin-top:12px;font-size:16px;font-weight:600"));
  rev.appendChild(line(c.rate+" · "+fmt(T.chance_line,{phrase:c.chance}),"margin-top:2px;font-size:14px;color:var(--muted)"));
  const box=document.createElement("div");box.className="why";
  box.appendChild(line(T.why,"font-weight:600;margin-bottom:4px"));
  box.appendChild(line(c.why,"line-height:1.55"));
  if(c.context)box.appendChild(line(fmt(T.context,{s:c.context}),"margin-top:6px;line-height:1.5;color:var(--muted)"));
  if(c.source)box.appendChild(line(fmt(T.source,{s:c.source}),"margin-top:6px;font-size:12px;color:var(--faint)"));
  rev.appendChild(box);
  const last=i>=game.length-1||lives<=0;
  const nx=document.createElement("button");nx.type="button";nx.className="primary";nx.style.marginTop="12px";
  nx.textContent=lives<=0?T.no_badges:(last?T.result:T.next);
  nx.addEventListener("click",()=>{if(last)finish();else{i++;beginCase();}});
  rev.appendChild(nx);
}));
function finish(){
  phase="over";ans.style.display="none";
  const scale=game.length/5;let r=T.ranks[0];
  G.thresholds.forEach((th,k)=>{if(score>=Math.round(th*scale))r=T.ranks[k];});
  $("round").textContent=T.over;if(score>=Math.round(G.thresholds[3]*scale))sfx.win();
  rev.innerHTML="";
  const box=document.createElement("div");box.className="card pop";
  box.appendChild(line(T.rank,"font-size:13px;color:var(--muted)"));
  const rk=line(r,"font-size:28px;margin-top:2px;color:var(--accent-dark)");rk.className="eyebrow";box.appendChild(rk);
  box.appendChild(line(fmt(T.final,{s:score,c:solved+" / "+game.length,b:lives>0?lives+" "+T.badges_ok:T.badges_lost}),"margin-top:4px;color:var(--muted)"));
  rev.appendChild(box);
  const row=document.createElement("div");row.className="row";row.style.marginTop="12px";
  ["full","quick"].forEach(m=>{const b=document.createElement("button");b.type="button";if(m===mode)b.className="primary";b.textContent="↻ "+modeLabel(m);b.addEventListener("click",()=>newGame(m));row.appendChild(b);});
  rev.appendChild(row);
}
function newGame(m){mode=m;maxLives=G.modes[m].lives;game=pickGame(G.modes[m].cases);i=0;score=0;lives=maxLives;streak=0;solved=0;hud();beginCase();}
$("go-full").addEventListener("click",()=>{$("start").style.display="none";sfx.stamp();newGame("full");});
$("go-quick").addEventListener("click",()=>{$("start").style.display="none";sfx.stamp();newGame("quick");});
$("mute").addEventListener("click",()=>{muted=!muted;$("mute").textContent=muted?"🔇":"🔊";$("mute").setAttribute("aria-label",muted?T.unmute:T.mute);});
$("round").textContent=T.title;$("file").textContent=T.title;$("pts").textContent="";hud();draw(false);
</script></body></html>
"""
