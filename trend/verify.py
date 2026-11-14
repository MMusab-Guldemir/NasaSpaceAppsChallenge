"""Verification: a second NASA dataset as a witness, and why a result is or is not verified.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. Team Avni asked to verify the results with more NASA data and to
explain why a result could not be verified. Reviewed by Claude Fable; its findings are applied.

1. Third witness: the same trend test on a second NASA dataset for the same place, over exactly the
   years both records have. For air temperature this is NASA GISTEMP v4 (weather stations, GISS)
   next to the MERRA-2 reanalysis that the app uses. Monthly witness series live in ``data/witness``.
   How independent each witness is, is said on the page; a close cousin (IMERG next to GPCP) is shown
   only as a high-resolution check, never as an extra witness.
2. Reasons: why a trend is not verified (short record, small change next to the year-to-year
   swings, the two tests disagree, a curved shape), with a rough record length that would give a 90%
   chance of detecting the change if it continued: Weatherhead et al. (1998, J. Geophys. Res. 103,
   17149-17161), eq. 2, written for annual values.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from trend.fetch import PROJECT_ROOT
from trend.i18n import chance_phrase, num, p_phrase, variable_text
from trend.linecheck import NEFF_LIMIT, line_check
from trend.stats import RECOMMENDED_YEARS, analyze_trend, to_annual
from trend.variables import VARIABLES

WITNESS_DIR = PROJECT_ROOT / "data" / "witness"
DETECT_Z = 3.3  # 1.96 (5%, two-sided) + 1.28 (90% power), as in Weatherhead et al. (1998)
MAX_YEARS = 150  # beyond this the change is too small to tell apart from the swings
WITNESS_MIN_YEARS = 10
SAME_SPEED = 0.67  # rates within a factor of 1.5 count as "roughly the same speed"
TOO_LITTLE_SNOW_MM = 10.0  # mean yearly snowfall below this in both records: too little to judge
CURVE_P = 0.01  # quadratic term this clear (plain OLS, so kept strict)
BREAK_VARIABLES = {"precipitation"}  # where the gap to a satellite-gauge record is checked for a break
BREAK_T = 7.0  # Welch t of the clearest before/after jump in the gap (strict: years are not independent)
BREAK_MIN_SIDE = 6  # years on each side of a jump
JUMP_NOT_DRIFT = 0.85  # two flat levels must leave under 85% of a straight line's squared error
AFRICA_RAIN_REGIONS = {"sahel", "cairo_nile"}  # MERRA-2 corrects rain with CMAP there, not CPC gauges
DESERT_REGIONS = {"medina", "cairo_nile"}  # rain records disagree a lot where it hardly rains
WITNESS_LAST_YEAR = {"aod": 2021}  # the app's aerosol data follow another satellite from April 2022
MODEL_WITNESSES = {"snowfall"}  # a model cross-check, not a measurement: never a contradiction
WEAK_SUPPORT_P = 0.20  # a witness that points the same way this clearly counts as weak support
STATION_WITNESSES = {"air_temperature"}  # GISTEMP stations: independent of MERRA-2 over land

# High-resolution checks that are close cousins of the witness (shown, not counted as a witness).
EXTRA_CHECKS = {
    "precipitation": ("imerg", "GPM IMERG", {"en": "satellites, about 10 km", "tr": "uydular, yaklaşık 10 km"}),
}

WITNESS_KIND = {
    "en": {
        "air_temperature": "Independent: weather-station records, while the app uses the MERRA-2 "
                           "reanalysis, which does not use station air temperatures over land.",
        "precipitation": "Partly independent: satellites plus rain gauges. The app's MERRA-2 rain is "
                         "corrected with NOAA CPC rain gauges, which share some station reports with this "
                         "record's GPCC gauges (how many is unknown).",
        "precipitation_africa": "Not independent (same family): over Africa the app's MERRA-2 rain is "
                                "corrected to GPCP version 2.1, an older version of this record, until "
                                "September 2009, and after that to CMAP rescaled to GPCP 2.1's average. "
                                "Agreement here is expected.",
        "precipitation_siberia": "Largely independent: north of 62.5° the app's MERRA-2 rain gets no gauge "
                                 "correction (very little at 60–62.5°), so it is model rain. Both records "
                                 "are least accurate this far north.",
        "snowfall": "A model cross-check, not a measurement: GLDAS-2.1 counts all precipitation as snow "
                    "whenever a weather model's air temperature is below 0 °C.",
        "aod": "Not independent: the app's aerosol values (CERES SYN1deg) are a model held close to MODIS "
               "Terra and Aqua readings until March 2022; from April 2022 they follow VIIRS on NOAA-20. "
               "Agreement checks consistency, not truth.",
        "ndvi": "A second satellite (Aqua) with the same kind of instrument as the app's Terra data.",
        "co": "A different satellite instrument (AIRS).",
        "default": "Another NASA dataset for the same place.",
    },
    "tr": {
        "air_temperature": "Bağımsız: meteoroloji istasyonlarının ölçümleri; uygulama ise karada istasyon "
                           "sıcaklıklarını kullanmayan MERRA-2 reanalizini kullanıyor.",
        "precipitation": "Kısmen bağımsız: uydular ve yağmur ölçerler. Uygulamadaki MERRA-2 yağışı NOAA CPC "
                         "yağmur ölçerleriyle düzeltiliyor; bunlar bu kaydın GPCC yağmur ölçerleriyle bazı "
                         "istasyon raporlarını paylaşıyor (kaç tane olduğu bilinmiyor).",
        "precipitation_africa": "Bağımsız değil (aynı aile): Afrika'da uygulamadaki MERRA-2 yağışı Eylül 2009'a "
                                "kadar bu kaydın eski bir sürümü olan GPCP 2.1'e, sonrasında ise GPCP 2.1'in "
                                "ortalamasına göre ölçeklenmiş CMAP'e göre düzeltiliyor. Burada uyum "
                                "beklenen bir şey.",
        "precipitation_siberia": "Büyük ölçüde bağımsız: 62,5°'nin kuzeyinde uygulamadaki MERRA-2 yağışı hiç "
                                 "yağmur ölçer düzeltmesi almıyor (60–62,5° arasında çok az), yani model "
                                 "yağışı. Bu kadar kuzeyde iki kayıt da en az isabetli hâlinde.",
        "snowfall": "Ölçüm değil, bir model karşılaştırması: GLDAS-2.1, bir hava modelinin hava sıcaklığı "
                    "0 °C'nin altındayken düşen bütün yağışı kar sayıyor.",
        "aod": "Bağımsız değil: uygulamanın aerosol değerleri (CERES SYN1deg), Mart 2022'ye kadar MODIS Terra "
               "ve Aqua ölçümlerine yakın tutulan bir model; Nisan 2022'den itibaren NOAA-20 üzerindeki "
               "VIIRS'i izliyor. Uyum doğruluğu değil, tutarlılığı sınar.",
        "ndvi": "Uygulamanın Terra verisiyle aynı tür alete sahip ikinci bir uydu (Aqua).",
        "co": "Farklı bir uydu aleti (AIRS).",
        "default": "Aynı yer için başka bir NASA verisi.",
    },
}

NO_WITNESS = {
    "en": {
        "no2": "No independent witness: OMI is NASA's only long NO₂ record; the next satellite record "
               "(TROPOMI, ESA) starts in 2018, too short for a trend.",
        "black_carbon": "No independent witness: soot comes only from the MERRA-2 aerosol reanalysis; no "
                        "satellite can measure soot mass directly.",
        "co2": "No independent witness: OCO-2 GEOS is NASA's only CO₂ record for these years (2015 "
               "onward), so there is no second NASA record to compare.",
        "tree_cover": "No independent witness: MOD44B is NASA's only yearly tree-cover product.",
        "custom": "The third witness works for the prepared regions for now.",
        "incomplete": "The second NASA dataset has too few years in common with this record here (for "
                      "example, it cannot measure in the polar winter), so there is nothing to compare.",
        "default": "No second NASA dataset for this measurement and region yet.",
    },
    "tr": {
        "no2": "Bağımsız tanık yok: OMI, NASA'nın tek uzun NO₂ kaydı; bir sonraki uydu kaydı (TROPOMI, ESA) "
               "2018'de başlıyor, trend için çok kısa.",
        "black_carbon": "Bağımsız tanık yok: is yalnızca MERRA-2 aerosol reanalizinden geliyor; uydular is "
                        "kütlesini doğrudan ölçemiyor.",
        "co2": "Bağımsız tanık yok: OCO-2 GEOS, bu yıllar için (2015'ten beri) NASA'nın tek CO₂ kaydı; "
               "karşılaştırılacak ikinci bir NASA kaydı yok.",
        "tree_cover": "Bağımsız tanık yok: MOD44B, NASA'nın tek yıllık ağaç örtüsü ürünü.",
        "custom": "Üçüncü tanık şimdilik hazır bölgelerde çalışıyor.",
        "incomplete": "İkinci NASA verisinin bu kayıtla burada yeterince ortak yılı yok (örneğin kutup kışında "
                      "ölçüm yapamıyor), bu yüzden karşılaştıracak bir şey kalmıyor.",
        "default": "Bu ölçüm ve bölge için henüz ikinci bir NASA verisi yok.",
    },
}

VERIFY_TEXT = {
    "en": {
        "witness_title": "🧾 Third witness: another NASA dataset",
        "witness_intro": "We also checked a different NASA dataset for the same place: {source}.",
        "witness_found": "The second dataset finds {rate} per decade ({sig}, {p}), {start}–{end}.",
        "sig": "significant", "not_sig": "not significant",
        "overlap": "Both records are compared over the same {n} years ({start}–{end}); over those years the "
                   "main data show {rate} per decade ({sig}).",
        "flip_sig": " Unlike the full period, the main trend is significant over these years.",
        "flip_nosig": " Unlike the full period, the main trend is not significant over these years.",
        "confirmed": "✅ Two different NASA datasets agree on the direction and roughly on the speed: a "
                     "third witness backs the case.",
        "confirmed_direction": "✅ Both datasets see a significant change in the same direction, but at "
                               "different speeds ({a} and {b} per decade). The direction is backed; the "
                               "speed is not settled.",
        "confirmed_weak": "Both datasets point the same way and both are significant, but on one side the "
                          "second test (rank-based) disagrees: likely, but not proven.",
        "opposite": "⚠️ Contradiction: the two datasets see significant changes in opposite directions.",
        "not_seen": "⚠️ Over the compared years the second dataset shows no significant trend, so it does "
                    "not back this up.",
        "witness_sees": "🔍 Over the compared years the second dataset sees a significant change ({rate} per "
                        "decade), but the main data do not reach the evidence line there. The change may be "
                        "real; see below why the main data could not prove it.",
        "stations_sees": "🔍 Weather stations (GISTEMP) show clear {change} here ({rate} per decade). The app's "
                         "record points the same way but more slowly ({main_rate} per decade) and {miss} the "
                         "5% line. The stations are independent of the app's data, so the {change} is "
                         "probably real.",
        "stations_up": "warming",
        "stations_down": "cooling",
        "stations_close": "just misses",
        "stations_far": "does not reach",
        "neither": "Over the compared years neither dataset shows a clear trend.",
        "same_way_weak": "Over the compared years the second dataset points the same way ({rate} per decade) "
                         "but does not reach the evidence line: weak support, not a contradiction.",
        "same_family": "The two records point the same way ({a} and {b} per decade), but they are related "
                       "(see above), so this agreement is expected and is not independent support.",
        "disagree": "↔️ The records disagree over the compared years ({a} per decade in the app's data, {b} "
                    "in the second dataset), so the second dataset neither backs nor overturns this result.",
        "cut_aod": "Years after 2021 are left out: from April 2022 the app's aerosol data follow another "
                   "satellite (VIIRS), and Terra's orbit drifts.",
        "too_little": "There is too little snow here (a few millimetres a year in both records) to judge "
                      "a trend.",
        "corr": "With each record's own trend removed, their year-to-year ups and downs match closely "
                "(correlation r = {r}).",
        "corr_low": "With each record's own trend removed, their year-to-year ups and downs match only partly "
                    "(correlation r = {r}).",
        "corr_none": "With each record's own trend removed, their year-to-year ups and downs hardly match "
                     "(correlation r = {r}): the two records see different things here, so treat the "
                     "comparison with care.",
        "data_break": "⚠️ Around {year} the gap between the app's record and the satellite-and-gauge record "
                      "jumps by about {size} {unit} a year. One of the two records has a break there (we "
                      "cannot tell which), so treat this trend with care.",
        "extra_check": "High-resolution check: {source_short} ({detail}), {start}–{end}: {rate} per decade "
                       "({sig}, {p}). It is a close cousin of the second dataset (they share GPCC rain gauges "
                       "and come from the same NASA Goddard team), not an extra independent one.",
        "differ_air_temperature": "Why can they differ? MERRA-2 blends a weather model with observations "
                                  "on a grid of about 50 km; GISTEMP comes from weather stations. Where "
                                  "stations are few, or sit in growing cities (urban heat), the two can "
                                  "show different speeds.",
        "differ_precipitation": "Why can they differ? The app's MERRA-2 rain is model output corrected "
                                "with rain gauges, while GPCP merges satellites with gauges; where gauges "
                                "are few, the two drift apart.",
        "differ_precipitation_desert": "Why can they differ? In the desert, rain is rare and patchy, and "
                                       "rain records disagree a lot (their yearly totals here can differ "
                                       "several times over). A disagreement means the records disagree, "
                                       "not that the detective is wrong.",
        "differ_snowfall": "Why can they differ? MERRA-2 and GLDAS compute snow with different models, "
                           "and snow is very sensitive to temperature, so small differences grow. NASA calls "
                           "only GLDAS-2.0 consistent over time (2.1 is provisional), and published tests "
                           "found false, temperature-driven snow trends in it.",
        "differ_aod": "Why can they differ? CERES blends MODIS aerosol with a model, while MODIS is the "
                      "direct satellite retrieval; clouds and bright desert or snow surfaces make aerosol "
                      "hard to measure from space.",
        "differ_ndvi": "Why can they differ? Terra passes in the morning and Aqua in the afternoon, and "
                       "instrument ageing and orbit drift affect the two satellites differently.",
        "differ": "Why can they differ? Different instruments, grid sizes and methods can show different "
                  "speeds for the same place.",
        "why_title": "Why is it not verified?",
        "disputed": "The main test finds a significant trend, but the second test (based on rankings, "
                    "not on a straight line) disagrees: a few unusual years may be driving the result.",
        "weak": "The second test sees a change, but the main test does not reach the evidence line: "
                "there is a trace, but the evidence is weak.",
        "short": "The record is short ({n} years); at least {rec} years are recommended for a trend.",
        "close": "It is just short of the evidence line: chance alone gives a trend this strong {phrase} "
                 "(the line is 5%).",
        "noise": "The whole change over the period ({change} {unit}) is less than twice the typical "
                 "year-to-year swing (±{swing} {unit}), so it is hard to tell apart from the noise.",
        "curve": "The series goes one way and then the other; a straight line describes that shape "
                 "badly. Try shorter periods and look at each part.",
        "accel": "The change speeds up or slows down over the period; a straight line describes it only "
                 "roughly.",
        "need_years": "If it continued at this speed, roughly {need} years of records would give a 90% "
                      "chance of detecting it; the chosen period spans {span} years (roughly {more} more, "
                      "to around {year}). This is a rough estimate (Weatherhead et al., 1998).",
        "no_change": "If there is a change, it is too small to tell apart from the year-to-year swings in "
                     "this record.",
    },
    "tr": {
        "witness_title": "🧾 Üçüncü tanık: başka bir NASA verisi",
        "witness_intro": "Aynı yer için farklı bir NASA verisine de baktık: {source}.",
        "witness_found": "İkinci verinin bulduğu: on yılda {rate} ({sig}, {p}), {start}–{end}.",
        "sig": "anlamlı", "not_sig": "anlamlı değil",
        "overlap": "İki kayıt aynı {n} yıl üzerinden karşılaştırıldı ({start}–{end}); bu yıllarda ana veri: on "
                   "yılda {rate} ({sig}).",
        "flip_sig": " Tüm dönemden farklı olarak, ana trend bu yıllarda anlamlı.",
        "flip_nosig": " Tüm dönemden farklı olarak, ana trend bu yıllarda anlamlı değil.",
        "confirmed": "✅ İki farklı NASA verisi yön ve yaklaşık hız konusunda aynı fikirde: dosyayı üçüncü "
                     "bir tanık da destekliyor.",
        "confirmed_direction": "✅ İki veri de aynı yönde anlamlı değişim görüyor, ama hızları farklı "
                               "(on yılda {a} ve {b}). Yön destekleniyor; hız konusunda veriler ayrışıyor.",
        "confirmed_weak": "İki veri de aynı yönü gösteriyor ve ikisi de anlamlı, ama taraflardan birinde ikinci "
                          "test (sıralamaya dayalı) aynı fikirde değil: muhtemel ama kanıtlanmış değil.",
        "opposite": "⚠️ Çelişki: iki veri zıt yönlerde anlamlı değişim görüyor.",
        "not_seen": "⚠️ Karşılaştırılan yıllarda ikinci veri anlamlı bir trend göstermiyor; yani bunu "
                    "desteklemiyor.",
        "witness_sees": "🔍 Karşılaştırılan yıllarda ikinci veri anlamlı bir değişim görüyor (on yılda {rate}), "
                        "ama ana veri bu yıllarda kanıt eşiğine ulaşmıyor. Değişim gerçek olabilir; ana "
                        "verinin neden kanıtlayamadığı aşağıda.",
        "stations_sees": "🔍 Meteoroloji istasyonları (GISTEMP) burada belirgin bir {change} gösteriyor (on yılda "
                         "{rate}). Uygulamanın kaydı aynı yönü gösteriyor ama daha yavaş (on yılda {main_rate}) "
                         "ve {miss}. İstasyonlar uygulamanın verisinden bağımsız olduğu için bu {change} "
                         "muhtemelen gerçek.",
        "stations_up": "ısınma",
        "stations_down": "soğuma",
        "stations_close": "%5 sınırını kıl payı kaçırıyor",
        "stations_far": "%5 sınırına ulaşmıyor",
        "neither": "Karşılaştırılan yıllarda iki veri de belirgin bir trend görmüyor.",
        "same_way_weak": "Karşılaştırılan yıllarda ikinci veri aynı yönü gösteriyor (on yılda {rate}) ama kanıt "
                         "eşiğine ulaşmıyor: zayıf destek, çelişki değil.",
        "same_family": "İki kayıt aynı yönü gösteriyor (on yılda {a} ve {b}), ama akraba kayıtlar (yukarıya "
                       "bak); bu yüzden bu uyum beklenen bir şey ve bağımsız destek sayılmaz.",
        "disagree": "↔️ Karşılaştırılan yıllarda kayıtlar uyuşmuyor (uygulamanın verisinde on yılda {a}, ikinci "
                    "veride {b}); yani ikinci veri bu sonucu ne destekliyor ne de çürütüyor.",
        "cut_aod": "2021 sonrası yıllar dışarıda bırakıldı: Nisan 2022'den itibaren uygulamanın aerosol verisi "
                   "başka bir uyduyu (VIIRS) izliyor ve Terra'nın yörüngesi kayıyor.",
        "too_little": "Burada bir trendi yargılamak için kar çok az (iki kayıtta da yılda birkaç milimetre).",
        "corr": "Her kaydın kendi trendi çıkarıldığında, yıldan yıla iniş çıkışları büyük ölçüde örtüşüyor "
                "(korelasyon r = {r}).",
        "corr_low": "Her kaydın kendi trendi çıkarıldığında, yıldan yıla iniş çıkışları ancak kısmen örtüşüyor "
                    "(korelasyon r = {r}).",
        "corr_none": "Her kaydın kendi trendi çıkarıldığında, yıldan yıla iniş çıkışları neredeyse hiç "
                     "örtüşmüyor (korelasyon r = {r}): iki kayıt burada farklı şeyler görüyor, karşılaştırmaya "
                     "temkinli bak.",
        "data_break": "⚠️ {year} civarında uygulamanın kaydı ile uydu-yağmur ölçer kaydı arasındaki fark yılda "
                      "yaklaşık {size} {unit} birden değişiyor. İki kayıttan birinde o yıl bir kopukluk var "
                      "(hangisi olduğunu bilemiyoruz); bu yüzden bu trende temkinli bak.",
        "extra_check": "Yüksek çözünürlüklü kontrol: {source_short} ({detail}), {start}–{end}: on yılda {rate} "
                       "({sig}, {p}). İkinci verinin yakın akrabası (aynı GPCC yağmur ölçerlerini kullanıyorlar ve aynı "
                       "NASA Goddard ekibinden geliyorlar); ayrı bir bağımsız tanık sayılmaz.",
        "differ_air_temperature": "Neden farklı olabilir? MERRA-2 bir hava modelini gözlemlerle birleştiren "
                                  "yaklaşık 50 km'lik bir ızgara; GISTEMP ise meteoroloji istasyonlarının "
                                  "ölçümleri. İstasyonların az olduğu ya da büyüyen şehirlerde durduğu "
                                  "(kentsel ısı) yerlerde iki veri farklı hızlar gösterebilir.",
        "differ_precipitation": "Neden farklı olabilir? Uygulamadaki MERRA-2 yağışı yağmur ölçerlerle "
                                "düzeltilmiş bir model çıktısı; GPCP ise uyduları yağmur ölçerlerle "
                                "birleştiriyor. Yağmur ölçerlerin az olduğu yerlerde iki veri ayrışıyor.",
        "differ_precipitation_desert": "Neden farklı olabilir? Çölde yağış nadir ve dağınık; yağış kayıtları "
                                       "burada birbirinden çok ayrışıyor (yıllık toplamlar birkaç kat "
                                       "farklı olabiliyor). Uyuşmazlık, kayıtların anlaşmadığı anlamına "
                                       "geliyor; dedektifin yanıldığı değil.",
        "differ_snowfall": "Neden farklı olabilir? MERRA-2 ve GLDAS karı farklı modellerle hesaplıyor; kar "
                           "sıcaklığa çok duyarlı olduğu için küçük farklar büyüyor. NASA yalnızca GLDAS-2.0'ı "
                           "zaman içinde tutarlı sayıyor (2.1 geçici sürüm) ve yayımlanmış testler onda "
                           "sıcaklıktan kaynaklanan yanlış kar trendleri buldu.",
        "differ_aod": "Neden farklı olabilir? CERES, MODIS aerosol ölçümünü bir modelle birleştiriyor; MODIS "
                      "ise doğrudan uydu ölçümü. Bulutlar ve parlak çöl ya da kar yüzeyleri aerosolü uzaydan "
                      "ölçmeyi zorlaştırıyor.",
        "differ_ndvi": "Neden farklı olabilir? Terra sabah, Aqua öğleden sonra geçiyor; aletlerin yaşlanması "
                       "ve yörünge kayması iki uyduyu farklı etkileyebiliyor.",
        "differ": "Neden farklı olabilir? Farklı aletler, ızgara boyutları ve yöntemler aynı yer için farklı "
                  "hızlar gösterebilir.",
        "why_title": "Neden doğrulanamadı?",
        "disputed": "Ana test anlamlı bir trend buluyor ama ikinci test (düz çizgiye değil sıralamaya "
                    "dayanan) aynı fikirde değil: birkaç olağandışı yıl sonucu sürüklüyor olabilir.",
        "weak": "İkinci test bir değişim görüyor ama ana test kanıt eşiğine ulaşmıyor: iz var ama delil "
                "zayıf.",
        "short": "Kayıt kısa ({n} yıl); bir trend için en az {rec} yıl öneriliyor.",
        "close": "%5 sınırını kıl payı geçemiyor: bu kadar güçlü bir trend tesadüfen {phrase} ihtimalle "
                 "çıkıyor (sınır %5).",
        "noise": "Dönem boyunca toplam değişim ({change} {unit}), tipik yıllık oynamanın (±{swing} {unit}) iki "
                 "katından az; bu yüzden gürültüden ayırmak zor.",
        "curve": "Seri önce bir yöne sonra öbür yöne gidiyor; düz bir çizgi bu şekli iyi anlatamıyor. "
                 "Dönemi kısaltıp her parçaya ayrı bakmayı dene.",
        "accel": "Değişim dönem içinde hızlanıyor ya da yavaşlıyor; düz bir çizgi bunu ancak kabaca anlatıyor.",
        "need_years": "Bu hızla sürerse, onu %90 ihtimalle yakalamak için kabaca {need} yıllık kayıt gerekir; "
                      "seçilen dönem {span} yıla yayılıyor (kabaca {more} yıl daha, {year} civarına kadar). Bu kaba bir "
                      "tahmin (Weatherhead ve ark., 1998).",
        "no_change": "Bir değişim varsa bile, bu kayıttaki yıllık oynamalardan ayırt edilemeyecek kadar küçük.",
    },
}


def verify_text(lang: str) -> dict:
    return VERIFY_TEXT.get(lang, VERIFY_TEXT["en"])


def witness_kind(lang: str, variable_key: str, region_key: str | None = None) -> str:
    """How independent the witness is from the app's own data for this measurement and region."""
    kinds = WITNESS_KIND.get(lang, WITNESS_KIND["en"])
    if variable_key == "precipitation" and region_key in AFRICA_RAIN_REGIONS:
        return kinds["precipitation_africa"]
    if variable_key == "precipitation" and region_key == "siberia":
        return kinds["precipitation_siberia"]
    return kinds.get(variable_key, kinds["default"])


def no_witness_reason(lang: str, variable_key: str, custom: bool = False, incomplete: bool = False) -> str:
    """Why a case has no third witness (``incomplete``: a witness file exists but too few common years)."""
    reasons_ = NO_WITNESS.get(lang, NO_WITNESS["en"])
    if custom:
        return reasons_["custom"]
    if incomplete:
        return reasons_["incomplete"]
    return reasons_.get(variable_key, reasons_["default"])


def load_witness(region_key: str, variable_key: str, suffix: str = "") -> pd.DataFrame | None:
    """The monthly witness series for a prepared region and measurement, if any.

    ``suffix`` reads a companion file such as ``<region>_precipitation_imerg.csv``.
    """
    name = f"{region_key}_{variable_key}" + (f"_{suffix}" if suffix else "") + ".csv"
    path = WITNESS_DIR / name
    if not path.exists():
        return None
    witness = pd.read_csv(path, parse_dates=["date"])
    if witness.empty or "value" not in witness.columns:
        return None
    return witness


def residual_swing(years, values) -> float:
    """Standard deviation of the year-to-year swings around the straight trend line."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    if len(x) < 3:
        return float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    return float(np.std(y - (intercept + slope * x), ddof=2))


def years_needed(slope_per_year: float, swing: float, lag1: float) -> float:
    """Rough record length that detects a trend of this size with 90% chance at the 5% level.

    Weatherhead et al. (1998), eq. 2, written for annual values: the standard error of an OLS slope
    over n years is about swing * sqrt(12) / n^1.5, inflated by sqrt((1 + phi) / (1 - phi)) for
    year-to-year persistence phi (clipped to 0..0.9). It is a z-test approximation, so it is rough.
    """
    if not math.isfinite(swing) or swing <= 0:
        return float("nan")
    if abs(slope_per_year) < 1e-12:
        return math.inf
    phi = min(max(lag1 if math.isfinite(lag1) else 0.0, 0.0), 0.9)
    return (DETECT_Z * math.sqrt(12) * swing / abs(slope_per_year) * math.sqrt((1 + phi) / (1 - phi))) ** (2 / 3)


def curvature(years, values) -> tuple[float, bool]:
    """p-value of a quadratic term (plain OLS), and whether its turning point lies in the middle 60%."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    n = len(x)
    if n < 8:
        return 1.0, False
    mean, spread = x.mean(), (x.std() or 1.0)
    xc = (x - mean) / spread
    design = np.column_stack([np.ones(n), xc, xc ** 2])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    dof = n - 3
    cov = (resid @ resid / dof) * np.linalg.inv(design.T @ design)
    if cov[2, 2] <= 0 or beta[2] == 0:
        return 1.0, False
    p_value = float(2 * sps.t.sf(abs(beta[2] / math.sqrt(cov[2, 2])), dof))
    vertex = mean + spread * (-beta[1] / (2 * beta[2]))
    low, high = x.min(), x.max()
    inside = low + 0.2 * (high - low) <= vertex <= high - 0.2 * (high - low)
    return p_value, bool(inside)


def curvature_p(years, values) -> float:
    return curvature(years, values)[0]


def why_not_confirmed(annual: pd.DataFrame, result, status: str, lang: str, variable_key: str,
                      witness_verdict: str | None = None) -> list[str]:
    """Plain-language reasons why a trend is not verified (empty for a confirmed one).

    When the app shows the "not a straight line" note (trend/linecheck.py: a steady one-way change
    that the straight-line verdict calls chance), the noise, years-needed and no-change lines are left
    out: all three assume the straight line is the right shape, which that note has just ruled out.
    """
    if status == "confirmed":
        return []
    text = verify_text(lang)
    variable = VARIABLES[variable_key]
    unit = variable_text(lang, variable)["annual_unit"]
    decimals = getattr(variable, "decimals", 2)
    years, values = annual["year"], annual["value"]
    steady_curve = not result.significant and line_check(years, values, result).show
    lines = []
    if status == "disputed":
        lines.append(text["disputed"])
    elif status == "weak":
        lines.append(text["weak"])
    if result.n_years < RECOMMENDED_YEARS:
        lines.append(text["short"].format(n=result.n_years, rec=RECOMMENDED_YEARS))
    if not result.significant and 0.05 <= result.p_value < 0.10:
        lines.append(text["close"].format(phrase=chance_phrase(result.p_value, lang)))
    swing = residual_swing(years, values)
    change = abs(result.total_change)
    if not steady_curve and math.isfinite(swing) and change < 2 * swing:
        lines.append(text["noise"].format(swing=num(swing, lang, decimals), change=num(change, lang, decimals), unit=unit))
    p_curve, turning_inside = curvature(years, values)
    if p_curve < CURVE_P:
        lines.append(text["curve"] if turning_inside else text["accel"])
    if not result.significant and not steady_curve:
        need = years_needed(result.slope_per_year, swing, result.lag1_autocorrelation)
        span = result.end_year - result.start_year + 1
        if math.isnan(need):
            pass
        elif not math.isfinite(need) or need > MAX_YEARS:
            if witness_verdict != "witness_sees":
                lines.append(text["no_change"])
        elif need > span and result.n_effective >= NEFF_LIMIT:
            # With only a few independent years the estimate is too unsure to promise a date.
            more = math.ceil(need) - span
            lines.append(text["need_years"].format(need=math.ceil(need), span=span, more=more,
                                                   year=result.end_year + more))
    return lines


def detrended_corr(first: pd.Series, second: pd.Series) -> float | None:
    """Correlation of two yearly series after removing each one's own straight trend line."""
    common = pd.concat([first.rename("first"), second.rename("second")], axis=1, join="inner").dropna()
    if len(common) < 8:
        return None
    x = common.index.values.astype(float)
    residuals = []
    for column in ("first", "second"):
        y = common[column].values.astype(float)
        slope, intercept = np.polyfit(x, y, 1)
        residuals.append(y - (intercept + slope * x))
    if np.std(residuals[0]) == 0 or np.std(residuals[1]) == 0:
        return None
    return float(np.corrcoef(residuals[0], residuals[1])[0, 1])


def _step_t(diff: pd.Series, year: int, min_side: int) -> float:
    before, after = diff[diff.index < year], diff[diff.index >= year]
    if len(before) < min_side or len(after) < min_side:
        return float("nan")
    return float(sps.ttest_ind(after.values, before.values, equal_var=False).statistic)


def data_break(main: pd.Series, witness: pd.Series) -> dict | None:
    """A clear jump in the gap between two yearly records (main minus witness), over their common years.

    The clearest before/after jump must have a Welch t of at least BREAK_T (strict, because neighbouring
    years are not independent and many years are tried), and two flat levels must fit the gap clearly
    better than a straight line, so a slow drift is not called a jump. It cannot tell which record
    has the break.
    """
    diff = (main - witness).dropna()
    if len(diff) < 2 * BREAK_MIN_SIDE:
        return None
    best_year, best_t = None, 0.0
    for year in diff.index[BREAK_MIN_SIDE:len(diff) - BREAK_MIN_SIDE + 1]:
        value = _step_t(diff, int(year), BREAK_MIN_SIDE)
        if math.isfinite(value) and abs(value) > abs(best_t):
            best_year, best_t = int(year), value
    if best_year is None or abs(best_t) < BREAK_T:
        return None
    x = diff.index.values.astype(float)
    slope, intercept = np.polyfit(x, diff.values, 1)
    line_sse = float(((diff.values - (intercept + slope * x)) ** 2).sum())
    before, after = diff[diff.index < best_year], diff[diff.index >= best_year]
    step_sse = float(((before - before.mean()) ** 2).sum() + ((after - after.mean()) ** 2).sum())
    if line_sse <= 0 or step_sse / line_sse >= JUMP_NOT_DRIFT:
        return None
    return {"year": best_year, "size": float(after.mean() - before.mean()), "t": best_t}


def extra_check_line(region_key: str, variable_key: str, lang: str, start_year: int, end_year: int) -> str | None:
    """One line for a high-resolution companion record (for example IMERG next to GPCP), if any."""
    if variable_key not in EXTRA_CHECKS:
        return None
    suffix, short, detail = EXTRA_CHECKS[variable_key]
    monthly = load_witness(region_key, variable_key, suffix)
    if monthly is None:
        return None
    annual, _ = to_annual(monthly, VARIABLES[variable_key])
    annual = annual[annual["year"].between(start_year, end_year)]
    if len(annual) < WITNESS_MIN_YEARS:
        return None
    check = analyze_trend(annual["year"], annual["value"])
    text = verify_text(lang)
    decimals = getattr(VARIABLES[variable_key], "decimals", 2)
    unit = str(monthly["unit"].iloc[0]).split(" (")[0] if "unit" in monthly.columns else ""
    return text["extra_check"].format(
        source_short=short, detail=detail.get(lang, detail["en"]), start=check.start_year, end=check.end_year,
        rate=f"{num(check.slope_per_decade, lang, decimals, signed=True)} {unit}".strip(),
        sig=text["sig"] if check.significant else text["not_sig"], p=p_phrase(check.p_value, lang),
    )


def compare_witness(result, witness_monthly: pd.DataFrame, lang: str, variable_key: str,
                    start_year: int, end_year: int, main_annual: pd.DataFrame | None = None,
                    region_key: str | None = None) -> dict | None:
    """The second dataset's trend over exactly the years both records have, and what it means.

    Returns None when the two records share fewer than WITNESS_MIN_YEARS complete years.
    """
    text = verify_text(lang)
    variable = VARIABLES[variable_key]
    decimals = getattr(variable, "decimals", 2)
    witness_annual, _ = to_annual(witness_monthly, variable)
    witness_annual = witness_annual[witness_annual["year"].between(start_year, end_year)].reset_index(drop=True)
    cut = WITNESS_LAST_YEAR.get(variable_key)
    cut_note = None
    if cut is not None and end_year > cut:
        witness_annual = witness_annual[witness_annual["year"] <= cut].reset_index(drop=True)
        cut_note = text[f"cut_{variable_key}"]
    overlap_line, main_years = None, None
    if main_annual is not None:
        main_in = main_annual[main_annual["year"].between(start_year, end_year)]
        common_years = sorted(set(main_in["year"]) & set(witness_annual["year"]))
        if len(common_years) < WITNESS_MIN_YEARS:
            return None
        main_common = main_in[main_in["year"].isin(common_years)].reset_index(drop=True)
        witness_annual = witness_annual[witness_annual["year"].isin(common_years)].reset_index(drop=True)
        main_years = main_common.set_index("year")["value"]
        if set(common_years) != set(main_in["year"]):
            full = result
            result = analyze_trend(main_common["year"], main_common["value"])
            main_unit = variable_text(lang, variable)["annual_unit"]
            overlap_line = text["overlap"].format(
                n=len(common_years), start=common_years[0], end=common_years[-1],
                rate=f"{num(result.slope_per_decade, lang, decimals, signed=True)} {main_unit}",
                sig=text["sig"] if result.significant else text["not_sig"],
            )
            if result.significant != full.significant:
                overlap_line += text["flip_sig"] if result.significant else text["flip_nosig"]
    if cut_note:
        overlap_line = f"{overlap_line} {cut_note}" if overlap_line else cut_note
    if len(witness_annual) < WITNESS_MIN_YEARS:
        return None
    witness = analyze_trend(witness_annual["year"], witness_annual["value"])
    unit = str(witness_monthly["unit"].iloc[0]).split(" (")[0] if "unit" in witness_monthly.columns else ""
    rate = f"{num(witness.slope_per_decade, lang, decimals, signed=True)} {unit}".strip()
    same_sign = (witness.slope_per_year > 0) == (result.slope_per_year > 0)
    too_little = (variable_key == "snowfall" and main_years is not None
                  and main_years.mean() < TOO_LITTLE_SNOW_MM
                  and witness_annual["value"].mean() < TOO_LITTLE_SNOW_MM)
    if too_little:
        verdict = "too_little"
    elif result.significant and witness.significant and same_sign:
        if not (result.agrees and witness.agrees):
            verdict = "confirmed_weak"
        else:
            small, big = sorted([abs(result.slope_per_decade), abs(witness.slope_per_decade)])
            verdict = "confirmed" if big == 0 or small / big >= SAME_SPEED else "confirmed_direction"
    elif result.significant and witness.significant:
        verdict = "opposite"
    elif result.significant:
        verdict = "same_way_weak" if same_sign and witness.p_value < WEAK_SUPPORT_P else "not_seen"
    elif witness.significant:
        verdict = "witness_sees"
    else:
        verdict = "neither"
    if verdict == "opposite" and not (result.agrees and witness.agrees):
        verdict = "disagree"  # one side's own rank test disagrees: not a clear contradiction
    if verdict == "witness_sees" and not witness.agrees:
        verdict = "disagree"  # the witness's own rank test does not back its change
    if variable_key in MODEL_WITNESSES and verdict in ("opposite", "witness_sees"):
        verdict = "disagree"  # a model cross-check can disagree, but it cannot prove or overturn
    if (variable_key == "precipitation" and region_key in AFRICA_RAIN_REGIONS
            and verdict in ("confirmed", "confirmed_direction", "confirmed_weak")):
        verdict = "same_family"  # related records: their agreement is expected, not independent support
    line_key = verdict
    if (verdict == "witness_sees" and variable_key in STATION_WITNESSES and same_sign
            and abs(result.slope_per_year) < abs(witness.slope_per_year)):
        line_key = "stations_sees"  # independent stations see it clearly; the app's record is slower
    lines = [text[line_key].format(
        rate=rate,
        a=num(result.slope_per_decade, lang, decimals, signed=True),
        b=num(witness.slope_per_decade, lang, decimals, signed=True),
        main_rate=f"{num(result.slope_per_decade, lang, decimals, signed=True)} {unit}".strip(),
        change=text["stations_up" if witness.slope_per_year > 0 else "stations_down"],
        miss=text["stations_close" if result.p_value < 0.10 else "stations_far"],
    )]
    found_break = None
    if variable_key in BREAK_VARIABLES and main_years is not None and verdict != "too_little":
        found_break = data_break(main_years, witness_annual.set_index("year")["value"])
        jump_explains = (found_break is not None and result.significant
                         and (found_break["size"] > 0) == (result.slope_per_year > 0))
        if jump_explains:
            size = abs(found_break["size"])
            lines.append(text["data_break"].format(
                year=found_break["year"], unit=unit,
                size=num(round(size, -1) if size >= 50 else size, lang, 0 if size >= 50 else 1),
            ))
        else:
            found_break = None
    lines.append(text["witness_found"].format(
        rate=rate, sig=text["sig"] if witness.significant else text["not_sig"],
        p=p_phrase(witness.p_value, lang), start=witness.start_year, end=witness.end_year,
    ))
    corr = None
    if main_years is not None:
        corr = detrended_corr(main_years, witness_annual.set_index("year")["value"])
        if corr is not None:
            tier = "corr" if corr >= 0.8 else "corr_low" if corr >= 0.3 else "corr_none"
            lines.append(text[tier].format(r=num(corr, lang, 2)))
    disagree = verdict in ("confirmed_direction", "confirmed_weak", "opposite", "not_seen", "witness_sees",
                           "disagree", "same_way_weak")
    if verdict != "too_little" and (disagree or (corr is not None and corr < 0.8)):
        desert = variable_key == "precipitation" and region_key in DESERT_REGIONS
        lines.append(text["differ_precipitation_desert"] if desert else text.get(f"differ_{variable_key}", text["differ"]))
    source = str(witness_monthly["source"].iloc[0]) if "source" in witness_monthly.columns else ""
    return {"verdict": verdict, "witness": witness, "corr": corr, "lines": lines, "source": source,
            "title": text["witness_title"], "intro": text["witness_intro"].format(source=source),
            "kind": witness_kind(lang, variable_key, region_key), "overlap": overlap_line,
            "break": found_break}
