"""English and Turkish texts for the app, plus number formatting per language.

Written with AI assistance (Claude Opus 5.5, Anthropic) for Team Avni,
NASA Space Apps Challenge 2026. English is the default language (the submission language);
Turkish is offered for local readers.
"""
from __future__ import annotations

from trend.variables import Variable

LANGUAGES = {"en": "EN", "tr": "TR"}

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "eyebrow": "NASA Earth data · Statistical investigation",
        "title": "Earth System Trend Detective",
        "subtitle": (
            "Pick a clue and a period. The detective checks NASA Earth data and tells you "
            "whether the change is real or could just be chance."
        ),
        "language": "Language",
        "region_label": "Region under investigation",
        "no_data_region": "No evidence has been collected for this region yet.",
        "step_where": "Step 1 · Where?",
        "step_what": "Step 2 · What do you want to investigate?",
        "step1_caption": "Each card is one measurement from NASA Earth data over its full record.",
        "group_climate": "Climate",
        "group_air": "Air",
        "group_carbon_green": "Carbon and green land",
        "short_record_note": (
            "This measurement has only {n} years of NASA data, fewer than the usual {usual}. The app "
            "allows it because the change is large compared with year-to-year swings; read the "
            "result with extra care."
        ),
        "examples_title": "Famous cases: open one with a single click",
        "why_title": "Why it matters",
        "why_body": (
            "- Claims about the climate and the environment are everywhere. This tool lets anyone "
            "check them against NASA's own measurements.\n"
            "- It shows how scientists decide whether a change is real: a trend, its uncertainty, a "
            "significance test and a second test of a different kind.\n"
            "- Every number can be downloaded and checked, so students and teachers can use it in "
            "class projects."
        ),
        "per_decade": "per decade",
        "evidence_pending": "Evidence pending",
        "investigate": "Investigate",
        "selected": "Selected",
        "case_label": "Case file · {region} · {variable}",
        "strip_eyebrow": "Case on the desk",
        "strip_link": "Read the case file ↓",
        "question": "Is the {subject} in {region} changing?",
        "question_body": "**{name}:** {definition} Each point on the chart is one {subject}.",
        "step_when": "Step 3 · When? Choose the period",
        "period_label": "Years to investigate",
        "too_short": (
            "Not enough evidence: a trend test needs at least {min} complete years, and this period "
            "has {n}. Pick a longer period."
        ),
        "step_verdict": "Step 4 · Real or chance?",
        "headline_up": "Unlikely to be chance: a significant upward trend",
        "headline_down": "Unlikely to be chance: a significant downward trend",
        "headline_disputed": "Borderline: the two tests disagree",
        "headline_chance": "Could be chance: no clear trend",
        "meter_question": (
            "If there were no real trend, how often would a trend this strong appear just by chance?"
        ),
        "meter_left": "Unlikely to be chance",
        "meter_right": "Could easily be chance",
        "meter_threshold": "5% line",
        "chance_tiny": "less than 0.1% of the time",
        "chance_over": "more than 99.9% of the time",
        "chance_value": "about {pct}% of the time",
        "how_much": "HOW MUCH",
        "total_change": "TOTAL CHANGE",
        "evidence_used": "EVIDENCE USED",
        "years_count": "{n} complete years",
        "ci": "95% CI {low} to {high}",
        "along_trend": "along the trend line",
        "verdict_sig": (
            "In **{region}**, the {subject} **{verb} by about {rate} {unit} per decade** from {start} "
            "to {end}, about {total} {unit} in total along the trend line. If there were no real "
            "trend, a trend this strong would appear by chance {chance}."
        ),
        "verb_up": "rose",
        "verb_down": "fell",
        "verdict_nosig": (
            "In **{region}**, **no significant trend was detected** in the {subject} from {start} to "
            "{end}. The values go up and down, but the overall direction cannot be told apart from "
            "natural year-to-year variation ({p})."
        ),
        "warn_short": (
            "Only {n} years of data. Trend tests are less reliable with fewer than {rec} years."
        ),
        "step_evidence": "Step 5 · The evidence",
        "based_on": "Based on {n} complete years ({start} to {end}).",
        "not_used": " Not used because incomplete: {years}.",
        "neff_note": (
            " Neighbouring years resemble each other, so these {n} years carry about as much "
            "information as {n_eff} independent years."
        ),
        "step_witness": "Step 6 · The second witness",
        "step_reasons": "Step 7 · Possible reasons",
        "reasons_intro_change": (
            "**The test shows that the {subject} changed, not why.** Reasons scientists often "
            "point to (checking them needs more evidence):"
        ),
        "reasons_intro_none": "**No clear trend.** Common reasons why a change may not show up:",
        "reasons_intro_disputed": (
            "**The two tests disagree, so this change is not certain.** If it is real, reasons "
            "scientists often point to (checking them needs more evidence):"
        ),
        "reason_covid": "The 2020 COVID-19 lockdowns briefly cut traffic and industry.",
        "local_context": "Local context",
        "witness_agrees": (
            "✅ **The second witness agrees:** the {method} test, which does not assume a straight "
            "line, finds {found} ({p}; Sen's slope {sen} {unit} per decade)."
        ),
        "witness_disagrees": (
            "⚠️ **The second witness disagrees:** the {method} test, which does not assume a "
            "straight line, finds {found} ({p}; Sen's slope {sen} {unit} per decade). "
            "Treat this verdict with caution."
        ),
        "found_increasing": "an increasing trend",
        "found_decreasing": "a decreasing trend",
        "found_none": "no significant trend",
        "cross_exam": (
            "Cross-examination: leaving out the newest year ({year}), whose data can still be revised, "
            "gives {rate} {unit} per decade ({p}, {sig})."
        ),
        "significant": "significant",
        "not_significant": "not significant",
        "case_notes": "Case notes",
        "keep_in_mind": "Keep in mind",
        "monthly_title": "Monthly values (with the seasonal cycle)",
        "monthly_caption": (
            "Monthly values still include the seasonal cycle, so they swing up and down every year."
        ),
        "table_title": "Data table and downloads",
        "months_used": "Months used",
        "source_recorded": "Source recorded when the data was fetched: {source}",
        "dl_annual": "Download the annual series (CSV)",
        "dl_results": "Download the case results (CSV)",
        "methods_title": "How the detective works (methods and limitations)",
        "data_label": "Data",
        "footer": (
            "Team Avni · NASA Space Apps Challenge 2026 · Built with AI assistance (Claude by "
            "Anthropic); see the README for details. Not affiliated with or endorsed by NASA."
        ),
        "band_name": "95% confidence band of the trend line",
        "trend_name": "Linear trend ({rate})",
        "month_axis": "Month",
        "map_caption": "The shaded box is the area averaged for {region}.",
        "share_title": "Share this case",
        "share_caption": (
            "This link opens exactly this case, period and language. Copy it with the button on the "
            "right of the box."
        ),
        "sidebar_title": "Choose the area",
        "mode_label": "Area type",
        "mode_prepared": "Prepared region",
        "mode_custom": "Anywhere on Earth (custom rectangle)",
        "coords_title": "Rectangle corners (degrees)",
        "west": "West longitude",
        "south": "South latitude",
        "east": "East longitude",
        "north": "North latitude",
        "apply_coords": "Investigate these coordinates",
        "custom_help": (
            "Temperature, precipitation, snowfall and dust and smoke come live from NASA POWER for "
            "any rectangle up to 40° × 40°. NO₂, carbon monoxide, soot, CO₂ and vegetation greenness "
            "are available for prepared regions only, because NASA delivers them through slower "
            "services that need a login."
        ),
        "map_help": (
            "Draw a rectangle with the square tool on the left of the map, or move and resize the "
            "current one with the edit tool (pencil) and click Save. A button then appears below "
            "the map. Prepared regions and exact coordinates are in the left panel (on a phone, "
            "open it with the » button at the top left)."
        ),
        "use_drawn": "Investigate the drawn rectangle ({bbox})",
        "custom_name": "Custom area ({bbox})",
        "fetching": "Fetching NASA data for this area… (usually a few seconds; large rectangles up to a minute)",
        "err_range": "Latitudes must be between -90 and 90, longitudes between -180 and 180.",
        "err_order": "West must be smaller than east, and south smaller than north.",
        "err_too_big": (
            "The rectangle is too large: at most 40° of latitude and 40° of longitude. Make it "
            "smaller."
        ),
        "note_small": (
            "This rectangle is smaller than NASA's data grid (cells of about 50 to 100 km), so its "
            "values come from the data cell inside it or the nearest one."
        ),
        "note_large": (
            "Large rectangle: NASA POWER sends at most 10° × 10° at a time, so the data comes in "
            "{n} pieces and can take up to a minute."
        ),
        "err_fetch": "NASA POWER did not answer for this area right now. Try again in a minute.",
        "fetch_failed_all": (
            "No evidence could be collected for this area because NASA POWER did not answer. "
            "Try again, or pick a prepared region in the left panel."
        ),
        "retry": "Try again",
        "err_no_data": "There is no {variable} data over this area (for example, open sea).",
    },
    "tr": {
        "eyebrow": "NASA Dünya verisi · İstatistiksel soruşturma",
        "title": "Dünya Sistemi Trend Dedektifi",
        "subtitle": (
            "Bir ipucu ve bir dönem seç. Dedektif NASA'nın Dünya verilerini inceler ve değişimin "
            "gerçek mi, yoksa tesadüf mü olduğunu söyler."
        ),
        "language": "Dil",
        "region_label": "İncelenen bölge",
        "no_data_region": "Bu bölge için henüz delil toplanmadı.",
        "step_where": "1. adım · Nerede?",
        "step_what": "2. adım · Neyi incelemek istiyorsun?",
        "step1_caption": "Her kart, NASA Dünya verisinden bir ölçümü tüm kayıt boyunca gösterir.",
        "group_climate": "İklim",
        "group_air": "Hava",
        "group_carbon_green": "Karbon ve yeşil alan",
        "short_record_note": (
            "Bu ölçümün yalnızca {n} yıllık NASA verisi var; her zamanki {usual} yıldan az. Değişim "
            "yıldan yıla dalgalanmaya göre büyük olduğu için izin veriyoruz; sonuca ekstra dikkatle bak."
        ),
        "examples_title": "Ünlü dosyalar: tek tıkla aç",
        "why_title": "Neden önemli?",
        "why_body": (
            "- İklim ve çevre hakkında her yerde iddialar var. Bu araç, herkesin bu iddiaları "
            "NASA'nın kendi ölçümleriyle kontrol etmesini sağlar.\n"
            "- Bilim insanlarının bir değişimin gerçek olup olmadığına nasıl karar verdiğini "
            "gösterir: trend, belirsizliği, anlamlılık testi ve farklı türde ikinci bir test.\n"
            "- Her sayı indirilip kontrol edilebilir; öğrenciler ve öğretmenler bunu sınıf "
            "projelerinde kullanabilir."
        ),
        "per_decade": "/ 10 yıl",
        "evidence_pending": "Delil bekleniyor",
        "investigate": "İncele",
        "selected": "Seçili",
        "case_label": "Dava dosyası · {region} · {variable}",
        "strip_eyebrow": "Masadaki dosya",
        "strip_link": "Dosyayı oku ↓",
        "question": "{region} bölgesinde {subject} değişiyor mu?",
        "question_body": "**{name}:** {definition} Grafikteki her nokta: {subject}.",
        "step_when": "3. adım · Ne zaman? Dönemi seç",
        "period_label": "İncelenecek yıllar",
        "too_short": (
            "Yeterli delil yok: trend testi için en az {min} tam yıl gerekiyor, bu dönemde {n} yıl "
            "var. Daha uzun bir dönem seç."
        ),
        "step_verdict": "4. adım · Gerçek mi, tesadüf mü?",
        "headline_up": "Tesadüf olması zor: anlamlı bir artış trendi",
        "headline_down": "Tesadüf olması zor: anlamlı bir azalış trendi",
        "headline_disputed": "Sınırda: iki test aynı fikirde değil",
        "headline_chance": "Tesadüf olabilir: belirgin bir trend yok",
        "meter_question": (
            "Gerçek bir trend olmasaydı, bu kadar güçlü bir trend ne sıklıkla tesadüfen ortaya çıkardı?"
        ),
        "meter_left": "Tesadüf olması zor",
        "meter_right": "Kolayca tesadüf olabilir",
        "meter_threshold": "%5 sınırı",
        "chance_tiny": "%0,1'den az",
        "chance_over": "%99,9'dan fazla",
        "chance_value": "yaklaşık %{pct}",
        "how_much": "NE KADAR",
        "total_change": "TOPLAM DEĞİŞİM",
        "evidence_used": "KULLANILAN DELİL",
        "years_count": "{n} tam yıl",
        "ci": "%95 güven aralığı: {low} ile {high}",
        "along_trend": "trend çizgisi boyunca",
        "verdict_sig": (
            "**{region}** bölgesinde {subject}, {start}–{end} arasında **on yılda yaklaşık {rate} "
            "{unit} {verb}**; trend çizgisi boyunca toplam yaklaşık {total} {unit}. Gerçek bir trend "
            "olmasaydı, bu kadar güçlü bir trendin tesadüfen ortaya çıkma ihtimali {chance} olurdu."
        ),
        "verb_up": "arttı",
        "verb_down": "azaldı",
        "verdict_nosig": (
            "**{region}** bölgesinde {subject} için {start}–{end} arasında **anlamlı bir trend tespit "
            "edilmedi**. Değerler inip çıkıyor, ama genel yön doğal yıldan yıla değişimden ayırt "
            "edilemiyor ({p})."
        ),
        "warn_short": (
            "Sadece {n} yıllık veri var. {rec} yıldan kısa dönemlerde trend testleri daha az güvenilir."
        ),
        "step_evidence": "5. adım · Delil",
        "based_on": "{n} tam yıla dayanıyor ({start}–{end}).",
        "not_used": " Eksik olduğu için kullanılmadı: {years}.",
        "neff_note": (
            " Komşu yıllar birbirine benzediği için bu {n} yıl, yaklaşık {n_eff} bağımsız yıl kadar "
            "bilgi taşıyor."
        ),
        "step_witness": "6. adım · İkinci tanık",
        "step_reasons": "7. adım · Olası nedenler",
        "reasons_intro_change": (
            "**Test, {subject} değerinin değiştiğini gösterir; nedenini göstermez.** Bilim "
            "insanlarının sık gösterdiği nedenler (doğrulamak için başka delil gerekir):"
        ),
        "reasons_intro_none": "**Belirgin bir trend yok.** Bir değişimin görünmemesinin yaygın nedenleri:",
        "reasons_intro_disputed": (
            "**İki test aynı fikirde değil, bu yüzden değişim kesin değil.** Gerçekse, bilim "
            "insanlarının sık gösterdiği nedenler (doğrulamak için başka delil gerekir):"
        ),
        "reason_covid": "2020'deki COVID-19 kapanmaları trafiği ve sanayiyi kısa süre azalttı.",
        "local_context": "Yerel bilgi",
        "witness_agrees": (
            "✅ **İkinci tanık doğruluyor:** düz bir çizgi varsaymayan {method} testinin sonucu: "
            "{found} ({p}; Sen eğimi on yılda {sen} {unit})."
        ),
        "witness_disagrees": (
            "⚠️ **İkinci tanık doğrulamıyor:** düz bir çizgi varsaymayan {method} testinin sonucu: "
            "{found} ({p}; Sen eğimi on yılda {sen} {unit}). Bu hükme temkinli yaklaş."
        ),
        "found_increasing": "artan trend",
        "found_decreasing": "azalan trend",
        "found_none": "anlamlı trend yok",
        "cross_exam": (
            "Çapraz sorgu: verisi henüz değişebilecek en yeni yılı ({year}) çıkarınca sonuç on yılda "
            "{rate} {unit} ({p}, {sig})."
        ),
        "significant": "anlamlı",
        "not_significant": "anlamlı değil",
        "case_notes": "Dosya notları",
        "keep_in_mind": "Dikkat edilecekler",
        "monthly_title": "Aylık değerler (mevsim döngüsüyle)",
        "monthly_caption": "Aylık değerlerde mevsim döngüsü hâlâ var, bu yüzden her yıl inip çıkıyorlar.",
        "table_title": "Veri tablosu ve indirme",
        "months_used": "Kullanılan ay",
        "source_recorded": "Veri çekilirken kaydedilen kaynak: {source}",
        "dl_annual": "Yıllık seriyi indir (CSV)",
        "dl_results": "Dosya sonuçlarını indir (CSV)",
        "methods_title": "Dedektif nasıl çalışır? (yöntem ve sınırlamalar)",
        "data_label": "Veri",
        "footer": (
            "Avni Takımı · NASA Space Apps Challenge 2026 · Yapay zekâ (Anthropic'in Claude'u) "
            "yardımıyla geliştirildi; ayrıntılar README'de. NASA ile bağlantılı değildir ve NASA "
            "tarafından onaylanmamıştır."
        ),
        "band_name": "Trend çizgisinin %95 güven bandı",
        "trend_name": "Doğrusal trend ({rate})",
        "month_axis": "Ay",
        "map_caption": "Gölgeli kutu, {region} için ortalaması alınan alan.",
        "share_title": "Bu dosyayı paylaş",
        "share_caption": (
            "Bu link tam olarak bu dosyayı, dönemi ve dili açar. Kutunun sağındaki düğmeyle "
            "kopyalayabilirsin."
        ),
        "sidebar_title": "Alanı seç",
        "mode_label": "Alan türü",
        "mode_prepared": "Hazır bölge",
        "mode_custom": "Dünyanın her yeri (özel dikdörtgen)",
        "coords_title": "Dikdörtgenin köşeleri (derece)",
        "west": "Batı boylamı",
        "south": "Güney enlemi",
        "east": "Doğu boylamı",
        "north": "Kuzey enlemi",
        "apply_coords": "Bu koordinatları incele",
        "custom_help": (
            "Sıcaklık, yağış, kar yağışı ve toz-duman, 40° × 40°'ye kadar her dikdörtgen için NASA "
            "POWER'dan canlı gelir. NO₂, karbon monoksit, is, CO₂ ve bitki yeşilliği ise NASA'nın giriş "
            "gerektiren daha yavaş servislerinden geldiği için sadece hazır bölgelerde var."
        ),
        "map_help": (
            "Haritanın solundaki kare aracıyla bir dikdörtgen çiz ya da mevcut dikdörtgeni "
            "düzenleme aracıyla (kalem) taşıyıp boyutlandır ve araç çubuğundaki Save düğmesine bas. "
            "Ardından haritanın altında bir düğme çıkar. Hazır bölgeler ve tam koordinatlar sol "
            "paneldedir (telefonda sol üstteki » düğmesiyle aç)."
        ),
        "use_drawn": "Çizilen dikdörtgeni incele ({bbox})",
        "custom_name": "Özel alan ({bbox})",
        "fetching": "Bu alan için NASA verisi getiriliyor… (genellikle birkaç saniye; büyük dikdörtgenlerde bir dakikayı bulabilir)",
        "err_range": "Enlemler -90 ile 90, boylamlar -180 ile 180 arasında olmalı.",
        "err_order": "Batı doğudan, güney de kuzeyden küçük olmalı.",
        "err_too_big": "Dikdörtgen çok büyük: en fazla 40° enlem ve 40° boylam olabilir. Küçült.",
        "note_small": (
            "Bu dikdörtgen NASA'nın veri ızgarasından küçük (hücreler yaklaşık 50–100 km), bu "
            "yüzden değerler içindeki ya da en yakındaki veri hücresinden geliyor."
        ),
        "note_large": (
            "Büyük dikdörtgen: NASA POWER bir seferde en fazla 10° × 10° gönderiyor, bu yüzden veri "
            "{n} parça halinde geliyor ve bir dakikayı bulabilir."
        ),
        "err_fetch": "NASA POWER şu an bu alan için cevap vermedi. Bir dakika sonra tekrar dene.",
        "fetch_failed_all": (
            "NASA POWER cevap vermediği için bu alan için delil toplanamadı. Tekrar dene ya da sol "
            "panelden hazır bir bölge seç."
        ),
        "retry": "Tekrar dene",
        "err_no_data": "Bu alanın üzerinde {variable} verisi yok (örneğin açık deniz).",
    },
}

STATUS: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "confirmed": ("Confirmed", "A significant trend: both tests agree."),
        "disputed": ("Disputed", "The headline test sees a trend, the second witness does not."),
        "noevidence": ("No evidence", "No significant trend detected."),
        "weak": ("Weak clue", "Only the second witness sees a trend."),
        "open": ("Open case", "Evidence still being collected."),
        "insufficient": (
            "Not enough data",
            "Too few complete years here, for example because the satellite cannot measure in the "
            "polar winter.",
        ),
        "no_snow": ("No snow", "It practically never snows here."),
        "no_data": ("No data", "NASA has no values for this measurement here, for example over open sea."),
        "prepared_only": (
            "Prepared regions only",
            "Needs slower NASA services, so it is prepared in advance for selected regions.",
        ),
    },
    "tr": {
        "confirmed": ("Doğrulandı", "Anlamlı bir trend: iki test de aynı fikirde."),
        "disputed": ("Tartışmalı", "Ana test trend görüyor, ikinci tanık görmüyor."),
        "noevidence": ("Delil yok", "Anlamlı bir trend tespit edilmedi."),
        "weak": ("Zayıf ipucu", "Trendi sadece ikinci tanık görüyor."),
        "open": ("Açık dosya", "Deliller hâlâ toplanıyor."),
        "insufficient": (
            "Yetersiz veri",
            "Burada yeterince tam yıl yok; örneğin uydu kutup kışında ölçüm yapamıyor.",
        ),
        "no_snow": ("Kar yok", "Burada neredeyse hiç kar yağmıyor."),
        "no_data": ("Veri yok", "NASA'nın burada bu ölçüm için değeri yok; örneğin açık deniz."),
        "prepared_only": (
            "Sadece hazır bölgeler",
            "Daha yavaş NASA servisleri gerektirdiği için seçili bölgelerde önceden hazırlanıyor.",
        ),
    },
}

REGION_NAMES = {
    "tr": {
        "colorado": "Colorado, ABD",
        "marmara": "İstanbul–Marmara, Türkiye",
        "medina": "Medine, Suudi Arabistan",
        "beijing": "Pekin, Çin",
        "los_angeles": "Los Angeles, ABD",
        "cairo_nile": "Kahire ve Nil Deltası, Mısır",
        "amazon": "Amazon ormanı (Rondônia), Brezilya",
        "sahel": "Sahel, Batı Afrika",
        "alps": "Alpler, İsviçre ve Avusturya",
        "siberia": "Sibirya (Yakutistan), Rusya",
    }
}

# "Possible reasons" step (idea of Team Avni). The trend test shows THAT something changed, not
# WHY, so these are common explanations from research, worded as possibilities.
REASONS: dict[str, dict[str, dict[str, list[str]]]] = {
    "en": {
        "air_temperature": {
            "up": [
                "Greenhouse gases from burning coal, oil and gas trap heat; this is warming almost "
                "every region of the world.",
                "Growing cities add extra local heat (the urban heat island), although this coarse "
                "NASA dataset mostly shows regional warming, not single cities.",
            ],
            "down": [
                "Cooling is rare in recent decades. It can come from natural cycles, more irrigation "
                "or more haze that blocks sunlight.",
            ],
            "none": [
                "Weather swings from year to year (and cycles such as El Niño) are large here "
                "compared with any steady change, so the period may be too short to tell them apart.",
            ],
        },
        "snowfall": {
            "up": [
                "Warmer air holds more moisture, so where it is still cold enough to snow, storms "
                "can bring more snow.",
                "Shifting storm tracks can bring more winter storms to a region.",
            ],
            "down": [
                "Warming turns more winter precipitation into rain instead of snow, especially at "
                "lower elevations.",
                "Drier winters or shifting storm tracks can also mean less snow.",
            ],
            "none": [
                "Snowfall depends on both temperature and precipitation, which can push in "
                "opposite directions, and it varies strongly from winter to winter.",
            ],
        },
        "no2": {
            "up": [
                "More traffic, industry and power plants as cities and economies grow.",
                "More fires or more fuel burning nearby.",
            ],
            "down": [
                "Cleaner cars, power plants and factories after emission rules such as exhaust "
                "standards.",
                "Less economic activity, for example during an economic slowdown.",
            ],
            "none": [
                "Growth (more traffic and industry) and cleaner technology can cancel each other "
                "out, and noise in the satellite measurement hides small changes.",
            ],
        },
        "aod": {
            "up": [
                "More desert dust storms, wildfires or smoke from burning fields.",
                "More air pollution from industry, traffic and coal burning.",
            ],
            "down": [
                "Clean-air rules that cut sulfur and soot from power plants, factories and vehicles.",
                "Fewer fires or fewer dust storms in recent years.",
            ],
            "none": [
                "Dust storms and wildfires make some years much hazier than others, which can hide "
                "a slow change.",
            ],
        },
        "precipitation": {
            "up": [
                "Warmer air holds more water vapour, so storms can drop more rain.",
                "Shifting storm tracks or monsoon changes can bring more rain to a region.",
            ],
            "down": [
                "Shifting storm tracks or a stronger dry season can bring less rain.",
                "Natural cycles that last several years (such as El Niño) can shift rainfall.",
            ],
            "none": [
                "Rain varies a lot from year to year, so a slow change is hard to see.",
            ],
        },
        "co": {
            "up": [
                "More fires, or more fuel burned for traffic, heating and industry.",
            ],
            "down": [
                "Cleaner engines with catalytic converters and cleaner industry.",
                "Fewer fires in recent years.",
            ],
            "none": [
                "Fires change a lot from year to year and can hide a slow change.",
            ],
        },
        "black_carbon": {
            "up": [
                "More diesel traffic, coal or wood burning, or more wildfires.",
            ],
            "down": [
                "Cleaner diesel engines and particle filters, and less coal and wood burning.",
                "Fewer wildfires in recent years.",
            ],
            "none": [
                "Fires and weather change soot from year to year and can hide a slow change.",
            ],
        },
        "co2": {
            "up": [
                "Burning coal, oil and gas adds CO₂ faster than plants and oceans can take it back.",
                "CO₂ spreads around the planet, so it rises almost everywhere at the same pace.",
            ],
            "down": [
                "A fall in CO₂ would be very unusual today; check the data and the period.",
            ],
            "none": [
                "The record here is short, so a change may not show up yet.",
            ],
        },
        "tree_cover": {
            "up": [
                "Forests growing back, tree planting, or plantations and orchards.",
            ],
            "down": [
                "Forest cut for farms, pasture or cities, or lost to wildfires.",
            ],
            "none": [
                "Losses and gains of trees can balance out, and small changes are hard to see.",
            ],
        },
        "ndvi": {
            "up": [
                "More rain or a longer, warmer growing season.",
                "More farming or irrigation, or forests growing back.",
                "More CO₂ in the air can help plants grow (the 'CO₂ fertilization' effect).",
            ],
            "down": [
                "Deforestation, wildfires or cities spreading over green land.",
                "Drought or hotter summers that stress plants.",
            ],
            "none": [
                "Rain varies a lot from year to year, so green and dry years can hide a slow change.",
            ],
        },
    },
    "tr": {
        "air_temperature": {
            "up": [
                "Kömür, petrol ve doğalgaz yakılınca çıkan sera gazları ısıyı tutar; bu, dünyanın "
                "neredeyse her bölgesini ısıtıyor.",
                "Büyüyen şehirler ek yerel ısı üretir (kentsel ısı adası); ancak bu kaba çözünürlüklü "
                "NASA verisi tek tek şehirleri değil, çoğunlukla bölgesel ısınmayı gösterir.",
            ],
            "down": [
                "Son on yıllarda soğuma nadirdir; doğal döngülerden, artan sulamadan ya da güneş "
                "ışığını engelleyen pustan kaynaklanabilir.",
            ],
            "none": [
                "Yıldan yıla hava değişimleri (ve El Niño gibi döngüler) buradaki istikrarlı "
                "değişime göre büyük; dönem, ikisini ayırt etmek için kısa olabilir.",
            ],
        },
        "snowfall": {
            "up": [
                "Isınan hava daha fazla nem taşır; hâlâ kar yağacak kadar soğuk yerlerde fırtınalar "
                "daha çok kar getirebilir.",
                "Kayan fırtına yolları bir bölgeye daha fazla kış fırtınası getirebilir.",
            ],
            "down": [
                "Isınma, kış yağışının daha büyük kısmını kar yerine yağmura çevirir; özellikle "
                "alçak yerlerde.",
                "Daha kurak kışlar ya da kayan fırtına yolları da daha az kar demek olabilir.",
            ],
            "none": [
                "Kar yağışı hem sıcaklığa hem yağışa bağlıdır; bunlar ters yönlere itebilir ve kar "
                "kıştan kışa çok değişir.",
            ],
        },
        "no2": {
            "up": [
                "Şehirler ve ekonomi büyüdükçe artan trafik, sanayi ve santraller.",
                "Yakınlarda daha fazla yangın ya da yakıt yakılması.",
            ],
            "down": [
                "Egzoz standartları gibi emisyon kurallarından sonra daha temiz arabalar, santraller "
                "ve fabrikalar.",
                "Azalan ekonomik faaliyet, örneğin ekonomik durgunluk dönemleri.",
            ],
            "none": [
                "Büyüme (daha çok trafik ve sanayi) ile daha temiz teknoloji birbirini dengeleyebilir; "
                "uydu ölçümündeki gürültü de küçük değişimleri gizler.",
            ],
        },
        "aod": {
            "up": [
                "Daha fazla çöl tozu fırtınası, orman yangını ya da tarla yakma dumanı.",
                "Sanayi, trafik ve kömür yakımından daha fazla hava kirliliği.",
            ],
            "down": [
                "Santral, fabrika ve araçlardan çıkan kükürt ve isi azaltan temiz hava kuralları.",
                "Son yıllarda daha az yangın ya da daha az toz fırtınası.",
            ],
            "none": [
                "Toz fırtınaları ve orman yangınları bazı yılları diğerlerinden çok daha puslu yapar; "
                "bu, yavaş bir değişimi gizleyebilir.",
            ],
        },
        "precipitation": {
            "up": [
                "Isınan hava daha fazla su buharı taşır; fırtınalar daha fazla yağmur bırakabilir.",
                "Kayan fırtına yolları ya da muson değişimleri bir bölgeye daha fazla yağmur getirebilir.",
            ],
            "down": [
                "Kayan fırtına yolları ya da daha güçlü bir kurak mevsim daha az yağmur getirebilir.",
                "Birkaç yıl süren doğal döngüler (El Niño gibi) yağışı kaydırabilir.",
            ],
            "none": [
                "Yağış yıldan yıla çok değişir; bu yüzden yavaş bir değişimi görmek zordur.",
            ],
        },
        "co": {
            "up": [
                "Daha fazla yangın ya da trafik, ısınma ve sanayi için daha fazla yakıt yakılması.",
            ],
            "down": [
                "Katalitik konvertörlü daha temiz motorlar ve daha temiz sanayi.",
                "Son yıllarda daha az yangın.",
            ],
            "none": [
                "Yangınlar yıldan yıla çok değişir ve yavaş bir değişimi gizleyebilir.",
            ],
        },
        "black_carbon": {
            "up": [
                "Daha fazla dizel trafik, kömür ya da odun yakımı veya daha fazla orman yangını.",
            ],
            "down": [
                "Daha temiz dizel motorlar ve partikül filtreleri, daha az kömür ve odun yakımı.",
                "Son yıllarda daha az orman yangını.",
            ],
            "none": [
                "Yangınlar ve hava koşulları isi yıldan yıla değiştirir ve yavaş bir değişimi gizleyebilir.",
            ],
        },
        "co2": {
            "up": [
                "Kömür, petrol ve doğalgaz yakmak, bitkilerin ve okyanusların geri alabileceğinden "
                "daha hızlı CO₂ ekliyor.",
                "CO₂ tüm gezegene yayılır; bu yüzden neredeyse her yerde aynı hızla artar.",
            ],
            "down": [
                "Bugün CO₂'nin düşmesi çok olağan dışı olurdu; veriyi ve dönemi kontrol et.",
            ],
            "none": [
                "Buradaki kayıt kısa; bir değişim henüz görünmeyebilir.",
            ],
        },
        "tree_cover": {
            "up": [
                "Yeniden büyüyen ormanlar, ağaçlandırma ya da plantasyonlar ve meyve bahçeleri.",
            ],
            "down": [
                "Tarla, mera ya da şehir için kesilen veya yangınlarda kaybedilen orman.",
            ],
            "none": [
                "Ağaç kayıpları ve kazançları birbirini dengeleyebilir; küçük değişimleri görmek zordur.",
            ],
        },
        "ndvi": {
            "up": [
                "Daha fazla yağmur ya da daha uzun, daha sıcak bir büyüme mevsimi.",
                "Daha fazla tarım ya da sulama, veya yeniden büyüyen ormanlar.",
                "Havadaki artan CO₂ bitkilerin büyümesine yardım edebilir ('CO₂ gübrelemesi').",
            ],
            "down": [
                "Ormansızlaşma, orman yangınları ya da yeşil alanlara yayılan şehirler.",
                "Bitkileri zorlayan kuraklık ya da daha sıcak yazlar.",
            ],
            "none": [
                "Yağış yıldan yıla çok değişir; yeşil ve kurak yıllar yavaş bir değişimi gizleyebilir.",
            ],
        },
    },
}

# Short local context for prepared regions (well-known facts, shown whatever the verdict is).
REGION_CONTEXT: dict[str, dict[str, dict[str, str]]] = {
    "en": {
        "beijing": {
            "no2": "China started a national clean-air plan in 2013. Try the period 2013 to 2025 "
                   "to see what happened after it.",
            "aod": "China's 2013 clean-air plan also targeted soot and dust (PM2.5).",
            "black_carbon": "China's 2013 clean-air plan cut coal burning and targeted soot. Try the "
                            "period 2013 to 2025.",
            "precipitation": "Check with a second record: NASA's GPCP satellite-gauge data show a "
                             "smaller rise here that is not significant (+38 mm per decade, p = 0.12, "
                             "1983-2025), so treat this result with caution.",
        },
        "los_angeles": {
            "no2": "California has some of the world's strictest vehicle exhaust rules, tightened "
                   "step by step since the 1990s. NO₂ here fell fastest before 2010, so one straight "
                   "line fits the whole record poorly and the cautious test cannot decide; from 2010 "
                   "to 2025 alone the decline is confirmed.",
        },
        "alps": {
            "no2": "European exhaust standards (Euro 1 to Euro 6) have lowered emissions from cars "
                   "and trucks since the 1990s.",
            "snowfall": "Snow in the Alps depends strongly on altitude: lower slopes are the most "
                        "sensitive to warming.",
        },
        "sahel": {
            "ndvi": "After severe droughts in the 1970s and 1980s, rains partly returned and "
                    "satellites saw the Sahel 'greening'.",
            "precipitation": "NASA's GPCP satellite-gauge record shows a rise here too (+29 mm per "
                             "decade, 1983-2025), in line with the rainfall recovery after the "
                             "1970s-80s droughts.",
        },
        "amazon": {
            "precipitation": "Suspicious clue: this record drops suddenly around 2005. NASA's GPCP "
                             "satellite-gauge record also shows drying here, but about half as strong "
                             "(-125 mm per decade, 1983-2025), so part of the drop probably comes from "
                             "a change in the rain-gauge data, not the weather.",
            "tree_cover": "Rondônia is part of the 'arc of deforestation', where forest has been "
                          "cleared for farms and pasture.",
            "ndvi": "Rondônia is part of the 'arc of deforestation', where forest has been cleared "
                    "for farms and pasture. Note: May to September is the growing season in the "
                    "northern mid-latitudes, but the dry season here, so this card measures "
                    "dry-season greenness.",
            "aod": "Smoke from dry-season fires used to clear forest makes some years very hazy.",
        },
        "siberia": {
            "air_temperature": "High northern latitudes are, on average, warming faster than the "
                               "world as a whole ('Arctic amplification'); compare this region's "
                               "rate with the other regions to see how strong it is here.",
            "aod": "Huge wildfires in Yakutia, for example in 2021, can make single years very "
                   "smoky.",
        },
        "cairo_nile": {
            "aod": "Desert dust, and in autumn the smoke from burning rice straw in the Nile Delta, "
                   "often cover Cairo in haze.",
        },
        "medina": {
            "aod": "Desert dust storms dominate the haze over the Arabian Peninsula.",
        },
    },
    "tr": {
        "beijing": {
            "no2": "Çin 2013'te ulusal bir temiz hava planı başlattı. Sonrasında ne olduğunu görmek "
                   "için 2013–2025 dönemini dene.",
            "aod": "Çin'in 2013 temiz hava planı is ve tozu (PM2,5) da hedefliyordu.",
            "black_carbon": "Çin'in 2013 temiz hava planı kömür yakımını azalttı ve isi hedefledi. "
                            "2013–2025 dönemini dene.",
            "precipitation": "İkinci bir kayıtla kontrol: NASA'nın GPCP uydu-yağmur ölçer verisi burada "
                             "daha küçük ve anlamlı olmayan bir artış gösteriyor (1983–2025, 10 yılda "
                             "+38 mm, p = 0,12); bu sonuca temkinli yaklaş.",
        },
        "los_angeles": {
            "no2": "Kaliforniya, 1990'lardan beri adım adım sıkılaştırılan, dünyanın en katı araç "
                   "egzoz kurallarından bazılarına sahip. Burada NO₂ en hızlı 2010'dan önce düştü; bu "
                   "yüzden tüm kayda tek bir düz çizgi iyi uymuyor ve temkinli test karar veremiyor. "
                   "Yalnızca 2010–2025'e bakınca düşüş doğrulanıyor.",
        },
        "alps": {
            "no2": "Avrupa egzoz standartları (Euro 1'den Euro 6'ya) 1990'lardan beri araba ve "
                   "kamyon emisyonlarını düşürdü.",
            "snowfall": "Alplerde kar büyük ölçüde yüksekliğe bağlı: ısınmaya en duyarlı yerler "
                        "alçak yamaçlar.",
        },
        "sahel": {
            "ndvi": "1970'ler ve 1980'lerdeki büyük kuraklıklardan sonra yağışlar kısmen geri döndü "
                    "ve uydular Sahel'in 'yeşillendiğini' gördü.",
            "precipitation": "NASA'nın GPCP uydu-yağmur ölçer kaydı da burada artış gösteriyor "
                             "(1983–2025, 10 yılda +29 mm); bu, 1970'ler-80'lerdeki kuraklıklardan "
                             "sonraki yağış toparlanmasıyla uyumlu.",
        },
        "amazon": {
            "precipitation": "Şüpheli ipucu: bu kayıt 2005 civarında aniden düşüyor. NASA'nın GPCP "
                             "uydu-yağmur ölçer kaydı da burada kuruma gösteriyor ama yaklaşık yarısı "
                             "kadar (1983–2025, 10 yılda −125 mm); bu yüzden düşüşün bir kısmı büyük "
                             "ihtimalle havadan değil yağmur ölçer verisindeki değişimden geliyor.",
            "tree_cover": "Rondônia, ormanın tarla ve mera için kesildiği 'ormansızlaşma yayının' "
                          "bir parçası.",
            "ndvi": "Rondônia, ormanın tarla ve mera için kesildiği 'ormansızlaşma yayının' bir "
                    "parçası. Not: Mayıs–Eylül kuzeydeki orta enlemlerde büyüme mevsimidir ama burada "
                    "kurak mevsimdir; yani bu kart kurak mevsimdeki yeşilliği ölçüyor.",
            "aod": "Orman açmak için kurak mevsimde çıkarılan yangınların dumanı bazı yılları çok "
                   "puslu yapıyor.",
        },
        "siberia": {
            "air_temperature": "Yüksek kuzey enlemleri ortalamada dünyanın geri kalanından daha "
                               "hızlı ısınıyor ('Arktik güçlenmesi'); buradaki hızı diğer bölgelerle "
                               "karşılaştır.",
            "aod": "Yakutistan'daki dev orman yangınları, örneğin 2021'de, bazı yılları çok dumanlı "
                   "yapabiliyor.",
        },
        "cairo_nile": {
            "aod": "Çöl tozu ve sonbaharda Nil Deltası'nda yakılan pirinç saplarının dumanı "
                   "Kahire'yi sık sık pusla kaplıyor.",
        },
        "medina": {
            "aod": "Arap Yarımadası'ndaki pusu çoğunlukla çöl tozu fırtınaları oluşturuyor.",
        },
    },
}


# Display names of the second-witness test (the English names come from trend.stats).
METHOD_NAMES = {
    "tr": {
        "Mann-Kendall": "Mann-Kendall",
        "persistence-adjusted Mann-Kendall": "sürekliliğe göre düzeltilmiş Mann-Kendall",
    }
}

VARIABLE_TEXT: dict[str, dict[str, dict]] = {
    "tr": {
        "air_temperature": {
            "name": "Hava sıcaklığı",
            "definition": "Yerden yaklaşık 2 metre yükseklikteki havanın ne kadar sıcak olduğu.",
            "annual_label": "Yıllık ortalama hava sıcaklığı",
            "unit": "°C",
            "annual_unit": "°C",
            "year_axis_label": "Yıl",
            "caveats": [
                "Reanaliz verisidir: milyonlarca gözlemle birleştirilmiş bir hava modeli, yaklaşık "
                "50 km'lik ızgara.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "snowfall": {
            "name": "Kar yağışı",
            "definition": "Ne kadar kar yağdığı; eridiğinde oluşturacağı su yüksekliği olarak ölçülür.",
            "annual_label": "Su yılı (Ekim–Eylül) toplam kar yağışı",
            "unit": "ayda mm su",
            "annual_unit": "mm su",
            "year_axis_label": "Su yılı (Ekim–Eylül, bitiş yılıyla adlandırılır)",
            "caveats": [
                "Bu kar yağışı MERRA-2 reanalizinden gelir (gözlemlerle yönlendirilen bir hava "
                "modeli); doğrudan kar ölçümü ya da kar derinliği değildir.",
                "Reanaliz trendleri, on yıllar içinde gözlem sistemindeki değişimleri de kısmen "
                "yansıtabilir.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "no2": {
            "name": "Hava kirliliği (NO₂)",
            "definition": (
                "Atmosferin alt katmanındaki azot dioksit; çoğunlukla taşıtlardan, santrallerden ve "
                "sanayiden gelen bir gaz."
            ),
            "annual_label": "Yıllık ortalama troposferik NO₂ sütunu",
            "unit": "10¹⁵ molekül/cm²",
            "annual_unit": "10¹⁵ molekül/cm²",
            "year_axis_label": "Yıl",
            "caveats": [
                "Değer tüm kutunun ortalamasıdır; kırsal alanlar ve kıyılarda deniz de dahil "
                "olduğu için şehirlerdeki kirlilik seyrelir.",
                "OMI aletindeki 'satır anomalisi' kullanılabilir ölçüm sayısını azaltır.",
                "2020'de COVID-19 salgınındaki azalan faaliyetle bağlantılı bir düşüş var.",
                "OMI aleti yaşlanıyor ve Aura uydusunun yörüngesi son yıllarda kayıyor; yaklaşık "
                "2022 sonrası değişimlere ekstra temkinle bak.",
            ],
        },
        "precipitation": {
            "name": "Yağış (yağmur ve kar)",
            "definition": "Gökyüzünden yağmur ve kar olarak düşen su miktarı; su yüksekliği olarak ölçülür.",
            "annual_label": "Yıllık toplam yağış",
            "unit": "ayda mm su",
            "annual_unit": "mm su",
            "year_axis_label": "Yıl",
            "caveats": [
                "MERRA-2 reanalizinden gelir; mümkün olan yerlerde ölçülen yağışla düzeltilmiştir; "
                "yaklaşık 50 km'lik ızgara.",
                "Yağış yıldan yıla çok değişir; bir trendin görünmesi için uzun kayıt gerekir.",
                "Düzeltmede kullanılan yağmur ölçer verileri on yıllar içinde değişir (bazı bölgelerde "
                "2000'lerin ortasından sonra çok daha az istasyon var); bu yüzden trendin bir kısmı "
                "havadan değil veriden gelebilir. NASA'nın GPCP uydu-yağmur ölçer kaydı iyi bir ikinci "
                "kontroldür.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "co": {
            "name": "Karbon monoksit (CO)",
            "definition": "Eksik yanmadan çıkan zehirli bir gaz: araba egzozu, sanayi, sobalar ve yangınlar.",
            "annual_label": "Yıllık ortalama karbon monoksit sütunu",
            "unit": "10¹⁸ molekül/cm²",
            "annual_unit": "10¹⁸ molekül/cm²",
            "year_axis_label": "Yıl",
            "caveats": [
                "Değer, yalnızca yerdeki değil tüm hava sütunundaki karbon monoksidi sayar.",
                "Amazon'daki gibi büyük yangın yılları öne çıkabilir; Sibirya gibi en kuzey "
                "bölgelerde kış ortasında gündüz ölçümü olmadığı için tam yıllık değer oluşturulamaz.",
                "Giovanni'deki MOPITT verisi şu an Aralık 2024'te bitiyor.",
            ],
        },
        "black_carbon": {
            "name": "Kara karbon (is)",
            "definition": "Dizel, kömür, odun ve orman yakılınca çıkan minik siyah is parçacıkları; yere yakın havada.",
            "annual_label": "Yere yakın havada yıllık ortalama kara karbon",
            "unit": "µg/m³",
            "annual_unit": "µg/m³",
            "year_axis_label": "Yıl",
            "caveats": [
                "MERRA-2 aerosol reanalizinden gelir: uydu aerosol ölçümleriyle yönlendirilen bir "
                "model, yaklaşık 50 km'lik ızgara.",
                "Modelin kullandığı emisyon verileri son yıllardaki gerçek değişimlerin gerisinde "
                "kalabilir.",
                "Orman yangını dumanı bazı yılları öne çıkarabilir.",
            ],
        },
        "co2": {
            "name": "Karbondioksit (CO₂)",
            "definition": "Ana sera gazı; çoğunlukla kömür, petrol ve doğalgaz yakılınca çıkar, bir kısmını bitkiler ve okyanuslar geri alır.",
            "annual_label": "Hava sütununda yıllık ortalama CO₂",
            "unit": "ppm",
            "annual_unit": "ppm",
            "year_axis_label": "Yıl",
            "caveats": [
                "Bu NASA kaydı yalnızca 2015–2021'i kapsıyor; bu yüzden burada her zamanki 10 yıl "
                "yerine 7 yıla izin veriyoruz. CO₂ o kadar düzenli artıyor ki 7 yıl bile bunu "
                "gösterebiliyor.",
                "CO₂ yaklaşık bir yıl içinde tüm gezegene karışır; bu yüzden yerel emisyon "
                "azaltımları bölgesel değerde neredeyse görünmez.",
                "OCO-2 uydu ölçümlerini GEOS modeliyle birleştirir.",
            ],
        },
        "aod": {
            "name": "Toz ve duman (aerosol)",
            "definition": (
                "Havadaki toz, duman ve kirlilik pusu gibi minik parçacıkların güneş ışığını ne kadar "
                "engellediği. Yüksek değer daha puslu hava demek."
            ),
            "annual_label": "Yıllık ortalama aerosol optik derinliği",
            "unit": "AOD (birimsiz)",
            "annual_unit": "AOD",
            "year_axis_label": "Yıl",
            "caveats": [
                "Aerosol optik derinliği yalnızca yerde soluduğumuz havayı değil, tüm hava "
                "sütunundaki parçacıkları sayar; bu yüzden PM2,5 ile aynı şey değildir.",
                "MODIS uydu ölçümleriyle düzeltilen bir aerosol modelinden (CERES SYN1deg) gelir; "
                "yaklaşık 100 km'lik (1 derece) ızgarada ve 2001'den itibaren.",
                "Kar ve buz üzerinde ve kutup kışının karanlığında değer yoktur; bu aylar hesaba "
                "katılmaz.",
                "Çöl toz fırtınaları ve büyük orman yangınları bazı yılları öne çıkarabilir.",
                "NASA POWER'daki en yeni aylar neredeyse gerçek zamanlı bir üründen gelebilir ve "
                "sonradan düzeltilebilir.",
            ],
        },
        "tree_cover": {
            "name": "Ağaç örtüsü",
            "definition": "Toprağın ağaç taçlarıyla kaplı kısmı, yüzde olarak.",
            "annual_label": "Ağaç örtüsü (yıllık harita)",
            "unit": "toprağın %'si",
            "annual_unit": "toprağın %'si",
            "year_axis_label": "Yıl",
            "caveats": [
                "Bir yılın MODIS görüntülerinden yapılan yıllık bir harita; su ve eksik pikseller "
                "hesaba katılmaz.",
                "Plantasyonlar ve meyve bahçeleri de ağaç sayılır; bu yüzden doğal orman küçülürken "
                "ağaç örtüsü artabilir.",
            ],
        },
        "ndvi": {
            "name": "Bitki yeşilliği (NDVI)",
            "definition": (
                "Bitkilerin ne kadar yeşil ve yoğun olduğu; -1 ile 1 arasında bir ölçek, yüksek değer "
                "daha fazla yeşil bitki demek."
            ),
            "annual_label": "Mayıs–Eylül ortalama NDVI",
            "unit": "NDVI (birimsiz)",
            "annual_unit": "NDVI",
            "year_axis_label": "Yıl",
            "caveats": [
                "Terra uydusunun yörüngesi yaklaşık 2020'den beri kayıyor; bu, son değerleri biraz "
                "etkileyebilir.",
            ],
        },
    }
}

METHODS = {
    "en": """
- **Area average:** for temperature, precipitation, snowfall and dust and smoke, the value for {region} is the
  average of all NASA POWER grid cells whose centres lie inside or on the edge of the box, weighted
  by the cosine of latitude (cells centred on the edge reach half a cell beyond the box). A
  rectangle smaller than one grid cell uses the nearest cell with data, and a rectangle larger than
  10° is fetched in pieces that are averaged together. For NO₂, carbon monoxide, soot and CO₂, NASA
  Giovanni computes the average over the same box, and for vegetation greenness and tree cover,
  NASA AppEEARS does; there, pixels over the sea have no value and are left out.
- **One value per year:** monthly values are combined into one value per year, which removes the
  seasonal cycle. A year is used only if all of its months are available.
- **Headline test:** a straight line is fitted with ordinary least squares (OLS). We report its
  slope, the 95% confidence interval of the slope and the p-value of a two-sided t-test. The
  **p-value** is the chance of seeing a trend at least this strong if there were really no trend.
  We call a trend significant ("unlikely to be chance") when p < 0.05.
- **Year-to-year persistence:** when a year's departure from the trend line tends to be followed by
  a similar departure (positive autocorrelation), the uncertainty is widened using an effective
  sample size (Santer et al., 2000) with a small-sample adjustment (Nychka et al., 2000), because
  short records underestimate this persistence.
- **How often can the detective be wrong?** In simulations of data with no trend at all, a false
  *Confirmed* appears in about 3% of cases when years are independent, in about 5-7% with moderate
  persistence over 15 years or more (about 10% with only 10 years), and in about 9-18% for very
  persistent series such as soot. Short records therefore get a warning.
- **How often does it find a real trend?** A real trend as large as one typical year-to-year swing
  per decade is confirmed in about 7% of cases with 10 years, 51% with 20, 81% with 25 and over 99%
  with 35 years or more (independent years); persistent years need longer records (41% with 25 years,
  95% with 45). So "no significant trend" often means "the record is too short", not "no change".
  The numbers can be reproduced with scripts/accuracy_report.py.
- **Second witness:** the Mann-Kendall test checks for a steady rise or fall without assuming a
  straight line; Sen's slope is a robust estimate of the rate. When neighbouring years are
  positively correlated, its uncertainty is widened with the same effective sample size as the
  headline test, so both tests count persistent years the same way.
- **Stamps:** *Confirmed* = significant and the second witness agrees; *Disputed* = significant but
  the second witness disagrees; *No evidence* = no significant trend; *Weak clue* = only the second
  witness sees a trend; *No snow* = it practically never snows there; *Not enough data* = fewer
  than {min_years} complete years; *No data* = NASA has no values there.
- **Total change** is the slope multiplied by the time span (last year minus first year), not the
  last value minus the first.
- **Confidence band:** the shaded band is the 95% confidence band of the fitted line, not a range for
  individual years.
- **Short periods:** at least {min_years} years are required (7 for CO₂, whose NASA record is
  short); fewer than 20 years gives a warning.
- **Possible reasons** are common explanations from research for a rise, a fall or no clear trend;
  the trend test itself cannot prove any of them.
- **Many tests:** if you test many measurements, regions and periods, about 1 in 20 tests can look
  significant by chance alone.
- **No significant trend detected** does not mean "no change"; a longer record may reveal one.
""",
    "tr": """
- **Bölge ortalaması:** sıcaklık, yağış, kar yağışı ve toz-duman için {region} değeri, merkezi kutunun
  içinde ya da kenarında kalan tüm NASA POWER ızgara hücrelerinin enlemin kosinüsüyle
  ağırlıklandırılmış ortalamasıdır (kenarda merkezlenen hücreler kutunun yarım hücre dışına uzanır).
  Bir hücreden küçük dikdörtgenlerde veri olan en yakın hücre kullanılır; 10°'den büyük
  dikdörtgenler parça parça getirilip birlikte ortalanır. NO₂, karbon monoksit, is ve CO₂ için
  ortalamayı aynı kutu üzerinden NASA Giovanni, bitki yeşilliği ve ağaç örtüsü için NASA AppEEARS
  hesaplar; orada deniz üzerindeki piksellerin değeri yoktur ve hesaba katılmaz.
- **Yılda tek değer:** aylık değerler her yıl için tek bir değerde birleştirilir; böylece mevsim
  döngüsü ortadan kalkar. Bir yıl yalnızca tüm ayları mevcutsa kullanılır.
- **Ana test:** en küçük kareler yöntemiyle (OLS) düz bir çizgi oturtulur. Eğimi, eğimin %95 güven
  aralığını ve iki yönlü t-testinin p-değerini veririz. **p-değeri**, gerçekte hiç trend yokken en
  az bu kadar güçlü bir trend görme ihtimalidir. p < 0,05 olduğunda trendi anlamlı ("tesadüf olması
  zor") kabul ederiz.
- **Yıldan yıla süreklilik:** bir yılın trend çizgisinden sapması, ardından gelen yılda benzer bir
  sapmayla devam ediyorsa (pozitif otokorelasyon), belirsizlik etkin örneklem büyüklüğüyle büyütülür
  (Santer ve ark., 2000); kısa kayıtlar bu sürekliliği olduğundan az gösterdiği için küçük örneklem
  düzeltmesi de uygulanır (Nychka ve ark., 2000).
- **Dedektif ne sıklıkla yanılabilir?** Hiç trend olmayan verilerle yapılan simülasyonlarda yanlış
  bir *Doğrulandı*, yıllar bağımsızken vakaların yaklaşık %3'ünde, orta süreklilikte 15 yıl ve
  üzerinde %5–7'sinde (yalnızca 10 yılda yaklaşık %10), is gibi çok sürekli serilerde %9–18'inde
  çıkıyor. Bu yüzden kısa kayıtlar uyarı alır.
- **Gerçek bir trendi ne sıklıkla bulur?** On yılda bir tipik yıllık dalgalanma kadar büyük gerçek
  bir trend, yıllar bağımsızken 10 yıllık kayıtta vakaların yaklaşık %7'sinde, 20 yılda %51'inde,
  25 yılda %81'inde, 35 yıl ve üzerinde %99'undan fazlasında doğrulanır; yıllar birbirine benziyorsa
  daha uzun kayıt gerekir (25 yılda %41, 45 yılda %95). Bu yüzden "anlamlı trend yok" çoğu zaman
  "kayıt kısa" demektir, "değişim yok" değil. Sayılar scripts/accuracy_report.py ile yeniden
  üretilebilir.
- **İkinci tanık:** Mann-Kendall testi, düz bir çizgi varsaymadan istikrarlı bir artış ya da azalış
  olup olmadığına bakar; Sen eğimi, değişim hızının sağlam bir tahminidir. Komşu yıllar birbiriyle
  pozitif ilişkiliyse, bu testin belirsizliği de ana testteki aynı etkin örneklem büyüklüğüyle
  büyütülür; böylece iki test de birbirine benzeyen yılları aynı şekilde sayar.
- **Damgalar:** *Doğrulandı* = anlamlı ve ikinci tanık doğruluyor; *Tartışmalı* = anlamlı ama ikinci
  tanık doğrulamıyor; *Delil yok* = anlamlı trend yok; *Zayıf ipucu* = trendi sadece ikinci tanık
  görüyor; *Kar yok* = orada neredeyse hiç kar yağmıyor; *Yetersiz veri* = {min_years} tam yıldan
  az; *Veri yok* = NASA'nın orada değeri yok.
- **Toplam değişim**, eğimin dönemin uzunluğuyla (son yıl eksi ilk yıl) çarpımıdır; son değer
  eksi ilk değer değildir.
- **Güven bandı:** gölgeli bant, oturtulan çizginin %95 güven bandıdır; tek tek yılların aralığı
  değildir.
- **Kısa dönemler:** en az {min_years} yıl gerekir (NASA kaydı kısa olan CO₂ için 7); 20 yıldan
  kısa dönemlerde uyarı verilir.
- **Olası nedenler**, bir artış, azalış ya da belirgin trend olmaması için araştırmalarda sık
  geçen açıklamalardır; trend testi bunların hiçbirini kanıtlayamaz.
- **Çok sayıda test:** çok sayıda ölçüm, bölge ve dönem test edersen, yaklaşık her 20 testten biri
  sadece tesadüfen anlamlı görünebilir.
- **Anlamlı trend tespit edilmedi** demek "değişim yok" demek değildir; daha uzun bir kayıt bir trend
  ortaya çıkarabilir.
""",
}


def t(lang: str, key: str, **values) -> str:
    """Translated text for ``key``, falling back to English."""
    text = TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"][key])
    return text.format(**values) if values else text


def status_text(lang: str, status: str) -> tuple[str, str]:
    return STATUS.get(lang, STATUS["en"])[status]


def region_name(lang: str, region_key: str, default: str) -> str:
    return REGION_NAMES.get(lang, {}).get(region_key, default)


def reasons(lang: str, variable_key: str, direction: str) -> list[str]:
    """Common explanations for a rise ("up"), a fall ("down") or no clear trend ("none")."""
    return REASONS.get(lang, REASONS["en"]).get(variable_key, {}).get(direction, [])


def region_context(lang: str, region_key: str, variable_key: str) -> str | None:
    return REGION_CONTEXT.get(lang, REGION_CONTEXT["en"]).get(region_key, {}).get(variable_key)


def method_name(lang: str, method: str) -> str:
    return METHOD_NAMES.get(lang, {}).get(method, method)


def variable_text(lang: str, variable: Variable) -> dict:
    """Display texts for a variable in the chosen language (English comes from the catalog)."""
    english = {
        "name": variable.name,
        "definition": variable.definition,
        "annual_label": variable.annual_label,
        "unit": variable.unit,
        "annual_unit": variable.annual_unit,
        "year_axis_label": variable.year_axis_label,
        "caveats": list(variable.caveats),
    }
    return {**english, **VARIABLE_TEXT.get(lang, {}).get(variable.key, {})}


def num(value: float, lang: str, decimals: int = 2, signed: bool = False) -> str:
    """Format a number with a decimal comma in Turkish and a decimal point in English.

    A value that rounds to zero is shown without a sign ("0.000", never "-0.000").
    """
    rounded = round(float(value), decimals)
    if rounded == 0:
        text = f"{0:.{decimals}f}"
    else:
        text = f"{rounded:+.{decimals}f}" if signed else f"{rounded:.{decimals}f}"
    return text.replace(".", ",") if lang == "tr" else text


def _digits_near(value: float, threshold: float, decimals: int) -> int:
    """Add decimals while rounding would put a value next to the 5% line on the line itself."""
    while decimals < 6 and value != threshold and round(value, decimals) == threshold:
        decimals += 1
    return decimals


def p_phrase(p: float, lang: str) -> str:
    """'p < 0.001', 'p = 0.046' or 'p > 0.999', with a decimal comma in Turkish."""
    if p < 0.001:
        return "p < 0,001" if lang == "tr" else "p < 0.001"
    if p > 0.999:
        return "p > 0,999" if lang == "tr" else "p > 0.999"
    return f"p = {num(p, lang, _digits_near(p, 0.05, 3))}"


def chance_phrase(p: float, lang: str) -> str:
    """How often a trend this strong would appear by chance, in words."""
    if p < 0.001:
        return t(lang, "chance_tiny")
    if p > 0.999:
        return t(lang, "chance_over")
    pct = p * 100
    return t(lang, "chance_value", pct=num(pct, lang, _digits_near(pct, 5.0, 1)))


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]
