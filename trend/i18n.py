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
            "Temperature and snowfall come live from NASA POWER for any rectangle up to 10° × 10°. "
            "Air pollution and vegetation are available for prepared regions only, because NASA "
            "delivers them through slower services."
        ),
        "map_help": (
            "Draw a rectangle with the square tool on the left of the map, or move and resize the "
            "current one with the edit tool (pencil) and click Save. A button then appears below "
            "the map. Prepared regions and exact coordinates are in the left panel (on a phone, "
            "open it with the » button at the top left)."
        ),
        "use_drawn": "Investigate the drawn rectangle ({bbox})",
        "custom_name": "Custom area ({bbox})",
        "fetching": "Fetching NASA data for this area… (usually a few seconds, at most about a minute)",
        "err_range": "Latitudes must be between -90 and 90, longitudes between -180 and 180.",
        "err_order": "West must be smaller than east, and south smaller than north.",
        "err_too_big": (
            "The rectangle is too large: NASA POWER allows at most 10° of latitude and 10° of "
            "longitude. Make it smaller."
        ),
        "note_widened": (
            "The rectangle was widened to at least 2° in each direction, the smallest area NASA "
            "POWER serves."
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
            "Sıcaklık ve kar yağışı, 10° × 10°'ye kadar her dikdörtgen için NASA POWER'dan canlı "
            "gelir. Hava kirliliği ve bitki yeşilliği ise NASA'nın daha yavaş servislerinden geldiği "
            "için sadece hazır bölgelerde var."
        ),
        "map_help": (
            "Haritanın solundaki kare aracıyla bir dikdörtgen çiz ya da mevcut dikdörtgeni "
            "düzenleme aracıyla (kalem) taşıyıp boyutlandır ve araç çubuğundaki Save düğmesine bas. "
            "Ardından haritanın altında bir düğme çıkar. Hazır bölgeler ve tam koordinatlar sol "
            "paneldedir (telefonda sol üstteki » düğmesiyle aç)."
        ),
        "use_drawn": "Çizilen dikdörtgeni incele ({bbox})",
        "custom_name": "Özel alan ({bbox})",
        "fetching": "Bu alan için NASA verisi getiriliyor… (genellikle birkaç saniye, en fazla yaklaşık bir dakika)",
        "err_range": "Enlemler -90 ile 90, boylamlar -180 ile 180 arasında olmalı.",
        "err_order": "Batı doğudan, güney de kuzeyden küçük olmalı.",
        "err_too_big": (
            "Dikdörtgen çok büyük: NASA POWER en fazla 10° enlem ve 10° boylama izin veriyor. "
            "Küçült."
        ),
        "note_widened": (
            "Dikdörtgen, NASA POWER'ın verdiği en küçük alan olan her yönde en az 2°'ye genişletildi."
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
        "prepared_only": (
            "Sadece hazır bölgeler",
            "Daha yavaş NASA servisleri gerektirdiği için seçili bölgelerde önceden hazırlanıyor.",
        ),
    },
}

REGION_NAMES = {"tr": {"colorado": "Colorado, ABD", "marmara": "İstanbul–Marmara, Türkiye"}}

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
        "ndvi": {
            "name": "Bitki yeşilliği (NDVI)",
            "definition": (
                "Bitkilerin ne kadar yeşil ve yoğun olduğu; -1 ile 1 arasında bir ölçek, yüksek değer "
                "daha fazla yeşil bitki demek."
            ),
            "annual_label": "Büyüme mevsimi (Mayıs–Eylül) ortalama NDVI",
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
- **Area average:** for temperature and snowfall, the value for {region} is the average of all NASA
  POWER grid cells whose centres lie inside or on the edge of the region's box, weighted by the
  cosine of latitude (cells centred on the edge reach about a quarter of a degree beyond the box).
  For air pollution and vegetation, NASA Giovanni and AppEEARS compute the average over the same
  box; for vegetation, pixels over the sea have no value and are left out.
- **One value per year:** monthly values are combined into one value per year, which removes the
  seasonal cycle. A year is used only if all of its months are available.
- **Headline test:** a straight line is fitted with ordinary least squares (OLS). We report its
  slope, the 95% confidence interval of the slope and the p-value of a two-sided t-test. The
  **p-value** is the chance of seeing a trend at least this strong if there were really no trend.
  We call a trend significant ("unlikely to be chance") when p < 0.05.
- **Year-to-year persistence:** when a year's departure from the trend line tends to be followed by
  a similar departure (positive autocorrelation), the uncertainty is widened using an effective
  sample size (Santer et al., 2000), which makes the result less overconfident (for short records
  the correction is only partial).
- **Second witness:** the Mann-Kendall test checks for a steady rise or fall without assuming a
  straight line; Sen's slope is a robust estimate of the rate. When neighbouring years are
  positively correlated, its uncertainty is widened with the same effective sample size as the
  headline test, so both tests count persistent years the same way.
- **Stamps:** *Confirmed* = significant and the second witness agrees; *Disputed* = significant but
  the second witness disagrees; *No evidence* = no significant trend; *Weak clue* = only the second
  witness sees a trend.
- **Total change** is the slope multiplied by the time span (last year minus first year), not the
  last value minus the first.
- **Confidence band:** the shaded band is the 95% confidence band of the fitted line, not a range for
  individual years.
- **Short periods:** at least {min_years} years are required; fewer than 20 years gives a warning.
- **Many tests:** if you test many measurements, regions and periods, about 1 in 20 tests can look
  significant by chance alone.
- **No significant trend detected** does not mean "no change"; a longer record may reveal one.
""",
    "tr": """
- **Bölge ortalaması:** sıcaklık ve kar yağışı için {region} değeri, merkezi bölge kutusunun
  içinde ya da kenarında kalan tüm NASA POWER ızgara hücrelerinin enlemin kosinüsüyle
  ağırlıklandırılmış ortalamasıdır (kenarda merkezlenen hücreler kutunun yaklaşık çeyrek derece
  dışına uzanır). Hava kirliliği ve bitki yeşilliği için ortalamayı aynı kutu üzerinden NASA
  Giovanni ve AppEEARS hesaplar; bitki yeşilliğinde deniz üzerindeki piksellerin değeri yoktur ve
  hesaba katılmaz.
- **Yılda tek değer:** aylık değerler her yıl için tek bir değerde birleştirilir; böylece mevsim
  döngüsü ortadan kalkar. Bir yıl yalnızca tüm ayları mevcutsa kullanılır.
- **Ana test:** en küçük kareler yöntemiyle (OLS) düz bir çizgi oturtulur. Eğimi, eğimin %95 güven
  aralığını ve iki yönlü t-testinin p-değerini veririz. **p-değeri**, gerçekte hiç trend yokken en
  az bu kadar güçlü bir trend görme ihtimalidir. p < 0,05 olduğunda trendi anlamlı ("tesadüf olması
  zor") kabul ederiz.
- **Yıldan yıla süreklilik:** bir yılın trend çizgisinden sapması, ardından gelen yılda benzer bir
  sapmayla devam ediyorsa (pozitif otokorelasyon), belirsizlik etkin örneklem büyüklüğüyle büyütülür
  (Santer ve ark., 2000); böylece sonuç daha az iddialı çıkar (kısa kayıtlarda bu düzeltme
  kısmidir).
- **İkinci tanık:** Mann-Kendall testi, düz bir çizgi varsaymadan istikrarlı bir artış ya da azalış
  olup olmadığına bakar; Sen eğimi, değişim hızının sağlam bir tahminidir. Komşu yıllar birbiriyle
  pozitif ilişkiliyse, bu testin belirsizliği de ana testteki aynı etkin örneklem büyüklüğüyle
  büyütülür; böylece iki test de birbirine benzeyen yılları aynı şekilde sayar.
- **Damgalar:** *Doğrulandı* = anlamlı ve ikinci tanık doğruluyor; *Tartışmalı* = anlamlı ama ikinci
  tanık doğrulamıyor; *Delil yok* = anlamlı trend yok; *Zayıf ipucu* = trendi sadece ikinci tanık
  görüyor.
- **Toplam değişim**, eğimin dönemin uzunluğuyla (son yıl eksi ilk yıl) çarpımıdır; son değer
  eksi ilk değer değildir.
- **Güven bandı:** gölgeli bant, oturtulan çizginin %95 güven bandıdır; tek tek yılların aralığı
  değildir.
- **Kısa dönemler:** en az {min_years} yıl gerekir; 20 yıldan kısa dönemlerde uyarı verilir.
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
    """Format a number with a decimal comma in Turkish and a decimal point in English."""
    text = f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"
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
